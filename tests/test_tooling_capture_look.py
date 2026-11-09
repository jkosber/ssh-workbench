"""scripts/capture_look.py renders fictional machines to SVG, headless.

The suite's guards stand in for the ones the script's own entry point installs.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_LOOK = ROOT / "scripts" / "capture_look.py"


def load_capture_look() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "capture_look_under_test", CAPTURE_LOOK
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sizes_are_the_size_matrix() -> None:
    assert load_capture_look().SIZES == (
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


@pytest.mark.asyncio
@pytest.mark.usefixtures("no_external_actions", "no_app_connections")
async def test_capture_writes_one_svg_per_size(tmp_path: Path) -> None:
    capture_look = load_capture_look()
    paths = await capture_look.capture(tmp_path, sizes=((80, 24), (40, 16)))
    assert paths == [tmp_path / "look-80x24.svg", tmp_path / "look-40x16.svg"]
    assert sorted(tmp_path.iterdir()) == sorted(paths)
    home = str(Path.home())
    for path in paths:
        svg = path.read_text(encoding="utf-8")
        assert svg.startswith("<svg")
        assert "machines" in svg
        assert home not in svg
