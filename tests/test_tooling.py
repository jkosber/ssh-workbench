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


def test_package_check_precompiles_dependencies_but_not_the_wheel() -> None:
    # uv writes no .pyc files unless asked, so the first child to import
    # Textual compiled every dependency inside its 10 s timeout, which a cold
    # Windows runner exceeded (PR #23). The wheel stays uncompiled: compiling
    # hides a SyntaxWarning in Workbench's own code from the stderr checks.
    source = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    compiles = {"sync": set(), "install": set()}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.List):
            words = [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            if words[:2] in (["pip", "sync"], ["pip", "install"]):
                compiles[words[1]].add("--compile-bytecode" in words)
    assert compiles == {"sync": {True}, "install": {False}}


def test_package_check_fails_when_the_loader_child_writes_to_stderr() -> None:
    # The loader child is the first to import the modules --help does not
    # load, and it writes their bytecode, so a SyntaxWarning in one of them,
    # such as app, reaches only that child's stderr (PR #35).
    source = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    loader = {}
    for node in ast.walk(ast.parse(source)):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for statement, following in zip(body, [*body[1:], None], strict=True):
            call = getattr(statement, "value", None)
            if not (
                isinstance(call, ast.Call)
                and call.args
                and isinstance(call.args[0], ast.List)
                and any(
                    isinstance(item, ast.Constant) and item.value == "loader"
                    for item in call.args[0].elts
                )
            ):
                continue
            keywords = {
                keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords
            }
            result = (
                ast.unparse(statement.targets[0])
                if isinstance(statement, ast.Assign)
                else None
            )
            loader["stderr captured"] = (
                keywords.get("capture_output") == "True"
                or keywords.get("stderr") == "subprocess.PIPE"
            )
            loader["stderr checked"] = (
                isinstance(following, ast.If)
                and f"{result}.stderr"
                in {ast.unparse(part) for part in ast.walk(following.test)}
                and isinstance(following.body[0], ast.Raise)
            )
    assert loader == {"stderr captured": True, "stderr checked": True}


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


def test_ci_runs_once_for_a_push_to_a_pull_request() -> None:
    # A branch push runs only as its pull request; `main` and version tags,
    # which the release checklist checks, run as pushes.
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    triggers = re.search(r"^on:\n((?:[ \t]+.*\n)+)", workflow, re.MULTILINE)
    assert triggers is not None, "on: should list each event with its filters"
    assert triggers.group(1).splitlines() == [
        "  push:",
        "    branches: [main]",
        '    tags: ["v*"]',
        "  pull_request:",
    ]
