"""Status checks with every network and process boundary substituted."""

import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from ssh_workbench import status
from ssh_workbench.config import Machine
from ssh_workbench.ssh import SSHLaunchError
from ssh_workbench.status import (
    AliasTarget,
    MachineStatus,
    State,
    StatusChecker,
    check_machine,
    port_open,
    resolve_alias,
)

pytestmark = pytest.mark.usefixtures("no_external_actions")

G_OUTPUT = (
    "user dev\nhostname 192.0.2.40\nport 2222\nidentitiesonly no\n"
    "proxycommand none\nproxyjump none\n"
)
# ssh -G evaluates Match exec; its children must not reach Workbench's terminal.
DETACHED = (
    {"creationflags": subprocess.CREATE_NO_WINDOW}
    if sys.platform == "win32"
    else {"start_new_session": True}
)


def test_port_open_connects_and_closes_without_sending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = Mock(spec=socket.socket)
    create = Mock(return_value=connection)
    monkeypatch.setattr(status.socket, "create_connection", create)

    assert port_open("host.example", 2222) is True

    create.assert_called_once_with(("host.example", 2222), timeout=3.0)
    connection.close.assert_called_once_with()
    connection.send.assert_not_called()
    connection.sendall.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        ConnectionRefusedError(),
        TimeoutError(),
        socket.gaierror(),
        OSError("private-marker"),
    ],
)
def test_closed_or_unreachable_port_is_offline(
    monkeypatch: pytest.MonkeyPatch, error: OSError
) -> None:
    monkeypatch.setattr(status.socket, "create_connection", Mock(side_effect=error))
    assert port_open("fd7a:115c:a1e0::1", 22, timeout=0.5) is False


def substitute_ssh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, outcome: object
) -> Mock:
    monkeypatch.setattr(status, "find_ssh", lambda: str(tmp_path / "ssh"))
    run = Mock(side_effect=outcome if isinstance(outcome, BaseException) else None)
    run.return_value = outcome
    monkeypatch.setattr(status.subprocess, "run", run)
    return run


def test_resolve_alias_runs_ssh_g_without_a_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SSH_WORKBENCH_SSH_DIR")
    run = substitute_ssh(
        monkeypatch, tmp_path, subprocess.CompletedProcess([], 0, G_OUTPUT, "")
    )

    assert resolve_alias("lab-host") == AliasTarget(
        "192.0.2.40", 2222, proxied=False, user="dev"
    )

    run.assert_called_once_with(
        [str(tmp_path / "ssh"), "-G", "--", "lab-host"],
        shell=False,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        # A Match exec child that keeps a captured stderr open would make the
        # Windows timeout wait for it; stderr is never read.
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
        timeout=10.0,
        **DETACHED,
    )


def test_resolve_alias_reads_the_overridden_ssh_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    folder = tmp_path / "fictional-ssh"
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    run = substitute_ssh(
        monkeypatch, tmp_path, subprocess.CompletedProcess([], 0, G_OUTPUT, "")
    )

    resolve_alias("lab-host")

    assert run.call_args.args[0] == [
        str(tmp_path / "ssh"),
        "-G",
        "-F",
        str(folder / "config"),
        "--",
        "lab-host",
    ]


@pytest.mark.parametrize(
    "output",
    [
        G_OUTPUT.replace("proxyjump none", "proxyjump bastion.example"),
        G_OUTPUT.replace("proxycommand none", "proxycommand ssh -W %h:%p bastion"),
    ],
)
def test_proxied_alias_is_marked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, output: str
) -> None:
    substitute_ssh(
        monkeypatch, tmp_path, subprocess.CompletedProcess([], 0, output, "")
    )
    assert resolve_alias("lab-host") == AliasTarget(
        "192.0.2.40", 2222, proxied=True, user="dev"
    )


def test_resolve_alias_without_a_user_line_has_an_empty_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    substitute_ssh(
        monkeypatch,
        tmp_path,
        subprocess.CompletedProcess([], 0, "hostname 192.0.2.40\nport 22\n", ""),
    )
    assert resolve_alias("lab-host") == AliasTarget(
        "192.0.2.40", 22, proxied=False, user=""
    )


def test_resolve_alias_reports_the_keys_the_alias_offers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = G_OUTPUT.replace("identitiesonly no", "identitiesonly yes") + (
        "identityfile ~/.ssh/id_ed25519_lab\nidentityfile C:/Fictional Keys/id_lab\n"
    )
    substitute_ssh(
        monkeypatch, tmp_path, subprocess.CompletedProcess([], 0, output, "")
    )
    assert resolve_alias("lab-host") == AliasTarget(
        "192.0.2.40",
        2222,
        proxied=False,
        user="dev",
        identity_files=("~/.ssh/id_ed25519_lab", "C:/Fictional Keys/id_lab"),
        identities_only=True,
    )


