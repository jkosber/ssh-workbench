# SSH Workbench

A keyboard-driven terminal interface for the machines you work on. Keep a short
list of projects, each with its SSH alias and optional repository and
documentation links. Pick one, press **C**, and your own OpenSSH client takes
over the terminal. When the session ends, you are back in the list with the same
project selected.

Workbench reads one TOML file and starts `ssh` with a single alias argument.
Passwords, keys, the SSH agent and host-key checks all stay with OpenSSH.

## Platform support

| Platform | Status |
| --- | --- |
| Windows 11 | Tested in Windows Terminal with real SSH hosts and browser links |
| Linux | Automated tests in CI only. Opening links needs a desktop session with `gio` and is untested on a real desktop |
| macOS | Untested. Links report "browser unavailable" |

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/). It downloads
  Python 3.14 for Workbench if you don't have it.
- The OpenSSH client: `ssh.exe` on Windows (the built-in "OpenSSH Client"
  optional feature), `ssh` elsewhere. Only absolute `PATH` entries count, so an
  `ssh.exe` in the folder you start Workbench from is never run.
- Hosts you can already reach with `ssh <alias>`.

## Install

From a clone:

```text
git clone https://github.com/jkosber/ssh-workbench.git
cd ssh-workbench
uv tool install .
ssh-workbench --version
```

Or directly from GitHub, which needs access to the private repository:

```text
uv tool install git+https://github.com/jkosber/ssh-workbench@v0.1.0
```

If your shell can't find `ssh-workbench`, run `uv tool update-shell` and open a
new terminal. To upgrade a clone install, run `git pull`, then
`uv tool install --reinstall .`. To remove Workbench, run
`uv tool uninstall ssh-workbench`; your projects file stays where it is.

## Quick start

1. Check that `ssh <alias>` connects on its own.
2. Create the projects file. On Windows, in PowerShell:

   ```powershell
   New-Item -ItemType Directory -Force "$env:APPDATA\ssh-workbench"
   notepad "$env:APPDATA\ssh-workbench\projects.toml"
   ```

   On Linux or macOS, run `mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/ssh-workbench"`
   and create `projects.toml` in that folder.
3. Add a project:

   ```toml
   schema_version = 1

   [[projects]]
   id = "web"
   name = "Web server"
   ssh_alias = "web"
   repository = "https://example.com/web.git"
   documentation = "https://example.com/web/docs"
   ```

4. Run `ssh-workbench`, select the project and press **C**. Type `exit` in the
   remote shell to come back.

`ssh-workbench --help` shows where Workbench looks for the projects file on
your machine; a long path may wrap onto the next line.
[examples/projects.example.toml](examples/projects.example.toml) has
another example, including a project without links.

## Configuration

### Where the file lives

| Platform | Default projects file |
| --- | --- |
| Windows | `%APPDATA%\ssh-workbench\projects.toml` |
| Linux, macOS | `$XDG_CONFIG_HOME/ssh-workbench/projects.toml`, or `~/.config/ssh-workbench/projects.toml` when `XDG_CONFIG_HOME` is unset or relative |

`ssh-workbench --config PATH` reads a different file instead, and the default
file is then not checked at all. Workbench only reads: it never creates or
changes either file. Restart it to pick up edits. Without a file, the start
screen shows where to create one.

### Schema

The file is UTF-8 TOML; a byte-order mark is fine. Schema version 1:

