"""Launch native SSH synchronously on the main thread with inherited terminal I/O."""

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
            executable = shutil.which("ssh.exe" if sys.platform == "win32" else "ssh")
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
