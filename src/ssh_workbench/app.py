"""Machine selection, literal details, editing and explicit SSH and link actions."""

from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Header, ListItem, ListView, OptionList, Static
from textual.widgets.option_list import Option

from ssh_workbench.config import (
    ConfigError,
    Link,
    Machine,
    format_machines,
    read_machines,
)
from ssh_workbench.display import display_lines as _display_lines
from ssh_workbench.display import display_text as _display_text
from ssh_workbench.forms import ConfirmDelete, MachineForm
from ssh_workbench.links import LinkResult, open_link
from ssh_workbench.ssh import SSHLaunchError, launch_ssh, ssh_handoff
from ssh_workbench.sshconfig import host_names, ssh_folder
from ssh_workbench.status import (
    AliasTarget,
    MachineStatus,
    State,
    StatusChecker,
    check_machine,
)
from ssh_workbench.store import (
    FileChangedError,
    SaveError,
    backup_path,
    save_machines,
)

# Seconds between status rounds; the timer never runs ssh -G.
STATUS_INTERVAL = 30.0
ANIMATION_TICK = 0.2
SPINNER = "◐◓◑◒"


@dataclass
class StatusFinished(Message):
    round: int
    machine_id: str
    status: MachineStatus
    # Set when this check ran ssh -G for the alias.
    alias: str | None
    target: AliasTarget | None


