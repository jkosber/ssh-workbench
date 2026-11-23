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

## Release 0.4.0, 2026-11-23

Arch Linux (Omarchy, Hyprland 0.56.2, Wayland), Ghostty 1.4.0 (JetBrainsMono
Nerd Font, size 9; the wrapper printed `TERM=xterm-ghostty size=80x24`),
Python 3.14.10, Textual 8.2.8, `release/0.4.0` at `86ad113`. The built wheel
installed as a tool into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`),
with the install output kept, leaving Jadon's own tool alone. A coding agent
drove a floating Ghostty window and took screenshots with grim, as for Task
30; keys went through Hyprland's `send_key_state`, and window sizes were set
in cells. `NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at ignored folders with no Workbench files.
Every run used `--config` on a copy of the example machine file in an ignored
folder, so the status rounds tried the example's fictional names. No SSH
connection and no browser: C, K and O were never pressed.

| Check | Observed |
| --- | --- |
| Installed tool | `uv tool install --reinstall` of `ssh_workbench-0.4.0-py3-none-any.whl` into the ignored folders ended with `Installed 1 executable: ssh-workbench`; that executable's `--version` printed `ssh-workbench 0.4.0`, while the `ssh-workbench` on `PATH` printed `ssh-workbench 0.3.4`; every row below ran that executable |
| 80x24 | The header read `2 machines · ◇ 1 can't check · ▖ 1 checking`, then `○ 1 offline` once the check finished. Garden demo was selected, with a cyan `▌`, a band and a bold name, and `1/2` in the list's label row. Its details read `◇ can't check · SSH could not resolve the alias` (the empty SSH folder has no config file) and `alias · garden-demo-host (not in your SSH config)`, with the link's URL wrapped before `/fictional`. The result line was blank, and the nine footer keys were on one row: `c connect  o link  a add  e edit  x delete  k key  r check  ? keys  q quit` |
| Down, Up, Tab | Down showed Studio box: `2/2`, `○ offline`, `direct · studio@studio-box.example.com:2222`, the key, both addresses and two links. Up showed Garden demo and `1/2` again. Tab moved the thick cyan line to the details' label row and dimmed the band; a second Tab moved both back. Page Down and Page Up left Garden demo's details as they were, as they fit |
| `?` | A panel at the right of the panes listed `↑ ↓ tab pgup pgdn`, then the nine keys. `?` again closed it; opened once more, Escape closed it |
| R | The header read `▖ 1 checking` with a blue block on Studio box's row; in the next screenshot, six seconds later, it read `○ 1 offline` again |
| Resizes | 120x30: each row showed its alias or first address at the right. 60x20: side by side, the footer on two rows, each details label above its value. 50x24: the list above the details with the details' label row between them, labels beside their values, the footer on two rows, the header cut to `2 machines · ◇ 1 can't check`. 40x16: stacked, the header as symbols (`2 · ◇1 ○1`), the footer on three rows with all nine keys, the details with a scrollbar. 120x18: one footer row, a blank result line, nothing overlapping. 160x50: a header row `name  target  user` over the list and `studio` in the user column |
| Details scrolling, 60x20 | Studio box's details had a scrollbar. With the details focused, Page Down showed the end of the links block and Page Up the top again |
| Form during a resize | E at 80x24, then 52x22: the edit form stayed open, its labels moved above their fields, the fields scrolled and the buttons stayed on the last row. After Escape the browser was stacked with the footer on two rows |
| Add form, 80x24 and 60x20 | A opened `Add machine` over a screen dimmed to faint text; words of the header and details could still be made out when looked for. Labels sat beside their fields and the links box showed its grey explanation. `x` then Backspace put `expected a nonempty string` in red under `id`, and typing `x` again removed the row. Tab moved the cyan `▌` to `name`. Tab, Down, Space filled the `Direct (addresses)` ring and emptied the other, and the frame grew to show `addresses`, `user`, `port`, `key` and `export` with their grey explanations. The last row was `^s save` and `esc cancel`; Escape closed the form and nothing was saved. Narrowed from 80x24 to 50x24, the labels went above their fields and the two rings stacked; back at 80x24 they were beside them again, and the typed `x` was kept |
| Delete question, 80x24 and 60x20 | X on Garden demo: a red frame with `Delete Garden demo (garden-demo)?`, the rewrite warning after it, as the copy has comments, a blank row and `y delete  n keep` as the last row. N kept the machine |
| Include question | E on Studio box, seven Tabs to `export`, Space: `·` became `X`. The first Ctrl+S showed the rewrite sentence ending `Press Ctrl+S again to save.` above the buttons. The second saved and showed `Exported aliases`: the question naming the config in the ignored SSH folder, `Include ssh-workbench.config` in bold with a blank row above and below, `The file doesn't exist yet; Workbench creates it with this line.`, a blank row and `y add  n not now`. N closed it; the result line read `· Exported aliases work once your SSH config starts with: Include ssh-workbench.config` on two rows, and the `connect` row ended with `· exported as ssh studio-box` |
| Quit | Q in two runs and Ctrl+Q in a third: the wrapper printed `APP EXIT STATUS: 0`, and `echo typed-ok` at the prompt printed `typed-ok`. After the run with the resizes, the wrapper's own lines above the prompt were cut at 40 columns, that run's narrowest width |
| Files | A state file beside the copied machine file. After the save: the copy without its comments and with `export_alias = true`, `machines.toml.bak` with the old text, and `ssh-workbench.config` with `Host studio-box` in the ignored SSH folder, where no `config` file was created. The `APPDATA` folder stayed empty and nothing changed under `examples/` |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1458 passed |

Not checked: Windows Terminal (the look check above ran on `728d023`, before
the version change) and macOS; C, K and O, as the fixture scripts were not run
for the release; the result line's limit of two rows at 120x18, as the only
result shown was at 80x24; Y in either question; the `?` panel at other
sizes; a physical keyboard and the mouse; the install from the tag, which
needs the tag.

## TUI overhaul: the look in Windows Terminal, 2026-11-23

