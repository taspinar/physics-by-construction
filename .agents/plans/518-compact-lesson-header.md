# Plan: F174, the compact lesson header and the reproduction disclosure (Issue #518)

Change request section 11 (U1a, U1c, U1d); requirements decision 44;
`docs/architecture.md`, "The reading experience". A presentation change of
every lesson page: no lesson prose, number, figure, figure status, or claim
changes; every fact stays on the page.

**Level 3**, by trigger (ADR 020 decision 1; review round 1, M1): the
diff changes assertions of existing tests, which the scripts detect
(`tests/unit/test_authoring.py`, the reproduction section;
`tests/unit/test_introductions.py`, the order of the header terms). The
paths alone give Level 2 (`src/pbc/authoring/path.py`,
`src/pbc/authoring/reproduce.py`, `src/pbc/authoring/context.py`,
`site/assets/site.css`, docs, tests; no protected path). No changed
assertion is removed or weakened: the tests that read rows in the closed
disclosure open it first, natively, without scripts; the summary test is
strengthened to "one sentence, no commit, no command"; the test that no
section names a render now runs for a clean and a dirty build and exempts
only the owner's exact notice "Local preview: ...". The approval request
`.agents/approvals/518.md` asks for the owner's approving review of the
exact head. The shared inputs change, so CI runs everything; the session
runs the unit and integration tests of the changed modules and the e2e
tests on rendered M1, M5, and MAT6, and the supervisor runs the full
verification of the final tree (the owner's rule of 2026-11-08, on the
Issue).

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f
Skills: none (teaching: the lessons' sequence, explanations, exercises, and displayed code are unchanged; step 6 moves a pointer paragraph on the data download, word for word, into the run instructions)

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
  they appear. Not inside the reproduce region: the pager follows anything
  a page renders after the last section's cell (step 6 moved the sixteen
  measured-data labs' paragraphs into the section, but the placement does
  not depend on it). The last line of the `.reproduce` block stays "Suggest an
  improvement".
- **The last section** (the owner's decision of 2026-11-14 on the Issue,
  which replaces the earlier sentence with the commit): heading and anchor
  unchanged; visible only one sentence in the words of the kind of the
  lesson ("Run this experiment on your own computer.", "Replay this
  recorded agent run on your own computer.", "Check this proof on your own
  computer.", with "and check its proofs" or "and run its experiment" when a
  lesson has both) and the closed `<details class="reproduce-details">`
  "Setup and commands"; no commit and no command outside it. Inside: the
  install line with the setup page; the clone (the latest version on
  `main`, the default route) with "The latest version may produce different
  results."; "Optional: use the version behind this page" with "Skip this
  step to use the latest version." (the owner's review of 2026-11-14), the
  one optional extra step, `git checkout` of the build commit, linked descriptively ("the commit this page
  was built from"); then, "in either version", the shared steps once; what
  the run writes (the promise that numbers and figures match only for an
  exact build commit); the files and tests at the build commit; and, for an
  agent lesson, the live run's labelled not-verified box, apart from the
  replay. Each command block keeps the class `reproduce-commands`; together,
  in page order, they are the same command list as before, so the
  experiment check runs them unchanged. A dirty build shows the visible
  notice "Local preview: results may differ from the linked source." under
  the sentence and explains inside that the linked commit lacks the local
  changes, with no promise of exact reproduction; an unknown commit offers
  `main` only and says why. The last line of the `.reproduce` block stays
  "Suggest an improvement".
- **Figure status**: its CSS is left as it is (V2 owns it); nothing to change.

## Tests

- `tests/unit/test_authoring.py`: the visible part is the one sentence (no
  commit, no command); every command is in "Setup and commands" exactly
  once; `main` first with its note, then the page version's checkout of the
  build commit, linked descriptively, then the shared steps; an unknown
  commit offers `main` only; a dirty build shows the notice and promises no
  exact reproduction; the live run of an agent lesson is inside the
  disclosure.
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
  e2e tests: the keyboard reaches the summary after the visible links and
  opens it with Enter; the last section of every lesson shows one sentence
  and the closed "Setup and commands" without scripts, no commit and no
  command before it is opened, opens by keyboard, and lists `main` before
  the version behind the page. `tests/e2e/test_lessons.py` reads every
  `reproduce-commands` block in page order.

## Steps

1. Header and pager in `pbc.authoring.path`; the pager inserted at the end
   of `main` by `pbc.authoring.context.regenerate_page`.
2. The sentence and disclosure in `pbc.authoring.reproduce`.
3. CSS in `site/assets/site.css`.
4. Tests; render M1, M5, MAT6; screenshots; targeted verification.
5. The owner's decision of 2026-11-14: the last section as above, its
   tests and docs, and the complete before-and-after set of M1, M5, and
   MAT6 at 1280, 390, and 320 px without scripts, the header and the last
   section each closed and open, in `.agents/handoffs/518-screenshots/`.
6. The owner's review of 2026-11-14 (Issue comment "Owner's review of the
   reworked 'Run this experiment'"): the checkout is labelled "Optional:
   use the version behind this page" with "Skip this step to use the
   latest version." before its command; the paragraph on the data card's
   download that sixteen measured-data labs (MAT6 among them) wrote after
   the last section's cell moves, word for word, into the new `data`
   argument of `reproduce_this`, shown inside "Setup and commands" after
   what the run writes (a small extension of scope the owner accepted; no
   claim, number, or figure changes). Unit and e2e tests, the authoring
   guide, and the after screenshots of M1, M5, and MAT6 updated.
