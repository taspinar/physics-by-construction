# Plan 62: F46 Scientific code verification and debugging

Issue #62. Short plan.

## Design

- `pbc.verification.estimates`: observed and fitted order, convergence table,
  invariant drift and band. Plain arrays in, numbers out.
- `pbc.verification.checks`: `Claim`, `Finding`, five named checks in the order
  `clock`, `purity`, `limits`, `convergence-order`, `bounded-energy`, and
  `verify(build, claim)`. References are independent: exact oscillator, exact
  free and constant-force motion, the experiment's own clock. Every simulation
  of a check gets a fresh stepper from `build`, so hidden state cannot help a
  later run.
- `pbc.verification.faulty`: six steppers wrong on purpose, each with the
  correct method it poses as, its claim, and the checks that must fail.
  Imported only by the lesson and the tests.
- Lesson `mechanics/09-verifying-scientific-code` (format 1, method
  `simulation`, next order after M8, ADR 008 decision 3).
- `docs/validation-contract.md`, titled "Scientific validation contract",
  named in the lesson and reusable by F18 and F45.

## Decisions

- Mechanics lesson M8 has no previous/next prose; only its description called
  it "the capstone of the mechanics course", now "the physics capstone".
- Each faulty stepper is caught by an exact set of checks (asserted in
  `tests/unit/test_verification.py`), and every check is the only catch of at
  least one fault, except `limits`, which the wrong-sign and the no-half faults share.
- Format 1 rather than format 2: the format 2 checks (no printed number blocks,
  one self-check) would need a different page structure; migration is for the
  editorial pass.

## Acceptance

| Criterion | Evidence |
|---|---|
| Each faulty implementation caught by a named test on the page, a correct one passes the same tests | The matrix cells of the page; `test_each_faulty_stepper_fails_exactly_the_checks_named_for_it`, `test_every_check_passes_a_correct_method` |
| Contract referenced by name in the lesson, reusable by F18 | `test_the_lesson_and_the_contract_name_each_other_and_the_checks`; the "Reuse" section of the contract |
| Usual lesson and page checks | `tests/lessons`, `tests/e2e` |
