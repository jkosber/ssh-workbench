"""Host names from fictional SSH config folders; only Host and Include lines count."""

from pathlib import Path

import pytest

from ssh_workbench import sshconfig
from ssh_workbench.sshconfig import host_names, ssh_folder


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_literal_host_names_in_first_seen_order(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    write(
        folder,
        "config",
        "Host alpha beta\n"
        "    HostName 192.0.2.1\n"
        "Host *.wild !negated gamma? delta\n"
        "host   Echo\n"
        "HOST=foxtrot\n"
        "Host\talpha\n"
        "Match host zulu\n"
        "# Host commented\n"
        '  Host "quoted-name" bad@name -option\n'
        "Host golf # trailing comment\n",
    )

    assert host_names(folder) == [
        "alpha",
        "beta",
        "delta",
        "Echo",
        "foxtrot",
        "quoted-name",
        "golf",
    ]


def test_includes_are_followed_in_order(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    absolute = write(tmp_path, "absolute.conf", "Host absolute\n")
    write(
        folder,
        "config",
        "Include config.d/*.conf\n"
        "Include ~/.ssh/extra missing-file nothing/*.conf\n"
        "Host main\n"
        f'Include "{absolute}"\n',
    )
    write(folder, "config.d/b.conf", "Host bee\n")
    write(folder, "config.d/a.conf", "Host ay\n")
    write(folder, "extra", "Host extra-host\n")

    assert host_names(folder) == ["ay", "bee", "extra-host", "main", "absolute"]


def test_include_cycles_end(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include a\nHost root\n")
    write(folder, "a", "Include config a\nHost in-a\n")

    assert host_names(folder) == ["in-a", "root"]


def test_include_depth_is_limited(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include f1\nHost h0\n")
    for level in range(1, 21):
        write(folder, f"f{level}", f"Include f{level + 1}\nHost h{level}\n")

    assert host_names(folder) == [f"h{level}" for level in range(16, -1, -1)]


def test_key_and_known_hosts_files_are_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / ".ssh"
    write(
        folder,
        "config",
        "Include id_ed25519 id_ed25519.pub keys.PUB known_hosts known_hosts.old "
        "authorized_keys other.conf\n",
    )
    for name in (
        "id_ed25519",
        "id_ed25519.pub",
        "keys.PUB",
        "known_hosts",
        "known_hosts.old",
        "authorized_keys",
    ):
        write(folder, name, "Host leaked\n")
    write(folder, "other.conf", "Host fine\n")
    read = []
    original = Path.read_bytes

    def spy(path: Path) -> bytes:
        read.append(path.name)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", spy)

    assert host_names(folder) == ["fine"]
    assert read == ["config", "other.conf"]


def test_other_key_file_names_are_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include *\n")
    for name in ("work.pem", "putty.PPK", "server.key", "github_ed25519.pub"):
        write(folder, name, "Host leaked\n")
    write(folder, "other.conf", "Host fine\n")
    read = []
    original = Path.read_bytes

    def spy(path: Path) -> bytes:
        read.append(path.name)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", spy)

    assert host_names(folder) == ["fine"]
    assert sorted(read) == ["config", "other.conf"]


def test_unreadable_and_oversized_files_are_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / ".ssh"
    write(folder, "config", "Include locked big folder\nHost kept\n")
    write(folder, "locked", "Host locked-host\n")
    write(folder, "big", "Host big-host\n" + "#" * 1_100_000)
    (folder / "folder").mkdir()
    original = Path.read_bytes

    def deny(path: Path) -> bytes:
        if path.name == "locked":
            raise PermissionError("private-marker")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", deny)

    assert host_names(folder) == ["kept"]


def test_missing_config_has_no_names(tmp_path: Path) -> None:
    assert host_names(tmp_path / ".ssh") == []


def test_ssh_folder_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)

    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", str(tmp_path / "fictional"))
    assert ssh_folder() == tmp_path / "fictional"
    monkeypatch.setenv("SSH_WORKBENCH_SSH_DIR", "relative")
    assert ssh_folder() == home / ".ssh"
    monkeypatch.delenv("SSH_WORKBENCH_SSH_DIR")
    assert ssh_folder() == home / ".ssh"

    def no_home() -> Path:
        raise RuntimeError("no home")

    monkeypatch.setattr(Path, "home", no_home)
    assert ssh_folder() is None


def test_reader_has_no_process_or_network_access() -> None:
    source = Path(sshconfig.__file__).read_text(encoding="utf-8")
    for name in ("subprocess", "socket", "os.system"):
        assert name not in source
