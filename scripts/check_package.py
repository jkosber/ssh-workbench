"""Install the built wheel in a temporary environment and check its real CLI."""

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
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if expected not in result.stdout or result.stderr:
                raise SystemExit(f"Installed wheel CLI check failed: {option}")
    print("Built wheel: isolated installation, --help and --version passed.")


if __name__ == "__main__":
    main()
