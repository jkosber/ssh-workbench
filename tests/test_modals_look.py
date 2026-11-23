"""The shared modal look: backdrop, breakpoints, hint rows, marks and the two
questions sized to their text. Fictional files in tmp_path only."""

from pathlib import Path

import pytest
from support import contrast, showing, wait_for
from textual.color import Color
from textual.widgets import Static

from ssh_workbench.app import LinkPicker, SSHWorkbenchApp
from ssh_workbench.config import Link, Machine, format_machines, parse_machines
from ssh_workbench.forms import (
    Box,
    ConfirmDelete,
    ConfirmInclude,
    KeyChoice,
    KeySetup,
    MachineForm,
    Ring,
    WorkbenchModal,
    hint_row,
    marked,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

STUDIO = Machine(
    "studio",
    "Studio",
    user="dev",
    addresses=("192.0.2.40",),
    links=(
        Link("Dashboard", "https://192.0.2.40:8006"),
        Link("Status page", "https://studio.example.com/status"),
    ),
)
# A 60-character name and a 130-character ID.
LONG = Machine(
    ("long-machine-id-" * 9)[:130],
    "Rack machine number one in the far corner of the server room",
    alias="rack-host",
)
SHORT_PATH = "/srv/example/homes/.ssh/config"
LONG_PATH = "/srv/" + "fictional-folder/" * 6 + "nested/config"
DELETE_HINT = " y delete  n keep "
INCLUDE_HINT = " y add  n not now "
KEY = "$footer-key-foreground bold"
LABEL = "$footer-description-foreground"


def saved_app(tmp_path: Path, machines=(STUDIO,), text: str | None = None):
    path = tmp_path / "machines.toml"
    text = format_machines(machines) if text is None else text
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text), path


def variable(app: SSHWorkbenchApp, name: str) -> Color:
    return Color.parse(app.get_css_variables()[name])


def hint(screen) -> Static:
    return screen.query_one(".frame > .hint", Static)


async def open_delete(app, pilot) -> ConfirmDelete:
    await pilot.press("x")
    await wait_for(pilot, lambda: showing(app, ConfirmDelete))
    await pilot.pause()
    return app.screen


async def test_hint_row_is_the_footer_style() -> None:
    row = hint_row([("y", "delete"), ("n", "keep")])
    assert row.plain == " y delete  n keep "
    assert [(span.start, span.end, span.style) for span in row.spans] == [
        (1, 2, KEY),
        (3, 9, LABEL),
        (11, 12, KEY),
        (13, 17, LABEL),
    ]
    assert hint_row([("[b]", "x")]).plain == " [b] x "


async def test_hint_keys_match_the_drawn_footer() -> None:
    app = SSHWorkbenchApp((STUDIO,))
    async with app.run_test(size=(80, 24)):
        surface = variable(app, "surface")
        for name in ("footer-key-foreground", "footer-description-foreground"):
            ratio = contrast(variable(app, name), surface)
            assert ratio >= 4.5, (name, ratio)


@pytest.mark.parametrize("modal", ["form", "delete", "links", "keys", "include"])
async def test_every_modal_dims_the_base_screen(tmp_path: Path, modal: str) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        if modal == "form":
            await pilot.press("a")
            kind = MachineForm
        elif modal == "delete":
            await pilot.press("x")
            kind = ConfirmDelete
        elif modal == "links":
            await pilot.press("o")
            kind = LinkPicker
        elif modal == "keys":
            choice = KeyChoice(Path("~/.ssh/id_a"), "id_a.pub")
            app.push_screen(KeySetup(STUDIO, [choice], None))
            kind = KeySetup
        else:
            app.push_screen(ConfirmInclude(Path(SHORT_PATH), True))
            kind = ConfirmInclude
        await wait_for(pilot, lambda: showing(app, kind))
        assert isinstance(app.screen, WorkbenchModal)
        assert app.screen.styles.background == variable(app, "background").with_alpha(
            0.88
        )


HORIZONTAL = ("-narrow", "-normal", "-large")


