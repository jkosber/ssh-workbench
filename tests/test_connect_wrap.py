"""A direct machine's connect value: where it breaks when it is too wide."""

import pytest
from support import wait_for
from textual.content import Content
from textual.geometry import Size
from textual.widgets import Static

from ssh_workbench.app import SSHWorkbenchApp, wrap_target
from ssh_workbench.config import Machine
from ssh_workbench.status import AliasTarget

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("no_external_actions", "no_app_connections"),
]

TARGET = "studio@studio-box.example.com:2222"
LONG_USER = "administrator@studio-box.example.com:2222"
LONG_HOST = "a-very-long-host-name.department.example.com:2222"
IPV6 = "admin@[2001:db8:85a3::8a2e:370:7334]:2222"
IPV6_SHORT = "2001:db8:85a3::8a2e:370:7334"
IPV6_LONG = "2001:db8:85a3:1234:5678:8a2e:370:7334"
STUDIO = Machine(
    "studio-box",
    "Studio box",
    user="studio",
    addresses=("studio-box.example.com", "192.0.2.40"),
    port=2222,
)
WRAPPED = ["direct ·", "studio@studio-box.example.com", ":2222"]


class SecondAddressOnline:
    """Only 192.0.2.40 answers."""

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return None

    def port_open(self, host: str, port: int) -> bool:
        return host == "192.0.2.40"


class NameOnline:
    """Only studio-box.example.com answers."""

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return None

    def port_open(self, host: str, port: int) -> bool:
        return host == "studio-box.example.com"


def connect(app: SSHWorkbenchApp) -> Static:
    return app.query_one("#machine-connect", Static)


def shown_rows(widget: Static) -> list[str]:
    """The widget's rows as the screen draws them."""
    return [
        "".join(segment.text for segment in widget.render_line(y)).rstrip()
        for y in range(widget.size.height)
    ]


async def selected(app: SSHWorkbenchApp, pilot, machine_id: str) -> None:
    await wait_for(
        pilot, lambda: str(app.query_one("#details-id", Static).content) == machine_id
    )
    await pilot.pause()


@pytest.mark.parametrize(
    ("text", "width", "host_at", "port_at", "lines"),
    [
        # It fits: one line.
        (TARGET, 34, 7, 29, [TARGET]),
        ("192.0.2.20", 33, 0, None, ["192.0.2.20"]),
        # Too wide: before the port's colon.
        (TARGET, 33, 7, 29, ["studio@studio-box.example.com", ":2222"]),
        (TARGET, 32, 7, 29, ["studio@studio-box.example.com", ":2222"]),
        # The port's colon is out of reach: after the @.
        (LONG_USER, 33, 14, 36, ["administrator@", "studio-box.example.com:2222"]),
        (TARGET, 24, 7, 29, ["studio@", "studio-box.example.com", ":2222"]),
        # A bracketed IPv6 address breaks before its port, not inside itself.
        (IPV6, 33, 6, 36, ["admin@", "[2001:db8:85a3::8a2e:370:7334]", ":2222"]),
        # Neither in reach: before the last . or - of the address that fits.
        (
            LONG_HOST,
            33,
            0,
            44,
            ["a-very-long-host-name.department", ".example.com:2222"],
        ),
        (
            "studio@a-very-long-host-name.example.com",
            20,
            7,
            None,
            ["studio@", "a-very-long-host", "-name.example.com"],
        ),
        # An IPv6 address breaks after a colon, so no row starts like a port,
        (
            "2001:db8:85a3:1234:5678:8a2e:370:7334",
            20,
            0,
            None,
            ["2001:db8:85a3:1234:", "5678:8a2e:370:7334"],
        ),
        # after both colons of a `::`, never between them.
        (IPV6_SHORT, 15, 0, None, ["2001:db8:85a3::", "8a2e:370:7334"]),
        (IPV6_SHORT, 14, 0, None, ["2001:db8:", "85a3::8a2e:", "370:7334"]),
        # Nothing to break before: at the width.
        ("a" * 40 + ":2222", 30, 0, 40, ["a" * 30, "a" * 10 + ":2222"]),
    ],
)
async def test_wrap_target(
    text: str, width: int, host_at: int, port_at: int | None, lines: list[str]
) -> None:
    assert wrap_target(text, width, host_at, port_at) == lines
    assert "".join(lines) == text


@pytest.mark.parametrize(
    ("text", "host_at", "port_at"),
    [
        (TARGET, 7, 29),
        (LONG_USER, 14, 36),
        (LONG_HOST, 0, 44),
        (IPV6, 6, 36),
        ("a" * 40 + ":2222", 0, 40),
    ],
)
async def test_wrap_target_never_splits_the_port(
    text: str, host_at: int, port_at: int
) -> None:
    for width in range(5, 60):
        lines = wrap_target(text, width, host_at, port_at)
        assert "".join(lines) == text
        assert all(Content(line).cell_length <= width for line in lines)
        assert [line for line in lines if ":2222" in line] == [lines[-1]]


@pytest.mark.parametrize(
    ("text", "host_at", "port_at"),
    [
        (IPV6_LONG, 0, None),
        (IPV6_SHORT, 0, None),
        (f"admin@{IPV6_LONG}", 6, None),
        (f"admin@[{IPV6_LONG}]:2222", 6, 45),
        (IPV6, 6, 36),
    ],
)
async def test_wrap_target_starts_no_row_with_an_address_colon(
    text: str, host_at: int, port_at: int | None
) -> None:
    for width in range(6, 60):
        lines = wrap_target(text, width, host_at, port_at)
        assert "".join(lines) == text
        # Only the port's own row may start with a colon.
        colons = [line for line in lines if line.startswith(":")]
        assert colons == [] or (port_at is not None and colons == [":2222"])


