"""Installed-wheel checks that check_package.py runs with ``python -I``.

Usage: ``python -I package_smoke.py ENVIRONMENT MODE [KEY]``, where MODE is
``loader``, ``app`` or ``quit`` and KEY is ``q`` or ``ctrl+q`` for ``quit``.
Every mode first checks that each loaded ``ssh_workbench`` module comes from the
installed ENVIRONMENT, never from the checkout that PYTHONPATH names.
"""

import asyncio
import importlib
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from subprocess import CompletedProcess
from threading import Event
from unittest.mock import patch

from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Footer, ListView, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.cli import main as cli_main
from ssh_workbench.config import Project, load_projects
from ssh_workbench.links import LinkResult

PACKAGE_MODULES = (
    "ssh_workbench",
    "ssh_workbench.app",
    "ssh_workbench.cli",
    "ssh_workbench.config",
    "ssh_workbench.links",
    "ssh_workbench.ssh",
)


def verify_isolation(environment: Path) -> None:
    for name in PACKAGE_MODULES:
        importlib.import_module(name)
    assert sys.flags.isolated == 1
    assert Path(sys.prefix).resolve() == environment
    for name, module in tuple(sys.modules.items()):
        if name == "ssh_workbench" or name.startswith("ssh_workbench."):
            assert Path(module.__file__).resolve().is_relative_to(environment), name


def guarded_boundaries() -> tuple[str, ...]:
    # -I leaves this folder off sys.path. It holds the shared guard list and no
    # ssh_workbench package, so the isolation check above still holds.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    shared = importlib.import_module("external_boundaries")
    if hasattr(os, "startfile"):
        return (*shared.EXTERNAL_BOUNDARIES, shared.WINDOWS_OPENER)
    return shared.EXTERNAL_BOUNDARIES


def reject_external_action(*args, **kwargs):
    raise AssertionError("The package check attempted an external action")


def reject_external_actions(guards: ExitStack) -> None:
    for boundary in guarded_boundaries():
        guards.enter_context(patch(boundary, side_effect=reject_external_action))


def check_loader() -> None:
    assert load_projects(Path("projects.toml")) == [
        Project("package-demo", "Package demo", "package-demo-host")
    ]


async def wait_until(pilot, predicate):
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def check_browser(app):
    assert app.config_supplied
    assert app.projects == (
        Project(
            "package-first",
            "Package [b]first[/b]",
            "fictional-first",
            "https://example.invalid/first?q=fictional%26query#repository",
            "https://example.invalid/first/docs#start",
        ),
        Project("package-second", "Package second", "fictional-second"),
    )
    async with app.run_test(size=(80, 24)) as pilot:
        footer = app.query_one(Footer)
        await wait_until(
            pilot,
            lambda: (
                {"connect", "repository", "documentation"}
                <= {key.action for key in footer.query("FooterKey")}
            ),
        )
        projects = app.query_one("#project-list", ListView)
        assert projects.index == 0
        name = app.query_one("#project-name", Static)
        assert "Package [b]first[/b]" in str(name.content)
        for key, url, outcome, expected in (
            (
                "r",
                app.projects[0].repository,
                LinkResult.ACCEPTED,
                "Repository browser request accepted",
            ),
            (
                "d",
                app.projects[0].documentation,
                LinkResult.FAILED,
                "Documentation browser request failed",
            ),
            (
                "r",
                app.projects[0].repository,
                OSError("private-marker ?secret=private-marker"),
                "Repository browser request failed",
            ),
            (
                "d",
                app.projects[0].documentation,
                LinkResult.ACCEPTED,
                "Documentation browser request accepted",
            ),
        ):
            await pilot.press("tab")
            focused = app.focused
            assert focused in (
                projects,
                app.query_one("#project-details", VerticalScroll),
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
                    [executable, "fictional-second"],
                    shell=False,
                    check=False,
                    stdin=None,
                    stdout=None,
                    stderr=None,
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


async def check_browser_without_connections(app):
    # Windows creates the event loop's local socket pair before these guards.
    with (
        patch("socket.socket.connect", side_effect=reject_external_action),
        patch("socket.socket.connect_ex", side_effect=reject_external_action),
    ):
        await check_browser(app)


def run_headless(app):
    asyncio.run(check_browser_without_connections(app))


def check_app() -> None:
    with ExitStack() as guards:
        reject_external_actions(guards)
        guards.enter_context(patch.object(SSHWorkbenchApp, "run", run_headless))
        assert cli_main(["--config", "browser-projects.toml"]) == 0


def check_quit(key: str) -> None:
    entered = Event()
    never_released = Event()

    def blocked_opener(url):
        assert url == "https://example.invalid/blocked"
        entered.set()
        never_released.wait()
        raise AssertionError("The blocked opener must not be released")

    async def check_quit_key():
        app = SSHWorkbenchApp(
            [
                Project(
                    "blocked-fixture",
                    "Blocked fixture",
                    "fictional-blocked",
                    "https://example.invalid/blocked",
                )
            ]
        )
        async with app.run_test(size=(60, 20)) as pilot:
            footer = app.query_one(Footer)
            async with asyncio.timeout(5):
                while "repository" not in {
                    binding.action for binding in footer.query("FooterKey")
                }:
                    await pilot.pause()
            await pilot.press("r")
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await pilot.pause()
            assert app._link_request is not None
            await pilot.press(key)
            assert not app.is_running and app.return_code == 0
        assert app._links_closed.is_set()
        assert app._link_request is None
        assert not never_released.is_set()

    async def check_quit_without_connections():
        with (
            patch("socket.socket.connect", side_effect=reject_external_action),
            patch("socket.socket.connect_ex", side_effect=reject_external_action),
        ):
            await check_quit_key()

    with ExitStack() as guards:
        reject_external_actions(guards)
        guards.enter_context(patch("ssh_workbench.app.open_link", blocked_opener))
        asyncio.run(check_quit_without_connections())
    print("Blocked opener: quit completed", flush=True)


def main() -> None:
    environment, mode, *options = sys.argv[1:]
    verify_isolation(Path(environment).resolve())
    if mode == "loader":
        check_loader()
    elif mode == "app":
        check_app()
    elif mode == "quit":
        (key,) = options
        check_quit(key)
    else:
        raise SystemExit(f"Unknown package check mode: {mode}")


if __name__ == "__main__":
    main()
