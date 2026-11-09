"""The look: theme, header summary and the layout at each terminal size."""

import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest
from test_app import MACHINES as APP_MACHINES
from test_app import empty_lines, empty_text
from test_exports_ui import LAB, add_exported_box, workspace
from textual.color import Color
from textual.containers import VerticalScroll
from textual.content import Span
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, HelpPanel, Input, KeyPanel, ListView, Static
from textual.widgets._footer import FooterKey
from textual.widgets._key_panel import BindingsTable

from ssh_workbench import app as app_module
from ssh_workbench.app import (
    STATE_COLORS,
    Glyph,
    KeyFooter,
    ResultLine,
    ResultSlot,
    SSHWorkbenchApp,
    StatusSymbol,
    state_css,
)
from ssh_workbench.config import Link, Machine, format_machines, parse_machines
from ssh_workbench.exports import ExportError
from ssh_workbench.forms import ConfirmDelete, MachineForm
from ssh_workbench.links import LinkResult
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
LONG_SUMMARY = "4 machines · ◇ 1 can't check · ○ 1 offline · ● 2 online"
TRIMMED_SUMMARY = "4 machines · ◇ 1 can't check · ○ 1 offline"
SHORT_SUMMARY = "4 · ◇1 ○1 ●2"


class FakeChecker:
    """Garden and Studio online, Lab offline, Hop proxied."""

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return TARGETS.get(alias)

    def port_open(self, host: str, port: int) -> bool:
        return host in ("192.0.2.10", "192.0.2.40")


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def checked(app, pilot) -> None:
    await wait_for(
        pilot,
        lambda: State.CHECKING not in [w.state for w in app.query(StatusSymbol)],
    )


def summary(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#app-summary", Static).content)


def status_of(state: State) -> MachineStatus:
    return MachineStatus(state)


def panes(app: SSHWorkbenchApp) -> tuple[ListView, VerticalScroll]:
    return app.query_one(ListView), app.query_one("#machine-details", VerticalScroll)


def saved_app(tmp_path: Path, machines) -> SSHWorkbenchApp:
    path = tmp_path / "machines.toml"
    text = format_machines(machines)
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text)


def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


def rule(selector: str) -> str:
    """The single declaration of one generated rule, whitespace collapsed."""
    body = state_css().split(f"{selector} {{", 1)[1].split("}", 1)[0]
    return " ".join(body.split())


def luminance(color: Color) -> float:
    """WCAG 2 relative luminance."""

    def linear(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * linear(color.r) + 0.7152 * linear(color.g) + 0.0722 * linear(color.b)
    )


def contrast(foreground: Color, background: Color) -> float:
    """The WCAG 2 contrast ratio; a translucent foreground is first composited
    onto the background."""
    if foreground.a < 1:
        foreground = background.tint(foreground)
    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


async def test_the_workbench_theme_is_active() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)):
        assert app.theme == "workbench"
        theme = app.current_theme
        assert (theme.primary, theme.background, theme.dark) == (
            "#4FC1E9",
            "#10141B",
            True,
        )


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((120, 40), LONG_SUMMARY),
        ((80, 24), LONG_SUMMARY),
        ((60, 20), TRIMMED_SUMMARY),
        ((40, 16), SHORT_SUMMARY),
    ],
)
async def test_header_counts_machines_by_status(
    size: tuple[int, int], expected: str
) -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=size) as pilot:
        await checked(app, pilot)
        await wait_for(pilot, lambda: summary(app) == expected)
        title = app.query_one("#app-title", Static)
        assert str(title.content).strip() == "SSH Workbench"
        assert app.screen.region.contains_region(app.query_one("#app-summary").region)


async def test_header_follows_the_terminal_width() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(120, 40)) as pilot:
        await checked(app, pilot)
        await wait_for(pilot, lambda: summary(app) == LONG_SUMMARY)
        await pilot.resize_terminal(40, 16)
        await wait_for(pilot, lambda: summary(app) == SHORT_SUMMARY)
        await pilot.resize_terminal(120, 40)
        await wait_for(pilot, lambda: summary(app) == LONG_SUMMARY)


@pytest.mark.parametrize(
    ("machines", "expected"),
    [
        (MACHINES[:2], "2 machines · not checked"),
        (MACHINES[:1], "1 machine · not checked"),
        ([], ""),
        (None, ""),
    ],
)
async def test_header_without_status_checks_counts_machines(
    machines, expected: str
) -> None:
    app = SSHWorkbenchApp(machines)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert summary(app) == expected