@pytest.mark.parametrize("size", [(80, 24), (60, 20)])
async def test_a_wide_direct_target_breaks_before_its_port(
    size: tuple[int, int],
) -> None:
    app = SSHWorkbenchApp([STUDIO])
    async with app.run_test(size=size) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        assert shown_rows(widget) == WRAPPED
        assert widget.region.height == 3
        # The text itself stays one line; only the drawing breaks it.
        assert str(widget.content) == f"direct · {TARGET}"
        # The row below starts right under the value.
        row = app.query_one("#machine-connect-row")
        below = app.query_one("#machine-addresses-row")
        assert below.region.y == row.region.y + row.region.height


async def test_a_direct_target_that_fits_stays_on_one_row() -> None:
    app = SSHWorkbenchApp([STUDIO])
    async with app.run_test(size=(120, 30)) as pilot:
        await selected(app, pilot, "studio-box")
        assert shown_rows(connect(app)) == [f"direct · {TARGET}"]


async def test_a_target_as_wide_as_the_row_is_not_broken() -> None:
    app = SSHWorkbenchApp([STUDIO])
    async with app.run_test(size=(40, 16)) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        assert widget.size.width >= 34
        assert shown_rows(widget) == ["direct ·", TARGET]


async def test_a_target_exactly_as_wide_as_the_row_is_not_broken() -> None:
    app = SSHWorkbenchApp([STUDIO])
    async with app.run_test(size=(37, 16)) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        assert widget.size.width == 34
        assert shown_rows(widget) == ["direct ·", TARGET]


async def test_an_ipv6_address_without_a_port_shows_no_row_like_a_port() -> None:
    machine = Machine("box", "Box", user="admin", addresses=(IPV6_LONG,))
    app = SSHWorkbenchApp([machine])
    async with app.run_test(size=(80, 24)) as pilot:
        await selected(app, pilot, "box")
        widget = connect(app)
        assert widget.size.width == 33
        assert shown_rows(widget) == [
            "direct · admin@",
            "2001:db8:85a3:1234:5678:8a2e:370:",
            "7334",
        ]


async def test_no_width_is_no_height() -> None:
    app = SSHWorkbenchApp([STUDIO])
    async with app.run_test(size=(80, 24)) as pilot:
        await selected(app, pilot, "studio-box")
        size = Size(80, 24)
        assert connect(app).get_content_height(size, size, 0) == 0


async def test_the_exported_note_follows_the_port() -> None:
    machine = Machine(
        "studio-box",
        "Studio box",
        user="studio",
        addresses=("studio-box.example.com",),
        port=2222,
        export_alias=True,
    )
    app = SSHWorkbenchApp([machine])
    async with app.run_test(size=(80, 24)) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        assert widget.size.width == 33
        assert shown_rows(widget) == [
            "direct ·",
            "studio@studio-box.example.com",
            ":2222 · exported as ssh",
            "studio-box",
        ]
        assert str(widget.content) == (
            f"direct · {TARGET} · exported as ssh studio-box"
        )


async def test_the_break_follows_a_resize() -> None:
    app = SSHWorkbenchApp([STUDIO])
    async with app.run_test(size=(120, 30)) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        assert shown_rows(widget) == [f"direct · {TARGET}"]
        await pilot.resize_terminal(80, 24)
        await wait_for(pilot, lambda: widget.region.height == 3)
        assert shown_rows(widget) == WRAPPED
        await pilot.resize_terminal(120, 30)
        await wait_for(pilot, lambda: widget.region.height == 1)
        assert shown_rows(widget) == [f"direct · {TARGET}"]


async def test_the_break_follows_the_address_a_check_finds() -> None:
    app = SSHWorkbenchApp([STUDIO], checker=SecondAddressOnline())
    async with app.run_test(size=(80, 24)) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        await wait_for(
            pilot, lambda: str(widget.content) == "direct · studio@192.0.2.40:2222"
        )
        await wait_for(pilot, lambda: widget.region.height == 1)
        assert shown_rows(widget) == ["direct · studio@192.0.2.40:2222"]


async def test_a_wide_address_a_check_finds_breaks_before_its_port() -> None:
    machine = Machine(
        "studio-box",
        "Studio box",
        user="studio",
        addresses=("192.0.2.41", "studio-box.example.com"),
        port=2222,
    )
    app = SSHWorkbenchApp([machine], checker=NameOnline())
    async with app.run_test(size=(80, 24)) as pilot:
        await selected(app, pilot, "studio-box")
        widget = connect(app)
        await wait_for(pilot, lambda: str(widget.content) == f"direct · {TARGET}")
        await wait_for(pilot, lambda: widget.region.height == 3)
        assert shown_rows(widget) == WRAPPED


async def test_an_alias_value_is_drawn_as_before() -> None:
    machine = Machine("garden", "Garden", alias="garden-demo-host")
    app = SSHWorkbenchApp([machine])
    async with app.run_test(size=(80, 24)) as pilot:
        await selected(app, pilot, "garden")
        assert shown_rows(connect(app)) == ["alias · garden-demo-host"]
