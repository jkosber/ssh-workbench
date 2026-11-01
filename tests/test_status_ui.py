"""Live status in the app, driven by a fake checker; nothing touches the network."""

import asyncio
import platform
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from textual import events
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, Input, ListView, RadioButton, Static

from ssh_workbench import app as app_module
from ssh_workbench.aliases import state_path
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


def details_id(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#machine-id", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


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
            assert status_text(app) == "▖ checking"
            hold.set()
            await checked(app, pilot)
            assert symbols(app) == [
                State.ONLINE,
                State.ONLINE,
                State.OFFLINE,
                State.UNKNOWN,
            ]
            expected = [
                "● online via alias",
                "● online: 192.0.2.40",
                "○ offline",
                "◇ can't check: the alias uses ProxyJump or ProxyCommand",
            ]
            for index, text in enumerate(expected):
                app.query_one(ListView).index = index
                # The details follow once Highlighted has bubbled to the app,
                # which a single pause does not guarantee.
                await wait_for(pilot, lambda: details_id(app) == MACHINES[index].id)
                assert status_text(app) == text
            assert sorted(checker.resolved) == ["garden-host", "hop-host"]
            assert ("10.0.0.1", 2222) in checker.checked
            assert ("192.0.2.11", 22) not in checker.checked
    finally:
        hold.set()


@pytest.mark.parametrize("key", ["r", "R"])
async def test_refresh_resolves_aliases_again(key: str) -> None:
    checker = FakeChecker()
    app = SSHWorkbenchApp(MACHINES, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert checker.resolved.count("garden-host") == 1
        await pilot.press(key)
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


async def test_shutdown_ignores_status_results_and_timers() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    app.animation_level = "full"
    seen: dict[str, tuple[int, int]] = {}
    errors: list[Exception] = []

    def during_shutdown(message: events.Event) -> None:
        # Textual turns is_running False, then removes the screens one widget at
        # a time while app timers and messages still run; each Unmount is a
        # step of that removal.
        if app.is_running or not isinstance(message, events.Unmount):
            return
        seen.setdefault("before", (app._round, app._frame))
        try:
            app.on_status_finished(
                StatusFinished(
                    app._round,
                    "lab",
                    MachineStatus(State.ONLINE, address="192.0.2.50"),
                    None,
                    None,
                )
            )
            app._timer_round()
            app._tick_animation()
        except Exception as error:
            errors.append(error)

    async with app.run_test(message_hook=during_shutdown) as pilot:
        await checked(app, pilot)
    assert errors == []
    assert seen["before"] == (app._round, app._frame)
    assert app._statuses["lab"] == MachineStatus(State.OFFLINE)


async def test_shutdown_skips_a_pending_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = SSHWorkbenchApp(MACHINES)
    rebuild = app._rebuild
    ran: list[int] = []
    queued: list[asyncio.Task[None]] = []

    async def recorded(select: int) -> None:
        ran.append(select)
        await rebuild(select)

    monkeypatch.setattr(app, "_rebuild", recorded)

    def during_shutdown(message: events.Event) -> None:
        # A save queues the rebuild; run_test's teardown can reach it while the
        # screens are being removed, or after. The task is kept and awaited, so
        # it runs either way.
        if app.is_running or not isinstance(message, events.Unmount) or queued:
            return
        queued.append(asyncio.get_running_loop().create_task(app._rebuild(2)))

    async with app.run_test(message_hook=during_shutdown) as pilot:
        await pilot.pause()
    await asyncio.gather(*queued)
    assert ran == [2]
    assert app._initial_index == 0


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


async def test_connect_during_a_round_uses_the_last_online_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = Mock(return_value=0)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    hold = threading.Event()
    hold.set()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, checker=checker)
    try:
        async with app.run_test() as pilot:
            await checked(app, pilot)
            hold.clear()
            await pilot.press("r")
            await pilot.pause()
            assert symbols(app)[1] is State.CHECKING
            await pilot.press("down")
            app.action_connect()
            await pilot.pause()
            assert launcher.call_args_list[0].args == (MACHINES[1], "192.0.2.40")
    finally:
        hold.set()


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
        assert "removed" not in app._statuses


class FailingChecker(FakeChecker):
    def port_open(self, host: str, port: int) -> bool:
        if host == "192.0.2.50":
            raise RuntimeError("fictional")
        return super().port_open(host, port)


async def test_a_check_that_fails_says_so() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FailingChecker())
    async with app.run_test() as pilot:
        await checked(app, pilot)
        app.query_one(ListView).index = 2
        await wait_for(pilot, lambda: details_id(app) == "lab")
        assert status_text(app) == "◇ can't check: the check failed"


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
                seen = {widget.render().plain}
                if moves:
                    # The interval timer drives the spinner.
                    async with asyncio.timeout(5):
                        while len(seen) < 2:
                            await pilot.pause()
                            seen.add(widget.render().plain)
                else:
                    for _ in range(8):
                        app._tick_animation()
                        seen.add(widget.render().plain)
                assert (len(seen) > 1) is moves
                assert seen <= {"▖", "▘", "▝", "▗"}
    finally:
        hold.set()


