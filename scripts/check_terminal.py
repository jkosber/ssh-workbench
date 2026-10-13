"""Interactive terminal check with local children only; never invokes SSH."""

import argparse
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from ssh_workbench.app import SSHWorkbenchApp
from ssh_workbench.config import Project
from ssh_workbench.ssh import launch_ssh

CASES = {
    "fixture-zero": "Normal exit (0)",
    "fixture-seven": "Nonzero exit (7)",
    "fixture-interrupt": "Ctrl+C exits the child (130)",
    "fixture-continue": "Ctrl+C keeps the child running",
    "fixture-missing": "SSH unavailable (simulated)",
    "fixture-error": "Process start failure (simulated)",
    "fixture-keyboard": "Launch interrupted (simulated)",
}
RUN_CHILD = subprocess.run


def child(alias: str) -> int:
    streams = [stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr)]
    print(f"Local child: {alias}; terminal stdin/stdout/stderr: {streams}", flush=True)
    print("Local child stderr is visible.", file=sys.stderr, flush=True)
    if not all(streams):
        return 1
    while True:
        try:
            reply = input("Type return, or press Ctrl+C for an interruption check: ")
        except KeyboardInterrupt:
            print("\nChild received Ctrl+C.", flush=True)
            if alias == "fixture-continue":
                print(
                    "Child still owns the terminal; type return to finish.", flush=True
                )
                continue
            return 130
        print(f"Child input: {reply}", flush=True)
        if reply == "return":
            return 7 if alias == "fixture-seven" else 0


def launch_fixture(alias: str) -> int:
    if alias not in CASES:
        raise AssertionError("Only the built-in fictional aliases are permitted")
    executable = str(Path(sys.executable).resolve())

    def run_fixture(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        assert argv == [executable, alias]
        assert kwargs == {
            "shell": False,
            "check": False,
            "stdin": None,
            "stdout": None,
            "stderr": None,
        }
        if alias == "fixture-error":
            raise OSError("Simulated process start failure")
        if alias == "fixture-keyboard":
            raise KeyboardInterrupt
        return RUN_CHILD(
            [executable, str(Path(__file__).resolve()), "--child", alias], **kwargs
        )

    # Keep the production validation, signal handling and terminal handoff.
    # Both executable lookup and process invocation are replaced before launch.
    with (
        patch(
            "ssh_workbench.ssh.shutil.which",
            return_value=None if alias == "fixture-missing" else executable,
        ),
        patch("ssh_workbench.ssh.subprocess.run", run_fixture),
    ):
        return launch_ssh(alias)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(args.child)
    projects = [Project(alias, name, alias) for alias, name in CASES.items()]
    with patch("ssh_workbench.app.launch_ssh", launch_fixture):
        app = SSHWorkbenchApp(projects)
        app.run()
    return app.return_code


if __name__ == "__main__":
    raise SystemExit(main())
