# Plan 613: the guided ACT route piloted, with the manual route verified (F139)

Issue #613. Risk Level 2 (documentation and starter files; no protected
path, no check of `scripts/verify.conf`, no dependency changed).

Skills: none (documentation and a recorded pilot). The feature changes no
lesson's teaching: the teaching line of ADR 023 decision 2 is not
applicable. Visual deliverables: none.

## Limits (decision 42, "Pilots"; written on the Issue before any run)

| Route | Wall-clock time | Further limit |
|---|---|---|
| Manual | 2 hours | none |
| Agent Codeyard | 2 hours, from creating the repository to an open pull request with passing tests | one feature cycle; planning included |
| Coding agent, no Codeyard | 30 minutes | 40 agent turns; allowlist: read, edit, and the test command |

Cost: all agent runs inside the owner's subscription, no per-call billing;
durations are recorded instead (ceiling EUR 50 per capstone untouched). A
route that reaches its limit ends there.

## The runs (made by the supervisor, recorded on the Issue)

- Manual: 12 of 12 provided tests and the starter's 5, first run.
- Coding agent under `docs/coding-agent-workflow.md`: 12 of 12, 164 s, 18
  turns; one write outside the scratch copy (a gap of the profile).
- Agent Codeyard at `df5430aa`: no open pull request within the limit
  (setup 7 min, planning 54 min, cycle 59 min to the limit; the review
  refused a reviewer of the implementer's provider). Owner's decision
  2026-11-25: a narrower go. The guided route is optional, the manual route
  is the default.

This session starts no agent and runs no Codeyard script (Issue, "No
nested workflow").

## Steps

1. Starter: `my_lab/ringdown.py` (the skeleton) and `SPECIFICATION.md`
   and `tests/test_ringdown.py`, verbatim from the Issue's comment "The
   pilot's common task". The provided tests fail until the learner's work
   exists, and the repository's `starters` check runs `tests/` twice; a
   `tests/conftest.py` therefore skips the ring-down tests, by name and
   with the reason, while `fit_ringdown` still raises
   `NotImplementedError`, and runs them unchanged once it does not. The
   tests are still collected and imported at the pin and the current tree,
   so a change of what they import fails CI. One starter test checks that
   the skeleton keeps the interface the specification fixes. No solution
   is committed (F145 holds the reference, `pbc.products.physics_lab.ringdown`).
2. `products/physics-lab/ROUTES.md`: the feature, the manual route
   (default), the lighter guided option (a coding agent under
   `docs/coding-agent-workflow.md`), the optional Agent Codeyard route at
   `df5430aa` with only the commands that ran and its conditions, the
   pilot's record in short, the gaps, and the workload estimate for Path 1
   labelled as an estimate from one pilot (no learner was timed).
3. Links: the product's README ("What is here", a routes paragraph), the
   starter's README (the third place of YOUR WORK), `docs/products.md` (a
   short section on the pilot and its decision).
4. Evidence: the starter's tests against the current tree and at the pin
   (`python -m pbc.products.starters`); the provided tests run against a
   throw-away solution outside the repository, to show the skip turns into
   a run; the targeted verification, last.

## Pin

The new files import only `pbc.electromagnetism.circuits` and
`pbc.instruments.simulated`, both present at the pin `84d1477`; the
dependency surface does not change, so no pin bump follows. If the
`starters` check at the pin fails, the follow-up is a pin bump in its own
change after the merge (ADR 022 decision 5), never here.
