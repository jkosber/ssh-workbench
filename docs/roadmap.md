# Roadmap

This is the single development backlog. Obsidian may link to a task and record
personal context, but does not maintain another set of acceptance criteria.

## Bootstrap milestone

The bootstrap establishes the unreleased 0.0.1 scaffold: packaging, startup,
help/version, keyboard exit, tests, CI configuration and development documentation.
It does not complete any product feature below. See [validation](validation.md)
for evidence and remaining verification limits.

## 1. Load and validate local project metadata

**Merged in PR #1** at `84d392f`; final Task 1 head `c08259a`. The standalone
loader and its tests are complete. No SSH, discovery, network requests, URL opening or project-selection
UI was added. See the [schema](../README.md#schema), [Python API](architecture.md#python-api) and
[task 1 evidence](validation.md#task-1-local-project-metadata-2026-10-09).

Acceptance criteria:

- [x] A loader accepts an explicit `pathlib.Path`, reads UTF-8 TOML and returns typed
  project records in file order. It has no dependency on Textual or subprocesses.
  It does not search the filesystem or inspect SSH configuration.
- [x] Support `schema_version = 1` and a `projects` array. Accept an empty array as
  zero projects. Treat a missing array, an unsupported schema version or a
  boolean masquerading as an integer version as an error.
- [x] Each project requires a unique `id`, a nonempty `name` and `ssh_alias`.
  IDs use lowercase letters/digits separated by single hyphens. Aliases start
  with an ASCII letter/digit and contain only ASCII letters/digits, dots,
  underscores or hyphens. Reject leading dashes, whitespace, `user@host`, shell
  punctuation and values that encode commands or options.
- [x] `repository` and `documentation` are optional HTTP/HTTPS URLs without embedded
  credentials. Require correct types and nonempty values when supplied. Reject
  unsupported schemes and unknown fields so mistakes are visible. Keep the
  schema small; local repository paths and arbitrary SSH arguments are deferred.
- [x] Missing/unreadable files, malformed TOML and invalid fields produce a concise
  domain error that identifies the field/project when possible without echoing
  the entire file or private values. Choose a small typed record and one clear
  error type; no schema framework is needed.
- [x] Confirm or revise the supported example (`examples/projects.example.toml`,
  replaced in Task 8 by [machines.example.toml](../examples/machines.example.toml))
  and document the implemented schema. Private files belong outside Git; the
  loader never creates or overwrites them.

Implemented tests use `tmp_path` and fictional data (the string parser also has
a direct test without a file):

- Valid single/multiple projects preserve ordering; optional fields can be absent.
- Empty `projects = []` succeeds; missing files and unreadable-file errors are
  handled (simulate permission errors portably).
- Malformed TOML, missing/unknown fields, wrong types, duplicate IDs, empty
  required strings and unsupported schema versions fail usefully.
- Parameterized hostile aliases and URLs are rejected, including a leading SSH
  option, whitespace, shell punctuation, embedded credentials and `file:` URLs.
- No test needs a real host, SSH files, the vault or network access.

## 2. Select projects and inspect details

**Merged in [PR #2](https://github.com/jkosber/ssh-workbench/pull/2)** as `4852e1c`.
The [final local checks](validation.md#task-2-final-local-verification-2026-10-12)
and [initial Task 2 validation](validation.md#task-2-project-browser-2026-10-09)
record the local evidence. [Task 2 remote CI](validation.md#task-2-pr-documentation-and-remote-ci-2026-10-12)
also passed on Windows and Ubuntu.

The [2026-10-12 console follow-up](validation.md#task-2-interactive-console-follow-up-2026-10-12)
also verifies real 80x24 terminal input, scrolling, errors and return to a working
PowerShell prompt.

The [browser visual follow-up](validation.md#task-2-browser-visual-follow-up-2026-10-12)
verifies screenshots and live browser resizing through 80x24, 60x20 and 120x40,
including selection, pane focus, wrapping and scrolling.

The [native terminal follow-up](validation.md#task-2-native-terminal-follow-up-2026-10-12)
verifies real WezTerm window resizing, navigation, scrolling and both quit keys.
The later [desktop screenshot follow-up](validation.md#task-2-desktop-screenshot-follow-up-2026-10-12)
adds native Windows Terminal startup and WezTerm appearance evidence. Reinspection
and independent review corrected an earlier mistaken report of missing project
names; the captures show both names. Human review remains separate from these
agent-run checks.

Acceptance criteria:

- [x] `--config PATH` reads only the requested file through the existing loader;
  no discovery, default file, schema changes or configuration writes. Help/version
  exit before configuration reading. Invalid/unreadable files report sanitized
  errors with status 2 before starting the terminal interface.
- [x] No configuration and an explicit empty project collection have distinct
  informative screens. Neither silently loads example data.
- [x] Projects appear in loader order. The first project starts selected and
  focused; Up/Down changes selection. The row highlight and pane border make
  selection and focus visible. Tab/Shift+Tab switch panes.
- [x] Details update to the selected ID, name, alias and both optional references;
  absent references show `Not provided`. Details wrap and scroll; selecting a
  different project resets scrolling to the top.
- [x] Configuration values render literally without markup, actions or generated
  hyperlinks. Nonprinting characters are visibly escaped only for display;
  underlying records remain unchanged. Unicode and long values are covered.
- [x] The list/details layout is exercised headlessly at 80x24, 120x40 and 60x20,
  with resizing, long text, a scrolling list and Q/Ctrl+Q exit. No nonworking
  connect/open-link controls are shown.
- [x] Focused CLI/headless tests and isolated installed-wheel checks use fictional
  temporary data; application tests guard common connection/process/browser
  boundaries. Existing loader coverage is retained.
- [x] At the user's request, the agent exercises the
  [Windows terminal checklist](validation.md#task-2-windows-terminal-checklist),
  including real console flows, native screenshots and WezTerm window resizing.
  Windows Terminal live resizing, other DPI settings and screen readers remain
  outside the verified evidence. Jadon reviews the PR before authorizing merge.

SSH launching, link opening, editing, search/filtering, discovery, tmux and file
transfer remain outside Task 2. Task 3 adds the SSH action below.

## 3. Launch native SSH and return cleanly

**Merged in [PR #3](https://github.com/jkosber/ssh-workbench/pull/3)** as `eeb6e39`. Based on
merged PR #2 at `4852e1c`. Version remains 0.0.1 with unchanged dependencies.
See [Task 3 evidence](validation.md#task-3-native-ssh-2026-10-12) for automated
checks and the real Windows terminal fixture results; no real host was contacted.
Jadon also confirmed navigation works in Microsoft Windows Terminal on
2026-10-12. That manual report covers navigation only.
[Task 3 remote CI](validation.md#task-3-pr-and-remote-ci-2026-10-12) passed on
Windows and Ubuntu for the implementation and documentation commits.

Acceptance criteria:

- [x] One explicit Connect action has a visible C binding, works from either
  pane, requires a selection and prevents overlapping launches. Startup,
  navigation and Enter never connect automatically.
- [x] Revalidate at the process boundary with the loader's existing alias rule.
  Resolve `ssh.exe` on Windows or `ssh` elsewhere; pass the absolute executable
  and selected alias as an argument list with `shell=False`. Accept no arbitrary
  flags or remote commands.
- [x] Suspend the TUI while native SSH owns the terminal and inherited standard
  input/output. Leave authentication, SSH configuration and host-key checks to
  that client; capture no credentials or SSH output and weaken no verification.
- [x] Preserve normal native Ctrl+C behavior, including when the child continues
  afterward. Guard parent SIGINT throughout lookup and terminal handoff; restore
  the prior handler after the browser reclaims the terminal.
- [x] Restore the selected project, usable keyboard input and predictable list
  focus after success, nonzero exit, process-start error or interruption; show
  the exit status or launch result. Verify exceptional resumption against the
  installed Textual suspension code, not only a replacement context manager.
- [x] Missing SSH and unsupported terminal handoff show useful messages and
  leave the browser usable. Keep error handling scoped to this launch path.
- [x] Preserve Task 1/2 loading, literal display, selection, scrolling, empty/error
  states and Q/Ctrl+Q. Keep process logic separate from rendering.
- [x] Automated tests and installed-wheel checks substitute process boundaries
  and use fictional fixtures. Cover exact argv, rejected aliases, no selection,
  exits, errors, interruption, repeat launches and restoration; retain guards
  against unrequested process, network and browser actions.
- [x] Exercise a harmless local child in a real Windows terminal. Confirm
  inherited input/output, Ctrl+C, restoration, retry, selection and focus, then
  clean up only owned test windows/processes. Record platform/terminal limits.
- [x] Run required checks, build and isolated package validation; update usage,
  architecture, Unreleased notes, observed validation and existing Obsidian records.

Link opening belongs to Task 4 below. Editing, search, discovery, tmux, file
transfer, embedded terminals, global settings and infrastructure changes remain
deferred. Completion does not
authorize a commit, push, PR, merge, tag or release.

## 4. Handle failures and useful documentation links

**Merged in [PR #4](https://github.com/jkosber/ssh-workbench/pull/4)** as
`9b28e86c0d6c980c6058297f60e6ff623e657031`, containing reviewed feature head
`0fe97d169a59094dbfdce179480d6889efb4dcdb`. The merge tree matches that head.
Based on Task 3 merge `eeb6e39bf93a8ba1532503a7a2e0e565f9a9d8f2`.
Version 0.0.1 and dependencies are unchanged.
See [Task 4 evidence](validation.md#task-4-errors-and-links-2026-10-12) for new
local results, native fixture limits and real-world behavior still untested.
The [Task 5 preparation record](validation.md#task-5-preparation-and-safe-local-verification-2026-10-12)
verifies the merge and its own Windows/Ubuntu CI separately from PR checks.

Acceptance: missing configuration, missing SSH, failed connections and cancelled
actions have actionable messages. Open validated HTTP/HTTPS links only on an
explicit action; handle absent links and browser-launch failures. Test these
paths without opening a real browser or executing unsafe commands.

- [x] Retain explicit configuration loading, sanitized failures exiting 2 and
  configuration-independent help/version. No-config and empty states explain
  how to supply projects. Existing missing SSH and launch-error guidance remains.
- [x] Give neutral retry guidance after nonzero SSH exits and interrupted
  handoffs. Preserve exact return codes and all Task 3 suspension/SIGINT, native
  authentication, host-key, selection, focus and quit safeguards; parse no output.
- [x] Expose R / Repository and D / Documentation with visible footer bindings
  from either pane. No selection and absent URLs produce clear feedback.
  Startup, navigation, selection, rendering, focus and Enter never open links.
- [x] Capture the selected project, link kind and exact URL at invocation.
  Keep configuration text literal, with no generated inline hyperlinks. Delayed
  results identify the original project and leave current interaction state alone.
- [x] Share the loader's existing HTTP/HTTPS validation at a separate browser
  boundary. Preserve schema, errors and accepted values; reject invalid schemes,
  credentials and prohibited controls. Pass URLs as data without shell commands,
  metadata-supplied executable/flags, fetching, probing or normalization.
- [x] Report invalid, missing, unavailable, reported failure, expected exception
  and accepted results safely. Acceptance never claims page loading. Document
  Windows/GIO support, unsupported environments and opening where Workbench runs.
- [x] Keep potentially blocking dispatch off the UI thread, with one pending
  request, no queue/retry and no text-browser fallback. Preserve navigation and
  Q/Ctrl+Q; ignore stale/closed-app completions and state actual cancellation limits.
- [x] Guard external actions in fictional unit/UI/native fixtures. Cover exact
  URLs, both panes, all outcomes, literal messages, repeats, slow requests, changed
  selection, shutdown, scrolling, focus, quit and coexistence with native SSH.
- [x] Exercise keyboard behavior and layout at 60x20, 80x24 and 120x40, using
  bounded readiness checks. Headless checks and native WezTerm text/dimensions
  passed; attempted desktop screenshots were obscured and do not verify pixels.
- [x] Run required checks, full suite, build and isolated installed-package checks;
  update relevant usage, architecture, Unreleased notes, evidence and project records.

Real browser/website checks, real SSH and the remaining platform/visual usability
checks require separately authorized Task 5 work. Configuration editing, search,
discovery, tmux, transfers, embedded terminals, global settings, infrastructure
and release work remain outside Task 4.

## 5. Validate usability and review 0.1.0 readiness

**Merged in [PR #5](https://github.com/jkosber/ssh-workbench/pull/5)** as
`ac4f6e8`, based on Task 4 merge `9b28e86`. The
[Task 5 status table](validation.md#task-5-preparation-and-safe-local-verification-2026-10-12)
links each record. The 0.1.0 review on 2026-10-20 closed the last box below.

Acceptance:

- [x] Obtain approval for named real-world test targets and actions. Jadon chose
  three SSH aliases and the repository/README URLs; alias names stay in the
  ignored configuration.
- [x] Record observed behavior with [the manual checklist](validation.md#task-5-user-executed-manual-session).
  Jadon reported the first SSH handoff in Windows Terminal. The
  [agent Windows Terminal check](validation.md#task-5-authorized-windows-terminal-check-2026-10-20)
  completed steps A-D: R/D opened the chosen pages in Chrome, SSH returned with
  status 0, and resizing through 60x20, 120x40 and 80x24 and both quit keys kept
  the shell usable. [Footer clicks](validation.md#task-5-footer-click-check-2026-10-20)
  and [two more SSH targets](validation.md#task-5-additional-ssh-targets-and-review-fixes-2026-10-20),
  including a real timeout with status 255, also passed.
- [x] Fix material usability issues. The manual checks found none. A whole-project
  review found two defects, fixed after failing tests: an `ssh.exe` in the launch
  folder could run on Windows, and UTF-8 configurations with a byte-order mark
  failed to load.
- [x] Update documentation: accuracy pass on 2026-10-20.
- [x] Review privacy: no private data in history, PRs or the built package.
- [x] Review release scope and decide the license. On 2026-10-20 Jadon chose a
  private `v0.1.0` tag, the MIT license and the Task 6 scope below.

A passing test or completed task does not authorize a release. Follow
[the manual release checklist](../CONTRIBUTING.md) only when requested.

## 6. Prepare the 0.1.0 release

**Merged in [PR #6](https://github.com/jkosber/ssh-workbench/pull/6)** as
`54f6a3e`, based on Task 5 merge `ac4f6e8`, and tagged as the annotated, private
`v0.1.0` on 2026-10-20. See the
[Task 6 evidence](validation.md#task-6-010-readiness-2026-10-20).
The 0.1.0 review found the features sufficient but daily use and user
documentation lacking. This task closes those gaps and tags 0.1.0 privately.

Acceptance:

- [x] Without `--config`, read a per-user default file if it exists:
  `%APPDATA%\ssh-workbench\projects.toml` on Windows, otherwise
  `$XDG_CONFIG_HOME/ssh-workbench/projects.toml` when that variable is absolute,
  else `~/.config/ssh-workbench/projects.toml`. `--config` always wins and the
  default is then not checked. Never create or write the file or its folder.
  Default-file errors exit 2 before the TUI, prefixed `default configuration file:`,
  without paths or values. Existing `--config` errors are unchanged.
- [x] Show the resolved default path in `--help` and on the no-config screen,
  escaped for display. Drop the hint to the checkout-only example file.
- [x] Cap Textual below 9: the suspension handling was verified only on 8.2.8.
- [x] Rewrite the README for users: install as a uv tool, quick start, alias
  rules, keys, platform support and troubleshooting. Move internals and the
  Python API to the architecture document, which gains a module map.
- [x] Add the MIT license, set version 0.1.0, write a dated user-facing
  changelog entry and remove "unreleased" and "scaffold" status wording.
- [x] Run the full checks, then smoke-test the installed tool in Windows
  Terminal with one approved SSH target loaded from the default file.
- [x] With Jadon's approval for each step: PR, merge, annotated `v0.1.0` tag on
  the merge commit and the updated GitHub description. No GitHub Release.

## 0.2.0 milestone

Planned and approved on 2026-10-20. Machines replace projects: each machine
connects through an existing SSH alias or directly by address, and can be added,
edited and deleted inside Workbench. Live status, key login setup, named web
links, renamed-alias detection and optional exported SSH aliases follow. Each
task is one pull request; its acceptance criteria are added when it starts.

| Task | Delivers |
| --- | --- |
| 7. Tooling cleanup | `uv_build` range and CI uv pin updated together, one shared guard list, the package check's Python moved out of strings |
| 8. Machines replace projects | Read-only machine file (schema 2, schema 1 still loads), alias and direct connections, per-machine keys, named links |
| 9. Add, edit and delete machines | Forms with shared validation; saving with a backup, atomic replace and an outside-change check |
| 10. Live status | Background port checks on a timer, an indicator readable without color, Connect using the first online address |
| 11. Alias rename detection | A small state file and a one-key rename suggestion |
| 12. Key login setup | Pick or create a per-machine key, install it on POSIX and Windows targets, confirm key-only login |
| 13. Exported aliases | Workbench's own SSH config file and one confirmed `Include` line |
| 14. 0.2.0 release | Supervised release work after Tasks 7-13 merge |

## 7. Tooling cleanup

**Merged in [PR #8](https://github.com/jkosber/ssh-workbench/pull/8)** as
`11449aa`, containing tested head `d6f3a61`; the merge tree matches that head.
See the [Task 7 evidence](validation.md#task-7-tooling-cleanup-2026-10-20).

Three development items from the 0.1.x candidates. No user-visible behavior
changes.

Acceptance:

- [x] Raise the build backend to `uv_build>=0.13.3,<0.14.0` and the uv version
  pinned in CI to `0.13.3` in the same change. A test fails when the CI pin and
  the range's lower bound differ, or the upper bound is not the next minor
  release. `uv build` no longer warns about the `uv_build` upper bound.
- [x] One shared list names the process, network and browser entry points that
  tests and fixtures must never reach. `tests/conftest.py`,
  `tests/link_fixture_process.py`, `scripts/check_links.py` and the package check
  use it instead of their own copies. A test checks that the in-process guard
  rejects every listed entry point.
- [x] `scripts/check_package.py` holds no Python source in strings. The
  installed-wheel checks live in their own file, still run with `python -I`
  against the installed wheel, and keep the isolation and import-path
  assertions. A test fails if Python source returns to strings there.
- [x] Full checks, build, package check and CI on Windows and Ubuntu pass.
  CONTRIBUTING and the architecture module map describe the new files.

## 8. Machines replace projects

Read-only: Workbench still writes nothing. Saving, status checks and SSH config
reading come in Tasks 9-11.

Acceptance:

- [x] Schema 2 machine file with a `machines` array. Each machine has a unique
  `id` and a `name`, plus either `alias` or `addresses` (with optional `user`,
  `port` and `key`), never both, and optional named `links`. Unknown fields stay
  errors, and errors never repeat values, unknown keys or paths.
- [x] Field rules shared by the loader and the launch boundary. `user` and each
  address reject anything that could become an SSH option or several arguments
  (a leading `-`, whitespace, control characters, `@` in `user`). Addresses
  accept hostnames, IPv4 and IPv6. Ports are 1-65535. A `key` is an absolute or
  `~/` path to a private key, without quotes, `%`, `${` or a `.pub` ending.
  Link names are unique within a machine; URLs keep the 0.1.0 rule.
- [x] Schema 1 files still load: each project becomes an alias machine whose
  `repository` and `documentation` become links named "Repository" and
  "Documentation". Their errors keep `projects[N]` locations.
- [x] The default file is `machines.toml` in the 0.1.0 folders, with no
  fallback to `projects.toml`. `--config PATH` still overrides it.
- [x] Connect runs `ssh -- <alias>` for alias machines. Direct machines run
  `ssh -o HostKeyAlias=<id> [-l user] [-p port] [-i key -o IdentitiesOnly=yes]
  -- <address>` with the first listed address. Values are revalidated just
  before launch; every 0.1.0 handoff safeguard stays. Real OpenSSH on Windows
  and a portable build accept the arguments.
- [x] O opens the selected machine's only link, or a picker when there are
  several: Enter opens, Escape cancels, and C, O and a second request are blocked
  while it is open. R and D are gone. The 0.1.0 browser boundary is unchanged.
- [x] The details pane shows the connection kind, alias or addresses, user, port,
  key and links, all literal. C and O are dimmed without a selection, while
  connecting and (O) without links. Status lines name the machine.
- [x] Folded 0.1.x fixes: a folder given with `--config` or at the default path
  reports "expected a file, got a directory"; the empty-file screen no longer
  says to restart with `--config PATH`; `--help` prints the default path on its
  own line; a test shows `--help` and `--version` ignore an invalid default
  file; the help line fits 60 columns; README escaping and Git-tag upgrade
  wording.
- [ ] Tests, fixtures, the package check and the example file use machines.
  Full checks and CI pass; a native Windows Terminal check with fictional
  machines and a real alias connect to an approved target pass.

## 0.1.x candidates

Findings from the 0.1.0 review, deferred as non-blocking. Each needs its own
explicit task. Task 7 took the `uv_build`, guard-list and `check_package.py`
items; Task 8 took the R/D, help line, status line, folder, empty-file,
`--help` path, help/version test and README items. Two remain:

- Split current test procedures from `validation.md` into a short testing guide
  and keep the dated log.
- URLs containing U+202E or U+200B pass validation; display already escapes them.

## 0.2.x candidates

Minor review findings from the 0.2.0 tasks, deferred as non-blocking.

- Task 7: `test_no_external_actions_rejects_every_shared_boundary` passes even
  without a direct `subprocess.run` guard, because the guarded `Popen` fails
  first; assert that every guarded attribute is the fixture's own function.
- Task 7: no test proves that `check_links.install_fixture_guards` and
  `package_smoke.reject_external_actions` install the shared guards.
- Task 7: the strings test in `tests/test_tooling.py` misses inline children
  such as `["python", "-I", "-c", "..."]`; also reject a `"-c"` string.
- Task 7: `package_smoke.guarded_boundaries()` inserts `scripts/` at the front
  of `sys.path`; load the list by path or append it instead.
- Task 8: the `%(prog)` branch of the `--help` epilog has no test.
- Task 8: a few schema tests match message prefixes instead of exact strings.
- Task 8: the 60x20 many-links picker test does not press Escape; the 80x24
  test covers Escape restoring selection and focus.
- Task 8: an empty schema 1 file is told to add `[[machines]]` entries, which
  that schema would reject; the hint should name `schema_version = 2`.
- Task 8: at 80x24 the details pane needs scrolling to show a machine's key and
  links; alias machines spend three rows on "From your SSH config".

## Deferred ideas

tmux integration, automatic discovery, file transfer, cloud sync, embedded
terminals, AI features, Proxmox controls and a plugin framework are outside the
initial usable-release scope. Reconsider them only through a new explicit task.