class StatusSymbol(Widget):
    """A machine's status symbol. Each state has its own shape; color and
    motion are only added on top."""

    DEFAULT_CSS = """
    StatusSymbol {
        width: 2;
        height: 1;
    }
    StatusSymbol.state-online {
        color: $success;
    }
    StatusSymbol.state-online.-dim {
        color: $success 45%;
    }
    StatusSymbol.state-offline {
        color: $error;
    }
    StatusSymbol.state-unknown {
        color: $warning;
    }
    StatusSymbol.state-checking {
        color: $accent;
    }
    StatusSymbol.state-not_checked {
        color: $text-muted;
    }
    """

    state: reactive[State] = reactive(State.NOT_CHECKED)
    frame: reactive[int] = reactive(0)

    def __init__(self, state: State) -> None:
        super().__init__(classes=f"state-{state.name.lower()}")
        self.set_reactive(StatusSymbol.state, state)

    def watch_state(self, state: State) -> None:
        for other in State:
            self.set_class(other is state, f"state-{other.name.lower()}")

    def watch_frame(self, frame: int) -> None:
        # A gentle pulse: online symbols dim for 0.8 s in every 1.6 s.
        self.set_class(self.state is State.ONLINE and frame // 4 % 2 == 1, "-dim")

    def render(self) -> Content:
        if self.state is State.CHECKING:
            return Content(SPINNER[self.frame % len(SPINNER)])
        return Content(self.state.symbol)


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


class MachinePanes(Vertical):
    """The browser panes. A save rebuilds them in place: `App.recompose` would
    rebuild whichever screen is active, which can be an open form."""

    def compose(self) -> ComposeResult:
        yield from self.app.compose_panes()


class SSHWorkbenchApp(App[None]):
    TITLE = "SSH Workbench"
    SUB_TITLE = "Machines"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("c", "connect", "Connect"),
        Binding("o", "open_link", "Link"),
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("x", "delete", "Delete"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]
    CSS = """
    #panes, #browser {
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
    #machine-list ListItem Horizontal {
        height: 1;
    }
    #machine-list Static {
        width: 1fr;
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
        file_text: str | None = None,
        checker: StatusChecker | None = None,
    ) -> None:
        super().__init__()
        self.config_supplied = machines is not None
        self.config_path = config_path
        # The loaded text; a save refuses to overwrite a file that differs.
        self.file_text = file_text
        self.machines = tuple(machines or ())
        self._initial_index = 0
        # Between a save and the rebuild, the list on screen is the old one.
        self._rebuilding = False
        self._connecting = False
        self._link_request: LinkRequest | None = None
        self._links_closed = Event()
        # Without a checker the app never checks; the CLI passes the real one.
        self.checker = checker
        self._statuses: dict[str, MachineStatus] = {}
        # The address each machine's last finished check found online; a new
        # round shows Checking but Connect keeps using this.
        self._online: dict[str, str] = {}
        # What ssh -G said for each alias at startup or the last refresh.
        self._targets: dict[str, AliasTarget | None] = {}
        self._round = 0
        self._frame = 0
        self._status_closed = Event()

    def compose(self) -> ComposeResult:
        yield Header()
        yield MachinePanes(id="panes")
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
        yield Footer(compact=True)

    def compose_panes(self) -> ComposeResult:
        """The list and details, or the empty screen; rebuilt after each save."""
        if self.machines:
            with Horizontal(id="browser"):
                machine_list = ListView(
                    *(
                        ListItem(
                            Horizontal(
                                StatusSymbol(self._status_of(machine).state),
                                Static(_display_text(machine.name), markup=False),
                            )
                        )
                        for machine in self.machines
                    ),
                    initial_index=min(self._initial_index, len(self.machines) - 1),
                    id="machine-list",
                )
                machine_list.border_title = "Machines"
                yield machine_list
                with VerticalScroll(id="machine-details") as details:
                    details.border_title = "Machine details"
                    for field, label in (
                        ("id", "ID"),
                        ("name", "Name"),
                        ("status", "Status"),
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

    def _empty_message(self) -> str:
        path = (
            _display_text(str(self.config_path))
            if self.config_path is not None
            else None
        )
        if self.config_supplied:
            location = f":\n{path}" if path is not None else "."
            return f"No machines in this file yet{location}\n\nPress A to add one."
        if path is not None:
            return (
                "No machine file yet.\n\nPress A to add your first machine. "
                f"Workbench creates the file at:\n{path}\n\n"
                "Or restart with --config PATH. The README describes the format."
            )
        return (
            "No machine file selected.\n\n"
            "Restart with --config PATH. The README describes the format."
        )

    def on_mount(self) -> None:
        if self.machines:
            self.query_one("#machine-list", ListView).focus()
        if self.checker is not None:
            self._start_round(resolve=True)
            self.set_interval(STATUS_INTERVAL, self._timer_round)
            self.set_interval(ANIMATION_TICK, self._tick_animation)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self.refresh_bindings()
        index = event.list_view.index
        # An old list can still report a highlight while the panes rebuild.
        if index is not None and not self._rebuilding:
            self._show_details(index)

    def _machine_list(self) -> ListView | None:
        """The list, or None while the panes show the empty screen or rebuild."""
        found = self.query("#machine-list")
        return found.first(ListView) if found else None

    def _show_details(self, index: int) -> None:
        machine = self.machines[index]
        direct = machine.alias is None
        unset = "Not set" if direct else "From your SSH config"
        for field, value in (
            ("id", _display_text(machine.id)),
            ("name", _display_text(machine.name)),
            ("status", self._status_text(machine)),
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

    def _status_of(self, machine: Machine) -> MachineStatus:
        default = State.NOT_CHECKED if self.checker is None else State.CHECKING
        return self._statuses.get(machine.id, MachineStatus(default))

    def _status_text(self, machine: Machine) -> str:
        status = self._status_of(machine)
        text = f"{status.state.symbol} {status.state.word}"
        if status.state is State.ONLINE:
            if status.address is None:
                return f"{text} via alias"
            return f"{text}: {_display_text(status.address)}"
        if status.state is State.UNKNOWN and status.reason:
            return f"{text}: {status.reason}"
        return text

    def _online_address(self, machine: Machine) -> str | None:
        """The address the last finished check found online, for direct machines."""
        address = self._online.get(machine.id)
        # An edit may have removed the address since that check.
        return address if address in machine.addresses else None

    def action_refresh(self) -> None:
        if self.check_action("refresh", ()) is True:
            self._start_round(resolve=True)

    def _timer_round(self) -> None:
        if self.machines and not self._connecting and not self._rebuilding:
            self._start_round(resolve=False)

    def _start_round(self, resolve: bool) -> None:
        """Check every machine in the background; only `resolve` runs ssh -G."""
        self._round += 1
        for machine in self.machines:
            self._statuses[machine.id] = MachineStatus(State.CHECKING)
            known = machine.alias is None or machine.alias in self._targets
            target = self._targets.get(machine.alias) if machine.alias else None
            # Daemon threads, like the link worker: quitting never waits for a
            # check that hangs on DNS or a dropped connection.
            try:
                Thread(
                    target=self._check,
                    args=(self._round, machine, resolve, known, target),
                    daemon=True,
                ).start()
            except RuntimeError:
                self._statuses[machine.id] = MachineStatus(
                    State.UNKNOWN, reason="the check could not start"
                )
        self._show_statuses()

    def _check(
        self,
        round_id: int,
        machine: Machine,
        resolve: bool,
        known: bool,
        target: AliasTarget | None,
    ) -> None:
        if self._status_closed.is_set():
            return
        resolved = resolve and machine.alias is not None
        try:
            if resolved:
                target = self.checker.resolve_alias(machine.alias)
            if machine.alias is not None and not resolved and not known:
                status = MachineStatus(
                    State.UNKNOWN, reason="press R to resolve this alias"
                )
            else:
                status = check_machine(machine, target, self.checker.port_open)
        except Exception:
            # Never let a background failure print a traceback into the TUI.
            status = MachineStatus(State.UNKNOWN, reason="the check failed")
        if not self._status_closed.is_set():
            try:
                self.post_message(
                    StatusFinished(
                        round_id,
                        machine.id,
                        status,
                        machine.alias if resolved else None,
                        target if resolved else None,
                    )
                )
            except RuntimeError:
                # The event loop may close between the guard and enqueue.
                pass

    def on_status_finished(self, message: StatusFinished) -> None:
        if self._status_closed.is_set() or message.round != self._round:
            return
        if message.alias is not None:
            self._targets[message.alias] = message.target
        if message.machine_id in {machine.id for machine in self.machines}:
            self._statuses[message.machine_id] = message.status
            if message.status.state is State.ONLINE and message.status.address:
                self._online[message.machine_id] = message.status.address
            else:
                self._online.pop(message.machine_id, None)
            self._show_statuses()

    def _show_statuses(self) -> None:
        machine_list = self._machine_list()
        if machine_list is None or self._rebuilding:
            return
        for symbol, machine in zip(
            machine_list.query(StatusSymbol), self.machines, strict=False
        ):
            symbol.state = self._status_of(machine).state
        index = machine_list.index
        if index is not None and index < len(self.machines):
            self.query_one("#machine-status", Static).update(
                self._status_text(self.machines[index])
            )

    def _tick_animation(self) -> None:
        if self.animation_level == "none":
            return
        self._frame += 1
        for symbol in self.query(StatusSymbol):
            symbol.frame = self._frame

    def _browsing(self) -> bool:
        """True when the browser screen is active, current and not connecting."""
        return (
            not self._connecting
            and not self._rebuilding
            and len(self.screen_stack) == 1
        )

    def _selected_index(self) -> int | None:
        machine_list = self._machine_list()
        if not self._browsing() or not self.machines or machine_list is None:
            return None
        return machine_list.index

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "refresh":
            ready = self.checker is not None and self._browsing() and self.machines
            return True if ready else None
        if action == "add":
            return True if self._browsing() and self.config_path is not None else None
        if action in ("connect", "open_link", "edit", "delete"):
            index = self._selected_index()
            if index is None:
                return None
            if action in ("edit", "delete") and self.config_path is None:
                return None
            if action == "open_link" and not self.machines[index].links:
                return None
        return True

    def _rewrite_warning(self) -> str | None:
        """Why a save would lose text, when the file is not in Workbench's format."""
        if self.file_text is None or self.file_text == format_machines(self.machines):
            return None
        backup = _display_text(backup_path(self.config_path).name)
        return (
            "Saving rewrites the file without its comments or formatting; "
            f"the old file is kept as {backup}."
        )

    def _form(
        self,
        machine: Machine | None,
        save: Callable[[Machine], str | None],
        ids_in_use: Callable[[], Collection[str]],
    ) -> MachineForm:
        folder = ssh_folder()

        def rewrite_warning() -> str | None:
            warning = self._rewrite_warning()
            return warning and f"{warning} Press Ctrl+S again to save."

        return MachineForm(
            machine,
            ids_in_use=ids_in_use,
            host_names=host_names(folder) if folder is not None else (),
            save=save,
            rewrite_warning=rewrite_warning,
        )

    def action_add(self) -> None:
        if self.check_action("add", ()) is not True:
            return

        def save(machine: Machine) -> str | None:
            return self._save_one([*self.machines, machine], len(self.machines))

        self.push_screen(
            self._form(None, save, lambda: {machine.id for machine in self.machines})
        )

    def action_edit(self) -> None:
        index = self._selected_index()
        if index is None or self.check_action("edit", ()) is not True:
            return
        original = self.machines[index]

        def save(machine: Machine) -> str | None:
            machines = list(self.machines)
            ids = [item.id for item in machines]
            # After an outside change the machine may have moved or vanished.
            position = ids.index(original.id) if original.id in ids else len(machines)
            machines[position : position + 1] = [machine]
            return self._save_one(machines, position)

        self.push_screen(
            self._form(
                original,
                save,
                lambda: {m.id for m in self.machines if m.id != original.id},
            )
        )

    def action_delete(self) -> None:
        index = self._selected_index()
        if index is None or self.check_action("delete", ()) is not True:
            return
        machine = self.machines[index]

        def answered(confirmed: bool | None) -> None:
            if not confirmed:
                return
            remaining = [item for item in self.machines if item.id != machine.id]
            problem = self._save(
                remaining, min(index, len(remaining) - 1), retry="delete"
            )
            self.query_one("#connection-status", Static).update(
                problem or f"Deleted machine {index + 1}: {_display_text(machine.id)}."
            )

        self.push_screen(ConfirmDelete(machine, self._rewrite_warning()), answered)

    def _save_one(self, machines: list[Machine], position: int) -> str | None:
        problem = self._save(machines, position)
        if problem is None:
            self.query_one("#connection-status", Static).update(
                f"Saved machine {position + 1}: {_display_text(machines[position].id)}."
            )
        return problem

    def _save(
        self, machines: list[Machine], select: int, retry: str = "save"
    ) -> str | None:
        """Write the file and rebuild the panes; return a problem to show, if any."""
        try:
            text = save_machines(self.config_path, machines, self.file_text)
        except FileChangedError:
            return self._reload_after_outside_change(retry)
        except SaveError as error:
            return str(error)
        self.machines = tuple(machines)
        self.file_text = text
        self.config_supplied = True
        self._rebuilding = True
        self.call_later(self._rebuild, select)
        return None

    def _reload_after_outside_change(self, retry: str) -> str:
        machines: list[Machine] = []
        text = None
        if self.config_path.exists():
            try:
                machines, text = read_machines(self.config_path)
            except ConfigError as error:
                detail = str(error).removeprefix("configuration: ")
                return (
                    "The machine file changed outside Workbench and now has an "
                    f"error: {detail}. Fix the file, then {retry} again."
                )
        # Keep the same machine selected, not the same row: a connect must not
        # go to whichever machine moved into that position.
        index = self._selected_index_any()
        selected = self.machines[index].id if index is not None else None
        ids = [machine.id for machine in machines]
        self.machines = tuple(machines)
        self.file_text = text
        self.config_supplied = text is not None
        self._rebuilding = True
        self.call_later(self._rebuild, ids.index(selected) if selected in ids else 0)
        return (
            "The machine file changed outside Workbench and was reloaded. "
            f"Check the list, then {retry} again."
        )

    def _selected_index_any(self) -> int | None:
        """The list's selection even while a form is open on top of it."""
        machine_list = self._machine_list()
        index = machine_list.index if machine_list is not None else None
        return index if index is not None and index < len(self.machines) else None

    async def _rebuild(self, select: int) -> None:
        self._initial_index = min(max(select, 0), max(len(self.machines) - 1, 0))
        try:
            await self.query_one(MachinePanes).recompose()
        finally:
            self._rebuilding = False
        machine_list = self._machine_list()
        if machine_list is not None:
            self._show_details(self._initial_index)
            # The browser may sit under a form; focus returns here when it closes.
            self.screen_stack[0].set_focus(machine_list)
        self.refresh_bindings()
        if self.checker is not None:
            self._start_round(resolve=False)

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
        self._status_closed.set()

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
                        address = self._online_address(machine)
                        status = (
                            launch_ssh(machine, address)
                            if address is not None
                            else launch_ssh(machine)
                        )
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
