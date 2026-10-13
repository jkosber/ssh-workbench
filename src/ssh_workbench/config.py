"""Read and validate project metadata without using its aliases or links."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class ProjectConfigError(ValueError):
    """A configuration cannot be read, parsed or validated."""


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    ssh_alias: str
    repository: str | None = None
    documentation: str | None = None


def load_projects(path: Path) -> list[Project]:
    """Read only the supplied UTF-8 file; never create or modify configuration."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ProjectConfigError("configuration: file not found") from None
    except PermissionError:
        raise ProjectConfigError("configuration: permission denied") from None
    except IsADirectoryError:
        raise ProjectConfigError(
            "configuration: expected a file, got a directory"
        ) from None
    except OSError:
        raise ProjectConfigError("configuration: could not read file") from None
    except UnicodeDecodeError:
        raise ProjectConfigError("configuration: expected UTF-8 text") from None
    except ValueError:
        raise ProjectConfigError("configuration: invalid file path") from None
    return parse_projects(text)


def parse_projects(text: str) -> list[Project]:
    """Parse TOML and validate its schema, preserving project order and values."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        # Parser messages can contain keys or values from the private document.
        raise ProjectConfigError(
            f"TOML: invalid syntax at line {error.lineno}, column {error.colno}"
        ) from None
    return _validate_projects(data)


def is_valid_ssh_alias(value: object) -> bool:
    """Share the schema's alias rule with the native process boundary."""
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None
    )


def _validate_projects(data: dict[str, object]) -> list[Project]:
    _check_fields(data, {"schema_version", "projects"}, "configuration")
    if "schema_version" not in data:
        raise ProjectConfigError("schema_version: required field is missing")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ProjectConfigError("schema_version: expected integer 1")
    if "projects" not in data:
        raise ProjectConfigError("projects: required array is missing")
    entries = data["projects"]
    if not isinstance(entries, list):
        raise ProjectConfigError("projects: expected an array of project tables")

    projects = []
    identifiers: dict[str, int] = {}
    for index, entry in enumerate(entries, start=1):
        location = f"projects[{index}]"
        if not isinstance(entry, dict):
            raise ProjectConfigError(f"{location}: expected a project table")
        _check_fields(
            entry, {"id", "name", "ssh_alias", "repository", "documentation"}, location
        )
        identifier = _string(entry, "id", location)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
            raise ProjectConfigError(
                f"{location}.id: use lowercase ASCII letters/digits with single hyphens"
            )
        if identifier in identifiers:
            raise ProjectConfigError(
                f"{location}.id: duplicate of projects[{identifiers[identifier]}].id"
            )
        identifiers[identifier] = index

        name = _string(entry, "name", location)
        alias = _string(entry, "ssh_alias", location)
        if not is_valid_ssh_alias(alias):
            raise ProjectConfigError(
                f"{location}.ssh_alias: start with an ASCII letter/digit; "
                "use only ASCII letters/digits, dots, underscores or hyphens"
            )
        projects.append(
            Project(
                id=identifier,
                name=name,
                ssh_alias=alias,
                repository=_optional_url(entry, "repository", location),
                documentation=_optional_url(entry, "documentation", location),
            )
        )
    return projects


def _check_fields(data: dict[str, object], allowed: set[str], location: str) -> None:
    if data.keys() - allowed:
        # Unknown keys can also contain private text; show the allowed names only.
        raise ProjectConfigError(
            f"{location}: unknown field; allowed fields: {', '.join(sorted(allowed))}"
        )


def _string(data: dict[str, object], field: str, location: str) -> str:
    if field not in data:
        raise ProjectConfigError(f"{location}.{field}: required field is missing")
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ProjectConfigError(f"{location}.{field}: expected a nonempty string")
    return value


def _optional_url(data: dict[str, object], field: str, location: str) -> str | None:
    if field not in data:
        return None
    value = _string(data, field, location)
    message = (
        f"{location}.{field}: expected an absolute HTTP/HTTPS URL with a host "
        "and no credentials, whitespace, control characters or backslashes"
    )
    # urlsplit strips some whitespace/controls; browsers can normalize backslashes.
    if any(
        c.isspace() or ord(c) < 32 or 127 <= ord(c) <= 159 or c == "\\" for c in value
    ):
        raise ProjectConfigError(message)
    try:
        url = urlsplit(value)
        _ = url.port  # Accessing this property checks port syntax and range.
    except ValueError:
        raise ProjectConfigError(
            f"{location}.{field}: invalid URL host or port"
        ) from None
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
    ):
        raise ProjectConfigError(message)
    return value
