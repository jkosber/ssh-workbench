import json
import traceback
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ssh_workbench.config import (
    Project,
    ProjectConfigError,
    load_projects,
    parse_projects,
)


def write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "projects.toml"
    path.write_text(text, encoding="utf-8")
    return path


def project_config(**fields: str) -> str:
    """Field overrides are TOML literals, including deliberately invalid values."""
    values = {
        "id": '"garden-demo"',
        "name": '"Garden demo"',
        "ssh_alias": '"garden-demo-host"',
    }
    values.update(fields)
    return "schema_version = 1\n[[projects]]\n" + "\n".join(
        f"{key} = {value}" for key, value in values.items()
    )


def test_load_single_project_without_optional_fields(tmp_path: Path) -> None:
    text = project_config(name='"  Jardin café  "')
    path = write_config(tmp_path, text)

    assert load_projects(path) == [
        Project("garden-demo", "  Jardin café  ", "garden-demo-host")
    ]
    assert path.read_text(encoding="utf-8") == text


def test_load_multiple_projects_in_file_order(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        project_config(
            id='"z-garden"',
            repository='"https://example.com/fictional/garden.git"',
        )
        + '\n[[projects]]\nid = "a-notes"\nname = "Notes"'
        '\nssh_alias = "Notes_2.example"'
        '\ndocumentation = "http://example.org/fictional/notes?q=help#start"\n',
    )

    assert load_projects(path) == [
        Project(
            "z-garden",
            "Garden demo",
            "garden-demo-host",
            repository="https://example.com/fictional/garden.git",
        ),
        Project(
            "a-notes",
            "Notes",
            "Notes_2.example",
            documentation="http://example.org/fictional/notes?q=help#start",
        ),
    ]


def test_parse_projects_without_file_access() -> None:
    assert parse_projects(project_config()) == [
        Project("garden-demo", "Garden demo", "garden-demo-host")
    ]


def test_project_records_are_immutable() -> None:
    project = parse_projects(project_config())[0]
    with pytest.raises(FrozenInstanceError):
        project.name = "Changed name"


def test_invalid_configuration_is_not_modified(tmp_path: Path) -> None:
    path = write_config(tmp_path, project_config(ssh_alias='"--help"'))
    original = path.read_bytes()
    with pytest.raises(ProjectConfigError, match=r"projects\[1\].ssh_alias:"):
        load_projects(path)
    assert path.read_bytes() == original


def test_documented_example(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "examples/projects.example.toml"
    path = write_config(tmp_path, example.read_text(encoding="utf-8"))

    assert load_projects(path) == [
        Project(
            "garden-demo",
            "Garden demo",
            "garden-demo-host",
            "https://example.com/fictional/garden-demo.git",
            "https://example.com/fictional/garden-demo/docs",
        )
    ]


def test_empty_project_collection(tmp_path: Path) -> None:
    assert (
        load_projects(write_config(tmp_path, "schema_version = 1\nprojects = []")) == []
    )


def test_missing_file_is_not_created(tmp_path: Path) -> None:
    path = tmp_path / "missing.toml"
    with pytest.raises(ProjectConfigError, match="file not found") as caught:
        load_projects(path)
    assert str(path) not in str(caught.value)
    assert not path.exists()


def test_directory_is_not_a_config_file(tmp_path: Path) -> None:
    # Windows may report a directory as PermissionError rather than IsADirectoryError.
    with pytest.raises(ProjectConfigError, match="configuration:"):
        load_projects(tmp_path)


def test_nul_in_path_has_safe_domain_error(tmp_path: Path) -> None:
    path = tmp_path / "fictional-private\x00.toml"
    with pytest.raises(
        ProjectConfigError, match="configuration: invalid file path"
    ) as caught:
        load_projects(path)
    assert "fictional-private" not in "".join(traceback.format_exception(caught.value))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("error_type", "message"),
    [
        (PermissionError, "permission denied"),
        (OSError, "could not read file"),
        (ValueError, "invalid file path"),
    ],
)
def test_file_access_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[OSError | ValueError],
    message: str,
) -> None:
    path = write_config(tmp_path, project_config())

    def fail_read(self: Path, *, encoding: str) -> str:
        assert self == path
        assert encoding == "utf-8"
        raise error_type("private-file-details")

    monkeypatch.setattr(Path, "read_text", fail_read)
    with pytest.raises(ProjectConfigError, match=message) as caught:
        load_projects(path)
    assert "private-file-details" not in "".join(
        traceback.format_exception(caught.value)
    )


