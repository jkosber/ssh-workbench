# Task 27: colors, glyphs and states. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every status one color role from one table, lowercase the state words, replace the spinner with block glyphs and drop the online pulse, and make the header name only what needs attention, in urgency order.

**Architecture:** `status.py` keeps the `State` enum as the single source of words and symbols. `app.py` gains one table, `STATE_COLORS`, from which a function generates the CSS for the list symbols and the details value, and which the header summary reads for its spans. The summary becomes a pure function of the counts and the width, so its fitting rules are unit-tested without a terminal.

**Tech Stack:** Python 3.14, Textual 8.2.8 (`Content.assemble` spans with `$variable` styles, `App.get_css_variables`, `textual.color.Color`), pytest with `App.run_test`.

**Spec:** `docs/superpowers/specs/2026-10-31-tui-overhaul-design.md`, sections "Header (Task 27)", "Colors and glyphs (Task 27)", "Decisions already made" and the Task 27 row.

## Global Constraints

- AGENTS.md binds: tests committed failing first, never a test change in an implementation commit, stage named files only, no AI attribution, Jadon's identity. Commits on `feat/task27-colors-and-states` are authorized; pushes, the pull request and the merge are asked separately.
- No new runtime dependency. No new control; `?` belongs to Task 28, not here.
- Every key and every result-line message keeps its wording. Only state words, the header summary and their tests change.
- Contrast: every text pair at 4.5:1 or better against its own background. Values in the plan are the floor; the builder may move hex values to pass.
- Glyphs: `●`, `○`, `◇`, `·`, `×`, and `▖▘▝▗` for the spinner. Never `◐◓◑◒`.
- Formatting: `uv run --locked ruff format .` after each code change; `uv run --locked ruff check .` and the full `uv run --locked pytest` before every commit.
- The repository is public: fictional data only, no private paths.

## Review Focus

1. A single machine: the header reads `1 machine · all online`, never `1 machines`. Pinned in Task 4's `test_header_names_only_what_needs_attention`.
2. The width at which the count and the first entry just fit: words at that width, symbols one column narrower. Pinned in Task 4's `test_summary_drops_entries_from_the_end`.
3. Mixed states with nothing urgent, online and checking only: the first colored word is `checking`. Pinned in Task 4's `test_summary_orders_states_by_urgency`.
4. The alias-not-found sentences after lowercasing: `× alias not found. Fix your SSH config and press R, ...` keeps its capital `Fix` and `Looks`. Pinned in Task 1 by the rewritten `OFFER` and `NO_OFFER` constants in `tests/test_renames_ui.py`.
5. Animations off (`TEXTUAL_ANIMATIONS=none`): a checking machine shows `▖`, the same glyph as `State.CHECKING.symbol`. Pinned in Task 2's `test_spinner_moves_only_when_animations_are_on`.

---

### Task 1: Lowercase state words and the new spinner glyphs

**Files:**
- Modify: `src/ssh_workbench/status.py:31-39` (the `State` enum)
- Modify: `src/ssh_workbench/app.py:99` (`SPINNER`)
- Test: `tests/test_status.py`, `tests/test_status_ui.py`, `tests/test_renames_ui.py`, `tests/test_look.py`

**Interfaces:**
- Produces: `State.word` values `"checking"`, `"online"`, `"offline"`, `"can't check"`, `"not checked"`, `"alias not found"`; `State.CHECKING.symbol == "▖"`; `SPINNER == "▖▘▝▗"`.

- [ ] **Step 1: Rewrite the tests that pin the words and symbols**

In `tests/test_status.py` change `test_state_words_and_symbols_are_all_different` to expect the lowercase list above, and `test_alias_not_found_has_its_own_word_and_symbol` to `("alias not found", "×")`. In `tests/test_status_ui.py` replace every expected status string: `"▖ checking"`, `"● online via alias"`, `"● online: 192.0.2.40"`, `"○ offline"`, `"◇ can't check: the alias uses ProxyJump or ProxyCommand"`, `"◇ can't check: the check failed"`, `"· not checked"`, `"◇ can't check: press R to resolve this alias"`, `"◇ can't check: the check could not start"`, and in `test_spinner_moves_only_when_animations_are_on` the set `{"▖", "▘", "▝", "▗"}`. In `tests/test_renames_ui.py` rewrite `OFFER`, `NO_OFFER` and the `"● online via alias"` assertions. Grep for any other `Online`, `Offline`, `Can't check`, `Not checked`, `Alias not found`, `Checking` and `◐` in `tests/` and rewrite each.

