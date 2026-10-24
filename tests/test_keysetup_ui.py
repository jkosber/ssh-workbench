"""K in the app: the key picker and the three handed-off steps, all substituted.

No real ssh-keygen, SSH or key is used. `run_native` is replaced by a recorder
that writes fictional key files when asked to create a key.
"""

import asyncio
import base64
import dataclasses
import platform
import signal
import struct
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, Input, ListView, OptionList, RadioButton, Static

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.aliases import AliasMemory, AliasRecord, format_state, state_path
from ssh_workbench.app import SSHWorkbenchApp, StatusSymbol
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.forms import KeyChoice, KeySetup, MachineForm
from ssh_workbench.keys import (
    PublicKey,
    posix_install_command,
    windows_install_command,
)
from ssh_workbench.status import AliasTarget, State

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

SSH = "/fictional/ssh"
KEYGEN = "/fictional/ssh-keygen"
NO_REMOTE_COMMAND = ["-o", "RemoteCommand=none"]
KEY_ONLY = [
    "-o",
    "PreferredAuthentications=publickey",
    "-o",
    "PasswordAuthentication=no",
    "-o",
    "KbdInteractiveAuthentication=no",
    "-o",
    "ControlPath=none",
    *NO_REMOTE_COMMAND,
]
BOX = Machine("box", "Box", user="dev", addresses=("192.0.2.60",))
GARDEN = Machine("garden", "Garden", alias="garden-host")


def blob(seed: int) -> str:
    data = (
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes([seed]) * 32
    )
    return base64.b64encode(data).decode()


def public_key(seed: int, comment: str) -> PublicKey:
    return PublicKey("ssh-ed25519", blob(seed), comment)


def rsa_key(bits: int, comment: str) -> PublicKey:
    """An RSA public key of the given size in the OpenSSH layout; no private half."""
    parts = (b"ssh-rsa", b"\x01\x00\x01", b"\x00" + b"\xc1" * (bits // 8))
    data = b"".join(struct.pack(">I", len(part)) + part for part in parts)
    return PublicKey("ssh-rsa", base64.b64encode(data).decode(), comment)


def press_ctrl_c() -> None:
    """Deliver Ctrl+C to Workbench as the console does: to its SIGINT handler."""
    signal.getsignal(signal.SIGINT)(signal.SIGINT, None)


class Native:
    """Records each handed-off command; ssh-keygen writes a fictional key pair.

    `ctrl_c` names a step during which Ctrl+C reaches Workbench too; that step
    still exits with its status, as Windows tools can.
    """

    def __init__(
        self,
        statuses: dict[str, int] | None = None,
        interrupt: str | None = None,
        new_key: str | None = None,
        ctrl_c: str | None = None,
    ) -> None:
        self.statuses = statuses or {}
        self.interrupt = interrupt
        self.new_key = new_key or public_key(9, "ssh-workbench-box").line
        self.ctrl_c = ctrl_c
        self.calls: list[list[str]] = []

    @staticmethod
    def step(arguments: list[str]) -> str:
        if arguments[0] == KEYGEN:
            return "keygen"
        return "test" if arguments[-1] == "exit" else "install"

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        step = self.step(arguments)
        if step == self.interrupt:
            raise KeyboardInterrupt
        if step == self.ctrl_c:
            press_ctrl_c()
        if step == "keygen":
            private = Path(arguments[arguments.index("-f") + 1])
            private.write_text("fictional private half\n", encoding="ascii")
            Path(f"{private}.pub").write_text(self.new_key + "\n", encoding="ascii")
        return self.statuses.get(step, 0)


class FakeChecker:
    def __init__(self, target: AliasTarget | None, hold=None) -> None:
        self.target = target
        self.hold = hold
        self.resolved: list[str] = []

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        if self.hold is not None:
            self.hold.wait(30)
        return self.target

    def port_open(self, host: str, port: int) -> bool:
        return False


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machines: tuple[Machine, ...],
    native: Native,
    text: str | None = None,
) -> tuple[Path, Path, str]:
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text("", encoding="ascii")
    (folder / "id_a.pub").write_text(public_key(1, "a").line + "\n", "ascii")
    (folder / "id_b.pub").write_text(public_key(2, "b").line + "\n", "ascii")
    (folder / "junk.pub").write_text("not a key\n", encoding="ascii")
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines(machines) if text is None else text
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    return folder, path, text


def option_labels(screen: KeySetup) -> list[str]:
    options = screen.query_one(OptionList)
    return [
        str(options.get_option_at_index(index).prompt)
        for index in range(options.option_count)
    ]


def note(screen: KeySetup) -> str:
    return str(screen.query_one("#key-note", Static).content)


def connection_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


async def picker(app: SSHWorkbenchApp, pilot) -> KeySetup:
    await pilot.press("k")
    await wait_for(pilot, lambda: showing(app, KeySetup))
    return app.screen


async def finished(app: SSHWorkbenchApp, pilot) -> None:
    await wait_for(pilot, lambda: "Machine 1:" in connection_status(app))


async def test_a_direct_machine_without_a_key_offers_pub_files_and_a_new_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert option_labels(screen) == [
            "id_a.pub",
            "id_b.pub",
            "Create a new key: id_ed25519_box",
        ]
        assert screen.query_one("#system-posix", RadioButton).value is True
        assert note(screen) == ""
        await pilot.press("escape")
        await wait_for(pilot, lambda: not isinstance(app.screen, KeySetup))
    assert native.calls == []
    assert path.read_text(encoding="utf-8") == text


async def test_a_new_key_is_created_installed_tested_and_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    new = folder / "id_ed25519_box"
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("down", "down", "enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Key login works. The key is saved as this machine's key. Machine 1: box"
        )
    created = public_key(9, "ssh-workbench-box")
    assert native.calls == [
        [KEYGEN, "-t", "ed25519", "-f", str(new), "-C", "ssh-workbench-box"],
        [
            SSH,
            *NO_REMOTE_COMMAND,
            "-o",
            "HostKeyAlias=box",
            "-l",
            "dev",
            "--",
            "192.0.2.60",
            posix_install_command(created),
        ],
        [
            SSH,
            *KEY_ONLY,
            "-o",
            "HostKeyAlias=box",
            "-l",
            "dev",
            "-i",
            str(new),
            "-o",
            "IdentitiesOnly=yes",
            "--",
            "192.0.2.60",
            "exit",
        ],
    ]
    assert read_machines(path)[0] == [dataclasses.replace(BOX, key=str(new))]


async def test_a_windows_target_gets_the_windows_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        screen.query_one("#system-windows", RadioButton).value = True
        await pilot.pause()
        await pilot.press("enter")
        await finished(app, pilot)
    assert native.calls[0][-1] == windows_install_command(public_key(1, "a"))


TOO_LARGE = (
    "This key is too large for the Windows install command, which cmd.exe "
    "limits to 8191 characters. Use an Ed25519 key or an RSA key of up to "
    "4096 bits; nothing was installed."
)


async def test_a_key_too_large_for_windows_is_refused_before_the_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    big = rsa_key(8192, "big")
    (folder / "id_big.pub").write_text(big.line + "\n", "ascii")
    suspended: list[bool] = []
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: suspended.append(True),
    )
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert option_labels(screen)[2] == "id_big.pub"
        await pilot.press("down", "down")
        screen.query_one("#system-windows", RadioButton).value = True
        await pilot.pause()
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{TOO_LARGE} Machine 1: box"
    assert native.calls == []
    assert suspended == []
    assert path.read_text(encoding="utf-8") == text


