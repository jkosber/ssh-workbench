"""O finds GIO only on absolute PATH entries, never in the working folder."""

import os
import shlex
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from ssh_workbench import links
from ssh_workbench.links import LinkResult, open_link

URL = "https://example.com/"
# A "." or empty PATH entry makes shutil.which search the working folder.
RELATIVE_ENTRIES = pytest.mark.parametrize(
    "relative_entry", [os.curdir, ""], ids=["dot", "empty"]
)


def linux_desktop(monkeypatch: pytest.MonkeyPatch, *path_entries: str) -> None:
    # The global platform changes, as in test_links.py, so shutil.which takes
    # its POSIX branch on Windows too and finds these extensionless files.
    monkeypatch.setattr(links.sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":fixture")
    monkeypatch.setenv("PATH", os.pathsep.join(path_entries))


def recording_gio(directory: Path, recorder: Path) -> Path:
    # Shell builtins only: the PATH under test holds no external tools.
    directory.mkdir()
    gio = directory / "gio"
    gio.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$0" "$@" > {shlex.quote(str(recorder))}\n'
    )
    gio.chmod(0o755)
    return gio


def fictional_gio(directory: Path) -> Path:
    # Never executed: subprocess.run is substituted in every caller.
    directory.mkdir()
    gio = directory / "gio"
    gio.write_bytes(b"")
    gio.chmod(0o755)
    return gio


@RELATIVE_ENTRIES
def test_gio_found_only_through_a_relative_path_entry_is_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative_entry: str
) -> None:
    # subprocess.run stays real, so a gio run from the working folder leaves
    # its argv in the recorder. Windows cannot start the extensionless script.
    recorder = tmp_path / "gio-argv.txt"
    planted = recording_gio(tmp_path / "launch", recorder)
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.chdir(planted.parent)
    linux_desktop(monkeypatch, relative_entry, str(empty))

    result = open_link(URL)

    assert not recorder.exists(), recorder.read_text()
    assert result is LinkResult.UNAVAILABLE


@pytest.mark.usefixtures("no_external_actions")
def test_gio_on_an_absolute_path_entry_runs_by_that_absolute_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    installed = fictional_gio(tmp_path / "bin")
    linux_desktop(monkeypatch, str(installed.parent))
    launch = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(links.subprocess, "run", launch)

    assert open_link(URL) is LinkResult.ACCEPTED

    launch.assert_called_once()
    assert launch.call_args.args == ([str(installed), "open", "--", URL],)
    assert Path(launch.call_args.args[0][0]).is_absolute()


@pytest.mark.usefixtures("no_external_actions")
@RELATIVE_ENTRIES
def test_gio_in_the_working_folder_is_skipped_for_one_on_an_absolute_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative_entry: str
) -> None:
    planted = fictional_gio(tmp_path / "launch")
    installed = fictional_gio(tmp_path / "bin")
    monkeypatch.chdir(planted.parent)
    linux_desktop(monkeypatch, relative_entry, str(installed.parent))
    launch = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(links.subprocess, "run", launch)

    assert open_link(URL) is LinkResult.ACCEPTED

    launch.assert_called_once()
    assert launch.call_args.args == ([str(installed), "open", "--", URL],)
