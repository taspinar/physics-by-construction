# Plan: Course Atlas, inline expanding courses (Issue #483)

Follow-up of F133 (#338, the two-layer atlas) and F157 (#436, the learning
journey on the atlas). The owner's redesign request of 2026-11-11: the
Course Atlas less text-heavy, the curriculum at a glance, every course and
method path expanding inline beneath its own row on every viewport; the
owner's fixed copy for the subtitle, the two paragraphs that replace "The
learning journey", and the progress sentence. The atelier design language,
the illustrations, the lesson content, the progress storage, the
accessibility floor, and the verification guarantees stay.

**Level 3.** Paths: `docs/decisions/021-…` (ADR 021 decision 3 amended by a
dated note), `docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md` (protected).
Triggers: tests removed or replaced (listed under "Tests" below). Assessed:
the page is the site's main navigation and the shared stylesheet changes.
The owner approves the exact head at the merge gate; `finish-feature.sh`
writes the approval request for #483 under `.agents/approvals`. Intermediate rounds
may take quick feedback from the unit tests of the changed modules and from
`pytest tests/e2e/test_atlas.py` on a locally rendered path page; the final
tree gets the full verification and a full review after it, which the
supervisor runs after the commit (sessions do not run the full
`./scripts/verify.sh`).

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f

- **Page and layout** (the Course Atlas: its opening, the sequence rows,
  the expanded content, the lesson rows, "Your progress", "How the lessons
  work"). Impeccable in its Read mode (`reference/craft-floor.md`,
  `reference/distill.md`, `reference/layout.md`, `reference/adapt.md`);
  frontend-design for restraint (one memorable element: the row of
  illustrated courses; everything else quiet). Expected artifact: the
  rendered `path/index.html` at 1280×800, 768×1024, 390×844, 360×640,
  320×568, at 200 % text, with the keyboard, without scripts, with reduced
  motion; screenshots in the PR (all collapsed; a physics course expanded;
  a method path expanded; the phone layouts). Validation: the unit tests of
  `pbc.authoring.atlas` and `pbc.authoring.path`, the e2e tests of the
  atlas (layout at three viewports, keyboard, no scripts, anchors, the
  accessibility scan, the reflow at 320 px, the payload), the rendered
  review, and the owner's approval on the rendered page (`owner_approval`).
  Accessible fallback: native `<details>`/`<summary>` disclosures, every
  lesson reachable without scripts, the visually hidden textual equivalent
  kept.
- No scientific figure, conceptual diagram, animation, or new artwork: the
  twelve illustrations are reused at the card size; nothing is regenerated.

## Decisions taken in this plan

- **The opening.** Quarto's `subtitle` of `site/path/index.qmd` carries the
  owner's subtitle (also the page's `description` meta, which no longer
  states counts); the breadcrumb leaves the atlas index only
  (`pbc.authoring.introductions` keeps its own). The two paragraphs that
  replace "The learning journey" are the owner's fixed text, held as a
  constant of `pbc.authoring.atlas` (`ATLAS_INTRODUCTION`, pinned by a unit
  test) like the Lean entry's sentence; no new data file, no change to
  `site/journey.yaml`, whose Part A and Part B text About keeps. The
  journey's four other sections (background, routes, capstones, the three
  kinds of evidence) are shown on no page after this change; the file keeps
  and validates them (the Issue leaves the shared file alone), and "How we
  verify the science" explains the kinds of evidence. The atlas no longer
  reads the journey: `JourneyContent.atlas_markdown`, the `Opening`
  protocol, the `journey` field of `AtlasSection`, and `atlas_journey` are
  removed; `about_markdown` and the validation stay.
- **The three figures.** One `<ul class="atlas-figures">` with three items,
  each a number and a label: the physics courses (the sequences of Part A),
  the AI method paths (Part B), the published lessons (every published
  lesson of the learning path, which is every row with a lesson, the
  extension and Lean lessons included). Derived in `AtlasSection`, never
  written. Numbers in the text face at the second heading size, labels in
  the small muted size; no card, no accent, no eyebrow.
