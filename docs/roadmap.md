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
UI was added. See [schema and usage](../README.md#load-project-metadata) and
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
- [x] Confirm or revise the [supported example](../examples/projects.example.toml)
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

**Implemented and verified in [PR #2](https://github.com/jkosber/ssh-workbench/pull/2).**
The [final local checks](validation.md#task-2-final-local-verification-2026-10-12)
and [initial Task 2 validation](validation.md#task-2-project-browser-2026-10-09)
record the local evidence. [Task 2 remote CI](validation.md#task-2-pr-documentation-and-remote-ci-2026-10-12)
also passed on Windows and Ubuntu. The PR records the current merge and check status.

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
transfer remain outside Task 2. Do not begin Task 3 without a separate request.

## 3. Launch native SSH and return cleanly

Acceptance: an explicit action launches only the selected validated alias with
an argument list and no shell. Native SSH handles authentication and host-key
checks. Restore the TUI after success, failure or interruption; report exit
status. Tests substitute the process boundary and never connect to infrastructure.

## 4. Handle failures and useful documentation links

Acceptance: missing configuration, missing SSH, failed connections and cancelled
actions have actionable messages. Open validated HTTP/HTTPS links only on an
explicit action; handle absent links and browser-launch failures. Test these
paths without opening a real browser or executing unsafe commands.

## 5. Validate usability and review 0.1.0 readiness

Acceptance: obtain approval for named real-world test targets and actions, then
record observed behavior using [the manual checklist](validation.md). Fix material
usability issues, update documentation and review release scope, privacy and the
license decision. A passing test or completed task does not authorize a release.
Follow [the manual release checklist](../CONTRIBUTING.md) only when requested.

## Deferred ideas

tmux integration, automatic discovery, file transfer, cloud sync, embedded
terminals, AI features, Proxmox controls and a plugin framework are outside the
initial usable-release scope. Reconsider them only through a new explicit task.
