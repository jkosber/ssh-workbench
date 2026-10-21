import asyncio
import os
import signal
import socket
import subprocess
import sys
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import ListView, Static

from ssh_workbench import ssh
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine

pytestmark = pytest.mark.usefixtures("no_external_actions")

FICTIONAL = Machine("fictional", "Fictional", alias="fictional-host")
DIRECT = Machine(
    "agent-box",
    "Agent box",
    user="dev",
    addresses=("100.64.0.12", "192.168.1.40"),
    port=2222,
    key="C:\\Fictional Keys\\id_ed25519_agent_box",
)
INVALID_MACHINE = (
    "Invalid machine settings. Check its ID, user, addresses, port and key."
)


@pytest.mark.parametrize(
    ("machine", "address", "expected"),
    [
        (
            DIRECT,
            None,
            [
                "-o",
                "HostKeyAlias=agent-box",
                "-l",
                "dev",
                "-p",
                "2222",
                "-i",
                "C:\\Fictional Keys\\id_ed25519_agent_box",
                "-o",
                "IdentitiesOnly=yes",
                "--",
                "100.64.0.12",
            ],
        ),
        (
            DIRECT,
            "192.168.1.40",
            [
                "-o",
                "HostKeyAlias=agent-box",
                "-l",
                "dev",
                "-p",
                "2222",
                "-i",
                "C:\\Fictional Keys\\id_ed25519_agent_box",
                "-o",
                "IdentitiesOnly=yes",
                "--",
                "192.168.1.40",
            ],
        ),
        (
            Machine("box", "Box", addresses=("box.example",)),
            None,
            ["-o", "HostKeyAlias=box", "--", "box.example"],
        ),
        (
            Machine("v6", "IPv6", addresses=("fd7a:115c:a1e0::1",)),
            None,
            ["-o", "HostKeyAlias=v6", "--", "fd7a:115c:a1e0::1"],
        ),
        (
            Machine("posix", "POSIX", addresses=("host",), key="/home/dev/.ssh/id"),
            None,
            [
                "-o",
                "HostKeyAlias=posix",
                "-i",
                "/home/dev/.ssh/id",
                "-o",
                "IdentitiesOnly=yes",
                "--",
                "host",
            ],
        ),
        (FICTIONAL, None, ["--", "fictional-host"]),
    ],
)
def test_machine_arguments(
    machine: Machine, address: str | None, expected: list[str]
) -> None:
    assert ssh.ssh_arguments(machine, address) == expected


@pytest.mark.parametrize("key", ["~/.ssh/id_box", "~\\.ssh\\id_box"])
def test_key_in_home_folder_is_expanded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, key: str
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    machine = Machine("box", "Box", addresses=("host",), key=key)
    # Either separator style names the same file on every platform.
    assert ssh.ssh_arguments(machine)[3] == str(tmp_path / ".ssh" / "id_box")


@pytest.mark.parametrize(
    "changes", [{"user": "dev"}, {"port": 22}, {"key": "~/.ssh/id_box"}]
)
def test_alias_machine_with_direct_fields_is_rejected(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.ssh_arguments(replace(FICTIONAL, **changes))
    assert str(caught.value) == INVALID_MACHINE


def test_key_without_home_folder_is_a_launch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_home() -> Path:
        raise RuntimeError("fictional-private-home")

    monkeypatch.setattr(Path, "home", no_home)
    machine = Machine("box", "Box", addresses=("host",), key="~/.ssh/id_box")
    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.ssh_arguments(machine)
    assert (
        str(caught.value) == "Could not find your home folder for this machine's key."
    )


def test_direct_machine_launch_passes_every_argument(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "ssh"
    monkeypatch.setattr(ssh.shutil, "which", Mock(return_value=str(executable)))
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(ssh.subprocess, "run", run)

    assert ssh.launch_ssh(DIRECT, "192.168.1.40") == 0

    run.assert_called_once_with(
        [str(executable.resolve()), *ssh.ssh_arguments(DIRECT, "192.168.1.40")],
        shell=False,
        check=False,
        stdin=None,
        stdout=None,
        stderr=None,
    )
    assert run.call_args.args[0][-2:] == ["--", "192.168.1.40"]


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "Agent Box"},
        {"id": "-oProxyCommand=x"},
        {"user": "-oProxyCommand=x"},
        {"user": "dev@other"},
        {"user": "two words"},
        {"addresses": ("-oProxyCommand=x",)},
        {"addresses": ("100.64.0.12", "evil host")},
        {"addresses": "100.64.0.12"},
        {"port": 0},
        {"port": True},
        {"port": "2222"},
        {"key": "id_ed25519"},
        {"key": "~/.ssh/100%key"},
        {"key": "~/.ssh/id.pub"},
        {"alias": "also-an-alias"},
    ],
)
def test_invalid_direct_settings_are_rejected_before_lookup(
    monkeypatch: pytest.MonkeyPatch, changes: dict[str, object]
) -> None:
    which = Mock(side_effect=AssertionError("Unexpected executable lookup"))
    run = Mock(side_effect=AssertionError("Unexpected child process"))
    monkeypatch.setattr(ssh.shutil, "which", which)
    monkeypatch.setattr(ssh.subprocess, "run", run)

    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.launch_ssh(replace(DIRECT, **changes))

    assert str(caught.value) == INVALID_MACHINE
    which.assert_not_called()
    run.assert_not_called()


