"""Saving the machine file: change check, backup and atomic replace."""

import os
import stat
from pathlib import Path

import pytest

from ssh_workbench import store
from ssh_workbench.config import Machine, format_machines, parse_machines, read_machines
from ssh_workbench.store import FileChangedError, SaveError, backup_path, save_machines

MACHINES = [Machine("mint", "Mint", alias="mint-host")]
ORIGINAL = b"# Hand-written notes\r\nschema_version = 2\r\nmachines = []\r\n"
OTHER = b'schema_version = 2\n[[machines]]\nid = "other"\nname = "Other"\nalias = "o"\n'


def snapshot(folder: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(folder.iterdir())}


def test_first_save_creates_folder_and_file(tmp_path: Path) -> None:
    path = tmp_path / "new" / "ssh-workbench" / "machines.toml"

    text = save_machines(path, MACHINES, None)

    assert text == format_machines(MACHINES)
    assert path.read_bytes() == text.encode("utf-8")
    assert snapshot(path.parent) == {"machines.toml": text.encode("utf-8")}


def test_save_writes_utf8_with_lf_and_no_byte_order_mark(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    save_machines(path, [Machine("cafe", "Café", alias="cafe-host")], None)
    data = path.read_bytes()
    assert data.startswith(b"schema_version = 2\n")
    assert b"\r" not in data
    assert "Café".encode() in data


def test_save_keeps_the_previous_bytes_as_backup(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(ORIGINAL)
    _, loaded = read_machines(path)

    text = save_machines(path, MACHINES, loaded)

    assert backup_path(path) == tmp_path / "machines.toml.bak"
    assert snapshot(tmp_path) == {
        "machines.toml": text.encode("utf-8"),
        "machines.toml.bak": ORIGINAL,
    }
    assert parse_machines(path.read_text(encoding="utf-8")) == MACHINES

    save_machines(path, [], text)
    assert backup_path(path).read_bytes() == text.encode("utf-8")
    assert parse_machines(path.read_text(encoding="utf-8")) == []


def test_unchanged_text_is_not_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    original = format_machines(MACHINES).replace("\n", "\r\n").encode("utf-8")
    path.write_bytes(original)
    _, loaded = read_machines(path)

    assert save_machines(path, MACHINES, loaded) == format_machines(MACHINES)

    assert snapshot(tmp_path) == {"machines.toml": original}


@pytest.mark.parametrize("change", ["edited", "created", "deleted"])
def test_outside_change_is_never_overwritten(tmp_path: Path, change: str) -> None:
    path = tmp_path / "machines.toml"
    expected: str | None = None
    if change == "created":
        path.write_bytes(OTHER)
    else:
        path.write_bytes(ORIGINAL)
        _, expected = read_machines(path)
        if change == "edited":
            path.write_bytes(OTHER)
        else:
            path.unlink()
    before = snapshot(tmp_path)

    with pytest.raises(FileChangedError) as caught:
        save_machines(path, MACHINES, expected)

    assert str(caught.value) == "The machine file changed outside Workbench."
    assert snapshot(tmp_path) == before


def test_failed_replace_leaves_the_file_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(ORIGINAL)
    _, loaded = read_machines(path)
    real_replace = os.replace

    def fail_for_the_machine_file(source: str, target: str) -> None:
        if Path(target) == path:
            raise PermissionError("private-marker")
        real_replace(source, target)

    monkeypatch.setattr(store.os, "replace", fail_for_the_machine_file)

    with pytest.raises(SaveError) as caught:
        save_machines(path, MACHINES, loaded)

    assert str(caught.value) == "Could not save the machine file: permission denied."
    assert caught.value.__suppress_context__
    assert snapshot(tmp_path) == {
        "machines.toml": ORIGINAL,
        "machines.toml.bak": ORIGINAL,
    }


def test_failed_write_leaves_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(ORIGINAL)
    _, loaded = read_machines(path)

    def disk_full(descriptor: int) -> None:
        raise OSError(28, "private-marker")

    monkeypatch.setattr(store.os, "fsync", disk_full)

    with pytest.raises(SaveError) as caught:
        save_machines(path, MACHINES, loaded)

    assert str(caught.value) == "Could not save the machine file: could not write."
    assert "private-marker" not in str(caught.value)
    assert snapshot(tmp_path) == {"machines.toml": ORIGINAL}


def test_folder_at_the_path_is_a_save_error(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    path.mkdir()

    with pytest.raises(SaveError) as caught:
        save_machines(path, MACHINES, None)

    assert str(caught.value) == (
        "Could not save the machine file: expected a file, got a directory."
    )
    assert str(tmp_path) not in str(caught.value)
    assert list(path.iterdir()) == []


def test_read_only_file_leaves_no_temporary_file_and_saves_once_writable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(ORIGINAL)
    _, loaded = read_machines(path)
    path.chmod(stat.S_IREAD)
    try:
        if os.name == "nt":
            # Windows refuses to replace a read-only file.
            with pytest.raises(SaveError) as caught:
                save_machines(path, MACHINES, loaded)
            assert str(caught.value) == (
                "Could not save the machine file: permission denied."
            )
            assert path.read_bytes() == ORIGINAL
        else:
            # POSIX replaces the directory entry and keeps the file's mode.
            save_machines(path, MACHINES, loaded)
            assert stat.S_IMODE(path.stat().st_mode) == stat.S_IREAD
        assert [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []
        assert os.access(backup_path(path), os.W_OK)
    finally:
        path.chmod(stat.S_IREAD | stat.S_IWRITE)
    _, loaded = read_machines(path)

    save_machines(path, [], loaded)

    assert parse_machines(path.read_text(encoding="utf-8")) == []


def test_file_mode_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(ORIGINAL)
    path.chmod(0o600)
    before = stat.S_IMODE(path.stat().st_mode)
    _, loaded = read_machines(path)

    save_machines(path, MACHINES, loaded)

    assert stat.S_IMODE(path.stat().st_mode) == before
    if os.name == "posix":
        assert before == 0o600
