# Validation

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
head and its merge status. Task 3 remains unimplemented, and the terminal/DPI/
screen-reader limits recorded below still apply.

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

The shared Serena project settings are included for development. Cache files,
local overrides and memories remain ignored. No private configuration is needed
by the application or tests.

## Bootstrap environment: 2026-10-09

Local commands execute on a Windows 11 Home Insider Preview x64 workstation
(OS build 10.0.26340), using PowerShell 7.6.6. No remote machine is involved.
Project Python: 3.14.7. Declared minimum: >=3.14. Tools observed: Git
2.55.0.windows.5, GitHub CLI 2.98.0 and uv 0.12.24.

Resolved direct dependencies: Textual 8.2.8; development tools pytest 9.1.1,
pytest-asyncio 1.4.0 and Ruff 0.16.10. `uv.lock` records exact transitive versions.
The uv build backend requirement was generated by uv: >=0.12.24,<0.13.0.

## Automated checks

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

## Manual verification and limits

On 2026-10-09, Jadon confirmed that the application's appearance, Q exit and
Ctrl+Q exit work in manual testing. This is user-confirmed verification of the
scaffold's appearance and exit shortcuts. Automated startup and keyboard exit
were also verified with Textual's headless pilot.

The earlier tool-based interactive launch was blocked when Windows returned
"Access is denied" while creating the terminal process. That tool-launch failure
was not an observed application exception; the manual check is now complete.

No real SSH feature exists, and no SSH configuration, keys, known_hosts,
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

## Future approved manual SSH checklist

These checks are **not performed** during bootstrap. Obtain approval for the
specific hosts and connection actions first, and record date, platform and result.

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
