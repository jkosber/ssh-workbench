# Roadmap

What is being built now, what comes next, and what is already done. This is
the only backlog: Obsidian notes may link here but keep no second list. How a
task moves from here to a release is in [the workflow guide](workflow.md).

## Now

No task is in progress.

## Next

Nothing is planned yet; the [backlog](#backlog) holds candidates.

## Backlog

Deferred findings from reviews and manual checks, grouped by area. "From"
names the task, release or pull request where each was found; the context is
in [the archive](archive/roadmap-tasks-1-18.md) for Tasks 1-18 and in the pull
request for later ones. Each needs its own task before work starts.

### Interface

| Item | From |
| --- | --- |
| An empty schema 1 file is told to add `[[machines]]` entries, which that schema rejects; the hint should name `schema_version = 2` | 8 |
| Duplicate messages show internal locations such as `machine.links[1].name` | 9 |
| Changing a direct machine's ID makes SSH ask to trust its host key again; the form gives no hint | 9 |
| The first creation of `ssh-workbench.config` isn't named in the status line | 13 |
| The details pane does not show key-login state | 12 |
| Status colors are defined in three places (`StatusSymbol` CSS, `#machine-status.state-*` CSS and `SUMMARY_STYLES`); consistent today, they could share one set of `.state-*` rules | 20 |
| When the local `TERM` is terminal-specific (`xterm-ghostty`, `xterm-kitty`), full-screen programs on a host without that terminfo entry may reject it, and Ghostty's shell integration does not apply because Workbench runs `ssh` directly (not observed); a proposal is to run `ssh` with `TERM=xterm-256color` in that case, which `SetEnv TERM=xterm-256color` in the user's SSH config already does | [#36](https://github.com/jkosber/ssh-workbench/pull/36) |
| Keys Textual reads while C hands over the terminal (it keeps reading for up to 0.1 s) run as shortcuts when the child exits, however long it ran: a second C reconnects, Q quits, K opens key setup; seen only with synthetic typing (a `k` typed after `c` opened key setup when the child returned) | 24 |

### Status and aliases

| Item | From |
| --- | --- |
| A save during an R review can show Alias not found for an alias that review finds listed again, until its `ssh -G` answers | 21 |
| After a failed startup review, keeping a missing alias with a form save does not reach the state file, so the next R marks it missing again | 21 |
| A `Match exec` command that hangs outlives `ssh -G`'s 10 s timeout and, now that `ssh -G` runs detached, the terminal too; one can pile up per startup, R or K | 21 |

### Key setup

| Item | From |
| --- | --- |
| The login test also accepts keys from a `Host` entry in the user's SSH config that matches a direct machine's address (documented); the only fix, `-F none`, would drop the user's config for that address | 14 |

### Machine file and forms

| Item | From |
| --- | --- |
| URLs containing U+202E or U+200B pass validation; the display already escapes them | 0.1.0 review |
| A symlinked machine file is replaced by a regular file (write to the resolved path); untested, because this Windows account cannot create symlinks | 9 |
| A save that fails after the backup step has already replaced the previous `.bak` | 9 |
| Link names with line breaks or surrounding spaces do not survive the edit form | 9 |
| `Include` lines are missed when the SSH folder path contains `[` | 9 |
| `Host` names are read on the UI thread when a form opens; a slow network share would pause the screen | 9 |

### Exported aliases

| Item | From |
| --- | --- |
| An exported ID may equal another machine's alias, or a `Host` the user adds later; the form checks only the user's literal `Host` names at save | 13 |
| The Include check does not follow the user's own `Include` files, compares names case-sensitively, and counts an `Include` of a same-named file in another folder | 13 |
| Every `\` in a key path becomes `/`, also on Linux, where `\` is a legal file-name character | 13 |
| The generated file is not rewritten at startup or after an outside reload; a hand-set `export_alias` waits for the next save | 13 |
| `exports.py` copies `sshconfig.py`'s line parser and `store.py`'s error wording; the extra `chmod 600` calls repeat what the atomic write does | 13 |

### Tests and tooling

| Item | From |
| --- | --- |
| `test_no_external_actions_rejects_every_shared_boundary` passes even without a direct `subprocess.run` guard, because the guarded `Popen` fails first; assert that every guarded attribute is the fixture's own function | 7 |
| No test proves that `check_links.install_fixture_guards` and `package_smoke.reject_external_actions` install the shared guards | 7 |
| The strings test in `tests/test_tooling.py` misses inline children such as `["python", "-I", "-c", "..."]`; also reject a `"-c"` string | 7 |
| `package_smoke.guarded_boundaries()` inserts `scripts/` at the front of `sys.path`; load the list by path or append it instead | 7 |
| The `%(prog)` branch of the `--help` epilog has no test | 8 |
| A few schema tests match message prefixes instead of exact strings | 8 |
| The 60x20 many-links picker test does not press Escape; the 80x24 test covers Escape restoring selection and focus | 8 |
| `test_actions_wait_for_the_rebuilt_list` collects the active bindings without asserting them | 9 |
| The failure paths of `write_exports` and `add_include` have few tests | 13 |
| `test_windows_install_script_has_no_comment_lines` checks only lines that start with `#`, so it misses PowerShell `<# #>` block comments and trailing `#` comments | 23 |
| The release checklist does not ask to keep the output of step 6's `uv tool install`; the 0.3.3 evidence starts at `ssh-workbench --version` | 0.3.3 release |
| `test_ci_runs_once_for_a_push_to_a_pull_request` fails on harmless edits to the trigger block; a blank line inside the block ends the match early, so the failure reports missing lines | [#33](https://github.com/jkosber/ssh-workbench/pull/33) |
| `docs/testing.md` and `docs/workflow.md` say CI runs for every pull request; GitHub skips a pull request with a merge conflict | [#33](https://github.com/jkosber/ssh-workbench/pull/33) |
| The package check catches a `SyntaxWarning` only in the modules `--help` loads (`ssh_workbench`, `cli`, `config`); one elsewhere, such as `app.py`, passes because the `loader` child compiles it first and that child's stderr is unchecked; check that stderr, or add Ruff's `W605` (invalid escapes) to `select` | [#35](https://github.com/jkosber/ssh-workbench/pull/35) |
| `test_package_check_precompiles_dependencies_but_not_the_wheel` keeps only the last `uv pip sync` call and the last `uv pip install` call it finds; earlier calls of either kind go unchecked | [#35](https://github.com/jkosber/ssh-workbench/pull/35) |
| `scripts/check_terminal.py` replaces only Connect: K reaches the real `ssh-keygen` and then SSH through the real SSH config, although the script's docstring says it never invokes SSH; a discarded manual run started ssh-keygen this way | 24 |
| `test_return_preserves_scroll_and_literal_details` can check End's scroll before it starts: Textual defers it to the next refresh, `wait_for_scheduled_animations` then finds no animation to wait for, and `scroll_y` is still 0. [Task 25's emulation](validation.md#task-25-details-reset-before-the-next-frame-2026-10-30) with 30 ms late timers failed there in 6 of 60 cases with the fix and 12 of 60 before it | 25 |

## Done

Each finished task, the pull request that merged it and the release that
shipped it. The full acceptance criteria of Tasks 1-18 are in
[the archive](archive/roadmap-tasks-1-18.md), with their evidence in
[the archived log](archive/validation-tasks-1-18.md); later tasks keep theirs
in the pull request description.

| Task | Delivered | PR | Release |
| --- | --- | --- | --- |
| Bootstrap | Packaging, startup, help and version, tests, CI | - | - |
| 1 | Load and validate the project file | [#1](https://github.com/jkosber/ssh-workbench/pull/1) | 0.1.0 |
| 2 | Browse projects and their details | [#2](https://github.com/jkosber/ssh-workbench/pull/2) | 0.1.0 |
| 3 | Launch native SSH and return cleanly | [#3](https://github.com/jkosber/ssh-workbench/pull/3) | 0.1.0 |
| 4 | Error messages and opening links | [#4](https://github.com/jkosber/ssh-workbench/pull/4) | 0.1.0 |
| 5 | Usability checks and the 0.1.0 review | [#5](https://github.com/jkosber/ssh-workbench/pull/5) | 0.1.0 |
| 6 | Default machine file, user README, MIT license, release | [#6](https://github.com/jkosber/ssh-workbench/pull/6) | 0.1.0 |
| - | Record the 0.1.0 release | [#7](https://github.com/jkosber/ssh-workbench/pull/7) | 0.2.0 |
| 7 | Tooling cleanup | [#8](https://github.com/jkosber/ssh-workbench/pull/8) | 0.2.0 |
| 8 | Machines replace projects | [#9](https://github.com/jkosber/ssh-workbench/pull/9) | 0.2.0 |
| 9 | Add, edit and delete machines | [#10](https://github.com/jkosber/ssh-workbench/pull/10) | 0.2.0 |
| 10 | Live status | [#11](https://github.com/jkosber/ssh-workbench/pull/11), [#12](https://github.com/jkosber/ssh-workbench/pull/12) | 0.2.0 |
| 11 | Alias rename detection | [#13](https://github.com/jkosber/ssh-workbench/pull/13) | 0.2.0 |
| 12 | Key login setup | [#14](https://github.com/jkosber/ssh-workbench/pull/14) | 0.2.0 |
| 13 | Exported aliases | [#15](https://github.com/jkosber/ssh-workbench/pull/15) | 0.2.0 |
| 14 | Release 0.2.0, with real-target checks | [#16](https://github.com/jkosber/ssh-workbench/pull/16) | 0.2.0 |
| - | Record the 0.2.0 release and follow-up checks | [#17](https://github.com/jkosber/ssh-workbench/pull/17) | 0.2.1 |
| - | UI tests wait for pushed screens to mount | [#18](https://github.com/jkosber/ssh-workbench/pull/18) | 0.2.1 |
| 15 | Key setup fixes from real use | [#19](https://github.com/jkosber/ssh-workbench/pull/19) | 0.2.1 |
| 16 | Release 0.2.1 | [#20](https://github.com/jkosber/ssh-workbench/pull/20) | 0.2.1 |
| - | uv 0.13.4 security pin | [#21](https://github.com/jkosber/ssh-workbench/pull/21) | 0.2.2 |
| 17 | Ctrl+C, large-key and status fixes; Python 3.14.8 | [#22](https://github.com/jkosber/ssh-workbench/pull/22) | 0.2.2 |
| 18 | Release 0.2.2 | [#23](https://github.com/jkosber/ssh-workbench/pull/23) | 0.2.2 |
| 19 | Documentation and workflow guides; Tasks 1-18 archived | [#24](https://github.com/jkosber/ssh-workbench/pull/24) | 0.3.0 |
| 20 | UI makeover: theme, status header, responsive layout | [#25](https://github.com/jkosber/ssh-workbench/pull/25) | 0.3.0 |
| - | Release 0.3.0 | [#26](https://github.com/jkosber/ssh-workbench/pull/26) | 0.3.0 |
| 21 | Status and alias fixes; K's late answer | [#27](https://github.com/jkosber/ssh-workbench/pull/27) | 0.3.1 |
| - | Release 0.3.1 | [#28](https://github.com/jkosber/ssh-workbench/pull/28) | 0.3.1 |
| 22 | Key setup fixes: no empty key list, keys without a `.pub` named, Ctrl+C naming its step, plain-text Windows errors, a login shell check | [#29](https://github.com/jkosber/ssh-workbench/pull/29) | 0.3.2 |
| - | Release 0.3.2 | [#30](https://github.com/jkosber/ssh-workbench/pull/30) | 0.3.2 |
| 23 | Key setup follow-ups: a configured `.pub` names its key, the picker at 60x20, the Windows script's result order and one-line errors | [#31](https://github.com/jkosber/ssh-workbench/pull/31) | 0.3.3 |
| - | Release 0.3.3 | [#32](https://github.com/jkosber/ssh-workbench/pull/32) | 0.3.3 |
| - | CI runs once for a push to a pull request | [#33](https://github.com/jkosber/ssh-workbench/pull/33) | 0.3.4 |
| - | The repository is public; docs no longer call it private | [#34](https://github.com/jkosber/ssh-workbench/pull/34) | 0.3.4 |
| - | The package check precompiles its dependencies before its timed steps | [#35](https://github.com/jkosber/ssh-workbench/pull/35) | 0.3.4 |
| - | Manual checks cover Ghostty on Linux; the terminal fixture runs on Linux | [#36](https://github.com/jkosber/ssh-workbench/pull/36) | 0.3.4 |
| - | The validation log records the terminal fixture in Windows Terminal | [#37](https://github.com/jkosber/ssh-workbench/pull/37) | 0.3.4 |
| - | Eight deferred findings join the backlog; the validation log records uppercase letters in Ghostty | [#38](https://github.com/jkosber/ssh-workbench/pull/38) | 0.3.4 |
| 24 | Letter keys work with Caps Lock on or typed as capitals | [#39](https://github.com/jkosber/ssh-workbench/pull/39) | 0.3.4 |
| 25 | Details reset before the next frame, so the scroll test's check after Down no longer depends on a refresh | [#40](https://github.com/jkosber/ssh-workbench/pull/40) | 0.3.4 |
| - | Release 0.3.4 | [#41](https://github.com/jkosber/ssh-workbench/pull/41) | 0.3.4 |
| - | The validation log records Caps Lock in Windows Terminal | [#42](https://github.com/jkosber/ssh-workbench/pull/42) | Unreleased |

## Deferred ideas

Outside the current scope; each would need its own task: tmux integration,
automatic discovery, file transfer, cloud sync, embedded terminals, AI
features, Proxmox controls and a plugin framework.
