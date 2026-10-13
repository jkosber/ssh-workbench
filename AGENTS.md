# SSH Workbench

This is an unreleased Python/Textual scaffold. Read [the roadmap](docs/roadmap.md)
for the single backlog and [the architecture](docs/architecture.md) for boundaries.
Implement only the requested task; keep the `src/` layout and runtime dependencies small.

## Work and checks

Inspect `git status --short --branch` before editing and preserve unrelated work.
Use the project Python in `.python-version` and uv; do not modify global Python.

```text
uv sync --locked
uv run --locked ssh-workbench
uv run --locked ssh-workbench --help
uv run --locked ssh-workbench --version
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
uv run --locked python scripts/check_package.py
```

Use `uv run --locked ruff format .` to format changed Python files. Use `uv add`
or `uv add --dev` for dependencies and commit the generated `uv.lock`. Run the
checks above after relevant changes; package validation is described in
[CONTRIBUTING.md](CONTRIBUTING.md). Inspect the final diff and staged file list.

## Scope and safety

- Tasks 1–3 support explicit configuration, project browsing, native SSH launch
  and return. Do not add controls for deferred roadmap features.
- Never read real SSH configuration, keys, host inventories or remote hosts as
  part of development tests. Use temporary files and fictional fixtures.
- Native SSH owns authentication and host-key checks. Launch code must revalidate
  aliases and pass argument lists without a shell. Never disable
  host-key verification or store passwords/private keys.
- Keep expected launch errors inside Textual's suspension block: the locked
  8.2.8 context skips resumption when an exception escapes it. Verify the installed
  implementation when changing this path. Use `scripts/check_terminal.py` for
  native terminal tests without SSH.
- Keep private paths, actual infrastructure details, credentials and workspace
  notes out of Git. `.local/` is ignored. No AI service is required at runtime.

## Documentation and approval

Update relevant documentation when behavior or commands change, meaningful
changes under `Unreleased` in [CHANGELOG.md](CHANGELOG.md), and observed evidence
in [docs/validation.md](docs/validation.md). Label proposals and untested claims.
Keep detailed acceptance criteria in the roadmap; Obsidian holds personal context
and links, not a second backlog.

Keep the application version authoritative in `pyproject.toml`; the CLI reads
installed metadata. Do not bump versions per edit or session. No license is
selected; resolve that before a public release.

The initial bootstrap commit and push are authorized for this setup only.
Future commits, pushes, tags, releases, publication, visibility changes and
infrastructure changes require the user's applicable authorization. Follow the
manual release checklist in [CONTRIBUTING.md](CONTRIBUTING.md).