async def test_a_key_too_large_for_windows_still_installs_on_posix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    big = rsa_key(8192, "big")
    (folder / "id_big.pub").write_text(big.line + "\n", "ascii")
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("down", "down", "enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Key login works. The key is saved as this machine's key. Machine 1: box"
        )
    assert native.calls[0][-1] == posix_install_command(big)
    assert [Native.step(call) for call in native.calls] == ["install", "test"]


async def test_a_machine_with_a_key_uses_only_that_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    key = tmp_path / "ssh" / "id_keyed"
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key=str(key))
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)
    Path(f"{key}.pub").write_text(public_key(3, "keyed").line + "\n", "ascii")
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert option_labels(screen) == [f"{key} (this machine's key)"]
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == "Key login works. Machine 1: keyed"
    assert native.calls[0] == [
        SSH,
        *NO_REMOTE_COMMAND,
        "-o",
        "HostKeyAlias=keyed",
        "--",
        "192.0.2.61",
        posix_install_command(public_key(3, "keyed")),
    ]
    assert native.calls[1][-4:] == ["IdentitiesOnly=yes", "--", "192.0.2.61", "exit"]
    assert path.read_text(encoding="utf-8") == text


CREATING = "Key setup interrupted while creating the key; nothing was installed."
BEFORE_INSTALL = "Key setup interrupted before the install; nothing was installed."
DURING_INSTALL = "Key setup interrupted during the install; login was not tested."


