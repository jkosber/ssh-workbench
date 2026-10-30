# Validation log

Evidence that automated checks cannot give: runs in a real terminal, checks
against real machines, and what a person saw. CI results, merges and tags live
on GitHub and are not copied here. Evidence for Tasks 1-18 is in
[the archive](archive/validation-tasks-1-18.md).

## How to add an entry

One section per task, newest first, written while the task is open:

```markdown
## Task N: short title, YYYY-MM-DD

Windows 11, Windows Terminal 80x24, Python 3.14.8, Textual 8.2.8.

| Check | Observed |
| --- | --- |
| What was run or done | What actually happened |

Not checked: what was left out, and why.
```

| Rule | Detail |
| --- | --- |
| Observed, not expected | Write what happened. A check that was planned but not run goes under "Not checked" |
| Real targets | Name only that Jadon approved the target; never its host name, alias, address or account |
| Screenshots | Only from fictional data; keep the rest in ignored `.local/` |
| Automated checks | One line with the test count is enough; CI keeps the rest |

## Linux desktop checks, 2026-10-30

Arch Linux (Omarchy 4.0.6, Hyprland, Wayland), Ghostty 1.4.0, 80x24 at start,
Python 3.14.8, Textual 8.2.8, PowerShell 7.6.9 for the Windows-script tests.
A coding agent drove the checks: it sent keys with wtype, set window sizes in
pixels with Hyprland's resize dispatcher and read grim screenshots. Jadon did
not watch them. `NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at empty ignored folders. The fixtures ran in
a second window at 83x24.

| Check | Observed |
| --- | --- |
| `uv run --locked pytest` without PowerShell | 12 failed, 1112 passed; every failure was `AssertionError: PowerShell is needed to run the Windows script` |
| Ruff check and format, `uv run --locked pytest` with `pwsh` 7.6.9, `uv build`, `check_package.py` | Passed; 1124 passed. The package check warned `Failed to hardlink files; falling back to full copy`: the temporary folder and uv's cache are on different file systems |
| `scripts/check_shells.py` piped to `sh -s`, locally | bash PASS; dash, zsh, fish and tcsh are not installed, so it exited 1 |
| Smoke check on `examples/machines.example.toml` | Ghostty opened the 80x24 request at 77 columns (`stty size` answered 24 77). The list, details and footer drew. Garden demo read "Can't check: SSH could not resolve the alias" (the SSH folder is empty); Studio box read Offline. With Up, Down, Tab, Page Up and Page Down the selection and details followed, and Tab moved focus to the details pane; R showed Checking, then Offline and Can't check. The run wrote `examples/machines.example.state.<computer>.json` beside the example file |
| Quit | Q gave back the shell prompt, `echo hello` echoed, Up recalled the line and the app's status was 0. Ctrl+Q on a second run gave back the prompt and `stty size` answered 24 77 |
| Resizes, set in pixels | At 56 and 59 columns the list moved above the details, the footer took two rows and the header counts shortened to "2 ◯1 ◇1". At 111 columns each list row showed where it connects ("garden-demo-host", "studio-box.example…"). At 19 rows the help line hid and the footer stayed. E open, a resize to 56 columns, then Escape: the browser behind the form had the narrow layout when the form closed |
| Ghostty's narrowest window | About 19 columns (139 logical px wide); the shell kept working |
| `scripts/check_links.py` 1 | Accepted, from the list and from the details: "[b]Only[/b] link browser request accepted. Machine 1: fixture-accepted", with `[b]` kept as text. Failed and error both read "browser request failed. Check the environment's browser setup and retry." with no private marker. The long message wrapped inside the details pane and the status area |
| `check_links.py` 2 to 4 | No links: "o Link" dimmed in the footer and O changed nothing. Picker: O opened "Open a link" with both links; Enter opened the first, Down then Enter the second; Escape closed it with the same selection and focus. Blocked: a second O read "browser request still pending. Wait or Q to quit."; Up and Tab worked; Q exited at once, status 0 |
| `scripts/check_keys.py` | K on Box listed id_a.pub, id_lab.pub and "Create a new key: id_ed25519_box", then offered Linux/macOS/POSIX or Windows as the target system. With every step at status 0, the keygen, install (the POSIX command, 564 characters) and test children each took `return`; the result read "Key login works. The key is saved as this machine's key." and the Key field showed the working folder's `ssh/id_ed25519_box` |
| `check_keys.py --test-status 255` | "The key was installed, but key-only login failed (SSH exited with status 255). The key was not saved as this machine's key."; Key stayed Not set |
| `check_keys.py`, Ctrl+C at the install child | "Key setup interrupted during the install; login was not tested."; no test child ran. Q gave back the shell prompt after each of the three runs |
| `scripts/check_terminal.py` as on `main` | Every C read "SSH exited with status 1". `.venv/bin/python` is a symlink on Linux and the fixture resolved it, so the child ran under `/usr/bin/python3.14` and could not import `ssh_workbench`. The fix starts the child with `sys.executable` |
| `check_terminal.py` 1 to 3, after the fix | 1: after C the child printed `terminal stdin/stdout/stderr: [True, True, True]` and echoed input; `return` gave "SSH exited with status 0. Machine 1: fixture-zero", the same machine selected, the list focused, Up and Down working. 2: Tab, C, `return` gave "SSH exited with status 7. Check the SSH client's message and alias; C retries. Machine 2: fixture-seven", and Down then changed the selection. 3: Ctrl+C gave "SSH exited with status 130 ... Machine 3: fixture-interrupt" |
| `check_terminal.py` 4 to 6, after the fix | 4: at each of two Ctrl+C the child printed "Child still owns the terminal; type return to finish." and it echoed `still-here`; `return` gave status 0 for machine 4. 5: each simulated entry, pressed twice, kept the selection: "SSH not found. Install OpenSSH and add it to PATH. Machine 5"; "Could not start SSH. Check its installation and executable permissions. Machine 6"; "SSH interrupted. Press C to retry or Q to quit. Machine 7". 6: after Q, and after Ctrl+Q on a second run, the shell prompt came back, `stty size` answered and `echo` printed |
| Real link, a URL Jadon approved: O on an ignored copy of the example file whose Documentation link is `https://example.com/` | The status read "Documentation browser request accepted."; Chromium, the desktop's default browser, opened a new window titled "Example Domain" on the same workspace, showing example.com |

