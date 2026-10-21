"""Interactive link check using fictional machines and substituted OS boundaries.

Run ``uv run --locked python scripts/check_links.py`` in a native terminal.
Use O from both panes, open both links of the picker case and cancel its picker
with Escape, inspect literal/long metadata, and try the missing, reported-failure
and raised-error cases. Choose the blocked request last: repeat O, change
selection and focus, then quit with Q or Ctrl+Q. The blocked stub is never
released, so quitting also checks that it cannot hold the process open.

No browser, SSH, website, SSH configuration or global settings are used. Windows
startfile and Linux GIO execution are replaced. The reported-failure case returns
a substituted result because Windows startfile has no failure return value.
The standalone entry point keeps every guard installed until process exit:
an already-started daemon may still dispatch after the TUI returns or raises.
Importing this module does not install guards.
"""

import argparse
import os
import subprocess
import sys
from threading import Event
from unittest.mock import patch

from external_boundaries import EXTERNAL_BOUNDARIES, WINDOWS_OPENER

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Link, Machine
from ssh_workbench.links import LinkResult, open_link
from ssh_workbench.ssh import SSHLaunchError

CASES = (
    ("accepted", "Accepted [b]literal[/b] request"),
    ("failed", "Reported browser request failure"),
    ("error", "Raised opener error (sanitized)"),
    ("missing", "No links (O is dimmed)"),
    ("long", "Long literal metadata " + "[b]fixture[/b] " * 18),
    ("picker", "Two links: picker, Enter and Escape"),
    ("blocked", "Blocked request: navigate, repeat, then quit"),
)
URL_CASES: dict[str, str] = {}
MACHINES: list[Machine] = []
for case, name in CASES:
    links = []
    kinds = (
        ()
        if case == "missing"
        else ("first", "second")
        if case == "picker"
        else ("only",)
    )
    for kind in kinds:
        url = (
            f"https://example.invalid/fixture/{case}/{kind}/"
            + ("long-path/" * 70 if case == "long" else "")
            + "?query=fictional%26value#section"
        )
        URL_CASES[url] = case
        links.append(Link(f"[b]{kind.title()}[/b] link", url))
    MACHINES.append(
        Machine(f"fixture-{case}", name, alias=f"fictional-{case}", links=tuple(links))
    )


def reject_external_action(*args: object, **kwargs: object) -> None:
    raise AssertionError("Unexpected external action in the link fixture")


def simulate_dispatch(url: str) -> None:
    case = URL_CASES.get(url)
    if case not in {"accepted", "error", "long", "picker", "blocked"}:
        raise AssertionError("Only known fictional fixture URLs may be dispatched")
    if case == "error":
        raise OSError("private-marker ?secret=fixture-value\x1b[31m")
    if case == "blocked":
        Event().wait()


def simulate_gio(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    assert argv[:3] == ["/fictional/gio", "open", "--"]
    assert len(argv) == 4
    assert kwargs == {
        "shell": False,
        "check": False,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "start_new_session": True,
    }
    simulate_dispatch(argv[3])
    return subprocess.CompletedProcess(argv, 0)


def open_fixture(url: str | None) -> LinkResult:
    if url is not None and URL_CASES.get(url) == "failed":
        return LinkResult.FAILED
    return open_link(url)


def install_fixture_guards() -> None:
    """Install guards for this dedicated process; never restore real boundaries."""
    # start() retains each patch without context-manager teardown. Do not stop
    # these patches, even on errors: a daemon can outlive app.run(). Waiting for
    # the intentionally blocked daemon would prevent normal interpreter exit.
    for boundary in EXTERNAL_BOUNDARIES:
        patch(boundary, side_effect=reject_external_action).start()
    if hasattr(os, "startfile"):
        patch(WINDOWS_OPENER, simulate_dispatch).start()
    if sys.platform == "linux":
        patch.dict(os.environ, {"DISPLAY": ":fixture"}).start()
        patch("ssh_workbench.links.shutil.which", return_value="/fictional/gio").start()
        patch("ssh_workbench.links.subprocess.run", simulate_gio).start()
    patch("ssh_workbench.app.open_link", open_fixture).start()
    patch(
        "ssh_workbench.app.launch_ssh",
        side_effect=SSHLaunchError("SSH is disabled in this link fixture."),
    ).start()


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    install_fixture_guards()
    app = SSHWorkbenchApp(MACHINES)
    app.run()
    return app.return_code


if __name__ == "__main__":
    raise SystemExit(main())
