import asyncio
import signal
import socket
import subprocess
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import ListView, Static

from ssh_workbench import ssh
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Project

pytestmark = pytest.mark.usefixtures("no_external_actions")


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

    assert ssh.launch_ssh("Garden.demo-host_2") == status

    which.assert_called_once_with(command)
    run.assert_called_once_with(
        [str(executable.resolve()), "Garden.demo-host_2"],
        shell=False,
        check=False,
        stdin=None,
        stdout=None,
        stderr=None,
    )
    assert Path(run.call_args.args[0][0]).is_absolute()


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
        ssh.launch_ssh(alias)

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
        ssh.launch_ssh("fictional-host")

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
        ssh.launch_ssh("fictional-host")

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
                ssh.launch_ssh("fictional-host")
        elif isinstance(outcome, OSError):
            with pytest.raises(ssh.SSHLaunchError):
                ssh.launch_ssh("fictional-host")
        else:
            assert ssh.launch_ssh("fictional-host") == outcome
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
                ssh.launch_ssh("fictional-host")
            run.assert_not_called()
        else:
            assert ssh.launch_ssh("fictional-host") == 0
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
            Project("garden-demo", "Garden demo", "garden-demo-host"),
            Project("studio-demo", "Studio demo", "studio-demo-host"),
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
                    assert message == "SSH exited with status 0."
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
