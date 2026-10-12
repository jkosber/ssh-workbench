import shutil
import subprocess
import sysconfig
from importlib.metadata import version
from pathlib import Path

import pytest

from ssh_workbench import cli as cli_module
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Project


@pytest.fixture
def started_apps(
    monkeypatch: pytest.MonkeyPatch, no_external_actions: None
) -> list[SSHWorkbenchApp]:
    """Keep the real CLI, loader and app; replace only terminal startup."""
    applications: list[SSHWorkbenchApp] = []

    def capture_run(app: SSHWorkbenchApp) -> None:
        applications.append(app)
        app.exit(return_code=0)

    monkeypatch.setattr(SSHWorkbenchApp, "run", capture_run)
    return applications


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
    assert "--config" in result.stdout
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


def test_explicit_config_loads_records_without_writing(
    tmp_path: Path, started_apps: list[SSHWorkbenchApp]
) -> None:
    path = tmp_path / "fictional-projects.toml"
    original = (
        b'schema_version = 1\n[[projects]]\nid = "second"\n'
        b'name = "Second listed"\nssh_alias = "fictional-second"\n'
        b'repository = "https://example.invalid/second"\n'
        b'documentation = "https://example.invalid/second/docs"\n'
        b'[[projects]]\nid = "first"\n'
        b'name = "First named"\nssh_alias = "fictional-first"\n'
    )
    path.write_bytes(original)

    assert cli_module.main(["--config", str(path)]) == 0

    assert len(started_apps) == 1
    app = started_apps[0]
    assert app.config_supplied
    assert app.projects == (
        Project(
            "second",
            "Second listed",
            "fictional-second",
            "https://example.invalid/second",
            "https://example.invalid/second/docs",
        ),
        Project("first", "First named", "fictional-first"),
    )
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_no_config_does_not_discover_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    started_apps: list[SSHWorkbenchApp],
) -> None:
    path = tmp_path / "projects.toml"
    path.write_text("invalid fictional configuration", encoding="utf-8")
    original_read_text = Path.read_text

    def guard_read(file: Path, *args: object, **kwargs: object) -> str:
        if file.resolve().is_relative_to(tmp_path):
            pytest.fail("No --config must not discover or read configuration")
        return original_read_text(file, *args, **kwargs)

    def unexpected_load(file: Path) -> None:
        pytest.fail("No --config must not call the project loader")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "read_text", guard_read)
    monkeypatch.setattr(cli_module, "load_projects", unexpected_load)

    assert cli_module.main([]) == 0

    assert len(started_apps) == 1
    assert not started_apps[0].config_supplied
    assert started_apps[0].projects == ()
    assert path.read_bytes() == b"invalid fictional configuration"
    assert list(tmp_path.iterdir()) == [path]


def test_explicit_empty_config_stays_distinct_from_no_config(
    tmp_path: Path, started_apps: list[SSHWorkbenchApp]
) -> None:
    path = tmp_path / "empty.toml"
    path.write_text("schema_version = 1\nprojects = []\n", encoding="utf-8")

    assert cli_module.main(["--config", str(path)]) == 0

    assert len(started_apps) == 1
    assert started_apps[0].config_supplied
    assert started_apps[0].projects == ()


@pytest.mark.parametrize(
    ("contents", "expected_error"),
    [
        ("private-marker = [", "TOML: invalid syntax"),
        (
            'schema_version = 1\n[[projects]]\nid = "private-marker"\n'
            'name = "Fictional"\nssh_alias = "--private-marker"\n',
            "projects[1].ssh_alias:",
        ),
        (b"private-marker\xff", "configuration: expected UTF-8 text"),
    ],
)
def test_invalid_config_has_useful_sanitized_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    started_apps: list[SSHWorkbenchApp],
    contents: str | bytes,
    expected_error: str,
) -> None:
    path = tmp_path / "private-marker.toml"
    original = contents.encode() if isinstance(contents, str) else contents
    path.write_bytes(original)

    with pytest.raises(SystemExit) as raised:
        cli_module.main(["--config", str(path)])

    assert raised.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert expected_error in output.err
    assert "private-marker" not in output.err
    assert str(path) not in output.err
    assert "Traceback" not in output.err
    assert not started_apps
    assert path.read_bytes() == original


def test_missing_config_is_not_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    started_apps: list[SSHWorkbenchApp],
) -> None:
    path = tmp_path / "missing-private-marker.toml"

    with pytest.raises(SystemExit) as raised:
        cli_module.main(["--config", str(path)])

    assert raised.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "configuration: file not found" in output.err
    assert "private-marker" not in output.err
    assert "Traceback" not in output.err
    assert not started_apps
    assert not path.exists()
    assert not list(tmp_path.iterdir())


def test_unreadable_config_has_sanitized_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    started_apps: list[SSHWorkbenchApp],
) -> None:
    path = tmp_path / "unreadable-private-marker.toml"
    path.write_text("schema_version = 1\nprojects = []\n", encoding="utf-8")
    original_read_text = Path.read_text

    def deny_fixture(file: Path, *args: object, **kwargs: object) -> str:
        if file == path:
            raise PermissionError("private-marker: operating system details")
        return original_read_text(file, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_fixture)

    with pytest.raises(SystemExit) as raised:
        cli_module.main(["--config", str(path)])

    assert raised.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "configuration: permission denied" in output.err
    assert "private-marker" not in output.err
    assert "Traceback" not in output.err
    assert not started_apps


@pytest.mark.parametrize("option", ["--help", "--version"])
@pytest.mark.parametrize("config_first", [False, True])
def test_help_and_version_ignore_explicit_config(
    cli: str, tmp_path: Path, option: str, config_first: bool
) -> None:
    missing = tmp_path / "private-marker.toml"
    config_args = ["--config", str(missing)]
    arguments = [*config_args, option] if config_first else [option, *config_args]

    result = subprocess.run(
        [cli, *arguments], capture_output=True, text=True, timeout=10, check=False
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert "private-marker" not in result.stdout
    assert not missing.exists()
    expected = (
        "usage: ssh-workbench"
        if option == "--help"
        else f"ssh-workbench {version('ssh-workbench')}"
    )
    assert expected in result.stdout
