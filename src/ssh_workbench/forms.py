"""The machine form, the delete confirmation and the key-setup picker.

The form checks a machine with `config.validate_machine`, the loader's own rules,
and shows the first problem under its field. Saving is the app's job: the form
hands over a valid machine and shows any problem the save reports.
"""

import re
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.visual import VisualType
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    OptionList,
    RadioButton,
    RadioSet,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option

from ssh_workbench.config import ConfigError, Machine, validate_machine
from ssh_workbench.display import display_text
from ssh_workbench.exports import BACKUP_NAME, INCLUDE_LINE

FIELDS = (
    "id",
    "name",
    "alias",
    "addresses",
    "user",
    "port",
    "key",
    "export_alias",
    "links",
)
_LOCATION = re.compile(r"machine(?:\.(\w+)(?:\[(\d+)\])?(?:\.(\w+))?)?")


class WorkbenchModal[T](ModalScreen[T]):
    """The base of every modal: a near-solid backdrop and a frame sized to its
    content, at most 90% of the screen and, from 80 columns, 72 cells."""

    # A screen's own breakpoints replace the app's horizontal classes for it.
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (60, "-normal"), (80, "-large")]
    DEFAULT_CSS = """
    WorkbenchModal {
        align: center middle;
        background: $background 88%;
    }
    WorkbenchModal .frame {
        width: auto;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        border: round $primary;
        border-title-color: $primary;
        border-title-style: bold;
        background: $surface;
        padding: 0 1;
    }
    /* A cell cap does not clamp to the screen, so it applies only from 80. */
    WorkbenchModal.-large .frame {
        max-width: 72;
    }
    /* An auto-width frame needs auto-width text, or the text gets no cells. */
    WorkbenchModal .frame > Static {
        width: auto;
        max-width: 100%;
    }
    /* A docked hint row covers its whole row, or scrolled text shows beside it. */
    WorkbenchModal .frame > .hint {
        width: 100%;
    }
    """


def hint_row(pairs: Sequence[tuple[str, str]]) -> Content:
    """A row of keys in the footer's style: each key, a space and its label."""
    parts: list[str | tuple[str, str]] = [" "]
    for index, (key, label) in enumerate(pairs):
        if index:
            parts.append("  ")
        parts += [
            (key, "$footer-key-foreground bold"),
            " ",
            (label, "$footer-description-foreground"),
        ]
    parts.append(" ")
    return Content.assemble(*parts)


class Ring(RadioButton):
    """A radio button whose mark changes shape: filled when selected."""

    @property
    def BUTTON_INNER(self) -> str:
        return "●" if self.value else "○"


class Box(Checkbox):
    """A checkbox whose mark changes shape: X when checked."""

    @property
    def BUTTON_INNER(self) -> str:
        return "X" if self.value else "·"


def marked(label: str | Content, on: bool) -> Content:
    """An option prompt with a lead cell: the selection marker when `on`."""
    return Content.assemble(("▌" if on else " ", "$primary"), label)


class FormMessage(Static):
    """The form's message: takes a row only while it has text."""

    def update(self, content: VisualType = "", *, layout: bool = True) -> None:
        super().update(content, layout=layout)
        self.display = bool(str(content))
        if self.is_mounted and isinstance(self.screen, MachineForm):
            self.screen._cap_fields()


