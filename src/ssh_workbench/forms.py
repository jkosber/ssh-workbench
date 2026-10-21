"""The machine form and the delete confirmation.

The form checks a machine with `config.validate_machine`, the loader's own rules,
and shows the first problem under its field. Saving is the app's job: the form
hands over a valid machine and shows any problem the save reports.
"""

import re
from collections.abc import Callable, Collection, Sequence

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widget import Widget
from textual.widgets import Button, Input, RadioButton, RadioSet, Static, TextArea

from ssh_workbench.config import ConfigError, Machine, validate_machine
from ssh_workbench.display import display_text

FIELDS = ("id", "name", "alias", "addresses", "user", "port", "key", "links")
_LOCATION = re.compile(r"machine(?:\.(\w+)(?:\[(\d+)\])?(?:\.(\w+))?)?")


class MachineForm(ModalScreen[None]):
    """Add a machine, or edit one, without writing anything until it is valid."""

    # Priority bindings keep keys typed into the fields from triggering app
    # actions, and handle Ctrl+S and Escape in the order they arrive.
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]
    DEFAULT_CSS = """
    MachineForm {
        align: center middle;
    }
    #machine-form {
        width: 90%;
        max-width: 100;
        height: 90%;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
    }
    #form-fields {
        height: 1fr;
    }
    .form-label {
        text-style: bold;
        margin-top: 1;
    }
    .form-error {
        color: $error;
        height: auto;
    }
    #form-hosts {
        color: $text-muted;
    }
    #form-kind {
        height: auto;
    }
    #form-links {
        height: 5;
    }
    #form-message {
        height: auto;
    }
    #form-buttons {
        height: auto;
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
                "links": "\n".join(f"{link.name} {link.url}" for link in machine.links),
            }
        self._initial = values
        with Vertical(id="machine-form") as form:
            form.border_title = "Edit machine" if machine else "Add machine"
            with VerticalScroll(id="form-fields"):
                yield from _field("id", "ID", Input(values["id"], id="form-id"))
                yield from _field("name", "Name", Input(values["name"], id="form-name"))
                yield Static("Connection", classes="form-label", markup=False)
                yield RadioSet(
                    RadioButton("SSH alias", value=not direct, id="kind-alias"),
                    RadioButton("Direct (addresses)", value=direct, id="kind-direct"),
                    id="form-kind",
                )
                with Vertical(id="alias-fields"):
                    alias = Input(
                        values["alias"],
                        id="form-alias",
                        suggester=SuggestFromList(
                            self.host_names, case_sensitive=False
                        ),
                    )
                    yield from _field("alias", "SSH alias", alias)
                    yield Static(self._hosts_text(), id="form-hosts", markup=False)
                with Vertical(id="direct-fields"):
                    for field, label in (
                        ("addresses", "Addresses (the first one is used)"),
                        ("user", "User (optional)"),
                        ("port", "Port (optional)"),
                        ("key", "Key: path of the private key (optional)"),
                    ):
                        yield from _field(
                            field, label, Input(values[field], id=f"form-{field}")
                        )
                yield from _field(
                    "links",
                    "Links: one per line, the name and then the URL",
                    TextArea(values["links"], id="form-links", tab_behavior="focus"),
                )
            yield Static("", id="form-message", markup=False)
            with Horizontal(id="form-buttons"):
                yield Button("Save", id="form-save", variant="primary")
                yield Button("Cancel", id="form-cancel")
            yield Static(
                "Tab: next field   Ctrl+S: save   Escape: cancel", markup=False
            )

    def on_mount(self) -> None:
        self._show_kind()
        self.query_one("#form-id", Input).focus()

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

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self._show_kind()
        self._validate()

    def _changed(self, field: str, value: str) -> None:
        if value != self._initial.get(field, ""):
            self._touched.add(field)
        self._validate()

    def _validate(self) -> Machine | None:
        machine, field, problem = self._check()
        for name in FIELDS:
            shown = name == field and (self._attempted or name in self._touched)
            self.query_one(f"#form-{name}-error", Static).update(
                problem if shown else ""
            )
        if field is None and problem:
            self.query_one("#form-message", Static).update(problem)
        return machine

    def _check(self) -> tuple[Machine | None, str | None, str]:
        table, line_numbers = self._table()
        try:
            machine = validate_machine(table, "machine")
        except ConfigError as error:
            return None, *_place(str(error), line_numbers)
        if machine.id in self.ids_in_use():
            return None, "id", "already used by another machine"
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


class ConfirmDelete(ModalScreen[bool]):
    """Ask before deleting; Y deletes, N or Escape keeps the machine."""

    BINDINGS = [
        Binding("y", "answer(True)", "Delete", priority=True),
        Binding("n", "answer(False)", "Keep", priority=True),
        Binding("escape", "answer(False)", "Keep", priority=True),
    ]
    DEFAULT_CSS = """
    ConfirmDelete {
        align: center middle;
    }
    #confirm-delete {
        width: 90%;
        max-width: 80;
        height: auto;
        border: solid $error;
        background: $surface;
        padding: 0 1;
    }
    """

    def __init__(self, machine: Machine, rewrite_warning: str | None) -> None:
        super().__init__()
        self.machine = machine
        self.rewrite_warning = rewrite_warning
        self._answered = False

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-delete") as box:
            box.border_title = "Delete machine"
            yield Static(
                f"Delete {display_text(self.machine.name)} "
                f"({display_text(self.machine.id)})?",
                markup=False,
            )
            if self.rewrite_warning:
                yield Static(self.rewrite_warning, markup=False)
            yield Static("Y: delete   N or Escape: keep", markup=False)

    def action_answer(self, confirmed: bool) -> None:
        if not self._answered:
            self._answered = True
            self.dismiss(confirmed)


def _field(field: str, label: str, widget: Widget) -> ComposeResult:
    yield Static(label, classes="form-label", markup=False)
    yield widget
    yield Static("", id=f"form-{field}-error", classes="form-error", markup=False)


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
