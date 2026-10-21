"""Check the installed wheel's CLI and substituted SSH/browser actions in isolation."""

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    wheel = root / "dist" / f"ssh_workbench-{version}-py3-none-any.whl"
    if not wheel.is_file():
        raise SystemExit("Build the wheel first with: uv build")
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv must be available on PATH.")
    smoke = root / "scripts" / "package_smoke.py"

    with tempfile.TemporaryDirectory(prefix="ssh-workbench-package-") as directory:
        temporary = Path(directory)
        environment = temporary / "venv"
        requirements = temporary / "requirements.txt"
        subprocess.run(
            [uv, "venv", "--python", sys.executable, str(environment)], check=True
        )
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        cli = scripts / ("ssh-workbench.exe" if os.name == "nt" else "ssh-workbench")
        cli_environment = os.environ.copy()
        cli_environment.pop("PYTHONPATH", None)
        cli_environment.pop("PYTHONHOME", None)
        # The add form reads Host names; never let it reach the real SSH folder.
        cli_environment["SSH_WORKBENCH_SSH_DIR"] = str(temporary / "no-ssh-folder")
        isolated_environment = cli_environment | {"PYTHONPATH": str(root / "src")}
        smoke_command = [str(python), "-I", str(smoke), str(environment)]
        subprocess.run(
            [
                uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [uv, "pip", "sync", "--python", str(python), str(requirements)],
            check=True,
        )
        subprocess.run(
            [uv, "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
            check=True,
        )
        for option, expected in [
            ("--help", "usage: ssh-workbench"),
            ("--version", f"ssh-workbench {version}"),
        ]:
            result = subprocess.run(
                [str(cli), option],
                cwd=temporary,
                env=cli_environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if expected not in result.stdout or result.stderr:
                raise SystemExit(f"Installed wheel CLI check failed: {option}")
        missing = temporary / "missing-private-marker.toml"
        result = subprocess.run(
            [str(cli), "--config", str(missing)],
            cwd=temporary,
            env=cli_environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if (
            result.returncode != 2
            or result.stdout
            or "configuration: file not found" not in result.stderr
            or "private-marker" in result.stderr
            or "Traceback" in result.stderr
            or missing.exists()
        ):
            raise SystemExit("Installed wheel CLI check failed: missing configuration")
        fixture = temporary / "machines.toml"
        fixture.write_text(
            'schema_version = 2\n[[machines]]\nid = "package-demo"\n'
            'name = "Package demo"\nalias = "package-demo-host"\n'
            '[[machines]]\nid = "package-direct"\nname = "Package direct"\n'
            'user = "demo"\naddresses = ["192.0.2.10"]\nport = 2222\n'
            '[[machines.links]]\nname = "Dashboard"\nurl = "https://192.0.2.10:8006"\n',
            encoding="utf-8",
        )
        subprocess.run(
            [*smoke_command, "loader"],
            cwd=temporary,
            env=isolated_environment,
            check=True,
            timeout=10,
        )
        browser_fixture = temporary / "browser-projects.toml"
        original = (
            b'schema_version = 1\n[[projects]]\nid = "package-first"\n'
            b'name = "Package [b]first[/b]"\nssh_alias = "fictional-first"\n'
            b'repository = "https://example.invalid/first?q=fictional%26query#repository"\n'
            b'documentation = "https://example.invalid/first/docs#start"\n'
            b'[[projects]]\nid = "package-second"\n'
            b'name = "Package second"\nssh_alias = "fictional-second"\n'
        )
        browser_fixture.write_bytes(original)
        subprocess.run(
            [*smoke_command, "app"],
            cwd=temporary,
            env=isolated_environment,
            check=True,
            timeout=30,
        )
        if browser_fixture.read_bytes() != original:
            raise SystemExit("Installed wheel modified its machine file")
        for key in ("q", "ctrl+q"):
            result = subprocess.run(
                [*smoke_command, "quit", key],
                cwd=temporary,
                env=isolated_environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if (
                result.stdout.strip() != "Blocked opener: quit completed"
                or result.stderr
            ):
                raise SystemExit(
                    f"Installed wheel blocked-opener quit check failed: {key}"
                )
        result = subprocess.run(
            [*smoke_command, "save"],
            cwd=temporary,
            env=isolated_environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        if result.stdout.strip() != "Saved machine file: created and loaded back":
            raise SystemExit("Installed wheel save check failed")
    print(
        "Built wheel: isolated installation, help/version, configuration errors, "
        "verified installed import paths, machine loader, headless selection/quit, "
        "substituted SSH/link results, blocked-opener Q/Ctrl+Q exit and a first "
        "save passed."
    )


if __name__ == "__main__":
    main()
