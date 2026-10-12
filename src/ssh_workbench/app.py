"""Read-only project selection and details; no configuration or process I/O."""

from collections.abc import Sequence

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, ListItem, ListView, Static

from ssh_workbench.config import Project


def _display_text(value: str) -> str:
    """Make controls visible without interpreting markup or changing records."""
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in value)


class SSHWorkbenchApp(App[None]):
    TITLE = "SSH Workbench"
    SUB_TITLE = "Project browser - unreleased"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
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
    #navigation-help {
        height: auto;
        padding: 0 1;
    }
    #empty-content {
        padding: 1 2;
    }
    """

    def __init__(self, projects: Sequence[Project] | None = None) -> None:
        super().__init__()
        self.config_supplied = projects is not None
        self.projects = tuple(projects or ())

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
                "Up/Down: select   Tab: switch pane   Up/Down in details: scroll\n"
                "Read only. References are text; SSH is not available.",
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
                    "Try: ssh-workbench --config examples/projects.example.toml\n\n"
                    "Development build: project browsing only; SSH is not available.",
                    id="empty-state",
                    markup=False,
                )
        yield Footer()

    def on_mount(self) -> None:
        if self.projects:
            self.query_one("#project-list", ListView).focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
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
