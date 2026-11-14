# Plan: F174, the compact lesson header and the reproduction disclosure (Issue #518)

Change request section 11 (U1a, U1c, U1d); requirements decision 44;
`docs/architecture.md`, "The reading experience". A presentation change of
every lesson page: no lesson prose, number, figure, figure status, or claim
changes; every fact stays on the page.

**Level 2.** Paths: `src/pbc/authoring/path.py`, `src/pbc/authoring/reproduce.py`,
`src/pbc/authoring/context.py`, `site/assets/site.css`, tests. No protected
path. Assertions of existing tests change where they pin the order or the
visibility of the header's rows and the reproduction summary's command (see
"Tests"); none is removed or weakened: the tests that read rows in the
closed disclosure open it first, natively, without scripts, and the summary
test is strengthened to "no command in the summary". The shared inputs
change, so CI runs everything; the session runs the targeted tier and the
unit and integration tests of the changed modules, and `review-feature.sh`
runs the full verification of the final tree (the owner's rule of
2026-11-08, on the Issue).

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f

- **Page and layout** (the lesson header and the last section of every
  lesson). Impeccable in its Read mode (`reference/mode-read.md`,
  `reference/craft-floor.md`, `reference/distill.md`: progressive
  disclosure, say it once); frontend-design for restraint (no new
  decoration, the site's tokens only). Expected artifact: the rendered M1,
  M5, and MAT6 pages at 1280×800, 390×844, and 320×568 without scripts,
  before and after, in `.agents/handoffs/518-screenshots/` for the pull
  request. Validation: the unit tests of `pbc.authoring.path` and
  `pbc.authoring.reproduce`, the context integration test, the e2e tests of
  the header, the last section, the glossary disclosures, the accessibility
  scan, the anchors and links, and the 320 px reflow. Accessible fallback:
  native `<details>`/`<summary>` and a `<nav>` with a label; no script.
- No scientific figure, diagram, or animation.

## Decisions

- **Visible header** (a definition list, as now): Course (with the
  position), Methods, Difficulty, What you'll learn, Previous, Next. The
  title and the purpose are Quarto's title block (`title`, `description`),
  unchanged.
- **The disclosure**: a closed `<details class="lesson-header-details">`
  at the end of the header, summary "Prerequisites, related lessons, and
  where this lesson fits", holding in the same order as before Slot,
  Introduction, Prerequisites, Before you begin (with its glossary
  definitions), Related, and Connections.
- **The end of the lesson**: the post-render step (`pbc.authoring.context`,
  ADR 014 decision 9) inserts before the end of `main` of every lesson page
  that has a last section a `<nav class="lesson-pager" aria-label="Previous
  and next lesson">` with the header's two rows; it is the only other place
  they appear. Not inside the reproduce region: sixteen measured-data labs
  have a paragraph after the last section's cell, and the pager must follow
  it. The last line of the `.reproduce` block stays "Suggest an
  improvement".
- **The last section**: heading and anchor unchanged; one sentence names the
  commit and says what the experiment (or the proof check) regenerates; the
  closed `<details class="reproduce-details">` holds every command, then the
  files and tests, then what the run writes. The summary shows no command,
  so no command appears twice. The live run of an agent lesson keeps its
  labelled not-verified box after the disclosure.
- **Figure status**: its CSS is left as it is (V2 owns it); nothing to change.

## Tests

- `tests/unit/test_authoring.py`: the summary holds the commit and no
  command; every command is in the details exactly once.
- `tests/unit/test_introductions.py`: the term order reads Course first and
  Slot, Introduction first inside the disclosure.
- New unit tests (`tests/unit/test_lesson_header.py`): the visible rows and
  the disclosure's rows of every header, none lost; the pager of the first,
  a middle, and the last lesson; the pager after everything the render wrote
  (a data lab's closing paragraph included); a page without `main` fails.
- `tests/e2e/test_learning_path.py`, `test_atlas.py`,
  `test_glossary_and_improvement.py`: open the header's disclosure by its
  summary (no script) before reading its rows; the term list gains no row
  and loses none; the disclosure is closed on load, and the pager is the
  last element of `main` with the header's previous and next links. New
  e2e test: the keyboard reaches the summary after the visible links and
  opens it with Enter.

## Steps

1. Header and pager in `pbc.authoring.path`; the pager inserted at the end
   of `main` by `pbc.authoring.context.regenerate_page`.
2. The sentence and disclosure in `pbc.authoring.reproduce`.
3. CSS in `site/assets/site.css`.
4. Tests; render M1, M5, MAT6; screenshots; targeted verification.
