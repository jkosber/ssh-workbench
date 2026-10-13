"""Project selection, literal details and explicit SSH and link actions."""

from collections.abc import Sequence
from dataclasses import dataclass
from threading import Event, Thread
from typing import Literal

from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import Footer, Header, ListItem, ListView, Static

from ssh_workbench.config import Project
from ssh_workbench.links import LinkResult, open_link
from ssh_workbench.ssh import SSHLaunchError, launch_ssh, ssh_handoff


def _display_text(value: str) -> str:
    """Make controls visible without interpreting markup or changing records."""
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in value)


@dataclass(frozen=True)
class LinkRequest:
    project: Project
    kind: Literal["Repository", "Documentation"]
    url: str | None
    position: int


@dataclass
class LinkFinished(Message):
    request: LinkRequest
    result: LinkResult


class SSHWorkbenchApp(App[None]):
    TITLE = "SSH Workbench"
    SUB_TITLE = "Project browser - unreleased"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("c", "connect", "Connect"),
        Binding("r", "repository", "Repository"),
        Binding("d", "documentation", "Documentation"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]
    CSS = """
    #browser {
        height: 1fr;
    }
    #project-list {
        width: 1fr;
        min-width: 20;
        border: solid $panel;
    }
    #project-list:focus, #project-details:focus {
        border: solid $accent;
    }
    #project-list ListItem {
        height: 1;
        padding: 0 1;
    }
    #project-list Static {
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    #project-details {
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

    def __init__(self, projects: Sequence[Project] | None = None) -> None:
        super().__init__()
        self.config_supplied = projects is not None
        self.projects = tuple(projects or ())
        self._connecting = False
        self._link_request: LinkRequest | None = None
        self._links_closed = Event()

    def compose(self) -> ComposeResult:
        yield Header()
        if self.projects:
            with Horizontal(id="browser"):
                project_list = ListView(
                    *(
                        ListItem(Static(_display_text(project.name), markup=False))
                        for project in self.projects
                    ),
                    initial_index=0,
                    id="project-list",
                )
                project_list.border_title = "Projects"
                yield project_list
                with VerticalScroll(id="project-details") as details:
                    details.border_title = "Project details"
                    for field, label in (
                        ("id", "ID"),
                        ("name", "Name"),
                        ("ssh-alias", "SSH alias"),
                        ("repository", "Repository"),
                        ("documentation", "Documentation"),
                    ):
                        yield Static(label, classes="field-label", markup=False)
                        yield Static(
                            id=f"project-{field}", classes="field-value", markup=False
                        )
            yield Static(
                "Up/Down: select   Tab: switch pane   Up/Down in details: scroll",
                id="navigation-help",
                markup=False,
            )
        else:
            with VerticalScroll(id="empty-content"):
                yield Static(
                    "No projects in this configuration.\n\n"
                    "Add project entries to the file, then restart with --config PATH."
                    if self.config_supplied
                    else "No configuration selected.\n\n"
                    "To browse projects, restart with --config PATH.\n"
                    "Try: ssh-workbench --config examples/projects.example.toml",
                    id="empty-state",
                    markup=False,
                )
        yield Static(
            "C: connect to the selected SSH alias."
            if self.projects
            else "Select a project to connect.",
            id="connection-status",
            markup=False,
        )
        yield Static(
            "R: repository   D: documentation   Opens in this environment.",
            id="link-status",
            markup=False,
        )
        yield Footer()

    def on_mount(self) -> None:
        if self.projects:
            self.query_one("#project-list", ListView).focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self.refresh_bindings()
        index = event.list_view.index
        if index is None:
            return
        project = self.projects[index]
        for field, value in (
            ("id", project.id),
            ("name", project.name),
            ("ssh-alias", project.ssh_alias),
            ("repository", project.repository),
            ("documentation", project.documentation),
        ):
            self.query_one(f"#project-{field}", Static).update(
                _display_text(value) if value is not None else "Not provided"
            )
        self.query_one("#project-details", VerticalScroll).scroll_home(animate=False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "connect":
            if self._connecting or not self.projects:
                return None
            return True if self.query_one(ListView).index is not None else None
        return True

    def action_repository(self) -> None:
        self._open_project_link("Repository")

    def action_documentation(self) -> None:
        self._open_project_link("Documentation")

    def _open_project_link(self, kind: Literal["Repository", "Documentation"]) -> None:
        if self._links_closed.is_set():
            return
        status = self.query_one("#link-status", Static)
        if self._link_request is not None:
            request = self._link_request
            self._show_link_result(
                request, "browser request still pending. Wait or Q to quit."
            )
            return
        index = self.query_one(ListView).index if self.projects else None
        if index is None:
            status.update(f"{kind}: select a project first.")
            return
        project = self.projects[index]
        request = LinkRequest(project, kind, getattr(project, kind.lower()), index + 1)
        if request.url is None:
            self._show_link_result(request, LinkResult.MISSING.value)
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
            result = open_link(request.url)
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
            f"{request.kind} {result} "
            f"Project {request.position}: {_display_text(request.project.id)}"
        )

    def on_unmount(self) -> None:
        self._links_closed.set()
        self._link_request = None

    def action_connect(self) -> None:
        if self._connecting or not self.projects:
            return
        project_list = self.query_one(ListView)
        index = project_list.index
        if index is None:
            return
        self._connecting = True
        self.refresh_bindings()
        with ssh_handoff():
            try:
                with self.suspend():
                    # Textual 8.2.8 resumes only on a normal context exit. Handle
                    # launch errors here so they cannot skip terminal restoration.
                    try:
                        status = launch_ssh(self.projects[index].ssh_alias)
                    except SSHLaunchError as error:
                        message = str(error)
                    except KeyboardInterrupt:
                        message = "SSH interrupted. Press C to retry or Q to quit."
                    else:
                        message = f"SSH exited with status {status}."
                        if status != 0:
                            message += (
                                " Check the SSH client's message and alias; C retries."
                            )
            except SuspendNotSupported:
                message = (
                    "Cannot hand off this terminal. "
                    "Run SSH Workbench in a local terminal."
                )
            finally:
                self._connecting = False
                project_list.focus()
                self.refresh_bindings()
            self.query_one("#connection-status", Static).update(message)
