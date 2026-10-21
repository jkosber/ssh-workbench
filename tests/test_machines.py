"""Schema 2 machine files and schema 1 project files loaded as machines."""

import json
import traceback
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ssh_workbench.config import (
    ConfigError,
    Link,
    Machine,
    load_machines,
    parse_machines,
)

ALIAS = {"id": '"mint"', "name": '"Mint laptop"', "alias": '"mint-host"'}
DIRECT = {
    "id": '"agent-box"',
    "name": '"Agent mini PC"',
    "addresses": '["100.64.0.12"]',
}


def table(base: dict[str, str], **fields: str | None) -> str:
    """Field values are TOML literals; None removes a field from the base."""
    values = dict(base)
    for key, value in fields.items():
        if value is None:
            values.pop(key, None)
        else:
            values[key] = value
    return "\n".join(f"{key} = {value}" for key, value in values.items())


def machine_file(*tables: str) -> str:
    return "schema_version = 2\n" + "".join(
        f"\n[[machines]]\n{text}\n" for text in tables
    )


def config_error(text: str) -> ConfigError:
    with pytest.raises(ConfigError) as caught:
        parse_machines(text)
    return caught.value


def assert_private(error: ConfigError, value: str) -> None:
    if len(value) >= 3:
        assert value not in str(error)
        assert value not in "".join(traceback.format_exception(error))


def test_schema_2_alias_and_direct_machines_in_file_order(tmp_path: Path) -> None:
    text = (
        "schema_version = 2\n\n"
        '[[machines]]\nid = "mint"\nname = "Mint laptop"\nalias = "mint-host"\n\n'
        '[[machines]]\nid = "agent-box"\nname = "Agent mini PC"\nuser = "dev"\n'
        'addresses = ["100.64.0.12", "192.168.1.40"]\nport = 22\n'
        'key = "~/.ssh/id_ed25519_agent_box"\n\n'
        '[[machines.links]]\nname = "Dashboard"\nurl = "https://192.168.1.40:8006"\n'
    )
    path = tmp_path / "machines.toml"
    path.write_text(text, encoding="utf-8")

    assert load_machines(path) == [
        Machine("mint", "Mint laptop", alias="mint-host"),
        Machine(
            "agent-box",
            "Agent mini PC",
            user="dev",
            addresses=("100.64.0.12", "192.168.1.40"),
            port=22,
            key="~/.ssh/id_ed25519_agent_box",
            links=(Link("Dashboard", "https://192.168.1.40:8006"),),
        ),
    ]
    assert path.read_text(encoding="utf-8") == text


def test_alias_machine_with_links() -> None:
    text = machine_file(
        table(ALIAS)
        + '\n[[machines.links]]\nname = "Docs"\nurl = "https://example.invalid/d"'
        + '\n[[machines.links]]\nname = "Repo"\nurl = "https://example.invalid/r"'
    )
    assert parse_machines(text) == [
        Machine(
            "mint",
            "Mint laptop",
            alias="mint-host",
            links=(
                Link("Docs", "https://example.invalid/d"),
                Link("Repo", "https://example.invalid/r"),
            ),
        )
    ]


def test_utf8_byte_order_mark_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "machines.toml"
    path.write_bytes(b"\xef\xbb\xbf" + machine_file(table(ALIAS)).encode("utf-8"))
    assert load_machines(path) == [Machine("mint", "Mint laptop", alias="mint-host")]


def test_empty_machine_collection() -> None:
    assert parse_machines("schema_version = 2\nmachines = []") == []


def test_machine_records_are_immutable() -> None:
    machine = parse_machines(machine_file(table(DIRECT)))[0]
    assert machine.addresses == ("100.64.0.12",)
    with pytest.raises(FrozenInstanceError):
        machine.name = "Changed"


def test_schema_1_projects_load_as_alias_machines_with_named_links() -> None:
    text = (
        'schema_version = 1\n[[projects]]\nid = "garden"\nname = "Garden"\n'
        'ssh_alias = "garden-host"\nrepository = "https://example.invalid/g.git"\n'
        'documentation = "https://example.invalid/g/docs"\n'
        '[[projects]]\nid = "notes"\nname = "Notes"\nssh_alias = "notes-host"\n'
        'documentation = "https://example.invalid/n/docs"\n'
        '[[projects]]\nid = "plain"\nname = "Plain"\nssh_alias = "plain-host"\n'
    )
    assert parse_machines(text) == [
        Machine(
            "garden",
            "Garden",
            alias="garden-host",
            links=(
                Link("Repository", "https://example.invalid/g.git"),
                Link("Documentation", "https://example.invalid/g/docs"),
            ),
        ),
        Machine(
            "notes",
            "Notes",
            alias="notes-host",
            links=(Link("Documentation", "https://example.invalid/n/docs"),),
        ),
        Machine("plain", "Plain", alias="plain-host"),
    ]


def test_schema_1_errors_keep_project_locations() -> None:
    error = config_error(
        'schema_version = 1\n[[projects]]\nid = "garden"\nname = "Garden"\n'
        'ssh_alias = "--private-marker"\n'
    )
    assert str(error).startswith("projects[1].ssh_alias:")
    assert_private(error, "--private-marker")


