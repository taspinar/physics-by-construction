# Plan: Home, copy and structure (Issue #481)

Follow-up of F158 (Issue #462). The owner's copy of 2026-11-11 is fixed text:
the hero subtitle, the sections "What is Physics by Construction?", "Build.
Experiment. Understand.", "From computational physics to artificial
intelligence" (Part A, Part B, and the transition "First understand the
physics. Then challenge the AI."), and "How we verify what we teach". The
example lesson previews leave Home; the eight Part A subjects appear as one
compact line derived from the curriculum. The visual hero (the sibling
Issue) is out of scope.

**Level 3.** Paths: `docs/decisions/021-…` (ADR 021 decision 4 amended),
`docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md` (protected). Triggers:
tests removed or replaced (the examples tests of `tests/unit/test_home.py`,
`tests/e2e/test_home.py`, `tests/integration/test_home_build.py`; the Home
half of `test_home_and_about_carry_the_sentence_and_the_footer_carries_the_line`
in `tests/e2e/test_identity_site.py`); the text rule "no 'discover'" is
narrowed for the Home copy (below), a change of a validation rule. The
owner approves the exact head at the merge gate; the approval request
`.agents/approvals/481.md` is written by `finish-feature.sh`.

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f

- **Page and layout** (Home below the hero; the hero only by its subtitle).
  Impeccable in its Persuade mode within the restraint of the brief
  (`reference/craft-floor.md`, `reference/mode-persuade.md`,
  `reference/layout.md`); frontend-design for restraint ("spend your
  boldness in one place": the hero; everything below is quiet). Expected
  artifact: the rendered `index.html` at 1280×800, 768×1024, 390×844,
  360×640, 320×568, at 200 % text, with the keyboard and without scripts.
  Validation: the unit, integration, and e2e tests of Home, the checks every
  page gets (accessibility scan, keyboard pass, reflow, payload budget), the
  rendered review, and the owner's approval on the rendered page
  (`owner_approval`). Accessible fallback: the page is static HTML; the
  subjects are a real list (`<ul>`) whose separators are CSS only.
- No scientific figure, conceptual diagram, animation, or new artwork. No
  "subtle visual representation of the process" is added: the owner allowed
  one, did not require it; a row of steps would be the feature-card pattern
  the Issue rules out, and the prose carries the sequence.

## Decisions taken in this plan

- **Data files.** `site/hero.yaml`: `subtext` becomes the owner's new
  subtitle; nothing else changes. `site/home.yaml` keeps its four sections
  in their order and keys (`identity`, `philosophy`, `curriculum`,
  `integrity`), each with the owner's `heading` and `text`. `curriculum`
  loses `examples` and gains `part-a`, `part-b`, and `relation`, each a
  mapping of `heading` and `text`, validated like the other sections. The
  curriculum section has no paragraphs of its own (the owner gave none).
  `site/journey.yaml` is untouched: the Course Atlas and About keep its
  longer Part A and Part B text; Home no longer reads it for the parts.
- **Anchors stay**: `#about-the-site`, `#how-physics-is-learned`,
  `#what-you-can-learn`, `#integrity`, and `#part-a`, `#part-b`,
  `#part-a-to-part-b`, so that no existing link breaks.
- **Identity.** Home's introduction no longer opens with the canonical
  sentence of `pbc.authoring.identity`; Home starts with the owner's first
  paragraph and keeps the one link "About the creator and JIDAI". The
  identity module is unchanged in code; its docstring no longer lists Home
  among the surfaces of the sentence. About, README, `CITATION.cff`, and the
  footer (also on Home) keep it. The e2e identity test checks About for the
  sentence, the footer of both for the line, and that Home's content does
  not hold the sentence.
- **"discover".** The owner's Part B paragraph says "The aim is not to
  assume that AI can make scientific discoveries"; the heading "Can AI help
  us discover new physics?" is a heading (plain text, never under the
  journey's word rule). For the Home copy there is no rule about the word "discover": the home page is not part of the curriculum (owner's decision of 2026-11-11 on Issue #481, which replaces the narrowed exception of round 1 and its tests). The journey file, the introductions, and the lessons keep the strict rule, pinned by a unit test.
- **The subjects.** One `<ul class="home-subjects">` after Part A's
  paragraphs, labelled "The courses of Part A" for assistive technology,
  its items the course titles in curriculum order from `COURSES` (the list
  `site/curriculum.yaml` is validated equal to, titles included, by
  `pbc.authoring.path`), so no second list is written. Plain text, no
  links (lesson discovery belongs to the atlas); a course with no published
  lesson carries "(planned)", so no planned course reads as published
  (today all eight have lessons). Inline items with a middle dot drawn by
  CSS (`li + li::before`), as the owner's spec shows them; without CSS it
  is an ordinary list.
- **Removal of the examples.** `HomeContent.example`, `_example_card`, the
  preview imports, `PARTS`, the `examples` validation, and the CSS of
  `.home-example`, `.home-preview`, `.home-meta` leave. `pbc.authoring.previews`
  stays (the learning path page uses it). Every lesson stays reachable
  through the atlas and the header; nothing in a lesson changes.
- **Layout.** Part A and Part B side by side from 992 px as now, under
  their cobalt and copper rules, with the subjects as a quieter line under
  Part A. The transition below them spans both columns with a thin neutral
  rule and a smaller heading (the `h3` at body-large size), so it reads as a
  link between the parts, not a third part. "How we verify what we teach"
  is the quietest: its heading one step smaller than the other `h2`s, the
  prose in the muted ink at the body size, more space above it. No cards,
  badges, panels, or icons.
- **Tests.** Replaced: the examples tests (unit, integration, e2e) by tests
  of the parts' copy and the subjects; the order test's headings by the
  owner's; the hero subtext test by the new words. Added: the exact owner
  copy pinned in a unit test; the subjects follow `COURSES` and mark a
  planned course; the narrowed "discover" rule (a question and a negation
  pass, an assertion fails); the canonical sentence absent from Home's
  introduction and present on About. The integration test builds the page
  from a minimal project and checks the subjects and that no preview or
  example is on it.
- **Documents.** ADR 021 decision 4 gains an amendment of 2026-11-11; the
  requirements' "Home page" and decision 43 notes, the roadmap block of
  F158 (a note of the follow-up), `docs/architecture.md` (textbook sources,
  the Home section, the file tree), `docs/atelier.md` ("Home page"), and
  `docs/authoring.md` (the Home copy file) are brought up to it.

## Runtime and payload estimate

Home loses two preview images (each about 20–40 kB WebP, lazy-loaded, so
counted in the page's payload budget) and their markup, and gains about 2 kB
of prose and a list of eight items. The page's payload goes down; no new
request, script, font, or image. The page renders as before (one Python
cell); build time unchanged within noise. The checks: unit tests of Home
(seconds), the integration build of a minimal project (about a minute),
the e2e tests of Home on a built site.

## Steps

1. Data files (`site/hero.yaml`, `site/home.yaml`).
2. `src/pbc/authoring/home.py` (schema, validation, page), the
   `journey.py` keyword for the narrowed rule, the identity docstring.
3. CSS of the curriculum section, the subjects, the transition, integrity.
4. Tests (unit, integration, e2e).
5. Documents (ADR 021, requirements, roadmap, architecture, atelier,
   authoring).
6. Render Home and review it at the five sizes, 200 % text, keyboard, no
   scripts; screenshots for the PR.
7. `./scripts/verify.sh --targeted` (or `--base`), last.

## Found while building (2026-11-11)

- **Payload, measured** by the payload check of `tests/e2e/test_built_site.py`
  on Home alone: 1,298,134 bytes on `main` (CI run of 769a2bb), 1,264,614
  bytes with this change (−33.5 kB, the two previews).
- **The subjects wrap by name.** Each subject is an inline block, so a
  name never breaks across lines when it fits a line; the separator ends
  the line. At 320 CSS px and 200 % text the column is narrower than
  "Electromagnetism" at that size, and the page's `overflow-wrap:
  break-word` breaks it inside, as it breaks any word longer than the
  column. `hyphens: auto` was tried and rejected: Chromium then hyphenated
  other names ("cos-mology", "mat-ter") and still broke that one without a
  hyphen. For the owner's look at the rendered page.
- **The 200 % check of the rendered review** set the root font size to
  200 %; at 768 px that makes the hero wider than the screen on `main` as
  well (807 px), so it is no finding of this change; the reflow test of
  the project, which scales text its own way, passes.
