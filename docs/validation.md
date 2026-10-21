# Validation

## Task 7: tooling cleanup, 2026-10-20

Branch `feat/task7-tooling-cleanup`. Environment as in Task 6: Windows 11,
Python 3.14.7, Textual 8.2.8, uv 0.13.3, Ruff 0.16.10 and pytest 9.1.1.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | The shared-list tests failed at collection (`No module named 'external_boundaries'`); the strings test failed listing lines 13, 34, 192 and 357 of `check_package.py` |
| Drift test | Passed on the old 0.12.24 pair, failed (`['0.12.24'] == ['0.13.3']`) after only `pyproject.toml` changed, and passed once CI matched |
| `uv build` before and after | The warning that `uv-build>=0.12.24,<0.13.0` excludes uv 0.13.3 appeared before the change and is gone after it. `uv lock --check` reported the lock unchanged |
| Isolation assertions | `package_smoke.py` without `-I` failed on `sys.flags.isolated`; with `-I` against the development environment it failed naming `ssh_workbench`, whose editable install points at the checkout |
| `uv sync --locked`, Ruff check and format | Passed; 32 files already formatted |
| `uv run --locked pytest` | 450 passed (446 before Task 7) |
| `uv build`, `scripts/check_package.py` | Passed, with the same success line as before |
| Relative Markdown links | 62 checked, 0 broken |

No native terminal check was needed: no application code changed.

## Task 6: 0.1.0 readiness, 2026-10-20

Branch `feat/task6-0.1.0-readiness`. Environment: Windows 11 Home Insider
Preview build 26340, PowerShell 7.6.7, Microsoft Windows Terminal 1.25.2733.0,
Python 3.14.7, Textual 8.2.8, uv 0.13.3, Ruff 0.16.10 and pytest 9.1.1.

| Check | Agent-observed result |
| --- | --- |
| New default-file tests before implementation | 12 failed for the missing feature; the precedence and no-path guards and all existing tests passed |
| `uv sync --locked`, Ruff check and format | Passed; 29 files already formatted |
| `uv run --locked pytest` | 445 passed (431 before Task 6) |
| `uv build` | Source archive and wheel for 0.1.0. Wheel metadata shows `License-Expression: MIT` and `License-File: LICENSE`; both archives contain `LICENSE`. The known `uv_build<0.13.0` warning from uv 0.13.3 remains |
| `uv run --locked python scripts/check_package.py` | Passed |
| Relative Markdown links | 61 checked, 0 broken |
| `uv tool install .`, then `--reinstall .` | Installed `ssh-workbench.exe` into the uv tool folder; `ssh-workbench --version` printed `ssh-workbench 0.1.0` from another folder |

Installed-tool smoke test in an owned 80x24 Windows Terminal window, with
`NO_COLOR` cleared and `APPDATA` pointed at ignored `.local/` folders so the real
per-user file was untouched:

| Step | Result |
| --- | --- |
| No default file, no `--config` | No-configuration screen named the default path under the overridden `APPDATA`, wrapping cleanly at 80 columns; Q exited with status 0 |
| Default file holding one approved SSH alias | Project loaded without `--config` |
| C, then `exit` at the remote prompt | No password or host-key prompt appeared. Workbench returned with `SSH exited with status 0.` and the same project selected |
| Ctrl+Q | Exited with status 0 to a usable prompt; the window was then closed |

The alias name and screenshots stay in ignored `.local/task6-session/`. Linux
and macOS were not exercised natively.

Two fresh reviewers then checked the branch for plan compliance and quality. One
defect was fixed after a failing test: `--help` crashed with `UnicodeEncodeError`
when redirected output used a code page that cannot encode the default path. The
path is now escaped for the output encoding. Documentation fixes followed for the
agent check list, the example file header, the Linux quick start and two stale or
wrong statements. Remaining minor findings are listed under 0.1.x candidates in
the roadmap. After the fixes: 446 tests passed, Ruff and links were clean, the
build and package check passed again, and redirected help with a fictional
non-cp1252 `APPDATA` exited 0 with the path escaped. The native smoke test was
not repeated; the fix changes only help text.

### Integration and release

Each step below had Jadon's approval.

