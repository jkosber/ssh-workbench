"""The look: theme, header summary and the layout at each terminal size."""

import asyncio
from pathlib import Path

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Footer, ListView, Static

from ssh_workbench.app import SSHWorkbenchApp, StatusSymbol
from ssh_workbench.config import Link, Machine, format_machines, parse_machines
from ssh_workbench.forms import ConfirmDelete, MachineForm
from ssh_workbench.status import AliasTarget, State

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
LONG_SUMMARY = "4 machines   ● 2 online   ○ 1 offline   ◇ 1 can't check"
SHORT_SUMMARY = "4  ●2 ○1 ◇1"


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


def panes(app: SSHWorkbenchApp) -> tuple[ListView, VerticalScroll]:
    return app.query_one(ListView), app.query_one("#machine-details", VerticalScroll)


def saved_app(tmp_path: Path, machines) -> SSHWorkbenchApp:
    path = tmp_path / "machines.toml"
    text = format_machines(machines)
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text)


def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


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
    [((120, 40), LONG_SUMMARY), ((80, 24), LONG_SUMMARY), ((60, 20), SHORT_SUMMARY)],
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
        await pilot.resize_terminal(60, 20)
        await wait_for(pilot, lambda: summary(app) == SHORT_SUMMARY)
        await pilot.resize_terminal(120, 40)
        await wait_for(pilot, lambda: summary(app) == LONG_SUMMARY)


@pytest.mark.parametrize(
    ("machines", "expected"),
    [(MACHINES[:2], "2 machines"), (MACHINES[:1], "1 machine"), ([], ""), (None, "")],
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
        assert summary(app) == "2 machines"
        for remaining in ("1 machine", ""):
            await pilot.press("x")
            await wait_for(pilot, lambda: showing(app, ConfirmDelete))
            await pilot.press("y")
            await wait_for(pilot, lambda: summary(app) == remaining)


@pytest.mark.parametrize("size", [(50, 24), (40, 16)])
async def test_narrow_terminals_stack_the_list_above_the_details(
    size: tuple[int, int],
) -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        machine_list, pane = panes(app)
        assert machine_list.region.bottom <= pane.region.y
        assert machine_list.region.x == pane.region.x
        assert machine_list.region.width == pane.region.width
        assert machine_list.region.height >= 4
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


@pytest.mark.parametrize(
    ("size", "shown"),
    [((80, 16), False), ((80, 20), True), ((50, 24), False), ((60, 24), True)],
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
    ("size", "rows"), [((40, 16), 2), ((50, 20), 2), ((60, 20), 1)]
)
async def test_narrow_footers_show_every_key_on_two_rows(
    size: tuple[int, int], rows: int
) -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=size) as pilot:
        footer = app.query_one(Footer)
        await wait_for(
            pilot,
            lambda: (
                len(footer.query("FooterKey")) == 8
                and all(key.region.width for key in footer.query("FooterKey"))
            ),
        )
        assert footer.region.height == rows
        for key in footer.query("FooterKey"):
            assert app.screen.region.contains_region(key.region), key.action
        machine_list, _ = panes(app)
        assert machine_list.region.height >= 4


@pytest.mark.parametrize(("height", "rows"), [(16, 2), (20, 3)])
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


@pytest.mark.parametrize("size", [(40, 16), (200, 50)])
async def test_empty_screen_fits_any_size(size: tuple[int, int]) -> None:
    app = SSHWorkbenchApp([])
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        empty = app.query_one("#empty-state", Static)
        assert "Press A to add one." in str(empty.content)
        assert app.screen.region.contains_region(empty.region)
