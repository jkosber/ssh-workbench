"""A machine file path holding a lone surrogate, as Python reads a folder name with
a byte that isn't UTF-8, is refused before the generated file is written.

No folder with such a name is created: Windows can't hold one.
"""

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Checkbox, Input, RadioButton

from ssh_workbench import app as app_module
from ssh_workbench.app import ResultSlot, SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.exports import (
    EXPORT_NAME,
    ExportError,
    format_exports,
    write_exports,
)
from ssh_workbench.forms import ConfirmInclude, MachineForm

BOX = Machine("box", "Box", addresses=("192.0.2.60",), export_alias=True)
LAB = Machine("lab", "Lab", addresses=("192.0.2.61",))
USER_CONFIG = b"Host mine\n    HostName 192.0.2.10\n"
REFUSED = "Can't export: the machine file's path can't be written to an SSH config."


# On Linux the byte 0xFF in a folder name reads as U+DCFF; U+D800 and U+DFFF
# are the ends of the surrogate range.
@pytest.mark.parametrize("name", ["cfg\udcff", "cfg\ud800", "cfg\udfff"])
def test_a_machine_file_path_with_a_surrogate_is_refused_before_any_write(
    tmp_path: Path, name: str
) -> None:
    folder = tmp_path / "ssh"
    source = tmp_path / name / "machines.toml"

    with pytest.raises(ExportError) as caught:
        write_exports(folder, [BOX], source)

    assert str(caught.value) == REFUSED
    assert not (folder / EXPORT_NAME).exists()
    assert not folder.exists()


@pytest.mark.parametrize("name", ["cfg", "café", "cfg퟿", "cfg"])
def test_a_machine_file_path_without_a_surrogate_is_written(
    tmp_path: Path, name: str
) -> None:
    folder = tmp_path / "ssh"
    source = tmp_path / name / "machines.toml"

    write_exports(folder, [BOX], source)

    assert (folder / EXPORT_NAME).read_text(encoding="utf-8") == format_exports(
        [BOX], source
    )


def connection_status(app: SSHWorkbenchApp) -> str:
    return app.query_one("#connection-status", ResultSlot).message


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


@pytest.mark.asyncio
@pytest.mark.usefixtures("no_external_actions", "no_app_connections")
async def test_a_with_an_export_shows_the_refusal_and_keeps_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "ssh"
    folder.mkdir()
    (folder / "config").write_bytes(USER_CONFIG)
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    path = tmp_path / "machines.toml"
    text = format_machines((LAB,))
    path.write_text(text, encoding="utf-8")
    # The app saves a real machine file; only the path it hands the export names
    # the surrogate folder, which is never created.
    unwritable = tmp_path / "cfg\udcff" / "machines.toml"
    real_write_exports = app_module.write_exports

    def from_unwritable(folder: Path, machines: object, source: Path) -> None:
        real_write_exports(folder, machines, unwritable)

    monkeypatch.setattr(app_module, "write_exports", from_unwritable)
    app = SSHWorkbenchApp((LAB,), config_path=path, file_text=text)
    async with app.run_test() as pilot:
        await pilot.press("a")
        await wait_for(pilot, lambda: showing(app, MachineForm))
        form = app.screen
        form.query_one("#form-id", Input).value = "box"
        form.query_one("#form-name", Input).value = "Box"
        form.query_one("#kind-direct", RadioButton).value = True
        await pilot.pause()
        form.query_one("#form-addresses", Input).value = "192.0.2.60"
        form.query_one("#form-export_alias", Checkbox).value = True
        await pilot.pause()
        await pilot.press("ctrl+s")
        await wait_for(pilot, lambda: "Can't export" in connection_status(app))
        await pilot.pause()
        assert connection_status(app) == f"Saved machine 2: box. {REFUSED}"
        assert not isinstance(app.screen, ConfirmInclude)
        assert app.machines == (LAB, BOX)
    assert read_machines(path)[0] == [LAB, BOX]
    assert not (folder / EXPORT_NAME).exists()
    assert (folder / "config").read_bytes() == USER_CONFIG
