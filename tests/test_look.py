"""The look: theme, header summary and the layout at each terminal size."""

import asyncio
from pathlib import Path

import pytest
from textual.color import Color
from textual.containers import VerticalScroll
from textual.widgets import Footer, HelpPanel, KeyPanel, ListView, Static
from textual.widgets._footer import FooterKey
from textual.widgets._key_panel import BindingsTable

from ssh_workbench.app import (
    STATE_COLORS,
    KeyFooter,
    SSHWorkbenchApp,
    StatusSymbol,
    state_css,
)
from ssh_workbench.config import Link, Machine, format_machines, parse_machines
from ssh_workbench.forms import ConfirmDelete, MachineForm
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


@pytest.mark.parametrize(("size", "min_rows"), [((50, 24), 4), ((40, 16), 2)])
async def test_narrow_terminals_stack_the_list_above_the_details(
    size: tuple[int, int], min_rows: int
) -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        machine_list, pane = panes(app)
        assert machine_list.region.bottom <= pane.region.y
        assert machine_list.region.x == pane.region.x
        assert machine_list.region.width == pane.region.width
        assert machine_list.region.height >= min_rows
        assert app.screen.region.contains_region(pane.region)


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


@pytest.mark.parametrize(
    ("size", "shown"),
    [
        ((80, 16), False),
        ((80, 23), False),
        ((80, 24), True),
        ((50, 24), False),
        ((60, 24), True),
    ],
)
async def test_short_or_narrow_terminals_hide_the_help_line(
    size: tuple[int, int], shown: bool
) -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        assert app.query_one("#navigation-help").display is shown
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


@pytest.mark.parametrize(("height", "rows"), [(16, 2), (23, 2), (24, 3)])
async def test_short_terminals_give_link_results_two_rows(
    height: int, rows: int
) -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, height)) as pilot:
        await pilot.pause()
        assert app.query_one("#link-status").region.height == rows


@pytest.mark.parametrize("path", [None, Path("fictional") / "machines.toml"])
async def test_no_file_screen_names_the_user_guide(path: Path | None) -> None:
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = str(app.query_one("#empty-state", Static).content)
        assert content.endswith("The user guide describes the format.")
        assert "README" not in content


@pytest.mark.parametrize("size", [(40, 16), (60, 20)])
async def test_no_file_screen_fits_narrow_terminals(size: tuple[int, int]) -> None:
    path = Path("fictional") / ("long-folder-name-" * 4) / "machines.toml"
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        # The message may be taller than a short screen, which scrolls; it
        # must never be wider, which nothing can scroll to.
        empty = app.query_one("#empty-state", Static)
        screen = app.screen.region
        assert screen.x <= empty.region.x and empty.region.right <= screen.right
        lines = [empty.render_line(y).text.rstrip() for y in range(empty.region.height)]
        assert any(line.endswith("format.") for line in lines)


@pytest.mark.parametrize("size", [(40, 16), (200, 50)])
async def test_empty_screen_fits_any_size(size: tuple[int, int]) -> None:
    app = SSHWorkbenchApp([])
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        empty = app.query_one("#empty-state", Static)
        assert "Press A to add one." in str(empty.content)
        assert app.screen.region.contains_region(empty.region)
