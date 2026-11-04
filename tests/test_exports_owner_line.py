"""A machine file whose folder name holds a character `str.splitlines` breaks at,
but SSH doesn't, still owns the generated file it wrote; temporary folders only.

U+2028, U+2029 and U+0085 pass the control-character check, and Linux and NTFS
allow each in a folder name.
"""

from pathlib import Path

import pytest

from ssh_workbench.config import Machine, format_machines
from ssh_workbench.exports import EXPORT_NAME, _owner, format_exports, write_exports

BOX = Machine("box", "Box", addresses=("192.0.2.60",), export_alias=True)


@pytest.mark.parametrize(
    "name", ["dir\u2028tail", "dir\u2029tail", "dir\x85tail", "plain"]
)
def test_a_second_save_keeps_the_exports_of_the_same_machine_file(
    tmp_path: Path, name: str
) -> None:
    folder = tmp_path / "ssh"
    exported = folder / EXPORT_NAME
    source = tmp_path / name / "machines.toml"
    source.parent.mkdir()
    source.write_text(format_machines((BOX,)), encoding="utf-8")

    write_exports(folder, [BOX], source)
    assert write_exports(folder, [BOX], source) is None

    assert exported.is_file()
    assert exported.read_text(encoding="utf-8") == format_exports([BOX], source)
    assert _owner(exported) == str(source)
