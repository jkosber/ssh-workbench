# Architecture

## Module map

| Path | Responsibility |
| --- | --- |
| `src/ssh_workbench/cli.py` | Entry point: help and version, default-file location, loading, starting the app |
| `src/ssh_workbench/config.py` | TOML loading and formatting, schema 1 and 2 validation, `Machine` and `Link` records and the shared field rules. No Textual, subprocesses or filesystem search |
| `src/ssh_workbench/store.py` | The only file writing: outside-change check, `.bak` copy and atomic replace of the machine file |
| `src/ssh_workbench/sshconfig.py` | The SSH folder and the literal `Host` names from its `config` and `Include` files; nothing else is interpreted |
| `src/ssh_workbench/app.py` | Textual app: machine list, details, status lines, the link picker and the C/O/A/E/X/Q actions |
| `src/ssh_workbench/forms.py` | The machine form and the delete confirmation |
| `src/ssh_workbench/display.py` | Literal display of configuration text, with nonprinting characters escaped |
| `src/ssh_workbench/ssh.py` | Native SSH boundary: machine recheck, argument list, executable lookup, child process and SIGINT guard |
| `src/ssh_workbench/links.py` | Browser boundary: URL recheck and operating-system dispatch |
| `src/ssh_workbench/__main__.py` | `python -m ssh_workbench` |
| `tests/` | Loader, CLI, boundary and headless UI tests with fictional data |
| `scripts/check_package.py` | Installs the wheel from `uv build` in a temporary environment and checks it |
| `scripts/package_smoke.py` | The installed-wheel loader, headless app, blocked-opener quit and first-save checks, run by `check_package.py` with `python -I` |
| `scripts/external_boundaries.py` | The shared list of process, network and browser entry points that tests, fixtures and the package check reject |
| `scripts/check_terminal.py` | Interactive terminal handoff check with harmless local children instead of SSH |
| `scripts/check_links.py` | Interactive link check with substituted openers; never opens a real browser |
| `examples/` | Fictional configuration |
| `.github/` | CI and the pull-request template |

`cli` imports `config` and, after argument parsing, `app`. `app` uses `forms`,
`store`, `sshconfig`, `ssh` and `links`, which reuse validation from `config`.
Only `__main__` imports `cli`.

## Implemented CLI and machine browser

The installed `ssh-workbench` entry point calls `ssh_workbench.cli.main`.
Standard-library `argparse` handles help, version and invalid options before
reading configuration or loading the TUI. Version output uses
`importlib.metadata.version`; the source of that metadata is `pyproject.toml`.

An explicit `--config PATH` calls `load_machines(Path)` once and skips the
default file entirely. Without it, `default_config_path()` names the per-user
file: `%APPDATA%\ssh-workbench\machines.toml` on Windows, otherwise
`$XDG_CONFIG_HOME/ssh-workbench/machines.toml` when that variable is absolute,
or `~/.config/ssh-workbench/machines.toml`. The XDG specification says to ignore
relative values; an unset or relative `APPDATA`, or an unresolvable home folder,
means no default location. Resolution reads only environment variables and the
home folder. The default file is loaded when `Path.exists()` is true, so a
folder at that path is reported instead of hidden; a missing file leaves the app
in its no-configuration state, which shows the path. The 0.1.0 name
`projects.toml` is not checked. Nothing searches other folders, and loading
never creates or writes anything; only a save does.

A `ConfigError` becomes an argparse error on stderr with exit status 2, before
terminal startup. Default-file errors read `default configuration file:`
followed by the loader's message without its own `configuration:` prefix, so a
user can tell which file failed without the path being printed. `--help` prints
the resolved path on its own line in an epilog that `RawDescriptionHelpFormatter`
does not rewrap, escaped for display and for the output encoding. argparse
%-formats an epilog only when it contains `%(prog)`, so `%` is doubled only then.

`SSHWorkbenchApp(machines, config_path, file_text)` receives validated records
in file order and the text they were read from. It retains them in a tuple;
`None` means no file was loaded and an empty sequence means a loaded file
contains no machines. Those states have different informative screens, both
naming `config_path`, escaped for display, when one exists: the loaded file, or
the default location, where the first save creates the file. Only the no-file
screen mentions `--config`. The app makes no network calls. Its explicit Connect
action delegates process I/O to the small native SSH boundary; O delegates URL
dispatch to a separate browser boundary; saves go through `store`.

