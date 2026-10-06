# Plan: Issue #7, F02 — Lesson format and the first mechanics lesson

- Issue: #7 (source: `docs/roadmap.md`, F02)
- Branch: `feature/7-lesson-format-and-the`
- Base commit: `e475377`
- Risk: Medium (the format is expensive to change once several lessons use it)
- Governing documents: `docs/architecture.md` ("Lesson model", "Verified
  display forms", invariants I5, I6, I18), ADR 001, ADR 002, ADR 004

## Goal

Define what a lesson is, enforce it with checks, document how to write one,
and prove it with lesson M1, "Kinematics as a program".

## Current state at the base commit

The F01 pipeline: Python package with one sample module, a Quarto site with
home, about, and rendering-check pages, built-site checks, and the
determinism check. No lesson, no lesson format, no `pbc.mechanics`, no
`pbc.authoring`.

## Design

### Lesson format

The format is specified for authors in `docs/authoring.md`; this section
records the decisions and their reasons.

| Decision | Reason |
|---|---|
| A lesson is `site/lessons/<strand>/<nn>-<slug>/index.qmd`; the directory holds nothing else | Architecture, "Lesson model". An allowlist per directory is the strongest form of "generated artifacts are never committed" |
| Lesson metadata sits under one front matter key, `lesson:` (`id`, `strand`, `order`, `difficulty`, `prerequisites.lessons`, `prerequisites.outside`, optional `lean-modules`) | The architecture fixes the fields and leaves the exact schema to F02. One key keeps them clear of Quarto's own options (`order`, `id`) and lets a filter or check read them as one mapping |
| Front matter allows only `title`, `description`, and `lesson`; unknown keys under `lesson` are rejected | A misspelt field must not pass silently, and a per-page `execute`, `freeze`, or `jupyter` option would undermine the display rules |
| `strand` and `order` must agree with the directory | The architecture has both the path and the fields; a check keeps them from drifting |
| Required sections are level-2 headings found by identifier: `assumptions`, `explanation`, `code`, `worked-examples`, `reproduce-this`, and `exercises` or `interactive-visualization`; none may be empty | Architecture, "Required sections, checked for presence". Identifiers give every lesson the same anchors while a heading may carry a title of its own (`## The program {#code}`) |
| Exercises are `.exercise` divs, each with a `.solution` div; `site/_filters/lesson.lua` numbers them and turns the solution into a closed `<details>` | ADR 001: solutions use `details`, no JavaScript. The filter runs `at: pre-ast`, because Quarto would otherwise turn `.solution` into its proof environment |
| The "not verified" marker is the class `not-verified` on a div or span; the filter writes the label into the page | The label is text in the page, so it is visible without styles or scripts and is read by assistive technology |
| The replay fixture location is the file `replay.json` next to the `index.qmd` of a lesson | ADR 002 asks F02 for one declared location. One file name is the narrowest exemption; F09 defines the content |

### Verified display forms for Python

| Form | Mechanism |
|---|---|
| Executed cell | A <code>```{python}</code> fence, options on `#\|` lines |
| By-reference excerpt | `pbc.authoring.excerpt(obj)`, called from an executed cell. It reads the source of a top-level function or class of `pbc` with `inspect`, and renders a highlighted listing that carries `data-source="<module>:<name>"`, followed by the file, the lines, and a link to them at the built commit |
| Values | Cell output, or an inline `` `{python} ...` `` expression |
| Figures | Drawn by a cell with a `fig-` label and `fig-alt` |
| Anything else | `.not-verified` |

`pbc.authoring` emits Markdown through `_repr_markdown_`, so it needs neither
IPython nor Quarto as a dependency.

### "Reproduce this"

`pbc.authoring.reproduce_this(code=[...], tests=[...])` writes the section
from an executed cell: the commit of the checkout (`git rev-parse HEAD`,
found from the location of the installed package, so it is the same in the
copy the determinism check builds), links to the page, code, and test files
at that commit, and the commands from `git clone` to
`uv run --locked quarto render <page>`. The page path is derived from the
directory the cell runs in. A checkout with uncommitted or untracked changes
is stated on the page; a build outside a Git checkout says the commit is
unknown.

### Checks

Lesson source checks: `tests/support/lesson_checks.py`, run on the
repository by `tests/lessons` as the new check
`lesson-checks: uv run --locked pytest tests/lessons`, placed before
`site-build` (architecture, verification step 4).

| Check | Rules |
|---|---|
| `check_metadata` | `metadata` |
| `check_sections` | `sections`: required and non-empty sections, exercise with solution, `reproduce_this()` in "Reproduce this" |
| `check_displayed_code` | `unverified-code`: any code block that is not an executed `{python}` cell (plain blocks in any language, indented blocks, raw `<pre>`, `eval: false`) without the marker; `include` and `embed` shortcodes. `cell-form`: another engine, options in the fence, a cell outside the top level, a div, or a list. `execution-disabled`: `execute` options in `_quarto.yml` that stop execution |
| `check_figures` | `figure-alt`: a declared figure cell without `fig-alt`. `figure-source`: an image file in the page |
| `check_committed_files` | `committed-artifact`: under `site/` and `src/`, build and cache directories and the file types of rendered pages, notebooks, figures, and stored outputs. `lesson-layout`: any other file under `site/lessons/` that is not a lesson page or a replay fixture. Lists the files Git tracks or would add (`git ls-files --cached --others --exclude-standard`), so an artifact is reported before `finish-feature.sh` commits it |

The body of a lesson is read through the Pandoc that Quarto ships
(`quarto pandoc --to json`), after rewriting Quarto's cell fences with
Quarto's own line pattern, because Pandoc does not know them. Headings,
identifiers, code blocks, and divs are therefore found where Pandoc finds
them, not by a second Markdown parser.

Built-site checks added to `tests/support/site_checks.py`, run by
`tests/e2e/test_lessons.py`:

| Check | Rules |
|---|---|
| `check_sections` | `lesson-page`: every lesson has a built page with the required sections |
| `check_not_verified_labels` | `not-verified-label`: every `.not-verified` element shows a label that says so, without scripts |
| `check_displayed_code` | `excerpt`: every listing with `data-source` is textually identical to the source file, read independently with `ast`. `unexecuted-cell`: no page shows a `{python}` cell or inline expression the build did not execute |
| Reproduce test, per lesson | The commands of the built page, run on a copy of the files Git tracks or would add, regenerate the page and its figure files byte for byte; the render takes less than 30 seconds |

### Lesson M1 and its code

`pbc.mechanics.kinematics`: `State`, `Trajectory`, `euler_step`, `simulate`,
`constant_acceleration`. The interface is deliberately small and specific to
kinematics (acceleration as a function of time); F04 defines the general
stepping interface.

The lesson derives the exact error of explicit Euler under a constant
acceleration, `x_n - x(t_n) = -a t_n dt / 2`, and shows it in executed code:
a ball thrown upward, the error against the time step, and a time-dependent
acceleration for which the observed order only tends to 1. Three exercises
with executed solutions. Every result on the page is cell output or an
inline expression; the values an example starts from are set in cells.

### Other changes

- `site/_quarto.yml`: the footer linked to `about.qmd` relative to each page,
  which breaks on a page in a subdirectory. It is now `/about.qmd`.
- `site/assets/site.css`: styles of the constructs; inline code inside a
  link had too little contrast on its grey background (found by the
  accessibility scan), so that background is dropped.
- `site/rendering-check.qmd`: one sample of each lesson construct, so the
  real site always carries an excerpt, both forms of the marker, and an
  exercise for the checks and for the cross-engine rendering check.
- `site/index.qmd`: a hand-maintained link to M1, until F03 generates the
  learning path.

## Discoveries during implementation

| Finding | Resolution |
|---|---|
| Pandoc reads a <code>```{python}</code> fence as inline code, not as a code block | The check rewrites cell fences before it calls Pandoc, with the pattern Quarto uses to find cells |
| Quarto does not execute a cell inside a block quote and shows it as inline code | Built-site rule `unexecuted-cell` |
| Quarto turns a `.solution` div into its proof environment before user filters run | `lesson.lua` runs `at: pre-ast` |
| A footer link in `_quarto.yml` is resolved relative to each page | `/about.qmd` |
| The theme's link colour on the background of inline code fails WCAG contrast | CSS, see above |
| Ruff 0.16 cannot read `.qmd` files | See "Deliberately not done" |
| Explicit Euler's leading error term vanishes for `a = cos t` near `t = 1.9` | The unit test of first-order convergence uses `t = 1` and also asserts the size of the error |

## Deliberately not done

- **Linting of lesson cells** (architecture, verification step 1; deferred
  by the F01 plan to "the lesson format and its checks"). The Issue lists
  the lesson source checks and this is not among them, and Ruff does not
  read `.qmd`. It needs an extraction step of its own. The cells of M1, the
  template, and the rendering-check page were checked once by hand with
  `ruff format` and `ruff check` on the extracted code; only the long `#|`
  lines of alternative text exceed the line length. Suggested as a follow-up
  Issue.
- **Path validation across lessons** (unique ids, prerequisites exist, no
  cycles, order without gaps): F03 by the roadmap. F02 validates each lesson
  on its own.
- **Lesson header with strand, difficulty, and prerequisites on the page,
  and previous and next links**: F03.
- **Validation of the content of `replay.json`**: F09. The exemption is by
  location only, as ADR 002 states.
- **`.gitignore`**: unchanged. It already ignores everything a build writes,
  and freeze and cache directories cannot appear while both are off; the
  committed-file check covers them if they ever do.
- **`tests/lessons/`** is a directory the architecture's layout sketch does
  not list; it names the lesson checks under `tests/integration/`. F01 made
  that directory the tests of the checks themselves (`check-tests`), so the
  checks on the real lessons have their own directory and their own check
  name, as the built-site checks have `tests/e2e`. No planning document is
  changed.

## Steps

1. `pbc.mechanics.kinematics` with unit tests. Done.
2. `pbc.authoring` (`excerpt`, `reproduce_this`, `build_commit`) with unit
   tests. Done.
3. Site: `lesson.lua`, styles, configuration. Done.
4. Lesson M1. Done.
5. Lesson source checks, `lesson-checks` in `verify.conf`, tests on violating
   lessons. Done.
6. Built-site checks for lessons, tests on violating pages. Done.
7. `docs/authoring.md`, `docs/lesson-template.qmd`, test that a lesson made
   from the template passes and builds. Done.
8. `docs/development.md`, `docs/project-map.md`, README, CONTRIBUTING. Done.

## Acceptance criteria that need the pull request or the reviewer

| Criterion | What is still needed |
|---|---|
| 1, "published" | The merge to `main`; then open the lesson at the Pages URL. |
| 4, Linux | The CI run of the pull request is the Linux run: it builds the page, runs the "Reproduce this" commands, and asserts the pinned rows of `KINEMATICS_REFERENCE`, which were produced on macOS. Docker was not running on the development machine, so no Linux run exists yet. |
| 8 | The reviewer follows `docs/authoring.md`. |

## Verification evidence

2026-10-06, macOS (Darwin 24.6) on Apple M1 Max, working tree on base `e475377`
(uncommitted; `finish-feature.sh` creates the commit).

`./scripts/verify.sh`: **Verification passed**, 29 of 29 checks `PASS`,
including the workflow self-tests, which ran because `scripts/verify.conf`
changed. Wall time about 27 minutes; most of it is the self-tests, which are
slow in the Rosetta shell of this machine, and the first fetch of the Mathlib
cache in this worktree.

One qualification: three files changed while that run was in its `lean-build`
check, after `lint`, `format`, and `unit-tests` had passed and before every
later check started: `site/assets/site.css` (wrapping of file paths in
links), `tests/e2e/test_lessons.py` (the test for it), and one message in
`tests/support/lesson_checks.py`. `ruff check .`, `ruff format --check .`,
and `pytest tests/unit` were run again on the final tree and pass. No file
changed after the run except this plan.

| Check | Result |
|---|---|
| `unit-tests` | 38 passed, 2.5 s |
| `lean-build` | passed; axiom audit of 1 declaration |
| `check-tests` | 164 passed, 128 s |
| `lesson-checks` | 6 passed, 0.4 s |
| `site-build` | 4 pages; the lesson executes 13 cells |
| `site-checks` | 25 passed, 21 s |
| `determinism` | two builds byte-identical, 27 files |

Per criterion:

| # | Evidence | State |
|---|---|---|
| 1 | `tests/e2e/test_lessons.py`: built page with every required section; linked from the home page | built and checked; publication needs the merge |
| 2 | `tests/integration/test_lesson_checks.py`, at the level of the check functions and again through the `lesson-checks` command of `verify.conf` (`test_verification_fails_on_a_violating_lesson`): missing metadata field, missing required section, Python block without the marker, figure without alt text, committed generated figure. `test_file_at_the_replay_fixture_location_is_accepted`, and `test_recording_anywhere_else_is_reported` for the same file elsewhere | met |
| 3 | `test_excerpts_are_identical_to_their_source_and_every_cell_ran` on the built site, with `test_the_first_lesson_shows_its_program_by_reference` so it is not vacuous; `test_excerpt_that_differs_from_its_source_is_reported` on violating pages | met |
| 4 | `test_reproduce_commands_regenerate_the_page_within_the_time_budget`: the commands of the built page regenerate the page and both figures byte for byte. `test_reproduce_section_names_the_built_commit`. `test_the_first_lesson_displays_the_same_numbers_on_every_platform` pins the displayed rows | met on macOS; Linux is the CI run of the pull request |
| 5 | Results are cell output or inline expressions; `tests/unit/test_kinematics.py::test_euler_matches_the_closed_form_within_its_known_error` (tolerance 1e-11) and `::test_error_halves_when_the_time_step_halves` (order within 0.01 of 1) | met; "every numerical claim" is for the reviewer to confirm by reading |
| 6 | Existing built-site checks on all pages (readable without JavaScript at 1280 and 320 px, axe-core scan), `test_the_first_lesson_shows_mathml_results_and_figures`, `test_solutions_open_without_javascript`, render time under 30 s asserted in the reproduce test | met |
| 7 | `test_material_marked_not_verified_shows_a_label` and `test_the_not_verified_label_is_visible_text_on_the_sample_page` on the real site; `test_not_verified_material_without_a_visible_label_is_reported` | met |
| 8 | `tests/integration/test_lesson_template.py`: the template with its two placeholders set passes the source checks and builds as a second lesson with every construct; unset placeholders are reported | mechanical part met; the reviewer follows the guide |

### Review round 1 (triage `feature-7-lesson-format-and-the-review-01-triage.json`)

2026-10-07, same machine. Fixed the approved `FIX_NOW` findings:

| Finding | Change |
|---|---|
| M1 | `Cell.options` in `tests/support/lesson_checks.py` recognises an option line with Quarto's own pattern (`#\s*\| ?`, `nb_cell_yaml_lines` in its `notebook.py`), so `# | eval: false` is a skipped cell. Cases `eval-false-spaced` in `_NOT_EXECUTED` (reported without the marker, accepted with it) and `skipped-cell-without-marker` in `test_verification_fails_on_a_violating_lesson`. A render of such a cell with Quarto 1.10.19 confirmed that it does not run. |
| MIN2 | `_UNLABELLED` in `tests/support/site_checks.py` opens the `<details>` ancestors of each marked element before judging the label. `test_labelled_material_inside_a_closed_solution_passes`, three new violating cases, and a marked block inside the solution of `site/rendering-check.qmd`, asserted by `test_the_not_verified_label_is_visible_text_on_the_sample_page`. |
| MIN3 | Exercise 3 of M1 restricts the conclusion to a constant acceleration and states that an error remains for a varying one, without comparing its size. |

Checks run on the final tree: `ruff check`, `ruff format --check`, `pytest
tests/unit` (38 passed), `pytest tests/integration/test_site_checks.py
tests/integration/test_lesson_checks.py tests/lessons` (154 passed),
`build-site.sh`, `pytest tests/e2e` (25 passed), `check-determinism.sh`
(27 files byte-identical). MIN1 is deferred to Issue #8.
