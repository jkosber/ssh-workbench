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
| Standalone TOML project loader and validation | Load configuration into the interface |
| Textual screen with a visible scaffold notice | Select projects and inspect their details |
| Q or Ctrl+Q to exit | Launch native SSH and return to the interface |
| `--help` and `--version` | Open useful documentation links |
| Tests, lint/format checks and package build | Approved usability checks |

The [example configuration](examples/projects.example.toml) contains fictional
data accepted by the loader. The CLI and screen do not load configuration yet;
that integration belongs to roadmap task 2. There are no SSH connections, remote
commands or infrastructure controls in this scaffold.

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

## Load project metadata

The Python API accepts an explicit `pathlib.Path`; there is no configuration CLI
option or default search path yet. From the repository directory, exercise the
fictional example with:

```text
uv run --locked python -c "from pathlib import Path; from ssh_workbench.config import load_projects; print(load_projects(Path('examples/projects.example.toml')))"
uv run --locked pytest tests/test_config.py -q
```

`load_projects(path)` reads UTF-8 TOML and returns a `list[Project]` in file order.
Each frozen record contains `id`, `name`, `ssh_alias`, `repository` and
`documentation`; absent optional references are `None`. `parse_projects(text)`
performs the same parsing and validation on an existing string. Both report
configuration problems through `ProjectConfigError`. Neither uses the metadata
to connect, execute commands, inspect repository locations or open links.

Schema version 1:

| Field | Rule |
| --- | --- |
| `schema_version` | Required integer `1`; booleans and floats are rejected |
| `projects` | Required array of tables, usually written as `[[projects]]`; `projects = []` returns an empty list |
| `projects[].id` | Required, unique lowercase ASCII letters/digits, with single hyphens between groups |
| `projects[].name` | Required string with at least one non-whitespace character |
| `projects[].ssh_alias` | Required string starting with an ASCII letter/digit, followed only by ASCII letters/digits, dots, underscores or hyphens |
| `projects[].repository` | Optional nonempty absolute HTTP/HTTPS URL without embedded credentials |
| `projects[].documentation` | Same URL rules as `repository` |

Unknown fields are rejected at both levels. References require a host and a valid
port if specified; raw whitespace, control characters and backslashes are
rejected. HTTP and HTTPS scheme matching is case-insensitive. Encoded spaces in
URL paths, query strings and fragments are allowed. These are syntax checks;
the loader does not resolve hosts or check whether a resource exists. Repository
paths and arbitrary SSH arguments remain deferred by the schema. Supplied values
are preserved, with no trimming or case conversion.

Parsing checks TOML syntax and converts it to Python values. Validation checks
those values against the schema. This configuration passes both:

```toml
schema_version = 1

[[projects]]
id = "garden-demo"
name = "Garden demo"
ssh_alias = "garden-demo-host"
```

Changing the last line to `ssh_alias = "--help"` still parses as TOML, but fails
validation at `projects[1].ssh_alias` because an alias cannot start with a dash.
A missing closing quote would instead be a parsing error.

Errors identify a field and a **one-based** project position where possible;
syntax errors give a line and column. Messages omit file paths, private values
and unknown key names; unknown-field errors list the allowed fields. The loader
stops at the first error and never returns partial results. It never creates or
overwrites configuration. Keep private files outside Git, for example in ignored
`.local/projects.toml`.

## Check a change

```text
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
uv run --locked python scripts/check_package.py
```

The last check installs the wheel and locked runtime dependencies in a temporary
environment, tests its help/version commands and loader with a fictional file,
then removes that environment.
CI runs these checks on Linux and Windows using the project Python version.
See [validation evidence](docs/validation.md) for actual results and limitations.

## Find your way around

| Path | Purpose |
| --- | --- |
| `src/ssh_workbench/` | Standalone metadata loader, CLI and Textual application |
| `tests/` | Metadata, CLI and headless UI tests |
| `examples/` | Fictional supported configuration |
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
