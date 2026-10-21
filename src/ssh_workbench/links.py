"""Validate one URL and request a desktop browser without using terminal I/O."""

import os
import shutil
import subprocess
import sys
from enum import Enum

from ssh_workbench.config import ConfigError, validate_http_url


class LinkResult(Enum):
    ACCEPTED = "browser request accepted."
    MISSING = "link not configured. Add it to the configuration and restart."
    INVALID = "link is invalid. Check its HTTP/HTTPS URL in the configuration."
    UNAVAILABLE = (
        "browser unavailable. Use Windows or a Linux desktop with GIO "
        "and a configured browser."
    )
    FAILED = "browser request failed. Check the environment's browser setup and retry."


def open_link(url: str | None) -> LinkResult:
    """Report dispatch only, never page loading; preserve the exact accepted URL."""
    if url is None:
        return LinkResult.MISSING
    try:
        validated = validate_http_url(url)
    except ConfigError:
        return LinkResult.INVALID

    try:
        if sys.platform == "win32":
            # ShellExecute receives the URL as data, without a command or flags.
            os.startfile(validated)
            return LinkResult.ACCEPTED
        if sys.platform == "linux" and (
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        ):
            executable = shutil.which("gio")
            if executable is not None:
                # GIO uses desktop associations. Avoid webbrowser/xdg-open's
                # text-browser fallback; no child may inherit the live TUI.
                result = subprocess.run(
                    [executable, "open", "--", validated],
                    shell=False,
                    check=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return (
                    LinkResult.ACCEPTED if result.returncode == 0 else LinkResult.FAILED
                )
    except OSError, ValueError, RuntimeError:
        return LinkResult.FAILED
    return LinkResult.UNAVAILABLE
