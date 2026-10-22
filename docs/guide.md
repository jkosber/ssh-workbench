# User guide

Everything SSH Workbench does, in the order you meet it. For a first run, the
[quick start](../README.md#quick-start) is enough.

| Section | Covers |
| --- | --- |
| [Install, upgrade and remove](#install-upgrade-and-remove) | uv tool commands |
| [The machine file](#the-machine-file) | Where it lives, the [schema](#schema) and the value rules |
| [Adding, editing and deleting](#adding-editing-and-deleting) | The form and how saving works |
| [Connecting](#connecting) | What C runs and how host keys work |
| [Status](#status) | The symbols and how checks work |
| [Renamed aliases](#renamed-aliases) | Alias not found and U |
| [Key login](#key-login) | What K does, step by step |
| [Exported aliases](#exported-aliases) | `ssh <id>` outside Workbench |
| [Opening links](#opening-links) | What O does |
| [Keys](#keys) | Every key and when it is dimmed |
| [Troubleshooting](#troubleshooting) | Messages and what to do |
| [Privacy](#privacy) | What Workbench reads, writes and sends |

## Install, upgrade and remove

| You need | Detail |
| --- | --- |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Downloads Python 3.14 or later for Workbench if you don't have it |
| The OpenSSH client | `ssh.exe` on Windows (the built-in "OpenSSH Client" optional feature), `ssh` elsewhere. Only absolute `PATH` entries count, so an `ssh.exe` in the folder you start Workbench from is never run |
| Machines you can reach with SSH | Through a `Host` entry in your SSH config, or directly by address |

| Task | Command |
| --- | --- |
| Install from GitHub | `uv tool install git+https://github.com/jkosber/ssh-workbench@v0.2.2` (needs access to the private repository) |
| Install from a clone | `uv tool install .` in the clone |
| Upgrade a GitHub install | The same `uv tool install` command with `--reinstall` and the new tag |
| Upgrade a clone install | `git pull`, then `uv tool install --reinstall .` |
| Remove | `uv tool uninstall ssh-workbench`. Your machine file stays where it is |
| Command not found | Run `uv tool update-shell` and open a new terminal |

## The machine file

### Where it lives

| Platform | Default machine file |
| --- | --- |
| Windows | `%APPDATA%\ssh-workbench\machines.toml` |
| Linux, macOS | `$XDG_CONFIG_HOME/ssh-workbench/machines.toml`, or `~/.config/ssh-workbench/machines.toml` when `XDG_CONFIG_HOME` is unset or relative |

`ssh-workbench --config PATH` reads a different file instead; the default file
is then not checked at all, and the file must already exist. Workbench writes
the file only when you add, edit or delete a machine, and creates the default
file and its folder on the first save. Without a file, the start screen shows
where it will be created.

Version 0.1.0 read `projects.toml` from the same folder. Workbench no longer
looks for that name: rename the file to `machines.toml`. Its schema 1 contents
still load, as described [below](#schema-1-files).

### Schema

The file is UTF-8 TOML; a byte-order mark is fine. Schema version 2:

| Field | Rule |
| --- | --- |
| `schema_version` | Required, the integer `2` |
| `machines` | Required array of tables, usually written as `[[machines]]` blocks. `machines = []` is valid and shows an empty-list message |
| `id` | Required and unique. Lowercase ASCII letters and digits, with single hyphens between groups, such as `lab-box` |
| `name` | Required. Any text with at least one non-space character |
| `alias` | A `Host` name from your SSH config. See [Connecting](#connecting) |
| `addresses` | Instead of `alias`: one or more hostnames or IP addresses. Workbench connects to the first one the latest status check found online, else the first listed, so list the address you use most first |
| `user` | Optional, with `addresses` only. The login name, such as `admin` |
| `port` | Optional, with `addresses` only. An integer from 1 to 65535; SSH's default otherwise |
| `key` | Optional, with `addresses` only. The path of this machine's private key |
| `export_alias` | Optional, with `addresses` only. `true` also writes the machine to Workbench's own SSH config file; see [Exported aliases](#exported-aliases) |
| `links` | Optional array of tables, written as `[[machines.links]]` after the machine, each with a `name` and a `url` |

Each machine has either `alias` or `addresses`, never both.
[examples/machines.example.toml](../examples/machines.example.toml) shows both
kinds.

### Value rules

| Value | Accepted |
| --- | --- |
| `alias` | Starts with an ASCII letter or digit; only ASCII letters, digits, dots, underscores and hyphens |
| Address | A hostname made of letters, digits, hyphens and underscores between dots, an IPv4 address, or an IPv6 address without brackets or a `%` zone |
| `user` | Starts with an ASCII letter, digit or underscore; only ASCII letters, digits, dots, underscores and hyphens |
| `key` | An absolute path, or one starting with `~/` (or `~\`) inside your home folder. On Windows, use single quotes so backslashes stay literal: `key = 'C:\Users\you\.ssh\id_ed25519_lab'`. No double quotes, `%` or `${`, because SSH would read them as substitutions, and not the `.pub` file |
| Link `name` | Any text with at least one non-space character, unique within the machine |
| Link `url` | An absolute `http://` or `https://` URL without a username or password |

These rules keep every value a single safe argument: nothing can start with
`-`, and only a key path may contain spaces, so no value can turn into an SSH
option. A Windows user name with a space needs an alias machine with a `User`
line in your SSH config.

Unknown fields are errors, so a typo such as `adress` is reported instead of
silently ignored. Links can't contain raw spaces, control characters or
backslashes; write a space as `%20`. Values appear exactly as written, except
that control characters, format characters such as right-to-left marks, and
non-ASCII spaces show as escapes such as `\x1b`. Nothing in the file is treated
as markup or turned into a clickable link.

### Schema 1 files

Schema 1 files from 0.1.0 still load. Each `[[projects]]` entry becomes a
machine whose `ssh_alias` is its `alias`, and whose `repository` and
`documentation` become links named "Repository" and "Documentation".

## Adding, editing and deleting

**A** adds a machine, **E** edits the selected one and **X** deletes it after
asking. The form checks each value with the same rules as the file and shows
the first problem under its field. **Ctrl+S** saves only a valid machine;
**Escape** closes the form without saving.

| Field | Enter |
| --- | --- |
| ID, Name | As in the file. The ID must be unique |
| SSH alias | A `Host` name. The form lists the literal `Host` names in your SSH config and completes them as you type (Right accepts); any other name is allowed too |
| Addresses | One or more, separated by commas or spaces. Workbench connects to the first |
| User, Port, Key | Optional. Leave them empty to use SSH's defaults |
| Export as an SSH alias | Optional, for direct machines. See [Exported aliases](#exported-aliases) |
| Links | One per line: the name, then the URL, such as `Dashboard https://192.168.1.20:8006` |

To list `Host` names, Workbench reads `config` in your SSH folder (`~/.ssh`, or
`%USERPROFILE%\.ssh` on Windows) and the files its `Include` lines name. It
interprets only `Host` and `Include` lines and skips names with `*`, `?` or
`!`. It never opens an included file named like a key (`id_*`, `*.pub`,
`*.pem`, `*.ppk`, `*.key`), `known_hosts` or `authorized_keys`. It changes
your SSH config only to add one `Include` line for
[exported aliases](#exported-aliases), after you press **Y**. Set
`SSH_WORKBENCH_SSH_DIR` to an absolute path to read a different folder
instead; in its `Include` lines, `~` then means that folder's parent.

How saving works:

| Rule | Detail |
| --- | --- |
| Backup | The previous file is kept as `machines.toml.bak` next to it |
| One step | The new file replaces the old one in one step, so an interrupted save never leaves half a file |
| Formatting | Saving writes the whole file in Workbench's own format. Comments and hand formatting are not kept: when the file has some, the first save says so and waits for a second **Ctrl+S**; deleting says so too |
| Outside changes | If the file changed on disk since Workbench loaded it, for example in another editor or a synced folder, Workbench does not overwrite it. It reloads the list and keeps your form open, so you can check and save again |

Edits made to the file outside Workbench show up after a restart, or when a
save finds them.

## Connecting

**C** suspends Workbench and runs SSH in the same terminal window. Everything
during the session belongs to SSH: password and key prompts, host-key
confirmation and Ctrl+C. When SSH exits, Workbench comes back with the same
machine selected and shows the exit status below the panes. Only one
connection runs at a time.

| Machine | Workbench runs |
| --- | --- |
| With `alias` | `ssh -- <alias>`. Your SSH config decides the host, user, port and key |
| With `addresses` | `ssh -o HostKeyAlias=<id> [-l <user>] [-p <port>] [-i <key> -o IdentitiesOnly=yes] -- <address>`, with the first address the latest status check found online, else the first listed |

The `--` ends SSH's options, so the destination can never be read as one. An
alias can also be a plain hostname, or a name that a pattern such as
`Host *.example.com` matches.

A machine with addresses needs no SSH config:

- `HostKeyAlias` makes SSH remember the machine's host key under its ID, so
  you confirm the key once per machine whichever address is used. Host keys
  that `known_hosts` already holds under an address don't carry over: the
  first connection asks once.
- With a `key`, SSH offers that key instead of the other keys in your agent
  and the default keys (`IdentitiesOnly`). A key with a passphrase asks for
  it, unless your SSH agent already holds the key.

Your SSH config still applies to the address: a `Host` entry that matches it
adds its options, such as `IdentityFile` or `StrictHostKeyChecking`. With
`StrictHostKeyChecking yes`, SSH refuses the first connection instead of
asking (`No <type> host key is known for <id>`, status 255). To record the key
once, run this in a terminal and check the fingerprint, or the names SSH says
the key is already known by, before answering yes:

```text
ssh -o HostKeyAlias=<id> -o StrictHostKeyChecking=ask [-l <user>] [-p <port>] -- <address>
```

Run Workbench in a local terminal. Environments that can't hand the terminal
over, such as Textual Web, show a message instead of starting SSH.

## Status

Each machine shows its status as a symbol in the list and as a word in the
details, with color on top:

| Symbol | Status | Meaning |
| --- | --- | --- |
| `◐` (turning) | Checking | A check is running |
| `●` (pulsing) | Online | The SSH port answered. The details show the address that answered, or "via alias" |
| `○` | Offline | No address answered. Each connection attempt waits up to 3 seconds; a refused connection or a name that doesn't resolve also counts as offline |
| `◇` | Can't check | SSH could not resolve the alias, the alias uses `ProxyJump` or `ProxyCommand`, an added or edited alias waits for **R**, or the check itself failed |
| `×` | Alias not found | The alias was in your SSH config at an earlier check and is gone now; see [Renamed aliases](#renamed-aliases) |

Workbench checks at startup, when you press **R**, and every 30 seconds. A
check looks up the machine's host name if it has one, then opens a TCP
connection to its SSH port and closes it at once: it sends nothing, logs in
nowhere and uses no ping. Checks run in the background, so the screen and
quitting never wait for them.

For an alias, Workbench asks `ssh -G` which host and port the alias uses, at
startup and on **R** only. `ssh -G` reads your whole SSH config, including any
`Match exec` lines that run commands, so the 30-second timer reuses the last
answer. The details show "via alias" rather than the host.

| Timing rule | Why |
| --- | --- |
| **R** stays dimmed until the alias checks of the last startup or **R** have all reported | It never starts a second set of `ssh -G` runs beside them |
| A 30-second check waits for any check still running | A slow check still shows its result |

The symbols turn and pulse only while animations are on; set
`TEXTUAL_ANIMATIONS=none` to keep them still.

## Renamed aliases

Workbench remembers the `Host` names it saw at each startup and **R**, and
where each alias machine's alias pointed. When an alias that was in your SSH
config is gone, the machine shows **Alias not found** and **C** is hidden for
it, so a connect never goes somewhere you didn't choose. Workbench runs
neither `ssh -G` nor a status check for it.

| Situation | What to do |
| --- | --- |
| Exactly one `Host` name added since the alias was last listed points at the same host, user and port, and no other missing alias matches it | The details say "Looks like old became new. Press U to update." **U** saves the selected machine with the new alias. If the file has comments or hand formatting, the first **U** says they will be dropped and the second saves |
| No such offer | Fix your SSH config and press **R**, or press **E** and save the machine. Saving from the form keeps or changes its alias and clears Alias not found, for example after you moved the alias into a pattern on purpose |

Workbench checks again at each startup and **R**, so an offer can appear later,
for example once a second matching name is gone. An alias that is not a
literal `Host` name, for example one matched by `Host *.example`, still
connects; the details mark it "not in your SSH config".

This memory is a state file next to the machine file, one per computer:
`machines.state.<computer>.json` for `machines.toml`. A machine file in a
synced folder therefore gets one state file per computer, and each computer
keeps its own. The file holds the `Host` names and, for each alias, the host,
user and port `ssh -G` resolved; no passwords or keys. Workbench writes it
only when the machine file exists. Deleting it is safe: Workbench then forgets
which aliases existed until the next startup or **R**.

## Key login

**K** sets up key login for the selected machine in three steps, all in the
terminal Workbench hands over, as for Connect. Workbench never sees a password
or passphrase: SSH and `ssh-keygen` ask for them.

1. **Pick a key.** A direct machine with a `key` uses it. Otherwise the list
   shows the public keys (`.pub` files) in your SSH folder and **Create a new
   key**, an Ed25519 key named for the machine, such as `id_ed25519_box`. For
   an alias, the keys its SSH config offers come first. Choose the target
   system too: Linux, macOS or other POSIX, or Windows (OpenSSH Server).
   Enter starts; Escape cancels.
2. **Install it.** SSH logs in, asking for the account's password if needed,
   and runs one fixed command that adds the public key once:

   | Target | Where the key goes |
   | --- | --- |
   | POSIX | `~/.ssh/authorized_keys`, with the folder at `700` and the file at `600` |
   | Windows, administrator | `C:\ProgramData\ssh\administrators_authorized_keys`, which may grant access only to SYSTEM and Administrators (sshd ignores it otherwise) |
   | Windows, other accounts | `%USERPROFILE%\.ssh\authorized_keys` |

   On Windows the command starts PowerShell itself, because the default remote
   shell is cmd.exe. cmd.exe limits the command's length, so Workbench refuses
   an RSA key larger than about 6000 bits before connecting; Ed25519 keys and
   4096-bit RSA keys fit.
3. **Test it.** SSH logs in once more allowing only public-key authentication
   and runs `exit`. Workbench reports "Key login works." or what failed. A key
   with a passphrase works: SSH asks for it.

What to know about the result:

| Case | Behavior |
| --- | --- |
| Another key passes the test | The test can pass with another key SSH offers: any key `ssh <alias>` would use, or one named in a `Host` entry that matches a direct machine's address. When the alias's config doesn't name the key you picked, a passing test says SSH may have used another key |
| Ctrl+C | Stops the setup: Workbench reports it as interrupted, whatever the tool's exit status, and starts no later step |
| Ctrl+C at ssh-keygen's passphrase prompt on Windows | That prompt takes Ctrl+C as a key, so Workbench never sees it; ssh-keygen then exits 255, which shows as that status. SSH's own password and passphrase prompts have not been checked |
| Direct machine | The chosen key is saved as its `key` once the login test passes |
| Alias machine | Its SSH config decides its keys, and Workbench never edits that config: when you pick a key the alias doesn't name, Workbench shows the `IdentityFile` line to add under its `Host` entry |

Workbench reads only `.pub` files and never opens a private key. To type a
passphrase once per session instead of at every login, load the key into
ssh-agent. On Windows the agent service is disabled by default; in an elevated
PowerShell:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519_box
```

## Exported aliases

A direct machine can also be exported, so `ssh <id>` works in any terminal, in
scripts and for coding agents, not only inside Workbench. Tick **Export as an
SSH alias** in the form (or set `export_alias = true`); it is off by default.

Workbench then writes its own file, `ssh-workbench.config`, in your SSH folder
and rewrites it from the machine file whenever Workbench saves that file, so a
hand edit of `export_alias` takes effect at the next save. The file names the
machine file it comes from; another machine file, opened with `--config`,
can't overwrite it and says so when it has exports of its own. Each exported
machine becomes one block:

```text
Host box
    HostName 192.0.2.60
    User dev
    Port 2222
    HostKeyAlias box
    IdentityFile "~/.ssh/id_ed25519_box"
    IdentitiesOnly yes
```

`HostName` is the first address, and `HostKeyAlias` is the ID, as for Connect,
so both use the same host key. `User`, `Port` and the key appear when the
machine has them; the key path is quoted, with `/` for `\`. On Linux and macOS
the file is readable and writable only by you, as SSH requires. Inside
Workbench, **C** still connects directly.

SSH reads that file only once your own SSH config includes it, with one line
before any `Host` or `Match` block:

```text
Include ssh-workbench.config
```

After you save an exported machine, Workbench shows this line and asks:

| Answer | Effect |
| --- | --- |
| **Y** | Copies your config to `config.ssh-workbench.bak`, then adds only that line at the top and changes no other byte; a missing config is created with the line |
| **N** | Changes nothing. Workbench doesn't ask again until you restart it |

If your config is a link, as dotfile managers make it, or read-only, Workbench
changes nothing and shows the line for you to add yourself. It doesn't ask
when saving the generated file failed. The form refuses to export an ID that
your own SSH config already names as a `Host`, because SSH would use
Workbench's entry first.

## Opening links

**O** passes the selected machine's link to the system: the default browser on
Windows, or `gio open` on a Linux desktop where `DISPLAY` or `WAYLAND_DISPLAY`
is set. With several links, O shows a list: Enter opens the highlighted one and
Escape cancels.

"browser request accepted" means the system took the request, not that the
page loaded. The browser opens on the machine running Workbench, which over a
remote terminal may not be the one in front of you. One request can be pending
at a time, and Q still quits while it waits.

## Keys

| Key | Action |
| --- | --- |
| Up / Down | Select a machine; in the details pane, scroll |
| Tab / Shift+Tab | Move between the machine list and the details pane |
| Page Up / Page Down, Home / End | Scroll the details pane |
| C | Connect to the selected machine |
| R | Check every machine's status again, resolving aliases too |
| U | Update the selected machine's alias when Workbench offers a renamed one |
| K | Set up key login for the selected machine |
| O | Open the selected machine's link, or choose one when it has several |
| Enter / Escape | In the link list: open the highlighted link / cancel |
| A / E / X | Add a machine / edit the selected one / delete it after asking |
| Tab, Ctrl+S, Escape | In the form: next field, save, close without saving |
| Y / N | When deleting: delete / keep |
| Q or Ctrl+Q | Quit (in a form or the delete question, only Ctrl+Q) |

C, O, A, E, X, K, R and Q also appear in the footer and can be clicked; O is
labelled Link and R Check there. Keys that can't act right now are dimmed or
hidden:

| Key | Dimmed or hidden when |
| --- | --- |
| C | Hidden for a machine whose alias is not found; U appears in its place when Workbench offers a rename |
| K | Dimmed for a machine whose alias is not found, and for a direct machine without a key when Workbench has no file location |
| C, O, E, X, K | Dimmed when nothing is selected |
| O | Dimmed when the machine has no links |
| A, E, X | Dimmed when Workbench has no file location |
| R | Dimmed while the alias checks of the last startup or R are still running |

Startup, selection and Enter in the machine list never connect, open or change
anything; the status checks are the only thing that starts on its own.

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
| `Could not save the machine file: permission denied.` | The file or its folder is read-only, or another program holds the file open. The machine file was not changed |
| `The machine file changed outside Workbench and was reloaded. ...` | Another program changed the file. Check the reloaded list, then save again |
| `The machine file changed outside Workbench and now has an error: ...` | Fix the file's error, then save again |
| `Cannot hand off this terminal. ...` | Start Workbench from a local terminal |
| `browser unavailable. ...` | Links work only on Windows and on Linux desktops with `gio` |
| `ssh-workbench` not found after installing | Run `uv tool update-shell` and open a new terminal |

## Privacy

| Area | What Workbench does |
| --- | --- |
| Files it writes | Its machine file, the `.bak` copy and the `machines.state.<computer>.json` state file. For exported machines, `ssh-workbench.config` in your SSH folder and, only after you press **Y**, one `Include` line in your SSH config, keeping a copy first |
| SSH config | To suggest aliases it reads only the `Host` and `Include` lines. At startup and on **R** it also runs `ssh -G` for each alias, and for new `Host` names that could replace a missing alias; **K** runs it for the alias it sets up. SSH then evaluates your whole SSH config, including any `Match exec` commands, and Workbench reads only the host, user, port, key and proxy settings it prints |
| Keys | **K** reads the `.pub` files in your SSH folder, and the one next to each key an alias's config names. It never opens a private key |
| Remote commands | **K** runs two fixed commands on the machine, in the terminal it hands over: the key install, and `exit` for the login test |
| Network | Its own traffic is the status checks: DNS lookups for host names, and one TCP connection to each checked address's SSH port, closed at once without sending anything. Everything else comes from the SSH sessions and browser requests you start |
| Never | Changes any other line of your SSH config, reads `known_hosts`, stores credentials, changes host-key settings, collects telemetry or needs an AI service |
