"""Live status in the app, driven by a fake checker; nothing touches the network."""

import asyncio
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, Input, ListView, Static

from ssh_workbench import app as app_module
from ssh_workbench.app import SSHWorkbenchApp, StatusFinished, StatusSymbol
from ssh_workbench.config import Machine, format_machines
from ssh_workbench.forms import MachineForm
from ssh_workbench.status import AliasTarget, MachineStatus, State

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

MACHINES = (
    Machine("garden", "Garden", alias="garden-host"),
    Machine("studio", "Studio", addresses=("10.0.0.1", "192.0.2.40"), port=2222),
    Machine("lab", "Lab", addresses=("192.0.2.50",)),
    Machine("hop", "Hop", alias="hop-host"),
)
TARGETS = {
    "garden-host": AliasTarget("192.0.2.10", 22, proxied=False),
    "hop-host": AliasTarget("192.0.2.11", 22, proxied=True),
}


class FakeChecker:
    def __init__(self, open_hosts=("192.0.2.10", "192.0.2.40"), hold=None) -> None:
        self.open_hosts = set(open_hosts)
        self.hold = hold
        self.resolved: list[str] = []
        self.checked: list[tuple[str, int]] = []

    def _wait(self) -> None:
        if self.hold is not None:
            self.hold.wait(30)

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        self._wait()
        return TARGETS.get(alias)

    def port_open(self, host: str, port: int) -> bool:
        self.checked.append((host, port))
        self._wait()
        return host in self.open_hosts


def symbols(app: SSHWorkbenchApp) -> list[State]:
    return [widget.state for widget in app.query(StatusSymbol)]


def status_text(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#machine-status", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def checked(app, pilot) -> None:
    await wait_for(pilot, lambda: State.CHECKING not in symbols(app))


async def test_startup_shows_checking_then_each_result() -> None:
    hold = threading.Event()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, checker=checker)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert symbols(app) == [State.CHECKING] * 4
            assert status_text(app) == "◐ Checking"
            hold.set()
            await checked(app, pilot)
            assert symbols(app) == [
                State.ONLINE,
                State.ONLINE,
                State.OFFLINE,
                State.UNKNOWN,
            ]
            expected = [
                "● Online via alias",
                "● Online: 192.0.2.40",
                "○ Offline",
                "◇ Can't check: the alias uses ProxyJump or ProxyCommand",
            ]
            for index, text in enumerate(expected):
                app.query_one(ListView).index = index
                await pilot.pause()
                assert status_text(app) == text
            assert sorted(checker.resolved) == ["garden-host", "hop-host"]
            assert ("10.0.0.1", 2222) in checker.checked
            assert ("192.0.2.11", 22) not in checker.checked
    finally:
        hold.set()


async def test_refresh_resolves_aliases_again() -> None:
    checker = FakeChecker()
    app = SSHWorkbenchApp(MACHINES, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert checker.resolved.count("garden-host") == 1
        await pilot.press("r")
        await wait_for(pilot, lambda: checker.resolved.count("garden-host") == 2)
        await checked(app, pilot)
        assert symbols(app)[0] is State.ONLINE


async def test_timer_rounds_never_run_ssh_g(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "STATUS_INTERVAL", 0.05)
    checker = FakeChecker()
    app = SSHWorkbenchApp(MACHINES, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        first_round = checker.checked.count(("192.0.2.50", 22))
        await wait_for(
            pilot, lambda: checker.checked.count(("192.0.2.50", 22)) >= first_round + 2
        )
        assert sorted(checker.resolved) == ["garden-host", "hop-host"]
        assert checker.checked.count(("192.0.2.10", 22)) >= 2


async def test_connect_uses_the_first_online_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = Mock(return_value=0)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await pilot.press("down")
        app.action_connect()
        await pilot.pause()
        await pilot.press("down")
        app.action_connect()
        await pilot.pause()
        assert launcher.call_args_list[0].args == (MACHINES[1], "192.0.2.40")
        assert launcher.call_args_list[1].args == (MACHINES[2],)


async def test_results_from_an_older_round_are_ignored() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test() as pilot:
        await checked(app, pilot)
        before = symbols(app)
        app.post_message(
            StatusFinished(
                app._round - 1, "garden", MachineStatus(State.OFFLINE), None, None
            )
        )
        app.post_message(
            StatusFinished(
                app._round, "removed", MachineStatus(State.OFFLINE), None, None
            )
        )
        await pilot.pause()
        assert symbols(app) == before


@pytest.mark.parametrize("key", ["q", "ctrl+q"])
async def test_quit_never_waits_for_a_check(key: str) -> None:
    never = threading.Event()
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker(hold=never))
    async with asyncio.timeout(5):
        async with app.run_test() as pilot:
            await pilot.pause()
            assert State.CHECKING in symbols(app)
            await pilot.press(key)
            assert not app.is_running
    assert app._status_closed.is_set()


async def test_spinner_moves_only_when_animations_are_on() -> None:
    hold = threading.Event()
    try:
        for level, moves in (("full", True), ("none", False)):
            app = SSHWorkbenchApp(MACHINES[:1], checker=FakeChecker(hold=hold))
            app.animation_level = level
            async with app.run_test() as pilot:
                widget = app.query_one(StatusSymbol)
                seen = set()
                for _ in range(8):
                    seen.add(widget.render().plain)
                    await asyncio.sleep(0.12)
                    await pilot.pause()
                assert (len(seen) > 1) is moves
                assert seen <= {"◐", "◓", "◑", "◒"}
    finally:
        hold.set()


async def test_without_a_checker_nothing_is_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread = Mock(side_effect=AssertionError("Unexpected status thread"))
    monkeypatch.setattr(app_module, "Thread", thread)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert symbols(app) == [State.NOT_CHECKED] * 4
        assert status_text(app) == "· Not checked"
        assert app.check_action("refresh", ()) is None
        await pilot.press("r")
        thread.assert_not_called()


async def test_footer_keys_fit_at_60_columns() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(60, 20)) as pilot:
        footer = app.query_one(Footer)
        expected = {"connect", "open_link", "add", "edit", "delete", "refresh", "quit"}
        await wait_for(
            pilot, lambda: expected <= {key.action for key in footer.query("FooterKey")}
        )
        for key in footer.query("FooterKey"):
            # Windows Terminal cut the last column at 60x20; keep one spare.
            assert key.region.right <= 59, key.action


async def test_a_save_starts_a_round_without_resolving(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    text = format_machines(MACHINES)
    path.write_text(text, encoding="utf-8")
    checker = FakeChecker()
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await pilot.press("a")
        await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
        for field, value in (("id", "new"), ("name", "New"), ("alias", "new-host")):
            app.screen.query_one(f"#form-{field}", Input).value = value
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: len(app.query(StatusSymbol)) == 5)
        await checked(app, pilot)
        assert "new-host" not in checker.resolved
        assert symbols(app)[4] is State.UNKNOWN
        assert app.query_one(ListView).index == 4
        assert status_text(app) == "◇ Can't check: press R to resolve this alias"
        await pilot.press("r")
        await wait_for(pilot, lambda: "new-host" in checker.resolved)