@pytest.mark.parametrize(
    ("choice", "native", "steps", "message"),
    [
        (
            ["down", "down"],
            Native(statuses={"keygen": 1}),
            ["keygen"],
            "ssh-keygen exited with status 1; nothing was installed.",
        ),
        (
            ["down", "down"],
            Native(new_key="not a key"),
            ["keygen"],
            "id_ed25519_box.pub is not a single valid OpenSSH public key; "
            "nothing was installed.",
        ),
        (
            [],
            Native(statuses={"install": 255}),
            ["install"],
            "Installing the key failed (SSH exited with status 255); "
            "login was not tested.",
        ),
        (
            [],
            Native(interrupt="install"),
            ["install"],
            DURING_INSTALL,
        ),
        (
            ["down", "down"],
            Native(statuses={"keygen": -signal.SIGINT}),
            ["keygen"],
            CREATING,
        ),
        (
            [],
            Native(statuses={"install": 0xC000013A}),
            ["install"],
            DURING_INSTALL,
        ),
        (
            [],
            Native(statuses={"test": 0xFFFFFFFF}),
            ["install", "test"],
            "The key was installed, but the login test was interrupted. "
            "The key was not saved as this machine's key.",
        ),
    ],
)
async def test_a_failed_step_stops_the_later_ones(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    choice: list[str],
    native: Native,
    steps: list[str],
    message: str,
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press(*choice, "enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{message} Machine 1: box"
        assert app.is_running
    assert [Native.step(call) for call in native.calls] == steps
    assert path.read_text(encoding="utf-8") == text


INTERRUPTED_TEST = (
    "The key was installed, but the login test was interrupted. "
    "The key was not saved as this machine's key."
)


@pytest.mark.parametrize(
    ("step", "status", "steps", "message"),
    [
        ("keygen", 0, ["keygen"], CREATING),
        ("keygen", 255, ["keygen"], CREATING),
        ("install", 0, ["install"], DURING_INSTALL),
        ("install", 255, ["install"], DURING_INSTALL),
        ("test", 0, ["install", "test"], INTERRUPTED_TEST),
        ("test", 255, ["install", "test"], INTERRUPTED_TEST),
    ],
)
async def test_ctrl_c_during_a_step_is_an_interruption_whatever_its_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    step: str,
    status: int,
    steps: list[str],
    message: str,
) -> None:
    native = Native(statuses={step: status}, ctrl_c=step)
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press(*(["down", "down"] if step == "keygen" else []), "enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{message} Machine 1: box"
    assert [Native.step(call) for call in native.calls] == steps
    assert path.read_text(encoding="utf-8") == text


async def test_ctrl_c_between_steps_stops_the_later_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)

    def find_ssh() -> str:
        # ssh-keygen has finished; Ctrl+C arrives while Workbench looks up SSH.
        press_ctrl_c()
        return SSH

    monkeypatch.setattr(app_module, "find_ssh", find_ssh)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("down", "down", "enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{BEFORE_INSTALL} Machine 1: box"
    assert [Native.step(call) for call in native.calls] == ["keygen"]
    assert path.read_text(encoding="utf-8") == text


async def test_a_ctrl_c_that_reaches_workbench_after_the_test_still_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Windows runs the parent's Ctrl+C handler on a thread of its own, which
    # can lose the race with a child that exits 0; here it arrives while the
    # terminal is handed back.
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    monkeypatch.setattr(
        HeadlessDriver, "resume_application_mode", lambda self: press_ctrl_c()
    )
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{INTERRUPTED_TEST} Machine 1: box"
    assert [Native.step(call) for call in native.calls] == ["install", "test"]
    assert path.read_text(encoding="utf-8") == text


async def test_ctrl_c_while_the_terminal_is_handed_over_stops_every_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    monkeypatch.setattr(
        HeadlessDriver, "suspend_application_mode", lambda self: press_ctrl_c()
    )
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{BEFORE_INSTALL} Machine 1: box"
    assert native.calls == []
    assert path.read_text(encoding="utf-8") == text


async def test_ctrl_c_while_the_terminal_is_handed_over_before_a_new_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    monkeypatch.setattr(
        HeadlessDriver, "suspend_application_mode", lambda self: press_ctrl_c()
    )
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("down", "down", "enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{CREATING} Machine 1: box"
    assert native.calls == []
    assert not (folder / "id_ed25519_box").exists()
    assert path.read_text(encoding="utf-8") == text


async def test_an_earlier_ctrl_c_does_not_interrupt_the_next_key_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(ctrl_c="test")
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        first = connection_status(app)
        assert first == f"{INTERRUPTED_TEST} Machine 1: box"
        native.ctrl_c = None
        await picker(app, pilot)
        await pilot.press("enter")
        await wait_for(pilot, lambda: connection_status(app) != first)
        assert connection_status(app) == (
            "Key login works. The key is saved as this machine's key. Machine 1: box"
        )
    assert [Native.step(call) for call in native.calls] == [
        "install",
        "test",
        "install",
        "test",
    ]
    assert read_machines(path)[0][0].key == str(folder / "id_a")


async def test_a_failed_login_test_does_not_save_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            "status 255). The key was not saved as this machine's key. "
            "Machine 1: box"
        )
    assert path.read_text(encoding="utf-8") == text


async def test_a_failed_test_of_a_machines_own_key_adds_no_save_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(statuses={"test": 255})
    key = tmp_path / "ssh" / "id_keyed"
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key=str(key))
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)
    Path(f"{key}.pub").write_text(public_key(3, "keyed").line + "\n", "ascii")
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            "status 255). Machine 1: keyed"
        )
    assert path.read_text(encoding="utf-8") == text