async def test_header_follows_a_delete(tmp_path: Path) -> None:
    app = saved_app(tmp_path, MACHINES[:2])
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert summary(app) == "2 machines · not checked"
        for remaining in ("1 machine · not checked", ""):
            await pilot.press("x")
            await wait_for(pilot, lambda: showing(app, ConfirmDelete))
            await pilot.press("y")
            await wait_for(pilot, lambda: summary(app) == remaining)


async def test_summary_orders_states_by_urgency() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(200, 24)):
        app._statuses = {
            "garden": status_of(State.ONLINE),
            "studio": status_of(State.CHECKING),
            "lab": status_of(State.NOT_FOUND),
            "hop": status_of(State.OFFLINE),
        }
        content = app._summary(200)
        assert str(content) == (
            "4 machines · × 1 alias not found · ○ 1 offline · ▖ 1 checking · ● 1 online"
        )
        styles = [span.style for span in content.spans]
        assert styles[:2] == ["$error", "$text-error"]
        assert styles == [
            "$error",
            "$text-error",
            "$text-muted",
            "$text-muted",
            "$secondary",
            "$text-muted",
            "$success",
            "$text-muted",
        ]
        app._statuses["lab"] = status_of(State.ONLINE)
        app._statuses["hop"] = status_of(State.ONLINE)
        assert str(app._summary(200)) == "4 machines · ▖ 1 checking · ● 3 online"
        assert [span.style for span in app._summary(200).spans][:2] == [
            "$secondary",
            "$text-secondary",
        ]


async def test_header_names_only_what_needs_attention() -> None:
    app = SSHWorkbenchApp(MACHINES[:1], checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        await checked(app, pilot)
        await wait_for(pilot, lambda: summary(app) == "1 machine · all online")
        content = app.query_one("#app-summary", Static).content
        assert [span.style for span in content.spans] == ["$text-muted"]


async def test_summary_drops_entries_from_the_end() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(120, 40)) as pilot:
        await checked(app, pilot)
        room = len(app.title) + 4
        assert str(app._summary(len(LONG_SUMMARY) + room)) == LONG_SUMMARY
        assert str(app._summary(len(LONG_SUMMARY) + room - 1)) == TRIMMED_SUMMARY
        first = "4 machines · ◇ 1 can't check"
        assert str(app._summary(len(first) + room)) == first
        assert str(app._summary(len(first) + room - 1)) == SHORT_SUMMARY
        assert [span.style for span in app._summary(len(first) + room - 1).spans] == [
            "$warning",
            "$text-muted",
            "$success",
        ]


async def test_summary_phrases_fall_back_to_the_count() -> None:
    for app, phrase in (
        (
            SSHWorkbenchApp(MACHINES[:1], checker=FakeChecker()),
            "1 machine · all online",
        ),
        (SSHWorkbenchApp(MACHINES[:1]), "1 machine · not checked"),
    ):
        async with app.run_test(size=(80, 24)) as pilot:
            await wait_for(pilot, lambda: summary(app) == phrase)
            room = len(app.title) + 4
            assert str(app._summary(len(phrase) + room)) == phrase
            count = app._summary(len(phrase) + room - 1)
            assert (str(count), count.spans) == ("1 machine", [])
            assert str(app._summary(len("1 machine") + room)) == "1 machine"
            number = app._summary(len("1 machine") + room - 1)
            assert (str(number), number.spans) == ("1", [])


async def test_panes_have_label_rows_and_no_borders() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        assert str(app.query_one("#list-title", Static).content) == "machines"
        assert str(app.query_one("#list-position", Static).content) == "1/4"
        assert str(app.query_one("#details-name", Static).content) == "Garden"
        assert str(app.query_one("#details-id", Static).content) == "garden"
        # An unset border and `border: none` both read back as edge type "" in
        # 8.2.8; only the type is meaningful.
        for selector in ("#machine-list", "#machine-details", "#list-pane"):
            assert all(kind == "" for kind, _ in app.query_one(selector).styles.border)
        assert app.query_one("#details-pane").styles.border_left[0] == "solid"
        list_pane = app.query_one("#list-pane")
        details_pane = app.query_one("#details-pane")
        assert list_pane.has_class("-focused")
        assert not details_pane.has_class("-focused")
        assert app.query_one("#list-label").styles.border_bottom[0] == "heavy"
        assert app.query_one("#details-label").styles.border_bottom[0] == "solid"
        assert app.query_one("#list-label").region.height == 2
        # A container renders nothing itself (N3); the padding indents by one.
        assert app.query_one("#list-title").region.x == 1
        await pilot.press("tab")
        assert details_pane.has_class("-focused")
        assert not list_pane.has_class("-focused")
        assert app.query_one("#details-label").styles.border_bottom[0] == "heavy"
        # The details label keeps the name.
        assert str(app.query_one("#details-name", Static).content) == "Garden"
        await pilot.press("shift+tab", "down")
        assert str(app.query_one("#list-position", Static).content) == "2/4"


