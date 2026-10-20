# Architecture

## Implemented CLI and project browser

The installed `ssh-workbench` entry point calls `ssh_workbench.cli.main`.
Standard-library `argparse` handles help, version and invalid options before
reading configuration or loading the TUI. Version output uses
`importlib.metadata.version`; the source of that metadata is `pyproject.toml`.

An explicit `--config PATH` calls the existing `load_projects(Path)` once. A
`ProjectConfigError` becomes an argparse error on stderr with exit status 2, before
terminal startup. There is no default configuration, discovery, or file writing.

`SSHWorkbenchApp(projects)` receives validated records in file order. It retains
them in a tuple; `None` means no configuration was supplied and an empty sequence
means a loaded configuration contains no projects. Those states have different
informative screens. The app reads no files and makes no network calls. Its
explicit Connect action delegates process I/O to the small native SSH boundary;
R/D delegate URL dispatch to a separate browser boundary.

A Textual `ListView` starts focused on the first project. Its `Highlighted` event
updates five literal `Static` field values in a `VerticalScroll` details pane and
resets that pane to the top. Tab/Shift+Tab switch panes; details use Textual's
standard scrolling keys. List rows shorten long names while details wrap the
full value. Selection uses the list's highlight and focus uses an accent border.
The footer shows C / Connect, R / Repository, D / Documentation and Q / Quit,
with Ctrl+Q as an additional exit key. Textual owns the event loop and terminal
lifecycle. Link actions do not change pane focus or selection.

`_display_text` escapes nonprinting characters using Python-style representations,
including C0/C1 controls, formatting controls and nonprinting separators. It is
applied only when rendering; frozen `Project` values remain untouched. Every
configuration-derived `Static` uses `markup=False`, with no link widgets or
Rich/Textual markup interpretation. Terminal-provided URL detection is outside
the application's control.

| Decision | Reason |
| --- | --- |
| Python 3.14.7 for development, minimum >=3.14 | A supported stable interpreter already available at bootstrap; one version keeps the initial CI matrix small |
| Textual as the only direct runtime dependency | Terminal layout, keyboard handling and headless tests without a web backend |
| Standard-library argparse and metadata | Help/version need no extra CLI framework or duplicated version constant |
| uv with its build backend and a `src/` layout | One tool for environments, a committed lockfile and installable artifacts; tests exercise an installed package |
| pytest plus pytest-asyncio; Ruff | Small test and quality toolset with the same commands locally and in CI |

The source and wheel are built by `uv build`. The package check installs
the wheel and locked runtime dependencies in a disposable environment outside
the checkout, where it checks help/version, missing-configuration errors, and the
loader. It also substitutes the terminal-run boundary with Textual's headless
pilot to exercise CLI loading, initial selection, navigation and quit at 80x24.
Common process, connection and browser entry points fail that smoke check if
called unexpectedly. During explicit Connect checks, only executable resolution
and the process runner are substituted; installed suspension code exercises
success, nonzero exit, launch error and interruption. The package check does not
establish native terminal behavior or launch real SSH. Link smoke checks replace
the opener and exercise outcomes from both panes. Separate isolated processes
verify Q/Ctrl+Q exit with a permanently blocked stub. Python `-I` and module-path
assertions verify wheel imports while `PYTHONPATH` deliberately names the checkout.

## Implemented browser boundary

`links.open_link(url)` returns one `LinkResult`: missing, invalid, unavailable,
failed or accepted. It reuses `config.validate_http_url`, extracted unchanged
from the loader. The schema, field-specific configuration errors and accepted
values are unchanged. No lookup, process or browser action occurs for invalid
input. Accepted URLs remain exact data; no query/fragment normalization, fetching,
redirect handling or page-existence check occurs.

On Windows, `os.startfile(url)` dispatches through the URL association, as used
by Python 3.14.7's `webbrowser.WindowsDefault`. On Linux with `DISPLAY` or
`WAYLAND_DISPLAY`, `shutil.which("gio")` finds the fixed desktop helper and
`subprocess.run([executable, "open", "--", url], shell=False, check=False, ...)`
waits for its dispatch result. All three streams use `DEVNULL` and the helper
starts a separate session. A zero helper status is acceptance, not page loading.
OS errors become safe results; no underlying exception text or helper output is
shown. No browser executable, flags or commands come from metadata.

