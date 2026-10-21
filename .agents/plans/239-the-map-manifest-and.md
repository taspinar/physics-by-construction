# Plan: F125, the map manifest and the static atlas (Issue #239)

Source: Issue #239 (the authority on what is delivered), the owner's
comment on it (2026-10-20: the Learning path is not yet the visual atlas;
keep this feature's scope, take over nothing of F123, F124, F126, F127);
the change request `docs/changes/scientific-atelier-atlas.md` sections 4
("Course atlas"), 5, 7, 8; requirements decision 36 and "Data and
persistence"; ADR 018 decision 3 (the atlas) and decision 6 (review); ADR
013 (the curriculum file stays the one source of the planned structure);
ADR 019 (the skills); `docs/architecture.md`, "The atlas at build time"
and I31; `docs/atelier.md` (the design specification of F123).

Context: base `origin/main` at `3a83ab6`; the branch held no work when
this plan was written (2026-10-20). No plan existed; the implementer
wrote this one in the unattended session, so the owner reads it with the
pull request.

## Goal

The map manifest `site/atlas.yaml` and its validation in `pbc.authoring`;
the curated concepts and conceptual connections; the atlas as
build-generated semantic HTML and inline SVG with a textual equivalent,
placed on the path page above the F64 index, behind a switch of anchors,
with every published lesson reachable without scripts and every planned
slot labelled.

## Acceptance criteria and their gates (ADR 020 decision 2)

| # | Criterion (short) | Gate |
|---|---|---|
| 1 | Manifest rules with a failing test each; no curriculum or front-matter field; every reference resolves | implementation |
| 1 | The owner approved the manifest's content on the Issue after the independent review of the connections | owner_approval (pending) |
| 2 | Eight courses, four paths as a connected layer, the Lean and method views, three capstones planned with the manifest's explanation; EM9 on the map and in the index | implementation |
| 3 | Three edge types in drawing and words; prerequisite edges equal the front matter; conceptual edges with type and rationale; capstone links only when published | implementation |
| 4 | Planned concept or slot labelled, not by colour alone, never a link, never counted; counts equal the lessons | implementation |
| 5 | Without JavaScript every lesson reachable through the map and the index; previous addresses, anchors, graph nodes resolve; the switch works | implementation |
| 6 | Textual equivalent; scan; reflow at 320 px; payload; byte-stable rebuild; search index unchanged in meaning | implementation (the built-site tests of the full run) |
| 6 | The keyboard pass and the screen-reader reading order recorded in the manual pass | owner_approval (pending) |
| 7 | Rendered review: implementer's screenshots (implementation); reviewer's assessment and owner's pass on the Issue | implementation / owner_approval (pending) |
| 7 | Skills and their effect recorded; every illustration's code in the repository | implementation |
| 8 | The full verification run passes | implementation (local), pr_ci |

## Risk classification (ADR 020 decision 1)

Level 2: `site/atlas.yaml`, `site/path/index.qmd`, `site/assets/site.css`,
`src/pbc/authoring/atlas.py` and `path.py`, tests, `docs/authoring.md`,
`docs/atelier.md`. No protected path of `.agents/policies/guardrails.conf`
is touched (`docs/architecture.md` and `docs/roadmap.md` already describe
this feature and are not changed). Triggers: none that a script detects;
the manifest adds new scientific statements about the curriculum (the
conceptual connections) but changes no claim `main` publishes. Its content
needs the owner's approval on the Issue anyway (criterion 1, pending at
`owner_approval`). Shared inputs (`site.css`, `src/pbc/authoring`): the
last verification is the full `./scripts/verify.sh`.

## Visual deliverables and skills

| Deliverable | Class | Expected artifact | Scientific validation | Accessible fallback |
|---|---|---|---|---|
| The atlas section of the path page (breadcrumb, switch, legend, map region, capstones, concept panels) | page or layout | the HTML that `pbc.authoring.atlas` writes into `site/path/index.qmd`; the atlas rules in `site/assets/site.css` | none for the layout; the counts, states, and edges come from the data and are tested | the switch's anchors, the panels as native disclosures, the textual equivalent, the F64 index |
| The map drawing (course areas, concept nodes, the three edge marks, the Part B layer, the view layer) | page or layout (interface artwork in the sense of ADR 018) | inline SVG written by `AtlasMap.svg` in `src/pbc/authoring/atlas.py` | edges and counts tested against the front matter and the manifest | real links and text in the SVG; the textual equivalent |
| The eight course illustrations | interface artwork | small SVG drawings, one function per course in `src/pbc/authoring/atlas.py` (`ILLUSTRATIONS`) | each glyph's physics checked by the reviewer (a pendulum's arc centred on its pivot, an orbit with the star at a focus, a dipole's field lines, streamlines around a cylinder, equally spaced levels in a parabolic well, a lattice, a random walk, a sine wave); no number, no caption | `aria-hidden`: the course title beside it names the area |

The page and the map:

Skills: impeccable@08d5b470, frontend-design@dbd4588f

The course illustrations:

Skills: diagram-design@550fd66e

