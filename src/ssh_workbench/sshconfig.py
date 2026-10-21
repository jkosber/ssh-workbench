"""List literal Host names from the user's SSH config; read nothing else.

Only `Host` and `Include` lines are interpreted. Key files, `known_hosts` and
`authorized_keys` are never opened, even when an `Include` names them.
"""

import glob
import os
import re
from pathlib import Path

from ssh_workbench.config import is_valid_ssh_alias

# OpenSSH stops following Include lines at the same depth.
_MAX_DEPTH = 16
_MAX_BYTES = 1_000_000
_KEYWORD = re.compile(r"\s*([A-Za-z]+)(?:\s*=\s*|\s+)(.*)")
_WORD = re.compile(r'"([^"]*)"|(\S+)')
_NEVER_READ = re.compile(r"id_.*|.*\.pub|known_hosts.*|authorized_keys.*", re.I)


def ssh_folder() -> Path | None:
    """The user's SSH folder, or SSH_WORKBENCH_SSH_DIR when it is absolute."""
    override = Path(os.environ.get("SSH_WORKBENCH_SSH_DIR", ""))
    if override.is_absolute():
        return override
    try:
        return Path.home() / ".ssh"
    except RuntimeError:
        return None


def host_names(folder: Path) -> list[str]:
    """Literal `Host` names from `folder/config` and its includes, first seen first.

    Patterns with `*`, `?` or `!` and names that fail the alias rule are skipped.
    In an `Include`, `~` means the folder's parent, so an overridden folder
    never leads back to the real one.
    """
    names: list[str] = []
    _read(folder / "config", folder, 0, set(), names)
    return names


def _read(
    path: Path, folder: Path, depth: int, seen: set[Path], names: list[str]
) -> None:
    if depth > _MAX_DEPTH or _NEVER_READ.fullmatch(path.name):
        return
    try:
        resolved = path.resolve()
        if resolved in seen or not path.is_file() or path.stat().st_size > _MAX_BYTES:
            return
        seen.add(resolved)
        text = path.read_bytes().decode("utf-8", "replace")
    except OSError, RuntimeError, ValueError:
        return
    for line in text.splitlines():
        match = _KEYWORD.match(line)
        if match is None:
            continue
        keyword = match.group(1).lower()
        if keyword == "host":
            for word in _words(match.group(2)):
                if (
                    not any(character in word for character in "*?!")
                    and is_valid_ssh_alias(word)
                    and word not in names
                ):
                    names.append(word)
        elif keyword == "include":
            for word in _words(match.group(2)):
                for target in _include_targets(word, folder):
                    _read(target, folder, depth + 1, seen, names)


def _words(text: str) -> list[str]:
    words = []
    for match in _WORD.finditer(text):
        quoted, plain = match.groups()
        if plain is not None and plain.startswith("#"):
            break
        words.append(quoted if quoted is not None else plain)
    return words


def _include_targets(word: str, folder: Path) -> list[Path]:
    if word == "~" or word.startswith(("~/", "~\\")):
        pattern = folder.parent / word[2:]
    elif Path(word).is_absolute():
        pattern = Path(word)
    else:
        pattern = folder / word
    # OpenSSH reads the files a pattern matches in lexical order.
    return [Path(match) for match in sorted(glob.glob(str(pattern)))]
