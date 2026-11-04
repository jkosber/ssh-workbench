"""A key path starting with `~/` or `~\\` names a file inside the home folder.

Workbench joins the rest of such a key to the home folder, and the export
writes it as given, so a `..` or `.` part, or the empty part a doubled or
trailing separator leaves, would name a file outside the home folder or a
folder instead of a key. A name that only starts with dots is still a file
name. Fictional values only.
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
TRIGGER = "~/../../etc/x"
OUTSIDE = [
    TRIGGER,
    "~\\..\\..\\x",
    "~/..",
    "~/.",
    "~/.ssh/../id_x",
    "~/.ssh//id_x",
    "~/.ssh/id_x/",
]
KEYS = [
    "~/.ssh/id_x",
    "~\\.ssh\\id_x",
    "~/keys/sub/id_x",
    "~/.ssh/id_x.old",
    "~/.ssh/..hidden",
]


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\") + '"'


@pytest.mark.parametrize("key", OUTSIDE)
def test_a_dot_or_empty_part_after_the_tilde_is_not_a_key_path(key: str) -> None:
    assert is_valid_key_path(key) is False


@pytest.mark.parametrize("key", KEYS)
def test_a_key_file_in_the_home_folder_stays_valid(key: str) -> None:
    assert is_valid_key_path(key) is True


def test_a_machine_file_with_a_key_outside_the_home_folder_does_not_load() -> None:
    text = (
        f"# {MARKER}\nschema_version = 2\n\n[[machines]]\n"
        f'id = "box"\nname = "{MARKER} box"\naddresses = ["192.0.2.60"]\n'
        f"key = {toml_string(TRIGGER)}\n\n[[machines]]\n"
        f'id = "other"\nname = "Other"\naddresses = ["192.0.2.61"]\n'
        f'key = "~/.ssh/{MARKER}"\n'
    )

    with pytest.raises(ConfigError) as caught:
        parse_machines(text)

    error = caught.value
    assert str(error) == f"machines[1].key: {KEY_RULE}"
    shown = "".join(traceback.format_exception(error))
    assert TRIGGER not in shown
    assert MARKER not in shown


def test_the_machine_form_rejects_a_key_outside_the_home_folder() -> None:
    table = {
        "id": "box",
        "name": "Box",
        "addresses": ["192.0.2.60"],
        "key": TRIGGER,
    }

    with pytest.raises(ConfigError) as caught:
        validate_machine(table, "machine")

    assert str(caught.value) == f"machine.key: {KEY_RULE}"
