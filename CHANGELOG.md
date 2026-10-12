# Changelog

## Unreleased

The internal package version is 0.0.1. This scaffold has not been published as a
release; 0.1.0 is the first usable release target.

### Fixed

- Invalid configuration paths, including embedded NUL characters, now report a
  sanitized `ProjectConfigError` consistently with other file-read failures.

### Added

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
- Shared optional Serena project settings; local overrides, caches and memories
  remain ignored and are not required by the application.