class MachineForm(WorkbenchModal[None]):
    """Add a machine, or edit one, without writing anything until it is valid."""

    # Priority bindings keep keys typed into the fields from triggering app
    # actions, and handle Ctrl+S and Escape in the order they arrive.
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        # A modal screen hides the app's own Ctrl+Q.
        Binding("ctrl+q", "app.quit", "Quit", show=False, priority=True),
    ]
    DEFAULT_CSS = """
    #machine-form {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 90%;
        border: round $primary;
        border-title-color: $primary;
        border-title-style: bold;
        background: $surface;
        padding: 0 1;
    }
    /* Its cap is set from Python: see _cap_fields. */
    #form-fields {
        height: auto;
        scrollbar-size-vertical: 1;
    }
    /* One field: the label beside its cell from 60 columns, above it below. */
    .form-field {
        layout: horizontal;
        height: auto;
    }
    MachineForm.-narrow .form-field {
        layout: vertical;
    }
    .form-label {
        width: 12;
        height: 1;
        padding-right: 1;
        color: $text-muted;
    }
    MachineForm.-narrow .form-label {
        width: 1fr;
    }
    /* An input's own width: 100% beside the label would overflow the row. */
    .form-cell {
        width: 1fr;
        height: auto;
    }
    /* The focused field gets a left bar; the padding it replaces keeps the
       text in place. Compact widgets set border: none !important. */
    #form-fields Input {
        background: $panel;
        padding: 0 1;
    }
    #form-fields Input:focus {
        border-left: outer $primary !important;
        padding: 0 1 0 0;
    }
    /* Textual's placeholder, suggestion and selection text are under 4.5:1. */
    #form-fields Input > .input--placeholder,
    #form-fields Input > .input--suggestion {
        color: $text-muted;
    }
    #form-fields Input > .input--selection {
        color: $block-cursor-foreground;
    }
    #form-id, #form-user, #form-port {
        width: 32;
        max-width: 100%;
    }
    /* Shown only while there is an error; see _validate. */
    .form-error {
        color: $error;
        height: auto;
        display: none;
    }
    #form-hosts {
        color: $text-muted;
    }
    /* A Vertical defaults to 1fr, which a scrolling form squeezes to one row. */
    #alias-fields, #direct-fields {
        height: auto;
    }
    /* Side by side the two choices need exactly the 38 cells of a 60-column
       frame, so no margin between them; under 60 they stack. */
    #form-kind {
        layout: horizontal;
        width: 1fr;
        height: auto;
        padding-left: 1;
    }
    #form-kind > RadioButton {
        width: auto;
    }
    MachineForm.-narrow #form-kind {
        layout: vertical;
    }
    #form-kind:focus, #form-export_alias:focus, #form-links:focus {
        border-left: outer $primary !important;
        padding-left: 0;
    }
    #form-export_alias {
        padding-left: 1;
        max-width: 100%;
    }
    #form-links {
        height: 5;
        background: $panel;
        scrollbar-size-vertical: 1;
    }
    #form-message {
        height: auto;
        display: none;
    }
    /* The button row is the form's hint row: each button names its key. */
    #form-buttons {
        height: 1;
    }
    #form-buttons Button {
        min-width: 0;
        margin-right: 2;
    }
    #form-save {
        background: $primary;
        color: $background;
    }
    #form-save:hover {
        background: $primary-darken-1;
    }
    #form-cancel {
        background: $surface;
        color: $foreground;
    }
    /* Marks differ by shape; the selected one is not green, which means Online. */
    #form-kind > RadioButton > .toggle--button,
    #form-export_alias > .toggle--button {
        color: $text-muted;
    }
    #form-kind > RadioButton.-on > .toggle--button,
    #form-export_alias.-on > .toggle--button {
        color: $foreground;
    }
    """

    def __init__(
        self,
        machine: Machine | None,
        ids_in_use: Callable[[], Collection[str]],
        host_names: Sequence[str],
        save: Callable[[Machine], str | None],
        rewrite_warning: Callable[[], str | None],
    ) -> None:
        super().__init__()
        self.machine = machine
        self.ids_in_use = ids_in_use
        self.host_names = tuple(host_names)
        self.save = save
        self.rewrite_warning = rewrite_warning
        self._initial: dict[str, str] = {}
        self._touched: set[str] = set()
        self._attempted = False
        self._armed = False
        self._answered = False

    def compose(self) -> ComposeResult:
        machine = self.machine
        direct = machine is not None and machine.alias is None
        values = {field: "" for field in FIELDS}
        if machine is not None:
            values |= {
                "id": machine.id,
                "name": machine.name,
                "alias": machine.alias or "",
                "addresses": ", ".join(machine.addresses),
                "user": machine.user or "",
                "port": str(machine.port) if machine.port is not None else "",
                "key": machine.key or "",
                "export_alias": "true" if machine.export_alias else "",
                "links": "\n".join(f"{link.name} {link.url}" for link in machine.links),
            }
        self._initial = values
        with Vertical(id="machine-form") as form:
            form.border_title = "Edit machine" if machine else "Add machine"
            with VerticalScroll(id="form-fields"):
                yield _field(
                    "id", "id", Input(values["id"], id="form-id", compact=True)
                )
                yield _field(
                    "name", "name", Input(values["name"], id="form-name", compact=True)
                )
                yield Horizontal(
                    Static("connection", classes="form-label", markup=False),
                    RadioSet(
                        Ring("SSH alias", value=not direct, id="kind-alias"),
                        Ring("Direct (addresses)", value=direct, id="kind-direct"),
                        id="form-kind",
                        compact=True,
                    ),
                    classes="form-field",
                    id="field-kind",
                )
                with Vertical(id="alias-fields"):
                    alias = Input(
                        values["alias"],
                        id="form-alias",
                        compact=True,
                        suggester=SuggestFromList(
                            self.host_names, case_sensitive=False
                        ),
                    )
                    yield _field(
                        "alias",
                        "alias",
                        alias,
                        Static(self._hosts_text(), id="form-hosts", markup=False),
                    )
                with Vertical(id="direct-fields"):
                    for field, placeholder in (
                        ("addresses", "online one is used, else the first"),
                        ("user", "optional"),
                        ("port", "optional"),
                        ("key", "path of the private key, optional"),
                    ):
                        yield _field(
                            field,
                            field,
                            Input(
                                values[field],
                                id=f"form-{field}",
                                placeholder=placeholder,
                                compact=True,
                            ),
                        )
                    yield _field(
                        "export_alias",
                        "export",
                        Box(
                            "ssh <ID> works in any terminal",
                            values["export_alias"] == "true",
                            id="form-export_alias",
                            compact=True,
                        ),
                    )
                yield _field(
                    "links",
                    "links",
                    TextArea(
                        values["links"],
                        id="form-links",
                        tab_behavior="focus",
                        compact=True,
                        placeholder="one per line: the name, then the URL",
                    ),
                )
            yield FormMessage("", id="form-message", markup=False)
            with Horizontal(id="form-buttons"):
                yield Button(
                    Content("^s save"), id="form-save", variant="primary", compact=True
                )
                yield Button(Content("esc cancel"), id="form-cancel", compact=True)

    def on_mount(self) -> None:
        self._show_kind()
        self._cap_fields()
        self.query_one("#form-id", Input).focus()
        self.watch(
            self.query_one("#form-fields"),
            "virtual_size",
            self._fields_changed,
            init=False,
        )

    def _fields_changed(self) -> None:
        """Keep the focused field in view when the fields change height. An
        error row's layout can reach the screen after the scroll _validate
        queues has run, so scroll again from the new layout."""
        self.call_after_refresh(self._show_focused_field)

    def on_resize(self, event: events.Resize) -> None:
        self._cap_fields()
        # Stacked labels and a lower cap can leave the focused field below it.
        self.call_after_refresh(self._show_focused_field)

    def _cap_fields(self) -> None:
        """Cap the fields' scroll area, so a frame at most 90% of the screen
        keeps its border, the message and the button row. CSS alone cannot:
        the same pattern as MachinePanes.cap_list."""
        message = self.query_one("#form-message", FormMessage)
        rows = 0
        if message.display:
            width = self.query_one("#machine-form").size.width or self.size.width
            rows = message.get_content_height(self.size, self.size, width)
        self.query_one("#form-fields").styles.max_height = max(
            1, int(self.size.height * 0.9) - 2 - 1 - rows
        )

    def _hosts_text(self) -> str:
        if not self.host_names:
            return "No Host names found in your SSH config. Type any alias."
        return "In your SSH config: " + ", ".join(
            display_text(name) for name in self.host_names
        )

    def _direct(self) -> bool:
        return self.query_one("#kind-direct", RadioButton).value

    def _show_kind(self) -> None:
        direct = self._direct()
        self.query_one("#alias-fields").display = not direct
        self.query_one("#direct-fields").display = direct

    def on_input_changed(self, event: Input.Changed) -> None:
        self._changed((event.input.id or "").removeprefix("form-"), event.value)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._changed("links", event.text_area.text)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self._changed("export_alias", "true" if event.value else "")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self._show_kind()
        self._validate()

    def _changed(self, field: str, value: str) -> None:
        if value != self._initial.get(field, ""):
            self._touched.add(field)
        self._validate()

    def _validate(self) -> Machine | None:
        machine, field, problem = self._check()
        moved = False
        for name in FIELDS:
            shown = name == field and (self._attempted or name in self._touched)
            error = self.query_one(f"#form-{name}-error", Static)
            error.update(problem if shown else "")
            visible = shown and bool(problem)
            moved |= error.display != visible
            error.display = visible
        if field is None and problem:
            self.query_one("#form-message", Static).update(problem)
        # A row shown or hidden above the focused field moves it out of view.
        if moved:
            self.call_after_refresh(self._show_focused_field)
        return machine

    def _show_focused_field(self) -> None:
        """Scroll the focused field's row into view. The focus is read when
        this runs, not when it is scheduled: a failed save moves the focus to
        the field with the error after _validate has returned."""
        if self.focused is None:
            return
        for node in self.focused.ancestors_with_self:
            if isinstance(node, Widget) and node.has_class("form-field"):
                node.scroll_visible(animate=False)
                break

    def _check(self) -> tuple[Machine | None, str | None, str]:
        table, line_numbers = self._table()
        try:
            machine = validate_machine(table, "machine")
        except ConfigError as error:
            return None, *_place(str(error), line_numbers)
        if machine.id in self.ids_in_use():
            return None, "id", "already used by another machine"
        # The Include line comes first, so SSH would pick the exported entry.
        if machine.export_alias and machine.id in self.host_names:
            return (
                None,
                "export_alias",
                f"your SSH config already has Host {machine.id}; SSH would use the "
                "exported entry instead",
            )
        return machine, None, ""

    def _table(self) -> tuple[dict[str, object], list[int]]:
        def value(field: str) -> str:
            return self.query_one(f"#form-{field}", Input).value

        table: dict[str, object] = {"id": value("id").strip(), "name": value("name")}
        if self._direct():
            table["addresses"] = [
                address
                for address in re.split(r"[\s,]+", value("addresses"))
                if address
            ]
            for field in ("user", "key"):
                if value(field).strip():
                    table[field] = value(field).strip()
            port = value("port").strip()
            if port:
                table["port"] = int(port) if re.fullmatch(r"[0-9]{1,5}", port) else port
            if self.query_one("#form-export_alias", Checkbox).value:
                table["export_alias"] = True
        else:
            table["alias"] = value("alias").strip()
        links: list[dict[str, str]] = []
        line_numbers = []
        text = self.query_one("#form-links", TextArea).text
        for number, line in enumerate(text.splitlines(), start=1):
            # URLs cannot contain spaces, so the last word is the URL.
            parts = line.strip().rsplit(None, 1)
            if parts:
                links.append(
                    {"name": parts[0], "url": parts[1]}
                    if len(parts) == 2
                    else {"name": parts[0]}
                )
                line_numbers.append(number)
        if links:
            table["links"] = links
        return table, line_numbers

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "form-save":
            self.action_save()
        else:
            self.action_cancel()

    def action_save(self) -> None:
        if self._answered:
            return
        self._attempted = True
        machine, field, _ = self._check()
        self._validate()
        if machine is None:
            if field is not None:
                self.query_one(f"#form-{field}").focus()
            return
        # Asked at each save: an outside change can bring comments with it.
        warning = self.rewrite_warning()
        if warning and not self._armed:
            self._armed = True
            self.query_one("#form-message", Static).update(warning)
            return
        problem = self.save(machine)
        if problem is None:
            self._answered = True
            self.dismiss(None)
        else:
            self._armed = False
            self.query_one("#form-message", Static).update(problem)

    def action_cancel(self) -> None:
        if not self._answered:
            self._answered = True
            self.dismiss(None)


