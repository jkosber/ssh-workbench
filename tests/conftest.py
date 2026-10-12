import asyncio
import os
import socket
import subprocess
import webbrowser
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio


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
