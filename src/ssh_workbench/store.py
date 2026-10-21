"""Save the machine file: refuse outside changes, keep a backup, replace atomically."""

import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from ssh_workbench.config import (
    ConfigError,
    Machine,
    format_machines,
    read_machine_text,
)


class SaveError(Exception):
    """The machine file could not be saved; the message is safe to display."""


class FileChangedError(SaveError):
    """The file on disk is no longer the one Workbench loaded."""


def backup_path(path: Path) -> Path:
    return path.with_name(path.name + ".bak")


def save_machines(path: Path, machines: Sequence[Machine], expected: str | None) -> str:
    """Replace the file Workbench loaded as `expected` text and return the new text.

    `expected` is None when no file existed. If the file on disk differs, nothing
    is written, so an edit made elsewhere is never overwritten. The previous
    bytes are kept in `backup_path(path)`.
    """
    if not path.exists():
        current = None
    else:
        try:
            current = read_machine_text(path)
        except ConfigError as error:
            detail = str(error).removeprefix("configuration: ")
            raise SaveError(f"Could not save the machine file: {detail}.") from None
    if current != expected:
        raise FileChangedError("The machine file changed outside Workbench.")
    text = format_machines(machines)
    if text == current:
        # Nothing to change; keep the file's bytes and the previous backup.
        return text
    existing = path if current is not None else None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if existing is not None:
            _replace(backup_path(path), path.read_bytes(), mode_from=existing)
        _replace(path, text.encode("utf-8"), mode_from=existing)
    except OSError as error:
        reason = (
            "permission denied"
            if isinstance(error, PermissionError)
            else "could not write"
        )
        raise SaveError(f"Could not save the machine file: {reason}.") from None
    return text


def _replace(target: Path, data: bytes, mode_from: Path | None) -> None:
    # A temporary file in the same folder and os.replace mean a crash leaves
    # either the old file or the new one, never a half-written file.
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode_from is not None:
            shutil.copymode(mode_from, temporary)
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
