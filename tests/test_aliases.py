"""The alias state file and the rename review, with fictional names and files only."""

import json
from pathlib import Path

import pytest

from ssh_workbench.aliases import (
    AliasMemory,
    AliasRecord,
    format_state,
    load_state,
    parse_state,
    review,
    save_state,
    state_path,
)
from ssh_workbench.status import AliasTarget

COMPUTER = "workstation"
RECORD = AliasRecord("192.0.2.10", "dev", 22)
SAME = AliasTarget("192.0.2.10", 22, proxied=False, user="dev")
# The Host names at the last review, when old-host was still listed.
BEFORE = ("old-host", "hop-host")


class Resolver:
    """Stands in for `ssh -G`; records which names were resolved."""

    def __init__(self, targets: dict[str, AliasTarget | None]) -> None:
        self.targets = targets
        self.calls: list[str] = []

    def __call__(self, alias: str) -> AliasTarget | None:
        self.calls.append(alias)
        return self.targets.get(alias)


def memory(
    names: tuple[str, ...] = BEFORE,
    records: dict[str, AliasRecord] | None = None,
    baselines: dict[str, tuple[str, ...]] | None = None,
) -> AliasMemory:
    """What the last review saw: `old-host` was a literal Host name then."""
    return AliasMemory(
        names,
        {"old-host": RECORD} if records is None else records,
        baselines or {},
    )


def test_state_path_is_per_computer_next_to_the_machine_file(tmp_path: Path) -> None:
    assert (
        state_path(tmp_path / "machines.toml", COMPUTER)
        == tmp_path / "machines.state.workstation.json"
    )
    assert (
        state_path(tmp_path / "lab.toml", "Lab PC/2\\x")
        == tmp_path / "lab.state.Lab_PC_2_x.json"
    )
    assert state_path(tmp_path / "lab.toml", "") == tmp_path / "lab.state.computer.json"


def test_state_text_is_stable_json() -> None:
    state = AliasMemory(
        ("garden-host", "hop-host"),
        {"garden-host": RECORD},
        {"old-host": ("garden-host",)},
    )

    assert format_state(state, COMPUTER) == (
        "{\n"
        '  "aliases": {\n'
        '    "garden-host": {\n'
        '      "host": "192.0.2.10",\n'
        '      "port": 22,\n'
        '      "user": "dev"\n'
        "    }\n"
        "  },\n"
        '  "baselines": {\n'
        '    "old-host": [\n'
        '      "garden-host"\n'
        "    ]\n"
        "  },\n"
        '  "computer": "workstation",\n'
        '  "host_names": [\n'
        '    "garden-host",\n'
        '    "hop-host"\n'
        "  ],\n"
        '  "version": 1\n'
        "}\n"
    )


def test_state_round_trips_through_an_atomic_save(tmp_path: Path) -> None:
    state = memory(baselines={"old-host": BEFORE})
    path = tmp_path / "machines.state.workstation.json"

    save_state(path, format_state(state, COMPUTER))
    save_state(path, format_state(state, COMPUTER))

    assert load_state(path, COMPUTER) == state
    assert [item.name for item in tmp_path.iterdir()] == [path.name]


def test_state_from_another_computer_is_no_state() -> None:
    assert parse_state(format_state(memory(), "laptop"), COMPUTER) is None


VALID = json.loads(format_state(memory(baselines={"old-host": BEFORE}), COMPUTER))


def changed(path: tuple[str, ...], value: object) -> str:
    data = json.loads(json.dumps(VALID))
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return json.dumps(data)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        changed(("version",), 2),
        changed(("version",), True),
        changed(("computer",), 7),
        changed(("extra",), 1),
        changed(("host_names",), "old-host"),
        changed(("host_names",), ["old host"]),
        changed(("aliases",), []),
        changed(("aliases", "-oProxyCommand=x"), {"host": "h", "port": 22, "user": ""}),
        changed(("aliases", "old-host"), {"host": "192.0.2.10", "user": "dev"}),
        changed(("aliases", "old-host", "extra"), 1),
        changed(("aliases", "old-host", "host"), ""),
        changed(("aliases", "old-host", "user"), 5),
        changed(("aliases", "old-host", "port"), True),
        changed(("aliases", "old-host", "port"), 0),
        changed(("aliases", "old-host", "port"), 65536),
        changed(("baselines",), ["old-host"]),
        changed(("baselines", "old-host"), "hop-host"),
        changed(("baselines", "old-host"), ["hop host"]),
        changed(("baselines", "-oProxyCommand=x"), []),
    ],
)
def test_invalid_state_is_no_state(text: str) -> None:
    assert parse_state(text, COMPUTER) is None


