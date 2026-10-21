import json
import os
from pathlib import Path

import pytest
from textual.containers import VerticalScroll
from textual.content import Content
from textual.widgets import Footer, ListView, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Link, Machine, parse_machines

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
    Machine(
        "studio-box",
        "Studio box",
        user="studio",
        addresses=("studio.example", "192.0.2.40"),
        port=2222,
        key="~/.ssh/id_ed25519_studio",
    ),
)
EXPECTED_DETAILS = (
    {
        "id": "garden-demo",
        "name": "Garden demo",
        "connection": "SSH alias",
        "target-label": "SSH alias",
        "target": "garden-demo-host",
        "user": "From your SSH config",
        "port": "From your SSH config",
        "key": "From your SSH config",
        "links": "Repository: https://example.com/garden.git\n"
        "Documentation: https://example.com/garden/docs",
    },
    {
        "id": "studio-box",
        "name": "Studio box",
        "connection": "Direct",
        "target-label": "Addresses",
        "target": "studio.example\n192.0.2.40",
        "user": "studio",
        "port": "2222",
        "key": "~/.ssh/id_ed25519_studio",
        "links": "None",
    },
)


def details(app: SSHWorkbenchApp) -> dict[str, str]:
    return {
        field: str(app.query_one(f"#machine-{field}", Static).content)
        for field in EXPECTED_DETAILS[0]
    }


@pytest.mark.parametrize("size", [(80, 24), (120, 40), (60, 20)])
@pytest.mark.parametrize(
    ("machines", "message", "hint"),
    [
        (None, "No machine file selected.", "--config PATH"),
        ([], "No machines in this file yet.", "Add [[machines]] entries"),
    ],
)
async def test_empty_states(
    machines, message: str, hint: str, size: tuple[int, int]
) -> None:
    app = SSHWorkbenchApp(machines)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        assert app.is_running
        assert app.title == "SSH Workbench"
        status = app.query_one("#empty-state", Static)
        assert status.visible
        assert message in str(status.content)
        assert hint in str(status.content)
        assert not app.query(ListView)
        await pilot.press("down", "tab", "up", "q")
        assert not app.is_running
        assert app.return_code == 0


async def test_no_config_screen_names_default_path() -> None:
    path = Path("fictional") / "odd\x1bname" / "machines.toml"
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = str(app.query_one("#empty-state", Static).content)
        assert "No machine file yet." in content
        assert f"fictional{os.sep}odd\\x1bname{os.sep}machines.toml" in content
        assert "\x1b" not in content
        assert "--config PATH" in content


async def test_no_config_screen_without_default_path() -> None:
    app = SSHWorkbenchApp(None)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = str(app.query_one("#empty-state", Static).content)
        assert "Restart with --config PATH" in content
        assert "None" not in content


async def test_empty_file_screen_names_the_file_without_config_hint() -> None:
    path = Path("fictional") / "odd\x1bname" / "machines.toml"
    app = SSHWorkbenchApp([], config_path=path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = str(app.query_one("#empty-state", Static).content)
        assert "No machines in this file yet:" in content
        assert f"fictional{os.sep}odd\\x1bname{os.sep}machines.toml" in content
        assert "\x1b" not in content
        assert "--config" not in content
        assert "Add [[machines]] entries to it, then restart." in content


async def test_initial_selection_order_and_keyboard_details() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)) as pilot:
        machine_list = app.query_one(ListView)
        assert app.focused is machine_list
        assert machine_list.index == 0
        assert machine_list.border_title == "Machines"
        assert [str(widget.content) for widget in machine_list.query(Static)] == [
            "Garden demo",
            "Studio box",
        ]
        for index, key in [(0, "up"), (1, "down"), (1, "down"), (0, "up")]:
            await pilot.press(key)
            assert machine_list.index == index
            assert machine_list.highlighted_child is machine_list.children[index]
            assert details(app) == EXPECTED_DETAILS[index]
        await pilot.press("tab")
        pane = app.query_one("#machine-details", VerticalScroll)
        assert app.focused is pane
        assert machine_list.index == 0
        assert pane.styles.border.top != machine_list.styles.border.top
        await pilot.press("shift+tab")
        assert app.focused is machine_list


