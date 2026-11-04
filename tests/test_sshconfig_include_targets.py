"""Include targets in fictional SSH folders: a key file is never read, whatever
name the Include gives it."""

import os
from pathlib import Path

import pytest

from ssh_workbench.sshconfig import host_names

KEY_TEXT = "MARKER fictional key file, not a real key\nHost leaked-from-key\n"


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Names of the files read, in order; each read still returns the bytes."""
    read: list[str] = []
    original = Path.read_bytes

    def record(path: Path) -> bytes:
        read.append(path.name)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", record)
    return read


def test_an_include_linked_to_a_key_file_is_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reads: list[str]
) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include hosts.conf\nHost safe-host\n")
    key = write(folder, "id_test", KEY_TEXT)
    link = folder / "hosts.conf"
    try:
        os.symlink("id_test", link)
    except OSError:
        # Creating a link needs a privilege some Windows accounts lack. Stand in
        # for it at the file system: hosts.conf holds the key's text and
        # resolves to the key, as a link to it does.
        write(folder, "hosts.conf", KEY_TEXT)
        real_resolve = Path.resolve
        key_target = real_resolve(key)
        monkeypatch.setattr(
            Path,
            "resolve",
            lambda self, strict=False: (
                key_target if self == link else real_resolve(self, strict)
            ),
        )
    assert link.resolve().name == "id_test"
    assert link.read_text(encoding="utf-8") == KEY_TEXT
    reads.clear()

    assert host_names(folder) == ["safe-host"]
    assert reads == ["config"]


def test_an_include_naming_a_key_file_is_never_read(
    tmp_path: Path, reads: list[str]
) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include id_test\nHost safe-host\n")
    write(folder, "id_test", KEY_TEXT)

    assert host_names(folder) == ["safe-host"]
    assert reads == ["config"]


def test_an_include_of_a_regular_file_is_read(tmp_path: Path, reads: list[str]) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include hosts.conf\nHost safe-host\n")
    write(folder, "hosts.conf", "Host from-hosts\n")

    assert host_names(folder) == ["from-hosts", "safe-host"]
    assert reads == ["config", "hosts.conf"]