async def test_modal_breakpoints(tmp_path: Path) -> None:
    for width, height, expected, vertical in (
        (59, 20, "-narrow", "-short"),
        (60, 20, "-normal", "-short"),
        (79, 24, "-normal", "-tall"),
        (80, 24, "-large", "-tall"),
        (130, 20, "-large", "-short"),
    ):
        app, _ = saved_app(tmp_path)
        async with app.run_test(size=(width, height)) as pilot:
            screen = await open_delete(app, pilot)
            present = [name for name in HORIZONTAL if screen.has_class(name)]
            assert present == [expected], (width, present)
            assert screen.has_class(vertical), (height, vertical)
    app, _ = saved_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        screen = await open_delete(app, pilot)
        assert screen.has_class("-large")
        await pilot.resize_terminal(59, 20)
        await pilot.pause()
        assert [name for name in HORIZONTAL if screen.has_class(name)] == ["-narrow"]


@pytest.mark.parametrize("size", [(160, 50), (80, 24), (60, 20)])
async def test_the_delete_question_hugs_its_text(
    tmp_path: Path, size: tuple[int, int]
) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test(size=size) as pilot:
        screen = await open_delete(app, pilot)
        frame = screen.query_one("#confirm-delete")
        region = frame.region
        assert region.width == len("Delete Studio (studio)?") + 4
        assert region.height == 5
        left, right = region.x, size[0] - region.right
        assert abs(left - right) <= 1
        assert frame.styles.border_top[1] == variable(app, "error")
        row = hint(screen)
        assert row.content.plain == DELETE_HINT
        assert row.region.height == 2
        assert row.region.bottom == region.bottom - 1
        question = frame.query_children(Static).first()
        assert question.region.bottom == row.region.y


COMMENTED_LONG = "# a note added elsewhere\n" + format_machines((LONG, STUDIO))


@pytest.mark.parametrize(("size", "width"), [((80, 24), 72), ((60, 20), 54)])
async def test_a_long_question_keeps_its_hint_row(
    tmp_path: Path, size: tuple[int, int], width: int
) -> None:
    app, path = saved_app(tmp_path, (LONG, STUDIO), COMMENTED_LONG)
    async with app.run_test(size=size) as pilot:
        screen = await open_delete(app, pilot)
        text = "\n".join(str(widget.content) for widget in screen.query(Static))
        assert "without its comments or formatting" in text
        frame = screen.query_one("#confirm-delete")
        assert app.screen.region.contains_region(frame.region)
        assert frame.region.width == width
        assert frame.max_scroll_y == 0
        row = hint(screen)
        assert row.content.plain == DELETE_HINT
        assert row.region.bottom == frame.region.bottom - 1
        await pilot.press("y")
        await wait_for(pilot, lambda: len(app.screen_stack) == 1)
        await wait_for(
            pilot,
            lambda: (
                [m.id for m in parse_machines(path.read_text(encoding="utf-8"))]
                == ["studio"]
            ),
        )
    app, path = saved_app(tmp_path, (LONG, STUDIO), COMMENTED_LONG)
    async with app.run_test(size=size) as pilot:
        for key in ("n", "escape"):
            await open_delete(app, pilot)
            await pilot.press(key)
            await wait_for(pilot, lambda: len(app.screen_stack) == 1)
            await pilot.pause()
            assert path.read_text(encoding="utf-8") == COMMENTED_LONG
            assert [m.id for m in app.machines] == [LONG.id, "studio"]


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("config", [SHORT_PATH, LONG_PATH])
async def test_the_include_question_fits(
    tmp_path: Path, size: tuple[int, int], exists: bool, config: str
) -> None:
    assert len(config) in (30, 120)
    app, _ = saved_app(tmp_path)
    async with app.run_test(size=size) as pilot:
        app.push_screen(ConfirmInclude(Path(config), exists))
        await wait_for(pilot, lambda: showing(app, ConfirmInclude))
        await pilot.pause()
        screen = app.screen
        frame = screen.query_one("#confirm-include")
        assert screen.region.contains_region(frame.region)
        assert frame.max_scroll_y == 0
        row = hint(screen)
        assert row.content.plain == INCLUDE_HINT
        assert row.region.bottom == frame.region.bottom - 1
        line = screen.query_one("#include-line", Static)
        assert str(line.content) == "Include ssh-workbench.config"
        children = list(frame.query_children(Static))
        index = children.index(line)
        assert children[index - 1].region.bottom == line.region.y - 1
        assert children[index + 1].region.y == line.region.bottom + 1


async def test_marks_change_shape() -> None:
    assert Ring("x", value=True).BUTTON_INNER == "●"
    assert Ring("x", value=False).BUTTON_INNER == "○"
    assert Box("x", value=True).BUTTON_INNER == "X"
    assert Box("x", value=False).BUTTON_INNER == "·"
    assert marked("a", True).plain == "▌a"
    assert marked("a", False).plain == " a"
