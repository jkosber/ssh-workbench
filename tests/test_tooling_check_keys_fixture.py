"""C in scripts/check_keys.py, run headless with native SSH replaced by recorders.

The fixture promises never to run ssh-keygen or SSH. K's steps are its local
children; C must not reach ssh.py's own lookup or launch either.
"""

import asyncio
import importlib.util
import socket
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import ListView

from ssh_workbench import ssh
from ssh_workbench.app import ResultSlot, SSHWorkbenchApp

ROOT = Path(__file__).resolve().parents[1]
CHECK_KEYS = ROOT / "scripts" / "check_keys.py"


def load_check_keys() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_keys_under_test", CHECK_KEYS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def connection_status(app: SSHWorkbenchApp) -> str:
    return app.query_one("#connection-status", ResultSlot).message


@pytest.mark.usefixtures("no_external_actions")
@pytest.mark.parametrize(
    ("position", "machine"),
    [pytest.param(0, "box", id="direct"), pytest.param(1, "garden", id="alias")],
)
def test_c_in_the_key_check_shows_a_result_without_reaching_native_ssh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, position: int, machine: str
) -> None:
    check_keys = load_check_keys()
    # ssh.launch_ssh looks these up in its own module, not in app's.
    find_ssh = Mock(side_effect=AssertionError("C reached ssh.find_ssh"))
    run_native = Mock(side_effect=AssertionError("C reached ssh.run_native"))
    monkeypatch.setattr(ssh, "find_ssh", find_ssh)
    monkeypatch.setattr(ssh, "run_native", run_native)
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
    seen: list[tuple[int | None, str, bool, int | None, list[str]]] = []

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("The key fixture attempted a socket connection")

    async def press_c(app: SSHWorkbenchApp) -> None:
        # The Windows loop's local socket pair exists before these guards.
        with monkeypatch.context() as guard:
            guard.setattr(socket.socket, "connect", unexpected)
            guard.setattr(socket.socket, "connect_ex", unexpected)
            async with app.run_test(size=(80, 24)) as pilot:
                # R is offered again once the startup review has reported.
                async with asyncio.timeout(5):
                    while app.check_action("refresh", ()) is not True:
                        await pilot.pause()
                for _ in range(position):
                    await pilot.press("down")
                await pilot.press("c")
                seen.append(
                    (
                        app.query_one(ListView).index,
                        connection_status(app),
                        app.is_running,
                        app.return_code,
                        list(events),
                    )
                )
                await pilot.press("q")

    monkeypatch.setattr(SSHWorkbenchApp, "run", lambda app: asyncio.run(press_c(app)))
    monkeypatch.setattr(
        sys, "argv", [str(CHECK_KEYS), "--folder", str(tmp_path / "keys")]
    )

    assert check_keys.main() == 0
    find_ssh.assert_not_called()
    run_native.assert_not_called()
    assert seen == [
        (
            position,
            "C does not start SSH in this key-setup check. "
            f"Machine {position + 1}: {machine}",
            True,
            None,
            ["suspend", "resume"],
        )
    ]
