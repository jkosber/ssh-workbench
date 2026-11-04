"""Machine files beyond the TOML parser's limits fail like any other TOML error.

Python's tomllib raises RecursionError for deep nesting or a dotted key with
too many parts, and ValueError for an integer with too many digits, instead of
TOMLDecodeError. The inputs are built here, with fictional text only.
"""

import asyncio
import shutil
import subprocess
import sysconfig
import traceback
from pathlib import Path

import pytest
from textual.widgets import Input, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import (
    ConfigError,
    Machine,
    format_machines,
    parse_machines,
    read_machines,
)
from ssh_workbench.forms import MachineForm

MARKER = "private-marker"
HEAD = f"# {MARKER}\nschema_version = 2\n"
BEYOND_LIMITS = {
    "nested-arrays": HEAD + f"{MARKER} = " + "[" * 1000 + "]" * 1000 + "\n",
    "nested-inline-tables": (
        HEAD + f"{MARKER} = " + "{a = " * 1000 + "1" + "}" * 1000 + "\n"
    ),
    "integer-of-4301-digits": HEAD + f"{MARKER} = " + "1" * 4301 + "\n",
    "dotted-key-of-1001-parts": HEAD + ".".join([MARKER] * 1001) + " = 1\n",
}
MESSAGE = "TOML: could not parse the file"
MACHINES = (Machine("studio", "Studio", addresses=("192.0.2.40",)),)


def write_machine_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / MARKER / "machines.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def cli() -> str:
    entry_point = shutil.which("ssh-workbench", path=sysconfig.get_path("scripts"))
    assert entry_point is not None, "Install the package with uv sync --locked first."
    return entry_point


@pytest.mark.parametrize("text", BEYOND_LIMITS.values(), ids=BEYOND_LIMITS)
def test_loader_reports_a_fixed_toml_error(tmp_path: Path, text: str) -> None:
    path = write_machine_file(tmp_path, text)

    with pytest.raises(ConfigError) as caught:
        read_machines(path)

    assert str(caught.value) == MESSAGE
    report = "".join(traceback.format_exception(caught.value))
    assert MARKER not in report
    assert str(path) not in report
    assert path.read_text(encoding="utf-8") == text
    # The parser still works after the failure.
    assert parse_machines(format_machines(MACHINES)) == list(MACHINES)


@pytest.mark.parametrize("text", BEYOND_LIMITS.values(), ids=BEYOND_LIMITS)
def test_cli_exits_with_the_toml_error(cli: str, tmp_path: Path, text: str) -> None:
    path = write_machine_file(tmp_path, text)

    result = subprocess.run(
        [cli, "--config", str(path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.splitlines()[-1] == f"ssh-workbench: error: {MESSAGE}"
    assert "Traceback" not in result.stderr
    assert MARKER not in result.stderr
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.asyncio
@pytest.mark.usefixtures("no_external_actions", "no_app_connections")
@pytest.mark.parametrize("text", BEYOND_LIMITS.values(), ids=BEYOND_LIMITS)
async def test_outside_change_beyond_limits_shows_the_error(
    tmp_path: Path, text: str
) -> None:
    saved = format_machines(MACHINES)
    path = write_machine_file(tmp_path, saved)
    app = SSHWorkbenchApp(parse_machines(saved), config_path=path, file_text=saved)
    async with app.run_test() as pilot:
        await pilot.press("a")
        async with asyncio.timeout(5):
            while not (isinstance(app.screen, MachineForm) and app.screen.is_mounted):
                await pilot.pause()
        form = app.screen
        for field, value in {"id": "web", "name": "Web", "alias": "web-host"}.items():
            form.query_one(f"#form-{field}", Input).value = value
        path.write_text(text, encoding="utf-8")

        await pilot.press("ctrl+s")
        await pilot.pause()

        assert app.is_running
        assert str(form.query_one("#form-message", Static).content) == (
            "The machine file changed outside Workbench and now has an error: "
            f"{MESSAGE}. Fix the file, then save again."
        )
        assert path.read_text(encoding="utf-8") == text
        assert app.machines == MACHINES