async def test_online_symbols_dim_for_half_of_each_pulse() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test() as pilot:
        await checked(app, pilot)
        widgets = list(app.query(StatusSymbol))
        dimmed: list[list[bool]] = [[] for _ in widgets]
        for frame in range(8):
            for widget, seen in zip(widgets, dimmed, strict=True):
                widget.frame = frame
                seen.append(widget.has_class("-dim"))
        pulse = [False] * 4 + [True] * 4
        assert dimmed == [pulse, pulse, [False] * 8, [False] * 8]


async def test_the_animation_moves_only_checking_and_online_symbols() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    app.animation_level = "full"
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert symbols(app) == [
            State.ONLINE,
            State.ONLINE,
            State.OFFLINE,
            State.UNKNOWN,
        ]
        widgets = list(app.query(StatusSymbol))
        before = [widget.frame for widget in widgets]
        app._tick_animation()
        app._tick_animation()
        moved = [w.frame - b for w, b in zip(widgets, before, strict=True)]
        assert moved == [2, 2, 0, 0]


async def test_without_a_checker_nothing_is_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread = Mock(side_effect=AssertionError("Unexpected status thread"))
    monkeypatch.setattr(app_module, "Thread", thread)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert symbols(app) == [State.NOT_CHECKED] * 4
        assert status_text(app) == "· not checked"
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
        # Regions are empty until the footer has been laid out.
        await wait_for(
            pilot, lambda: all(key.region.width for key in footer.query("FooterKey"))
        )
        for key in footer.query("FooterKey"):
            # Textual leaves the bottom-right cell empty on Windows, so the
            # footer must end before the last column.
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
        await wait_for(pilot, lambda: showing(app, MachineForm))
        for field, value in (("id", "new"), ("name", "New"), ("alias", "new-host")):
            app.screen.query_one(f"#form-{field}", Input).value = value
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: len(app.query(StatusSymbol)) == 5)
        await checked(app, pilot)
        assert "new-host" not in checker.resolved
        assert symbols(app)[4] is State.UNKNOWN
        assert app.query_one(ListView).index == 4
        assert status_text(app) == "◇ can't check: press R to resolve this alias"
        await pilot.press("r")
        await wait_for(pilot, lambda: "new-host" in checker.resolved)


async def save_in_form(
    app, pilot, key: str, values: dict[str, str], direct: bool = False
) -> None:
    """Open the form with `key`, fill it in and save; returns once it closed."""
    await pilot.press(key)
    await wait_for(pilot, lambda: showing(app, MachineForm))
    if direct:
        app.screen.query_one("#kind-direct", RadioButton).value = True
        await pilot.pause()
    for field, value in values.items():
        app.screen.query_one(f"#form-{field}", Input).value = value
    await pilot.press("ctrl+s")
    await wait_for(pilot, lambda: len(app.screen_stack) == 1)


