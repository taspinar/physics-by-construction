# Plan: F126, the atlas interaction (Issue #244)

Source: Issue #244 (the authority on what is delivered) and the owner's
comment on it (2026-10-21: readability of the relationships through
selection and focused highlighting is an explicit acceptance
consideration); the change request `docs/changes/scientific-atelier-atlas.md`
sections 4 ("Course atlas at the existing path address", items 2 and 4,
the mobile rule), 5 ("Accessible interactions"), 8 (slice E);
requirements decision 36; ADR 018 decision 3; `docs/architecture.md`,
"The atlas at build time", the component row "Atlas modules", the budget
row of the map enhancement, I16 and I31; `docs/atelier.md`, "The course
atlas"; the plan of F125 (`.agents/plans/239-the-map-manifest-and.md`).

Context: base `origin/main` at `2d0d84a`; the branch held no work when
this plan was written (2026-10-22). No plan existed; the implementer
wrote this one in the unattended session, so the owner reads it with the
pull request.

## Goal

Small dependency-free ES modules in `site/learner/` that enhance the
generated atlas of F125 when scripts run: the switch, selection with the
selected-concept panel, modes that show concepts and the kinds of
relationship apart, zoom, filters coordinated with the index's filters,
and the phone's region selector with a focused view and an ordinary list.
They store nothing, request nothing, animate nothing; without them the
page is the page of F125.

## Acceptance criteria and their gates (ADR 020 decision 2)

| # | Criterion (short) | Gate |
|---|---|---|
| 1 | With JavaScript disabled nothing is lost: the F125 tests pass unchanged | implementation |
| 2 | No request, cookie, or storage while every control is operated (extended scan); `progress.js` the only script that stores | implementation |
| 3 | Every control by keyboard with visible focus and a label; accessibility scan; reduced motion | implementation |
| 3 | The screen-reader reading order recorded in the manual pass | owner_approval (pending) |
| 4 | Phone: region selector, focused view, list; reflow at 320 px; desktop and tablet labels at or above the minimum (test) | implementation |
| 5 | Payload of the enhancement measured and within budget; search the same with and without filters; F13, F14, F41 tests pass | implementation |
| 6 | Display label and navigation wording decided by the owner in the preview, applied with address and anchors unchanged | owner_approval (pending); the test over the previous addresses is F125's and passes |
| 7 | Rendered review: implementer's screenshots at three widths (implementation); reviewer's assessment (implementation, review); owner's pass over the preview (owner_approval, pending); skills and their effect recorded (implementation) | mixed |
| 8 | The full verification run passes | implementation (local), pr_ci |
| owner's comment | Selection or focus highlights a concept's prerequisites and connections with direction and meaning clear; structure visible by default; textual, keyboard inspection of the relationships; data unchanged; no graph framework or edge routing; tests and screenshots of the default map and a selected concept | implementation |

## Risk classification (ADR 020 decision 1)

Level 2: `site/learner/atlas.js` (new), `site/learner/path.js`,
`site/assets/site.css`, `src/pbc/authoring/atlas.py`, tests
(`tests/e2e/test_atlas_interaction.py` new, `tests/support/site_checks.py`
two new checks, `tests/unit/test_atlas.py` new tests), `docs/atelier.md`,
`docs/authoring.md`, this plan. No protected path (architecture and
roadmap already describe the feature and are not changed;
`site/_quarto.yml` is not changed, the label waits for the owner). No
trigger: no test, assertion, tolerance, or budget is changed or removed,
no dependency, no published scientific claim; the checks added only add
guarantees. Shared inputs (`site.css`, `src/pbc/authoring`, `tests/e2e`,
`tests/support`): the last verification is the full `./scripts/verify.sh`.

## Visual deliverables and skills

| Deliverable | Class | Expected artifact | Scientific validation | Accessible fallback |
|---|---|---|---|---|
| The atlas controls (region, show, zoom, filters), the selection states of the map, the selected-concept panel, the region's list, the phone view | page or layout | `site/learner/atlas.js`, the atlas rules in `site/assets/site.css`, the two placeholders written by `pbc.authoring.atlas` | none for the layout; which concepts and lessons a filter keeps and which relationships a selection shows come from the generated data attributes and edges, tested against `Atlas` | the page of F125: the map's links, the concept panels, the textual equivalent, the index |

