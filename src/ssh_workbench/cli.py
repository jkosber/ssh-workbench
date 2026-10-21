"""Command-line entry point."""

import argparse
import os
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from ssh_workbench.config import ConfigError, load_machines


def default_config_path() -> Path | None:
    """Locate the per-user machine file without reading or creating anything."""
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
    return root / "ssh-workbench" / "machines.toml"


def _help_text(path: Path) -> str:
    """Make a path safe in help: visible and encodable by stdout. Without this,
    redirected help on a cp1252 console can crash."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    visible = "".join(c if c.isprintable() else ascii(c)[1:-1] for c in str(path))
    return visible.encode(encoding, "backslashreplace").decode(encoding)


def _epilog(path: Path | None) -> str:
    if path is None:
        return "No default machine file location is available."
    text = f"Default machine file:\n  {_help_text(path)}"
    # argparse %-formats an epilog only when it contains "%(prog)".
    return text.replace("%", "%%") if "%(prog)" in text else text


def main(argv: Sequence[str] | None = None) -> int:
    default_config = default_config_path()
    parser = argparse.ArgumentParser(
        prog="ssh-workbench",
        description="Browse your machines and connect with native SSH.",
        epilog=_epilog(default_config),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('ssh-workbench')}"
    )
    parser.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="read machines from this TOML file instead of the default file",
    )
    args = parser.parse_args(argv)

    machines = None
    config_path = default_config
    if args.config is not None:
        config_path = args.config
        try:
            machines = load_machines(args.config)
        except ConfigError as error:
            parser.error(str(error))
    elif default_config is not None and default_config.exists():
        try:
            machines = load_machines(default_config)
        except ConfigError as error:
            detail = str(error).removeprefix("configuration: ")
            parser.error(f"default configuration file: {detail}")

    from ssh_workbench.app import SSHWorkbenchApp

    app = SSHWorkbenchApp(machines, config_path=config_path)
    app.run()
    return app.return_code
