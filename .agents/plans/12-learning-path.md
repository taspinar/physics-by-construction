# Plan: Issue #12, F03 — Learning path

- Issue: #12 (source: `docs/roadmap.md`, F03)
- Branch: `feature/12-learning-path`
- Base commit: `db4e4a3`
- Risk: Medium (Quarto validates no custom metadata; the generation and
  validation code is project-owned)
- Governing documents: `docs/architecture.md` ("Lesson model": the path is
  derived from lesson front matter, there is no second list; verification
  step 4 lists the prerequisite graph among the lesson source checks),
  ADR 001 (path links must work without JavaScript; the path page and lesson
  headers need project-owned generation), ADR 002, the F02 plan
  (`7-lesson-format-and-the.md`, which deferred path validation, headers,
  and previous and next links to F03)

## Goal

Make the ordered learning path visible everywhere: a path page that lists
strands in order and, within each, lessons with order, difficulty, and
prerequisites; and on every lesson a header with its strand, position,
difficulty, linked prerequisites, and previous and next links. All of it
generated from lesson front matter and validated by a check.

## Current state at the base commit

F02 is merged: the lesson format with its source checks (`tests/support/
lesson_checks.py`), the built-site checks, one lesson (M1), the authoring
guide and template. Each lesson is validated on its own; nothing relates the
lessons to each other. The home page carries a hand-maintained list of
lessons. `STRANDS` and `DIFFICULTIES` are tuples of ids and numbers in the
check module; the scale has no names or explanation.

## Design

### Where the path is generated

| Decision | Reason |
|---|---|
| One module, `pbc.authoring.path`, defines the strands (id, title, description, in path order) and the difficulty scale (level, title, description), reads the front matter of every lesson, orders the lessons, validates the path, and renders the path page and the lesson header as Markdown | "One difficulty scale defined in one place": the pages render the definition and the checks validate against it (`lesson_checks.STRANDS` and `DIFFICULTIES` are derived from it). Validation and generation share one reading and one ordering, so they cannot disagree |
| The pages are produced by executed cells: `learning_path()` in `site/path/index.qmd`, `lesson_header()` as the first cell of every lesson | The mechanism F02 established for `excerpt()` and `reproduce_this()`: the page shows what the build read from the repository (ADR 002). A Lua filter would need the path logic a second time in Lua; a pre-render script would write a generated file into the source tree |
| A helper finds its website project by walking up from the directory the cell runs in (`pbc.authoring.website.project_root`, shared with `reproduce_this`) | The same page then builds in the checkout, in the copy the determinism check makes, in the copy of the template test, and in a learner's clone |
| The path page cell prints with `output: asis` | The strand sections must be top-level sections of the page, so they get anchors the lesson header links to (`path/index.html#mechanics`) and appear in the table of contents. A cell result sits inside the cell's output div, where Quarto gives it no table of contents entry |
| The header is a definition list (Strand, Difficulty, Prerequisites, Previous, Next) with links, at the top of the lesson, before the introduction | Plain HTML, read in order by assistive technology, works without scripts; previous and next are part of the header the Issue asks for. The source check requires the cell before the first heading |
| The home page links to the path page instead of listing lessons | Acceptance criterion 1: no hand-maintained list. The navbar gets a "Learning path" entry |
| A strand appears on the path page only when it has a lesson; the page's prose names the planned strands | Acceptance criterion "a strand appears only when it has a published lesson" |
| `pyyaml` moves from the dev group to the runtime dependencies of `pbc` | `pbc.authoring` now reads YAML front matter when a page is built; the declared dependencies stay honest. `uv.lock` changes by those two lines only |

### Validation

`pbc.authoring.path.problems(lessons)` returns every violation, attributed to
a lesson page:

| Rule | Message |
|---|---|
| Unique ids | `lesson id 'x' is already used by <page>` (on the later lesson) |
| Orders of a strand run from 1 without gaps | `'lesson.order' is 3, but strand 'mechanics' has no lesson with order 2` |
| Orders of a strand have no duplicate | `'lesson.order' 2 is already used by <page>` |
| Prerequisites exist | `prerequisite 'x' is not the id of any lesson` |
| Prerequisites come earlier in the path | `prerequisite 'x' does not come earlier in the learning path` |
| No cycle | `prerequisites form a cycle: a -> b -> a` (once per cycle, on its first member) |

A cycle always also violates "earlier"; it is reported by name because the
Issue lists it as a rule and the message says which lessons form it.

`lesson_checks.check_path` runs these as rule `path` in `lesson-checks`
(verification step 4), on the lessons whose front matter passes
`check_metadata`, so one mistake is reported once. `LearningPath.read` raises
with the same messages, so a page build fails on an inconsistent path too
(`site-build`).

### Built-site checks

- `tests/e2e/test_learning_path.py`: without JavaScript, a crawl from the
  home page reaches the path page and every lesson; the path page explains
  every level of the scale and lists each strand's lessons in order with
  links, difficulty, and prerequisites, and has no section for a strand
  without lessons; every lesson header shows the strand and position,
  difficulty, prerequisites, previous and next, with links to the expected
  pages. The expected values come from `LearningPath.read` on the sources;
  the module's own ordering and validation are unit-tested with explicit
  expectations.
