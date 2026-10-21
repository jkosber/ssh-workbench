"""Public keys, new key names and the fixed install commands; fictional keys only.

The keys here are built from fixed bytes: they have the OpenSSH public format
and no private half. The install commands run only against temporary folders.
"""

import base64
import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from ssh_workbench import keys
from ssh_workbench.keys import (
    KEY_TYPES,
    KeySetupError,
    PublicKey,
    identity_paths,
    key_setting,
    keygen_arguments,
    new_key_path,
    parse_public_key,
    posix_install_command,
    public_key_files,
    read_public_key,
    windows_install_command,
)


def blob(key_type: str, payload: bytes = b"\x01" * 32) -> str:
    """Base64 in the OpenSSH layout: a length-prefixed type, then key data."""
    data = (
        struct.pack(">I", len(key_type))
        + key_type.encode()
        + struct.pack(">I", len(payload))
        + payload
    )
    return base64.b64encode(data).decode()


ED_BLOB = blob("ssh-ed25519")
ED_LINE = f"ssh-ed25519 {ED_BLOB} dev@workstation"
ED_KEY = PublicKey("ssh-ed25519", ED_BLOB, "dev@workstation")


def test_a_public_key_line_parses() -> None:
    assert parse_public_key(ED_LINE + "\n") == ED_KEY
    assert parse_public_key(ED_LINE + "\r\n") == ED_KEY
    assert parse_public_key(ED_LINE) == ED_KEY
    assert ED_KEY.line == ED_LINE


@pytest.mark.parametrize("key_type", sorted(KEY_TYPES))
def test_every_known_key_type_parses(key_type: str) -> None:
    assert parse_public_key(f"{key_type} {blob(key_type)}") == PublicKey(
        key_type, blob(key_type), None
    )


def test_known_key_types() -> None:
    assert KEY_TYPES == {
        "ssh-ed25519",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-rsa",
        "sk-ssh-ed25519@openssh.com",
        "sk-ecdsa-sha2-nistp256@openssh.com",
    }


@pytest.mark.parametrize(
    "text",
    [
        "",
        "ssh-ed25519",
        f"ssh-ed25519 {ED_BLOB} one\nssh-ed25519 {ED_BLOB} two",
        f"{ED_LINE}\n\n",
        f"ssh-dss {blob('ssh-dss')}",
        f"ssh-ed25519 {blob('ssh-rsa')}",
        f"ssh-ed25519 {ED_BLOB[:-4]}",
        f"ssh-ed25519 {ED_BLOB}$x",
        f"ssh-ed25519\t{ED_BLOB}",
        f"ssh-ed25519  {ED_BLOB}",
        f" ssh-ed25519 {ED_BLOB}",
        f"ssh-ed25519 {ED_BLOB}\0",
        "ssh-ed25519 AAAA",
        f'from="192.0.2.1" ssh-ed25519 {ED_BLOB}',
        f"ssh-ed25519 {blob('ssh-ed25519', b'\x01' * 16_384)}",
    ],
)
def test_anything_else_is_not_a_public_key(text: str) -> None:
    assert parse_public_key(text) is None


@pytest.mark.parametrize(
    "comment",
    [
        "dev@host; rm -rf ~",
        '"quoted"',
        "$(whoami)",
        "it's",
        "DOMAIN\\dev",
        "café",
        "trailing ",
        "x" * 101,
    ],
)
def test_an_unsafe_comment_is_dropped(comment: str) -> None:
    assert parse_public_key(f"ssh-ed25519 {ED_BLOB} {comment}") == PublicKey(
        "ssh-ed25519", ED_BLOB, None
    )


def test_a_safe_comment_with_spaces_is_kept() -> None:
    line = f"ssh-ed25519 {ED_BLOB} dev@work station-2 key.v1+old_x"
    assert parse_public_key(line) == PublicKey(
        "ssh-ed25519", ED_BLOB, "dev@work station-2 key.v1+old_x"
    )


def test_read_public_key(tmp_path: Path) -> None:
    good = tmp_path / "id_good.pub"
    good.write_bytes((ED_LINE + "\n").encode())
    assert read_public_key(good) == ED_KEY

    for name, data in (
        ("id_two.pub", (ED_LINE + "\n" + ED_LINE + "\n").encode()),
        ("id_big.pub", b" " * 16_385),
        ("id_bytes.pub", b"\xff\xfe"),
    ):
        (tmp_path / name).write_bytes(data)
        with pytest.raises(KeySetupError) as caught:
            read_public_key(tmp_path / name)
        assert str(caught.value) == (
            f"{name} is not a single valid OpenSSH public key; nothing was installed."
        )

    with pytest.raises(KeySetupError) as caught:
        read_public_key(tmp_path / "id_missing.pub")
    assert str(caught.value) == "Could not read id_missing.pub; nothing was installed."


