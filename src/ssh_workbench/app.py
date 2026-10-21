"""Machine selection, literal details and explicit SSH and link actions."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, ListItem, ListView, OptionList, Static
from textual.widgets.option_list import Option

from ssh_workbench.config import Link, Machine
from ssh_workbench.links import LinkResult, open_link
from ssh_workbench.ssh import SSHLaunchError, launch_ssh, ssh_handoff


def _display_text(value: str) -> str:
    """Make controls visible without interpreting markup or changing records."""
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in value)


def _display_lines(values: Sequence[str]) -> str:
    return "\n".join(_display_text(value) for value in values)


@dataclass(frozen=True)
class LinkRequest:
    machine: Machine
    link: Link
    position: int


@dataclass
class LinkFinished(Message):
    request: LinkRequest
    result: LinkResult


class LinkPicker(ModalScreen[Link | None]):
    """Choose one of a machine's links; Escape cancels without opening anything."""

    # A modal screen hides the app's bindings, so Q and Ctrl+Q are repeated here.
    # Enter and Escape are priority bindings, handled in the order they arrive.
    # Otherwise OptionList delivers Enter's choice as a later message, and a
    # key typed right after it could overtake the choice.
    BINDINGS = [
        Binding("enter", "choose", "Open", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("q", "app.quit", "Quit"),
        Binding("ctrl+q", "app.quit", "Quit", show=False),
    ]
    DEFAULT_CSS = """
    LinkPicker {
        align: center middle;
    }
    #link-picker {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 90%;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
    }
    #link-options {
        height: auto;
        max-height: 60vh;
    }
    """

    def __init__(self, machine: Machine) -> None:
        super().__init__()
        self.machine = machine
        self._answered = False

    def compose(self) -> ComposeResult:
        with Vertical(id="link-picker") as picker:
            picker.border_title = "Open a link"
            yield Static(_display_text(self.machine.name), markup=False)
            yield OptionList(
                *(
                    Option(
                        Content(
                            f"{_display_text(link.name)}  {_display_text(link.url)}"
                        )
                    )
                    for link in self.machine.links
                ),
                id="link-options",
            )
            yield Static("Enter: open   Escape: cancel", markup=False)

    def on_mount(self) -> None:
        options = self.query_one(OptionList)
        options.highlighted = 0
        options.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._close(self.machine.links[event.option_index])

    def action_choose(self) -> None:
        index = self.query_one(OptionList).highlighted
        if index is not None:
            self._close(self.machine.links[index])

    def action_cancel(self) -> None:
        self._close(None)

    def _close(self, link: Link | None) -> None:
        # One console read can deliver several keys before the pop happens; a
        # second dismissal would pop the browser screen itself.
        if not self._answered:
            self._answered = True
            self.dismiss(link)


class SSHWorkbenchApp(App[None]):
    TITLE = "SSH Workbench"
    SUB_TITLE = "Machines"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("c", "connect", "Connect"),
        Binding("o", "open_link", "Open link"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]
    CSS = """
    #browser {
        height: 1fr;
    }
    #machine-list {
        width: 1fr;
        min-width: 20;
        border: solid $panel;
    }
    #machine-list:focus, #machine-details:focus {
        border: solid $accent;
    }
    #machine-list ListItem {
        height: 1;
        padding: 0 1;
    }
    #machine-list Static {
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    #machine-details {
        width: 2fr;
        border: solid $panel;
        padding: 0 1;
        scrollbar-gutter: stable;
    }
    .field-label {
        text-style: bold;
    }
    .field-value {
        margin-bottom: 1;
    }
    #navigation-help, #connection-status, #link-status {
        height: auto;
        padding: 0 1;
    }
    #link-status {
        height: 3;
    }
    #empty-content {
        padding: 1 2;
    }
    """

    def __init__(
        self,
        machines: Sequence[Machine] | None = None,
        config_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.config_supplied = machines is not None
        self.config_path = config_path
        self.machines = tuple(machines or ())
        self._connecting = False
        self._link_request: LinkRequest | None = None
        self._links_closed = Event()

    def compose(self) -> ComposeResult:
        yield Header()
        if self.machines:
            with Horizontal(id="browser"):
                machine_list = ListView(
                    *(
                        ListItem(Static(_display_text(machine.name), markup=False))
                        for machine in self.machines
                    ),
                    initial_index=0,
                    id="machine-list",
                )
                machine_list.border_title = "Machines"
                yield machine_list
                with VerticalScroll(id="machine-details") as details:
                    details.border_title = "Machine details"
                    for field, label in (
                        ("id", "ID"),
                        ("name", "Name"),
                        ("connection", "Connection"),
                        ("target", "SSH alias"),
                        ("user", "User"),
                        ("port", "Port"),
                        ("key", "Key"),
                        ("links", "Links"),
                    ):
                        yield Static(
                            label,
                            id=f"machine-{field}-label",
                            classes="field-label",
                            markup=False,
                        )
                        yield Static(
                            id=f"machine-{field}", classes="field-value", markup=False
                        )
            yield Static(
                "Up/Down: select   Tab: switch pane   PgUp/PgDn: scroll",
                id="navigation-help",
                markup=False,
            )
        else:
            with VerticalScroll(id="empty-content"):
                yield Static(self._empty_message(), id="empty-state", markup=False)
        yield Static(
            "C: connect to the selected machine."
            if self.machines
            else "No machines to connect to.",
            id="connection-status",
            markup=False,
        )
        yield Static(
            "O: open a link of the selected machine. Opens in this environment.",
            id="link-status",
            markup=False,
        )
        yield Footer()

    def _empty_message(self) -> str:
        path = (
            _display_text(str(self.config_path))
            if self.config_path is not None
            else None
        )
        if self.config_supplied:
            location = f":\n{path}" if path is not None else "."
            return (
                f"No machines in this file yet{location}\n\n"
                "Add [[machines]] entries to it, then restart."
            )
        if path is not None:
            return (
                f"No machine file yet.\n\nCreate one at:\n{path}\n\n"
                "or restart with --config PATH. The README describes the format."
            )
        return (
            "No machine file selected.\n\n"
            "Restart with --config PATH. The README describes the format."
        )

    def on_mount(self) -> None:
        if self.machines:
            self.query_one("#machine-list", ListView).focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self.refresh_bindings()
        index = event.list_view.index
        if index is None:
            return
        machine = self.machines[index]
        direct = machine.alias is None
        unset = "Not set" if direct else "From your SSH config"
        for field, value in (
            ("id", _display_text(machine.id)),
            ("name", _display_text(machine.name)),
            ("connection", "Direct" if direct else "SSH alias"),
            (
                "target",
                _display_lines(machine.addresses)
                if direct
                else _display_text(machine.alias),
            ),
            ("user", _display_text(machine.user) if machine.user else unset),
            ("port", str(machine.port) if machine.port is not None else unset),
            ("key", _display_text(machine.key) if machine.key else unset),
            (
                "links",
                _display_lines([f"{link.name}: {link.url}" for link in machine.links])
                if machine.links
                else "None",
            ),
        ):
            self.query_one(f"#machine-{field}", Static).update(value)
        self.query_one("#machine-target-label", Static).update(
            "Addresses" if direct else "SSH alias"
        )
        self.query_one("#machine-details", VerticalScroll).scroll_home(animate=False)

    def _selected_index(self) -> int | None:
        """The selection, when the browser screen is active and not connecting."""
        if self._connecting or not self.machines or isinstance(self.screen, LinkPicker):
            return None
        return self.query_one(ListView).index

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action in ("connect", "open_link"):
            index = self._selected_index()
            if index is None:
                return None
            if action == "open_link" and not self.machines[index].links:
                return None
        return True

    def action_open_link(self) -> None:
        if self._links_closed.is_set():
            return
        index = self._selected_index()
        if index is None:
            return
        if self._link_request is not None:
            self._show_link_result(
                self._link_request, "browser request still pending. Wait or Q to quit."
            )
            return
        machine = self.machines[index]
        if not machine.links:
            return
        if len(machine.links) == 1:
            self._open_machine_link(LinkRequest(machine, machine.links[0], index + 1))
            return

        def picked(link: Link | None) -> None:
            if link is not None:
                self._open_machine_link(LinkRequest(machine, link, index + 1))

        self.push_screen(LinkPicker(machine), picked)

    def _open_machine_link(self, request: LinkRequest) -> None:
        if self._links_closed.is_set() or self._link_request is not None:
            return
        self._link_request = request
        self._show_link_result(request, "browser request pending. Q still quits.")
        # Textual's executor workers can delay interpreter shutdown. One daemon
        # thread lets Q finish even when the OS opener does not return.
        try:
            Thread(target=self._launch_link, args=(request,), daemon=True).start()
        except RuntimeError:
            self._link_request = None
            self._show_link_result(request, LinkResult.FAILED.value)

    def _launch_link(self, request: LinkRequest) -> None:
        if self._links_closed.is_set():
            return
        try:
            result = open_link(request.link.url)
        except Exception:
            # An unexpected opener error must not print private data from a
            # background traceback into the terminal.
            result = LinkResult.FAILED
        if not self._links_closed.is_set():
            try:
                self.post_message(LinkFinished(request, result))
            except RuntimeError:
                # The event loop may close between the guard and enqueue.
                pass

    def on_link_finished(self, message: LinkFinished) -> None:
        if self._links_closed.is_set() or message.request is not self._link_request:
            return
        self._link_request = None
        self._show_link_result(message.request, message.result.value)

    def _show_link_result(self, request: LinkRequest, result: str) -> None:
        self.query_one("#link-status", Static).update(
            f"{_display_text(request.link.name)} {result} "
            f"Machine {request.position}: {_display_text(request.machine.id)}"
        )

    def on_unmount(self) -> None:
        self._links_closed.set()
        self._link_request = None

    def action_connect(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        machine = self.machines[index]
        machine_list = self.query_one(ListView)
        self._connecting = True
        self.refresh_bindings()
        with ssh_handoff():
            try:
                with self.suspend():
                    # Textual 8.2.8 resumes only on a normal context exit. Handle
                    # launch errors here so they cannot skip terminal restoration.
                    try:
                        status = launch_ssh(machine)
                    except SSHLaunchError as error:
                        message = str(error)
                    except KeyboardInterrupt:
                        message = "SSH interrupted. Press C to retry or Q to quit."
                    else:
                        message = f"SSH exited with status {status}."
                        if status != 0:
                            message += (
                                " Check the SSH client's message and alias; C retries."
                                if machine.alias is not None
                                else " Check the SSH client's message and the "
                                "machine's settings; C retries."
                            )
            except SuspendNotSupported:
                message = (
                    "Cannot hand off this terminal. "
                    "Run SSH Workbench in a local terminal."
                )
            finally:
                self._connecting = False
                machine_list.focus()
                self.refresh_bindings()
            self.query_one("#connection-status", Static).update(
                f"{message} Machine {index + 1}: {_display_text(machine.id)}"
            )
