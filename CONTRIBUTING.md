# Contributing

SSH Workbench is developed by Jadon Kosberg with coding agents. The repository
is private for now; these notes are written so that others can join once it is
public.

| Read | For |
| --- | --- |
| [Workflow](docs/workflow.md) | How a task goes from idea to release, and who approves what |
| [Testing](docs/testing.md) | The automated checks and the manual terminal checks |
| [Architecture](docs/architecture.md) | How the code is organized and its safety boundaries |
| [AGENTS.md](AGENTS.md) | The rules coding agents follow, which apply to people too |

## Set up once

Work from the repository folder, so uv and coding agents find the project
files:

```text
git status --short --branch
uv sync --locked
uv run --locked ssh-workbench --config examples/machines.example.toml
```

| Piece | What it does |
| --- | --- |
| `.python-version` | The Python version uv installs into `.venv`; don't change your global Python |
| `pyproject.toml` | Dependencies and the application version |
| `uv.lock` | The exact resolved versions. `--locked` fails if it disagrees with `pyproject.toml` instead of silently changing it |
| Editable install | Source changes take effect on the next run |

Add a runtime dependency with `uv add PACKAGE` or a development tool with
`uv add --dev PACKAGE`, only when the current task needs it, and commit
`pyproject.toml` and `uv.lock` together. Never edit `uv.lock` by hand.

## Your real files

Without `--config`, `uv run --locked ssh-workbench` uses your real machine file:
A, E, X and U change it, and a state file appears next to it. The app also
reads `Host` lines from your real SSH config, runs `ssh -G` on it for alias
machines and checks every machine's SSH port. For manual runs, point it at
ignored folders first, as [the testing guide](docs/testing.md#manual-checks-in-a-real-terminal)
shows. The test suite never touches real files.

Keep private configuration and notes in the ignored `.local/` folder, and look
at every file before staging it: ignore rules cannot catch every secret.

## Everyday commands

| Command | Purpose |
| --- | --- |
| `uv run --locked ssh-workbench --config examples/machines.example.toml` | Run the app on fictional machines |
| `uv run --locked ssh-workbench --help` / `--version` | Help, with the default machine file's path / the version |
| `uv run --locked pytest` | The test suite |
| `uv run --locked ruff format .` | Format the code |
| `uv run --locked ruff check .` | Lint |
| `uv build` then `uv run --locked python scripts/check_package.py` | Build and test the installed wheel |

## Project rules

| Rule | Detail |
| --- | --- |
| One task at a time | Implement only the task at hand; keep the `src/` layout and runtime dependencies small |
| Tests first | Commit failing tests before the code; never change a test in the commit that implements the code. Fix the code to match the tests |
| Fictional data only | Tests and fixtures never read real SSH files, keys, inventories or the real machine file, and never reach real hosts or browsers |
| OpenSSH owns security | Authentication, host-key checks and private keys stay with the native SSH client |
| Textual is pinned below 9 | The terminal handoff was verified only on the locked 8.2.8 |
| Docs follow behavior | A change a user would notice updates the guide and the changelog |

## Recover without losing work

| Situation | Safe step |
| --- | --- |
| Something looks wrong | Read `git status` and `git diff` first |
| Uncertain uncommitted work | Keep a private copy before discarding anything |
| A file staged by mistake | `git restore --staged PATH` keeps its changes |
| Need old code | `git log --oneline`, then `git show COMMIT:PATH` |
| Undo a shared commit | A reviewed `git revert COMMIT` |
| A hook or signing step fails | Find the cause; never bypass hooks, authentication or signing |

Ask before discarding work or rewriting history. Avoid `git reset --hard`,
`git clean -fd` and force-pushing.