class ConfirmDelete(WorkbenchModal[bool]):
    """Ask before deleting; Y deletes, N or Escape keeps the machine."""

    BINDINGS = [
        Binding("y,Y", "answer(True)", "Delete", priority=True),
        Binding("n,N", "answer(False)", "Keep", priority=True),
        Binding("escape", "answer(False)", "Keep", priority=True),
        Binding("ctrl+q", "app.quit", "Quit", show=False, priority=True),
    ]
    DEFAULT_CSS = """
    /* The border title needs the frame at least its width + 6. The text
       may scroll under the docked hint row on a very small screen. */
    #confirm-delete {
        border: round $error;
        border-title-color: $error;
        min-width: 20;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
    }
    /* A docked row's margin is not painted; padding gives the blank row. */
    #confirm-delete > .hint {
        dock: bottom;
        padding-top: 1;
    }
    """

    def __init__(self, machine: Machine, rewrite_warning: str | None) -> None:
        super().__init__()
        self.machine = machine
        self.rewrite_warning = rewrite_warning
        self._answered = False

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-delete", classes="frame") as box:
            box.border_title = "Delete machine"
            yield Static(
                f"Delete {display_text(self.machine.name)} "
                f"({display_text(self.machine.id)})?",
                markup=False,
            )
            if self.rewrite_warning:
                yield Static(self.rewrite_warning, markup=False)
            yield Static(hint_row([("y", "delete"), ("n", "keep")]), classes="hint")

    def action_answer(self, confirmed: bool) -> None:
        if not self._answered:
            self._answered = True
            self.dismiss(confirmed)


