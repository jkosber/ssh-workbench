# SSH Workbench

A keyboard-driven terminal interface for the machines you work on. Keep a short
list of machines, each with a way to connect and optional web links such as a
dashboard. Pick one, press **C**, and your own OpenSSH client takes over the
terminal. When the session ends, you are back in the list with the same machine
selected.

Workbench reads one TOML file and starts `ssh` with an argument list it checks
first. Passwords, keys, the SSH agent and host-key checks all stay with OpenSSH.

## Platform support

| Platform | Status |
| --- | --- |
| Windows 11 | Tested in Windows Terminal with real SSH hosts and browser links |
| Linux | Automated tests in CI only. Opening links needs a desktop session with `gio` and is untested on a real desktop |
| macOS | Untested. Links report "browser unavailable" |

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/). It downloads
  Python 3.14 or later for Workbench if you don't have it.
- The OpenSSH client: `ssh.exe` on Windows (the built-in "OpenSSH Client"
  optional feature), `ssh` elsewhere. Only absolute `PATH` entries count, so an
  `ssh.exe` in the folder you start Workbench from is never run.
- Machines you can reach with SSH, either through a `Host` entry in your SSH
  config or directly by address.

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

The `v0.1.0` tag predates machines: it reads `projects.toml` and uses R and D
instead of O. Install from a clone to get the version this README describes.

If your shell can't find `ssh-workbench`, run `uv tool update-shell` and open a
new terminal. To upgrade a clone install, run `git pull`, then
`uv tool install --reinstall .`. To upgrade an install from GitHub, run the same
`uv tool install` command with `--reinstall` and the new tag. To remove
Workbench, run `uv tool uninstall ssh-workbench`; your machine file stays where
it is.

## Quick start

1. Create the machine file. On Windows, in PowerShell:

   ```powershell
   New-Item -ItemType Directory -Force "$env:APPDATA\ssh-workbench"
   notepad "$env:APPDATA\ssh-workbench\machines.toml"
   ```

   On Linux or macOS, run `mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/ssh-workbench"`
   and create `machines.toml` in that folder.
2. Add a machine. Use `alias` if `ssh <alias>` already works for it, or
   `addresses` to connect without any SSH config:

   ```toml
   schema_version = 2

   [[machines]]
   id = "web"
   name = "Web server"
   alias = "web"

   [[machines]]
   id = "lab-box"
   name = "Lab box"
   user = "admin"
   addresses = ["100.64.0.20", "192.168.1.20"]

   [[machines.links]]
   name = "Dashboard"
   url = "https://192.168.1.20:8006"
   ```

3. Run `ssh-workbench`, select a machine and press **C**. Type `exit` in the
   remote shell to come back.

`ssh-workbench --help` shows where Workbench looks for the machine file on your
machine. [examples/machines.example.toml](examples/machines.example.toml) has
another example with both kinds of machine.

## Configuration

### Where the file lives

| Platform | Default machine file |
| --- | --- |
| Windows | `%APPDATA%\ssh-workbench\machines.toml` |
| Linux, macOS | `$XDG_CONFIG_HOME/ssh-workbench/machines.toml`, or `~/.config/ssh-workbench/machines.toml` when `XDG_CONFIG_HOME` is unset or relative |

`ssh-workbench --config PATH` reads a different file instead, and the default
file is then not checked at all. Workbench only reads: it never creates or
changes either file. Restart it to pick up edits. Without a file, the start
screen shows where to create one.

Version 0.1.0 read `projects.toml` from the same folder. Workbench no longer
looks for that name; rename the file to `machines.toml`. Its schema 1 contents
still load, as described below.

### Schema

The file is UTF-8 TOML; a byte-order mark is fine. Schema version 2:

