# Plan: F124, the home page of the atelier (Issue #238)

Source: Issue #238 (the authority on what is delivered) and the owner's
comment on it (2026-10-20: the home page is too text-heavy; keep this
feature's scope, take over nothing of F123, F125 to F127); requirements
decision 36 ("Home page") and the owner's answer of 2026-10-17 (a static
figure from an existing verified implementation); ADR 018 decision 4 (the
home page) and decision 6 (review); ADR 016 decision 2 (the figure-writing
pattern); ADR 013 (the curriculum file); `docs/atelier.md`; the map
manifest of F125 (`site/atlas.yaml`, `AtlasManifest.capstone`).

Context: base `origin/main` at `e4e4d94` (F125 merged, pull request #247).
No plan existed; the implementer wrote this one in the unattended session,
so the owner reads it with the pull request.

## Goal

The home page of decision 36: the shared header; the opening "Build a
world. See if it obeys physics." with a static figure drawn by a verified
implementation, its status, alt text, and provenance; the introduction with
the three activities as the project goal; Part A and Part B from the
curriculum file and the front matter with links into the atlas; the
capstone projects from the manifest; the invitation; the shared footer.

## Acceptance criteria and their gates (ADR 020 decision 2)

| # | Criterion (short) | Gate |
|---|---|---|
| 1 | The structure; no "From a question to a working model", no numbered formula | implementation (tests); confirmed in review |
| 2 | The figure: executed cell, `src/pbc` function over a verified implementation, status, alt, provenance, byte-stable, no script; the plan records the implementation and its validation | implementation |
| 3 | Counts and names from the metadata; planned labelled and unlinked; capstone text only the manifest's; thermal capstone hypothetical | implementation |
| 4 | Without JavaScript, the scan, reflow at 320 px, payload | implementation (the built-site checks of the full run) |
| 5 | A reviewer confirms every sentence about the site is true | implementation (the independent review) |
| 6 | The rendered review: implementer's screenshots and the skills' effect (implementation); the reviewer's assessment and the owner's pass on the Issue (owner_approval, pending) | implementation / owner_approval |
| 7 | The full verification run passes | implementation (local), pr_ci |

## Risk classification (ADR 020 decision 1)

Level 3 by assessment. Paths: `site/index.qmd`, `site/assets/site.css`,
`src/pbc/authoring/home.py`, `src/pbc/mechanics/experiments/home_opening.py`,
tests, `docs/authoring.md`, `docs/atelier.md` (path minimum 2; no protected
path). Triggers: the page removes the section "One result, constructed and
proved", whose statements (the energy of a mass on a spring, the drift a
simulation shows, the factor of one explicit Euler step settled by a proof)
are scientific claims that `main` publishes; existing tests are changed
(the F25 home tests, the equation test of `tests/e2e/test_built_site.py`
moved from the home page to the first lesson, which has display
equations). The approval request is `.agents/approvals/238.md`; the last
verification is the full `./scripts/verify.sh`.

## Visual deliverables and skills

| Deliverable | Class | Expected artifact | Scientific validation | Accessible fallback |
|---|---|---|---|---|
| The home page (opening, sections, lists, capstone boxes) | page or layout | `site/index.qmd`, the generated parts of `pbc.authoring.home`, the home rules of `site/assets/site.css` | the counts and states come from the data and are tested | readable without scripts; one column below 992 px; reflow at 320 px |
| The opening figure | scientific figure | `fig-opening`, drawn by `draw_opening` of `pbc.mechanics.experiments.home_opening` in an executed cell | see "The figure" below | the alt text, the caption, and the note with the run's numbers |

The page:

Skills: impeccable@08d5b470, frontend-design@dbd4588f

The figure:

Skills: pbc-scientific-visualization@a70b5016

