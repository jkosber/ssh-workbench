# Roadmap

This is the single development backlog. Obsidian may link to a task and record
personal context, but does not maintain another set of acceptance criteria.

## Bootstrap milestone

The bootstrap establishes the unreleased 0.0.1 scaffold: packaging, startup,
help/version, keyboard exit, tests, CI configuration and development documentation.
It does not complete any product feature below. See [validation](validation.md)
for evidence and remaining verification limits.

## 1. Load and validate local project metadata

**Recommended next task.** Implement the loader and its tests only; no SSH,
discovery, network requests, URL opening or project-selection UI.

Acceptance criteria:

- A loader accepts an explicit `pathlib.Path`, reads UTF-8 TOML and returns typed
  project records in file order. It has no dependency on Textual or subprocesses.
  It does not search the filesystem or inspect SSH configuration.
- Support `schema_version = 1` and a `projects` array. Accept an empty array as
  zero projects. Treat a missing array, an unsupported schema version or a
  boolean masquerading as an integer version as an error.
- Each project requires a unique `id`, a nonempty `name` and `ssh_alias`.
  IDs use lowercase letters/digits separated by single hyphens. Aliases start
  with an ASCII letter/digit and contain only ASCII letters/digits, dots,
  underscores or hyphens. Reject leading dashes, whitespace, `user@host`, shell
  punctuation and values that encode commands or options.
- `repository` and `documentation` are optional HTTP/HTTPS URLs without embedded
  credentials. Require correct types and nonempty values when supplied. Reject
  unsupported schemes and unknown fields so mistakes are visible. Keep the
  schema small; local repository paths and arbitrary SSH arguments are deferred.
- Missing/unreadable files, malformed TOML and invalid fields produce a concise
  domain error that identifies the field/project when possible without echoing
  the entire file or private values. Choose a small typed record and one clear
  error type; no schema framework is needed.
- Confirm or revise the [illustrative example](../examples/projects.example.toml)
  and document the implemented schema. Private files belong outside Git; the
  loader never creates or overwrites them.

Required tests use `tmp_path` and fictional data:

- Valid single/multiple projects preserve ordering; optional fields can be absent.
- Empty `projects = []` succeeds; missing files and unreadable-file errors are
  handled (simulate permission errors portably).
- Malformed TOML, missing/unknown fields, wrong types, duplicate IDs, empty
  required strings and unsupported schema versions fail usefully.
- Parameterized hostile aliases and URLs are rejected, including a leading SSH
  option, whitespace, shell punctuation, embedded credentials and `file:` URLs.
- No test needs a real host, SSH files, the vault or network access.

Suggested next request: "Implement roadmap task 1 only, including its acceptance
tests and documentation. Do not add the project UI or SSH launching. Do not commit
or push until I instruct you."

## 2. Select projects and inspect details

Acceptance: connect the loader to an explicit configuration option; document any
default path. Display projects in file order with keyboard selection and show the
selected name, alias and optional references. Empty and invalid configurations
have clear states. Test selection, detail changes and exit headlessly. Include
no connect or open-link controls until those actions work.

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