Generic `webbrowser.open` and `xdg-open` are deliberately avoided because they
can fall back to text browsers. No `BROWSER` overrides, automatic retries,
system preference changes or forwarding to a terminal client are implemented.
Linux without the desktop environment or GIO, macOS and other platforms report
unavailable. Dispatch uses the environment running Workbench, including its
browser associations; the application cannot inspect external page state.

Each explicit R/D action captures a frozen `LinkRequest` containing the project,
kind, exact URL and one-based list position. One daemon thread calls the boundary;
repeated actions receive a pending message without starting another request.
Installed Textual 8.2.8 thread workers use asyncio's default executor, whose
shutdown can wait for blocked calls. The daemon avoids that quit delay and
communicates only through Textual's thread-safe `post_message`. The event handler
alone updates UI state, accepts only the current request identity, and never
restores selection or focus. Fixed three-row link status prevents completion
from resizing the panes; a project number remains visible even if its ID clips.
The separate SSH status cannot be overwritten by a link completion.

Unmount sets a thread-safe shutdown event and clears the request. The thread
checks before dispatch and before posting; closed-loop posting errors are
discarded. A dispatch already past the shutdown check may still run. Quitting
does not wait for the daemon, cancel an OS request, kill the helper or close a
browser. There is no invented browser-cancellation or page-loading signal.
Browser actions do not install signal handlers or suspend Textual.

`scripts/check_links.py` supplies fictional cases, stubs OS dispatch and guards
other execution/network entry points. It never invokes real browser or SSH
actions. Its standalone entry point installs all guards before constructing the
app and keeps them active until process exit, including after normal return or
exception unwinding. Scoped teardown could restore a real opener while a delayed
daemon still runs. There is no guard cleanup or daemon join; importing the module
does not install patches. Isolated child tests hold a worker before dispatch,
unwind the entry point, then release it into the still-active fixture guards.
Automated checks separately cover changed selection, repeat requests,
shutdown races, layout and simultaneous SSH lifecycle results.

## Implemented native SSH boundary

`ssh_workbench.ssh.launch_ssh(alias)` is synchronous and runs on the main thread.
It shares `config.is_valid_ssh_alias` with the loader, rechecking immediately before
executable lookup. `shutil.which` finds `ssh.exe` on Windows or `ssh` elsewhere;
the resulting absolute path and the unchanged alias form the entire argument
list. The Windows lookup explicitly requests an executable rather than a batch
file. On Windows, `shutil.which` checks the current directory before `PATH`
unless `NoDefaultCurrentDirectoryInExePath` is set, and a relative `PATH` entry
has the same effect anywhere. A relative result is therefore discarded and only
absolute `PATH` entries are searched, so an `ssh.exe` in the launch folder never runs. `subprocess.run` uses `shell=False`, `check=False` and inherited stdin,
stdout and stderr. No timeout, pipe, new process group or new session interferes
with native SSH's terminal behavior.

Missing executables and OS launch errors become sanitized `SSHLaunchError`
messages. A started client's integer return code is returned unchanged, including
nonzero or negative signal statuses. Output, authentication and SSH configuration
are owned entirely by the native client.

The shared `ssh_handoff` context temporarily installs a callable SIGINT handler
in the parent and restores the exact prior handler in `finally`. The app uses it
across suspension, lookup, child execution and resumption; the standalone launcher
also uses it, nesting safely inside the app's guard. This shields Textual's
asyncio task even during slow executable lookup or driver transitions. The child
receives normal Ctrl+C behavior. Using `SIG_IGN` could make the child inherit
ignored interrupts. SSH can handle Ctrl+C and keep running, so the parent waits
for actual child completion rather than treating Ctrl+C as an exit.

