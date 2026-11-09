"""K for a direct machine whose key is the other system's absolute form.

A machine file shared between Windows and Linux may name a key such as
`C:\\Users\\example\\.ssh\\id_ed25519`. The loader accepts it, but on Linux
that is a relative path, a file in the working folder; on Windows,
`/home/example/.ssh/id_ed25519` names a folder at the root of the working
folder's drive. K must not install or test such a key. Everything is fictional
and substituted: no real ssh, key, SSH folder or machine file.
"""

import asyncio
import base64
import struct
import sys
from pathlib import Path

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import OptionList

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.app import ResultSlot, SSHWorkbenchApp
from ssh_workbench.config import (
    Machine,
    format_machines,
    is_valid_key_path,
    read_machines,
)
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import PublicKey, posix_install_command

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

SSH = "/fictional/ssh"
KEYGEN = "/fictional/ssh-keygen"
# Each system's absolute form is not absolute on the other one.
FOREIGN_KEY = (
    "/home/example/.ssh/id_ed25519"
    if sys.platform == "win32"
    else "C:\\Users\\example\\.ssh\\id_ed25519"
)
MESSAGE = "This machine's key is a path for another system; nothing was installed."


def blob(seed: int) -> str:
    data = (
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes([seed]) * 32
    )
    return base64.b64encode(data).decode()


PLANTED = PublicKey("ssh-ed25519", blob(0x5A), "planted-in-the-working-folder")
OWN = PublicKey("ssh-ed25519", blob(0x3C), "keyed")


class Native:
    """Records each handed-off command; every step exits 0."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        return 0


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machine: Machine,
    native: Native,
) -> tuple[Path, str, list[bool]]:
    """An empty SSH folder, the machine file, the working folder and the
    substituted native boundary; returns the file, its text and the suspends."""
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text("", encoding="ascii")
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines((machine,))
    path.write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    suspended: list[bool] = []
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: suspended.append(True),
    )
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    return path, text, suspended


def connection_status(app: SSHWorkbenchApp) -> str:
    return app.query_one("#connection-status", ResultSlot).message


def showing_picker(app: SSHWorkbenchApp) -> bool:
    return isinstance(app.screen, KeySetup) and app.screen.is_mounted


def option_labels(screen: KeySetup) -> list[str]:
    options = screen.query_one(OptionList)
    return [
        str(options.get_option_at_index(index).prompt)
        for index in range(options.option_count)
    ]


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def k_answered(app: SSHWorkbenchApp, pilot) -> None:
    """K opened the picker or reported something in the status line."""
    await pilot.press("k")
    await wait_for(
        pilot,
        lambda: showing_picker(app) or "Machine 1:" in connection_status(app),
    )


async def test_a_machine_key_for_another_system_is_not_installed_or_tested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    winkey = Machine("winkey", "Winkey", addresses=("192.0.2.70",), key=FOREIGN_KEY)
    path, text, suspended = workspace(tmp_path, monkeypatch, winkey, native)
    # Shared machine files keep loading on both systems.
    assert is_valid_key_path(FOREIGN_KEY) is True
    assert read_machines(path) == ([winkey], text)
    assert Path(FOREIGN_KEY).is_absolute() is False
    if sys.platform == "win32":
        # The POSIX form names the working drive's root, outside tmp_path.
        assert Path(FOREIGN_KEY).drive == ""
    else:
        # The Windows form is one file name here: plant a key pair under it.
        (tmp_path / f"{FOREIGN_KEY}.pub").write_text(PLANTED.line + "\n", "ascii")
        (tmp_path / FOREIGN_KEY).write_text("fictional private half\n", "ascii")
        assert sorted(item.name for item in Path.cwd().iterdir()) == sorted(
            ["machines.toml", "ssh", FOREIGN_KEY, f"{FOREIGN_KEY}.pub"]
        )
    app = SSHWorkbenchApp((winkey,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await k_answered(app, pilot)
        assert not isinstance(app.screen, KeySetup)
        assert connection_status(app) == f"{MESSAGE} Machine 1: winkey"
        assert app.is_running
    arguments = [argument for call in native.calls for argument in call]
    assert posix_install_command(PLANTED) not in arguments
    assert FOREIGN_KEY not in arguments
    assert native.calls == []
    assert suspended == []
    assert path.read_text(encoding="utf-8") == text


async def test_a_machine_key_in_the_home_folder_is_still_installed_and_tested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key="~/.ssh/id_x")
    path, text, suspended = workspace(tmp_path, monkeypatch, keyed, native)
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    private = home / ".ssh" / "id_x"
    Path(f"{private}.pub").write_text(OWN.line + "\n", "ascii")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await k_answered(app, pilot)
        assert option_labels(app.screen) == ["~/.ssh/id_x (this machine's key)"]
        await pilot.press("enter")
        await wait_for(pilot, lambda: "Key login" in connection_status(app))
        assert connection_status(app) == "Key login works. Machine 1: keyed"
    assert native.calls == [
        [
            SSH,
            "-o",
            "RemoteCommand=none",
            "-o",
            "HostKeyAlias=keyed",
            "--",
            "192.0.2.61",
            posix_install_command(OWN),
        ],
        [
            SSH,
            "-o",
            "PreferredAuthentications=publickey",
            "-o",
            "PasswordAuthentication=no",
            "-o",
            "KbdInteractiveAuthentication=no",
            "-o",
            "ControlPath=none",
            "-o",
            "RemoteCommand=none",
            "-o",
            "HostKeyAlias=keyed",
            "-i",
            str(private),
            "-o",
            "IdentitiesOnly=yes",
            "--",
            "192.0.2.61",
            "exit",
        ],
    ]
    assert suspended == [True]
    assert path.read_text(encoding="utf-8") == text
