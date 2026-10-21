"""Command-line entry point."""

import argparse
import os
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from ssh_workbench.config import ProjectConfigError, load_projects


def default_config_path() -> Path | None:
    """Locate the per-user projects file without reading or creating anything."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", ""))
    else:
        # The XDG specification says to ignore relative values.
        root = Path(os.environ.get("XDG_CONFIG_HOME", ""))
        if not root.is_absolute():
            try:
                root = Path.home() / ".config"
            except RuntimeError:
                return None
    if not root.is_absolute():
        return None
    return root / "ssh-workbench" / "projects.toml"


def _help_text(path: Path) -> str:
    """Make a path safe in help: visible, encodable by stdout and %-formatted by
    argparse. Without this, redirected help on a cp1252 console can crash."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    visible = "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))
    return (
        visible.encode(encoding, "backslashreplace").decode(encoding).replace("%", "%%")
    )


def main(argv: Sequence[str] | None = None) -> int:
    default_config = default_config_path()
    parser = argparse.ArgumentParser(
        prog="ssh-workbench",
        description="Browse local projects and explicitly connect with native SSH.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('ssh-workbench')}"
    )
    parser.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="read projects from this TOML file "
        + (
            f"(default: {_help_text(default_config)})"
            if default_config is not None
            else "(no default location available)"
        ),
    )
    args = parser.parse_args(argv)

    projects = None
    if args.config is not None:
        try:
            projects = load_projects(args.config)
        except ProjectConfigError as error:
            parser.error(str(error))
    elif default_config is not None and default_config.is_file():
        try:
            projects = load_projects(default_config)
        except ProjectConfigError as error:
            detail = str(error).removeprefix("configuration: ")
            parser.error(f"default configuration file: {detail}")

    from ssh_workbench.app import SSHWorkbenchApp

    app = SSHWorkbenchApp(projects, default_config=default_config)
    app.run()
    return app.return_code