async def test_saving_a_key_warns_about_comments_in_the_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    text = "# Fictional notes kept by hand\n" + format_machines((BOX,))
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native, text)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert note(screen) == (
            "Saving rewrites the file without its comments or formatting; the old "
            "file is kept as machines.toml.bak."
        )
        await pilot.press("enter")
        await finished(app, pilot)
    assert read_machines(path)[0][0].key == str(folder / "id_a")


async def test_an_alias_offers_its_own_keys_first_and_explains_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10",
        22,
        proxied=False,
        user="dev",
        identity_files=("~/ssh/id_lab", "~/ssh/id_missing"),
        identities_only=True,
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        screen = await picker(app, pilot)
        assert checker.resolved == ["garden-host", "garden-host"]
        assert option_labels(screen) == [
            "id_lab.pub (your SSH config offers this)",
            "id_a.pub",
            "id_b.pub",
            "Create a new key: id_ed25519_garden",
        ]
        assert note(screen) == ""
        await pilot.press("down")
        line = f"IdentityFile {folder / 'id_a'}"
        assert note(screen) == (
            "Your SSH config doesn't name this key for garden-host. Add this line "
            f"under Host garden-host; Workbench never edits the config: {line}"
        )
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            "status 255). Your SSH config offers only its own keys for garden-host "
            f"(IdentitiesOnly); add this line under Host garden-host: {line} "
            "Machine 1: garden"
        )
    assert native.calls == [
        [
            SSH,
            *NO_REMOTE_COMMAND,
            "--",
            "garden-host",
            posix_install_command(public_key(1, "a")),
        ],
        [SSH, *KEY_ONLY, "--", "garden-host", "exit"],
    ]
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    ("identities_only", "hint"),
    [
        (
            True,
            "Your SSH config offers only its own keys for garden-host "
            "(IdentitiesOnly); add this line under Host garden-host:",
        ),
        (
            False,
            "Your SSH config doesn't name this key for garden-host; add this line "
            "under Host garden-host:",
        ),
    ],
)
async def test_an_alias_test_passing_with_an_unnamed_key_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, identities_only: bool, hint: str
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10",
        22,
        proxied=False,
        user="dev",
        identity_files=("~/ssh/id_lab",),
        identities_only=identities_only,
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("down")
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Key-only login works, but SSH may have used another key. "
            f"{hint} IdentityFile {folder / 'id_a'} Machine 1: garden"
        )
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    "native",
    [Native(statuses={"test": 0xFFFFFFFF}), Native(ctrl_c="test")],
    ids=["interrupted-status", "ctrl-c-and-status-0"],
)
async def test_an_alias_login_test_interrupted_with_an_unnamed_key_gives_no_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native: Native
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10",
        22,
        proxied=False,
        user="dev",
        identity_files=("~/ssh/id_lab",),
        identities_only=True,
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("down")
        await pilot.press("enter")
        await finished(app, pilot)
        # An interrupted test says nothing about which key SSH used.
        assert connection_status(app) == (
            "The key was installed, but the login test was interrupted. "
            "Machine 1: garden"
        )
    assert [Native.step(call) for call in native.calls] == ["install", "test"]
    assert path.read_text(encoding="utf-8") == text


async def test_an_alias_test_passing_with_its_configured_key_says_it_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10", 22, proxied=False, user="dev", identity_files=("~/ssh/id_lab",)
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == "Key login works. Machine 1: garden"


async def test_k_waits_for_the_alias_and_quitting_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    try:
        async with asyncio.timeout(5):
            async with app.run_test() as pilot:
                await pilot.press("k")
                await wait_for(
                    pilot, lambda: checker.resolved.count("garden-host") == 2
                )
                assert not isinstance(app.screen, KeySetup)
                await pilot.press("q")
                assert not app.is_running
    finally:
        hold.set()


