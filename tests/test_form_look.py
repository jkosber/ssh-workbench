"""The machine form's look: one-row fields with labels beside them, error rows
only while there is an error, named buttons and a frame sized to the form.
Fictional files and SSH folders in tmp_path only."""

from pathlib import Path

import pytest
from support import contrast, showing, wait_for
from textual.color import Color
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioButton, Static, TextArea

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Link, Machine, format_machines, parse_machines
from ssh_workbench.forms import MachineForm

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

FULL = Machine(
    "studio-box",
    "Studio box",
    user="studio",
    addresses=("studio-box.example.com", "192.0.2.40"),
    port=2222,
    key="~/.ssh/id_ed25519_studio_box",
    export_alias=True,
    links=(
        Link("Dashboard", "https://192.0.2.40:8006"),
        Link("Status page", "https://studio-box.example.com/status"),
        Link(
            "Grafana",
            "https://grafana.example.com/d/fictional-studio-overview?orgId=1&refresh=30s",
        ),
    ),
)
GARDEN = Machine("garden", "Garden", alias="garden-host")
COMMENTED = "# a note added elsewhere\n" + format_machines((FULL, GARDEN))
# Each label, in order, and the widget on its row.
LABELS = {
    "id": "#form-id",
    "name": "#form-name",
    "connection": "#form-kind",
    "alias": "#form-alias",
    "addresses": "#form-addresses",
    "user": "#form-user",
    "port": "#form-port",
    "key": "#form-key",
    "export": "#form-export_alias",
    "links": "#form-links",
}
EDIT_LABELS = [
    "id",
    "name",
    "connection",
    "addresses",
    "user",
    "port",
    "key",
    "export",
    "links",
]
PLACEHOLDERS = {
    "#form-addresses": "online one is used, else the first",
    "#form-user": "optional",
    "#form-port": "optional",
    "#form-key": "path of the private key, optional",
    "#form-links": "one per line: the name, then the URL",
}


def saved_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    text: str | None = None,
) -> tuple[SSHWorkbenchApp, Path]:
    """A saved file holding FULL and an alias machine, and an SSH folder whose
    config names three hosts."""
    folder = tmp_path / "fictional-ssh"
    folder.mkdir(parents=True)
    (folder / "config").write_text(
        "Host garden-host\nHost lab-host\nHost web-host\n", encoding="utf-8"
    )
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines((FULL, GARDEN)) if text is None else text
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text), path


def variable(app: SSHWorkbenchApp, name: str) -> Color:
    return Color.parse(app.get_css_variables()[name])


async def open_form(app, pilot, state: str = "add") -> MachineForm:
    """The form for "add", "direct" (add switched to direct) or "edit" (FULL)."""
    await pilot.press("e" if state == "edit" else "a")
    await wait_for(pilot, lambda: showing(app, MachineForm))
    form = app.screen
    if state == "edit":
        assert form.query_one("#form-id", Input).value == FULL.id
    if state == "direct":
        form.query_one("#kind-direct", RadioButton).value = True
    await pilot.pause()
    await pilot.pause()
    return form


def shown(widget: Widget) -> bool:
    """The widget and every container up to its screen are displayed."""
    node = widget
    while isinstance(node, Widget) and node is not widget.screen:
        if not node.display:
            return False
        node = node.parent
    return True


def labels(form: MachineForm) -> list[Static]:
    return [
        label for label in form.query(".form-label").results(Static) if shown(label)
    ]


def frame(form: MachineForm) -> Widget:
    return form.query_one("#machine-form")


def last_content_row(form: MachineForm) -> int:
    return frame(form).region.bottom - 2


def mark(widget: Widget, glyph: str):
    """The drawn segment of a radio or checkbox mark."""
    (segment,) = [s for s in widget.render_line(0) if glyph in s.text]
    return segment


@pytest.mark.parametrize(
    ("size", "heights"),
    [
        ((80, 24), {"add": 13, "direct": 16, "edit": 16}),
        ((60, 20), {"add": 14, "direct": 16, "edit": 16}),
    ],
)
@pytest.mark.parametrize("state", ["add", "direct", "edit"])
async def test_the_form_fits_without_scrolling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int],
    heights: dict[str, int],
    state: str,
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=size) as pilot:
        form = await open_form(app, pilot, state)
        box = frame(form)
        assert form.query_one("#form-fields").max_scroll_y == 0
        assert form.region.contains_region(box.region)
        assert box.region.height <= int(size[1] * 0.9)
        assert box.region.height == heights[state]
        buttons = form.query_one("#form-buttons")
        assert buttons.region.height == 1
        assert buttons.region.bottom == box.region.bottom - 1
        assert form.query_one("#form-id").region.y == box.region.y + 1


