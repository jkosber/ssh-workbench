"""A NUL byte in a fictional SSH config ends its line, as it does for OpenSSH."""

import asyncio
import platform
from pathlib import Path

import pytest
from textual.widgets import Static

from ssh_workbench.aliases import AliasMemory, AliasRecord, format_state, state_path
from ssh_workbench.app import SSHWorkbenchApp, StatusSymbol
from ssh_workbench.config import Machine, format_machines
from ssh_workbench.forms import MachineForm
from ssh_workbench.sshconfig import host_names
from ssh_workbench.status import AliasTarget, State

GARDEN = Machine("garden", "Garden", alias="old-host")
LAB = Machine("lab", "Lab", addresses=("192.0.2.50",))
# At the last check old-host was a literal Host name pointing at this record.
PREVIOUS = AliasMemory(
    ("old-host",), {"old-host": AliasRecord("192.0.2.10", "dev", 22)}, {}
)
NUL_INCLUDE = b"Include a\x00b/*\nHost safe-host\n"
NO_OFFER = (
    "× alias not found. Fix your SSH config and press R, or press E and save to "
    "keep or change the alias."
)


class FakeChecker:
    def __init__(self) -> None:
        self.resolved: list[str] = []

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        self.resolved.append(alias)
        return None

    def port_open(self, host: str, port: int) -> bool:
        return False


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machines: tuple[Machine, ...],
    config: bytes,
    state: AliasMemory | None = None,
) -> tuple[Path, str]:
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_bytes(config)
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines(machines)
    path.write_text(text, encoding="utf-8")
    if state is not None:
        state_path(path, platform.node()).write_text(
            format_state(state, platform.node()), encoding="utf-8"
        )
    return path, text


def symbols(app: SSHWorkbenchApp) -> list[State]:
    return [widget.state for widget in app.query(StatusSymbol)]


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


def test_an_include_with_a_nul_before_a_wildcard_never_raises(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    folder.mkdir()
    (folder / "config").write_bytes(NUL_INCLUDE)

    assert host_names(folder) == ["safe-host"]


def test_a_host_line_ends_at_its_first_nul(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    folder.mkdir()
    (folder / "config").write_bytes(b"Host alpha\x00beta gamma\nHost delta\n")

    assert host_names(folder) == ["alpha", "delta"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("no_external_actions", "no_app_connections")
async def test_a_opens_the_form_with_the_names_after_a_nul_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, text = workspace(tmp_path, monkeypatch, (LAB,), NUL_INCLUDE)
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("a")
        await wait_for(pilot, lambda: showing(app, MachineForm))

        assert app.screen.host_names == ("safe-host",)
        await pilot.press("ctrl+q")
        assert not app.is_running
        assert app.return_code == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("no_external_actions", "no_app_connections")
async def test_the_review_marks_a_vanished_alias_missing_after_a_nul_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = (GARDEN, LAB)
    path, text = workspace(tmp_path, monkeypatch, machines, NUL_INCLUDE, PREVIOUS)
    checker = FakeChecker()
    app = SSHWorkbenchApp(machines, config_path=path, file_text=text, checker=checker)
    async with app.run_test() as pilot:
        await wait_for(
            pilot, lambda: symbols(app) and State.CHECKING not in symbols(app)
        )

        assert app._missing == {"old-host": None}
        assert symbols(app) == [State.NOT_FOUND, State.OFFLINE]
        assert str(app.query_one("#machine-status", Static).content) == NO_OFFER
        # Only the review's rename lookup ran ssh -G; old-host never did.
        assert checker.resolved == ["safe-host"]
