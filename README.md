# SSH Workbench

A project-aware terminal interface for keeping SSH aliases and project context
together. The goal is to select a project, see its host and useful references,
and connect through the existing native SSH client. This is a first larger
version-controlled program being developed in small, reviewable steps.

## Current status

**0.0.1 is an unreleased development scaffold.** The first usable release target
is 0.1.0; it has not been released.

| Works now | Planned |
| --- | --- |
| Textual screen with a visible scaffold notice | Load and validate project configuration |
| Q or Ctrl+Q to exit | Select projects and inspect their details |
| `--help` and `--version` | Launch native SSH and return to the interface |
| Tests, lint/format checks and package build | Open useful documentation links |

The [example configuration](examples/projects.example.toml) is fictional and
illustrative. The application does not read it yet. There are no SSH connections,
remote commands or infrastructure controls in this scaffold.

The application requires no Codex, ChatGPT, OpenAI API key or AI subscription.

## Install and run

Prerequisites: Git, [uv](https://docs.astral.sh/uv/getting-started/installation/)
and a terminal. Development uses Python **3.14.7**, recorded in `.python-version`;
the package declares **Python >=3.14**. uv uses the matching interpreter or can
download a project interpreter without replacing system Python.

From the repository directory, in PowerShell or a POSIX shell:

```text
uv sync --locked
uv run --locked ssh-workbench --help
uv run --locked ssh-workbench --version
uv run --locked ssh-workbench
```

Press **Q** or **Ctrl+Q** to close the screen. `uv sync` creates the local `.venv`
and installs the package and development tools. No environment activation is
needed when using `uv run`. Initial dependency installation needs network access;
the installed scaffold runs locally.

## Check a change

```text
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
uv run --locked python scripts/check_package.py
```

The last check installs the wheel and locked runtime dependencies in a temporary
environment, tests its help and version commands, and removes that environment.
CI runs these checks on Linux and Windows using the project Python version.
See [validation evidence](docs/validation.md) for actual results and limitations.

## Find your way around

| Path | Purpose |
| --- | --- |
| `src/ssh_workbench/` | CLI and Textual application |
| `tests/` | CLI and headless UI tests |
| `examples/` | Fictional planned configuration |
| `scripts/check_package.py` | Isolated built-package check |
| `pyproject.toml`, `uv.lock` | Package metadata, version, dependencies and resolved versions |
| `.github/` | CI and the short pull-request template |

- [CONTRIBUTING](CONTRIBUTING.md): everyday development, Git recovery and releases.
- [AGENTS](AGENTS.md): project-specific coding-agent instructions.
- [Changelog](CHANGELOG.md): meaningful changes under Unreleased.
- [Architecture](docs/architecture.md): design decisions and SSH safety boundaries.
- [Roadmap](docs/roadmap.md): the single backlog and task acceptance criteria.
- [Publishing](docs/publishing.md): future portfolio and guide readiness.

Private configuration and machine-specific notes belong in ignored `.local/`.
Review files before staging; ignore rules cannot identify every possible secret.
No license has been selected. Resolve licensing before any public release.
