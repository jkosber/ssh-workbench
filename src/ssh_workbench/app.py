"""Machine selection, literal details, editing and explicit SSH and link actions."""

import platform
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event, Thread

from textual import events
from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widget import Widget
from textual.widgets import Footer, ListItem, ListView, OptionList, Static
from textual.widgets.option_list import Option

from ssh_workbench.aliases import (
    AliasMemory,
    Review,
    format_state,
    load_state,
    review,
    save_state,
    state_path,
)
from ssh_workbench.config import (
    ConfigError,
    Link,
    Machine,
    format_machines,
    read_machines,
)
from ssh_workbench.display import display_lines as _display_lines
from ssh_workbench.display import display_text as _display_text
from ssh_workbench.exports import (
    BACKUP_NAME,
    EXPORT_NAME,
    INCLUDE_LINE,
    ExportError,
    add_include,
    include_present,
    write_exports,
)
from ssh_workbench.forms import (
    ConfirmDelete,
    ConfirmInclude,
    KeyChoice,
    KeyPlan,
    KeySetup,
    MachineForm,
)
from ssh_workbench.keys import (
    KeySetupError,
    identity_paths,
    key_setting,
    keygen_arguments,
    new_key_path,
    posix_install_command,
    public_key_files,
    read_public_key,
    windows_install_command,
)
from ssh_workbench.links import LinkResult, open_link
from ssh_workbench.ssh import (
    SSHLaunchError,
    ctrl_c_count,
    find_ssh,
    install_arguments,
    interrupted,
    key_argument,
    launch_ssh,
    login_test_arguments,
    run_native,
    ssh_handoff,
)
from ssh_workbench.sshconfig import host_names, ssh_folder, ssh_folder_override
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

# Workbench's own colors; Textual derives every shade from these.
WORKBENCH_THEME = Theme(
    name="workbench",
    primary="#4FC1E9",
    secondary="#7AA2F7",
    accent="#F2B25C",
    warning="#E5C07B",
    error="#EF6B73",
    success="#7FD48C",
    foreground="#D8DEE9",
    background="#10141B",
    surface="#161B24",
    panel="#1E2531",
    dark=True,
    variables={
        "border": "#4FC1E9",
        "border-blurred": "#2C3646",
        "footer-key-foreground": "#4FC1E9",
        "footer-background": "#161B24",
        "block-cursor-background": "#24435A",
        "block-cursor-foreground": "#F2F6FA",
        "block-cursor-text-style": "bold",
        "block-cursor-blurred-background": "#1F2A38",
        "block-cursor-blurred-foreground": "#D8DEE9",
        "block-cursor-blurred-text-style": "none",
    },
)
# The header counts these states, in this order. Not checked means status
# checks are off, so it is left out.
SUMMARY_STYLES = {
    State.ONLINE: "$success",
    State.OFFLINE: "$error",
    State.CHECKING: "$accent",
    State.UNKNOWN: "$warning",
    State.NOT_FOUND: "$error",
}


@dataclass
class StatusFinished(Message):
    round: int
    machine_id: str
    status: MachineStatus
    # Set when this check ran ssh -G for the alias.
    alias: str | None
    target: AliasTarget | None


@dataclass
class KeyTargetResolved(Message):
    """What `ssh -G` said about an alias when K was pressed."""

    machine_id: str
    target: AliasTarget | None


