import os
import shutil
import subprocess
import sysconfig
from importlib.metadata import version
from pathlib import Path

import pytest

from ssh_workbench import cli as cli_module
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Link, Machine


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
    assert app.config_path == path
    assert app.machines == (
        Machine(
            "second",
            "Second listed",
            alias="fictional-second",
            links=(
                Link("Repository", "https://example.invalid/second"),
                Link("Documentation", "https://example.invalid/second/docs"),
            ),
        ),
        Machine("first", "First named", alias="fictional-first"),
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
        pytest.fail("No --config must not call the machine loader")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "read_text", guard_read)
    monkeypatch.setattr(cli_module, "load_machines", unexpected_load)

    assert cli_module.main([]) == 0

    assert len(started_apps) == 1
    assert not started_apps[0].config_supplied
    assert started_apps[0].machines == ()
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
    assert started_apps[0].machines == ()
    assert started_apps[0].config_path == path


@pytest.mark.parametrize(
    ("contents", "expected_error"),
    [
        ("private-marker = [", "TOML: invalid syntax"),
        (
            'schema_version = 1\n[[projects]]\nid = "private-marker"\n'
            'name = "Fictional"\nssh_alias = "--private-marker"\n',
            "projects[1].ssh_alias:",
        ),
        (
            'schema_version = 2\n[[machines]]\nid = "private-marker"\n'
            'name = "Fictional"\naddresses = ["--private-marker"]\n',
            "machines[1].addresses[1]:",
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


def test_explicit_config_folder_has_directory_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    started_apps: list[SSHWorkbenchApp],
) -> None:
    folder = tmp_path / "private-marker"
    folder.mkdir()

    with pytest.raises(SystemExit) as raised:
        cli_module.main(["--config", str(folder)])

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert "configuration: expected a file, got a directory" in error
    assert "permission denied" not in error
    assert "private-marker" not in error
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


VALID_DEFAULT = (
    'schema_version = 2\n[[machines]]\nid = "first"\n'
    'name = "First named"\nalias = "fictional-first"\n'
)


def use_user_config(monkeypatch: pytest.MonkeyPatch, folder: Path) -> Path:
    """Point both platforms' per-user configuration roots at one folder."""
    monkeypatch.setenv("APPDATA", str(folder))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(folder))
    return folder / "ssh-workbench" / "machines.toml"


def test_default_config_loads_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, started_apps: list[SSHWorkbenchApp]
) -> None:
    default = use_user_config(monkeypatch, tmp_path)
    default.parent.mkdir()
    default.write_text(VALID_DEFAULT, encoding="utf-8")

    assert cli_module.main([]) == 0

    assert len(started_apps) == 1
    assert started_apps[0].config_supplied
    assert started_apps[0].config_path == default
    assert started_apps[0].machines == (
        Machine("first", "First named", alias="fictional-first"),
    )
    assert default.read_text(encoding="utf-8") == VALID_DEFAULT


def test_missing_default_config_shows_no_config_screen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, started_apps: list[SSHWorkbenchApp]
) -> None:
    default = use_user_config(monkeypatch, tmp_path)

    assert cli_module.main([]) == 0

    assert len(started_apps) == 1
    assert not started_apps[0].config_supplied
    assert started_apps[0].config_path == default
    assert list(tmp_path.iterdir()) == []


def test_projects_toml_at_default_location_is_not_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, started_apps: list[SSHWorkbenchApp]
) -> None:
    default = use_user_config(monkeypatch, tmp_path)
    default.parent.mkdir()
    old_default = default.with_name("projects.toml")
    old_default.write_text(
        'schema_version = 1\n[[projects]]\nid = "old"\nname = "Old"\n'
        'ssh_alias = "fictional-old"\n',
        encoding="utf-8",
    )

    assert cli_module.main([]) == 0

    assert len(started_apps) == 1
    assert not started_apps[0].config_supplied
    assert started_apps[0].machines == ()
    assert started_apps[0].config_path == default
    assert sorted(default.parent.iterdir()) == [old_default]


def test_default_path_folder_exits_with_directory_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    started_apps: list[SSHWorkbenchApp],
) -> None:
    default = use_user_config(monkeypatch, tmp_path)
    default.mkdir(parents=True)

    with pytest.raises(SystemExit) as raised:
        cli_module.main([])

    assert raised.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "default configuration file: expected a file, got a directory" in output.err
    assert str(tmp_path) not in output.err
    assert not started_apps
    assert default.is_dir()


def test_explicit_config_ignores_default_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, started_apps: list[SSHWorkbenchApp]
) -> None:
    default = use_user_config(monkeypatch, tmp_path / "user")
    default.parent.mkdir(parents=True)
    default.write_text("private-marker = [", encoding="utf-8")
    explicit = tmp_path / "explicit.toml"
    explicit.write_text(VALID_DEFAULT, encoding="utf-8")

    assert cli_module.main(["--config", str(explicit)]) == 0

    assert len(started_apps) == 1
    assert started_apps[0].config_path == explicit
    assert started_apps[0].machines == (
        Machine("first", "First named", alias="fictional-first"),
    )


