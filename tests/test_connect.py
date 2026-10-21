import asyncio
from unittest.mock import Mock

import pytest
from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, ListView, Static

from ssh_workbench import app as app_module
from ssh_workbench import ssh
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Link, Machine
from ssh_workbench.ssh import SSHLaunchError

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

MACHINES = (
    Machine(
        "garden-demo",
        "Garden demo",
        alias="garden-demo-host",
        links=(
            Link("Repository", "https://example.com/garden.git"),
            Link("Documentation", "https://example.com/garden/docs"),
        ),
    ),
    Machine("studio-demo", "Studio demo", alias="studio-demo-host"),
)
DIRECT = Machine(
    "agent-box", "Agent box", user="dev", addresses=("100.64.0.12",), port=2222
)
RETRY = " Check the SSH client's message and alias; C retries."


@pytest.fixture
def suspend_events(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record driver handoff while retaining the installed App.suspend code.

    Textual 8.2.8 resumes after a bare yield rather than in a finally clause.
    Replacing that context manager would hide exceptional restoration defects.
    """
    events: list[str] = []
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: events.append("suspend"),
    )
    monkeypatch.setattr(
        HeadlessDriver, "resume_application_mode", lambda self: events.append("resume")
    )
    return events


def connection_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
async def test_connect_is_visible_and_never_automatic(
    monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    launch = Mock(side_effect=AssertionError("Unexpected SSH launch"))
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        footer = app.query_one(Footer)
        # Binding refresh can briefly remove keys during async recomposition.
        async with asyncio.timeout(5):
            while not (
                connect_keys := [
                    key for key in footer.query("FooterKey") if key.action == "connect"
                ]
            ):
                await pilot.pause()
        assert len(connect_keys) == 1
        connect_key = connect_keys[0]
        assert connect_key.key == "c"
        assert connect_key.visible
        assert "Connect" in connect_key.render().plain
        assert "C" in connect_key.render().plain.upper()
        assert app.screen.region.contains_region(connect_key.region)
        await pilot.press("down", "up", "enter", "tab", "enter")
        await pilot.click("#machine-links")
        await pilot.click("#machine-target")
        launch.assert_not_called()
        assert app.is_running


@pytest.mark.parametrize("machines", [None, (), MACHINES])
async def test_no_selected_machine_never_launches(
    monkeypatch: pytest.MonkeyPatch, suspend_events: list[str], machines
) -> None:
    launch = Mock(side_effect=AssertionError("Unexpected SSH launch"))
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(machines)
    async with app.run_test() as pilot:
        if machines:
            app.query_one(ListView).index = None
            await pilot.pause()
        status = connection_status(app)
        await pilot.press("c")
        app.action_connect()
        launch.assert_not_called()
        assert suspend_events == []
        assert connection_status(app) == status
        assert app.is_running
        await pilot.press("q")
        assert not app.is_running


@pytest.mark.parametrize("machines", [None, (), MACHINES])
async def test_connect_disabled_without_selection_is_dimmed(machines) -> None:
    app = SSHWorkbenchApp(machines)
    async with app.run_test() as pilot:
        if machines:
            assert app.check_action("connect", ()) is True
            app.query_one(ListView).index = None
            await pilot.pause()
        assert app.check_action("connect", ()) is None
        await pilot.press("q")


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
@pytest.mark.parametrize("from_details", [False, True])
async def test_connect_uses_selected_machine_and_restores_focus(
    monkeypatch: pytest.MonkeyPatch,
    suspend_events: list[str],
    size: tuple[int, int],
    from_details: bool,
) -> None:
    app = SSHWorkbenchApp(MACHINES)

    def launch(machine: Machine) -> int:
        assert machine is MACHINES[1]
        assert suspend_events == ["suspend"]
        assert app._connecting
        assert not app._driver._auto_restart
        suspend_events.append("launch")
        return 0

    launcher = Mock(side_effect=launch)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    async with app.run_test(size=size) as pilot:
        await pilot.press("down")
        machine_list = app.query_one(ListView)
        if from_details:
            await pilot.press("tab")
            assert app.focused is app.query_one("#machine-details", VerticalScroll)
        await pilot.press("c")
        assert suspend_events == ["suspend", "launch", "resume"]
        launcher.assert_called_once_with(MACHINES[1])
        assert not app._connecting
        assert app._driver._auto_restart
        assert app.focused is machine_list
        assert machine_list.index == 1
        assert str(app.query_one("#machine-name", Static).content) == "Studio demo"
        status = app.query_one("#connection-status", Static)
        assert str(status.content) == (
            "SSH exited with status 0. Machine 2: studio-demo"
        )
        assert app.screen.region.contains_region(status.region)
        await pilot.press("up")
        assert machine_list.index == 0
        assert str(app.query_one("#machine-name", Static).content) == "Garden demo"
        await pilot.press("tab", "q")
        assert not app.is_running
        assert app.return_code == 0


async def test_direct_machine_connect_passes_machine(
    monkeypatch: pytest.MonkeyPatch, suspend_events: list[str]
) -> None:
    launcher = Mock(return_value=9)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    app = SSHWorkbenchApp([DIRECT])
    async with app.run_test() as pilot:
        await pilot.press("c")
        launcher.assert_called_once_with(DIRECT)
        assert suspend_events == ["suspend", "resume"]
        assert connection_status(app) == (
            "SSH exited with status 9. Check the SSH client's message and the "
            "machine's settings; C retries. Machine 1: agent-box"
        )
        await pilot.press("q")


@pytest.mark.parametrize(
    "outcome, message",
    [
        (0, "SSH exited with status 0."),
        (255, "SSH exited with status 255." + RETRY),
        (-2, "SSH exited with status -2." + RETRY),
        (SSHLaunchError("SSH not found."), "SSH not found."),
        (SSHLaunchError("Could not start SSH."), "Could not start SSH."),
        (KeyboardInterrupt(), "SSH interrupted. Press C to retry or Q to quit."),
    ],
)
async def test_all_launch_outcomes_resume_real_suspend_context(
    monkeypatch: pytest.MonkeyPatch,
    suspend_events: list[str],
    outcome: int | BaseException,
    message: str,
) -> None:
    def launch(machine: Machine) -> int:
        suspend_events.append("launch")
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.press("down", "tab", "c")
        assert suspend_events == ["suspend", "launch", "resume"]
        assert connection_status(app) == message + " Machine 2: studio-demo"
        machine_list = app.query_one(ListView)
        assert app.focused is machine_list
        assert machine_list.index == 1
        assert not app._connecting
        assert app.check_action("connect", ()) is True
        await pilot.press("up", "tab", "shift+tab")
        assert machine_list.index == 0
        assert app.focused is machine_list
        await pilot.press("ctrl+q")
        assert not app.is_running
        assert app.return_code == 0


async def test_launch_boundary_errors_restore_browser(
    monkeypatch: pytest.MonkeyPatch, suspend_events: list[str], tmp_path
) -> None:
    # Keep the actual launch boundary so its OSError translation must reach the
    # app's exception handling without escaping Textual's suspend context.
    monkeypatch.setattr(ssh.shutil, "which", Mock(return_value=str(tmp_path / "ssh")))
    run = Mock(side_effect=PermissionError("synthetic-private-path"))
    monkeypatch.setattr(ssh.subprocess, "run", run)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert suspend_events == ["suspend", "resume"]
        run.assert_called_once()
        assert run.call_args.args[0][1:] == ["--", "garden-demo-host"]
        message = connection_status(app)
        assert "Could not start SSH" in message
        assert "synthetic-private-path" not in message
        assert app.focused is app.query_one(ListView)
        await pilot.press("down", "q")
        assert not app.is_running


async def test_launch_boundary_revalidates_selected_alias(
    monkeypatch: pytest.MonkeyPatch, suspend_events: list[str]
) -> None:
    which = Mock(side_effect=AssertionError("Unexpected executable lookup"))
    run = Mock(side_effect=AssertionError("Unexpected child process"))
    monkeypatch.setattr(ssh.shutil, "which", which)
    monkeypatch.setattr(ssh.subprocess, "run", run)
    app = SSHWorkbenchApp(
        [Machine("unsafe-demo", "Unsafe demo", alias="-oProxyCommand=x")]
    )
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert suspend_events == ["suspend", "resume"]
        assert "Invalid SSH alias" in connection_status(app)
        assert connection_status(app).endswith(" Machine 1: unsafe-demo")
        which.assert_not_called()
        run.assert_not_called()
        assert app.focused is app.query_one(ListView)
        await pilot.press("q")
        assert not app.is_running


async def test_repeated_launches_after_every_outcome_and_reentrant_guard(
    monkeypatch: pytest.MonkeyPatch, suspend_events: list[str]
) -> None:
    outcomes = iter(
        [0, 5, SSHLaunchError("Could not start SSH."), KeyboardInterrupt(), 0]
    )
    app = SSHWorkbenchApp(MACHINES)

    def launch(machine: Machine) -> int:
        assert app._connecting
        assert app.check_action("connect", ()) is None
        app.action_connect()
        suspend_events.append("launch")
        outcome = next(outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    launcher = Mock(side_effect=launch)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    async with app.run_test() as pilot:
        for count, message in enumerate(
            [
                "SSH exited with status 0.",
                "SSH exited with status 5." + RETRY,
                "Could not start SSH.",
                "SSH interrupted. Press C to retry or Q to quit.",
                "SSH exited with status 0.",
            ],
            start=1,
        ):
            await pilot.press("c")
            assert launcher.call_count == count
            assert suspend_events == ["suspend", "launch", "resume"] * count
            assert connection_status(app) == message + " Machine 1: garden-demo"
            assert not app._connecting
            assert app.check_action("connect", ()) is True
            assert app.query_one(ListView).index == 0
        await pilot.press("down", "q")
        assert not app.is_running


async def test_unsupported_terminal_does_not_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = Mock(side_effect=AssertionError("Unexpected SSH launch"))
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        assert not app._driver.can_suspend
        await pilot.press("down", "tab", "c")
        launch.assert_not_called()
        assert connection_status(app) == (
            "Cannot hand off this terminal. Run SSH Workbench in a local terminal. "
            "Machine 2: studio-demo"
        )
        assert app.query_one(ListView).index == 1
        assert app.focused is app.query_one(ListView)
        assert not app._connecting
        await pilot.press("up", "q")
        assert not app.is_running


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
async def test_return_preserves_scroll_and_literal_details(
    monkeypatch: pytest.MonkeyPatch,
    suspend_events: list[str],
    size: tuple[int, int],
) -> None:
    machine = Machine(
        "literal-demo",
        "[bold]Literal[/bold] " * 30,
        alias="literal-demo-host",
        links=(
            Link("Repository", "https://example.com/" + "[link=path]/" * 80),
            Link("Documentation", "https://example.com/" + "docs/" * 100),
        ),
    )
    monkeypatch.setattr(app_module, "launch_ssh", Mock(return_value=0))
    app = SSHWorkbenchApp([machine, MACHINES[1]])
    async with app.run_test(size=size) as pilot:
        await pilot.press("tab", "end")
        await pilot.wait_for_scheduled_animations()
        pane = app.query_one("#machine-details", VerticalScroll)
        scroll_y = pane.scroll_y
        assert scroll_y > 0
        await pilot.press("c")
        assert suspend_events == ["suspend", "resume"]
        assert pane.scroll_y == scroll_y
        rendered = app.query_one("#machine-name", Static).render()
        assert rendered.plain == machine.name
        assert not rendered.spans
        await pilot.press("down")
        assert pane.scroll_y == 0
        assert str(app.query_one("#machine-name", Static).content) == "Studio demo"
