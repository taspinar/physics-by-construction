# ADR 010: Coding-agent exercises run only on the learner's machine under a sandbox profile; the site verifies the code, never the agent

## Status

Proposed with the planning of the change cycle `physics-next-phase`;
accepted when that planning is approved. Adds the explicit, sandboxed
opt-in that ADR 004 said would need a new ADR; ADR 004's harness is
unchanged.

Date: 2026-10-09

## Context

The re-approved requirements add optional local workflows in which a
learner drives a coding agent (for example Claude Code or Codex) on their
own machine with their own account, from an approved physical
specification to a tested Python simulation, and later to a Lean proof.
Such exercises require sandboxing, an explicit tool and command allowlist,
budgets (steps, time, cost), and human review of the result before it is
trusted. The site verifies the produced code, tests, and proofs in CI; an
agent session shown on a page is either a replay fixture whose tool
results CI recomputes or is visibly marked as not verified. No paid-model
token or secret appears in static web assets or CI.

ADR 004 decided that the harness treats model output as data and never
executes model-written code, and that letting the agent write and run
Python "requires a real sandbox and contradicts the requirement to withhold
arbitrary execution by default. Out of scope unless a later feature adds an
explicit, sandboxed opt-in through a new ADR." The features F45, F55, and
F22 are that opt-in. Replaying agent-written code in CI would mean
executing arbitrary code CI did not review, and coding agents differ by
vendor and change monthly.

## Decision

1. **Two kinds of agent, kept apart.** Agents in the harness of ADR 004
   (experiments, counterexample hunting, review, experimental design) call
   allowlisted functions of `src/pbc` and are verified by replay; that
   decision stands unchanged. Coding agents are external tools the learner
   runs; the harness never becomes one, and no code of the site or of
   `src/pbc` invokes a coding agent.
2. **Exercises, not features of the site.** A coding-agent exercise is a
   documented local workflow in a lesson: a physical specification
   (physics, assumptions, interface, units, and the tests the result must
   pass), a sandbox profile, a budget, and a review rubric. The learner
   chooses the agent and supplies the account; the lesson names no vendor
   as a requirement and the site never claims that an agent will succeed.
3. **The sandbox profile** is stated in full on the page and in the
   workflow document of F45, and every later exercise reuses it: the agent
   works in a scratch checkout; it may run only the listed commands (the
   tests, the formatter, the lesson's own scripts); it has no network
   access beyond its own provider; its credential stays in the learner's
   environment; the budget in steps, time, and cost is set per exercise;
   the learner reads every diff before running it and never runs the
   agent's commands on a checkout they care about.
4. **What the site verifies.** The reference solution, its tests, and any
   proof are ordinary code and proofs in `src/pbc` and `lean/`, verified by
   CI like everything else. A contribution produced with an agent reaches
   the repository only through the ordinary pull request path and is
   marked agent-drafted as `docs/content-proposals.md` requires. The
   agent's transcript is never an input to CI, is never replayed, and, if
   shown on a page, carries the "not verified" marker with the agent and
   the date.
5. **Lean generation** (F22) follows the same rules: the agent writes
   Lean on the learner's machine; a proof shown on the site is compiled by
   `lake build` like every proof; the page says what a compiled proof does
   and does not establish; the semantic review is human.
6. **A test keeps the boundary**: no workflow file, script, check, or
   package module invokes a coding agent or references its credential, and
   CI holds no such credential (invariant I2 and I24).

## Alternatives considered

**Extend the harness with a sandboxed code-execution tool and replay it in
CI.** Rejected: CI would execute code a model wrote and no human reviewed;
the sandbox would become part of the site's trusted computing base; replay
of code execution is not deterministic across machines.

**Run coding-agent exercises in CI with a repository secret and a
container sandbox.** Rejected: forbidden by the requirements (no model
token in CI), costly, non-deterministic, and a secret exposed to workflow
changes; ADR 006's reasoning applies.

**Ship a vendor-specific agent configuration as the exercise.** Rejected:
vendors and their tools change faster than the site; the exercise is
defined by the specification, the profile, the tests, and the rubric,
which any agent can be pointed at.

**No coding-agent exercises.** Rejected by the requirements, which name
them as a later-phase use case.

## Consequences

Positive:

- The security boundary of ADR 004 is unchanged and the site's trusted base
  does not grow; the only new trust is the learner's, on their own machine,
  stated plainly.
- Exercises survive vendor churn because they specify outcomes and checks,
  not agent behaviour.
- The same profile serves simulation, experimental analysis, and Lean
  exercises.

Negative, with mitigations:

- The site cannot show a verified agent run for these exercises; it shows
  the verified result and a labelled example transcript, and says why.
- A learner can misconfigure the sandbox; the page states the profile as
  a checklist, the scratch checkout limits the damage, and the review rule
  is first in the rubric.
- Exercises cannot be auto-graded by the site; the provided tests decide,
  and the learner runs them.
