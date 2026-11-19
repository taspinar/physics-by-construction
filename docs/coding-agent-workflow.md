# Coding-agent workflow

How a learner lets a coding agent write scientific code from a
specification, on their own machine, and how the result is verified and
reviewed. A coding agent is a program that takes a task in words, writes
files, and runs commands (Claude Code, Codex, and similar tools). This
document is the one definition every coding-agent exercise of the project
follows (ADR 010; invariant I24 of `docs/architecture.md`): the
specification format, the sandbox profile, the budget, the review rubric,
and what the site verifies. The lesson "Verifying scientific code"
(`site/lessons/mechanics/09-verifying-scientific-code/index.qmd`, slot SA2)
teaches it on the damped driven oscillator; the Lean exercises with an
agent (F22) and the guided route of the Part B products (the Agentic Coding
Template, ADR 022 decision 7) reuse it unchanged.

It was delivered by F141 (Issue #561), which carries the scope of the
dropped F45.

## What runs where

Two kinds of agent exist in this project, and they are kept apart (ADR 010
decision 1).

- **Harness agents** (ADR 004) call allowlisted functions of `src/pbc`
  through `pbc.agents` and are verified by replay. They never write or run
  code.
- **Coding agents** are external tools the learner chooses and runs. The
  site, the build, the checks, and CI never start one, install one, or hold
  a credential of one; no module of `src/pbc` invokes one.

What the site verifies is the produced code: the reference solution of an
exercise and its tests are ordinary code in `src/pbc` and `tests/`, checked
by CI like everything else. What an agent did in a session is never
verified, never replayed, and never an input of the build.

The site does not claim that an agent will succeed at an exercise, and it
names no agent or vendor as a requirement.

## 1. The specification

A coding task is given to an agent as a specification with these parts,
written before the agent starts. A part that is missing is a decision the
agent will make for you.

| Part | What it holds |
|---|---|
| **Physics** | The model: its equations, in words and symbols |
| **Assumptions** | What the model and the code may take for granted, and what they may not |
| **Interface** | The file, the function, its arguments and result, what it refuses, and what it must not do (global state, printing, files, network) |
| **Units** | The unit of every argument and result |
| **Claim** | What the code says about itself in numbers, such as its order of accuracy (the claim of `docs/validation-contract.md`) |
| **Tests the result must pass** | The command, and the named checks it runs |
| **Not allowed** | What the solution may not import or change: the reference solution, the checks, the tests |

The tests are provided with the task and are not the agent's to write or
change. They are checks of the Scientific validation contract: each
compares the result with a reference the code under test did not compute.

## 2. The sandbox profile

The profile is stated in full on the page of every exercise, as this
checklist. The learner sets it up before the agent starts.

1. **A scratch checkout.** The agent works in a fresh clone or an empty
   directory, never in a checkout the learner cares about. *Prevents:* a
   wrong command damaging work.
2. **An allowlist of commands.** The agent may run the tests, the
   formatter, and the exercise's own scripts, and nothing else: no
   installer, no version control, no other shell command. Where the agent
   asks for permission to run another command, the answer is no. Without
   a container or a separate machine this is a setting of the agent, not a
   limit the machine enforces. *Prevents:* the agent changing the
   environment the tests run in.
3. **No network beyond the agent's own provider.** Like the allowlist, it
   holds only where a container, a firewall, or a separate machine enforces
   it. *Prevents:* fetched code or data entering the solution, and anything
   leaving the machine.
4. **The credential stays in the learner's environment**, where the
   agent's own documentation says: never in a file of the checkout, never
   in a prompt, never in anything committed. The agent's commands run as
   the learner, so every credential in the environment variables of its
   shell is readable to them, not only the agent's own key: the agent starts
   in a shell that holds no other. A credential stored in a file the agent's
   commands can read (an SSH key, the configuration of a cloud tool, a
   stored Git credential, the agent's own login) is just as readable to
   them, wherever the checkout is: only a container or a separate machine
   keeps such a file out of reach. *Prevents:* a leaked key.
5. **A budget, set before the start** (section 3).
6. **Every diff is read before it is run.** The tests execute the agent's
   code; the learner reads what was written first, and never runs a command
   the agent proposes on a checkout that matters. This covers what the
   learner runs, not the code the agent runs itself while it works (the
   tests on its own draft, for example): that code runs unread, and only
   the scratch checkout and any isolation limit what it reaches.
   *Prevents:* the learner running code nobody has looked at.

**What the profile is not.** It is a way of working that limits the damage
of a mistake, not a security boundary. Without further isolation, rules 2
and 3 are settings of the agent, not limits the machine enforces: an agent's
own permission settings are the only enforcement the profile assumes, and
they differ between tools and versions. A learner who needs a boundary runs
the agent in a container or on a separate machine with no credential but
the agent's own. The profile also does not make the code right; sections 4
and 5 are for that.

## 3. The budget

Three numbers, written down before the session: steps (tool calls or
messages), time, and cost. When any is reached the session ends, whether
the tests pass or not, and the outcome is recorded as it is. A budget that
is raised until the tests pass is no budget; a session that ends without a
result is an outcome. A first exercise of the size of the one below needs
on the order of a dozen tool calls and a few runs of the tests.

## 4. The run

1. Make the scratch checkout and install the project's packages.
2. Put the specification and the provided tests in a directory of their
   own inside it.
3. Configure the agent with the allowlist and the budget, and start it in
   that directory with the specification as its task. Ask it to report the
   assumptions it made that the specification did not state, and what the
   tests do not cover.
4. When it stops, read the diff (rubric item 1) before running anything.
5. Run the provided tests yourself. The tests decide whether the claim is
   supported; the agent's summary does not.
6. Go through the rubric and write down what you found.

## 5. The review rubric

The rubric is the Scientific validation contract applied to code someone
else wrote: the claim came with the task, the checks ran on the result, and
the reading finds what the checks cannot.

1. **The diff.** Only the requested files were written; the imports are
   the allowed ones; the reference solution and the checks are not used.
2. **Assumptions.** Every decision the specification left open is listed
   and acceptable, including the ones the agent did not mention.
3. **Units.** Every term has the unit its place requires; each argument is
   used in the unit the specification gives.
4. **Update order.** The state variables are updated in the order the
   method requires; a force is evaluated at the time, position, and
   velocity of the stage that uses it; the clock is the state's.
5. **Tests.** The provided tests ran unchanged and pass; what they do not
   cover is named and, where it matters, checked by hand. Tests the agent
   added count for nothing until they have been read.
6. **Failure modes.** What the code does at the edge: invalid input, a
   step too large, a start at another time than zero, a run that is not
   finite.

A review reports each item with what was looked at and what was found, not
a score.

## 6. What reaches the repository

Nothing, by default: the exercise is the learner's. A contribution written
with an agent reaches the repository only through the ordinary pull
request, is read by a person, passes the same checks as any other change,
and is marked agent-drafted as `docs/content-proposals.md` requires (ADR
010 decision 4).

## 7. Transcripts

A transcript of an agent session shown on a page is an example, never
evidence. It stands inside a "not verified" block that names the agent,
with its version or model, and the date; it says how it was shortened and
whether the profile was enforced or only given as instructions. The build
reads no transcript, and none is committed as a file.

## 8. The example task

The task of the lesson, as the text to hand to an agent. The reference
solution is `simulate_driven` of `src/pbc/mechanics/resonance.py`
(`tests/unit/test_verification_driven.py` shows that it passes), and the
checks are `pbc.verification.driven`.

`SPECIFICATION.md`:

```text
# Specification: a simulation of the damped driven oscillator

## Physics

A mass m on a spring of constant k, with linear drag b, driven by the force
F0 cos(Omega t):

    m x'' + b x' + k x = F0 cos(Omega t)

## Assumptions

- Motion along one line; m, k, b, F0, and Omega are constants.
- The drag is linear in the velocity and acts against it.
- The time in the driving force is the time of the state (the clock of the
  initial state), not the time since the first step.
- No restriction to weak damping: any m > 0, k > 0, b >= 0.

## Interface

A Python function in the file `driven.py`:

    simulate_driven(initial, mass, k, b, force, omega, dt, n_steps) -> Trajectory

- `initial` is a `pbc.mechanics.dynamics.State` (`t`, and `x`, `v` as arrays
  of length 1).
- The result is a `pbc.mechanics.dynamics.Trajectory` with `n_steps + 1`
  rows: the initial state and the state after every step of length `dt`.
- It raises `ValueError` for mass <= 0, k <= 0, b < 0, or dt <= 0.
- No global state, no printing, no file, no network.

## Units

SI: mass in kg, k in N/m, b in kg/s, force in N, omega in rad/s (an angular
frequency, not a frequency in hertz), times in s, positions in m,
velocities in m/s.

## Claim

The method is of order 4 in the time step.

## Tests the result must pass

    python -m pytest test_driven.py

runs the checks `limits`, `convergence-order`, `units`, and `energy-balance`
of the Scientific validation contract on `simulate_driven`, under the claim.

## Not allowed

`driven.py` imports only `numpy` and `State` and `Trajectory` of
`pbc.mechanics.dynamics`. It does not import the reference solution
(`pbc.mechanics.resonance`), the steppers (`pbc.mechanics.integrators`), or
the checks (`pbc.verification`).
```

`test_driven.py`:

```python
"""The tests the result must pass: the checks of the Scientific validation
contract on the simulation in driven.py, under its claim."""

import pytest
from driven import simulate_driven

from pbc.verification.driven import ModelClaim, verify_simulation

FINDINGS = verify_simulation(simulate_driven, ModelClaim(order=4))


@pytest.mark.parametrize("finding", FINDINGS, ids=lambda finding: finding.check)
def test_the_simulation_passes_the_check(finding):
    assert finding.passed, finding.detail
```

The provided tests do not call the function with invalid input: the four
refusals of the interface are a rubric item (5 and 6), checked by reading
and by hand.

## 9. Reuse

- **A later simulation or analysis exercise** writes its own specification
  in the form of section 1 and its own checks in the evidence form of the
  contract, and reuses sections 2 to 7 unchanged.
- **Lean generation (F22).** The agent writes Lean on the learner's
  machine under the same profile; a proof shown on the site is compiled by
  the Lean build like every proof; the semantic review is human (ADR 010
  decision 5).
- **The guided route of the Part B products (ADR 022 decision 7).** The
  Agentic Coding Template is a coding-agent workflow on the learner's
  machine under this document: the route names a pinned, demonstrated
  revision and only the commands a learner needs, and no file of this
  repository's build or checks depends on it.

## 10. The boundary test

`tests/unit/test_coding_agent_boundary.py` keeps the boundary (ADR 010
decision 6). It computes what CI and the build are made of, in two parts.

- **The build side:** the CI workflows, the checks of `scripts/verify.conf`
  and the scripts they run or source, the site, the package, the test
  suites CI runs. The test fails when any of it starts a coding agent,
  reaches the launcher of the development workflow (`scripts/lib/agent.sh`,
  which the maintainer's own scripts use on the maintainer's machine,
  ADR 006), names a coding agent's credential, or depends on the Agentic
  Coding Template.
- **The self-tests of the development workflow:** the checks of
  `scripts/verify-workflow.conf`, which CI runs with `verify.sh --all`
  (ADR 005). CI does reach the launcher here, and only here: these
  self-tests load it and call it, and what they start under the name of an
  agent is a fake program the test wrote. The test fails when a self-test
  that can start an agent does not make a fake of every program the
  launcher starts, or sets a `PATH` that does not begin with those fakes
  (a `PATH` of the system directories alone is the one other form, for the
  case of a missing program); when a file of that reach names a credential;
  or when anything CI runs installs a coding agent.

Both parts are read from the text of the files: the test shows how CI, the
scripts, and the self-tests are written, not what one run of them did. It
also checks that the transcript of the lesson is marked. It extends
`tests/unit/test_skills_boundary.py`, the boundary of the agent skills
(I32).
