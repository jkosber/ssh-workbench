"""K pressed while the startup review still runs, on an alias it finds missing.

The review and K's ssh -G are held by a fake resolver, so each test fixes the
order of their answers: the review first, or K's picker first. Once the review
says the alias is missing, no picker may stay open and Enter must not install
or test a key through the old name, wherever SSH now sends it. Everything is
fictional and substituted: no real ssh, key, SSH folder or machine file.
"""

import asyncio
import base64
import platform
import struct
import threading
from pathlib import Path

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Static

from ssh_workbench import app as app_module
from ssh_workbench import keys
from ssh_workbench.aliases import AliasMemory, AliasRecord, format_state, state_path
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import PublicKey, posix_install_command
from ssh_workbench.status import AliasTarget

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
OLD = Machine("old", "Old", alias="old-host")
# A second vanished alias makes the review resolve new-host, where the fake
# holds it, even when old-host is still listed.
GONE = Machine("gone", "Gone", alias="gone-host")
MACHINES = (OLD, GONE)
# The previous run saw both aliases as literal Host names.
PREVIOUS = AliasMemory(
    ("old-host", "gone-host"),
    {
        "old-host": AliasRecord("192.0.2.10", "dev", 22),
        "gone-host": AliasRecord("192.0.2.20", "dev", 22),
    },
    {},
)
TARGETS = {
    # Where old-host pointed, so the review offers it as old-host's new name.
    "new-host": AliasTarget("192.0.2.10", 22, proxied=False, user="dev"),
    # Wherever SSH sends old-host now, listed or not.
    "old-host": AliasTarget(
        "192.0.2.11", 22, proxied=False, user="dev", identity_files=("~/ssh/id_a",)
    ),
}
OFFER = "× alias not found. Looks like old-host became new-host. Press U to update."
ORDERINGS = pytest.mark.parametrize(
    "picker_first",
    [False, True],
    ids=["review-before-k-answers", "picker-open-at-review"],
)


def blob(seed: int) -> str:
    data = (
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes([seed]) * 32
    )
    return base64.b64encode(data).decode()


KEY = PublicKey("ssh-ed25519", blob(1), "a")


class Native:
    """Records each handed-off command; every step exits 0."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, arguments: list[str], name: str = "SSH") -> int:
        self.calls.append(list(arguments))
        return 0


class HeldPerAlias:
    """Each alias's ssh -G waits for its own event; port checks find nothing."""

    def __init__(self) -> None:
        self.holds = {"new-host": threading.Event(), "old-host": threading.Event()}
        self.resolved: list[str] = []

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        self.holds[alias].wait(30)
        return TARGETS[alias]

    def port_open(self, host: str, port: int) -> bool:
        return False

    def release(self) -> None:
        for hold in self.holds.values():
            hold.set()


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    native: Native,
    hosts: tuple[str, ...],
) -> tuple[Path, str]:
    """An SSH folder listing `hosts` with one key, the machine file, the
    previous run's state and the substituted native boundary."""
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_text(
        "".join(f"Host {name}\n    User dev\n" for name in hosts), encoding="ascii"
    )
    (folder / "id_a.pub").write_text(KEY.line + "\n", "ascii")
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines(MACHINES)
    path.write_text(text, encoding="utf-8")
    state_path(path, platform.node()).write_text(
        format_state(PREVIOUS, platform.node()), encoding="utf-8"
    )
    monkeypatch.setattr(app_module, "run_native", native)
    monkeypatch.setattr(app_module, "find_ssh", lambda: SSH)
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: KEYGEN)
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    return path, text


def tracked_threads(monkeypatch: pytest.MonkeyPatch) -> list[threading.Thread]:
    """Record every thread the app starts, so a test can wait for all of them."""
    started: list[threading.Thread] = []

    def thread(*args, **kwargs) -> threading.Thread:
        started.append(threading.Thread(*args, **kwargs))
        return started[-1]

    monkeypatch.setattr(app_module, "Thread", thread)
    return started


async def answered(pilot, threads: list[threading.Thread]) -> None:
    """Each answer is posted before its thread ends; then it is handled."""
    for thread in threads:
        thread.join(5)
    await pilot.pause()


def connection_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


def machine_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#machine-status", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


async def k_during_review(
    app: SSHWorkbenchApp,
    pilot,
    checker: HeldPerAlias,
    threads: list[threading.Thread],
    picker_first: bool,
) -> None:
    """K on Old while the startup review is held; then the review's answer and
    K's ssh -G answer arrive in the order `picker_first` names."""
    # The review checks new-host as a rename and waits there; it is the first
    # thread the app starts.
    await wait_for(pilot, lambda: checker.resolved == ["new-host"])
    if picker_first:
        checker.holds["old-host"].set()
        await pilot.press("k")
        await wait_for(pilot, lambda: showing(app, KeySetup))
        checker.holds["new-host"].set()
        await answered(pilot, threads)
    else:
        await pilot.press("k")
        await wait_for(pilot, lambda: checker.resolved == ["new-host", "old-host"])
        checker.holds["new-host"].set()
        # The review answers while K's ssh -G is still held.
        await answered(pilot, threads[:1])
        checker.holds["old-host"].set()
        await answered(pilot, threads)


@ORDERINGS
async def test_k_sets_up_no_key_through_an_alias_the_review_finds_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, picker_first: bool
) -> None:
    native = Native()
    path, text = workspace(tmp_path, monkeypatch, native, ("new-host",))
    threads = tracked_threads(monkeypatch)
    checker = HeldPerAlias()
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await k_during_review(app, pilot, checker, threads, picker_first)
            assert not isinstance(app.screen, KeySetup)
            assert machine_status(app) == OFFER
            assert app.check_action("key_setup", ()) is None
            # Enter, as the user would press it in the picker.
            await pilot.press("enter")
            await pilot.pause()
    finally:
        checker.release()
    assert native.calls == []
    # ssh -G ran for the review's rename check and for K, nothing else.
    assert checker.resolved == ["new-host", "old-host"]
    assert path.read_text(encoding="utf-8") == text


@ORDERINGS
async def test_k_during_a_review_that_keeps_the_alias_sets_up_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, picker_first: bool
) -> None:
    native = Native()
    path, text = workspace(tmp_path, monkeypatch, native, ("old-host", "new-host"))
    threads = tracked_threads(monkeypatch)
    checker = HeldPerAlias()
    app = SSHWorkbenchApp(MACHINES, config_path=path, file_text=text, checker=checker)
    try:
        async with app.run_test() as pilot:
            await k_during_review(app, pilot, checker, threads, picker_first)
            await wait_for(pilot, lambda: showing(app, KeySetup))
            await pilot.press("enter")
            await wait_for(pilot, lambda: "Machine 1:" in connection_status(app))
            assert connection_status(app) == "Key login works. Machine 1: old"
    finally:
        checker.release()
    assert native.calls == [
        [SSH, *NO_REMOTE_COMMAND, "--", "old-host", posix_install_command(KEY)],
        [SSH, *KEY_ONLY, "--", "old-host", "exit"],
    ]
    assert path.read_text(encoding="utf-8") == text
