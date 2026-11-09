"""K for an alias: the note on a key the alias's SSH config may already name.

The picker's "doesn't name this key" note, and the hint a passing login test
adds, are for keys the config is known not to name. The key Create would make
can be named before it exists, and when `ssh -G` fails Workbench doesn't know
which keys the config names at all. Everything is fictional and substituted:
no real ssh, ssh-keygen, key, SSH folder or machine file.
"""

import asyncio
import base64
import struct
from pathlib import Path

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import OptionList, Static

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.app import ResultSlot, SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import PublicKey
from ssh_workbench.status import AliasTarget

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

SSH = "/fictional/ssh"
KEYGEN = "/fictional/ssh-keygen"
GARDEN = Machine("garden", "Garden", alias="garden-host")
LABELS = ["id_a.pub", "id_b.pub", "Create a new key: id_ed25519_garden"]
UNREAD = (
    "Your SSH config couldn't be read for garden-host, so Workbench can't tell "
    "whether it names this key."
)


def blob(seed: int) -> str:
    data = (
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes([seed]) * 32
    )
    return base64.b64encode(data).decode()


def public_key(seed: int, comment: str) -> PublicKey:
    return PublicKey("ssh-ed25519", blob(seed), comment)


class Native:
    """Records each handed-off command; ssh-keygen writes a fictional key pair."""

    def __init__(self, statuses: dict[str, int] | None = None) -> None:
        self.statuses = statuses or {}
        self.calls: list[list[str]] = []

    @staticmethod
    def step(arguments: list[str]) -> str:
        if arguments[0] == KEYGEN:
            return "keygen"
        return "test" if arguments[-1] == "exit" else "install"

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        step = self.step(arguments)
        if step == "keygen":
            private = Path(arguments[arguments.index("-f") + 1])
            private.write_text("fictional private half\n", encoding="ascii")
            Path(f"{private}.pub").write_text(
                public_key(9, "ssh-workbench-garden").line + "\n", encoding="ascii"
            )
        return self.statuses.get(step, 0)


class FakeChecker:
    def __init__(self, target: AliasTarget | None) -> None:
        self.target = target
        self.resolved: list[str] = []

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        return self.target

    def port_open(self, host: str, port: int) -> bool:
        return False


def workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native: Native
) -> tuple[Path, Path, str]:
    """An SSH folder with id_a and id_b, the machine file and the substituted
    native boundary; returns the folder, the file and its text."""
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text("", encoding="ascii")
    (folder / "id_a.pub").write_text(public_key(1, "a").line + "\n", "ascii")
    (folder / "id_b.pub").write_text(public_key(2, "b").line + "\n", "ascii")
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines((GARDEN,))
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    return folder, path, text


def naming(*identity_files: str) -> AliasTarget:
    return AliasTarget(
        "192.0.2.10", 22, proxied=False, user="dev", identity_files=identity_files
    )


def option_labels(screen: KeySetup) -> list[str]:
    options = screen.query_one(OptionList)
    return [
        str(options.get_option_at_index(index).prompt)
        for index in range(options.option_count)
    ]


def note(screen: KeySetup) -> str:
    return str(screen.query_one("#key-note", Static).content)


def connection_status(app: SSHWorkbenchApp) -> str:
    return app.query_one("#connection-status", ResultSlot).message


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def picker(app: SSHWorkbenchApp, pilot, checker: FakeChecker) -> KeySetup:
    """K once startup's ssh -G has answered."""
    await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
    await pilot.press("k")
    await wait_for(
        pilot, lambda: isinstance(app.screen, KeySetup) and app.screen.is_mounted
    )
    return app.screen


async def finished(app: SSHWorkbenchApp, pilot) -> None:
    await wait_for(pilot, lambda: "Machine 1:" in connection_status(app))