def test_public_key_files_are_valid_pub_files_by_name(tmp_path: Path) -> None:
    folder = tmp_path / ".ssh"
    folder.mkdir()
    (folder / "id_b.pub").write_text(ED_LINE + "\n", encoding="ascii")
    (folder / "id_a.pub").write_text(ED_LINE + "\n", encoding="ascii")
    (folder / "id_bad.pub").write_text("not a key\n", encoding="ascii")
    (folder / "id_c").write_text("private half, never read\n", encoding="ascii")
    (folder / "config").write_text("Host x\n", encoding="ascii")
    (folder / "dir.pub").mkdir()

    assert public_key_files(folder) == [folder / "id_a.pub", folder / "id_b.pub"]
    assert public_key_files(tmp_path / "missing") == []


def test_new_key_path_is_named_for_the_machine(tmp_path: Path) -> None:
    assert new_key_path(tmp_path, "agent-box") == tmp_path / "id_ed25519_agent_box"


def test_keygen_arguments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(keys, "find_ssh_keygen", lambda: "/usr/bin/ssh-keygen")
    path = tmp_path / "id_ed25519_agent_box"

    assert keygen_arguments(path, "agent-box") == [
        "/usr/bin/ssh-keygen",
        "-t",
        "ed25519",
        "-f",
        str(path),
        "-C",
        "ssh-workbench-agent-box",
    ]
    with pytest.raises(KeySetupError):
        keygen_arguments(path, "-oProxyCommand=x")


def test_key_setting(tmp_path: Path) -> None:
    home = tmp_path / "home"
    assert key_setting(home / ".ssh" / "id_box", home) == "~/.ssh/id_box"
    assert key_setting(tmp_path / "ssh" / "id_box", None) == str(
        tmp_path / "ssh" / "id_box"
    )
    assert key_setting(tmp_path / "keys" / "id_box", home) == str(
        tmp_path / "keys" / "id_box"
    )
    with pytest.raises(KeySetupError) as caught:
        key_setting(tmp_path / "keys" / "id_%h", None)
    assert str(caught.value) == (
        "Workbench can't save this key's path in the machine file."
    )


def test_identity_paths(tmp_path: Path) -> None:
    folder = tmp_path / "home" / ".ssh"
    absolute = tmp_path / "keys" / "id_abs"

    assert identity_paths(
        [
            "~/.ssh/id_lab",
            "~\\keys\\id_win",
            str(absolute),
            "relative/id_rel",
            "~/.ssh/id_%h",
            "${HOME}/.ssh/id_env",
            "~/.ssh/id_lab",
        ],
        folder,
    ) == [
        tmp_path / "home" / ".ssh" / "id_lab",
        tmp_path / "home" / "keys" / "id_win",
        absolute,
    ]


def test_posix_install_command_text() -> None:
    assert posix_install_command(ED_KEY) == (
        "exec sh -c '"
        'umask 077 && mkdir -p "$HOME/.ssh" && f="$HOME/.ssh/authorized_keys"'
        ' && touch "$f" && chmod 700 "$HOME/.ssh" && chmod 600 "$f"'
        f' && if grep -qF "{ED_BLOB}" "$f";'
        ' then echo "SSH Workbench: the key was already installed.";'
        ' else { if [ -s "$f" ] && [ -n "$(tail -c 1 "$f")" ]; then echo; fi;'
        f' echo "{ED_LINE}"; }} >> "$f"'
        ' && echo "SSH Workbench: key installed."; fi'
        "'"
    )


def posix_shell() -> str:
    found = shutil.which("sh")
    if found is None and os.name == "nt":
        git_shell = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        git_shell = git_shell / "Git" / "bin" / "sh.exe"
        found = str(git_shell) if git_shell.is_file() else None
    assert found is not None, "A POSIX sh is needed to run the install command"
    return found


