import pytest
from textual.widgets import Static

from ssh_workbench.app import SSHWorkbenchApp


@pytest.mark.asyncio
async def test_startup_shows_scaffold_status() -> None:
    app = SSHWorkbenchApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.is_running
        assert app.title == "SSH Workbench"
        status = app.query_one("#scaffold-status", Static)
        assert status.visible
        assert str(status.content) == "Development scaffold - unreleased"


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["q", "ctrl+q"])
async def test_keyboard_exit_is_clean(key: str) -> None:
    app = SSHWorkbenchApp()
    async with app.run_test() as pilot:
        await pilot.press(key)
        assert not app.is_running
        assert app.return_code == 0