Not checked: real SSH targets (none approved); `check_shells.py` beyond bash
(dash, zsh, fish and tcsh are not installed); macOS; Windows Terminal, which
is unchanged since the earlier entries; the Windows install script against a
Windows host.

## Package check bytecode, 2026-10-28

Windows 11, uv 0.13.6, Python 3.14.8, Textual 8.2.8. The timings come from a
throwaway script that repeats the package check's install in a fresh
environment, then runs the `loader` child three times.

| Check | Observed |
| --- | --- |
| Cause, from PR #23's failed Windows attempt | After the install, help, version and the missing-file check took about 4.8 s; the `loader` child, the first to import Textual, then timed out after 10 s. On 2026-10-24, Windows runs finished all the children in 8-11 s |
| `loader` child after the default install, two environments | First run 1.20 s and 0.77 s; later runs 0.38-0.40 s |
| `loader` child with the dependencies compiled, two environments | First run 0.43 s both times; later runs 0.37-0.39 s. The install took about 0.7 s instead of 0.3 s |
| `_PROBE = "\d"` added to `config.py` in a throwaway worktree, then `uv build` and `check_package.py` | `main` and this branch both failed with `Installed wheel CLI check failed: --help`. An earlier commit of this branch that also compiled the wheel passed, hiding the warning |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1124 passed |

Not checked: a cold Windows runner. A timeout like PR #23's cannot be
reproduced on demand; the pull request's CI shows only the new timings.

## Repository made public, 2026-10-24

Windows 11, uv 0.13.4, Git for Windows. Scans used `gh` signed in as Jadon;
the checks after the change used `curl`, `git` and `uv` without credentials.
Jadon approved the change after the checks before it.