def test_missing_unreadable_or_oversized_state_is_no_state(tmp_path: Path) -> None:
    path = tmp_path / "machines.state.workstation.json"
    assert load_state(path, COMPUTER) is None
    assert load_state(tmp_path, COMPUTER) is None
    path.write_bytes(b"\xff\xfe")
    assert load_state(path, COMPUTER) is None
    path.write_text(" " * 1_000_001 + format_state(memory(), COMPUTER), "utf-8")
    assert load_state(path, COMPUTER) is None


def test_without_memory_nothing_is_missing() -> None:
    resolve = Resolver({"new-host": SAME})

    result = review(
        None, ["old-host", "garden-host"], ["new-host", "garden-host"], resolve
    )

    assert result.missing == {}
    assert result.memory == AliasMemory(("new-host", "garden-host"), {}, {})
    assert resolve.calls == []


def test_a_vanished_alias_gets_the_one_new_name_that_matches() -> None:
    elsewhere = AliasTarget("192.0.2.99", 22, proxied=False, user="dev")
    resolve = Resolver({"new-host": SAME, "other-host": elsewhere})

    result = review(
        memory(),
        ["old-host", "old-host"],
        ["hop-host", "other-host", "new-host"],
        resolve,
    )

    assert result.missing == {"old-host": "new-host"}
    assert result.memory == AliasMemory(
        ("hop-host", "other-host", "new-host"),
        {"old-host": RECORD},
        {"old-host": BEFORE},
    )
    assert result.resolved == {"other-host": elsewhere, "new-host": SAME}
    assert sorted(resolve.calls) == ["new-host", "other-host"]


@pytest.mark.parametrize(
    "targets",
    [
        {"new-host": SAME, "twin-host": SAME},
        {"new-host": AliasTarget("192.0.2.10", 22, proxied=False, user="root")},
        {"new-host": AliasTarget("192.0.2.10", 2222, proxied=False, user="dev")},
        {"new-host": None},
    ],
)
def test_no_single_match_means_no_suggestion(
    targets: dict[str, AliasTarget | None],
) -> None:
    result = review(memory(), ["old-host"], ["hop-host", *targets], Resolver(targets))

    assert result.missing == {"old-host": None}
    assert result.memory.baselines == {"old-host": BEFORE}


def test_a_name_that_did_not_resolve_at_first_is_offered_once_it_matches() -> None:
    names = ["hop-host", "new-host"]
    first = review(memory(), ["old-host"], names, Resolver({"new-host": None}))

    second = review(first.memory, ["old-host"], names, Resolver({"new-host": SAME}))

    assert first.missing == {"old-host": None}
    assert second.missing == {"old-host": "new-host"}


def test_an_ambiguous_match_is_offered_once_only_one_name_is_left() -> None:
    first = review(
        memory(),
        ["old-host"],
        ["hop-host", "new-host", "twin-host"],
        Resolver({"new-host": SAME, "twin-host": SAME}),
    )

    second = review(
        first.memory,
        ["old-host"],
        ["hop-host", "new-host"],
        Resolver({"new-host": SAME}),
    )

    assert first.missing == {"old-host": None}
    assert second.missing == {"old-host": "new-host"}


def test_a_new_name_matching_two_vanished_aliases_is_offered_to_neither() -> None:
    state = memory(records={"old-host": RECORD, "old-shed": RECORD})

    result = review(
        state, ["old-host", "old-shed"], ["new-host"], Resolver({"new-host": SAME})
    )

    assert result.missing == {"old-host": None, "old-shed": None}
    assert result.memory.baselines == {"old-host": BEFORE, "old-shed": BEFORE}


