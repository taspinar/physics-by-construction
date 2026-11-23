# Plan: Follow-up bundle 2 (Issue #610)

Issue #610 bundles #606, #608, and two defects of the documentation audit of
2026-11-23 (A13, W11). Each item keeps its own acceptance criteria.

Skills: pbc-physics-teaching@7f34987
Skills: none (tests, code and docs only)

The teaching skill is selected for the text change on RR6's page (#606);
the second line covers #608, A13, and W11.

Visual deliverables: none. No figure, diagram, or page layout changes.

Risk: Level 3. A13 pins the starter, so the existing assertion
`tests/unit/test_starters.py::test_the_physics_lab_starter_is_found_with_its_pending_pin`
changes (the Issue's trigger "an existing test assertion changes");
`.agents/approvals/610.md` requests the owner's review.

## #606: RR6, the record carries the identity of its specification

**Fix.** `parse` (`pbc.agents.specification`) records the digest of the
data it parsed in `Specification.digest`; `execute` copies it into
`Record.specification`, so the identity is set by the execution, not by
the caller. `pbc.research.plan.execute` builds the positive control's
specification from the plan's with another measuring action; it gets its
own digest (the plan's specification and the control action), so that the
control's record never claims the identity of the specification it did
not run. `Log.record(test, record)` reads the recorded identity and refuses
a record whose identity is not the digest of the declared specification
(and a record without one); the optional third argument, when given, must
also be that identity. `record_digest` covers the specification's digest.
RR6's experiment registers its records without the argument, and its page
says what the check now establishes.

**Test.** New tests in `tests/unit/test_research_followup.py`: experiment
A executed by the route and registered under test B is refused; a record
without an identity is refused; `record_digest` changes when only the
identity changes. A new test in `tests/unit/test_specification.py`:
`execute` sets the identity from `parse`; one in
`tests/unit/test_research_plan.py`: the plan's positive control does not
carry the plan's identity. The existing
test helper builds its synthetic record with the identity of `SPEC`; no
existing assertion changes.

**Defect class swept.** "An identity supplied by the caller instead of the
run": every construction of `Specification` or `Record` outside `parse` and
`execute` (only the positive control of `pbc.research.plan`), and every call
of `Log.record`.

**Claims.** SA1 (`mechanics/21`), RR2 and RR6 (`mechanics/25`) compute the
same runs, brackets, and verdicts; only record digests (hashes) change.

## #608: the replay of a live export writes the live processing

**Fix.** `pbc.products.physics_lab.workflow.run` writes `LIVE_PROCESSING`
when the mode is live or the recorded sample is a live export (a
directory, read by `read_export`).

**Test.** A new test in `tests/unit/test_data_ad3_rlc_pilot.py`: the replay
of the committed fixture writes the processing of the live run it replays,
and does not claim whole periods or the `steady_phasor` projection
unconditionally.

**Defect class swept.** "The replay route of a live export treated as a
synthetic sample": every branch on `Path(sample).is_dir()` in `workflow.py`
(the envelope, the circuit, the processing).

## A13: the starter's pin

**Fix.** `products/physics-lab/starter/pyproject.toml` pins `pbc` to
84d1477bbfef063a0bec3ca1d92c94787a2c8fcf, the head of `main` this bundle
starts from (F140 merged, CI passed). `docs/products.md` and
`docs/architecture.md` say how the pin is kept current, in place of the
bootstrap sentence about the bump after F138.

**Test.** The existing test of the physics-lab starter asserts a full
hash in the history of `HEAD`, not `pending`; the `starters` check runs
its at-pin half.

**Defect class swept.** Every mention of the `pending` pin of this
starter in docs, comments, and tests.

## W11: units only from the documented form

**Fix.** `pbc.authoring.excerpt._units` takes the unit of a name from its
first ``` ``name`` (unit) ``` whose text is unit-like: it begins with a unit
expression (unit symbols or names joined by `/`, `·`, or a space, with
powers), or with `<words> in <unit expression>`, or with `units of`. A
parenthesis that is not unit-like is ignored, and a later occurrence never
overrides an earlier one. `docs/authoring.md` states the rule.

**Test.** New tests in `tests/unit/test_authoring.py`: the two docstrings of
the audit (`acceptance.agreement`, `bands.ring_hamiltonian`) give no unit;
the first unit-like occurrence wins; the documented forms are kept.

**Defect class swept.** Every ``` ``name`` (…) ``` in `src/pbc`: the
displayed units that change are only non-unit texts that leave the column
(a shape, a description, a default), recorded in the handoff note.

## Verification

The changed tests; the session checks of the Issue; `--targeted` or
`--base` with `VERIFY_JOBS=2`. The excerpt parser is a shared input, so the
selection may be every lesson: then the criterion is `pr_ci` pending, and
the full run is the script's after the session (Level 3).
