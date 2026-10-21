import json
import os
from pathlib import Path

import pytest
from textual.containers import VerticalScroll
from textual.content import Content
from textual.widgets import Footer, ListView, Static

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Project, parse_projects

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

PROJECTS = (
    Project(
        "garden-demo",
        "Garden demo",
        "garden-demo-host",
        "https://example.com/garden.git",
        "https://example.com/garden/docs",
    ),
    Project("studio-demo", "Studio demo", "studio-demo-host"),
)


@pytest.mark.parametrize("size", [(80, 24), (120, 40), (60, 20)])
@pytest.mark.parametrize(
    ("projects", "message"),
    [(None, "No configuration selected."), ([], "No projects in this configuration.")],
)
async def test_empty_states(projects, message: str, size: tuple[int, int]) -> None:
    app = SSHWorkbenchApp(projects)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        assert app.is_running
        assert app.title == "SSH Workbench"
        status = app.query_one("#empty-state", Static)
        assert status.visible
        assert message in str(status.content)
        assert "--config PATH" in str(status.content)
        assert not app.query(ListView)
        await pilot.press("down", "tab", "up", "q")
        assert not app.is_running
        assert app.return_code == 0


async def test_no_config_screen_names_default_path() -> None:
    path = Path("fictional") / "odd\x1bname" / "projects.toml"
    app = SSHWorkbenchApp(None, default_config=path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = str(app.query_one("#empty-state", Static).content)
        assert "No configuration selected." in content
        assert f"fictional{os.sep}odd\\x1bname{os.sep}projects.toml" in content
        assert "\x1b" not in content
        assert "--config PATH" in content


async def test_no_config_screen_without_default_path() -> None:
    app = SSHWorkbenchApp(None)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        content = str(app.query_one("#empty-state", Static).content)
        assert "restart with --config PATH" in content
        assert "None" not in content


async def test_initial_selection_order_and_keyboard_details() -> None:
    app = SSHWorkbenchApp(PROJECTS)
    async with app.run_test(size=(80, 24)) as pilot:
        project_list = app.query_one(ListView)
        assert app.focused is project_list
        assert project_list.index == 0
        assert [str(widget.content) for widget in project_list.query(Static)] == [
            "Garden demo",
            "Studio demo",
        ]
        for index, key in [(0, "up"), (1, "down"), (1, "down"), (0, "up")]:
            await pilot.press(key)
            project = PROJECTS[index]
            assert project_list.index == index
            assert project_list.highlighted_child is project_list.children[index]
            for field, expected in (
                ("id", project.id),
                ("name", project.name),
                ("ssh-alias", project.ssh_alias),
                ("repository", project.repository or "Not provided"),
                ("documentation", project.documentation or "Not provided"),
            ):
                assert (
                    str(app.query_one(f"#project-{field}", Static).content) == expected
                )
        await pilot.press("tab")
        details = app.query_one("#project-details", VerticalScroll)
        assert app.focused is details
        assert project_list.index == 0
        assert details.styles.border.top != project_list.styles.border.top
        await pilot.press("shift+tab")
        assert app.focused is project_list


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        ("[bold]Garden[/bold]", "[bold]Garden[/bold]"),
        (
            "[@click=app.quit]click[/] [link=https://example.com]link[/link]",
            "[@click=app.quit]click[/] [link=https://example.com]link[/link]",
        ),
        ("Cafe\u0301 / 東京 / \U0001f331", "Cafe\u0301 / 東京 / \U0001f331"),
        ("row\nnext\r\t\b\0", r"row\nnext\r\t\x08\x00"),
        (
            "escape\x1b]8;;https://example.com\x07",
            r"escape\x1b]8;;https://example.com\x07",
        ),
        ("C1\x85\x9b31m", r"C1\x85\x9b31m"),
        ("direction\u202e\u2066\u200b\u2028", r"direction\u202e\u2066\u200b\u2028"),
    ],
)
async def test_names_are_literal_and_controls_are_visible(
    name: str, shown: str
) -> None:
    projects = parse_projects(
        'schema_version = 1\n[[projects]]\nid = "literal-demo"\n'
        f"name = {json.dumps(name, ensure_ascii=False)}\n"
        'ssh_alias = "literal-demo-host"\n'
        'repository = "https://example.com/[bold]repo[/bold]"\n'
        'documentation = "https://example.com/[link=docs]"\n'
    )
    app = SSHWorkbenchApp(projects)
    async with app.run_test(size=(80, 24)) as pilot:
        widgets = [
            app.query_one(ListView).query_one(Static),
            app.query_one("#project-name", Static),
        ]
        for widget in widgets:
            rendered = widget.render()
            assert isinstance(rendered, Content)
            assert rendered.plain == shown
            assert not rendered.spans
        for field in ("repository", "documentation"):
            rendered = app.query_one(f"#project-{field}", Static).render()
            assert isinstance(rendered, Content)
            assert rendered.plain == getattr(projects[0], field)
            assert not rendered.spans
        await pilot.click("#project-name")
        await pilot.click("#project-repository")
        await pilot.press("enter")
        assert app.is_running
        assert projects[0].name == name
        assert app.projects[0] is projects[0]