def test_a_name_that_already_existed_is_never_suggested() -> None:
    resolve = Resolver({"hop-host": SAME})

    result = review(memory(), ["old-host"], ["hop-host"], resolve)

    assert result.missing == {"old-host": None}
    assert resolve.calls == []


def test_an_alias_never_listed_is_not_missing() -> None:
    resolve = Resolver({"new-host": SAME})

    result = review(memory(records={}), ["old-host"], ["new-host"], resolve)

    assert result.missing == {}
    assert resolve.calls == []


def test_names_are_resolved_only_while_an_alias_is_missing() -> None:
    resolve = Resolver({"new-host": SAME})

    result = review(
        memory(), ["old-host"], ["old-host", "hop-host", "new-host"], resolve
    )

    assert result.missing == {}
    assert resolve.calls == []


def test_an_offer_survives_the_next_review_while_it_still_matches() -> None:
    names = ["hop-host", "new-host"]
    first = review(memory(), ["old-host"], names, Resolver({"new-host": SAME}))
    resolve = Resolver({"new-host": SAME})

    second = review(first.memory, ["old-host"], names, resolve)

    assert second.missing == {"old-host": "new-host"}
    assert second.memory.baselines == {"old-host": BEFORE}
    assert resolve.calls == ["new-host"]


@pytest.mark.parametrize(
    ("names", "targets"),
    [
        (["hop-host"], {}),
        (
            ["hop-host", "new-host"],
            {"new-host": AliasTarget("192.0.2.77", 22, proxied=False, user="dev")},
        ),
    ],
)
def test_an_offer_is_dropped_once_it_no_longer_matches(
    names: list[str], targets: dict[str, AliasTarget | None]
) -> None:
    first = review(
        memory(), ["old-host"], ["hop-host", "new-host"], Resolver({"new-host": SAME})
    )

    second = review(first.memory, ["old-host"], names, Resolver(targets))

    assert second.missing == {"old-host": None}


def test_alias_not_found_survives_later_reviews() -> None:
    first = review(memory(), ["old-host"], ["hop-host"], Resolver({}))

    second = review(first.memory, ["old-host"], ["hop-host"], Resolver({}))

    assert second.missing == {"old-host": None}
    assert second.memory.records == {"old-host": RECORD}
    assert second.memory.baselines == {"old-host": BEFORE}


def test_a_returning_alias_clears_missing_and_its_baseline() -> None:
    first = review(
        memory(), ["old-host"], ["hop-host", "new-host"], Resolver({"new-host": SAME})
    )
    resolve = Resolver({})

    second = review(
        first.memory, ["old-host"], ["hop-host", "new-host", "old-host"], resolve
    )

    assert second.missing == {}
    assert second.memory.baselines == {}
    assert second.memory.records == {"old-host": RECORD}
    assert resolve.calls == []


def test_listing_is_case_sensitive() -> None:
    result = review(
        memory(), ["old-host"], ["hop-host", "OLD-HOST"], Resolver({"OLD-HOST": SAME})
    )

    assert result.missing == {"old-host": "OLD-HOST"}


def test_records_and_baselines_for_unused_aliases_are_dropped() -> None:
    state = memory(
        records={"old-host": RECORD, "gone-host": RECORD},
        baselines={"gone-host": BEFORE},
    )

    result = review(state, ["old-host"], ["old-host", "hop-host"], Resolver({}))

    assert result.memory == AliasMemory(
        ("old-host", "hop-host"), {"old-host": RECORD}, {}
    )


def test_remember_records_only_listed_aliases() -> None:
    state = AliasMemory(("garden-host",), {}, {})

    state.remember("garden-host", SAME)
    state.remember("pattern-host", SAME)

    assert state.records == {"garden-host": RECORD}


def test_forget_drops_an_alias_record_and_baseline() -> None:
    state = memory(baselines={"old-host": BEFORE})

    state.forget("old-host")

    assert state == AliasMemory(BEFORE, {}, {})
