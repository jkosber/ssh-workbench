"""Check the installed wheel's CLI and substituted SSH/browser actions in isolation."""

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import tomllib
from pathlib import Path

ISOLATION_CHECK = textwrap.dedent(
    """\
    import sys
    from pathlib import Path

    import ssh_workbench
    import ssh_workbench.app
    import ssh_workbench.cli
    import ssh_workbench.config
    import ssh_workbench.links
    import ssh_workbench.ssh

    environment = Path(sys.argv[1]).resolve()
    assert sys.flags.isolated == 1
    assert Path(sys.prefix).resolve() == environment
    for name, module in tuple(sys.modules.items()):
        if name == "ssh_workbench" or name.startswith("ssh_workbench."):
            assert Path(module.__file__).resolve().is_relative_to(environment), name
    """
)

HEADLESS_APP_CHECK = ISOLATION_CHECK + textwrap.dedent(
    """\
    import asyncio
    import os
    from contextlib import ExitStack
    from pathlib import Path
    from subprocess import CompletedProcess
    from unittest.mock import patch

    from textual.containers import VerticalScroll
    from textual.drivers.headless_driver import HeadlessDriver
    from textual.widgets import Footer, ListView, Static

    from ssh_workbench.app import SSHWorkbenchApp
    from ssh_workbench.cli import main
    from ssh_workbench.config import Project
    from ssh_workbench.links import LinkResult

    async def wait_until(pilot, predicate):
        async with asyncio.timeout(5):
            while not predicate():
                await pilot.pause()

    async def check_browser(app):
        assert app.config_supplied
        assert app.projects == (
            Project(
                "package-first", "Package [b]first[/b]", "fictional-first",
                "https://example.invalid/first?q=fictional%26query#repository",
                "https://example.invalid/first/docs#start",
            ),
            Project("package-second", "Package second", "fictional-second"),
        )
        async with app.run_test(size=(80, 24)) as pilot:
            footer = app.query_one(Footer)
            await wait_until(pilot, lambda: {"connect", "repository", "documentation"}
                <= {key.action for key in footer.query("FooterKey")})
            projects = app.query_one("#project-list", ListView)
            assert projects.index == 0
            name = app.query_one("#project-name", Static)
            assert "Package [b]first[/b]" in str(name.content)
            for key, url, outcome, expected in (
                ("r", app.projects[0].repository, LinkResult.ACCEPTED,
                    "Repository browser request accepted"),
                ("d", app.projects[0].documentation, LinkResult.FAILED,
                    "Documentation browser request failed"),
                ("r", app.projects[0].repository,
                    OSError("private-marker ?secret=private-marker"),
                    "Repository browser request failed"),
                ("d", app.projects[0].documentation, LinkResult.ACCEPTED,
                    "Documentation browser request accepted"),
            ):
                await pilot.press("tab")
                focused = app.focused
                assert focused in (
                    projects, app.query_one("#project-details", VerticalScroll)
                )
                with patch("ssh_workbench.app.open_link") as open_link:
                    open_link.side_effect = (
                        outcome if isinstance(outcome, BaseException) else None
                    )
                    open_link.return_value = outcome
                    await pilot.press(key)
                    await wait_until(pilot, lambda: app._link_request is None)
                    open_link.assert_called_once_with(url)
                status = app.query_one("#link-status", Static)
                assert expected in str(status.content)
                assert "private-marker" not in str(status.content)
                assert "package-first" in str(status.content)
                assert not status.render().spans
                assert projects.index == 0 and app.focused is focused
            await pilot.press("down")
            assert projects.index == 1
            assert "Package second" in str(name.content)
            alias = app.query_one("#project-ssh-alias", Static)
            assert "fictional-second" in str(alias.content)
            repository = app.query_one("#project-repository", Static)
            assert "example.invalid/first" not in str(repository.content)
            with patch("ssh_workbench.app.open_link") as open_link:
                for key, kind in (("r", "Repository"), ("d", "Documentation")):
                    await pilot.press(key)
                    status = str(app.query_one("#link-status", Static).content)
                    assert kind + " link not configured" in status
                open_link.assert_not_called()
            # Use installed App.suspend with a recording driver, never a terminal
            # or a real SSH executable in this isolated package smoke check.
            lifecycle = []
            def suspend(driver):
                lifecycle.append("suspend")
            def resume(driver):
                lifecycle.append("resume")
            executable = str(Path("fictional-ssh").resolve())
            with (
                patch.object(HeadlessDriver, "can_suspend", True),
                patch.object(HeadlessDriver, "suspend_application_mode", suspend),
                patch.object(HeadlessDriver, "resume_application_mode", resume),
                patch("ssh_workbench.ssh.shutil.which", return_value=executable),
                patch("ssh_workbench.ssh.subprocess.run") as launch,
            ):
                for outcome, expected in (
                    (CompletedProcess([], 0), "status 0"),
                    (CompletedProcess([], 7), "status 7"),
                    (OSError("private-marker"), "Could not start SSH"),
                    (KeyboardInterrupt(), "SSH interrupted"),
                ):
                    launch.reset_mock()
                    launch.side_effect = (
                        outcome if isinstance(outcome, BaseException) else None
                    )
                    launch.return_value = outcome
                    await pilot.press("tab", "c")
                    launch.assert_called_once_with(
                        [executable, "fictional-second"], shell=False, check=False,
                        stdin=None, stdout=None, stderr=None,
                    )
                    assert projects.index == 1
                    assert app.focused is projects
                    status = str(app.query_one("#connection-status", Static).content)
                    assert expected in status and "private-marker" not in status
                assert lifecycle == ["suspend", "resume"] * 4
            await pilot.press("up", "down")
            assert projects.index == 1
            await pilot.press("q")
            assert not app.is_running
            assert app.return_code == 0

    def reject_external_action(*args, **kwargs):
        raise AssertionError("The package check attempted an external action")

    async def check_browser_without_connections(app):
        # Windows creates the event loop's local socket pair before these guards.
        with (
            patch("socket.socket.connect", side_effect=reject_external_action),
            patch("socket.socket.connect_ex", side_effect=reject_external_action),
        ):
            await check_browser(app)

    def run_headless(app):
        asyncio.run(check_browser_without_connections(app))

    with ExitStack() as guards:
        for boundary in (
            "socket.create_connection", "socket.getaddrinfo",
            "subprocess.Popen", "subprocess.run",
            "os.system", "webbrowser.open", "webbrowser.open_new",
            "webbrowser.open_new_tab", "asyncio.create_subprocess_exec",
            "asyncio.create_subprocess_shell",
        ):
            guards.enter_context(patch(boundary, side_effect=reject_external_action))
        if hasattr(os, "startfile"):
            guards.enter_context(
                patch("os.startfile", side_effect=reject_external_action)
            )
        guards.enter_context(patch.object(SSHWorkbenchApp, "run", run_headless))
        assert main(["--config", "browser-projects.toml"]) == 0
    """
)