def tracked_threads(monkeypatch: pytest.MonkeyPatch) -> list[threading.Thread]:
    """Record every thread the app starts, so a test can wait for all of them."""
    started: list[threading.Thread] = []

    def thread(*args, **kwargs) -> threading.Thread:
        started.append(threading.Thread(*args, **kwargs))
        return started[-1]

    monkeypatch.setattr(app_module, "Thread", thread)
    return started


async def answered(pilot, threads: list[threading.Thread]) -> None:
    """Each answer is posted before its thread ends; then it is handled."""
    for thread in threads:
        thread.join(5)
    await pilot.pause()


async def k_waits(app: SSHWorkbenchApp, pilot, checker: FakeChecker) -> None:
    """K on Garden, with startup's and K's ssh -G both held."""
    await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
    await pilot.press("k")
    await wait_for(pilot, lambda: checker.resolved.count("garden-host") == 2)


async def test_a_k_answer_after_c_opens_no_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    monkeypatch.setattr(app_module, "launch_ssh", Mock(return_value=0))
    threads = tracked_threads(monkeypatch)
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    ended = "SSH exited with status 0. Machine 1: garden"
    try:
        async with app.run_test() as pilot:
            await k_waits(app, pilot, checker)
            await pilot.press("c")
            await wait_for(pilot, lambda: connection_status(app) == ended)
            hold.set()
            await answered(pilot, threads)
            assert not isinstance(app.screen, KeySetup)
            assert connection_status(app) == ended
    finally:
        hold.set()


async def test_a_k_answer_after_a_form_opens_no_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    threads = tracked_threads(monkeypatch)
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await k_waits(app, pilot, checker)
            await pilot.press("e")
            await wait_for(pilot, lambda: showing(app, MachineForm))
            await pilot.press("escape")
            await wait_for(pilot, lambda: len(app.screen_stack) == 1)
            hold.set()
            await answered(pilot, threads)
            assert not isinstance(app.screen, KeySetup)
    finally:
        hold.set()


async def test_moving_away_while_k_waits_opens_no_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    machines = (GARDEN, BOX)
    folder, path, text = workspace(tmp_path, monkeypatch, machines, Native())
    threads = tracked_threads(monkeypatch)
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await k_waits(app, pilot, checker)
            await pilot.press("down")
            await wait_for(pilot, lambda: app.query_one(ListView).index == 1)
            hold.set()
            await answered(pilot, threads)
            assert not isinstance(app.screen, KeySetup)
    finally:
        hold.set()


async def test_a_second_k_while_waiting_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    still = "Still looking up garden-host in your SSH config. Machine 1: garden"
    try:
        async with app.run_test() as pilot:
            await k_waits(app, pilot, checker)
            await pilot.press("k")
            await wait_for(pilot, lambda: connection_status(app) == still)
            assert checker.resolved.count("garden-host") == 2
            hold.set()
            await wait_for(pilot, lambda: showing(app, KeySetup))
    finally:
        hold.set()


async def test_k_after_a_dropped_wait_looks_up_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    machines = (GARDEN, BOX)
    folder, path, text = workspace(tmp_path, monkeypatch, machines, Native())
    threads = tracked_threads(monkeypatch)
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await k_waits(app, pilot, checker)
            await pilot.press("down")
            await wait_for(pilot, lambda: app.query_one(ListView).index == 1)
            await pilot.press("up")
            await wait_for(pilot, lambda: app.query_one(ListView).index == 0)
            await pilot.press("k")
            await wait_for(pilot, lambda: checker.resolved.count("garden-host") == 3)
            hold.set()
            await wait_for(pilot, lambda: showing(app, KeySetup))
            await answered(pilot, threads)
            # Two answers, one picker.
            assert len(app.screen_stack) == 2
    finally:
        hold.set()


class HeldPerAlias(FakeChecker):
    """Each alias's ssh -G waits for its own event."""

    def __init__(
        self, targets: dict[str, AliasTarget], holds: dict[str, threading.Event]
    ) -> None:
        super().__init__(None)
        self.targets = targets
        self.holds = holds

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        self.holds[alias].wait(30)
        return self.targets[alias]


def offering(*keys: str) -> AliasTarget:
    return AliasTarget(
        "192.0.2.10", 22, proxied=False, identity_files=keys, identities_only=True
    )


