import asyncio
import signal
import threading
from unittest.mock import Mock

import pytest
from textual import events
from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, ListView, OptionList, Static

from ssh_workbench import app as app_module
from ssh_workbench.app import LinkFinished, LinkPicker, LinkRequest, SSHWorkbenchApp
from ssh_workbench.config import Link, Machine, parse_machines
from ssh_workbench.links import LinkResult

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

MACHINES = (
    Machine(
        "first",
        "First",
        alias="first-host",
        links=(Link("Repository", "https://example.invalid/first"),),
    ),
    Machine(
        "second",
        "Second [bold]literal[/bold]",
        alias="second-host",
        links=(
            Link(
                "Repository", "HTTP://Example.invalid:8080/a%20b?x=one&y=%26#fragment"
            ),
            Link("Documentation", "https://example.invalid/docs?chapter=two#part%202"),
        ),
    ),
)
INITIAL_STATUS = "O: open a link of the selected machine. Opens in this environment."


def status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#link-status", Static).content)


async def completed(app, pilot) -> None:
    async with asyncio.timeout(5):
        while app._link_request is not None:
            await pilot.pause()
    await pilot.pause()


async def picker_open(app, pilot) -> LinkPicker:
    # push_screen makes a screen current before it has composed its widgets.
    async with asyncio.timeout(5):
        while not (isinstance(app.screen, LinkPicker) and app.screen.is_mounted):
            await pilot.pause()
    return app.screen


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
async def test_visible_bindings_and_no_automatic_open(monkeypatch, size) -> None:
    opener = Mock(side_effect=AssertionError("Unexpected browser action"))
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        footer = app.query_one(Footer)
        async with asyncio.timeout(5):
            while "open_link" not in {key.action for key in footer.query("FooterKey")}:
                await pilot.pause()
        keys = [key for key in footer.query("FooterKey") if key.action == "open_link"]
        assert len(keys) == 1
        assert keys[0].key == "o"
        assert "Link" in keys[0].render().plain
        assert keys[0].visible
        assert app.screen.region.contains_region(keys[0].region)
        actions = {key.action for key in footer.query("FooterKey")}
        assert not actions & {"repository", "documentation"}
        assert status(app) == INITIAL_STATUS
        await pilot.press("down", "up", "enter", "tab", "enter", "pagedown", "home")
        await pilot.press("r", "d")
        app.query_one("#machine-details", VerticalScroll).scroll_to_widget(
            app.query_one("#machine-links"), animate=False
        )
        await pilot.pause()
        await pilot.click("#machine-links")
        await pilot.resize_terminal(80, 24)
        await pilot.press("shift+tab", "q")
        opener.assert_not_called()
        assert not app.is_running


@pytest.mark.parametrize("size", [(60, 20), (80, 24), (120, 40)])
@pytest.mark.parametrize("from_details", [False, True])
@pytest.mark.parametrize(
    ("index", "picks", "link"),
    [(0, (), 0), (1, ("enter",), 0), (1, ("down", "enter"), 1)],
)
async def test_exact_selected_url_from_either_pane(
    monkeypatch, size, from_details, index, picks, link
) -> None:
    ui_thread = threading.get_ident()
    called_threads = []

    def open_url(url):
        called_threads.append(threading.get_ident())
        return LinkResult.ACCEPTED

    opener = Mock(side_effect=open_url)
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        await pilot.press(*(["down"] * index))
        if from_details:
            await pilot.press("tab", "end")
            await pilot.wait_for_scheduled_animations()
        focus = app.focused
        details = app.query_one("#machine-details", VerticalScroll)
        scroll = details.scroll_y
        await pilot.press("o")
        if picks:
            await picker_open(app, pilot)
            await pilot.press(*picks)
        await completed(app, pilot)
        chosen = MACHINES[index].links[link]
        opener.assert_called_once_with(chosen.url)
        assert called_threads[0] != ui_thread
        assert not isinstance(app.screen, LinkPicker)
        assert app.query_one(ListView).index == index
        assert app.focused is focus
        assert details.scroll_y == scroll
        assert status(app) == (
            f"{chosen.name} browser request accepted. "
            f"Machine {index + 1}: {MACHINES[index].id}"
        )
        assert app.screen.region.contains_region(app.query_one("#link-status").region)
        await pilot.press("ctrl+q")
        assert not app.is_running


