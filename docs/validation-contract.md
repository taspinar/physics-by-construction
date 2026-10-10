# Scientific validation contract

This is the contract a verifier follows when it is asked whether a piece of
scientific code is right: what it checks, in what order, and with what
evidence. A verifier is a person, a test suite, or a review agent; the
contract is the same for all three. The lesson "Verifying scientific code"
teaches it on steppers of the mechanics course, `pbc.verification` implements
it for them, and the multi-agent review (F18) and the rubric for
agent-assisted simulation development (F45) reuse it by name: **the Scientific
validation contract**.

The contract says what a verdict means. It does not say that a passed check
proves the code correct: it says what has been shown and what has not.

## What is verified

A **subject** (the code), a **claim** (what its author says it does, stated
before checking and in numbers: an order of accuracy, a conserved quantity, a
limit it reproduces), and a **model** (the physical system the claim is about).
A subject without a claim cannot be verified, only run. `pbc.verification.Claim`
is the claim of a stepper.

## Rules for every check

1. **Independent reference.** The thing a result is compared with is not
   computed by the code under test or by code derived from it: an exact
   solution, a limiting case, a conservation law, or a second implementation
   written from a different derivation. The experiment's own clock and step
   count are used, never the subject's.
2. **Tolerances before results.** Each tolerance is written down, with its
   reason, before the subject is run. A tolerance is never widened to make a
   check pass; a check that must be widened is reported as it is.
3. **Evidence in a fixed form.** Each check reports its name, the claim it
   tests, the measured value, the tolerance, the verdict, and how to
   reproduce it: the call of the check on a fresh subject and a claim
   (`pbc.verification.Finding`, fields `check`, `claim`, `measured`,
   `tolerance`, `passed`, `reproduction`).
4. **A check can fail.** Every check is shown to fail on a subject known to
   be wrong (the negative test) and to pass one known to be right. A check
   without a failing case is not a check. `pbc.verification.faulty` is the
   gallery of wrong steppers; it is marked as wrong and imported by nothing
   that simulates.
5. **Not measured is not passed.** A value that is not finite, a run that
   did not finish, and an error of zero where one cannot be zero are
   failures of the check, reported as such.

## The checks, in order

The order runs from what is cheapest and most basic to what is expensive and
needs the earlier results to mean anything. A verifier stops at the first
failed check of a group only to report it; it still runs the rest, because
the pattern of failures locates the fault.

| # | Check | What it asks | Reference |
|---|---|---|---|
| 1 | `clock` | Does a step of length dt advance the time by dt? | the experiment's dt |
| 2 | `purity` | Does a step depend only on its arguments, not on earlier steps? | the same step repeated |
| 3 | `limits` | Does it reproduce the cases with a closed form: no force, a constant force (velocity, and position for order 2 or more)? | the exact motion |
| 4 | `convergence-order` | Does the error fall as the step to the claimed power? | the exact solution of a model, at several steps |
| 5 | `bounded-energy` | When it claims to conserve a quantity, does the quantity stay in a band that does not grow, over a long run? | the first periods of the same run |

The first three are interface and limit checks: they need no long run and
fail on faults that no physical result shows. Convergence and conservation
need a reference solution and a run; they are the checks that find a fault
which only changes the numbers slightly. A fault that passes the physics
checks and fails the interface checks (a stopped clock, a hidden state) is
the reason the order starts there.

## Evidence and verdicts

A check ends in one of three verdicts: **passed** (measured within the
tolerance), **failed** (measured outside it, or not measured), and
**not applicable** (the claim does not include it: a method that does not
claim bounded energy is not checked for it). `pbc.verification.verify`
returns one finding for each check that applies.

A report of a verification states, for each check, the verdict and the
evidence of rule 3, and then, separately, what the checks did not cover: the
models, the step sizes, and the force laws that were not tried. A passed check
supports the claim **numerically-verified** for the models and steps it ran
on, in the sense of the claim types of the authoring guide, and for nothing
more. A claim about another model needs its own run.

## Reuse

- **F18, multi-agent scientific review.** A review agent takes the claim and
  the subject, runs or reads the checks above in order, and reports in the
  form of rule 3. It does not decide a verdict by judgement where a check can
  be run; it names which check it would run. Several reviewers agree on the
  checks and the tolerances (rules 1 and 2) before they compare verdicts.
- **F45, agent-assisted simulation development.** The rubric for code a coding
  agent wrote is this contract: the claim comes with the task, the checks run
  on the result, and the evidence is part of what the learner reads.
- **A new model.** The checks of a different model keep their names where
  they ask the same question (`limits`, `convergence-order`) and add their own
  where the model has a conserved quantity or a symmetry of its own. A
  conserved quantity gets a bounded-or-drifting check like check 5; a
  symmetry gets a check that the result transforms as the model does.

## What the contract does not do

It does not prove a method correct for all inputs; that is the work of a
proof, and the Lean lesson of this site shows the difference. It does not
check the physical model against nature; that is validation against
measurement, which the measured-data labs do. And it does not replace reading
the code: the checks find that something is wrong, the reading finds what.
