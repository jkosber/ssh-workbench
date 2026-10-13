import asyncio
import signal
import threading
from unittest.mock import Mock

import pytest
from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, ListView, Static

from ssh_workbench import app as app_module
from ssh_workbench.app import LinkFinished, LinkRequest, SSHWorkbenchApp
from ssh_workbench.config import Project
from ssh_workbench.links import LinkResult

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

PROJECTS = (
    Project("first", "First", "first-host", "https://example.invalid/first"),
    Project(
        "second",
        "Second [bold]literal[/bold]",
        "second-host",
        "HTTP://Example.invalid:8080/a%20b?x=one&y=%26#fragment",
        "https://example.invalid/docs?chapter=two#part%202",
    ),
)


def status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#link-status", Static).content)


async def completed(app, pilot) -> None:
    async with asyncio.timeout(5):
        while app._link_request is not None:
            await pilot.pause()
    await pilot.pause()


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
async def test_visible_bindings_and_no_automatic_open(monkeypatch, size) -> None:
    opener = Mock(side_effect=AssertionError("Unexpected browser action"))
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test(size=size) as pilot:
        footer = app.query_one(Footer)
        async with asyncio.timeout(5):
            while not {"repository", "documentation"} <= {
                key.action for key in footer.query("FooterKey")
            }:
                await pilot.pause()
        for action, binding, label in (
            ("repository", "r", "Repository"),
            ("documentation", "d", "Documentation"),
        ):
            keys = [key for key in footer.query("FooterKey") if key.action == action]
            assert len(keys) == 1
            assert keys[0].key == binding
            assert label in keys[0].render().plain
            assert keys[0].visible
            assert app.screen.region.contains_region(keys[0].region)
        await pilot.press("down", "up", "enter", "tab", "enter", "pagedown", "home")
        await pilot.click("#project-repository")
        await pilot.resize_terminal(80, 24)
        await pilot.press("shift+tab", "q")
        opener.assert_not_called()
        assert not app.is_running


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
@pytest.mark.parametrize("from_details", [False, True])
@pytest.mark.parametrize("key, field", [("r", "repository"), ("d", "documentation")])
async def test_exact_selected_url_from_either_pane(
    monkeypatch, size, from_details, key, field
) -> None:
    ui_thread = threading.get_ident()
    called_threads = []

    def open_url(url):
        called_threads.append(threading.get_ident())
        return LinkResult.ACCEPTED

    opener = Mock(side_effect=open_url)
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test(size=size) as pilot:
        await pilot.press("down")
        if from_details:
            await pilot.press("tab", "end")
            await pilot.wait_for_scheduled_animations()
        focus = app.focused
        details = app.query_one("#project-details", VerticalScroll)
        scroll = details.scroll_y
        await pilot.press(key)
        await completed(app, pilot)
        opener.assert_called_once_with(getattr(PROJECTS[1], field))
        assert called_threads[0] != ui_thread
        assert app.query_one(ListView).index == 1
        assert app.focused is focus
        assert details.scroll_y == scroll
        assert (
            status(app)
            == f"{field.title()} browser request accepted. Project 2: second"
        )
        assert app.screen.region.contains_region(app.query_one("#link-status").region)
        await pilot.press("ctrl+q")
        assert not app.is_running


@pytest.mark.parametrize("projects", [None, (), PROJECTS])
async def test_no_selection_explains_both_actions(monkeypatch, projects) -> None:
    opener = Mock()
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(projects)
    async with app.run_test() as pilot:
        if projects:
            app.query_one(ListView).index = None
            await pilot.pause()
        for key, label in [("r", "Repository"), ("d", "Documentation")]:
            await pilot.press(key)
            assert status(app) == f"{label}: select a project first."
        opener.assert_not_called()
        await pilot.press("q")


async def test_absent_links_do_not_dispatch(monkeypatch) -> None:
    opener = Mock()
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp([Project("missing", "Missing", "missing-host")])
    async with app.run_test() as pilot:
        for key, label in [("r", "Repository"), ("d", "Documentation")]:
            await pilot.press("tab", key)
            assert status(app).startswith(f"{label} link not configured.")
            assert "restart" in status(app)
            assert app._link_request is None
        opener.assert_not_called()