@pytest.mark.parametrize("size", [(80, 24), (120, 40), (60, 20)])
async def test_long_values_wrap_scroll_and_reset(size: tuple[int, int]) -> None:
    long_project = Project(
        "long-demo-" + "x" * 120,
        "Long 東京 " * 50,
        "demo-" + "host" * 100,
        "https://example.com/" + "path/" * 150,
        "https://example.com/" + "docs/" * 150,
    )
    app = SSHWorkbenchApp([long_project, PROJECTS[1]])
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        project_list = app.query_one(ListView)
        details = app.query_one("#project-details", VerticalScroll)
        footer = app.query_one(Footer)
        assert app.screen.region.contains_region(project_list.region)
        assert app.screen.region.contains_region(details.region)
        assert app.screen.region.contains_region(footer.region)
        assert project_list.region.right <= details.region.x
        assert details.region.bottom <= footer.region.y
        assert details.max_scroll_x == 0
        assert details.max_scroll_y > 0
        assert str(app.query_one("#project-documentation", Static).content).endswith(
            "docs/" * 150
        )
        await pilot.press("tab", "down", "pagedown")
        await pilot.wait_for_scheduled_animations()
        assert app.focused is details
        assert details.scroll_y > 0
        await pilot.press("end")
        await pilot.wait_for_scheduled_animations()
        assert details.scroll_y == details.max_scroll_y
        await pilot.press("shift+tab", "down")
        await pilot.pause()
        assert project_list.index == 1
        assert details.scroll_y == 0
        assert str(app.query_one("#project-name", Static).content) == "Studio demo"
        await pilot.resize_terminal(80, 24)
        assert app.is_running


async def test_many_projects_keep_keyboard_selection_visible() -> None:
    projects = [Project(f"demo-{i}", f"Demo {i}", f"demo-{i}-host") for i in range(35)]
    app = SSHWorkbenchApp(projects)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press(*(["down"] * 34))
        project_list = app.query_one(ListView)
        assert project_list.index == 34
        assert project_list.scroll_y > 0
        assert str(app.query_one("#project-id", Static).content) == "demo-34"
        assert project_list.scrollable_content_region.contains_region(
            project_list.highlighted_child.region
        )


@pytest.mark.parametrize("key", ["q", "ctrl+q"])
@pytest.mark.parametrize("projects", [None, [], PROJECTS])
async def test_keyboard_exit_is_clean(key: str, projects) -> None:
    app = SSHWorkbenchApp(projects)
    async with app.run_test() as pilot:
        if projects:
            await pilot.press("tab")
        await pilot.press(key)
        assert not app.is_running
        assert app.return_code == 0
