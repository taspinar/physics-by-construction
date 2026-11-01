# Plan: F133 — The Course Atlas as a two-layer navigation page, Issue #338

- Issue: #338 (source: `docs/roadmap.md`, F133; ADR 021 decisions 1 to 3,
  amending ADR 002 and superseding ADR 018 decisions 2 and 3 in part).
- Branch: `feature/338-the-course-atlas-as`; base `6627512` (F132 merged).
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 3, assessed (the committed-artifact check, a guard of I6, is
  widened; the main navigation page, the shared CSS, and the lesson template
  change) and by trigger (the tests of the removed map, views, and controls
  of F125 and F126 are replaced, criterion 10). The full
  `./scripts/verify.sh` runs last; the approval request is
  `.agents/approvals/338.md`.

## The page (`site/path/index.qmd`, `pbc.authoring.atlas`)

The title stays "Course Atlas" and the address `path/`. The page body, in
order:

1. The breadcrumb (Home › Course Atlas) and one sentence on what the page
   is, with the totals (sequences, published lessons, planned lessons).
2. `<section id="atlas">` holding `<div id="choose" class="atlas">`, the
   grid of the sequences:
   - the group label "Part A · Physics by construction" (`id="courses"`),
     then the eight courses in the order of the curriculum file;
   - the group label "Part B · Physics and AI" (`id="paths"`), then the
     four method paths;
   - the smaller entry "Beyond the curriculum: proofs in Lean"
     (`id="lean"`).
   Each sequence is `<details class="atlas-sequence" name="atlas"
   id="course-<id>|path-<id>">`; the first course carries `open` in the
   HTML. The `<summary>` is the card: the card image (76 px slot), the title,
   "n of m lessons", and the progress hairline (one `<i>` segment per
   published lesson, see "Learner state"). The content is the panel: the
   panel image (200 px slot), the kicker "Part A · Course 3" or "Part B ·
   Method path 2", the title as `<h2>`, the manifest's one-line description,
   "n published · k planned", and the lesson rows; for a Part B sequence a
   visible caption "Computed from a toy model; no agent was run." under the
   panel image is **not** added (the owner declined extra descriptive text
   on 2026-10-31); its alt text says in one line that it shows a toy-model
   example.
3. The section "About the lessons" with the anchors the lesson pages link
   to: `#difficulty` (the scale), `#methods` with `#method-<id>` (each
   method's description; no lesson lists), and `#order` (the three orders,
   without the reference to the removed dependency map).
4. The section "Your progress" (`#your-progress`, `#progress-controls`)
   and the recommendations panel (`#recommendations`), unchanged, and the
   learner-state data element (`#learner-state-data`) with the learning path
   as today.
5. A visually hidden "The atlas in words": every sequence with its lessons
   and their state (published, planned), and the Lean entry.

Rows: a published lesson is `<li class="path-card atlas-row"
data-lesson-id=… data-state="published">` with the label (Plex Mono), the
title as `<a class="lesson-link">`, and only the marks Lab, Capstone, ★ Lean
(text, so never colour alone); a planned slot is `<li class="atlas-row
planned-slot" data-state="planned">` with the label, the title in italics,
and the word "planned", no link. The capstone row is last (curriculum order
puts it last) and set in the night tokens. Course sequences list the
course's slots in curriculum order, then the course's published lessons
that fill no slot and are not Lean lessons (today one:
`equations-from-noisy-trajectories`, in Classical mechanics, without a
label). The Lean entry lists the lessons of the Lean strand (L1) and the
published Lean lessons without a slot. Every published lesson is a row in
exactly one sequence. "n" counts published rows, "m" all rows; a planned
slot is never counted as published.

A capstone without a lesson (FL10) shows its planned description from the
manifest (the explanation of the concept that represents it) under its row.

### Layout (`site/assets/site.css`)

The F125/F126 atlas rules and the course-index rules of the path page are
removed (the index's lesson rows remain only on course pages, which do not
exist yet, so the rules go). At `min-width: 56em`, `.atlas` is a CSS grid
(`22rem` / `1fr`); every sequence is `display: contents`, its summary in
column 1, its `::details-content` `display: contents`, the panel in column
2 spanning every row, sticky; a trailing `1fr` row absorbs the panel's
height. The wide rule sits in `@supports selector(::details-content)`, so a
browser without it gets the accordion; a phone always does. Part A in the
cobalt ink, Part B in a copper ink (`--pbc-copper: #8a4b1f`, surface
`#f4ebe0`, both added to `pbc.authoring.design` with their contrast pairs);
Part A and B are also told apart by the group label and the kicker text.

