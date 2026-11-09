"""K in scripts/check_links.py, run headless with native tools replaced by recorders.

The link fixture promises that no SSH configuration and no SSH are used: K must
offer no key from the user's SSH folder, and Enter must end in a result line
with the terminal handed back. HOME holds a fictional key in place of the real
folder, so nothing real is read or run even while these tests fail.
"""

import asyncio
import base64
import importlib.util
import socket
import struct
import sys
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.pilot import Pilot
from textual.widgets import OptionList

from ssh_workbench import app as app_module
from ssh_workbench import keys, ssh
from ssh_workbench.app import ResultSlot, SSHWorkbenchApp
from ssh_workbench.forms import KeySetup
from ssh_workbench.keys import PublicKey
from ssh_workbench.sshconfig import ssh_folder

ROOT = Path(__file__).resolve().parents[1]
CHECK_LINKS = ROOT / "scripts" / "check_links.py"
# The bindings K's steps call (app and keys import their own) and ssh.py's own.
NATIVE = (
    (app_module, "find_ssh"),
    (app_module, "run_native"),
    (keys, "find_ssh_keygen"),
    (ssh, "find_ssh"),
    (ssh, "find_ssh_keygen"),
    (ssh, "run_native"),
)
# K's choice for the first fixture machine, fixture-accepted.
CREATE = "Create a new key: id_ed25519_fixture_accepted"

type Answer = Callable[[SSHWorkbenchApp, Pilot[None], list[str]], Awaitable[None]]


def load_check_links() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_links_under_test", CHECK_LINKS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fictional_key_line() -> str:
    data = (
        struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + bytes([7]) * 32
    )
    return PublicKey("ssh-ed25519", base64.b64encode(data).decode(), "probe").line


def connection_status(app: SSHWorkbenchApp) -> str:
    return app.query_one("#connection-status", ResultSlot).message


def run_k(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: Answer
) -> tuple[int | None, list[str], list[str], list[Mock]]:
    """Run check_links.main() headless: K on the first machine, then `answer`.

    Returns main()'s result, the picker's options, the suspend events and the
    native recorders. SSH_WORKBENCH_SSH_DIR is unset, as an operator who follows
    the fixture's own instructions leaves it.
    """
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh" / "id_probe.pub").write_text(fictional_key_line() + "\n", "ascii")
    monkeypatch.setenv("HOME", str(home))
    # Path.home() reads USERPROFILE on Windows.
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("SSH_WORKBENCH_SSH_DIR")
    # A folder made with tempfile stays under tmp_path.
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    # Without the fixture's own guard, K would read the fictional home.
    assert ssh_folder() == home / ".ssh"

    check_links = load_check_links()
    recorders = []
    for owner, name in NATIVE:
        recorder = Mock(
            side_effect=AssertionError(f"K reached {owner.__name__}.{name}")
        )
        monkeypatch.setattr(owner, name, recorder)
        recorders.append(recorder)
    events: list[str] = []
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(
        HeadlessDriver,
        "suspend_application_mode",
        lambda self: events.append("suspend"),
    )
    monkeypatch.setattr(
        HeadlessDriver, "resume_application_mode", lambda self: events.append("resume")
    )
    options: list[str] = []

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("The link fixture attempted a socket connection")

    async def press_k(app: SSHWorkbenchApp) -> None:
        # The Windows loop's local socket pair exists before these guards.
        with monkeypatch.context() as guard:
            guard.setattr(socket.socket, "connect", unexpected)
            guard.setattr(socket.socket, "connect_ex", unexpected)
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("k")
                # push_screen makes a screen current before it has composed
                # its widgets.
                async with asyncio.timeout(5):
                    while app.is_running and not (
                        isinstance(app.screen, KeySetup) and app.screen.is_mounted
                    ):
                        await pilot.pause()
                picker = app.screen.query_one(OptionList)
                options.extend(
                    str(picker.get_option_at_index(index).prompt)
                    for index in range(picker.option_count)
                )
                await answer(app, pilot, events)
                await pilot.press("q")

    monkeypatch.setattr(SSHWorkbenchApp, "run", lambda app: asyncio.run(press_k(app)))
    monkeypatch.setattr(sys, "argv", [str(CHECK_LINKS)])
    try:
        result = check_links.main()
    finally:
        # main() keeps its guards for a dedicated process; this is pytest's.
        patch.stopall()
    assert sorted(path.name for path in (home / ".ssh").iterdir()) == ["id_probe.pub"]
    return result, options, events, recorders


@pytest.mark.usefixtures("no_external_actions")
def test_k_in_the_link_check_offers_no_key_from_the_home_ssh_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def cancel(app: SSHWorkbenchApp, pilot: Pilot[None], _: list[str]) -> None:
        await pilot.press("escape")
        async with asyncio.timeout(5):
            while app.is_running and isinstance(app.screen, KeySetup):
                await pilot.pause()

    result, options, events, recorders = run_k(tmp_path, monkeypatch, cancel)

    assert result == 0
    assert options == [CREATE]
    assert events == []
    for recorder in recorders:
        recorder.assert_not_called()


@pytest.mark.usefixtures("no_external_actions")
def test_enter_on_create_in_the_link_check_shows_a_result_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, bool, int | None, list[str]]] = []

    async def create(
        app: SSHWorkbenchApp, pilot: Pilot[None], events: list[str]
    ) -> None:
        assert isinstance(app.screen, KeySetup)
        index = next(
            position
            for position, choice in enumerate(app.screen.choices)
            if choice.create
        )
        for _ in range(index):
            await pilot.press("down")
        await pilot.press("enter")
        async with asyncio.timeout(5):
            while app.is_running and isinstance(app.screen, KeySetup):
                await pilot.pause()
        seen.append(
            (connection_status(app), app.is_running, app.return_code, list(events))
        )

    result, _, _, recorders = run_k(tmp_path, monkeypatch, create)

    assert result == 0
    for recorder in recorders:
        recorder.assert_not_called()
    assert seen == [
        (
            "Key setup is disabled in this link fixture. Machine 1: fixture-accepted",
            True,
            None,
            ["suspend", "resume"],
        )
    ]