async def test_an_earlier_k_lookup_never_opens_the_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holds = {"garden-host": threading.Event(), "other-host": threading.Event()}
    targets = {
        "garden-host": offering("~/ssh/id_a"),
        "other-host": offering("~/ssh/id_b"),
    }
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    threads = tracked_threads(monkeypatch)
    checker = HeldPerAlias(targets, holds)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await k_waits(app, pilot, checker)
            await pilot.press("e")
            await wait_for(pilot, lambda: showing(app, MachineForm))
            app.screen.query_one("#form-alias", Input).value = "other-host"
            await pilot.press("ctrl+s")
            await wait_for(pilot, lambda: len(app.screen_stack) == 1)
            await pilot.press("k")
            await wait_for(pilot, lambda: checker.resolved.count("other-host") == 1)
            # garden-host answers first: startup's and the first K's lookup.
            holds["garden-host"].set()
            for thread in threads[:-1]:
                thread.join(5)
            await pilot.pause()
            assert not isinstance(app.screen, KeySetup)
            holds["other-host"].set()
            await wait_for(pilot, lambda: showing(app, KeySetup))
            assert option_labels(app.screen)[0] == (
                "id_b.pub (your SSH config offers this)"
            )
    finally:
        for hold in holds.values():
            hold.set()


async def test_without_a_terminal_handoff_nothing_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: False))
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Cannot hand off this terminal. Run SSH Workbench in a local terminal. "
            "Machine 1: box"
        )
    assert native.calls == []


async def test_key_setup_hands_the_terminal_over_and_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    seen: list[tuple[bool, bool | None, bool | None]] = []

    class Watched(Native):
        def __call__(self, arguments: list[str], name: str = "SSH") -> int:
            seen.append(
                (
                    app._connecting,
                    app.check_action("key_setup", ()),
                    app.check_action("connect", ()),
                )
            )
            return super().__call__(arguments, name)

    native = Watched()
    # A machine with its own key: no save afterwards, which would refocus the list.
    key = tmp_path / "ssh" / "id_keyed"
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key=str(key))
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)
    Path(f"{key}.pub").write_text(public_key(3, "keyed").line + "\n", "ascii")
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: events.append("suspend"),
    )
    monkeypatch.setattr(
        HeadlessDriver, "resume_application_mode", lambda self: events.append("resume")
    )
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("tab")
        assert app.focused is not app.query_one(ListView)
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert events == ["suspend", "resume"]
        assert seen == [(True, None, None), (True, None, None)]
        assert app.focused is app.query_one(ListView)
        assert not app._connecting
        assert app.check_action("key_setup", ()) is True
        assert connection_status(app) == "Key login works. Machine 1: keyed"
    assert [Native.step(call) for call in native.calls] == ["install", "test"]
    assert path.read_text(encoding="utf-8") == text


async def test_a_key_in_a_missing_home_folder_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key="~/.ssh/id_keyed")
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)

    def no_home(cls: type[Path]) -> Path:
        raise RuntimeError("no home folder")

    monkeypatch.setattr(Path, "home", classmethod(no_home))
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("k")
        await wait_for(pilot, lambda: "Machine 1:" in connection_status(app))
        assert connection_status(app) == (
            "Could not find your home folder for this machine's key. Machine 1: keyed"
        )
        assert not isinstance(app.screen, KeySetup)
        assert app.is_running
    assert native.calls == []


async def test_k_is_dimmed_for_a_missing_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    record = AliasRecord("192.0.2.10", "dev", 22)
    state_path(path, platform.node()).write_text(
        format_state(
            AliasMemory(("garden-host",), {"garden-host": record}, {}),
            platform.node(),
        ),
        encoding="utf-8",
    )
    checker = FakeChecker(None)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(
            pilot,
            lambda: [s.state for s in app.query(StatusSymbol)] == [State.NOT_FOUND],
        )
        assert app.check_action("key_setup", ()) is None
        await pilot.press("k")
        await pilot.pause()
        assert not isinstance(app.screen, KeySetup)


async def test_footer_with_k_fits_60_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), Native())
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test(size=(60, 20)) as pilot:
        footer = app.query_one(Footer)
        await wait_for(
            pilot,
            lambda: "key_setup" in {key.action for key in footer.query("FooterKey")},
        )
        await wait_for(
            pilot, lambda: all(key.region.width for key in footer.query("FooterKey"))
        )
        for key in footer.query("FooterKey"):
            assert key.region.right <= 59, key.action


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_the_picker_shows_its_note_and_keys_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text)
    async with app.run_test(size=size) as pilot:
        screen = await picker(app, pilot)
        await wait_for(pilot, lambda: note(screen).startswith("Your SSH config"))
        await pilot.pause()
        box = screen.query_one("#key-setup")
        assert box.region.bottom <= size[1]
        for widget in ("#key-note", "#key-help", "#key-choices", "#key-system"):
            region = screen.query_one(widget).region
            assert region.height > 0, widget
            assert box.region.contains_region(region), widget


NO_KEY = (
    "No key to offer: your SSH folder has no valid .pub file, and a key named "
    "{} already exists; nothing was installed."
)