- [ ] **Step 2: Run the suite to see exactly these tests fail**

Run: `uv run --locked pytest -q`
Expected: failures only in the rewritten tests, each on a string comparison; no errors.

- [ ] **Step 3: Commit the tests**

```bash
git add tests/test_status.py tests/test_status_ui.py tests/test_renames_ui.py
git commit -m "test: state words are lowercase and the spinner uses block glyphs"
```

- [ ] **Step 4: Change `State` and `SPINNER`**

In `status.py` the enum values become `("checking", "▖")`, `("online", "●")`, `("offline", "○")`, `("can't check", "◇")`, `("not checked", "·")`, `("alias not found", "×")`. In `app.py`, `SPINNER = "▖▘▝▗"`. Update the enum docstring to say shape carries meaning and the spinner's still frame is the checking symbol.

- [ ] **Step 5: Run the suite**

Run: `uv run --locked pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/ssh_workbench/status.py src/ssh_workbench/app.py
git commit -m "feat: lowercase state words and a block-glyph spinner"
```

---

### Task 2: Static glyphs, the online pulse removed

**Files:**
- Modify: `src/ssh_workbench/app.py:174-224` (`StatusSymbol`), `app.py:1161-1169` (`_tick_animation`)
- Test: `tests/test_status_ui.py:336-360`

- [ ] **Step 1: Replace the pulse tests**

Delete `test_online_symbols_dim_for_half_of_each_pulse`. Add:

```python
async def test_online_symbols_never_change_with_the_frame() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test() as pilot:
        await checked(app, pilot)
        widget = app.query(StatusSymbol).first()
        assert widget.state is State.ONLINE
        for frame in range(8):
            widget.frame = frame
            assert not widget.has_class("-dim")
            assert widget.render().plain == "●"
```

Rename `test_the_animation_moves_only_checking_and_online_symbols` to `test_the_animation_moves_only_checking_symbols` and make it assert that after several `app._tick_animation()` calls only the `State.CHECKING` widget's `frame` changed and every other widget's `frame` is still `0`.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run --locked pytest tests/test_status_ui.py -q -k "frame or animation"`
Expected: the new test fails on `has_class("-dim")`; the renamed one fails because online widgets' frames change.

- [ ] **Step 3: Commit the tests**

```bash
git add tests/test_status_ui.py
git commit -m "test: only the checking symbol moves"
```

- [ ] **Step 4: Remove the pulse**

In `StatusSymbol`: delete the `.state-online.-dim` CSS rule and the whole `watch_frame` method; `frame` stays a reactive, which is what redraws the spinner. In `_tick_animation`, assign `symbol.frame` only when `symbol.state is State.CHECKING`.

- [ ] **Step 5: Run the suite**

Run: `uv run --locked pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/ssh_workbench/app.py
git commit -m "feat: status glyphs stay still except the checking spinner"
```

---

### Task 3: One table for state colors, and the contrast guard

**Files:**
- Modify: `src/ssh_workbench/app.py:103-137` (theme and `SUMMARY_STYLES`), `app.py:178-200` (`StatusSymbol.DEFAULT_CSS`), `app.py:388-460` (`#machine-status` rules in `CSS`)
- Test: `tests/test_look.py`

**Interfaces:**
- Produces: `STATE_COLORS: dict[State, tuple[str, str]]` in `app.py`, state to `(symbol_color, word_color)` as CSS variable names with `$`:

| State | symbol | word |
| --- | --- | --- |
| `ONLINE` | `$success` | `$text-success` |
| `OFFLINE` | `$text-muted` | `$text-muted` |
| `CHECKING` | `$secondary` | `$text-secondary` |
| `UNKNOWN` | `$warning` | `$text-warning` |
| `NOT_CHECKED` | `$text-muted` | `$text-muted` |
| `NOT_FOUND` | `$error` | `$text-error` |

- Produces: `state_css() -> str`, the rules `StatusSymbol.state-<name> { color: <symbol>; }` and `#machine-status.state-<name> { color: <word>; }` for every state, prepended to `SSHWorkbenchApp.CSS`. `SUMMARY_STYLES` is removed.
- Produces: `contrast(foreground: Color, background: Color) -> float` in `tests/test_look.py` (WCAG 2 relative luminance; a translucent foreground is composited with `background.tint(foreground)` first).