@pytest.mark.parametrize(
    "outcome",
    [
        subprocess.CompletedProcess([], 255, "", "private-marker error"),
        subprocess.CompletedProcess([], 0, "user dev\nport 22\n", ""),
        subprocess.CompletedProcess([], 0, "hostname h\nport twenty\n", ""),
        subprocess.TimeoutExpired(["ssh"], 10.0),
        OSError("private-marker"),
        SSHLaunchError("SSH not found."),
    ],
)
def test_unresolvable_alias_is_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, outcome: object
) -> None:
    if isinstance(outcome, SSHLaunchError):

        def missing() -> str:
            raise outcome

        monkeypatch.setattr(status, "find_ssh", missing)
    else:
        substitute_ssh(monkeypatch, tmp_path, outcome)
    assert resolve_alias("lab-host") is None


@pytest.mark.parametrize("alias", ["-oProxyCommand=x", "two words", "", "a@b"])
def test_invalid_alias_never_starts_a_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, alias: str
) -> None:
    run = substitute_ssh(
        monkeypatch, tmp_path, AssertionError("Unexpected child process")
    )
    assert resolve_alias(alias) is None
    run.assert_not_called()


def answering(*hosts: str):
    calls: list[tuple[str, int]] = []

    def check(host: str, port: int) -> bool:
        calls.append((host, port))
        return host in hosts

    return check, calls


def test_direct_machine_uses_the_first_address_that_answers() -> None:
    machine = Machine(
        "box", "Box", addresses=("10.0.0.1", "192.0.2.2", "192.0.2.3"), port=2222
    )
    check, calls = answering("192.0.2.2", "192.0.2.3")

    assert check_machine(machine, None, check) == MachineStatus(
        State.ONLINE, address="192.0.2.2"
    )
    assert calls == [("10.0.0.1", 2222), ("192.0.2.2", 2222)]


def test_direct_machine_without_answers_is_offline_on_port_22() -> None:
    machine = Machine("box", "Box", addresses=("fd7a:115c:a1e0::1", "box.example"))
    check, calls = answering()

    assert check_machine(machine, None, check) == MachineStatus(State.OFFLINE)
    assert calls == [("fd7a:115c:a1e0::1", 22), ("box.example", 22)]


@pytest.mark.parametrize(
    ("target", "answers", "expected"),
    [
        (
            None,
            (),
            MachineStatus(State.UNKNOWN, reason="SSH could not resolve the alias"),
        ),
        (
            AliasTarget("192.0.2.40", 2222, proxied=True),
            ("192.0.2.40",),
            MachineStatus(
                State.UNKNOWN, reason="the alias uses ProxyJump or ProxyCommand"
            ),
        ),
        (
            AliasTarget("192.0.2.40", 2222, proxied=False),
            ("192.0.2.40",),
            MachineStatus(State.ONLINE),
        ),
        (
            AliasTarget("192.0.2.40", 2222, proxied=False),
            (),
            MachineStatus(State.OFFLINE),
        ),
    ],
)
def test_alias_machine_status(
    target: AliasTarget | None, answers: tuple[str, ...], expected: MachineStatus
) -> None:
    check, calls = answering(*answers)
    machine = Machine("lab", "Lab", alias="lab-host")

    assert check_machine(machine, target, check) == expected
    if target is None or target.proxied:
        assert calls == []
    else:
        assert calls == [("192.0.2.40", 2222)]


def test_state_words_and_symbols_are_all_different() -> None:
    words = [state.word for state in State]
    symbols = [state.symbol for state in State]
    assert words == [
        "checking",
        "online",
        "offline",
        "can't check",
        "not checked",
        "alias not found",
    ]
    assert len(set(symbols)) == len(symbols)
    assert all(symbol.strip() for symbol in symbols)


def test_alias_not_found_has_its_own_word_and_symbol() -> None:
    assert (State.NOT_FOUND.word, State.NOT_FOUND.symbol) == (
        "alias not found",
        "×",
    )


def test_status_checker_uses_the_module_functions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        status, "port_open", lambda host, port: (host, port) == ("h", 1)
    )
    monkeypatch.setattr(
        status, "resolve_alias", lambda alias: AliasTarget(alias, 9, False)
    )
    checker = StatusChecker()
    assert checker.port_open("h", 1) is True
    assert checker.resolve_alias("lab-host") == AliasTarget("lab-host", 9, False)
