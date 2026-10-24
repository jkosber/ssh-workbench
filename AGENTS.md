# SSH Workbench: agent guide

SSH Workbench is a Python 3.14 / Textual terminal app for the machines a user
connects to with SSH. 0.3.1 is its current release, tagged privately. These
rules bind every coding agent working here; when they and a task disagree,
stop and ask Jadon.

## Start here

| Need | Read |
| --- | --- |
| What to build | [Roadmap](docs/roadmap.md): implement only the requested task |
| How work flows, and who approves what | [Workflow](docs/workflow.md) |
| Modules, boundaries and design decisions | [Architecture](docs/architecture.md) |
| Checks and manual terminal fixtures | [Testing](docs/testing.md) |
| What users see | [User guide](docs/guide.md) |

Before editing, run `git status --short --branch` and preserve unrelated work.

## Commands

Use the project Python in `.python-version` and uv; never change the global
Python.

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

Format changed Python with `uv run --locked ruff format .`. Add dependencies
with `uv add` or `uv add --dev` and commit the generated `uv.lock`.

## Working rules

| Rule | Detail |
| --- | --- |
| Scope | Implement only the requested task. Keep the `src/` layout and runtime dependencies small. Add no controls for deferred roadmap features |
| Tests first | Commit failing tests before the implementation; never change a test in the implementation commit. Fix code to match tests |
| Checks | Run the commands above after relevant changes; inspect the final diff and the staged file list |
| Docs | Update the docs a behavior or command change touches, a changelog line under Unreleased for user-visible changes, and observed manual evidence in [validation](docs/validation.md). Label proposals and untested claims |
| Backlog | Acceptance criteria live in the roadmap. Obsidian holds personal context and links, not a second backlog |
| Version | `pyproject.toml` holds the only version; the CLI reads installed metadata. Never bump it per edit or session |
| Privacy | Keep private paths, real infrastructure details, credentials and workspace notes out of Git; `.local/` is ignored. No AI service is needed at runtime |
| License | MIT, in `LICENSE`. Publication needs [the publishing checklist](docs/publishing.md) and Jadon's approval |

## Safety boundaries

Never break these. The [architecture](docs/architecture.md) explains each.

| Area | Rule |
| --- | --- |
| Network | `status.py` is the only network code: TCP port checks, never a login. Tests inject a fake checker |
| `ssh -G` | Runs only at startup, on R and for K's alias, never on the status timer. It evaluates the user's whole SSH config, `Match exec` included |
| Files Workbench writes | Only its machine file and `machines.toml.bak`, through `store.save_machines` (outside-change check, backup, atomic replace), and `machines.state.<computer>.json` through `aliases.save_state` |
| Exported aliases | `exports.py` writes `ssh-workbench.config` in the SSH folder and, only after the user's Y, inserts one `Include` line at the top of the SSH config, with a backup. No other line of that config ever changes |
| Reading SSH config | Only `Host` and `Include` lines are read directly. Native checks give `-F` only the generated file: a relative `Include` in a `-F` file resolves against the real `~/.ssh` |
| Real data in development | Never read real SSH configuration, keys, host inventories, remote hosts or the real machine file in tests. Use temporary files and fictional fixtures; the suite points `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` at an empty folder |
| Manual runs | Without `--config`, `uv run --locked ssh-workbench` loads, and A/E/X/U change, the developer's real machine file. Any run with alias machines writes a state file, runs `ssh -G` on the real SSH config and checks every port, the example's fictional names included. Set the three variables to ignored `.local/` folders first |
| Key setup | Reads only `.pub` files. `keys.py` builds the two fixed remote commands; the app runs them in the handed-off terminal. Tests and native checks never create real keys, run real `ssh-keygen` or install a key anywhere real; `scripts/check_keys.py` uses local children and fictional keys |
| Launching SSH | Native SSH owns authentication and host-key checks. Revalidate every machine value with the loader's predicates, pass argument lists without a shell, and put `--` before the destination. Never disable host-key verification or store passwords or private keys |
| Terminal handoff | Keep expected launch errors inside Textual's suspension block: the locked 8.2.8 context skips resumption when an exception escapes it. Verify the installed implementation when changing this path; use `scripts/check_terminal.py` for native checks without SSH |
| Links | Dispatch shares the loader's URL validation, stays off the UI thread, preserves exact URLs and never falls back to a terminal browser. Use `scripts/check_links.py` for native checks without a real browser |
| Native checks | Run them in Microsoft Windows Terminal. A real SSH target or browser URL needs Jadon's approval by name |

## Approvals

Commits, pushes, pull requests, merges, version changes, tags, releases,
publication, visibility changes and infrastructure changes each need Jadon's
authorization for that action. He may give several at once when starting a
task, such as commits, a push and a pull request; merges, versions, tags and
real targets are always asked separately. See
[who decides what](docs/workflow.md#who-decides-what). Releases follow
[the release checklist](docs/workflow.md#releasing).

## Before you say done

- [ ] Full checks pass, and you read their output.
- [ ] Every test the task needs exists and failed before its code.
- [ ] Docs, changelog and validation log updated where needed.
- [ ] `git diff` and the staged file list reviewed: no debug leftovers, no
  private data, no unrelated changes.
- [ ] Anything not verified is said plainly.
