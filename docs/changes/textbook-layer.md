# Change request: a textbook layer on top of the curriculum

Date: 2026-11-03. Owner: Ahmet Taspinar. Written with the agent after the audit of the site and of the 94 published lessons (2026-11-03) and the owner's review of the proposal. This is the input for one short planning change (`--change`, with `--grill` about the change only). The feature IDs below are the next free ones after F155; the planner confirms them.

## What I want

The site reads like a collection of lessons. I want it to read like one online physics textbook, without touching the scientific content, the curriculum, or the verification guarantees. The missing layer is the *educational narrative*: why the curriculum is organised as it is and how a course, a lesson, and a capstone contribute to a learning journey. It is neither the curriculum (which lessons exist) nor the editorial voice of a lesson (F114 to F116).

1. **A course or method path opens with an introduction**, like the first chapter of a textbook: why the subject matters, the central questions, what the reader learns, why the lessons come in this order, which method (numerical experiment or AI) is used and why, the capstone as the culmination, what comes next, and the prerequisites (linked, not copied).
2. **The Course Atlas opens with the learning journey** (from computational physics to AI-supported scientific investigation) before the cards.
3. **About explains the mission and the philosophy**; how results are verified stays on "How we verify the science".
4. **Home orients a first-time visitor**: identity, how physics is learned here (building models, predicting, measuring, interpreting), Part A and Part B, integrity last; and one consistent first step.
5. **The standard is introduced in phases**, not applied to 94 lessons at once.

## Decisions already taken

- **Planning change:** one short planning change, with `--grill` if the planner wants it. No new ADR. ADR 021 decision 4 is brought in line in the same cycle.
- **F127 is split.** The "course openings" leave F127 (they become the course introductions below); F127 keeps the reading-column rollout, the capstone template, and the supporting pages.
- **Hero.** The Home hero image is no longer the two constellations. It is one of a small set of existing Part A illustrations (computed interface artwork already in the provenance register): the double pendulum (classical mechanics), the vortex street (fluid dynamics), the hot and cold gas (thermodynamics), and the exoplanet transit (astrophysics), each made at hero size from its master. One fixed default (the double pendulum) stays in the HTML; a small script picks one at random per visit, independently of the headline pair, before the image is requested; a parameter forces one for tests; no storage, no request, no measurement of which works better. Every image has its own alt text and registration, and its own test. No animation. The owner confirmed on 2026-11-03 that the double pendulum is the default; the set of four stands as proposed, and the owner can still change it when the Home feature starts.
- **Start learning.** Two distinct actions, the same on Home and in the header: one to the Course Atlas, one to the first lesson of Part A. (The labels are for the Home feature.)
- **The phases** (the audit of 2026-11-03): phase 1 now, set the standard (F114 in place, F115, F116; the textbook structure on one Part A course and one Part B path); phase 2 during development, new lessons follow the standard and the introductions and existing lessons are improved per course when the course is content-stable; phase 3 at the end, one review of the whole material as a book.
- **No rewrite of the 94 lessons.** The audit's per-lesson suggestions are hypotheses, not defects; two real corrections (Issues #367 and #368) are handled separately.

## What this changes

- **Requirements.** Decision 40 (and the matching part of decision 41), "Home": the hero image, the limit of three sentences, and three example lessons with one capstone are replaced by the contents of the Home feature below. Nothing else of decisions 36 to 42 changes.
- **ADR 021** decision 4 (the hero image and the three sentences) is updated to match. No new ADR: this is a content and presentation decision inside ADR 018 and ADR 021.
- **Roadmap.** F127 loses its "course openings" and gains a note naming F156; five new features are added (below). F116 gains in its scope the two rubric additions of the audit (conceptual synthesis in the lesson review; the provenance of AI lessons stated at once: a model transcript, a written example, a recorded run, a tool replay, and an independent evaluation are different levels of evidence).
- **Not changed:** F114, F115, F132 to F134 (no work reopened), the curriculum, the lessons, the verification.

## The features

- **F156, course introductions: the source, the generator, and a pilot.** The editorial text of an introduction is held in one data file per sequence beside the atlas manifest; the generator writes the page; lessons, prerequisites, counts, the capstone, and published or planned come from the curriculum file and the front matter (no second lesson list). Pilot: Classical mechanics and the method path Scientific law discovery (published lessons). Each introduction is linked from the atlas panel and from the lesson header; a reference that does not resolve fails the build; a planned lesson is not a link and is not counted; the page is complete without scripts and readable at 320 px; the search index finds it; every lesson address, bookmark, and the learner state are unchanged. A short section on the editorial rules for pages that are not lessons is added to the editorial guide. Depends on F135 (merged) and not on F115.
- **F157, the learning journey: the Atlas introduction and About.** One source for the Part A and Part B text, used by the Atlas and About. The Atlas states how Part A leads to Part B, the expected background, that a route needs only the stated prerequisites, how a capstone fits, and the difference between numerical evidence, empirical evidence, and formal proof, without implying that an AI result is a discovery. About explains the mission and the philosophy, keeps the attribution to JIDAI and Ahmet Taspinar, and refers to "How we verify the science" instead of repeating it. Depends on F156.
- **F158, Home: orientation, the hero, and the first step.** The copy in the order identity, educational philosophy, curriculum (Part A, Part B), integrity, with no sentence limit; "What you can learn" explains Part A and Part B and shows at most one or two examples; the hero image is picked at random from the four Part A illustrations above, with the default in the HTML; the header and Home share the two actions. Depends on the planning change and F157; the hero is approved by the owner on the rendered page.
- **F159, introductions for the remaining sequences.** The other seven courses and the other method paths, in batches of about three, each batch after its sequence is content-stable and with the scientific review of a lesson feature; the Part B introductions follow F136. Lesson transitions are written only in new or revised lessons, never as a boilerplate paragraph on every page.
- **F160, the book review.** Planned last: the whole material is read as one book (transitions, terminology, references, figures, the learning progression) and only what needs it is corrected. No more detail than that at the planning stage.

## Order

Planning change, then F156, then F157, then F158 (the hero last), then F159 batches (the Part B introductions after F136), and F160 at the end. F115 and F116 run on their own course. F156 needs the files of `pbc.authoring` and the atlas; nothing else writes there in the meantime.

## Not in this change

New capstones, new lessons, a rewrite of existing lessons, a change of an equation or a verified output, a CMS, a backend, runtime AI content, new state or telemetry, the interactive pendulum (F128, still the owner's separate decision), and the legacy-format migration of `agents-llm/02` to `/04` and `mechanics/09` (a targeted Issue after F136, because F136 re-slots those lessons).

## Open for the planning

1. Whether the introductions' address is one new tree under the existing course path or a flat `/courses/<id>/` (the recommendation is the flat form).
2. Where the Part A and Part B text lives (the recommendation: beside `atlas.yaml`, validated like it).
3. Whether F160 gets its ID now or when F159 is nearly done.

## Material

The audit of the 94 lessons (`pbc_lesaudit_94_lessen_2026-11-03.md`) and the proposal of 2026-11-03 (`textbook-voorstel.md`), to be staged for the planning worktree under `docs/changes/textbook-layer/`.