def saved_file(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "machines.toml"
    text = format_machines(MACHINES)
    path.write_text(text, encoding="utf-8")
    return path, text


NEW_DIRECT = {"id": "new", "name": "New", "addresses": "192.0.2.60"}


async def test_a_save_while_ssh_g_runs_keeps_its_answers(tmp_path: Path) -> None:
    path, text = saved_file(tmp_path)
    hold = threading.Event()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await wait_for(
                pilot, lambda: sorted(checker.resolved) == ["garden-host", "hop-host"]
            )
            await save_in_form(app, pilot, "a", NEW_DIRECT, direct=True)
            await wait_for(pilot, lambda: len(app.query(StatusSymbol)) == 5)
            hold.set()
            await checked(app, pilot)
            assert symbols(app)[0] is State.ONLINE
            app.query_one(ListView).index = 0
            await wait_for(pilot, lambda: details_id(app) == "garden")
            assert status_text(app) == "● online via alias"
            assert symbols(app)[3] is State.UNKNOWN
            assert sorted(checker.resolved) == ["garden-host", "hop-host"]
            assert state_path(path, platform.node()).exists()
    finally:
        hold.set()


async def test_two_saves_while_ssh_g_runs_still_use_its_answer(
    tmp_path: Path,
) -> None:
    path, text = saved_file(tmp_path)
    hold = threading.Event()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await wait_for(
                pilot, lambda: sorted(checker.resolved) == ["garden-host", "hop-host"]
            )
            await save_in_form(app, pilot, "a", NEW_DIRECT, direct=True)
            await wait_for(pilot, lambda: details_id(app) == "new")
            await save_in_form(app, pilot, "e", {"name": "Newer"})
            await wait_for(pilot, lambda: len(app.query(StatusSymbol)) == 5)
            hold.set()
            await checked(app, pilot)
            assert symbols(app)[0] is State.ONLINE
            assert checker.resolved.count("garden-host") == 1
    finally:
        hold.set()


async def test_changing_an_alias_while_ssh_g_runs_waits_for_r(
    tmp_path: Path,
) -> None:
    path, text = saved_file(tmp_path)
    hold = threading.Event()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await wait_for(
                pilot, lambda: sorted(checker.resolved) == ["garden-host", "hop-host"]
            )
            await save_in_form(app, pilot, "e", {"alias": "other-host"})
            hold.set()
            # Every late answer has reported once R is offered again.
            await wait_for(pilot, lambda: app.check_action("refresh", ()) is True)
            await checked(app, pilot)
            app.query_one(ListView).index = 0
            await wait_for(pilot, lambda: details_id(app) == "garden")
            assert status_text(app) == "◇ can't check: press R to resolve this alias"
            assert "other-host" not in checker.resolved
    finally:
        hold.set()


async def test_an_alias_waiting_for_r_needs_no_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "machines.toml"
    text = format_machines(MACHINES)
    path.write_text(text, encoding="utf-8")
    app = SSHWorkbenchApp(
        MACHINES, config_path=path, file_text=text, checker=FakeChecker()
    )
    async with app.run_test() as pilot:
        await checked(app, pilot)
        monkeypatch.setattr(app_module, "Thread", NoThread)
        await pilot.press("a")
        await wait_for(pilot, lambda: showing(app, MachineForm))
        for field, value in (("id", "new"), ("name", "New"), ("alias", "new-host")):
            app.screen.query_one(f"#form-{field}", Input).value = value
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: len(app.query(StatusSymbol)) == 5)
        await wait_for(pilot, lambda: details_id(app) == "new")
        assert status_text(app) == "◇ can't check: press R to resolve this alias"


class OneSlowHost(FakeChecker):
    """Holds the port check of one host until released."""

    def __init__(self, host: str, release: threading.Event) -> None:
        super().__init__()
        self.host = host
        self.release = release

    def port_open(self, host: str, port: int) -> bool:
        if host == self.host:
            self.release.wait(30)
        return super().port_open(host, port)


async def test_a_timer_round_waits_for_a_check_still_running() -> None:
    release = threading.Event()
    app = SSHWorkbenchApp(MACHINES, checker=OneSlowHost("192.0.2.50", release))
    try:
        async with app.run_test() as pilot:
            await wait_for(pilot, lambda: symbols(app).count(State.CHECKING) == 1)
            assert symbols(app)[2] is State.CHECKING
            started = app._round
            app._timer_round()
            assert app._round == started
            release.set()
            # The slow check's own result arrives instead of being replaced.
            await wait_for(pilot, lambda: symbols(app)[2] is State.OFFLINE)
            app._timer_round()
            assert app._round == started + 1
    finally:
        release.set()