@pytest.mark.parametrize("version", ["0", "3", "-1", "true", '"2"', "2.0", "[]"])
def test_schema_version_accepts_only_1_and_2(version: str) -> None:
    error = config_error(f"schema_version = {version}\nmachines = []")
    assert str(error) == "schema_version: expected integer 1 or 2"


def test_directory_has_a_file_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        load_machines(tmp_path)
    assert str(caught.value) == "configuration: expected a file, got a directory"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("schema_version = 2", "machines: required array is missing"),
        ("schema_version = 2\nmachines = {}", "machines: expected an array"),
        ('schema_version = 2\nmachines = "x"', "machines: expected an array"),
        ("schema_version = 2\nmachines = [1]", "machines[1]: expected a machine table"),
        (
            "schema_version = 2\nmachines = []\nprojects = []",
            "configuration: unknown field; allowed fields: machines, schema_version",
        ),
        (
            "schema_version = 2\nprojects = []",
            "configuration: unknown field; allowed fields: machines, schema_version",
        ),
    ],
)
def test_schema_2_structure_errors(text: str, message: str) -> None:
    assert str(config_error(text)).startswith(message)


def test_unknown_machine_field_is_not_echoed() -> None:
    error = config_error(machine_file(table(ALIAS, private_marker_key='"value"')))
    assert str(error) == (
        "machines[1]: unknown field; allowed fields: "
        "addresses, alias, id, key, links, name, port, user"
    )
    assert_private(error, "private_marker_key")


@pytest.mark.parametrize("field", ["id", "name"])
def test_required_machine_fields(field: str) -> None:
    error = config_error(machine_file(table(ALIAS, **{field: None})))
    assert str(error) == f"machines[1].{field}: required field is missing"


@pytest.mark.parametrize("identifier", ["Mint", "a--b", "-mint", "mint-", "a_b", "é"])
def test_invalid_machine_ids(identifier: str) -> None:
    error = config_error(machine_file(table(ALIAS, id=json.dumps(identifier))))
    assert str(error) == (
        "machines[1].id: use lowercase ASCII letters/digits with single hyphens"
    )


def test_duplicate_machine_ids() -> None:
    error = config_error(machine_file(table(ALIAS), table(DIRECT, id='"mint"')))
    assert str(error) == "machines[2].id: duplicate of machines[1].id"


def test_alias_and_addresses_together_are_rejected() -> None:
    error = config_error(machine_file(table(ALIAS, addresses='["host"]')))
    assert str(error) == "machines[1]: use either alias or addresses, not both"


def test_machine_without_alias_or_addresses_is_rejected() -> None:
    error = config_error(machine_file(table(ALIAS, alias=None)))
    assert str(error) == "machines[1]: add alias or addresses"


@pytest.mark.parametrize(
    ("field", "value"), [("user", '"dev"'), ("port", "22"), ("key", '"~/.ssh/id"')]
)
def test_direct_fields_on_alias_machine_are_rejected(field: str, value: str) -> None:
    error = config_error(machine_file(table(ALIAS, **{field: value})))
    assert str(error) == (
        f"machines[1].{field}: only machines with addresses take this field"
    )


@pytest.mark.parametrize(
    "alias", ["-oProxyCommand=x", "user@host", "two hosts", "host:22", "höst"]
)
def test_invalid_aliases(alias: str) -> None:
    error = config_error(machine_file(table(ALIAS, alias=json.dumps(alias))))
    assert str(error).startswith("machines[1].alias: start with an ASCII letter")
    assert_private(error, alias)


@pytest.mark.parametrize(
    "address",
    [
        "host",
        "host.example",
        "under_score.example",
        "Agent-Box.tailnet-name.ts.net",
        "100.64.0.12",
        "fd7a:115c:a1e0::1",
        "::1",
        "a" * 63 + "." + "b" * 63,
    ],
)
def test_valid_addresses_are_preserved(address: str) -> None:
    machines = parse_machines(
        machine_file(table(DIRECT, addresses=json.dumps([address])))
    )
    assert machines[0].addresses == (address,)


@pytest.mark.parametrize(
    "address",
    [
        "",
        " ",
        "-oProxyCommand=x",
        "-host",
        "user@host",
        "two hosts",
        "host\n",
        "host\x00",
        "höst",
        "host:22",
        "[::1]",
        "fe80::1%eth0",
        "999.1.1.1",
        "1.2.3",
        "host-",
        ".host",
        "host.",
        "a..b",
        "a" * 64,
        ".".join(["abcdefghi"] * 26),
        "host;x",
        "host/x",
        "host\\x",
    ],
)
def test_invalid_addresses(address: str) -> None:
    error = config_error(
        machine_file(table(DIRECT, addresses=json.dumps(["ok.example", address])))
    )
    assert str(error) == (
        "machines[1].addresses[2]: expected a hostname or IP address "
        "without spaces, @, ports or a leading dash"
    )
    assert_private(error, address)