No scientific figure is added (the previews stay F63's), so the PBC
Scientific Visualization skill does not apply:

Skills: none (no scientific figure and no conceptual diagram in a lesson; pbc-scientific-visualization does not apply)

## Current state (inspected at 3a83ab6)

- `site/path/index.qmd`: front matter (title "Learning path"), the section
  `## Choose a physics course {#choose}` with two paragraphs, and one cell
  printing `learning_path()` (`PathOverview` in `src/pbc/authoring/path.py`):
  courses (`#courses`, `#course-<id>`), method paths (`#paths`,
  `#path-<id>`), methods (`#methods`, `#method-<id>`), difficulty, order,
  progress, the prerequisite graph (`#graph`, `#dependency-map`), and the
  script `learner/path.js`.
- `site/curriculum.yaml`: 8 courses, 4 paths, 115 slots; capstones T11,
  EM9, FL10 (kind `applied capstone`); L1 has the strand `lean` as home.
- 45 lessons; 41 fill a slot; 4 Lean lessons and
  `equations-from-noisy-trajectories` have none. Methods in use:
  simulation 40, llm-agents 7, lean 5, measured-data 3, abm 1.
- `learner/path.js` filters every element with `[data-state][data-course]`
  or `[data-state][data-home]`, and the tests count `li.path-card`,
  `li.planned-slot`, `.slot-label`, and `section.level3`: the atlas uses
  none of those names, so the index's filters and tests are unaffected.
- `site/search-index.py` leaves the path page out of the search index
  (`NOT_INDEXED`): adding the atlas to the page leaves the index unchanged.
- The built-site checks (scan, keyboard pass, reflow at three widths,
  payload, other origins, images, readable without scripts, internal links,
  determinism) run on every page, the path page among them.

## Decisions

1. **The manifest schema** (`site/atlas.yaml`), two lists and nothing else:
   - `concepts`: each `{id, area, position, slots, explanation}`. `id` is a
     lower-case hyphenated identifier; the display name of the concept is
     the identifier in words (hyphens to spaces, first letter upper case),
     so no title is written. `area` is a course id or a path id of the
     curriculum file. `position` is `[column, row]` in the area's grid
     (columns 1 to 2, rows 1 to 4), unique in its area. `slots` is a
     non-empty list of slot labels. `explanation` is one short text.
   - `connections`: each `{concepts, type, rationale}`: two different
     concept ids, a type of `same-mathematics`, `limit`, `same-method`,
     `application`, and a rationale. `limit` and `application` read in
     order ("A is a limit of B", "A applies B"); the other two are
     symmetric. A pair is listed once.
2. **The rules**, each a message of `atlas_problems` and a failing test:
   the top level holds exactly the two lists; an unknown field of a
   concept or a connection is rejected; a field the curriculum file or the
   front matter holds (`title`, `description`, `outcomes`, `prerequisites`,
   `lesson`, `lessons`, `state`, `count`, `kind`, `course`, `path`, and the
   rest of `_FRONT_MATTER_FIELDS`), an illustration reference, and a
   prerequisite are rejected with their own message; the connection types
   `prerequisite`, `requires`, and `capstone` are rejected as not
   curated; every area, slot, and concept reference resolves; a concept
   names at least one slot; a slot that is not a capstone slot has its
   home in the concept's area; a concept that names only capstone slots
   names exactly one (it represents that capstone); every capstone slot of
   the curriculum file is represented by exactly one concept; ids and
   positions are unique. A violation fails the build of the path page and
   the lesson source checks (`check_atlas` in the lesson checks, as the
   curriculum file is checked).
3. **Capstones.** The concept whose only slot is a capstone slot represents
   it; its explanation is the planned description, the one place that text
   lives (consistent with the roadmap's F80, F87, F88). A concept that
   names a capstone slot beside its own slots is a member of that capstone:
   capstone membership is derived from those associations. The reader
   `AtlasManifest.capstone(label)` serves F124 later.
4. **Derivation** (`Atlas`, from `LearningPath` and the manifest): a
   concept's own slots are its slots minus the capstones it is a member
   of; its lessons are the published lessons that fill them, in teaching
   order; its state is published (every own slot filled), partly published,
   or planned (none); its count is the number of its lessons. Prerequisite
   edges: from concept B to concept A when a lesson of A requires a lesson
   of B (A different from B), with the lesson pairs that make it, ordered by
   the manifest. Capstone membership: from each member to the capstone's
   concept; the capstone's lesson is linked only when published. Conceptual
   connections from the manifest.
5. **The drawing**, one inline SVG at its natural size (1152 by about 1500
   user units), laid out in Python like the graph of F26, deterministic:
   Part A as eight course areas in two rows of four (thin rule, the course
   title, its illustration at the top right), each with a 2 by 4 grid of
   concept nodes at the manifest's positions; Part B below as four path
   lanes joined by one rail line (the connected layer), each lane with its
   title and its concepts; the view layer below as a band per method (Lean
   first, "Formal proofs"), each listing its lessons as links. A concept
   node is a link to its panel (`#concept-<id>`) with its name and its
   state in words ("3 lessons", "1 lesson, 2 planned", "planned"); a
   planned node has a dashed outline, italic name, and the word planned; a
   capstone node a double outline and "capstone project, planned". Edges
   routed at right angles along the gutters between the nodes and the
   areas, never across a node or an area's title, each on its own track
   (triage of review 02, M1): prerequisite solid with a filled arrowhead, conceptual
   dashed without a head and with open circles at both ends, capstone
   membership dotted with an open diamond at the capstone: three dash
   patterns and three markers, never colour alone. No raster, no geography:
   the areas are a grid in the curriculum's order.
6. **The page.** In `site/path/index.qmd`, before `## Choose a physics
   course`, a cell prints `course_atlas()`: the breadcrumb (Home, then the
   page), the switch (`#atlas-map` map, `#choose` course index), `##
   Course atlas {#atlas}` with a short explanation and the counts, the
   legend, the map in a focusable region that scrolls sideways (wider than
   the text column on a desktop, Quarto's `column-page`), the capstone
   projects, the concept panels (native `<details id="concept-<id>">`, each
   with the explanation, its slots with their state, its lesson links, its
   conceptual connections with rationale, its prerequisite edges, and its
   capstone membership), and the visually hidden textual equivalent. The
   F64 content after it is unchanged. Quarto's title block stays (no copied
   template), so the breadcrumb follows the title.
7. **No script** in this feature (F126 adds them); `learner/path.js` opens
   a panel a link points to, as it opens any disclosure.

## Steps

1. This plan; the handoff note.
2. Failing tests first: `tests/unit/test_atlas.py` (the rules, the
   derivation, the drawing's links and marks, the textual equivalent) and
   the lesson source check.
3. `src/pbc/authoring/atlas.py`: the reader and validation, the
   derivation, the layout and the SVG, the illustrations, the page section.
4. The curation: `site/atlas.yaml`.
5. The page: `site/path/index.qmd`; the CSS in `site/assets/site.css`.
6. Built-site tests: `tests/e2e/test_atlas.py` (reachability without
   scripts through the map and the index, the switch, the panels, the
   keyboard order and focus, the region on a phone, previous anchors).
7. Build the page, look at it at 1280, 768, 375 px, apply the skills'
   critique, take the screenshots into `.agents/run/239/screenshots/`.
8. Documentation: `docs/authoring.md` ("The course atlas"),
   `docs/atelier.md` (the atlas components, what the skills changed).
9. The full `./scripts/verify.sh`, last.

## Verification strategy

- Unit: each rule with a failing case; the real manifest valid; every
  course and path slot named by a concept and every non-capstone slot by
  exactly one (curation); counts equal to the lessons; prerequisite edges
  equal to those computed from the front matter; capstone links only for
  a published capstone (a fixture with a published capstone); planned
  nodes without a link; the textual equivalent naming every concept, edge,
  and lesson of the views; two renders byte-identical.
- Built site: the e2e tests above; the existing F64 and F26 tests
  unchanged; the generic checks of every page.
- No test of CSS values or of pixels (ADR 018 decision 6).

## Discoveries during the implementation

- Quarto's `column-page` overlaps the sticky table of contents in the right
  margin (Quarto's script collapses it into a toggle over the map, and
  without a script it would cover the map). The path page takes
  `body-classes: pbc-atlas`, and the contents in the margin stay at the top
  of the page (`position: static`) instead of following the reader; the
  map is 1120 units wide, which fits the page column at 1280 px.
- The derivation is cached per `Atlas` (`cached_property`): without it the
  section took 4 s to render; now 0.03 s.
- Chromium opens a closed panel when a link targets it; the page does not
  rely on it (the summary is at the target, and F126's script opens it).
- `site/search-index.py` already leaves the path page out of the search
  index, so the index is unchanged by the atlas.
- The capstone concepts' explanations avoid the word "planned": the state
  is derived, and the explanation stays right once a capstone is published.

## Open questions

None blocking. For the owner's review: the concepts, their grouping, and
the 25 or so conceptual connections are a first curation; the display name
comes from the identifier, so a concept name has no apostrophe and no
mid-name capital (the ids avoid proper nouns after the first word).

## Next action

Steps 2 to 8 are implemented; the full `./scripts/verify.sh` is the last
step. Then the independent review, including the review of the manifest's
concepts and connections as scientific claims, and the owner's approval of
`site/atlas.yaml` and the rendered review on the Issue.

## Accepted limitation (the owner, 2026-10-21, in the conversation)

Review rounds 2 and 3 found that the connections of the static map cross and
crowd one another. The owner reviewed the screenshots at three widths and
approved the structure (eight courses, four paths, concept cards, published
against planned), accepted the density and the crossings as a known visual
limitation of the static atlas in F125, provided that the three
relationship types are distinguishable, the relationships and their
directions are accurate, nothing is obscured or inaccessible, and the
textual equivalent stays complete; he did not want CSS-based selection, new
interaction states or more routing infrastructure in F125 (selection is
F126's scope), and asked for the improvement of readability through
selection and focused highlighting to be an explicit acceptance
consideration of F126. Documented in docs/atelier.md; recorded on #239 and on
the Issue of F126.