async def test_a_long_name_keeps_the_id_in_the_details_label() -> None:
    name = "A sixty-column machine name that fills the label to its edge"
    app = SSHWorkbenchApp([Machine("long-name", name, addresses=("192.0.2.60",))])
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        label = app.query_one("#details-label")
        name_region = app.query_one("#details-name").region
        id_region = app.query_one("#details-id").region
        assert len(name) == 60
        assert label.region.contains_region(id_region)
        assert id_region.right == label.content_region.right
        assert id_region.width == len("long-name")
        assert not name_region.overlaps(id_region)


@pytest.mark.parametrize(
    ("width", "list_width"),
    [
        (60, 24),
        (80, 32),
        (100, 40),
        (120, 48),
        (129, 51),
        (130, 52),
        (160, 64),
        (200, 80),
        (300, 80),
    ],
)
async def test_list_width_is_two_fifths_clamped(width: int, list_width: int) -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(width, 30)):
        list_pane = app.query_one("#list-pane")
        details_pane = app.query_one("#details-pane")
        assert list_pane.region.width == list_width
        assert list_pane.region.width <= width // 2
        assert details_pane.region.right == width
        assert details_pane.region.x == list_pane.region.right


async def test_scrollbars_are_one_column() -> None:
    # Size (80, 16) with tests/test_app.py's MACHINES: the details overflow, so
    # the scrollbar is drawn.
    app = SSHWorkbenchApp(APP_MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 16)) as pilot:
        await pilot.pause()
        details = app.query_one("#machine-details", VerticalScroll)
        assert details.max_scroll_y > 0
        assert details.styles.scrollbar_size_vertical == 1
        assert details.styles.scrollbar_gutter == "stable"
        # Padding 1 + 1 and the gutter (I3).
        assert details.scrollable_content_region.width == details.region.width - 3
        machine_list = app.query_one("#machine-list", ListView)
        assert machine_list.styles.scrollbar_size_vertical == 1


THIRTY = tuple(
    Machine(f"m{i:02}", f"Machine {i:02}", addresses=(f"192.0.2.{i}",))
    for i in range(1, 31)
)


@pytest.mark.parametrize(
    ("size", "min_rows"), [((50, 24), 3), ((40, 16), 2), ((50, 17), 2)]
)
async def test_narrow_terminals_stack_the_panes(
    size: tuple[int, int], min_rows: int
) -> None:
    app = SSHWorkbenchApp(THIRTY, checker=FakeChecker())
    async with app.run_test(size=size) as pilot:
        await checked(app, pilot)
        # Textual 8.2.8 keeps #browser's side-by-side arrangement cached when
        # only its own layout changes; the next layout pass stacks the panes.
        await pilot.pause()
        list_pane = app.query_one("#list-pane")
        details_pane = app.query_one("#details-pane")
        assert app.query_one("#browser").styles.layout.name == "vertical"
        assert list_pane.region.bottom == details_pane.region.y
        assert list_pane.region.height <= int(0.4 * size[1])
        machine_list = app.query_one("#machine-list", ListView)
        assert machine_list.region.height >= min_rows
        assert details_pane.styles.border_left[0] == ""
        for _ in range(20):
            await pilot.press("down")
        await pilot.pause()
        highlighted = machine_list.children[machine_list.index]
        # C4: the capped list scrolls to keep the selection on screen.
        assert list_pane.region.contains_region(highlighted.region)


def rebuilt(app: SSHWorkbenchApp, old_list: ListView) -> bool:
    """The rebuild replaced the list and gave the new one focus."""
    lists = app.query("#machine-list")
    return (
        len(lists) == 1
        and lists.first() is not old_list
        and app.focused is lists.first()
    )


async def rename_first(app: SSHWorkbenchApp, pilot, name: str) -> None:
    """Edit the selected machine's name through the form, save, and wait for
    the rebuilt list."""
    old_list = app.query_one("#machine-list", ListView)
    await pilot.press("e")
    await wait_for(pilot, lambda: showing(app, MachineForm))
    app.screen.query_one("#form-name", Input).value = name
    await pilot.press("ctrl+s")
    await wait_for(pilot, lambda: rebuilt(app, old_list))
    await pilot.pause()