@pytest.mark.parametrize(
    "machines", [None, (), MACHINES, (Machine("bare", "Bare", alias="bare-host"),)]
)
async def test_open_link_disabled_without_selection_or_links(
    monkeypatch, machines
) -> None:
    opener = Mock()
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(machines)
    async with app.run_test() as pilot:
        if machines == MACHINES:
            assert app.check_action("open_link", ()) is True
            app.query_one(ListView).index = None
            await pilot.pause()
        before = status(app)
        assert app.check_action("open_link", ()) is None
        await pilot.press("o")
        app.action_open_link()
        await pilot.pause()
        assert status(app) == before
        assert app._link_request is None
        assert not isinstance(app.screen, LinkPicker)
        opener.assert_not_called()
        await pilot.press("q")


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
    machine = Machine(
        "literal[bold]\x1b", "Literal", alias="literal-host", links=MACHINES[0].links
    )
    app = SSHWorkbenchApp([machine])
    async with app.run_test() as pilot:
        for count in (1, 2):
            await pilot.press("o")
            await completed(app, pilot)
            result = LinkResult.FAILED if isinstance(outcome, Exception) else outcome
            assert (
                status(app)
                == f"Repository {result.value} Machine 1: literal[bold]\\x1b"
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
    app = SSHWorkbenchApp(
        [Machine("invalid", "Invalid", alias="invalid-host", links=(Link("Bad", url),))]
    )
    async with app.run_test() as pilot:
        for _ in range(2):
            await pilot.press("o")
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
    machines = list(MACHINES) + [
        Machine(
            f"demo-{i}",
            "Long name " * 50,
            alias="host",
            links=(Link("Repository", "https://example.invalid/" + "path/" * 100),),
        )
        for i in range(30)
    ]
    app = SSHWorkbenchApp(machines)
    try:
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.press("down", "o")
            await picker_open(app, pilot)
            await pilot.press("enter")
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await pilot.pause()
            request = app._link_request
            assert request.machine is MACHINES[1]
            assert request.link is MACHINES[1].links[0]
            await pilot.press(*(["down"] * 20), "tab", "pagedown")
            await pilot.wait_for_scheduled_animations()
            machine_list = app.query_one(ListView)
            details = app.query_one("#machine-details", VerticalScroll)
            index, list_scroll, detail_scroll = (
                machine_list.index,
                machine_list.scroll_y,
                details.scroll_y,
            )
            assert index == 21 and list_scroll > 0 and detail_scroll > 0
            await pilot.press("o", "o", "o")
            assert not isinstance(app.screen, LinkPicker)
            assert "still pending" in status(app)
            assert "Machine 2: second" in status(app)
            assert app._link_request is request
            assert opener.call_count == 1
            release.set()
            await completed(app, pilot)
            assert "accepted. Machine 2: second" in status(app)
            assert machine_list.index == index
            assert machine_list.scroll_y == list_scroll
            assert details.scroll_y == detail_scroll
            assert app.focused is details
            await pilot.press("o")
            await completed(app, pilot)
            assert opener.call_count == 2
            opener.assert_called_with(machines[index].links[0].url)
            assert f"Machine {index + 1}: {machines[index].id}" in status(app)
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
    app = SSHWorkbenchApp(MACHINES)
    updates = Mock(wraps=app._show_link_result)
    monkeypatch.setattr(app, "_show_link_result", updates)
    try:
        async with app.run_test() as pilot:
            await pilot.press("o")
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


async def test_result_while_the_screens_close_is_ignored(monkeypatch) -> None:
    release, entered = threading.Event(), threading.Event()

    def open_url(url):
        entered.set()
        assert release.wait(10)
        return LinkResult.ACCEPTED

    monkeypatch.setattr(app_module, "open_link", open_url)
    app = SSHWorkbenchApp(MACHINES)
    updates = Mock(wraps=app._show_link_result)
    monkeypatch.setattr(app, "_show_link_result", updates)
    pending: dict[str, LinkRequest] = {}
    counts: list[int] = []

    def during_shutdown(message: events.Event) -> None:
        # Textual removes the screens after is_running turns False, while the
        # app still handles messages.
        if app.is_running or not isinstance(message, events.Unmount):
            return
        counts.append(updates.call_count)
        app.on_link_finished(LinkFinished(pending["request"], LinkResult.ACCEPTED))

    try:
        async with app.run_test(message_hook=during_shutdown) as pilot:
            await pilot.press("o")
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await pilot.pause()
            pending["request"] = app._link_request
        assert counts
        assert updates.call_count == counts[0]
    finally:
        release.set()


async def test_stale_result_does_not_replace_new_request(monkeypatch) -> None:
    release = threading.Event()
    monkeypatch.setattr(
        app_module, "open_link", lambda url: release.wait(10) and LinkResult.ACCEPTED
    )
    app = SSHWorkbenchApp(MACHINES)
    try:
        async with app.run_test() as pilot:
            await pilot.press("o")
            old_request = app._link_request
            release.set()
            await completed(app, pilot)
            release.clear()
            await pilot.press("down", "o")
            await picker_open(app, pilot)
            await pilot.press("down", "enter")
            new_request = app._link_request
            assert new_request.link is MACHINES[1].links[1]
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

    def launch(machine):
        assert signal.getsignal(signal.SIGINT) is not previous
        lifecycle.append("launch")
        release.set()
        assert finished.wait(5)
        return 7

    monkeypatch.setattr(app_module, "open_link", open_url)
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    app = SSHWorkbenchApp(MACHINES)
    try:
        async with app.run_test() as pilot:
            await pilot.press("o", "down", "tab", "c")
            await completed(app, pilot)
            assert lifecycle == ["suspend", "launch", "resume"]
            assert signal.getsignal(signal.SIGINT) is previous
            assert "accepted. Machine 1: first" in status(app)
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
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.press("o")
        assert app._link_request is None
        assert "browser request failed" in status(app)
        assert "private-marker" not in status(app)
        await pilot.press("q")


async def test_closed_loop_race_discards_completion(monkeypatch) -> None:
    app = SSHWorkbenchApp(MACHINES)
    request = LinkRequest(MACHINES[0], MACHINES[0].links[0], 1)
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    post = Mock(side_effect=RuntimeError("Event loop is closed"))
    monkeypatch.setattr(app, "post_message", post)
    app._launch_link(request)
    post.assert_called_once()
    opener.assert_called_once_with(request.link.url)
    app.on_unmount()
    app._launch_link(request)
    assert opener.call_count == 1


async def test_long_ids_keep_visible_attribution_and_bounded_layout(
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_module, "open_link", lambda url: LinkResult.UNAVAILABLE)
    machines = [
        Machine(
            "shared-" + "x" * 400 + str(i),
            "Fictional",
            alias="host",
            links=MACHINES[0].links,
        )
        for i in range(2)
    ]
    app = SSHWorkbenchApp(machines)
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.press("down", "o")
        await completed(app, pilot)
        status_widget = app.query_one("#link-status", Static)
        assert status_widget.region.height == 3
        assert "Machine 2:" in status(app)
        visible = "\n".join(status_widget.render_line(y).text for y in range(3))
        assert "Machine 2:" in visible
        assert app.query_one(ListView).region.height > 5
        assert app.screen.region.contains_region(app.query_one(Footer).region)


async def test_picker_escape_keeps_selection_and_focus(monkeypatch) -> None:
    opener = Mock(side_effect=AssertionError("Unexpected browser action"))
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("down", "tab", "end")
        await pilot.wait_for_scheduled_animations()
        details = app.query_one("#machine-details", VerticalScroll)
        scroll = details.scroll_y
        await pilot.press("o")
        picker = await picker_open(app, pilot)
        assert picker.query_one(OptionList).highlighted == 0
        await pilot.press("down", "escape")
        await pilot.pause()
        assert not isinstance(app.screen, LinkPicker)
        assert app.query_one(ListView).index == 1
        assert app.focused is details
        assert details.scroll_y == scroll
        assert status(app) == INITIAL_STATUS
        assert app._link_request is None
        opener.assert_not_called()
        await pilot.press("q")


async def test_picker_blocks_connect_and_second_request_but_quits(
    monkeypatch,
) -> None:
    launch = Mock(side_effect=AssertionError("Unexpected SSH launch"))
    opener = Mock(side_effect=AssertionError("Unexpected browser action"))
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    monkeypatch.setattr(app_module, "open_link", opener)
    # A real handoff must be possible, or an unguarded Connect would stop at
    # SuspendNotSupported before reaching launch_ssh and the test would pass.
    lifecycle = []
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
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.press("down", "o")
        await picker_open(app, pilot)
        connection = str(app.query_one("#connection-status", Static).content)
        assert app.check_action("connect", ()) is None
        assert app.check_action("open_link", ()) is None
        await pilot.press("c", "o")
        app.action_connect()
        app.action_open_link()
        await pilot.pause()
        assert len(app.screen_stack) == 2
        assert lifecycle == []
        assert str(app.query_one("#connection-status", Static).content) == connection
        launch.assert_not_called()
        opener.assert_not_called()
        await pilot.press("q")
        assert not app.is_running
        assert app.return_code == 0


@pytest.mark.parametrize(
    "keys",
    [
        ("enter", "enter"),
        ("enter", "escape"),
        ("escape", "enter"),
        ("escape", "escape"),
    ],
)
async def test_picker_ignores_a_second_key_in_the_same_batch(monkeypatch, keys) -> None:
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        await pilot.press("down", "o")
        await picker_open(app, pilot)
        # Windows delivers one console read as back-to-back key events.
        for key in keys:
            app.post_message(events.Key(key, "\r" if key == "enter" else None))
        await pilot.pause()
        await completed(app, pilot)
        assert app.is_running
        assert len(app.screen_stack) == 1
        if keys[0] == "enter":
            opener.assert_called_once_with(MACHINES[1].links[0].url)
        else:
            opener.assert_not_called()
        await pilot.press("q")
        assert not app.is_running
        assert app.return_code == 0


async def test_schema_1_single_link_opens_without_picker(monkeypatch) -> None:
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    machines = parse_machines(
        'schema_version = 1\n[[projects]]\nid = "old"\nname = "Old"\n'
        'ssh_alias = "old-host"\ndocumentation = "https://example.invalid/old"\n'
    )
    app = SSHWorkbenchApp(machines)
    async with app.run_test() as pilot:
        await pilot.press("o")
        assert len(app.screen_stack) == 1
        await completed(app, pilot)
        opener.assert_called_once_with("https://example.invalid/old")
        assert len(app.screen_stack) == 1
        assert status(app) == "Documentation browser request accepted. Machine 1: old"


async def test_picker_scrolls_many_long_links_at_60x20(monkeypatch) -> None:
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    links = tuple(
        Link(f"Link {i} " + "long name " * 8, f"https://example.invalid/{i}")
        for i in range(30)
    )
    app = SSHWorkbenchApp([Machine("many", "Many", alias="many-host", links=links)])
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.press("o")
        picker = await picker_open(app, pilot)
        options = picker.query_one(OptionList)
        assert app.screen.region.contains_region(options.region)
        await pilot.press("end")
        assert options.highlighted == 29
        assert options.scroll_y > 0
        await pilot.press("enter")
        await completed(app, pilot)
        opener.assert_called_once_with("https://example.invalid/29")
        assert status(app).startswith("Link 29 ")


async def test_picker_prompts_are_literal(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "open_link", Mock(return_value=LinkResult.ACCEPTED))
    links = (
        Link("[bold]Dash[/bold]\x1b", "https://example.invalid/[link=x]"),
        Link("Plain", "https://example.invalid/plain"),
    )
    app = SSHWorkbenchApp([Machine("lit", "Lit", alias="lit-host", links=links)])
    async with app.run_test() as pilot:
        await pilot.press("o")
        picker = await picker_open(app, pilot)
        options = picker.query_one(OptionList)
        prompt = options.get_option_at_index(0).prompt
        assert (
            prompt.plain == "[bold]Dash[/bold]\\x1b  https://example.invalid/[link=x]"
        )
        assert not prompt.spans
        await pilot.press("escape", "q")