A Textual `ListView` starts focused on the first machine. Its `Highlighted`
event updates literal `Static` values in a `VerticalScroll` details pane and
resets that pane to the top: ID, name, connection kind, the alias or the
addresses (one per line, under a label that changes with the kind), user, port,
key and links (`name: URL` per line). Unset direct fields read `Not set`; alias
machines read `From your SSH config`. Tab/Shift+Tab switch panes; details use
Textual's standard scrolling keys. List rows shorten long names while details
wrap the full value. Selection uses the list's highlight and focus uses an
accent border. The footer shows C / Connect, O / Open link, A / Add, E / Edit,
X / Delete and Q / Quit, with Ctrl+Q as an additional exit key. `check_action`
dims every action while connecting, while a modal screen is open and while the
panes rebuild after a save; it also dims C, O, E and X without a selection, O
for a machine without links, and A, E and X without a file location. Textual
owns the event loop and terminal lifecycle. Link actions do not change pane
focus or selection. Connect results end with `Machine N: <id>` so they name the
machine.

The list, details and help line live in `MachinePanes`, a container whose
`compose` asks the app for its children. A save rebuilds that container with
`Widget.recompose`: `App.recompose` would rebuild whichever screen is active,
which can be an open form. Between a save and the rebuild the old list is still
mounted while the app already holds the new machines, so a `_rebuilding` flag
keeps actions and stale highlights off until the rebuild ends; the rebuild then
shows the saved machine's details and focuses the list on the browser screen.

`_display_text` escapes nonprinting characters using Python-style representations,
including C0/C1 controls, formatting controls and nonprinting separators. It is
applied only when rendering; frozen `Machine` and `Link` values remain
untouched. Every configuration-derived `Static` uses `markup=False`, and picker
options are plain `Content`, with no link widgets or Rich/Textual markup
interpretation. Terminal-provided URL detection is outside the application's
control.

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
loader. The checks that import the installed package live in
`scripts/package_smoke.py`; each run starts with the isolation and module-path
assertions. The package check also substitutes the terminal-run boundary with Textual's headless
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

The explicit O action opens a machine's only link directly. With several links
it pushes `LinkPicker`, a `ModalScreen` with an `OptionList` of `name  URL`
prompts: Enter dismisses it with the highlighted link and Escape with none.
Textual's modal binding chain hides the app's bindings, so C and O cannot run
while it is open; the picker repeats Q and Ctrl+Q so quitting still works.
The chosen link becomes a frozen `LinkRequest` holding the machine, the `Link`
and the one-based list position. One daemon thread calls the boundary; repeated
actions receive a pending message without opening a picker or starting another
request.
Installed Textual 8.2.8 thread workers use asyncio's default executor, whose
shutdown can wait for blocked calls. The daemon avoids that quit delay and
communicates only through Textual's thread-safe `post_message`. The event handler
alone updates UI state, accepts only the current request identity, and never
restores selection or focus. Fixed three-row link status prevents completion
from resizing the panes; a machine number remains visible even if its ID clips.
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

`ssh_workbench.ssh.launch_ssh(machine, address=None)` is synchronous and runs on
the main thread. `ssh_arguments(machine, address)` first rechecks the machine
with the loader's own predicates, before executable lookup:

| Machine | Arguments after the executable |
| --- | --- |
| Alias | `--`, alias |
| Direct | `-o HostKeyAlias=<id>`, then `-l <user>`, `-p <port>` and `-i <key> -o IdentitiesOnly=yes` when set, then `--` and the address |