def test_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "projects.toml"
    path.write_bytes(b"schema_version = 1\n# \xff")
    with pytest.raises(ProjectConfigError, match="expected UTF-8 text"):
        load_projects(path)


@pytest.mark.parametrize(
    "text",
    [
        'schema_version = 1\n[[projects]\nname = "fictional-private-value"',
        'schema_version = 1\n"fictional-private-key" = 1\n"fictional-private-key" = 2',
        '[1, 2, "fictional-private-value"]',
    ],
)
def test_malformed_toml_has_safe_location(tmp_path: Path, text: str) -> None:
    with pytest.raises(
        ProjectConfigError, match=r"TOML: invalid syntax at line \d+, column \d+"
    ) as caught:
        load_projects(write_config(tmp_path, text))
    assert "fictional-private" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(
    "version", ["0", "2", "-1", "true", "false", '"1"', "1.0", "[]", "{}"]
)
def test_invalid_schema_version(tmp_path: Path, version: str) -> None:
    with pytest.raises(ProjectConfigError, match="schema_version: expected integer 1"):
        load_projects(
            write_config(tmp_path, f"schema_version = {version}\nprojects = []")
        )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "schema_version: required field"),
        ("projects = []", "schema_version: required field"),
        ("schema_version = 1", "projects: required array"),
        ("schema_version = 1\nprojects = {}", "projects: expected an array"),
        ('schema_version = 1\nprojects = "garden"', "projects: expected an array"),
        ("schema_version = 1\nprojects = true", "projects: expected an array"),
        ("schema_version = 1\nprojects = 1", "projects: expected an array"),
        (
            'schema_version = 1\n[projects]\nid = "garden"',
            "projects: expected an array",
        ),
        (
            'schema_version = 1\nprojects = ["garden"]',
            "projects[1]: expected a project",
        ),
        ("schema_version = 1\nprojects = [1]", "projects[1]: expected a project"),
        ("schema_version = 1\nprojects = [true]", "projects[1]: expected a project"),
        ("schema_version = 1\nprojects = [[]]", "projects[1]: expected a project"),
    ],
)
def test_invalid_structure(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ProjectConfigError) as caught:
        load_projects(write_config(tmp_path, text))
    assert message in str(caught.value)


@pytest.mark.parametrize("field", ["id", "name", "ssh_alias"])
def test_missing_project_field(tmp_path: Path, field: str) -> None:
    text = "\n".join(
        line
        for line in project_config().splitlines()
        if not line.startswith(f"{field} =")
    )
    with pytest.raises(ProjectConfigError) as caught:
        load_projects(write_config(tmp_path, text))
    assert f"projects[1].{field}: required field is missing" == str(caught.value)


@pytest.mark.parametrize(
    "field", ["id", "name", "ssh_alias", "repository", "documentation"]
)
@pytest.mark.parametrize("value", ["1", "true", "[]", "{}", "2000-01-01", '""', '"  "'])
def test_invalid_project_field_types_and_empty_values(
    tmp_path: Path, field: str, value: str
) -> None:
    with pytest.raises(ProjectConfigError) as caught:
        load_projects(write_config(tmp_path, project_config(**{field: value})))
    assert str(caught.value) == f"projects[1].{field}: expected a nonempty string"


@pytest.mark.parametrize(
    "text",
    [
        'schema_version = 1\nprojects = []\nfictional_private_key = "private-value"',
        project_config(fictional_private_key='"private-value"'),
    ],
)
def test_unknown_fields_are_rejected_without_echoing_keys(
    tmp_path: Path, text: str
) -> None:
    with pytest.raises(
        ProjectConfigError, match="unknown field; allowed fields:"
    ) as caught:
        load_projects(write_config(tmp_path, text))
    message = str(caught.value)
    assert message.startswith(
        "projects[1]:" if "[[projects]]" in text else "configuration:"
    )
    assert "fictional_private_key" not in message
    assert "private-value" not in message


