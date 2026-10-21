"""K in the app: the key picker and the three handed-off steps, all substituted.

No real ssh-keygen, SSH or key is used. `run_native` is replaced by a recorder
that writes fictional key files when asked to create a key.
"""

import asyncio
import base64
import dataclasses
import platform
import struct
import threading
from pathlib import Path

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, OptionList, RadioButton, Static

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.aliases import AliasMemory, AliasRecord, format_state, state_path
from ssh_workbench.app import SSHWorkbenchApp, StatusSymbol
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import (
    PublicKey,
    posix_install_command,
    windows_install_command,
)
from ssh_workbench.status import AliasTarget, State

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

SSH = "/fictional/ssh"
KEYGEN = "/fictional/ssh-keygen"
NO_REMOTE_COMMAND = ["-o", "RemoteCommand=none"]
KEY_ONLY = [
    "-o",
    "PreferredAuthentications=publickey",
    "-o",
    "PasswordAuthentication=no",
    "-o",
    "KbdInteractiveAuthentication=no",
    "-o",
    "ControlPath=none",
    *NO_REMOTE_COMMAND,
]
BOX = Machine("box", "Box", user="dev", addresses=("192.0.2.60",))
GARDEN = Machine("garden", "Garden", alias="garden-host")


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

    def __init__(
        self,
        statuses: dict[str, int] | None = None,
        interrupt: str | None = None,
        new_key: str | None = None,
    ) -> None:
        self.statuses = statuses or {}
        self.interrupt = interrupt
        self.new_key = new_key or public_key(9, "ssh-workbench-box").line
        self.calls: list[list[str]] = []

    @staticmethod
    def step(arguments: list[str]) -> str:
        if arguments[0] == KEYGEN:
            return "keygen"
        return "test" if arguments[-1] == "exit" else "install"

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        step = self.step(arguments)
        if step == self.interrupt:
            raise KeyboardInterrupt
        if step == "keygen":
            private = Path(arguments[arguments.index("-f") + 1])
            private.write_text("fictional private half\n", encoding="ascii")
            Path(f"{private}.pub").write_text(self.new_key + "\n", encoding="ascii")
        return self.statuses.get(step, 0)


class FakeChecker:
    def __init__(self, target: AliasTarget | None, hold=None) -> None:
        self.target = target
        self.hold = hold
        self.resolved: list[str] = []

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        if self.hold is not None:
            self.hold.wait(30)
        return self.target

    def port_open(self, host: str, port: int) -> bool:
        return False


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machines: tuple[Machine, ...],
    native: Native,
    text: str | None = None,
) -> tuple[Path, Path, str]:
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text("", encoding="ascii")
    (folder / "id_a.pub").write_text(public_key(1, "a").line + "\n", "ascii")
    (folder / "id_b.pub").write_text(public_key(2, "b").line + "\n", "ascii")
    (folder / "junk.pub").write_text("not a key\n", encoding="ascii")
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines(machines) if text is None else text
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    return folder, path, text


def option_labels(screen: KeySetup) -> list[str]:
    options = screen.query_one(OptionList)
    return [
        str(options.get_option_at_index(index).prompt)
        for index in range(options.option_count)
    ]


def note(screen: KeySetup) -> str:
    return str(screen.query_one("#key-note", Static).content)


def connection_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


async def picker(app: SSHWorkbenchApp, pilot) -> KeySetup:
    await pilot.press("k")
    await wait_for(pilot, lambda: showing(app, KeySetup))
    return app.screen


async def finished(app: SSHWorkbenchApp, pilot) -> None:
    await wait_for(pilot, lambda: "Machine 1:" in connection_status(app))


async def test_a_direct_machine_without_a_key_offers_pub_files_and_a_new_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert option_labels(screen) == [
            "id_a.pub",
            "id_b.pub",
            "Create a new key: id_ed25519_box",
        ]
        assert screen.query_one("#system-posix", RadioButton).value is True
        assert note(screen) == ""
        await pilot.press("escape")
        await wait_for(pilot, lambda: not isinstance(app.screen, KeySetup))
    assert native.calls == []
    assert path.read_text(encoding="utf-8") == text


async def test_a_new_key_is_created_installed_tested_and_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    new = folder / "id_ed25519_box"
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("down", "down", "enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Key login works. The key is saved as this machine's key. Machine 1: box"
        )
    created = public_key(9, "ssh-workbench-box")
    assert native.calls == [
        [KEYGEN, "-t", "ed25519", "-f", str(new), "-C", "ssh-workbench-box"],
        [
            SSH,
            *NO_REMOTE_COMMAND,
            "-o",
            "HostKeyAlias=box",
            "-l",
            "dev",
            "--",
            "192.0.2.60",
            posix_install_command(created),
        ],
        [
            SSH,
            *KEY_ONLY,
            "-o",
            "HostKeyAlias=box",
            "-l",
            "dev",
            "-i",
            str(new),
            "-o",
            "IdentitiesOnly=yes",
            "--",
            "192.0.2.60",
            "exit",
        ],
    ]
    assert read_machines(path)[0] == [dataclasses.replace(BOX, key=str(new))]


