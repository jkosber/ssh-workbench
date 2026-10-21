"""Remember SSH aliases between runs and spot renamed ones.

The state file sits next to the machine file and holds only what Workbench saw:
the literal `Host` names at the last refresh and, for each alias that was one of
them, the host, user and port `ssh -G` resolved. It is a cache: any problem
reading it means no state, which only loses rename suggestions until the next
refresh. Nothing here changes a machine; the app asks first.
"""

import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ssh_workbench.config import is_valid_ssh_alias
from ssh_workbench.status import AliasTarget
from ssh_workbench.store import replace_atomically

STATE_VERSION = 1
_MAX_BYTES = 1_000_000
_KEYS = {"aliases", "computer", "host_names", "renames", "version"}
_RECORD_KEYS = {"host", "port", "user"}


@dataclass(frozen=True)
class AliasRecord:
    """Where an alias pointed while it was a literal `Host` name."""

    host: str
    user: str
    port: int


@dataclass
class AliasMemory:
    host_names: tuple[str, ...] = ()
    # Kept while an alias is missing, so Alias not found survives restarts.
    records: dict[str, AliasRecord] = field(default_factory=dict)
    # A vanished alias and the one new name it probably became.
    renames: dict[str, str] = field(default_factory=dict)

    def remember(self, alias: str, target: AliasTarget) -> None:
        """Record what `ssh -G` said for an alias that is a literal `Host` name."""
        if alias in self.host_names:
            self.records[alias] = AliasRecord(target.host, target.user, target.port)


@dataclass(frozen=True)
class Review:
    memory: AliasMemory
    # Each missing alias and its suggested new name, if exactly one matched.
    missing: dict[str, str | None]
    # The names resolved while looking for a match.
    resolved: dict[str, AliasTarget | None]


def state_path(machine_file: Path) -> Path:
    return machine_file.with_name(f"{machine_file.stem}.state.json")


def format_state(memory: AliasMemory, computer: str) -> str:
    data = {
        "aliases": {
            alias: {"host": record.host, "port": record.port, "user": record.user}
            for alias, record in memory.records.items()
        },
        "computer": computer,
        "host_names": list(memory.host_names),
        "renames": memory.renames,
        "version": STATE_VERSION,
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def parse_state(text: str, computer: str) -> AliasMemory | None:
    """The remembered state, or None for anything Workbench did not write here.

    A machine file in a synced folder is shared by computers with different SSH
    configs, so a state written on another computer counts as no state.
    """
    try:
        data = json.loads(text)
    except ValueError, RecursionError:
        return None
    if not isinstance(data, dict) or set(data) != _KEYS:
        return None
    version, names = data["version"], data["host_names"]
    records, renames = data["aliases"], data["renames"]
    if (
        type(version) is not int
        or version != STATE_VERSION
        or data["computer"] != computer
        or not isinstance(names, list)
        or not all(is_valid_ssh_alias(name) for name in names)
        or not isinstance(records, dict)
        or not isinstance(renames, dict)
        or not all(
            is_valid_ssh_alias(old) and is_valid_ssh_alias(new)
            for old, new in renames.items()
        )
    ):
        return None
    parsed: dict[str, AliasRecord] = {}
    for alias, record in records.items():
        if (
            not is_valid_ssh_alias(alias)
            or not isinstance(record, dict)
            or set(record) != _RECORD_KEYS
        ):
            return None
        host, user, port = record["host"], record["user"], record["port"]
        if not (
            isinstance(host, str)
            and host
            and isinstance(user, str)
            and type(port) is int
            and 1 <= port <= 65535
        ):
            return None
        parsed[alias] = AliasRecord(host, user, port)
    return AliasMemory(tuple(names), parsed, dict(renames))


def load_state(path: Path, computer: str) -> AliasMemory | None:
    try:
        with path.open("rb") as handle:
            data = handle.read(_MAX_BYTES + 1)
        text = data.decode("utf-8")
    except OSError, ValueError:
        return None
    if len(data) > _MAX_BYTES:
        return None
    return parse_state(text, computer)


def save_state(path: Path, text: str) -> None:
    """Replace the state file atomically; `OSError` reaches the caller."""
    replace_atomically(path, text.encode("utf-8"), mode_from=None)


def review(
    memory: AliasMemory | None,
    aliases: Iterable[str],
    names: Sequence[str],
    resolve: Callable[[str], AliasTarget | None],
) -> Review:
    """Compare the machines' aliases with the `Host` names read now.

    An alias recorded while it was a literal `Host` name and missing now is
    missing. Its suggestion is a kept one that still resolves to the record, or
    else the single name that appeared since the last review and resolves to
    the record, and only if no other missing alias gets the same name.
    `resolve` runs only for those names.
    """
    used = dict.fromkeys(aliases)
    listed = set(names)
    previous = set(memory.host_names) if memory is not None else None
    records = {
        alias: record
        for alias, record in (memory.records if memory else {}).items()
        if alias in used
    }
    renames = {
        alias: name
        for alias, name in (memory.renames if memory else {}).items()
        if alias in used
    }
    appeared = [name for name in names if previous is not None and name not in previous]
    resolved: dict[str, AliasTarget | None] = {}

    def resolves_to(name: str, record: AliasRecord) -> bool:
        if name not in resolved:
            resolved[name] = resolve(name)
        target = resolved[name]
        return (
            target is not None
            and AliasRecord(target.host, target.user, target.port) == record
        )

    missing: dict[str, str | None] = {}
    for alias in used:
        if alias in listed:
            renames.pop(alias, None)
            continue
        record = records.get(alias)
        if record is None:
            continue
        kept = renames.get(alias)
        if kept is not None and kept in listed and resolves_to(kept, record):
            missing[alias] = kept
            continue
        found = [name for name in appeared if resolves_to(name, record)]
        missing[alias] = found[0] if len(found) == 1 else None
    # A name that fits two vanished aliases can't say which one it replaced.
    offered = Counter(name for name in missing.values() if name is not None)
    for alias, name in missing.items():
        if name is not None and offered[name] == 1:
            renames[alias] = name
        else:
            missing[alias] = None
            renames.pop(alias, None)
    return Review(AliasMemory(tuple(names), records, renames), missing, resolved)
