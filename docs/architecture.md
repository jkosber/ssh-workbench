# Architecture

## Implemented scaffold

The installed `ssh-workbench` entry point calls `ssh_workbench.cli.main`.
Standard-library `argparse` handles help, version and invalid options before
loading the TUI. Version output uses `importlib.metadata.version`; the source
of that metadata is `pyproject.toml`.

`ssh_workbench.app.SSHWorkbenchApp` renders a header, a scaffold notice and a
footer with the quit binding. Textual owns the event loop and terminal lifecycle.
The CLI and TUI do not read project configuration or start SSH processes.

| Decision | Reason |
| --- | --- |
| Python 3.14.7 for development, minimum >=3.14 | A supported stable interpreter already available at bootstrap; one version keeps the initial CI matrix small |
| Textual as the only direct runtime dependency | Terminal layout, keyboard handling and headless tests without a web backend |
| Standard-library argparse and metadata | Help/version need no extra CLI framework or duplicated version constant |
| uv with its build backend and a `src/` layout | One tool for environments, a committed lockfile and installable artifacts; tests exercise an installed package |
| pytest plus pytest-asyncio; Ruff | Small test and quality toolset with the same commands locally and in CI |

The source and wheel are built by `uv build`. The package check installs
the wheel and locked runtime dependencies in a disposable environment outside
the checkout, where it checks the console entry point and loads a fictional TOML
file through the installed module. It does not launch SSH.

## Implemented project metadata loader

`ssh_workbench.config.load_projects(path: Path) -> list[Project]` reads only the
explicit UTF-8 file. `parse_projects(text)` uses standard-library `tomllib` and
passes the resulting data to a separate schema validator. The frozen `Project`
dataclass stores the five documented fields; the list preserves file order.
Neither loading nor validation depends on Textual, subprocesses or network I/O.
There is no file discovery, default path or CLI integration in task 1.

The [README schema](../README.md#load-project-metadata) and
[fictional example](../examples/projects.example.toml) describe the supported
format. Small policy choices for version 1 are:

| Decision | Reason |
| --- | --- |
| Reject unknown fields at both levels; accept an explicit empty array | Catch spelling mistakes while allowing a valid configuration with no projects |
| Preserve strings; reject whitespace-only strings | Avoid changing display names or reference values silently |
| Require exact integer version 1 and unique, case-sensitive IDs | Python booleans are integers too; explicit checks preserve the TOML contract |
| Validate HTTP/HTTPS scheme, host presence, credentials and port syntax/range | `urlsplit` separates components but is not a full URL validator |
| Reject raw whitespace, controls and backslashes before URL parsing | Parsers can discard controls and browsers can normalize backslashes; rejecting them avoids ambiguous input |
| Keep paths and SSH argument lists outside the schema | These need separate semantics; no reference is checked against the local filesystem |
| Fail on the first error with one `ProjectConfigError` type | Callers receive either complete validated data or an actionable failure |
| Use one-based project positions and omit supplied values, paths and unknown key names in errors | Locate a problem without exposing private metadata; allowed field names and TOML line/column provide context |

URL syntax checks do not establish DNS validity, reachability or trust in a link's
contents. Standard HTTP/HTTPS ports, queries, fragments and encoded path spaces
are supported; the original string is retained. All metadata stays inert until
a later, explicitly requested action uses it. No private file is created or
overwritten, and underlying parser/file exception text is suppressed.

## Proposed boundaries

Develop these only as the corresponding [roadmap](roadmap.md) tasks are selected:

1. **TUI:** connect the existing loader to an explicit configuration option,
   then own selection and presentation of validated records. Add controls only
   when their behavior exists.
2. **SSH launcher:** accept a validated alias after an explicit user action,
   temporarily release terminal ownership to native SSH and restore the TUI on
   completion. Design the exact terminal handoff when that task is implemented.

No launcher or plugin layer is prebuilt for those steps.
No database, telemetry, service account, cloud service or AI API is required.

## Security and privacy boundaries

Native SSH will handle credentials, agents, user SSH configuration and host-key
checks. SSH Workbench will not store passwords or private keys, parse private
keys, or disable host-key verification. Bootstrap and automated tests must never
read real SSH files or access real hosts.

For future subprocess code, validate aliases as data and use an argument list
with a resolved executable and `shell=False`. Reject values that could be flags,
commands or multiple arguments. Never build shell command strings from project
metadata. Do not accept arbitrary SSH flags or remote commands from configuration.

Metadata is untrusted input: display it as plain text, report validation errors
without dumping file contents, and validate supported URL schemes before opening
links. Opening a URL or connecting to a host must follow an explicit user action.
Do not log secrets or raw authentication output.

Use fictional fixtures and temporary files for tests. Keep private configuration,
inventories and machine-specific notes in ignored `.local/`; review all staged
files because ignore rules are only one boundary. Committed documentation uses
portable relative links and contains no private vault or lab paths.

## References checked for task 1

- [Python 3.14 TOML parsing and errors](https://docs.python.org/3.14/library/tomllib.html)
- [Python URL parsing behavior and validation limits](https://docs.python.org/3.14/library/urllib.parse.html#url-parsing-security)

## References checked during bootstrap

- [Textual application lifecycle](https://textual.textualize.io/guide/app/)
- [Textual headless testing](https://textual.textualize.io/guide/testing/)
- [uv build backend and src layout](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [Python 3.14.7 release](https://www.python.org/downloads/release/python-3147/)
