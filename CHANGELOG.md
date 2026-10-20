# Changelog

## Unreleased

The internal package version is 0.0.1. This scaffold has not been published as a
release; 0.1.0 is the first usable release target.

### Fixed

- On Windows, C no longer runs an `ssh.exe` found in the folder Workbench was
  started from or through a relative `PATH` entry; only absolute `PATH` entries
  supply the SSH client.
- Configuration files saved as UTF-8 with a byte-order mark (Windows PowerShell
  5.1 `-Encoding UTF8`) now load instead of failing at line 1, column 1.
- The development link fixture keeps all external-action stubs installed until
  process exit, preventing a delayed daemon from reaching restored real openers
  after the TUI returns or raises.
- Nonzero SSH exits and interrupted handoffs now include retry guidance while
  retaining the exact status and existing terminal/signal safeguards.
- Invalid configuration paths, including embedded NUL characters, now report a
  sanitized `ProjectConfigError` consistently with other file-read failures.

### Added

- Task 5 manual validation checklist, placeholder configuration and locked
  installed-wheel session instructions. Recorded user-reported Windows Terminal
  SSH return and authorized agent Windows Terminal checks covering real browser
  links, three SSH targets including a timeout, resizing, footer clicks and both
  quit keys. The release scope and license decision remain pending.
- Explicit R / Repository and D / Documentation actions from either pane, with
  shared URL revalidation and sanitized missing/invalid/unavailable/failure
  results. Windows URL associations and Linux desktop GIO receive unchanged URLs.
- One pending browser request with responsive navigation and quit, captured
  project attribution, no automatic retry and shutdown-safe completion messages.
- Browser-boundary, concurrency and installed-wheel exit tests, plus a guarded
  native link fixture that never opens a real browser.
- Explicit C / Connect action for the selected alias, launching the resolved
  native SSH client without a shell, flags or remote commands. SSH owns terminal
  I/O, authentication and host-key checks.
- Return to the selected project and list focus with exit status or a sanitized
  launch error, including unavailable SSH and interruption. Repeated launches,
  signal restoration and Textual suspension paths have automated coverage and a
  harmless interactive local-child fixture.
- Explicit `--config PATH` loading into a read-only project browser, with ordered
  keyboard selection, five-field details, visible focus and scrollable long text.
- Separate no-configuration and empty-project screens; configuration errors exit
  before terminal startup. Help/version remain independent of configuration.
- Literal metadata rendering with visible escapes for nonprinting characters,
  headless interaction tests at several sizes, and installed-wheel browser checks.
- A standalone UTF-8 TOML loader for schema version 1, returning ordered typed
  project records with validated IDs, SSH aliases and optional HTTP/HTTPS links.
- Concise configuration errors and tests for file failures, malformed input,
  unknown fields, duplicate IDs and unsafe aliases/URLs.
- A Textual development screen with keyboard exit, CLI help and a version read
  from installed package metadata.
- A uv-managed Python package, locked dependencies, CLI and headless UI tests,
  Ruff checks, and isolated wheel installation verification.
- Linux/Windows CI, development instructions, security boundaries and a small
  ordered roadmap with a fictional configuration example.
