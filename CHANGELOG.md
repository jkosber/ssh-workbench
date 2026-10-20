# Changelog

Changes by release, newest first. Version numbers follow the policy in
[CONTRIBUTING](CONTRIBUTING.md#versions-and-deliberate-releases).

## Unreleased

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