| Check | Observed |
| --- | --- |
| Secrets in every commit reachable from a branch, a tag or a pull request | No private keys or GitHub tokens: 304 commits before the change, and 311 when rechecked during PR #34 |
| Personal details in history | No home-folder paths or personal email. Three docs commits from 2026-10-21 name a Windows computer and an SSH alias, without addresses; Jadon chose to keep them rather than rewrite history |
| Addresses in fixtures and examples | Jadon confirmed they are made up |
| Pull requests | The text and comments of all 33 were clean; every pull request's head is in `main` or a tag, and none was force-pushed |
| Repository contents beyond Git | No Actions artifacts, releases, secrets or environments; the workflow token is read-only |
| After the change | `gh repo view` reported `PUBLIC`; the page and the API answered without signing in; `git ls-remote` with no credential helper listed `v0.3.3` |
| Install as anyone | `uv tool install git+https://github.com/jkosber/ssh-workbench@v0.3.3`, with Git's global and system configuration and credential helpers switched off, installed into ignored folders; `ssh-workbench --version` then printed `ssh-workbench 0.3.3` |

Not checked: commits that exist on GitHub but no longer belong to any branch,
tag or pull request, which no listing shows.

## Release 0.3.3, 2026-10-24

Windows 11, Windows Terminal, Python 3.14.8, Textual 8.2.8. The built wheel
installed as a tool into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`),
leaving Jadon's installed 0.3.2 alone. An owned window with `NO_COLOR`
removed and `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointing
at empty ignored folders; a copy of the example machine file. No SSH
connection and no browser.