- [ ] **Step 1: Write the tests**

```python
def test_every_state_has_one_color_role() -> None:
    assert set(STATE_COLORS) == set(State)
    assert STATE_COLORS[State.OFFLINE] == ("$text-muted", "$text-muted")
    assert STATE_COLORS[State.CHECKING] == ("$secondary", "$text-secondary")
    assert len({symbol for symbol, _ in STATE_COLORS.values()} - {"$text-muted"}) == 4
    assert SSHWorkbenchApp.CSS.startswith(state_css())
    assert rule("StatusSymbol.state-not_found") == "color: $error;"
    assert rule("#machine-status.state-online") == "color: $text-success;"
    assert rule("#machine-status.state-offline") == "color: $text-muted;"


def rule(selector: str) -> str:
    """The single declaration of one generated rule, whitespace collapsed."""
    body = state_css().split(f"{selector} {{", 1)[1].split("}", 1)[0]
    return " ".join(body.split())


async def test_the_details_status_takes_the_table_color() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        await checked(app, pilot)
        variables = app.get_css_variables()
        status = app.query_one("#machine-status", Static)
        await wait_for(pilot, lambda: status.has_class("state-online"))
        assert status.styles.color == Color.parse(variables["text-success"])
        symbol = app.query(StatusSymbol).first()
        assert symbol.styles.color == Color.parse(variables["success"])
        app.query_one(ListView).index = 2
        await wait_for(pilot, lambda: status.has_class("state-offline"))
        assert status.styles.color == Color.parse(variables["text-muted"])


async def test_text_colors_reach_four_and_a_half_to_one() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(80, 24)):
        variables = app.get_css_variables()
        foregrounds = (
            {"foreground", "text-muted"}
            | {word.lstrip("$") for _, word in STATE_COLORS.values()}
            | {symbol.lstrip("$") for symbol, _ in STATE_COLORS.values()}
        )
        for name in foregrounds:
            for surface in ("background", "surface", "panel"):
                ratio = contrast(
                    Color.parse(variables[name]), Color.parse(variables[surface])
                )
                assert ratio >= 4.5, (name, surface, ratio)
```

`contrast` lives in the test module. `Color.parse` handles `rgba(...)` strings; composite with `tint` when `foreground.a < 1`.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run --locked pytest tests/test_look.py -q -k "color or contrast"`
Expected: `ImportError` for `STATE_COLORS` and `state_css`.

- [ ] **Step 3: Commit the tests**

```bash
git add tests/test_look.py
git commit -m "test: one table gives every state its color, and text contrast is guarded"
```

- [ ] **Step 4: Build the table and generate the CSS**

Add `STATE_COLORS` and `state_css()` to `app.py` above `StatusSymbol`. Remove the color rules from `StatusSymbol.DEFAULT_CSS` (keep `width` and `height`) and the `#machine-status.state-*` rules from `CSS`; set `CSS = state_css() + """..."""`. Delete `SUMMARY_STYLES`; Task 4 replaces its only use. If any pair in the contrast test falls short, adjust that theme value in `WORKBENCH_THEME` and keep `primary` `#4FC1E9` and `background` `#10141B`, which `test_the_workbench_theme_is_active` pins.

- [ ] **Step 5: Run the suite**

Run: `uv run --locked pytest -q`
Expected: all pass. Ruff: `uv run --locked ruff check . && uv run --locked ruff format --check .`.

- [ ] **Step 6: Commit**

```bash
git add src/ssh_workbench/app.py
git commit -m "feat: one table colors every state in the list and the details"
```

---

### Task 4: The header names only what needs attention

**Files:**
- Modify: `src/ssh_workbench/app.py:785-822` (`_summary`)
- Test: `tests/test_look.py`

