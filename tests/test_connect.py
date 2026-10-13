import asyncio
from unittest.mock import Mock

import pytest
from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, ListView, Static

from ssh_workbench import app as app_module
from ssh_workbench import ssh
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Project
from ssh_workbench.ssh import SSHLaunchError

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

PROJECTS = (
    Project(
        "garden-demo",
        "Garden demo",
        "garden-demo-host",
        "https://example.com/garden.git",
        "https://example.com/garden/docs",
    ),
    Project("studio-demo", "Studio demo", "studio-demo-host"),
)


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


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
async def test_connect_is_visible_and_never_automatic(
    monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    launch = Mock(side_effect=AssertionError("Unexpected SSH launch"))
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(PROJECTS)
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
        await pilot.click("#project-repository")
        await pilot.click("#project-documentation")
        launch.assert_not_called()
        assert app.is_running


@pytest.mark.parametrize("projects", [None, (), PROJECTS])
async def test_no_selected_project_never_launches(
    monkeypatch: pytest.MonkeyPatch, suspend_events: list[str], projects
) -> None:
    launch = Mock(side_effect=AssertionError("Unexpected SSH launch"))
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(projects)
    async with app.run_test() as pilot:
        if projects:
            app.query_one(ListView).index = None
            await pilot.pause()
        status = str(app.query_one("#connection-status", Static).content)
        await pilot.press("c")
        app.action_connect()
        launch.assert_not_called()
        assert suspend_events == []
        assert str(app.query_one("#connection-status", Static).content) == status
        assert app.is_running
        await pilot.press("q")
        assert not app.is_running


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
@pytest.mark.parametrize("from_details", [False, True])
async def test_connect_uses_selected_alias_and_restores_focus(
    monkeypatch: pytest.MonkeyPatch,
    suspend_events: list[str],
    size: tuple[int, int],
    from_details: bool,
) -> None:
    app = SSHWorkbenchApp(PROJECTS)

    def launch(alias: str) -> int:
        assert alias == "studio-demo-host"
        assert suspend_events == ["suspend"]
        assert app._connecting
        assert not app._driver._auto_restart
        suspend_events.append("launch")
        return 0

    launcher = Mock(side_effect=launch)
    monkeypatch.setattr(app_module, "launch_ssh", launcher)
    async with app.run_test(size=size) as pilot:
        await pilot.press("down")
        project_list = app.query_one(ListView)
        if from_details:
            await pilot.press("tab")
            assert app.focused is app.query_one("#project-details", VerticalScroll)
        await pilot.press("c")
        assert suspend_events == ["suspend", "launch", "resume"]
        launcher.assert_called_once_with("studio-demo-host")
        assert not app._connecting
        assert app._driver._auto_restart
        assert app.focused is project_list
        assert project_list.index == 1
        assert str(app.query_one("#project-name", Static).content) == "Studio demo"
        status = app.query_one("#connection-status", Static)
        assert str(status.content) == "SSH exited with status 0."
        assert app.screen.region.contains_region(status.region)
        await pilot.press("up")
        assert project_list.index == 0
        assert str(app.query_one("#project-name", Static).content) == "Garden demo"
        await pilot.press("tab", "q")
        assert not app.is_running
        assert app.return_code == 0


@pytest.mark.parametrize(
    "outcome, message",
    [
        (0, "SSH exited with status 0."),
        (
            255,
            "SSH exited with status 255. "
            "Check the SSH client's message and alias; C retries.",
        ),
        (
            -2,
            "SSH exited with status -2. "
            "Check the SSH client's message and alias; C retries.",
        ),
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
    def launch(alias: str) -> int:
        suspend_events.append("launch")
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test() as pilot:
        await pilot.press("down", "tab", "c")
        assert suspend_events == ["suspend", "launch", "resume"]
        assert str(app.query_one("#connection-status", Static).content) == message
        project_list = app.query_one(ListView)
        assert app.focused is project_list
        assert project_list.index == 1
        assert not app._connecting
        assert app.check_action("connect", ()) is True
        await pilot.press("up", "tab", "shift+tab")
        assert project_list.index == 0
        assert app.focused is project_list
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
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert suspend_events == ["suspend", "resume"]
        run.assert_called_once()
        message = str(app.query_one("#connection-status", Static).content)
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
    app = SSHWorkbenchApp([Project("unsafe-demo", "Unsafe demo", "-oProxyCommand=x")])
    async with app.run_test() as pilot:
        await pilot.press("c")
        assert suspend_events == ["suspend", "resume"]
        assert "Invalid SSH alias" in str(
            app.query_one("#connection-status", Static).content
        )
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
    app = SSHWorkbenchApp(PROJECTS)

    def launch(alias: str) -> int:
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
                "SSH exited with status 5. "
                "Check the SSH client's message and alias; C retries.",
                "Could not start SSH.",
                "SSH interrupted. Press C to retry or Q to quit.",
                "SSH exited with status 0.",
            ],
            start=1,
        ):
            await pilot.press("c")
            assert launcher.call_count == count
            assert suspend_events == ["suspend", "launch", "resume"] * count
            assert str(app.query_one("#connection-status", Static).content) == message
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
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test() as pilot:
        assert not app._driver.can_suspend
        await pilot.press("down", "tab", "c")
        launch.assert_not_called()
        assert "Cannot hand off this terminal" in str(
            app.query_one("#connection-status", Static).content
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
    project = Project(
        "literal-demo",
        "[bold]Literal[/bold] " * 30,
        "literal-demo-host",
        "https://example.com/" + "[link=path]/" * 80,
        "https://example.com/" + "docs/" * 100,
    )
    monkeypatch.setattr(app_module, "launch_ssh", Mock(return_value=0))
    app = SSHWorkbenchApp([project, PROJECTS[1]])
    async with app.run_test(size=size) as pilot:
        await pilot.press("tab", "end")
        await pilot.wait_for_scheduled_animations()
        details = app.query_one("#project-details", VerticalScroll)
        scroll_y = details.scroll_y
        assert scroll_y > 0
        await pilot.press("c")
        assert suspend_events == ["suspend", "resume"]
        assert details.scroll_y == scroll_y
        rendered = app.query_one("#project-name", Static).render()
        assert rendered.plain == project.name
        assert not rendered.spans
        await pilot.press("down")
        assert details.scroll_y == 0
        assert str(app.query_one("#project-name", Static).content) == "Studio demo"