@pytest.mark.parametrize(
    "identifier", ["Garden", "a--b", "-garden", "garden-", "a_b", "é", "a b"]
)
def test_invalid_project_ids(tmp_path: Path, identifier: str) -> None:
    with pytest.raises(ProjectConfigError, match=r"projects\[1\].id:"):
        load_projects(write_config(tmp_path, project_config(id=json.dumps(identifier))))


def test_duplicate_id_identifies_both_entries_without_echoing_id(
    tmp_path: Path,
) -> None:
    text = project_config() + project_config().removeprefix("schema_version = 1")
    with pytest.raises(ProjectConfigError) as caught:
        load_projects(write_config(tmp_path, text))
    assert str(caught.value) == "projects[2].id: duplicate of projects[1].id"


@pytest.mark.parametrize("alias", ["Garden_2.example-host", "9", "a--b"])
def test_valid_aliases_are_preserved(tmp_path: Path, alias: str) -> None:
    path = write_config(
        tmp_path, project_config(id='"9-demo"', ssh_alias=json.dumps(alias))
    )
    assert load_projects(path)[0].ssh_alias == alias


@pytest.mark.parametrize(
    "alias",
    [
        "-oProxyCommand=echo",
        "--help",
        " user",
        "user ",
        "two hosts",
        "user@host",
        "host;echo",
        "host&&echo",
        "$(echo)",
        "`echo`",
        "host|echo",
        "host>file",
        "host/command",
        "host\\command",
        "host:22",
        "host\ncommand",
        "host\tcommand",
        "host\x00",
        "höst",
        ".host",
        "_host",
    ],
)
def test_hostile_aliases(tmp_path: Path, alias: str) -> None:
    with pytest.raises(ProjectConfigError, match=r"projects\[1\].ssh_alias:"):
        load_projects(
            write_config(tmp_path, project_config(ssh_alias=json.dumps(alias)))
        )


@pytest.mark.parametrize("field", ["repository", "documentation"])
@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/fictional/repo.git",
        "HTTP://Example.org:8080/docs?q=a#start",
        "https://example.invalid/not-present-on-this-computer",
        "https://[2001:db8::1]/docs",
        "https://example.com/a%20b",
    ],
)
def test_valid_urls_are_preserved(tmp_path: Path, field: str, url: str) -> None:
    path = write_config(tmp_path, project_config(**{field: json.dumps(url)}))
    assert getattr(load_projects(path)[0], field) == url


@pytest.mark.parametrize("field", ["repository", "documentation"])
@pytest.mark.parametrize(
    "url",
    [
        "file:///fictional/repo",
        "ssh://example.com/repo",
        "ftp://example.com/docs",
        "javascript:alert(1)",
        "//example.com/docs",
        "/srv/fictional/repo",
        "host:/srv/fictional/repo",
        "https:example.com",
        "https:///docs",
        "https://",
        "https://user:password@example.com/docs",
        "https://user@example.com/docs",
        "https://@example.com",
        "https://:password@example.com",
        " https://example.com",
        "https://example.com ",
        "https://example.com/a b",
        "https://exam\tple.com",
        "https://example.com/\npath",
        "\x00https://example.com",
        "https://example.com/\x7f",
        "https://example.com/\u0081",
        "https://example.com/\u009f",
        "https://example.com\\@other.example",
        "https://example.com:bad",
        "https://example.com:65536",
        "https://[broken",
    ],
)
def test_invalid_urls(tmp_path: Path, field: str, url: str) -> None:
    with pytest.raises(ProjectConfigError) as caught:
        load_projects(
            write_config(tmp_path, project_config(**{field: json.dumps(url)}))
        )
    assert str(caught.value).startswith(f"projects[1].{field}:")
    assert url not in "".join(traceback.format_exception(caught.value))
