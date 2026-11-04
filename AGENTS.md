# SSH Workbench: agent guide

**Extends ~/.claude/CLAUDE.md**

When these rules and a task disagree, stop and ask Jadon.

| Need | Read |
| --- | --- |
| What to build | [Roadmap](docs/roadmap.md) |
| Branches, commits, pull requests, approvals, releases | [Workflow](docs/workflow.md) |
| Modules, boundaries and design decisions | [Architecture](docs/architecture.md) |
| Checks and manual terminal fixtures | [Testing](docs/testing.md) |
| What users see | [User guide](docs/guide.md) |

## Working rules

| Rule | Detail |
| --- | --- |
| Start | Run `git status --short --branch` before editing and preserve unrelated work |
| Python | Use uv and the project Python in `.python-version`; never change the global Python |
| Gates | Run the six commands in [testing](docs/testing.md#automated-checks) and read their output before calling a change done; CI runs the same steps |
| Scope | Implement only the requested task. Add a runtime dependency only when the current task needs it. Add no controls for deferred roadmap features |
| Plans | Plans go in ignored `.local/plans/`, `superpowers:writing-plans` output included; never in `docs/superpowers/plans/` |
| Docs | Update the docs a behavior or command change touches, a changelog line under Unreleased for user-visible changes, and observed manual evidence in [validation](docs/validation.md). Label proposals and untested claims |
| Privacy | The repository is public: everything pushed, branches and pull requests included, can be read by anyone. Keep private paths, real infrastructure details, credentials and workspace notes out of Git; `.local/` is ignored. Read the staged file list before every commit |

## Safety boundaries

Never break these. The [architecture](docs/architecture.md) explains each.

| Area | Rule |
| --- | --- |
| Network | `status.py` is the only network code: TCP port checks, never a login. Tests inject a fake checker |
| `ssh -G` | Runs only at startup, on R and for K's alias, never on the status timer. It evaluates the user's whole SSH config, `Match exec` included |
| Files Workbench writes | Only its machine file and `machines.toml.bak`, through `store.save_machines` (outside-change check, backup, atomic replace), and `machines.state.<computer>.json` through `aliases.save_state` |
| Exported aliases | `exports.py` writes `ssh-workbench.config` in the SSH folder and, only after the user's Y, inserts one `Include` line at the top of the SSH config, with a backup. No other line of that config ever changes |
| Reading SSH config | Only `Host` and `Include` lines are read directly. Native checks give `-F` only the generated file: a relative `Include` in a `-F` file resolves against the real `~/.ssh` |
| Real data in development | Never read real SSH configuration, keys, host inventories, remote hosts or the real machine file in tests. Use temporary files and fictional fixtures |
| Test guards | `scripts/external_boundaries.py` lists the module-level process, socket and browser entry points that tests, fixtures and the package check reject. Add a new one there, not to a single test |
| Manual runs | Without `--config`, `uv run --locked ssh-workbench` loads, and A/E/X/U change, the developer's real machine file. Any run with alias machines writes a state file, runs `ssh -G` on the real SSH config and checks every port, the example's fictional names included. First set `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` to ignored `.local/` folders |
| Key setup | Reads only `.pub` files. `keys.py` builds the two fixed remote commands; the app runs them in the handed-off terminal. Tests and native checks never create real keys, run real `ssh-keygen` or install a key anywhere real; `scripts/check_keys.py` uses local children and fictional keys |
| Launching SSH | Native SSH owns authentication and host-key checks. Revalidate every machine value with the loader's predicates, pass argument lists without a shell, and put `--` before the destination. Never disable host-key verification or store passwords or private keys |
| Terminal handoff | Keep expected launch errors inside Textual's suspension block: the locked 8.2.8 context skips resumption when an exception escapes it. Verify the installed implementation when changing this path; use `scripts/check_terminal.py` for native checks without SSH |
| Links | Dispatch shares the loader's URL validation, stays off the UI thread, preserves exact URLs and never falls back to a terminal browser. Use `scripts/check_links.py` for native checks without a real browser |
| Native checks | Run them in a real terminal: Ghostty on Linux or Microsoft Windows Terminal on Windows |

## Approvals

Each of these needs Jadon's authorization for that action: commits, pushes,
pull requests, merges, version changes, tags, releases, publication of
anything drawn from the repository (follow [publishing](docs/publishing.md)),
visibility changes, infrastructure changes, and use of any real SSH target or
browser URL, with the approval naming it. Several may be authorized at once
when a task starts, such as commits, a push and a pull request; merges,
versions, tags and real targets are always asked separately. Releases follow
[the release checklist](docs/workflow.md#releasing).
