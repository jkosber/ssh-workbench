"""K when stdout fails while the terminal is handed over.

The three `SSH Workbench: ...` lines K prints during the handoff are
informational. When writing one fails, as with an I/O error, a broken pipe or a
closed stream, K still runs its steps and Workbench takes the terminal back.
Textual's suspend points stdout at `sys.__stdout__`, so a failing stream stands
in for it. Everything is fictional and substituted: no real ssh, ssh-keygen,
key, SSH folder or machine file.
"""

import asyncio
import base64
import dataclasses
import errno
import struct
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from textual.drivers.headless_driver import HeadlessDriver

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.app import ResultSlot, SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import PublicKey

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

SSH = "/fictional/ssh"
KEYGEN = "/fictional/ssh-keygen"
BOX = Machine("box", "Box", user="dev", addresses=("192.0.2.60",))
CREATING = "SSH Workbench: creating the key; ssh-keygen asks for a passphrase."
INSTALLING = "SSH Workbench: installing the key; SSH may ask for the password."
TESTING = "SSH Workbench: testing key-only login."
ERRORS = [
    pytest.param(lambda: OSError(errno.EIO, "Input/output error"), id="io-error"),
    pytest.param(lambda: BrokenPipeError(errno.EPIPE, "Broken pipe"), id="pipe"),
    pytest.param(lambda: ValueError("I/O operation on closed file."), id="closed"),
]


def blob(seed: int) -> str:
    data = (
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes([seed]) * 32
    )
    return base64.b64encode(data).decode()


OWN = PublicKey("ssh-ed25519", blob(3), "keyed")
CREATED = PublicKey("ssh-ed25519", blob(9), "ssh-workbench-box")


class Native:
    """Records each handed-off command; ssh-keygen writes a fictional key pair."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    @staticmethod
    def step(arguments: list[str]) -> str:
        if arguments[0] == KEYGEN:
            return "keygen"
        return "test" if arguments[-1] == "exit" else "install"

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        if self.step(arguments) == "keygen":
            private = Path(arguments[arguments.index("-f") + 1])
            private.write_text("fictional private half\n", encoding="ascii")
            Path(f"{private}.pub").write_text(CREATED.line + "\n", encoding="ascii")
        return 0


class FailingStdout:
    """A stream whose every write and flush raises `error`; it keeps the texts."""

    encoding = "utf-8"
    errors = "strict"

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.attempted: list[str] = []

    def write(self, text: str) -> int:
        self.attempted.append(text)
        raise self.error

    def flush(self) -> None:
        raise self.error

    def isatty(self) -> bool:
        return False


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machine: Machine,
    native: Native,
) -> tuple[Path, Path, str, list[str]]:
    """An empty SSH folder, the machine file and the substituted native
    boundary; returns the folder, the file, its text and the driver events."""
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text("", encoding="ascii")
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines((machine,))
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    # The installed App.suspend runs; only the driver's handoff is recorded.
    events: list[str] = []
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: events.append("suspend"),
    )
    monkeypatch.setattr(
        HeadlessDriver, "resume_application_mode", lambda self: events.append("resume")
    )
    return folder, path, text, events


def connection_status(app: SSHWorkbenchApp) -> str:
    return app.query_one("#connection-status", ResultSlot).message


def printed(stream: FailingStdout) -> list[str]:
    return [text.removesuffix("\n") for text in stream.attempted]


async def wait_for(pilot, predicate: Callable[[], bool]) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def k_with_failing_stdout(
    app: SSHWorkbenchApp,
    pilot,
    monkeypatch: pytest.MonkeyPatch,
    stream: FailingStdout,
) -> None:
    """Open K's picker, break stdout, take the first choice and wait until K
    reports a result or the app has stopped."""
    await pilot.press("k")
    await wait_for(
        pilot, lambda: isinstance(app.screen, KeySetup) and app.screen.is_mounted
    )
    monkeypatch.setattr(sys, "__stdout__", stream)
    await pilot.press("enter")
    await wait_for(
        pilot,
        lambda: app.return_code is not None or "Machine 1:" in connection_status(app),
    )


@pytest.mark.parametrize("error", ERRORS)
async def test_a_failing_stdout_still_installs_and_tests_a_machines_own_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Callable[[], Exception]
) -> None:
    native = Native()
    key = tmp_path / "ssh" / "id_keyed"
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key=str(key))
    folder, path, text, events = workspace(tmp_path, monkeypatch, keyed, native)
    Path(f"{key}.pub").write_text(OWN.line + "\n", "ascii")
    stream = FailingStdout(error())
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await k_with_failing_stdout(app, pilot, monkeypatch, stream)
        assert events == ["suspend", "resume"]
        assert app.return_code is None
        assert app.is_running
        assert connection_status(app) == "Key login works. Machine 1: keyed"
    assert printed(stream) == [INSTALLING, TESTING]
    assert [Native.step(call) for call in native.calls] == ["install", "test"]
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize("error", ERRORS)
async def test_a_failing_stdout_still_creates_installs_tests_and_saves_a_new_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Callable[[], Exception]
) -> None:
    native = Native()
    folder, path, text, events = workspace(tmp_path, monkeypatch, BOX, native)
    new = folder / "id_ed25519_box"
    stream = FailingStdout(error())
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await k_with_failing_stdout(app, pilot, monkeypatch, stream)
        assert events == ["suspend", "resume"]
        assert app.return_code is None
        assert app.is_running
        assert connection_status(app) == (
            "Key login works. The key is saved as this machine's key. Machine 1: box"
        )
    assert printed(stream) == [CREATING, INSTALLING, TESTING]
    assert [Native.step(call) for call in native.calls] == [
        "keygen",
        "install",
        "test",
    ]
    assert native.calls[0] == [
        KEYGEN,
        "-t",
        "ed25519",
        "-f",
        str(new),
        "-C",
        "ssh-workbench-box",
    ]
    assert read_machines(path)[0] == [dataclasses.replace(BOX, key=str(new))]