async def test_direct_machine_without_optional_fields_shows_not_set() -> None:
    app = SSHWorkbenchApp([Machine("plain-box", "Plain", addresses=("plain.example",))])
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert details(app) == {
            "id": "plain-box",
            "name": "Plain",
            "connection": "Direct",
            "target-label": "Addresses",
            "target": "plain.example",
            "user": "Not set",
            "port": "Not set",
            "key": "Not set",
            "links": "None",
        }


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        ("[bold]Garden[/bold]", "[bold]Garden[/bold]"),
        (
            "[@click=app.quit]click[/] [link=https://example.com]link[/link]",
            "[@click=app.quit]click[/] [link=https://example.com]link[/link]",
        ),
        ("Café / 東京 / \U0001f331", "Café / 東京 / \U0001f331"),
        ("row\nnext\r\t\b\0", r"row\nnext\r\t\x08\x00"),
        (
            "escape\x1b]8;;https://example.com\x07",
            r"escape\x1b]8;;https://example.com\x07",
        ),
        ("C1\x85\x9b31m", r"C1\x85\x9b31m"),
        ("direction‮⁦​ ", r"direction‮⁦​ "),
    ],
)
async def test_names_are_literal_and_controls_are_visible(
    name: str, shown: str
) -> None:
    machines = parse_machines(
        'schema_version = 2\n[[machines]]\nid = "literal-demo"\n'
        f"name = {json.dumps(name, ensure_ascii=False)}\n"
        'alias = "literal-demo-host"\n'
        '[[machines.links]]\nname = "[bold]Repo[/bold]"\n'
        'url = "https://example.com/[bold]repo[/bold]"\n'
        f"[[machines.links]]\nname = {json.dumps(name, ensure_ascii=False)}\n"
        'url = "https://example.com/[link=docs]"\n'
    )
    app = SSHWorkbenchApp(machines)
    async with app.run_test(size=(80, 24)) as pilot:
        widgets = [
            app.query_one(ListView).query_one(Static),
            app.query_one("#machine-name", Static),
        ]
        for widget in widgets:
            rendered = widget.render()
            assert isinstance(rendered, Content)
            assert rendered.plain == shown
            assert not rendered.spans
        rendered = app.query_one("#machine-links", Static).render()
        assert isinstance(rendered, Content)
        assert rendered.plain == (
            "[bold]Repo[/bold]: https://example.com/[bold]repo[/bold]\n"
            f"{shown}: https://example.com/[link=docs]"
        )
        assert not rendered.spans
        await pilot.click("#machine-name")
        app.query_one("#machine-details", VerticalScroll).scroll_to_widget(
            app.query_one("#machine-links"), animate=False
        )
        await pilot.pause()
        await pilot.click("#machine-links")
        await pilot.press("enter")
        assert app.is_running
        assert machines[0].name == name
        assert app.machines[0] is machines[0]


@pytest.mark.parametrize("size", [(80, 24), (120, 40), (60, 20)])
async def test_long_values_wrap_scroll_and_reset(size: tuple[int, int]) -> None:
    long_machine = Machine(
        "long-demo-" + "x" * 120,
        "Long 東京 " * 50,
        alias="demo-" + "host" * 100,
        links=(
            Link("Repository", "https://example.com/" + "path/" * 150),
            Link("Documentation", "https://example.com/" + "docs/" * 150),
        ),
    )
    app = SSHWorkbenchApp([long_machine, MACHINES[1]])
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        machine_list = app.query_one(ListView)
        pane = app.query_one("#machine-details", VerticalScroll)
        footer = app.query_one(Footer)
        assert app.screen.region.contains_region(machine_list.region)
        assert app.screen.region.contains_region(pane.region)
        assert app.screen.region.contains_region(footer.region)
        assert machine_list.region.right <= pane.region.x
        assert pane.region.bottom <= footer.region.y
        assert pane.max_scroll_x == 0
        assert pane.max_scroll_y > 0
        assert str(app.query_one("#machine-links", Static).content).endswith(
            "docs/" * 150
        )
        await pilot.press("tab", "down", "pagedown")
        await pilot.wait_for_scheduled_animations()
        assert app.focused is pane
        assert pane.scroll_y > 0
        await pilot.press("end")
        await pilot.wait_for_scheduled_animations()
        assert pane.scroll_y == pane.max_scroll_y
        await pilot.press("shift+tab", "down")
        await pilot.pause()
        assert machine_list.index == 1
        assert pane.scroll_y == 0
        assert str(app.query_one("#machine-name", Static).content) == "Studio box"
        await pilot.resize_terminal(80, 24)
        assert app.is_running


async def test_many_machines_keep_keyboard_selection_visible() -> None:
    machines = [
        Machine(f"demo-{i}", f"Demo {i}", alias=f"demo-{i}-host") for i in range(35)
    ]
    app = SSHWorkbenchApp(machines)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press(*(["down"] * 34))
        machine_list = app.query_one(ListView)
        assert machine_list.index == 34
        assert machine_list.scroll_y > 0
        assert str(app.query_one("#machine-id", Static).content) == "demo-34"
        assert machine_list.scrollable_content_region.contains_region(
            machine_list.highlighted_child.region
        )


async def test_help_line_fits_60_columns() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.pause()
        help_line = app.query_one("#navigation-help", Static)
        assert str(help_line.content) == (
            "Up/Down: select   Tab: switch pane   PgUp/PgDn: scroll"
        )
        assert help_line.region.height == 1


@pytest.mark.parametrize("key", ["q", "ctrl+q"])
@pytest.mark.parametrize("machines", [None, [], MACHINES])
async def test_keyboard_exit_is_clean(key: str, machines) -> None:
    app = SSHWorkbenchApp(machines)
    async with app.run_test() as pilot:
        if machines:
            await pilot.press("tab")
        await pilot.press(key)
        assert not app.is_running
        assert app.return_code == 0