@dataclass
class AliasesReviewed(Message):
    round: int
    # The literal Host names read for this review.
    names: tuple[str, ...]
    # None when the review failed; the round then checks every alias that is
    # not already missing.
    review: Review | None


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
    StatusSymbol.state-not_found {
        color: $error;
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


class RowTarget(Widget):
    """Where a machine connects, shown in its list row on wide terminals. Not a
    `Static`, so the name stays the row's only one."""

    DEFAULT_CSS = """
    RowTarget {
        display: none;
        width: auto;
        max-width: 50%;
        height: 1;
        padding-left: 1;
        color: $text-muted;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    """

    def __init__(self, target: str) -> None:
        super().__init__(classes="row-target")
        self.target = target

    def render(self) -> Content:
        return Content(self.target)


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
        border: round $primary;
        border-title-color: $primary;
        border-title-style: bold;
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


class KeyFooter(Footer):
    """The compact footer. On narrow screens it becomes a grid of four columns,
    so every key stays on screen, on two rows."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        # Footer sets one grid column per key; the grid applies only when narrow.
        self.styles.grid_size_columns = 4


class MachinePanes(Vertical):
    """The browser panes. A save rebuilds them in place: `App.recompose` would
    rebuild whichever screen is active, which can be an open form."""

    def compose(self) -> ComposeResult:
        yield from self.app.compose_panes()


class SSHWorkbenchApp(App[None]):
    TITLE = "SSH Workbench"
    ENABLE_COMMAND_PALETTE = False
    # Screen classes for the layout: the list stacks above the details and the
    # footer wraps when narrow, rows show their target when wide, and the help
    # line hides when narrow or short.
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (60, "-normal"), (110, "-wide")]
    VERTICAL_BREAKPOINTS = [(0, "-short"), (20, "-tall")]
    BINDINGS = [
        Binding("c", "connect", "Connect"),
        # Shown only for a machine with a rename offer, which hides Connect.
        Binding("u", "update_alias", "Update"),
        Binding("o", "open_link", "Link"),
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("x", "delete", "Delete"),
        Binding("k", "key_setup", "Key"),
        # "Check", not "Refresh": eight keys must fit 60 columns.
        Binding("r", "refresh", "Check"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]
    CSS = """
    #app-header {
        height: 1;
        background: $panel;
    }
    #app-title {
        width: auto;
        padding: 0 1;
        background: $primary;
        color: $background;
        text-style: bold;
    }
    #app-summary {
        width: 1fr;
        padding: 0 1;
        text-align: right;
        color: $text-muted;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    #panes, #browser {
        height: 1fr;
    }
    #machine-list, #machine-details {
        background: $surface;
        border: round $border-blurred;
        border-title-color: $text-muted;
        border-title-style: bold;
    }
    #machine-list:focus, #machine-details:focus {
        border: round $border;
        border-title-color: $primary;
    }
    #machine-list {
        width: 1fr;
        min-width: 20;
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
        padding: 0 1;
        scrollbar-gutter: stable;
    }
    .field-row {
        height: auto;
    }
    .field-label {
        width: 12;
        color: $text-muted;
        text-style: bold;
    }
    .field-value {
        width: 1fr;
    }
    #machine-name {
        text-style: bold;
    }
    #machine-status.state-online {
        color: $success;
    }
    #machine-status.state-offline, #machine-status.state-not_found {
        color: $error;
    }
    #machine-status.state-unknown {
        color: $warning;
    }
    #machine-status.state-checking {
        color: $accent;
    }
    #navigation-help, #connection-status, #link-status {
        height: auto;
        padding: 0 1;
    }
    #navigation-help {
        color: $text-muted;
    }
    #connection-status, #link-status {
        background: $surface;
    }
    #link-status {
        height: 3;
    }
    #empty-content {
        align: center middle;
        padding: 1 2;
    }
    #empty-state {
        width: 1fr;
        max-width: 76;
        height: auto;
        padding: 1 2;
        border: round $border-blurred;
        background: $surface;
    }

    Screen.-narrow #browser {
        layout: vertical;
    }
    Screen.-narrow #machine-list {
        width: 1fr;
        height: 2fr;
        min-width: 0;
    }
    Screen.-narrow #machine-details {
        width: 1fr;
        height: 3fr;
    }
    Screen.-narrow .field-label {
        width: 11;
    }
    Screen.-wide #machine-list {
        width: 2fr;
    }
    Screen.-wide #machine-details {
        width: 3fr;
    }
    Screen.-wide RowTarget {
        display: block;
    }
    Screen.-narrow KeyFooter {
        layout: grid;
        grid-columns: 1fr;
        height: 2;
    }
    Screen.-narrow #navigation-help, Screen.-short #navigation-help {
        display: none;
    }
    Screen.-short #link-status {
        height: 2;
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
        self.register_theme(WORKBENCH_THEME)
        self.theme = WORKBENCH_THEME.name
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
        # Rename detection. The state file is loaded by the first review.
        self._computer = platform.node()
        self._memory: AliasMemory | None = None
        self._memory_loaded = False
        self._state_text: str | None = None
        # The literal Host names at the last review; None before one finished.
        self._host_names: frozenset[str] | None = None
        # Missing aliases and their rename offers, from the last review.
        self._missing: dict[str, str | None] = {}
        # Aliases this round still resolves; the state is saved when none are left.
        self._pending_aliases: set[str] = set()
        # True while a startup or R round still reviews or resolves aliases.
        self._resolving = False
        # Machines whose check in this round has not reported; the timer waits.
        self._checking: set[str] = set()
        # Reviews and ssh -G checks still running, from any round. R waits for
        # them, so it never starts a second set of ssh -G runs beside them.
        self._resolves_running = 0
        # The machine and new alias a first U warned about.
        self._update_armed: tuple[str, str] | None = None
        # The machine whose alias K is resolving, if any.
        self._key_resolving: str | None = None
        # Exported aliases: a problem writing Workbench's SSH config file, shown
        # after the rebuild, and whether to offer the Include line then.
        self._export_problem: str | None = None
        self._include_offer = False
        self._include_declined = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="app-header"):
            yield Static(self.title, id="app-title", markup=False)
            yield Static(id="app-summary", markup=False)
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
        yield KeyFooter(compact=True)

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
                                RowTarget(
                                    _display_text(machine.alias or machine.addresses[0])
                                ),
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
                        with Horizontal(classes="field-row"):
                            yield Static(
                                label,
                                id=f"machine-{field}-label",
                                classes="field-label",
                                markup=False,
                            )
                            yield Static(
                                id=f"machine-{field}",
                                classes="field-value",
                                markup=False,
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
                "Or restart with --config PATH. The user guide describes the format."
            )
        return (
            "No machine file selected.\n\n"
            "Restart with --config PATH. The user guide describes the format."
        )

    def on_mount(self) -> None:
        self._update_summary()
        if self.machines:
            self.query_one("#machine-list", ListView).focus()
        if self.checker is not None:
            self._start_round(resolve=True)
            self.set_interval(STATUS_INTERVAL, self._timer_round)
            self.set_interval(ANIMATION_TICK, self._tick_animation)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._update_armed = None
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
        self._show_status(machine)
        for field, value in (
            ("id", _display_text(machine.id)),
            ("name", _display_text(machine.name)),
            (
                "connection",
                (
                    f"Direct, exported as ssh {machine.id}"
                    if machine.export_alias
                    else "Direct"
                )
                if direct
                else "SSH alias",
            ),
            ("target", self._target_text(machine)),
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

    def _show_status(self, machine: Machine) -> None:
        """The selected machine's status in the details, colored by its state."""
        widget = self.query_one("#machine-status", Static)
        widget.update(self._status_text(machine))
        state = self._status_of(machine).state
        for other in State:
            widget.set_class(other is state, f"state-{other.name.lower()}")

    def _update_summary(self, width: int | None = None) -> None:
        found = self.query("#app-summary")
        if found:
            found.first(Static).update(self._summary(width or self.size.width))

    def _summary(self, width: int) -> Content:
        """Machines counted by status: in words when they fit beside the title,
        else as symbols."""
        count = len(self.machines)
        if not count:
            return Content("")
        states = [self._status_of(machine).state for machine in self.machines]
        counts = [
            (state, style, states.count(state))
            for state, style in SUMMARY_STYLES.items()
            if state in states
        ]
        words = Content.assemble(
            f"{count} machine{'' if count == 1 else 's'}",
            *(
                part
                for state, style, number in counts
                for part in (
                    "   ",
                    (f"{state.symbol} {number} {state.word.lower()}", style),
                )
            ),
        )
        # The words must fit beside the title, with one cell of padding on each
        # side of both.
        if not counts or words.cell_length + len(self.title) + 4 <= width:
            return words
        return Content.assemble(
            f"{count} ",
            *(
                part
                for state, style, number in counts
                for part in (" ", (f"{state.symbol}{number}", style))
            ),
        )

    def on_resize(self, event: events.Resize) -> None:
        self._update_summary(event.size.width)

    def _target_text(self, machine: Machine) -> str:
        if machine.alias is None:
            return _display_lines(machine.addresses)
        alias = _display_text(machine.alias)
        # Information only: SSH may still resolve it through a pattern.
        if (
            self._host_names is not None
            and machine.alias not in self._host_names
            and machine.alias not in self._missing
        ):
            return f"{alias} (not in your SSH config)"
        return alias

    def _rename_offer(self, machine: Machine) -> str | None:
        return self._missing.get(machine.alias) if machine.alias is not None else None

    def _status_text(self, machine: Machine) -> str:
        status = self._status_of(machine)
        text = f"{status.state.symbol} {status.state.word}"
        if status.state is State.NOT_FOUND:
            offer = self._rename_offer(machine)
            if offer is None:
                return (
                    f"{text}. Fix your SSH config and press R, or press E and save "
                    "to keep or change the alias."
                )
            return (
                f"{text}. Looks like {_display_text(machine.alias)} became "
                f"{_display_text(offer)}. Press U to update."
            )
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
        # When run_test tears the app down, Textual turns is_running False and
        # removes the screens while app timers and messages still run; a normal
        # exit stops both first. Timers and results do nothing in that window.
        if not self.is_running:
            return
        # A timer round would replace a startup or R round still resolving, or
        # a check still running, whose result would then never show.
        if self._resolving or self._checking:
            return
        if self.machines and not self._connecting and not self._rebuilding:
            self._start_round(resolve=False)

    def _start_round(self, resolve: bool) -> None:
        """Check every machine in the background; only `resolve` runs ssh -G.

        A resolving round first reviews the aliases against the SSH config, so
        an alias that vanished never reaches ssh -G or a port check.
        """
        self._round += 1
        self._checking = set()
        aliases = [machine.alias for machine in self.machines if machine.alias]
        reviewing = resolve and bool(aliases)
        self._resolving = reviewing
        for machine in self.machines:
            if not resolve and machine.alias in self._missing:
                self._statuses[machine.id] = MachineStatus(State.NOT_FOUND)
                continue
            self._statuses[machine.id] = MachineStatus(State.CHECKING)
            # Alias checks start once the review is in.
            if not (reviewing and machine.alias is not None):
                self._start_check(machine, resolve)
        if reviewing:
            first = self.config_path if not self._memory_loaded else None
            arguments = (self._round, aliases, self._memory, first)
            # Counted first: a review that cannot start reports at once.
            self._resolves_running += 1
            if not self._start_thread(self._review_aliases, arguments):
                self.on_aliases_reviewed(AliasesReviewed(self._round, (), None))
                return
            # The footer dims R until the review reports.
            self.refresh_bindings()
        self._show_statuses()

    def _start_thread(self, target: Callable[..., None], arguments: tuple) -> bool:
        # Daemon threads, like the link worker: quitting never waits for a
        # check that hangs on DNS, ssh -G or a dropped connection.
        try:
            Thread(target=target, args=arguments, daemon=True).start()
        except RuntimeError:
            return False
        return True

    def _start_check(self, machine: Machine, resolve: bool) -> bool:
        unresolved = machine.alias is not None and machine.alias not in self._targets
        if unresolved and not resolve:
            # Only startup, R and K run ssh -G; nothing to check until then.
            self._statuses[machine.id] = MachineStatus(
                State.UNKNOWN, reason="press R to resolve this alias"
            )
            return True
        target = self._targets.get(machine.alias) if machine.alias else None
        arguments = (self._round, machine, resolve, target)
        if self._start_thread(self._check, arguments):
            self._checking.add(machine.id)
            if resolve and machine.alias is not None:
                self._resolves_running += 1
            return True
        self._statuses[machine.id] = MachineStatus(
            State.UNKNOWN, reason="the check could not start"
        )
        return False

    def _review_aliases(
        self,
        round_id: int,
        aliases: list[str],
        memory: AliasMemory | None,
        machine_file: Path | None,
    ) -> None:
        if self._status_closed.is_set():
            return
        try:
            if machine_file is not None:
                path = state_path(machine_file, self._computer)
                memory = load_state(path, self._computer)
            folder = ssh_folder()
            # Workbench's exported entries are not the user's Host names.
            names = (
                tuple(host_names(folder, skip=folder / EXPORT_NAME))
                if folder is not None
                else ()
            )
            result = review(memory, aliases, names, self.checker.resolve_alias)
        except Exception:
            # Without a review the round still checks the aliases not missing.
            names, result = (), None
        if not self._status_closed.is_set():
            try:
                self.post_message(AliasesReviewed(round_id, names, result))
            except RuntimeError:
                # The event loop may close between the guard and enqueue.
                pass

    def on_aliases_reviewed(self, message: AliasesReviewed) -> None:
        self._resolve_reported()
        if (
            self._status_closed.is_set()
            or not self.is_running
            or message.round != self._round
        ):
            return
        if message.review is not None:
            self._memory = message.review.memory
            self._memory_loaded = True
            self._host_names = frozenset(message.names)
            self._missing = message.review.missing
            self._targets.update(message.review.resolved)
        self._pending_aliases = set()
        for machine in self.machines:
            if machine.alias is None:
                continue
            if machine.alias in self._missing:
                self._statuses[machine.id] = MachineStatus(State.NOT_FOUND)
            elif self._start_check(machine, resolve=True):
                self._pending_aliases.add(machine.alias)
        if not self._pending_aliases:
            self._round_resolved()
        self._show_statuses()
        self.refresh_bindings()

    def _resolve_reported(self) -> None:
        """A review or ssh -G check reported, from this round or an older one."""
        self._resolves_running -= 1
        if (
            not self._resolves_running
            and self.is_running
            and not self._status_closed.is_set()
        ):
            # R is offered again.
            self.refresh_bindings()

    def _round_resolved(self) -> None:
        """Every alias of this startup or R round has reported."""
        self._resolving = False
        self._write_state()

    def _forget_alias(self, alias: str) -> None:
        """The user saved a machine with this alias, listed or not."""
        del self._missing[alias]
        if self._memory is not None:
            self._memory.forget(alias)
        self._write_state()

    def _write_state(self) -> None:
        """Save what the review and ssh -G found, next to an existing machine file."""
        if self._memory is None or self.config_path is None or self.file_text is None:
            return
        text = format_state(self._memory, self._computer)
        if text == self._state_text:
            return
        try:
            save_state(state_path(self.config_path, self._computer), text)
        except OSError:
            # The state is a cache; losing it only loses rename offers.
            return
        self._state_text = text

    def _check(
        self,
        round_id: int,
        machine: Machine,
        resolve: bool,
        target: AliasTarget | None,
    ) -> None:
        if self._status_closed.is_set():
            return
        resolved = resolve and machine.alias is not None
        try:
            if resolved:
                target = self.checker.resolve_alias(machine.alias)
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
        if message.alias is not None:
            self._resolve_reported()
        if (
            self._status_closed.is_set()
            or not self.is_running
            or message.round != self._round
        ):
            return
        self._checking.discard(message.machine_id)
        if message.alias is not None:
            self._targets[message.alias] = message.target
            if message.target is not None and self._memory is not None:
                self._memory.remember(message.alias, message.target)
            if message.alias in self._pending_aliases:
                self._pending_aliases.discard(message.alias)
                if not self._pending_aliases:
                    self._round_resolved()
        if message.machine_id in {machine.id for machine in self.machines}:
            self._statuses[message.machine_id] = message.status
            if message.status.state is State.ONLINE and message.status.address:
                self._online[message.machine_id] = message.status.address
            else:
                self._online.pop(message.machine_id, None)
            self._show_statuses()

    def _show_statuses(self) -> None:
        self._update_summary()
        machine_list = self._machine_list()
        if machine_list is None or self._rebuilding:
            return
        for symbol, machine in zip(
            machine_list.query(StatusSymbol), self.machines, strict=False
        ):
            symbol.state = self._status_of(machine).state
        index = machine_list.index
        if index is not None and index < len(self.machines):
            machine = self.machines[index]
            self._show_status(machine)
            # A review changes whether the alias is marked.
            self.query_one("#machine-target", Static).update(self._target_text(machine))

    def _tick_animation(self) -> None:
        if self.animation_level == "none" or not self.is_running:
            return
        self._frame += 1
        for symbol in self.query(StatusSymbol):
            # Only the spinner and the Online pulse move.
            if symbol.state in (State.CHECKING, State.ONLINE):
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
            ready = (
                self.checker is not None
                and self._browsing()
                and self.machines
                and not self._resolves_running
            )
            return True if ready else None
        if action == "add":
            return True if self._browsing() and self.config_path is not None else None
        if action == "key_setup":
            index = self._selected_index()
            if index is None:
                return None
            machine = self.machines[index]
            # A missing alias can't be reached, and a new key needs a file to go in.
            if machine.alias in self._missing or (
                machine.alias is None
                and machine.key is None
                and self.config_path is None
            ):
                return None
            return True
        if action == "update_alias":
            index = self._selected_index()
            # Hidden, not dimmed: it appears only with a rename offer.
            return (
                index is not None
                and self.config_path is not None
                and self._rename_offer(self.machines[index]) is not None
            )
        if action in ("connect", "open_link", "edit", "delete"):
            index = self._selected_index()
            if index is None:
                return None
            if action == "connect" and self.machines[index].alias in self._missing:
                # Hidden until the alias is fixed; U takes its place.
                return False
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
            # Workbench's own exported entries are not the user's Host names.
            host_names=(
                host_names(folder, skip=folder / EXPORT_NAME)
                if folder is not None
                else ()
            ),
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

    def action_update_alias(self) -> None:
        index = self._selected_index()
        if index is None or self.check_action("update_alias", ()) is not True:
            return
        machine = self.machines[index]
        new = self._rename_offer(machine)
        status = self.query_one("#connection-status", Static)
        warning = self._rewrite_warning()
        if warning is not None and self._update_armed != (machine.id, new):
            self._update_armed = (machine.id, new)
            status.update(f"{warning} Press U again to update.")
            return
        self._update_armed = None
        machines = list(self.machines)
        machines[index] = replace(machine, alias=new)
        problem = self._save(machines, index, retry="update")
        status.update(
            problem
            or f"Updated machine {index + 1}: {_display_text(machine.id)} "
            f"now uses alias {_display_text(new)}."
        )

    def _save_one(self, machines: list[Machine], position: int) -> str | None:
        problem = self._save(machines, position)
        if problem is None:
            # Saving from the form confirms the alias, even one no longer listed.
            if machines[position].alias in self._missing:
                self._forget_alias(machines[position].alias)
            # Offered after the rebuild, once the form has closed.
            self._include_offer = machines[position].export_alias
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
        # Rewritten from the machine file on every save.
        self._export_problem = self._write_exports()
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
        if not self.is_running:
            return
        self._initial_index = min(max(select, 0), max(len(self.machines) - 1, 0))
        try:
            await self.query_one(MachinePanes).recompose()
        finally:
            self._rebuilding = False
        self._update_summary()
        machine_list = self._machine_list()
        if machine_list is not None:
            self._show_details(self._initial_index)
            # The browser may sit under a form; focus returns here when it closes.
            self.screen_stack[0].set_focus(machine_list)
        self.refresh_bindings()
        if self.checker is not None:
            self._start_round(resolve=False)
        if self._export_problem is not None:
            status = self.query_one("#connection-status", Static)
            status.update(f"{status.content} {self._export_problem}")
            self._export_problem = None
            # The Include line would only point at a file that wasn't written,
            # and answering the question would hide this message.
            self._include_offer = False
        if self._include_offer and self._browsing():
            self._include_offer = False
            self._offer_include()

    def _write_exports(self) -> str | None:
        """Rewrite Workbench's own SSH config file; return a problem to show."""
        folder = ssh_folder()
        if folder is None:
            if any(machine.export_alias for machine in self.machines):
                return "Could not find your SSH folder for exported aliases."
            return None
        try:
            # A relative --config path would name a different file elsewhere.
            write_exports(folder, self.machines, self.config_path.absolute())
        except ExportError as error:
            return str(error)
        return None

    def _offer_include(self) -> None:
        """Ask for the Include line unless the SSH config has it or N was said."""
        folder = ssh_folder()
        if folder is None or self._include_declined:
            return
        config = folder / "config"
        try:
            exists = config.is_file()
            text = config.read_bytes().decode("utf-8", "replace") if exists else ""
        except OSError:
            return
        if include_present(text):
            return
        self.push_screen(
            ConfirmInclude(config, exists),
            lambda add: self._include_answered(config, exists, bool(add)),
        )

    def _include_answered(self, config: Path, exists: bool, add: bool) -> None:
        status = self.query_one("#connection-status", Static)
        if not add:
            self._include_declined = True
            status.update(
                "Exported aliases work once your SSH config starts with: "
                f"{INCLUDE_LINE}"
            )
            return
        try:
            add_include(config)
        except ExportError as error:
            status.update(str(error))
            return
        path = _display_text(str(config))
        status.update(
            f'Added "{INCLUDE_LINE}" to {path}; a copy is in {BACKUP_NAME}.'
            if exists
            else f'Created {path} with "{INCLUDE_LINE}".'
        )

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
        if (
            self._links_closed.is_set()
            or not self.is_running
            or message.request is not self._link_request
        ):
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
        if index is None or self.check_action("connect", ()) is not True:
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

    def action_key_setup(self) -> None:
        index = self._selected_index()
        if index is None or self.check_action("key_setup", ()) is not True:
            return
        machine = self.machines[index]
        if machine.alias is None or self.checker is None:
            self._open_key_setup(machine, None)
            return
        if self._key_resolving is not None:
            return
        # Key setup is one of the moments ssh -G may run: it names the keys
        # the alias offers.
        self._key_resolving = machine.id
        if not self._start_thread(self._resolve_key_target, (machine,)):
            self._key_resolving = None
            self._open_key_setup(machine, None)

    def _resolve_key_target(self, machine: Machine) -> None:
        if self._status_closed.is_set():
            return
        try:
            target = self.checker.resolve_alias(machine.alias)
        except Exception:
            target = None
        if not self._status_closed.is_set():
            try:
                self.post_message(KeyTargetResolved(machine.id, target))
            except RuntimeError:
                # The event loop may close between the guard and enqueue.
                pass

    def on_key_target_resolved(self, message: KeyTargetResolved) -> None:
        if self._status_closed.is_set() or not self.is_running:
            return
        self._key_resolving = None
        ids = [machine.id for machine in self.machines]
        if message.machine_id in ids and self._browsing():
            machine = self.machines[ids.index(message.machine_id)]
            self._open_key_setup(machine, message.target)

    def _open_key_setup(self, machine: Machine, target: AliasTarget | None) -> None:
        folder = ssh_folder()
        if folder is None:
            self._show_key_result(machine, "Could not find your SSH folder.")
            return
        # Only a direct machine without a key gets a key saved into the file.
        warning = (
            self._rewrite_warning()
            if machine.alias is None and machine.key is None
            else None
        )
        try:
            choices = self._key_choices(machine, target, folder)
        except SSHLaunchError as error:
            # A machine key under "~" needs the home folder.
            self._show_key_result(machine, str(error))
            return
        self.push_screen(
            KeySetup(machine, choices, warning),
            lambda plan: self._key_plan_chosen(machine.id, plan),
        )

    def _key_choices(
        self, machine: Machine, target: AliasTarget | None, folder: Path
    ) -> list[KeyChoice]:
        """The machine's own key; else the alias's keys, the folder's and a new one."""
        if machine.alias is None and machine.key is not None:
            private = Path(key_argument(machine.key))
            label = f"{machine.key} (this machine's key)"
            return [KeyChoice(private, label)]
        home = _home() if ssh_folder_override() is None else None
        choices: list[KeyChoice] = []
        if target is not None:
            for private in identity_paths(target.identity_files, folder):
                if _has_public_key(private):
                    label = f"{private.name}.pub (your SSH config offers this)"
                    choices.append(KeyChoice(private, label))
        offered = {choice.private for choice in choices}
        for public in public_key_files(folder):
            private = public.with_name(public.name.removesuffix(".pub"))
            if private not in offered:
                choices.append(_key_choice(machine, target, private, public.name, home))
        new = new_key_path(folder, machine.id)
        if not new.exists() and not Path(f"{new}.pub").exists():
            label = f"Create a new key: {new.name}"
            choices.append(_key_choice(machine, target, new, label, home, True))
        return choices

    def _key_plan_chosen(self, machine_id: str, plan: KeyPlan | None) -> None:
        ids = [machine.id for machine in self.machines]
        if plan is not None and machine_id in ids:
            index = ids.index(machine_id)
            self._run_key_setup(index, self.machines[index], plan)

    def _run_key_setup(self, index: int, machine: Machine, plan: KeyPlan) -> None:
        """Create, install and test the key in one terminal handoff."""
        setting = machine.key
        if machine.alias is None and setting is None:
            home = _home() if ssh_folder_override() is None else None
            try:
                setting = key_setting(plan.choice.private, home)
            except KeySetupError as error:
                self._show_key_result(machine, str(error))
                return
        if plan.windows and not plan.choice.create:
            # cmd.exe limits the command's length, so a large RSA key is refused
            # before the handoff; a new Ed25519 key always fits.
            private = plan.choice.private
            try:
                windows_install_command(
                    read_public_key(private.with_name(f"{private.name}.pub"))
                )
            except KeySetupError as error:
                self._show_key_result(machine, str(error))
                return
        machine_list = self.query_one(ListView)
        works = False
        self._connecting = True
        self.refresh_bindings()
        # Counted from here, so a Ctrl+C while the terminal is handed over
        # stops the first step too.
        pressed = ctrl_c_count()
        with ssh_handoff():
            try:
                with self.suspend():
                    # As for C: errors stay inside the suspension block, so
                    # the terminal is always handed back.
                    try:
                        message, works = self._key_steps(
                            machine, plan, setting, pressed
                        )
                    except (SSHLaunchError, KeySetupError) as error:
                        message = str(error)
                    except KeyboardInterrupt:
                        message = "Key setup interrupted."
            except SuspendNotSupported:
                message = (
                    "Cannot hand off this terminal. "
                    "Run SSH Workbench in a local terminal."
                )
            finally:
                self._connecting = False
                machine_list.focus()
                self.refresh_bindings()
            # Windows runs Workbench's Ctrl+C handler on a thread of its own,
            # which can lose the race with a test that exits 0; handing the
            # terminal back gives it time to arrive.
            if works and ctrl_c_count() != pressed:
                works = False
                message = _test_failed(machine, setting, None, None)
        if works and setting != machine.key:
            machines = list(self.machines)
            machines[index] = replace(machine, key=setting)
            problem = self._save(machines, index, retry="set up the key")
            message += (
                f" {problem}"
                if problem
                else (" The key is saved as this machine's key.")
            )
        self._show_key_result(machine, message)

    def _key_steps(
        self, machine: Machine, plan: KeyPlan, setting: str | None, pressed: int
    ) -> tuple[str, bool]:
        """Runs while the terminal is handed over; returns the result and
        whether key-only login works, which a new machine key needs before
        it is saved. `pressed` is the Ctrl+C count when the handoff began."""
        choice = plan.choice

        def run(arguments: list[str], name: str = "SSH") -> int | None:
            # A step's status, or None once Ctrl+C has reached Workbench: Windows
            # ssh can exit 0 after it, and no later step may start.
            if ctrl_c_count() != pressed:
                return None
            status = run_native(arguments, name)
            if interrupted(status) or ctrl_c_count() != pressed:
                return None
            return status

        if choice.create:
            print("SSH Workbench: creating the key; ssh-keygen asks for a passphrase.")
            status = run(keygen_arguments(choice.private, machine.id), "ssh-keygen")
            if status is None:
                return "Key setup interrupted.", False
            if status != 0:
                return (
                    f"ssh-keygen exited with status {status}; nothing was installed.",
                    False,
                )
        key = read_public_key(choice.private.with_name(f"{choice.private.name}.pub"))
        address = self._online_address(machine)
        command = (
            windows_install_command(key) if plan.windows else posix_install_command(key)
        )
        ssh = find_ssh()
        print("SSH Workbench: installing the key; SSH may ask for the password.")
        status = run([ssh, *install_arguments(machine, address, command)])
        if status is None:
            return "Key setup interrupted.", False
        if status != 0:
            return (
                f"Installing the key failed (SSH exited with status {status}); "
                "login was not tested."
            ), False
        tested = machine if setting is None else replace(machine, key=setting)
        print("SSH Workbench: testing key-only login.")
        status = run([ssh, *login_test_arguments(tested, address)])
        if status == 0:
            # A hint means the alias's config doesn't name this key, so SSH
            # offered other keys and the test cannot show which one worked.
            if choice.hint:
                return (
                    "Key-only login works, but SSH may have used another key. "
                    f"{choice.hint}"
                ), True
            return "Key login works.", True
        return _test_failed(machine, setting, status, choice.hint), False

    def _show_key_result(self, machine: Machine, message: str) -> None:
        ids = [item.id for item in self.machines]
        position = ids.index(machine.id) + 1 if machine.id in ids else "?"
        self.query_one("#connection-status", Static).update(
            f"{_display_text(message)} Machine {position}: {_display_text(machine.id)}"
        )


def _home() -> Path | None:
    try:
        return Path.home()
    except RuntimeError:
        return None


def _test_failed(
    machine: Machine, setting: str | None, status: int | None, hint: str | None
) -> str:
    """Why the login test did not show key login works; `status` is None when
    Ctrl+C interrupted it, and an interrupted test says nothing about keys."""
    if status is None:
        message = "The key was installed, but the login test was interrupted."
    else:
        message = (
            "The key was installed, but key-only login failed "
            f"(SSH exited with status {status})."
        )
        if hint:
            message += f" {hint}"
    if setting != machine.key:
        message += " The key was not saved as this machine's key."
    return message


def _has_public_key(private: Path) -> bool:
    try:
        read_public_key(private.with_name(f"{private.name}.pub"))
    except KeySetupError:
        return False
    return True


def _identity_value(private: Path, home: Path | None) -> str:
    if home is not None and private.parent == home / ".ssh":
        return f"~/.ssh/{private.name}"
    value = str(private)
    return f'"{value}"' if " " in value else value


def _key_choice(
    machine: Machine,
    target: AliasTarget | None,
    private: Path,
    label: str,
    home: Path | None,
    create: bool = False,
) -> KeyChoice:
    """A choice that an alias's own SSH config does not name explains the line
    it would need; Workbench never edits that config."""
    alias = machine.alias
    if alias is None:
        return KeyChoice(private, label, create)
    line = f"IdentityFile {_identity_value(private, home)}"
    note = (
        f"Your SSH config doesn't name this key for {alias}. Add this line under "
        f"Host {alias}; Workbench never edits the config: {line}"
    )
    if target is not None and target.identities_only:
        hint = (
            f"Your SSH config offers only its own keys for {alias} (IdentitiesOnly); "
            f"add this line under Host {alias}: {line}"
        )
    else:
        hint = (
            f"Your SSH config doesn't name this key for {alias}; add this line "
            f"under Host {alias}: {line}"
        )
    return KeyChoice(private, label, create, note, hint)
