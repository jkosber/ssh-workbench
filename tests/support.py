"""Helpers shared by test modules, so no test module imports another."""

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
from textual.color import Color
from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Static
from textual.widgets._footer import FooterKey

from ssh_workbench import app as app_module
from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Link, Machine

TWO_MACHINES = (
    Machine(
        "garden-demo",
        "Garden demo",
        alias="garden-demo-host",
        links=(
            Link("Repository", "https://example.com/garden.git"),
            Link("Documentation", "https://example.com/garden/docs"),
        ),
    ),
    Machine(
        "studio-box",
        "Studio box",
        user="studio",
        addresses=("studio.example", "192.0.2.40"),
        port=2222,
        key="~/.ssh/id_ed25519_studio",
    ),
)


def empty_lines(app: SSHWorkbenchApp) -> list[Static]:
    """The empty screen's lines, one Static each."""
    return list(app.query_one("#empty-state", VerticalScroll).query_children(Static))


def empty_text(app: SSHWorkbenchApp) -> str:
    return "\n".join(str(line.content) for line in empty_lines(app))


def handoff(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """A terminal that can be handed off and an SSH that exits with 0."""
    monkeypatch.setattr(HeadlessDriver, "can_suspend", property(lambda self: True))
    monkeypatch.setattr(HeadlessDriver, "suspend_application_mode", lambda self: None)
    monkeypatch.setattr(HeadlessDriver, "resume_application_mode", lambda self: None)
    launch = Mock(return_value=0)
    monkeypatch.setattr(app_module, "launch_ssh", launch)
    return launch


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


def footer_ready(app) -> bool:
    """The footer has its keys and each is laid out. The footer gets them
    after the first screen update, and until it is laid out with them the
    panes above it are taller."""
    keys = list(app.query(FooterKey))
    return bool(keys) and all(key.region.width for key in keys)


# push_screen makes a screen current before it has composed its widgets.
def showing(app, kind) -> bool:
    return isinstance(app.screen, kind) and app.screen.is_mounted


def luminance(color: Color) -> float:
    """WCAG 2 relative luminance."""

    def linear(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * linear(color.r) + 0.7152 * linear(color.g) + 0.0722 * linear(color.b)
    )


def contrast(foreground: Color, background: Color) -> float:
    """The WCAG 2 contrast ratio; a translucent foreground is first composited
    onto the background."""
    if foreground.a < 1:
        foreground = background.tint(foreground)
    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


CAPTURE_LOOK = Path(__file__).resolve().parents[1] / "scripts" / "capture_look.py"


def load_capture_look() -> ModuleType:
    spec = importlib.util.spec_from_file_location("capture_look_sizes", CAPTURE_LOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