def install_with_sh(home: Path, key: PublicKey) -> str:
    result = subprocess.run(
        [posix_shell(), "-c", posix_install_command(key)],
        env={**os.environ, "HOME": home.as_posix()},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_posix_install_adds_the_key_once(tmp_path: Path) -> None:
    keys_file = tmp_path / ".ssh" / "authorized_keys"

    assert install_with_sh(tmp_path, ED_KEY) == "SSH Workbench: key installed.\n"
    assert install_with_sh(tmp_path, ED_KEY) == (
        "SSH Workbench: the key was already installed.\n"
    )

    assert keys_file.read_bytes() == (ED_LINE + "\n").encode()
    if os.name == "posix":
        assert keys_file.parent.stat().st_mode & 0o777 == 0o700
        assert keys_file.stat().st_mode & 0o777 == 0o600


def test_posix_install_keeps_existing_lines_whole(tmp_path: Path) -> None:
    keys_file = tmp_path / ".ssh" / "authorized_keys"
    keys_file.parent.mkdir()
    other = f"ssh-ed25519 {blob('ssh-ed25519', b'\x02' * 32)} other"
    keys_file.write_bytes(other.encode())

    install_with_sh(tmp_path, ED_KEY)

    assert keys_file.read_bytes() == f"{other}\n{ED_LINE}\n".encode()


def test_posix_install_finds_the_key_behind_options(tmp_path: Path) -> None:
    keys_file = tmp_path / ".ssh" / "authorized_keys"
    keys_file.parent.mkdir()
    existing = f'from="192.0.2.0/24" ssh-ed25519 {ED_BLOB} old comment\n'
    keys_file.write_bytes(existing.encode())

    assert install_with_sh(tmp_path, ED_KEY) == (
        "SSH Workbench: the key was already installed.\n"
    )
    assert keys_file.read_bytes() == existing.encode()


PREFIX = "powershell -NoProfile -NonInteractive -EncodedCommand "


def windows_script(key: PublicKey) -> str:
    command = windows_install_command(key)
    assert command.startswith(PREFIX)
    return base64.b64decode(command.removeprefix(PREFIX)).decode("utf-16-le")


def test_windows_install_script_holds_the_key_once() -> None:
    script = windows_script(ED_KEY)

    assert script.startswith("$ErrorActionPreference = 'Stop'\n")
    assert script.count(ED_LINE) == 1
    assert f"$key = '{ED_LINE}'\n" in script
    for fact in (
        "'S-1-5-32-544'",
        "'S-1-5-18'",
        "'administrators_authorized_keys'",
        "$env:ProgramData",
        "$env:USERPROFILE",
        "SetAccessRuleProtection($true, $false)",
        "Set-Acl",
        "-SimpleMatch",
        "SSH Workbench: key installed.",
        "SSH Workbench: the key was already installed.",
    ):
        assert fact in script, fact


def test_windows_install_script_parses(tmp_path: Path) -> None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None, "PowerShell is needed to parse the Windows script"
    script = tmp_path / "install.ps1"
    script.write_text(windows_script(ED_KEY), encoding="utf-8-sig")
    checker = tmp_path / "check.ps1"
    checker.write_text(
        "param($Path)\n"
        "$errors = $null\n"
        "$null = [System.Management.Automation.Language.Parser]::ParseFile("
        "$Path, [ref]$null, [ref]$errors)\n"
        "$errors.Count\n",
        encoding="utf-8-sig",
    )

    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(checker),
            str(script),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert (result.returncode, result.stdout.strip()) == (0, "0"), result.stderr


def test_windows_command_fits_cmd_with_a_large_rsa_key() -> None:
    rsa = PublicKey("ssh-rsa", blob("ssh-rsa", b"\x01" * 535), "dev@workstation")

    assert len(windows_install_command(rsa)) < 8191


def install_with_powershell(home: Path, key: PublicKey) -> str:
    """Run the Windows script's standard-user branch with USERPROFILE in `home`.

    The administrator lines are replaced: that branch would change real ACLs.
    """
    script = windows_script(key)
    lines = script.splitlines(keepends=True)
    detect = [line for line in lines if line.startswith(("$me = ", "$admin = "))]
    assert len(detect) == 2
    for line in detect:
        script = script.replace(line, "")
    script = "$admin = $false\n" + script
    # Windows targets run Windows PowerShell 5.1; elsewhere pwsh runs the script.
    shell = shutil.which("powershell") or shutil.which("pwsh")
    assert shell is not None, "PowerShell is needed to run the Windows script"
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        env={**os.environ, "USERPROFILE": str(home)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_windows_install_adds_the_key_once_for_a_standard_user(
    tmp_path: Path,
) -> None:
    keys_file = tmp_path / ".ssh" / "authorized_keys"

    assert install_with_powershell(tmp_path, ED_KEY) == (
        "SSH Workbench: key installed.\n"
    )
    assert install_with_powershell(tmp_path, ED_KEY) == (
        "SSH Workbench: the key was already installed.\n"
    )

    assert keys_file.read_bytes() == (ED_LINE + "\r\n").encode()


def test_windows_install_keeps_existing_lines_whole(tmp_path: Path) -> None:
    keys_file = tmp_path / ".ssh" / "authorized_keys"
    keys_file.parent.mkdir()
    keys_file.write_bytes(b"other")

    install_with_powershell(tmp_path, ED_KEY)

    assert keys_file.read_bytes() == f"other\r\n{ED_LINE}\r\n".encode()