def recorded_suspends(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    suspended: list[bool] = []
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: suspended.append(True),
    )
    return suspended


async def k_answered(app: SSHWorkbenchApp, pilot) -> None:
    """K opened the picker or reported something in the status line."""
    await pilot.press("k")
    await wait_for(
        pilot,
        lambda: showing(app, KeySetup) or "Machine 1:" in connection_status(app),
    )


def unlisted(screen: KeySetup) -> str:
    return str(screen.query_one("#key-unlisted", Static).content)


async def test_no_key_to_offer_opens_no_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    (folder / "id_a.pub").unlink()
    (folder / "id_b.pub").unlink()
    (folder / "id_ed25519_box").write_text("fictional private half\n", "ascii")
    suspended = recorded_suspends(monkeypatch)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await k_answered(app, pilot)
        assert not isinstance(app.screen, KeySetup)
        assert connection_status(app) == (
            f"{NO_KEY.format('id_ed25519_box')} Machine 1: box"
        )
    assert native.calls == []
    assert suspended == []
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    ("pub", "message"),
    [
        (None, "Could not read id_keyed.pub; nothing was installed."),
        (
            "not a key\n",
            "id_keyed.pub is not a single valid OpenSSH public key; "
            "nothing was installed.",
        ),
    ],
)
async def test_a_machines_own_key_without_a_valid_pub_opens_no_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pub: str | None, message: str
) -> None:
    native = Native()
    key = tmp_path / "ssh" / "id_keyed"
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key=str(key))
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)
    key.write_text("fictional private half\n", "ascii")
    if pub is not None:
        Path(f"{key}.pub").write_text(pub, "ascii")
    suspended = recorded_suspends(monkeypatch)
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await k_answered(app, pilot)
        assert not isinstance(app.screen, KeySetup)
        assert connection_status(app) == f"{message} Machine 1: keyed"
    assert native.calls == []
    assert suspended == []


def keys_without_pub(folder: Path, names: tuple[str, ...]) -> AliasTarget:
    """Garden's config offers these keys, id_lab (with a valid .pub), a key
    that doesn't exist and a folder; each named key is a private file only."""
    for name in names:
        (folder / name).write_text("fictional private half\n", "ascii")
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    (folder / "id_dir").mkdir()
    files = [f"~/ssh/{name}" for name in names]
    files[1:1] = ["~/ssh/id_lab", "~/ssh/id_gone", "~/ssh/id_dir"]
    return AliasTarget(
        "192.0.2.10", 22, proxied=False, user="dev", identity_files=tuple(files)
    )


@pytest.mark.parametrize(
    ("names", "line"),
    [
        (
            ("id_work",),
            "Not listed: id_work, which your SSH config offers, has no valid "
            ".pub file.",
        ),
        (
            ("id_work", "my key"),
            "Not listed: id_work and my key, which your SSH config offers, have "
            "no valid .pub file.",
        ),
        (
            ("id_work", "my key", "id_old"),
            "Not listed: id_work, my key and id_old, which your SSH config "
            "offers, have no valid .pub file.",
        ),
    ],
)
async def test_an_alias_names_its_keys_without_a_pub_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    names: tuple[str, ...],
    line: str,
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    checker = FakeChecker(keys_without_pub(folder, names))
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        screen = await picker(app, pilot)
        assert option_labels(screen) == [
            "id_lab.pub (your SSH config offers this)",
            "id_a.pub",
            "id_b.pub",
            "Create a new key: id_ed25519_garden",
        ]
        assert unlisted(screen) == line


async def test_a_config_naming_the_pub_file_gets_no_not_listed_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Some agents' setup guides say to name the .pub: `IdentityFile ~/.ssh/x.pub`.
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    target = AliasTarget(
        "192.0.2.10", 22, proxied=False, identity_files=("~/ssh/id_a.pub",)
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        screen = await picker(app, pilot)
        assert option_labels(screen) == [
            "id_a.pub (your SSH config offers this)",
            "id_b.pub",
            "Create a new key: id_ed25519_garden",
        ]
        assert note(screen) == ""
        assert not screen.query("#key-unlisted")


async def test_a_config_naming_the_pub_file_tests_without_a_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    target = AliasTarget(
        "192.0.2.10", 22, proxied=False, identity_files=("~/ssh/id_a.pub",)
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == "Key login works. Machine 1: garden"
    assert native.calls[0][-1] == posix_install_command(public_key(1, "a"))


@pytest.mark.parametrize(
    ("identity_files", "hint"),
    [
        (
            ("~/ssh/id_a.pub",),
            " Your SSH config names id_a.pub for garden-host, which SSH uses only "
            "through an agent that holds the key; without one, add this line under "
            "Host garden-host: IdentityFile {folder}",
        ),
        # The private key is named too, so SSH can load it without an agent.
        (("~/ssh/id_a.pub", "~/ssh/id_a"), ""),
    ],
    ids=["pub-only", "pub-and-key"],
)
async def test_a_failed_test_of_a_named_pub_explains_the_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity_files: tuple[str, ...],
    hint: str,
) -> None:
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    target = AliasTarget("192.0.2.10", 22, proxied=False, identity_files=identity_files)
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            f"status 255).{hint.format(folder=folder / 'id_a')} Machine 1: garden"
        )