class ConfirmInclude(WorkbenchModal[bool]):
    """Ask before adding the one Include line; Y adds it, N or Escape does not."""

    BINDINGS = [
        Binding("y,Y", "answer(True)", "Add", priority=True),
        Binding("n,N", "answer(False)", "Not now", priority=True),
        Binding("escape", "answer(False)", "Not now", priority=True),
        Binding("ctrl+q", "app.quit", "Quit", show=False, priority=True),
    ]
    DEFAULT_CSS = """
    /* The border title needs the frame at least its width + 6. The text
       may scroll under the docked hint row on a very small screen. */
    #confirm-include {
        min-width: 22;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
    }
    /* A docked row's margin is not painted; padding gives the blank row. */
    #confirm-include > .hint {
        dock: bottom;
        padding-top: 1;
    }
    #include-line {
        text-style: bold;
        margin: 1 0;
    }
    """

    def __init__(self, config: Path, exists: bool) -> None:
        super().__init__()
        self.config = config
        self.exists = exists
        self._answered = False

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-include", classes="frame") as box:
            box.border_title = "Exported aliases"
            yield Static(
                "SSH sees exported aliases once your SSH config includes "
                "Workbench's file. Add this line at the top of "
                f"{display_text(str(self.config))}?",
                markup=False,
            )
            yield Static(INCLUDE_LINE, id="include-line", markup=False)
            yield Static(
                f"Workbench first keeps a copy as {BACKUP_NAME} and changes no "
                "other line."
                if self.exists
                else "The file doesn't exist yet; Workbench creates it with this line.",
                markup=False,
            )
            yield Static(hint_row([("y", "add"), ("n", "not now")]), classes="hint")

    def action_answer(self, confirmed: bool) -> None:
        if not self._answered:
            self._answered = True
            self.dismiss(confirmed)


