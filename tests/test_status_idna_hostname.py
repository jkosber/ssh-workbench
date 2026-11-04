"""A host name with an empty label, or a label of 64 or more characters.

OpenSSH accepts such a HostName and `ssh -G` prints it, so an alias can point
at `lab..example.test`. Python's lookup encodes the name with the IDNA codec
before it asks any resolver, and the codec raises UnicodeEncodeError, not an
OSError. The status check must still say offline, as for any host that does
not answer. The real `create_connection` and lookup run here, with
AI_NUMERICHOST added so no name ever reaches a resolver, and any connection
attempt fails the test.
"""

import socket

import pytest

from ssh_workbench.config import Machine
from ssh_workbench.status import (
    AliasTarget,
    MachineStatus,
    State,
    StatusChecker,
    check_machine,
    port_open,
)

pytestmark = pytest.mark.usefixtures("no_external_actions")

# Taken at import, before no_external_actions replaces both with failures.
REAL_CREATE_CONNECTION = socket.create_connection
REAL_GETADDRINFO = socket.getaddrinfo

REJECTED_HOSTS = (
    "lab..example.test",
    ".example.test",
    "a" * 64 + ".example.test",
)
LAB = Machine("lab", "Lab", alias="lab-host")


class Network:
    def __init__(self) -> None:
        self.failed_lookups: list[tuple[str, type[Exception]]] = []
        self.connections: list[object] = []


@pytest.fixture
def network(monkeypatch: pytest.MonkeyPatch) -> Network:
    """The real create_connection and lookup, without a resolver or a connection."""
    network = Network()

    def numeric_only(host, port, family=0, socktype=0, proto=0, flags=0):
        try:
            return REAL_GETADDRINFO(
                host, port, family, socktype, proto, flags | socket.AI_NUMERICHOST
            )
        except Exception as error:
            network.failed_lookups.append((host, type(error)))
            raise

    def no_connection(sock: socket.socket, address: object) -> None:
        network.connections.append(address)
        raise AssertionError("port_open attempted a connection")

    monkeypatch.setattr(socket, "create_connection", REAL_CREATE_CONNECTION)
    monkeypatch.setattr(socket, "getaddrinfo", numeric_only)
    monkeypatch.setattr(socket.socket, "connect", no_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", no_connection)
    return network


@pytest.mark.parametrize("host", REJECTED_HOSTS)
def test_host_the_idna_codec_rejects_is_offline_without_a_connection(
    network: Network, host: str
) -> None:
    assert port_open(host, 22) is False

    assert network.failed_lookups == [(host, UnicodeEncodeError)]
    assert network.connections == []


@pytest.mark.parametrize("host", REJECTED_HOSTS)
def test_alias_whose_host_the_idna_codec_rejects_is_offline(
    network: Network, host: str
) -> None:
    target = AliasTarget(host, 22, proxied=False)

    status = check_machine(LAB, target, StatusChecker().port_open)

    assert status == MachineStatus(State.OFFLINE)
    assert (status.state.word, status.state.symbol) == ("offline", "○")
    assert network.failed_lookups == [(host, UnicodeEncodeError)]
    assert network.connections == []


def test_valid_host_whose_connection_fails_is_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[str, int], float]] = []

    def refused(address: tuple[str, int], timeout: float) -> socket.socket:
        calls.append((address, timeout))
        raise ConnectionRefusedError()

    monkeypatch.setattr(socket, "create_connection", refused)
    target = AliasTarget("192.0.2.10", 22, proxied=False)

    assert port_open("192.0.2.10", 22) is False
    assert check_machine(LAB, target, StatusChecker().port_open) == MachineStatus(
        State.OFFLINE
    )
    assert calls == [(("192.0.2.10", 22), 3.0), (("192.0.2.10", 22), 3.0)]
