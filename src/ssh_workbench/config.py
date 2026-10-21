"""Read and validate machine files without using their aliases, addresses or links."""

import ipaddress
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit


class ConfigError(ValueError):
    """A configuration cannot be read, parsed or validated."""


@dataclass(frozen=True)
class Link:
    name: str
    url: str


@dataclass(frozen=True)
class Machine:
    """Either an SSH alias, or addresses with an optional user, port and key."""

    id: str
    name: str
    alias: str | None = None
    user: str | None = None
    addresses: tuple[str, ...] = ()
    port: int | None = None
    key: str | None = None
    links: tuple[Link, ...] = ()


_MACHINE_FIELDS = {"id", "name", "alias", "user", "addresses", "port", "key", "links"}
_HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?"
_ALIAS_RULE = (
    "start with an ASCII letter/digit; "
    "use only ASCII letters/digits, dots, underscores or hyphens"
)


def _read_config(path: Path) -> str:
    # Windows reports reading a folder as permission denied; name the real cause.
    if path.is_dir():
        raise ConfigError("configuration: expected a file, got a directory")
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError("configuration: file not found") from None
    except PermissionError:
        raise ConfigError("configuration: permission denied") from None
    except IsADirectoryError:
        raise ConfigError("configuration: expected a file, got a directory") from None
    except OSError:
        raise ConfigError("configuration: could not read file") from None
    except UnicodeDecodeError:
        raise ConfigError("configuration: expected UTF-8 text") from None
    except ValueError:
        raise ConfigError("configuration: invalid file path") from None
    # Some Windows editors and PowerShell 5.1 prefix UTF-8 with a byte-order mark.
    return text.removeprefix("﻿")


def _parse_toml(text: str) -> dict[str, object]:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        # Parser messages can contain keys or values from the private document.
        raise ConfigError(
            f"TOML: invalid syntax at line {error.lineno}, column {error.colno}"
        ) from None


def load_machines(path: Path) -> list[Machine]:
    """Read only the supplied UTF-8 file; never create or modify it."""
    return parse_machines(_read_config(path))


def parse_machines(text: str) -> list[Machine]:
    """Parse a schema 1 or 2 file, preserving machine order and values."""
    data = _parse_toml(text)
    if "schema_version" not in data:
        raise ConfigError("schema_version: required field is missing")
    version = data["schema_version"]
    if type(version) is not int or version not in (1, 2):
        raise ConfigError("schema_version: expected integer 1 or 2")
    if version == 1:
        return _projects_as_machines(data)
    return _validate_machines(data)


def is_valid_ssh_alias(value: object) -> bool:
    """Share the schema's alias rule with the native process boundary."""
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None
    )


def is_valid_machine_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None
    )


def is_valid_user(value: object) -> bool:
    """One SSH login name: never an option, an `@` destination or two arguments."""
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]*", value) is not None
    )


def is_valid_address(value: object) -> bool:
    """An IP address without a zone, or a hostname of letter/digit labels."""
    if not isinstance(value, str) or "%" in value:
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        return True
    return (
        len(value) <= 253
        and re.fullmatch(rf"{_HOST_LABEL}(?:\.{_HOST_LABEL})*", value) is not None
        # Digits and dots that are not a valid IPv4 address are a typo, not a host.
        and re.fullmatch(r"[0-9.]+", value) is None
    )


def is_valid_port(value: object) -> bool:
    return type(value) is int and 1 <= value <= 65535


def is_valid_key_path(value: object) -> bool:
    """A private key path SSH reads literally.

    OpenSSH checks the raw -i path before expanding `%` and `${}` codes, so
    neither can be passed safely. Either platform's absolute form is accepted
    because one machine file may be shared between Windows and Linux.
    """
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not value.isprintable()
        or any(text in value for text in ('"', "%", "${"))
        or value.lower().endswith(".pub")
    ):
        return False
    if value.startswith(("~/", "~\\")):
        # The rest stays inside the home folder: no second root and no drive.
        rest = value[2:]
        return bool(rest) and rest[0] not in "/\\" and not PureWindowsPath(rest).drive
    return PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()


def _projects_as_machines(data: dict[str, object]) -> list[Machine]:
    """Schema 1 projects become alias machines with named links."""
    _check_fields(data, {"schema_version", "projects"}, "configuration")
    if "projects" not in data:
        raise ConfigError("projects: required array is missing")
    entries = data["projects"]
    if not isinstance(entries, list):
        raise ConfigError("projects: expected an array of project tables")

    machines = []
    identifiers: dict[str, int] = {}
    for index, entry in enumerate(entries, start=1):
        location = f"projects[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{location}: expected a project table")
        _check_fields(
            entry, {"id", "name", "ssh_alias", "repository", "documentation"}, location
        )
        identifier = _identifier(entry, "projects", index, identifiers)
        name = _string(entry, "name", location)
        alias = _string(entry, "ssh_alias", location)
        if not is_valid_ssh_alias(alias):
            raise ConfigError(f"{location}.ssh_alias: {_ALIAS_RULE}")
        links = []
        for field in ("repository", "documentation"):
            url = _optional_url(entry, field, location)
            if url is not None:
                links.append(Link(field.title(), url))
        machines.append(Machine(identifier, name, alias=alias, links=tuple(links)))
    return machines


