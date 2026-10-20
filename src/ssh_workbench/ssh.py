"""Launch native SSH synchronously on the main thread with inherited terminal I/O."""

import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType

from ssh_workbench.config import is_valid_ssh_alias


class SSHLaunchError(Exception):
    """SSH could not be started; the message is safe to display."""


def _wait_for_ssh(signum: int, frame: FrameType | None) -> None:
    # A callable shields the parent without inheriting SIG_IGN in the child.
    # SSH may handle Ctrl+C and continue, so only its exit ends the handoff.
    pass


def _which_on_absolute_path(command: str) -> str | None:
    # A directory part stops shutil.which from adding the current directory.
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.isabs(directory):
            found = shutil.which(os.path.join(directory, command))
            if found is not None:
                return found
    return None


@contextmanager
def ssh_handoff() -> Iterator[None]:
    """Shield the parent until the browser has reclaimed the terminal."""
    previous_handler = signal.signal(signal.SIGINT, _wait_for_ssh)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous_handler)


def launch_ssh(alias: str) -> int:
    """Revalidate one alias and wait for native SSH; never interpret its output."""
    with ssh_handoff():
        if not is_valid_ssh_alias(alias):
            raise SSHLaunchError(
                "Invalid SSH alias. Use ASCII letters/digits, dots, underscores or "
                "hyphens, starting with a letter/digit."
            )
        try:
            command = "ssh.exe" if sys.platform == "win32" else "ssh"
            executable = shutil.which(command)
            if executable is not None and not os.path.isabs(executable):
                # Windows tries the launch directory before PATH, and a relative
                # PATH entry does the same anywhere. Never run a client found so.
                executable = _which_on_absolute_path(command)
            if executable is None:
                raise SSHLaunchError(
                    "SSH not found. Install OpenSSH and add it to PATH."
                )
            executable = str(Path(executable).resolve())
            return subprocess.run(
                [executable, alias],
                shell=False,
                check=False,
                stdin=None,
                stdout=None,
                stderr=None,
            ).returncode
        except OSError:
            raise SSHLaunchError(
                "Could not start SSH. "
                "Check its installation and executable permissions."
            ) from None
