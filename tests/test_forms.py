"""Adding, editing and deleting machines, with fictional files in tmp_path."""

import asyncio
from pathlib import Path

import pytest
from textual import events
from textual.containers import VerticalScroll
from textual.widgets import Footer, Input, ListView, RadioButton, Static, TextArea

from ssh_workbench import store
from ssh_workbench.app import MachinePanes, SSHWorkbenchApp
from ssh_workbench.config import Link, Machine, format_machines, parse_machines
from ssh_workbench.forms import ConfirmDelete, MachineForm

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

MACHINES = (
    Machine("garden", "Garden", alias="garden-host"),
    Machine("studio", "Studio", user="dev", addresses=("192.0.2.40",), port=2222),
    Machine("lab", "Lab", alias="lab-host"),
)


def saved_app(tmp_path: Path, machines=MACHINES, text: str | None = None):
    path = tmp_path / "machines.toml"
    text = format_machines(machines) if text is None else text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return SSHWorkbenchApp(parse_machines(text), config_path=path, file_text=text), path


def status(app: SSHWorkbenchApp) -> str:
    return str(app.query_one("#connection-status", Static).content)


async def wait_for(pilot, predicate) -> None:
    async with asyncio.timeout(5):
        while not predicate():
            await pilot.pause()


async def open_form(app, pilot, key: str) -> MachineForm:
    await pilot.press(key)
    await wait_for(pilot, lambda: isinstance(app.screen, MachineForm))
    return app.screen


def fill(form: MachineForm, **values: str) -> None:
    for field, value in values.items():
        form.query_one(f"#form-{field}", Input).value = value


def error(form: MachineForm, field: str) -> str:
    return str(form.query_one(f"#form-{field}-error", Static).content)


def message(form: MachineForm) -> str:
    return str(form.query_one("#form-message", Static).content)


async def back_to_browser(app, pilot) -> None:
    await wait_for(pilot, lambda: len(app.screen_stack) == 1)
    await wait_for(pilot, lambda: app.focused is not None)


async def test_add_edit_delete_bindings_are_visible(tmp_path: Path) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test(size=(60, 20)) as pilot:
        footer = app.query_one(Footer)
        await wait_for(
            pilot,
            lambda: (
                {"add", "edit", "delete"}
                <= {key.action for key in footer.query("FooterKey")}
            ),
        )
        for action, key, label in (
            ("add", "a", "Add"),
            ("edit", "e", "Edit"),
            ("delete", "x", "Delete"),
        ):
            keys = [item for item in footer.query("FooterKey") if item.action == action]
            assert len(keys) == 1 and keys[0].key == key
            assert label in keys[0].render().plain
            assert app.screen.region.contains_region(keys[0].region)


async def test_actions_are_dimmed_without_a_location_or_selection(
    tmp_path: Path,
) -> None:
    app = SSHWorkbenchApp(None)
    async with app.run_test() as pilot:
        for action in ("add", "edit", "delete"):
            assert app.check_action(action, ()) is None
        await pilot.press("a", "e", "x")
        assert len(app.screen_stack) == 1
    app, _ = saved_app(tmp_path)
    async with app.run_test() as pilot:
        assert app.check_action("add", ()) is True
        assert app.check_action("edit", ()) is True
        app.query_one(ListView).index = None
        await pilot.pause()
        assert app.check_action("add", ()) is True
        assert app.check_action("edit", ()) is None
        assert app.check_action("delete", ()) is None
        await open_form(app, pilot, "a")
        for action in ("add", "edit", "delete", "connect", "open_link"):
            assert app.check_action(action, ()) is None


async def test_edit_and_delete_need_a_file_location() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test() as pilot:
        assert app.query_one(ListView).index == 0
        for action in ("add", "edit", "delete"):
            assert app.check_action(action, ()) is None
        await pilot.press("a", "e", "x")
        assert len(app.screen_stack) == 1


