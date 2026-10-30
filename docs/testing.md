# Testing

How SSH Workbench is checked: the automated checks that CI runs, and the
manual checks in a real terminal that automation cannot replace.
Results of manual checks go in [the validation log](validation.md).

## Automated checks

CI runs these on Windows and Ubuntu for every pull request and every push to
`main` or a version tag; a branch without a pull request gets no CI run. Run
them locally before opening a pull request:

```text
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
uv run --locked python scripts/check_package.py
```

| Check | What it proves | When it fails |
| --- | --- | --- |
| `ruff check` | No unused imports or other selected code problems | Read the file and line in each message and fix the cause |
| `ruff format --check` | Formatting matches Ruff's | Run `uv run --locked ruff format .`, review the result, check again |
| `pytest` | Loader, CLI, boundaries and the UI (headless) behave as specified | A failed assertion is a behavior to investigate. Fix the code, never weaken the test |
| `uv build` | A source archive and a wheel build under `dist/` | Read the build error; the backend is `uv_build` |
| `check_package.py` | The built wheel installs and works outside the checkout | See below |

The package check installs the wheel with the locked runtime dependencies in
a temporary environment. It compiles the dependencies to bytecode, so no timed
step spends its limit compiling Textual, but not the wheel, so a
`SyntaxWarning` in a module that `--help` loads (`ssh_workbench`, `cli`,
`config`) still fails the help check; one in another module, such as `app`,
does not. It then runs `scripts/package_smoke.py` there with `python -I`, so
the wheel is tested rather than the checkout. It covers help, version,
missing-file errors, loading a fictional file, a headless app that selects and
quits, Connect with a substituted SSH (success, failure, launch error,
interruption), link outcomes, quitting while a browser request hangs, and a
first save. A build alone proves nothing about SSH or a real terminal; the
manual checks below do.

The Windows key-install script's tests (`tests/test_keys.py`) run or parse
that script with PowerShell 7 (`pwsh`) or Windows PowerShell and fail without
one. GitHub's Ubuntu and Windows runners include PowerShell; on your own Linux
machine, install PowerShell 7 to run the whole suite.

UI tests use Textual's headless pilot. A test that waits for the screen should
wait for the condition it asserts, not for a fixed pause.

## What tests may touch

Tests use fictional data and temporary folders only. They never read real SSH
configuration, keys, host inventories or the real machine file, and never
reach a real host or browser.

| Guard | Detail |
| --- | --- |
| Folders | The suite points `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` at an empty temporary folder |
| Process, network and browser | `scripts/external_boundaries.py` lists every module-level entry point (process start, sockets, browser openers). Tests, fixtures and the package check reject them all. Add a new entry point there, not to one test |
| Sockets | `connect` and `connect_ex` are patched separately, once the event loop exists, because Windows opens a local socket pair when the loop starts |
| Status checks | The app checks status only when given a checker; tests pass fakes |

## Manual checks in a real terminal

Run these in a real terminal: Ghostty on Linux or Microsoft Windows Terminal
on Windows, the terminals the validation log records. Before a manual run, point
Workbench at ignored folders so it cannot touch your real files. In bash:

```bash
export APPDATA="$PWD/.local/manual/appdata"
export XDG_CONFIG_HOME="$PWD/.local/manual/xdg"
export SSH_WORKBENCH_SSH_DIR="$PWD/.local/manual/ssh"
```

In PowerShell:

```powershell
$env:APPDATA = "$PWD\.local\manual\appdata"
$env:XDG_CONFIG_HOME = "$PWD\.local\manual\xdg"
$env:SSH_WORKBENCH_SSH_DIR = "$PWD\.local\manual\ssh"
```

The variables last until the shell closes, so use a separate shell for
manual runs.

Without `--config`, `uv run --locked ssh-workbench` loads, and A, E, X and U
can change, your real machine file. Any run with alias machines also writes a
state file next to the machine file, runs `ssh -G` on the SSH config and
checks every machine's port, the example file's fictional names included.
A run on `examples/machines.example.toml` writes
`examples/machines.example.state.<computer>.json` beside it, which
`.gitignore` covers (`*.state.*.json`).

Each fixture script replaces the boundary it checks: `check_terminal.py`
Connect's SSH, `check_links.py` the browser, `check_keys.py` `ssh-keygen` and
SSH. A check against a real SSH target or a real URL needs Jadon's approval
for that target by name.

### App smoke check

```text
uv run --locked ssh-workbench --config examples/machines.example.toml
```

