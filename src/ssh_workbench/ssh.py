"""Launch native SSH synchronously on the main thread with inherited terminal I/O."""

import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType

from ssh_workbench.config import (
    Machine,
    is_valid_address,
    is_valid_key_path,
    is_valid_machine_id,
    is_valid_port,
    is_valid_ssh_alias,
    is_valid_user,
)


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


def _key_argument(key: str) -> str:
    # OpenSSH expands only "~/". Expand "~\" too, accepting either separator so
    # one machine file names the same key on Windows and Linux.
    if not key.startswith(("~/", "~\\")):
        return key
    try:
        home = Path.home()
    except RuntimeError:
        raise SSHLaunchError(
            "Could not find your home folder for this machine's key."
        ) from None
    return str(home.joinpath(*re.split(r"[\\/]+", key[2:])))


def ssh_arguments(machine: Machine, address: str | None = None) -> list[str]:
    """Revalidate a machine and return every argument after the executable.

    `--` always separates the options from the destination, as a second
    safeguard behind validation. Direct machines check host keys under their
    ID, so every address of one machine shares a single known_hosts entry.
    """
    if not machine.addresses:
        if not is_valid_ssh_alias(machine.alias):
            raise SSHLaunchError(
                "Invalid SSH alias. Use ASCII letters/digits, dots, underscores or "
                "hyphens, starting with a letter/digit."
            )
        # An alias's own SSH config decides these; ignoring them would hide that.
        if address is not None or any(
            value is not None for value in (machine.user, machine.port, machine.key)
        ):
            raise SSHLaunchError(
                "Invalid machine settings. Check its ID, user, addresses, port and key."
            )
        return ["--", machine.alias]
    if (
        machine.alias is not None
        or type(machine.addresses) is not tuple
        or not all(is_valid_address(value) for value in machine.addresses)
        or not is_valid_machine_id(machine.id)
        or (machine.user is not None and not is_valid_user(machine.user))
        or (machine.port is not None and not is_valid_port(machine.port))
        or (machine.key is not None and not is_valid_key_path(machine.key))
        or (address is not None and address not in machine.addresses)
    ):
        raise SSHLaunchError(
            "Invalid machine settings. Check its ID, user, addresses, port and key."
        )
    arguments = ["-o", f"HostKeyAlias={machine.id}"]
    if machine.user is not None:
        arguments += ["-l", machine.user]
    if machine.port is not None:
        arguments += ["-p", str(machine.port)]
    if machine.key is not None:
        arguments += ["-i", _key_argument(machine.key), "-o", "IdentitiesOnly=yes"]
    return [*arguments, "--", machine.addresses[0] if address is None else address]


def find_ssh() -> str:
    """Resolve the native client from absolute PATH entries only."""
    command = "ssh.exe" if sys.platform == "win32" else "ssh"
    executable = shutil.which(command)
    if executable is not None and not os.path.isabs(executable):
        # Windows tries the launch directory before PATH, and a relative
        # PATH entry does the same anywhere. Never run a client found so.
        executable = _which_on_absolute_path(command)
    if executable is None:
        raise SSHLaunchError("SSH not found. Install OpenSSH and add it to PATH.")
    return str(Path(executable).resolve())


def launch_ssh(machine: Machine, address: str | None = None) -> int:
    """Revalidate one machine and wait for native SSH; never read its output."""
    with ssh_handoff():
        arguments = ssh_arguments(machine, address)
        try:
            return subprocess.run(
                [find_ssh(), *arguments],
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