- `check_no_horizontal_scroll` now runs at phone, tablet (768 px), and
  desktop width (criterion 4). The accessibility scan already covers every
  page, so the path page (criterion 5); a guard test asserts the page exists.

### Other changes

- `tests/integration/test_lesson_checks.py`: a second lesson fixture; cases
  for every path rule at check level, and through the `lesson-checks` command
  for the four named in criterion 2 plus a lesson without the header cell.
- `tests/integration/test_lesson_template.py`: the lesson made from the
  template joins the path (header says "lesson 2 of 2", path page lists
  both).
- `site/assets/site.css`: the header as a boxed list; two columns from
  576 px.
- `docs/authoring.md`, `docs/development.md`, `docs/project-map.md`,
  `scripts/verify.conf` comment.

## Discoveries during implementation

| Finding | Resolution |
|---|---|
| Headings inside a cell result are sectioned but get no table of contents entry | The path page cell prints with `output: asis` |
| A duplicate id must not merge the prerequisites of both lessons into one graph node, or it reports a spurious cycle; and the position a prerequisite refers to is the first lesson with that id | `problems` keys the graph and the positions by the first lesson with each id |
| Python 3.14: `ruff` wants `except A, B:` without parentheses and no quoted forward references | Followed |

## Deliberately not done

- **Previous and next links at the end of the page as well.** A filter can
  only append inside the last section ("Reproduce this"), because Pandoc
  makes the sections after all filters; a placement outside `main` needs a
  template partial. The header at the top carries the links; a footer
  navigation is a possible follow-up.
- **Strand titles and descriptions in `_quarto.yml`.** The definition could
  live in site configuration, but then the Python check and the generator
  would each read it; one Python definition is the smaller design.
- **Progress, recommendations, search**: out of scope (Issue).

## Steps

1. `pbc.authoring.path` and `pbc.authoring.website`; unit tests. Done.
2. `lesson_checks.check_path`, header-cell rule in `check_sections`;
   `tests/lessons` and `tests/integration` cases. Done.
3. Site: path page, navbar, home page, header cell in M1 and the template,
   styles. Done.
4. Built-site checks: `tests/e2e/test_learning_path.py`, widths. Done.
5. Docs. Done.
6. `./scripts/verify.sh`; evidence below.

## Verification evidence

2026-10-07, macOS (Darwin 24.6) on Apple M1 Max, working tree on base
`db4e4a3` (uncommitted; `finish-feature.sh` creates the commit).

`./scripts/verify.sh`: **Verification passed**, 14 of 14 checks `PASS`. The
workflow self-tests were reported as `SKIP`: no workflow script differs from
`origin/main` (the only change under `scripts/` is a comment in
`verify.conf`). No file changed after the run except this plan.

| Check | Result |
|---|---|
| `unit-tests` | 67 passed, 2.3 s (29 of them `test_learning_path.py`) |
| `lean-build` | passed; axiom audit of 1 declaration |
| `check-tests` | 187 passed, 136 s |
| `lesson-checks` | 7 passed, 0.4 s |
| `site-build` | 5 pages, including `path/index.html` |
| `site-checks` | 29 passed, 26 s |
| `determinism` | two builds byte-identical, 28 files |

Per criterion:

| # | Evidence | State |
|---|---|---|
| 1 | `site/path/index.qmd` holds prose and one cell; the header of M1 and of the template is one cell; `site/index.qmd` has no lesson list. `tests/integration/test_lesson_template.py` builds a copy of the site with a second lesson made from the template and finds it on the path page and in its own header ("lesson 2 of 2", link to M1) without any other edit. `check_sections` requires the header cell, so no lesson can carry a hand-written header | met |
| 2 | `tests/integration/test_lesson_checks.py::test_lessons_that_do_not_form_a_path_are_reported` at check level (duplicate id, unknown prerequisite, cycle, later prerequisite, gap, duplicate order) and `::test_verification_fails_on_a_violating_lesson` through the `lesson-checks` command of `verify.conf` for the four rules the criterion names (exit status 1, `[path]` in the output). `tests/unit/test_learning_path.py::test_reading_an_inconsistent_site_fails_with_every_problem`: the page build raises on the same input | met |
| 3 | `tests/e2e/test_learning_path.py::test_every_lesson_is_reached_from_the_home_page_without_javascript` crawls the links of the built site with scripts disabled from `index.html` and reaches the path page and every lesson; `::test_lesson_header_shows_the_facts_of_the_path_with_links` asserts the previous, next, and prerequisite links of every lesson point to the expected pages, with scripts disabled | met |
| 4 | `check_no_horizontal_scroll` runs on every page at 320, 768, and 1280 px, with and without scripts (`test_pages_do_not_scroll_sideways_at_phone_width`); `test_page_wider_than_a_phone_or_a_tablet_is_reported` shows the tablet width is checked; `test_the_site_has_lessons_and_a_path_page` guards that the path page is among the pages | met |
| 5 | `test_wcag_scan_finds_no_violation` on every page at both widths, with the same guard. One finding during implementation (link contrast on a grey header background) was fixed by dropping the background | met |

Manual look at screenshots of the header and the path page at 320 and
1280 px: the header reads as two columns on desktop and as a stacked list on
a phone; the path page lists the scale and the mechanics strand; the navbar
entry "Learning path" stays on one line.
