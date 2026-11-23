"""The key picker's look: a blank row above each section label, a hint row
pinned under a scrolling body, rings that differ by shape and a marker on the
highlighted key. Fictional files in tmp_path only."""

from pathlib import Path

import pytest
from support import contrast, showing, wait_for
from textual.color import Color
from textual.content import Content
from textual.widgets import OptionList, RadioButton, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, parse_machines
from ssh_workbench.forms import KeyChoice, KeyPlan, KeySetup

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

GARDEN = Machine("garden", "Garden", user="dev", addresses=("192.0.2.60",))
# The choices, note and "Not listed" line of the 60x20 fit test in
# tests/test_keysetup_ui.py.
NOTE = (
    "Your SSH config doesn't name this key for garden-host. Add this line "
    "under Host garden-host; Workbench never edits the config: "
    "IdentityFile ~/.ssh/id_a"
)
SSH = Path("~/.ssh")
CHOICES = [
    KeyChoice(SSH / "id_lab", "id_lab.pub (your SSH config offers this)"),
    KeyChoice(SSH / "id_a", "id_a.pub", note=NOTE),
    KeyChoice(SSH / "id_b", "id_b.pub", note=NOTE),
    KeyChoice(
        SSH / "id_ed25519_garden",
        "Create a new key: id_ed25519_garden",
        True,
        NOTE,
    ),
]
UNLISTED = (
    "Not listed: id_work and id_old, which your SSH config offers, have no "
    "valid .pub file."
)
HINT = " ↑↓ key  tab system  enter start  esc cancel "


def saved_app(tmp_path: Path) -> SSHWorkbenchApp:
    path = tmp_path / "machines.toml"
    text = format_machines((GARDEN,))
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text)


def variable(app: SSHWorkbenchApp, name: str) -> Color:
    return Color.parse(app.get_css_variables()[name])


async def open_picker(app, pilot, results: list) -> KeySetup:
    app.push_screen(KeySetup(GARDEN, CHOICES, None, UNLISTED), results.append)
    await wait_for(pilot, lambda: showing(app, KeySetup))
    await pilot.pause()
    return app.screen


async def show_note(screen: KeySetup, pilot) -> None:
    """Highlight the second choice, which has a note."""
    note = screen.query_one("#key-note", Static)
    await pilot.press("down")
    await wait_for(pilot, lambda: str(note.content) == NOTE)
    await pilot.pause()


async def test_a_blank_row_sits_above_each_section_label(tmp_path: Path) -> None:
    app = saved_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        screen = await open_picker(app, pilot, [])
        note = screen.query_one("#key-note", Static)
        key_label = screen.query(".key-label").first(Static)
        assert str(key_label.content) == "Key"
        assert str(note.content) == ""
        assert note.region.height == 1
        assert key_label.region.y == note.region.bottom
        await show_note(screen, pilot)
        rows = len(Content(NOTE).wrap(note.content_region.width))
        assert rows > 1
        assert note.region.height == rows + 1
        assert key_label.region.y == note.region.bottom
        unlisted = screen.query_one("#key-unlisted", Static)
        system_label = screen.query_one("#key-system-label", Static)
        assert system_label.has_class("key-label")
        assert system_label.region.y == unlisted.region.bottom + 1
        assert note.styles.color == variable(app, "warning")
        assert unlisted.styles.color == variable(app, "text-muted")


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_the_hint_row_is_the_last_row(
    tmp_path: Path, size: tuple[int, int]
) -> None:
    app = saved_app(tmp_path)
    async with app.run_test(size=size) as pilot:
        screen = await open_picker(app, pilot, [])
        frame = screen.query_one("#key-setup")
        hint = screen.query_one("#key-help", Static)
        assert hint.has_class("hint")
        assert hint.content.plain == HINT
        assert hint.region.height == 1
        assert hint.region.bottom == frame.region.bottom - 1
        await show_note(screen, pilot)
        assert hint.region.height == 1
        assert hint.region.bottom == frame.region.bottom - 1
        assert screen.query_one("#key-body").max_scroll_y == 0
        if size == (60, 20):
            assert frame.region.height == 20


