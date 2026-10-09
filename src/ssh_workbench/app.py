"""The small runnable scaffold; project loading and SSH are planned."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Static


class SSHWorkbenchApp(App[None]):
    TITLE = "SSH Workbench"
    SUB_TITLE = "Development scaffold"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit", show=False),
    ]
    CSS = """
    #scaffold-content {
        padding: 1 2;
    }
    #scaffold-status {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="scaffold-content"):
            yield Static("Development scaffold - unreleased", id="scaffold-status")
            yield Static(
                "This screen verifies application startup and keyboard exit.\n\n"
                "Planned: select a project, inspect its context, and connect "
                "with native SSH.\n"
                "Project configuration is not loaded yet. SSH connections "
                "are not available.\n\n"
                "Press Q or Ctrl+Q to quit.",
                markup=False,
            )
        yield Footer()