At 80x24: the list, details and footer draw; Up and Down change the selected
machine and its details; Tab moves between the panes; Page Up and Page Down
scroll the details; R checks again; Q exits, and a second run exits with
Ctrl+Q. After each exit the shell prompt, echo and keys work normally.

Resize while it runs: under 60 columns the list moves above the details and
the footer wraps onto two rows; at 110 columns or more each row shows where
it connects; under 20 rows the help line hides. Resize once with a form open
(E, then Escape): the browser behind it follows. Windows Terminal will not go
narrower than about 47 columns (Ghostty: about 19, see the validation log).
If everything is grey, the shell has `NO_COLOR` set (coding agents set it);
clear it first with `unset NO_COLOR` in bash or `Remove-Item Env:NO_COLOR` in
PowerShell.

### Terminal handoff: `scripts/check_terminal.py`

```text
uv run --locked python scripts/check_terminal.py
```

Each fictional machine runs a local child instead of SSH.

Do not press K here. This fixture does not replace key setup, so K then Enter
starts the real `ssh-keygen` and then real SSH to the fictional alias;
`check_keys.py` covers K. Send one key at a time and wait for the screen: keys
typed while C hands over the terminal can run as shortcuts when the child
exits.

1. **Normal exit (0)**: press C. The child reports that stdin, stdout and
   stderr are all a terminal, and echoes what you type. Type `return`: status
   0, the same machine selected, the list focused, arrow keys working.
2. **Nonzero exit (7)**: Tab to the details, press C, type `return`. Status
   7, and Down still changes the selection.
3. **Ctrl+C exits the child (130)**: press C, then Ctrl+C. Status 130.
4. **Ctrl+C keeps the child running**: press C, then Ctrl+C twice. The child
   still accepts text; type `return` to come back.
5. The three simulated entries (**SSH unavailable**, **Process start
   failure**, **Launch interrupted**): each shows its message, keeps the
   selection and allows another C.
6. Quit with Q and check the shell. Run again, connect and return, quit with
   Ctrl+Q, check the shell again.

This does not check SSH's own authentication or networking.

### Links: `scripts/check_links.py`

```text
uv run --locked python scripts/check_links.py
```

Run at 80x24. Every browser and operating-system opener is substituted.

1. On each case, press O from the list and again from the details pane.
   Accepted reports "accepted"; failed and error report "failed" without the
   private marker; the long case wraps in the details pane and stays inside
   the status area.
2. On the no-links case, O is dimmed and pressing it changes nothing.
3. On the picker case, O opens the list: Enter opens the first link, Down
   then Enter the second, and Escape closes it with the same selection and
   focus.
4. Last, on the blocked case, O reports pending and a second O reports "still
   pending". Change the selection and focus, then quit with Q or Ctrl+Q: the
   process exits at once.

### Key setup: `scripts/check_keys.py`

```text
uv run --locked python scripts/check_keys.py
```

Select a machine and press K. The app works in a temporary folder with
fictional keys; local children stand in for `ssh-keygen` and SSH, say which
step they are, and wait for `return` or Ctrl+C.

| Option | Effect |
| --- | --- |
| `--keygen-status N`, `--install-status N`, `--test-status N` | Exit status of that step's child (default 0) |
| `--folder PATH` | Reuse a working folder, so a second run shows a saved key |

Useful runs: all steps with status 0 ("Key login works." and, for the direct
machine, the key saved); `--test-status 255` (the failure message, no key
saved); Ctrl+C at the install child ("Key setup interrupted during the
install; login was not tested." and no test child); Ctrl+C at the keygen
child ("Key setup interrupted while creating the key; nothing was
installed."); `--test-status 0` with Ctrl+C at the test child ("The key was
installed, but the login test was interrupted."). The alias's picker names
`id_work` under the list: its config offers it, but it has no `.pub`.

### Login shells: `scripts/check_shells.py`

```text
uv run --locked python scripts/check_shells.py | sh -s
uv run --locked python scripts/check_shells.py | ssh <approved target> sh -s
```

sshd runs the install command as `<login shell> -c <command>`. The script
prints a POSIX sh script that does the same from bash, dash, zsh, fish and
tcsh (`--shells` names others), twice each, with HOME in a new temporary
folder and a fictional key, so no real `~/.ssh` is touched. Each shell reads
PASS, FAIL (with what it printed) or "not installed", and the exit status is
0 only if every shell passed. A real machine needs Jadon's approval by name.

## Recording results

Write what you saw, not what should happen, in
[the validation log](validation.md): the terminal and size, each check and its
result, and what was not checked.
