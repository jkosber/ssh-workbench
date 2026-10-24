"""Interactive key-setup check with local children only; never runs ssh-keygen or SSH.

The app runs on fictional machines in a working folder. Each handed-off step
starts a local child that says which step it stands for, waits for "return" or
Ctrl+C and exits with the status chosen on the command line, as Windows ssh can
exit 0 after Ctrl+C. The key-generation child writes a fictional key pair:
fixed bytes in the OpenSSH public format, never a usable key. No network is
used: the status checker reports every port closed.
"""

import argparse
import base64
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Machine, format_machines, read_machines
from ssh_workbench.status import AliasTarget

STEPS = ("keygen", "install", "test")
SSH_FIXTURE = "ssh-fixture"
KEYGEN_FIXTURE = "ssh-keygen-fixture"
MACHINES = (
    Machine("box", "Box", user="dev", addresses=("192.0.2.60",)),
    Machine("garden", "Garden", alias="garden-host"),
)


def fictional_public_key(seed: int, comment: str) -> str:
    data = (
        struct.pack(">I", 11)
        + b"ssh-ed25519"
        + struct.pack(">I", 32)
        + bytes([seed]) * 32
    )
    return f"ssh-ed25519 {base64.b64encode(data).decode()} {comment}"


def child(step: str, status: int, target: str | None) -> int:
    print(f"Local child for the {step} step; it exits with status {status}.")
    if step == "install" and target:
        system = "POSIX" if target.startswith("exec sh -c ") else "Windows"
        print(f"Install command for a {system} target, {len(target)} characters.")
    if step == "keygen" and target:
        Path(target).write_text("fictional private half\n", encoding="ascii")
        Path(f"{target}.pub").write_text(
            fictional_public_key(9, "ssh-workbench-box") + "\n", encoding="ascii"
        )
    try:
        while input("Type return to finish this step: ") != "return":
            pass
    except KeyboardInterrupt:
        print(f"\nThe child received Ctrl+C and exits with status {status}.")
    return status


class FictionalChecker:
    """Every port is closed; the alias names two fictional keys, and only
    id_lab has a .pub, so the picker lists it and names id_work below."""

    def resolve_alias(self, alias: str) -> AliasTarget | None:
        return AliasTarget(
            "192.0.2.10",
            22,
            proxied=False,
            user="dev",
            identity_files=("~/ssh/id_lab", "~/ssh/id_work"),
            identities_only=True,
        )

    def port_open(self, host: str, port: int) -> bool:
        return False


def prepare(folder: Path) -> Path:
    ssh = folder / "ssh"
    ssh.mkdir(parents=True, exist_ok=True)
    (ssh / "config").write_text("Host garden-host\n    HostName 192.0.2.10\n", "ascii")
    for seed, name in ((1, "id_a"), (4, "id_lab")):
        (ssh / f"{name}.pub").write_text(
            fictional_public_key(seed, name) + "\n", encoding="ascii"
        )
    (ssh / "id_work").write_text("fictional private half\n", encoding="ascii")
    path = folder / "machines.toml"
    # A second run in the same folder shows the key the first one saved.
    if not path.exists():
        path.write_text(format_machines(MACHINES), encoding="utf-8")
    os.environ["SSH_WORKBENCH_SSH_DIR"] = str(ssh)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", choices=STEPS, help=argparse.SUPPRESS)
    parser.add_argument("--target", help=argparse.SUPPRESS)
    for step in STEPS:
        parser.add_argument(
            f"--{step}-status",
            type=int,
            default=0,
            help=f"exit status of the {step} child (default 0)",
        )
    parser.add_argument(
        "--folder", type=Path, help="working folder; a new temporary one by default"
    )
    args = parser.parse_args()
    statuses = {step: getattr(args, f"{step}_status") for step in STEPS}
    if args.child:
        return child(args.child, statuses[args.child], args.target)

    script = str(Path(__file__).resolve())

    def run_child(arguments: list[str], name: str = "SSH") -> int:
        if arguments[0] == KEYGEN_FIXTURE:
            step, target = "keygen", arguments[arguments.index("-f") + 1]
        elif arguments[-1] == "exit":
            step, target = "test", None
        else:
            step, target = "install", arguments[-1]
        assert arguments[0] in (SSH_FIXTURE, KEYGEN_FIXTURE)
        command = [sys.executable, script, "--child", step]
        command += [f"--{step}-status", str(statuses[step])]
        if target is not None:
            command += ["--target", target]
        return subprocess.run(command, shell=False, check=False).returncode

    folder = args.folder or Path(tempfile.mkdtemp(prefix="ssh-workbench-keys-"))
    path = prepare(folder.resolve())
    print(f"Working folder: {folder}")
    with (
        patch("ssh_workbench.app.run_native", run_child),
        patch("ssh_workbench.app.find_ssh", return_value=SSH_FIXTURE),
        patch("ssh_workbench.keys.find_ssh_keygen", return_value=KEYGEN_FIXTURE),
    ):
        machines, text = read_machines(path)
        app = SSHWorkbenchApp(
            machines, config_path=path, file_text=text, checker=FictionalChecker()
        )
        app.run()
    return app.return_code or 0


if __name__ == "__main__":
    raise SystemExit(main())