async def test_label_rows_survive_a_rebuild(tmp_path: Path) -> None:
    app = saved_app(tmp_path, MACHINES)
    async with app.run_test(size=(80, 24)) as pilot:
        await rename_first(app, pilot, "Garden two")
        assert str(app.query_one("#details-name", Static).content) == "Garden two"
        assert str(app.query_one("#list-position", Static).content) == "1/4"
        assert app.query_one("#list-label").has_class("pane-label")


async def test_a_rebuild_keeps_the_stacked_list_capped(tmp_path: Path) -> None:
    # The rebuild mounts a new list; the cap must follow it, or the stacked
    # list grows to all thirty rows and the details lose their space.
    app = saved_app(tmp_path, THIRTY)
    async with app.run_test(size=(50, 24)) as pilot:
        await rename_first(app, pilot, "Machine one")
        list_pane = app.query_one("#list-pane")
        details_pane = app.query_one("#details-pane")
        assert list_pane.region.height <= int(0.4 * 24)
        assert list_pane.region.bottom == details_pane.region.y
        assert app.query_one("#machine-list", ListView).region.height >= 3


async def test_resizing_while_a_form_is_open_updates_the_layout(
    tmp_path: Path,
) -> None:
    app = saved_app(tmp_path, MACHINES[:2])
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("e")
        await wait_for(pilot, lambda: showing(app, MachineForm))
        await pilot.resize_terminal(50, 24)
        await pilot.pause()
        await pilot.press("escape")
        await wait_for(pilot, lambda: len(app.screen_stack) == 1)
        await pilot.pause()
        machine_list, pane = panes(app)
        assert machine_list.region.bottom <= pane.region.y
        assert not any(target.region.width for target in app.query(".row-target"))


async def test_wide_rows_show_where_each_machine_connects() -> None:
    long_alias = Machine("long", "Long", alias="a" * 200)
    app = SSHWorkbenchApp((*MACHINES, long_alias))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        targets = list(app.query(".row-target"))
        assert [target.render().plain for target in targets] == [
            "garden-host",
            "10.0.0.1",
            "192.0.2.50",
            "hop-host",
            "a" * 200,
        ]
        assert all(target.region.width > 0 for target in targets)
        names = list(app.query_one(ListView).query(Static))
        assert all(name.region.width >= 6 for name in names)
        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        assert not any(target.region.width for target in app.query(".row-target"))
        assert [
            str(name.content) for name in app.query_one(ListView).query(Static)
        ] == [
            "Garden",
            "Studio",
            "Lab",
            "Hop",
            "Long",
        ]


async def test_details_fit_at_80x24_without_scrolling() -> None:
    machine = Machine(
        "lab-box",
        "Lab box",
        user="admin",
        addresses=("192.0.2.20", "198.51.100.20"),
        port=2222,
        key="~/.ssh/id_ed25519_lab",
        links=(
            Link("Dashboard", "https://192.0.2.20:8006"),
            Link("Docs", "https://docs.example.com"),
        ),
    )
    app = SSHWorkbenchApp([machine])
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        _, pane = panes(app)
        assert pane.max_scroll_y == 0
        assert pane.region.contains_region(app.query_one("#machine-links").region)


async def test_the_status_value_is_colored_by_its_state() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        await checked(app, pilot)
        status = app.query_one("#machine-status", Static)
        await wait_for(pilot, lambda: status.has_class("state-online"))
        app.query_one(ListView).index = 2
        await wait_for(pilot, lambda: status.has_class("state-offline"))
        assert not status.has_class("state-online")


async def test_every_state_has_one_color_role() -> None:
    assert set(STATE_COLORS) == set(State)
    assert STATE_COLORS[State.OFFLINE] == ("$text-muted", "$text-muted")
    assert STATE_COLORS[State.CHECKING] == ("$secondary", "$text-secondary")
    assert len({symbol for symbol, _ in STATE_COLORS.values()} - {"$text-muted"}) == 4
    assert SSHWorkbenchApp.CSS.startswith(state_css())
    assert rule("StatusSymbol.state-not_found") == "color: $error;"
    assert rule("#machine-status.state-online") == "color: $text-success;"
    assert rule("#machine-status.state-offline") == "color: $text-muted;"


async def test_the_details_status_takes_the_table_color() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        await checked(app, pilot)
        variables = app.get_css_variables()
        status = app.query_one("#machine-status", Static)
        await wait_for(pilot, lambda: status.has_class("state-online"))
        assert status.styles.color == Color.parse(variables["text-success"])
        symbol = app.query(StatusSymbol).first()
        assert symbol.styles.color == Color.parse(variables["success"])
        app.query_one(ListView).index = 2
        await wait_for(pilot, lambda: status.has_class("state-offline"))
        assert status.styles.color == Color.parse(variables["text-muted"])