@pytest.mark.parametrize(
    "outcome",
    [
        LinkResult.ACCEPTED,
        LinkResult.FAILED,
        LinkResult.UNAVAILABLE,
        OSError("private-path?secret=value\x1b[31m[bold]"),
        RuntimeError("private-path?secret=value\x1b[31m[bold]"),
    ],
)
async def test_results_are_literal_sanitized_and_retryable(
    monkeypatch, outcome
) -> None:
    opener = Mock(
        side_effect=outcome if isinstance(outcome, Exception) else None,
        return_value=outcome,
    )
    monkeypatch.setattr(app_module, "open_link", opener)
    project = Project(
        "literal[bold]\x1b", "Literal", "literal-host", PROJECTS[0].repository
    )
    app = SSHWorkbenchApp([project])
    async with app.run_test() as pilot:
        for count in (1, 2):
            await pilot.press("r")
            await completed(app, pilot)
            result = LinkResult.FAILED if isinstance(outcome, Exception) else outcome
            assert (
                status(app)
                == f"Repository {result.value} Project 1: literal[bold]\\x1b"
            )
            assert opener.call_count == count
            rendered = app.query_one("#link-status", Static).render()
            assert not rendered.spans
            assert all(
                word not in rendered.plain for word in ("secret", "private", "\x1b")
            )
        await pilot.press("down", "q")


@pytest.mark.parametrize(
    "url",
    ["file:///private", "https://u:p@example.invalid", "https://example.invalid/\x1b"],
)
async def test_real_boundary_rejects_invalid_ui_records(url) -> None:
    app = SSHWorkbenchApp([Project("invalid", "Invalid", "invalid-host", url, url)])
    async with app.run_test() as pilot:
        for key in ("r", "d"):
            await pilot.press(key)
            await completed(app, pilot)
            assert "link is invalid" in status(app)
            assert url not in status(app)


async def test_pending_request_is_bounded_and_preserves_new_selection_and_scroll(
    monkeypatch,
) -> None:
    release = threading.Event()
    entered = threading.Event()

    def open_url(url):
        entered.set()
        assert release.wait(10)
        return LinkResult.ACCEPTED

    opener = Mock(side_effect=open_url)
    monkeypatch.setattr(app_module, "open_link", opener)
    projects = list(PROJECTS) + [
        Project(
            f"demo-{i}",
            "Long name " * 50,
            "host",
            "https://example.invalid/" + "path/" * 100,
        )
        for i in range(30)
    ]
    app = SSHWorkbenchApp(projects)
    try:
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.press("down", "r")
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await pilot.pause()
            request = app._link_request
            assert request.project is PROJECTS[1]
            assert request.url == PROJECTS[1].repository
            await pilot.press(*(["down"] * 20), "tab", "pagedown")
            await pilot.wait_for_scheduled_animations()
            project_list = app.query_one(ListView)
            details = app.query_one("#project-details", VerticalScroll)
            index, list_scroll, detail_scroll = (
                project_list.index,
                project_list.scroll_y,
                details.scroll_y,
            )
            assert index == 21 and list_scroll > 0 and detail_scroll > 0
            await pilot.press("r", "d", "r")
            assert "still pending" in status(app)
            assert "Project 2: second" in status(app)
            assert app._link_request is request
            assert opener.call_count == 1
            release.set()
            await completed(app, pilot)
            assert "accepted. Project 2: second" in status(app)
            assert project_list.index == index
            assert project_list.scroll_y == list_scroll
            assert details.scroll_y == detail_scroll
            assert app.focused is details
            await pilot.press("r")
            await completed(app, pilot)
            assert opener.call_count == 2
            opener.assert_called_with(projects[index].repository)
            assert f"Project {index + 1}: {projects[index].id}" in status(app)
    finally:
        release.set()


@pytest.mark.parametrize("key", ["q", "ctrl+q"])
async def test_shutdown_ignores_delayed_completion(monkeypatch, key) -> None:
    release, entered, finished = threading.Event(), threading.Event(), threading.Event()

    def open_url(url):
        entered.set()
        assert release.wait(10)
        finished.set()
        return LinkResult.ACCEPTED

    monkeypatch.setattr(app_module, "open_link", open_url)
    app = SSHWorkbenchApp(PROJECTS)
    updates = Mock(wraps=app._show_link_result)
    monkeypatch.setattr(app, "_show_link_result", updates)
    try:
        async with app.run_test() as pilot:
            await pilot.press("r")
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await pilot.pause()
            request = app._link_request
            await pilot.press(key)
            assert not app.is_running
        assert app._links_closed.is_set()
        count = updates.call_count
        release.set()
        async with asyncio.timeout(5):
            while not finished.is_set():
                await asyncio.sleep(0)
        app.on_link_finished(LinkFinished(request, LinkResult.ACCEPTED))
        assert updates.call_count == count
        assert app._link_request is None
    finally:
        release.set()