### The address module (`site/learner/atlas.js`, rewritten)

About twenty lines: on load and on `hashchange`, the sequence the hash
names (its id, or an alias in `data-aliases`: `course-<id>-lessons` and
`concept-<id>` of the base page) is opened; on `toggle` to open, the hash
is replaced with the sequence's id (`history.replaceState`), and on a
narrow screen the card is scrolled into view. No request, no cookie, no
storage. `site/learner/path.js` (filters, opening disclosures of the old
index) is removed with its markup.

### Anchors of the base page

Listed from the page generated at the base (`AtlasSection` and
`PathOverview` of `6627512`), recorded in `tests/e2e/test_atlas.py`:

- kept as ids: `atlas`, `choose`, `courses`, `paths`, `course-<id>` (8),
  `path-<id>` (4), `methods`, `method-<id>` (5), `difficulty`, `order`,
  `your-progress`, `progress-controls`, `recommendations`,
  `learner-state-data`;
- opened through the module (`data-aliases`): `course-<id>-lessons` (8) and
  `concept-<id>` (67, the sequence of the concept's area);
- reach the top of the page (parts of the removed drawings and controls):
  `atlas-*` (map, controls, selection, concepts, capstones, text, markers),
  `graph`, `dependency-map`, `path-filters`, `prerequisite-graph-*`,
  `map-<course>-*`.

## The manifest (`site/atlas.yaml`)

Gains `sequences`: a list with one entry per course and method path of the
curriculum file and no other, each `{id, description, illustration}`;
`illustration` is the stem of the files under `site/assets/atlas/`
(`<stem>-card-152.webp` … `-panel-800.webp`), each of which the register
names. Checked by `atlas_problems` (a failing unit test per rule: a missing
sequence, an unknown id, a duplicate, a missing or empty description, an
unknown field, an illustration whose four files the register does not name,
a field the curriculum holds). The concepts lose `position` (the map's
placement, which nothing reads now), and its check goes with it; every
other concept and connection rule stays. `site/curriculum.yaml` is
unchanged.

## The illustrations

- Files: `site/assets/atlas/<sequence>-card-152.webp`, `-card-228.webp`,
  `-panel-400.webp`, `-panel-800.webp`: the 48 derived files of the
  owner's approved set (`pbc-illustration-material/derived`, re-derivation
  checked identical by the owner), WebP, 4:3. Cards `srcset` 152w/228w
  with `sizes="76px"`; panels 400w/800w with `sizes="200px"`;
  `width`/`height` set; the panel images are `loading="lazy"` except the
  first open one.
- Register (`site/assets/provenance.yaml`): one entry per file, the raster
  form `{origin, licence, master}`: `origin` is `{script: <repository
  path>}` and/or `{author: …, date: …}` or `{model, prompt, date}`;
  `master` the file name of the master and its SHA-256. Astrophysics (the
  transit) has no script: author and date.
- Scripts: `tools/illustrations/` (outside `site/`, excluded from ruff, not
  run by the build or CI): the owner's scripts of the chosen images as
  delivered (`double_pendulum_atlas.py`, `render_hot_cold.py`,
  `render_waves.py`, `render_solenoid.py`, `generate_fluid_dynamics.py`,
  `generate_wigner_cat.py`, `render_phonons.py`, `render_part_b.py`),
  `part_b_textfree.py` and `derive_assets.py` adapted to the repository
  paths, a `README.md`, and `regenerate.py`, the regeneration check on
  demand: it runs a sequence's script in a scratch directory, hashes the
  master it writes against the register, and, where the bytes differ (the
  renders are not promised to be byte-stable across library versions),
  derives the 800 px panel and reports the mean absolute pixel difference
  against the committed one, failing above 2 of 255. Not listed in
  `scripts/verify.conf`. Left out: `render_ising.py`, `render_lensing.py`,
  `test_lensing.py`, `render_standing_wave.py` (their images were not
  chosen).
