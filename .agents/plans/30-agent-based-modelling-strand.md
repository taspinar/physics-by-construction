# Plan: Issue #30, F11 — Agent-based modelling strand: first lesson

- Issue: #30 (source: `docs/roadmap.md`, F11)
- Branch: `feature/30-agent-based-modelling-strand`
- Base commit: `6b4a000`
- Risk: Medium (physics content; run time against the 30 s lesson budget)
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`
- Written by the implementer: no plan existed when the feature started.

## Design

Lesson A-ABM1, `site/lessons/agents-abm/01-particles-in-a-box/index.qmd`
(`particles-in-a-box`, difficulty 2, prerequisite `momentum-and-collisions`).
New package `src/pbc/abm/`, module `gas.py`: hard discs in a square box.

| Piece | Contents |
|---|---|
| `initial_gas`, `Gas` | Non-overlapping random start from a `numpy.random.Generator`; one speed, random directions, zero total momentum |
| `step`, `run` | Drift, wall reflection with wall impulse counted, then elastic collision of overlapping, approaching pairs by `pbc.mechanics.particles.hard_sphere_collision` (reused, not rewritten) |
| `measure` | One seeded run: relax, then measure speeds and wall pressure |
| `wall_pressure`, `ideal_gas_pressure`, `virial_correction`, `rayleigh_pdf`, `speed_ratio`, `temperature` | Theory and estimators, shared by the page and the tests |
| `mean_and_error` | Mean and standard error over independent runs |

## Decisions

| Decision | Reason |
|---|---|
| Time-stepped, not event-driven; pairs found with an N x N distance matrix | Smallest code that reuses the M7 collision rule; N = 200 keeps one run near 0.6 s. N = 400 took 10 s per run in the Rosetta shell |
| No agent-based modelling framework | Out of scope unless justified; the model is 150 lines of numpy |
| Dilute gas (packing fraction about 3 %), pressure compared with `1 + 2 phi` | The ideal gas law alone is 14 standard errors off, so the check distinguishes the two. The pressure and the area use the side the centres can reach (`L - 2r`); with the box side the measurement was 1.4 % high |
| Emergent quantity for the distribution: `<v^4>/<v^2>^2 = 2` | Independent of the temperature, so no fit is needed. Start value is about 1 |
| Tolerance: 4 standard errors of the mean over 6 seeded runs | Stated on the page and in `tests/unit/test_gas.py` as a chosen heuristic. The standard error comes from the spread between runs, not from the number of discs; estimated from 6 runs, the discrepancy follows Student's t with 5 degrees of freedom, so chance exceeds 4 in about 1 case in 100 (review 01, MIN1) |
| `initial_gas` requires n >= 2 and bounds the placement search (100 batches per start, 100 starts) with a `ValueError` after that | Review 01: M1 (unbounded rejection loop hung on n=2, r=0.28, seed 0) and MIN2 (n=1 gave NaN velocities). The candidate draw order is unchanged when the first start succeeds, so the seeded page numbers are unchanged |
| Test also asserts the ideal-only law is rejected | A tolerance that accepts both laws would not be a check of the excluded-area term |
| No new widget, no new dependency, no change to `docs/architecture.md` | The lesson fits the F02 format as is |

## Verification

- `tests/unit/test_gas.py`: seeded start, wall bounce impulse, head-on
  exchange, no collision when separating, energy conservation of a run,
  determinism of a run, the Rayleigh formulas, and the two emergent
  quantities against theory (acceptance criteria 2 and 3).
- `tests/lessons`, `tests/e2e`, determinism build: criteria 1 and 2.
- `./scripts/verify.sh`: see "Evidence".

## Evidence

`./scripts/verify.sh` passed on 2026-10-08 (base `6b4a000`, uncommitted
changes): 362 unit tests, 223 integration tests, 8 lesson-source checks, 153
built-site checks, including the determinism build (two builds byte-identical).
Emergent quantities on the page: speed ratio 2.01 +- 0.03 (theory 2); pressure
ratio 1.057 +- 0.004 (theory 1.063 with the excluded area; ideal law 14 standard
errors off). Criterion 4: the Assumptions and Explanation sections state the
assumptions and the difference from the LLM agents strand.

Review 01 triage (M1, MIN1, MIN2 fixed): `./scripts/verify.sh` passed again on
2026-10-08 with 365 unit tests (three added: n < 2 refused, the seeded n=2,
r=0.28 start placed by a restart, the bounded search giving up with a clear
error), 223 integration tests, 8 lesson-source checks, 153 built-site checks,
and the determinism build byte-identical.
