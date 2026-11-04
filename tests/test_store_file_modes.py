"""Saving keeps the machine file's mode and gives the backup the private default."""

import os
import stat
import sys
from pathlib import Path

import pytest

from ssh_workbench.config import Machine, read_machines
from ssh_workbench.store import backup_path, save_machines

MACHINES = [Machine("mint", "Mint", alias="mint-host")]
ORIGINAL = b"schema_version = 2\nmachines = []\n"


@pytest.mark.parametrize("mode", [0o644, 0o640], ids=oct)
def test_save_keeps_the_file_mode_and_gives_the_backup_0o600(
    tmp_path: Path, mode: int
) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(ORIGINAL)
    if sys.platform != "win32":
        path.chmod(mode)
    _, loaded = read_machines(path)

    text = save_machines(path, MACHINES, loaded)

    assert path.read_bytes() == text.encode("utf-8")
    assert backup_path(path).read_bytes() == ORIGINAL
    if sys.platform != "win32":
        # The temporary file starts at 0o600; only the copied mode makes it
        # match the original. The backup keeps that private default.
        assert stat.S_IMODE(path.stat().st_mode) == mode
        assert stat.S_IMODE(backup_path(path).stat().st_mode) == 0o600
    else:
        # Windows keeps only the read-only flag, so both files stay replaceable.
        assert os.access(path, os.W_OK) is True
        assert os.access(backup_path(path), os.W_OK) is True