The address defaults to the first listed one and must be one of the machine's
addresses. `--` ends option parsing as a second safeguard behind validation;
Windows OpenSSH 9.5p2 and portable OpenSSH 10.5p1 accept it before hostname,
IPv4 and IPv6 destinations, and still refuse `-- -oProxyCommand=x` as an
invalid hostname. `HostKeyAlias` checks one `known_hosts` entry per machine,
whichever address is used. A key starting with `~/` or `~\` is expanded with
`Path.home()`, splitting the rest on either separator, because OpenSSH expands
only `~/`; the rules keep that rest inside the home folder (no second root or
drive). Other keys pass unchanged.
OpenSSH checks that the raw `-i` path exists before expanding `%` and `${}`
codes, so the rules reject those characters rather than escaping them. Workbench
never opens the key file.

`shutil.which` finds `ssh.exe` on Windows or `ssh` elsewhere; the resulting
absolute path and those arguments form the entire argument list. The Windows
lookup explicitly requests an executable rather than a batch file. On Windows, `shutil.which` checks the current directory before `PATH`
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
suspension handling, signal guard and restoration remain unchanged. Task 8 adds
the machine argument list and names the machine in the status line; the retry
guidance mentions the machine's settings rather than the alias for direct
machines.

## Implemented machine file loader

`ssh_workbench.config.load_machines(path: Path) -> list[Machine]` reads only the
explicit UTF-8 file and drops a leading byte-order mark, which Windows PowerShell
5.1 and some editors write. A folder is reported as `expected a file, got a
directory` before reading, because Windows would otherwise say "permission
denied". `parse_machines(text)` uses standard-library `tomllib`, checks
`schema_version` first and then validates that version's schema. The frozen
`Machine` dataclass holds `id`, `name`, `alias`, `user`, `addresses`, `port`,
`key` and `links`; `Link` holds `name` and `url`; tuples keep them immutable and
the list preserves file order. Neither loading nor validation depends on
Textual, subprocesses or network I/O. The loader has no default path or
discovery of its own; the CLI chooses which file to pass.

Schema 1 files load as alias machines: `ssh_alias` becomes `alias`, and
`repository` and `documentation` become links named "Repository" and
"Documentation" in that order. Their errors keep `projects[N]` locations, so a
0.1.0 file reports its field errors at the same locations as before. The
version message now reads `expected integer 1 or 2`.

The [README schema](../README.md#schema) and
[fictional example](../examples/machines.example.toml) describe the supported
format. Small policy choices:

| Decision | Reason |
| --- | --- |
| Reject unknown fields at every level; accept an explicit empty array | Catch spelling mistakes while allowing a valid file with no machines |
| Preserve strings; reject whitespace-only strings | Avoid changing display names or reference values silently |
| Require exact integer version 1 or 2 and unique, case-sensitive IDs | Python booleans are integers too; explicit checks preserve the TOML contract |
| Either `alias` or `addresses`; `user`, `port` and `key` only with `addresses` | An alias's SSH config already decides those values; mixing them would hide which one SSH uses |
| `user` and addresses never start with `-` and contain no whitespace, controls or `@`; addresses are hostnames, IPv4 or IPv6 without a `%` zone; digits-and-dots values must be valid IPv4 | Each value stays one SSH argument and cannot become an option or a second destination |
| Accept either platform's absolute key path, or `~/` and `~\` | A machine file in a synced folder can serve Windows and Linux |
| Reject `"`, `%`, `${`, controls and `.pub` in key paths | OpenSSH would expand `%` and `${}` after checking the raw path; a `.pub` file is never a private key |
| Unique link names within a machine; URLs keep the 0.1.0 rule | Names identify picker entries; the browser boundary rechecks the same URL rule |
| Validate HTTP/HTTPS scheme, host presence, credentials and port syntax/range | `urlsplit` separates components but is not a full URL validator |
| Reject raw whitespace, controls and backslashes before URL parsing | Parsers can discard controls and browsers can normalize backslashes; rejecting them avoids ambiguous input |
| Fail on the first error with one `ConfigError` type | Callers receive either complete validated data or an actionable failure |
| Use one-based positions and omit supplied values, paths and unknown key names in errors | Locate a problem without exposing private metadata; allowed field names and TOML line/column provide context |

The predicates `is_valid_machine_id`, `is_valid_ssh_alias`, `is_valid_user`,
`is_valid_address`, `is_valid_port` and `is_valid_key_path` are public so the
launch boundary, and later the edit forms, apply exactly the loader's rules.

URL syntax checks do not establish DNS validity, reachability or trust in a link's
contents. Standard HTTP/HTTPS ports, queries, fragments and encoded path spaces
are supported; the original string is retained. All metadata stays inert until
a later, explicitly requested action uses it. The loader creates and overwrites
nothing, and underlying parser/file exception text is suppressed.

No database, telemetry, service account, cloud service or AI API is required.

### Python API

`load_machines(path)` reads UTF-8 TOML, with or without a byte-order mark, and
returns a `list[Machine]` in file order. Absent optional fields are `None`, or
an empty tuple for `addresses` and `links`. `parse_machines(text)` performs the
same parsing and validation on an existing string. Both report problems through
`ConfigError`. Neither uses the data to connect, run commands or open links.
From the repository:

```text
uv run --locked python -c "from pathlib import Path; from ssh_workbench.config import load_machines; print(load_machines(Path('examples/machines.example.toml')))"
```

Parsing checks TOML syntax; validation then checks the values against the
schema. `alias = "--help"` parses as TOML but fails validation at
`machines[1].alias`, because an alias cannot start with a dash. A missing
closing quote is a parsing error instead, reported with a line and column.

Errors identify a field and a one-based position where possible. They
omit file paths, supplied values and unknown key names; unknown-field errors list
the allowed fields. The loader stops at the first error and never returns
partial results.

## Implemented editing and saving

A, E and X open `forms.MachineForm` or `forms.ConfirmDelete` as modal screens.
The form turns its fields into a table (addresses split on commas and spaces,
a port of digits made an integer, one link per line with the last word as the
URL, structured fields stripped) and checks it with `config.validate_machine`,
the loader's per-machine rules, plus a unique-ID check. It shows the first
problem under its field once that field changed or a save was attempted.
Ctrl+S and Escape are priority bindings handled in arrival order, and the form
answers once, so keys typed after a save cannot save twice.

The form hands a valid machine to the app, which calls
`store.save_machines(path, machines, expected_text)`:

| Step | Detail |
| --- | --- |
| Outside change | The current text is read the same way as when loading. If it differs from the text loaded (or the file appeared or vanished), `FileChangedError` stops the save. The app reloads the file and keeps the form open with a message; an invalid file is reported and nothing changes |
| Unchanged | When the new text equals the current text, nothing is written |
| Backup | The previous bytes go to `machines.toml.bak`, written like the file itself |
| Write | `config.format_machines` produces schema 2 TOML in a fixed layout, escaping every control character. The bytes go to a temporary file in the same folder, are flushed and fsynced, take the old file's mode, and `os.replace` puts them in place |
| Failure | The temporary file is removed and a `SaveError` names only the reason, never the path |

A text comparison catches edits that keep the modification time, such as some
synced folders. Saving drops comments and hand formatting; when the loaded text
differs from `format_machines` of the loaded machines, the form's first Ctrl+S
says so and the second saves, and the delete question repeats the warning.
`parse_machines(format_machines(m)) == m` is tested for every record shape.

The add form lists literal `Host` names from `sshconfig.host_names`. It reads
`config` in the SSH folder (`SSH_WORKBENCH_SSH_DIR` when absolute, else
`~/.ssh`) and follows `Include` lines: relative names from that folder, `~`
meaning its parent, globs in sorted order, up to OpenSSH's depth of 16, each
file once and at most 1 MB. Only `Host` and `Include` keywords are interpreted;
names with `*`, `?` or `!`, or that fail the alias rule, are skipped. Include
targets named `id_*`, `*.pub`, `known_hosts*` or `authorized_keys*` are never
opened. Unreadable files are skipped silently, because the names are only
suggestions.

## Security and privacy boundaries

Native SSH handles credentials, agents, user SSH configuration and host-key
checks. SSH Workbench does not store passwords or private keys, parse private
keys, or disable host-key verification. Bootstrap and automated tests must never
read real SSH files or access real hosts; the test suite points
`SSH_WORKBENCH_SSH_DIR`, `APPDATA` and `XDG_CONFIG_HOME` at an empty folder.

0.2.0 deliberately changes two 0.1.0 rules:

| 0.1.0 rule | Now |
| --- | --- |
| Never writes configuration | Writes its own machine file and `.bak` copy, only from A, E or X, with the change check and atomic replace above |
| Never reads SSH configuration | Reads `Host` and `Include` lines of the user's SSH config to suggest aliases; never opens keys, `known_hosts` or `authorized_keys`, and never changes the SSH config |

For subprocess code, validate aliases, users, addresses, ports and key paths as
data and use an argument list with a resolved executable and `shell=False`.
Reject values that could be flags, commands or multiple arguments, revalidate
them at the boundary, and put `--` before the destination. Never build shell
command strings from machine data. Do not accept arbitrary SSH flags or remote
commands from configuration. `HostKeyAlias` changes where SSH records a host
key, never whether it checks one.

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

## References checked for task 9

- [Python os.replace](https://docs.python.org/3.14/library/os.html#os.replace) and [tempfile.mkstemp](https://docs.python.org/3.14/library/tempfile.html#tempfile.mkstemp)
- [OpenSSH ssh_config(5)](https://man.openbsd.org/ssh_config) for `Host` patterns and `Include`
- [TOML 1.0 basic strings](https://toml.io/en/v1.0.0#string)

Installed Textual 8.2.8 sources were checked for `Widget.recompose` against
`App.recompose`, `Screen.set_focus` on an inactive screen, priority bindings in
modal screens, `RadioSet`, `TextArea` and `SuggestFromList`.

## References checked for task 8

- [OpenSSH ssh(1)](https://man.openbsd.org/ssh) for `-l`, `-p`, `-i` and `-o`
- [OpenSSH ssh_config(5)](https://man.openbsd.org/ssh_config) for `HostKeyAlias`, `IdentitiesOnly` and token expansion
- [Textual screens and modal screens](https://textual.textualize.io/guide/screens/)
- [Textual OptionList](https://textual.textualize.io/widgets/option_list/)

Windows OpenSSH 9.5p2 and Git for Windows' portable OpenSSH 10.5p1 were run
with `-F none -G`, which reads no configuration file and connects nowhere, on the
exact argument lists `ssh_arguments` builds. Installed Textual 8.2.8 sources were
inspected for `check_action`, the modal binding chain and `OptionList`
highlighting. Python 3.14.7 `argparse` formats an epilog with `%` only when it
contains `%(prog)`.

## References checked during bootstrap

- [Textual application lifecycle](https://textual.textualize.io/guide/app/)
- [Textual headless testing](https://textual.textualize.io/guide/testing/)
- [uv build backend and src layout](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [Python 3.14.7 release](https://www.python.org/downloads/release/python-3147/)