**Interfaces:**
- Consumes: `STATE_COLORS` from Task 3.
- Produces: `SUMMARY_ORDER = (State.NOT_FOUND, State.UNKNOWN, State.OFFLINE, State.CHECKING, State.ONLINE)` in `app.py`; `_summary(self, width: int) -> Content` keeps its signature and these rules:
  - Count: `N machine` or `N machines`.
  - All machines `ONLINE`: `N machines · all online`, the phrase in `$text-muted`.
  - All machines `NOT_CHECKED` (no checker): `N machines · not checked`, muted.
  - Otherwise, entries for every nonzero state in `SUMMARY_ORDER`, `NOT_CHECKED` left out, joined by ` · `, each `<symbol> <n> <word>`. Each entry is exactly two styled spans: the symbol in its symbol color, then `"<n> <word>"` as one span in the word color for the first entry and `$text-muted` for later ones. The count and the separators are unstyled, so `content.spans` lists the entries' styles in order.
  - Fit: `width - len(self.title) - 4` is the room. Drop entries from the end until the words fit. If the count plus the first entry does not fit, return the symbol form `N · ×1 ◇2 ○3`, every symbol in its symbol color, as today.
  - No machines: empty `Content`.

- [ ] **Step 1: Rewrite the header constants and tests**

In `tests/test_look.py` set `LONG_SUMMARY = "4 machines · ◇ 1 can't check · ○ 1 offline · ● 2 online"`, `TRIMMED_SUMMARY = "4 machines · ◇ 1 can't check · ○ 1 offline"` and `SHORT_SUMMARY = "4 · ◇1 ○1 ●2"`. Parametrize `test_header_counts_machines_by_status` with `((120, 40), LONG_SUMMARY)`, `((80, 24), LONG_SUMMARY)`, `((60, 20), TRIMMED_SUMMARY)`, `((40, 16), SHORT_SUMMARY)`. In `test_header_follows_the_terminal_width` resize to `(40, 16)` for the short form. In `test_header_without_status_checks_counts_machines` expect `"2 machines · not checked"` and `"1 machine · not checked"`; in `test_header_follows_a_delete` expect `"2 machines · not checked"` then `"1 machine · not checked"` then `""`. Add:

```python
def status_of(state: State) -> MachineStatus:
    return MachineStatus(state)


async def test_summary_orders_states_by_urgency() -> None:
    app = SSHWorkbenchApp(MACHINES)
    async with app.run_test(size=(200, 24)):
        app._statuses = {
            "garden": status_of(State.ONLINE),
            "studio": status_of(State.CHECKING),
            "lab": status_of(State.NOT_FOUND),
            "hop": status_of(State.OFFLINE),
        }
        content = app._summary(200)
        assert (
            str(content)
            == "4 machines · × 1 alias not found · ○ 1 offline · ▖ 1 checking · ● 1 online"
        )
        styles = [span.style for span in content.spans]
        assert styles[:2] == ["$error", "$text-error"]
        assert "$text-muted" in styles and "$text-success" not in styles
        app._statuses["lab"] = status_of(State.ONLINE)
        app._statuses["hop"] = status_of(State.ONLINE)
        assert str(app._summary(200)) == "4 machines · ▖ 1 checking · ● 3 online"
        assert [span.style for span in app._summary(200).spans][:2] == [
            "$secondary",
            "$text-secondary",
        ]


async def test_header_names_only_what_needs_attention() -> None:
    app = SSHWorkbenchApp(MACHINES[:1], checker=FakeChecker())
    async with app.run_test(size=(80, 24)) as pilot:
        await checked(app, pilot)
        await wait_for(pilot, lambda: summary(app) == "1 machine · all online")
        content = app.query_one("#app-summary", Static).content
        assert [span.style for span in content.spans] == ["$text-muted"]


async def test_summary_drops_entries_from_the_end() -> None:
    app = SSHWorkbenchApp(MACHINES, checker=FakeChecker())
    async with app.run_test(size=(120, 40)) as pilot:
        await checked(app, pilot)
        room = len(app.title) + 4
        assert str(app._summary(len(LONG_SUMMARY) + room)) == LONG_SUMMARY
        assert str(app._summary(len(LONG_SUMMARY) + room - 1)) == TRIMMED_SUMMARY
        first = "4 machines · ◇ 1 can't check"
        assert str(app._summary(len(first) + room)) == first
        assert str(app._summary(len(first) + room - 1)) == SHORT_SUMMARY
```

`MachineStatus` is imported from `ssh_workbench.status`; check its constructor's positional order there before writing `status_of`.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run --locked pytest tests/test_look.py -q -k "summary or header"`
Expected: the parametrized cases fail on the old `   `-separated text; the new tests fail on text or on `SUMMARY_ORDER` missing.

- [ ] **Step 3: Commit the tests**

```bash
git add tests/test_look.py
git commit -m "test: the header names nonzero states in urgency order and trims from the end"
```

- [ ] **Step 4: Rewrite `_summary`**

