# Changelog

Changes by release, newest first. Version numbers follow the policy in
[CONTRIBUTING](CONTRIBUTING.md#versions-and-deliberate-releases).

## Unreleased

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
- Workbench keeps a state file per computer next to the machine file,
  `machines.state.<computer>.json`, with the `Host` names it saw and where
  each alias pointed. Deleting it is safe.

### Security

- Every SSH command puts `--` before the destination, and every value is
  rechecked just before launch.
- Direct machines use `HostKeyAlias` with the machine's ID, so you confirm one
  host key per machine whichever address is used. Keys already recorded under
  an address don't carry over, so the first connection asks once.
- A machine's key is offered with `IdentitiesOnly`, so SSH tries no other key.
  Workbench passes the key's path to SSH and never opens the file.
- A save or delete never overwrites a machine file that changed on disk since
  Workbench loaded it; it reloads the list and keeps your unsaved change so you
  can try again. A read-only machine file is never replaced.
- Workbench's own network traffic is the status checks: DNS lookups for host
  names and one TCP connection to each checked address's SSH port, closed
  without sending anything. `ssh -G` resolves aliases at startup and on R
  only, never on the timer; it evaluates your whole SSH config, including
  `Match exec` lines.
- To suggest aliases, only `Host` and `Include` lines of your SSH config are
  read; Workbench never
  opens an included file named like a key, `known_hosts` or `authorized_keys`,
  and never changes the config.

### Development

- Builds use `uv_build` 0.13 and CI uses uv 0.13.3, which removes the build
  warning about the backend's version range.
- Tests, fixtures and the package check share one list of guarded process,
  network and browser entry points. The installed-wheel checks moved from
  strings in `scripts/check_package.py` into `scripts/package_smoke.py`.

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
