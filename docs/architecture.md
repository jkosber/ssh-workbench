# Architecture

## Implemented scaffold

The installed `ssh-workbench` entry point calls `ssh_workbench.cli.main`.
Standard-library `argparse` handles help, version and invalid options before
loading the TUI. Version output uses `importlib.metadata.version`; the source
of that metadata is `pyproject.toml`.

`ssh_workbench.app.SSHWorkbenchApp` renders a header, a scaffold notice and a
footer with the quit binding. Textual owns the event loop and terminal lifecycle.
No project configuration is read and no SSH process is started.

| Decision | Reason |
| --- | --- |
| Python 3.14.7 for development, minimum >=3.14 | A supported stable interpreter already available at bootstrap; one version keeps the initial CI matrix small |
| Textual as the only direct runtime dependency | Terminal layout, keyboard handling and headless tests without a web backend |
| Standard-library argparse and metadata | Help/version need no extra CLI framework or duplicated version constant |
| uv with its build backend and a `src/` layout | One tool for environments, a committed lockfile and installable artifacts; tests exercise an installed package |
| pytest plus pytest-asyncio; Ruff | Small test and quality toolset with the same commands locally and in CI |

The source and wheel are built by `uv build`. The package check installs
the wheel and locked runtime dependencies in a disposable environment outside
the checkout, where it checks the console entry point. It does not launch SSH.

## Proposed boundaries

Develop these only as the corresponding [roadmap](roadmap.md) tasks are selected:

1. **Project metadata:** parse an explicitly supplied TOML path, validate the
   schema and return typed project records. Keep parsing independent of Textual
   and subprocesses. The standard library provides `tomllib`.
2. **TUI:** own selection and presentation of already validated records. Add
   controls only when their behavior exists. The illustrative
   [configuration](../examples/projects.example.toml) is a schema proposal.
3. **SSH launcher:** accept a validated alias after an explicit user action,
   temporarily release terminal ownership to native SSH and restore the TUI on
   completion. Design the exact terminal handoff when that task is implemented.

No launcher, metadata abstraction or plugin layer is prebuilt for those steps.
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

## References checked during bootstrap

- [Textual application lifecycle](https://textual.textualize.io/guide/app/)
- [Textual headless testing](https://textual.textualize.io/guide/testing/)
- [uv build backend and src layout](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [Python 3.14.7 release](https://www.python.org/downloads/release/python-3147/)