- **The rows.** Each sequence stays one `<details class="atlas-sequence"
  name="atlas" id="course-<id>|path-<id>|lean">`, none open at load. The
  `<summary>` is the row: the card illustration (76 px, the registered
  card files; the panel files stay registered and in use on the
  introduction pages), the title, the count "n published · k planned" (or
  "n published"), the progress hairline (one segment per published core
  lesson, which `progress.js` marks; hidden by CSS until a segment is
  completed, so a first visit shows none), and a drawn chevron that turns
  when the row is open (decorative; the disclosure's own state is what
  assistive technology reads). The expanded content is directly beneath,
  at every width: the title as the `h2`, the manifest's description, the
  link "Read the course introduction" (a method path: "Read the method
  path introduction") where an introduction file exists and nothing
  otherwise, then the lesson rows in teaching order, then the optional
  extensions. The panel illustration and the kicker ("Part A · Course 3")
  leave; the part is told in words by the group label before the courses
  and the paths, as before. The Lean entry keeps its place after the paths.
- **Exclusivity.** The `name="atlas"` group gives one open sequence at a
  time without a script in Chromium 120+, Firefox 130+, Safari 17.2+.
  `site/learner/atlas.js` gains the fallback for a browser that lacks it:
  on a `toggle` that opens a sequence it closes every other open one.
  Without scripts in such a browser every row can open and the exclusivity
  may be lost; every lesson stays reachable. The module also drops its
  narrow-only condition: opening a row scrolls it to the top of the window
  at every width, because the inline accordion shifts the page when the
  previously open row closes. No request, cookie, or storage; the source
  check `check_atlas_module_sources` stays.
- **The lesson rows.** `<li class="atlas-row path-card" data-state
  data-lesson-id>`: the slot label in the monospace face (muted), the title
  as the link (the part's ink, no underline until hover or focus), the
  difficulty title from the front matter (`DIFFICULTIES`), and the marks in
  words: Lab, Capstone, Lean, planned; "✓ completed" is added by the
  existing CSS when `progress.js` marks the row. A planned row is no link
  and not focusable, in italics and muted with the word planned. Hairline
  separators between rows; the capstone row loses the night ground and the
  lab its accent hairline (no cards, no coloured surfaces; the words carry
  the meaning); the Lean star leaves. Order and content from the curriculum
  and the front matter as before.
- **Your progress.** The heading and anchor `#your-progress` stay. The
  place `#progress-controls` holds the owner's sentence for a reader
  without scripts; `progress.js` (`pathPage`) renders without saved
  progress the same sentence, and with saved progress "n of m lessons
  completed." with a hairline indicator (`aria-hidden`; the sentence says
  it) and the completed lessons in a closed native disclosure; the clear
  button stays always rendered; "All stored progress was cleared." stays
  after clearing. The storage key, the data shape, and every other function
  of the script are unchanged. The long explanation of what is stored
  moves into a closed `<details class="atlas-note">` under the sentence
  (the lesson pages' link "What is stored, and how to clear it" still
  reaches `#your-progress`). The recommendations panel keeps its markup.
- **How the lessons work** (`h2`, anchor `#about-the-lessons` kept). Three
  `h3`: "Difficulty" (`#difficulty`): one sentence naming the three levels
  as shown in the rows, the descriptions in a closed disclosure; "Methods"
  (`#methods`): one list of the methods a published lesson uses, each with
  its anchor `#method-<id>` for the lesson headers, the name and its one
  sentence; "Lesson order and prerequisites" (`#order`): courses have a
  recommended teaching order (the lists above), each lesson names its
  prerequisites in its header and those are all it needs first, related
  lessons offer further exploration, and previous and next at the foot of
  a lesson follow the site's one linear order course by course, so a
  prerequisite may lie outside it. The previous/next behaviour is not
  changed; only its explanation is shorter.
- **Layout.** No `column-page`: the whole page in the reading column. No
  grid, no `::details-content`, no sticky panel, no `--atlas-rows`. The
  open row's content is indented under the illustration with a 1 px rule in
  the part's ink at its left, as the accordion already did. The one motion
  is a 150 ms turn of the chevron that answers the reader's click (see
  "The chevron's transition" below); `prefers-reduced-motion: reduce`
  removes it, and there is no other transition or animation. The wide-screen rule,
  the journey rules, the panel head, the kicker, the night capstone, and
  the lab hairline leave the stylesheet; Home's rules are untouched.
