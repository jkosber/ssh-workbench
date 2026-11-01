# TUI overhaul: look, content and responsive layout

Design for Tasks 27 to 30. Written 2026-10-31 from a review of the 0.3.4
screens at nine terminal sizes, a study of herdr's terminal interface, and
research into terminal UI practice (Textual's design guide, lazygit, k9s,
Charm's guidelines, WCAG contrast rules). The recon evidence lives in the
ignored `.local/ux-overhaul/` folder; nothing in it is needed to build from
this document.

## Intent

SSH Workbench shows a machine list beside the selected machine's details, with
a header, status lines and a key footer. The screens work, but they spend
rows and columns on chrome, break content badly at common sizes, fail
contrast where it matters, and style key hints three different ways. The
overhaul makes the interface quiet, dense and consistent: chrome recedes,
content gets the space, every color has one role, and the layout holds at
every size people actually run.

The inspiration is herdr's terminal UI. What transfers is its discipline, not
its palette: one accent hue only for focus and actions, state color only on
the glyph and the status word, three text levels, a selection band instead of
borders, dim dividers and lowercase section labels instead of boxed panes,
key hints in one style everywhere, and a summary that names only what needs
attention.

## Findings the design answers

| Finding | Evidence (0.3.4) |
| --- | --- |
| 9 of 24 rows are chrome at 80x24; the link line reserves 3 rows for 1 line | header 1, pane borders 2, help 1, connection 1, link 3, footer 1 |
| Above 120 columns the list pane is half empty and the footer hugs the left | 160x50, 200x60 captures |
| The unfocused border is 1.5:1 against the background; the unfocused selection 1.2:1 | the selected machine cannot be found while the details have focus |
| Checking and Can't check are two near-identical ambers | `$accent` #F2B25C and `$warning` #E5C07B |
| URLs wrap mid-word; a link renders as `Name:` alone on a line when the URL does not fit | 60x20, 80x24 captures |
| Row targets appear only from 110 columns, which no 1080p half screen reaches | 1080p half screens are 83 to 104 columns |
| Key hints come in three styles: footer `c Connect`, lines `C: connect`, modals `Y: delete   N or Escape: keep` | every screen |
| The add form spends 6 rows per field; 80x24 shows two fields | 80x24 add capture |
| The spinner glyphs `◐◓◑◒` are missing from JetBrains Mono Nerd Font | font tables |
| Bold alone marks the selected name, labels and border titles; Windows Terminal renders bold as bright by default and leaves RGB colors unchanged | Windows Terminal defaults |

## Goals, non-goals, anti-goals

| Kind | Items |
| --- | --- |
| Goals | Content first: at 80x24 the bottom chrome is 2 rows, not 6. One hint style everywhere. Every color has one role; every text pair reaches 4.5:1 and every band, marker and divider 3:1. Nothing depends on a special font. The layout holds at the size matrix below, headless and in a real terminal |
| Non-goals | No new features: no tmux, discovery, file transfer, embedded terminals, sorting, filtering or mouse-first controls. No change to what Workbench reads, writes, launches or checks. No new runtime dependency. No change to the machine file |
| Anti-goals | A screen that looks busier than today. A layout that needs more than 60x20 to be usable. Meaning carried by color or bold alone. Glyphs from private-use font areas. A second UI library |

## Decisions already made

| Decision | Choice | Why |
| --- | --- | --- |
| Palette | Workbench keeps its own colors; a theme in the terminal's 16 ANSI colors is a backlog row | A second theme needs a new flag or setting |
| Offline color | A muted grey ring; red only for an alias not found | For a homelab, offline is often expected; red should mean something to fix |
| Labels | Lowercase, muted: `machines`, `links`, `status` | Quiet labels let values stand out |
| State words | Lowercase on screen: `online`, `can't check`, `alias not found` | Matches the labels; the header and the details read as one voice |
| Results | One persistent result line, 1 row idle, up to 3 when a message wraps | Survives a terminal handoff; toasts expire |
| List rows | One row per machine; a muted right-aligned target from 100 columns; aligned columns with a header from 130 | Keeps every machine visible; two-row entries are a backlog row |
| Key help | The help line goes; `?` opens Textual's key panel | Saves a row; the panel lists every key with its description |
| Motion | Static glyphs; the online pulse goes; Checking keeps a spinner drawn with block glyphs | The screen changes only when state changes |
| Work split | Four tasks, each its own branch, review and pull request: 27 colors, glyphs and states; 28 main-screen layout and breakpoints; 29 list and details content; 30 forms and pickers | Each reviewable on its own |
| Widgets | `ListView` stays; `DataTable` has no `fr` columns or ellipsis | Flexible widths matter more than a built-in header |
| Keys | Every key stays; `?` is the only new key | Behavioral contracts |
| Strings that stay | The result-line messages (connect, save, delete, update, Include and link results), validation messages and the empty screens' paths keep their wording | Tests and the guide quote them; a terminal handoff may show them outside the app |
| Strings that change | Labels, state words, header summaries, footer labels, `Not set`, `Press A to add one.`, modal hint sentences and the bottom lines' IDs. The tests that assert them are rewritten in the task's failing-tests commit, never in an implementation commit | The workflow allows test changes only in a test commit that precedes the code |
| Resolved targets | Not shown. The architecture keeps what `ssh -G` resolves off the screen; an alias machine's `connect` row shows the alias with today's `_target_text` wording, `(not in your SSH config)` included | A documented decision this overhaul does not reverse |

## The screen

Sketch at 80x24, Studio box selected, list focused. `▌` is the selection
marker; the band also fills the row's background. Values are fictional.

```text
 SSH Workbench       10 · × 1 alias not found · ◇ 2 can't check · ○ 3 offline
 machines               2/10 │ Studio box                           studio-box
─────────────────────────────┼──────────────────────────────────────────────────
  ● Garden demo              │ status      ● online · 192.0.2.40
▌ ● Studio box               │ connect     direct · studio@192.0.2.40:2222
  ○ Build runner for the ni… │ key         ~/.ssh/id_ed25519_studio_box
  ◇ Hop gateway              │ addresses   studio-box.example.com
  × Archive NAS              │             192.0.2.40
  ▖ Edge cluster             │
  ○ Media server             │ links
  ◇ Lab Pi                   │   Dashboard    https://192.0.2.40:8006
  ● Backup box               │   Status page  https://studio-box.example.com
  ○ Office printer           │                /status
                             │   Grafana      https://grafana.example.com/d/
                             │                fictional-studio-overview
                             │                ?orgId=1&refresh=30s
                             │
                             │
                             │
                             │
                             │
                             │
 ● connected to Studio box · session ended
 c connect  o link  a add  e edit  x delete  k key  r check  ? keys  q quit
```

### Header (Task 27)

| Part | Rule |
| --- | --- |
| Title | The filled title block stays, as today |
| Summary | The machine count, then the nonzero states in urgency order: alias not found, can't check, offline, checking, online. Each entry is its symbol and `N word`. The first entry's word takes its state color; later words are muted; every symbol keeps its state color |
| Nothing wrong | `10 machines · all online` muted. Without status checks: `10 machines · not checked` |
| Fit | Entries drop from the end until the line fits. When the count and the first entry do not fit, the symbol form `10 · ×1 ◇2 ○3` is used, as today's fallback |
| Width | The summary never wraps and never pushes the title |

### Panes and dividers (Task 28)

| Part | Rule |
| --- | --- |
| Borders | None on the main screen. A dim vertical divider separates the list and the details; a dim rule sits under the label row. How the divider is drawn (a `Rule`, a keyline or a border side) is the builder's call |
| Label row | Left: ` machines` and the position `2/10` right-aligned in the list's width. Right: the machine name, bold and in the foreground color, with the ID muted at the right edge |
| Focus | The rule under the focused pane's label row is heavy (`━`) in the accent; under the unfocused pane it is thin and dim. The focused pane's label text is in the accent too, except the details label, which stays the machine name in the foreground color. The list's selection band is brighter when the list has focus and dimmer when it does not; the marker stays either way |
| Widths | The list takes about two fifths of the width with a floor of 24 columns and a cap near 56, raised to 80 at `-xwide`; the details take the rest. The list never exceeds half the screen |
| Scrollbars | One column wide, thumb muted, track in the surface color. The details keep a stable gutter |
| Stacked | Under 60 columns the list sits above the details, takes `height: auto` up to 40% of the screen, and the rule between them doubles as the details label row |

### List rows (Task 29)

| Part | Rule |
| --- | --- |
| Row | Column 0 holds the selection marker `▌` in the accent on the highlighted row, in every focus state. Then the state symbol in its state color, a space, the name in the foreground color with ellipsis |
| Target | From 100 columns: the alias, or the address the last check found online else the first, muted and right-aligned, at most half the row |
| Columns | From 130 columns: a muted lowercase header row above the list, outside the scroll: `name`, `target`, `user`. The user column shows the user of a direct machine and stays blank for an alias |
| Selection | A full-width band and the marker. The marker is the non-color cue and must reach 3:1 against the surface. The bands need no ratio against the surface, only to be visibly distinct from it and from each other (the focused one brighter), because text on them has to stay readable: the name, the target and every state symbol keep their colors on the selected row and must reach 4.5:1 against the band, which keeps the bands dark |

### Details (Task 29)

Rows have a lowercase muted label of 11 columns and a value. A row whose value
is unset is left out rather than printing `Not set`.

| Row | Direct machine | Alias machine |
| --- | --- | --- |
| `status` | `● online · 192.0.2.40`, the word in its state color, the address muted; other states as their word plus any detail the state carries today | same |
| `connect` | `direct · user@address:port`: user and `:port` only when set, the address the last check found online else the first; `· exported as ssh <id>` when exported | `alias · ` followed by today's `_target_text`, so a missing alias reads `alias · name (not in your SSH config)` with the note in the error color. What `ssh -G` resolves is never shown |
| `key` | The key path, only when set | The key path, only when set |
| `addresses` | One per line | not shown |
| `links` | A blank row, the `links` label alone, then each link as a name column (auto width, capped at 20) and the URL. A URL wraps at the URL column, never into the name column. `links  none` muted when there are none | same |

Under 48 columns of pane width every label stacks above its value, and each
link becomes a name line with its URL on the next line, indented two.

### Bottom rows (Task 28)

| Part | Rule |
| --- | --- |
| Result line | One widget replaces the help, connection and link lines. It holds two slots, the last connection result and the last link result, so a link result that arrives during an SSH session never erases the session's exit status. Blank until something happens. When one slot is set it shows that message; when both are set, the newer one first and the older on the next row. Each message starts with a glyph: `●` success, `×` failure, `›` an opened link, `·` anything else, such as a pending browser request or the U warning. Message texts stay what they are today. Height 1 idle, `auto` up to 3, the overflow cut with an ellipsis |
| Footer | Textual's compact footer: key in the accent, label muted, one space inside a pair, two between pairs. Labels lowercase. `?` with label `keys` opens the key panel; the panel must list Up/Down, Tab and PgUp/PgDn with descriptions, however the builder achieves that. The nine keys need 74 columns on one row, so the footer takes two rows under 80 columns and three under 45, with columns sized to their content rather than equal; every key stays visible down to 40 columns |
| Short | Under 24 rows: the result line is capped at 2 |

### Modals (Task 30)

| Part | Rule |
| --- | --- |
| Backdrop | The base screen dims to near-solid so fragments of it do not compete with the modal |
| Frame | One round border in the accent (error color for the delete question), title in the border, surface background, width to content within a cap, height `auto` within 90% |
| Hint row | Every modal ends with one row in the footer style: ` ↵ open  esc cancel `, ` y delete  n keep `, ` ^s save  esc cancel `. No `Key: action` sentences |
| Form fields | Label and a one-row input on the same row from 60 columns (label column 12), stacked when narrower. The ID, user and port inputs are about 32 columns; name, alias, addresses and key fill the row. The error row exists only while an error is shown. The focused input has a cue that is not color alone (a `▌` marker or an underline is the builder's call). The links `TextArea` keeps 5 rows |
| Buttons | One row each, named with their key: ` ^s save ` in the accent fill, ` esc cancel ` plain, side by side |
| Radio buttons | The unselected ring is visible: muted, not black |
| Link picker | No border on the `OptionList`. Each option is two lines: the name, then the URL muted and indented two, so long URLs never break the column |
| Key picker | One blank row above each section label; the `Not listed` and note rows keep their colors; hint row as above |
| Questions | The delete and Include questions size to their text with a blank row before the hint row |

### Colors and glyphs (Task 27)

| Role | Use |
| --- | --- |
| Accent (`$primary`) | Focus: the focused pane label, the selection marker and band, footer keys, modal borders, the title block, the save button |
| `$secondary` | Checking |
| `$success` | Online |
| `$warning` | Can't check |
| `$error` | Alias not found, failures in the result line, the delete question |
| `$text-muted` | Offline, Not checked, labels, targets, secondary values, inactive footer labels |
| Structural | Dividers and rules at 3:1 or better against the background |

Status words use the `$text-*` variants; symbols use the base colors. The
exact hex values are the builder's call within these constraints: every text
pair at 4.5:1 or better against its own background, the selection bands
included; the selection marker, dividers and rules at 3:1 or better against
the surface; the two bands visibly distinct from the surface and from each
other; offline and not-checked distinguishable by shape; and no two states
sharing a hue.

| State | Symbol |
| --- | --- |
| online | `●` |
| offline | `○` |
| can't check | `◇` |
| not checked | `·` |
| alias not found | `×` |
| checking | `▖▘▝▗` as the spinner, `▖` when still |

All of these are in Cascadia Mono, Adwaita Mono, JetBrains Mono and Noto
Sans Mono; `◇` and the block quarters are missing from Liberation Mono only.
Bold may decorate but never carries meaning on its own.

### Breakpoints (Task 28)

| Class | Range | Layout |
| --- | --- | --- |
| `-narrow` | under 60 columns | Stacked panes, symbol-form header, stacked detail labels |
| `-normal` | 60 to 99 | Side by side; rows show symbol and name; the footer takes two rows under 80 columns |
| `-wide` | 100 to 129 | Adds the row target |
| `-xwide` | 130 and up | Adds the column header and the user column |
| `-short` | under 24 rows | Result line capped at 2 |
| `-tall` | 24 rows and up | Everything |

### Empty states (Task 28)

One short muted line, lowercase, with the key styled like a footer key:
` no machines in this file yet · a to add`, followed by the file path on its
own line. The no-file screens keep their path and `--config` sentence in the
same style. Paths stay literal.

## Size matrix

Headless tests and the manual check cover these sizes. The first four are
the sizes that occur most: GNOME Terminal, macOS Terminal and tmux defaults,
Windows Terminal's default, and 1080p half and full screens.

| Size | Must hold |
| --- | --- |
| 80x24 | Every footer key visible; the example machine's details fit without scrolling; the bottom chrome is 2 rows |
| 120x30 | Row targets shown; details rows end well before the pane edge; no wasted header |
| 100x30, 120x40 | Row targets shown |
| 160x50, 200x60 | Column header and user column; the list is at most half the width; no empty bands |
| 60x20 | Side by side, every key visible on a two-row footer, details scroll but never clip a row |
| 50x24 | Stacked; the list shows at least 3 machines; the footer takes 2 rows |
| 40x16 | Every key visible on a three-row footer; nothing overlaps. Content may scroll |
| 80x50 | The list does not stretch its rows; the details start at the top |
| 120x18 | `-short`; the result line is at most 2 rows; nothing overlaps |

Every modal fits at 60x20 and 80x24 with its hint row visible.

## Tasks

| Task | Branch | Delivers | Acceptance |
| --- | --- | --- | --- |
| 27 | `feat/task27-colors-and-states` | Color roles, contrast, offline grey, Checking blue, static glyphs, the block spinner, lowercase state words, the urgency-ordered header, one set of `.state-*` rules | Contrast ratios asserted in a test from the theme values; the header's order and fallback tested at 60, 80 and 160 columns; the pulse and its tests removed; the backlog row about status colors in three places closed |
| 28 | `feat/task28-layout-and-breakpoints` | Borders to dividers and label rows, pane widths, scrollbars, the result line, the help line's removal, `?` and the key panel, footer rhythm, the new breakpoints, stacked and short rules, empty states, a capture script | Geometry tests at every size in the matrix; the key panel lists the navigation keys; `scripts/capture_look.py` renders the matrix headless from fictional machines into `.local/` |
| 29 | `feat/task29-list-and-details` | Row marker, selection bands, targets from 100 columns, columns from 130, position counter, the details rows and links block, narrow stacking | Tests for each row form, unset rows omitted, URL wrapping at the URL column, the counter following selection and deletes |
| 30 | `feat/task30-forms-and-pickers` | Backdrop, hint rows, one-row fields, sized inputs, error rows on demand, named buttons, visible radio rings, two-line link options, key picker spacing, sized questions | Each modal fits at 60x20 and 80x24 with its hint row visible; form tests keep every validation and save behavior |

Order: 27, 28, 29, 30. Each task follows the workflow guide: tests committed
failing first, the implementation in its own commits, docs and the changelog
in the same pull request, a manual check in Ghostty with captures in
`.local/`, and a validation entry. A single Windows Terminal look check after
Task 30 is recommended for bold and glyph rendering, since the bold rule
comes from Windows Terminal's defaults and was not observed; whether to run
it is Jadon's call under the testing policy.

## Docs each task touches

| Doc | Change |
| --- | --- |
| `docs/guide.md` | "The screen" tables: parts, the size table, the `?` key, the result line, the new states' words and colors |
| `docs/architecture.md` | The Interface rows: Header, Layout, Footer, status colors; the breakpoints; the Textual facts a task verifies |
| `docs/roadmap.md` | The task in Now, then Done; the closed backlog rows; new backlog rows: the ANSI theme, two-row list entries, toasts |
| `CHANGELOG.md` | Under Unreleased, in the user's words |
| `docs/validation.md` | One entry per task with the sizes checked in Ghostty |
| `docs/testing.md` | The size matrix and the capture script |

## Left to the builder

- Exact color values, within the contrast constraints.
- How the divider, rules and label rows are built in Textual 8.2.8, verified
  against the installed package.
- How the key panel comes to list the navigation keys.
- Whether the `-short` rule needs more than the result-line cap once the help
  line is gone.
- Test design: geometry and content assertions in the style of
  `tests/test_look.py`; no snapshot dependency unless the plan argues for
  one.
- The capture script's shape, modeled on the test fixtures: fictional
  machines, a fake checker, the environment pointed at empty folders.
