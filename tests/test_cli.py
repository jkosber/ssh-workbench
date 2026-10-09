import shutil
import subprocess
import sysconfig
from importlib.metadata import version

import pytest


@pytest.fixture
def cli() -> str:
    entry_point = shutil.which("ssh-workbench", path=sysconfig.get_path("scripts"))
    assert entry_point is not None, "Install the package with uv sync --locked first."
    return entry_point


def test_help(cli: str) -> None:
    result = subprocess.run(
        [cli, "--help"], capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 0
    assert "usage: ssh-workbench" in result.stdout
    assert "--version" in result.stdout
    assert "development scaffold" in result.stdout
    assert result.stderr == ""


def test_version_matches_package_metadata(cli: str) -> None:
    result = subprocess.run(
        [cli, "--version"], capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"ssh-workbench {version('ssh-workbench')}"
    assert result.stderr == ""


def test_unknown_option_is_rejected(cli: str) -> None:
    result = subprocess.run(
        [cli, "--connect"], capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --connect" in result.stderr