Windows 11, Windows Terminal 1.25.3131.0 (MesloLGM Nerd Font Mono, size 11,
the profile's dark scheme at 85% opacity), PowerShell 7.6.10, Python 3.14.10,
Textual 8.2.8, `main` at `728d023`. This is the one Windows Terminal look
check the overhaul's design recommended after Task 30. At Jadon's request, a
coding agent on another machine drove the window through a scheduled task in
the Windows workstation's desktop session and the Windows Terminal harness, as
in the Caps Lock entry of 2026-10-31; the task was unregistered afterwards.
Three launchers were used: the Task 30 look launcher (51 fictional machines, a
stand-in checker, a temporary machine file, state file and SSH folder, the
process, socket and browser entry points rejected), `scripts/check_keys.py`
for the key picker, and a launcher of the same build with five fictional
machines for the README image. `NO_COLOR` was unset. No port check, no
`ssh -G`, no `ssh`, no browser. C was never pressed, and K only in
`check_keys.py`. Windows opened at 80x24, 60x20, 120x30 and 110x22; resizing
an open window by pixels gave 57x19, 78x23 and 58x19.

| Check | Observed |
| --- | --- |
| Bold | The selected machine's name, the details' name, the border titles, the footer and hint keys, the form's two buttons, the key picker's section labels, the highlighted option and the focused radio label drew in a heavier weight, each in its own color |
| Glyphs | `▌ ● ○ ◇ × · X ↑↓` and the rounded frame corners each took one cell and drew in MesloLGM Nerd Font Mono |
| Main screen | 80x24: the header with two counts, the `▌` marker and band on the selected row, five details rows and the links block with wrapped URLs, nine footer keys on one row. 60x20: labels above their values, the footer on two rows. 120x30: all five header counts and row targets |
| `?` | The key panel opened at the right with cyan keys; Escape closed it |
| Backdrop | Behind every modal the main screen was dimmed to faint text on the background color; the frames were solid |
| Add form, 80x24 | `Add machine` in the border, lowercase labels beside the fields, the muted placeholder in the links box, `^s save` filled and `esc cancel` plain on the last row. Ctrl+S on the empty form put `expected a nonempty string` in red under `id` and the frame grew by a row; typing `demo` moved the error under `name` |
| Focus bar and marks | Tab moved a cyan `▌` to the connection row, the checkbox and the links box without moving their text. Down then Space filled the `Direct (addresses)` ring and emptied the other, and the frame grew to show the direct fields with their placeholders. Space on the checkbox turned `·` into `X` |
| Edit form | Studio box's values in their fields, the links box at five rows. Tab, Tab: the band was on `SSH alias` while the filled ring was on `Direct (addresses)`, as in the roadmap's backlog row |
| Form across 60 columns | With an id and a name typed at 80x24, narrowing to 57x19 put the labels above their fields and stacked the two rings; the focused name field stayed in view and the buttons on the last row. Back at 78x23 the labels were beside their fields and both values were kept |
| Link picker | Three links: the machine's name, each link's name over its muted URL, Grafana's URL wrapped under the name, the `▌` marker and band following Down, `enter open  esc cancel` on the last row; the same at 60x20 and 120x30. Twelve links at 80x24: the list scrolled with a one-column scrollbar between the name and the hint row, and End showed the twelfth with its marker |
| Delete question | A red frame as wide as `Delete Studio box (studio-box)?`, a blank row, `y delete  n keep`; for the long name and 86-character ID the frame went to its width cap with the ID wrapped. N and Escape kept the machine |
| Key picker (`check_keys.py`) | `Key login`, the intro, a blank row, `Key` bold, three options with the `▌` marker, a blank row, `Target system`, the filled and empty rings, and `↑↓ key  tab system  enter start  esc cancel` on the last row. Tab, Down, Space filled the Windows ring. For the alias machine the amber note and the muted `Not listed` line showed, and everything fit 80x24. Narrowed to 58x19 the body scrolled under the hint row with the highlighted key in view. Escape closed it and nothing started |
| README image | `docs/images/workbench.png` retaken at 110x22 from the five-machine launcher with the second machine selected, cropped to the terminal area |
| Q | `APP EXIT STATUS: 0` after each of the eight runs but the first, whose window was closed by the harness after a script error before Q was sent |

Not checked: 40x16 and 160x50 in Windows Terminal; Enter in either picker, Y
in either question and a save (no machine file was changed); the Include
question; the mouse and a physical keyboard; text contrast as a measured
ratio; other fonts and Windows Terminal's default profile settings.

## TUI overhaul Task 30: forms and pickers, 2026-11-22

Arch Linux (Omarchy, Hyprland 0.56.2, Wayland), Ghostty 1.4.0
(JetBrainsMono Nerd Font, size 9; the wrapper printed `TERM=xterm-ghostty`),
Python 3.14.10, Textual 8.2.8, `feat/task30-forms-and-pickers` at `ea2c727`.
A coding agent drove a floating Ghostty window and took screenshots with grim,
as for Task 29. Keys went through Hyprland's `send_key_state`, one at a time,
and the agent checked that the test window had the focus before each key. Two
launchers were used. The first was a copy of the Task 29 launcher in an ignored
folder: 51 fictional machines (the Task 29 set plus a machine with twelve
links), a stand-in checker, a temporary machine file, state file and SSH
folder, `NO_COLOR` unset, and the process, socket and browser entry points
rejected. It ran once as is and once with a machine file that starts with a
comment, so the rewrite warning shows. The second was
`scripts/check_keys.py`, for the key picker. No port check, no `ssh -G`, no
`ssh`, no browser. C was never pressed, and K only in `check_keys.py`. Window
sizes were set in cells and matched each grid: 80x24, 60x20, 120x30, 160x50,
40x16, and 59x20 for the breakpoint.

| Check | Observed |
| --- | --- |
| Backdrop | Behind every modal the main screen's text sat at 1.20:1 to 1.33:1 against the backdrop (sampled pixels: header, list rows, details, footer). The panes stayed faintly there; words such as `Node 09` and the footer keys could still be made out when looked for |
| Machine form, 80x24 | `Add machine` and `Edit machine` titles in the accent, bold, on a rounded accent border. About 71 columns wide, centered, as tall as its rows. Lowercase labels beside the fields: `id name connection alias links`; for Direct, `addresses user port key export`. The `id`, `user` and `port` inputs were 32 columns; the others filled the row. On empty Direct fields the placeholders `online one is used, else the first`, `optional`, `optional`, `path of the private key, optional` and `one per line: the name, then the URL` were muted. No empty error rows |
| Buttons | The last row of the frame: `^s save` filled in the accent and `esc cancel` plain, with nothing under them. With the focus, `^s save` turned to accent text on a dark cell, weaker than its fill, and `esc cancel` to a light grey fill |
| Error shown and cleared | Ctrl+S on an empty add form put `expected a nonempty string` in red under `id`, and the frame grew by one row. Typing `demo` removed it, and the next empty field's error (`name`, then `alias`) appeared under that field instead. For Direct, typing an address removed `expected a nonempty array of strings`, and the frame shrank back |
| Focus bar | Tab moved a cyan `▌` through id, name, the connection row, alias or the Direct inputs, the checkbox and the links box (its full 5 rows). The field text stayed in the same column with and without the focus. One Tab stop after `esc cancel` showed no cue (the fields' scroll container, a stop before this task too); the next Tab reached `id` |
| Rings and checkbox | Selected `●` in the foreground color, unselected `○` muted. Down then Space on the connection row moved the band to `Direct (addresses)` and filled its ring; only one was filled. The checkbox showed `·` muted when off and `X` when on, with the band on its label while focused |
| Editing a direct machine | E on Studio box, Tab, Tab: the band was on `SSH alias` while the filled ring was on `Direct (addresses)`. Space was not pressed there |
| Labels across 60 | With values typed and the checkbox on: at 59x20 the labels went above their fields, the two rings stacked, the fields scrolled with a one-column scrollbar, and the buttons stayed on the last row. At 60x20 and back at 80x24 the labels were beside their fields again. Every typed value and the checkbox were kept. With the links box focused, the links box was below the fields' last row after the narrowing, out of view |
| Long save message, 60x20 | With the commented file, E, Ctrl+S: the rewrite sentence and `Press Ctrl+S again to save.` took three rows above the buttons. The fields gave up the rows and scrolled, beside the links box's own scrollbar; the buttons stayed inside the frame |
| Include question | Reached through the app's own export flow (add a Direct machine with `export` ticked, Ctrl+S) in the launcher's temporary SSH folder. `Exported aliases` title; the question naming the temporary config; `Include ssh-workbench.config` bold with a blank row above and below; `The file doesn't exist yet; ...`; a blank row; the hint row `y add  n not now`. N closed it and the result line read `Exported aliases work once your SSH config starts with: Include ssh-workbench.config` |
| Delete question | Red border and red `Delete machine` title. For `Link shelf (link-shelf)` the frame was about 34 columns wide and 5 rows tall, centered; for the long name with the 86-character ID it went to the 72-column cap at 80x24 and up, and to 90% at 60x20 and 40x16, with the ID wrapped. With the commented file the rewrite warning followed the question. The hint row `y delete  n keep` was the frame's last row, with a blank row above it, at every size, 40x16 with the warning included. N and Escape kept the machine |
| Link picker, three links | `Open a link` with `Studio box` above the options. Each option was the name with its URL on the next row, indented two past the name. Grafana's URL wrapped before `&refresh=30s` at 80x24 and up, and before `/fictional-studio-overview` at 60x20 and 40x16, every piece indented under the name. A cyan `▌` ran down the highlighted option's rows, the name turned bold, and the marker moved with Down. 72 columns wide from 80, 90% below. Hint row `enter open  esc cancel` at the bottom; Escape returned to the list with the same selection |
| Link picker, twelve links | At 80x24, 120x30, 60x20 and 40x16 the options scrolled between the machine name and the hint row with a one-column scrollbar; the highlighted option and its marker stayed in view down to option 12. At 160x50 all twelve fit. With option 3 highlighted, resizing 60x20 to 80x24 and back rewrapped the URLs; option 3 kept the highlight and marker, and no URL piece started in column 0 |
| Key picker (`check_keys.py`) | `Key login`; the intro; a blank row; `Key` bold; the options with the `▌` marker on the highlighted one, which moved with Down; `Target system` after a blank row; `● Linux, macOS or other POSIX` and `○ Windows (OpenSSH Server)`; the hint row `↑↓ key  tab system  enter start  esc cancel`. Tab, Down, Space filled the Windows ring and emptied the other; the focused rings showed the band and bold, no `▌` bar. Escape closed it and nothing started. For the alias machine, `Not listed: id_work, ...` was muted under the options |
| Key picker with a note | The fixture's note names a temporary path, longer than a real SSH folder's. At 80x24 everything fit. At 60x20 the note pushed the Windows ring below the fold and the body scrolled. At 40x16 the first label wrapped over two rows, its second row starting under the marker, the hint row took two rows, and after Down onto a key with a note the note took about 7 rows and the highlighted key was out of view until the body was scrolled |
| Glyphs | `▌ ● ○ · X ↑↓` each took one cell and drew in JetBrainsMono Nerd Font |
| Hint row colors | Sampled: keys #4FBFE7 bold, labels near #A9AEB9, background #171B26, the same as the main footer's |
| Q | `APP EXIT STATUS: 0` and the wrapper's prompt after all three runs |
| After the check | The review then found that a failed save on a small terminal scrolled the newly focused field out of view. That, the links box hidden by the narrowing and the key hidden at 40x16 were changed after `ea2c727`; the three were seen fixed in headless tests only, not again in Ghostty |
| Automated | 1458 passed; `ruff check` and `ruff format --check` clean; `uv build` and the package check passed |

Not checked: Windows Terminal (after the merge, with the README screenshot);
Enter in the link picker and in the key picker (no link opener and no
key-setup child was run); Y in either question; Space on a form button; a
130-character ID (the launcher's is 86); the key picker's note with a real
SSH folder's path; text contrast inside the frames as a measured ratio; a
physical keyboard; the mouse. The findings above that are not this task's to
fix are backlog rows in [the roadmap](roadmap.md), each "From 30".

## Dependency update, 2026-11-22

Arch Linux (Omarchy), uv 0.13.4 from the Arch package, Textual 8.2.8,
`ci/dependency-update`. No SSH and no browser.

| Check | Observed |
| --- | --- |
| `uv python list 3.14 --all-versions --only-downloads` on uv 0.13.4 | The newest build listed is 3.14.8; uv's release notes add 3.14.10 in 0.13.6 |
| `uv python install 3.14.10 --no-bin` on uv 0.13.4, with `UV_PYTHON_INSTALL_DIR` at an empty folder | `error: No download found for request: cpython-3.14.10-linux-x86_64-gnu` |
| `uv sync --locked --dry-run` on uv 0.13.4, with that empty folder and `UV_PYTHON_PREFERENCE=only-managed` | `error: No interpreter found for Python 3.14.10 in managed installations`, with a hint to retry on a newer uv |
| `uv tool run --from uv==0.13.9 uv python install 3.14.10 --no-bin` | uv 0.13.9, run as a tool, installed 3.14.10 among uv's managed Pythons |
| `uv sync --locked` on uv 0.13.4, with `.python-version` at 3.14.10 | The environment was recreated on the managed 3.14.10; before, it ran the system's 3.14.8. `ssl.OPENSSL_VERSION` is OpenSSL 3.5.9 |
| `uv lock --check` on uv 0.13.4 and on 0.13.9 | Both accept the lockfile, which uv 0.13.4 wrote |
| `uv build` on uv 0.13.4 with `uv_build>=0.13.9,<0.14.0` | Both artifacts built, with no warning about the backend's range |
| Re-inspection | The 3.14.9 and 3.14.10 changelogs and the CPython `v3.14.8..v3.14.10` diff change no code that the earlier notes rely on; see [architecture](architecture.md#installed-source-and-local-runs) |

Then in a real terminal: Ghostty 1.4.0 at 80x24 (Hyprland 0.56.2, Wayland; the
wrapper printed `TERM=xterm-ghostty size=80x24`), Python 3.14.10, at
`2d29495`. At Jadon's request, a coding agent drove a floating Ghostty
window, sent keys one at a time through Hyprland's `send_key_state` and took
screenshots with grim. `NO_COLOR` was unset and `APPDATA`,
`XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointed at ignored folders. C
was pressed only in `scripts/check_terminal.py`; K and O never.

| Check | Observed |
| --- | --- |
| `check_terminal.py` 1 | C: the child printed `Local child: fixture-zero; terminal stdin/stdout/stderr: [True, True, True]` and `Local child stderr is visible.`; `return` gave "SSH exited with status 0. Machine 1: fixture-zero" after a green `●`, with machine 1 still selected |
| `check_terminal.py` 2 | Tab, C, `return`: "SSH exited with status 7. Check the SSH client's message and alias; C retries. Machine 2: fixture-seven" after a red `×`, on two rows; Down then selected fixture-interrupt |
| `check_terminal.py` 3 | C, then Ctrl+C: the child printed `Child received Ctrl+C.` and the result read "SSH exited with status 130. Check the SSH client's message and alias; C retries. Machine 3: fixture-interrupt"; the app kept running |
| `check_terminal.py` 4 | After each of two Ctrl+C presses the child printed `Child received Ctrl+C.` and `Child still owns the terminal; type return to finish.`; `return` gave "SSH exited with status 0. Machine 4: fixture-continue" |
| `check_terminal.py` 5 | "SSH not found. Install OpenSSH and add it to PATH. Machine 5: fixture-missing"; "Could not start SSH. Check its installation and executable permissions." with "Machine 6: fixture-error" on the next row; "SSH interrupted. Press C to retry or Q to quit. Machine 7: fixture-keyboard". Each kept its selection, and a second C on machine 7 left a byte-identical screenshot |
| `check_terminal.py` 6 | Q printed `APP EXIT STATUS: 0` and gave back the `check$` prompt, where `echo hello` printed `hello`; the shell's screen kept every child's output. In a second run, C on machine 1 and `return` gave status 0, then Ctrl+Q gave the same exit status and a working prompt |
| App smoke check on `examples/machines.example.toml` | The list, the details and the nine footer keys drew on one row each, with a blank result line; the header read `2 machines · ◇ 1 can't check · ○ 1 offline`. Down selected Studio box, with `2/2` in the list's label row and its details; Tab moved the thick cyan line to the details' label row and dimmed the band; Page Down changed nothing, since the details fit. ? opened the key panel at the right of the panes with ↑ ↓ tab pgup pgdn first, and Escape closed it; R turned Studio box to `checking`, and the header counted `1 checking`. Q, and Ctrl+Q in a second run, printed `APP EXIT STATUS: 0` and left a prompt where `echo hello` printed `hello` |
| Resize during that run | At 60x20 the panes stayed side by side, the footer took two rows and each details label sat above its value; at 120x30 each row showed its target, `garden-demo-host` and `studio-box.example.com`; back at 80x24, Q exited as above |

Not checked: Windows Terminal, which rests on the CI runner; K and O; ? a
second time to close the key panel; the other sizes of the smoke check's
resize list and a resize with a form open; a real SSH target.

## TUI overhaul Task 29: list rows and details, 2026-11-22

Arch Linux (Omarchy, Hyprland 0.56.2, Wayland), Ghostty 1.4.0 (the wrapper
printed `TERM=xterm-ghostty`), Python 3.14.8, Textual 8.2.8,
`feat/task29-list-and-details` at `065fcd6`, and one screen again at
`2ceea3a` after the review changed how URLs break; the commits between
change the capture example and docs, not the app. A coding agent drove a
floating Ghostty window and took screenshots with grim, as for Task 28. Keys
went through Hyprland's `send_key_state`, one at a time. The app ran from a
launcher in an ignored folder, built the way `scripts/capture_look.py` builds
its app: 50 fictional machines (the size matrix's Studio box, a machine with
an 86-character ID, a long link name and a long URL, alias, offline, proxied
and missing-alias machines, and 44 fillers), a stand-in checker, a temporary
machine file and state file, the user and SSH folders in a temporary folder,
`NO_COLOR` unset, and the process, socket and browser entry points rejected.
No port check, no `ssh -G`, no `ssh`, no browser; C, K and O were never
pressed. Window sizes were set in cells, and the window's pixel size matched
each grid.

| Check | Observed |
| --- | --- |
| 80x24 | Header `50 machines · × 1 alias not found · ◇ 8 can't check`. On the selected row a cyan `▌` in column 0 and a blue-grey band across the list; only the selected name was bold. No row targets. Studio box's details: `status ● online · 192.0.2.40` (word green, address muted), `connect direct · studio@192.0.2.40:2222`, `key`, `addresses` on two lines, a blank row, `links` alone, then three links with names in one column and URLs in another. Nothing scrolled; the footer showed all nine keys on one row |
| Link wrapping at 80x24 | The URL column was 29 columns. `Grafana` broke before `/fictional-studio-overview` and before `?orgId=1&refresh=30s`. `Status page` broke at the column edge, as `https://studio-box.example.co` over `m/status`: its only `/` after the scheme is one column too far. No URL line started under the name column |
| The same screen at `2ceea3a` | A URL with no `/`, `?`, `&` or `#` in reach now breaks before a `.` or `-`. `Status page` broke as `https://studio-box.example` over `.com/status`; `Dashboard` and `Grafana` as before |
| Tab and back at 80x24 | The thick cyan line moved under the details' label row and `machines` lost its cyan. The list band dimmed to grey and the `▌` stayed. A second Tab put everything back |
| Unset rows | The long-ID machine had no `key` row; the alias machines had no `key` or `addresses` rows; machines without links showed `links  none` muted |
| Other states | Lab `○ offline`; Hop `◇ can't check · the alias uses ProxyJump or ProxyCommand`; Archive `× alias not found. Fix your SSH config and press R, or press E and save to keep or change the alias.` with `connect alias · archive-host`, and the footer hid `c connect`. Garden demo and Hop showed `(not in your SSH config)` in red: the launcher's SSH folder has no `Host` lines |
| Long link name and URL at 80x24 | The name was cut at 20 columns as `Fictional monitorin…`; the URL wrapped over nine rows inside its column, with five breaks before a `/`, `?` or `&` and three at the column edge |
| Long name and long ID | The label row read `Long identifier machin…fictional-long-identi…`: the name's `…` sat directly against the ID, with no space, at 80x24, 60x20 and 40x16 |
| `?`, Escape | The panel opened at the right with cyan keys and lowercase labels; Escape closed it |
| `?`, `a`, Escape, Escape | `a` opened the Add machine form over the panel. The first Escape closed the form and the panel was still open; the second closed the panel |
| 120x30 | All five header entries. Row targets muted and right-aligned: Studio box `192.0.2.40` (the address that answered, not the first), the alias for alias machines, the address for the other direct machines. The long name ended `with a …` before its target. Studio box's links each fit on one row except Grafana, which broke once, before `/fictional-studio-overview`. Tab dimmed the band and kept the marker |
| 160x50 | A muted `name  target  user` header above the list and three aligned columns; the user column was blank for alias machines and for direct machines without a user. Studio box's three links each took one row. After Page Down the list showed Node 01 to Node 44 under the same header, columns still aligned; the selection stayed on 1/50, out of view |
| 60x20 | Side by side, list 24 columns. Details labels above their values; each link name on its own line with its URL on the next, indented two; a one-column scrollbar. Footer on two rows |
| 50x24 | Stacked panes: seven machines, the details' label row, then details with labels beside their values and links in two columns. Footer on two rows; the band dimmed on Tab here too |
| 40x16 | Header `50 · ×1 ◇8 ○26 ●15`; four machines, the details' label row, then details rows with labels above values and a scrollbar; footer on three rows. Nothing overlapped, also with a two-row result line |
| 120x18 | Two keys in the launcher put fictional results on the result line. One the length of Task 28's connect result took two rows, whole; a longer one took two rows ending `repeats t…`. The details still showed their last links row; nothing overlapped |
| Glyphs | `▌ ● ○ ◇ × ·` and `…` each took one cell, in the colors of their states |
| Bands | Sampled pixels: focused rgb(32,59,81), unfocused rgb(34,43,57), list surface rgb(34,37,46). Text on both bands read clearly; the unfocused band was faint but visible |
| Home in the list | The selection stayed where it was (6/50) |
| Q | `APP EXIT STATUS: 0` and the `check$` prompt after both runs |
| Automated | 1393 passed at `2ceea3a`; ruff check and format clean; `uv build` and the package check passed |

Not checked: Windows Terminal (the design defers it to after Task 30); a
physical keyboard; 100x30, 120x40, 200x60 and 80x50 in Ghostty, which the
size matrix test covers headless; `· exported as ssh <id>` in the connect
row; a selected row in a scrolled list from 130 columns; a result line made
by C, K, O or a save; the other sizes and screens after `2ceea3a`; text
contrast on the bands as a measured ratio in the terminal (the theme test
measures it from the theme's values).

## TUI overhaul Task 28, 2026-11-09

Arch Linux (Omarchy 4.5, Hyprland 0.56.2, Wayland), Ghostty 1.4.0 (the
wrapper printed `TERM=xterm-ghostty`), Python 3.14.8, Textual 8.2.8,
`feat/task28-layout-and-breakpoints` at `f774948`. A coding agent drove a
floating Ghostty window and took screenshots with grim, as for Task 27.
`NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at ignored folders with no Workbench files;
the machine file was a copy of the example in an ignored folder. Window sizes
were set in cells and read back with `stty size`. Keys went through
Hyprland's `send_key_state`: wtype's `?` reached Textual as Escape with `?`
as its text, as wtype's capitals did on 2026-10-30, and after wtype had typed,
`send_key_state` failed with "key not found" until `hyprctl switchxkblayout`
reset the desktop keymap. One `ssh` run, to the example's fictional host
name, which does not resolve; no browser.

| Check | Observed |
| --- | --- |
| 80x24 | No borders. The header read `2 machines · ◇ 1 can't check · ○ 1 offline`. The list's label row read `machines` in cyan and `1/2` muted; the details' read `Garden demo` in bold with `garden-demo` muted at the right edge. A thick cyan line ran under the list's label row, a thin grey one under the details' and a thin grey vertical line between the panes. The list was 32 columns wide and all nine details rows fit. One blank row sat above the footer, which held all nine keys on one row, `c connect` to `q quit`, keys cyan and labels grey |
| 120x30 | List 48 columns; the rows showed `garden-demo-host` and `studio-box.example.com` muted at the right; the details fit; footer on one row |
| 60x20 | Side by side, list 24 columns; the header kept both entries; the footer took two rows, five keys over four, in aligned columns; the details showed a one-column scrollbar |
| 50x24 | Stacked: the list's label row, both machines, then the details' label row with its thin line, then the details at full width. The header dropped the offline entry: `2 machines · ◇ 1 can't check`. Footer on two rows |
| 40x16 | Stacked; header `2 · ◇1 ○1`; the two machines, the details' label row and four details rows with a scrollbar; footer on three rows, `c connect  o link  a add`, `e edit  x delete  k key` and `r check  ? keys  q quit` |
| 120x18 | Side by side with row targets, all nine details rows, the blank result row and a one-row footer |
| 160x50 | List 64 columns, row targets, the details fit, one-row footer; below the rows both panes were empty. The column header and user column come in Task 29 |
| `?` at 80x24 | A 30-column panel opened at the right of the panes, from the label row down to the result line, over the details' right side; the header and footer kept their full width. It listed `↑ Cursor up`, `↓ Cursor down`, `tab Focus Next`, `pgup Page Up`, `pgdn Page Down`, a blank row, then `^q q Q quit`, `c C connect`, `o O link`, `a A add`, `e E edit`, `x X delete`, `k K key`, `r R check` and `? keys`, the keys in amber. A second `?` closed it |
| Tab at 80x24 | The thick cyan line moved under the details' label row and the list's turned thin and grey; `machines` lost its cyan |
| C on Studio box at 80x24 | Within 1.5 seconds the app was back and the result line had grown to two rows: `× SSH exited with status 255. Check the SSH client's message and the machine's settings; C retries. Machine 2: studio-box`, the `×` red. After the app quit, the shell showed ssh's `Could not resolve hostname` line |
| O, then Escape | The link list opened with every footer key dimmed, `? keys` included; `?` there opened no panel. Escape closed the list; the result line kept only the connect result, as the picker writes none |
| The same result at 120x18, 60x20 and 40x16 | 120x18: two rows, whole. 60x20: two rows, the second ending `Machine 2:…`. 40x16: two rows, ending `the mach…` |
| Start at 51x24 (Ghostty opened 51 columns for 50) | Captures 35 ms apart: for about 100 ms the panes drew side by side, most detail values still empty and no footer, then stacked; the footer appeared about 200 ms after that. Started at 80x24, the footer also came last, about 260 ms after the first frame |
| Live resize from 80 to 50 columns | One capture, of captures 50 ms apart, showed the panes side by side at 50 columns with the one-row footer cut at `k ke`; the next was stacked with a two-row footer |
| Empty machine file (`machines = []`) at 80x24 and 40x16 | Muted `no machines in this file yet · a to add` with the `a` in bold cyan, then the path as given to `--config`; in the footer only `a add`, `? keys` and `q quit` were lit. At 40x16 the line broke between `a to` and `add`, and the path wrapped |
| Q | `APP EXIT STATUS: 0` and the `check$` prompt after each run |
| Files | The run wrote a state file next to the example's copy in the ignored folder; the `APPDATA` and SSH folders stayed empty |
| Automated | 1330 passed; ruff check and format clean; `uv build` and the package check passed |

Not checked: Windows Terminal (the design defers it to after Task 30; `?` is
a new key, so docs/testing.md asks for one run there, Jadon's call); a
physical keyboard; 100x30, 120x40, 200x60 and 80x50 in Ghostty, which the
size matrix test covers headless; the key panel below 24 rows in a real
terminal; a link result, which needs a browser; the no-file screens.

## App icon centering, 2026-11-09

Arch Linux (Omarchy 4.5), rsvg-convert 2.63.3, ImageMagick 7.1.2-34. Branch
`docs/icon-center-s`.

| Check | Observed |
| --- | --- |
| Center of the S's cyan and green pixels at 256 px, faint glow excluded | Full: 118.5, 139.5 before and 128.5, 127.5 after. Contained: 112.5, 143.5 before and 128.5, 127.5 after. The half pixel left over is the art: the pad ring is wider than the end node |
| Launcher with the S centered and the screwdriver moved with it, scaled to 0.81 about its tip | S center 115.5, 142.5 before and 128.5, 127.5 after. The handle ends 4.37 px inside the top and right canvas edges after the 1.09 scale. Visible area 244x242 at +10+4 before, 242x242 at +10+4 after. In a 4x enlargement of the 18 px and 36 px renders the S and the screwdriver were still recognizable to the agent that made the change; the dock check by eye is below |
| `ssh-workbench-launcher-256.png` against a fresh render of its SVG | Byte-identical |
| Screwdriver tip on the pad ring | Full and contained: in a 48 px crop around the pad, the cyan and shaft-grey pixels match the before render moved by the S's shift, pixel for pixel. Launcher: its shift is not a whole pixel and the screwdriver is smaller, so that crop differs in 59 of 2304 pixels; 7 cyan pixels lie within 1 px of shaft-grey ones, the same count as before, and a control render with the screwdriver 3 units off the ring gives 0 such pixels |
| Canvas edges and visible area (`magick -trim`) | No pixel on any canvas edge in any version, the launcher included. Full: 226x224 at +20+12 before, 232x232 at +20+4 after; its handle, shortened from 52 to 47 units, ends 4 px from the top and right edges. Contained: 240x240 at +8+8 before and after; its handle, shortened from 40 to 32 units, shares no pixel with the rim |
| `ssh-workbench.ico` | Six frames: 16 to 64 px as 32-bit BMP and 256 px as PNG, each pixel-identical to a render of `ssh-workbench-contained.svg` at that size. In an 8x enlargement the 16 px frame still shows the S |
| Automated checks | 1275 passed; ruff check and format clean; `uv build` and the package check passed |

Not checked: the icon in the dock by eye (needs a shell restart, left to
Jadon); the `.ico` on Windows (Windows runs are limited to the terminal
handoff, keys and the install script).

## App icon, 2026-11-05

Arch Linux (Omarchy 4.5, Hyprland, Qt 6.12), rsvg-convert 2.63.3,
ImageMagick 7.1.2-34. Branch `docs/app-icon`.

| Check | Observed |
| --- | --- |
| Launcher PNG installed with `omarchy tui install`, seen in the dock next to Docker and Ghostty | Jadon: a little small next to the other icons. The launcher drawing was scaled by 1.09; its visible area went from 224x222 to 244x242 of 256, with no pixel on the canvas edge |
| The three SVGs rendered by Qt SVG 6.12 (`qml6`, offscreen) and by librsvg | Within 0.26% RMSE at 256 px |
| `ssh-workbench-launcher-256.png` against a fresh render of its SVG | Byte-identical |
| `ssh-workbench.ico` | Six frames: 16 to 64 px as 32-bit BMP and 256 px as PNG, each pixel-identical to a render of `ssh-workbench-contained.svg` at that size |

Not checked: the enlarged icon in the dock by eye; the `.ico` on Windows; the
README on github.com in a browser.

## Audit fixes, 2026-11-04

Arch Linux (Omarchy), uv 0.13.4, Python 3.14.8, Textual 8.2.8, headless
pytest; no real terminal run. Branch `fix/audit-20261103-findings` on
`d4201ae`: 20 test/fix pairs and one test-only commit.

| Check | Observed |
| --- | --- |
| Full suite at `d4201ae`, the audit's baseline | 1151 passed, 0 skipped, 0 warnings |
| Full suite at the branch head, with this entry | 1275 passed, 0 skipped, 0 warnings; ruff check and format clean |
| The audit's three-arm check of the first 19 pairs, at `6e1a36d` | Every new test file failed at its test commit, passed at `6e1a36d` and failed again with its fix reverse-applied there. The fixes in `34a8de7` and `6804d2e` overlap later fixes, so they were reverted at their own fix commits and failed there |
| The same check for `133f84a` and `f4a704b` | `tests/test_keysetup_ui_create_choice_note.py`: 3 failed at `133f84a`, 7 passed at `f4a704b`, and 3 failed at `ea3d204` with `f4a704b`'s `app.py` change reverse-applied |
| `ea3d204` | Test-only: it pins behavior the code already had (a save keeps the machine file's mode and gives the backup `0o600`), so it has no failing arm |
| `uv build` and `scripts/check_package.py`, at `6e1a36d` | Both exited 0; the package check ended with `a first save passed.` |
| K with stdout on `/dev/full` (`23a60fc`) | A headless probe outside the repository ran the CLI with fictional SSH and `ssh-keygen` stand-ins, `PYTHONUNBUFFERED=1` and stdout redirected to `/dev/full`. At `ea3d204`, K on a machine with its own key ended with `Key login works.`, and K creating a key with `Key login works. The key is saved as this machine's key.`; the driver recorded suspend, then resume. At `8e8c0f7`, before the fix, both stopped on `OSError: [Errno 28] No space left on device` with only suspend recorded and return code 1 |

Not checked: the fixtures in a real terminal (Ghostty, Windows Terminal);
Windows CI, which runs after a push; the manual K flows against a real
target; `uv build` and the package check after `6e1a36d`.

## Task 27: colors, glyphs and states, 2026-11-01

Arch Linux (Omarchy, Hyprland, Wayland), Ghostty at 80x24 (the wrapper
printed `TERM=xterm-ghostty size=80x24`), JetBrains Mono Nerd Font, Python
3.14.8, Textual 8.2.8, `feat/task27-colors-and-states` at `ada7c07`. At
Jadon's request, a coding agent drove a floating Ghostty window with wtype
and Hyprland's dispatchers and took screenshots with grim, as for the 0.3.4
release. `NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at ignored folders with no Workbench files; a
copy of the example machine file in an ignored folder. No SSH connection and
no browser. Headless captures of the same build came from a throwaway script
modeled on the tests, with ten fictional machines in every state.

| Check | Observed |
| --- | --- |
| 80x24 | The header read `2 machines · ◇ 1 can't check · ○ 1 offline`, the `can't check` word amber and `offline` muted. Garden demo read `◇ can't check: SSH could not resolve the alias` (the empty SSH folder has no config file); Studio box's ring was grey |
| R | The header read `2 machines · ◇ 1 can't check · ▖ 1 checking`, the `▖` blue and `1 checking` muted, as can't check came first; Studio box's row showed a blue quarter block, drawn by Ghostty; four seconds later the header read as before |
| 120x30 | The full header `2 machines · ◇ 1 can't check · ○ 1 offline` with room to spare, each row with its alias or address on the right |
| 60x20 | The same two entries fit (59 of 60 columns) |
| 40x16 | The symbol form `2 · ◇1 ○1` |
| Down | Studio box's details showed `○ offline` in muted grey |
| Q | The wrapper printed `APP EXIT STATUS: 0`; `echo hello` echoed at the restored prompt |
| Headless, 10 machines | At 80 columns the header trimmed to `10 machines · × 1 alias not found · ◇ 2 can't check`, at 60 to the first entry, at 40 to `10 · ×1 ◇2 ○3 ▖1 ●3`; at 120 and 160 columns every state was named. Without a checker every row showed `·` and the header `10 machines · not checked`; the details read `· not checked` muted. Offline rings and words were grey; the alias-not-found symbol and word red |
| Automated | 1151 passed with no warnings; ruff check and format; `uv build`; the package check passed |

Not checked: Windows Terminal, deferred to the single look check after Task
30; a terminal without true color; the spinner's four frames one by one (one
frame was caught); contrast measured on screen, which the test computes from
the theme values instead.

## Task 26: tooling hygiene, 2026-10-31

Arch Linux, uv 0.13.4, Python 3.14.8, Textual 8.2.8, no terminal, no SSH, no
browser: the package check's own temporary environments. A probe line
`_TASK26_PROBE = "\d"` was appended to `src/ssh_workbench/app.py`, the wheel
rebuilt and `scripts/check_package.py` run, once on `main` at `1bac677` and
once on `ci/task26-tooling-hygiene` at `f8272f1`; the line was removed and
the wheel rebuilt afterwards.

| Check | Observed |
| --- | --- |
| `main` | The loader child printed `app.py:1987: SyntaxWarning: "\d" is an invalid escape sequence` to stderr, and the check still ended with `Built wheel: ... passed.` and exit status 0 |
| This branch | The check ended with `Installed wheel loader check failed (exit status 0):` followed by that warning, exit status 1 |
| Ruff | On `main`'s configuration `ruff check` on the probed file printed `All checks passed!`; on this branch it printed `Found 1 error.` for `W605` |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` without the probe | Passed; 1142 passed |

Not checked: a `SyntaxWarning` in `__main__.py`, which no check imports; a
loader child that exits nonzero with nothing on stderr (the test keeps the
exit status checked, but no run forced that case).

## Caps Lock in Windows Terminal, 2026-10-31

Windows 11, Windows Terminal at 80x24 running PowerShell 7, Python 3.14.8,
Textual 8.2.8, `main` at `fc2028e` (release 0.3.4; `uv run --locked
ssh-workbench --version` printed `ssh-workbench 0.3.4` in the window). This
run covers Windows Terminal after Task 24's fix, which that task's entry below
left unchecked. At Jadon's request, a coding agent on another machine drove
the window through a scheduled task in the Windows workstation's desktop
session and the Windows Terminal harness, as in the terminal fixture entry of
2026-10-30. A synthetic tap of the Caps Lock key turned the toggle on before
the app's keys were sent (`[Console]::CapsLock` read True while the app ran)
and off again before the window closed. C and Q were sent as plain key
presses, without Shift, so with the toggle on they typed capitals. `NO_COLOR`
was unset and `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointed
at empty ignored folders. `scripts/check_terminal.py` with its fictional
fixtures; the app made no SSH connection and opened no browser.

| Check | Observed |
| --- | --- |
| Caps Lock on, C on fixture-zero | The child printed `Local child: fixture-zero; terminal stdin/stdout/stderr: [True, True, True]`, `Local child stderr is visible.` and `Type return, or press Ctrl+C for an interruption check:` |
| `return` | `SSH exited with status 0. Machine 1: fixture-zero`, with fixture-zero still selected |
| Caps Lock on, Q | The app exited and `$LASTEXITCODE` printed `0`; with Caps Lock off again, `echo typed-ok` printed `typed-ok` |
| Footer | `c Connect o Link a Add e Edit x Delete k Key r Check q Quit`, lowercase throughout |
| Files | Nothing under the ignored `APPDATA`, config and SSH folders; no python process or test window left after `exit` |

Not checked: a physical Caps Lock key (a synthetic tap set the toggle);
letters other than C and Q, and Y and N in the dialogs; capitals typed into
the forms; with Caps Lock off after the fix, plain letters and Shift+letter
(the terminal fixture entry sent Shift+C and Shift+Q only with Caps Lock on,
before the fix, where they type lowercase).

## Release 0.3.4, 2026-10-31

Arch Linux (Omarchy, Hyprland, Wayland), Ghostty at 80x24 (a wrapper script
printed `TERM=xterm-ghostty size=80x24`), Python 3.14.8, Textual 8.2.8. The
built wheel installed as a tool into ignored folders (`UV_TOOL_DIR`,
`UV_TOOL_BIN_DIR`), with the install output kept, leaving Jadon's installed
0.3.3 alone. At Jadon's request, a coding agent drove a floating Ghostty
window with wtype and Hyprland's window dispatchers and took screenshots with
grim. `NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at ignored folders with no Workbench files; a
copy of the example machine file in an ignored folder. No SSH connection and
no browser.

| Check | Observed |
| --- | --- |
| Installed tool | `uv tool install --reinstall` of the wheel into the ignored folders ended with `Installed 1 executable: ssh-workbench`; that executable's `--version` printed `ssh-workbench 0.3.4`, while the `ssh-workbench` on `PATH` still printed `ssh-workbench 0.3.3`; every row below ran that executable with `--config` on the copied machine file |
| 80x24 | The header read `2 machines   ◐ 1 checking   ◇ 1 can't check`, then `○ 1 offline` once the check finished; Garden demo read `◇ Can't check: SSH could not resolve the alias` (the empty SSH folder has no config file), with the help line and the footer's eight keys in lowercase. Down showed Studio box's details (`○ Offline`, both addresses, port 2222) and Up Garden demo's again; Tab moved the focus border to the details; Page Down and Page Up left the details as they were, as they fit without scrolling; R showed `◐ 1 checking` again |
| 50x24 | The list above the details, the header as symbols (`2  ○1 ◇1`), the footer on two rows, the help line hidden, the details with a scrollbar |
| 120x30 | Each row showed its alias or address on the right |
| 80x18 | Side by side, the help line hidden |
| Form during a resize | E at 80x24, then 52x22: the edit form stayed open over the browser, with its ID and Name fields and the Save and Cancel buttons; after Escape, the browser was stacked with the footer on two rows |
| Quit | Q and, in a second run, Ctrl+Q exited with status 0 and returned to a prompt that echoed `echo typed-ok` and printed `typed-ok` |
| Files | A state file beside the copied machine file in the ignored folder; nothing under `examples/`; the `APPDATA` and SSH folders stayed empty |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1141 passed |

Not checked: Windows Terminal and macOS; scrolling the details, which fit at
80x24, and with it Task 25's reset on a new selection; Caps Lock and capitals
in this run (Task 24's entry covers C and Q); the install from the tag, which
needs the tag.

## Task 25: details reset before the next frame, 2026-10-30

Arch Linux, Python 3.14.8, Textual 8.2.8, headless pilot only: no terminal, no
SSH, no browser. Fictional machines: those of
`test_return_preserves_scroll_and_literal_details`, and for the trace a second
machine with a long link. One run of that test covers its 3 sizes, so 20 runs
are 60 cases. Two pytest plugins kept outside the repository emulated a slow
Windows runner: one rounds the process time that `textual._wait.wait_for_idle`
reads down to 15.625 ms steps, as Windows counts it, and one makes every
Textual timer sleep 20 or 30 ms late. The plain and 20 ms runs were not
interleaved; the 30 ms runs alternated between the branch and `main` run by
run, from two worktrees with nothing else running, so both met the same load.

| Check | Branch at `2448e3b` | `main` at `5f57ad3` |
| --- | --- | --- |
| Traced at 80x24: Down from the long machine, scrolled to its bottom, to the machine with a long link | The handler scrolled the pane to 0; the first frame showing the new machine was at the top | The handler left the pane at 67; the first frame showing the new machine was at 9, its bottom; the pane reached 0 one frame later, 86 ms after the handler returned |
| `test_return_preserves_scroll_and_literal_details` | All 20 runs passed | All 20 runs passed |
| The same, emulated with 20 ms late timers | All 20 runs passed | 8 of 20 runs failed, 8 of 60 cases, all at the check after Down (line 371): `assert 67 == 0` twice, `assert 22 == 0` six times |
| The same, emulated with 30 ms late timers, interleaved | 5 of 20 runs failed, 6 of 60 cases, all at the check after End (line 363, `assert 0.0 > 0`) | 15 of 20 runs failed, 17 of 60 cases: 5 at the check after Down (line 371), 12 at the check after End (line 363) |
| Ruff check and format, `uv run --locked pytest`, `uv build`, `check_package.py` | Passed; 1125 passed | Not run |

With the fix, the check after Down (line 371, the one CI saw) did not fail in
any of the 40 emulated runs. The check after End (line 363) still failed at
30 ms: End's scroll is Textual's own, this task leaves it alone, and a backlog
row records it.

Not checked: a Windows runner or machine, where the emulated delays are
assumed rather than measured; a native run in Ghostty, where the one-frame
difference is too short to judge by eye.

## Task 24: uppercase letter keys, 2026-10-30

Arch Linux (Omarchy 4.0.6, Hyprland 0.56.2, Wayland), Ghostty 1.4.0 at 80x24
(a wrapper script printed `TERM=xterm-ghostty size=80x24`), uv 0.13.4, Python
3.14.8, Textual 8.2.8, `fix/caps-lock-letters` at `18db80d`. At Jadon's
request, a coding agent drove `scripts/check_terminal.py` and took screenshots
with grim. `NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at ignored folders with no Workbench files.
wtype turned out not to send Shift+letter (first two rows), so Hyprland's
`send_key_state` sent the uppercase letters through the desktop's keymap, as
Shift+letter or as the letter with the Caps Lock modifier; lowercase text went
through wtype or `send_key_state`.

| Check | Observed |
| --- | --- |
| wtype `C`, then `return` and Return, then `Q` | No screen change; the app kept running, as in the entry below |
| Raw input in a key-logging Textual app | wtype `C` arrived as `ESC [27;;67u` and wtype `Q` as `ESC [27;;81u`; Textual named both `escape`, with the letter as the character. Through Hyprland, Shift+C arrived as `ESC [99;2;67u`, C with the Caps Lock modifier as `ESC [99;65;67u` and Shift+Q as `ESC [113;2;81u`; Textual named them `C`, `C` and `Q` |
| Shift+C on machine 1 | The child printed `Local child: fixture-zero; terminal stdin/stdout/stderr: [True, True, True]` and `Type return, or press Ctrl+C for an interruption check:` |
| `return` | "SSH exited with status 0. Machine 1: fixture-zero", with machine 1 still selected |
| C with the Caps Lock modifier, in a new run | The same child lines; `return` gave the same status line |
| Q with the Caps Lock modifier | `APP EXIT STATUS: 0` and the `check$` prompt |
| Shift+Q, in a new run | `APP EXIT STATUS: 0` and the `check$` prompt |
| Footer | `c Connect o Link a Add e Edit x Delete k Key r Check q Quit` in every screenshot of the browser |
| Discarded attempt | After wtype had typed, `send_key_state` failed with "key not found" until a real key press, and the next wtype text, meant for the shell, reached the app. Its `c` started the fixture-zero child; a `k` the app had read before the handoff ran K once the child returned; a later Return chose "Create a new key". `check_terminal.py` does not replace key setup, so the real ssh-keygen started for a key in the ignored SSH folder, which the native-check rules forbid. The window was closed at its passphrase prompt: no key file was written, no SSH command ran and no process was left |
| Files | No state file under `examples/` or the ignored folders; the `APPDATA` and SSH folders stayed empty |

Not checked: a physical keyboard, its Caps Lock key included (Hyprland sent
the Caps Lock modifier with each key); in a real terminal, letters other than
C and Q, Y and N in the dialogs among them, and capitals typed into the forms
(a test covers the add form; the edit form is the same `MachineForm`);
Windows Terminal after the fix.

## Uppercase letters in Ghostty, 2026-10-30

Arch Linux (Omarchy 4.0.6, Hyprland 0.56.2, Wayland), Ghostty 1.4.0 at 80x24
(`tput cols` and `tput lines` answered 80 and 24) with `TERM=xterm-ghostty`,
uv 0.13.4, Python 3.14.8, Textual 8.2.8, `main` at `d0d98b3`. At Jadon's
request, a coding agent drove `scripts/check_terminal.py`: it sent keys with
wtype and took screenshots with grim. `NO_COLOR` was unset and `APPDATA`,
`XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointed at empty ignored
folders. Uppercase letters were sent as Shift+letter.

| Check | Observed |
| --- | --- |
| Uppercase C on machine 1 | The screen did not change: no child started and machine 1 stayed selected |
| Uppercase Q | The app did not quit |
| Lowercase c | The child printed `Local child: fixture-zero; terminal stdin/stdout/stderr: [True, True, True]` and its prompt, `Type return, or press Ctrl+C for an interruption check:` |
| `return` | "SSH exited with status 0. Machine 1: fixture-zero", with the same machine selected |
| Lowercase q | The shell prompt came back; the app's exit status was 0 |
| Uppercase `CQ` typed at the bash prompt in the same window, without Return | The prompt echoed `CQ` |

Not checked: Caps Lock itself on Linux; the other letters in uppercase; a
physical keyboard; Windows, which the entry below covers.

Found later the same day (entry above): the sentence "Uppercase letters were
sent as Shift+letter" is wrong. wtype types a capital without Shift, and in
this setup Ghostty reports it to Textual as Escape with the letter as text, so
the first two rows do not show what uppercase C or Q did.

## Terminal fixture in Windows Terminal, 2026-10-30

Windows 11, Windows Terminal 1.25.2733.0 at 80x24 (read back from the screen)
running PowerShell 7.6.9, uv 0.13.6, Python 3.14.8, Textual 8.2.8, `main` at
`3406baf` (the merge of PR #36, which changed the fixture to start its child
with `sys.executable`). This run covers `check_terminal.py` on Windows after
the fix, which the Linux entry below left unchecked. At Jadon's request, a
coding agent on another machine drove the checks through a scheduled task in
the Windows workstation's desktop session and a Windows Terminal harness: it
sent keys with SendInput, read the screen text through UI Automation and took
screenshots with PrintWindow. `NO_COLOR` was unset and `APPDATA`,
`XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointed at empty ignored
folders. Caps Lock was on for the whole run (see the Caps Lock row).

| Check | Observed |
| --- | --- |
| `scripts/check_terminal.py` 1 | C: the child printed `Local child: fixture-zero; terminal stdin/stdout/stderr: [True, True, True]` and `Local child stderr is visible.`, and echoed `hello` as `Child input: hello`. `return` gave "SSH exited with status 0. Machine 1: fixture-zero", the same machine selected and the list focused (its border highlighted); Down selected fixture-seven, Up fixture-zero |
| `check_terminal.py` 2 | Tab highlighted the details pane; C started the fixture-seven child; `return` gave "SSH exited with status 7. Check the SSH client's message and alias; C retries." with "Machine 2: fixture-seven" on the next row, and focus came back to the list; Down selected fixture-interrupt, Up fixture-seven |
| `check_terminal.py` 3 | C, then Ctrl+C: the child printed `Child received Ctrl+C.` and the status read "SSH exited with status 130. Check the SSH client's message and alias; C retries. Machine 3: fixture-interrupt", wrapped after "; C"; the app kept running |
| `check_terminal.py` 4 | After each of two Ctrl+C presses the child printed `Child received Ctrl+C.` and `Child still owns the terminal; type return to finish.`; it echoed `still-here` as `Child input: still-here`; `return` gave "SSH exited with status 0. Machine 4: fixture-continue" |
| `check_terminal.py` 5 | On each simulated entry C showed its message and kept the selection: "SSH not found. Install OpenSSH and add it to PATH. Machine 5: fixture-missing"; "Could not start SSH. Check its installation and executable permissions." with "Machine 6: fixture-error" on the next row; "SSH interrupted. Press C to retry or Q to quit. Machine 7: fixture-keyboard". A second C left the same text and a byte-identical screenshot |
| `check_terminal.py` 6 | Q gave back the PowerShell prompt; on a second run, C on machine 1 and `return` gave "SSH exited with status 0. Machine 1: fixture-zero", then Ctrl+Q gave back the prompt. Both times `$LASTEXITCODE` was 0 and `echo hello` printed `hello`. After quitting, the shell's screen kept every child's output from the run and showed nothing of the app's screen |
| Status lines at 80 columns | The status 7, status 130 and start-failure messages took two rows, replacing the one-row "C: connect to the selected machine." line |
| Caps Lock | The console's key state reported Caps Lock on. A plain C on machine 1 did nothing, twice: no child and no status, while Up and Down worked. Shift+C and Shift+Q (lowercase letters while Caps Lock is on) worked for the rest of the run, and every C and Q above was sent that way. Inferred, not observed: Textual's Windows driver reports the typed character, so the app received `C`, which none of its lowercase letter bindings match |
| Files | `git status` was clean after the run; there was no state file, and the three ignored folders were still empty |

Not checked: real SSH targets (none approved); resizing during the fixture;
the smoke check on `examples/machines.example.toml`, `check_links.py` and
`check_keys.py` in Windows Terminal on this commit; the letter keys with Caps
Lock off in this run; whether Caps Lock has the same effect on Linux; whether
the second C on the simulated entries ran the action again (the screen did not
change).

## Linux desktop checks, 2026-10-30

Arch Linux (Omarchy 4.0.6, Hyprland, Wayland), Ghostty 1.4.0 with JetBrainsMono
Nerd Font at 9pt, 77x24 (the window opened for an 80x24 request; the fixtures
ran in a second window at 83x24), uv 0.13.4, Python 3.14.8, Textual 8.2.8,
PowerShell 7.6.9 for the Windows-script tests. A coding agent drove the checks
at Jadon's request: it sent keys with wtype, set window sizes in pixels with
Hyprland's resize dispatcher and read grim screenshots. Jadon did not watch
them. `NO_COLOR` was unset and `APPDATA`, `XDG_CONFIG_HOME` and
`SSH_WORKBENCH_SSH_DIR` pointed at empty ignored folders. Jadon approved
`https://example.com/` by name on 2026-10-30.

| Check | Observed |
| --- | --- |
| `uv run --locked pytest` without PowerShell | 12 failed, 1112 passed; every failure was a missing-PowerShell assertion (`PowerShell is needed to run the Windows script`, or `to parse` for the parse test) |
| Ruff check and format, `uv run --locked pytest` with `pwsh` 7.6.9, `uv build`, `check_package.py` | Passed; 1124 passed. The package check warned `Failed to hardlink files; falling back to full copy`: the temporary folder and uv's cache are on different file systems |
| `scripts/check_shells.py` piped to `sh -s`, locally | bash PASS; dash, zsh, fish and tcsh are not installed, so it exited 1 |
| Smoke check on `examples/machines.example.toml` | At 77x24 (`stty size` answered 24 77) the list, details and footer drew. Garden demo read "Can't check: SSH could not resolve the alias" (the SSH folder is empty); Studio box read Offline. With Up, Down, Tab, Page Up and Page Down the selection and details followed, and Tab moved focus to the details pane; R showed Checking, then Offline and Can't check. The run wrote `examples/machines.example.state.<computer>.json` beside the example file |
| Quit | Q gave back the shell prompt, `echo hello` echoed, Up recalled the line and the app's status was 0. Ctrl+Q on a second run gave back the prompt and `stty size` answered 24 77 |
| Resizes, set in pixels | At 56 and 59 columns the list moved above the details, the footer took two rows and the header counts shortened to `2  ○1 ◇1`. At 111 columns each list row showed where it connects ("garden-demo-host", "studio-box.example…"). At 19 rows the help line hid and the footer stayed. E open, a resize to 56 columns, then Escape: the browser behind the form had the narrow layout when the form closed |
| Ghostty's narrowest window | About 19 columns (139 logical px wide); the shell kept working |
| `scripts/check_links.py` 1 | Accepted, from the list and from the details: "[b]Only[/b] link browser request accepted. Machine 1: fixture-accepted", with `[b]` kept as text. Failed and error both read "browser request failed. Check the environment's browser setup and retry." with no private marker. The long message wrapped inside the details pane and the status area |
| `check_links.py` 2 to 4 | No links: "o Link" dimmed in the footer and O changed nothing. Picker: O opened "Open a link" with both links; Enter opened the first, Down then Enter the second; Escape closed it with the same selection and focus. Blocked: O read pending; a second O read "browser request still pending. Wait or Q to quit."; Up and Tab worked; Q exited at once, status 0 |
| `scripts/check_keys.py` | K on Box listed id_a.pub, id_lab.pub and "Create a new key: id_ed25519_box", then offered Linux/macOS/POSIX or Windows as the target system. With every step at status 0, the keygen, install (the POSIX command, 564 characters) and test children each took `return`; the result read "Key login works. The key is saved as this machine's key." and the Key field showed the working folder's `ssh/id_ed25519_box` |
| `check_keys.py --test-status 255` | "The key was installed, but key-only login failed (SSH exited with status 255). The key was not saved as this machine's key."; Key stayed Not set |
| `check_keys.py`, Ctrl+C at the install child | "Key setup interrupted during the install; login was not tested."; no test child ran. Q gave back the shell prompt after each of the three runs |
| `scripts/check_terminal.py` as on `main` | Every C read "SSH exited with status 1". `.venv/bin/python` is a symlink on Linux and the fixture resolved it, so the child ran under `/usr/bin/python3.14` and could not import `ssh_workbench`. The fix starts the child with `sys.executable` |
| `check_terminal.py` 1 to 3, after the fix | 1: after C the child printed `terminal stdin/stdout/stderr: [True, True, True]` and echoed input; `return` gave "SSH exited with status 0. Machine 1: fixture-zero", the same machine selected, the list focused, Up and Down working. 2: Tab, C, `return` gave "SSH exited with status 7. Check the SSH client's message and alias; C retries. Machine 2: fixture-seven", and Down then changed the selection. 3: Ctrl+C gave "SSH exited with status 130 ... Machine 3: fixture-interrupt" |
| `check_terminal.py` 4 to 6, after the fix | 4: after each of two Ctrl+C presses the child printed "Child still owns the terminal; type return to finish." and it echoed `still-here`; `return` gave status 0 for machine 4. 5: on each simulated entry, C pressed twice kept the selection: "SSH not found. Install OpenSSH and add it to PATH. Machine 5"; "Could not start SSH. Check its installation and executable permissions. Machine 6"; "SSH interrupted. Press C to retry or Q to quit. Machine 7". 6: after Q, and after Ctrl+Q on a second run, the shell prompt came back, `stty size` answered and `echo` printed |
| Real link: O on Garden demo's Documentation link, in an ignored copy of the example file that points it at `https://example.com/` | The status read "Documentation browser request accepted."; Chromium, the desktop's default browser, opened a new window titled "Example Domain" on the same workspace, showing example.com |

Not checked: real SSH targets (none approved); `check_terminal.py` on Windows
after the fix; `check_keys.py` with Ctrl+C at the keygen or test child, on the
alias machine, or with the Windows target; whether Page Up and Page Down
scroll the details (they fit the pane at 80x24); failed and error links from
the details pane; `check_shells.py` beyond bash (dash, zsh, fish and tcsh are
not installed); macOS; Windows Terminal; the Windows install script against a
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