| Check | Observed |
| --- | --- |
| Installed tool | Before the release folder was on `PATH`, Jadon's own tool printed `ssh-workbench 0.3.2`. Then `ssh-workbench` resolved to the ignored tool folder and `--version` printed `ssh-workbench 0.3.3` |
| 80x24 | The header read `2 machines   ○ 1 offline   ◇ 1 can't check`; Garden demo read `◇ Can't check: SSH could not resolve the alias` (the empty SSH folder has no config file, so `ssh -G -F` fails), with the help line and the footer's eight keys. Down showed Studio box's details and Up Garden demo's again; Tab, Page Down and Page Up left the details as they were, as they fit without scrolling; R showed `◐ 1 checking` |
| 50x24 | The list above the details, the header as symbols (`2  ◐1 ◇1` during R's check), the footer on two rows, the help line hidden |
| 120x30 | Each row showed its alias or address on the right |
| 80x18 | The help line hidden, side by side |
| Form during a resize | E at 80x24, then 52x22: the edit form stayed open over the browser; after Escape, the browser was stacked with the footer on two rows |
| Quit | Q and, in a second run, Ctrl+Q exited with status 0 and returned to a working prompt |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1122 passed |

Not checked: Linux and macOS terminals; which pane Tab focused (only the
screen text was read); scrolling the details, which fit at 80x24; whether
typed input echoed after each exit (each snapshot follows a `cls`); the
install from the tag, which needs the tag.

## Task 23: key setup follow-ups, 2026-10-24

Windows 11, Windows Terminal, Python 3.14.8, Textual 8.2.8. An owned window
with `NO_COLOR` removed and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointing at ignored folders, except where the real
target needed the real SSH config. Jadon approved the Windows target by name
on 2026-10-24.

| Check | Observed |
| --- | --- |
| Command length, measured before the change | The script could change by about -10 to +38 characters and keep the three length tests passing. Printing the result last cost +22; folding error lines another +23, more than the room left, so the one-use `$sidType` variable was inlined. With Ruff's line length, the 6144-bit key with a 40-character comment comes to 8150 of 8156 characters |
| `check_keys.py` at 60x20 | Garden's picker with the configured key highlighted: the list, "Not listed: id_work, which your SSH config offers, has no valid .pub file.", both target systems and the two-row help line, inside the box. With `id_a.pub` highlighted, its note named the session folder in full (five rows): the picker took the whole height, covering the header row, and still showed everything down to "Escape: cancel" |
| K on the approved Windows target | Windows OpenSSH with an administrator account, the branch's Workbench with the real SSH config. Status Online; the picker's first choice was the key the config offers, with no "Not listed" line. Windows target, Enter: "the key was already installed.", which the script now prints only after the ACL step and its read-back with the inlined type, then "testing key-only login." and "Key login works.", with no prompt and no CLIXML. `administrators_authorized_keys` was copied first; afterwards its hash, ACL (SDDL) and size matched, and the copy was deleted (separate SSH commands, results kept with the session evidence). A read-only check afterwards: the account passes the script's own administrator test over SSH |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1122 passed |

Not checked: the administrator branch's failure path on a real target, which
the tests cover with the ACL step replaced by a `throw`; a real agent that
holds a key named by its `.pub`.

## Release 0.3.2, 2026-10-24

Windows 11, Windows Terminal, Python 3.14.8, Textual 8.2.8. The built wheel
installed as a tool into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`),
leaving Jadon's installed 0.3.1 alone. An owned window with `NO_COLOR`
removed and `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointing
at empty ignored folders; a copy of the example machine file. No SSH
connection and no browser.

| Check | Observed |
| --- | --- |
| Installed tool | Before the release folder was on `PATH`, Jadon's own tool printed `ssh-workbench 0.3.1`. Then `ssh-workbench` resolved to the ignored tool folder and `--version` printed `ssh-workbench 0.3.2` |
| 80x24 | The header read `2 machines   ○ 1 offline   ◇ 1 can't check`; Garden demo read `◇ Can't check: SSH could not resolve the alias` (the empty SSH folder has no config file, so `ssh -G -F` fails), with the help line and the footer's eight keys. Down showed Studio box's details and Up Garden demo's again; Tab, Page Down and Page Up left the details as they were, as they fit without scrolling; R showed `◐ 1 checking` |
| 50x24 | The list above the details, the header as symbols (`2  ◐1 ◇1` during R's check), the footer on two rows, the help line hidden |
| 120x30 | Each row showed its alias or address on the right |
| 80x18 | The help line hidden, side by side |
| Form during a resize | E at 80x24, then 52x22: the edit form stayed open over the browser; after Escape, the browser was stacked with the footer on two rows |
| Quit | Q and, in a second run, Ctrl+Q exited with status 0 and returned to a working prompt |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1112 passed |

Not checked: Linux and macOS terminals; which pane Tab focused (only the
screen text was read); scrolling the details, which fit at 80x24; the
install from the tag, which needs the tag.

## Task 22: key setup fixes, 2026-10-24

Windows 11, Windows Terminal 80x24, Python 3.14.8, Textual 8.2.8. An owned
window with `NO_COLOR` removed and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointing at ignored folders, except where a real
target needed the real SSH config. Jadon approved the two real machines below
by name on 2026-10-24.

| Check | Observed |
| --- | --- |
| CLIXML, before the fix | A script that throws, run as `powershell -NoProfile -NonInteractive -EncodedCommand` with output redirected (as under sshd without a terminal), wrote its error to stderr as a `#< CLIXML` block; `-OutputFormat Text` made no difference. With the `trap`, the same failure printed one plain stdout line and exited 1, in Windows PowerShell 5.1 and in pwsh |
| `check_terminal.py` | Normal exit: the child saw a terminal on stdin, stdout and stderr; status 0, then Down selected the next machine. From the details pane: status 7, then Down still moved the list. Ctrl+C: status 130. SSH unavailable, start failure and launch interrupted each showed their message. Q exited with status 0 to a working prompt |
| `check_keys.py` | Box: id_a, both children answered: "Key login works. The key is saved as this machine's key." K again offered only that key; Ctrl+C at the install child: "Key setup interrupted during the install; login was not tested.", and no test child started. Garden's picker listed `id_lab.pub (your SSH config offers this)`, `id_a.pub` and Create, with "Not listed: id_work, which your SSH config offers, has no valid .pub file." below in a muted color; Ctrl+C at the keygen child: "Key setup interrupted while creating the key; nothing was installed." Q exited with status 0 |
| Login shells, on the approved Linux machine | Linux Mint 22.3, with zsh, fish and tcsh installed for this check at Jadon's request (undo: `sudo apt-get remove zsh fish tcsh`). `check_shells.py` piped to `ssh <target> sh -s`: bash 5.2.21, dash 0.5.12, zsh 5.9, fish 3.7.0 and tcsh 6.24.10 each PASS, exit 0; no temporary folder was left. The first attempt failed in dash on CRLF line ends from Windows; fixed test first |
| K on the approved Windows target | Windows OpenSSH with an administrator account and cmd.exe as its shell, the branch's Workbench with the real SSH config. Status Online; the picker's first choice was the key the config offers, with no "Not listed" line. Windows target, Enter: "the key was already installed.", "testing key-only login.", then "Key login works.", with no prompt and no CLIXML on screen, twice. `administrators_authorized_keys` was copied first; afterwards its hash, ACL (SDDL) and size matched the earlier ones, and the copy was deleted |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1112 passed |

Not checked: the trap's own error path on a real target (that would mean
breaking a real key file or its ACL); macOS's zsh, which the Linux zsh stands
in for; Linux and macOS terminals for the handoff.

## Release 0.3.1, 2026-10-23

Windows 11, Windows Terminal, Python 3.14.8, Textual 8.2.8. The built wheel
installed as a tool into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`),
leaving Jadon's installed 0.3.0 alone. An owned window with `NO_COLOR`
removed and `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointing
at empty ignored folders; a copy of the example machine file. No SSH
connection and no browser.

| Check | Observed |
| --- | --- |
| Installed tool | `ssh-workbench` resolved to the ignored tool folder; `--version` printed `ssh-workbench 0.3.1`. In a second window, before the release folder was on `PATH`, Jadon's own tool printed `ssh-workbench 0.3.0` |
| 80x24 | The header read `2 machines   ○ 1 offline   ◇ 1 can't check`; Garden demo read `◇ Can't check: SSH could not resolve the alias`, as its alias is not in the empty SSH config. Down showed Studio box's details and Up Garden demo's again; Tab, Page Down and Page Up left the details as they were, as they fit without scrolling; R showed `◐ 1 checking` |
| 50x24 | The list above the details, the header as symbols, the footer on two rows, the help line hidden |
| 120x30 | Each row showed its alias or address on the right |
| 80x18 | The help line hidden, side by side |
| Form during a resize | In the second window, E at 80x24 opened the edit form; resizing to 52x22 with it open stacked the browser behind it; Escape closed it, the browser still stacked |
| Quit | Q and, in a second run, Ctrl+Q exited with status 0 and returned to a working prompt |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1096 passed |

Not checked: Linux and macOS terminals; which pane Tab focused (only the
screen text was read); scrolling the details, which fit at 80x24; the install
from the tag, which needs the tag.

## Task 21: status and alias fixes, 2026-10-23

Windows 11, Windows Terminal 80x24, Python 3.14.8, Textual 8.2.8, Windows
OpenSSH 9.5p2 (`C:\Windows\System32\OpenSSH\ssh.exe`). An owned window with
`NO_COLOR` removed and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointing at ignored folders. The SSH folder held a
fictional config, `Match exec "ping -n 6 127.0.0.1 >NUL & echo DRAWN-OVER> CON"`
above `Host garden-demo-host` with `HostName 192.0.2.10`, so each `ssh -G`
waited about 5 s and then wrote to the console. The example's machines,
written in Workbench's own format. No SSH connection and no browser. The same
steps ran on the branch (`uv run`) and on `main` (the 0.3.0 tool from the
release check; `main` is the `v0.3.0` commit).

| Check | Branch | `main` |
| --- | --- | --- |
| Save while `ssh -G` runs: Down, E on Studio box, Ctrl+S, 1.6 s after the list drew, Garden demo still Checking | Garden demo stayed Checking, then read `○ Offline`; the header read `○ 2 offline` | Garden demo read `◇ Can't check: press R to resolve this alias` at once and kept it |
| `Match exec` writing to the console | `DRAWN-OVER` never appeared in 14 s of screen reads | `DRAWN-OVER` appeared over the list and details 4.9 s after the list drew |
| State file | Written next to the machine file | None written |
| Q | Exit status 0, working prompt | Exit status 0, working prompt |

| Check | Observed |
| --- | --- |
| Detached `ssh -G` still runs `Match exec` | With the same config, `resolve_alias("garden-demo-host")` passed `creationflags=CREATE_NO_WINDOW` and returned host `192.0.2.10`, port 22, after 5.1 s |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1095 passed |

Not checked: Linux and macOS terminals, where `start_new_session` replaces
`CREATE_NO_WINDOW` (CI's Ubuntu job checks the argument, not a real
`Match exec`); a `Match exec` command that waits for input (its input is
closed); K's late answers in a real terminal, which the tests cover.

## Release 0.3.0, 2026-10-23

Windows 11, Windows Terminal, Python 3.14.8, Textual 8.2.8. The built wheel
installed as a tool into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`),
leaving Jadon's installed 0.2.2 alone. An owned window with `NO_COLOR`
removed and `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointing
at empty ignored folders; a copy of the example machine file. No SSH
connection and no browser.

| Check | Observed |
| --- | --- |
| Installed tool | `ssh-workbench` resolved to the ignored tool folder; `--version` printed `ssh-workbench 0.3.0`. Jadon's own tool still printed `ssh-workbench 0.2.2` |
| 80x24 | The header read `2 machines   ○ 1 offline   ◇ 1 can't check`; list, details and footer drew. Down showed Studio box's details, Up Garden demo's again; Tab moved the highlighted border from the list to the details and back; Page Down and Page Up changed nothing, as the details fit; R showed `◐ 1 checking` |
| 50x24 | The list above the details, the header as symbols, the footer on two rows, the help line hidden |
| 120x30 | Each row showed its alias or address on the right |
| 80x18 | The help line hidden, side by side |
| Form during a resize | E at 80x24 opened the edit form; resizing to 52x22 with it open stacked the browser behind it; Escape closed it |
| Quit | Q and, in a second run, Ctrl+Q exited with status 0 and returned to a working prompt |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1077 passed |

Not checked: Linux and macOS terminals; the install from the tag, which
needs the tag.

## Task 20: UI makeover, 2026-10-22

Windows 11, Windows Terminal, Python 3.14.8, Textual 8.2.8. An owned window
driven by keystrokes and window resizes, with `NO_COLOR` removed and
`APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointing at empty
ignored folders; a copy of the example machine file. No SSH connection and no
browser.

| Check | Observed |
| --- | --- |
| 80x24 | Rounded borders, the title chip and colored counts drew as designed; the header read `2 machines   ◐ 1 checking   ◇ 1 can't check`, then `○ 1 offline` once the fictional host's check ended. Every detail field of the alias machine fit without scrolling |
| 60x20 | Side by side; the header kept words; the footer on one row |
| 47x16, the narrowest Windows Terminal allows | The list above the details, the header as symbols (`2  ○1 ◇1`), all eight footer keys on two rows, the help line hidden |
| 120x40 and 199x46, the largest that fits this screen | Each row showed its alias or address on the right; details one line per field |
| Form during a resize | E at 120x40 opened the themed form; resizing to 51x21 with it open, then Escape, left the browser stacked with the footer on two rows |
| Help line at 51x21 | Wrapped onto two rows in the first run; after hiding it below 60 columns, a restart showed none |
| Quit | Q, and Ctrl+Q after a restart, returned to a working prompt (`echo` answered) |
| README image | `.local/task20-session/demo.py` ran the app at 110x22 on five fictional machines with a stand-in checker (no network, no `ssh -G`); the window was cropped to the terminal area |
| Fresh review | An Opus reviewer found no critical issue and one important one: the no-file screen's box took its longest line's width, so at 60 columns and below a long path and the format sentence ran off the screen. Fixed test first; at 50x20 in Windows Terminal the box then fit the width and scrolled down for the rest. Five minor findings were fixed in code comments and docs; sharing the three copies of the status colors was left as optional |
| Ruff check and format, `uv run --locked pytest` | Passed; 1077 passed |

Not checked: 200x50 natively (the screen fits 46 rows; the headless test
covers 200x50), Linux and macOS terminals, light terminal themes (Workbench
paints its own background), and screen readers.

## Task 19: documentation and workflow, 2026-10-22

Windows 11, Python 3.14.8, uv 0.13.4. Documentation only; no code changed.

| Check | Observed |
| --- | --- |
| Archive | `docs/roadmap.md` and `docs/validation.md` moved unchanged to `docs/archive/` in one commit (0 lines changed). The diff since then adds only the PR #23 record, Task 18's two ticks, one backlog item, each file's header and relative links rewritten for the new folder, or retargeted where their content moved (the schema, the release checklist, the Task 17 references) |
| Fresh review | An Opus reviewer compared old and new docs rule by rule and against the code: no critical findings. Three important ones were fixed (commit approval had been relaxed, a Linux platform qualifier was lost, Task 19 was not moved to Done) with ten minor ones; the app's "The README describes the format." moves to Task 20, a code change |
| Links | A scratch checker resolved all 172 relative links in the 14 Markdown files, anchors included, with GitHub's heading slugs |
| Ruff check and format, `uv run --locked pytest` | Passed; 1046 passed |

Not checked: how GitHub renders the two Mermaid diagrams; they are checked on
the pull request.
