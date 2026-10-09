"""Command-line entry point."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ssh-workbench",
        description=(
            "SSH Workbench development scaffold. SSH connections are not available yet."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('ssh-workbench')}"
    )
    parser.parse_args(argv)

    from ssh_workbench.app import SSHWorkbenchApp

    app = SSHWorkbenchApp()
    app.run()
    return app.return_code