- **Anchors and deep links.** `#course-<id>`, `#path-<id>`, `#lean`, the
  aliases of the previous atlas (`data-aliases`), `#atlas`, `#choose`,
  `#courses`, `#paths`, `#your-progress`, `#progress-controls`,
  `#recommendations`, `#learner-state-data`, `#about-the-lessons`,
  `#difficulty`, `#methods`, `#method-<id>`, `#order` all stay ids of the
  page; `#journey*` leave with the journey. Lesson addresses and course ids
  unchanged.
- **Tests.** Replaced in `tests/e2e/test_atlas.py`:
  `test_a_wide_screen_shows_the_cards_and_the_first_panel_beside_them`,
  `test_a_phone_shows_an_accordion_with_the_open_panel_under_its_card`, and
  `test_without_the_wide_rule_the_page_falls_back_to_the_accordion` by
  `test_every_row_is_collapsed_at_load_and_opens_inline_beneath_itself`
  (1280×800, 768×1024, 390×844, with and without scripts) and
  `test_nothing_of_the_atlas_is_sticky_or_beside_the_rows`;
  `test_the_journey_comes_before_the_cards_and_opens_by_keyboard_without_scripts`,
  `test_an_address_inside_the_journey_opens_it`, and
  `test_the_open_journey_passes_the_scan_and_reflows` by
  `test_the_opening_is_the_subtitle_the_two_paragraphs_and_the_three_figures`
  and `test_the_atlas_holds_no_journey_and_about_still_does`;
  `test_the_illustrations_load_at_the_density_of_the_screen` by the same
  test for the card image only. Changed: the keyboard tests (no row open
  at load), the counts of the extension test, the accessibility and reflow
  tests (they open rows first). Added: planned rows are no link and not
  focusable; the rows show the difficulty of the front matter; the
  introduction link stands before the rows and a sequence without an
  introduction has none; the script fallback keeps one row open when the
  `name` attribute is removed. In `tests/unit/test_atlas.py`: the page tests
  follow the new markup (none open, the counts, the marks, the difficulty,
  no kicker, the figures, the introduction's place). In
  `tests/unit/test_journey.py` the seven tests of "The opening of the Course
  Atlas" are replaced by one test that the atlas holds no journey text and
  About does. In `tests/unit/test_learning_path.py` the overview tests
  follow the new headings and texts. In `tests/e2e/test_learning_path.py`
  the difficulty test opens the disclosure and the order test reads the
  new words. In `tests/e2e/test_learner_state.py` the progress test reads
  the owner's sentence without progress and opens the completed-lessons
  disclosure. `tests/e2e/test_recommendations.py` passes unchanged. In
  `tests/unit/test_curriculum.py`
  `test_the_page_opens_only_the_first_sequence_and_loads_nothing_from_outside`
  becomes `test_the_page_opens_no_sequence_and_loads_nothing_from_outside`,
  and its count helpers read the one count of the row. In
  `tests/unit/test_introductions.py`
  `test_the_panel_link_comes_after_the_lessons_so_that_the_tab_order_holds`
  is replaced by
  `test_the_atlas_link_comes_before_the_lessons_after_the_description`.
  `tests/support/site_checks.py`: `check_controls_keep_nothing` loads the
  faces the stylesheet declares before it records requests, as it loads
  the lazy images (the italic face was fetched when the first planned row
  appeared, since no row is open at load); the check stays strict for every
  other request.
- **Documents.** ADR 021 decision 3 gains a dated amendment (2026-11-11,
  Issue #483); the requirements' "Course atlas" bullet gains a dated note;
  the roadmap blocks of F133 and F157 gain a note (F126 is already the
  record of what F133 replaced; a one-line note points here);
  `docs/architecture.md` ("The course atlas", "The Course Atlas" of the
  quieter site, the component rows of the atlas modules and the textbook
  sources), `docs/atelier.md` ("The course atlas", "The atlas's address
  module", the phone line), `docs/authoring.md` ("The course atlas", the
  journey paragraph), and the comments of `site/journey.yaml` and
  `pbc.authoring.journey` are brought up to it.

## Runtime and payload estimate

The page loses the journey (about 6 kB of HTML), the breadcrumb, the
summary sentence, the first panel's eager illustration (`mechanics-panel-400`
at 2x, about 30 kB) and the lazy panel illustrations that the open rows
requested; it gains the subtitle, two paragraphs, three figures, and one
difficulty word per published row (under 3 kB). `atlas.js` grows by about
six lines; `progress.js` changes one function without a new request. The
payload at 1280 px and 2x goes down by about 35 kB from the measured
figure the payload test prints; the budget holds. The page renders as
before from two Python cells; build time unchanged within noise. The
checks: the unit tests (seconds), the e2e tests of the atlas on a built
site (minutes).

## Steps

1. `src/pbc/authoring/atlas.py`: the opening, the figures, the rows, the
   expanded content; `journey.py` loses the atlas opening.
2. `src/pbc/authoring/path.py`: "Your progress" and "How the lessons work".
3. `site/path/index.qmd`: subtitle and description.
4. `site/assets/site.css`: the atlas rules; `site/learner/atlas.js` and
   `progress.js` (`pathPage`).
5. Tests (unit, e2e).
6. Documents (ADR 021, requirements, roadmap, architecture, atelier,
   authoring, the journey comments).
7. Render the path page locally and review it at the five sizes, 200 %
   text, keyboard, no scripts, reduced motion; screenshots for the PR.
8. `./scripts/verify.sh --targeted`, last (it will report that CI runs
   everything: `src/pbc/authoring` and `tests/e2e` are shared inputs).

## Found while building (2026-11-11)

- **The subtitle** is Quarto's `description` of the page, not `subtitle`:
  the title block prints both when both are set, and `description` also
  feeds the meta description. The rendered element is `.description`.
- **Payload, measured** by the payload test on the rendered page at 1280 px
  and 2x: 1,416,723 bytes in 38 files, of which the illustrations 29,854
  (the card files only); within the budget.
- **200 % text at 320 CSS px**: a title or a mark breaks inside its word
  only when the word cannot fit (`overflow-wrap: anywhere` on the row's
  text columns and, below 40 em, on the marks), so no row widens the page.
  The page still scrolls to 335 px with a course open at that zoom; About
  (396 px) and the course introduction (409 px) scroll wider at the same
  zoom on the same site, so this is the site's rule for prose at that zoom
  (the subtitle's longest word), not a finding of this change. At normal
  text the reflow test holds at 320 px.
- **The local e2e run** used CI's built site of `be7c7e4` with the path page
  and About re-rendered from this tree. The eleven failures of
  `tests/e2e/test_learning_path.py` and `test_learner_state.py` outside the
  atlas were the stale lesson pages (EM8 and the header of the EM lessons
  came after that run); the full CI run on the pull request checks them.
- **The chevron's transition** is the one motion of the page (150 ms on the
  mark that answers the reader's click); `prefers-reduced-motion: reduce`
  removes it, shown by a test.