The app has one Connect action, bound to C and exposed by the footer. It requires
a selection and guards against reentrant launches. The synchronous action enters
`App.suspend()`, invokes the boundary and records the result. Expected launch
errors and `KeyboardInterrupt` are caught **inside** the suspension block:
installed Textual 8.2.8 resumes after a bare `yield`, without a `finally`, so an
escaping exception would skip restoration. `SuspendNotSupported` is handled
outside the block without launching a process. Afterward the selection and
details scroll remain intact, focus returns to the list, the launch guard clears
and a literal status message appears below the panes.

Headless tests retain the installed `App.suspend` implementation and substitute
only the driver's terminal methods to assert suspend/launch/resume ordering.
The separate `scripts/check_terminal.py` replaces resolution and process
invocation with fixed local Python children. It exercises real terminal handoff,
including a child that continues after Ctrl+C, without SSH resources. Its
[observed results](validation.md#task-3-native-ssh-2026-10-12) are platform-specific.
Task 4 adds only retry guidance for nonzero status and interruption; the launcher,
suspension handling, signal guard and restoration remain unchanged.

## Implemented project metadata loader

`ssh_workbench.config.load_projects(path: Path) -> list[Project]` reads only the
explicit UTF-8 file and drops a leading byte-order mark, which Windows PowerShell
5.1 and some editors write. `parse_projects(text)` uses standard-library `tomllib` and
passes the resulting data to a separate schema validator. The frozen `Project`
dataclass stores the five documented fields; the list preserves file order.
Neither loading nor validation depends on Textual, subprocesses or network I/O.
There is no file discovery or default path. Task 2 integrates this unchanged
loader at the CLI boundary.

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

No database, telemetry, service account, cloud service or AI API is required.

## Security and privacy boundaries

Native SSH handles credentials, agents, user SSH configuration and host-key
checks. SSH Workbench does not store passwords or private keys, parse private
keys, or disable host-key verification. Bootstrap and automated tests must never
read real SSH files or access real hosts.

For subprocess code, validate aliases as data and use an argument list
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

## References checked for task 2

- [Textual ListView selection and messages](https://textual.textualize.io/widgets/list_view/)
- [Textual Static literal rendering](https://textual.textualize.io/widgets/static/)
- [Textual headless interaction testing](https://textual.textualize.io/guide/testing/)

Installed Textual 8.2.8 source was also checked for selection events, focus,
literal rendering and the details pane's scrolling bindings.

## References checked for task 3

- [Textual terminal suspension](https://textual.textualize.io/api/app/#textual.app.App.suspend)
- [Python subprocess arguments, inherited streams and signals](https://docs.python.org/3.14/library/subprocess.html)
- [Python signal handlers](https://docs.python.org/3.14/library/signal.html)
- [Windows console handler inheritance](https://learn.microsoft.com/en-us/windows/console/setconsolectrlhandler)
- [Windows Ctrl+C delivery](https://learn.microsoft.com/en-us/windows/console/ctrl-c-and-ctrl-break-signals)

Installed Textual 8.2.8 application, Windows/Linux driver and Python 3.14.7
asyncio/subprocess sources were inspected for exceptional restoration and signal
handling. Source inspection of the Linux driver is not a Linux terminal test.

## References checked for task 4

- [Python browser fallback and blocking behavior](https://docs.python.org/3.14/library/webbrowser.html)
- [Python OS URL dispatch](https://docs.python.org/3.14/library/os.html#os.startfile)
- [Textual worker threading and messages](https://textual.textualize.io/guide/workers/)
- [GIO desktop URI dispatch implementation](https://github.com/GNOME/glib/blob/main/gio/gio-tool-open.c)

Installed Python 3.14.7 `webbrowser` and Textual 8.2.8 worker, message-pump and
shutdown sources were inspected. Linux dispatch is covered with substituted
boundaries; it has not been exercised on a Linux desktop.

## References checked during bootstrap

- [Textual application lifecycle](https://textual.textualize.io/guide/app/)
- [Textual headless testing](https://textual.textualize.io/guide/testing/)
- [uv build backend and src layout](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [Python 3.14.7 release](https://www.python.org/downloads/release/python-3147/)
