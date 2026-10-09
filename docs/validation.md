# Validation

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

The shared Serena project settings are included for development. Cache files,
local overrides and memories remain ignored. No private configuration is needed
by the application or tests.

## Bootstrap environment: 2026-10-09

Local commands execute on a Windows 11 Home Insider Preview x64 workstation
(OS build 10.0.26340), using PowerShell 7.6.6. No remote machine is involved.
Project Python: 3.14.7. Declared minimum: >=3.14. Tools observed: Git
2.55.0.windows.5, GitHub CLI 2.98.0 and uv 0.12.24.

Resolved direct dependencies: Textual 8.2.8; development tools pytest 9.1.1,
pytest-asyncio 1.4.0 and Ruff 0.16.10. `uv.lock` records exact transitive versions.
The uv build backend requirement was generated by uv: >=0.12.24,<0.13.0.

## Automated checks

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

## Manual verification and limits

On 2026-10-09, Jadon confirmed that the application's appearance, Q exit and
Ctrl+Q exit work in manual testing. This is user-confirmed verification of the
scaffold's appearance and exit shortcuts. Automated startup and keyboard exit
were also verified with Textual's headless pilot.

The earlier tool-based interactive launch was blocked when Windows returned
"Access is denied" while creating the terminal process. That tool-launch failure
was not an observed application exception; the manual check is now complete.

No real SSH feature exists, and no SSH configuration, keys, known_hosts,
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

## Future approved manual SSH checklist

These checks are **not performed** during bootstrap. Obtain approval for the
specific hosts and connection actions first, and record date, platform and result.

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
