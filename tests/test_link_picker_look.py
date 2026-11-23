"""The link picker's look: each link a name over its URL, a marker on the
highlighted one, the machine name and the hint row pinned while the list
scrolls. Fictional machines and URLs only."""

from unittest.mock import Mock

import pytest
from support import showing, wait_for
from textual.content import Content
from textual.widgets import OptionList, Static

from ssh_workbench import app as app_module
from ssh_workbench.app import LinkPicker, SSHWorkbenchApp, link_prompt
from ssh_workbench.config import Link, Machine
from ssh_workbench.links import LinkResult

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

GRAFANA = (
    "https://grafana.example.com/d/fictional-overviews/main-board?orgId=1&refresh=30s"
)
STUDIO = Machine(
    "studio-box",
    "Studio box",
    alias="studio-box-host",
    links=(
        Link("Dashboard", "https://192.0.2.40:8006"),
        Link("Status page", "https://studio-box.example.com/status"),
        Link("Grafana", GRAFANA),
    ),
)
MANY = Machine(
    "service-rack",
    "Service rack",
    alias="service-rack-host",
    links=tuple(
        Link(f"Service {i:02}", f"https://service-{i:02}.example.com/status")
        for i in range(1, 13)
    ),
)
HINT = " enter open  esc cancel "


def prompts(options: OptionList) -> list[Content]:
    return [
        options.get_option_at_index(index).prompt
        for index in range(options.option_count)
    ]


def url_lines(prompt: Content) -> list[str]:
    return prompt.plain.split("\n")[1:]


async def open_picker(app, pilot) -> LinkPicker:
    await pilot.press("o")
    await wait_for(pilot, lambda: showing(app, LinkPicker))
    await pilot.pause()
    await pilot.pause()
    return app.screen


def parts(picker: LinkPicker):
    return (
        picker.query_one("#link-picker"),
        picker.query_one("#link-machine", Static),
        picker.query_one("#link-options", OptionList),
        picker.query_one("#link-picker > .hint", Static),
    )


async def test_link_prompt() -> None:
    assert len(GRAFANA) == 80
    prompt = link_prompt("Dashboard", "https://192.0.2.40:8006", 40, True)
    assert prompt.plain == "▌Dashboard\n   https://192.0.2.40:8006"
    assert url_lines(link_prompt("Grafana", GRAFANA, 46, False)) == [
        "   https://grafana.example.com/d",
        "   /fictional-overviews/main-board?orgId=1",
        "   &refresh=30s",
    ]
    for width in (20, 33, 46):
        prompt = link_prompt("Grafana", GRAFANA, width, False)
        lines = prompt.plain.split("\n")
        assert lines[0] == " Grafana"
        assert all(Content(line).cell_length <= width for line in lines), width
        assert all(line.startswith("   ") for line in lines[1:]), width
        assert "".join(line[3:] for line in lines[1:]) == GRAFANA, width
    assert len(link_prompt("Grafana", GRAFANA, None, True).plain.split("\n")) == 2


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_each_option_is_a_name_over_its_url(size: tuple[int, int]) -> None:
    app = SSHWorkbenchApp((STUDIO,))
    async with app.run_test(size=size) as pilot:
        picker = await open_picker(app, pilot)
        frame, name, options, hint = parts(picker)
        assert options.styles.border_top[0] == ""
        assert tuple(options.styles.padding) == (0, 0, 0, 0)
        assert options.option_count == 3
        for prompt in prompts(options):
            assert url_lines(prompt)
            assert all(line.startswith("   ") for line in url_lines(prompt))
        assert str(name.content) == "Studio box"
        assert name.region.y == frame.region.y + 1
        assert hint.content.plain == HINT
        assert hint.region.bottom == frame.region.bottom - 1
        assert options.max_scroll_y == 0
        assert app.screen.region.contains_region(frame.region)


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_many_links_scroll_between_the_name_and_the_hint(
    size: tuple[int, int],
) -> None:
    app = SSHWorkbenchApp((MANY,))
    async with app.run_test(size=size) as pilot:
        picker = await open_picker(app, pilot)
        frame, name, options, hint = parts(picker)
        assert options.max_scroll_y > 0
        assert frame.region.contains_region(name.region)
        assert frame.region.contains_region(hint.region)
        assert hint.region.bottom == frame.region.bottom - 1
        assert frame.region.height <= int(size[1] * 0.9)
        for prompt in prompts(options):
            assert all(line.startswith("   ") for line in url_lines(prompt))
        before = hint.region
        await pilot.press("end")
        await pilot.pause()
        assert options.highlighted == 11
        assert hint.region == before
        assert hint.content.plain == HINT


async def test_the_highlighted_link_has_a_marker(monkeypatch) -> None:
    opener = Mock(return_value=LinkResult.ACCEPTED)
    monkeypatch.setattr(app_module, "open_link", opener)
    app = SSHWorkbenchApp((STUDIO,))
    async with app.run_test(size=(80, 24)) as pilot:
        picker = await open_picker(app, pilot)
        options = picker.query_one("#link-options", OptionList)
        assert [prompt.plain[0] for prompt in prompts(options)] == ["▌", " ", " "]
        await pilot.press("down")
        await pilot.pause()
        assert [prompt.plain[0] for prompt in prompts(options)] == [" ", "▌", " "]
        await pilot.press("enter")
        await wait_for(pilot, lambda: opener.call_count == 1)
        opener.assert_called_once_with(STUDIO.links[1].url)


async def test_a_resize_rewraps_and_keeps_the_highlight() -> None:
    app = SSHWorkbenchApp((STUDIO,))
    async with app.run_test(size=(80, 24)) as pilot:
        picker = await open_picker(app, pilot)
        options = picker.query_one("#link-options", OptionList)
        await pilot.press("down", "down")
        await pilot.resize_terminal(60, 20)
        await pilot.pause()
        await pilot.pause()
        assert options.highlighted == 2
        third = prompts(options)[2]
        assert third.plain.startswith("▌")
        for prompt in prompts(options):
            for line in prompt.plain.split("\n"):
                assert Content(line).cell_length <= options.size.width - 1, line
        assert "".join(line[3:] for line in url_lines(third)) == GRAFANA
        await pilot.press("escape")
