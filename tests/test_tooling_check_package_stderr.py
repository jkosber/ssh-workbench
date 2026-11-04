"""scripts/check_package.py with every child replaced by a stand-in at subprocess.run.

The stand-in answers as the real uv, CLI and package_smoke.py children do, from a
fictional checkout that holds a copy of the script, a pyproject and an empty
wheel. One child can add a stderr marker while it still exits 0: the stand-in
returns that text when the script captures stderr and writes it to the parent's
stderr when it does not, as subprocess.run would. Nothing is built, installed
or run.
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
MARKER = "DeprecationWarning: fictional stderr marker from a stand-in child"
SMOKE_STDOUT = {
    "quit": "Blocked opener: quit completed\n",
    "save": "Saved machine file: created and loaded back\n",
}

type Run = Callable[..., subprocess.CompletedProcess[str]]


def load_check_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load a copy of the script from a fictional checkout with a built wheel."""
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    (project / "dist").mkdir()
    (project / "pyproject.toml").write_text(
        f'[project]\nname = "ssh-workbench"\nversion = "{VERSION}"\n', "utf-8"
    )
    (project / "dist" / f"ssh_workbench-{VERSION}-py3-none-any.whl").write_bytes(b"")
    script = project / "scripts" / "check_package.py"
    shutil.copyfile(CHECK_PACKAGE, script)
    # A folder made with tempfile stays under tmp_path.
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    monkeypatch.setattr(shutil, "which", lambda name: UV if name == "uv" else None)
    spec = importlib.util.spec_from_file_location("check_package_under_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stand_in(children: list[tuple[str, ...]], noisy: tuple[str, ...] | None) -> Run:
    """Answer each child; the package_smoke.py child named by `noisy` adds MARKER."""

    def run(
        command: Sequence[object], **options: object
    ) -> subprocess.CompletedProcess[str]:
        words = [str(word) for word in command]
        returncode, stdout, stderr = 0, "", ""
        if words[0] == UV:
            pass
        elif Path(words[0]).stem == "ssh-workbench":
            if words[1:] == ["--help"]:
                stdout = "usage: ssh-workbench [-h] [--version] [--config PATH]\n"
            elif words[1:] == ["--version"]:
                stdout = f"ssh-workbench {VERSION}\n"
            elif words[1] == "--config":
                returncode = 2
                stderr = "ssh-workbench: configuration: file not found\n"
            else:
                pytest.fail(f"Unexpected CLI child: {words[1:]}")
        elif len(words) > 2 and Path(words[2]).name == "package_smoke.py":
            child = tuple(words[4:])
            children.append(child)
            stdout = SMOKE_STDOUT.get(child[0], "")
            if child == noisy:
                stderr = MARKER + "\n"
        else:
            pytest.fail(f"Unexpected child: {words}")
        both = options.get("capture_output") is True
        out = stdout if both or options.get("stdout") == subprocess.PIPE else None
        err = stderr if both or options.get("stderr") == subprocess.PIPE else None
        # A stream neither captured nor redirected is the parent's own.
        if out is None and options.get("stdout") is None:
            sys.stdout.write(stdout)
        if err is None and options.get("stderr") is None:
            sys.stderr.write(stderr)
        if options.get("check") and returncode:
            raise subprocess.CalledProcessError(returncode, command, out, err)
        return subprocess.CompletedProcess(command, returncode, out, err)

    return run


@pytest.mark.usefixtures("no_external_actions")
def test_package_check_passes_when_every_stand_in_child_is_quiet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    check_package = load_check_package(tmp_path, monkeypatch)
    children: list[tuple[str, ...]] = []
    monkeypatch.setattr(subprocess, "run", stand_in(children, None))

    check_package.main()

    assert children == [
        ("loader",),
        ("app",),
        ("quit", "q"),
        ("quit", "ctrl+q"),
        ("save",),
    ]
    output = capsys.readouterr()
    assert output.out.endswith("Q/Ctrl+Q exit and a first save passed.\n")
    assert output.err == ""


@pytest.mark.usefixtures("no_external_actions")
@pytest.mark.parametrize(
    ("noisy", "prefix"),
    [
        pytest.param(("loader",), "Installed wheel loader check failed", id="loader"),
        pytest.param(("app",), "Installed wheel app check failed", id="app"),
        pytest.param(("save",), "Installed wheel save check failed", id="save"),
    ],
)
def test_package_check_fails_with_the_stderr_of_a_child_that_exits_0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    noisy: tuple[str, ...],
    prefix: str,
) -> None:
    check_package = load_check_package(tmp_path, monkeypatch)
    children: list[tuple[str, ...]] = []
    monkeypatch.setattr(subprocess, "run", stand_in(children, noisy))

    with pytest.raises(SystemExit) as failure:
        check_package.main()

    message = str(failure.value)
    assert message.startswith(prefix), message
    assert MARKER in message, message
    assert children[-1] == noisy


@pytest.mark.usefixtures("no_external_actions")
def test_package_check_fails_when_a_quit_child_that_exits_0_writes_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check_package = load_check_package(tmp_path, monkeypatch)
    children: list[tuple[str, ...]] = []
    monkeypatch.setattr(subprocess, "run", stand_in(children, ("quit", "q")))

    with pytest.raises(SystemExit) as failure:
        check_package.main()

    message = str(failure.value)
    assert message.startswith("Installed wheel blocked-opener quit check failed: q"), (
        message
    )
    assert children == [("loader",), ("app",), ("quit", "q")]
