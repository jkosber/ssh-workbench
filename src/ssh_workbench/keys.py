"""Key login setup: public keys, new keys and the two fixed install commands.

Workbench reads only `.pub` files. The one variable part of an install command
is a public key line that `parse_public_key` accepted: a known type, strict
base64 and a comment of safe characters, so it sits inside shell and
PowerShell quotes as it is.
"""

import base64
import binascii
import re
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ssh_workbench.config import is_valid_key_path, is_valid_machine_id
from ssh_workbench.ssh import find_ssh_keygen

KEY_TYPES = frozenset(
    {
        "ssh-ed25519",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-rsa",
        "sk-ssh-ed25519@openssh.com",
        "sk-ecdsa-sha2-nistp256@openssh.com",
    }
)
_MAX_BYTES = 16 * 1024
_BASE64 = re.compile(r"[A-Za-z0-9+/]+={0,2}")
_COMMENT = re.compile(r"[A-Za-z0-9._@+-]+(?: [A-Za-z0-9._@+-]+)*")
_COMMENT_LENGTH = 100


class KeySetupError(Exception):
    """Key setup cannot go on; the message is safe to display."""


@dataclass(frozen=True)
class PublicKey:
    type: str
    blob: str
    comment: str | None = None

    @property
    def line(self) -> str:
        return " ".join(part for part in (self.type, self.blob, self.comment) if part)


def parse_public_key(text: str) -> PublicKey | None:
    """One OpenSSH public key line, or None. An unsafe comment is dropped."""
    for ending in ("\r\n", "\n"):
        if text.endswith(ending):
            text = text[: -len(ending)]
            break
    if len(text) > _MAX_BYTES or any(ord(c) < 32 or ord(c) == 127 for c in text):
        return None
    parts = text.split(" ", 2)
    if (
        len(parts) < 2
        or parts[0] not in KEY_TYPES
        or _BASE64.fullmatch(parts[1]) is None
    ):
        return None
    key_type, blob = parts[0], parts[1]
    try:
        strings = _ssh_strings(base64.b64decode(blob, validate=True))
    except binascii.Error, ValueError:
        return None
    if strings is None or len(strings) < 2 or strings[0] != key_type.encode():
        return None
    comment = parts[2] if len(parts) == 3 else None
    if comment is not None and (
        len(comment) > _COMMENT_LENGTH or _COMMENT.fullmatch(comment) is None
    ):
        comment = None
    return PublicKey(key_type, blob, comment)


def _ssh_strings(data: bytes) -> list[bytes] | None:
    """The length-prefixed strings of a key blob, or None unless they use it all."""
    strings: list[bytes] = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < 4:
            return None
        (length,) = struct.unpack_from(">I", data, offset)
        offset += 4
        if length > len(data) - offset:
            return None
        strings.append(data[offset : offset + length])
        offset += length
    return strings


def read_public_key(path: Path) -> PublicKey:
    try:
        with path.open("rb") as handle:
            data = handle.read(_MAX_BYTES + 1)
    except OSError:
        raise KeySetupError(
            f"Could not read {path.name}; nothing was installed."
        ) from None
    try:
        key = (
            parse_public_key(data.decode("ascii")) if len(data) <= _MAX_BYTES else None
        )
    except UnicodeDecodeError:
        key = None
    if key is None:
        raise KeySetupError(
            f"{path.name} is not a single valid OpenSSH public key; "
            "nothing was installed."
        )
    return key


def public_key_files(folder: Path) -> list[Path]:
    """The `.pub` files directly in the folder that hold one valid key, by name."""
    found: list[Path] = []
    try:
        candidates = sorted(folder.glob("*.pub"))
    except OSError:
        return found
    for path in candidates:
        try:
            if path.is_file():
                read_public_key(path)
                found.append(path)
        except KeySetupError, OSError:
            continue
    return found


def new_key_path(folder: Path, machine_id: str) -> Path:
    return folder / f"id_ed25519_{machine_id.replace('-', '_')}"


def keygen_arguments(path: Path, machine_id: str) -> list[str]:
    """`ssh-keygen` for a new Ed25519 key; it asks for the passphrase itself."""
    if not is_valid_machine_id(machine_id):
        raise KeySetupError("Invalid machine ID for a new key.")
    return [
        find_ssh_keygen(),
        "-t",
        "ed25519",
        "-f",
        str(path),
        "-C",
        f"ssh-workbench-{machine_id}",
    ]


def key_setting(path: Path, home: Path | None) -> str:
    """How the machine file names a chosen key; `home` is None for a test folder."""
    if home is not None and path.parent == home / ".ssh":
        setting = f"~/.ssh/{path.name}"
    else:
        setting = str(path)
    if not is_valid_key_path(setting):
        raise KeySetupError("Workbench can't save this key's path in the machine file.")
    return setting