Skills: impeccable@08d5b470, frontend-design@dbd4588f

No diagram is drawn or changed (the drawing of F125 stays as it is) and no
scientific figure is added:

Skills: none (no conceptual diagram and no scientific figure; diagram-design and pbc-scientific-visualization do not apply)

## Current state (inspected at 2d0d84a)

- `AtlasSection` writes the breadcrumb, the switch (three anchors), the
  legend, the map (`#atlas-map`, focusable region, inline SVG at 1120 by
  2202 units), the capstones, the concept panels (`details#concept-<id>`),
  and the textual equivalent; no script.
- The edges carry `data-kind`, `data-from`, `data-to` (and `data-type`
  for a conceptual connection); the nodes `data-concept` and
  `data-concept-state`; the lesson plates of the views `data-lesson`.
  Areas are `g.atlas-area[data-area]`; their boxes are 253 by 466 units,
  which fits a 320 px screen at natural size.
- `learner/path.js` (F64) builds the index's filter form in
  `#path-filters` (course, method, difficulty, state), hides rows
  `[data-state][data-course]`, `[data-state][data-home]`, and opens the
  disclosure a hash points into.
- The built-site checks require that content seen only with scripts is
  inside a declared enhancement (`[data-enhancement]` with an id) that has
  visible fallback content without scripts.
- The map's smallest label is the count and state line at 11.5 CSS px.

## Decisions

1. **One new module, `site/learner/atlas.js`**, and the coordination added
   to `path.js`; no import between them (a static import would be another
   module request), they talk by two document events:
   `pbc:filters` (path.js announces the index's filter values after it
   applies them) and `pbc:set-filters` (atlas.js asks path.js to take
   values). Each works alone.
2. **What the generator adds** (`src/pbc/authoring/atlas.py`), and nothing
   in the drawing's geometry, marks, or text:
   - on each concept node: `data-area`, `data-lessons` (its lesson ids),
     `data-planned` (the number of its planned own slots);
   - on each lesson plate of the views: `data-course`, `data-path` (the
     path of its slot, or empty), `data-methods`, `data-difficulty`, the
     attributes the index's rows carry;
   - two declared enhancements around the map: `#atlas-controls` before
     it and `#atlas-selection` after it, each with one visible sentence
     that is true without scripts;
   - the script element of `learner/atlas.js`.
3. **The switch** stays three links; the module marks the part of the page
   in view with `aria-current="location"` and moves keyboard focus to the
   target when a link is followed. The map and the index stay on the page
   together (the progress marks and recommendations of the index stay as
   they are).
4. **Selection.** Activating a node (pointer, Enter) selects its concept
   instead of jumping to its panel; Escape or the panel's close button
   clears it. Hover and keyboard focus preview the same highlighting. A
   selection marks the node, its edges of the kinds shown, and the
   concepts at their other ends; every other node and edge is muted (not
   hidden). Direction and kind stay what the static drawing shows
   (arrowhead, dash pattern, end marks of the legend); the meaning is
   written in the panel. Nothing is drawn or routed anew.
