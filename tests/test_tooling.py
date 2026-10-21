import ast
import importlib
import re
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest
from external_boundaries import EXTERNAL_BOUNDARIES, WINDOWS_OPENER

from ssh_workbench.sshconfig import ssh_folder

ROOT = Path(__file__).resolve().parents[1]


def test_suite_never_points_at_the_real_ssh_folder(empty_user_config: Path) -> None:
    assert ssh_folder() == empty_user_config / "ssh"
    assert ssh_folder() != Path.home() / ".ssh"


def test_shared_boundaries_are_the_expected_entry_points() -> None:
    assert EXTERNAL_BOUNDARIES == (
        "socket.create_connection",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "subprocess.run",
        "os.system",
        "webbrowser.open",
        "webbrowser.open_new",
        "webbrowser.open_new_tab",
        "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell",
    )
    assert WINDOWS_OPENER == "os.startfile"


def test_no_external_actions_rejects_every_shared_boundary(
    no_external_actions: None,
) -> None:
    for name in (*EXTERNAL_BOUNDARIES, WINDOWS_OPENER):
        owner, attribute = name.rsplit(".", 1)
        module = importlib.import_module(owner)
        if not hasattr(module, attribute):
            assert name == WINDOWS_OPENER and sys.platform != "win32"
            continue
        with pytest.raises(pytest.fail.Exception, match="attempted an external action"):
            getattr(module, attribute)()


def test_package_check_keeps_python_out_of_strings() -> None:
    source = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    embedded = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                parsed = ast.parse(textwrap.dedent(node.value))
            except SyntaxError:
                continue
            if any(
                isinstance(child, ast.Import | ast.ImportFrom)
                for child in ast.walk(parsed)
            ):
                embedded.append(node.lineno)
    assert embedded == []


def test_ci_uv_pin_matches_build_backend_range() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires = project["build-system"]["requires"]
    assert len(requires) == 1
    match = re.fullmatch(r"uv_build>=(\d+)\.(\d+)\.(\d+),<(\d+)\.(\d+)\.0", requires[0])
    assert match is not None, requires[0]
    major, minor, patch, upper_major, upper_minor = map(int, match.groups())
    assert (upper_major, upper_minor) == (major, minor + 1)
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pins = re.findall(r'^\s+version: "([^"]+)"$', workflow, re.MULTILINE)
    assert pins == [f"{major}.{minor}.{patch}"]
