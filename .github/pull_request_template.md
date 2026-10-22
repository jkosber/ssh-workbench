## Purpose

Which roadmap task this is, and what changes for the user.

## Acceptance

The task's acceptance criteria from the roadmap, ticked. This copy is their
record once the task leaves the roadmap.

## Checks

- [ ] `ruff check`, `ruff format --check`, `pytest`, `uv build` and `check_package.py` pass
- [ ] Manual terminal checks, if the screen, terminal handoff or SSH changed (recorded in `docs/validation.md`)

What remains untested:

## Docs

- [ ] User guide or README, if behavior changed
- [ ] Changelog line under Unreleased, if a user would notice
- [ ] Roadmap row moved to Done
- [ ] No private hosts, aliases, addresses, paths or credentials in code, fixtures or evidence