async def test_contrast_helper_matches_wcag() -> None:
    assert contrast(Color(255, 255, 255), Color(0, 0, 0)) == pytest.approx(21.0)
    background = Color.parse("#10141B")
    translucent = contrast(Color(255, 255, 255, 0.6), background)
    assert translucent == contrast(Color.parse("#9FA1A3"), background)
    assert translucent == pytest.approx(7.12, abs=0.01)


async def test_text_colors_reach_four_and_a_half_to_one() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)):
        variables = app.get_css_variables()
        foregrounds = (
            {"foreground", "text-muted"}
            | {word.lstrip("$") for _, word in STATE_COLORS.values()}
            | {symbol.lstrip("$") for symbol, _ in STATE_COLORS.values()}
        )
        for name in foregrounds:
            for surface in ("background", "surface", "panel"):
                ratio = contrast(
                    Color.parse(variables[name]), Color.parse(variables[surface])
                )
                assert ratio >= 4.5, (name, surface, ratio)


async def test_divider_reaches_three_to_one() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)):
        variables = app.get_css_variables()
        for surface in ("background", "surface"):
            ratio = contrast(
                Color.parse(variables["divider"]), Color.parse(variables[surface])
            )
            assert ratio >= 3, (surface, ratio)


@pytest.mark.parametrize("size", [(80, 16), (80, 23), (80, 24), (50, 24), (60, 24)])
async def test_no_help_line_and_the_details_keep_five_rows(
    size: tuple[int, int],
) -> None:
    # The ? key panel replaces the help line at every size.
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        assert not app.query("#navigation-help")
        _, pane = panes(app)
        assert pane.region.height >= 5


@pytest.mark.parametrize(
    ("size", "classes"),
    [
        ((59, 24), {"-narrow", "-tall"}),
        ((60, 23), {"-normal", "-short"}),
        ((99, 24), {"-normal", "-tall"}),
        ((100, 24), {"-wide", "-tall"}),
        ((129, 30), {"-wide", "-tall"}),
        ((130, 30), {"-xwide", "-tall"}),
    ],
)
async def test_breakpoint_classes(size, classes) -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=size):
        assert classes <= set(app.screen.classes)


async def test_footer_columns_for_width() -> None:
    assert KeyFooter.columns_for(80, 9) == 9
    assert KeyFooter.columns_for(79, 9) == 5
    assert KeyFooter.columns_for(45, 9) == 5
    assert KeyFooter.columns_for(44, 9) == 3
    assert KeyFooter.columns_for(40, 9) == 3


KEYS = [
    "c connect",
    "o link",
    "a add",
    "e edit",
    "x delete",
    "k key",
    "r check",
    "? keys",
    "q quit",
]


@pytest.mark.parametrize(
    ("size", "rows"),
    [
        ((40, 16), 3),
        ((44, 24), 3),
        ((45, 24), 2),
        ((60, 20), 2),
        ((79, 24), 2),
        ((80, 24), 1),
        ((120, 30), 1),
    ],
)
async def test_footer_rows_follow_width(size, rows) -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=size) as pilot:
        # a bindings change recomposes the footer; the columns must survive it
        await pilot.press("tab")
        await wait_for(pilot, lambda: all(k.region.width for k in app.query(FooterKey)))
        footer = app.query_one(Footer)
        keys = list(app.query(FooterKey))
        assert footer.region.height == rows
        assert [k.render().plain for k in keys] == KEYS
        assert max(k.region.right for k in keys) <= size[0]
        assert all(k.region.width == len(k.render().plain) for k in keys)
        # columns are content-sized: the gap between a column's widest key and
        # the next column is 2 (N2)
        xs = sorted({k.region.x for k in keys})
        right = {x: max(k.region.right for k in keys if k.region.x == x) for x in xs}
        assert all(n - right[x] == 2 for x, n in zip(xs, xs[1:]))


async def test_footer_labels_are_muted_and_keys_accented() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 24)):
        variables = app.get_css_variables()
        assert variables["footer-description-foreground"] == variables["text-muted"]
        assert variables["footer-key-foreground"] == variables["primary"]


def panel_text(app) -> str:
    """The key panel's text inside its viewport: what shows without scrolling."""
    view = app.screen.query_one(KeyPanel).scrollable_content_region
    table = app.screen.query_one(BindingsTable)
    rows = range(
        max(view.y - table.region.y, 0),
        min(view.bottom - table.region.y, table.region.height),
    )
    return "\n".join(table.render_line(y).text for y in rows)