| Field | Rule |
| --- | --- |
| `schema_version` | Required, the integer `1` |
| `projects` | Required array of tables, usually written as `[[projects]]` blocks. `projects = []` is valid and shows an empty-list message |
| `id` | Required and unique. Lowercase ASCII letters and digits, with single hyphens between groups, such as `web-server` |
| `name` | Required. Any text with at least one non-space character |
| `ssh_alias` | Required. See [SSH aliases](#ssh-aliases) |
| `repository` | Optional absolute `http://` or `https://` URL without a username or password |
| `documentation` | Optional, with the same rules as `repository` |

Unknown fields are errors, so a typo such as `ssh-alias` is reported instead of
silently ignored. Links can't contain raw spaces, control characters or
backslashes; write a space as `%20`. Values appear exactly as written, except
that control characters show as escapes such as `\x1b`. Nothing in the file is
treated as markup or turned into a clickable link.

### SSH aliases

Workbench runs `ssh <ssh_alias>` with the alias as the only argument, so the
alias can be anything `ssh` accepts as a destination: usually a `Host` entry in
your SSH config (`~/.ssh/config`, or `%USERPROFILE%\.ssh\config` on Windows), or
a plain hostname.

To keep it a single safe argument, an alias must start with an ASCII letter or
digit and contain only ASCII letters, digits, dots, underscores and hyphens.
That rules out `user@host`, ports and options. Put those in a `Host` entry
instead:

```text
Host web
    HostName web.example.com
    User deploy
    Port 2222
```

Then set `ssh_alias = "web"`.

## Keys

| Key | Action |
| --- | --- |
| Up / Down | Select a project; in the details pane, scroll |
| Tab / Shift+Tab | Move between the project list and the details pane |
| Page Up / Page Down, Home / End | Scroll the details pane |
| C | Connect to the selected project |
| R | Open the repository link |
| D | Open the documentation link |
| Q or Ctrl+Q | Quit |

C, R, D and Q also appear in the footer and can be clicked. Startup, selection
and Enter never connect or open anything.

## Connecting

C suspends Workbench and runs SSH in the same terminal window. Everything during
the session belongs to SSH: password and key prompts, host-key confirmation and
Ctrl+C. When SSH exits, Workbench comes back with the same project selected and
shows the exit status below the panes. Only one connection runs at a time.

Run Workbench in a local terminal. Environments that can't hand the terminal
over, such as Textual Web, show a message instead of starting SSH.

## Opening links

R and D pass the selected project's URL to the system: the default browser on
Windows, or `gio open` on a Linux desktop where `DISPLAY` or `WAYLAND_DISPLAY`
is set. "browser request accepted" means the system took the request, not that
the page loaded. The browser opens on the machine running Workbench, which over
a remote terminal may not be the one in front of you. One request can be
pending at a time, and Q still quits while it waits.

## Troubleshooting

Configuration errors appear before the screen starts, and Workbench exits with
status 2.

| Message | What to do |
| --- | --- |
| `configuration: file not found` | Check the path given to `--config` |
| `configuration: permission denied` | The file can't be read. On Windows this also appears when the path is a folder |
| `configuration: expected UTF-8 text` | Save the file as UTF-8 |
| `TOML: invalid syntax at line L, column C` | Fix the TOML at that position; a missing quote or bracket is the usual cause |
| `projects[N].field: ...` | Fix that field in project N, counting from 1. Messages never repeat the value, to keep private data off the screen |
| `default configuration file: ...` | One of the errors above, from the default projects file; `ssh-workbench --help` shows its path |
| `SSH not found. Install OpenSSH and add it to PATH.` | Install the OpenSSH client. On Windows 11: Settings > System > Optional features > OpenSSH Client |
| `SSH exited with status 255. ...` | SSH couldn't connect or authenticate. Run `ssh <alias>` directly to see its message |
| `Cannot hand off this terminal. ...` | Start Workbench from a local terminal |
| `browser unavailable. ...` | Links work only on Windows and on Linux desktops with `gio` |
| `link not configured. ...` | Add `repository` or `documentation` to the project and restart |
| `ssh-workbench` not found after installing | Run `uv tool update-shell` and open a new terminal |

## Privacy

Workbench reads only its projects file. It doesn't read your SSH config, keys or
`known_hosts`, store credentials, change host-key settings, collect telemetry or
need an AI service. Network traffic comes only from the SSH sessions and browser
requests you start.

## Development

[CONTRIBUTING](CONTRIBUTING.md) covers setup, checks, the terminal test fixtures
and the release checklist.

| Document | Contents |
| --- | --- |
| [Architecture](docs/architecture.md) | Module map, design decisions, safety boundaries and the Python API |
| [Roadmap](docs/roadmap.md) | The backlog and each task's acceptance criteria |
| [Validation](docs/validation.md) | Dated test evidence |
| [Changelog](CHANGELOG.md) | Changes by release |
| [AGENTS](AGENTS.md) | Instructions for coding agents |
| [Publishing](docs/publishing.md) | Checklist before any public release |

## License

MIT. See [LICENSE](LICENSE).
