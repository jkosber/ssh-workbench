"""Exported aliases in the app: the form's checkbox, the generated file and the
Include prompt, all in temporary SSH folders."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Checkbox, Input, RadioButton, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.exports import EXPORT_NAME, format_exports
from ssh_workbench.forms import ConfirmDelete, ConfirmInclude, MachineForm

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

BOX = Machine("box", "Box", addresses=("192.0.2.60",), export_alias=True)
LAB = Machine("lab", "Lab", addresses=("192.0.2.61",))
USER_CONFIG = b"Host mine\n    HostName 192.0.2.10\n"
ADDED = (
    'Added "Include ssh-workbench.config" to {path}; a copy is in '
    "config.ssh-workbench.bak."
)
DECLINED = (
    "Exported aliases work once your SSH config starts with: "
    "Include ssh-workbench.config"
)


def workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    machines: tuple[Machine, ...],
    config: bytes | None = USER_CONFIG,
) -> tuple[Path, Path, str]:
    folder = tmp_path / "ssh"
    folder.mkdir()
    if config is not None:
        (folder / "config").write_bytes(config)
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines(machines)
    path.write_text(text, encoding="utf-8")
    return folder, path, text


def connection_status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def add_exported_box(app: SSHWorkbenchApp, pilot) -> MachineForm:
    await pilot.press("a")
    await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
    form = app.screen
    form.query_one("#form-id", Input).value = "box"
    form.query_one("#form-name", Input).value = "Box"
    form.query_one("#kind-direct", RadioButton).value = True
    await pilot.pause()
    form.query_one("#form-addresses", Input).value = "192.0.2.60"
    form.query_one("#form-export_alias", Checkbox).value = True
    await pilot.pause()
    await pilot.press("ctrl+s")
    return form


async def test_the_export_checkbox_belongs_to_direct_machines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,))
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("a")
        await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
        form = app.screen
        assert form.query_one("#direct-fields").display is False
        form.query_one("#kind-direct", RadioButton).value = True
        await pilot.pause()
        assert form.query_one("#direct-fields").display is True
        box = form.query_one("#form-export_alias", Checkbox)
        assert box.parent.id == "direct-fields"
        assert box.value is False
        assert str(box.label) == (
            "Export as an SSH alias: ssh <ID> works in any terminal"
        )


async def test_saving_an_export_writes_the_file_and_y_adds_the_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,))
    config = folder / "config"
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await add_exported_box(app, pilot)
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmInclude))
        assert read_machines(path)[0] == [LAB, BOX]
        assert (folder / EXPORT_NAME).read_text(encoding="utf-8") == format_exports(
            [LAB, BOX]
        )
        assert config.read_bytes() == USER_CONFIG
        assert str(app.screen.query_one("#include-line", Static).content) == (
            "Include ssh-workbench.config"
        )
        await pilot.press("y")
        await wait_for(pilot, lambda: not isinstance(app.screen, ConfirmInclude))
        assert connection_status(app) == ADDED.format(path=config)
    assert config.read_bytes() == b"Include ssh-workbench.config\n" + USER_CONFIG
    assert (folder / "config.ssh-workbench.bak").read_bytes() == USER_CONFIG


async def test_n_changes_nothing_and_is_not_asked_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,))
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await add_exported_box(app, pilot)
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmInclude))
        await pilot.press("n")
        await wait_for(pilot, lambda: not isinstance(app.screen, ConfirmInclude))
        assert connection_status(app) == DECLINED
        await pilot.press("e")
        await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: "Saved machine 2: box." in connection_status(app))
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmInclude)
    assert (folder / "config").read_bytes() == USER_CONFIG
    assert not (folder / "config.ssh-workbench.bak").exists()


async def test_an_existing_include_line_means_no_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    included = b"Include ssh-workbench.config\n" + USER_CONFIG
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,), included)
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await add_exported_box(app, pilot)
        await wait_for(pilot, lambda: "Saved machine 2: box." in connection_status(app))
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmInclude)
    assert (folder / EXPORT_NAME).exists()
    assert (folder / "config").read_bytes() == included


async def test_y_creates_a_missing_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,), config=None)
    config = folder / "config"
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await add_exported_box(app, pilot)
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmInclude))
        await pilot.press("y")
        await wait_for(pilot, lambda: not isinstance(app.screen, ConfirmInclude))
        assert connection_status(app) == (
            f'Created {config} with "Include ssh-workbench.config".'
        )
    assert config.read_bytes() == b"Include ssh-workbench.config\n"


async def test_deleting_the_exported_machine_removes_its_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX, LAB))
    exported = folder / EXPORT_NAME
    exported.write_text(format_exports([BOX]), encoding="utf-8")
    app = SSHWorkbenchApp((BOX, LAB), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("y")
        await wait_for(pilot, lambda: "Deleted machine 1" in connection_status(app))
    assert exported.read_text(encoding="utf-8") == format_exports([])


async def test_an_export_named_like_a_users_host_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    own = b"Include ssh-workbench.config\nHost box\n    HostName 192.0.2.9\n"
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,), own)
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        form = await add_exported_box(app, pilot)
        await pilot.pause()
        assert isinstance(app.screen, MachineForm)
        assert str(form.query_one("#form-export_alias-error", Static).content) == (
            "your SSH config already has Host box; SSH would use the exported entry "
            "instead"
        )
    assert read_machines(path)[0] == [LAB]
    assert not (folder / EXPORT_NAME).exists()


async def test_the_generated_file_never_counts_as_a_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    included = b"Include ssh-workbench.config\n" + USER_CONFIG
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX, LAB), included)
    (folder / EXPORT_NAME).write_text(format_exports([BOX]), encoding="utf-8")
    app = SSHWorkbenchApp((BOX, LAB), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("e")
        await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: "Saved machine 1: box." in connection_status(app))


async def test_details_name_the_exported_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX, LAB))
    app = SSHWorkbenchApp((BOX, LAB), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.pause()
        connection = app.query_one("#machine-connection", Static)
        assert str(connection.content) == "Direct, exported as ssh box"
        await pilot.press("down")
        await pilot.pause()
        assert str(connection.content) == "Direct"
