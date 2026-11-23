"""Helpers shared by test modules, so no test module imports another."""

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
from textual.containers import VerticalScroll
from textual.drivers.headless_driver import HeadlessDriver
from textual.widgets import Static

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


CAPTURE_LOOK = Path(__file__).resolve().parents[1] / "scripts" / "capture_look.py"


def load_capture_look() -> ModuleType:
    spec = importlib.util.spec_from_file_location("capture_look_sizes", CAPTURE_LOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
