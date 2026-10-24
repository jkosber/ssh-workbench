"""Renamed aliases in the app: fake checker, temporary SSH folders and files."""

import asyncio
import dataclasses
import platform
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from textual import events
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, ListView, Static

from ssh_workbench import app as app_module
from ssh_workbench.aliases import (
    AliasMemory,
    AliasRecord,
    Review,
    format_state,
    load_state,
    state_path,
)
from ssh_workbench.app import AliasesReviewed, SSHWorkbenchApp, StatusSymbol
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.forms import MachineForm
from ssh_workbench.status import AliasTarget, State

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

GARDEN = Machine("garden", "Garden", alias="old-host")
LAB = Machine("lab", "Lab", addresses=("192.0.2.50",))
RECORD = AliasRecord("192.0.2.10", "dev", 22)
SAME = AliasTarget("192.0.2.10", 22, proxied=False, user="dev")
# At the last check old-host was a literal Host name pointing at RECORD.
PREVIOUS = AliasMemory(("old-host",), {"old-host": RECORD}, {})
OFFER = "× Alias not found. Looks like old-host became new-host. Press U to update."
NO_OFFER = (
    "× Alias not found. Fix your SSH config and press R, or press E and save to "
    "keep or change the alias."
)
WARNING = (
    "Saving rewrites the file without its comments or formatting; the old file "
    "is kept as machines.toml.bak. Press U again to update."
)


class FakeChecker:
    def __init__(
        self,
        targets: dict[str, AliasTarget | None],
        hold: threading.Event | None = None,
    ) -> None:
        self.targets = dict(targets)
        self.hold = hold
        self.resolved: list[str] = []
        self.checked: list[tuple[str, int]] = []

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        if self.hold is not None:
            self.hold.wait(30)
        return self.targets.get(alias)

    def port_open(self, host: str, port: int) -> bool:
        self.checked.append((host, port))
        return host == "192.0.2.10"


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machines: tuple[Machine, ...],
    hosts: list[str],
    state: AliasMemory | None = None,
    text: str | None = None,
) -> tuple[Path, str]:
    """A fictional SSH folder with `hosts`, a machine file and maybe a state file."""
    folder = tmp_path / "ssh"
    folder.mkdir(exist_ok=True)
    write_hosts(folder, hosts)
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines(machines) if text is None else text
    path.write_text(text, encoding="utf-8")
    if state is not None:
        state_path(path, platform.node()).write_text(
            format_state(state, platform.node()), encoding="utf-8"
        )
    return path, text


def write_hosts(folder: Path, hosts: list[str]) -> None:
    (folder / "config").write_text(
        "".join(f"Host {name}\n    HostName 192.0.2.10\n" for name in hosts),
        encoding="utf-8",
    )


def symbols(app: SSHWorkbenchApp) -> list[State]:
    return [widget.state for widget in app.query(StatusSymbol)]


def field(app: SSHWorkbenchApp, name: str) -> str:
    return str(app.query_one(f"#machine-{name}", Static).content)


def connection_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


def footer_actions(app: SSHWorkbenchApp) -> set[str]:
    return {key.action for key in app.query_one(Footer).query("FooterKey")}


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


async def checked(app, pilot) -> None:
    await wait_for(
        pilot,
        lambda: symbols(app) and State.CHECKING not in symbols(app),
    )


def tracked_threads(monkeypatch: pytest.MonkeyPatch) -> list[threading.Thread]:
    """Record every thread the app starts, so a test can wait for all of them."""
    started: list[threading.Thread] = []

    def thread(*args, **kwargs) -> threading.Thread:
        started.append(threading.Thread(*args, **kwargs))
        return started[-1]

    monkeypatch.setattr(app_module, "Thread", thread)
    return started


def allow_connect(monkeypatch: pytest.MonkeyPatch) -> Mock:
    launcher = Mock(return_value=0)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    return launcher


