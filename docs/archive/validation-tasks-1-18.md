# Validation log archive: Tasks 1-18

> Archived on 2026-10-22. This is the dated evidence from the bootstrap to
> the 0.2.2 release, newest first, including CI runs and merges as they were
> recorded then. It is kept as a record and is no longer updated. New
> evidence goes in [the validation log](../validation.md).

## Task 18: 0.2.2 release, 2026-10-21

Branch `feat/task18-release-0.2.2`. Environment as in Task 17. Jadon asked to
release 0.2.2 and tag it, as 0.2.1 was, and to upgrade his own tool from the
tag.

| Check | Agent-observed result |
| --- | --- |
| `uv lock`, `uv sync --locked` | The lockfile changed only in Workbench's own version, 0.2.1 to 0.2.2 |
| Current-state lines | `pyproject.toml`, `AGENTS.md`, CONTRIBUTING's version table and the README install line name 0.2.2; Unreleased moved into `## 0.2.2 - 2026-10-21` |
| Ruff check and format, `uv run --locked pytest` | Passed; 53 files already formatted; 1046 passed |
| `uv build`, `scripts/check_package.py` | Source archive and wheel for 0.2.2; the package check passed |
| Installed tool | `uv tool install` of the wheel into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`), leaving Jadon's installed 0.2.1 alone; `--version` printed `ssh-workbench 0.2.2` |
| Installed-tool smoke in an owned 80x24 Windows Terminal window | With `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointing at empty ignored folders and a copy of the example machine file, the list, details and footer drew, Down selected the second machine, and Q exited with status 0 |

A fresh Opus review of PR #23 found no critical or important issue. Two of its
three minor findings were fixed; the changelog date stayed 2026-10-21, the
day the tag landed.