| Step | Result |
| --- | --- |
| [PR #6](https://github.com/jkosber/ssh-workbench/pull/6) CI on head `8320728` | [Push run 39518641055](https://github.com/jkosber/ssh-workbench/actions/runs/39518641055) and [PR run 39518656107](https://github.com/jkosber/ssh-workbench/actions/runs/39518656107) passed on Windows and Ubuntu; the PR run logs show 446 tests on each |
| Merge | Merged at 2026-10-21 00:03 UTC (2026-10-20 locally) as **`54f6a3e`**, guarded on head `8320728`. Parents `ac4f6e8` and `8320728`; tree identical to the tested head. Local `main` fast-forwarded to it |
| Merged `main` CI | [Run 39518897638](https://github.com/jkosber/ssh-workbench/actions/runs/39518897638) passed on Windows and Ubuntu |
| Tag | Annotated `v0.1.0` ("Release 0.1.0", tagger Jadon Kosberg) on `54f6a3e`, pushed to origin |
| Install from the tag | `uv tool install --reinstall git+https://github.com/jkosber/ssh-workbench@v0.1.0` installed 0.1.0; `ssh-workbench --version` printed `ssh-workbench 0.1.0` |
| Repository | Description updated to match `pyproject.toml`. Still private, with no GitHub Release. The merged branch was deleted |

## Task 5: preparation and safe local verification, 2026-10-12

**Task 5 is complete and merged in PR #5.** Initial preparation merged Task 4, verified the
baseline with substituted external actions, and prepared the user-run session
below. No real SSH connection or browser/GIO dispatch occurred during that
preparation. Later user-reported and explicitly authorized agent checks in
Windows Terminal are recorded separately below.
On 2026-10-20, at Jadon's request, the agent listed only the `Host` names in his
SSH configuration so he could choose test targets. It printed no host names,
users or key paths, and has read no keys or inventories. These Task 5 records
stayed uncommitted until 2026-10-20.

| Task 5 item | Status | Evidence |
| --- | --- | --- |
| Approved real-world targets | Done | One alias (2026-10-12); the GitHub repository and README URLs and two more aliases (2026-10-20). Alias names stay in the ignored configuration |
| Checklist A-D in Windows Terminal | Done | [Windows Terminal check](#task-5-authorized-windows-terminal-check-2026-10-20); step C is also [user-reported](#task-5-user-executed-manual-session) |
| Footer mouse clicks | Done | [Footer click check](#task-5-footer-click-check-2026-10-20) |
| More SSH targets and a real nonzero exit | Done | [Additional targets](#task-5-additional-ssh-targets-and-review-fixes-2026-10-20) |
| Project review and material fixes | Done | Same section: SSH lookup in the launch folder and UTF-8 byte-order-mark configs, each fixed after a failing test |
| Documentation accuracy pass | Done | 2026-10-20 |
| Release scope and license decision | Done | 2026-10-20: private `v0.1.0` tag, MIT license, scope in roadmap Task 6 |

### Verified Task 4 merge and CI

The starting checkout was clean on `feat/errors-and-links`, at reviewed head
`0fe97d169a59094dbfdce179480d6889efb4dcdb`. Origin and ownership were verified as
private `jkosber/ssh-workbench`; GitHub authenticated as `jkosber`. PR #4 was open,
not a draft, into `main`, with that exact head, no GitHub reviews/comments or
unresolved review threads, and `CLEAN` / `MERGEABLE` status. The branch API
reported main unprotected; the rules endpoint was unavailable for this private
repository's plan. No requirements or settings were changed.

Both named Windows/Ubuntu jobs passed in
[push CI 38334751595](https://github.com/jkosber/ssh-workbench/actions/runs/38334751595)
and [PR CI 38334807914](https://github.com/jkosber/ssh-workbench/actions/runs/38334807914).
Each log confirmed 428 tests, build and isolated package checks. PR checkout
`e1328ec3c837b2ebca6d0fb1fea2a7ee2cea82be` had prior main `eeb6e39` and reviewed
head `0fe97d1` as parents, with the same tree as the reviewed head.

[PR #4](https://github.com/jkosber/ssh-workbench/pull/4) merged normally at
2026-10-13 02:14:39 UTC (2026-10-12 locally), as
**`9b28e86c0d6c980c6058297f60e6ff623e657031`**. The CLI's author-email override was
rejected before merging; the successful REST merge used `merge_method=merge`
and `sha=0fe97d169a59094dbfdce179480d6889efb4dcdb` as the equivalent head guard.
GitHub attributed the merge author to Jadon Kosberg's `jkosber` account and used
its server committer. Local/global Git identity settings were preserved. There
was no admin override, auto-merge, branch deletion or visibility change.

Fetch confirmed the merge's two expected parents and a tree identical to the
reviewed feature head. Local main fast-forwarded to origin/main;
`test/task5-validation` was created at the same merge. The repository remains
private. New [merged-main CI 38335955509](https://github.com/jkosber/ssh-workbench/actions/runs/38335955509)
completed successfully for **`9b28e86`**, with Windows and Ubuntu each passing
428 tests, locked sync, Ruff, build and isolated installed-package validation.
This is a separate run from Task 4's push/PR checks.

### Merged-baseline local evidence

Every result in this table tests merge **`9b28e86`**, before Task 5 documentation
edits. Environment: Windows 11 Home Insider Preview build 26340, PowerShell
7.6.6, Python 3.14.7, Textual 8.2.8, uv 0.13.0, Ruff 0.16.10 and pytest 9.1.1.
Microsoft Windows Terminal 1.25.2733.0 is installed, but the initial preparation's
interactive checks used an owned Windows pseudoterminal with a profile-free
PowerShell through cmd.exe. They do not establish Windows Terminal pixels,
resizing or SSH handoff. No screenshots were taken during that preparation.

| Command/check | Agent-observed result |
| --- | --- |
| `uv sync --locked` | Passed; existing lockfile and project Python |
| `uv run --locked ssh-workbench --help` / `--version` | Passed; 0.0.1 |
| `uv run --locked ssh-workbench` | No-config screen; Q returned status 0 and usable shell input; no external action invoked |
| `uv run --locked ruff check .` / `ruff format --check .` | Passed; 29 files (20 Python, 9 Markdown) already formatted |
| `uv run --locked pytest --basetemp .local/task5-session/pytest` | 428 passed in 67.09s; fresh ignored directory avoided the previously documented shared-temp cleanup issue |
| `uv build` | Source archive and wheel built |
| `uv run --locked python scripts/check_package.py` | Passed isolated wheel/import provenance, CLI/configuration, headless selection/quit, substituted SSH/link outcomes and blocked-opener Q/Ctrl+Q interpreter exit |
| `uv run --locked python scripts/check_links.py` | Standalone fixture: R from list, D from details, accepted/failed/error/missing results, blocked request with changed selection/focus and repeat feedback; Q and Ctrl+Q each returned 0 to usable shell input |
| `uv run --locked python scripts/check_terminal.py` | Local Python children only: inherited terminal I/O, typed input, exits 0/7/130, C from details, two Ctrl+C events while the child continued, normal return, simulated missing/start/interruption errors, retry and both quit keys; selection and list focus restored |
| Persistent session wheel installation below | Locked runtime install passed; help/version and Python `-I` site-packages provenance passed. No-config startup and Ctrl+Q returned 0 to usable shell input |
| Local placeholder TOML | Installed loader accepted two projects; only the explicit new file was read, with no external action |

The existing warning remains: installed uv 0.13.0 is outside
`uv_build>=0.12.24,<0.13.0`. Build and package checks passed; tooling and the
previously recorded backend-provenance limitation are unchanged. No production
defect was confirmed during this preparation. No code, tests, dependencies or
new test harnesses were added. The owned fixture shell and children exited;
the isolated package check removed its temporary environment. The separate
manual environment is retained for Jadon.

Fixture entry points were inspected before execution. The link fixture starts
guards before app construction and retains them until interpreter exit; the
full suite includes all 11 lifetime/exit/import regressions. The terminal fixture
substitutes executable lookup and invocation with fixed local Python children.
New fixture results above are distinct from historical WezTerm evidence below.

At the preparation handoff, all 23 relative links/anchors in the three changed
Markdown files passed validation, and the documented TOML matched the then-current
ignored placeholder template. Final diff/whitespace and empty-index checks passed;
only the roadmap, this record and the Unreleased changelog changed in Git.

### Task 5 evidence gaps against the existing acceptance

| Evidence class | Supported now / remaining gap |
| --- | --- |
| Automated | Configuration, selection/details, focus/scroll/quit, sanitized failures, SSH/browser boundary contracts and package installation pass on this revision. These support the baseline, not the required real-world observations. |
| Substituted boundaries / native fixtures | Current pseudoterminal checks exercise local handoff, recovery and stubbed dispatch. Historical WezTerm resize/text results retain their recorded scope; obscured Task 4 screenshots remain excluded. |
| Real manual interaction | Jadon reported Windows Terminal SSH handoff, return, preserved selection, immediate arrow navigation and status 0. An authorized agent check of the installed build in Windows Terminal (2026-10-20) covered live SSH return, navigation, resizing, detail scrolling and both quit keys with shell checks. In Windows Terminal, R/D opened the chosen GitHub repository and README pages in Chrome. Mouse clicks on the footer's Connect (local-child fixture), Repository, Documentation and Quit actions also worked. |
| Still unverified / unavailable | Linux GIO browser dispatch and a native Linux desktop; other DPI settings and screen readers. Authentication mechanisms and host-key prompts were not separately examined. macOS browser dispatch is explicitly unavailable in this version. Ubuntu CI does not validate a Linux desktop. Agent observation is not a human visual review. |
| Documentation, issues and readiness review | Checklist steps A-D are complete with no material defect found. Scope and privacy boundaries were reviewed; final readiness and the unselected license remain open. No release/version/visibility decision is made. |
| Outside initial-release requirements | Deferred editing/search, discovery, tmux, transfers, cloud sync, embedded terminals, AI, Proxmox controls and plugins. Manual checks use Microsoft Windows Terminal; this task adds no all-platform or accessibility certification requirement. |

### Task 5 installed build and local configuration

Use Microsoft Windows Terminal for the first real pass. Run these commands from
the repository in PowerShell. The session directory was absent before preparation
and `git check-ignore -v` verified `.local/` ignores the configuration, environment
and exported requirements. Existing local files were preserved. Keep real target
details only in `.local/task5-session/projects.toml`, never in tracked examples.

The following **local installation steps have already passed**. They mirror the
existing package-check installation sequence and do not alter global Python.
For another installation, choose a fresh ignored directory; do not overwrite an
existing environment, requirements export or configuration.

```powershell
uv sync --locked
uv build
uv venv --python .venv\Scripts\python.exe .local\task5-session\venv
uv export --locked --no-dev --no-emit-project --output-file .local\task5-session\runtime-requirements.txt
uv pip sync --python .local\task5-session\venv\Scripts\python.exe .local\task5-session\runtime-requirements.txt
uv pip install --python .local\task5-session\venv\Scripts\python.exe --no-deps dist\ssh_workbench-0.0.1-py3-none-any.whl
```

The retained installed wheel was built from `9b28e86`, version 0.0.1, SHA-256
`71d1522a22fb6c9549ad7b0a7ca18650b247a37f495eaa5e82c3e8a35aadf589`.
Documentation edits afterward do not change that installed artifact.

The original schema-correct template below is retained as a fictional reference.
Jadon subsequently chose an existing alias; both local records use that alias.
On 2026-10-20 he chose the repository and README URLs for the first record; the
second still omits them. Actual target details stay in the ignored file. The second row supports navigation and missing
references without another host. When reusing this template, replace its alias
and URL placeholders before C/R/D; restart Workbench after editing the file.

```toml
schema_version = 1

[[projects]]
id = "manual-target"
name = "Manual target"
ssh_alias = "CHOOSE_EXISTING_ALIAS"
repository = "https://example.invalid/choose-repository"
documentation = "https://example.invalid/choose-documentation"

[[projects]]
id = "navigation-check"
name = "Navigation check - use the same existing alias; no links on this row"
ssh_alias = "CHOOSE_EXISTING_ALIAS"
# Optional URLs omitted to check the 'Not provided' display.
```

Jadon can now use the installed build without rebuilding or activating a venv:

```powershell
git rev-parse HEAD
& .\.local\task5-session\venv\Scripts\ssh-workbench.exe --version
& .\.local\task5-session\venv\Scripts\ssh-workbench.exe --config .local\task5-session\projects.toml
```

Launching/selection reads that file without contacting a target. **C contacts
the configured SSH destination; R/D open a real browser.** These actions below
are for Jadon to perform. No passwords, private keys, MFA codes, sensitive
transcripts or screenshots are requested. Pause unexpected host-key/trust prompts
for independent verification; do not auto-accept, remove warnings, edit
known_hosts or disable checking. An actual login may create normal session or
audit records; use the existing trusted workflow without extra remote operations.

### Task 5 authorized Windows Terminal check, 2026-10-20

Jadon chose the repository and README URLs below and authorized one live SSH
connection to the alias already in the ignored configuration. The agent ran
checklist steps A, B, C and D in one owned Microsoft Windows Terminal 1.25.2733.0
window with PowerShell 7.6.7 on Windows build 26340. The installed wheel above
(0.0.1 from `9b28e86`) was used; `src/`, `pyproject.toml`, `uv.lock` and `README.md`
are unchanged between `9b28e86` and the tested branch head `5378fcd`.

The first row of the ignored configuration gained
`repository = "https://github.com/jkosber/ssh-workbench"` and
`documentation = "https://github.com/jkosber/ssh-workbench/blob/main/README.md"`.
The second row still omits both. A dated backup of the prior file was kept.

| Step | Agent-observed result |
| --- | --- |
| A. Baseline | `--version` printed 0.0.1. Startup selected the first project with list focus. Up/Down switched details between both projects; the second showed `Not provided` twice. Tab moved the accent border to details; Down/End scrolled the one overflowing line and Home returned. Shift+Tab restored list navigation. |
| B. Browser | R reported `Repository browser request accepted. Project 1: manual-target`. Windows' URL association opened Google Chrome 155.0.8059.85, whose address bar showed `github.com/jkosber/ssh-workbench` and whose title was the repository page. D reported the matching acceptance and Chrome showed `github.com/jkosber/ssh-workbench/blob/main/README.md` with the README title. The private repository loaded in Chrome's existing signed-in session. R on the second project showed `Repository link not configured. Add it to the configuration and restart.` with `Project 2: navigation-check`. Navigation continued after returning from the browser, and Q exited 0 to usable shell input. |
| C. SSH | After a relaunch, C handed the terminal to native SSH. A remote shell prompt appeared with no password, MFA or host-key prompt. The agent typed only `exit`. Workbench returned with `SSH exited with status 0.`, the same project selected and list focus; Up/Down worked immediately. |
| D. Restoration | In the same session after the SSH return, the window was resized to 60x20, 120x40 and back to 80x24, with dimensions confirmed from the rendered screen. Up/Down worked at each size. At 60x20 the title and second name truncated, help text wrapped, the footer stayed visible, and details scrolled to the wrapped README URL. Q then exited 0 and `Write-Output` worked. A separate launch exited 0 with Ctrl+Q and `Write-Output` again worked. |

How it ran: Win32 `SendInput` keystrokes were sent only while the owned window
was in the foreground, and the run stopped otherwise. Screen text came from Windows UI Automation
and screenshots from `Graphics.CopyFromScreen` of that window only. Window size
was set with `SetWindowPos`. Fifteen Workbench-only PNGs are kept under ignored
`.local/task5-session/wt-20261020/`. No screenshot covered the SSH session or the
browser, and remote output was not recorded.

Run notes:

- The agent's environment sets `NO_COLOR=1`, which the new window inherited, so the
  first launch rendered monochrome. The variable was removed in that test shell
  only and the checks were repeated with normal colors.
- Jadon accidentally typed into the window during size calibration, before
  Workbench started. That only affected a calibration command in the shell.
- The Chrome tabs opened by R/D were left open. The test window was closed with `exit`.

No application defect was found. The link status after R on the second project
kept naming project 2 when the selection moved back to project 1, as documented:
link results stay attributed to the project that requested them.

### Task 5 footer click check, 2026-10-20

The README says the footer's Connect, Repository and Documentation actions can be
clicked. Automated tests only confirm those footer keys exist and are visible,
so the agent clicked them with the mouse in a new owned Windows Terminal window,
using the same setup as the check above. Source is unchanged from that check.
Each click targeted the label's on-screen bounds from UI Automation and
was refused unless that point belonged to the owned window. The cursor was
restored afterwards.

| Click | Agent-observed result |
| --- | --- |
| Connect, in `scripts/check_terminal.py` (local child, no SSH) | The first fixture project handed off to the local child with terminal stdin/stdout/stderr. After `return`, Workbench showed `SSH exited with status 0.` with the same project selected and list focus |
| Quit, in the fixture | Exited 0; `Write-Output` worked |
| Repository, installed build, list focused | `Repository browser request accepted. Project 1: manual-target`; Chrome showed `github.com/jkosber/ssh-workbench` |
| Documentation, installed build, details focused | Matching acceptance; Chrome showed the README URL. Details kept focus and the selection was unchanged |
| Quit, installed build | Exited 0; `Write-Output` worked |

Connect was clicked only in the local-child fixture, so no SSH connection was
made. Screenshots are in ignored `.local/task5-session/wt-footer-20261020/`.

### Task 5 additional SSH targets and review fixes, 2026-10-20

**Review.** Three read-only reviews covered the whole project: code and tests,
documentation accuracy, and privacy. No crash or bad-state bug was found. Git
history on all branches, the PR text and the built package contain no private
paths, hosts, aliases, tokens or AI attribution. The reviews confirmed two defects,
each fixed after a failing test was committed (`b753e3b`):

| Defect | Fix |
| --- | --- |
| On Windows, `shutil.which` checks the current directory before `PATH` unless `NoDefaultCurrentDirectoryInExePath` is set, so C could run an `ssh.exe` sitting in the folder Workbench was started from. A relative `PATH` entry had the same effect on any platform | `2653323`: a relative lookup result is discarded and only absolute `PATH` entries are searched |
| A configuration saved as UTF-8 with a byte-order mark (Windows PowerShell 5.1 `-Encoding UTF8`) failed with "invalid syntax at line 1, column 1" | `b8a4218`: a leading byte-order mark is removed before parsing |

At `b8a4218`, locked sync, Ruff lint/format, 431 tests, `uv build` and
`scripts/check_package.py` passed.

**More SSH targets.** Jadon approved two more aliases for machines outside his
homelab; their names stay in the ignored configuration. The agent ran the current
checkout with `uv run --locked ssh-workbench` in a new owned Windows Terminal
window, under the same rules as the earlier check. It printed no remote output and
took no screenshots of SSH sessions.

| Target | Agent-observed result |
| --- | --- |
| Second alias, first attempt (the workstation's VPN was off) | Native SSH reported a connection timeout. Workbench returned with `SSH exited with status 255. Check the SSH client's message and alias; C retries.` and kept the project selected. This is the first real-world check of the nonzero-exit path |
| Second alias, retry with the VPN on | A remote shell prompt appeared with no password or host-key prompt; `exit` returned `SSH exited with status 0.` with the selection kept. Ctrl+Q then exited 0 and `Write-Output` worked |
| Third alias | Same as the retry: remote prompt, `exit`, status 0, selection kept. Q exited 0 and `Write-Output` worked |

A harness bug sent one extra Ctrl+C after the third alias's `exit`. It reached
Workbench after SSH had returned, and Textual showed its built-in "Do you want to
quit? Press ctrl+q to quit the app" notice. Workbench kept running and no input
reached the remote host. The harness was corrected.

### Task 5 user-executed manual session

Results below distinguish user reports from agent observations. This manual
session follows the prepared installed build, version 0.0.1 from `9b28e86`;
the agent did not observe the user's executable or authentication session.

**User-reported, 2026-10-12:** In Microsoft Windows Terminal running PowerShell,
C switched to SSH in the same terminal session. Exiting SSH returned directly
to Workbench, kept the same project selected, accepted Up/Down immediately, and
displayed `SSH exited with status 0`. This completes the reported handoff/normal
return check; it does not establish browser dispatch, resize or quit restoration.
No sensitive transcript or screenshot was requested or collected for this report.

The checklist below records Windows Terminal status. Step C is Jadon's report.
Steps A, B and D passed in the
[agent Windows Terminal check](#task-5-authorized-windows-terminal-check-2026-10-20),
which also repeated C. Those are agent observations, not user reports.

- [x] **A. Baseline (local; agent-observed pass, 2026-10-20):** Record 0.0.1, the tested commit, Windows version and
  Windows Terminal version. Fill the private configuration, launch with the command
  above, and check Up/Down selection, details, Tab/Shift+Tab focus and detail scrolling.
- [x] **B. Browser (opens real destinations; agent-observed pass, 2026-10-20):** Select `manual-target`; explicitly
  invoke R / Repository and D / Documentation. Observe the intended destination
  and page result in the browser separately from Workbench's dispatch message.
  Return to the terminal, check navigation and Q, then relaunch for C.
- [x] **C. SSH (user-reported pass; contacts the chosen real system):** Use one existing noncritical
  host and the account already used there. If a direct baseline is needed, Jadon
  runs `ssh CHOOSE_EXISTING_ALIAS` after replacing the placeholder, authenticates
  privately and leaves normally. In Workbench use C / Connect, authenticate,
  leave normally, and verify the same selection, list focus, status and further use.
- [x] **D. Restoration (local; agent-observed pass, 2026-10-20):** After returning, resize the terminal and check
  navigation. Test Q and Ctrl+Q in separate launches; after each, confirm usable
  shell input, for example `Write-Output 'shell input works'`.

For deliberate failures, blocked openers and aggressive interruption, use only
the existing [link fixture](#task-4-stubbed-link-checklist) and
[local-child fixture](#task-3-local-terminal-fixture). Do not use wrong credentials,
interrupt unrelated remote work, stop services, change host keys or create outages.
The authorized Windows Terminal check above is complete within its recorded scope.

Report further observations briefly and without sensitive details: step A/B/C/D, pass/fail/not tested, expected
versus observed behavior, version/commit/terminal and any minimal reproduction.
Label them **user-reported**; keep agent fixture and automated evidence separate.
Browser acceptance alone is not proof of page loading. The readiness review
(scope, privacy, license) closed Task 5 on 2026-10-20.

## Task 4: errors and links, 2026-10-12

Starting state was inspected and fetched: clean `main` and `origin/main` both
pointed to Task 3 merge `eeb6e39bf93a8ba1532503a7a2e0e565f9a9d8f2`, with the expected
`jkosber/ssh-workbench` origin. No Task 4 branch existed; `feat/errors-and-links`
was created from that commit. No unrelated tracked work needed preservation.
Existing ignored evidence was preserved. Version 0.0.1, Python 3.14.7,
Textual 8.2.8 and the lockfile/dependencies are unchanged.

These are **local Windows results from the implementation session**, not remote
CI for Task 4. At that handoff, nothing had been staged, committed, pushed,
opened as a PR or published. Earlier Task 3 Windows/
Ubuntu CI and terminal evidence below remain historical evidence for that merge.

| Check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed with the existing environment and lockfile |
| CLI help/version | Passed; version remains 0.0.1 |
| `uv run --locked ssh-workbench` | Native no-config screen; R/D explained no selection; Q returned status 0 to the shell |
| Ruff lint and format | Passed |
| Full pytest, fresh ignored base directory | 417 passed: 289 prior tests, 92 URL/boundary cases, 35 link UI/concurrency cases, one additional negative SSH status case |
| `uv build` | Source archive and wheel built; existing warning that the installed uv 0.13.0 is outside the project's uv-build range remains, with no dependency change |
| Isolated package validation | Passed CLI/config/loader, verified wheel imports, headless actions, substituted SSH/link results and separate-process blocked-opener Q/Ctrl+Q exits |
| Documentation and final review | 43 relative links/anchors and whitespace checks passed; source and README/UI semantic review completed; deterministic code scan reported no findings (README skipped by prose scope) |
| Native WezTerm fixture | Accepted, reported failure, raised error, missing links, repeat/blocked requests, scrolling, resizing and both quit keys passed through substituted boundaries |
| Native screenshots | Attempted with the established Windows capture helper; owned test window could not be brought to foreground reliably. Captures were obscured, excluded as evidence and removed |

The first targeted run exposed a real scroll shift when link status changed
height; a fixed three-row status region corrected it. A later source review found
the closed-loop posting race and ambiguous clipped long IDs; a narrow posting
guard and captured project number corrected them, with focused regressions.
The final full suite includes those corrections. One initial pytest invocation
also hit an access-denied error cleaning the shared Windows temporary-directory
link; subsequent complete runs used fresh `.local` base directories without
changing permissions or deleting the shared directory.

### Task 4 acceptance evidence

| Criterion | Verification and limits |
| --- | --- |
| Existing configuration and SSH errors remain actionable | Original loader/CLI/SSH tests passed. Nonzero and negative codes retain their value and add neutral client-message/alias retry guidance; interruption offers C/Q |
| Explicit R/D with visible bindings from both panes | Headless keyboard checks at all three sizes; native accepted requests from list and details; footer controls visible in terminal text |
| No automatic action; absent links/no selection | Guarded startup/navigation/focus/Enter/click/resize tests; missing links and native no-config R/D feedback passed |
| Capture project, kind and exact URL | Both keys pass their selected URL including query/fragment/encoding; slow completion preserves newer selection, focus and scrolling and attributes the original project |
| Literal, sanitized output | Markup/control metadata stays literal; errors omit private markers and query values; long IDs cannot obscure the captured project number |
| Shared validation and independent dispatch | Loader and boundary contract cases passed; malformed URLs cannot reach Windows/GIO calls; exact argv and detached/null terminal streams asserted |
| Outcomes and supported environment policy | Accepted/missing/invalid/unavailable/failure/exception cases passed with substitutions. Windows associations and Linux desktop GIO implemented; macOS/other environments explicitly unavailable |
| Responsiveness/repeats/shutdown | Event-controlled slow requests permit navigation and quit; repeats do not queue; stale messages and closed-loop races are discarded. Installed subprocesses exit with a forever-blocked opener on both quit keys |
| No SSH lifecycle interference | Original real-suspension, SIGINT restoration and lookup/transition regression tests passed. A pending browser completion during substituted SSH preserves both statuses and the newer selection |
| Layout and scrolling | Headless 60x20/80x24/120x40 checks passed. Native WezTerm dimensions and text verified live resizing and wrapped/scrollable content; this session has no usable native pixel evidence |
| Packaging and records | Isolated Python `-I` runs and assertions verify every imported Workbench module resides in the disposable installation, even with checkout `PYTHONPATH`; documentation and vault session/project/daily records updated |

### Task 4 native fixture details

The existing portable WezTerm `20240203-110809-5046fc22` ran in a new owned
process with an explicit test configuration, no SSH/WSL domains and a clean
PowerShell profile. `scripts/check_links.py` used fictional projects and stubbed
Windows `os.startfile`; reported failure was also substituted because startfile
has no failure return value. Guards rejected other browser, process and network
actions. No real browser, website, SSH configuration, keys, inventory or host was
used. The application dependency set and global terminal settings were untouched.

Verified process/socket identity preceded CLI input. Readiness checks used
expected terminal text and reported dimensions. The same fixture resized
80x24 -> 60x20 -> 120x40 -> 80x24 at 96 DPI. Both actions accepted from either pane;
failed/missing/error cases showed safe guidance at 60x20. The long fixture stayed
at the same scroll position after an accepted request: before/after screen text
differed only in the link-status line. A blocked request retained its original
project number while selection/focus moved and repeated R/D reported pending.
Q and Ctrl+Q each exited status 0 despite the indefinitely blocked stub; both
shell input/echo checks passed. A normal no-config CLI run also exited cleanly.

Some early resize snapshots preceded the application's redraw, and one expected
text condition spanned a wrapped line; settled text and narrower readiness
conditions confirmed the final states. No resize workaround was introduced.
The screenshot helper could not verify the owned window as foreground, so no
appearance claim is made. Existing Task 2 native screenshots remain valid for
their recorded state. The owned terminal/process was closed; reproducible text
and dimension evidence remain ignored locally.

### Task 4 stubbed link checklist

These commands do not open a real browser or connect to SSH:

```text
uv sync --locked
uv run --locked ssh-workbench --help
uv run --locked ssh-workbench --version
uv run --locked python scripts/check_links.py
```

1. Select the accepted fixture; try R from the list and D from details, then
   reverse them. Check literal metadata, the request result and unchanged focus.
2. Try reported failure, raised error and missing links. Confirm useful feedback
   with no raw exception/query data. Retry an action after its result.
3. Use the long fixture, scroll with Page Down/End, invoke a link and verify
   preserved scrolling. Resize to 60x20, 80x24 and 120x40 and check the footer.
4. Choose the blocked fixture last. Press R/D again, change selection/pane and
   confirm the original request remains identified. Q must return to the shell;
   repeat with Ctrl+Q. The stub stays blocked until process exit.

### Task 4 fixture lifetime correction, 2026-10-12

The review after the original runs above returned **FIX BEFORE COMMIT**. It
confirmed a development-fixture defect: `check_links.py` removed its external-action
patches when `app.run()` returned, although a daemon already past its shutdown
check could still reach dispatch. A controlled Windows reproduction reached an
outer sentinel after teardown; no real browser opened. The original 417-test and
WezTerm results above describe the pre-correction candidate, not this correction.
No production application regression was confirmed.

The fixture entry point now starts every guard before constructing the app and
intentionally leaves them installed until process exit, including after normal
return, `RuntimeError` or `KeyboardInterrupt`. It registers no restoration
cleanup, waits for no blocked daemon and uses no forced interpreter exit.
Importing the script installs no guards. Production application, SSH/SIGINT,
version 0.0.1, dependencies, build requirements and CI tooling are unchanged.

[Fixture regressions](../tests/test_link_fixture.py) run the actual entry point
through a [child-only harness](../tests/link_fixture_process.py). Events pause a
real R-triggered application worker inside URL validation, after its shutdown
check but before dispatch. Q closes the TUI and the entry point returns or raises;
only then does the harness release validation. Positive dispatch and completion
events establish that the worker ran. Harmless outer sentinels remain beneath
the fixture guards, including when testing the defective version.

| Correction check | Observed result |
| --- | --- |
| Same six race tests against a disposable pre-correction copy | All six failed as expected: fixture dispatch 0, outer sentinel 1, guards restored; normal/error/interrupt cases on both dispatch paths |
| Corrected fixture tests | 11 passed: six race cases, four blocked-opener exits, one import-side-effect check |
| Race completion | Fixture dispatch 1, outer sentinel 0; all guarded callable identities retained after entry-point unwind |
| Blocked-opener interpreter exit | Q and Ctrl+Q passed for Windows and simulated Linux; the original fixture stub remained blocked. A parent timeout fails the test, rather than supplying passing exit evidence |
| Affected fixture/link/UI tests | 138 passed, including Windows success with `os.startfile` explicitly returning `None` |
| Full pytest with a unique disposable base directory | 428 passed; no temporary-directory cleanup error |
| Locked sync, Ruff lint/format, CLI help/version | Passed; 29 files (20 Python, 9 Markdown) formatted and CLI version 0.0.1 |
| Build and isolated package validation | Passed, including installed-import assertions and existing blocked-opener Q/Ctrl+Q processes |
| Relative documentation links/anchors and whitespace | 45 links/anchors passed; `git diff --check` passed |
| Focused independent review | No additional correction defect found; this was a static review, not another native-platform run |

The existing build warning recurred: uv 0.13.0 is outside the declared
`uv_build>=0.12.24,<0.13.0` range. No tooling was upgraded or requirements changed
to suppress it. The build and installed-package checks passed; the prior review's
backend-provenance limitation remains.

After the correction and regressions passed, the standalone script was exercised
in an owned Windows pseudoterminal through the supported cmd.exe/PowerShell route.
R from the list and D from details reported accepted fixture requests. A blocked
request allowed repeated-action feedback, changed selection and pane focus.
Q and Ctrl+Q each returned application status 0 to working PowerShell input; the
owned shell then exited normally. This was a focused terminal input/return check,
not a repeat of WezTerm resizing or screenshot verification. No new screenshots
were taken, and obscured historical captures remain excluded.

Linux-path tests simulate the platform and GIO lookup/runner on Windows; they do
not establish native Linux desktop behavior. All browser/process dispatch in
these fixture tests was substituted. No real browser, GIO dispatch, host or SSH
configuration was used. At the correction handoff, changes remained unstaged and
uncommitted on `feat/errors-and-links` at base
`eeb6e39bf93a8ba1532503a7a2e0e565f9a9d8f2`. No Task 4 remote CI had run and no
Task 5 work was performed. Subsequent PR and CI status belongs in the PR record.

**Would open a real browser:** running the normal application with a configured
URL and pressing R/D (or clicking its footer action). This was not tested.
A separately approved manual test should name the URL and running environment,
then observe actual dispatch; Workbench cannot establish page loading or closure.
Real SSH/authentication/host-key prompts, Linux desktop dispatch, macOS execution,
Windows Terminal handoff, other DPI settings and screen readers remain unverified.
Jadon's earlier Windows Terminal navigation confirmation is not SSH handoff
evidence. No Task 5, release, portfolio or infrastructure work was performed.

## Task 3: native SSH, 2026-10-12

Implemented on `feat/native-ssh` from clean, fetched `main` at
`4852e1c3719700d1e5ea8d6c867bf13bd3c50eb0`. Before branching, PR #2 was verified
merged, local main matched origin, no open PRs existed and
[merged-main CI](https://github.com/jkosber/ssh-workbench/actions/runs/38304097388)
had passed. That CI result applies to Task 2. Task 3 was initially held
uncommitted for review. On 2026-10-12, Jadon authorized staging, committing,
pushing this feature branch and opening a PR after checking the Task 3 criteria.

Version remains 0.0.1; Python 3.14.7, Textual 8.2.8, dependencies and lockfile are
unchanged. All development fixtures are fictional. Executable lookup and process
invocation were substituted; no real SSH client, configuration, keys, inventories
or hosts were used.

| Local Windows check | Observed result |
| --- | --- |
| Locked sync | Passed without dependency changes |
| Ruff lint and format check | Passed |
| Full pytest suite, fresh explicit `.local` base directory | 289 passed: all 213 preexisting tests plus 76 launch, signal and UI cases |
| CLI help, CLI version and module version | Passed; Connect description updated, version remains 0.0.1 |
| No-config CLI in a Windows pseudoterminal | Correct empty message and disabled C binding; C remained inert and Q exited with status 0 |
| Build | Source archive and wheel built successfully at 0.0.1 |
| Isolated wheel validation | Passed outside the checkout with locked runtime dependencies: help/version, loader, missing-config errors, headless selection/quit, and substituted SSH success, status 7, start error and interruption |

Local uv 0.13.0 still warns that the existing build-backend range excludes
0.13.0; the build and isolated installation succeeded with the unchanged range.
An initial focused test run using the shared pytest temporary directory hit the
previously observed Windows `pytest-current` cleanup permission error. A fresh
explicit base directory passed; no permission changes or weakened tests were
used. The isolated package environment was removed normally.

The new tests assert the exact absolute executable/one-alias argv, `shell=False`,
inherited streams, Windows `ssh.exe` versus POSIX `ssh` lookup, alias/type
rejection before lookup, sanitized launch errors and restoration of the original
SIGINT handler. They retain process/network/browser guards. UI tests cover no
selection, no automatic launch, visible C binding, selected alias, status and
focus restoration, repeated/reentrant actions, unsupported suspension and long
literal/scrolling content at 60x20, 80x24 and 120x40.

Exception-path tests use **installed `App.suspend()`**, replacing only the
headless driver's suspension methods. Textual 8.2.8 has a bare yield followed by
resume, so the app catches expected errors inside the context. Assertions verify
suspend/launch/resume ordering after success, nonzero exit, launch error and
`KeyboardInterrupt`. Source inspection also confirmed why the parent needs a
temporary callable SIGINT handler: asyncio may otherwise cancel its main task,
and subprocess may terminate a still-running child during exception cleanup.

Independent review found and corrected an interruption gap before the original
signal guard: Ctrl+C during executable lookup could cancel asyncio's main task.
The shared guard now spans lookup and the entire suspend/resume cycle. Eight
regression cases run with asyncio's actual installed SIGINT handler, invoking
the active handler during lookup and both driver transitions, on success and
error paths. Cancellation counts stay zero, the original handler is restored,
and the browser remains usable after yielding to the event loop. The focused
review follow-up confirmed the fix with no remaining finding. The native
terminal checks below were repeated after this correction.

Final diff/whitespace and package-content checks passed; wheel modules match the
source and both archives exclude private workspace directories. All 39 relative
documentation links/anchors resolve. The deterministic code scan reported no
findings; README was outside its configured prose scope and was read in review.

### Real Windows terminal evidence

The agent ran `scripts/check_terminal.py` through `uv run --locked python` in a
new, isolated native WezTerm `20240203-110809-5046fc22` window on Windows. The
terminal reported 80x24 at 96 DPI, `xterm-256color` and `truecolor`. Its fixed local
Python children replace SSH while retaining production alias validation,
signal handling, `App.suspend` and result rendering.

| Native terminal check | Agent-observed result |
| --- | --- |
| Terminal ownership | Child stdin, stdout and stderr all reported `isatty=True`; typed text was echoed and read by the child, and its stderr appeared directly |
| Normal and nonzero exit | Status 0 and 7 returned to the same project; navigation worked immediately afterward |
| Connect from details | C launched the selected alias; afterward Down changed the project, confirming focus returned to the list |
| Ctrl+C ending a child | Child received Ctrl+C and returned 130; the browser resumed and displayed 130 |
| Ctrl+C while a child continues | Two successive interrupts reached the child; it stayed active, accepted more text and returned only after explicit input; the browser then displayed status 0 |
| Missing executable and process-start error | Both showed the expected messages with the selection intact; repeated failed launches and subsequent navigation worked |
| Injected launch interruption | `KeyboardInterrupt` returned to the browser with an interruption message and usable navigation |
| Repeat launch and quit | A fresh interactive-shell launch connected again; Q and Ctrl+Q returned to PowerShell with app status 0, and subsequent commands were accepted and echoed |

An initial `pwsh -File` harness ended after quitting because Ctrl+C had also
cancelled the enclosing PowerShell script. Repeating with an interactive
`-NoExit` shell established a working prompt and status 0. This was a test-harness
correction; no application workaround or shell profile changes were made.
All owned test windows and their shell/child processes exited. Existing user
terminals were preserved. Text captures, terminal metadata and an evidence-check
summary remain under ignored `.local/task3-native-20261012/`.

This is native process/input evidence, not a headless or browser screenshot
claim. Jadon separately reported on 2026-10-12 that Task 3 navigation works in
Microsoft Windows Terminal. This is human-reported navigation evidence; it does
not establish terminal handoff, interruption or authentication behavior in that
terminal. Real SSH authentication,
host-key prompts and connections remain untested and require separately approved
targets/actions. Linux/macOS native terminal behavior, Microsoft Windows
Terminal handoff, native resizing, other DPI settings and screen readers remain
unverified for this change.

### Task 3 local terminal fixture

From an interactive terminal, run:

```text
uv run --locked python scripts/check_terminal.py
```

This script accepts only built-in fictional cases. It replaces executable lookup
and process invocation before calling the production launcher; it never invokes
SSH or loads a project inventory. Use this fixture for development handoff checks.

1. Select **Normal exit**, press C, check that all three terminal flags are True,
   type some text and confirm the child echoes it. Type `return` and verify status
   0, the same selection, list focus and working arrow keys.
2. Select **Nonzero exit**, Tab to details, press C, then type `return`. Check
   status 7 and that Down changes the selection afterward.
3. Select **Ctrl+C exits the child**, press C and Ctrl+C. Check status 130.
4. Select **Ctrl+C keeps the child running**, press C and Ctrl+C twice. Confirm
   the child still accepts text. Type `return` to resume the browser.
5. Exercise the three simulated error/interruption entries. Check their messages,
   preserved selection, navigation and repeated C actions.
6. Quit with Q and confirm shell input/echo. Run the fixture again, connect and
   return, then quit with Ctrl+Q and check the shell again.

Record the terminal, operating system and actual results. This local fixture does
not verify the native SSH client's authentication or network behavior.

### Task 3 pre-PR verification, 2026-10-12

Jadon authorized the commit, push and PR after confirming navigation in
Microsoft Windows Terminal. A fresh local run found one intermittent footer
assertion: the test queried keys while Textual was asynchronously removing and
remounting them. The Connect action remained enabled. A probe reproduced that
transient state once in 40 starts, and the next refresh restored the keys.

The visibility test now waits for the Connect key with a bounded five-second
timeout and retains every count, key, visibility, label, screen-region and
no-launch assertion. Sixty startup probes across the three test sizes passed;
six needed another readiness pause. No application code changed for this fix.

After the test correction, all 289 tests and Ruff lint/format checks passed.
Locked sync, CLI help/version, build and isolated package validation also passed,
as did all 39 relative documentation links/anchors and whitespace checks.
The README and PR draft received a documentation review with no actionable
findings. The earlier native fixture evidence still applies to the unchanged
application code.

### Task 3 PR and remote CI, 2026-10-12

[PR #3](https://github.com/jkosber/ssh-workbench/pull/3) was opened from
`feat/native-ssh` into `main` after the authorized commit and push. Implementation
commit `da64844f47a4f872ca1ece582d70049eab68a422` contains the Task 3 behavior,
tests, fixture and documentation, including the footer-test readiness correction.

[Push CI 38325768048](https://github.com/jkosber/ssh-workbench/actions/runs/38325768048)
and [PR CI 38325776914](https://github.com/jkosber/ssh-workbench/actions/runs/38325776914)
passed on both Windows and Ubuntu. Each job passed locked installation, Ruff,
all 289 tests, build and isolated package validation. These results apply to
`da64844`. The documentation follow-up at `b71423c` also passed
[push CI 38325986119](https://github.com/jkosber/ssh-workbench/actions/runs/38325986119)
and [PR CI 38325990481](https://github.com/jkosber/ssh-workbench/actions/runs/38325990481)
on both platforms, including 289 tests and isolated package checks. All 40
relative documentation links/anchors resolved. The PR records checks for later
documentation commits, its merge commit and current status.

CI verifies automated and substituted process behavior. Linux native terminal
handoff, macOS execution, real SSH authentication and the remaining terminal
limits above still need their own evidence.

## Task 2 PR documentation and remote CI, 2026-10-12

[PR #2](https://github.com/jkosber/ssh-workbench/pull/2) contains the read-only
project browser, tests, fictional example and updated usage, architecture,
contribution, roadmap and changelog documentation. Its implementation commit is
`aacbb6ddda37d38b39c4e4ccc9f104bf4466dce1`; local files matched that pushed tree.

[Push CI 38302914229](https://github.com/jkosber/ssh-workbench/actions/runs/38302914229)
and [PR CI 38302918709](https://github.com/jkosber/ssh-workbench/actions/runs/38302918709)
both completed successfully for that commit. Each Windows and Ubuntu job passed
locked installation, lint/format, all 213 tests, the build and isolated wheel
checks. Job logs confirm the test count and installed-package browser checks.

This documentation-only follow-up records those observed results; it changes no
application code, dependencies or version. The PR records checks for its current
head and its merge status. Task 3 was unimplemented at that point; its later
implementation and verification are recorded at the top of this document.

## Task 2 final local verification, 2026-10-12

Before committing Task 2, locked sync, Ruff lint/format, all 213 tests, CLI
help/version, module version, the build and isolated installed-wheel check passed
again on Windows with Python 3.14.7 and Textual 8.2.8. The package remains 0.0.1;
dependencies and the lockfile are unchanged. Local uv 0.13.0 warned that the
existing build-backend range excludes 0.13.0; both artifact builds and installation
checks succeeded with that existing range. CI still pins uv 0.12.24.

The earlier report of disappearing project names was a mistaken screenshot
interpretation. Reinspection of the original, settled and timer-driven 120x40
captures shows both names clearly while details has focus. An independent review
confirmed this and repeated headless 60x20 -> 120x40 rendering twice: both labels
remained in the exported SVGs and rendered list rows. No application defect or
production workaround was established; the inaccurate finding below is corrected.

The user delegated terminal checks to the agent and authorized committing the
verified Task 2 work and opening a PR into `main`. The preceding console, browser
and native screenshot checks provide that evidence. Human review and merge
authorization remain separate. Windows Terminal live resizing, other DPI settings
and screen readers were not tested. This section records local results only;
the remote CI evidence is recorded above.

## Task 2 desktop screenshot follow-up, 2026-10-12

At the user's request, direct desktop capture worked around the desktop tool's
missing terminal-window targets. Windows
[Graphics.CopyFromScreen](https://learn.microsoft.com/en-us/dotnet/api/system.drawing.graphics.copyfromscreen)
captured the primary 1920x1080 monitor, and the agent inspected the saved PNGs.
This establishes a working native screenshot route. The test window must be
visible and unobstructed; this method captures the desktop as displayed.

Windows Terminal 1.25.2733.0 was inspected at a console-confirmed 80x24. Its
test tab was brought forward with the terminal's `focus-tab` CLI command.
The initial project selection, focus border, all five fields and footer were
visible. This was a startup appearance check, not a live-resize or keyboard
check in Windows Terminal.

Portable WezTerm screenshots covered 80x24, 60x20 and 120x40, then return to
80x24. They showed selection, pane focus, narrow reference wrapping, scrolling
to the final field, and Studio's absent references. The initial tool-launched
process inherited `NO_COLOR=1`; removing it only in the test child restored color.
The colored WezTerm child reported `xterm-256color` and `truecolor`. No personal
profile or global environment was changed.

**Corrected observation:** the 120x40 captures show both project names while
details has focus. An initial claim that the names disappeared was incorrect,
as confirmed by reinspection and independent review. Focusing the list changes
its selection highlight and border as expected; it does not restore missing text.

The colored WezTerm run exited with status 0 and restored working shell input
and echo. Owned test windows were closed; existing user terminals were preserved.
Screenshots, the capture helper and evidence remain under ignored `.local/`;
desktop images were not added to Git. No application or dependency changes were
needed. The prior automated results remain current; no suite rerun was needed
for this experiment. Other DPI settings and screen readers were not tested.

## Task 2 native terminal follow-up, 2026-10-12

A separate Windows Terminal 1.25.2733.0 window launched the supported fictional
example with an 80x24 size request. The user confirmed seeing the test window.
The desktop tool did not return that window as a capture/input target, so its
appearance and native resize behavior could not be inspected in that attempt.
Window visibility alone is not a visual acceptance result. The later desktop
screenshot follow-up above establishes a separate capture route.

The official portable WezTerm `20240203-110809-5046fc22` Windows archive was
verified against its published SHA-256 and extracted under ignored `.local/`.
An explicit test configuration, separate process/class and isolated PowerShell
session kept the check independent of personal terminal configuration. The
application still used locked Python 3.14.7 and Textual 8.2.8.

| Native WezTerm check | Agent-observed result |
| --- | --- |
| Live window resizing | The same running application resized through 80x24 -> 60x20 -> 120x40 -> 80x24 using `window:set_inner_size`; CLI-reported pane dimensions matched each size at 96 DPI |
| Project navigation | Up/Down changed Garden/Studio details; selection persisted during resizing and changing selection reset details to the top |
| Pane focus and scrolling | Tab/Shift+Tab changed the pane receiving input; End in details reached both absent optional references at 60x20; expanding restored all fields |
| Narrow layout | Captured terminal text showed wrapped Garden references at 60x20 and complete layout recovery at larger sizes |
| Q and Ctrl+Q | Separate application runs exited with status 0, restored an 80x24 PowerShell console, and accepted/echoed the test input afterward |

WezTerm's `cli list`, `get-text` and `send-text --no-paste` worked when directed
to the verified test process's socket. Class-based discovery failed in this
environment. Input delivery completes before application redraw; early snapshots
were stale, so later observations confirmed the expected changes. Watched-file
configuration reloads called the documented
[native window sizing API](https://wezterm.org/config/lua/window/set_inner_size.html);
this was not browser resizing or a headless test. The upstream CLI documents
[screen-text retrieval](https://wezterm.org/cli/cli/get-text.html) and
[input delivery](https://wezterm.org/cli/cli/send-text.html).

The desktop tool also did not expose WezTerm for capture. Text/ANSI captures and
reported dimensions establish native terminal behavior, not rendered-pixel,
font, antialiasing or visual-focus verification. Native screenshots were obtained
in the later desktop follow-up above; screen-reader behavior remains unverified.

Both test terminals were closed, preserving the user's existing terminal.
The isolated harness and text/dimension evidence remain under ignored `.local/`.
No application or dependency changes were needed; no global settings, staging,
commits or pushes changed. No additional automated-suite run was needed for this
terminal experiment and documentation update.

## Task 2 browser visual follow-up, 2026-10-12

The existing Playwright browser tools exercised the real application through
`textual-serve` 1.1.3 on localhost. The helper ran with `uv run --locked --with
textual-serve==1.1.3`; it was not added to the project dependencies or lockfile.
The application still used locked Textual 8.2.8 and Python 3.14.7. Only the
supported fictional example was loaded.

Agent-inspected screenshots covered 80x24, 60x20 and 120x40 cell layouts
(720x504, 540x420 and 1080x840 browser pixels with the measured 9x21 cell size).
The same running session resized through 80x24 -> 60x20 -> 120x40 -> 80x24.
Selection survived resizing. Up/Down changed the selected project and its
details; Tab/Shift+Tab visibly moved pane focus. At 60x20, reference text wrapped
and End scrolled to the final optional field. Returning to a larger size restored
the full layout. Q ended the application session, confirmed by the browser's
`Session ended` message.

Screenshots and browser-tool logs are retained locally under ignored `.local/`.
The temporary tab and server were closed after the check. No application-code
changes, global settings, security changes, staging, commits or pushes were
needed. These are browser-rendered visual and live-resize results, separate from
the console evidence below. Normal Windows Terminal font/DPI behavior, native
window resizing and screen-reader behavior remain unverified; no human visual
confirmation is claimed.

## Task 2 interactive console follow-up, 2026-10-12

The installed application was exercised through a real Windows pseudoterminal
at 80x24, independently of Textual's headless pilot. The normal tool PowerShell
launch failed with `Access is denied` before the app started. Selecting the
existing `cmd.exe` shell worked; an isolated `pwsh -NoProfile` session launched
through it also worked. No security settings or user profiles were changed.
This establishes console input/output behavior, not a visual check in the user's
normal Windows Terminal window.

| Flow | Agent-observed result |
| --- | --- |
| Supported two-project example | Garden starts selected; Down shows Studio's ID/name/alias and two `Not provided` references; Up restores Garden and both references |
| Focus and long details | Tab/Shift+Tab switch panes; Page Down/Page Up and End/Home reach long references and return to the initial fields; selecting another project resets the details to the top |
| Literal and Unicode display | Fictional Japanese text and `[bold]` text remain visible; newline/tab/ESC/direction characters appear as literal escapes in the terminal output; long names truncate in the list and wrap in details |
| Quoting paths | Explicit configuration with a space in its filename loads successfully |
| Q and Ctrl+Q | Both exit cleanly; Q was also exercised from details focus; the PowerShell prompt returns and subsequent typed commands report application exit status 0 |
| No configuration and empty array | Distinct informative screens appear; both quit cleanly with status 0 |
| Missing file and invalid alias | Concise field/domain errors appear without a traceback or supplied alias; PowerShell reports status 2 |
| Help/version with a nonexistent config | Both work without loading the file; version stays 0.0.1 |
| Input preservation | All three temporary fictional files retained their original UTF-8/Windows-newline bytes; the missing file was not created |
| Existing full suite | 213 tests passed again using a fresh explicit pytest base directory, including headless 80x24/120x40/60x20 and resize coverage |

The test terminal was closed after verification. No application-code changes
were needed. At this stage Task 2 was unstaged/uncommitted, with no push or new
remote CI; later verification and handoff are recorded above.
Normal Windows Terminal appearance, real-window resizing and screen-reader
behavior remain unverified; no human visual confirmation is claimed. The manual
checklist below is retained for reproduction, with its functional paths now
covered by this additional console evidence.

## Task 2: project browser, 2026-10-09

Implemented locally on `feat/project-browser`, based directly on fetched
`origin/main` at `84d392f0e4fa00eaf129ecae715dff4262e4f97e`. Local `main` was
fast-forwarded to that merge without forcing or discarding work. The working
tree was clean at transition: earlier scaffold validation edits and shared
Serena settings were already committed in Task 1. All earlier evidence below
is retained. No Serena files or ignore policies were changed for Task 2.

Version remains 0.0.1, unreleased; dependencies and schema are unchanged. Task 2
was unstaged and uncommitted at this initial check, with no push or PR. These are
**local Windows results**, using Python 3.14.7 and Textual 8.2.8, not Task 2 remote CI.

| Acceptance criterion | Observed evidence |
| --- | --- |
| Explicit CLI-to-loader entry; no config discovery/writes | Real-loader CLI tests preserve file order, records and input bytes; no-config test rejects loader calls and fixture reads; installed-wheel smoke check exercises CLI to real headless UI |
| Clear no-config, empty, invalid and unreadable states | Both empty screens tested at 80x24, 120x40 and 60x20; malformed TOML, invalid schema fields, invalid UTF-8, missing files and simulated permission errors return sanitized status 2 before UI startup |
| Help/version independent of config | Console tests pass with a nonexistent `--config` before and after help/version; existing unknown-option coverage retained |
| Predictable selection, focus and all five details | Initial first selection/focus, loader order, Up/Down bounds, changing fields, absent optional references and Tab/Shift+Tab focus tested |
| Literal values; safe controls; original records retained | Markup/action/link-like names and URLs render as plain content with no markup spans; clicks/Enter remain inert; C0/C1, terminal escape, direction-control and separator cases show visible escapes; Unicode names and original object values checked |
| Long values and ordinary terminal sizes | All five long fields exercised with wrapping/scrolling at 80x24, 120x40 and 60x20, plus resize, pane bounds, no horizontal overflow, End scrolling and scroll reset on selection; 35-project list keeps selected row visible |
| Quit and read-only boundary | Q/Ctrl+Q exit with status 0 in no-config, empty and populated states, including details focus; common socket, process and browser boundaries fail application tests if called |

| Local check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed; no dependency changes |
| `uv run --locked ruff check .` | Passed |
| `uv run --locked ruff format --check .` | Passed; 19 Python files formatted |
| `uv run --locked pytest --basetemp <fresh-directory>` | 213 passed: 24 headless UI, 15 CLI and 174 loader tests |
| CLI help, CLI version, module version | Passed; help lists `--config PATH`; version remains `ssh-workbench 0.0.1` |
| `uv build` | Passed; source archive and wheel built at 0.0.1 |
| `uv run --locked python scripts/check_package.py` | Passed outside checkout: isolated locked-runtime install, help/version, missing-config error, loader and CLI-driven headless selection/quit at 80x24; fixture bytes unchanged |
| Diff, documentation links and package contents | Whitespace check passed; 23 local links/anchors resolved; wheel modules matched source; archives excluded `.local/`, `.serena/`, `.venv/` and Git metadata |
| Final review | Primary diff review and independent static review found no actionable defects; targeted added-content scan found no private absolute paths or credential-token patterns; staging area remained empty |

Tests use fictional metadata and temporary files. Fresh explicit pytest base
directories avoided the earlier shared-temp cleanup issue; no permissions or
security settings were changed. The isolated package environment was removed
normally. No actual SSH files or hosts were used.

The scaffold-only startup assertion now checks the intentional no-config screen;
the help expectation now includes the implemented configuration option. The
supported example contains two fictional projects for selection and absent-field
checks; its loader test still compares the exact expected records. No existing
coverage was skipped or removed to conceal a failure.

During verification, an overbroad test guard initially blocked Windows asyncio's
own local socket pair. The low-level connection guard now starts after event-loop
creation and before application execution. A long-details check also exposed
scrollbar-width reflow; the details pane now reserves scrollbar space. Tests wait
for completed scrolling animations before checking positions. The final full
suite passed with the original no-horizontal-overflow assertion retained.

The independent review covered the changed code, tests, documentation and
installed Textual behavior; it did not rerun the suite or inspect a real terminal.
The deterministic style scan reported one false positive in a test failure
message, not a code comment; README was outside that scanner's configured prose
scope and was read during review. These checks do not establish screen-reader
behavior, terminal restoration or a new Linux result.

### Task 2 Windows terminal checklist

The user delegated these checks to the agent. The 2026-10-12 console, browser,
native terminal and desktop screenshot follow-ups above record the results and
their limits. They do not claim human acceptance. This checklist remains available
for Jadon's PR review; the earlier scaffold confirmation does not verify this browser.

From the repository directory, run:

```text
uv sync --locked
uv run --locked ssh-workbench --config examples/projects.example.toml
```

- At 80x24, check that Garden demo starts selected/focused. Use Up/Down to select
  Studio demo and return; confirm all fields change and Studio's references say
  `Not provided`.
- Use Tab/Shift+Tab to check the visible focus border. With a temporary fictional
  configuration containing long names/references, scroll details with arrows,
  Page Up/Page Down and Home/End. Change selection and confirm scrolling resets.
- Resize the terminal and inspect readability, Unicode and literal markup-like
  text. References should have no application opening action.
- Quit with Q, rerun, and quit with Ctrl+Q. Confirm the shell prompt, echo and
  keyboard input return normally.
- Run without `--config`, then with a temporary `schema_version = 1` /
  `projects = []` file; check the distinct messages. Try a nonexistent config
  path and confirm a concise error and PowerShell `$LASTEXITCODE` of 2.

Record the observed result and platform after the check. SSH launching, opening
links, editing, search, discovery and remote commands are deferred.

## Verified Task 1 merge and remote CI, 2026-10-09

[PR #1](https://github.com/jkosber/ssh-workbench/pull/1) is merged into `main` at
`84d392f0e4fa00eaf129ecae715dff4262e4f97e` (2026-10-09 20:14:40 UTC).
Its final head was `c08259a7b88401bc46bdfa0c42793af4e1ab3863`; that commit is a
parent of the merge, and the fetched main tree matches the final Task 1 tree.
The repository was verified as owned by `jkosber` and private. This session
verified the existing merge; it did not merge a second time.

Both [push CI 37984283908](https://github.com/jkosber/ssh-workbench/actions/runs/37984283908)
and [PR CI 37984288701](https://github.com/jkosber/ssh-workbench/actions/runs/37984288701)
are completed successfully for head `c08259a`. Each has successful named
`Checks (windows-latest)` and `Checks (ubuntu-latest)` jobs. These final-head
results supersede the earlier pre-merge note's pending-CI statement and are
separate from the historical scaffold CI and Task 2's local checks above.

## Task 1: local project metadata, 2026-10-09

Initial local checks for `feat/project-config`, committed as `c6ea622`, with
Python 3.14.7 on Windows. Version remains 0.0.1. These tables describe that
snapshot; the pre-merge follow-up below records the later corrections.

| Acceptance criterion | Observed evidence |
| --- | --- |
| Explicit `Path`, UTF-8, ordered typed records; independent of Textual/processes | Single/multiple-project, Unicode and direct string-parser tests passed; source review confirms only explicit file reading and standard-library parsing/validation |
| Integer schema version 1, required project array, explicit empty array | Valid/empty cases passed; missing structure, wrong shapes, unsupported versions, booleans and float versions rejected |
| Unique IDs, nonempty names and restricted SSH aliases | Missing/type/empty-field, duplicate-ID and invalid-ID tests passed; parameterized safe/hostile alias cases passed |
| Optional HTTP/HTTPS references without credentials; unknown fields rejected | Both optional fields tested absent and present; type/empty, scheme, credentials, whitespace/control, backslash and host/port failures passed; no resource existence check |
| Concise domain errors for reading, parsing and validation | Missing file, directory, simulated permission/general I/O, invalid UTF-8 and malformed TOML tests passed; messages identify positions/fields without private values or raw underlying errors |
| Supported example/schema documented; private files never created/overwritten | Example copied into a temporary test file and loaded successfully; missing-file and unchanged-input assertions passed; README/architecture document the API and policies |

| Local check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed; 17 packages resolved/checked with no dependency changes |
| `uv run --locked pytest tests/test_config.py -q --basetemp <fresh-directory>` | 170 passed |
| `uv run --locked pytest --basetemp <fresh-directory>` | 176 passed, including all 6 existing CLI/headless UI tests |
| `uv run --locked ruff check .` | Passed after fixing two new overlong lines |
| `uv run --locked ruff format --check .` | Passed |
| `uv run --locked ssh-workbench --help` | Passed; existing options retained, no configuration option added |
| `uv run --locked ssh-workbench --version` | Passed: `ssh-workbench 0.0.1` |
| `uv run --locked python -m ssh_workbench --version` | Passed with the same version |
| README loader command | Passed; fictional example returned one `Project` with both references |
| `uv build` | Passed; source archive and wheel built at 0.0.1 |
| `uv run --locked python scripts/check_package.py` | Passed; isolated installed wheel ran help/version and loaded a temporary fictional project outside the checkout |
| `git diff --check` | Passed |
| Documentation links and package contents | 21 relative links/anchors resolved; the built loader matched its source; wheel/source archive excluded `.local/`, `.serena/`, `.venv/` and Git metadata |

Final review reran the checks in a disposable export of the staged files, with
a fresh environment and no excluded workspace files. An initial pytest run
encountered a Windows permission error while cleaning its shared temporary
directory link after the test cases ran. Rerunning with fresh explicit
`--basetemp` directories passed as recorded above. No tests, permissions or
security settings were changed to address that environment-specific failure.

Initial independent source/documentation review found one URL-policy mismatch: C1
control characters were accepted despite the documented rule. The filter now
rejects them, with U+0081/U+009F regression cases for both optional references;
the test counts above include that correction. No other concrete review findings
were reported. Final diff review found no unrelated code edits or private data
introduced by this task; existing validation notes and the untracked tool
directory were preserved.

Tests use fictional data and temporary files; no real SSH files, hosts, remote
paths or vault data are read. Configuration strings remain inert. The installed
package check removes its temporary environment and fixture when finished.

CLI/UI startup code is unchanged. Jadon's manual confirmation below covers the
scaffold's appearance and exit shortcuts; the loader is verified separately by
the automated checks. Headless tests are not visual checks.

### Pre-merge follow-up: 2026-10-09

Review of `c6ea622` against merge base `6639e5c` found one low-impact error-contract
defect: a path containing a NUL character raised a raw `ValueError`. The loader
now wraps that failure in a sanitized `ProjectConfigError`. Regression coverage
checks the real invalid path and a portable simulated failure, frozen records,
unchanged invalid input, and suppression of invalid URLs in formatted tracebacks.
Alias/URL validation and the installed-wheel loader check needed no code changes.

Fresh local checks on Windows with Python 3.14.7 passed after these corrections:

| Check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed with no dependency changes |
| Ruff lint and formatting checks | Passed |
| Full pytest suite with a fresh unique `--basetemp` | 180 passed: 174 loader tests and 6 CLI/headless UI tests |
| CLI help, CLI version and module version | Passed; version remains 0.0.1 |
| `uv build` and `scripts/check_package.py` | Passed; installed wheel loaded the fictional configuration outside the checkout |

The earlier shared-temp cleanup error did not recur with a fresh `--basetemp`.
This does not establish the original cause; no permissions or tests were weakened.
A fresh tool-based interactive launch again failed with Windows "Access is
denied" before the application started. It supplies no new visual evidence and
does not invalidate Jadon's manual scaffold check.

For the original reviewed commit `c6ea622`, both Windows and Ubuntu passed in
[feature CI run 37977814920](https://github.com/jkosber/ssh-workbench/actions/runs/37977814920)
and [PR CI run 37977893973](https://github.com/jkosber/ssh-workbench/actions/runs/37977893973).
The PR run checked merge commit `47ede5b`, whose parents were the reviewed base
and head and whose tree matched the head. Job logs confirmed dependency sync,
lint, formatting, 176 tests, build and installed-package validation. These remote
results apply to that snapshot; the follow-up requires its own CI after pushing.

At this point the shared Serena project settings were committed for development;
they were removed on 2026-10-20. No private configuration is needed by the
application or tests.

## Bootstrap, 2026-10-09

The records below describe the initial 0.0.1 scaffold, before any product feature.

### Bootstrap environment

Local commands execute on a Windows 11 Home Insider Preview x64 workstation
(OS build 10.0.26340), using PowerShell 7.6.6. No remote machine is involved.
Project Python: 3.14.7. Declared minimum: >=3.14. Tools observed: Git
2.55.0.windows.5, GitHub CLI 2.98.0 and uv 0.12.24.

Resolved direct dependencies: Textual 8.2.8; development tools pytest 9.1.1,
pytest-asyncio 1.4.0 and Ruff 0.16.10. `uv.lock` records exact transitive versions.
The uv build backend requirement was generated by uv: >=0.12.24,<0.13.0.

### Bootstrap automated checks

| Check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed; project environment matches the lockfile |
| CLI `--help`, `--version` | Passed; help exits successfully and version is `ssh-workbench 0.0.1` |
| `python -m ssh_workbench --version` through uv | Passed with the same installed version |
| `uv run --locked ruff check .` | Passed |
| `uv run --locked ruff format --check .` | Passed after formatting |
| `uv run --locked pytest` | 6 passed: help, metadata version, rejected unknown option, startup, Q exit and Ctrl+Q exit |
| `uv build` | Passed; source archive and wheel created; wheel built from the source archive |
| `uv run --locked python scripts/check_package.py` | Passed; wheel installed with locked runtime dependencies in a temporary environment; help/version worked outside the checkout |

An initial lint/format issue was corrected. A trial `uv build --locked` failed
because this uv version does not support that option for builds. All build
instructions and CI now use the verified `uv build` command. Dependency sync
and export remain locked. These results establish scaffold behavior, not product
feature completion.

Before the initial commit, all 24 staged files were reviewed. A targeted scan
found no credential tokens, private absolute paths or actual host/account details;
24 relative Markdown links resolved and the illustrative TOML parsed. The wheel
and source archive contained no `.local/`, `.venv/` or Git metadata. Git whitespace
checks passed. An independent source/documentation review found no blocking
issues. These checks reduce accidental disclosure risk but do not replace review
of future changes.

### Bootstrap manual verification and limits

On 2026-10-09, Jadon confirmed that the application's appearance, Q exit and
Ctrl+Q exit work in manual testing. This is user-confirmed verification of the
scaffold's appearance and exit shortcuts. Automated startup and keyboard exit
were also verified with Textual's headless pilot.

The earlier tool-based interactive launch was blocked when Windows returned
"Access is denied" while creating the terminal process. That tool-launch failure
was not an observed application exception; the manual check is now complete.

At bootstrap no real SSH feature existed, and no SSH configuration, keys, known_hosts,
infrastructure or vault data is used by tests. macOS and other Python versions
have not been tested.

CI is configured for `ubuntu-latest` and `windows-latest`, both using the version
in `.python-version`. After the initial push,
[CI run 37966249655](https://github.com/jkosber/ssh-workbench/actions/runs/37966249655)
passed on both targets for commit `6639e5c`, including dependency installation,
Ruff, tests, build and isolated package checks. This result applies to that commit;
check the repository's Actions tab for later changes. Action references were
verified through their official GitHub
release/tag APIs: actions/checkout v7.0.1 and astral-sh/setup-uv v10.2.0; full
commit references are recorded in the workflow. Permissions are `contents: read`.

### Bootstrap's planned manual SSH checklist

Superseded by the [Task 5 checklist](#task-5-user-executed-manual-session) and
its recorded real SSH and browser checks. Kept as the original plan. These checks
were **not performed** during bootstrap.

- Select a fictional/local fixture, then an approved real project; verify the
  shown alias and context match the intended target before connecting.
- Check existing native SSH authentication and normal host-key verification;
  never bypass an unexpected host-key warning.
- Connect and disconnect, cancel authentication, and interrupt a connection;
  verify terminal input, display and project selection recover correctly.
- Check unavailable SSH, an unknown alias and an unreachable approved target;
  confirm useful errors without credentials or sensitive output in logs.
- Exercise small terminal sizes and keyboard navigation. Open only an explicitly
  selected, approved documentation URL. Review screenshots/logs for private data.
- Have Jadon review usability and explain the tested behavior before treating it
  as personal learning or public portfolio evidence.
