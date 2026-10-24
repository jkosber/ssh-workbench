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