@pytest.mark.parametrize(("size", "name"), [((80, 24), 56), ((60, 20), 38)])
async def test_labels_sit_beside_their_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int], name: int
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=size) as pilot:
        form = await open_form(app, pilot, "edit")
        muted = variable(app, "text-muted")
        rows = labels(form)
        assert [str(label.content) for label in rows] == EDIT_LABELS
        for label in rows:
            text = str(label.content)
            assert label.region.width == 12, text
            assert label.styles.color == muted, text
            assert not any(
                segment.style and segment.style.bold for segment in label.render_line(0)
            ), text
            assert label.region.y == form.query_one(LABELS[text]).region.y, text
        for selector in ("#form-id", "#form-user", "#form-port"):
            assert form.query_one(selector).region.width == 32, selector
        assert form.query_one("#form-name").region.width == name
        links = form.query_one("#form-links", TextArea)
        assert links.region.height == 5
        assert links.styles.scrollbar_size_vertical == 1


async def test_labels_stack_under_60_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def above(form: MachineForm) -> bool:
        return all(
            label.region.y == form.query_one(LABELS[str(label.content)]).region.y - 1
            for label in labels(form)
        )

    def beside(form: MachineForm) -> bool:
        return all(
            label.region.y == form.query_one(LABELS[str(label.content)]).region.y
            for label in labels(form)
        )

    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(59, 20)) as pilot:
        form = await open_form(app, pilot, "edit")
        assert [str(label.content) for label in labels(form)] == EDIT_LABELS
        assert above(form)
        alias = form.query_one("#kind-alias").region
        assert form.query_one("#kind-direct").region.y == alias.y + 1
    app, _ = saved_app(tmp_path / "again", monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "add")
        assert app.focused is form.query_one("#form-id")
        await pilot.press(*"studio-9")
        assert beside(form)
        await pilot.resize_terminal(59, 20)
        await pilot.pause()
        await pilot.pause()
        assert above(form)
        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        await pilot.pause()
        assert beside(form)
        assert form.query_one("#form-id", Input).value == "studio-9"


async def test_error_rows_show_only_with_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "add")
        errors = list(form.query(".form-error").results(Static))
        assert len(errors) == 9
        for error in errors:
            assert error.display is False, error.id
            assert error.region.height == 0, error.id
        await pilot.press("ctrl+s")
        await pilot.pause()
        error = form.query_one("#form-id-error", Static)
        assert error.display is True
        assert error.region.height == 1
        assert error.region.x == form.query_one("#form-id").region.x
        others = [other for other in errors if other is not error]
        assert len(others) == 8
        for other in others:
            assert other.region.height == 0, other.id
        await pilot.press(*"web-1")
        await pilot.pause()
        assert error.display is False
        assert error.region.height == 0


async def test_the_message_row_shows_only_with_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch, COMMENTED)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "add")
        assert form.query_one("#form-message").region.height == 0
        form.query_one("#form-id", Input).value = "web"
        form.query_one("#form-name", Input).value = "Web"
        form.query_one("#form-alias", Input).value = "web-host"
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
        await pilot.pause()
        assert "Press Ctrl+S again to save." in str(
            form.query_one("#form-message", Static).content
        )
        assert form.query_one("#form-message").region.height >= 1
        buttons = form.query_one("#form-buttons")
        assert buttons.region.bottom - 1 == last_content_row(form)


async def test_a_long_message_keeps_the_buttons_on_screen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(60, 20)) as pilot:
        form = await open_form(app, pilot, "edit")
        form.query_one("#form-message", Static).update("x " * 100)
        await pilot.pause()
        await pilot.pause()
        box = frame(form)
        assert form.query_one("#form-message").region.height >= 4
        buttons = form.query_one("#form-buttons")
        assert box.region.contains_region(buttons.region)
        assert buttons.region.bottom - 1 == last_content_row(form)
        assert box.region.height <= 18
        assert form.query_one("#form-fields").max_scroll_y > 0


async def test_an_error_above_the_focused_field_keeps_it_in_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(40, 16)) as pilot:
        form = await open_form(app, pilot, "edit")
        user = form.query_one("#form-user", Input)
        user.focus()
        await pilot.pause()
        await pilot.pause()
        form.query_one("#form-name", Input).value = ""
        await pilot.pause()
        await pilot.pause()
        assert form.query_one("#form-name-error", Static).display is True
        assert app.focused is user
        assert form.query_one("#form-fields").region.contains_region(user.region)


@pytest.mark.parametrize("size", [(40, 16), (59, 20)])
async def test_a_failed_save_shows_the_field_it_focuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=size) as pilot:
        form = await open_form(app, pilot)
        form.query_one("#form-links", TextArea).focus()
        await pilot.pause()
        await pilot.pause()
        await pilot.press("ctrl+s")
        identifier = form.query_one("#form-id", Input)
        await wait_for(pilot, lambda: app.focused is identifier)
        for _ in range(6):
            await pilot.pause()
        assert form.query_one("#form-id-error", Static).display is True
        assert app.focused is identifier
        assert form.query_one("#form-fields").region.contains_region(identifier.region)


async def test_narrowing_keeps_the_focused_field_in_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "edit")
        links = form.query_one("#form-links", TextArea)
        links.focus()
        await pilot.pause()
        await pilot.pause()
        await pilot.resize_terminal(59, 20)
        for _ in range(6):
            await pilot.pause()
        assert app.focused is links
        assert form.query_one("#form-fields").region.contains_region(links.region)


