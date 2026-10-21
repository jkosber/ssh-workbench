"""Machine status: TCP port checks and SSH's own view of an alias.

This is Workbench's only network code. A check opens a TCP connection to the
SSH port and closes it at once: it sends nothing, logs in nowhere and uses no
ICMP. `resolve_alias` asks native SSH (`ssh -G`) where an alias points; it runs
only when the app asks, never on the status timer.
"""

import re
import socket
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from ssh_workbench.config import Machine, is_valid_ssh_alias
from ssh_workbench.ssh import SSHLaunchError, find_ssh
from ssh_workbench.sshconfig import ssh_folder_override


class State(Enum):
    """Each state has a word and a distinct symbol, so color is never needed."""

    CHECKING = ("Checking", "◐")
    ONLINE = ("Online", "●")
    OFFLINE = ("Offline", "○")
    UNKNOWN = ("Can't check", "◇")
    NOT_CHECKED = ("Not checked", "·")
    NOT_FOUND = ("Alias not found", "×")

    def __init__(self, word: str, symbol: str) -> None:
        self.word = word
        self.symbol = symbol


@dataclass(frozen=True)
class AliasTarget:
    host: str
    port: int
    proxied: bool
    # Recorded for rename suggestions; never displayed.
    user: str = ""
    # The keys SSH offers for the alias, as `ssh -G` prints them, for key setup.
    identity_files: tuple[str, ...] = ()
    identities_only: bool = False


@dataclass(frozen=True)
class MachineStatus:
    state: State
    # The direct address that answered; None for alias machines ("via alias").
    address: str | None = None
    reason: str | None = None


def port_open(host: str, port: int, timeout: float = 3.0) -> bool:
    """Whether a TCP connection to the port opens; the connection is closed unused."""
    try:
        connection = socket.create_connection((host, port), timeout=timeout)
    except OSError:
        return False
    connection.close()
    return True


def resolve_alias(alias: str, timeout: float = 10.0) -> AliasTarget | None:
    """The host and port native SSH would use for an alias, or None.

    `ssh -G` evaluates the whole SSH config, including `Match exec` lines that
    run commands, so callers run it only at startup and on refresh. Its output
    is parsed, never shown.
    """
    if not is_valid_ssh_alias(alias):
        return None
    try:
        command = [find_ssh(), "-G"]
        override = ssh_folder_override()
        if override is not None:
            command += ["-F", str(override / "config")]
        result = subprocess.run(
            [*command, "--", alias],
            shell=False,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            # On Windows a timeout still waits for every captured pipe to
            # close, and a Match exec child can hold stderr open; it is unread.
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except SSHLaunchError, OSError, subprocess.SubprocessError:
        return None
    if result.returncode != 0:
        return None
    values: dict[str, str] = {}
    identity_files: list[str] = []
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key.lower() == "identityfile":
            identity_files.append(value.strip())
        values.setdefault(key.lower(), value.strip())
    host, port = values.get("hostname"), values.get("port", "")
    if not host or re.fullmatch(r"[0-9]{1,5}", port) is None:
        return None
    proxied = any(
        values.get(key, "none").lower() != "none"
        for key in ("proxyjump", "proxycommand")
    )
    return AliasTarget(
        host,
        int(port),
        proxied,
        values.get("user", ""),
        tuple(identity_files),
        values.get("identitiesonly", "no").lower() == "yes",
    )


def check_machine(
    machine: Machine,
    target: AliasTarget | None,
    reachable: Callable[[str, int], bool],
) -> MachineStatus:
    """Direct machines: the first listed address that answers. Aliases: `target`."""
    if machine.alias is None:
        port = machine.port or 22
        for address in machine.addresses:
            if reachable(address, port):
                return MachineStatus(State.ONLINE, address=address)
        return MachineStatus(State.OFFLINE)
    if target is None:
        return MachineStatus(State.UNKNOWN, reason="SSH could not resolve the alias")
    if target.proxied:
        # A direct port test would say nothing about a route through a proxy.
        return MachineStatus(
            State.UNKNOWN, reason="the alias uses ProxyJump or ProxyCommand"
        )
    reached = reachable(target.host, target.port)
    return MachineStatus(State.ONLINE if reached else State.OFFLINE)


class StatusChecker:
    """The real boundary; tests give the app an object with these two methods."""

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return resolve_alias(alias)

    def port_open(self, host: str, port: int) -> bool:
        return port_open(host, port)
