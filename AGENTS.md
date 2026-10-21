# SSH Workbench

SSH Workbench is a Python/Textual terminal interface; 0.1.0 is its first
release, tagged privately. Read [the roadmap](docs/roadmap.md)
for the single backlog and [the architecture](docs/architecture.md) for boundaries.
Implement only the requested task; keep the `src/` layout and runtime dependencies small.

## Work and checks

Inspect `git status --short --branch` before editing and preserve unrelated work.
Use the project Python in `.python-version` and uv; do not modify global Python.

```text
uv sync --locked
uv run --locked ssh-workbench --config examples/machines.example.toml
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

- Tasks 1–10 support explicit or per-user default machine files (schema 1
  still loads), machine browsing, adding, editing and deleting machines, live
  status, alias and direct SSH launch and return, and named links opened
  with O. Do not add
  controls for deferred roadmap features.
- `status.py` is the only network code: TCP port checks, never a login. Tests
  inject a fake checker; `ssh -G` never runs on the status timer.
- Workbench writes only its machine file and `machines.toml.bak`, through
  `store.save_machines` (outside-change check, backup, atomic replace). It reads
  only `Host` and `Include` lines of the SSH config, runs `ssh -G` (which
  evaluates the whole config) only at startup and on R, and never changes it.
- Never read real SSH configuration, keys, host inventories, remote hosts or the
  real per-user machine file as part of development tests. Use temporary files
  and fictional fixtures; the test suite points `APPDATA`, `XDG_CONFIG_HOME` and
  `SSH_WORKBENCH_SSH_DIR` at an empty folder. Without `--config`,
  `uv run --locked ssh-workbench` loads, and A/E/X can now change, the
  developer's real machine file. Any run with alias machines also runs `ssh -G`
  on the real SSH config and checks every machine's port, the example file's
  fictional names included; native checks and manual runs set those
  variables to ignored `.local/` folders first.
- Native SSH owns authentication and host-key checks. Launch code must revalidate
  every machine value with the loader's predicates, pass argument lists without a
  shell and put `--` before the destination. Never disable host-key
  verification or store passwords/private keys.
- Keep expected launch errors inside Textual's suspension block: the locked
  8.2.8 context skips resumption when an exception escapes it. Verify the installed
  implementation when changing this path. Use `scripts/check_terminal.py` for
  native terminal tests without SSH. Run native checks in Microsoft Windows
  Terminal; a real SSH target or browser URL needs Jadon's approval by name.
- Link dispatch shares the loader's URL validation. Keep it off the UI thread,
  preserve exact URLs and avoid terminal-browser fallback. Use
  `scripts/check_links.py` for native checks without opening a real browser.
- Keep private paths, actual infrastructure details, credentials and workspace
  notes out of Git. `.local/` is ignored. No AI service is required at runtime.

## Documentation and approval

Update relevant documentation when behavior or commands change, meaningful
changes under `Unreleased` in [CHANGELOG.md](CHANGELOG.md), and observed evidence
in [docs/validation.md](docs/validation.md). Label proposals and untested claims.
Keep detailed acceptance criteria in the roadmap; Obsidian holds personal context
and links, not a second backlog.

Keep the application version authoritative in `pyproject.toml`; the CLI reads
installed metadata. Do not bump versions per edit or session. The project uses
the MIT license in `LICENSE`; publication still needs the
[publishing checklist](docs/publishing.md) and the user's approval.

Commits, pushes, tags, releases, publication, visibility changes and
infrastructure changes require the user's applicable authorization. Follow the
manual release checklist in [CONTRIBUTING.md](CONTRIBUTING.md).
