# Plan: F37 lesson metadata and course navigation (Issue #43)

Source: Issue #43, ADR 008, docs/architecture.md "Lesson model".

## Schema
`lesson.course`, `lesson.methods`, `lesson.outcomes`, `lesson.related` are
required keys under `lesson` (an empty `related: []` is allowed). Vocabularies
`COURSES` (`mechanics`) and `METHODS` (the six of ADR 008) in
`pbc.authoring.path`. `path.problems()` validates: course in `COURSES`,
methods non-empty/known/unique, 2 to 5 outcomes, related exists, is not the
lesson itself and not among its prerequisites. The schema check in
`tests/support/lesson_checks.py` validates the shape; `check_path` feeds the
same `problems()`.

## Migration (front matter only)
| lesson | methods | related |
|---|---|---|
| M1 kinematics | simulation | proving-what-the-simulation-showed |
| M2, M3 | simulation | M3: agent-experiment |
| M4 harmonic-oscillator | simulation | proving-what-the-simulation-showed |
| M5, M6, M8 | simulation | |
| M7 | simulation | particles-in-a-box |
| A1 agent-experiment | simulation, llm-agents | |
| particles-in-a-box | simulation, abm | |
| L1 proving... | lean | |

## Page layout
Path page: Difficulty, Order (what previous/next mean vs course order vs
prerequisites), Courses (one h3 per course: core lessons = lessons in the
course's own strand, extensions = the rest), Methods (one h3 per method that
has a lesson). Ids are `course-<id>` and `method-<id>`; strand sections are
gone, strand stays in URLs and order. Header rows: Course, Methods, Difficulty,
What you'll learn, Prerequisites, Related, Previous, Next.

## Sidebar
Omitted. Quarto's sidebar collapses behind a JavaScript toggle below the
large breakpoint, and a per-course sidebar would need a hand-maintained list
in `_quarto.yml` (auto contents sort by path, not by course). The header and
the path page give the course navigation without JavaScript.
