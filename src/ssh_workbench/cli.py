"""Command-line entry point."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from ssh_workbench.config import ProjectConfigError, load_projects


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ssh-workbench",
        description=(
            "Browse local project metadata. SSH connections are not available yet."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('ssh-workbench')}"
    )
    parser.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="read projects from this TOML file (no default file or discovery)",
    )
    args = parser.parse_args(argv)

    projects = None
    if args.config is not None:
        try:
            projects = load_projects(args.config)
        except ProjectConfigError as error:
            parser.error(str(error))

    from ssh_workbench.app import SSHWorkbenchApp

    app = SSHWorkbenchApp(projects)
    app.run()
    return app.return_code
