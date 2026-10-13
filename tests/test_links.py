"""URL validation and browser dispatch with every external boundary replaced."""

import json
import subprocess
from unittest.mock import Mock

import pytest

from ssh_workbench import config, links
from ssh_workbench.config import ProjectConfigError, parse_projects, validate_http_url
from ssh_workbench.links import LinkResult, open_link

pytestmark = pytest.mark.usefixtures("no_external_actions")


def project_config(field: str, value: object) -> str:
    return (
        'schema_version = 1\n[[projects]]\nid = "link-fixture"\n'
        'name = "Link fixture"\nssh_alias = "fictional-host"\n'
        f"{field} = {json.dumps(value)}\n"
    )


@pytest.fixture
def windows_opener(monkeypatch: pytest.MonkeyPatch) -> Mock:
    opener = Mock(return_value=None)
    monkeypatch.setattr(links.sys, "platform", "win32")
    monkeypatch.setattr(links.os, "startfile", opener, raising=False)
    return opener


def test_loader_and_launch_boundary_share_the_url_validator() -> None:
    assert links.validate_http_url is config.validate_http_url


@pytest.mark.parametrize("field", ["repository", "documentation"])
@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/fictional/repository.git",
        "HTTP://Example.invalid:8080/docs?q=a#start",
        "https://[2001:db8::1]/docs",
        "https://example.invalid/a%20b?token=fictional%26value&next=%2Fdocs#part-2",
        "https://example.invalid/[b]literal[/b]?value=$(fictional)&other=`literal`",
    ],
)
def test_accepted_urls_remain_exact_at_loading_and_dispatch(
    field: str, url: str, windows_opener: Mock
) -> None:
    assert validate_http_url(url) == url
    assert getattr(parse_projects(project_config(field, url))[0], field) == url
    assert open_link(url) is LinkResult.ACCEPTED
    windows_opener.assert_called_once_with(url)


@pytest.mark.parametrize("field", ["repository", "documentation"])
@pytest.mark.parametrize(
    "url",
    [
        "",
        " ",
        "file:///fictional/repository",
        "ssh://example.invalid/repository",
        "javascript:alert(1)",
        "//example.invalid/docs",
        "fictional-browser --new-window",
        "https:example.invalid",
        "https:///docs",
        "https://",
        "https://user:private-marker@example.invalid/docs",
        "https://user@example.invalid/docs",
        "https://@example.invalid",
        "https://:private-marker@example.invalid",
        " https://example.invalid",
        "https://example.invalid ",
        "https://example.invalid/a b",
        "https://exam\tple.invalid",
        "https://example.invalid/\npath",
        "\x00https://example.invalid",
        "https://example.invalid/\x1b[31m",
        "https://example.invalid/\x7f",
        "https://example.invalid/\u0081",
        "https://example.invalid/\u009f",
        "https://example.invalid\\@other.invalid",
        "https://example.invalid:bad",
        "https://example.invalid:65536",
        "https://[broken",
        7,
        True,
        [],
        {},
    ],
)
def test_loader_and_boundary_reject_the_same_invalid_values(
    field: str, url: object, windows_opener: Mock
) -> None:
    with pytest.raises(ProjectConfigError):
        validate_http_url(url)
    with pytest.raises(ProjectConfigError):
        parse_projects(project_config(field, url))
    assert open_link(url) is LinkResult.INVALID
    windows_opener.assert_not_called()


def test_missing_link_never_invokes_the_os(windows_opener: Mock) -> None:
    assert open_link(None) is LinkResult.MISSING
    windows_opener.assert_not_called()


@pytest.mark.parametrize("platform", ["win32", "linux"])
@pytest.mark.parametrize(
    "error", [OSError, ValueError, RuntimeError, NotImplementedError]
)
def test_expected_launch_errors_have_only_sanitized_results(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    platform: str,
    error: type[Exception],
) -> None:
    monkeypatch.setattr(links.sys, "platform", platform)
    monkeypatch.setenv("DISPLAY", ":fixture")
    monkeypatch.setattr(links.shutil, "which", Mock(return_value="/fixture/gio"))
    exception = error(
        "private-path https://example.invalid/?secret=private-marker\x1b[31m"
    )
    monkeypatch.setattr(
        links.os, "startfile", Mock(side_effect=exception), raising=False
    )
    monkeypatch.setattr(links.subprocess, "run", Mock(side_effect=exception))

    result = open_link("https://example.invalid/?secret=private-marker")

    assert result is LinkResult.FAILED
    assert "private" not in result.value
    assert "\x1b" not in result.value
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("display", ["DISPLAY", "WAYLAND_DISPLAY"])
@pytest.mark.parametrize(
    "returncode, expected", [(0, LinkResult.ACCEPTED), (7, LinkResult.FAILED)]
)
def test_linux_gio_uses_exact_url_as_an_argument_without_terminal_io(
    monkeypatch: pytest.MonkeyPatch,
    display: str,
    returncode: int,
    expected: LinkResult,
) -> None:
    monkeypatch.setattr(links.sys, "platform", "linux")
    for name in ("DISPLAY", "WAYLAND_DISPLAY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(display, ":fixture")
    monkeypatch.setenv("BROWSER", "fictional-browser --arbitrary-flag")
    lookup = Mock(return_value="/fixture/gio")
    launch = Mock(return_value=subprocess.CompletedProcess([], returncode))
    monkeypatch.setattr(links.shutil, "which", lookup)
    monkeypatch.setattr(links.subprocess, "run", launch)
    url = "https://example.invalid/a%20b?q=fictional%26value&next=%2Fdocs#part-2"

    assert open_link(url) is expected

    lookup.assert_called_once_with("gio")
    launch.assert_called_once_with(
        ["/fixture/gio", "open", "--", url],
        shell=False,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def test_linux_desktop_without_gio_reports_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(links.sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":fixture")
    monkeypatch.setenv("BROWSER", "fictional-browser --arbitrary-flag")
    lookup = Mock(return_value=None)
    monkeypatch.setattr(links.shutil, "which", lookup)

    assert open_link("https://example.invalid/docs") is LinkResult.UNAVAILABLE
    lookup.assert_called_once_with("gio")


@pytest.mark.parametrize("platform", ["linux", "darwin", "unsupported-fixture"])
def test_unsupported_environment_does_not_try_a_text_browser(
    monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    monkeypatch.setattr(links.sys, "platform", platform)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("BROWSER", "fictional-browser --arbitrary-flag")
    lookup = Mock()
    monkeypatch.setattr(links.shutil, "which", lookup)

    assert open_link("https://example.invalid/docs") is LinkResult.UNAVAILABLE
    lookup.assert_not_called()