Implement the rules in the Interfaces block. Build the entries as a list of `Content` pieces per entry so dropping from the end is a slice, then `Content.assemble` with `" · "` between. The symbol form reuses today's loop over the same ordered entries.

- [ ] **Step 5: Run the suite**

Run: `uv run --locked pytest -q`
Expected: all pass, including `test_header_follows_the_terminal_width`.

- [ ] **Step 6: Commit**

```bash
git add src/ssh_workbench/app.py
git commit -m "feat: the header names only what needs attention, in urgency order"
```

---

### Task 5: Docs, roadmap and changelog

**Files:**
- Modify: `docs/guide.md:212-224` (the Status table), `docs/architecture.md:148-152` (Theme, Header rows), `docs/architecture.md:308-313` (the `StatusSymbol` paragraph), `docs/roadmap.md` (Now, the Interface backlog, Done), `CHANGELOG.md` (Unreleased)

- [ ] **Step 1: Guide**

Rewrite the Status table: `▖` (turning) checking, `●` online, `○` offline (grey), `◇` can't check, `×` alias not found, `·` not checked. Replace "the header counts each status except Not checked" with: the header names the nonzero states in urgency order, alias not found first, and says `all online` when nothing needs attention or `not checked` when checks are off; when the words do not fit, the entries drop from the end, then shrink to symbols. Lowercase the state words wherever the guide quotes them as screen text; keep headings and prose capitalization.

- [ ] **Step 2: Architecture**

Theme row: status colors come from one table, `STATE_COLORS`, whose `state_css()` output opens the app's CSS; symbols use the base colors and the details word the `$text-*` variants. Header row: the urgency order, the trim rule and the symbol fallback. `StatusSymbol` paragraph: the timer turns only the checking spinner (`▖▘▝▗`); nothing else moves.

- [ ] **Step 3: Roadmap**

Under Now add `### 27. Colors, glyphs and states` with the date, a link to the design document, and checkboxes for: one color table; offline and not checked muted, checking blue; lowercase state words; block spinner and no pulse; the urgency-ordered header with its trim rule; the contrast guard; docs, changelog, validation entry; a fresh review. Remove the Interface backlog row "Status colors are defined in three places". Add three backlog rows with From `27`: a theme in the terminal's 16 ANSI colors; two-row list entries; toast notifications for results.

- [ ] **Step 4: Changelog**

Under Unreleased, a `### Changed` section: the header names only the states that need attention, worst first, and says "all online" when none do; offline machines show a grey ring and only a missing alias is red; checking machines show a turning block glyph that common terminal fonts have, and online dots no longer pulse; status words are lowercase.

- [ ] **Step 5: Check and commit**

Run: `uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv build && uv run --locked python scripts/check_package.py`
Expected: all pass; the package check ends with `passed.`

```bash
git add docs/guide.md docs/architecture.md docs/roadmap.md CHANGELOG.md
git commit -m "docs: Task 27 colors, glyphs and the attention-ordered header"
```

---

### Task 6: Manual check and validation entry (orchestrator)

**Files:**
- Modify: `docs/validation.md` (a new section under the how-to block)

- [ ] **Step 1: Headless captures**

Adapt the throwaway capture script in `.local/ux-overhaul/current-0.3.4/capture.py` on the branch to render `80x24-main`, `120x30-main`, `40x16-main` and `80x24-main-not-checked` into `.local/ux-overhaul/task27/`. Open each PNG and compare with the design's header and color rules.

- [ ] **Step 2: Ghostty run**

In Ghostty on the Linux development machine, with `APPDATA`, `XDG_CONFIG_HOME` and `SSH_WORKBENCH_SSH_DIR` pointed at empty folders under `.local/`, run `uv run --locked ssh-workbench --config examples/machines.example.toml` at 80x24 and 120x30. Observe: the spinner turns through the four block glyphs and renders in JetBrains Mono; the header reads the trimmed or full form; Q returns to an echoing prompt. Keep screenshots under `.local/`.

- [ ] **Step 3: Validation entry**

Add `## Task 27: colors, glyphs and states, 2026-MM-DD` with the environment line, a table of each check and what was observed, and `Not checked:` naming Windows Terminal (deferred to the single check after Task 30 per the design) and a physical low-color terminal.

```bash
git add docs/validation.md
git commit -m "docs: Task 27 validation in Ghostty"
```