@pytest.mark.parametrize("value", ["[]", '"host"', "1", "[1]", "{}"])
def test_addresses_must_be_a_nonempty_string_array(value: str) -> None:
    error = config_error(machine_file(table(DIRECT, addresses=value)))
    assert str(error).startswith("machines[1].addresses")


def test_duplicate_addresses() -> None:
    error = config_error(
        machine_file(table(DIRECT, addresses='["a.example", "b.example", "a.example"]'))
    )
    assert (
        str(error) == "machines[1].addresses[3]: duplicate of machines[1].addresses[1]"
    )


@pytest.mark.parametrize("user", ["dev", "_svc", "first.last-2", "9user"])
def test_valid_users_are_preserved(user: str) -> None:
    machines = parse_machines(machine_file(table(DIRECT, user=json.dumps(user))))
    assert machines[0].user == user


@pytest.mark.parametrize(
    "user",
    ["-l", "-oProxyCommand=x", "a@b", "a b", "DOMAIN\\user", "jösé", ".dev", "x\n"],
)
def test_invalid_users(user: str) -> None:
    error = config_error(machine_file(table(DIRECT, user=json.dumps(user))))
    assert str(error) == (
        "machines[1].user: start with an ASCII letter, digit or underscore; "
        "use only ASCII letters, digits, dots, underscores or hyphens"
    )
    assert_private(error, user)


@pytest.mark.parametrize("value", ['""', '"  "', "1", "true"])
def test_user_must_be_a_nonempty_string(value: str) -> None:
    error = config_error(machine_file(table(DIRECT, user=value)))
    assert str(error) == "machines[1].user: expected a nonempty string"


@pytest.mark.parametrize("port", [1, 22, 65535])
def test_valid_ports_are_preserved(port: int) -> None:
    machines = parse_machines(machine_file(table(DIRECT, port=str(port))))
    assert machines[0].port == port


@pytest.mark.parametrize("value", ["0", "65536", "-1", "true", '"22"', "22.0", "[]"])
def test_invalid_ports(value: str) -> None:
    error = config_error(machine_file(table(DIRECT, port=value)))
    assert str(error) == "machines[1].port: expected an integer from 1 to 65535"


@pytest.mark.parametrize(
    "key",
    [
        "~/.ssh/id_ed25519_box",
        "~\\.ssh\\id_ed25519_box",
        "C:\\Users\\Dev\\.ssh\\id with space",
        "c:/Users/Dev/.ssh/id",
        "/home/dev/.ssh/id_ed25519",
        "\\\\server\\share\\id",
        "~/.ssh/$id",
    ],
)
def test_valid_keys_load_on_every_platform(key: str) -> None:
    machines = parse_machines(machine_file(table(DIRECT, key=json.dumps(key))))
    assert machines[0].key == key


@pytest.mark.parametrize(
    "key",
    [
        "id_ed25519",
        ".ssh/id",
        "~",
        "~user/id",
        "-i",
        " ~/id",
        "~/id ",
        "~/id\n",
        "~/id\x1b",
        '~/"id"',
        "~/${HOME}/id",
        "~/.ssh/100%key",
        "C:relative\\id",
    ],
)
def test_invalid_keys(key: str) -> None:
    error = config_error(machine_file(table(DIRECT, key=json.dumps(key))))
    assert str(error) == (
        "machines[1].key: expected an absolute path or one starting with ~/, "
        "without quotes, %, ${ or control characters"
    )
    assert_private(error, key)


def test_public_key_file_is_rejected() -> None:
    error = config_error(machine_file(table(DIRECT, key='"~/.ssh/id_ed25519.pub"')))
    assert str(error) == "machines[1].key: name the private key file, not its .pub file"


@pytest.mark.parametrize(
    ("links", "message"),
    [
        (
            '[{ url = "https://example.invalid" }]',
            "machines[1].links[1].name: required",
        ),
        ('[{ name = "Docs" }]', "machines[1].links[1].url: required"),
        (
            '[{ name = " ", url = "https://example.invalid" }]',
            "machines[1].links[1].name: expected a nonempty string",
        ),
        (
            '[{ name = "Docs", url = "file:///private-marker" }]',
            "machines[1].links[1].url: expected an absolute HTTP/HTTPS URL",
        ),
        (
            '[{ name = "Docs", url = "https://example.invalid", private_marker = 1 }]',
            "machines[1].links[1]: unknown field; allowed fields: name, url",
        ),
        (
            '[{ name = "Docs", url = "https://a.invalid" }, '
            '{ name = "Docs", url = "https://b.invalid" }]',
            "machines[1].links[2].name: duplicate of machines[1].links[1].name",
        ),
        ('"https://example.invalid"', "machines[1].links: expected an array"),
        ("[1]", "machines[1].links[1]: expected a link table"),
    ],
)
def test_link_rules(links: str, message: str) -> None:
    error = config_error(machine_file(table(DIRECT, links=links)))
    assert str(error).startswith(message)
    assert_private(error, "private-marker")
    assert_private(error, "private_marker")