@dataclass(frozen=True)
class KeyChoice:
    """A key the picker offers; `private` names the key file, which is never read."""

    private: Path
    label: str
    create: bool = False
    # Shown while the choice is highlighted.
    note: str | None = None
    # Added to the result when key-only login fails, or passes perhaps with
    # another key.
    hint: str | None = None
    # Added to the result only when key-only login fails.
    failed_hint: str | None = None


@dataclass(frozen=True)
class KeyPlan:
    choice: KeyChoice
    windows: bool


class KeySetup(WorkbenchModal[KeyPlan | None]):
    """Pick a key and the target system; Enter starts, Escape cancels."""

    BINDINGS = [
        Binding("enter", "start", "Start", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+q", "app.quit", "Quit", show=False, priority=True),
    ]
    DEFAULT_CSS = """
    #key-setup {
        /* The whole height before it scrolls: at 60x20 a note and a
           "Not listed" line need every row. */
        max-height: 100%;
        min-width: 15;
    }
    /* The body scrolls inside the frame; the hint row stays under it. */
    #key-setup > .hint {
        dock: bottom;
    }
    #key-body {
        height: auto;
        max-height: 100%;
        scrollbar-size-vertical: 1;
    }
    #key-body > Static {
        width: auto;
        max-width: 100%;
    }
    /* Borderless lists keep the picker within 60x20 with a wrapped note. */
    /* As wide as the body less its scrollbar: a label longer than that wraps
       and stays whole, and the body never scrolls sideways. */
    #key-choices, #key-system {
        border: none;
        padding: 0;
        height: auto;
        width: 1fr;
    }
    #key-choices {
        max-height: 8;
    }
    .key-label {
        text-style: bold;
    }
    #key-system-label {
        margin-top: 1;
    }
    /* The note's last row, or the empty note itself, is the blank row
       above "Key". */
    #key-note {
        height: auto;
        color: $warning;
        padding-bottom: 1;
    }
    #key-note.-empty {
        height: 1;
        padding-bottom: 0;
    }
    #key-unlisted {
        height: auto;
        color: $text-muted;
    }
    /* An id selector beats Textual's own ring colors. */
    #key-system > RadioButton > .toggle--button {
        color: $text-muted;
    }
    #key-system > RadioButton.-on > .toggle--button {
        color: $foreground;
    }
    """

    def __init__(
        self,
        machine: Machine,
        choices: Sequence[KeyChoice],
        warning: str | None,
        unlisted: str | None = None,
    ) -> None:
        super().__init__()
        self.machine = machine
        self.choices = tuple(choices)
        # The rewrite warning, shown unless a choice has its own note.
        self.warning = warning
        # Names the configured keys the list leaves out, if any.
        self.unlisted = unlisted
        self._answered = False
        # The option that draws the selection marker.
        self._marked = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="key-setup", classes="frame") as box:
            box.border_title = "Key login"
            with VerticalScroll(id="key-body"):
                yield Static(
                    f"Set up key login for {display_text(self.machine.name)} "
                    f"({display_text(self.machine.id)}).",
                    markup=False,
                )
                # Above the lists, so a small terminal still shows it.
                yield Static("", id="key-note", markup=False)
                yield Static("Key", classes="key-label", markup=False)
                # on_mount highlights the first choice.
                yield OptionList(
                    *(
                        Option(self._prompt(index, index == 0))
                        for index in range(len(self.choices))
                    ),
                    id="key-choices",
                )
                if self.unlisted is not None:
                    yield Static(
                        display_text(self.unlisted), id="key-unlisted", markup=False
                    )
                yield Static(
                    "Target system",
                    id="key-system-label",
                    classes="key-label",
                    markup=False,
                )
                with RadioSet(id="key-system"):
                    yield Ring(
                        "Linux, macOS or other POSIX", value=True, id="system-posix"
                    )
                    yield Ring("Windows (OpenSSH Server)", id="system-windows")
            yield Static(
                hint_row(
                    [
                        ("↑↓", "key"),
                        ("tab", "system"),
                        ("enter", "start"),
                        ("esc", "cancel"),
                    ]
                ),
                id="key-help",
                classes="hint",
            )

    def _prompt(self, index: int, on: bool) -> Content:
        return marked(display_text(self.choices[index].label), on)

    def on_mount(self) -> None:
        options = self.query_one(OptionList)
        options.highlighted = 0
        options.focus()
        self._show_note()
        self.watch(
            self.query_one("#key-body"), "virtual_size", self._body_changed, init=False
        )

    def _body_changed(self) -> None:
        """Keep the focused list in view when the body's content changes
        height: a note that grows above the keys pushes them down a body that
        scrolls. Run from the new layout, not from the highlight, which comes
        before it."""
        if self.focused is not None:
            self.call_after_refresh(self.focused.scroll_visible, animate=False)

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        # Move the marker: redraw the old and the new highlighted prompt.
        new = event.option_index
        if new != self._marked:
            for index in (self._marked, new):
                event.option_list.replace_option_prompt_at_index(
                    index, self._prompt(index, index == new)
                )
            self._marked = new
        self._show_note()

    def _show_note(self) -> None:
        index = self.query_one(OptionList).highlighted
        choice = self.choices[index] if index is not None else None
        text = (choice.note if choice is not None else None) or self.warning or ""
        note = self.query_one("#key-note", Static)
        note.update(display_text(text))
        note.set_class(not text, "-empty")

    def action_start(self) -> None:
        index = self.query_one(OptionList).highlighted
        if index is None:
            return
        windows = self.query_one("#system-windows", RadioButton).value
        self._close(KeyPlan(self.choices[index], windows))

    def action_cancel(self) -> None:
        self._close(None)

    def _close(self, plan: KeyPlan | None) -> None:
        if not self._answered:
            self._answered = True
            self.dismiss(plan)


def _field(field: str, label: str, widget: Widget, *extra: Widget) -> Horizontal:
    """One form row: the label beside a cell with the widget and its error."""
    return Horizontal(
        Static(label, classes="form-label", markup=False),
        Vertical(
            widget,
            *extra,
            Static("", id=f"form-{field}-error", classes="form-error", markup=False),
            classes="form-cell",
        ),
        classes="form-field",
        id=f"field-{field}",
    )


def _place(message: str, line_numbers: Sequence[int]) -> tuple[str | None, str]:
    """Map a validation message to its form field and a short explanation."""
    location, _, text = message.partition(": ")
    match = _LOCATION.fullmatch(location)
    if match is None or match.group(1) is None:
        return None, text
    field, index, part = match.groups()
    if field == "addresses" and index:
        return field, f"Address {index}: {text}"
    if field == "links" and index:
        line = line_numbers[int(index) - 1]
        return field, f"Line {line}{f' {part}' if part else ''}: {text}"
    return field, text
