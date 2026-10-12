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
| Explicit `--config PATH` with TOML validation | Launch native SSH and return to the interface |
| Keyboard project selection and read-only details | Open useful documentation links |
| Q or Ctrl+Q to exit; `--help` and `--version` | Approved usability checks |
| Tests, lint/format checks and package build | 0.1.0 readiness review |

The [example configuration](examples/projects.example.toml) contains fictional
data for trying the browser. There are no SSH connections, remote commands,
link-opening actions or infrastructure controls in this development build.

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
uv run --locked ssh-workbench --config examples/projects.example.toml
```

Press **Q** or **Ctrl+Q** to close the screen. `uv sync` creates the local `.venv`
and installs the package and development tools. No environment activation is
needed when using `uv run`. Initial dependency installation needs network access;
the installed application runs locally.

Without `--config`, an informative empty development screen explains how to load
projects. No default file is read and the example is never loaded automatically.
An explicit path is relative to the current directory unless absolute; quote
paths containing spaces. The application only reads the requested file and never
creates or overwrites configuration. An invalid or unreadable file produces a
concise error on stderr and exits with status 2 before starting the TUI.
`--help` and `--version` exit without reading configuration, even when `--config`
is also supplied.

## Browse projects

The list preserves file order, with the first project selected and focused at
startup. **Up/Down** changes the selection and immediately updates the details.
The highlighted row marks the selection; the accent border marks keyboard focus.
**Tab** and **Shift+Tab** move focus between the list and details. In the details
pane, use **Up/Down**, **Page Up/Page Down**, or **Home/End** to scroll.

Details show the selected project's ID, name, SSH alias, repository and
documentation. Missing optional references show `Not provided`. A configuration
with `projects = []` shows a separate empty-project message. Restart the app to
read file changes; editing and reloading are not implemented.

Long names are shortened visually in the list; full values wrap in the scrollable
details pane. Unicode text is preserved. Nonprinting characters, including
newlines, tabs, terminal escapes and direction controls, appear as visible
Python-style escapes such as `\n`, `\x1b` and `\u202e`. Only the display changes;
the original project records are retained. Markup-like strings are literal text.
References have no application-generated hyperlinks or actions. A terminal may
independently recognize URL text; SSH Workbench does not open it.

## Load project metadata

The standalone Python API accepts an explicit `pathlib.Path`. It uses the same
loader as `--config`, with no default search path. From the repository directory,
exercise the fictional example without the TUI with:

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
environment and tests help/version, a missing configuration error, the loader,
and headless project selection/quit through the CLI with fictional files. It then
removes that environment. Headless checks do not replace a human terminal check.
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
