# Plan: the comparator test of `mechanics/11` on a run with a base (Issue #268)

Source: Issue #268 (the authority on what is delivered); ADR 014 decisions
2 to 5; `docs/incremental-main-evidence.md`, sections 1 and 5;
`docs/development.md`, "Verification". No plan existed; the implementer
wrote this one in the unattended session (2026-10-23), so the owner reads
it with the pull request.

Skills: none (no visual deliverable; a change to tests and their
documentation only).

## Investigation: which record says whether this run executed a lesson

| Candidate | Finding | Usable |
|---|---|---|
| The selection, .agents/verification/selection.json (`pbc.authoring.selection`) | `scripts/verify.sh` makes it once per run with a base and writes it to this one file; a run without a base removes any earlier one (`verify.sh`, "The selection of the run"). It holds `mode` (`full` or `selective`), `lessons`, `execute`, `reuse`, and the `base` it was made against. CI's e2e jobs run `verify.sh --only e2e-<part> --base` with the same base as the build job, so the selection there is the build's. It is already the record the checks read: `tests/e2e/conftest.py` deselects the `same_machine` reproductions of restored lessons from it, and `pbc.authoring.pages.checked` chooses the pages to check from it. | Yes |
| `provenance.json` and its per-lesson `executed` and `origin` (`pbc.authoring.provenance`) | A prototype of F120: its docstring says nothing of the workflow calls it, and no build writes it into the site or a base today. | No: absent from every run |
| The summary line verify.sh prints ("4 of 48 lessons executed, 44 restored") | `selection.summary` of the same selection; a line of output, not a record a test can read. | Only through the selection |

The selection is reliable for this question on the same terms as the
reproduction: it describes the site this repository built
(site/_site), not a site passed with `--site-dir`, and its absence
means a run without a base, which executes every lesson.

## Tests that compare a fresh local calculation with embedded lesson data

| Test | Same cause? | Change |
|---|---|---|
| `tests/e2e/test_comparator.py::test_the_embedded_series_and_metrics_agree_with_a_fresh_run_of_pbc` (`mechanics/11`) | Yes: recomputes on the checking machine, compares at 6e-6, the platforms differ by about 3e-5 | Yes |
| `tests/e2e/test_widgets.py::test_displayed_values_agree_with_a_fresh_run_of_pbc` (`mechanics/05`) | No: the displayed values are rounded to four and three significant digits and compared at 1e-3 and 1e-2 relative, far above the platform difference; never seen failing | No |
| `tests/e2e/test_home.py`, the opening figure | No: the home page is not a lesson and is executed in every build; the figure is recomputed in a subprocess from the same code | No |
| `tests/e2e/test_lessons.py`, the reproductions (`same_machine`) | Already handled: deselected for restored lessons by `tests/e2e/conftest.py` | No |

## Change (tests only)

1. `tests/support/site_checks.py`: `inherited(site_dir, lesson)` reads the
   selection and returns None when this run executed the lesson (no
   selection, a full run, a selection that executes it, or a site that is
   not site/_site), the reason when the selection restored it from the
   base, and raises `SelectionError` when the selection exists but cannot
   be read, is of another format or mode, does not list its lessons, does
   not name the lesson exactly once as executed or restored, or restores
   it without a base or in a full run, or names a base without its id
   (the SHA-256 of its digests) and the identity of its checks (review
   01, M2).
2. `tests/e2e/test_comparator.py`: the comparison asks `inherited` first;
   it compares as before, skips with the reason, or fails on
   `SelectionError`. The fresh calculation runs only when it compares.
3. `tests/integration/test_pages.py`: the cases of the helper, and the
   comparator test itself in the three cases (compared, skipped with the
   reason, failed).
4. `docs/development.md`: the rule for a test that recomputes a lesson's
   result on the checking machine.

"A missing record is a failure, never a skip": a missing selection file
is the documented state of a run without a base, which executed every
lesson, so it gives the comparison (never a skip). A selection that
exists but cannot be trusted fails the test.

Not changed: the tolerance, the lesson, `src/pbc`, any ADR, the selection
and provenance code, the other checks, and no new record.

## Risk and verification

Level 2 by paths (`tests/`, `docs/`), Level 3 by the trigger of a new
skip in a check (ADR 020 decision 1; review 01, M1), with the approval
request `.agents/approvals/268.md`. A change to `tests/e2e` changes the
check identity, so CI runs everything and the local tier is the full
`./scripts/verify.sh`.

## Acceptance criteria and their gates

| # | Criterion (short) | Gate |
|---|---|---|
| 1 | Investigation reported in the plan, with the existing metadata | implementation |
| 2 | Executed lesson compared exactly as today | implementation |
| 3 | Inherited lesson skipped with a stated reason | implementation |
| 4 | Missing, unreadable, or inconsistent metadata fails closed | implementation |
| 5 | A test shows each case | implementation |
| 6 | Other tests of the same cause listed; only those changed | implementation |
| 7 | Tolerance, lesson, `pbc`, ADRs, selection and provenance code unchanged; no new record | implementation |
