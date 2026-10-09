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

- Bootstrap supports startup, help, version and keyboard exit only. Do not add
  working-looking controls for planned features.
- Never read real SSH configuration, keys, host inventories or remote hosts as
  part of development tests. Use temporary files and fictional fixtures.
- Native SSH will own authentication and host-key checks. Future launch code
  must validate aliases and pass argument lists without a shell. Never disable
  host-key verification or store passwords/private keys.
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
