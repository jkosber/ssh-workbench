"""Run the standalone fixture's permanent guards only in owned child processes."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).with_name("link_fixture_process.py")


def run_fixture_child(tmp_path: Path, *arguments: str) -> str:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(HARNESS), str(ROOT), *arguments],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except subprocess.TimeoutExpired as error:
        # subprocess.run kills and reaps only this owned child on timeout. That
        # cleanup is a failed test, never evidence of successful interpreter exit.
        pytest.fail(f"Fixture child did not exit normally: {error}")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr, result.stderr
    return result.stdout.strip()


def test_import_does_not_install_permanent_guards(tmp_path: Path) -> None:
    assert run_fixture_child(tmp_path, "import") == "Import left boundaries unchanged"


@pytest.mark.parametrize("platform", ["win32", "linux"])
@pytest.mark.parametrize("unwind", ["return", "error", "interrupt"])
def test_delayed_dispatch_remains_guarded_after_fixture_unwinds(
    tmp_path: Path, platform: str, unwind: str
) -> None:
    assert run_fixture_child(tmp_path, "race", platform, unwind) == (
        f"Race {platform}/{unwind}: fixture dispatch=1, outer dispatch=0; "
        "guards retained=True"
    )


@pytest.mark.parametrize("platform", ["win32", "linux"])
@pytest.mark.parametrize("key", ["q", "ctrl+q"])
def test_fixture_blocked_opener_allows_interpreter_exit(
    tmp_path: Path, platform: str, key: str
) -> None:
    assert run_fixture_child(tmp_path, "blocked", platform, key) == (
        f"Blocked {platform}/{key}: fixture returned with daemon still blocked"
    )