@pytest.mark.parametrize(
    ("machine", "address"),
    [(DIRECT, "evil.example"), (DIRECT, "-oProxyCommand=x"), (FICTIONAL, "host")],
)
def test_unlisted_address_is_rejected(machine: Machine, address: str) -> None:
    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.ssh_arguments(machine, address)
    assert str(caught.value) == INVALID_MACHINE


@pytest.mark.parametrize("platform, command", [("win32", "ssh.exe"), ("linux", "ssh")])
@pytest.mark.parametrize("status", [0, 23, 255])
def test_exact_native_executable_and_single_alias_argument(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    platform: str,
    command: str,
    status: int,
) -> None:
    # The resolver is substituted: this path need not contain any executable.
    executable = tmp_path / "unused" / ".." / "Native Client" / command
    which = Mock(return_value=str(executable))
    run = Mock(return_value=subprocess.CompletedProcess([], status))
    monkeypatch.setattr(ssh, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(ssh.shutil, "which", which)
    monkeypatch.setattr(ssh.subprocess, "run", run)

    assert ssh.launch_ssh(Machine("demo", "Demo", alias="Garden.demo-host_2")) == status

    which.assert_called_once_with(command)
    run.assert_called_once_with(
        [str(executable.resolve()), "--", "Garden.demo-host_2"],
        shell=False,
        check=False,
        stdin=None,
        stdout=None,
        stderr=None,
    )
    assert Path(run.call_args.args[0][0]).is_absolute()


def fictional_client(directory: Path) -> Path:
    # Never executed: the process runner is substituted in every caller.
    directory.mkdir()
    client = directory / ("ssh.exe" if sys.platform == "win32" else "ssh")
    client.write_bytes(b"")
    client.chmod(0o755)
    return client


def search_launch_directory_first(
    monkeypatch: pytest.MonkeyPatch, launch: Path, *path_entries: Path
) -> None:
    # Windows searches the current directory before PATH unless
    # NoDefaultCurrentDirectoryInExePath is set; a relative PATH entry does the
    # same on every platform.
    monkeypatch.chdir(launch)
    monkeypatch.delenv("NoDefaultCurrentDirectoryInExePath", raising=False)
    monkeypatch.setenv(
        "PATH", os.pathsep.join([os.curdir, *(str(entry) for entry in path_entries)])
    )


def test_client_in_launch_directory_is_skipped_for_path_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    planted = fictional_client(tmp_path / "launch")
    installed = fictional_client(tmp_path / "bin")
    search_launch_directory_first(monkeypatch, planted.parent, installed.parent)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(ssh.subprocess, "run", run)

    assert ssh.launch_ssh(FICTIONAL) == 0

    assert run.call_args.args[0] == [str(installed.resolve()), "--", "fictional-host"]


def test_client_only_in_launch_directory_is_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    planted = fictional_client(tmp_path / "launch")
    search_launch_directory_first(monkeypatch, planted.parent)
    run = Mock(side_effect=AssertionError("Unexpected child process"))
    monkeypatch.setattr(ssh.subprocess, "run", run)

    with pytest.raises(ssh.SSHLaunchError, match="SSH not found"):
        ssh.launch_ssh(FICTIONAL)

    run.assert_not_called()


@pytest.mark.parametrize(
    "alias",
    [
        "",
        "-oProxyCommand=anything",
        "--",
        "demo-host command",
        "demo-host;command",
        "demo-host&command",
        "$(command)",
        "`command`",
        "demo|command",
        "demo>output",
        "demo<file",
        "demo\ncommand",
        "demo\rcommand",
        "demo\tcommand",
        "demo\0host",
        " demo-host",
        "demo-host ",
        "user@demo-host",
        "ssh://demo-host",
        "demo/host",
        "demo\\host",
        "[demo-host]",
        "demo\u202ehost",
        "démø-host",
        "東京",
        None,
        False,
        123,
        ["demo-host"],
        {"alias": "demo-host"},
        b"demo-host",
    ],
)
def test_invalid_alias_is_rejected_before_resolution_or_launch(
    monkeypatch: pytest.MonkeyPatch, alias: object
) -> None:
    which = Mock(side_effect=AssertionError("Unexpected executable lookup"))
    run = Mock(side_effect=AssertionError("Unexpected child process"))
    monkeypatch.setattr(ssh.shutil, "which", which)
    monkeypatch.setattr(ssh.subprocess, "run", run)

    with pytest.raises(ssh.SSHLaunchError, match="Invalid SSH alias"):
        ssh.launch_ssh(Machine("demo", "Demo", alias=alias))

    which.assert_not_called()
    run.assert_not_called()


def test_unavailable_ssh_does_not_start_a_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    which = Mock(return_value=None)
    run = Mock(side_effect=AssertionError("Unexpected child process"))
    monkeypatch.setattr(ssh.shutil, "which", which)
    monkeypatch.setattr(ssh.subprocess, "run", run)
    previous_handler = signal.getsignal(signal.SIGINT)

    with pytest.raises(ssh.SSHLaunchError, match="SSH not found"):
        ssh.launch_ssh(FICTIONAL)

    run.assert_not_called()
    assert signal.getsignal(signal.SIGINT) is previous_handler


@pytest.mark.parametrize("boundary", ["resolve", "start"])
def test_os_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, boundary: str
) -> None:
    error = PermissionError("fictional-private-path / synthetic-secret")
    which = Mock(return_value=str(tmp_path / "ssh"))
    run = Mock(side_effect=error)
    if boundary == "resolve":
        which.side_effect = error
    monkeypatch.setattr(ssh.shutil, "which", which)
    monkeypatch.setattr(ssh.subprocess, "run", run)

    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.launch_ssh(FICTIONAL)

    assert str(caught.value) == (
        "Could not start SSH. Check its installation and executable permissions."
    )
    assert caught.value.__suppress_context__
    if boundary == "resolve":
        run.assert_not_called()


