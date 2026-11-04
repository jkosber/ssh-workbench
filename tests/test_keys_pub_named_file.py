"""A `.pub` file whose name holds no key name, such as `.pub` or `..pub`.

`ssh-keygen -y -f key > ~/.ssh/$UNSET.pub` leaves a file named only `.pub`.
It names no private key, so it is no choice for K, and K still offers the
folder's other keys. Everything is fictional and substituted: no real ssh,
ssh-keygen, key, SSH folder or machine file.
"""

import asyncio
import base64
import struct
from pathlib import Path

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import OptionList

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import PublicKey, public_key_files

SSH = "/fictional/ssh"
KEYGEN = "/fictional/ssh-keygen"
BOX = Machine("box", "Box", user="dev", addresses=("192.0.2.60",))
# Names whose part before `.pub` is empty or only dots.
NO_KEY_NAMES = (".pub", "..pub", "...pub")


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


def key_folder(tmp_path: Path) -> Path:
    """An SSH folder with `id_a.pub` and a valid key under each no-key name."""
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text("", encoding="ascii")
    (folder / "id_a.pub").write_text(public_key(1, "a").line + "\n", "ascii")
    for name in NO_KEY_NAMES:
        (folder / name).write_text(public_key(2, "b").line + "\n", "ascii")
    return folder


class Native:
    """Records each handed-off command; every step exits 0."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        return 0


def test_public_key_files_skips_a_pub_file_without_a_key_name(
    tmp_path: Path,
) -> None:
    folder = key_folder(tmp_path)

    assert sorted(entry.name for entry in folder.iterdir()) == [
        "...pub",
        "..pub",
        ".pub",
        "config",
        "id_a.pub",
    ]
    assert public_key_files(folder) == [folder / "id_a.pub"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("no_external_actions", "no_app_connections")
async def test_k_offers_the_folder_keys_beside_a_pub_file_without_a_key_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = key_folder(tmp_path)
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines((BOX,))
    path.write_text(text, encoding="utf-8")
    native = Native()
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))

    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("k")
        # push_screen makes a screen current before it has composed its widgets.
        async with asyncio.timeout(5):
            while app.is_running and not (
                isinstance(app.screen, KeySetup) and app.screen.is_mounted
            ):
                await pilot.pause()
        assert app.return_code is None
        options = app.screen.query_one(OptionList)
        assert [
            str(options.get_option_at_index(index).prompt)
            for index in range(options.option_count)
        ] == ["id_a.pub", "Create a new key: id_ed25519_box"]
        await pilot.press("escape")
        async with asyncio.timeout(5):
            while isinstance(app.screen, KeySetup):
                await pilot.pause()
        assert app.return_code is None
    assert native.calls == []
    assert path.read_text(encoding="utf-8") == text
