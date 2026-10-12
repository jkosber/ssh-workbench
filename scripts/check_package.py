"""Check the built wheel's CLI, loader and headless browser outside the checkout."""

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import tomllib
from pathlib import Path

HEADLESS_BROWSER_CHECK = textwrap.dedent(
    """\
    import asyncio
    from contextlib import ExitStack
    from unittest.mock import patch

    from textual.widgets import ListView, Static

    from ssh_workbench.app import SSHWorkbenchApp
    from ssh_workbench.cli import main
    from ssh_workbench.config import Project

    async def check_browser(app):
        assert app.config_supplied
        assert app.projects == (
            Project(
                "package-first", "Package [b]first[/b]", "fictional-first",
                "https://example.invalid/first",
                "https://example.invalid/first/docs",
            ),
            Project("package-second", "Package second", "fictional-second"),
        )
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            projects = app.query_one("#project-list", ListView)
            assert projects.index == 0
            name = app.query_one("#project-name", Static)
            assert "Package [b]first[/b]" in str(name.content)
            await pilot.press("down")
            assert projects.index == 1
            assert "Package second" in str(name.content)
            alias = app.query_one("#project-ssh-alias", Static)
            assert "fictional-second" in str(alias.content)
            repository = app.query_one("#project-repository", Static)
            assert "example.invalid/first" not in str(repository.content)
            await pilot.press("q")
            assert not app.is_running
            assert app.return_code == 0

    def run_headless(app):
        asyncio.run(check_browser(app))

    def reject_external_action(*args, **kwargs):
        raise AssertionError("The read-only browser attempted an external action")

    with ExitStack() as guards:
        for boundary in (
            "socket.create_connection", "subprocess.Popen", "subprocess.run",
            "os.system", "webbrowser.open", "webbrowser.open_new",
            "webbrowser.open_new_tab", "asyncio.create_subprocess_exec",
            "asyncio.create_subprocess_shell",
        ):
            guards.enter_context(patch(boundary, side_effect=reject_external_action))
        guards.enter_context(patch.object(SSHWorkbenchApp, "run", run_headless))
        assert main(["--config", "browser-projects.toml"]) == 0
    """
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    wheel = root / "dist" / f"ssh_workbench-{version}-py3-none-any.whl"
    if not wheel.is_file():
        raise SystemExit("Build the wheel first with: uv build")
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv must be available on PATH.")

    with tempfile.TemporaryDirectory(prefix="ssh-workbench-package-") as directory:
        temporary = Path(directory)
        environment = temporary / "venv"
        requirements = temporary / "requirements.txt"
        subprocess.run(
            [uv, "venv", "--python", sys.executable, str(environment)], check=True
        )
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        cli = scripts / ("ssh-workbench.exe" if os.name == "nt" else "ssh-workbench")
        subprocess.run(
            [
                uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [uv, "pip", "sync", "--python", str(python), str(requirements)],
            check=True,
        )
        subprocess.run(
            [uv, "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
            check=True,
        )
        for option, expected in [
            ("--help", "usage: ssh-workbench"),
            ("--version", f"ssh-workbench {version}"),
        ]:
            result = subprocess.run(
                [str(cli), option],
                cwd=temporary,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if expected not in result.stdout or result.stderr:
                raise SystemExit(f"Installed wheel CLI check failed: {option}")
        missing = temporary / "missing-private-marker.toml"
        result = subprocess.run(
            [str(cli), "--config", str(missing)],
            cwd=temporary,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if (
            result.returncode != 2
            or result.stdout
            or "configuration: file not found" not in result.stderr
            or "private-marker" in result.stderr
            or "Traceback" in result.stderr
            or missing.exists()
        ):
            raise SystemExit("Installed wheel CLI check failed: missing configuration")
        fixture = temporary / "projects.toml"
        fixture.write_text(
            'schema_version = 1\n[[projects]]\nid = "package-demo"\n'
            'name = "Package demo"\nssh_alias = "package-demo-host"\n',
            encoding="utf-8",
        )
        subprocess.run(
            [
                str(python),
                "-c",
                "from pathlib import Path; "
                "from ssh_workbench.config import Project, load_projects; "
                "assert load_projects(Path('projects.toml')) == "
                "[Project('package-demo', 'Package demo', 'package-demo-host')]",
            ],
            cwd=temporary,
            check=True,
            timeout=10,
        )
        browser_fixture = temporary / "browser-projects.toml"
        original = (
            b'schema_version = 1\n[[projects]]\nid = "package-first"\n'
            b'name = "Package [b]first[/b]"\nssh_alias = "fictional-first"\n'
            b'repository = "https://example.invalid/first"\n'
            b'documentation = "https://example.invalid/first/docs"\n'
            b'[[projects]]\nid = "package-second"\n'
            b'name = "Package second"\nssh_alias = "fictional-second"\n'
        )
        browser_fixture.write_bytes(original)
        subprocess.run(
            [str(python), "-c", HEADLESS_BROWSER_CHECK],
            cwd=temporary,
            check=True,
            timeout=30,
        )
        if browser_fixture.read_bytes() != original:
            raise SystemExit("Installed wheel modified its project configuration")
    print(
        "Built wheel: isolated installation, help/version, configuration errors, "
        "project loader and headless project selection/quit passed."
    )


if __name__ == "__main__":
    main()