The visual revision (the owner's decisions below) adds interface artwork:

| Deliverable | Class | Expected artifact | Scientific validation | Accessible fallback |
|---|---|---|---|---|
| The tsunami wavefronts beside the featured capstone | interface artwork (generated) | `pbc.authoring.home_artwork`, written into the built site at `assets/home-wavefront.svg` by `site/home-artwork.py`, registered with its module in `site/assets/provenance.yaml` | none claimed: no axis, scale, number, or measurement label; labelled conceptual artwork for a planned capstone; a unit test checks the drawing has no text but its title | the alt text names what it is |
| The course illustrations of Part A | interface artwork (reused, F125's `ILLUSTRATIONS`) | inline SVG, decorative | unchanged from F125 | `aria-hidden`; the course name stands beside it |

Skills: impeccable@08d5b470, frontend-design@dbd4588f

No conceptual diagram is added:

Skills: none (no conceptual diagram; diagram-design does not apply)

## The figure

- **Implementation**: `pbc.mechanics.chaos.double_pendulum` and
  `double_pendulum_energy` (F68), stepped by `rk4_step`.
- **Why its validation suffices**: the lesson "The double pendulum and
  chaos" and its tests check that the equations reduce to the single
  pendulum when the second bob is light, that small oscillations have the
  periods of the two normal modes in closed form (to 1e-3), that the energy
  is kept by a small step, and the Lagrangian lesson derives the same
  equations symbolically (`tests/unit/test_lagrangian.py`,
  `test_the_lagrangian_double_pendulum_is_the_closed_form`). The figure
  shows the motion itself, not a statistic of it.
- **What the figure adds to make it faithful**: a chaotic motion is only
  step-independent for a while. At the lesson's step (0.01 s) the run parts
  from a run at half the step by 1 mm after about 6.8 s, so the figure
  follows the lesson's chaotic start (both rods at 2 rad, at rest) for
  10 s at 0.002 s, where the half-step run stays within 2e-5 m and the
  energy within 1e-7 of its start; a test bounds both (1e-4 m, 1e-6), and
  the page states the computed values.
- **Form**: two panels, the path of the second bob with the pendulum at the
  start and the end, and the relative change of the energy against time;
  `FIGURE_COLOURS` and the page's ink and muted; status `simulated`; the
  module and the commit stated beside it; the numbers from the run.
- **Byte-stable**: `pbc.experiment.encode`; a unit test compares two runs
  and the command's file, and a built-site test compares the served image
  with the module's bytes. No script computes or animates it.
- The module is a separate module in `pbc.mechanics.experiments`, beside the
  lesson's, so the lesson and its experiment are unchanged.

## Decisions

1. The title of the page is the opening line; `pagetitle` keeps the site's
   name in the browser's title.
2. The F25 sections "Three activities", "One result, constructed and
   proved", "Published", "Planned", and "Source and licence" are replaced:
   the activities become one paragraph with their examples; Part A and
   Part B carry the published and planned counts (the derived lists); the
   per-strand list of every lesson is left to the atlas and the course
   index, which the page links (the owner: too text-heavy); the licences
   and the secondary navigation are in the footer of F123; the repository
   link stays in the introduction.
3. A course or path with no published lesson is planned: labelled, never
   linked, also into the atlas (the index has no section for it).
4. A capstone shows its course, its state, and only the manifest's
   explanation (which names the project); the curriculum's slot title is
   not shown, so no second description exists.
5. No script, no animation (F128).

## Steps

1. This plan; the handoff note.
2. `home_opening.py` and `tests/unit/test_home_opening_experiment.py`.
3. `pbc.authoring.home` extended; `tests/unit/test_home.py` adapted.
4. `site/index.qmd`; the home rules of `site/assets/site.css`.
5. The built-site tests: `tests/e2e/test_home.py` adapted; the equation
   test moved; `tests/integration/test_home_build.py` adapted.
6. Build the page, look at it at 1280, 768, 375 px, apply the skills'
   critique; screenshots into `.agents/run/238/screenshots/`.
7. Documentation: `docs/authoring.md` (the home page bullets),
   `docs/atelier.md` (the component, what the skills changed).
8. The full `./scripts/verify.sh`, last.

## Verification strategy

- Unit: counts per course and path against `LearningPath`; planned rows
  without links; the capstone blocks equal to the manifest's explanation
  and nothing else, planned, unlinked, and linked once published (a
  fixture); no numbered or step headings; the provenance with the module
  and the commit; the figure's step independence, energy, rods, and bytes.
- Integration: the home page built in a minimal project follows the lessons.
- Built site: the order of the sections; the figure's bytes, status, alt,
  dimensions, and provenance; the atlas anchors the page links exist; the
  generic checks of every page (scan, reflow, payload, no script needed).

## Owner's design decisions for the visual revision (2026-10-21, in the conversation)

This section records the owner's approvals (the owner reviewed ADR 018 and decided that these editorial and visual-composition choices are consistent with ADR 018 decisions 2, 3, and 4 and need no new or amended ADR). Reference: the first rendered version of F124 compared with the approved visual concepts (hero with the double pendulum; featured courses; contrasting tsunami section); the mock-ups are visual references, not permission to invent working functionality.

1. **Provenance.** The detailed provenance and the energy plot sit in an accessible native disclosure below the main double-pendulum illustration; a concise scientific caption stays visible; the existing reproducibility information is preserved. (ADR 018 decision 4, the figure carries its status and provenance.)
2. **Featured physics courses.** Mechanics, Thermodynamics, and Waves are featured with richer illustrations, reusing F125's code-generated artwork where appropriate; the other five courses stay visible and accessible with accurate published and planned counts; planned content is never described as available. (Decisions 3 and 4.)
3. **Featured capstone.** The tsunami capstone is a distinctive full-width dark section. The editorial heading is "Model a wave. Understand a coastline.", followed by the existing approved description from the atlas manifest; the other two capstones are shown smaller; all three are clearly marked planned; the F125 manifest is not modified for home-page copy. (Decisions 3 and 4; ADR 018 decision 5, capstones may frame visualizations in dark navy.)
4. **Part B.** "Physics + AI" is an editorial section heading for Part B; the four official method-path names of the curriculum are preserved. (Decision 4.)
5. **Illustrations.** Code-generated, reproducible artwork consistent with ADR 018 decision 2. The tsunami is a conceptual wavefront illustration without invented quantitative scales, measurement labels, or claims of a working simulation, identified as conceptual artwork for a planned capstone, with its provenance registered. The double-pendulum hero uses the actual model parameters and trajectories; any quantitative annotation is subject to scientific review.

The three asset classes stay separate: the double-pendulum simulation is a verified scientific result with its status and provenance; the tsunami artwork is conceptual interface artwork for a planned capstone without invented data; the capstone descriptions come from the atlas manifest, with the editorial headings kept apart.

Boundaries: no interactive controls, no experiment gallery, no testimonials, no navigation entry to something that does not exist, nothing beyond F124. If the implementation finds a conflict with ADR 018, report the specific clause and ask for a decision; do not change the architecture or the scope silently.

Verification: focused tests during implementation, then the required independent review and one full final verification; fix rounds use the risk-proportionate checks the workflow permits and reuse valid evidence; no gate is weakened; where a rule requires a repeated full run, the exact requirement is stated. After implementation the rendered home page is shown at desktop, tablet, and phone width before the owner's final visual acceptance. The agent does not merge.


## Execution of the visual revision

1. `home_opening`: `fig-opening` is one square panel with the paths of both
   bobs (told apart by colour, width, and a direct label at each start);
   `fig-opening-energy` is the energy, its axis "relative energy change
   (dimensionless)". Both `simulated`, byte-stable, from one run.
2. `site/index.qmd`: a short lead; the caption visible; the provenance, the
   numbers, and the energy figure in a closed `<details>`; Part B headed
   "Physics + AI".
3. `pbc.authoring.home`: three featured courses (`FEATURED_COURSES`) with
   the atlas's illustrations, the counts, and the first lesson; the other
   five in a compact row; the paths as a layer; `FEATURED_CAPSTONE` (FL10)
   on the night ground under `FEATURED_HEADING`, then its course, state, and
   the manifest's explanation, beside the artwork and its label; the other
   two smaller.
4. The night tokens (`night`, `night-text`, `night-muted`, `night-line`) in
   `design.py`, `site.css`, and their contrast pairs.
5. `pbc.authoring.home_artwork`, `site/home-artwork.py` (post-render, the
   last), the register entry.
6. Tests: `tests/unit/test_home.py`, `test_home_opening_experiment.py`,
   `test_home_artwork.py`, `test_design.py`; `tests/e2e/test_home.py`.
7. Screenshots at 1280, 768, 375 px (and the disclosure open at 1280) in
   `.agents/run/238/screenshots/`; the docs (`docs/atelier.md`,
   `docs/authoring.md`); the full `./scripts/verify.sh`, last.

Level 3 stays (the assessment above); the revision adds two paths a
reviewer is told about: `site/_quarto.yml` (sensitive, the post-render
entry) and the shared tokens of `design.py` and `site.css`.