| Integration step | Result |
| --- | --- |
| [PR #23](https://github.com/jkosber/ssh-workbench/pull/23) CI on head `106ea7b` | [Push run 39717619068](https://github.com/jkosber/ssh-workbench/actions/runs/39717619068) passed. [PR run 39717622694](https://github.com/jkosber/ssh-workbench/actions/runs/39717622694) failed on Windows in its first attempt: `check_package.py`'s `loader` smoke child timed out after 10 s, with 1046 tests passing. A rerun of the failed job passed. The same code at `d666609` passed [push run 39717123516](https://github.com/jkosber/ssh-workbench/actions/runs/39717123516) and [PR run 39717127447](https://github.com/jkosber/ssh-workbench/actions/runs/39717127447) |
| Merge | Jadon approved it. Merged as **`c88f0f6`**, guarded on head `106ea7b`; tree identical to the tested head. The branch was deleted locally and on GitHub |
| Tag | Annotated `v0.2.2` on `c88f0f6`. `uv tool install` from the tag into ignored folders printed `ssh-workbench 0.2.2` |
| Merged `main` and tag CI | [Push run 39718654283](https://github.com/jkosber/ssh-workbench/actions/runs/39718654283) on `main` and [push run 39718667753](https://github.com/jkosber/ssh-workbench/actions/runs/39718667753) on the tag passed on Windows and Ubuntu, 1046 tests each |
| Jadon's tool | Upgraded from the tag; `ssh-workbench --version` prints 0.2.2, on Python 3.14.8 |

## Task 17: 0.2.2 fixes, 2026-10-21

Branch `feat/task17-0.2.2-fixes`. Environment as in Task 14, with Python
3.14.8. Jadon started the task with its scope.

Python moved from 3.14.7 to 3.14.8 in its own commit. The local virtual
environment had run 3.14.9 from a system install; it now runs uv's 3.14.8.

| Check | Agent-observed result |
| --- | --- |
| uv 0.13.4 downloads | 3.14.8 has Linux x86-64 and Windows builds; 3.14.9 has neither |
| `uv python install 3.14.8 --no-bin`, `uv sync --locked` | The environment was recreated on 3.14.8 with the locked packages; `ssl.OPENSSL_VERSION` is OpenSSL 3.5.9 |
| Re-inspection | The changelog and the CPython `v3.14.7..v3.14.8` diff change no code that the 3.14.7 notes rely on; see [architecture](../architecture.md#sources) |
| Ruff check and format, `uv run --locked pytest` | Passed; 53 files already formatted; 1021 passed |
| `uv build`, `scripts/check_package.py` | Source archive and wheel for 0.2.1; the package check passed |

The seven form tests, in a test-only commit, with a scratch pytest plugin that
replaces `pilot.pause()`'s CPU-idle wait with one event-loop yield:

| Run | Result |
| --- | --- |
| `tests/test_forms.py` before | 7 failed, 34 passed, three times out of three: the six direct-machine cases of `test_inline_error_names_the_field_and_blocks_saving` and `test_huge_port_is_an_error_not_a_crash` read an empty error |
| Fix | Each waits until the field shows an error, then asserts it exactly as before |
| `tests/test_forms.py` after | 41 passed, three times out of three |
| Whole suite under the plugin | 1021 passed after the fix; 1043 passed at the end of the task |

Native Ctrl+C check before the code, in an owned 80x24 Windows Terminal
window. A probe ran each tool through Workbench's own `find_ssh`,
`find_ssh_keygen` and `run_native`, with a callable SIGINT handler that
counts, as K's shield does. Local children only, three runs each:

| Tool and step | Exit status | Ctrl+C seen by Workbench | Exit after Ctrl+C |
| --- | --- | --- | --- |
| Windows OpenSSH 9.5p2 `ssh -F none`, waiting on a local ProxyCommand that sleeps 60 s | 0 | Yes, once | 8-10 ms |
| `ssh-keygen` at its passphrase prompt | 255 | No | 8-11 ms; no key file written |

Neither tool carries on after Ctrl+C. The status 0 that read as "Key login
works." comes with a Ctrl+C that Workbench sees, so counting it fixes that
case. The passphrase prompt reads Ctrl+C as a key and never passes it on,
so that 255 stays a status, as it was in 0.2.1. SSH's own password and
passphrase prompts were not checked: they need a server.

Tests first. Each fix's tests were committed failing before its
implementation:

| Fix | Failing first | Guards that passed before, as intended |
| --- | --- | --- |
| Ctrl+C | `test_the_shield_counts_each_ctrl_c`; six cases of `test_ctrl_c_during_a_step_is_an_interruption_whatever_its_status` (keygen, install and test, each with status 0 and 255); `test_ctrl_c_between_steps_stops_the_later_ones`; `test_an_earlier_ctrl_c_does_not_interrupt_the_next_key_setup`; the Ctrl+C-with-status-0 case of `test_an_alias_login_test_interrupted_with_an_unnamed_key_gives_no_hint` | That test's interrupted-status case; `test_posix_install_counts_an_active_copy_beside_a_commented_one` and its Windows twin, both orders each |
| Oversized key | `test_windows_command_is_refused_only_past_what_cmd_accepts`; `test_a_key_too_large_for_windows_is_refused_before_the_handoff` | `test_a_key_too_large_for_windows_still_installs_on_posix` |
| Status rounds | `test_a_timer_round_waits_for_a_check_still_running`; `test_r_is_dimmed_until_every_ssh_g_has_answered`; `test_r_after_a_save_still_waits_for_the_earlier_ssh_g` | `test_checks_that_cannot_start_leave_the_timer_and_r_working` |

The cmd.exe limit, measured locally and read in the Windows OpenSSH source:

| Question | Result |
| --- | --- |
| What cmd.exe counts | `cmd.exe /c rem xxxx...` ran up to a whole command line of 8191 characters, its own path and `/c` included, and printed "The command line is too long." past it, with three different prefixes |
| What Windows sshd runs | Win32-OpenSSH (`w32-doexec.c`, `pwd.c` on `latestw_all`) starts the default shell as `"c:\windows\system32\cmd.exe" /c "<command>"`, 35 characters around the command, so the command may have 8156. Read, not run against a real server |
| Largest RSA keys that fit | 6608 bits with no comment and 6008 bits with a 100-character one; a 4096-bit key with a 100-character comment makes 7306 characters. Task 15's figures counted only the command against 8191 |

| Check | Agent-observed result |
| --- | --- |
| Ruff check and format, `uv run --locked pytest` | Passed; 53 files already formatted; 1043 passed |
| `uv build`, `scripts/check_package.py`, `--help`, `--version` | Passed; `ssh-workbench 0.2.1` |
| `scripts/check_keys.py --test-status 0` in an owned 80x24 Windows Terminal window | Box with `id_a.pub`: the install child finished; Ctrl+C at the test child, which then exited 0, read "The key was installed, but the login test was interrupted. The key was not saved as this machine's key."; the machine file gained no key. K again, Ctrl+C at the install child, which exited 0: "Key setup interrupted.", and no test child ran. Q exited with status 0 |
| Smoke with a copy of the example file | `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointed at empty ignored folders: the list and statuses drew, R checked again, and Q exited with status 0 |
| [PR #22](https://github.com/jkosber/ssh-workbench/pull/22) CI on head `40e52a2` | [Push run 39711743203](https://github.com/jkosber/ssh-workbench/actions/runs/39711743203) and [PR run 39711767394](https://github.com/jkosber/ssh-workbench/actions/runs/39711767394) passed on Windows and Ubuntu with Python 3.14.8, 1043 tests each |

A fresh Opus review of the whole branch found no critical or important issue,
reproduced the test-first failure counts and the form tests under its own
no-idle plugin, and listed five minor findings. Four were fixed, the first two
test first:

| Finding | Fix and test |
| --- | --- |
| Windows runs the parent's Ctrl+C handler on a thread of its own, so it can arrive after a test that exits 0, which would again read "Key login works." and save the key | The count is taken before the handoff and read again after the terminal is handed back. `test_a_ctrl_c_that_reaches_workbench_after_the_test_still_counts` (Ctrl+C during the resume) and `test_ctrl_c_while_the_terminal_is_handed_over_stops_every_step` (during the suspend) failed first with "Key login works." |
| The footer kept showing R as available after R started a review | The round refreshes the bindings when its review starts. `test_the_footer_dims_r_while_the_review_it_started_runs` timed out waiting for the dimmed key first |
| "`ssh -G` runs never overlap" claimed too much: one round runs one per alias, and K's own `ssh -G` is not counted | README, changelog, architecture and the code comment now say R never starts a second set beside the first |
| README, changelog and architecture described SSH's own password prompt, which was not checked | They name ssh-keygen's passphrase prompt and say SSH's prompts are unchecked |

Left as a 0.2.x note: two Task 10 candidate lines are stale; "the check could
not start" now has a test, and "or timer round" was already guarded before
this task. Full suite after the fixes: 1046 passed. Task 18 corrected both
lines.

| Integration step | Result |
| --- | --- |
| [PR #22](https://github.com/jkosber/ssh-workbench/pull/22) CI on head `9cc996b` | [Push run 39714027352](https://github.com/jkosber/ssh-workbench/actions/runs/39714027352) and [PR run 39714032314](https://github.com/jkosber/ssh-workbench/actions/runs/39714032314) passed on Windows and Ubuntu, 1046 tests each |
| Merge | Jadon approved it. Merged as **`b8e37c6`**, guarded on head `9cc996b`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39715258548](https://github.com/jkosber/ssh-workbench/actions/runs/39715258548) passed on Windows and Ubuntu, 1046 tests each |

## uv 0.13.4 security pin, 2026-10-21

Branch `ci/uv-0.13.4`. Windows 11, Python 3.14.9, uv 0.13.4. Jadon asked for uv
to be updated wherever it is used, after uv's emSign root-certificate advisory
GHSA-hq85-5cpj-mr62.

| Check | Agent-observed result |
| --- | --- |
| Drift test | Failed after only `pyproject.toml` moved to `uv_build>=0.13.4,<0.14.0`; passed once the CI pin matched `0.13.4` |
| `uv lock --check`, `uv sync --locked` | Lock unchanged; 17 packages |
| Ruff check and format, `uv run --locked pytest` | Passed; 53 files already formatted; 1021 passed |
| `uv build`, `scripts/check_package.py` | Source archive and wheel for 0.2.1 with no `uv_build` range warning; package check passed |

No native terminal check was needed: no application code changed.

| Integration step | Result |
| --- | --- |
| [PR #21](https://github.com/jkosber/ssh-workbench/pull/21) CI on head `6f8a18f` | [Push run 39699491885](https://github.com/jkosber/ssh-workbench/actions/runs/39699491885) and [PR run 39699497858](https://github.com/jkosber/ssh-workbench/actions/runs/39699497858) passed on Windows and Ubuntu with uv 0.13.4, 1021 tests each |
| Merge | Merged as **`9429020`**, from another session; tree identical to the tested head. The branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39702270514](https://github.com/jkosber/ssh-workbench/actions/runs/39702270514) passed on Windows and Ubuntu, 1021 tests each |

## Task 16: 0.2.1 release, 2026-10-21

Branch `feat/task16-release-0.2.1`. Environment as in Task 14. Jadon asked to
release 0.2.1 and tag it.

| Check | Agent-observed result |
| --- | --- |
| `uv lock`, `uv sync --locked` | The lockfile changed only in Workbench's own version, 0.2.0 to 0.2.1 |
| Current-state lines | `pyproject.toml`, `AGENTS.md`, CONTRIBUTING's version table and the README install line name 0.2.1; Unreleased moved into `## 0.2.1 - 2026-10-21` |
| Ruff check and format, `uv run --locked pytest` | Passed; 1021 passed |
| `uv build`, `scripts/check_package.py` | Source archive and wheel for 0.2.1; the package check passed |
| Installed tool | `uv tool install` of the wheel into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`), leaving Jadon's installed 0.2.0 alone; `--version` printed `ssh-workbench 0.2.1` |
| Installed-tool smoke in an owned 80x24 Windows Terminal window | With `SSH_WORKBENCH_SSH_DIR` and `APPDATA` pointing at empty ignored folders and a copy of the example machine file, the list, details and footer drew; Q exited with status 0 |

PR #20's PR run on head `c9a270b`, a docs-only commit, failed on Windows with
1 failed and 1020 passed:
[run 39651258950](https://github.com/jkosber/ssh-workbench/actions/runs/39651258950).
The same commit's
[push run 39651250887](https://github.com/jkosber/ssh-workbench/actions/runs/39651250887)
passed with 1021 tests on each system.

| Item | Result |
| --- | --- |
| Failure | `test_startup_shows_checking_then_each_result` set `ListView.index = 2`, paused once, and read the previous machine's status, "● Online: 192.0.2.40" |
| Cause | Setting the index posts `ListView.Highlighted` to the list; it reaches the app, which updates the details, one parent at a time. `pilot.pause()` first waits for callbacks it queued on every widget, so it can finish while the message is still climbing. Only its CPU-idle heuristic then covered the gap |
| Reproduction | A scratch plugin replaced that heuristic with one yield. The test then failed every time, three out of three, reading the previous machine's status |
| Fix (tests only) | The loop waits until the details show the selected machine's ID, then asserts the status text exactly. It passed three times out of three under the plugin; the full suite passed, 1021 tests |
| Other latent cases | Under the plugin, seven `tests/test_forms.py` cases fail the same way; they are in the roadmap's 0.2.x candidates |

| Integration step | Result |
| --- | --- |
| [PR #20](https://github.com/jkosber/ssh-workbench/pull/20) CI on head `e4057ac` | [Push run 39653184964](https://github.com/jkosber/ssh-workbench/actions/runs/39653184964) and [PR run 39653193959](https://github.com/jkosber/ssh-workbench/actions/runs/39653193959) passed on Windows and Ubuntu, 1021 tests each |
| Merge | Merged as **`bfb3789`**, guarded on head `e4057ac`; tree identical to the tested head |
| Tag | Annotated `v0.2.1` on `bfb3789`; installing from the tag on GitHub prints `ssh-workbench 0.2.1` |
| Merged `main` and tag CI | [Main push run 39653931297](https://github.com/jkosber/ssh-workbench/actions/runs/39653931297) and [tag push run 39653940685](https://github.com/jkosber/ssh-workbench/actions/runs/39653940685) passed on Windows and Ubuntu, 1021 tests each |

## Task 15: 0.2.1 real-use fixes, 2026-10-21

Branch `feat/task15-real-use-fixes`. Environment as in Task 14. Jadon chose the
fixes and approved the real checks on the Windows laptop.

| Check | Agent-observed result |
| --- | --- |
| Tests first | Each fix's tests failed before its implementation commit: `test_windows_install_script_hides_progress` (line 2 was `$key`); six POSIX and three Windows commented-copy cases, and `test_posix_install_command_text`; both unnamed-key cases of `test_an_alias_test_passing_with_an_unnamed_key_says_so`; `test_a_failed_login_test_does_not_save_the_key`; seven `test_interrupted_statuses` cases and three new cases of `test_a_failed_step_stops_the_later_ones` |
| Guards that passed before their fix, as intended | `#` inside a key's options still counts as installed (POSIX and Windows); a configured key keeps the plain "Key login works."; a machine's own key that fails its test gets no save note |
| Existing assertions changed | `test_posix_install_command_text`: the script now skips comment lines, and after the review runs both greps with `LC_ALL=C`. `test_a_failed_login_test_still_saves_the_installed_key` became `test_a_failed_login_test_does_not_save_the_key`: Jadon reversed the Task 12 ruling to save a key once installed |
| Ruff check and format, `uv run --locked pytest` | Passed; 1021 passed after the review's fixes (993 before the task) |
| `uv build`, `scripts/check_package.py` | Passed |
| An invalid escape | The first Windows comment filter wrote `\s` in a normal Python string, and Python 3.14 warned at compile time. The source now writes `\\s`; the script still holds `^\s*#`, and the key tests pass with `SyntaxWarning` as an error |

Evidence gathered before the code:

| Question | Result |
| --- | --- |
| What prints the progress record, on the Windows laptop | The install script with its key check forced and its `Set-Acl` run on a new temporary file printed one CLIXML block with three "Preparing modules for first use." records, both times. With `$ProgressPreference = 'SilentlyContinue'` on line 2 it printed none, both times. The script without `Set-Acl` printed none either way. The temporary files were removed; the real key file was not touched |
| Which statuses Ctrl+C leaves, local tools only | In an owned Windows Terminal window, with the parent shielded as K's handoff shields it: `ssh-keygen` at its passphrase prompt exited 255, and `ssh` waiting on a local ProxyCommand exited 0, twice each. Neither can mark an interruption, so `interrupted` keeps -SIGINT, 0xC000013A and 0xFFFFFFFF, the status Task 14 saw when Ctrl+C stopped a login test |

`scripts/check_keys.py` in an owned 80x24 Windows Terminal window, with local
children only:

| Step | Result |
| --- | --- |
| Box, new key, the test child exits 255 | The keygen, install and test children ran. "The key was installed, but key-only login failed (SSH exited with status 255). The key was not saved as this machine's key."; the machine file gained no key |
| Box, `id_a.pub`, the test child exits 4294967295 | "The key was installed, but the login test was interrupted. The key was not saved as this machine's key." |
| Garden, an alias with `IdentitiesOnly`, `id_a.pub`, the test child exits 0 | The picker showed the `IdentityFile` note. "Key-only login works, but SSH may have used another key. Your SSH config offers only its own keys for garden-host (IdentitiesOnly); add this line under Host garden-host: IdentityFile <path>" |

Real check on the Windows laptop. The branch build was installed into ignored
folders and the administrator key file copied aside first. K ran with the
alias's configured key and the Windows target:

| Step | Result |
| --- | --- |
| First attempt | The install exited 255 after ssh reported a connection timeout; the status had shown Offline. The key file was unchanged |
| R, then K again | Online via alias. "the key was already installed.", "testing key-only login.", then "Key login works.", with no CLIXML in the handoff. This shows the new script works on Windows PowerShell 5.1; the absence of the record alone proves nothing, so the evidence above is what shows the fix. The administrator file stayed byte-identical, with its ACL unchanged, and its copy was deleted |

A fresh whole-branch review found no critical issue. Fixed from it, test first:

| Finding | Fix and test |
| --- | --- |
| The new grep pipeline missed the key when `authorized_keys` held non-UTF-8 bytes, so in a UTF-8 locale K appended a duplicate | Both greps run with `LC_ALL=C`. `test_posix_install_finds_a_key_whose_comment_is_not_utf8` failed first with "key installed." |
| The Windows command grew by about 480 characters, so a 6144-bit RSA key with a 40-character comment no longer fit (8250 characters) | The comment inside the script moved to Python. `test_windows_command_fits_cmd_with_a_6144_bit_rsa_key_and_a_comment` failed first. The largest key that fits is now 6704 bits with no comment and 6104 bits with a 100-character one (0.2.0: 7384 and 6760) |
| README and changelog said Workbench always reports Ctrl+C as an interruption | Both now name the Windows statuses that still show as they are |

Also corrected: the roadmap's RSA figures, its stale "reachable only by a
fake", and the comment on `ssh.interrupted`. The review's other findings are
in the roadmap's 0.2.x candidates.

| Integration step | Result |
| --- | --- |
| [PR #19](https://github.com/jkosber/ssh-workbench/pull/19) CI on head `2032157` | [Push run 39641216603](https://github.com/jkosber/ssh-workbench/actions/runs/39641216603) and [PR run 39641251724](https://github.com/jkosber/ssh-workbench/actions/runs/39641251724) passed on Windows and Ubuntu, 1021 tests each |
| Merge | Merged as **`ca7d984`**, guarded on head `2032157`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39641969719](https://github.com/jkosber/ssh-workbench/actions/runs/39641969719) passed on Windows and Ubuntu, 1021 tests each |

## Screen waits in UI tests, 2026-10-21

[PR run 39621203373](https://github.com/jkosber/ssh-workbench/actions/runs/39621203373)
on PR #17's first head `5e9368a`, a docs-only commit, failed on Windows with 1
failed and 992 passed. `test_an_alias_offers_its_own_keys_first_and_explains_others`
raised `NoMatches` for `OptionList` on `KeySetup`. The same commit's
[push run 39621197515](https://github.com/jkosber/ssh-workbench/actions/runs/39621197515)
passed with 993 tests on each system.

| Item | Result |
| --- | --- |
| Order of errors | The test's own `query_one(OptionList)` failed first. The app's `KeySetup.on_mount` then raised the same `NoMatches` while the screens closed, and `run_test` re-raised it on exit |
| Cause | `push_screen` makes the new screen current at once; the screen composes in its own task. The helpers waited only for `isinstance(app.screen, X)`. On an alias, K pushes the picker from a thread's message, which can arrive during a `pilot.pause()` after that pause has already waited for the screen, so `picker()` could return before the picker had any widgets. A scratch script showed `app.screen` as an unmounted `KeySetup` with no `OptionList` right after `push_screen` |
| Reproduction | A scratch pytest plugin delayed the modal screens' compose by 0.3 s and the alias's resolve by 0.3 s. The test then failed the same way on every run: the picker was pushed during a pause, and the pause ended with the picker current and not mounted |
| Fix (tests only) | Five UI test files get `showing(app, kind)`, which also requires `app.screen.is_mounted`; all 21 of their waits for a screen to appear use it. `picker_open` in `tests/test_link_actions.py` checks the same. Only the thread-driven K wait was reproduced; a screen pushed by a key has a narrower window, which a review pointed out for `picker_open` |
| After the fix | The reproduction passed three times out of three; the five UI test files passed under it, 104 tests |
| `uv run --locked pytest`, Ruff check and format | 993 passed; Ruff passed |
| [PR #18](https://github.com/jkosber/ssh-workbench/pull/18) CI on first head `1672a5c` | [Push run 39632124615](https://github.com/jkosber/ssh-workbench/actions/runs/39632124615) and [PR run 39632133087](https://github.com/jkosber/ssh-workbench/actions/runs/39632133087) passed on Windows and Ubuntu, 993 tests each |
| CI on head `d31c47d`, after the review's `picker_open` fix | [Push run 39633064673](https://github.com/jkosber/ssh-workbench/actions/runs/39633064673) and [PR run 39633072307](https://github.com/jkosber/ssh-workbench/actions/runs/39633072307) passed on Windows and Ubuntu, 993 tests each |
| Merge | Merged as **`497c5a8`**, guarded on head `d31c47d`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39633874192](https://github.com/jkosber/ssh-workbench/actions/runs/39633874192) passed on Windows and Ubuntu, 993 tests each |

## 0.2.0 follow-up checks, 2026-10-21

After the release, Jadon approved two more real targets for live status, K and
C with the 0.2.0 tool.

| Target | Details |
| --- | --- |
| Proxmox VE 9.2 host | Root's `~/.ssh/authorized_keys` is a link to `/etc/pve/priv/authorized_keys` on the Proxmox cluster file system |
| Windows 11 laptop | Windows OpenSSH 9.5p2, Windows PowerShell 5.1 and the default cmd shell; the user is an administrator |

Workbench was the 0.2.0 tool installed from the `v0.2.0` tag. It ran in an
owned 80x24 Windows Terminal window on the Windows workstation, with a machine
file in ignored `.local/` and the real SSH folder. Both targets' key files were
copied aside first, with their hashes, modes and ACL recorded.

| Step | Result |
| --- | --- |
| Live status | Both alias machines showed Online via alias; a direct machine for the Proxmox host showed Online with its address |
| K on the Proxmox alias with its configured key, POSIX | "the key was already installed.", then "Key login works." The script's `touch` and `chmod 600` went through the link into the cluster file system without error. The contents, mode 600 and the link were unchanged; only the modification time moved |
| First C of the direct machine, user `root` | No `Host` entry matches its address. SSH asked to trust the host key under the machine's ID and listed the address's existing record. The fingerprint matched that record, so yes was typed, and the remote prompt was reached. `exit` returned with status 0, and `known_hosts` gained one line under the ID |
| K on the direct machine: new key, POSIX | "key installed.", then "Key login works. The key is saved as this machine's key." The linked file gained exactly one line, with the earlier bytes unchanged. With no matching `Host` entry, the login test offered only the new key: `ssh -G` with the test's options lists one `IdentityFile`. A login with no config file and only the new key also succeeded |
| C on the direct machine again | Connected with only the saved key; status 0 |
| K on the Windows alias with its configured key, Windows | "the key was already installed.", then "Key login works." `administrators_authorized_keys` stayed byte-identical. Its ACL was already SYSTEM and Administrators only, and stayed unchanged |
| K on the Windows alias: new key, Windows | The picker showed the `IdentityFile` note. The administrator branch printed "key installed."; the file gained exactly one line ending in CRLF and kept its ACL. The login test printed "Key login works.", which the configured key passed: the alias's config doesn't name the new key. A login with no config file and only the new key proved the new one |
| C on the Windows alias, then `exit` at the cmd prompt | Returned with status 0 |
| Q | Exited with status 0 |

Both Windows installs wrote the CLIXML progress record again after
Workbench's own line, and the alias's login test again passed with the
configured key. Both match existing 0.2.x candidates: Task 14's CLIXML record
and Task 12's alias login test. There is no new finding.

Not tested:

- the Windows branch for a user who is not an administrator, on a real target;
- macOS;
- O on a Linux desktop.

Afterwards, each key file was restored to its original bytes after
confirming it held exactly those bytes plus the one test line. The link, modes
and ACL were unchanged. The copies, both test keys and the direct machine's
`known_hosts` line were deleted.

Earlier the same day, with Jadon's approval, Task 14's leftovers were deleted:

- the three pre-check copies;
- the test machine's host-key record;
- uv, its Python and the 0.2.0 tool on the Linux target.

Each copy was confirmed identical to its live file first.

| Integration step | Result |
| --- | --- |
| [PR #17](https://github.com/jkosber/ssh-workbench/pull/17) CI on first head `5e9368a` | [Push run 39621197515](https://github.com/jkosber/ssh-workbench/actions/runs/39621197515) passed on Windows and Ubuntu, 993 tests each. [PR run 39621203373](https://github.com/jkosber/ssh-workbench/actions/runs/39621203373) failed on Windows from a flaky test; see [Screen waits in UI tests](#screen-waits-in-ui-tests-2026-10-21) |
| CI on head `c72a66a` | [Push run 39621698413](https://github.com/jkosber/ssh-workbench/actions/runs/39621698413) and [PR run 39621707333](https://github.com/jkosber/ssh-workbench/actions/runs/39621707333) passed on Windows and Ubuntu, 993 tests each. The push run's jobs finished at 15:03 UTC, but GitHub showed the run in progress until 15:32 |
| Merge | Merged as **`db0f922`**, guarded on head `c72a66a`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39625837877](https://github.com/jkosber/ssh-workbench/actions/runs/39625837877) passed on Windows and Ubuntu, 993 tests each |

## Task 14: 0.2.0 release, 2026-10-21

Branch `feat/task14-release-0.2.0`. Windows 11 Home Insider Preview build
26340, PowerShell 7.6.7, Microsoft Windows Terminal 1.25.2733.0, Windows
OpenSSH 9.5p2, Python 3.14.7, Textual 8.2.8, uv 0.13.4, Ruff 0.16.10 and
pytest 9.1.1. Jadon approved each real target and change below on 2026-10-21.

| Check | Agent-observed result |
| --- | --- |
| `uv lock`, `uv sync --locked` | The lockfile changed only in Workbench's own version, 0.1.0 to 0.2.0 |
| Ruff check and format | Passed; 53 files already formatted |
| `uv run --locked pytest` | 993 passed |
| `uv build`, `scripts/check_package.py` | Source archive and wheel for 0.2.0; the package check passed |
| Installed tool | `uv tool install` of the wheel into ignored folders (`UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`), leaving the installed 0.1.0 alone; `--version` printed `ssh-workbench 0.2.0` |

Real-target checks used that installed tool in an owned 80x24 Windows Terminal
window, a machine file in ignored `.local/task14-session/` and the real SSH
folder. Before any change, the SSH config, the Linux target's
`authorized_keys` and the Windows `administrators_authorized_keys` were copied
aside, with their hashes, permissions and ACL recorded.

| Step | Result |
| --- | --- |
| Live status | An alias machine showed Online via alias; direct machines showed Online with their address |
| First Connect of a direct machine for this workstation's own SSH server | SSH asked to trust the host key under the machine's ID and listed the names that key is already known by. Answered no: nothing was trusted and no login ran. Workbench returned with status 255 |
| First Connect of a direct machine for the Linux target | Status 255 without a question. The user's SSH config has a `Host` entry matching that address with `StrictHostKeyChecking yes`, and no key was recorded under the machine's ID, so OpenSSH refused as configured. The README now explains this and the one-time `StrictHostKeyChecking=ask` command |
| That command, then C | Before yes was typed, the fingerprint shown was compared with the key already recorded for the address and matched. C then reached the remote prompt; `exit` returned with status 0 and the same machine selected |
| K on that direct machine: new key, POSIX | `ssh-keygen` asked for the passphrase, left empty for this test key. Install and test needed no password, because the matching `Host` entry names another authorized key: "Key login works. The key is saved as this machine's key." `authorized_keys` gained one line, the first unchanged, modes 700 and 600. A login with no config file and only the new key succeeded |
| E, export ticked, Ctrl+S, Y | The question named the config path and the exact line. The real config gained `Include ssh-workbench.config` and CRLF at the top; every other byte matched the original, and `config.ssh-workbench.bak` was byte-identical to the original. Details: `Direct, exported as ssh <id>` |
| `ssh <id>` in a plain terminal | Reached the remote prompt with no question; `ssh -G` showed the generated `HostName`, `User`, `HostKeyAlias` and only the new key |
| K on an alias whose key was already set up | "the key was already installed.", then "Key login works."; no line was added |

Linux natively: uv 0.13.3 and the same wheel (identical SHA-256) were installed
on the Linux target, Linux Mint 22.3 with OpenSSH 9.6p1; uv supplied Python
3.14.8 and Textual 8.2.8. Workbench ran there in a terminal opened with
`ssh -t` from the same Windows Terminal window, with an alias machine for the
Windows workstation:

| Step | Result |
| --- | --- |
| Start | List and details drew at 80x24; Online via alias |
| C, then `exit` at the PowerShell prompt | Returned with status 0 and the same machine selected |
| K: new key, Windows | The picker listed the alias's key first and showed the `IdentityFile` note for the new key. After `ssh-keygen`, the install printed "SSH Workbench: key installed." from the administrator branch, then "Key login works.", which another key passed: the alias's config doesn't name the new key |
| Windows result | `administrators_authorized_keys` gained exactly one line ending in CRLF, earlier lines unchanged; its ACL stayed SYSTEM and Administrators only, protected. A login from the Linux target with no config file and only the new key succeeded |
| Q | Exited with status 0 |

Not tested: macOS, and O on a Linux desktop.

New minor findings, added to the roadmap's 0.2.x candidates:

| Finding | Evidence |
| --- | --- |
| Windows PowerShell wrote a CLIXML progress record ("Preparing modules for first use.") into the handoff terminal after "key installed." | Seen once in the Windows install above |
| The login test also accepts keys from a `Host` entry matching a direct machine's address | The Linux target's matching entry names another authorized key; the separate new-key-only login above is what proved the new key. Documented in the README |
| A login test interrupted with Ctrl+C on Windows reported "SSH exited with status 4294967295" instead of an interruption | The check's own prompt detector matched an earlier passphrase line and sent Ctrl+C; the step was repeated and passed |

Afterwards both test keys were deleted and their lines removed: each
authorized-keys file was truncated back to its original length after confirming it held the
original bytes plus that one line, and compared identical to its copy, with the
ACL and modes unchanged. The generated `ssh-workbench.config` was deleted,
because it named the session's machine file. The `Include` line stays, as
approved; SSH ignores it while that file is missing, and the alias still logged
in. The test machine's host-key record, uv and the 0.2.0 tool on the Linux
target, and the pre-check copies were kept until after the merge; the
[follow-up checks](#020-follow-up-checks-2026-10-21) record their deletion.

Two fresh reviews, one for spec compliance and one for docs quality, found no
code issue. Fixed in the docs: the README install line still named `v0.1.0`;
"SSH offers only that key" in the README and the changelog's Security list,
which a matching `Host` entry's `IdentityFile` contradicts; and stale
current-state lines in CONTRIBUTING's version table, AGENTS and the
architecture's SSH config rule. Wording fixes covered the key type in the
strict-checking message, which keys the login test can pass with, and this
record.

| Integration step | Result |
| --- | --- |
| [PR #16](https://github.com/jkosber/ssh-workbench/pull/16) CI on head `b6e22db` | [Push run 39575331572](https://github.com/jkosber/ssh-workbench/actions/runs/39575331572) and [PR run 39575338295](https://github.com/jkosber/ssh-workbench/actions/runs/39575338295) passed on Windows and Ubuntu, 993 tests each |
| Merge | Merged as **`155808e`**, guarded on head `b6e22db`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39575912699](https://github.com/jkosber/ssh-workbench/actions/runs/39575912699) passed on Windows and Ubuntu, 993 tests each |
| Tag | Annotated `v0.2.0` on `155808e`, pushed. `uv tool install` from the tag into ignored folders printed `ssh-workbench 0.2.0`. No GitHub Release; the repository stays private |

## Task 13: exported aliases, 2026-10-21

Branch `feat/task13-exported-aliases`. Environment as in Task 8. The real
`~/.ssh/config` was not read or changed.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | `tests/test_exports.py` and `tests/test_exports_ui.py` failed at collection for the missing module and prompt; the `export_alias` schema tests and the `host_names` skip test failed. One existing assertion changed: the exact list of allowed machine fields gains `export_alias` |
| `uv sync --locked`, Ruff check and format | Passed |
| `uv run --locked pytest` | 984 passed (944 before Task 13) |
| `uv build`, `scripts/check_package.py` | Passed |

Windows Terminal check in an owned window, with `APPDATA`, `XDG_CONFIG_HOME`
and `SSH_WORKBENCH_SSH_DIR` pointed at ignored `.local/task13-session/`
folders; the fictional SSH config had CRLF line endings:

| Step | Result |
| --- | --- |
| Add `box` by keyboard: direct, `192.0.2.60`, user, port, a key path with a space, export ticked with Space | Saved; the Include question showed the exact line and the config path |
| Y | `Added "Include ssh-workbench.config" to <path>; a copy is in config.ssh-workbench.bak.` The config bytes were the new line plus CRLF, then the original bytes unchanged; the backup was byte-identical to the original. Details: `Direct, exported as ssh box` |
| Generated file | The header, then `Host box` with `HostName 192.0.2.60`, `User dev`, `Port 2222`, `HostKeyAlias box`, `IdentityFile "C:/Fictional Keys/id_box"` and `IdentitiesOnly yes` |
| `ssh -F <generated file> -G box` | OpenSSH 10.5p1 and Windows OpenSSH 9.5p2 both printed that host, user, port, host-key alias and the key path as one value. Only the generated file was given, since a relative `Include` in a `-F` file would resolve against the real `~/.ssh` |
| E on `box` at 60x20, export unticked | Saved without a question; the generated file kept only its header |

The first run of this check showed the add form squeezing the alias and direct
fields to one row, so typed addresses, users, ports and keys were invisible; it
had been so since Task 9, because a `Vertical` defaults to `height: 1fr`.
`test_every_connection_field_shows_in_the_form` failed at 80x24 and 60x20, then
passed once both containers got `height: auto`. At 60x20 the export checkbox's
long label overflowed, so its explanation moved into the field label. The check
above is the repeat.

Two fresh reviews, one for spec compliance and one for code and docs quality,
found these issues to fix; each was fixed after a failing test:

| Finding | Fix | Test |
| --- | --- | --- |
| A config that starts with a byte-order mark hid the added line from the check, so a second Y would add it again and overwrite the backup | The check ignores a leading mark | `test_include_present` (two new cases), `test_the_line_added_after_a_byte_order_mark_is_found` |
| A linked config (dotfile managers) would become an unlinked file, and a read-only one was replaced anyway | Both are refused with the line to add by hand | `test_a_linked_or_read_only_config_is_refused`; the link case fakes `Path.is_symlink`, because this Windows account cannot create links |
| Saving another machine file, opened with `--config`, rewrote the generated file and dropped the first file's exports | The header names its machine file; another machine file's exports are refused with a message | `test_another_machine_files_exports_are_left_alone` |
| The Include question opened after the generated file failed to write, and answering it hid the failure | No question then | `test_a_failed_export_is_shown_instead_of_the_question` |
| The rename review counted exported names as the user's `Host` names | It skips the generated file, like the form | `test_exported_names_are_not_the_users_host_names` |
| Docs still said Workbench never changes the SSH config, and described `%%` for key paths the loader already refuses | Reworded | Reviewed diff |

Two fakes of `host_names` in `tests/test_renames_ui.py` took the new `skip`
argument in their own commit; they passed against the code before the fix.

The repeated native check then showed the header naming the machine file by
the relative path typed after `--config`, which would compare differently from
another folder; `test_the_generated_file_names_the_machine_file_absolutely`
failed, then passed, and a further repeat showed the absolute path. One full
run also showed `test_shutdown_skips_a_pending_rebuild` (from PR #12) failing
once: a rebuild queued with `call_later` during teardown did not always run.
The test now creates and awaits that task; it passed eight times in a row and
fails when the `_rebuild` guard is removed.

After the fixes: 993 tests passed. Remaining minor findings are in the
roadmap's 0.2.x candidates.

Open for Jadon: inserting the `Include` line into a real `~/.ssh/config`.
Done in [Task 14](#task-14-020-release-2026-10-21).

| Integration step | Result |
| --- | --- |
| [PR #15](https://github.com/jkosber/ssh-workbench/pull/15) CI on head `4d77236` | [Push run 39567661862](https://github.com/jkosber/ssh-workbench/actions/runs/39567661862) and [PR run 39567703611](https://github.com/jkosber/ssh-workbench/actions/runs/39567703611) passed on Windows and Ubuntu, 993 tests each |
| Merge | Merged as **`777d766`**, guarded on head `4d77236`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39568301185](https://github.com/jkosber/ssh-workbench/actions/runs/39568301185) passed on Windows and Ubuntu, 993 tests each |

## Task 12: key login setup, 2026-10-21

Branch `feat/task12-key-setup`. Environment as in Task 8. No real key was
created, no real `ssh-keygen` ran and no key was installed anywhere real.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | `tests/test_keys.py` and `tests/test_keysetup_ui.py` failed at collection for the missing module and screen; the new `tests/test_ssh.py` and `tests/test_status.py` tests failed for the missing builders, runner and alias keys |
| `uv sync --locked`, Ruff check and format | Passed |
| `uv run --locked pytest` | 939 passed (868 before Task 12) |
| POSIX install command | Run by a local `sh` with `HOME` in a temporary folder: installed once, reported "already installed" on a second run, kept an existing last line without a newline whole, and found the key behind `from=` options |
| Windows install command | The decoded script parsed with no errors in PowerShell's own parser; a 4096-bit RSA key kept the command under 8191 characters. It was not run: its administrator branch would change real ACLs |
| `ssh -G` keys | `ssh -F <fictional file> -G` printed `identityfile` with `~/` unexpanded and listed the defaults when none is configured |
| Microsoft documentation | Read 2026-10-21: the administrator key file and its ACL, SIDs for localized names, cmd.exe as the default shell, ssh-agent disabled by default |

Windows Terminal check in an owned window with `scripts/check_keys.py`, whose
local children stand in for `ssh-keygen` and SSH, on fictional machines in
ignored `.local/task12-session/` folders:

| Run | Result |
| --- | --- |
| 1, Box (direct, no key): create a new key | The picker listed `id_a.pub`, `id_lab.pub` and `Create a new key: id_ed25519_box`. The keygen, install (POSIX, 519 characters) and test children each owned the terminal after a printed `SSH Workbench:` line. Back in the app: `Key login works. The key is saved as this machine's key. Machine 1: box`, and the machine file gained the key's path |
| 1, Garden (alias): second choice | `id_lab.pub (your SSH config offers this)` first; on `id_a.pub` the note showed the `IdentityFile` line with the whole path |
| 2, Garden, `id_a.pub`, Windows chosen with Tab and Space, test exits 255 | Windows install command of 5038 characters; result: key-only login failed, with the IdentitiesOnly explanation and the `IdentityFile` line |
| 3, 60x20, same folder as run 1 | Box offered only its saved key; footer `c Connect o Link a Add e Edit x Delete k Key r Check q Quit` fit; the picker showed every part |

The first run of this check showed the picker cutting off its note, so the
`IdentityFile` path was hidden at 80x24 and the note and keys at 60x20.
`test_the_picker_shows_its_note_and_keys_whole` failed at both sizes, then
passed once the note moved under the title and the lists lost their borders;
the check above is the repeat.

Two fresh reviews, one for spec compliance and one for code and docs quality,
found these issues to fix; each was fixed after a failing test:

| Finding | Fix | Evidence |
| --- | --- | --- |
| With `ControlMaster` and `ControlPersist` configured, the login test could reuse the install's connection and report success without the key | The test passes `ControlPath=none` | `test_login_test_arguments_allow_only_public_keys` and the UI argument lists failed, then passed |
| An alias whose config sets `RemoteCommand` made both the install and the test fail with status 255 | Both pass `RemoteCommand=none`; a fictional `-F` config confirmed both OpenSSH builds drop `remotecommand` and `controlpath` with these options | `test_install_arguments_never_offer_the_machine_key` failed, then passed |
| An `OSError` while looking up `ssh` or `ssh-keygen` escaped the terminal handoff, and a machine key under `~` without a home folder ended the app | Lookups turn it into a launch error; K reports the missing home folder | `test_lookup_errors_become_launch_errors`, `test_a_key_in_a_missing_home_folder_is_reported` |
| The Windows script was only parsed | Its standard-user branch now runs under PowerShell with `USERPROFILE` in a temporary folder, with the administrator lines replaced: installed once, "already installed" the second time, an existing last line kept whole | `test_windows_install_adds_the_key_once_for_a_standard_user`, `test_windows_install_keeps_existing_lines_whole` (passed as written) |
| Real host names in the roadmap and this record; docs left out the picker, the key name's underscores and the `.pub` read next to an alias's `IdentityFile` | Reworded | Reviewed diff |

After the fixes: 944 tests passed. Remaining minor findings are in the
roadmap's 0.2.x candidates.

Open for Jadon: installing and testing a real key against a real Windows
target and a real Linux target. Done in
[Task 14](#task-14-020-release-2026-10-21).

| Integration step | Result |
| --- | --- |
| [PR #14](https://github.com/jkosber/ssh-workbench/pull/14) CI on head `43b6448` | [Push run 39560759058](https://github.com/jkosber/ssh-workbench/actions/runs/39560759058) and [PR run 39560765769](https://github.com/jkosber/ssh-workbench/actions/runs/39560765769) passed on Windows and Ubuntu, 944 tests each |
| Merge | Merged as **`5dda419`**, guarded on head `43b6448`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39561245538](https://github.com/jkosber/ssh-workbench/actions/runs/39561245538) passed on Windows and Ubuntu, 944 tests each |

## Task 11: alias rename detection, 2026-10-21

Branch `feat/task11-alias-renames`. Environment as in Task 8.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | `tests/test_aliases.py` and `tests/test_renames_ui.py` failed at collection for the missing module and message; in `tests/test_status.py` six tests failed for the missing `user` field and state. Three existing assertions there were extended: `resolve_alias` results gain `user="dev"`, which their fixture prints, and the exact list of state words gains "Alias not found" |
| `uv sync --locked`, Ruff check and format | Passed |
| `uv run --locked pytest` | 861 passed (802 before Task 11) |
| `uv build`, `scripts/check_package.py` | Passed; the installed-import check now also covers `aliases` and `status` |
| `Host` matching | `ssh -F <fictional file> -G` with OpenSSH 10.5p1 and Windows OpenSSH 9.5p2 applied `Host lab-box` to `lab-box` but not to `LAB-BOX`, so an alias is listed only by exact name |

Windows Terminal check in an owned window, with `APPDATA`, `XDG_CONFIG_HOME`
and `SSH_WORKBENCH_SSH_DIR` pointed at ignored `.local/task11-session/`
folders, a local listener on 127.0.0.1, and three fictional alias machines:
Garden (`old-garden`), Shed (`old-shed`, another fictional user) and Pattern
(`pattern-only`, no `Host` entry):

| Run | Result |
| --- | --- |
| 1, both aliases listed | Garden and Shed `● Online via alias`; Pattern `○ Offline` and `pattern-only (not in your SSH config)`. One state file, `machines.state.<computer>.json`, listed both `Host` names, both targets, no baselines and version 1; `git check-ignore` matched it |
| 2, `old-garden` renamed to `new-garden` and `old-shed` removed | Both `×`. Garden: `× Alias not found. Looks like old-garden became new-garden. Press U to update.`, footer `u Update` without `c Connect`. Shed: `× Alias not found. Fix your SSH config and press R, or press E and save to keep or change the alias.`, neither C nor U in the footer, and C changed nothing. U on Garden: `Updated machine 1: garden now uses alias new-garden.`, `● Online via alias`, and the file's other machines unchanged |
| 3, restarted at 60x20 | Shed still Alias not found; the footer fit. E then Ctrl+S on Shed without changes: `Saved machine 2: shed.`, `◇ Can't check: press R to resolve this alias`, and `c Connect` back in the footer |

The first run of this check gave both machines the same host, user and port,
and Shed was also offered `new-garden`. An offer now has to fit only one
vanished alias: `test_a_new_name_matching_two_vanished_aliases_is_offered_to_neither`
failed, then passed, and the native check was repeated with distinct targets
as above.

Two fresh reviews, one for spec compliance and one for code and docs quality,
found these Important issues, each fixed after a failing test:

| Finding | Fix | Evidence |
| --- | --- | --- |
| A name seen once without a unique match (unresolved, or two candidates) was never offered later | Each missing alias keeps the `Host` names from when it was last listed as its baseline; every review resolves the names added since | `test_a_name_that_did_not_resolve_at_first_is_offered_once_it_matches`, `test_an_ambiguous_match_is_offered_once_only_one_name_is_left` |
| Computers sharing a synced machine file overwrote each other's state | One state file per computer, `<stem>.state.<computer>.json` | `test_state_path_is_per_computer_next_to_the_machine_file` |
| The documented example run wrote an untracked, unignored state file with the developer's `Host` names into `examples/` | `.gitignore` covers `*.state.*.json`; AGENTS and CONTRIBUTING say so | `git check-ignore` matched `examples/machines.example.state.WORKSTATION.json` and the native check's file |
| An alias moved into a pattern on purpose stayed blocked, and "Edit the machine" did not clear it | Saving the machine from the form forgets that alias's record | `test_saving_the_machine_from_the_form_keeps_its_alias`, `test_forget_drops_an_alias_record_and_baseline`; native run 3 |
| A timer tick during the startup or R review dropped it; the two 50 ms timer tests failed with an 80 ms review | Timer rounds wait while a startup or R round still reviews or resolves | `test_a_timer_round_waits_for_the_review`; both timer tests passed with the reviewer's 80 ms delay |

After the fixes: 868 tests passed, and the native check above was repeated.
Remaining minor findings are in the roadmap's 0.2.x candidates.

| Integration step | Result |
| --- | --- |
| [PR #13](https://github.com/jkosber/ssh-workbench/pull/13) CI on head `67bdee7` | [Push run 39554803189](https://github.com/jkosber/ssh-workbench/actions/runs/39554803189) and [PR run 39554808526](https://github.com/jkosber/ssh-workbench/actions/runs/39554808526) passed on Windows and Ubuntu, 868 tests each |
| Merge | Merged as **`56fab1a`**, guarded on head `67bdee7`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39555239315](https://github.com/jkosber/ssh-workbench/actions/runs/39555239315) passed on Windows and Ubuntu, 868 tests each |

## Status timer during shutdown, 2026-10-21

After [PR #11](https://github.com/jkosber/ssh-workbench/pull/11) merged as
`56c6d47` (guarded on head `4d4d473`, tree identical; the PR's
[push run 39547483007](https://github.com/jkosber/ssh-workbench/actions/runs/39547483007)
and [PR run 39547486885](https://github.com/jkosber/ssh-workbench/actions/runs/39547486885)
passed on Windows and Ubuntu with 799 tests each), the
[main run 39547849863](https://github.com/jkosber/ssh-workbench/actions/runs/39547849863)
failed on Ubuntu: `test_timer_rounds_never_run_ssh_g` raised `NoMatches` for
`#machine-status` from `_timer_round`, re-raised when `run_test` exited.

| Item | Result |
| --- | --- |
| Cause (inferred from the trace and the Textual 8.2.8 source; not reproduced on Windows) | When Pilot's `run_test` tears the app down, `App._shutdown` sets `_running` False and removes the screens in `_close_all` while the app's timers and message handling still run; only then does it stop them. The test's 0.05 s status timer fired in that window and queried a half-removed screen. A normal exit stops the timers and message handling first, so the window is a test-teardown race |
| First fix | `_timer_round` and `_tick_animation` return once `App.is_running` is False |
| Reviews | Two fresh reviewers reproduced the same `NoMatches` through `on_status_finished` in that window, and showed `on_link_finished` and a `call_later` rebuild are exposed the same way |
| Tests first | Each test hooks every `Unmount` dispatched after `is_running` turns False, so it acts at each step of the screen removal: `test_shutdown_ignores_status_results_and_timers` (31 `NoMatches` before the fix), `test_result_while_the_screens_close_is_ignored` and `test_shutdown_skips_a_pending_rebuild` failed, then passed |
| Fix | `on_status_finished`, `on_link_finished` and `_rebuild` also return once `App.is_running` is False |
| [PR #12](https://github.com/jkosber/ssh-workbench/pull/12) CI on head `05d90b9` | [Push run 39549706759](https://github.com/jkosber/ssh-workbench/actions/runs/39549706759) and [PR run 39549711277](https://github.com/jkosber/ssh-workbench/actions/runs/39549711277) passed on Windows and Ubuntu, 802 tests each |
| Merge | Merged as **`915639e`**, guarded on head `05d90b9`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39550082638](https://github.com/jkosber/ssh-workbench/actions/runs/39550082638) passed on Windows and Ubuntu, 802 tests each |
| `uv run --locked pytest` | 802 passed (799 before the fix) |
| `uv build`, `scripts/check_package.py` | Passed |

## Task 10: live status, 2026-10-21

Branch `feat/task10-live-status`. Environment as in Task 8.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | `tests/test_status.py` and `tests/test_status_ui.py` failed at collection for the missing module and widgets; the CLI checker test failed on the missing attribute |
| `uv sync --locked`, Ruff check and format | Passed |
| `uv run --locked pytest` | 798 passed (759 before Task 10) |
| `uv build`, `scripts/check_package.py` | Passed. The installed app ran its real checker inside the package check's guards; the guarded network and process calls ended as Can't check, with no traceback in the output |

Windows Terminal check in an owned window, with `APPDATA`, `XDG_CONFIG_HOME`
and `SSH_WORKBENCH_SSH_DIR` pointed at ignored `.local/task10-session/`
folders, a local listener on 127.0.0.1 that accepted and closed connections,
and four fictional machines:

| Machine | Result |
| --- | --- |
| Direct, addresses `192.0.2.1` then `127.0.0.1` on the listener's port | Turning `◐` at start, then `● Online: 127.0.0.1` once the first address timed out |
| Direct, `192.0.2.2` | `○ Offline` |
| Alias whose fictional `Host` entry points at the listener | `● Online via alias`, resolved with `ssh -F` on the fictional folder |
| Alias with `ProxyJump` | `◇ Can't check: the alias uses ProxyJump or ProxyCommand` |

R set every machine back to Checking. Q right after R, with checks still
waiting on the documentation-range address, returned to the prompt in 275 ms.
With `TEXTUAL_ANIMATIONS=none` the screen stayed identical across 0.9 s. At
60x20 the footer showed `q Qui`: Textual leaves the bottom-right cell empty on
Windows, and the seven keys needed all 60 columns. The first footer test read
the key regions before layout and passed wrongly; it now waits for the layout,
failed as expected, and passes since O is labelled Link in the footer.

Two fresh reviews, one for spec compliance and one for code and docs quality,
found three Important issues, each fixed after a failing test or, for docs, by
rewording:

| Finding | Fix | Evidence |
| --- | --- | --- |
| C during a running round connected to the first listed address: each round replaced the last online result with Checking | The app keeps the address each machine's last finished check found online, if the machine still lists it | `test_connect_during_a_round_uses_the_last_online_address` failed, then passed |
| `ssh -G` captured stderr; on Windows a timeout still waits for a `Match exec` child that holds that pipe open | stderr goes to `DEVNULL`; it was never read | `test_resolve_alias_runs_ssh_g_without_a_shell`, updated in the test commit, failed, then passed |
| Docs said only `Host` and `Include` lines are read and that the TCP connection is the only traffic; `ssh -G` evaluates the whole config, DNS lookups go out, and the example run reaches the real SSH config unless `SSH_WORKBENCH_SSH_DIR` is set | README, CHANGELOG, AGENTS, CONTRIBUTING, architecture and the example file corrected; Offline and Can't check reasons now match the code | Reviewed diff |

After the fixes: 799 tests passed. Remaining minor findings are in the
roadmap's 0.2.x candidates.

## Task 9: add, edit and delete machines, 2026-10-21

Branch `feat/task9-edit-machines`. Environment as in Task 8.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | The formatter, store and SSH config tests failed at collection for the missing functions and modules; the form tests failed at collection, and five app and two CLI tests failed on the new empty-screen text and the loaded-text handoff |
| Tests added during the task, each red first | Saving unchanged text writes nothing; E and X need a file location; actions stay off while a saved list is rebuilt (an `IndexError` before the fix) |
| `uv sync --locked`, Ruff check and format | Passed |
| `uv run --locked pytest` | 751 passed (685 before Task 9); 759 after the review fixes |
| `uv build`, `scripts/check_package.py` | Passed. The installed wheel now also adds a machine headless and saves it into a new folder, with `SSH_WORKBENCH_SSH_DIR` pointed at an empty temporary folder |

Windows Terminal check in an owned window, with `APPDATA`, `XDG_CONFIG_HOME`
and `SSH_WORKBENCH_SSH_DIR` pointed at ignored `.local/task9-session/` folders
holding a commented fictional machine file and an SSH config with
`Host alpha beta *.wild` and an `Include` of `Host lab-gamma`:

| Step | Result |
| --- | --- |
| A, typing the ID, name and `al`, Right, Ctrl+S | The form listed alpha, beta and lab-gamma; Right completed `alpha`. The first Ctrl+S showed the comment warning and left the file unchanged; the second saved, wrote `machines.toml.bak` and selected the new machine |
| E, adding a link line, Ctrl+S | Saved in place |
| X, then N; X, then Y | N kept the machine; Y deleted it and reported `Deleted machine 3` |
| An outside edit while the add form was open, then Ctrl+S twice | The first Ctrl+S reported the outside change and kept the form; the reloaded list held the new machine; the second saved both |
| A direct machine chosen with Tab, Down and Enter | Saved with both addresses, the user and the port |
| Escape from a form at 60x20 | The form scrolled to fit; the file hash was unchanged afterwards |

The first run of this check crashed: after a delete, the footer asked for its
bindings while the old three-item list was still mounted and the app already
held two machines, and `check_action` indexed past the end. A failing test
reproduced it inside the rebuild window, the fix keeps actions off until the
rebuild ends, and the second run passed every step above.

Two fresh reviewers (spec compliance; code and docs quality) found no critical
issues. One quality reviewer stopped on a service error before reporting; a
replacement with a reworded brief completed the review. Fixes, each after a
failing test:

| Finding | Fix and test |
| --- | --- |
| Comments added by an outside edit were dropped without the warning, because it was computed when the form opened | The form asks for the warning at each save and again after a refused save. `test_outside_comment_is_warned_about_before_saving` |
| A read-only machine file on Windows left a temporary file and a read-only `.bak` that blocked later saves; Linux replaced read-only files silently | A file the user made read-only is refused before anything is written, on every platform; no mode is copied to the backup or on Windows; the temporary file is made writable before removal. `test_read_only_file_is_refused_and_saves_once_writable` |
| Ctrl+Q did not quit from the form or the delete question | Both repeat a priority Ctrl+Q. `test_ctrl_q_quits_from_the_form_and_the_delete_question` |
| After a reload the selection stayed on the same row, so a machine inserted above moved C onto another machine | The same machine stays selected. `test_reload_keeps_the_selected_machine`; a refused delete now says to delete again |
| A port of thousands of digits crashed the app | Five digits at most become an integer. `test_huge_port_is_an_error_not_a_crash` |
| "Never opens keys" was true only for some names | `*.pem`, `*.ppk` and `*.key` are skipped too, and the docs name the skipped patterns. `test_other_key_file_names_are_never_read` |

After the fixes: 759 tests passed and the native check above was repeated with
the same results. Remaining minor findings are in the roadmap's 0.2.x
candidates.

| Integration step | Result |
| --- | --- |
| [PR #10](https://github.com/jkosber/ssh-workbench/pull/10) CI on head `3d2ad36` | [Push run 39544208450](https://github.com/jkosber/ssh-workbench/actions/runs/39544208450) and [PR run 39544212338](https://github.com/jkosber/ssh-workbench/actions/runs/39544212338) passed on Windows and Ubuntu, 759 tests each |
| Merge | Merged as **`96338e1`**, guarded on head `3d2ad36`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39544559783](https://github.com/jkosber/ssh-workbench/actions/runs/39544559783) passed on Windows and Ubuntu |

## Task 8: machines replace projects, 2026-10-20

Branch `feat/task8-machines`. Environment: Windows 11, PowerShell 7.6.7,
Microsoft Windows Terminal 1.25.2733.0, Python 3.14.7, Textual 8.2.8, uv 0.13.3,
Windows OpenSSH 9.5p2 and Git for Windows' portable OpenSSH 10.5p1.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | `tests/test_machines.py` failed at collection (`cannot import name 'ConfigError'`). After the converted test commit, 129 tests failed and one module failed to collect, all for the missing machine API |
| Test-only corrections before the implementation commit | Three new click steps targeted the links value, which sits below the visible details pane at 60x20 and 80x24; they now scroll first or click visible fields. Rewriting `tests/test_app.py` had turned two escaped name cases into literal characters; both lines were restored byte-for-byte from 0.1.0, and a scan found no other literal control or format characters in tracked files |
| `uv sync --locked`, Ruff check and format | Passed |
| `uv run --locked pytest` | 673 passed (450 before Task 8) |
| `uv build`, `scripts/check_package.py` | Passed; the package check now loads a schema 2 file and drives O through the picker in the installed wheel |
| Argument lists with real OpenSSH | `ssh -F none -G`, which reads no configuration and connects nowhere, on the lists `ssh_arguments` builds: a direct machine with user, port, a key path containing a space and an IPv6 address, and an alias machine. Both clients printed the expected `hostname`, `user`, `port`, `hostkeyalias`, `identitiesonly yes` and `identityfile` values and exited 0. An IPv4 destination after `--` parsed the same way, and `-- -oProxyCommand=x` was refused as an invalid hostname |
| `%` in a key path | With `-i`, a doubled `%%` made both clients report the key as not accessible, and a raw `%` passed their existence check only to be expanded as a token afterwards. Key paths therefore reject `%` |

Windows Terminal check in an owned window with fictional machines, `NO_COLOR`
cleared and `APPDATA` pointed at an empty ignored folder:

| Step | Result |
| --- | --- |
| Example file at 80x24 | Both machines listed. The alias machine showed `Connection: SSH alias` and its alias; the direct machine showed `Direct`, both addresses on separate lines and its user |
| O on the two-link machine | "Open a link" listed Dashboard and Status page with their URLs. Down, then Escape, closed it with the same selection and link status |
| 60x20, 120x40, back to 80x24 | The screen filled each size; at 60x20 the help line stayed on one row and the link hint wrapped inside its three-row area |
| Q | Exited with status 0 |
| `--help` in a 60-column window | `Default machine file:` followed by the full path unbroken on the next line |
| No machine file | The start screen named the default path under the overridden `APPDATA`; Ctrl+Q exited |
| `scripts/check_links.py` | O on the no-links case changed nothing. On the picker case, Down and Enter reported `[b]Second[/b] link browser request accepted. Machine 6: fixture-picker`, markup shown literally |
| `scripts/check_terminal.py` | C handed the terminal to the local child, whose three streams were terminals; typing `return` came back with `SSH exited with status 0. Machine 1: fixture-zero` |

Real connect checks, with Jadon's standing approval for these targets and
actions, from an ignored machine file:

| Target | Result |
| --- | --- |
| Alias machine for the first approved SSH target | Reached a remote prompt with no password or host-key prompt; only `exit` was typed. Workbench returned with `SSH exited with status 0.` and the same machine selected |
| Alias machine for the second approved target | No prompt appeared and SSH returned 255 without input; the target was not reachable and was skipped |

Two fresh reviewers (spec compliance; code and docs quality) found no critical
issues. Their important findings were fixed after failing tests:

| Finding | Fix and test |
| --- | --- |
| Two picker keys in one console read (Enter twice, or Enter then Escape) dismissed the picker twice and crashed with `ScreenStackError` | The picker answers once, and Enter and Escape are priority bindings handled in arrival order, so the first key wins. `test_picker_ignores_a_second_key_in_the_same_batch` covers all four pairs |
| A `~\` key became one file name containing backslashes on Linux, and `~//etc/key` or `~/C:\x` could leave the home folder | Either separator is split, and the rules reject a second root or a drive after `~`. `test_invalid_keys` and a literal `home/.ssh/id_box` expectation |
| An alias machine carrying `user`, `port` or `key` reached the boundary and was silently ignored | The boundary refuses it. `test_alias_machine_with_direct_fields_is_rejected` |
| The test for C while the picker is open passed even without the guard, because the headless driver cannot suspend | The test now allows suspension and asserts no handoff and an unchanged status; removing the guard makes it fail |

They also corrected the docs: Workbench connects to the first address (not each
in turn); a Windows key path needs single quotes in TOML; the `v0.1.0` tag
predates machines. After the fixes: 685 tests passed, the build and package
check passed, and the fictional Windows Terminal check above was repeated with
the same results. Remaining minor findings are listed under 0.2.x candidates in
the roadmap.

| Integration step | Result |
| --- | --- |
| [PR #9](https://github.com/jkosber/ssh-workbench/pull/9) CI on head `3462344` | [Push run 39538624432](https://github.com/jkosber/ssh-workbench/actions/runs/39538624432) and [PR run 39538651953](https://github.com/jkosber/ssh-workbench/actions/runs/39538651953) passed on Windows and Ubuntu, 685 tests each |
| Merge | Merged as **`47e7cd4`**, guarded on head `3462344`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39538890532](https://github.com/jkosber/ssh-workbench/actions/runs/39538890532) passed on Windows and Ubuntu |

No direct machine was connected for real: its first connection asks to trust
the host key under the new `HostKeyAlias`, and the approved actions allow only
typing `exit`. The alias names stay in ignored `.local/task8-session/`. Linux
and macOS were not exercised natively.

### Task 8 link fixture checklist

Run `uv run --locked python scripts/check_links.py` in Windows Terminal at
80x24. It substitutes every browser and OS boundary.

1. On each case, press O from the list and again from the details pane.
   Accepted reports "accepted"; failed and error report "failed" without the
   private marker; long wraps in the details pane and stays inside the status
   area.
2. On the no-links case, O is dimmed and pressing it changes nothing.
3. On the picker case, O opens the list: Enter opens the first link, Down and
   Enter the second, and Escape closes it with the same selection and focus.
4. Last, on the blocked case, O reports pending and a repeated O reports "still
   pending". Change the selection and focus, then quit with Q or Ctrl+Q; the
   process exits at once.

## Task 7: tooling cleanup, 2026-10-20

Branch `feat/task7-tooling-cleanup`. Environment as in Task 6: Windows 11,
Python 3.14.7, Textual 8.2.8, uv 0.13.3, Ruff 0.16.10 and pytest 9.1.1.

| Check | Agent-observed result |
| --- | --- |
| New tests before implementation | The shared-list tests failed at collection (`No module named 'external_boundaries'`); the strings test failed listing lines 13, 34, 192 and 357 of `check_package.py` |
| Drift test | Passed on the old 0.12.24 pair, failed (`['0.12.24'] == ['0.13.3']`) after only `pyproject.toml` changed, and passed once CI matched |
| `uv build` before and after | The warning that `uv-build>=0.12.24,<0.13.0` excludes uv 0.13.3 appeared before the change and is gone after it. `uv lock --check` reported the lock unchanged |
| Isolation assertions | `package_smoke.py` without `-I` failed on `sys.flags.isolated`; with `-I` against the development environment it failed naming `ssh_workbench`, whose editable install points at the checkout |
| `uv sync --locked`, Ruff check and format | Passed; 32 files already formatted |
| `uv run --locked pytest` | 450 passed (446 before Task 7) |
| `uv build`, `scripts/check_package.py` | Passed, with the same success line as before |
| Relative Markdown links | 62 checked, 0 broken |

No native terminal check was needed: no application code changed.

Two fresh reviewers (spec compliance; code and docs quality) found no critical
or important issues. Both confirmed the moved checks match the old string bodies
and reproduced the two isolation failures. Three documentation statements were
corrected; four minor test-strength findings are listed under 0.2.x candidates
in the roadmap.

| Integration step | Result |
| --- | --- |
| [PR #8](https://github.com/jkosber/ssh-workbench/pull/8) CI on head `d6f3a61` | [Push run 39532446289](https://github.com/jkosber/ssh-workbench/actions/runs/39532446289) and [PR run 39532471847](https://github.com/jkosber/ssh-workbench/actions/runs/39532471847) passed on Windows and Ubuntu, 450 tests each |
| Merge | Merged as **`11449aa`**, guarded on head `d6f3a61`; tree identical to the tested head. Local `main` fast-forwarded; the branch was deleted locally and on GitHub |
| Merged `main` CI | [Run 39532704983](https://github.com/jkosber/ssh-workbench/actions/runs/39532704983) passed on Windows and Ubuntu |

## Task 6: 0.1.0 readiness, 2026-10-20

Branch `feat/task6-0.1.0-readiness`. Environment: Windows 11 Home Insider
Preview build 26340, PowerShell 7.6.7, Microsoft Windows Terminal 1.25.2733.0,
Python 3.14.7, Textual 8.2.8, uv 0.13.3, Ruff 0.16.10 and pytest 9.1.1.

| Check | Agent-observed result |
| --- | --- |
| New default-file tests before implementation | 12 failed for the missing feature; the precedence and no-path guards and all existing tests passed |
| `uv sync --locked`, Ruff check and format | Passed; 29 files already formatted |
| `uv run --locked pytest` | 445 passed (431 before Task 6) |
| `uv build` | Source archive and wheel for 0.1.0. Wheel metadata shows `License-Expression: MIT` and `License-File: LICENSE`; both archives contain `LICENSE`. The known `uv_build<0.13.0` warning from uv 0.13.3 remains |
| `uv run --locked python scripts/check_package.py` | Passed |
| Relative Markdown links | 61 checked, 0 broken |
| `uv tool install .`, then `--reinstall .` | Installed `ssh-workbench.exe` into the uv tool folder; `ssh-workbench --version` printed `ssh-workbench 0.1.0` from another folder |

Installed-tool smoke test in an owned 80x24 Windows Terminal window, with
`NO_COLOR` cleared and `APPDATA` pointed at ignored `.local/` folders so the real
per-user file was untouched:

| Step | Result |
| --- | --- |
| No default file, no `--config` | No-configuration screen named the default path under the overridden `APPDATA`, wrapping cleanly at 80 columns; Q exited with status 0 |
| Default file holding one approved SSH alias | Project loaded without `--config` |
| C, then `exit` at the remote prompt | No password or host-key prompt appeared. Workbench returned with `SSH exited with status 0.` and the same project selected |
| Ctrl+Q | Exited with status 0 to a usable prompt; the window was then closed |

The alias name and screenshots stay in ignored `.local/task6-session/`. Linux
and macOS were not exercised natively.

Two fresh reviewers then checked the branch for plan compliance and quality. One
defect was fixed after a failing test: `--help` crashed with `UnicodeEncodeError`
when redirected output used a code page that cannot encode the default path. The
path is now escaped for the output encoding. Documentation fixes followed for the
agent check list, the example file header, the Linux quick start and two stale or
wrong statements. Remaining minor findings are listed under 0.1.x candidates in
the roadmap. After the fixes: 446 tests passed, Ruff and links were clean, the
build and package check passed again, and redirected help with a fictional
non-cp1252 `APPDATA` exited 0 with the path escaped. The native smoke test was
not repeated; the fix changes only help text.

### Integration and release

Each step below had Jadon's approval.

| Step | Result |
| --- | --- |
| [PR #6](https://github.com/jkosber/ssh-workbench/pull/6) CI on head `8320728` | [Push run 39518641055](https://github.com/jkosber/ssh-workbench/actions/runs/39518641055) and [PR run 39518656107](https://github.com/jkosber/ssh-workbench/actions/runs/39518656107) passed on Windows and Ubuntu; the PR run logs show 446 tests on each |
| Merge | Merged at 2026-10-21 00:03 UTC (2026-10-20 locally) as **`54f6a3e`**, guarded on head `8320728`. Parents `ac4f6e8` and `8320728`; tree identical to the tested head. Local `main` fast-forwarded to it |
| Merged `main` CI | [Run 39518897638](https://github.com/jkosber/ssh-workbench/actions/runs/39518897638) passed on Windows and Ubuntu |
| Tag | Annotated `v0.1.0` ("Release 0.1.0", tagger Jadon Kosberg) on `54f6a3e`, pushed to origin |
| Install from the tag | `uv tool install --reinstall git+https://github.com/jkosber/ssh-workbench@v0.1.0` installed 0.1.0; `ssh-workbench --version` printed `ssh-workbench 0.1.0` |
| Repository | Description updated to match `pyproject.toml`. Still private, with no GitHub Release. The merged branch was deleted |

## Task 5: preparation and safe local verification, 2026-10-12

**Task 5 is complete and merged in PR #5.** Initial preparation merged Task 4, verified the
baseline with substituted external actions, and prepared the user-run session
below. No real SSH connection or browser/GIO dispatch occurred during that
preparation. Later user-reported and explicitly authorized agent checks in
Windows Terminal are recorded separately below.
On 2026-10-20, at Jadon's request, the agent listed only the `Host` names in his
SSH configuration so he could choose test targets. It printed no host names,
users or key paths, and has read no keys or inventories. These Task 5 records
stayed uncommitted until 2026-10-20.

| Task 5 item | Status | Evidence |
| --- | --- | --- |
| Approved real-world targets | Done | One alias (2026-10-12); the GitHub repository and README URLs and two more aliases (2026-10-20). Alias names stay in the ignored configuration |
| Checklist A-D in Windows Terminal | Done | [Windows Terminal check](#task-5-authorized-windows-terminal-check-2026-10-20); step C is also [user-reported](#task-5-user-executed-manual-session) |
| Footer mouse clicks | Done | [Footer click check](#task-5-footer-click-check-2026-10-20) |
| More SSH targets and a real nonzero exit | Done | [Additional targets](#task-5-additional-ssh-targets-and-review-fixes-2026-10-20) |
| Project review and material fixes | Done | Same section: SSH lookup in the launch folder and UTF-8 byte-order-mark configs, each fixed after a failing test |
| Documentation accuracy pass | Done | 2026-10-20 |
| Release scope and license decision | Done | 2026-10-20: private `v0.1.0` tag, MIT license, scope in roadmap Task 6 |

### Verified Task 4 merge and CI

The starting checkout was clean on `feat/errors-and-links`, at reviewed head
`0fe97d169a59094dbfdce179480d6889efb4dcdb`. Origin and ownership were verified as
private `jkosber/ssh-workbench`; GitHub authenticated as `jkosber`. PR #4 was open,
not a draft, into `main`, with that exact head, no GitHub reviews/comments or
unresolved review threads, and `CLEAN` / `MERGEABLE` status. The branch API
reported main unprotected; the rules endpoint was unavailable for this private
repository's plan. No requirements or settings were changed.

Both named Windows/Ubuntu jobs passed in
[push CI 38334751595](https://github.com/jkosber/ssh-workbench/actions/runs/38334751595)
and [PR CI 38334807914](https://github.com/jkosber/ssh-workbench/actions/runs/38334807914).
Each log confirmed 428 tests, build and isolated package checks. PR checkout
`e1328ec3c837b2ebca6d0fb1fea2a7ee2cea82be` had prior main `eeb6e39` and reviewed
head `0fe97d1` as parents, with the same tree as the reviewed head.

[PR #4](https://github.com/jkosber/ssh-workbench/pull/4) merged normally at
2026-10-13 02:14:39 UTC (2026-10-12 locally), as
**`9b28e86c0d6c980c6058297f60e6ff623e657031`**. The CLI's author-email override was
rejected before merging; the successful REST merge used `merge_method=merge`
and `sha=0fe97d169a59094dbfdce179480d6889efb4dcdb` as the equivalent head guard.
GitHub attributed the merge author to Jadon Kosberg's `jkosber` account and used
its server committer. Local/global Git identity settings were preserved. There
was no admin override, auto-merge, branch deletion or visibility change.

Fetch confirmed the merge's two expected parents and a tree identical to the
reviewed feature head. Local main fast-forwarded to origin/main;
`test/task5-validation` was created at the same merge. The repository remains
private. New [merged-main CI 38335955509](https://github.com/jkosber/ssh-workbench/actions/runs/38335955509)
completed successfully for **`9b28e86`**, with Windows and Ubuntu each passing
428 tests, locked sync, Ruff, build and isolated installed-package validation.
This is a separate run from Task 4's push/PR checks.

### Merged-baseline local evidence

Every result in this table tests merge **`9b28e86`**, before Task 5 documentation
edits. Environment: Windows 11 Home Insider Preview build 26340, PowerShell
7.6.6, Python 3.14.7, Textual 8.2.8, uv 0.13.0, Ruff 0.16.10 and pytest 9.1.1.
Microsoft Windows Terminal 1.25.2733.0 is installed, but the initial preparation's
interactive checks used an owned Windows pseudoterminal with a profile-free
PowerShell through cmd.exe. They do not establish Windows Terminal pixels,
resizing or SSH handoff. No screenshots were taken during that preparation.

| Command/check | Agent-observed result |
| --- | --- |
| `uv sync --locked` | Passed; existing lockfile and project Python |
| `uv run --locked ssh-workbench --help` / `--version` | Passed; 0.0.1 |
| `uv run --locked ssh-workbench` | No-config screen; Q returned status 0 and usable shell input; no external action invoked |
| `uv run --locked ruff check .` / `ruff format --check .` | Passed; 29 files (20 Python, 9 Markdown) already formatted |
| `uv run --locked pytest --basetemp .local/task5-session/pytest` | 428 passed in 67.09s; fresh ignored directory avoided the previously documented shared-temp cleanup issue |
| `uv build` | Source archive and wheel built |
| `uv run --locked python scripts/check_package.py` | Passed isolated wheel/import provenance, CLI/configuration, headless selection/quit, substituted SSH/link outcomes and blocked-opener Q/Ctrl+Q interpreter exit |
| `uv run --locked python scripts/check_links.py` | Standalone fixture: R from list, D from details, accepted/failed/error/missing results, blocked request with changed selection/focus and repeat feedback; Q and Ctrl+Q each returned 0 to usable shell input |
| `uv run --locked python scripts/check_terminal.py` | Local Python children only: inherited terminal I/O, typed input, exits 0/7/130, C from details, two Ctrl+C events while the child continued, normal return, simulated missing/start/interruption errors, retry and both quit keys; selection and list focus restored |
| Persistent session wheel installation below | Locked runtime install passed; help/version and Python `-I` site-packages provenance passed. No-config startup and Ctrl+Q returned 0 to usable shell input |
| Local placeholder TOML | Installed loader accepted two projects; only the explicit new file was read, with no external action |

The existing warning remains: installed uv 0.13.0 is outside
`uv_build>=0.12.24,<0.13.0`. Build and package checks passed; tooling and the
previously recorded backend-provenance limitation are unchanged. No production
defect was confirmed during this preparation. No code, tests, dependencies or
new test harnesses were added. The owned fixture shell and children exited;
the isolated package check removed its temporary environment. The separate
manual environment is retained for Jadon.

Fixture entry points were inspected before execution. The link fixture starts
guards before app construction and retains them until interpreter exit; the
full suite includes all 11 lifetime/exit/import regressions. The terminal fixture
substitutes executable lookup and invocation with fixed local Python children.
New fixture results above are distinct from historical WezTerm evidence below.

At the preparation handoff, all 23 relative links/anchors in the three changed
Markdown files passed validation, and the documented TOML matched the then-current
ignored placeholder template. Final diff/whitespace and empty-index checks passed;
only the roadmap, this record and the Unreleased changelog changed in Git.

### Task 5 evidence gaps against the existing acceptance

| Evidence class | Supported now / remaining gap |
| --- | --- |
| Automated | Configuration, selection/details, focus/scroll/quit, sanitized failures, SSH/browser boundary contracts and package installation pass on this revision. These support the baseline, not the required real-world observations. |
| Substituted boundaries / native fixtures | Current pseudoterminal checks exercise local handoff, recovery and stubbed dispatch. Historical WezTerm resize/text results retain their recorded scope; obscured Task 4 screenshots remain excluded. |
| Real manual interaction | Jadon reported Windows Terminal SSH handoff, return, preserved selection, immediate arrow navigation and status 0. An authorized agent check of the installed build in Windows Terminal (2026-10-20) covered live SSH return, navigation, resizing, detail scrolling and both quit keys with shell checks. In Windows Terminal, R/D opened the chosen GitHub repository and README pages in Chrome. Mouse clicks on the footer's Connect (local-child fixture), Repository, Documentation and Quit actions also worked. |
| Still unverified / unavailable | Linux GIO browser dispatch and a native Linux desktop; other DPI settings and screen readers. Authentication mechanisms and host-key prompts were not separately examined. macOS browser dispatch is explicitly unavailable in this version. Ubuntu CI does not validate a Linux desktop. Agent observation is not a human visual review. |
| Documentation, issues and readiness review | Checklist steps A-D are complete with no material defect found. Scope and privacy boundaries were reviewed; final readiness and the unselected license remain open. No release/version/visibility decision is made. |
| Outside initial-release requirements | Deferred editing/search, discovery, tmux, transfers, cloud sync, embedded terminals, AI, Proxmox controls and plugins. Manual checks use Microsoft Windows Terminal; this task adds no all-platform or accessibility certification requirement. |

### Task 5 installed build and local configuration

Use Microsoft Windows Terminal for the first real pass. Run these commands from
the repository in PowerShell. The session directory was absent before preparation
and `git check-ignore -v` verified `.local/` ignores the configuration, environment
and exported requirements. Existing local files were preserved. Keep real target
details only in `.local/task5-session/projects.toml`, never in tracked examples.

The following **local installation steps have already passed**. They mirror the
existing package-check installation sequence and do not alter global Python.
For another installation, choose a fresh ignored directory; do not overwrite an
existing environment, requirements export or configuration.

```powershell
uv sync --locked
uv build
uv venv --python .venv\Scripts\python.exe .local\task5-session\venv
uv export --locked --no-dev --no-emit-project --output-file .local\task5-session\runtime-requirements.txt
uv pip sync --python .local\task5-session\venv\Scripts\python.exe .local\task5-session\runtime-requirements.txt
uv pip install --python .local\task5-session\venv\Scripts\python.exe --no-deps dist\ssh_workbench-0.0.1-py3-none-any.whl
```

The retained installed wheel was built from `9b28e86`, version 0.0.1, SHA-256
`71d1522a22fb6c9549ad7b0a7ca18650b247a37f495eaa5e82c3e8a35aadf589`.
Documentation edits afterward do not change that installed artifact.

The original schema-correct template below is retained as a fictional reference.
Jadon subsequently chose an existing alias; both local records use that alias.
On 2026-10-20 he chose the repository and README URLs for the first record; the
second still omits them. Actual target details stay in the ignored file. The second row supports navigation and missing
references without another host. When reusing this template, replace its alias
and URL placeholders before C/R/D; restart Workbench after editing the file.

```toml
schema_version = 1

[[projects]]
id = "manual-target"
name = "Manual target"
ssh_alias = "CHOOSE_EXISTING_ALIAS"
repository = "https://example.invalid/choose-repository"
documentation = "https://example.invalid/choose-documentation"

[[projects]]
id = "navigation-check"
name = "Navigation check - use the same existing alias; no links on this row"
ssh_alias = "CHOOSE_EXISTING_ALIAS"
# Optional URLs omitted to check the 'Not provided' display.
```

Jadon can now use the installed build without rebuilding or activating a venv:

```powershell
git rev-parse HEAD
& .\.local\task5-session\venv\Scripts\ssh-workbench.exe --version
& .\.local\task5-session\venv\Scripts\ssh-workbench.exe --config .local\task5-session\projects.toml
```

Launching/selection reads that file without contacting a target. **C contacts
the configured SSH destination; R/D open a real browser.** These actions below
are for Jadon to perform. No passwords, private keys, MFA codes, sensitive
transcripts or screenshots are requested. Pause unexpected host-key/trust prompts
for independent verification; do not auto-accept, remove warnings, edit
known_hosts or disable checking. An actual login may create normal session or
audit records; use the existing trusted workflow without extra remote operations.

### Task 5 authorized Windows Terminal check, 2026-10-20

Jadon chose the repository and README URLs below and authorized one live SSH
connection to the alias already in the ignored configuration. The agent ran
checklist steps A, B, C and D in one owned Microsoft Windows Terminal 1.25.2733.0
window with PowerShell 7.6.7 on Windows build 26340. The installed wheel above
(0.0.1 from `9b28e86`) was used; `src/`, `pyproject.toml`, `uv.lock` and `README.md`
are unchanged between `9b28e86` and the tested branch head `5378fcd`.

The first row of the ignored configuration gained
`repository = "https://github.com/jkosber/ssh-workbench"` and
`documentation = "https://github.com/jkosber/ssh-workbench/blob/main/README.md"`.
The second row still omits both. A dated backup of the prior file was kept.

| Step | Agent-observed result |
| --- | --- |
| A. Baseline | `--version` printed 0.0.1. Startup selected the first project with list focus. Up/Down switched details between both projects; the second showed `Not provided` twice. Tab moved the accent border to details; Down/End scrolled the one overflowing line and Home returned. Shift+Tab restored list navigation. |
| B. Browser | R reported `Repository browser request accepted. Project 1: manual-target`. Windows' URL association opened Google Chrome 155.0.8059.85, whose address bar showed `github.com/jkosber/ssh-workbench` and whose title was the repository page. D reported the matching acceptance and Chrome showed `github.com/jkosber/ssh-workbench/blob/main/README.md` with the README title. The private repository loaded in Chrome's existing signed-in session. R on the second project showed `Repository link not configured. Add it to the configuration and restart.` with `Project 2: navigation-check`. Navigation continued after returning from the browser, and Q exited 0 to usable shell input. |
| C. SSH | After a relaunch, C handed the terminal to native SSH. A remote shell prompt appeared with no password, MFA or host-key prompt. The agent typed only `exit`. Workbench returned with `SSH exited with status 0.`, the same project selected and list focus; Up/Down worked immediately. |
| D. Restoration | In the same session after the SSH return, the window was resized to 60x20, 120x40 and back to 80x24, with dimensions confirmed from the rendered screen. Up/Down worked at each size. At 60x20 the title and second name truncated, help text wrapped, the footer stayed visible, and details scrolled to the wrapped README URL. Q then exited 0 and `Write-Output` worked. A separate launch exited 0 with Ctrl+Q and `Write-Output` again worked. |

How it ran: Win32 `SendInput` keystrokes were sent only while the owned window
was in the foreground, and the run stopped otherwise. Screen text came from Windows UI Automation
and screenshots from `Graphics.CopyFromScreen` of that window only. Window size
was set with `SetWindowPos`. Fifteen Workbench-only PNGs are kept under ignored
`.local/task5-session/wt-20261020/`. No screenshot covered the SSH session or the
browser, and remote output was not recorded.

Run notes:

- The agent's environment sets `NO_COLOR=1`, which the new window inherited, so the
  first launch rendered monochrome. The variable was removed in that test shell
  only and the checks were repeated with normal colors.
- Jadon accidentally typed into the window during size calibration, before
  Workbench started. That only affected a calibration command in the shell.
- The Chrome tabs opened by R/D were left open. The test window was closed with `exit`.

No application defect was found. The link status after R on the second project
kept naming project 2 when the selection moved back to project 1, as documented:
link results stay attributed to the project that requested them.

### Task 5 footer click check, 2026-10-20

The README says the footer's Connect, Repository and Documentation actions can be
clicked. Automated tests only confirm those footer keys exist and are visible,
so the agent clicked them with the mouse in a new owned Windows Terminal window,
using the same setup as the check above. Source is unchanged from that check.
Each click targeted the label's on-screen bounds from UI Automation and
was refused unless that point belonged to the owned window. The cursor was
restored afterwards.

| Click | Agent-observed result |
| --- | --- |
| Connect, in `scripts/check_terminal.py` (local child, no SSH) | The first fixture project handed off to the local child with terminal stdin/stdout/stderr. After `return`, Workbench showed `SSH exited with status 0.` with the same project selected and list focus |
| Quit, in the fixture | Exited 0; `Write-Output` worked |
| Repository, installed build, list focused | `Repository browser request accepted. Project 1: manual-target`; Chrome showed `github.com/jkosber/ssh-workbench` |
| Documentation, installed build, details focused | Matching acceptance; Chrome showed the README URL. Details kept focus and the selection was unchanged |
| Quit, installed build | Exited 0; `Write-Output` worked |

Connect was clicked only in the local-child fixture, so no SSH connection was
made. Screenshots are in ignored `.local/task5-session/wt-footer-20261020/`.

### Task 5 additional SSH targets and review fixes, 2026-10-20

**Review.** Three read-only reviews covered the whole project: code and tests,
documentation accuracy, and privacy. No crash or bad-state bug was found. Git
history on all branches, the PR text and the built package contain no private
paths, hosts, aliases, tokens or AI attribution. The reviews confirmed two defects,
each fixed after a failing test was committed (`b753e3b`):

| Defect | Fix |
| --- | --- |
| On Windows, `shutil.which` checks the current directory before `PATH` unless `NoDefaultCurrentDirectoryInExePath` is set, so C could run an `ssh.exe` sitting in the folder Workbench was started from. A relative `PATH` entry had the same effect on any platform | `2653323`: a relative lookup result is discarded and only absolute `PATH` entries are searched |
| A configuration saved as UTF-8 with a byte-order mark (Windows PowerShell 5.1 `-Encoding UTF8`) failed with "invalid syntax at line 1, column 1" | `b8a4218`: a leading byte-order mark is removed before parsing |

At `b8a4218`, locked sync, Ruff lint/format, 431 tests, `uv build` and
`scripts/check_package.py` passed.

**More SSH targets.** Jadon approved two more aliases for machines outside his
homelab; their names stay in the ignored configuration. The agent ran the current
checkout with `uv run --locked ssh-workbench` in a new owned Windows Terminal
window, under the same rules as the earlier check. It printed no remote output and
took no screenshots of SSH sessions.

| Target | Agent-observed result |
| --- | --- |
| Second alias, first attempt (the workstation's VPN was off) | Native SSH reported a connection timeout. Workbench returned with `SSH exited with status 255. Check the SSH client's message and alias; C retries.` and kept the project selected. This is the first real-world check of the nonzero-exit path |
| Second alias, retry with the VPN on | A remote shell prompt appeared with no password or host-key prompt; `exit` returned `SSH exited with status 0.` with the selection kept. Ctrl+Q then exited 0 and `Write-Output` worked |
| Third alias | Same as the retry: remote prompt, `exit`, status 0, selection kept. Q exited 0 and `Write-Output` worked |

A harness bug sent one extra Ctrl+C after the third alias's `exit`. It reached
Workbench after SSH had returned, and Textual showed its built-in "Do you want to
quit? Press ctrl+q to quit the app" notice. Workbench kept running and no input
reached the remote host. The harness was corrected.

### Task 5 user-executed manual session

Results below distinguish user reports from agent observations. This manual
session follows the prepared installed build, version 0.0.1 from `9b28e86`;
the agent did not observe the user's executable or authentication session.

**User-reported, 2026-10-12:** In Microsoft Windows Terminal running PowerShell,
C switched to SSH in the same terminal session. Exiting SSH returned directly
to Workbench, kept the same project selected, accepted Up/Down immediately, and
displayed `SSH exited with status 0`. This completes the reported handoff/normal
return check; it does not establish browser dispatch, resize or quit restoration.
No sensitive transcript or screenshot was requested or collected for this report.

The checklist below records Windows Terminal status. Step C is Jadon's report.
Steps A, B and D passed in the
[agent Windows Terminal check](#task-5-authorized-windows-terminal-check-2026-10-20),
which also repeated C. Those are agent observations, not user reports.

- [x] **A. Baseline (local; agent-observed pass, 2026-10-20):** Record 0.0.1, the tested commit, Windows version and
  Windows Terminal version. Fill the private configuration, launch with the command
  above, and check Up/Down selection, details, Tab/Shift+Tab focus and detail scrolling.
- [x] **B. Browser (opens real destinations; agent-observed pass, 2026-10-20):** Select `manual-target`; explicitly
  invoke R / Repository and D / Documentation. Observe the intended destination
  and page result in the browser separately from Workbench's dispatch message.
  Return to the terminal, check navigation and Q, then relaunch for C.
- [x] **C. SSH (user-reported pass; contacts the chosen real system):** Use one existing noncritical
  host and the account already used there. If a direct baseline is needed, Jadon
  runs `ssh CHOOSE_EXISTING_ALIAS` after replacing the placeholder, authenticates
  privately and leaves normally. In Workbench use C / Connect, authenticate,
  leave normally, and verify the same selection, list focus, status and further use.
- [x] **D. Restoration (local; agent-observed pass, 2026-10-20):** After returning, resize the terminal and check
  navigation. Test Q and Ctrl+Q in separate launches; after each, confirm usable
  shell input, for example `Write-Output 'shell input works'`.

For deliberate failures, blocked openers and aggressive interruption, use only
the existing [link fixture](#task-4-stubbed-link-checklist) and
[local-child fixture](#task-3-local-terminal-fixture). Do not use wrong credentials,
interrupt unrelated remote work, stop services, change host keys or create outages.
The authorized Windows Terminal check above is complete within its recorded scope.

Report further observations briefly and without sensitive details: step A/B/C/D, pass/fail/not tested, expected
versus observed behavior, version/commit/terminal and any minimal reproduction.
Label them **user-reported**; keep agent fixture and automated evidence separate.
Browser acceptance alone is not proof of page loading. The readiness review
(scope, privacy, license) closed Task 5 on 2026-10-20.

## Task 4: errors and links, 2026-10-12

Starting state was inspected and fetched: clean `main` and `origin/main` both
pointed to Task 3 merge `eeb6e39bf93a8ba1532503a7a2e0e565f9a9d8f2`, with the expected
`jkosber/ssh-workbench` origin. No Task 4 branch existed; `feat/errors-and-links`
was created from that commit. No unrelated tracked work needed preservation.
Existing ignored evidence was preserved. Version 0.0.1, Python 3.14.7,
Textual 8.2.8 and the lockfile/dependencies are unchanged.

These are **local Windows results from the implementation session**, not remote
CI for Task 4. At that handoff, nothing had been staged, committed, pushed,
opened as a PR or published. Earlier Task 3 Windows/
Ubuntu CI and terminal evidence below remain historical evidence for that merge.

| Check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed with the existing environment and lockfile |
| CLI help/version | Passed; version remains 0.0.1 |
| `uv run --locked ssh-workbench` | Native no-config screen; R/D explained no selection; Q returned status 0 to the shell |
| Ruff lint and format | Passed |
| Full pytest, fresh ignored base directory | 417 passed: 289 prior tests, 92 URL/boundary cases, 35 link UI/concurrency cases, one additional negative SSH status case |
| `uv build` | Source archive and wheel built; existing warning that the installed uv 0.13.0 is outside the project's uv-build range remains, with no dependency change |
| Isolated package validation | Passed CLI/config/loader, verified wheel imports, headless actions, substituted SSH/link results and separate-process blocked-opener Q/Ctrl+Q exits |
| Documentation and final review | 43 relative links/anchors and whitespace checks passed; source and README/UI semantic review completed; deterministic code scan reported no findings (README skipped by prose scope) |
| Native WezTerm fixture | Accepted, reported failure, raised error, missing links, repeat/blocked requests, scrolling, resizing and both quit keys passed through substituted boundaries |
| Native screenshots | Attempted with the established Windows capture helper; owned test window could not be brought to foreground reliably. Captures were obscured, excluded as evidence and removed |

The first targeted run exposed a real scroll shift when link status changed
height; a fixed three-row status region corrected it. A later source review found
the closed-loop posting race and ambiguous clipped long IDs; a narrow posting
guard and captured project number corrected them, with focused regressions.
The final full suite includes those corrections. One initial pytest invocation
also hit an access-denied error cleaning the shared Windows temporary-directory
link; subsequent complete runs used fresh `.local` base directories without
changing permissions or deleting the shared directory.

### Task 4 acceptance evidence

| Criterion | Verification and limits |
| --- | --- |
| Existing configuration and SSH errors remain actionable | Original loader/CLI/SSH tests passed. Nonzero and negative codes retain their value and add neutral client-message/alias retry guidance; interruption offers C/Q |
| Explicit R/D with visible bindings from both panes | Headless keyboard checks at all three sizes; native accepted requests from list and details; footer controls visible in terminal text |
| No automatic action; absent links/no selection | Guarded startup/navigation/focus/Enter/click/resize tests; missing links and native no-config R/D feedback passed |
| Capture project, kind and exact URL | Both keys pass their selected URL including query/fragment/encoding; slow completion preserves newer selection, focus and scrolling and attributes the original project |
| Literal, sanitized output | Markup/control metadata stays literal; errors omit private markers and query values; long IDs cannot obscure the captured project number |
| Shared validation and independent dispatch | Loader and boundary contract cases passed; malformed URLs cannot reach Windows/GIO calls; exact argv and detached/null terminal streams asserted |
| Outcomes and supported environment policy | Accepted/missing/invalid/unavailable/failure/exception cases passed with substitutions. Windows associations and Linux desktop GIO implemented; macOS/other environments explicitly unavailable |
| Responsiveness/repeats/shutdown | Event-controlled slow requests permit navigation and quit; repeats do not queue; stale messages and closed-loop races are discarded. Installed subprocesses exit with a forever-blocked opener on both quit keys |
| No SSH lifecycle interference | Original real-suspension, SIGINT restoration and lookup/transition regression tests passed. A pending browser completion during substituted SSH preserves both statuses and the newer selection |
| Layout and scrolling | Headless 60x20/80x24/120x40 checks passed. Native WezTerm dimensions and text verified live resizing and wrapped/scrollable content; this session has no usable native pixel evidence |
| Packaging and records | Isolated Python `-I` runs and assertions verify every imported Workbench module resides in the disposable installation, even with checkout `PYTHONPATH`; documentation and vault session/project/daily records updated |

### Task 4 native fixture details

The existing portable WezTerm `20240203-110809-5046fc22` ran in a new owned
process with an explicit test configuration, no SSH/WSL domains and a clean
PowerShell profile. `scripts/check_links.py` used fictional projects and stubbed
Windows `os.startfile`; reported failure was also substituted because startfile
has no failure return value. Guards rejected other browser, process and network
actions. No real browser, website, SSH configuration, keys, inventory or host was
used. The application dependency set and global terminal settings were untouched.

Verified process/socket identity preceded CLI input. Readiness checks used
expected terminal text and reported dimensions. The same fixture resized
80x24 -> 60x20 -> 120x40 -> 80x24 at 96 DPI. Both actions accepted from either pane;
failed/missing/error cases showed safe guidance at 60x20. The long fixture stayed
at the same scroll position after an accepted request: before/after screen text
differed only in the link-status line. A blocked request retained its original
project number while selection/focus moved and repeated R/D reported pending.
Q and Ctrl+Q each exited status 0 despite the indefinitely blocked stub; both
shell input/echo checks passed. A normal no-config CLI run also exited cleanly.

Some early resize snapshots preceded the application's redraw, and one expected
text condition spanned a wrapped line; settled text and narrower readiness
conditions confirmed the final states. No resize workaround was introduced.
The screenshot helper could not verify the owned window as foreground, so no
appearance claim is made. Existing Task 2 native screenshots remain valid for
their recorded state. The owned terminal/process was closed; reproducible text
and dimension evidence remain ignored locally.

### Task 4 stubbed link checklist

These commands do not open a real browser or connect to SSH:

```text
uv sync --locked
uv run --locked ssh-workbench --help
uv run --locked ssh-workbench --version
uv run --locked python scripts/check_links.py
```

1. Select the accepted fixture; try R from the list and D from details, then
   reverse them. Check literal metadata, the request result and unchanged focus.
2. Try reported failure, raised error and missing links. Confirm useful feedback
   with no raw exception/query data. Retry an action after its result.
3. Use the long fixture, scroll with Page Down/End, invoke a link and verify
   preserved scrolling. Resize to 60x20, 80x24 and 120x40 and check the footer.
4. Choose the blocked fixture last. Press R/D again, change selection/pane and
   confirm the original request remains identified. Q must return to the shell;
   repeat with Ctrl+Q. The stub stays blocked until process exit.

### Task 4 fixture lifetime correction, 2026-10-12

The review after the original runs above returned **FIX BEFORE COMMIT**. It
confirmed a development-fixture defect: `check_links.py` removed its external-action
patches when `app.run()` returned, although a daemon already past its shutdown
check could still reach dispatch. A controlled Windows reproduction reached an
outer sentinel after teardown; no real browser opened. The original 417-test and
WezTerm results above describe the pre-correction candidate, not this correction.
No production application regression was confirmed.

The fixture entry point now starts every guard before constructing the app and
intentionally leaves them installed until process exit, including after normal
return, `RuntimeError` or `KeyboardInterrupt`. It registers no restoration
cleanup, waits for no blocked daemon and uses no forced interpreter exit.
Importing the script installs no guards. Production application, SSH/SIGINT,
version 0.0.1, dependencies, build requirements and CI tooling are unchanged.

[Fixture regressions](../../tests/test_link_fixture.py) run the actual entry point
through a [child-only harness](../../tests/link_fixture_process.py). Events pause a
real R-triggered application worker inside URL validation, after its shutdown
check but before dispatch. Q closes the TUI and the entry point returns or raises;
only then does the harness release validation. Positive dispatch and completion
events establish that the worker ran. Harmless outer sentinels remain beneath
the fixture guards, including when testing the defective version.

| Correction check | Observed result |
| --- | --- |
| Same six race tests against a disposable pre-correction copy | All six failed as expected: fixture dispatch 0, outer sentinel 1, guards restored; normal/error/interrupt cases on both dispatch paths |
| Corrected fixture tests | 11 passed: six race cases, four blocked-opener exits, one import-side-effect check |
| Race completion | Fixture dispatch 1, outer sentinel 0; all guarded callable identities retained after entry-point unwind |
| Blocked-opener interpreter exit | Q and Ctrl+Q passed for Windows and simulated Linux; the original fixture stub remained blocked. A parent timeout fails the test, rather than supplying passing exit evidence |
| Affected fixture/link/UI tests | 138 passed, including Windows success with `os.startfile` explicitly returning `None` |
| Full pytest with a unique disposable base directory | 428 passed; no temporary-directory cleanup error |
| Locked sync, Ruff lint/format, CLI help/version | Passed; 29 files (20 Python, 9 Markdown) formatted and CLI version 0.0.1 |
| Build and isolated package validation | Passed, including installed-import assertions and existing blocked-opener Q/Ctrl+Q processes |
| Relative documentation links/anchors and whitespace | 45 links/anchors passed; `git diff --check` passed |
| Focused independent review | No additional correction defect found; this was a static review, not another native-platform run |

The existing build warning recurred: uv 0.13.0 is outside the declared
`uv_build>=0.12.24,<0.13.0` range. No tooling was upgraded or requirements changed
to suppress it. The build and installed-package checks passed; the prior review's
backend-provenance limitation remains.

After the correction and regressions passed, the standalone script was exercised
in an owned Windows pseudoterminal through the supported cmd.exe/PowerShell route.
R from the list and D from details reported accepted fixture requests. A blocked
request allowed repeated-action feedback, changed selection and pane focus.
Q and Ctrl+Q each returned application status 0 to working PowerShell input; the
owned shell then exited normally. This was a focused terminal input/return check,
not a repeat of WezTerm resizing or screenshot verification. No new screenshots
were taken, and obscured historical captures remain excluded.

Linux-path tests simulate the platform and GIO lookup/runner on Windows; they do
not establish native Linux desktop behavior. All browser/process dispatch in
these fixture tests was substituted. No real browser, GIO dispatch, host or SSH
configuration was used. At the correction handoff, changes remained unstaged and
uncommitted on `feat/errors-and-links` at base
`eeb6e39bf93a8ba1532503a7a2e0e565f9a9d8f2`. No Task 4 remote CI had run and no
Task 5 work was performed. Subsequent PR and CI status belongs in the PR record.

**Would open a real browser:** running the normal application with a configured
URL and pressing R/D (or clicking its footer action). This was not tested.
A separately approved manual test should name the URL and running environment,
then observe actual dispatch; Workbench cannot establish page loading or closure.
Real SSH/authentication/host-key prompts, Linux desktop dispatch, macOS execution,
Windows Terminal handoff, other DPI settings and screen readers remain unverified.
Jadon's earlier Windows Terminal navigation confirmation is not SSH handoff
evidence. No Task 5, release, portfolio or infrastructure work was performed.

## Task 3: native SSH, 2026-10-12

Implemented on `feat/native-ssh` from clean, fetched `main` at
`4852e1c3719700d1e5ea8d6c867bf13bd3c50eb0`. Before branching, PR #2 was verified
merged, local main matched origin, no open PRs existed and
[merged-main CI](https://github.com/jkosber/ssh-workbench/actions/runs/38304097388)
had passed. That CI result applies to Task 2. Task 3 was initially held
uncommitted for review. On 2026-10-12, Jadon authorized staging, committing,
pushing this feature branch and opening a PR after checking the Task 3 criteria.

Version remains 0.0.1; Python 3.14.7, Textual 8.2.8, dependencies and lockfile are
unchanged. All development fixtures are fictional. Executable lookup and process
invocation were substituted; no real SSH client, configuration, keys, inventories
or hosts were used.

| Local Windows check | Observed result |
| --- | --- |
| Locked sync | Passed without dependency changes |
| Ruff lint and format check | Passed |
| Full pytest suite, fresh explicit `.local` base directory | 289 passed: all 213 preexisting tests plus 76 launch, signal and UI cases |
| CLI help, CLI version and module version | Passed; Connect description updated, version remains 0.0.1 |
| No-config CLI in a Windows pseudoterminal | Correct empty message and disabled C binding; C remained inert and Q exited with status 0 |
| Build | Source archive and wheel built successfully at 0.0.1 |
| Isolated wheel validation | Passed outside the checkout with locked runtime dependencies: help/version, loader, missing-config errors, headless selection/quit, and substituted SSH success, status 7, start error and interruption |

Local uv 0.13.0 still warns that the existing build-backend range excludes
0.13.0; the build and isolated installation succeeded with the unchanged range.
An initial focused test run using the shared pytest temporary directory hit the
previously observed Windows `pytest-current` cleanup permission error. A fresh
explicit base directory passed; no permission changes or weakened tests were
used. The isolated package environment was removed normally.

The new tests assert the exact absolute executable/one-alias argv, `shell=False`,
inherited streams, Windows `ssh.exe` versus POSIX `ssh` lookup, alias/type
rejection before lookup, sanitized launch errors and restoration of the original
SIGINT handler. They retain process/network/browser guards. UI tests cover no
selection, no automatic launch, visible C binding, selected alias, status and
focus restoration, repeated/reentrant actions, unsupported suspension and long
literal/scrolling content at 60x20, 80x24 and 120x40.

Exception-path tests use **installed `App.suspend()`**, replacing only the
headless driver's suspension methods. Textual 8.2.8 has a bare yield followed by
resume, so the app catches expected errors inside the context. Assertions verify
suspend/launch/resume ordering after success, nonzero exit, launch error and
`KeyboardInterrupt`. Source inspection also confirmed why the parent needs a
temporary callable SIGINT handler: asyncio may otherwise cancel its main task,
and subprocess may terminate a still-running child during exception cleanup.

Independent review found and corrected an interruption gap before the original
signal guard: Ctrl+C during executable lookup could cancel asyncio's main task.
The shared guard now spans lookup and the entire suspend/resume cycle. Eight
regression cases run with asyncio's actual installed SIGINT handler, invoking
the active handler during lookup and both driver transitions, on success and
error paths. Cancellation counts stay zero, the original handler is restored,
and the browser remains usable after yielding to the event loop. The focused
review follow-up confirmed the fix with no remaining finding. The native
terminal checks below were repeated after this correction.

Final diff/whitespace and package-content checks passed; wheel modules match the
source and both archives exclude private workspace directories. All 39 relative
documentation links/anchors resolve. The deterministic code scan reported no
findings; README was outside its configured prose scope and was read in review.

### Real Windows terminal evidence

The agent ran `scripts/check_terminal.py` through `uv run --locked python` in a
new, isolated native WezTerm `20240203-110809-5046fc22` window on Windows. The
terminal reported 80x24 at 96 DPI, `xterm-256color` and `truecolor`. Its fixed local
Python children replace SSH while retaining production alias validation,
signal handling, `App.suspend` and result rendering.

| Native terminal check | Agent-observed result |
| --- | --- |
| Terminal ownership | Child stdin, stdout and stderr all reported `isatty=True`; typed text was echoed and read by the child, and its stderr appeared directly |
| Normal and nonzero exit | Status 0 and 7 returned to the same project; navigation worked immediately afterward |
| Connect from details | C launched the selected alias; afterward Down changed the project, confirming focus returned to the list |
| Ctrl+C ending a child | Child received Ctrl+C and returned 130; the browser resumed and displayed 130 |
| Ctrl+C while a child continues | Two successive interrupts reached the child; it stayed active, accepted more text and returned only after explicit input; the browser then displayed status 0 |
| Missing executable and process-start error | Both showed the expected messages with the selection intact; repeated failed launches and subsequent navigation worked |
| Injected launch interruption | `KeyboardInterrupt` returned to the browser with an interruption message and usable navigation |
| Repeat launch and quit | A fresh interactive-shell launch connected again; Q and Ctrl+Q returned to PowerShell with app status 0, and subsequent commands were accepted and echoed |

An initial `pwsh -File` harness ended after quitting because Ctrl+C had also
cancelled the enclosing PowerShell script. Repeating with an interactive
`-NoExit` shell established a working prompt and status 0. This was a test-harness
correction; no application workaround or shell profile changes were made.
All owned test windows and their shell/child processes exited. Existing user
terminals were preserved. Text captures, terminal metadata and an evidence-check
summary remain under ignored `.local/task3-native-20261012/`.

This is native process/input evidence, not a headless or browser screenshot
claim. Jadon separately reported on 2026-10-12 that Task 3 navigation works in
Microsoft Windows Terminal. This is human-reported navigation evidence; it does
not establish terminal handoff, interruption or authentication behavior in that
terminal. Real SSH authentication,
host-key prompts and connections remain untested and require separately approved
targets/actions. Linux/macOS native terminal behavior, Microsoft Windows
Terminal handoff, native resizing, other DPI settings and screen readers remain
unverified for this change.

### Task 3 local terminal fixture

From an interactive terminal, run:

```text
uv run --locked python scripts/check_terminal.py
```

This script accepts only built-in fictional cases. It replaces executable lookup
and process invocation before calling the production launcher; it never invokes
SSH or loads a project inventory. Use this fixture for development handoff checks.

1. Select **Normal exit**, press C, check that all three terminal flags are True,
   type some text and confirm the child echoes it. Type `return` and verify status
   0, the same selection, list focus and working arrow keys.
2. Select **Nonzero exit**, Tab to details, press C, then type `return`. Check
   status 7 and that Down changes the selection afterward.
3. Select **Ctrl+C exits the child**, press C and Ctrl+C. Check status 130.
4. Select **Ctrl+C keeps the child running**, press C and Ctrl+C twice. Confirm
   the child still accepts text. Type `return` to resume the browser.
5. Exercise the three simulated error/interruption entries. Check their messages,
   preserved selection, navigation and repeated C actions.
6. Quit with Q and confirm shell input/echo. Run the fixture again, connect and
   return, then quit with Ctrl+Q and check the shell again.

Record the terminal, operating system and actual results. This local fixture does
not verify the native SSH client's authentication or network behavior.

### Task 3 pre-PR verification, 2026-10-12

Jadon authorized the commit, push and PR after confirming navigation in
Microsoft Windows Terminal. A fresh local run found one intermittent footer
assertion: the test queried keys while Textual was asynchronously removing and
remounting them. The Connect action remained enabled. A probe reproduced that
transient state once in 40 starts, and the next refresh restored the keys.

The visibility test now waits for the Connect key with a bounded five-second
timeout and retains every count, key, visibility, label, screen-region and
no-launch assertion. Sixty startup probes across the three test sizes passed;
six needed another readiness pause. No application code changed for this fix.

After the test correction, all 289 tests and Ruff lint/format checks passed.
Locked sync, CLI help/version, build and isolated package validation also passed,
as did all 39 relative documentation links/anchors and whitespace checks.
The README and PR draft received a documentation review with no actionable
findings. The earlier native fixture evidence still applies to the unchanged
application code.

### Task 3 PR and remote CI, 2026-10-12

[PR #3](https://github.com/jkosber/ssh-workbench/pull/3) was opened from
`feat/native-ssh` into `main` after the authorized commit and push. Implementation
commit `da64844f47a4f872ca1ece582d70049eab68a422` contains the Task 3 behavior,
tests, fixture and documentation, including the footer-test readiness correction.

[Push CI 38325768048](https://github.com/jkosber/ssh-workbench/actions/runs/38325768048)
and [PR CI 38325776914](https://github.com/jkosber/ssh-workbench/actions/runs/38325776914)
passed on both Windows and Ubuntu. Each job passed locked installation, Ruff,
all 289 tests, build and isolated package validation. These results apply to
`da64844`. The documentation follow-up at `b71423c` also passed
[push CI 38325986119](https://github.com/jkosber/ssh-workbench/actions/runs/38325986119)
and [PR CI 38325990481](https://github.com/jkosber/ssh-workbench/actions/runs/38325990481)
on both platforms, including 289 tests and isolated package checks. All 40
relative documentation links/anchors resolved. The PR records checks for later
documentation commits, its merge commit and current status.

CI verifies automated and substituted process behavior. Linux native terminal
handoff, macOS execution, real SSH authentication and the remaining terminal
limits above still need their own evidence.

## Task 2 PR documentation and remote CI, 2026-10-12

[PR #2](https://github.com/jkosber/ssh-workbench/pull/2) contains the read-only
project browser, tests, fictional example and updated usage, architecture,
contribution, roadmap and changelog documentation. Its implementation commit is
`aacbb6ddda37d38b39c4e4ccc9f104bf4466dce1`; local files matched that pushed tree.

[Push CI 38302914229](https://github.com/jkosber/ssh-workbench/actions/runs/38302914229)
and [PR CI 38302918709](https://github.com/jkosber/ssh-workbench/actions/runs/38302918709)
both completed successfully for that commit. Each Windows and Ubuntu job passed
locked installation, lint/format, all 213 tests, the build and isolated wheel
checks. Job logs confirm the test count and installed-package browser checks.

This documentation-only follow-up records those observed results; it changes no
application code, dependencies or version. The PR records checks for its current
head and its merge status. Task 3 was unimplemented at that point; its later
implementation and verification are recorded at the top of this document.

## Task 2 final local verification, 2026-10-12

Before committing Task 2, locked sync, Ruff lint/format, all 213 tests, CLI
help/version, module version, the build and isolated installed-wheel check passed
again on Windows with Python 3.14.7 and Textual 8.2.8. The package remains 0.0.1;
dependencies and the lockfile are unchanged. Local uv 0.13.0 warned that the
existing build-backend range excludes 0.13.0; both artifact builds and installation
checks succeeded with that existing range. CI still pins uv 0.12.24.

The earlier report of disappearing project names was a mistaken screenshot
interpretation. Reinspection of the original, settled and timer-driven 120x40
captures shows both names clearly while details has focus. An independent review
confirmed this and repeated headless 60x20 -> 120x40 rendering twice: both labels
remained in the exported SVGs and rendered list rows. No application defect or
production workaround was established; the inaccurate finding below is corrected.

The user delegated terminal checks to the agent and authorized committing the
verified Task 2 work and opening a PR into `main`. The preceding console, browser
and native screenshot checks provide that evidence. Human review and merge
authorization remain separate. Windows Terminal live resizing, other DPI settings
and screen readers were not tested. This section records local results only;
the remote CI evidence is recorded above.

## Task 2 desktop screenshot follow-up, 2026-10-12

At the user's request, direct desktop capture worked around the desktop tool's
missing terminal-window targets. Windows
[Graphics.CopyFromScreen](https://learn.microsoft.com/en-us/dotnet/api/system.drawing.graphics.copyfromscreen)
captured the primary 1920x1080 monitor, and the agent inspected the saved PNGs.
This establishes a working native screenshot route. The test window must be
visible and unobstructed; this method captures the desktop as displayed.

Windows Terminal 1.25.2733.0 was inspected at a console-confirmed 80x24. Its
test tab was brought forward with the terminal's `focus-tab` CLI command.
The initial project selection, focus border, all five fields and footer were
visible. This was a startup appearance check, not a live-resize or keyboard
check in Windows Terminal.

Portable WezTerm screenshots covered 80x24, 60x20 and 120x40, then return to
80x24. They showed selection, pane focus, narrow reference wrapping, scrolling
to the final field, and Studio's absent references. The initial tool-launched
process inherited `NO_COLOR=1`; removing it only in the test child restored color.
The colored WezTerm child reported `xterm-256color` and `truecolor`. No personal
profile or global environment was changed.

**Corrected observation:** the 120x40 captures show both project names while
details has focus. An initial claim that the names disappeared was incorrect,
as confirmed by reinspection and independent review. Focusing the list changes
its selection highlight and border as expected; it does not restore missing text.

The colored WezTerm run exited with status 0 and restored working shell input
and echo. Owned test windows were closed; existing user terminals were preserved.
Screenshots, the capture helper and evidence remain under ignored `.local/`;
desktop images were not added to Git. No application or dependency changes were
needed. The prior automated results remain current; no suite rerun was needed
for this experiment. Other DPI settings and screen readers were not tested.

## Task 2 native terminal follow-up, 2026-10-12

A separate Windows Terminal 1.25.2733.0 window launched the supported fictional
example with an 80x24 size request. The user confirmed seeing the test window.
The desktop tool did not return that window as a capture/input target, so its
appearance and native resize behavior could not be inspected in that attempt.
Window visibility alone is not a visual acceptance result. The later desktop
screenshot follow-up above establishes a separate capture route.

The official portable WezTerm `20240203-110809-5046fc22` Windows archive was
verified against its published SHA-256 and extracted under ignored `.local/`.
An explicit test configuration, separate process/class and isolated PowerShell
session kept the check independent of personal terminal configuration. The
application still used locked Python 3.14.7 and Textual 8.2.8.

| Native WezTerm check | Agent-observed result |
| --- | --- |
| Live window resizing | The same running application resized through 80x24 -> 60x20 -> 120x40 -> 80x24 using `window:set_inner_size`; CLI-reported pane dimensions matched each size at 96 DPI |
| Project navigation | Up/Down changed Garden/Studio details; selection persisted during resizing and changing selection reset details to the top |
| Pane focus and scrolling | Tab/Shift+Tab changed the pane receiving input; End in details reached both absent optional references at 60x20; expanding restored all fields |
| Narrow layout | Captured terminal text showed wrapped Garden references at 60x20 and complete layout recovery at larger sizes |
| Q and Ctrl+Q | Separate application runs exited with status 0, restored an 80x24 PowerShell console, and accepted/echoed the test input afterward |

WezTerm's `cli list`, `get-text` and `send-text --no-paste` worked when directed
to the verified test process's socket. Class-based discovery failed in this
environment. Input delivery completes before application redraw; early snapshots
were stale, so later observations confirmed the expected changes. Watched-file
configuration reloads called the documented
[native window sizing API](https://wezterm.org/config/lua/window/set_inner_size.html);
this was not browser resizing or a headless test. The upstream CLI documents
[screen-text retrieval](https://wezterm.org/cli/cli/get-text.html) and
[input delivery](https://wezterm.org/cli/cli/send-text.html).

The desktop tool also did not expose WezTerm for capture. Text/ANSI captures and
reported dimensions establish native terminal behavior, not rendered-pixel,
font, antialiasing or visual-focus verification. Native screenshots were obtained
in the later desktop follow-up above; screen-reader behavior remains unverified.

Both test terminals were closed, preserving the user's existing terminal.
The isolated harness and text/dimension evidence remain under ignored `.local/`.
No application or dependency changes were needed; no global settings, staging,
commits or pushes changed. No additional automated-suite run was needed for this
terminal experiment and documentation update.

## Task 2 browser visual follow-up, 2026-10-12

The existing Playwright browser tools exercised the real application through
`textual-serve` 1.1.3 on localhost. The helper ran with `uv run --locked --with
textual-serve==1.1.3`; it was not added to the project dependencies or lockfile.
The application still used locked Textual 8.2.8 and Python 3.14.7. Only the
supported fictional example was loaded.

Agent-inspected screenshots covered 80x24, 60x20 and 120x40 cell layouts
(720x504, 540x420 and 1080x840 browser pixels with the measured 9x21 cell size).
The same running session resized through 80x24 -> 60x20 -> 120x40 -> 80x24.
Selection survived resizing. Up/Down changed the selected project and its
details; Tab/Shift+Tab visibly moved pane focus. At 60x20, reference text wrapped
and End scrolled to the final optional field. Returning to a larger size restored
the full layout. Q ended the application session, confirmed by the browser's
`Session ended` message.

Screenshots and browser-tool logs are retained locally under ignored `.local/`.
The temporary tab and server were closed after the check. No application-code
changes, global settings, security changes, staging, commits or pushes were
needed. These are browser-rendered visual and live-resize results, separate from
the console evidence below. Normal Windows Terminal font/DPI behavior, native
window resizing and screen-reader behavior remain unverified; no human visual
confirmation is claimed.

## Task 2 interactive console follow-up, 2026-10-12

The installed application was exercised through a real Windows pseudoterminal
at 80x24, independently of Textual's headless pilot. The normal tool PowerShell
launch failed with `Access is denied` before the app started. Selecting the
existing `cmd.exe` shell worked; an isolated `pwsh -NoProfile` session launched
through it also worked. No security settings or user profiles were changed.
This establishes console input/output behavior, not a visual check in the user's
normal Windows Terminal window.

| Flow | Agent-observed result |
| --- | --- |
| Supported two-project example | Garden starts selected; Down shows Studio's ID/name/alias and two `Not provided` references; Up restores Garden and both references |
| Focus and long details | Tab/Shift+Tab switch panes; Page Down/Page Up and End/Home reach long references and return to the initial fields; selecting another project resets the details to the top |
| Literal and Unicode display | Fictional Japanese text and `[bold]` text remain visible; newline/tab/ESC/direction characters appear as literal escapes in the terminal output; long names truncate in the list and wrap in details |
| Quoting paths | Explicit configuration with a space in its filename loads successfully |
| Q and Ctrl+Q | Both exit cleanly; Q was also exercised from details focus; the PowerShell prompt returns and subsequent typed commands report application exit status 0 |
| No configuration and empty array | Distinct informative screens appear; both quit cleanly with status 0 |
| Missing file and invalid alias | Concise field/domain errors appear without a traceback or supplied alias; PowerShell reports status 2 |
| Help/version with a nonexistent config | Both work without loading the file; version stays 0.0.1 |
| Input preservation | All three temporary fictional files retained their original UTF-8/Windows-newline bytes; the missing file was not created |
| Existing full suite | 213 tests passed again using a fresh explicit pytest base directory, including headless 80x24/120x40/60x20 and resize coverage |

The test terminal was closed after verification. No application-code changes
were needed. At this stage Task 2 was unstaged/uncommitted, with no push or new
remote CI; later verification and handoff are recorded above.
Normal Windows Terminal appearance, real-window resizing and screen-reader
behavior remain unverified; no human visual confirmation is claimed. The manual
checklist below is retained for reproduction, with its functional paths now
covered by this additional console evidence.

## Task 2: project browser, 2026-10-09

Implemented locally on `feat/project-browser`, based directly on fetched
`origin/main` at `84d392f0e4fa00eaf129ecae715dff4262e4f97e`. Local `main` was
fast-forwarded to that merge without forcing or discarding work. The working
tree was clean at transition: earlier scaffold validation edits and shared
Serena settings were already committed in Task 1. All earlier evidence below
is retained. No Serena files or ignore policies were changed for Task 2.

Version remains 0.0.1, unreleased; dependencies and schema are unchanged. Task 2
was unstaged and uncommitted at this initial check, with no push or PR. These are
**local Windows results**, using Python 3.14.7 and Textual 8.2.8, not Task 2 remote CI.

| Acceptance criterion | Observed evidence |
| --- | --- |
| Explicit CLI-to-loader entry; no config discovery/writes | Real-loader CLI tests preserve file order, records and input bytes; no-config test rejects loader calls and fixture reads; installed-wheel smoke check exercises CLI to real headless UI |
| Clear no-config, empty, invalid and unreadable states | Both empty screens tested at 80x24, 120x40 and 60x20; malformed TOML, invalid schema fields, invalid UTF-8, missing files and simulated permission errors return sanitized status 2 before UI startup |
| Help/version independent of config | Console tests pass with a nonexistent `--config` before and after help/version; existing unknown-option coverage retained |
| Predictable selection, focus and all five details | Initial first selection/focus, loader order, Up/Down bounds, changing fields, absent optional references and Tab/Shift+Tab focus tested |
| Literal values; safe controls; original records retained | Markup/action/link-like names and URLs render as plain content with no markup spans; clicks/Enter remain inert; C0/C1, terminal escape, direction-control and separator cases show visible escapes; Unicode names and original object values checked |
| Long values and ordinary terminal sizes | All five long fields exercised with wrapping/scrolling at 80x24, 120x40 and 60x20, plus resize, pane bounds, no horizontal overflow, End scrolling and scroll reset on selection; 35-project list keeps selected row visible |
| Quit and read-only boundary | Q/Ctrl+Q exit with status 0 in no-config, empty and populated states, including details focus; common socket, process and browser boundaries fail application tests if called |

| Local check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed; no dependency changes |
| `uv run --locked ruff check .` | Passed |
| `uv run --locked ruff format --check .` | Passed; 19 Python files formatted |
| `uv run --locked pytest --basetemp <fresh-directory>` | 213 passed: 24 headless UI, 15 CLI and 174 loader tests |
| CLI help, CLI version, module version | Passed; help lists `--config PATH`; version remains `ssh-workbench 0.0.1` |
| `uv build` | Passed; source archive and wheel built at 0.0.1 |
| `uv run --locked python scripts/check_package.py` | Passed outside checkout: isolated locked-runtime install, help/version, missing-config error, loader and CLI-driven headless selection/quit at 80x24; fixture bytes unchanged |
| Diff, documentation links and package contents | Whitespace check passed; 23 local links/anchors resolved; wheel modules matched source; archives excluded `.local/`, `.serena/`, `.venv/` and Git metadata |
| Final review | Primary diff review and independent static review found no actionable defects; targeted added-content scan found no private absolute paths or credential-token patterns; staging area remained empty |

Tests use fictional metadata and temporary files. Fresh explicit pytest base
directories avoided the earlier shared-temp cleanup issue; no permissions or
security settings were changed. The isolated package environment was removed
normally. No actual SSH files or hosts were used.

The scaffold-only startup assertion now checks the intentional no-config screen;
the help expectation now includes the implemented configuration option. The
supported example contains two fictional projects for selection and absent-field
checks; its loader test still compares the exact expected records. No existing
coverage was skipped or removed to conceal a failure.

During verification, an overbroad test guard initially blocked Windows asyncio's
own local socket pair. The low-level connection guard now starts after event-loop
creation and before application execution. A long-details check also exposed
scrollbar-width reflow; the details pane now reserves scrollbar space. Tests wait
for completed scrolling animations before checking positions. The final full
suite passed with the original no-horizontal-overflow assertion retained.

The independent review covered the changed code, tests, documentation and
installed Textual behavior; it did not rerun the suite or inspect a real terminal.
The deterministic style scan reported one false positive in a test failure
message, not a code comment; README was outside that scanner's configured prose
scope and was read during review. These checks do not establish screen-reader
behavior, terminal restoration or a new Linux result.

### Task 2 Windows terminal checklist

The user delegated these checks to the agent. The 2026-10-12 console, browser,
native terminal and desktop screenshot follow-ups above record the results and
their limits. They do not claim human acceptance. This checklist remains available
for Jadon's PR review; the earlier scaffold confirmation does not verify this browser.

From the repository directory, run:

```text
uv sync --locked
uv run --locked ssh-workbench --config examples/projects.example.toml
```

- At 80x24, check that Garden demo starts selected/focused. Use Up/Down to select
  Studio demo and return; confirm all fields change and Studio's references say
  `Not provided`.
- Use Tab/Shift+Tab to check the visible focus border. With a temporary fictional
  configuration containing long names/references, scroll details with arrows,
  Page Up/Page Down and Home/End. Change selection and confirm scrolling resets.
- Resize the terminal and inspect readability, Unicode and literal markup-like
  text. References should have no application opening action.
- Quit with Q, rerun, and quit with Ctrl+Q. Confirm the shell prompt, echo and
  keyboard input return normally.
- Run without `--config`, then with a temporary `schema_version = 1` /
  `projects = []` file; check the distinct messages. Try a nonexistent config
  path and confirm a concise error and PowerShell `$LASTEXITCODE` of 2.

Record the observed result and platform after the check. SSH launching, opening
links, editing, search, discovery and remote commands are deferred.

## Verified Task 1 merge and remote CI, 2026-10-09

[PR #1](https://github.com/jkosber/ssh-workbench/pull/1) is merged into `main` at
`84d392f0e4fa00eaf129ecae715dff4262e4f97e` (2026-10-09 20:14:40 UTC).
Its final head was `c08259a7b88401bc46bdfa0c42793af4e1ab3863`; that commit is a
parent of the merge, and the fetched main tree matches the final Task 1 tree.
The repository was verified as owned by `jkosber` and private. This session
verified the existing merge; it did not merge a second time.

Both [push CI 37984283908](https://github.com/jkosber/ssh-workbench/actions/runs/37984283908)
and [PR CI 37984288701](https://github.com/jkosber/ssh-workbench/actions/runs/37984288701)
are completed successfully for head `c08259a`. Each has successful named
`Checks (windows-latest)` and `Checks (ubuntu-latest)` jobs. These final-head
results supersede the earlier pre-merge note's pending-CI statement and are
separate from the historical scaffold CI and Task 2's local checks above.

## Task 1: local project metadata, 2026-10-09

Initial local checks for `feat/project-config`, committed as `c6ea622`, with
Python 3.14.7 on Windows. Version remains 0.0.1. These tables describe that
snapshot; the pre-merge follow-up below records the later corrections.

| Acceptance criterion | Observed evidence |
| --- | --- |
| Explicit `Path`, UTF-8, ordered typed records; independent of Textual/processes | Single/multiple-project, Unicode and direct string-parser tests passed; source review confirms only explicit file reading and standard-library parsing/validation |
| Integer schema version 1, required project array, explicit empty array | Valid/empty cases passed; missing structure, wrong shapes, unsupported versions, booleans and float versions rejected |
| Unique IDs, nonempty names and restricted SSH aliases | Missing/type/empty-field, duplicate-ID and invalid-ID tests passed; parameterized safe/hostile alias cases passed |
| Optional HTTP/HTTPS references without credentials; unknown fields rejected | Both optional fields tested absent and present; type/empty, scheme, credentials, whitespace/control, backslash and host/port failures passed; no resource existence check |
| Concise domain errors for reading, parsing and validation | Missing file, directory, simulated permission/general I/O, invalid UTF-8 and malformed TOML tests passed; messages identify positions/fields without private values or raw underlying errors |
| Supported example/schema documented; private files never created/overwritten | Example copied into a temporary test file and loaded successfully; missing-file and unchanged-input assertions passed; README/architecture document the API and policies |

| Local check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed; 17 packages resolved/checked with no dependency changes |
| `uv run --locked pytest tests/test_config.py -q --basetemp <fresh-directory>` | 170 passed |
| `uv run --locked pytest --basetemp <fresh-directory>` | 176 passed, including all 6 existing CLI/headless UI tests |
| `uv run --locked ruff check .` | Passed after fixing two new overlong lines |
| `uv run --locked ruff format --check .` | Passed |
| `uv run --locked ssh-workbench --help` | Passed; existing options retained, no configuration option added |
| `uv run --locked ssh-workbench --version` | Passed: `ssh-workbench 0.0.1` |
| `uv run --locked python -m ssh_workbench --version` | Passed with the same version |
| README loader command | Passed; fictional example returned one `Project` with both references |
| `uv build` | Passed; source archive and wheel built at 0.0.1 |
| `uv run --locked python scripts/check_package.py` | Passed; isolated installed wheel ran help/version and loaded a temporary fictional project outside the checkout |
| `git diff --check` | Passed |
| Documentation links and package contents | 21 relative links/anchors resolved; the built loader matched its source; wheel/source archive excluded `.local/`, `.serena/`, `.venv/` and Git metadata |

Final review reran the checks in a disposable export of the staged files, with
a fresh environment and no excluded workspace files. An initial pytest run
encountered a Windows permission error while cleaning its shared temporary
directory link after the test cases ran. Rerunning with fresh explicit
`--basetemp` directories passed as recorded above. No tests, permissions or
security settings were changed to address that environment-specific failure.

Initial independent source/documentation review found one URL-policy mismatch: C1
control characters were accepted despite the documented rule. The filter now
rejects them, with U+0081/U+009F regression cases for both optional references;
the test counts above include that correction. No other concrete review findings
were reported. Final diff review found no unrelated code edits or private data
introduced by this task; existing validation notes and the untracked tool
directory were preserved.

Tests use fictional data and temporary files; no real SSH files, hosts, remote
paths or vault data are read. Configuration strings remain inert. The installed
package check removes its temporary environment and fixture when finished.

CLI/UI startup code is unchanged. Jadon's manual confirmation below covers the
scaffold's appearance and exit shortcuts; the loader is verified separately by
the automated checks. Headless tests are not visual checks.

### Pre-merge follow-up: 2026-10-09

Review of `c6ea622` against merge base `6639e5c` found one low-impact error-contract
defect: a path containing a NUL character raised a raw `ValueError`. The loader
now wraps that failure in a sanitized `ProjectConfigError`. Regression coverage
checks the real invalid path and a portable simulated failure, frozen records,
unchanged invalid input, and suppression of invalid URLs in formatted tracebacks.
Alias/URL validation and the installed-wheel loader check needed no code changes.

Fresh local checks on Windows with Python 3.14.7 passed after these corrections:

| Check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed with no dependency changes |
| Ruff lint and formatting checks | Passed |
| Full pytest suite with a fresh unique `--basetemp` | 180 passed: 174 loader tests and 6 CLI/headless UI tests |
| CLI help, CLI version and module version | Passed; version remains 0.0.1 |
| `uv build` and `scripts/check_package.py` | Passed; installed wheel loaded the fictional configuration outside the checkout |

The earlier shared-temp cleanup error did not recur with a fresh `--basetemp`.
This does not establish the original cause; no permissions or tests were weakened.
A fresh tool-based interactive launch again failed with Windows "Access is
denied" before the application started. It supplies no new visual evidence and
does not invalidate Jadon's manual scaffold check.

For the original reviewed commit `c6ea622`, both Windows and Ubuntu passed in
[feature CI run 37977814920](https://github.com/jkosber/ssh-workbench/actions/runs/37977814920)
and [PR CI run 37977893973](https://github.com/jkosber/ssh-workbench/actions/runs/37977893973).
The PR run checked merge commit `47ede5b`, whose parents were the reviewed base
and head and whose tree matched the head. Job logs confirmed dependency sync,
lint, formatting, 176 tests, build and installed-package validation. These remote
results apply to that snapshot; the follow-up requires its own CI after pushing.

At this point the shared Serena project settings were committed for development;
they were removed on 2026-10-20. No private configuration is needed by the
application or tests.

## Bootstrap, 2026-10-09

The records below describe the initial 0.0.1 scaffold, before any product feature.

### Bootstrap environment

Local commands execute on a Windows 11 Home Insider Preview x64 workstation
(OS build 10.0.26340), using PowerShell 7.6.6. No remote machine is involved.
Project Python: 3.14.7. Declared minimum: >=3.14. Tools observed: Git
2.55.0.windows.5, GitHub CLI 2.98.0 and uv 0.12.24.

Resolved direct dependencies: Textual 8.2.8; development tools pytest 9.1.1,
pytest-asyncio 1.4.0 and Ruff 0.16.10. `uv.lock` records exact transitive versions.
The uv build backend requirement was generated by uv: >=0.12.24,<0.13.0.

### Bootstrap automated checks

| Check | Observed result |
| --- | --- |
| `uv sync --locked` | Passed; project environment matches the lockfile |
| CLI `--help`, `--version` | Passed; help exits successfully and version is `ssh-workbench 0.0.1` |
| `python -m ssh_workbench --version` through uv | Passed with the same installed version |
| `uv run --locked ruff check .` | Passed |
| `uv run --locked ruff format --check .` | Passed after formatting |
| `uv run --locked pytest` | 6 passed: help, metadata version, rejected unknown option, startup, Q exit and Ctrl+Q exit |
| `uv build` | Passed; source archive and wheel created; wheel built from the source archive |
| `uv run --locked python scripts/check_package.py` | Passed; wheel installed with locked runtime dependencies in a temporary environment; help/version worked outside the checkout |

An initial lint/format issue was corrected. A trial `uv build --locked` failed
because this uv version does not support that option for builds. All build
instructions and CI now use the verified `uv build` command. Dependency sync
and export remain locked. These results establish scaffold behavior, not product
feature completion.

Before the initial commit, all 24 staged files were reviewed. A targeted scan
found no credential tokens, private absolute paths or actual host/account details;
24 relative Markdown links resolved and the illustrative TOML parsed. The wheel
and source archive contained no `.local/`, `.venv/` or Git metadata. Git whitespace
checks passed. An independent source/documentation review found no blocking
issues. These checks reduce accidental disclosure risk but do not replace review
of future changes.

### Bootstrap manual verification and limits

On 2026-10-09, Jadon confirmed that the application's appearance, Q exit and
Ctrl+Q exit work in manual testing. This is user-confirmed verification of the
scaffold's appearance and exit shortcuts. Automated startup and keyboard exit
were also verified with Textual's headless pilot.

The earlier tool-based interactive launch was blocked when Windows returned
"Access is denied" while creating the terminal process. That tool-launch failure
was not an observed application exception; the manual check is now complete.

At bootstrap no real SSH feature existed, and no SSH configuration, keys, known_hosts,
infrastructure or vault data is used by tests. macOS and other Python versions
have not been tested.

CI is configured for `ubuntu-latest` and `windows-latest`, both using the version
in `.python-version`. After the initial push,
[CI run 37966249655](https://github.com/jkosber/ssh-workbench/actions/runs/37966249655)
passed on both targets for commit `6639e5c`, including dependency installation,
Ruff, tests, build and isolated package checks. This result applies to that commit;
check the repository's Actions tab for later changes. Action references were
verified through their official GitHub
release/tag APIs: actions/checkout v7.0.1 and astral-sh/setup-uv v10.2.0; full
commit references are recorded in the workflow. Permissions are `contents: read`.

### Bootstrap's planned manual SSH checklist

Superseded by the [Task 5 checklist](#task-5-user-executed-manual-session) and
its recorded real SSH and browser checks. Kept as the original plan. These checks
were **not performed** during bootstrap.

- Select a fictional/local fixture, then an approved real project; verify the
  shown alias and context match the intended target before connecting.
- Check existing native SSH authentication and normal host-key verification;
  never bypass an unexpected host-key warning.
- Connect and disconnect, cancel authentication, and interrupt a connection;
  verify terminal input, display and project selection recover correctly.
- Check unavailable SSH, an unknown alias and an unreachable approved target;
  confirm useful errors without credentials or sensitive output in logs.
- Exercise small terminal sizes and keyboard navigation. Open only an explicitly
  selected, approved documentation URL. Review screenshots/logs for private data.
- Have Jadon review usability and explain the tested behavior before treating it
  as personal learning or public portfolio evidence.
