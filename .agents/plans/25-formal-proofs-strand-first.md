# Plan: Issue #25, F08 — Formal proofs strand: first Lean lesson

- Issue: #25 (source: `docs/roadmap.md`, F08)
- Branch: `feature/25-formal-proofs-strand-first`
- Base commit: `a1690fb`
- Risk: Medium (a new display form, a new build artifact between the Lean
  check and the site build, a hand-written syntax definition)
- Governing documents: `docs/architecture.md` ("Verified display forms",
  "Formal proof lesson", invariants I5, I12, I13), ADR 002 (display by
  reference), ADR 003 (one verification entry point, CI budget),
  `docs/authoring.md`, the F05 plan (M4 demonstrates the energy factor
  numerically and announces this proof)
- Written by the implementer: no plan existed when the feature started.

## Goal

Publish L1, "Proving what the simulation showed", as the first lesson of the
`lean` strand: the constant-acceleration identity and the per-step energy
growth of explicit Euler on the harmonic oscillator, stated and proved in
Lean 4 with Mathlib, shown by reference, and backed by visible build evidence.

## Current state at the base commit

F01 left the Lean project (`lean/`, pinned toolchain and Mathlib, a pipeline
module) and `scripts/check-lean.sh` (build + axiom audit). F02 to F06 left the
lesson format, the Python `excerpt` helper, `reproduce_this`, the learning
path, and eight mechanics lessons. The `lean` strand exists in
`pbc.authoring.path` but has no lesson. Pandoc has no Lean syntax definition
and none exists upstream in KDE's syntax-highlighting repository.

## Design