async def test_a_windows_target_gets_the_windows_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        screen.query_one("#system-windows", RadioButton).value = True
        await pilot.pause()
        await pilot.press("enter")
        await finished(app, pilot)
    assert native.calls[0][-1] == windows_install_command(public_key(1, "a"))


async def test_a_machine_with_a_key_uses_only_that_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    key = tmp_path / "ssh" / "id_keyed"
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key=str(key))
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)
    Path(f"{key}.pub").write_text(public_key(3, "keyed").line + "\n", "ascii")
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert option_labels(screen) == [f"{key} (this machine's key)"]
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == "Key login works. Machine 1: keyed"
    assert native.calls[0] == [
        SSH,
        *NO_REMOTE_COMMAND,
        "-o",
        "HostKeyAlias=keyed",
        "--",
        "192.0.2.61",
        posix_install_command(public_key(3, "keyed")),
    ]
    assert native.calls[1][-4:] == ["IdentitiesOnly=yes", "--", "192.0.2.61", "exit"]
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    ("choice", "native", "steps", "message"),
    [
        (
            ["down", "down"],
            Native(statuses={"keygen": 1}),
            ["keygen"],
            "ssh-keygen exited with status 1; nothing was installed.",
        ),
        (
            ["down", "down"],
            Native(new_key="not a key"),
            ["keygen"],
            "id_ed25519_box.pub is not a single valid OpenSSH public key; "
            "nothing was installed.",
        ),
        (
            [],
            Native(statuses={"install": 255}),
            ["install"],
            "Installing the key failed (SSH exited with status 255); "
            "login was not tested.",
        ),
        (
            [],
            Native(interrupt="install"),
            ["install"],
            "Key setup interrupted.",
        ),
    ],
)
async def test_a_failed_step_stops_the_later_ones(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    choice: list[str],
    native: Native,
    steps: list[str],
    message: str,
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press(*choice, "enter")
        await finished(app, pilot)
        assert connection_status(app) == f"{message} Machine 1: box"
        assert app.is_running
    assert [Native.step(call) for call in native.calls] == steps
    assert path.read_text(encoding="utf-8") == text


async def test_a_failed_login_test_still_saves_the_installed_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            "status 255). The key is saved as this machine's key. Machine 1: box"
        )
    assert read_machines(path)[0][0].key == str(folder / "id_a")


async def test_saving_a_key_warns_about_comments_in_the_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    text = "# Fictional notes kept by hand\n" + format_machines((BOX,))
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native, text)
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        screen = await picker(app, pilot)
        assert note(screen) == (
            "Saving rewrites the file without its comments or formatting; the old "
            "file is kept as machines.toml.bak."
        )
        await pilot.press("enter")
        await finished(app, pilot)
    assert read_machines(path)[0][0].key == str(folder / "id_a")


async def test_an_alias_offers_its_own_keys_first_and_explains_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native(statuses={"test": 255})
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10",
        22,
        proxied=False,
        user="dev",
        identity_files=("~/ssh/id_lab", "~/ssh/id_missing"),
        identities_only=True,
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        screen = await picker(app, pilot)
        assert checker.resolved == ["garden-host", "garden-host"]
        assert option_labels(screen) == [
            "id_lab.pub (your SSH config offers this)",
            "id_a.pub",
            "id_b.pub",
            "Create a new key: id_ed25519_garden",
        ]
        assert note(screen) == ""
        await pilot.press("down")
        line = f"IdentityFile {folder / 'id_a'}"
        assert note(screen) == (
            "Your SSH config doesn't name this key for garden-host. Add this line "
            f"under Host garden-host; Workbench never edits the config: {line}"
        )
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "The key was installed, but key-only login failed (SSH exited with "
            "status 255). Your SSH config offers only its own keys for garden-host "
            f"(IdentitiesOnly); add this line under Host garden-host: {line} "
            "Machine 1: garden"
        )
    assert native.calls == [
        [
            SSH,
            *NO_REMOTE_COMMAND,
            "--",
            "garden-host",
            posix_install_command(public_key(1, "a")),
        ],
        [SSH, *KEY_ONLY, "--", "garden-host", "exit"],
    ]
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    ("identities_only", "hint"),
    [
        (
            True,
            "Your SSH config offers only its own keys for garden-host "
            "(IdentitiesOnly); add this line under Host garden-host:",
        ),
        (
            False,
            "Your SSH config doesn't name this key for garden-host; add this line "
            "under Host garden-host:",
        ),
    ],
)
async def test_an_alias_test_passing_with_an_unnamed_key_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, identities_only: bool, hint: str
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10",
        22,
        proxied=False,
        user="dev",
        identity_files=("~/ssh/id_lab",),
        identities_only=identities_only,
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("down")
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Key-only login works, but SSH may have used another key. "
            f"{hint} IdentityFile {folder / 'id_a'} Machine 1: garden"
        )
    assert path.read_text(encoding="utf-8") == text


