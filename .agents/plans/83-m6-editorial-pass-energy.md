# Plan: F30 editorial pass, M6 energy conservation (Issue #83)

Source: Issue #83, docs/roadmap.md F30, docs/authoring.md "Lesson format 2",
plan 57 (the M5 pilot, whose audit template is reused).

## Audit
Posted on Issue #83 before the rewrite (comment of 2026-10-10).

## Decisions
- Every computation of the old lesson is kept; periods, drifts, orders, lags,
  the over-the-top energies, and the three exercise results are unchanged. Console
  blocks become `table()` tables with the same values.
- New derivations: the period integral and its substitution, the series
  1 + theta0^2/16 + 11 theta0^4/3072, the potential from the height, and the
  leading energy gain of one explicit Euler step (checked in a cell).
- Removed unsupported claims: "fastest where the bob moves fastest", the
  unexplained factor 2^5 of the classical Runge-Kutta drift (now measured, with
  the pattern of the oscillator derivation named and not claimed for the pendulum),
  "good to the digit shown" in exercise 1.
- References: SciPy `ellipk` (API, parameter convention) and Wikipedia
  "Pendulum (mechanics)" (derivation, series). Both pages were fetched as raw
  HTML with curl and read as text by the agent; no person has compared them yet.

## Guide gap
None found beyond the one M5 fixed.
