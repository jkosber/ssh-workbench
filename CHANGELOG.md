# Changelog

Changes by release, newest first. Version numbers follow the policy in
[the workflow guide](docs/workflow.md#versions).

## Unreleased

### Changed

- The GitHub repository is public, so installing from it needs no GitHub
  account or invitation.
- Opening links is tested on a real Linux desktop. The manual checks cover
  Ghostty on Linux as well as Windows Terminal, and `scripts/check_terminal.py`
  runs on Linux.

### Fixed

- Letter keys work with Caps Lock on or typed as capitals: each does what its
  lowercase key does, Y and N in the delete and Include questions included.
  The footer still shows them in lowercase.
- Selecting another machine shows its details from the top at once. Before,
  the first frame could show them scrolled down, as the previous machine was.

## 0.3.3 - 2026-10-24

Key setup follow-ups: a config that names a key by its `.pub` counts as
naming that key, the key picker uses the whole height so a note and a "Not
listed" line fit at 60x20, and an administrator's Windows install reports
its result only after setting the key file's permissions, with errors on one
line. Tagged privately.

### Fixed

- A config that names the public key (`IdentityFile ~/.ssh/x.pub`, as some
  SSH agents' guides suggest) counts as naming key x: K lists it as the key
  the config offers, without a "doesn't name this key" note. SSH uses such
  a line only through an agent that holds the key, so a failed login test
  says so and gives the `IdentityFile` line for the key itself.
- The key picker uses the whole terminal height before it scrolls, so at
  60x20 a note and a "Not listed" line fit.
- On a Windows target, an administrator's install says the key is installed
  only once the key file's permissions are set; if that step fails, only the
  error shows. An error message with line breaks prints on one line.

## 0.3.2 - 2026-10-24

Key setup fixes: K no longer opens an empty key list and names keys it can't
offer, Ctrl+C says which step it stopped, and a Windows install error prints
as plain text. Tagged privately.

### Fixed

- K no longer opens an empty key list: with no key to offer it says so. A
  machine's own key whose `.pub` file is missing or not valid is reported when
  K is pressed, before anything is handed over.
- For an alias, keys its SSH config offers that have no valid `.pub` file are
  named under the key list as "Not listed", instead of being left out
  silently.
- Ctrl+C during key setup says which step it stopped: while creating the key,
  before the install or during the install.
- An error in the Windows install script now prints as plain text, "SSH
  Workbench: the install stopped with an error: ...", instead of a block of
  CLIXML.

### Development

- `scripts/check_shells.py` checks that the POSIX install command works the
  same from bash, dash, zsh, fish and tcsh.

## 0.3.1 - 2026-10-23

Status and alias fixes: saves keep the alias checks in progress, `Match exec`
commands stay off the screen, and K's key list no longer opens after you
connect, open a form or select another machine. Tagged privately.

### Fixed

- Saving a machine while Workbench was still checking aliases at startup or
  after R no longer throws those checks away: alias machines show their
  status, Alias not found where it applies, and the state file is written,
  without pressing R again. Keeping a missing alias with a save during R
  also sticks.
- A `Match exec` command in the SSH config can no longer draw over
  Workbench's screen: `ssh -G` runs without the terminal.
- When reading the SSH config fails, aliases that were already missing at the
  last run stay Alias not found and are not checked.
- No state file is written next to a machine file deleted while Workbench
  runs.
- K's key list opens only if nothing happened since K: connecting, opening a
  form or selecting another machine first cancels it, and K again while it
  waits says it is still looking up the alias.

## 0.3.0 - 2026-10-23

A new look, a status header and a layout that follows the terminal's size,
with rewritten documentation. Tagged privately.

### Changed

- A new look: Workbench's own color theme, rounded panes and dialogs, and a
  header that counts machines by status. Every status keeps its symbol and
  word, so nothing depends on color.
- The details show one row per field, so a machine's key and links fit at
  80x24 without scrolling. The status takes its color.
- The layout follows the terminal's size: under 60 columns the list sits above
  the details and the footer wraps onto two rows; from 110 columns each row
  shows where the machine connects; under 60 columns or 20 rows the help line
  hides; under 20 rows the link result takes two rows instead of three.
- The no-file screen points to the user guide for the file's format.

### Documentation

- The README is now a short landing page; the full reference moved to
  [the user guide](docs/guide.md). New guides cover
  [the workflow](docs/workflow.md) and [testing](docs/testing.md), and the
  roadmap and validation log for Tasks 1-18 moved to
  [the archive](docs/archive/).

## 0.2.2 - 2026-10-21

Ctrl+C, large-key and status fixes, and security updates for development and
CI. Tagged privately.

### Security

- CI uses uv 0.13.4, and builds require `uv_build` 0.13.4 or later. uv 0.13.4
  removes emSign ECC Root CA - G3 from uv's bundled CA certificates after that
  root's intermediate keys were compromised
  ([GHSA-hq85-5cpj-mr62](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62)).
- Development and CI use Python 3.14.8, which fixes six CVEs in `ssl`,
  `zipfile`, `tarfile`, `urllib.request` and stringprep, and updates the
  OpenSSL bundled on Windows and macOS to 3.5.9
  ([release notes](https://www.python.org/downloads/release/python-3148/)).

### Fixed

- Ctrl+C during key setup reads as interrupted even when the tool then exits
  0, as Windows ssh can while it connects, so K no longer says "Key login
  works." or saves a direct machine's key after Ctrl+C. Workbench counts the
  Ctrl+C itself, and no later step starts. On Windows, ssh-keygen's
  passphrase prompt takes Ctrl+C as a key and exits 255, which still shows as
  that status; SSH's own prompts have not been checked.
- K refuses a key too large for the Windows install command, an RSA key over
  about 6000 bits, before it connects, instead of failing after the password
  prompt.
- A 30-second status check no longer replaces a check still running, so a
  machine whose check takes longer than 30 seconds leaves Checking. R stays
  dimmed until the alias checks of the last startup or R have reported, so
  pressing it repeatedly no longer starts a second set of `ssh -G` processes
  beside the first.

## 0.2.1 - 2026-10-21

Key setup fixes from use on real machines. Tagged privately.

### Fixed

- K on a Windows target no longer prints PowerShell's "Preparing modules for
  first use." progress record as XML after "key installed.".
- A commented-out copy of the key in `authorized_keys` no longer counts as
  installed; K adds the key.
- Ctrl+C during key setup reads "Key setup interrupted.", or "The key was
  installed, but the login test was interrupted.", instead of an exit status
  such as 4294967295. On Windows, ssh-keygen exits 255 after Ctrl+C at its
  passphrase prompt, which still shows as that status, and ssh can exit 0,
  which reads as success.
- When an alias's login test passes with a key its SSH config doesn't name, the
  result says SSH may have used another key and gives the `IdentityFile` line
  to add.
- A direct machine's new key is saved only after its login test passes, so a
  key that doesn't work no longer becomes the only key Connect offers.

## 0.2.0 - 2026-10-21

Machines replace projects: add, edit and delete them in Workbench, with live
status, key login setup and exported aliases. Tagged privately.

### Added

- Machines replace projects. Each machine connects through an SSH `alias`, or
  directly by `addresses` with an optional `user`, `port` and per-machine `key`,
  so it needs no SSH config. Schema 2 files hold a `machines` array; the README
  describes every field.
- Machines can have any number of named web links. O opens the only link, or a
  list to choose from when there are several; Escape closes the list.
- The details pane shows how each machine connects, and status lines name the
  machine they belong to.
- A adds, E edits and X deletes machines in a form that checks every value with
  the file's own rules. The first save creates the machine file and its folder.
- The add form suggests the `Host` names from your SSH config, following its
  `Include` lines.
- Live status: each machine shows Checking, Online (with the address that
  answered), Offline or Can't check, as a symbol and a word with color on top.
  Checks run at startup, on R and every 30 seconds in the background.
- C on a machine with addresses uses the first address the latest check
  found online.
- Renamed aliases are caught: an alias machine whose `Host` entry is gone
  shows Alias not found and can't connect. When exactly one new `Host` name
  points at the same host, user and port, U updates the machine. Aliases that
  are not literal `Host` names are marked "not in your SSH config".
- K sets up key login: pick a key from the SSH folder or create one with
  `ssh-keygen`, install its public half on a POSIX or Windows OpenSSH target
  with one fixed command, and confirm key-only login. A direct machine saves
  the key; for an alias Workbench shows the `IdentityFile` line to add.
- Exported aliases: a direct machine with `export_alias = true` (a
  checkbox in the form) gets a `Host <id>` block in Workbench's own
  `ssh-workbench.config`, so `ssh <id>` works in any terminal. After a save,
  Workbench offers to add `Include ssh-workbench.config` to your SSH config.

### Changed

- The default file is now `machines.toml` in the same folder; `projects.toml`
  is no longer read. Rename it: schema 1 files still load, with `repository`
  and `documentation` as links named "Repository" and "Documentation".
- R and D are replaced by O. C and O are dimmed when nothing is selected, and O
  when a machine has no links.
- A folder given with `--config` or found at the default path is reported as
  "expected a file, got a directory", instead of "permission denied" or the
  start screen.
- `--help` prints the default path on its own line, and the empty-file screen
  no longer suggests restarting with `--config`.
- Workbench now writes its machine file when you add, edit or delete a machine.
  Saving keeps the previous file as `machines.toml.bak`, replaces the file in
  one step, and drops comments and hand formatting after asking once.
- R is labelled Check in the footer, so eight keys fit 60 columns.
- Workbench keeps a state file per computer next to the machine file,
  `machines.state.<computer>.json`, with the `Host` names it saw and where
  each alias pointed. Deleting it is safe.

### Security

- Every SSH command puts `--` before the destination, and every value is
  rechecked just before launch.
- Direct machines use `HostKeyAlias` with the machine's ID, so you confirm one
  host key per machine whichever address is used. Keys already recorded under
  an address don't carry over, so the first connection asks once.
- A machine's key is offered with `IdentitiesOnly`, so SSH skips the other
  keys in your agent and the default keys.
  Workbench passes the key's path to SSH and never opens the file.
- A save or delete never overwrites a machine file that changed on disk since
  Workbench loaded it; it reloads the list and keeps your unsaved change so you
  can try again. A read-only machine file is never replaced.
- Workbench's own network traffic is the status checks: DNS lookups for host
  names and one TCP connection to each checked address's SSH port, closed
  without sending anything. `ssh -G` resolves aliases at startup and on R
  only, never on the timer; it evaluates your whole SSH config, including
  `Match exec` lines.
- Workbench changes your SSH config only after you press Y, and only by
  adding one `Include` line at the top, after keeping a copy as
  `config.ssh-workbench.bak`. Values in its generated file are quoted or
  refused.
- Key setup runs two fixed remote commands in the handed-off terminal, the
  install and `exit`; their only variable part is a public key line checked
  for type, base64 and a safe comment. Workbench reads only `.pub` files and
  never opens a private key.
- To suggest aliases, only `Host` and `Include` lines of your SSH config are
  read; Workbench never
  opens an included file named like a key, `known_hosts` or `authorized_keys`,
  and changes the config only by the one confirmed `Include` line.

### Development

- Builds use `uv_build` 0.13 and CI uses uv 0.13.3, which removes the build
  warning about the backend's version range.
- Tests, fixtures and the package check share one list of guarded process,
  network and browser entry points. The installed-wheel checks moved from
  strings in `scripts/check_package.py` into `scripts/package_smoke.py`.

### Known limitations

- Tested on Windows 11 in Windows Terminal and on Linux Mint 22.3 in a
  terminal reached over SSH; CI runs the tests on Ubuntu. macOS is untested
  and cannot open links, and links on a Linux desktop are untested.
- Your SSH config still applies to a direct machine's address. A matching
  `Host` entry with `StrictHostKeyChecking yes` makes the first connection
  fail instead of asking; the README shows the one-time fix.
- The key login test can pass with another key SSH offers: any key
  `ssh <alias>` would use, or one named in a `Host` entry that matches a direct
  machine's address.
- Requires Python 3.14 or later, which uv installs when needed.

## 0.1.0 - 2026-10-20

First usable release, tagged privately.

### Added

- A project list read from a TOML file: the per-user default file, or another
  file given with `--config PATH`. UTF-8 with or without a byte-order mark is
  accepted. Configuration errors exit with status 2 before the screen starts and
  never print the file's path or values.
- A details pane with each project's ID, name, SSH alias and optional repository
  and documentation links, shown literally with control characters escaped.
- C connects to the selected project through the system OpenSSH client in the
  same terminal, then returns to the list with the same project selected and the
  exit status shown.
- R and D open the repository and documentation links in the system browser on
  Windows and on Linux desktops with GIO.
- Keyboard navigation, clickable footer actions, Q and Ctrl+Q to quit, and
  `--help` and `--version`. `--help` shows where the default file lives.

### Security

- The alias reaches SSH as one argument without a shell, and is rechecked just
  before launch. Authentication and host-key checks stay with OpenSSH.
- On Windows, only absolute `PATH` entries supply `ssh.exe`, so a copy in the
  current folder never runs.
- Links are rechecked before opening, passed on unchanged, and never fall back
  to a terminal browser.

### Known limitations

- Tested on Windows 11 in Windows Terminal. Linux is covered by automated tests
  only. macOS is untested and cannot open links.
- The projects file is edited by hand, and changes take effect on restart.
- Requires Python 3.14 or later, which uv installs when needed.
