import asyncio
import os
import socket
import subprocess
import webbrowser
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def empty_user_config(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("no-user-config")


@pytest.fixture(autouse=True)
def isolated_user_config(
    monkeypatch: pytest.MonkeyPatch, empty_user_config: Path
) -> None:
    """Keep every test, and the processes it starts, away from the real user file."""
    monkeypatch.setenv("APPDATA", str(empty_user_config))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(empty_user_config))


@pytest.fixture
def no_external_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail common execution boundaries during in-process application tests."""

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("The project browser attempted an external action")

    for target, names in (
        (socket, ("create_connection", "getaddrinfo")),
        (subprocess, ("Popen",)),
        (asyncio, ("create_subprocess_exec", "create_subprocess_shell")),
        (os, ("system", "startfile")),
        (webbrowser, ("open", "open_new", "open_new_tab")),
    ):
        for name in names:
            if hasattr(target, name):
                monkeypatch.setattr(target, name, unexpected)


@pytest_asyncio.fixture
async def no_app_connections(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    # Windows creates a local socket pair when starting the event loop.
    # Install the low-level guard only after that loop exists, before the app runs.
    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("The project browser attempted a socket connection")

    with monkeypatch.context() as guard:
        guard.setattr(socket.socket, "connect", unexpected)
        guard.setattr(socket.socket, "connect_ex", unexpected)
        yield