async def open_key_panel(app, pilot) -> list[list[str]]:
    """Press ? and return the words of each row the panel shows."""
    await pilot.press("question_mark")
    await wait_for(
        pilot,
        lambda: (
            bool(app.screen.query(BindingsTable))
            and app.screen.query_one(BindingsTable).region.height > 0
        ),
    )
    return [line.split() for line in panel_text(app).splitlines()]


NAVIGATION_KEYS = ("↑", "↓", "tab", "pgup", "pgdn")
STOCK_KEYS = ("home", "end", "⏎", "enter", "^c", "ctrl+c", "←", "→")
APP_KEYS = (
    ("c", "connect"),
    ("o", "link"),
    ("a", "add"),
    ("e", "edit"),
    ("x", "delete"),
    ("k", "key"),
    ("r", "check"),
    ("?", "keys"),
    ("q", "quit"),
)


@pytest.mark.parametrize("size", [(40, 16), (60, 20), (80, 24), (120, 18)])
async def test_the_key_panel_shows_the_navigation_keys_at_every_size(
    size: tuple[int, int],
) -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=size) as pilot:
        rows = await open_key_panel(app, pilot)
        for key in NAVIGATION_KEYS:
            assert any(row[:1] == [key] for row in rows), key
        text = panel_text(app)
        for key in STOCK_KEYS:
            assert key not in text, key


async def test_question_mark_toggles_the_key_panel() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        rows = await open_key_panel(app, pilot)
        for key, label in APP_KEYS:
            assert any(key in row[:-1] and row[-1:] == [label] for row in rows), key
        footer = app.query_one(Footer)
        assert footer.region.width == 80 and footer.region.height == 1
        assert [k.render().plain for k in app.query(FooterKey)] == KEYS
        assert app.query_one("#app-header").region.width == 80
        assert "-normal" in app.screen.classes
        panel = app.query_one(HelpPanel)
        assert app.query_one("#panes").region.contains_region(panel.region)
        await pilot.press("question_mark")
        await wait_for(pilot, lambda: not app.query(HelpPanel))


async def test_question_mark_is_inert_in_modals(tmp_path) -> None:
    # ConfirmDelete, not MachineForm: a form's focused Input would swallow "?"
    # and the test would pass without the gate (N7).
    # App.query searches the default screen, so a missing gate shows up as a
    # mounted HelpPanel.
    app = saved_app(tmp_path, MACHINES)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("question_mark")
        await pilot.pause()
        assert not app.query(HelpPanel)


LINKED = (
    Machine(
        "garden",
        "Garden",
        alias="garden-host",
        links=(Link("Repository", "https://example.invalid/garden"),),
    ),
    Machine("studio", "Studio", addresses=("192.0.2.40",)),
)
# Long messages, 199 and 299 characters, cut wherever the tests use them.
LONG_200 = " ".join(["fictional"] * 20)
LONG_300 = " ".join(["fictional"] * 30)