def identity_paths(values: Iterable[str], folder: Path) -> list[Path]:
    """Key paths from `ssh -G`; `~` is the SSH folder's parent, as for `Include`."""
    paths: list[Path] = []
    for value in values:
        # Workbench does not expand SSH's own % and ${} tokens.
        if "%" in value or "${" in value:
            continue
        if value.startswith(("~/", "~\\")):
            path = folder.parent.joinpath(*re.split(r"[\\/]+", value[2:]))
        elif Path(value).is_absolute():
            path = Path(value)
        else:
            continue
        if path not in paths:
            paths.append(path)
    return paths


def posix_install_command(key: PublicKey) -> str:
    """Append the key to `~/.ssh/authorized_keys` once, with 700 and 600 modes.

    `exec sh -c` runs it the same from any login shell. The script holds no
    single quote and no `!` (tcsh history), and the key line needs no escaping
    inside double quotes. A copy on a comment line, as sshd reads them, does
    not count.
    """
    script = (
        'umask 077 && mkdir -p "$HOME/.ssh" && f="$HOME/.ssh/authorized_keys"'
        ' && touch "$f" && chmod 700 "$HOME/.ssh" && chmod 600 "$f"'
        f' && if grep -v "^[[:space:]]*#" "$f" | grep -qF "{key.blob}";'
        ' then echo "SSH Workbench: the key was already installed.";'
        ' else { if [ -s "$f" ] && [ -n "$(tail -c 1 "$f")" ]; then echo; fi;'
        f' echo "{key.line}"; }} >> "$f"'
        ' && echo "SSH Workbench: key installed."; fi'
    )
    return f"exec sh -c '{script}'"


# Windows OpenSSH runs commands through cmd.exe unless its DefaultShell is
# changed, so the script starts PowerShell explicitly. Administrators use the
# shared file sshd reads for the Administrators group; sshd ignores that file
# unless only SYSTEM and Administrators may access it. Without a console,
# progress records reach the terminal as CLIXML, so they are switched off.
_WINDOWS_SCRIPT = """$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$key = '@KEY@'
$blob = $key.Split(' ')[1]
$me = [Security.Principal.WindowsIdentity]::GetCurrent()
# Group claims include deny-only groups, so a filtered token still counts.
$admin = @($me.Claims | Where-Object { $_.Value -eq 'S-1-5-32-544' }).Count -gt 0
if ($admin) {
  $file = Join-Path (Join-Path $env:ProgramData 'ssh') 'administrators_authorized_keys'
} else {
  $folder = Join-Path $env:USERPROFILE '.ssh'
  New-Item -ItemType Directory -Force -Path $folder | Out-Null
  $file = Join-Path $folder 'authorized_keys'
}
$found = $false
if (Test-Path -LiteralPath $file) {
  # sshd skips comment lines, so a commented-out copy does not count.
  $found = [bool](Get-Content -LiteralPath $file |
    Where-Object { $_ -notmatch '^\\s*#' } |
    Select-String -SimpleMatch -Quiet -Pattern $blob)
}
if ($found) {
  'SSH Workbench: the key was already installed.'
} else {
  if ((Test-Path -LiteralPath $file) -and (Get-Item -LiteralPath $file).Length -gt 0) {
    $bytes = [IO.File]::ReadAllBytes($file)
    if ($bytes[-1] -ne 10) { [IO.File]::AppendAllText($file, "`r`n") }
  }
  [IO.File]::AppendAllText($file, $key + "`r`n")
  'SSH Workbench: key installed.'
}
if ($admin) {
  $acl = New-Object Security.AccessControl.FileSecurity
  $acl.SetAccessRuleProtection($true, $false)
  $sidType = [Security.Principal.SecurityIdentifier]
  foreach ($sid in 'S-1-5-32-544', 'S-1-5-18') {
    $who = New-Object Security.Principal.SecurityIdentifier $sid
    $rule = New-Object Security.AccessControl.FileSystemAccessRule(
      $who, 'FullControl', 'Allow')
    $acl.AddAccessRule($rule)
  }
  Set-Acl -LiteralPath $file -AclObject $acl
  $sids = (Get-Acl -LiteralPath $file).Access |
    ForEach-Object { $_.IdentityReference.Translate($sidType).Value } |
    Sort-Object -Unique
  if (($sids -join ',') -ne 'S-1-5-18,S-1-5-32-544') {
    throw 'The administrator key file kept other permissions.'
  }
}
"""


def windows_install_command(key: PublicKey) -> str:
    """The Windows OpenSSH install script, encoded so no shell reinterprets it."""
    script = _WINDOWS_SCRIPT.replace("@KEY@", key.line)
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"