async def test_stale_result_does_not_replace_new_request(monkeypatch) -> None:
    release = threading.Event()
    monkeypatch.setattr(
        app_module, "open_link", lambda url: release.wait(10) and LinkResult.ACCEPTED
    )
    app = SSHWorkbenchApp(PROJECTS)
    try:
        async with app.run_test() as pilot:
            await pilot.press("r")
            old_request = app._link_request
            release.set()
            await completed(app, pilot)
            release.clear()
            await pilot.press("down", "d")
            new_request = app._link_request
            before = status(app)
            app.post_message(LinkFinished(old_request, LinkResult.FAILED))
            await pilot.pause()
            assert app._link_request is new_request
            assert status(app) == before
            release.set()
            await completed(app, pilot)
    finally:
        release.set()


async def test_completion_during_ssh_keeps_both_results_and_signal_guard(
    monkeypatch,
) -> None:
    release, finished = threading.Event(), threading.Event()
    lifecycle = []
    previous = signal.getsignal(signal.SIGINT)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: lifecycle.append("suspend"),
    )
    monkeypatch.setattr(
        HeadlessDriver,
        "resume_application_mode",
        lambda self: lifecycle.append("resume"),
    )

    def open_url(url):
        assert release.wait(10)
        finished.set()
        return LinkResult.ACCEPTED

    def launch(alias):
        assert signal.getsignal(signal.SIGINT) is not previous
        lifecycle.append("launch")
        release.set()
        assert finished.wait(5)
        return 7

    monkeypatch.setattr(app_module, "open_link", open_url)
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(PROJECTS)
    try:
        async with app.run_test() as pilot:
            await pilot.press("r", "down", "tab", "c")
            await completed(app, pilot)
            assert lifecycle == ["suspend", "launch", "resume"]
            assert signal.getsignal(signal.SIGINT) is previous
            assert "accepted. Project 1: first" in status(app)
            assert "SSH exited with status 7." in str(
                app.query_one("#connection-status", Static).content
            )
            assert app.query_one(ListView).index == 1
            assert app.focused is app.query_one(ListView)
            await pilot.press("q")
    finally:
        release.set()


async def test_thread_start_error_clears_pending_request(monkeypatch) -> None:
    thread = Mock()
    thread.return_value.start.side_effect = RuntimeError("private-marker\x1b")
    monkeypatch.setattr(app_module, "Thread", thread)
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test() as pilot:
        await pilot.press("r")
        assert app._link_request is None
        assert "browser request failed" in status(app)
        assert "private-marker" not in status(app)
        await pilot.press("q")


async def test_closed_loop_race_discards_completion(monkeypatch) -> None:
    app = SSHWorkbenchApp(PROJECTS)
    request = LinkRequest(PROJECTS[0], "Repository", PROJECTS[0].repository, 1)
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    post = Mock(side_effect=RuntimeError("Event loop is closed"))
    monkeypatch.setattr(app, "post_message", post)
    app._launch_link(request)
    post.assert_called_once()
    opener.assert_called_once_with(request.url)
    app.on_unmount()
    app._launch_link(request)
    assert opener.call_count == 1


async def test_long_ids_keep_visible_attribution_and_bounded_layout(
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_module, "open_link", lambda url: LinkResult.UNAVAILABLE)
    projects = [
        Project(
            "shared-" + "x" * 400 + str(i), "Fictional", "host", PROJECTS[0].repository
        )
        for i in range(2)
    ]
    app = SSHWorkbenchApp(projects)
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.press("down", "r")
        await completed(app, pilot)
        status_widget = app.query_one("#link-status", Static)
        assert status_widget.region.height == 3
        assert "Project 2:" in status(app)
        visible = "\n".join(status_widget.render_line(y).text for y in range(3))
        assert "Project 2:" in visible
        assert app.query_one(ListView).region.height > 5
        assert app.screen.region.contains_region(app.query_one(Footer).region)