5. **The selected-concept panel** (`#atlas-selection`, after the map, kept
   at the bottom of the screen while the map is in view): the concept's
   name and state, its explanation, and the facts of its F125 panel
   (slots and lessons, connections with type and rationale, builds on,
   needed by, capstone), copied from the panel in the page; a concept link
   in it selects that concept (the keyboard way through the relationships,
   with focus on the panel's heading); a link to the full panel; a close
   button. A status line names the selection and its counts.
6. **Modes** (radio buttons "Show"): all relationships (the default, as
   without scripts), concepts only, prerequisites, conceptual connections.
7. **Zoom**: zoom out, zoom in, actual size, with the level as text; the
   levels 100, 125, 150, 200 %; the map never goes below its natural size
   (zoom out stops at 100 %), so its labels never shrink; the keys +, -,
   0 work while focus is in the map. The scroll position keeps the centre.
8. **Region selector** (a native select): the whole map, each course, each
   path, the Lean and method views. A region shows at the current zoom in
   the map box (the SVG's viewBox cut to the region), the rest of the map
   hidden from sight, the tab order, and assistive technology; under the
   map an ordinary list of the region's concepts (each selects it) and a
   link to the region in the course index. On a screen narrower than 40em
   the map opens focused on the first course; the whole map is one choice
   away.
9. **Filters** (course, path, method, difficulty, publication, "Show all",
   a status line) in the map's controls, mirrored with the index's form:
   changing either changes both. A concept matches when one of its
   lessons or one of its planned slots matches all filters; a lesson plate
   when its lesson does; what does not match is muted, not removed. In the
   index a path filter keeps the lessons of the path wherever they are
   listed, and its planned slots. The search index is built from the page
   at render time and does not change.
10. **No motion**: no transition or animation is added; scrolling into
    view is instant.

## Steps

1. This plan; the handoff note.
2. Failing tests: unit tests of the new attributes and placeholders;
   `tests/e2e/test_atlas_interaction.py`; the source scan and the
   storage and request check of the atlas modules in
   `tests/support/site_checks.py`.
3. The generator changes; `site/learner/atlas.js`; `path.js`.
4. The CSS.
5. Build the site, run the e2e tests of the atlas, the path, the learner
   state, the recommendations, and the generic checks on the path page.
6. Look at the page at 1280, 768, 375 px; apply the skills' critique;
   screenshots of the default map and of a selected concept into
   `.agents/run/244/screenshots/`.
7. Documentation: `docs/atelier.md` (the atlas's controls, the skills'
   effect), `docs/authoring.md` (the attributes the modules read).
8. The full `./scripts/verify.sh`, last.

## Verification strategy

- Unit: the data attributes equal what `Atlas` derives (lessons, planned
  count, area; a plate's course, path, methods, difficulty); the
  placeholders and the script are in the section; two renders identical.
- Built site, with scripts: selection by pointer and keyboard with the
  related nodes and edges marked exactly as the edges in the page say;
  the panel's facts and links; Escape; the modes hide exactly the other
  kinds; zoom never below natural size and the keys; the region view and
  its list; the filters mark exactly the concepts and lessons the data
  says, and stay in step with the index's form; the switch; keyboard
  operation and visible focus of every control; the accessibility scan in
  several states; no running animation with reduced motion; reflow at
  320 px; the minimum label size at desktop and tablet; the payload of
  the modules measured apart; no request, cookie, or storage while every
  control is operated; the search the same with and without the filters.
- Without scripts: the F125 tests unchanged.
- No test of CSS values or of pixels beyond the label size and the focus
  ring width the issue names (ADR 018 decision 6).

## Discoveries during the implementation

- The built-site check "readable without scripts" accepts content that
  only a script shows when it sits in a declared enhancement with an id and
  visible fallback content in the static page. Hence the two placeholders
  with a true sentence each, and no words drawn into the SVG on a
  selection: the map is not a declared enhancement, so a selection changes
  classes only, and its words are in the panel.
- Quarto's page script makes the in-page links before the map absolute
  (the switch's among them) and then stops with an error on the SVG links
  of the map (`links[i].href.replace is not a function`; present since
  F125, not changed here). The module therefore reads a link by its path
  and hash, never by an `href` that starts with `#`.
- The first render docked the panel at 45 % of the screen and hid the very
  marks a selection shows; it takes a third now, with the explanation
  beside the facts from 48em, and the page scrolls so that the chosen box
  stays above it.
- At 320 CSS px the map box is 263 px wide and an area 253 units: a focused
  region keeps a margin of 3 units so that it fits at its natural size.
- `measure_payloads` takes an optional list of pages, so that the payload
  of the path page is measured on its own (the default, every checked
  page, is unchanged).

## Open questions

None blocking. For the owner's preview: the display label ("the atlas" or
another) and the navigation wording (criterion 6); the label stays
"Learning path" until then.