async def test_r_is_dimmed_until_every_ssh_g_has_answered() -> None:
    hold = threading.Event()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, checker=checker)
    try:
        async with app.run_test() as pilot:
            await wait_for(
                pilot, lambda: sorted(checker.resolved) == ["garden-host", "hop-host"]
            )
            started = app._round
            assert app.check_action("refresh", ()) is None
            await pilot.press("r")
            assert app._round == started
            hold.set()
            await checked(app, pilot)
            await wait_for(pilot, lambda: app.check_action("refresh", ()) is True)
            assert sorted(checker.resolved) == ["garden-host", "hop-host"]
            await pilot.press("r")
            await wait_for(pilot, lambda: checker.resolved.count("garden-host") == 2)
            assert app._round == started + 1
    finally:
        hold.set()


async def test_r_after_a_save_still_waits_for_the_earlier_ssh_g(
    tmp_path: Path,
) -> None:
    path = tmp_path / "machines.toml"
    text = format_machines(MACHINES)
    path.write_text(text, encoding="utf-8")
    hold = threading.Event()
    checker = FakeChecker(hold=hold)
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await wait_for(
                pilot, lambda: sorted(checker.resolved) == ["garden-host", "hop-host"]
            )
            # A save starts a round without ssh -G while the first ones still run.
            before = app._round
            await pilot.press("a")
            await wait_for(pilot, lambda: showing(app, MachineForm))
            for field, value in (("id", "new"), ("name", "New"), ("alias", "new-host")):
                app.screen.query_one(f"#form-{field}", Input).value = value
            await pilot.press("ctrl+s")
            await wait_for(pilot, lambda: app._round == before + 1)
            await wait_for(pilot, lambda: len(app.screen_stack) == 1)
            assert app.check_action("refresh", ()) is None
            await pilot.press("r")
            assert app._round == before + 1
            assert sorted(checker.resolved) == ["garden-host", "hop-host"]
            hold.set()
            await wait_for(pilot, lambda: app.check_action("refresh", ()) is True)
            await pilot.press("r")
            await wait_for(pilot, lambda: "new-host" in checker.resolved)
            assert app._round == before + 2
    finally:
        hold.set()


class NoThread:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def start(self) -> None:
        raise RuntimeError("can't start new thread")


async def test_checks_that_cannot_start_leave_the_timer_and_r_working(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "Thread", NoThread)
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: symbols(app) == [State.UNKNOWN] * 4)
        app.query_one(ListView).index = 2
        await wait_for(pilot, lambda: details_id(app) == "lab")
        assert status_text(app) == "◇ can't check: the check could not start"
        assert app.check_action("refresh", ()) is True
        started = app._round
        app._timer_round()
        assert app._round == started + 1


def refresh_key(app: SSHWorkbenchApp):
    keys = app.query_one(Footer).query("FooterKey")
    return next((key for key in keys if key.action == "refresh"), None)


def r_dimmed(app: SSHWorkbenchApp) -> bool | None:
    """Whether the footer shows R dimmed; None while the footer has no R."""
    key = refresh_key(app)
    return None if key is None else key.has_class("-disabled")


async def test_the_footer_dims_r_while_the_review_it_started_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = threading.Event()
    reviews: list[Path] = []
    read = app_module.host_names

    def slow_host_names(folder: Path, skip: Path | None = None) -> list[str]:
        reviews.append(folder)
        # The startup review runs at once; the one R starts waits.
        if len(reviews) > 1:
            assert release.wait(10)
        return read(folder, skip=skip)

    monkeypatch.setattr(app_module, "host_names", slow_host_names)
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    try:
        async with app.run_test() as pilot:
            await checked(app, pilot)
            await wait_for(pilot, lambda: r_dimmed(app) is False)
            await pilot.press("r")
            await wait_for(pilot, lambda: len(reviews) == 2)
            await wait_for(pilot, lambda: r_dimmed(app) is True)
            release.set()
            await checked(app, pilot)
            await wait_for(pilot, lambda: r_dimmed(app) is False)
    finally:
        release.set()
