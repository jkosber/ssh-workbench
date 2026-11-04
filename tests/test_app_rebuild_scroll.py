"""A save that rebuilds a list longer than its pane keeps the selected row on screen."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Input, ListView, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, parse_machines
from ssh_workbench.forms import ConfirmDelete, MachineForm

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

# More machines than the list pane shows at 80x24.
MACHINES = tuple(
    Machine(
        f"demo-{number:02d}",
        f"Demo {number:02d}",
        addresses=(f"192.0.2.{number + 10}",),
    )
    for number in range(24)
)
# Below the first screenful, and not the last row.
SELECTED = 20


def saved_app(tmp_path: Path) -> tuple[SSHWorkbenchApp, Path]:
    path = tmp_path / "machines.toml"
    text = format_machines(MACHINES)
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text), path


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


def rebuilt(app: SSHWorkbenchApp, old_list: ListView) -> bool:
    """The rebuild replaced the list and gave the new one focus."""
    lists = app.query("#machine-list")
    return (
        len(lists) == 1
        and lists.first() is not old_list
        and app.focused is lists.first()
    )


def rows_on_screen(machine_list: ListView) -> list[int]:
    """The rows whose whole region lies inside the list's visible region."""
    visible = machine_list.scrollable_content_region
    return [
        index
        for index, row in enumerate(machine_list.children)
        if visible.contains_region(row.region)
    ]


async def select_below_first_screenful(app: SSHWorkbenchApp, pilot) -> ListView:
    await pilot.press(*(["down"] * SELECTED))
    machine_list = app.query_one("#machine-list", ListView)
    assert machine_list.index == SELECTED
    assert machine_list.highlighted_child is machine_list.children[SELECTED]
    assert machine_list.scroll_y > 0
    assert SELECTED in rows_on_screen(machine_list)
    assert 0 not in rows_on_screen(machine_list)
    return machine_list


async def test_delete_keeps_the_next_machine_on_screen(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        old_list = await select_below_first_screenful(app, pilot)
        await pilot.press("x")
        await wait_for(pilot, lambda: showing(app, ConfirmDelete))
        await pilot.press("y")
        await wait_for(pilot, lambda: rebuilt(app, old_list))
        await pilot.pause()
        assert [m.id for m in parse_machines(path.read_text(encoding="utf-8"))] == [
            machine.id for machine in MACHINES if machine.id != "demo-20"
        ]
        machine_list = app.query_one("#machine-list", ListView)
        assert len(machine_list.children) == 23
        assert machine_list.index == SELECTED
        assert machine_list.highlighted_child is machine_list.children[SELECTED]
        assert str(app.query_one("#machine-id", Static).content) == "demo-21"
        assert SELECTED in rows_on_screen(machine_list)


async def test_edit_keeps_the_edited_machine_on_screen(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        old_list = await select_below_first_screenful(app, pilot)
        await pilot.press("e")
        await wait_for(pilot, lambda: showing(app, MachineForm))
        app.screen.query_one("#form-name", Input).value = "Demo 20 renamed"
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: rebuilt(app, old_list))
        await pilot.pause()
        assert parse_machines(path.read_text(encoding="utf-8"))[SELECTED] == Machine(
            "demo-20", "Demo 20 renamed", addresses=("192.0.2.30",)
        )
        machine_list = app.query_one("#machine-list", ListView)
        assert len(machine_list.children) == 24
        assert machine_list.index == SELECTED
        assert machine_list.highlighted_child is machine_list.children[SELECTED]
        assert str(app.query_one("#machine-name", Static).content) == "Demo 20 renamed"
        assert SELECTED in rows_on_screen(machine_list)