@pytest.mark.parametrize(
    ("size", "alias", "direct"), [((160, 50), 13, 16), ((60, 20), 14, 16)]
)
async def test_the_frame_follows_the_connection_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int],
    alias: int,
    direct: int,
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=size) as pilot:
        form = await open_form(app, pilot, "add")
        box = frame(form)
        fields = form.query_one("#form-fields")
        buttons = form.query_one("#form-buttons")
        assert box.region.height == alias
        for selector, height in (("#kind-direct", direct), ("#kind-alias", alias)):
            form.query_one(selector, RadioButton).value = True
            await pilot.pause()
            await pilot.pause()
            assert box.region.height == height, selector
            assert buttons.region.bottom - 1 == last_content_row(form), selector
            assert fields.max_scroll_y == 0, selector


async def test_the_focused_field_has_a_bar_and_its_text_stays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "edit")
        primary = variable(app, "primary")
        for selector in (
            "#form-name",
            "#form-kind",
            "#form-export_alias",
            "#form-links",
        ):
            widget = form.query_one(selector)
            assert widget.styles.border_left[0] == "", selector
            before = widget.content_region.x
            widget.focus()
            await pilot.pause()
            await pilot.pause()
            assert app.focused is widget, selector
            assert widget.styles.border_left == ("outer", primary), selector
            assert widget.content_region.x == before, selector


async def test_the_buttons_name_their_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, path = saved_app(tmp_path, monkeypatch)
    before = path.read_bytes()
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "add")
        save = form.query_one("#form-save", Button)
        cancel = form.query_one("#form-cancel", Button)
        assert save.label.plain == "^s save"
        assert cancel.label.plain == "esc cancel"
        assert save.region.height == 1 and cancel.region.height == 1
        assert save.region.y == cancel.region.y
        assert save.region.right <= cancel.region.x
        primary = variable(app, "primary")
        assert save.styles.background == primary
        assert contrast(variable(app, "background"), primary) >= 4.5
        await pilot.click("#form-cancel")
        await wait_for(pilot, lambda: len(app.screen_stack) == 1)
        assert path.read_bytes() == before
    app, path = saved_app(tmp_path / "again", monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "add")
        form.query_one("#form-id", Input).value = "web"
        form.query_one("#form-name", Input).value = "Web"
        form.query_one("#form-alias", Input).value = "web-host"
        await pilot.pause()
        form.query_one("#form-save", Button).focus()
        await pilot.pause()
        await pilot.press("enter")
        await wait_for(pilot, lambda: len(app.screen_stack) == 1)
        await wait_for(
            pilot,
            lambda: (
                [m.id for m in parse_machines(path.read_text(encoding="utf-8"))]
                == ["studio-box", "garden", "web"]
            ),
        )


async def test_the_form_marks_change_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "add")
        muted = variable(app, "text-muted").rgb
        foreground = variable(app, "foreground").rgb
        alias = form.query_one("#kind-alias", RadioButton)
        direct = form.query_one("#kind-direct", RadioButton)
        assert mark(alias, "●").style.color.triplet == foreground
        assert mark(direct, "○").style.color.triplet == muted
        direct.value = True
        await pilot.pause()
        await pilot.pause()
        assert [alias.value, direct.value] == [False, True]
        assert mark(alias, "○").style.color.triplet == muted
        assert mark(direct, "●").style.color.triplet == foreground
        box = form.query_one("#form-export_alias", Checkbox)
        assert mark(box, "·").style.color.triplet == muted
        box.value = True
        await pilot.pause()
        await pilot.pause()
        assert mark(box, "X").style.color.triplet == foreground


async def test_placeholders_explain_empty_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        form = await open_form(app, pilot, "direct")
        for selector, text in PLACEHOLDERS.items():
            placeholder = str(form.query_one(selector).placeholder)
            assert placeholder == text, selector
            # The 60x20 field less its padding.
            assert len(placeholder) <= 36, selector


async def test_tab_order_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _ = saved_app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        for state, order in (
            (
                "add",
                [
                    "form-name",
                    "form-kind",
                    "form-alias",
                    "form-links",
                    "form-save",
                    "form-cancel",
                    "form-fields",
                ],
            ),
            (
                "direct",
                [
                    "form-name",
                    "form-kind",
                    "form-addresses",
                    "form-user",
                    "form-port",
                    "form-key",
                    "form-export_alias",
                    "form-links",
                    "form-save",
                    "form-cancel",
                    "form-fields",
                ],
            ),
        ):
            form = await open_form(app, pilot, state)
            form.query_one("#form-id").focus()
            await pilot.pause()
            visited = []
            for _ in order:
                await pilot.press("tab")
                visited.append(app.focused.id if app.focused else None)
            assert visited == order, state
            await pilot.press("escape")
            await wait_for(pilot, lambda: len(app.screen_stack) == 1)
