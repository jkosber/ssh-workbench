"""Render the app at each size of the size matrix to SVG, headless.

Run ``uv run --locked python scripts/capture_look.py``. The SVGs go to the
ignored ``.local/captures/look/`` in the repository, one ``look-WxH.svg`` per
size; ``--out DIR`` names another folder and ``--sizes 80x24,40x16`` other
sizes. No PNG is made: converting one would start another program.

Each capture shows fictional machines once their status checks finish, so
Checking never shows. A fake checker answers instead of SSH and the network,
and a temporary machine file with a remembered alias that is gone from the
SSH config gives every other state the header names.

The entry point points the user folders and the SSH folder at a temporary
folder and rejects every process, socket and browser entry point until the
process exits. Importing this module does neither: a caller of capture()
isolates the environment itself, as the test suite does.
"""

import argparse
import asyncio
import os
import platform
import re
import tempfile
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import patch

from external_boundaries import EXTERNAL_BOUNDARIES, WINDOWS_OPENER
from textual.pilot import Pilot

from ssh_workbench.aliases import AliasMemory, AliasRecord, format_state, state_path
from ssh_workbench.app import SSHWorkbenchApp, StatusSymbol
from ssh_workbench.config import Link, Machine, format_machines
from ssh_workbench.status import AliasTarget, State

ROOT = Path(__file__).resolve().parents[1]
# The size matrix, as (columns, rows). tests/test_look.py checks the layout at
# each of these sizes.
SIZES: tuple[tuple[int, int], ...] = (
    (80, 24),
    (120, 30),
    (100, 30),
    (120, 40),
    (160, 50),
    (200, 60),
    (60, 20),
    (50, 24),
    (40, 16),
    (80, 50),
    (120, 18),
)
MACHINES = (
    Machine(
        "studio",
        "Studio",
        user="studio",
        addresses=("192.0.2.30", "192.0.2.40"),
        port=2222,
        key="~/.ssh/id_ed25519_studio",
        links=(
            Link("Dashboard", "https://192.0.2.40:8006"),
            Link("Docs", "https://docs.example.invalid/studio"),
        ),
    ),
    Machine("garden", "Garden", alias="garden-host"),
    Machine("lab", "Lab", addresses=("192.0.2.50",)),
    Machine("hop", "Hop", alias="hop-host"),
    Machine("archive", "Archive", alias="archive-host"),
)
TARGETS = {
    "garden-host": AliasTarget("192.0.2.10", 22, proxied=False),
    "hop-host": AliasTarget("192.0.2.11", 22, proxied=True),
}
# archive-host was a Host name at the last check and is gone now.
REMEMBERED = AliasMemory(
    ("archive-host",), {"archive-host": AliasRecord("192.0.2.60", "archive", 22)}
)


class FakeChecker:
    """Studio (its second address) and Garden online, Lab offline, Hop proxied."""

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return TARGETS.get(alias)

    def port_open(self, host: str, port: int) -> bool:
        return host in ("192.0.2.10", "192.0.2.40")


async def settled(app: SSHWorkbenchApp, pilot: Pilot[None]) -> None:
    """Wait for every status check and for the footer they redraw."""

    def done() -> bool:
        return State.CHECKING not in [
            symbol.state for symbol in app.query(StatusSymbol)
        ] and all(key.region.width for key in app.query("FooterKey"))

    async with asyncio.timeout(10):
        while not done():
            await pilot.pause()
    # Under 60 columns the first layout pass keeps the side-by-side panes.
    await pilot.pause()


async def capture(
    out_dir: Path, sizes: Sequence[tuple[int, int]] = SIZES
) -> list[Path]:
    """Write ``look-WxH.svg`` into `out_dir` for each size; return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    text = format_machines(MACHINES)
    computer = platform.node()
    paths = []
    for width, height in sizes:
        # A new machine file and state each time: the app rewrites the state.
        with tempfile.TemporaryDirectory(prefix="ssh-workbench-look-") as folder:
            machine_file = Path(folder) / "machines.toml"
            machine_file.write_text(text, encoding="utf-8")
            state_path(machine_file, computer).write_text(
                format_state(REMEMBERED, computer), encoding="utf-8"
            )
            app = SSHWorkbenchApp(
                MACHINES,
                config_path=machine_file,
                file_text=text,
                checker=FakeChecker(),
            )
            async with app.run_test(size=(width, height)) as pilot:
                await settled(app, pilot)
                svg = app.export_screenshot()
        path = out_dir / f"look-{width}x{height}.svg"
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
    return paths


def parse_sizes(text: str) -> tuple[tuple[int, int], ...]:
    """``80x24,40x16`` as ``((80, 24), (40, 16))``."""
    sizes = []
    for part in text.split(","):
        match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", part.strip())
        if match is None:
            raise argparse.ArgumentTypeError(f"not a size like 80x24: {part!r}")
        sizes.append((int(match[1]), int(match[2])))
    return tuple(sizes)


def reject_external_action(*args: object, **kwargs: object) -> None:
    raise AssertionError("Unexpected external action in the look capture")


def install_guards() -> None:
    """Reject every process, socket and browser entry point until process exit."""
    for boundary in EXTERNAL_BOUNDARIES:
        patch(boundary, side_effect=reject_external_action).start()
    if hasattr(os, "startfile"):
        patch(WINDOWS_OPENER, side_effect=reject_external_action).start()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / ".local" / "captures" / "look",
        help="folder for the SVGs (default: .local/captures/look in the repository)",
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=SIZES,
        help="comma-separated WIDTHxHEIGHT sizes (default: the size matrix)",
    )
    args = parser.parse_args(argv)
    install_guards()
    with tempfile.TemporaryDirectory(prefix="ssh-workbench-look-") as folder:
        environment = {
            "APPDATA": folder,
            "XDG_CONFIG_HOME": folder,
            "SSH_WORKBENCH_SSH_DIR": str(Path(folder) / "ssh"),
        }
        with patch.dict(os.environ, environment):
            # Textual greys the first app's colors when NO_COLOR is set.
            os.environ.pop("NO_COLOR", None)
            paths = asyncio.run(capture(args.out, args.sizes))
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
