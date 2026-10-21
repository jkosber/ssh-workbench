# Contributing

## Set up once

Start in this repository so both uv and the coding agent find the project
instructions. Read [README.md](README.md) and [AGENTS.md](AGENTS.md), then run:

```text
git status --short --branch
uv sync --locked
uv run --locked ssh-workbench
```

uv creates `.venv` with the Python version in `.python-version`. It installs the
package in editable mode, so source changes are available on the next run.
`pyproject.toml` declares dependencies; `uv.lock` records the resolved versions.
`--locked` fails if those files disagree instead of silently changing the lock.

Without `--config`, the development command loads your real per-user projects
file if it exists; `ssh-workbench --help` shows its path. The test suite never
reads it. Keep private configuration and machine-specific notes in the ignored
`.local/` folder, and review files before staging: ignore rules cannot catch
every possible secret.

Use `uv add PACKAGE` for a runtime dependency or `uv add --dev PACKAGE` for a
development tool. Add a dependency only when the current task needs it. Review
and commit both metadata and lockfile changes together when authorized.

## Everyday Git and coding-agent workflow

1. Inspect `git status --short --branch` and read any existing changes. Preserve
   unrelated work. If a prior change is unclear, resolve that before mixing work.
2. Choose one task from [the roadmap](docs/roadmap.md). Ask the coding agent to
   implement that task and its acceptance tests, stating what is outside scope.
3. From a clean, current `main`, make a short-lived branch such as
   `git switch -c feat/project-config`. A branch names a line of development;
   it is not a numbered copy of the project directory.
4. Implement and test a small change. Update affected documentation, meaningful
   Unreleased notes and observed validation evidence.
5. Review `git diff --check`, `git diff` and `git status --short`. Check behavior,
   test assertions and every new file, including examples and lockfile changes.
6. When Jadon instructs a commit, stage only intended paths with `git add PATH`.
   Review `git diff --cached --stat` and `git diff --cached` before committing.
   A commit is a local snapshot; `git push -u origin BRANCH` sends it to GitHub
   and needs the applicable push authorization. Inspect CI before merging.

Commits, pushes, merges, tags, releases and publication are separate decisions,
each needing Jadon's authorization. Start coding-agent sessions from this
repository so the agent reads [AGENTS.md](AGENTS.md). The agent assists
development; the installed application works without a coding agent or AI account.

## Run and interpret checks

Run the same commands locally and in CI:

```text
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
uv run --locked python scripts/check_package.py
```

- **Ruff check:** reports unused imports and other selected code problems. Read
  the file and line in each message; fix the cause.
- **Formatting:** a failure means formatting differs. Run
  `uv run --locked ruff format .`, review the result and rerun the check.
- **pytest:** each failed assertion points to behavior that needs investigation.
  Do not weaken a test to hide a defect. Async UI tests use Textual's headless
  pilot; they do not contact hosts or inspect private files.
- **Build and package check:** produce a source archive and wheel under `dist/`,
  then install the wheel with locked runtime dependencies in a temporary virtual
  environment. Help, version and loading a fictional TOML file are exercised
  outside the checkout, along with missing-configuration errors and headless
  CLI-to-browser selection/quit and substituted SSH success, failure and
  interruption, plus explicit link outcomes and quit with a blocked browser
  opener. Isolated Python mode and imported-module path assertions check the
  wheel rather than the checkout. Those installed-wheel checks live in
  `scripts/package_smoke.py`, which `check_package.py` runs with `python -I`.
  A build alone does not prove SSH functionality or interactive terminal
  compatibility.

`scripts/external_boundaries.py` is the one list of process, network and browser
entry points that tests, fixtures and the package check must never reach. Add a
new entry point there, not to an individual test.

Also try `uv run --locked ssh-workbench --help`, `--version`, and the application
itself, with and without `--config examples/projects.example.toml`; check
selection, details, scrolling and both exit shortcuts. Record what was actually
observed in [validation](docs/validation.md). CI uses the same commands on Linux
and Windows with the Python version in `.python-version`; a queued run is not a
passing run.

For native terminal handoff, run `uv run --locked python scripts/check_terminal.py`
in a real terminal and follow the [fixture checklist](docs/validation.md#task-3-local-terminal-fixture).
It replaces executable lookup and child invocation before using the production
launcher, so it never invokes SSH or reads SSH files. Do not use real aliases,
keys or inventories in tests. A real connection requires separate approval for
the specific target and action.

For link actions, run `uv run --locked python scripts/check_links.py` and follow
the [stubbed link checklist](docs/validation.md#task-4-stubbed-link-checklist).
It replaces browser/OS boundaries, uses fictional projects and guards against
other external actions. Real R/D actions in the normal application open a browser
and require an explicitly approved URL for development verification.

## Recover without losing work

If something looks wrong, pause and inspect `git status` and `git diff` first.
Keep a private copy of uncertain uncommitted work before discarding anything.
`git restore --staged PATH` unstages a file while retaining its working changes.
To investigate old code, use `git log --oneline` and `git show COMMIT:PATH`.

Prefer an explicitly reviewed `git revert COMMIT` to undo a committed change
that has been shared. Ask before discarding working changes or rewriting
history. Do not default to `git reset --hard`, `git clean -fd` or force-pushing.
If a command or signing requirement fails, diagnose it without bypassing hooks,
authentication or signing policy.

## Versions and deliberate releases

The authoritative application version is `[project].version` in
`pyproject.toml`. `--version` reads installed package metadata. Do not add a
second version file, bump versions per session, or create numbered source folders.

| Version | Meaning |
| --- | --- |
| 0.0.1 | Development scaffold before the first release |
| 0.1.0 | First usable release, tagged privately |
| 0.1.1 | Example later bug-fix release |
| 0.2.0 | Example later feature milestone |
| 1.0.0 | A deliberately chosen stable release later |

Rows after 0.1.0 describe policy, not promised releases. Until stability is
deliberately declared, document compatibility changes explicitly.

Manual release checklist:

1. Review completed scope and validation, then choose a version. Resolve the
   license and privacy checklist before a public release; visibility changes
   need their own approval. Run `git grep -n -i -E "unreleased|scaffold"` and
   update every line that describes the current state, including the
   `pyproject.toml` description and the app subtitle.
2. Update `pyproject.toml`, run `uv lock` as needed and `uv sync --locked`, and
   review the metadata/lockfile diff.
3. Run the full checks above, including a fresh build and isolated installation.
   Complete the approved manual checks appropriate to the release.
4. Move relevant Unreleased notes into a dated changelog entry, leaving an
   Unreleased section for later work.
5. Review and commit the release changes when authorized. Keep the existing Git
   identity and any signing requirements.
6. When authorized, create an annotated tag, for example
   `git tag -a v0.1.0 -m "Release 0.1.0"` on the intended release commit.
7. When authorized, push the intended branch and exact tag, for example
   `git push origin main` and `git push origin v0.1.0`. Check remote state and CI.
8. Create a GitHub Release only when explicitly requested. Package publication
   also needs separate approval; there is no publishing automation here.