async def test_a_named_pub_that_is_missing_lists_its_key_as_not_listed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    (folder / "id_work").write_text("fictional private half\n", "ascii")
    target = AliasTarget(
        "192.0.2.10", 22, proxied=False, identity_files=("~/ssh/id_work.pub",)
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        screen = await picker(app, pilot)
        assert unlisted(screen) == (
            "Not listed: id_work, which your SSH config offers, has no valid .pub file."
        )


async def test_an_alias_with_no_key_to_offer_names_its_unlisted_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_a.pub").unlink()
    (folder / "id_b.pub").unlink()
    (folder / "id_ed25519_garden").write_text("fictional private half\n", "ascii")
    (folder / "id_work").write_text("fictional private half\n", "ascii")
    target = AliasTarget(
        "192.0.2.10", 22, proxied=False, identity_files=("~/ssh/id_work",)
    )
    checker = FakeChecker(target)
    suspended = recorded_suspends(monkeypatch)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await k_answered(app, pilot)
        assert not isinstance(app.screen, KeySetup)
        assert connection_status(app) == (
            f"{NO_KEY.format('id_ed25519_garden')} Not listed: id_work, which your "
            "SSH config offers, has no valid .pub file. Machine 1: garden"
        )
    assert native.calls == []
    assert suspended == []


# The test folder's notes name it in full, which can scroll at 60x20, so the
# configured key, which has no note, stays highlighted there; a real
# "~/.ssh/..." note is measured in the 60x20 real-note test below.
@pytest.mark.parametrize(("size", "with_note"), [((80, 24), True), ((60, 20), False)])
async def test_the_picker_shows_its_unlisted_keys_whole(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int],
    with_note: bool,
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    checker = FakeChecker(keys_without_pub(folder, ("id_work", "my key")))
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test(size=size) as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        screen = await picker(app, pilot)
        if with_note:
            await pilot.press("down")
            await wait_for(pilot, lambda: note(screen).startswith("Your SSH config"))
        await pilot.pause()
        box = screen.query_one("#key-setup")
        assert box.region.bottom <= size[1]
        # The box's region includes its border, so only this catches a row
        # hidden behind it.
        assert box.max_scroll_y == 0
        for widget in (
            "#key-note",
            "#key-choices",
            "#key-unlisted",
            "#key-system",
            "#key-help",
        ):
            region = screen.query_one(widget).region
            assert region.height > 0, widget
            assert box.region.contains_region(region), widget


async def test_the_picker_fits_60x20_with_a_real_note_and_the_not_listed_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The choices a real ~/.ssh folder gives; a test folder's absolute path
    # would make every note several rows longer.
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    note_text = (
        "Your SSH config doesn't name this key for garden-host. Add this line "
        "under Host garden-host; Workbench never edits the config: "
        "IdentityFile ~/.ssh/id_a"
    )
    ssh = Path("~/.ssh")
    choices = [
        KeyChoice(ssh / "id_lab", "id_lab.pub (your SSH config offers this)"),
        KeyChoice(ssh / "id_a", "id_a.pub", note=note_text),
        KeyChoice(ssh / "id_b", "id_b.pub", note=note_text),
        KeyChoice(
            ssh / "id_ed25519_garden",
            "Create a new key: id_ed25519_garden",
            True,
            note_text,
        ),
    ]
    line = (
        "Not listed: id_work and id_old, which your SSH config offers, have no "
        "valid .pub file."
    )
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text)
    async with app.run_test(size=(60, 20)) as pilot:
        app.push_screen(KeySetup(GARDEN, choices, None, line))
        await wait_for(pilot, lambda: showing(app, KeySetup))
        screen = app.screen
        await pilot.press("down")
        await wait_for(pilot, lambda: note(screen) == note_text)
        await pilot.pause()
        box = screen.query_one("#key-setup")
        assert box.max_scroll_y == 0
        for widget in (
            "#key-note",
            "#key-choices",
            "#key-unlisted",
            "#key-system",
            "#key-help",
        ):
            assert box.region.contains_region(screen.query_one(widget).region), widget