async def test_add_first_alias_machine_creates_the_file(tmp_path: Path) -> None:
    path = tmp_path / "new folder" / "ssh-workbench" / "machines.toml"
    app = SSHWorkbenchApp(None, config_path=path)
    async with app.run_test() as pilot:
        content = str(app.query_one("#empty-state", Static).content)
        assert "Press A to add your first machine" in content
        form = await open_form(app, pilot, "a")
        assert form.query_one("#kind-alias", RadioButton).value
        fill(form, id="web", name="Web server", alias="web-host")
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        expected = [Machine("web", "Web server", alias="web-host")]
        assert parse_machines(path.read_text(encoding="utf-8")) == expected
        assert app.machines == tuple(expected)
        machine_list = app.query_one(ListView)
        assert machine_list.index == 0
        assert app.focused is machine_list
        assert str(app.query_one("#machine-name", Static).content) == "Web server"
        assert status(app) == "Saved machine 1: web."


async def test_add_direct_machine_with_links(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path, machines=())
    async with app.run_test() as pilot:
        assert "Press A to add one." in str(
            app.query_one("#empty-state", Static).content
        )
        form = await open_form(app, pilot, "a")
        form.query_one("#kind-direct", RadioButton).value = True
        await pilot.pause()
        fill(
            form,
            id="lab-box",
            name="Lab box",
            addresses="100.64.0.12, 192.168.1.40",
            user="admin",
            port="2222",
            key="~/.ssh/id_ed25519_lab",
        )
        form.query_one("#form-links", TextArea).text = (
            "Proxmox dashboard https://192.168.1.40:8006\n\n"
            "Status https://example.invalid/status\n"
        )
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert parse_machines(path.read_text(encoding="utf-8")) == [
            Machine(
                "lab-box",
                "Lab box",
                user="admin",
                addresses=("100.64.0.12", "192.168.1.40"),
                port=2222,
                key="~/.ssh/id_ed25519_lab",
                links=(
                    Link("Proxmox dashboard", "https://192.168.1.40:8006"),
                    Link("Status", "https://example.invalid/status"),
                ),
            )
        ]


@pytest.mark.parametrize(
    ("kind", "values", "field", "expected"),
    [
        ("alias", {"id": "Web"}, "id", "use lowercase ASCII letters"),
        ("alias", {"id": ""}, "id", "expected a nonempty string"),
        ("alias", {"name": " "}, "name", "expected a nonempty string"),
        ("alias", {"alias": "-oProxyCommand=x"}, "alias", "start with an ASCII"),
        ("direct", {"addresses": "ok.example -bad"}, "addresses", "Address 2:"),
        ("direct", {"addresses": ""}, "addresses", "expected a nonempty array"),
        ("direct", {"port": "0"}, "port", "expected an integer from 1 to 65535"),
        ("direct", {"port": "ssh"}, "port", "expected an integer from 1 to 65535"),
        ("direct", {"user": "a b"}, "user", "start with an ASCII letter"),
        ("direct", {"key": "id_rsa"}, "key", "expected an absolute path"),
    ],
)
async def test_inline_error_names_the_field_and_blocks_saving(
    tmp_path: Path, kind: str, values: dict[str, str], field: str, expected: str
) -> None:
    app, path = saved_app(tmp_path)
    before = path.read_bytes()
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        if kind == "direct":
            form.query_one("#kind-direct", RadioButton).value = True
            await pilot.pause()
            fill(form, id="new-box", name="New", addresses="new.example")
        else:
            fill(form, id="new-box", name="New", alias="new-host")
        fill(form, **values)
        await pilot.pause()
        assert expected in error(form, field)
        others = {"id", "name", "alias", "addresses", "user", "port", "key", "links"}
        for other in others - {field}:
            assert error(form, other) == ""
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert isinstance(app.screen, MachineForm)
        assert path.read_bytes() == before
        assert expected in error(form, field)


async def test_link_line_without_a_url_is_reported_by_line(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="new-box", name="New", alias="new-host")
        form.query_one(
            "#form-links", TextArea
        ).text = "Good https://example.invalid\n\nDashboard\n"
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert error(form, "links") == "Line 3 url: required field is missing"
        assert isinstance(app.screen, MachineForm)


async def test_duplicate_id_is_refused_and_fixing_it_clears_the_error(
    tmp_path: Path,
) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="lab", name="Another lab", alias="other-host")
        await pilot.pause()
        assert error(form, "id") == "already used by another machine"
        fill(form, id="lab-two")
        await pilot.pause()
        assert error(form, "id") == ""
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert [m.id for m in parse_machines(path.read_text(encoding="utf-8"))] == [
            "garden",
            "studio",
            "lab",
            "lab-two",
        ]


