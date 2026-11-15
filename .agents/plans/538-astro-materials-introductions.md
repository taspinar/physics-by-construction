# Plan: F162, the course introductions of astrophysics and of condensed matter and materials (Issue #538)

Source: `docs/roadmap.md`, F162; Issue #538 (criteria 1 to 4 of F159 for
these two courses); the model of F159 (#519): `site/introductions/*.yaml`
and the thin page sources `site/courses/<id>/index.qmd`. Written by the
implementer at the start of the work (the Issue expects a short plan and
none existed).

Skills: none (text in the template of F156; the registered atlas
illustrations `atlas/astrophysics` and `atlas/materials` are reused, no new
visual).
Skills: none (pbc-physics-teaching not applicable: no lesson's teaching
changes; the owner's comment of 2026-11-15 says "change no lesson; an
introduction only").

Content-stable: the owner's decision of 2026-11-15 on the Issue.

## Steps

1. `site/introductions/astrophysics.yaml` and
   `site/introductions/materials.yaml`, every section of decision 43,
   written from the curriculum file and the front matter, descriptions,
   and limits of the published lessons on main: every lesson named by
   `{slot:...}`, no count, no number or result that a lesson does not show.
   Neither course has a capstone project, and each capstone section says
   so (`docs/editorial-voice.md`, "Pages that are not lessons").
2. `site/courses/astrophysics/index.qmd` and
   `site/courses/materials/index.qmd`, copies of the thin source of F159.
3. `tests/unit/test_introductions.py`: `BATCH_3` joins `INTRODUCED`, so
   every test parametrized over it covers the two new introductions; a
   header test for a lesson and a lab of each new course; a test that each
   capstone section states that the course has no capstone project. No
   existing assertion or marker changes (Level 2).
4. Lessons: none revised (the owner's comment).
5. Verification: `./scripts/verify.sh --base` (the headers of every lesson
   of the two courses change), pytest of the introduction and atlas tests.

## Coordination

F161 (#537) runs in parallel on the same test file and moves two of its
"no introduction yet" cases to astrophysics (`{sequence:astrophysics}` and
the lesson `cosmic-expansion`). Whichever of the two merges second moves
those cases to a sequence still without an introduction (a method path,
such as `reasoning`).
