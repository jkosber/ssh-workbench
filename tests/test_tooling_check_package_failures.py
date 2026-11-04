"""scripts/check_package.py when one stand-in child fails or warns.

Every child is replaced at subprocess.run by a stand-in that answers as the real
uv, CLI and package_smoke.py children do, from a fictional checkout that holds a
copy of the script, a pyproject and an empty wheel. The one child a case names
returns that case's exit status and stderr; like subprocess.run, the stand-in
raises CalledProcessError for a non-zero status when the script passes
check=True. Nothing is built, installed or run.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK_PACKAGE = ROOT / "scripts" / "check_package.py"
VERSION = "0.0.1"
UV = "fictional-uv"
CLI = "ssh-workbench"
SMOKE = "package_smoke.py"
FAILURE_STATUS = 3
MARKER = "AssertionError: fictional failure marker from a stand-in child"
SYNTAX_WARNING = (
    r'fictional/ssh_workbench/cli.py:1: SyntaxWarning: "\d" is an invalid escape '
    r"sequence. Such sequences will not work in the future. "
    r'Did you mean "\\d"? A raw string is also an option.'
)
CLI_STDOUT = {
    "--help": "usage: ssh-workbench [-h] [--version] [--config PATH]\n",
    "--version": f"ssh-workbench {VERSION}\n",
}
SMOKE_STDOUT = {
    "quit": "Blocked opener: quit completed\n",
    "save": "Saved machine file: created and loaded back\n",
}
CHECKS = [
    pytest.param(
        (CLI, "--help"), "Installed wheel CLI check failed: --help", id="help"
    ),
    pytest.param((SMOKE, "app"), "Installed wheel app check failed:", id="app"),
    pytest.param(
        (SMOKE, "quit", "q"),
        "Installed wheel blocked-opener quit check failed: q",
        id="quit",
    ),
    pytest.param((SMOKE, "save"), "Installed wheel save check failed", id="save"),
]

type Run = Callable[..., subprocess.CompletedProcess[str]]


def load_check_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load a copy of the script from a fictional checkout with a built wheel."""
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "dist").mkdir()
    (checkout / "pyproject.toml").write_text(
        f'[project]\nname = "ssh-workbench"\nversion = "{VERSION}"\n', "utf-8"
    )
    (checkout / "dist" / f"ssh_workbench-{VERSION}-py3-none-any.whl").write_bytes(b"")
    script = checkout / "scripts" / "check_package.py"
    shutil.copyfile(CHECK_PACKAGE, script)
    # The script's temporary folder is made with tempfile, so it lands here.
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    monkeypatch.setattr(shutil, "which", lambda name: UV if name == "uv" else None)
    spec = importlib.util.spec_from_file_location(
        "check_package_failures_under_test", script
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stand_in(
    children: list[tuple[str, ...]],
    failing: tuple[str, ...],
    status: int,
    stderr: str,
) -> Run:
    """Answer every child; the CLI or smoke child named by `failing` returns
    `status` and `stderr` with its usual stdout."""

    def run(
        command: Sequence[object], **options: object
    ) -> subprocess.CompletedProcess[str]:
        words = [str(word) for word in command]
        child: tuple[str, ...] | None = None
        returncode, stdout, error = 0, "", ""
        if words[0] == UV:
            pass
        elif Path(words[0]).stem == CLI:
            child = (CLI, *words[1:])
            if words[1:] == ["--help"] or words[1:] == ["--version"]:
                stdout = CLI_STDOUT[words[1]]
            elif words[1] == "--config":
                returncode = 2
                error = "ssh-workbench: configuration: file not found\n"
            else:
                pytest.fail(f"Unexpected CLI child: {words[1:]}")
        elif len(words) > 4 and Path(words[2]).name == SMOKE:
            child = (SMOKE, *words[4:])
            stdout = SMOKE_STDOUT.get(words[4], "")
        else:
            pytest.fail(f"Unexpected child: {words}")
        if child is not None:
            children.append(child)
        if child == failing:
            returncode, error = status, stderr
        captured = options.get("capture_output") is True
        out = stdout if captured or options.get("stdout") == subprocess.PIPE else None
        err = error if captured or options.get("stderr") == subprocess.PIPE else None
        # A stream the script neither captures nor redirects is its own.
        if out is None and options.get("stdout") is None:
            sys.stdout.write(stdout)
        if err is None and options.get("stderr") is None:
            sys.stderr.write(error)
        if options.get("check") and returncode:
            raise subprocess.CalledProcessError(returncode, command, out, err)
        return subprocess.CompletedProcess(command, returncode, out, err)

    return run


@pytest.mark.usefixtures("no_external_actions")
@pytest.mark.parametrize(("failing", "prefix"), CHECKS)
def test_package_check_fails_with_the_exit_status_and_stderr_of_a_failed_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing: tuple[str, ...],
    prefix: str,
) -> None:
    check_package = load_check_package(tmp_path, monkeypatch)
    children: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        subprocess, "run", stand_in(children, failing, FAILURE_STATUS, MARKER + "\n")
    )

    with pytest.raises(SystemExit) as failure:
        check_package.main()

    message = str(failure.value)
    assert message.startswith(prefix), message
    assert f"exit status {FAILURE_STATUS}" in message, message
    assert MARKER in message, message
    assert children[-1] == failing


@pytest.mark.usefixtures("no_external_actions")
@pytest.mark.parametrize(("failing", "prefix"), CHECKS)
def test_package_check_fails_with_the_exit_status_of_a_child_that_fails_silently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing: tuple[str, ...],
    prefix: str,
) -> None:
    # The child prints its usual stdout and nothing on stderr, so only its
    # exit status shows that it failed.
    check_package = load_check_package(tmp_path, monkeypatch)
    children: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        subprocess, "run", stand_in(children, failing, FAILURE_STATUS, "")
    )

    with pytest.raises(SystemExit) as failure:
        check_package.main()

    message = str(failure.value)
    assert message.startswith(prefix), message
    assert f"exit status {FAILURE_STATUS}" in message, message
    assert children[-1] == failing


@pytest.mark.usefixtures("no_external_actions")
def test_package_check_fails_with_the_syntax_warning_of_a_help_child_that_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check_package = load_check_package(tmp_path, monkeypatch)
    children: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        subprocess,
        "run",
        stand_in(children, (CLI, "--help"), 0, SYNTAX_WARNING + "\n"),
    )

    with pytest.raises(SystemExit) as failure:
        check_package.main()

    message = str(failure.value)
    assert message.startswith("Installed wheel CLI check failed: --help"), message
    assert SYNTAX_WARNING in message, message
    assert children == [(CLI, "--help")]