@pytest.mark.parametrize("outcome", [0, 37, OSError("synthetic"), KeyboardInterrupt()])
def test_sigint_handler_is_restored_on_every_launch_outcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, outcome: int | BaseException
) -> None:
    original_handler = signal.getsignal(signal.SIGINT)
    parent_handler = Mock()
    monkeypatch.setattr(ssh.shutil, "which", Mock(return_value=str(tmp_path / "ssh")))

    def child(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
        handler = signal.getsignal(signal.SIGINT)
        assert callable(handler)
        assert handler is not parent_handler
        assert handler != signal.SIG_IGN
        # Native SSH may remain alive after Ctrl+C. Only its completion returns
        # control to the app, and repeated signals must not invoke its handler.
        for _ in range(3):
            handler(signal.SIGINT, None)
            assert signal.getsignal(signal.SIGINT) is handler
        parent_handler.assert_not_called()
        if isinstance(outcome, BaseException):
            raise outcome
        return subprocess.CompletedProcess([], outcome)

    monkeypatch.setattr(ssh.subprocess, "run", child)
    signal.signal(signal.SIGINT, parent_handler)
    try:
        if isinstance(outcome, KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                ssh.launch_ssh(FICTIONAL)
        elif isinstance(outcome, OSError):
            with pytest.raises(ssh.SSHLaunchError):
                ssh.launch_ssh(FICTIONAL)
        else:
            assert ssh.launch_ssh(FICTIONAL) == outcome
        assert signal.getsignal(signal.SIGINT) is parent_handler
        parent_handler.assert_not_called()
    finally:
        signal.signal(signal.SIGINT, original_handler)


@pytest.mark.parametrize("lookup_error", [False, True])
def test_sigint_during_resolution_does_not_cancel_asyncio_runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lookup_error: bool
) -> None:
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(ssh.subprocess, "run", run)

    async def scenario() -> None:
        task = asyncio.current_task()
        assert task is not None
        previous_handler = signal.getsignal(signal.SIGINT)
        # asyncio.run installs a partial carrying the task that Ctrl+C cancels.
        assert isinstance(previous_handler, partial)
        assert previous_handler.keywords["main_task"] is task

        def lookup(command: str) -> str:
            handler = signal.getsignal(signal.SIGINT)
            assert callable(handler)
            for _ in range(2):
                handler(signal.SIGINT, None)
                assert task.cancelling() == 0
            if lookup_error:
                raise OSError("synthetic lookup error")
            return str(tmp_path / command)

        monkeypatch.setattr(ssh.shutil, "which", lookup)
        if lookup_error:
            with pytest.raises(ssh.SSHLaunchError, match="Could not start SSH"):
                ssh.launch_ssh(FICTIONAL)
            run.assert_not_called()
        else:
            assert ssh.launch_ssh(FICTIONAL) == 0
            run.assert_called_once()
        assert signal.getsignal(signal.SIGINT) is previous_handler
        await asyncio.sleep(0)
        assert task.cancelling() == 0

    original_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        asyncio.run(scenario())
        assert signal.getsignal(signal.SIGINT) is signal.default_int_handler
    finally:
        signal.signal(signal.SIGINT, original_handler)


@pytest.mark.parametrize("boundary", ["lookup", "suspend", "resume"])
@pytest.mark.parametrize("launch_error", [False, True])
def test_sigint_during_handoff_keeps_asyncio_browser_usable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    boundary: str,
    launch_error: bool,
) -> None:
    events: list[str] = []
    app = SSHWorkbenchApp(
        [
            Machine("garden-demo", "Garden demo", alias="garden-demo-host"),
            Machine("studio-demo", "Studio demo", alias="studio-demo-host"),
        ]
    )

    async def scenario() -> None:
        main_task = asyncio.current_task()
        assert main_task is not None
        previous_handler = signal.getsignal(signal.SIGINT)
        assert isinstance(previous_handler, partial)
        assert previous_handler.keywords["main_task"] is main_task

        def step(name: str) -> None:
            events.append(name)
            if name != boundary:
                return
            current_task = asyncio.current_task()
            assert current_task is not None
            handler = signal.getsignal(signal.SIGINT)
            assert callable(handler)
            for _ in range(2):
                handler(signal.SIGINT, None)
                assert current_task.cancelling() == 0
                assert main_task.cancelling() == 0

        def lookup(command: str) -> str:
            step("lookup")
            return str(tmp_path / command)

        def child(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
            events.append("launch")
            if launch_error:
                raise OSError("synthetic start error")
            return subprocess.CompletedProcess([], 0)

        def unexpected_connection(*args: object, **kwargs: object) -> None:
            pytest.fail("The project browser attempted a socket connection")

        # The loop's local Windows socket pair already exists. Keep the same
        # connection guard as the async UI tests inside this separate Runner.
        with monkeypatch.context() as guard:
            guard.setattr(socket.socket, "connect", unexpected_connection)
            guard.setattr(socket.socket, "connect_ex", unexpected_connection)
            guard.setattr(ssh.shutil, "which", lookup)
            guard.setattr(ssh.subprocess, "run", child)
            guard.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
            guard.setattr(
                HeadlessDriver, "suspend_application_mode", lambda self: step("suspend")
            )
            guard.setattr(
                HeadlessDriver, "resume_application_mode", lambda self: step("resume")
            )
            async with app.run_test() as pilot:
                await pilot.press("down", "tab", "c")
                await asyncio.sleep(0)
                assert events == ["suspend", "lookup", "launch", "resume"]
                assert main_task.cancelling() == 0
                assert signal.getsignal(signal.SIGINT) is previous_handler
                assert app.is_running
                assert not app._connecting
                project_list = app.query_one(ListView)
                assert project_list.index == 1
                assert app.focused is project_list
                message = str(app.query_one("#connection-status", Static).content)
                if launch_error:
                    assert "Could not start SSH" in message
                else:
                    assert message == "SSH exited with status 0. Machine 2: studio-demo"
                await pilot.press("up", "q")
                assert project_list.index == 0
                assert not app.is_running
                assert app.return_code == 0
        assert signal.getsignal(signal.SIGINT) is previous_handler

    original_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        asyncio.run(scenario())
        assert signal.getsignal(signal.SIGINT) is signal.default_int_handler
    finally:
        signal.signal(signal.SIGINT, original_handler)


def test_install_arguments_never_offer_the_machine_key() -> None:
    assert ssh.install_arguments(FICTIONAL, None, "fixed command") == [
        "--",
        "fictional-host",
        "fixed command",
    ]
    assert ssh.install_arguments(DIRECT, "192.168.1.40", "fixed command") == [
        "-o",
        "HostKeyAlias=agent-box",
        "-l",
        "dev",
        "-p",
        "2222",
        "--",
        "192.168.1.40",
        "fixed command",
    ]


KEY_ONLY = [
    "-o",
    "PreferredAuthentications=publickey",
    "-o",
    "PasswordAuthentication=no",
    "-o",
    "KbdInteractiveAuthentication=no",
]


def test_login_test_arguments_allow_only_public_keys() -> None:
    assert ssh.login_test_arguments(FICTIONAL, None) == [
        *KEY_ONLY,
        "--",
        "fictional-host",
        "exit",
    ]
    assert ssh.login_test_arguments(DIRECT, None) == [
        *KEY_ONLY,
        "-o",
        "HostKeyAlias=agent-box",
        "-l",
        "dev",
        "-p",
        "2222",
        "-i",
        "C:\\Fictional Keys\\id_ed25519_agent_box",
        "-o",
        "IdentitiesOnly=yes",
        "--",
        "100.64.0.12",
        "exit",
    ]


def test_install_and_test_arguments_revalidate_the_machine() -> None:
    broken = replace(DIRECT, addresses=("-oProxyCommand=x",))
    for build in (
        lambda: ssh.install_arguments(broken, None, "fixed command"),
        lambda: ssh.login_test_arguments(broken, None),
    ):
        with pytest.raises(ssh.SSHLaunchError) as caught:
            build()
        assert str(caught.value) == INVALID_MACHINE


def test_run_native_inherits_the_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    run = Mock(return_value=subprocess.CompletedProcess([], 5))
    monkeypatch.setattr(ssh.subprocess, "run", run)

    assert ssh.run_native(["/fictional/ssh-keygen", "-t", "ed25519"]) == 5

    run.assert_called_once_with(
        ["/fictional/ssh-keygen", "-t", "ed25519"],
        shell=False,
        check=False,
        stdin=None,
        stdout=None,
        stderr=None,
    )


def test_run_native_names_the_tool_that_could_not_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = Mock(side_effect=PermissionError("fictional-private-path"))
    monkeypatch.setattr(ssh.subprocess, "run", run)

    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.run_native(["/fictional/ssh-keygen"], "ssh-keygen")

    assert str(caught.value) == (
        "Could not start ssh-keygen. Check its installation and executable permissions."
    )
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    ("platform", "command"), [("win32", "ssh-keygen.exe"), ("linux", "ssh-keygen")]
)
def test_find_ssh_keygen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, platform: str, command: str
) -> None:
    executable = tmp_path / "Native Client" / command
    which = Mock(return_value=str(executable))
    monkeypatch.setattr(ssh, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(ssh.shutil, "which", which)

    assert ssh.find_ssh_keygen() == str(executable.resolve())
    which.assert_called_once_with(command)

    which.return_value = None
    with pytest.raises(ssh.SSHLaunchError) as caught:
        ssh.find_ssh_keygen()
    assert str(caught.value) == (
        "ssh-keygen not found. Install OpenSSH and add it to PATH."
    )