BLOCKED_LINK_CHECK = ISOLATION_CHECK + textwrap.dedent(
    """\
    import asyncio
    import os
    from contextlib import ExitStack
    from threading import Event
    from unittest.mock import patch

    from textual.widgets import Footer

    from ssh_workbench.app import SSHWorkbenchApp
    from ssh_workbench.config import Project

    entered = Event()
    never_released = Event()

    def blocked_opener(url):
        assert url == "https://example.invalid/blocked"
        entered.set()
        never_released.wait()
        raise AssertionError("The blocked opener must not be released")

    def reject_external_action(*args, **kwargs):
        raise AssertionError("The package check attempted an external action")

    async def check_quit():
        app = SSHWorkbenchApp([Project(
            "blocked-fixture", "Blocked fixture", "fictional-blocked",
            "https://example.invalid/blocked",
        )])
        async with app.run_test(size=(60, 20)) as pilot:
            footer = app.query_one(Footer)
            async with asyncio.timeout(5):
                while "repository" not in {
                    key.action for key in footer.query("FooterKey")
                }:
                    await pilot.pause()
            await pilot.press("r")
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await pilot.pause()
            assert app._link_request is not None
            await pilot.press(sys.argv[2])
            assert not app.is_running and app.return_code == 0
        assert app._links_closed.is_set()
        assert app._link_request is None
        assert not never_released.is_set()

    async def check_quit_without_connections():
        with (
            patch("socket.socket.connect", side_effect=reject_external_action),
            patch("socket.socket.connect_ex", side_effect=reject_external_action),
        ):
            await check_quit()

    with ExitStack() as guards:
        for boundary in (
            "socket.create_connection", "socket.getaddrinfo",
            "subprocess.Popen", "subprocess.run", "os.system",
            "webbrowser.open", "webbrowser.open_new", "webbrowser.open_new_tab",
            "asyncio.create_subprocess_exec", "asyncio.create_subprocess_shell",
        ):
            guards.enter_context(patch(boundary, side_effect=reject_external_action))
        if hasattr(os, "startfile"):
            guards.enter_context(
                patch("os.startfile", side_effect=reject_external_action)
            )
        guards.enter_context(patch("ssh_workbench.app.open_link", blocked_opener))
        asyncio.run(check_quit_without_connections())
    print("Blocked opener: quit completed", flush=True)
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
        cli_environment = os.environ.copy()
        cli_environment.pop("PYTHONPATH", None)
        cli_environment.pop("PYTHONHOME", None)
        isolated_environment = cli_environment | {"PYTHONPATH": str(root / "src")}
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
                env=cli_environment,
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
            env=cli_environment,
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
                "-I",
                "-c",
                ISOLATION_CHECK + "\n"
                "from ssh_workbench.config import Project, load_projects; "
                "assert load_projects(Path('projects.toml')) == "
                "[Project('package-demo', 'Package demo', 'package-demo-host')]",
                str(environment),
            ],
            cwd=temporary,
            env=isolated_environment,
            check=True,
            timeout=10,
        )
        browser_fixture = temporary / "browser-projects.toml"
        original = (
            b'schema_version = 1\n[[projects]]\nid = "package-first"\n'
            b'name = "Package [b]first[/b]"\nssh_alias = "fictional-first"\n'
            b'repository = "https://example.invalid/first?q=fictional%26query#repository"\n'
            b'documentation = "https://example.invalid/first/docs#start"\n'
            b'[[projects]]\nid = "package-second"\n'
            b'name = "Package second"\nssh_alias = "fictional-second"\n'
        )
        browser_fixture.write_bytes(original)
        subprocess.run(
            [str(python), "-I", "-c", HEADLESS_APP_CHECK, str(environment)],
            cwd=temporary,
            env=isolated_environment,
            check=True,
            timeout=30,
        )
        if browser_fixture.read_bytes() != original:
            raise SystemExit("Installed wheel modified its project configuration")
        for key in ("q", "ctrl+q"):
            result = subprocess.run(
                [str(python), "-I", "-c", BLOCKED_LINK_CHECK, str(environment), key],
                cwd=temporary,
                env=isolated_environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if (
                result.stdout.strip() != "Blocked opener: quit completed"
                or result.stderr
            ):
                raise SystemExit(
                    f"Installed wheel blocked-opener quit check failed: {key}"
                )
    print(
        "Built wheel: isolated installation, help/version, configuration errors, "
        "verified installed import paths, project loader, headless selection/quit, "
        "substituted SSH/link results and blocked-opener Q/Ctrl+Q exit passed."
    )


if __name__ == "__main__":
    main()
