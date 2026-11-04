"""A key path that names only a filesystem root never loads.

K finds a machine key's public key by adding `.pub` to the path's last part,
and a root such as `/`, `C:\\` or `\\\\server\\share\\` has none. Either
system's form is checked on every system, because one machine file may be
shared between Windows and Linux. Fictional values only.
"""

import traceback

import pytest

from ssh_workbench.config import (
    ConfigError,
    is_valid_key_path,
    parse_machines,
    validate_machine,
)

MARKER = "private-marker"
KEY_RULE = (
    "expected an absolute path or one starting with ~/, "
    "without quotes, %, ${ or control characters"
)
ROOTS = [
    "/",
    "//",
    "/.",
    "C:\\",
    "C:/",
    "\\\\server\\share\\",
    # Linux reads this as the folder `share`; Windows reads it as a share root.
    "//server/share/",
]
KEYS = [
    "/home/example/.ssh/id_x",
    "C:\\Users\\example\\.ssh\\id_x",
    "~/.ssh/id_x",
]


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\") + '"'


@pytest.mark.parametrize("key", ROOTS)
def test_a_root_is_not_a_key_path(key: str) -> None:
    assert is_valid_key_path(key) is False


@pytest.mark.parametrize("key", KEYS)
def test_a_key_file_path_stays_valid(key: str) -> None:
    assert is_valid_key_path(key) is True


@pytest.mark.parametrize("key", ROOTS)
def test_a_machine_file_with_a_root_key_does_not_load(key: str) -> None:
    text = (
        f"# {MARKER}\nschema_version = 2\n\n[[machines]]\n"
        f'id = "box"\nname = "{MARKER} box"\naddresses = ["192.0.2.60"]\n'
        f"key = {toml_string(key)}\n\n[[machines]]\n"
        f'id = "other"\nname = "Other"\naddresses = ["192.0.2.61"]\n'
        f'key = "~/.ssh/{MARKER}"\n'
    )

    with pytest.raises(ConfigError) as caught:
        parse_machines(text)

    error = caught.value
    assert str(error) == f"machines[1].key: {KEY_RULE}"
    assert MARKER not in "".join(traceback.format_exception(error))


@pytest.mark.parametrize("key", ROOTS)
def test_the_machine_form_rejects_a_root_key(key: str) -> None:
    table = {"id": "box", "name": "Box", "addresses": ["192.0.2.60"], "key": key}

    with pytest.raises(ConfigError) as caught:
        validate_machine(table, "machine")

    assert str(caught.value) == f"machine.key: {KEY_RULE}"