async def test_errors_wait_until_a_field_is_touched(tmp_path: Path) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        assert all(
            error(form, field) == ""
            for field in ("id", "name", "alias", "addresses", "links")
        )
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert error(form, "id") == "expected a nonempty string"
        assert form.focused is form.query_one("#form-id", Input)


async def test_edit_keeps_position_and_can_change_the_id(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("down")
        form = await open_form(app, pilot, "e")
        assert form.query_one("#form-id", Input).value == "studio"
        assert form.query_one("#kind-direct", RadioButton).value
        assert form.query_one("#form-addresses", Input).value == "192.0.2.40"
        assert form.query_one("#form-port", Input).value == "2222"
        fill(form, id="studio-two", name="Studio two")
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        saved = parse_machines(path.read_text(encoding="utf-8"))
        assert [m.id for m in saved] == ["garden", "studio-two", "lab"]
        assert saved[1] == Machine(
            "studio-two", "Studio two", user="dev", addresses=("192.0.2.40",), port=2222
        )
        assert app.query_one(ListView).index == 1
        assert status(app) == "Saved machine 2: studio-two."


async def test_edit_shows_links_one_per_line(tmp_path: Path) -> None:
    machines = (
        Machine(
            "docs",
            "Docs",
            alias="docs-host",
            links=(
                Link("Two words", "https://example.invalid/a"),
                Link("B", "https://example.invalid/b"),
            ),
        ),
    )
    app, path = saved_app(tmp_path, machines=machines)
    before = path.read_bytes()
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "e")
        assert form.query_one("#form-links", TextArea).text == (
            "Two words https://example.invalid/a\nB https://example.invalid/b"
        )
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert path.read_bytes() == before


@pytest.mark.parametrize("key", ["a", "e"])
async def test_escape_cancels_without_writing(tmp_path: Path, key: str) -> None:
    app, path = saved_app(tmp_path)
    before = path.read_bytes()
    async with app.run_test() as pilot:
        await pilot.press("down", "tab")
        details = app.focused
        form = await open_form(app, pilot, key)
        fill(form, id="changed", name="Changed")
        await pilot.press("escape")
        await back_to_browser(app, pilot)
        assert path.read_bytes() == before
        assert sorted(p.name for p in tmp_path.iterdir()) == ["machines.toml"]
        assert app.machines == MACHINES
        assert app.query_one(ListView).index == 1
        assert app.focused is details


@pytest.mark.parametrize("dialog", ["form", "delete"])
async def test_ctrl_q_quits_from_the_form_and_the_delete_question(
    tmp_path: Path, dialog: str
) -> None:
    app, path = saved_app(tmp_path)
    before = path.read_bytes()
    async with app.run_test() as pilot:
        if dialog == "form":
            await open_form(app, pilot, "a")
        else:
            await pilot.press("x")
            await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("ctrl+q")
        assert not app.is_running
        assert app.return_code == 0
    assert path.read_bytes() == before


async def test_q_and_keys_type_into_the_form(tmp_path: Path) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        await pilot.press("q", "c", "o", "x")
        assert app.is_running
        assert isinstance(app.screen, MachineForm)
        assert form.query_one("#form-id", Input).value == "qcox"