async def test_a_small_terminal_scrolls_the_body_not_the_hint(tmp_path: Path) -> None:
    app = saved_app(tmp_path)
    async with app.run_test(size=(40, 16)) as pilot:
        screen = await open_picker(app, pilot, [])
        await show_note(screen, pilot)
        frame = screen.query_one("#key-setup")
        body = screen.query_one("#key-body")
        hint = screen.query_one("#key-help", Static)
        assert body.max_scroll_y > 0
        assert frame.region.contains_region(hint.region)
        await pilot.press("tab")
        await pilot.pause()
        await pilot.pause()
        system = screen.query_one("#key-system")
        assert screen.focused is system
        assert body.region.contains_region(system.region)


def ring(button: RadioButton) -> tuple[str, Color]:
    """The ring glyph a radio button draws and its color."""
    (segment,) = [
        segment for segment in button.render_line(0) if segment.text in ("●", "○")
    ]
    return segment.text, Color.from_rich_color(segment.style.color)


async def test_the_rings_show_the_target_by_shape(tmp_path: Path) -> None:
    app = saved_app(tmp_path)
    results: list[KeyPlan | None] = []
    async with app.run_test(size=(80, 24)) as pilot:
        screen = await open_picker(app, pilot, results)
        posix = screen.query_one("#system-posix", RadioButton)
        windows = screen.query_one("#system-windows", RadioButton)
        foreground = variable(app, "foreground")
        muted = variable(app, "text-muted")
        assert contrast(muted, variable(app, "panel")) >= 3
        assert ring(posix) == ("●", foreground)
        assert ring(windows) == ("○", muted)
        await pilot.press("tab", "down", "space")
        await pilot.pause()
        assert [posix.value, windows.value] == [False, True]
        assert ring(posix) == ("○", muted)
        assert ring(windows) == ("●", foreground)
        await pilot.press("enter")
        await wait_for(pilot, lambda: results)
    assert results == [KeyPlan(CHOICES[0], True)]


LONG_LABEL = (
    "Create a new key: "
    "id_ed25519_rack-machine-number-one-far-corner-of-the-second-fictional-room"
)


@pytest.mark.parametrize("size", [(80, 24), (60, 20), (40, 16)])
async def test_a_long_key_label_is_shown_whole(
    tmp_path: Path, size: tuple[int, int]
) -> None:
    app = saved_app(tmp_path)
    choices = [
        KeyChoice(SSH / "id_a", "id_a.pub"),
        KeyChoice(SSH / "id_ed25519_rack", LONG_LABEL, True),
    ]
    async with app.run_test(size=size) as pilot:
        app.push_screen(KeySetup(GARDEN, choices, None), [].append)
        await wait_for(pilot, lambda: showing(app, KeySetup))
        await pilot.pause()
        body = app.screen.query_one("#key-body")
        options = app.screen.query_one("#key-choices", OptionList)
        # The list is no wider than the body, so no cell of it is hidden.
        assert len(LONG_LABEL) > body.content_region.width
        assert body.region.contains_region(options.region)
        assert body.max_scroll_x == 0
        drawn = "".join(
            "".join(segment.text for segment in options.render_line(y)).strip()
            for y in range(options.size.height)
        )
        assert LONG_LABEL.replace(" ", "") in drawn.replace(" ", "")


async def test_the_highlighted_key_has_a_marker(tmp_path: Path) -> None:
    app = saved_app(tmp_path)
    results: list[KeyPlan | None] = []
    async with app.run_test(size=(80, 24)) as pilot:
        screen = await open_picker(app, pilot, results)
        options = screen.query_one("#key-choices", OptionList)

        def leads() -> list[str]:
            return [
                str(options.get_option_at_index(index).prompt)[0]
                for index in range(options.option_count)
            ]

        assert leads() == ["▌", " ", " ", " "]
        await pilot.press("down")
        await pilot.pause()
        assert leads() == [" ", "▌", " ", " "]
        prompt = options.get_option_at_index(1).prompt
        assert isinstance(prompt, Content)
        assert prompt.plain == "▌id_a.pub"
        assert [(span.start, span.end, span.style) for span in prompt.spans] == [
            (0, 1, "$primary")
        ]
        await pilot.press("enter")
        await wait_for(pilot, lambda: results)
    assert results == [KeyPlan(CHOICES[1], False)]
