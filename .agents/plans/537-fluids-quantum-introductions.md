# Plan: F161, the course introductions of fluid dynamics and quantum physics (Issue #537)

Source: `docs/roadmap.md`, F161; Issue #537 (criteria 1 to 4 of F159 for
these two courses); the model of F159 (#519): `site/introductions/*.yaml`
and the thin page sources `site/courses/<id>/index.qmd`. Written by the
implementer at the start of the work (the Issue expects a short plan and
none existed).

Skills: none (text in the template of F156; the registered atlas
illustrations `atlas/fluids` and `atlas/quantum` are reused, no new visual).
Skills: none (pbc-physics-teaching not applicable: no lesson's teaching
changes; the owner's comment of 2026-11-15 says "change no lesson; an
introduction only").

Content-stable: the owner's decision of 2026-11-15 on the Issue.

## Steps

1. `site/introductions/fluids.yaml` and `site/introductions/quantum.yaml`,
   every section of decision 43, written from the curriculum file and the
   front matter and descriptions of the published lessons on main: every
   lesson named by `{slot:...}`, no count, no number or result that a lesson
   does not show. Quantum physics has no capstone project, and its
   capstone section says so (`docs/editorial-voice.md`, "Pages that are not
   lessons").
2. `site/courses/fluids/index.qmd` and `site/courses/quantum/index.qmd`,
   copies of the thin source of F159.
3. `tests/unit/test_introductions.py`: `BATCH_2` joins `INTRODUCED`; the
   assertion that `{sequence:quantum}` links to the atlas moves to a
   sequence still without an introduction (`astrophysics`); the lesson that
   shows no introduction link moves from FL1 to a lesson of a course still
   without one; a header test for a lesson of each new course. Changed
   assertions in an existing test: Level 3 (the owner's comment), with
   `.agents/approvals/537.md`.
4. Lessons: none revised (the owner's comment).
5. Verification: `./scripts/verify.sh --base` (the headers of every lesson
   of the two courses change), pytest of the introduction, atlas, header,
   and journey tests.