| Field | Rule |
| --- | --- |
| `schema_version` | Required, the integer `2` |
| `machines` | Required array of tables, usually written as `[[machines]]` blocks. `machines = []` is valid and shows an empty-list message |
| `id` | Required and unique. Lowercase ASCII letters and digits, with single hyphens between groups, such as `lab-box` |
| `name` | Required. Any text with at least one non-space character |
| `alias` | A `Host` name from your SSH config. See [Connecting](#connecting) |
| `addresses` | Instead of `alias`: one or more hostnames or IP addresses. Workbench connects to the first one, so list the address you use most first |
| `user` | Optional, with `addresses` only. The login name, such as `admin` |
| `port` | Optional, with `addresses` only. An integer from 1 to 65535; SSH's default otherwise |
| `key` | Optional, with `addresses` only. The path of this machine's private key |
| `links` | Optional array of tables, written as `[[machines.links]]` after the machine, each with a `name` and a `url` |

Each machine has either `alias` or `addresses`, never both. Rules for the values:

| Value | Accepted |
| --- | --- |
| `alias` | Starts with an ASCII letter or digit; only ASCII letters, digits, dots, underscores and hyphens |
| Address | A hostname made of letters, digits, hyphens and underscores between dots, an IPv4 address, or an IPv6 address without brackets or a `%` zone |
| `user` | Starts with an ASCII letter, digit or underscore; only ASCII letters, digits, dots, underscores and hyphens |
| `key` | An absolute path, or one starting with `~/` (or `~\`) inside your home folder. On Windows, use single quotes so backslashes stay literal: `key = 'C:\Users\you\.ssh\id_ed25519_lab'`. No double quotes, `%` or `${`, because SSH would read them as substitutions, and not the `.pub` file |
| Link `name` | Any text with at least one non-space character, unique within the machine |
| Link `url` | An absolute `http://` or `https://` URL without a username or password |

These rules keep every value a single safe argument: nothing can start with `-`,
and only a key path may contain spaces, so no value can turn into an SSH option. A Windows user name
with a space needs an alias machine with a `User` line in your SSH config.

Unknown fields are errors, so a typo such as `adress` is reported instead of
silently ignored. Links can't contain raw spaces, control characters or
backslashes; write a space as `%20`. Values appear exactly as written, except
that control characters, format characters such as right-to-left marks, and
non-ASCII spaces show as escapes such as `\x1b`. Nothing in the file is treated
as markup or turned into a clickable link.

Schema 1 files from 0.1.0 still load. Each `[[projects]]` entry becomes a
machine whose `ssh_alias` is its `alias`, and whose `repository` and
`documentation` become links named "Repository" and "Documentation".

## Connecting

C suspends Workbench and runs SSH in the same terminal window. Everything during
the session belongs to SSH: password and key prompts, host-key confirmation and
Ctrl+C. When SSH exits, Workbench comes back with the same machine selected and
shows the exit status below the panes. Only one connection runs at a time.

| Machine | Workbench runs |
| --- | --- |
| With `alias` | `ssh -- <alias>`. Your SSH config decides the host, user, port and key |
| With `addresses` | `ssh -o HostKeyAlias=<id> [-l <user>] [-p <port>] [-i <key> -o IdentitiesOnly=yes] -- <first address>` |

The `--` ends SSH's options, so the destination can never be read as one. An
alias can also be a plain hostname, or a name that a pattern such as
`Host *.example.com` matches.

A machine with addresses needs no SSH config. `HostKeyAlias` makes SSH remember
the machine's host key under its ID, so you confirm the key once per machine
whichever address is used. Host keys that `known_hosts` already holds under an
address don't carry over: the first connection asks once. With a `key`, SSH
offers only that key (`IdentitiesOnly`); a key with a passphrase asks for it,
unless your SSH agent already holds the key.

Run Workbench in a local terminal. Environments that can't hand the terminal
over, such as Textual Web, show a message instead of starting SSH.

## Keys

| Key | Action |
| --- | --- |
| Up / Down | Select a machine; in the details pane, scroll |
| Tab / Shift+Tab | Move between the machine list and the details pane |
| Page Up / Page Down, Home / End | Scroll the details pane |
| C | Connect to the selected machine |
| O | Open the selected machine's link, or choose one when it has several |
| Enter / Escape | In the link list: open the highlighted link / cancel |
| Q or Ctrl+Q | Quit |

C, O and Q also appear in the footer and can be clicked. C and O are dimmed when
nothing is selected, and O when the machine has no links. Startup, selection
and Enter in the machine list never connect or open anything.

## Opening links

O passes the selected link's URL to the system: the default browser on
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
| `configuration: expected a file, got a directory` | The path names a folder. Point `--config` at the file, or remove the folder at the default location |
| `configuration: permission denied` | The file can't be read |
| `configuration: expected UTF-8 text` | Save the file as UTF-8 |
| `TOML: invalid syntax at line L, column C` | Fix the TOML at that position; a missing quote or bracket is the usual cause |
| `machines[N].field: ...` | Fix that field in machine N, counting from 1. Messages never repeat the value, to keep private data off the screen |
| `projects[N].field: ...` | The same, in a schema 1 file |
| `default configuration file: ...` | One of the errors above, from the default machine file; `ssh-workbench --help` shows its path |
| `SSH not found. Install OpenSSH and add it to PATH.` | Install the OpenSSH client. On Windows 11: Settings > System > Optional features > OpenSSH Client |
| `SSH exited with status 255. ...` | SSH couldn't connect or authenticate. Run the same `ssh` command directly to see its message |
| `Invalid machine settings. ...` | A value failed the rules above; this only happens if records were changed after loading |
| `Cannot hand off this terminal. ...` | Start Workbench from a local terminal |
| `browser unavailable. ...` | Links work only on Windows and on Linux desktops with `gio` |
| `ssh-workbench` not found after installing | Run `uv tool update-shell` and open a new terminal |

## Privacy

Workbench reads only its machine file. It doesn't read your SSH config, keys or
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