| Piece | Decision | Reason |
|---|---|---|
| Lean excerpts | `lean_excerpt(module, anchor)` returns the lines between `-- ANCHOR: x` and `-- ANCHOR_END: x` in the module's file. Rendered as a `.lean` code block with `source="<module>:<anchor>"`, so the existing built-site comparison finds it | Anchors are comments, so the proof is unchanged; the same attribute drives the same check as for Python excerpts. A declaration-based extraction would need a Lean parser |
| Build evidence | `check-lean.sh` writes `lean/.lake/pbc-build-record.json` after a passed build and audit (and deletes it first): Lean version and commit, toolchain, Mathlib tag and revision, SHA-256 of every module. `lean_excerpt` and `lean_evidence` read it and refuse a module whose checksum differs | The page can only state what the same checkout's check observed, and cannot show a proof that was edited after it was compiled. The record is deterministic (no timestamps), so the determinism check holds |
| Evidence box | `lean_evidence(*modules)`: the commit (and a warning when the tree is dirty), Lean and Mathlib versions, per module a link to the repository file at the commit and one to the Lean web editor, and the statement of which source is authoritative | Acceptance criteria 6 and the roadmap scope |
| Web editor link | `https://live.lean-lang.org/#url=<encoded raw.githubusercontent.com URL of the file at the commit>` | The editor loads a file from a URL; the raw URL at a commit is immutable |
| Highlighting | `site/assets/lean.xml`, a Kate definition written for the project (MIT), registered by `syntax-definitions` in `site/_quarto.yml`; colours comments (nested), strings, numbers, declarations, commands, keywords, tactics, attributes | Build-time, no script (I4). Colours come from the site's `a11y` style, so contrast is covered by the existing axe scan |
| "Reproduce this" | When `code` lists a file under `lean/`, the commands include `./scripts/check-lean.sh` before the render, with a note that the first run fetches the Mathlib cache | A clone has no record; the page cannot be rebuilt without it |
| Lean files | `Mechanics/Kinematics.lean` (Torricelli's identity and the mean-velocity form) and `Mechanics/EulerOscillator.lean` (`springEnergy`, one-step factor, strict growth, `n` steps by induction). Physics is in hypotheses: `hx`, `hv`, `hnewton`, `hx'`, `hv'`, `hm`, `hk`, and for strict growth `hdt`, `hE` | Algebraic, so `subst`, `field_simp`, `ring`, `nlinarith`, `induction` suffice. No derivatives |
| Lesson check | `check_lean_modules`: `lean-modules` lists exactly the modules the page names, and each file exists | The field was validated for syntax only |

## Steps

1. Lean modules and `lake build` (done).
2. Syntax definition; Quarto `syntax-definitions`; CSS for the evidence box.
3. `pbc.authoring.lean`; `reproduce_this` step; `check-lean.sh` record.
4. Lesson L1 with executed examples connecting each theorem to M1 and M4.
5. Tests: unit (anchors, record, links, evidence), `check-lean` record,
   displayed-declarations audit, lesson-source check, built-site checks
   (excerpt identity for Lean, highlighting without JavaScript, evidence,
   links, hypotheses on the page), reproduce test shares the Mathlib packages.
6. Docs: authoring guide section, architecture flow, development, project map.
7. `./scripts/verify.sh`.

## Out of scope

Proofs about the Python code, hover information, derivatives or differential
equations (candidates for later lessons), a second Lean lesson.

## Discoveries during implementation

- No Kate/Skylighting definition for Lean exists upstream; the project's own
  is small by design and colours tokens only.
- The existing lesson check rejected an unmarked schematic ```` ``` ```` block
  in the draft lesson, which confirmed that Lean text outside an excerpt must
  carry the "not verified" marker.
- The reproduce test cloned the working tree without `lean/.lake`, and the
  new `check-lean.sh` command in the page made it fetch Mathlib (245 s, several
  GB). The test now links the packages of the checkout into the clone, as
  `test_lean_check.py` does (32 s).
- Quarto smart-quotes an apostrophe in an outside prerequisite, so the learning
  path page no longer matched the front matter text; the prerequisite is
  written without quotes.

## Verification evidence

`./scripts/verify.sh` on the working tree at base commit `a1690fb` plus the
uncommitted changes of this feature (macOS, Apple Silicon): all 14 checks
PASS in 9 min 38 s (preflight, preflight-test, lint, format, unit-tests,
lean-build, check-tests, lesson-checks, site-build, site-checks, determinism,
template-structure, shell-syntax, docs-scripts). The workflow self-tests were
skipped because no workflow file differs from `origin/main`. The first run
failed `check-tests` once: the template test counted the links of the path
page to mechanics lessons and did not expect the two prerequisites of L1; the
test now counts them.

Acceptance criteria:

1. L1 is `site/lessons/lean/01-proving-what-the-simulation-showed`; `lesson-checks`
   and `site-checks` pass.
2. `tests/e2e/test_lessons.py::test_excerpts_are_identical_to_their_source_and_every_cell_ran`
   compares each Lean listing with the region between its anchors, read
   independently of `pbc`; `test_lean_lesson.py` requires all six regions.
3. `check-lean.sh` runs `lake build` over every module; `tests/integration/test_lean_check.py`
   fails on a module that does not compile, on `sorry`, and on a project axiom;
   `test_lean_lessons.py` lists the axioms of every displayed declaration.
4. Hypotheses `hx`, `hv`, `hnewton`, `hx'`, `hv'`, `hm`, `hk`, `hdt`, and
   `hE` appear in the listings and in the assumptions section
   (`test_every_assumption_of_a_theorem_is_a_hypothesis_on_the_page`).
5. Highlighting is in the built HTML and read with JavaScript off
   (`test_lean_code_is_coloured_when_the_site_is_built`); the axe scan of all
   pages passes.
6. `test_links_point_at_the_built_commit_and_open_the_proofs` and the
   authoritative-source test.
7. The worked examples compute the residual of the identity on the exact and
   on the Euler motion, and the measured energy against the theorem; the
   "What the proofs do not cover" section lists the limits.
8. Budget: Lean check 7 s with the cache in place (limit 3 min), full site
   build 75 s (3 min), the reproduce test of L1 32 s, the page itself under
   the 30 s limit.

### Review round 1 (triage: M1, MIN1, MIN2 fixed)

- M1: the fall keeps its own step `fall_dt`, the final exercise uses it, and
  the cell asserts that $a^2 t\,\Delta t$ and the simulated residual agree to
  a relative $10^{-12}$; the rendered page prints 96.236 for both.
- MIN1: `check-lean.sh` resolves the project to an absolute path before
  changing into it; `test_a_relative_project_argument_keeps_the_record_in_that_project`
  covers a relative argument, and `./scripts/check-lean.sh lean` writes the
  record in `lean/.lake`.
- MIN2: the assumptions section explains `hdt` and `hE`, the listing
  introduction counts three hypotheses, and the assumption check requires
  both names on the page.
- `./scripts/verify.sh` on the working tree: all 14 checks PASS (workflow
  self-tests skipped, no workflow file differs from `origin/main`). A first
  run failed `site-checks` because the new inline code span `hE : 0 <
  springEnergy m k x v` could not wrap at phone width; the span is now the
  name only.

Manual steps: none.