def handoff(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """A terminal that can be handed off and an SSH that exits with 0."""
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    launch = Mock(return_value=0)
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    return launch


@pytest.mark.parametrize("machines", [MACHINES, ()])
async def test_result_line_starts_blank_and_is_one_row(machines) -> None:
    app = SSHWorkbenchApp(machines)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        result = app.query_one("#result-line", ResultLine)
        assert app.result is result
        assert result.connection is app.query_one("#connection-status", ResultSlot)
        assert result.link is app.query_one("#link-status", ResultSlot)
        assert list(result.children) == [result.connection, result.link]
        assert result.region.height == 1
        for slot in (result.connection, result.link):
            assert slot.message == ""
            assert slot.styles.display == "none"
        assert app.query_one(Footer).region.y == result.region.bottom
        assert app.query_one("#panes").region.bottom == result.region.y


async def test_result_line_keeps_both_slots_newest_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = handoff(monkeypatch)
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp(LINKED)
    async with app.run_test(size=(80, 24)) as pilot:
        result = app.result
        connection, link = result.connection, result.link
        await pilot.press("c")
        launch.assert_called_once_with(LINKED[0])
        await pilot.pause()
        assert connection.message == "SSH exited with status 0. Machine 1: garden"
        assert str(connection.content).startswith("● ")
        assert connection.render().spans == [Span(0, 1, "$success")]
        assert link.styles.display == "none"
        await pilot.press("o")
        await wait_for(pilot, lambda: "accepted" in link.message)
        await pilot.pause()
        opener.assert_called_once_with("https://example.invalid/garden")
        assert list(result.children) == [link, connection]
        assert link.message == (
            f"Repository {LinkResult.ACCEPTED.value} Machine 1: garden"
        )
        assert connection.message == "SSH exited with status 0. Machine 1: garden"
        assert str(link.content).startswith("› ")
        assert link.render().spans == [Span(0, 1, "$success")]
        assert result.region.height == 2
        assert link.region.bottom == connection.region.y
        await pilot.press("c")
        await pilot.pause()
        assert launch.call_count == 2
        assert list(result.children) == [connection, link]
        assert connection.region.bottom == link.region.y
        assert link.message == (
            f"Repository {LinkResult.ACCEPTED.value} Machine 1: garden"
        )


async def test_export_problem_appends_to_the_connection_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(folder: Path, machines: object, source: Path) -> None:
        raise ExportError("Could not write ssh-workbench.config: permission denied.")

    monkeypatch.setattr(app_module, "write_exports", refuse)
    _, path, text = workspace(tmp_path, monkeypatch, (LAB,))
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test(size=(80, 24)) as pilot:
        connection = app.result.connection
        await add_exported_box(app, pilot)
        await wait_for(pilot, lambda: "Could not write" in connection.message)
        await pilot.pause()
        assert connection.message == (
            "Saved machine 2: box. Could not write ssh-workbench.config: "
            "permission denied."
        )
        assert str(connection.content).startswith("× Saved machine 2: box.")
        assert connection.render().spans == [Span(0, 1, "$error")]


async def test_short_screens_cap_the_result_line_at_two_rows() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(120, 18)) as pilot:
        result = app.result
        result.show(result.connection, LONG_200, Glyph.FAILURE)
        result.show(result.link, LONG_200, Glyph.OTHER)
        await pilot.pause()
        footer = app.query_one(Footer)
        assert result.region.height == 2
        assert footer.region.height == 1
        assert app.query_one("#panes").region.bottom == result.region.y
        assert result.region.bottom == footer.region.y
        assert list(result.children) == [result.link, result.connection]
        for slot, glyph in ((result.link, "·"), (result.connection, "×")):
            assert slot.region.height == 1
            line = slot.render_line(0).text
            assert line.startswith(f"{glyph} fictional fictional")
            assert line.endswith("…")
            assert len(line) == 118


async def test_short_screens_give_a_lone_result_both_rows() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(120, 18)) as pilot:
        result = app.result
        footer = app.query_one(Footer)
        # 301 cells need three rows of 118, so the second row is cut.
        result.show(result.connection, LONG_300, Glyph.FAILURE)
        await pilot.pause()
        assert result.region.height == 2
        assert result.connection.region.height == 2
        lines = [result.connection.render_line(y).text for y in range(2)]
        assert lines[0].startswith("× fictional fictional")
        assert "…" not in lines[0]
        assert lines[1].endswith("…")
        assert len(lines[1]) == 118
        assert footer.region.height == 1
        assert app.query_one("#panes").region.bottom == result.region.y
        assert result.region.bottom == footer.region.y
        result.show(result.link, LONG_200, Glyph.OTHER)
        await pilot.pause()
        assert result.region.height == 2
        assert list(result.children) == [result.link, result.connection]
        for slot, glyph in ((result.link, "·"), (result.connection, "×")):
            assert slot.region.height == 1
            line = slot.render_line(0).text
            assert line.startswith(f"{glyph} fictional fictional")
            assert line.endswith("…")
        assert app.query_one("#panes").region.bottom == result.region.y


async def test_tall_screens_cap_the_result_line_at_three_rows() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        panes = app.query_one("#panes")
        idle = panes.region.height
        result = app.result
        result.show(result.connection, LONG_300, Glyph.FAILURE)
        await pilot.pause()
        assert result.region.height == 3
        assert result.connection.region.height == 3
        lines = [result.connection.render_line(y).text for y in range(3)]
        assert lines[0].startswith("× fictional fictional")
        assert "…" not in lines[0] + lines[1]
        assert lines[2].endswith("…")
        assert len(lines[2]) == 78
        assert panes.region.height == idle - 2
        assert panes.region.bottom == result.region.y
        result.show(result.link, LONG_300, Glyph.OTHER)
        await pilot.pause()
        assert result.region.height == 3
        assert list(result.children) == [result.link, result.connection]
        assert result.link.region.height == 2
        assert result.connection.region.height == 1
        assert result.link.render_line(0).text.startswith("· fictional fictional")
        assert result.link.render_line(1).text.endswith("…")
        assert result.connection.render_line(0).text.endswith("…")
        assert panes.region.height == idle - 2
        assert panes.region.bottom == result.region.y