@pytest.mark.parametrize(
    ("contents", "expected_error"),
    [
        ("private-marker = [", "default configuration file: TOML: invalid syntax"),
        (
            'schema_version = 1\n[[projects]]\nid = "private-marker"\n'
            'name = "Fictional"\nssh_alias = "--private-marker"\n',
            "default configuration file: projects[1].ssh_alias:",
        ),
        (
            'schema_version = 2\n[[machines]]\nid = "private-marker"\n'
            'name = "Fictional"\nalias = "--private-marker"\n',
            "default configuration file: machines[1].alias:",
        ),
        (b"private-marker\xff", "default configuration file: expected UTF-8 text"),
    ],
)
def test_invalid_default_config_exits_with_sanitized_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    started_apps: list[SSHWorkbenchApp],
    contents: str | bytes,
    expected_error: str,
) -> None:
    default = use_user_config(monkeypatch, tmp_path)
    default.parent.mkdir()
    original = contents.encode() if isinstance(contents, str) else contents
    default.write_bytes(original)

    with pytest.raises(SystemExit) as raised:
        cli_module.main([])

    assert raised.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert expected_error in output.err
    assert "private-marker" not in output.err
    assert str(tmp_path) not in output.err
    assert "Traceback" not in output.err
    assert not started_apps
    assert default.read_bytes() == original


def test_default_config_path_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.platform", "win32")

    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert (
        cli_module.default_config_path() == tmp_path / "ssh-workbench" / "machines.toml"
    )
    monkeypatch.setenv("APPDATA", "relative")
    assert cli_module.default_config_path() is None
    monkeypatch.delenv("APPDATA")
    assert cli_module.default_config_path() is None


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_default_config_path_posix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    monkeypatch.setattr("sys.platform", platform)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    fallback = home / ".config" / "ssh-workbench" / "machines.toml"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert (
        cli_module.default_config_path()
        == tmp_path / "xdg" / "ssh-workbench" / "machines.toml"
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative")
    assert cli_module.default_config_path() == fallback
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert cli_module.default_config_path() == fallback


def test_default_config_path_without_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME")

    def no_home() -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "home", no_home)

    assert cli_module.default_config_path() is None


def test_help_shows_default_path_with_percent(cli: str, tmp_path: Path) -> None:
    folder = tmp_path / "100%"
    environment = os.environ | {
        "APPDATA": str(folder),
        "XDG_CONFIG_HOME": str(folder),
        "COLUMNS": "500",
    }

    result = subprocess.run(
        [cli, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=environment,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert str(folder / "ssh-workbench" / "machines.toml") in result.stdout


def test_help_escapes_unencodable_default_path(cli: str, tmp_path: Path) -> None:
    folder = tmp_path / "u-Ł中"
    environment = os.environ | {
        "APPDATA": str(folder),
        "XDG_CONFIG_HOME": str(folder),
        "COLUMNS": "500",
        "PYTHONIOENCODING": "cp1252",
    }

    result = subprocess.run(
        [cli, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=environment,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert r"u-\u0141\u4e2d" in result.stdout


def test_help_prints_default_path_on_its_own_line(cli: str, tmp_path: Path) -> None:
    folder = tmp_path / "a-long-fictional-folder-name-with-many-hyphens-in-it"
    environment = os.environ | {
        "APPDATA": str(folder),
        "XDG_CONFIG_HOME": str(folder),
        "COLUMNS": "60",
    }

    result = subprocess.run(
        [cli, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=environment,
    )

    assert result.returncode == 0
    lines = result.stdout.splitlines()
    heading = lines.index("Default machine file:")
    assert lines[heading + 1] == "  " + str(folder / "ssh-workbench" / "machines.toml")


@pytest.mark.parametrize("option", ["--help", "--version"])
def test_help_and_version_ignore_invalid_default_file(
    cli: str, tmp_path: Path, option: str
) -> None:
    default = tmp_path / "ssh-workbench" / "machines.toml"
    default.parent.mkdir()
    default.write_text("private-marker = [", encoding="utf-8")
    environment = os.environ | {
        "APPDATA": str(tmp_path),
        "XDG_CONFIG_HOME": str(tmp_path),
    }

    result = subprocess.run(
        [cli, option],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=environment,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert "private-marker" not in result.stdout
    expected = (
        "usage: ssh-workbench"
        if option == "--help"
        else f"ssh-workbench {version('ssh-workbench')}"
    )
    assert expected in result.stdout
    assert default.read_text(encoding="utf-8") == "private-marker = ["
