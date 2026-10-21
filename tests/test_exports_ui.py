"""Exported aliases in the app: the form's checkbox, the generated file and the
Include prompt, all in temporary SSH folders."""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Checkbox, Input, RadioButton, Static

from ssh_workbench import app as app_module
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.exports import EXPORT_NAME, ExportError, format_exports
from ssh_workbench.forms import ConfirmDelete, ConfirmInclude, MachineForm
from ssh_workbench.status import AliasTarget

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
        assert str(box.label) == "ssh <ID> works in any terminal"


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
            [LAB, BOX], path
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
    exported.write_text(format_exports([BOX], path), encoding="utf-8")
    app = SSHWorkbenchApp((BOX, LAB), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("y")
        await wait_for(pilot, lambda: "Deleted machine 1" in connection_status(app))
    assert exported.read_text(encoding="utf-8") == format_exports([], path)


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
    (folder / EXPORT_NAME).write_text(format_exports([BOX], path), encoding="utf-8")
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


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_every_connection_field_shows_in_the_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int]
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,))
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test(size=size) as pilot:
        await pilot.press("a")
        await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
        form = app.screen
        await pilot.pause()
        aliases = form.query_one("#alias-fields")
        assert aliases.region.contains_region(form.query_one("#form-alias").region)
        assert aliases.region.contains_region(form.query_one("#form-hosts").region)
        form.query_one("#kind-direct", RadioButton).value = True
        await pilot.pause()
        direct = form.query_one("#direct-fields")
        for field in ("addresses", "user", "port", "key", "export_alias"):
            region = form.query_one(f"#form-{field}").region
            assert region.height > 0, field
            assert direct.region.contains_region(region), field


async def test_a_failed_export_is_shown_instead_of_the_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(folder: Path, machines: object, source: Path) -> None:
        raise ExportError("Could not write ssh-workbench.config: permission denied.")

    monkeypatch.setattr(app_module, "write_exports", refuse)
    folder, path, text = workspace(tmp_path, monkeypatch, (LAB,))
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await add_exported_box(app, pilot)
        await wait_for(pilot, lambda: "Could not write" in connection_status(app))
        await pilot.pause()
        assert connection_status(app) == (
            "Saved machine 2: box. Could not write ssh-workbench.config: permission "
            "denied."
        )
        assert not isinstance(app.screen, ConfirmInclude)
    assert (folder / "config").read_bytes() == USER_CONFIG


async def test_the_generated_file_names_the_machine_file_absolutely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX, LAB))
    # As typed after --config: relative to the working folder.
    monkeypatch.chdir(tmp_path)
    relative = Path("machines.toml")
    app = SSHWorkbenchApp((BOX, LAB), config_path=relative, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("down", "e")
        await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: "Saved machine 2: lab." in connection_status(app))
    assert (folder / EXPORT_NAME).read_text(encoding="utf-8") == format_exports(
        [BOX, LAB], path.absolute()
    )


class OfflineChecker:
    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return AliasTarget("192.0.2.10", 22, proxied=False, user="dev")

    def port_open(self, host: str, port: int) -> bool:
        return False


async def test_exported_names_are_not_the_users_host_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    included = b"Include ssh-workbench.config\n" + USER_CONFIG
    named_box = Machine("other", "Other", alias="box")
    folder, path, text = workspace(tmp_path, monkeypatch, (BOX, named_box), included)
    (folder / EXPORT_NAME).write_text(format_exports([BOX], path), encoding="utf-8")
    app = SSHWorkbenchApp(
        (BOX, named_box), config_path=path, file_text=text, checker=OfflineChecker()
    )
    async with app.run_test() as pilot:
        await pilot.press("down")
        target = app.query_one("#machine-target", Static)
        await wait_for(pilot, lambda: "not in your SSH config" in str(target.content))
        assert str(target.content) == "box (not in your SSH config)"