@pytest.mark.parametrize(
    "named",
    ["~/ssh/id_ed25519_garden", "{folder}/id_ed25519_garden"],
    ids=["home-form", "absolute"],
)
async def test_a_create_choice_the_config_already_names_gets_no_note_or_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, named: str
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, native)
    checker = FakeChecker(naming(named.format(folder=folder)))
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot, checker)
        assert option_labels(screen) == LABELS
        create = screen.choices[2]
        assert (create.create, create.note, create.hint, create.failed_hint) == (
            True,
            None,
            None,
            None,
        )
        await pilot.press("down", "down")
        await wait_for(pilot, lambda: screen.query_one(OptionList).highlighted == 2)
        assert note(screen) == ""
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == "Key login works. Machine 1: garden"
    assert [Native.step(call) for call in native.calls] == [
        "keygen",
        "install",
        "test",
    ]
    assert native.calls[0][4] == str(folder / "id_ed25519_garden")
    assert path.read_text(encoding="utf-8") == text


async def test_a_create_choice_whose_pub_the_config_names_explains_the_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # As for a named .pub that exists: SSH uses it only through an agent.
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, native)
    checker = FakeChecker(naming("~/ssh/id_ed25519_garden.pub"))
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    agent = (
        "Your SSH config names id_ed25519_garden.pub for garden-host, which SSH "
        "uses only through an agent that holds the key; without one, add this "
        f"line under Host garden-host: IdentityFile {folder / 'id_ed25519_garden'}"
    )
    async with app.run_test() as pilot:
        screen = await picker(app, pilot, checker)
        assert option_labels(screen) == LABELS
        create = screen.choices[2]
        assert (create.note, create.hint, create.failed_hint) == (None, None, agent)
        await pilot.press("down", "down")
        await wait_for(pilot, lambda: screen.query_one(OptionList).highlighted == 2)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            f"status 255). {agent} Machine 1: garden"
        )
    assert [Native.step(call) for call in native.calls] == [
        "keygen",
        "install",
        "test",
    ]


async def test_an_alias_whose_config_could_not_be_read_says_so_on_every_choice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, Native())
    checker = FakeChecker(None)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot, checker)
        assert option_labels(screen) == LABELS
        assert [
            (choice.note, choice.hint, choice.failed_hint) for choice in screen.choices
        ] == [(UNREAD, UNREAD, None)] * 3
        assert note(screen) == UNREAD


async def test_a_new_key_passing_the_test_when_the_config_could_not_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, native)
    checker = FakeChecker(None)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await picker(app, pilot, checker)
        await pilot.press("down", "down", "enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Key-only login works, but SSH may have used another key. "
            f"{UNREAD} Machine 1: garden"
        )
    assert [Native.step(call) for call in native.calls] == [
        "keygen",
        "install",
        "test",
    ]
    assert path.read_text(encoding="utf-8") == text


async def test_a_failed_test_when_the_config_could_not_be_read_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, native)
    checker = FakeChecker(None)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await picker(app, pilot, checker)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            f"status 255). {UNREAD} Machine 1: garden"
        )
    assert [Native.step(call) for call in native.calls] == ["install", "test"]


async def test_a_named_key_and_unnamed_keys_keep_their_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, Native())
    checker = FakeChecker(naming("~/ssh/id_a"))
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)

    def unnamed(name: str) -> tuple[str, str]:
        line = f"IdentityFile {folder / name}"
        return (
            "Your SSH config doesn't name this key for garden-host. Add this line "
            f"under Host garden-host; Workbench never edits the config: {line}",
            "Your SSH config doesn't name this key for garden-host; add this line "
            f"under Host garden-host: {line}",
        )

    async with app.run_test() as pilot:
        screen = await picker(app, pilot, checker)
        assert option_labels(screen) == [
            "id_a.pub (your SSH config offers this)",
            "id_b.pub",
            "Create a new key: id_ed25519_garden",
        ]
        assert [(choice.note, choice.hint) for choice in screen.choices] == [
            (None, None),
            unnamed("id_b"),
            unnamed("id_ed25519_garden"),
        ]
        assert note(screen) == ""
