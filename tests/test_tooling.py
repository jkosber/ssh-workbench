import importlib
import sys

import pytest
from external_boundaries import EXTERNAL_BOUNDARIES, WINDOWS_OPENER


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