async def test_result_line_recomputes_on_resize() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)) as pilot:
        result = app.result
        result.show(result.connection, LONG_300, Glyph.FAILURE)
        result.show(result.link, LONG_300, Glyph.OTHER)
        await pilot.pause()
        assert result.region.height == 3
        await pilot.resize_terminal(120, 18)
        await wait_for(pilot, lambda: "-short" in app.screen.classes)
        await pilot.pause()
        assert result.region.height == 2
        assert result.link.region.height == 1
        assert app.query_one("#panes").region.bottom == result.region.y
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 18)) as pilot:
        result = app.result
        result.show(result.connection, LONG_300, Glyph.FAILURE)
        await pilot.pause()
        assert result.region.height == 2
        # A height-only resize: no width changes, so only the classes do.
        await pilot.resize_terminal(80, 24)
        await wait_for(pilot, lambda: "-tall" in app.screen.classes)
        await pilot.pause()
        assert result.region.height == 3
        assert result.connection.render_line(2).text.endswith("…")
        # A width-only resize rewraps: 301 cells fit in two rows of 198.
        await pilot.resize_terminal(200, 24)
        await pilot.pause()
        assert result.region.height == 2
        assert result.connection.render_line(1).text.rstrip().endswith("fictional")


@pytest.mark.parametrize("path", [None, Path("fictional") / "machines.toml"])
async def test_no_file_screen_names_the_user_guide(path: Path | None) -> None:
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = empty_text(app)
        assert content.endswith("--config PATH · the user guide describes the format")
        assert "README" not in content


@pytest.mark.parametrize("size", [(40, 16), (60, 20)])
async def test_no_file_screen_fits_narrow_terminals(size: tuple[int, int]) -> None:
    path = Path("fictional") / ("long-folder-name-" * 4) / "machines.toml"
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        # Every line wraps inside the screen, the path included, and the
        # whole message sits above the result line.
        empty = app.query_one("#empty-state", VerticalScroll)
        assert app.query_one("#panes").region.contains_region(empty.region)
        rows = []
        for line in empty_lines(app):
            assert app.screen.region.contains_region(line.region)
            rows.append(
                [line.render_line(y).text.rstrip() for y in range(line.region.height)]
            )
        assert len(rows[2]) > 1
        assert "".join(rows[2]) == str(path)
        assert rows[3][-1].endswith("format")


async def test_empty_screen_is_muted_with_a_footer_style_key() -> None:
    app = SSHWorkbenchApp(None, config_path=Path("fictional") / "machines.toml")
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        muted = Color.parse(app.get_css_variables()["text-muted"])
        lines = empty_lines(app)
        assert [line.styles.color for line in lines] == [muted] * 4
        footer_key = next(key for key in app.query(FooterKey) if key.action == "add")
        (key_style,) = [
            segment.style
            for segment in footer_key.render_line(0)
            if segment.text.strip() == "a"
        ]
        segments = [
            (segment.text, segment.style)
            for line in lines
            for segment in line.render_line(0)
            if segment.text.strip()
        ]
        styled = [(text, style) for text, style in segments if style.bold]
        assert [(text, style.color) for text, style in styled] == [
            ("a", key_style.color)
        ]
        assert all(
            style.color.triplet == muted.rgb
            for text, style in segments
            if (text, style) not in styled
        )


@pytest.mark.parametrize("size", [(40, 16), (200, 50)])
async def test_empty_screen_fits_any_size(size: tuple[int, int]) -> None:
    app = SSHWorkbenchApp([])
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        empty = app.query_one("#empty-state", VerticalScroll)
        assert empty_text(app) == "no machines in this file yet · a to add"
        assert app.screen.region.contains_region(empty.region)
        # The panes' resize handler finds no list here and must not raise.
        await pilot.resize_terminal(40, 16)
        await pilot.pause()
        assert app.is_running


async def test_empty_screen_scrolls_to_its_last_line() -> None:
    # Taller than the panes at 40x16, so the empty screen scrolls.
    path = Path("fictional") / ("x" * 276) / "machines.toml"
    assert len(str(path)) == 300
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test(size=(40, 16)) as pilot:
        await pilot.pause()
        empty = app.query_one("#empty-state", VerticalScroll)
        assert empty.max_scroll_y > 0
        assert app.focused is empty
        last = empty_lines(app)[-1]
        assert not empty.region.contains_region(last.region)
        empty.scroll_end(animate=False)
        await wait_for(pilot, lambda: empty.scroll_y == empty.max_scroll_y)
        await pilot.pause()
        assert empty.region.contains_region(last.region)