async def test_an_alias_test_passing_with_its_configured_key_says_it_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), native)
    (folder / "id_lab.pub").write_text(public_key(4, "lab").line + "\n", "ascii")
    target = AliasTarget(
        "192.0.2.10", 22, proxied=False, user="dev", identity_files=("~/ssh/id_lab",)
    )
    checker = FakeChecker(target)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(pilot, lambda: checker.resolved == ["garden-host"])
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == "Key login works. Machine 1: garden"


async def test_k_waits_for_the_alias_and_quitting_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hold = threading.Event()
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    checker = FakeChecker(None, hold=hold)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    try:
        async with asyncio.timeout(5):
            async with app.run_test() as pilot:
                await pilot.press("k")
                await wait_for(
                    pilot, lambda: checker.resolved.count("garden-host") == 2
                )
                assert not isinstance(app.screen, KeySetup)
                await pilot.press("q")
                assert not app.is_running
    finally:
        hold.set()


async def test_without_a_terminal_handoff_nothing_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), native)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: False))
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await picker(app, pilot)
        await pilot.press("enter")
        await finished(app, pilot)
        assert connection_status(app) == (
            "Cannot hand off this terminal. Run SSH Workbench in a local terminal. "
            "Machine 1: box"
        )
    assert native.calls == []


async def test_a_key_in_a_missing_home_folder_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native = Native()
    keyed = Machine("keyed", "Keyed", addresses=("192.0.2.61",), key="~/.ssh/id_keyed")
    folder, path, text = workspace(tmp_path, monkeypatch, (keyed,), native)

    def no_home(cls: type[Path]) -> Path:
        raise RuntimeError("no home folder")

    monkeypatch.setattr(Path, "home", classmethod(no_home))
    app = SSHWorkbenchApp((keyed,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("k")
        await wait_for(pilot, lambda: "Machine 1:" in connection_status(app))
        assert connection_status(app) == (
            "Could not find your home folder for this machine's key. Machine 1: keyed"
        )
        assert not isinstance(app.screen, KeySetup)
        assert app.is_running
    assert native.calls == []


async def test_k_is_dimmed_for_a_missing_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    record = AliasRecord("192.0.2.10", "dev", 22)
    state_path(path, platform.node()).write_text(
        format_state(
            AliasMemory(("garden-host",), {"garden-host": record}, {}),
            platform.node(),
        ),
        encoding="utf-8",
    )
    checker = FakeChecker(None)
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(
            pilot,
            lambda: [s.state for s in app.query(StatusSymbol)] == [State.NOT_FOUND],
        )
        assert app.check_action("key_setup", ()) is None
        await pilot.press("k")
        await pilot.pause()
        assert not isinstance(app.screen, KeySetup)


async def test_footer_with_k_fits_60_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX,), Native())
    app = SSHWorkbenchApp((BOX,), config_path=path, file_text=text)
    async with app.run_test(size=(60, 20)) as pilot:
        footer = app.query_one(Footer)
        await wait_for(
            pilot,
            lambda: "key_setup" in {key.action for key in footer.query("FooterKey")},
        )
        await wait_for(
            pilot, lambda: all(key.region.width for key in footer.query("FooterKey"))
        )
        for key in footer.query("FooterKey"):
            assert key.region.right <= 59, key.action


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_the_picker_shows_its_note_and_keys_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (GARDEN,), Native())
    app = SSHWorkbenchApp((GARDEN,), config_path=path, file_text=text)
    async with app.run_test(size=size) as pilot:
        screen = await picker(app, pilot)
        await wait_for(pilot, lambda: note(screen).startswith("Your SSH config"))
        await pilot.pause()
        box = screen.query_one("#key-setup")
        assert box.region.bottom <= size[1]
        for widget in ("#key-note", "#key-help", "#key-choices", "#key-system"):
            region = screen.query_one(widget).region
            assert region.height > 0, widget
            assert box.region.contains_region(region), widget