async def test_a_vanished_alias_offers_its_rename_and_u_applies_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert symbols(app) == [State.NOT_FOUND, State.OFFLINE]
        assert field(app, "status") == OFFER
        await wait_for(pilot, lambda: "update_alias" in footer_actions(app))
        assert "connect" not in footer_actions(app)
        assert checker.resolved == ["new-host"]
        assert checker.checked == [("192.0.2.50", 22)]

        await pilot.press("u")
        await wait_for(pilot, lambda: symbols(app)[:1] == [State.ONLINE])

        updated = dataclasses.replace(GARDEN, alias="new-host")
        assert read_machines(path)[0] == [updated, LAB]
        assert field(app, "status") == "● Online via alias"
        assert field(app, "target") == "new-host"
        assert connection_status(app) == (
            "Updated machine 1: garden now uses alias new-host."
        )
        assert checker.resolved == ["new-host"]
        assert app.check_action("connect", ()) is True
        assert app.check_action("update_alias", ()) is False


async def test_without_exactly_one_match_there_is_no_offer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    hosts = ["new-host", "twin-host"]
    path, text = workspace(tmp_path, monkeypatch, machines, hosts, PREVIOUS)
    checker = FakeChecker({"new-host": SAME, "twin-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert field(app, "status") == NO_OFFER
        assert app.check_action("update_alias", ()) is False
        await pilot.press("u")
        await pilot.pause()
        assert path.read_text(encoding="utf-8") == text


async def test_c_never_connects_a_missing_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = allow_connect(monkeypatch)
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    app = SSHWorkbenchApp(
        machines,
        config_path=path,
        file_text=text,
        checker=FakeChecker({"new-host": SAME}),
    )
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert app.check_action("connect", ()) is False
        await pilot.press("c")
        app.action_connect()
        await pilot.pause()
        launcher.assert_not_called()


async def test_the_state_file_records_names_and_targets_after_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (Machine("garden", "Garden", alias="garden-host"), LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["garden-host", "spare"])
    checker = FakeChecker({"garden-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        state = state_path(path, platform.node())
        await wait_for(pilot, state.exists)
        assert load_state(state, platform.node()) == AliasMemory(
            ("garden-host", "spare"), {"garden-host": RECORD}, {}
        )
        assert path.read_text(encoding="utf-8") == text
        assert sorted(item.name for item in tmp_path.iterdir()) == sorted(
            [state.name, "machines.toml", "ssh"]
        )


async def test_no_state_file_without_a_machine_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (Machine("garden", "Garden", alias="garden-host"),)
    workspace(tmp_path, monkeypatch, (), ["garden-host"])
    missing = tmp_path / "later" / "machines.toml"
    app = SSHWorkbenchApp(
        machines, config_path=missing, checker=FakeChecker({"garden-host": SAME})
    )
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await pilot.pause()
        assert symbols(app) == [State.ONLINE]
    assert not (tmp_path / "later").exists()


async def test_timer_rounds_keep_alias_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "STATUS_INTERVAL", 0.05)
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await wait_for(pilot, lambda: len(checker.checked) >= 3)
        assert symbols(app)[0] is State.NOT_FOUND
        assert field(app, "status") == OFFER
        assert checker.resolved == ["new-host"]
        assert set(checker.checked) == {("192.0.2.50", 22)}


async def test_an_alias_outside_the_ssh_config_is_marked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (
        Machine("pattern", "Pattern", alias="pattern-host"),
        Machine("listed", "Listed", alias="listed-host"),
    )
    path, text = workspace(tmp_path, monkeypatch, machines, ["listed-host"])
    checker = FakeChecker({"pattern-host": SAME, "listed-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert symbols(app) == [State.ONLINE, State.ONLINE]
        assert field(app, "target") == "pattern-host (not in your SSH config)"
        assert app.check_action("connect", ()) is True
        app.query_one(ListView).index = 1
        await pilot.pause()
        assert field(app, "target") == "listed-host"


async def test_update_asks_again_before_dropping_comments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    text = "# Fictional notes kept by hand\n" + format_machines(machines)
    path, text = workspace(
        tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS, text=text
    )
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        assert connection_status(app) == WARNING
        assert path.read_text(encoding="utf-8") == text
        await pilot.press("u")
        await wait_for(pilot, lambda: read_machines(path)[0][0].alias == "new-host")
        assert connection_status(app) == (
            "Updated machine 1: garden now uses alias new-host."
        )


async def test_moving_away_between_two_u_presses_asks_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    text = "# Fictional notes kept by hand\n" + format_machines(machines)
    path, text = workspace(
        tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS, text=text
    )
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await pilot.press("u")
        await pilot.pause()
        assert connection_status(app) == WARNING
        app.query_one(ListView).index = 1
        await wait_for(pilot, lambda: field(app, "id") == "lab")
        app.query_one(ListView).index = 0
        await wait_for(pilot, lambda: field(app, "id") == "garden")
        await pilot.press("u")
        await pilot.pause()
        assert connection_status(app) == WARNING
        assert path.read_text(encoding="utf-8") == text
        await pilot.press("u")
        await wait_for(pilot, lambda: read_machines(path)[0][0].alias == "new-host")


async def test_r_save_and_reload_never_resolve_a_missing_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["hop-host"], PREVIOUS)
    checker = FakeChecker({"old-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)

    def still_missing() -> None:
        assert symbols(app)[0] is State.NOT_FOUND
        assert "old-host" not in checker.resolved

    async def save_lab() -> None:
        app.query_one(ListView).index = 1
        await wait_for(pilot, lambda: field(app, "id") == "lab")
        await pilot.press("e")
        await wait_for(pilot, lambda: showing(app, MachineForm))
        started = app._round
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: app._round > started)

    async with app.run_test() as pilot:
        await checked(app, pilot)
        still_missing()

        started = app._round
        await pilot.press("r")
        await wait_for(
            pilot,
            lambda: app._round > started and app.check_action("refresh", ()) is True,
        )
        await checked(app, pilot)
        still_missing()

        await save_lab()
        await wait_for(pilot, lambda: not showing(app, MachineForm))
        await checked(app, pilot)
        still_missing()

        # The reload path: the form stays open with the reload message.
        path.write_text(format_machines(machines) + "\n# outside\n", encoding="utf-8")
        await save_lab()
        assert showing(app, MachineForm)
        await pilot.press("escape")
        await wait_for(pilot, lambda: not showing(app, MachineForm))
        await checked(app, pilot)
        still_missing()


async def test_an_alias_that_returns_clears_alias_not_found_on_r(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    checker = FakeChecker({"new-host": SAME, "old-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert symbols(app)[0] is State.NOT_FOUND
        write_hosts(tmp_path / "ssh", ["new-host", "old-host"])
        await pilot.press("r")
        await wait_for(pilot, lambda: symbols(app)[0] is State.ONLINE)
        assert field(app, "status") == "● Online via alias"
        assert app.check_action("connect", ()) is True
        await wait_for(
            pilot,
            lambda: (
                load_state(state_path(path, platform.node()), platform.node())
                == AliasMemory(("new-host", "old-host"), {"old-host": RECORD}, {})
            ),
        )


async def test_a_shared_vanished_alias_updates_only_the_selected_machine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shed = Machine("shed", "Shed", alias="old-host")
    machines = (GARDEN, shed)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        await pilot.press("u")
        await wait_for(pilot, lambda: symbols(app)[:1] == [State.ONLINE])
        assert read_machines(path)[0] == [
            dataclasses.replace(GARDEN, alias="new-host"),
            shed,
        ]
        assert symbols(app)[1] is State.NOT_FOUND
        app.query_one(ListView).index = 1
        await pilot.pause()
        assert field(app, "status") == OFFER
        assert app.check_action("update_alias", ()) is True


async def test_an_outside_change_before_u_reloads_and_asks_to_update_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    outside = format_machines((GARDEN, dataclasses.replace(LAB, name="Lab bench")))
    async with app.run_test() as pilot:
        await checked(app, pilot)
        path.write_text(outside, encoding="utf-8")
        await pilot.press("u")
        await pilot.pause()
        assert connection_status(app) == (
            "The machine file changed outside Workbench and was reloaded. "
            "Check the list, then update again."
        )
        assert path.read_text(encoding="utf-8") == outside


async def test_quit_never_waits_for_a_hung_rename_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    never = threading.Event()
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    checker = FakeChecker({"new-host": SAME}, hold=never)
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    try:
        async with asyncio.timeout(5):
            async with app.run_test() as pilot:
                await wait_for(pilot, lambda: checker.resolved == ["new-host"])
                assert symbols(app)[0] is State.CHECKING
                await pilot.press("q")
                assert not app.is_running
    finally:
        never.set()


async def test_a_failed_review_still_checks_every_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(folder: Path, skip: Path | None = None) -> list[str]:
        raise RuntimeError("fictional failure")

    monkeypatch.setattr(app_module, "host_names", broken)
    machines = (Machine("garden", "Garden", alias="garden-host"), LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["garden-host"])
    checker = FakeChecker({"garden-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert symbols(app) == [State.ONLINE, State.OFFLINE]
        assert field(app, "target") == "garden-host"


async def test_a_review_while_the_screens_close_starts_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    threads = tracked_threads(monkeypatch)
    checker = FakeChecker({"new-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    late = Review(
        AliasMemory(("old-host",), {"old-host": RECORD}, {}), {}, {"old-host": SAME}
    )
    errors: list[Exception] = []
    calls: list[tuple[int, int]] = []

    def during_shutdown(message: events.Event) -> None:
        # run_test removes the screens after is_running turns False while the
        # app still handles messages.
        if app.is_running or not isinstance(message, events.Unmount):
            return
        calls.append((len(checker.resolved), len(checker.checked)))
        try:
            app.on_aliases_reviewed(AliasesReviewed(app._round, ("old-host",), late))
        except Exception as error:
            errors.append(error)

    async with app.run_test(message_hook=during_shutdown) as pilot:
        await checked(app, pilot)
    # Any check the late review started has finished once its thread has.
    for thread in threads:
        thread.join(5)
    assert errors == []
    assert calls
    assert (len(checker.resolved), len(checker.checked)) == calls[0]


async def test_footer_with_update_fits_60_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    app = SSHWorkbenchApp(
        machines,
        config_path=path,
        file_text=text,
        checker=FakeChecker({"new-host": SAME}),
    )
    async with app.run_test(size=(60, 20)) as pilot:
        footer = app.query_one(Footer)
        await wait_for(pilot, lambda: "update_alias" in footer_actions(app))
        await wait_for(
            pilot, lambda: all(key.region.width for key in footer.query("FooterKey"))
        )
        for key in footer.query("FooterKey"):
            assert key.region.right <= 59, key.action


async def test_saving_the_machine_from_the_form_keeps_its_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["hop-host"], PREVIOUS)
    checker = FakeChecker({"old-host": SAME})
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await checked(app, pilot)
        assert field(app, "status") == NO_OFFER
        await pilot.press("e")
        await wait_for(pilot, lambda: showing(app, MachineForm))
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: symbols(app)[:1] == [State.UNKNOWN])
        assert field(app, "status") == "◇ Can't check: press R to resolve this alias"
        assert app.check_action("connect", ()) is True
        state = state_path(path, platform.node())
        await wait_for(
            pilot,
            lambda: (
                load_state(state, platform.node()) == AliasMemory(("hop-host",), {}, {})
            ),
        )
        await pilot.press("r")
        await wait_for(pilot, lambda: symbols(app)[0] is State.ONLINE)
        assert field(app, "target") == "old-host (not in your SSH config)"
        assert checker.resolved == ["hop-host", "old-host"]


async def test_a_timer_round_waits_for_the_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()
    read = app_module.host_names

    def slow_host_names(folder: Path, skip: Path | None = None) -> list[str]:
        assert release.wait(10)
        return read(folder, skip=skip)

    monkeypatch.setattr(app_module, "host_names", slow_host_names)
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, ["new-host"], PREVIOUS)
    app = SSHWorkbenchApp(
        machines,
        config_path=path,
        file_text=text,
        checker=FakeChecker({"new-host": SAME}),
    )
    try:
        async with app.run_test() as pilot:
            await wait_for(pilot, lambda: symbols(app)[1:] == [State.OFFLINE])
            started = app._round
            app._timer_round()
            assert app._round == started
            release.set()
            await wait_for(pilot, lambda: symbols(app)[0] is State.NOT_FOUND)
            app._timer_round()
            assert app._round == started + 1
    finally:
        release.set()