- Alt text: names the illustration ("Illustration: a double pendulum's
  tracks"); a Part B one adds "a toy-model example, no agent was run".

## The committed-artifact check and the asset-source rule

`tests/support/lesson_checks.py`: a tracked `.webp` or `.png` under
`site/assets/` is admitted only when the register names it with a complete
raster entry (origin, licence, master with its SHA-256); an unregistered
raster, an incomplete entry, every other raster type (`.jpg`, `.gif`,
`.avif`, …), and every image outside `site/assets/` (a lesson directory
included) are rejected; an entry whose file is missing fails the
asset-source rule; a raster under `site/assets/` without an entry fails it
too. Tests in `tests/integration/test_lesson_checks.py`, written first and
seen failing.

## The relationships on the lesson pages

`LessonHeader` gains a row "Connections" after "Related", for a published
lesson whose slot belongs to a concept with a conceptual connection or a
capstone membership: each connection as a sentence of its type with the
other concept's name, a link to the other concept's sequence in the atlas,
and the rationale; each membership as "Part of the capstone project
<label> <title>" (a link when published); a capstone lesson lists the
concepts it integrates. Planned slots have no page, so no planned lesson
shows any. Built from the manifest by `pbc.authoring.atlas` (lazy import,
no cycle). The links of the header into the atlas (`#course-<id>`,
`#path-<id>`, `#method-<id>`, `#difficulty`, `#order`) all still resolve.

## Learner state

`progress.js` and `recommend.js` are not changed. The rows carry
`path-card` with `data-lesson-id` and `a.lesson-link`, so the progress
marks and the completed list work as before; the hairline segments in the
cards carry `path-link` with `data-lesson-id` (no link inside), which
`progress.js` already marks `data-completed`, and CSS colours them.
`tests/e2e/test_learner_state.py` and `tests/e2e/test_recommendations.py`
pass unchanged.

## Tests

- `tests/unit/test_atlas.py`: rewritten around the new generator: the
  manifest rules (old concept rules kept, `position` removed, sequence
  rules added), the HTML of the sequences (one details per sequence, one
  open, the name, ids, counts equal the rows, planned rows not links and
  not counted, each lesson once, the capstones, FL10's description, Part
  B's ink class and alt text, the Lean entry, the aliases), the textual
  equivalent, byte-stable output.
- `tests/unit/test_path.py` / header tests: the Connections row equals the
  manifest; none for a lesson without a concept connection.
- `tests/e2e/test_atlas.py` and `tests/e2e/test_atlas_interaction.py`:
  replaced: layout at 1280×800 and 390×844, no-script reachability by
  keyboard, exclusive opening, focus visible, anchors of the base (each
  kept id exists; aliases open their sequence), hash follows a click, no
  request/cookie/storage while operating, the fallback with the wide rule
  disabled, reflow at 320 px, the accessibility scan, in Chromium, Firefox,
  and WebKit.
- `tests/e2e/test_learning_path.py`: tests of the removed index, filters,
  method lists, and graph replaced by the atlas tests above; the header
  and the difficulty/order tests kept.
- `tests/e2e/test_home.py`: the anchors Home links to still exist.

## Docs

`docs/atelier.md` (the atlas component, the asset classes, the copper
ink), `docs/authoring.md` ("Course atlas"), `tools/illustrations/README.md`.
`docs/architecture.md` is protected and already restated by the planning.

## Visual deliverables and skills

Page and layout: the Course Atlas page and the lesson header's Connections
row.

Skills: impeccable@08d5b470, frontend-design@dbd4588f

Expected artifact: the built `path/index.html` at 1280 px and 390 px and a
lesson header. Scientific validation: none (no scientific figure; every
title, count, and state comes from the curriculum file and the front
matter, the descriptions and relationships from the manifest). Accessible
fallback: native disclosures without a script, the textual equivalent, the
accordion where `::details-content` is missing.

Interface artwork: the twelve sequence illustrations (class C of ADR 021).

Skills: impeccable@08d5b470

Expected artifact: 48 WebP files under `site/assets/atlas/`, registered.
Scientific validation: none required (class C; the visual check of
criterion 7 instead: composition, recognisability at 76 px, colour,
consistency, no text, number, or formula). Accessible fallback: alt text
naming each illustration. The PBC Scientific Visualization skill does not
apply (no scientific figure); diagram-design does not apply (no conceptual
diagram).

Exceptions to the skills, from the brief: the kicker ("Part A · Course
3"), the monospace labels and counts, and the middle dot in "n published ·
k planned" are fixed by the Issue's design (mock 3), which wins over the
skills' defaults; the kicker is set in sentence case, not capitals.