def _validate_machines(data: dict[str, object]) -> list[Machine]:
    _check_fields(data, {"schema_version", "machines"}, "configuration")
    if "machines" not in data:
        raise ConfigError("machines: required array is missing")
    entries = data["machines"]
    if not isinstance(entries, list):
        raise ConfigError("machines: expected an array of machine tables")

    machines = []
    identifiers: dict[str, int] = {}
    for index, entry in enumerate(entries, start=1):
        location = f"machines[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{location}: expected a machine table")
        _check_fields(entry, _MACHINE_FIELDS, location)
        identifier = _identifier(entry, "machines", index, identifiers)
        name = _string(entry, "name", location)
        if "alias" in entry and "addresses" in entry:
            raise ConfigError(f"{location}: use either alias or addresses, not both")
        if "alias" in entry:
            for field in ("user", "port", "key"):
                if field in entry:
                    raise ConfigError(
                        f"{location}.{field}: only machines with addresses take "
                        "this field"
                    )
            alias = _string(entry, "alias", location)
            if not is_valid_ssh_alias(alias):
                raise ConfigError(f"{location}.alias: {_ALIAS_RULE}")
            connection: dict[str, object] = {"alias": alias}
        elif "addresses" in entry:
            connection = {
                "user": _optional_user(entry, location),
                "addresses": _addresses(entry, location),
                "port": _optional_port(entry, location),
                "key": _optional_key(entry, location),
            }
        else:
            raise ConfigError(f"{location}: add alias or addresses")
        machines.append(
            Machine(identifier, name, **connection, links=_links(entry, location))
        )
    return machines


def _identifier(
    entry: dict[str, object], collection: str, index: int, seen: dict[str, int]
) -> str:
    location = f"{collection}[{index}]"
    identifier = _string(entry, "id", location)
    if not is_valid_machine_id(identifier):
        raise ConfigError(
            f"{location}.id: use lowercase ASCII letters/digits with single hyphens"
        )
    if identifier in seen:
        raise ConfigError(
            f"{location}.id: duplicate of {collection}[{seen[identifier]}].id"
        )
    seen[identifier] = index
    return identifier


def _optional_user(entry: dict[str, object], location: str) -> str | None:
    if "user" not in entry:
        return None
    user = _string(entry, "user", location)
    if not is_valid_user(user):
        raise ConfigError(
            f"{location}.user: start with an ASCII letter, digit or underscore; "
            "use only ASCII letters, digits, dots, underscores or hyphens"
        )
    return user


def _addresses(entry: dict[str, object], location: str) -> tuple[str, ...]:
    values = entry["addresses"]
    if not isinstance(values, list) or not values:
        raise ConfigError(f"{location}.addresses: expected a nonempty array of strings")
    seen: dict[str, int] = {}
    for position, address in enumerate(values, start=1):
        where = f"{location}.addresses[{position}]"
        if not is_valid_address(address):
            raise ConfigError(
                f"{where}: expected a hostname or IP address "
                "without spaces, @, ports or a leading dash"
            )
        if address in seen:
            raise ConfigError(
                f"{where}: duplicate of {location}.addresses[{seen[address]}]"
            )
        seen[address] = position
    return tuple(values)


def _optional_port(entry: dict[str, object], location: str) -> int | None:
    if "port" not in entry:
        return None
    if not is_valid_port(entry["port"]):
        raise ConfigError(f"{location}.port: expected an integer from 1 to 65535")
    return entry["port"]


def _optional_key(entry: dict[str, object], location: str) -> str | None:
    if "key" not in entry:
        return None
    key = _string(entry, "key", location)
    if key.lower().endswith(".pub"):
        raise ConfigError(
            f"{location}.key: name the private key file, not its .pub file"
        )
    if not is_valid_key_path(key):
        raise ConfigError(
            f"{location}.key: expected an absolute path or one starting with ~/, "
            "without quotes, %, ${ or control characters"
        )
    return key


def _links(entry: dict[str, object], location: str) -> tuple[Link, ...]:
    if "links" not in entry:
        return ()
    values = entry["links"]
    if not isinstance(values, list):
        raise ConfigError(f"{location}.links: expected an array of link tables")
    links = []
    names: dict[str, int] = {}
    for position, value in enumerate(values, start=1):
        where = f"{location}.links[{position}]"
        if not isinstance(value, dict):
            raise ConfigError(f"{where}: expected a link table")
        _check_fields(value, {"name", "url"}, where)
        name = _string(value, "name", where)
        if name in names:
            raise ConfigError(
                f"{where}.name: duplicate of {location}.links[{names[name]}].name"
            )
        names[name] = position
        url = validate_http_url(_string(value, "url", where), f"{where}.url")
        links.append(Link(name, url))
    return tuple(links)


def _check_fields(data: dict[str, object], allowed: set[str], location: str) -> None:
    if data.keys() - allowed:
        # Unknown keys can also contain private text; show the allowed names only.
        raise ConfigError(
            f"{location}: unknown field; allowed fields: {', '.join(sorted(allowed))}"
        )


def _string(data: dict[str, object], field: str, location: str) -> str:
    if field not in data:
        raise ConfigError(f"{location}.{field}: required field is missing")
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{location}.{field}: expected a nonempty string")
    return value


def _optional_url(data: dict[str, object], field: str, location: str) -> str | None:
    if field not in data:
        return None
    return validate_http_url(_string(data, field, location), f"{location}.{field}")


def validate_http_url(value: object, location: str = "URL") -> str:
    """Apply the same URL contract when loading and immediately before opening."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{location}: expected a nonempty string")
    message = (
        f"{location}: expected an absolute HTTP/HTTPS URL with a host "
        "and no credentials, whitespace, control characters or backslashes"
    )
    # urlsplit strips some whitespace/controls; browsers can normalize backslashes.
    if any(
        c.isspace() or ord(c) < 32 or 127 <= ord(c) <= 159 or c == "\\" for c in value
    ):
        raise ConfigError(message)
    try:
        url = urlsplit(value)
        _ = url.port  # Accessing this property checks port syntax and range.
    except ValueError:
        raise ConfigError(f"{location}: invalid URL host or port") from None
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
    ):
        raise ConfigError(message)
    return value