async def test_delete_asks_first(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    before = path.read_bytes()
    async with app.run_test() as pilot:
        await pilot.press("down")
        for answer in ("n", "escape"):
            await pilot.press("x")
            await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
            text = "\n".join(str(widget.content) for widget in app.screen.query(Static))
            assert "Delete Studio (studio)?" in text
            await pilot.press(answer)
            await back_to_browser(app, pilot)
            assert path.read_bytes() == before
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("y")
        await back_to_browser(app, pilot)
        assert [m.id for m in parse_machines(path.read_text(encoding="utf-8"))] == [
            "garden",
            "lab",
        ]
        assert app.query_one(ListView).index == 1
        assert str(app.query_one("#machine-id", Static).content) == "lab"
        assert status(app) == "Deleted machine 2: studio."


async def test_actions_wait_for_the_rebuilt_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actions = ("connect", "open_link", "add", "edit", "delete")
    original = MachinePanes.recompose
    during_rebuild = []

    async def observed_recompose(self: MachinePanes) -> None:
        # The old three-item list is still mounted while the app already holds
        # two machines; the footer asks for its bindings at exactly this point.
        app = self.app
        during_rebuild.append(
            {action: app.check_action(action, ()) for action in actions}
        )
        during_rebuild.append(sorted(app.screen_stack[0].active_bindings))
        await original(self)

    monkeypatch.setattr(MachinePanes, "recompose", observed_recompose)
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("down", "down", "x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("y")
        await wait_for(pilot, lambda: status(app) == "Deleted machine 3: lab.")
        await wait_for(pilot, lambda: len(app.query_one(ListView).children) == 2)
        await pilot.pause()
        assert during_rebuild[0] == dict.fromkeys(actions)
        assert app.is_running
        assert app.check_action("edit", ()) is True
        assert app.query_one(ListView).index == 1
        assert [m.id for m in parse_machines(path.read_text(encoding="utf-8"))] == [
            "garden",
            "studio",
        ]


async def test_deleting_the_last_machine_shows_the_empty_screen(
    tmp_path: Path,
) -> None:
    app, path = saved_app(tmp_path, machines=MACHINES[:1])
    async with app.run_test() as pilot:
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        await pilot.press("y")
        await wait_for(pilot, lambda: len(app.screen_stack) == 1)
        await wait_for(pilot, lambda: bool(app.query("#empty-state")))
        assert parse_machines(path.read_text(encoding="utf-8")) == []
        assert "Press A to add one." in str(
            app.query_one("#empty-state", Static).content
        )


COMMENTED = (
    "# My machines\nschema_version = 2\n\n[[machines]]\n"
    'id = "garden"  # the old laptop\nname = "Garden"\nalias = "garden-host"\n'
)


async def test_commented_file_warns_on_the_first_save(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path, machines=(), text=COMMENTED)
    original = path.read_bytes()
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert message(form) == (
            "Saving rewrites the file without its comments or formatting; the "
            "old file is kept as machines.toml.bak. Press Ctrl+S again to save."
        )
        assert path.read_bytes() == original
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert (tmp_path / "machines.toml.bak").read_bytes() == original
        assert [m.id for m in parse_machines(path.read_text(encoding="utf-8"))] == [
            "garden",
            "web",
        ]
        form = await open_form(app, pilot, "e")
        fill(form, name="Web again")
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert parse_machines(path.read_text(encoding="utf-8"))[1].name == "Web again"


async def test_delete_confirmation_warns_about_comments(tmp_path: Path) -> None:
    app, _ = saved_app(tmp_path, machines=(), text=COMMENTED)
    async with app.run_test() as pilot:
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        text = "\n".join(str(widget.content) for widget in app.screen.query(Static))
        assert "without its comments or formatting" in text
        await pilot.press("n")


async def test_outside_change_keeps_the_form_and_reloads_the_list(
    tmp_path: Path,
) -> None:
    app, path = saved_app(tmp_path)
    changed = MACHINES + (Machine("added-elsewhere", "Elsewhere", alias="else"),)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        path.write_text(format_machines(changed), encoding="utf-8")
        before = path.read_bytes()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert isinstance(app.screen, MachineForm)
        assert message(form) == (
            "The machine file changed outside Workbench and was reloaded. "
            "Check the list, then save again."
        )
        assert form.query_one("#form-id", Input).value == "web"
        assert path.read_bytes() == before
        assert app.machines == changed
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert [m.id for m in parse_machines(path.read_text(encoding="utf-8"))] == [
            "garden",
            "studio",
            "lab",
            "added-elsewhere",
            "web",
        ]
        assert app.query_one(ListView).index == 4


async def test_outside_comment_is_warned_about_before_saving(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        commented = "# a note added elsewhere\n" + format_machines(MACHINES)
        path.write_text(commented, encoding="utf-8")
        before = path.read_bytes()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert message(form).startswith("The machine file changed outside Workbench")
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert message(form).startswith("Saving rewrites the file without its comments")
        assert path.read_bytes() == before
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert (tmp_path / "machines.toml.bak").read_bytes() == before
        assert parse_machines(path.read_text(encoding="utf-8"))[-1].id == "web"


async def test_reload_keeps_the_selected_machine(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    inserted = (Machine("first", "First", alias="first-host"),) + MACHINES
    async with app.run_test() as pilot:
        await pilot.press("down")
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        path.write_text(format_machines(inserted), encoding="utf-8")
        await pilot.press("ctrl+s")
        await pilot.pause()
        await pilot.press("escape")
        await back_to_browser(app, pilot)
        await pilot.pause()
        assert str(app.query_one("#machine-id", Static).content) == "studio"
        assert app.query_one(ListView).index == 2


async def test_refused_delete_says_to_delete_again(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("x")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmDelete))
        path.write_text(format_machines(MACHINES[1:]), encoding="utf-8")
        await pilot.press("y")
        await back_to_browser(app, pilot)
        assert status(app) == (
            "The machine file changed outside Workbench and was reloaded. "
            "Check the list, then delete again."
        )


async def test_huge_port_is_an_error_not_a_crash(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        form.query_one("#kind-direct", RadioButton).value = True
        await pilot.pause()
        fill(form, id="big", name="Big", addresses="big.example", port="9" * 5000)
        await pilot.pause()
        assert app.is_running
        assert error(form, "port") == "expected an integer from 1 to 65535"


async def test_outside_change_to_an_invalid_file_writes_nothing(
    tmp_path: Path,
) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        path.write_text("private-marker = [", encoding="utf-8")
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert message(form) == (
            "The machine file changed outside Workbench and now has an error: "
            "TOML: invalid syntax at line 1, column 19. Fix the file, then save again."
        )
        assert "private-marker" not in message(form)
        assert path.read_text(encoding="utf-8") == "private-marker = ["
        assert app.machines == MACHINES


async def test_save_failure_shows_a_sanitized_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, path = saved_app(tmp_path)
    before = path.read_bytes()

    def fail(source: str, target: str) -> None:
        raise PermissionError(f"private-marker {target}")

    monkeypatch.setattr(store.os, "replace", fail)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert message(form) == "Could not save the machine file: permission denied."
        assert path.read_bytes() == before
        assert isinstance(app.screen, MachineForm)


async def test_host_names_are_offered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "fictional-ssh"
    folder.mkdir()
    (folder / "config").write_text(
        "Host alpha beta *.wild\nHost alpha-two\n", encoding="utf-8"
    )
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(folder))
    app, path = saved_app(tmp_path / "files")
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        hosts = str(form.query_one("#form-hosts", Static).content)
        assert hosts == "In your SSH config: alpha, beta, alpha-two"
        alias = form.query_one("#form-alias", Input)
        assert await alias.suggester.get_suggestion("alp") == "alpha"
        fill(form, id="unlisted", name="Unlisted", alias="not-in-config")
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        assert parse_machines(path.read_text(encoding="utf-8"))[-1].alias == (
            "not-in-config"
        )


async def test_no_host_names_says_so(tmp_path: Path) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        assert str(form.query_one("#form-hosts", Static).content) == (
            "No Host names found in your SSH config. Type any alias."
        )


async def test_save_from_the_details_pane_returns_focus_to_the_list(
    tmp_path: Path,
) -> None:
    app, _ = saved_app(tmp_path)
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.press("down", "down", "tab")
        assert app.focused is app.query_one("#machine-details", VerticalScroll)
        form = await open_form(app, pilot, "e")
        fill(form, name="Lab renamed")
        await pilot.press("ctrl+s")
        await back_to_browser(app, pilot)
        machine_list = app.query_one(ListView)
        assert app.focused is machine_list
        assert machine_list.index == 2
        assert str(app.query_one("#machine-name", Static).content) == "Lab renamed"


async def test_two_saves_in_one_batch_add_once(tmp_path: Path) -> None:
    app, path = saved_app(tmp_path)
    async with app.run_test() as pilot:
        form = await open_form(app, pilot, "a")
        fill(form, id="web", name="Web", alias="web-host")
        for _ in range(2):
            app.post_message(events.Key("ctrl+s", None))
        await back_to_browser(app, pilot)
        await pilot.pause()
        ids = [m.id for m in parse_machines(path.read_text(encoding="utf-8"))]
        assert ids == ["garden", "studio", "lab", "web"]
        assert app.is_running
