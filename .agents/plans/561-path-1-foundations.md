# Plan: F141, Path 1 foundations: SA1 "From research question to experiment specification" and SA2 "Building and verifying scientific simulation tools" (Issue #561)

Source: `docs/roadmap.md`, F141 (and the block of the dropped F45, whose
workflow, sandbox profile, rubric, and boundary test F141 carries); ADR 010;
ADR 022 decision 7; ADR 023 decision 2; requirements decision 42; the
session instructions on Issue #561. Written by the implementer at the start
of the work (the Issue expects a detailed plan and none existed).

**Level 3 by assessment** (the Issue): the boundary test of invariant I24
is extended to coding agents. No protected path other than the approval
request `.agents/approvals/561.md`; no ADR, no CI workflow, no check of
`scripts/verify.conf`, no dependency changes. Sensitive paths touched:
`docs/architecture.md` (the module table and the evidence of I24).
Triggers named in the completion record: verification guarantees (a new
boundary test; none removed or weakened). The published claims of
`verifying-scientific-code` do not change: its existing text, numbers,
tables, figure, exercises, and tests stay as they are, and the feature
only adds to the page.

## What is delivered

| Part | Where |
|---|---|
| SA1, a new lesson | `site/lessons/mechanics/21-experiment-specification/index.qmd`, id `experiment-specification`, slot SA1, course and strand mechanics, format 2 |
| The specification format, its validation, and the scripted route | `src/pbc/agents/specification.py`; tests `tests/unit/test_specification.py` |
| SA1's experiment | `src/pbc/mechanics/experiments/experiment_specification.py`; test `tests/unit/test_experiment_specification_experiment.py` |
| SA2, the extension of mechanics/09 | two new sections of `site/lessons/mechanics/09-verifying-scientific-code/index.qmd`, new outcomes, the method `coding-agents`, the prerequisite `resonance` |
| SA2's reference solution as a tool | `simulate_driven` in `src/pbc/mechanics/resonance.py` (the simulation M12 already runs inside `measured_resonance_curve`, given a name; M12's numbers do not change) |
| The contract's checks on a model | `src/pbc/verification/driven.py` (limits, convergence order, units, energy balance, in the fixed evidence form), the wrong-on-purpose simulations `src/pbc/verification/faulty_driven.py`; tests `tests/unit/test_verification_driven.py` |
| SA2's experiment | additions to `src/pbc/mechanics/experiments/verifying_scientific_code.py` and its test |
| The coding-agent workflow document | `docs/coding-agent-workflow.md`: specification format, sandbox profile, budget, review rubric, what the site verifies; `docs/authoring.md`, "Coding-agent exercises"; `docs/validation-contract.md`, "Reuse" |
| The boundary test of I24 | `tests/unit/test_coding_agent_boundary.py` (beside `tests/unit/test_skills_boundary.py`, whose docstring names it) |
| The approval request | `.agents/approvals/561.md` |

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501, diagram-design@550fd66

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| The parts of a specification and what reads each | Conceptual diagram (`pbc.authoring.diagrams`) | `fig-specification-parts`, SA1 | Shows no result; the parts are the ones `PARTS` of the module names (a test compares the labels) | `fig-alt` with the insight; the list in the prose says the same |
| The route's runs: range against angle, coarse scan and refinement, the bracket, the predicted bound | Scientific figure, `simulated` | `fig-specified-search`, SA1 (the preview) | Every point is a call the route made through the allowlist; the unit test compares the bracket with an independent fine scan | alt text; the table of the runs |
| Convergence of the driven oscillator against its exact motion, the reference and two faulty simulations, reference slopes | Scientific figure, `simulated`, log-log | `fig-driven-convergence`, SA2 | `pbc.mechanics.resonance.driven_motion` is the reference; the fitted orders are the findings of the checks | alt text; the findings table |
| Reference limits: the free decay inside its envelope and the steady amplitude on the closed form | Scientific figure, `simulated` | `fig-driven-limits`, SA2 | closed forms of `pbc.mechanics.resonance` | alt text; the findings table |

No animation, no widget, no page layout.

## SA1: the learner and the subject

- **Learner.** Has done M3 (`projectile-with-drag`): the throw with
  quadratic drag, a scan of the angle by hand, the dependence of the range
  on the time step. Difficulty 2. Has not met an agent or an allowlist; the
  lesson explains "permitted action" from scratch and points forward to
  SA5 (`agent-experiment`), where a model takes the route's place.
- **Central question.** What has to be written down before the first run,
  so that the result can count against the idea it tests, and so that a
  program with no judgement can run the experiment and know when to stop?
- **Counterintuitive points.** (a) A specification is tested by whether it
  can fail: the same specification, run on the throw without drag, must
  refute the hypothesis, and does. (b) A stopping condition is part of the
  science, not housekeeping: with a budget too small the honest outcome is
  "no verdict", and a route without a budget has no such outcome. (c) A
  number without a unit is not a smaller specification but a different
  experiment: the same number read as radians is another throw.
- **Target misconceptions.** "The hypothesis is what the data showed."
  "Stop when the result looks right." "The units are obvious."
  "Success means the hypothesis was confirmed."
- **Archetype.** Model or simulation (the design of a numerical
  experiment), with the evidence kind stated at once as the AI-evidence
  archetype asks: every run on the page is made by a scripted route, a
  fixed procedure without a model, and computed by the build.
- **Journey.** The question and a loose plan that cannot be run; the seven
  parts, each introduced by what goes wrong without it; the diagram; the
  specification of the worked example (the projectile experiment of SA5);
  the validation (what is refused, and why before any run); the route; the
  prediction moment (what will the same specification report without
  drag?); the run with drag and the run without; limits; self-check.
- **Deliberate moments.** (1) Before the vacuum run: predict the verdict.
  (2) The self-check: a route that met its success criteria and refuted
  the hypothesis, was the experiment a success?
- **Code the learner reads.** `SPECIFICATION` (region; the object the
  lesson is about), `Problem` and the validation of the stopping part and
  of the units (exact selections: the rule that refuses), `execute` (exact
  full source or a selection of the loop: the route's control flow is the
  point: scan, refine, stop), `verdict` (the three outcomes). Drawing code:
  Source links.
- **Exercises.** (1) Write the specification of a new question (the same
  ball at 40 m/s; the prediction relative to the first result), which the
  route executes. (2) A specification with three defects (no stopping
  condition, a variable without a unit, a unit that is not the action's):
  find them, then read the refusal. (3) A budget too small: what does the
  route report, and what may be concluded?

## The specification format (`pbc.agents.specification`)

A specification is a mapping (plain data, written before the run) with
seven parts, `PARTS`:

1. `question`: the research question, a sentence.
2. `hypothesis`: a `statement` and a `prediction`
   (`quantity`, `relation` `below` or `above`, `value`, `unit`): a
   statement that a result can contradict.
3. `variables`: each with a `role` (`varied` with `low` and `high`,
   `fixed` with `value`, `numerical` with `value`, a parameter of the
   method that is not physics) and a `unit`.
4. `observable`: the `name` of the result of the action that is observed,
   its `unit`, and the `goal` (`largest` or `smallest`).
5. `actions`: the names of the permitted actions, each one of the
   laboratory (a `Laboratory` is an allowlist of `pbc.agents.tools` with the
   unit of every argument and result).
6. `success`: the `resolution` of the answer (value and unit of the varied
   variable) and `stable`, the requirement that the answer holds when the
   numerical variable is halved.
7. `stopping`: `max_runs`, the budget of executed actions.

`parse(mapping, laboratory)` returns a `Specification` or raises
`SpecificationRejected` with every `Problem` (part, message), never only
the first. It refuses: a missing part; a missing stopping condition or a
budget that is not a positive whole number; a variable, observable,
resolution, or prediction without a unit; a unit that differs from the
action's (no conversion is attempted); an action the laboratory does not
have; a variable the action does not take or one it takes that is missing;
a range or value outside the action's bounds; not exactly one varied
variable; a prediction about anything but the varied variable; a
`stable` criterion without a numerical variable whose half is permitted.

`execute(specification, laboratory)` is the scripted route: a coarse scan
of the varied variable, then repeated halving of the bracket around the
best setting until it is no wider than the resolution, then the check at
half the numerical variable; every call goes through the allowlist with
the specification's budget; it stops with one of `criteria met`,
`budget spent`, `action refused`, and returns a `Record` (the runs, the
bracket, the stop reason, the criteria, and the verdict `supported`,
`refuted`, `undecided`, or `no verdict` when a criterion is not met). It
never judges a hypothesis from a run that did not meet its criteria.

Tests (acceptance criterion 2): the route executes the lesson's
specification in the build (the experiment and the page) and reaches the
bracket an independent fine scan gives; a specification without a
stopping condition is rejected, and one without units is rejected, each
naming the part; a call beyond the budget is not executed; the vacuum
laboratory refutes; a refused action stops the route; the route makes no
call outside the specification's ranges.

## SA2: the extension of `verifying-scientific-code`

- **Learner.** Has the page's first half (the five checks on steppers, the
  gallery). M12 (`resonance`, order 16) comes later in the same strand, and
  a prerequisite in the same strand must come earlier, so it cannot be a
  prerequisite of order 9, and `related` is for extensions, which M12 is
  not: the section states the model itself, names M12 by its title as the
  lesson that studies the system, and needs from it only that the motion
  has a closed form. The prerequisites of the lesson are unchanged.
- **Central question (of the extension).** The page ended on a warning: the
  linear oscillator cannot show a fault that needs a force depending on
  time or velocity. Given a model the checks were not written for, and
  code someone or something else wrote for it, which checks carry over,
  which are new, and what do the provided tests decide?
- **Counterintuitive points.** (a) The stopped clock, which no physical
  test on the oscillator could see, is the first thing the driven
  oscillator shows. (b) A simulation tested only at unit mass passes with
  a missing division by the mass: the units check (rescale the units, the
  answer must rescale with them) finds what a convenient parameter hides.
  (c) Tests that pass do not review the code: the rubric asks what the
  tests cannot (assumptions, update order, failure modes), and the diff is
  read before anything runs.
- **Archetype.** Model or simulation, then AI agent or evaluation for the
  last section, with the kind of evidence stated at once: the build
  verifies the reference solution and the checks; the agent transcript is
  an unverified record of one session.
- **The model-to-code route** (`## From a model to tested code
  {#model-to-code}`): the specification in the workflow document's form
  (physics, assumptions, interface, units, the tests the result must
  pass); the code (`driving_force`, `simulate_driven`); the claim
  (`pbc.verification.driven.ModelClaim`: order 4); the checks in the
  contract's order: `limits` (no drive and no damping: the exact
  oscillator; no drive: the decay envelope; slow drive: the static
  deflection), `convergence-order` (against `driven_motion`), `units`
  (three rescalings of mass, length, and time), `energy-balance` (the
  work of the drive minus the dissipation equals the change of the
  energy, by quadrature of the simulated trajectory, the model's invariant
  in place of a conserved energy); a prediction moment (which of the
  page's six faulty steppers fail now that the force depends on time?);
  the gallery of faulty simulations, each caught by a named check.
- **Verifying coding-agent output** (`## Code a coding agent wrote
  {#coding-agent}`): what the site verifies and what it never runs; the
  sandbox profile in full, as a checklist; the budget; the review rubric
  in full; the provided tests (`verify_simulation`) on three submissions
  (the page runs the faulty simulations as stand-ins and says so); the
  example transcript, marked "not verified", with the agent and the date;
  the exercise on the learner's machine, marked "not verified".
- **The example transcript.** Recorded by the implementer on 2026-11-18:
  one session of a coding agent given the specification and the profile in
  a scratch directory outside the repository. The page shows a condensed
  excerpt (the request, what the agent did, the test result, the review
  notes), says that it is condensed, that the build did not run it, and
  that the profile was given as instructions to the agent in that session.
  The agent's code is not committed.
- **Existing content.** Unchanged. The new outcomes are added to the
  existing three (five at most); the description gains a clause; the
  format stays 1 (a migration to format 2 is an editorial pass, not this
  feature), and the new sections follow the format 2 rules that apply to a
  section anyway (figure status, tables through `table()`, interpretation
  after each figure).

## The coding-agent workflow document

`docs/coding-agent-workflow.md`: (1) scope and the two kinds of agent (ADR
010 decision 1); (2) the specification format of a coding task: physics,
assumptions, interface, units, tests the result must pass; (3) the
sandbox profile, numbered, with the reason and the failure each rule
prevents, and what the profile does not protect against; (4) the budget;
(5) the run, step by step, vendor-neutral; (6) the review rubric
(the diff first; assumptions; units; update order; tests; failure modes),
tied to the Scientific validation contract; (7) what reaches the
repository and how (the ordinary pull request, marked agent-drafted); (8)
transcripts ("not verified", agent, date; never an input of the build);
(9) reuse by F22 (Lean) and by the products' guided route (the Agentic
Coding Template, ADR 022 decision 7); (10) the boundary test.

## The boundary test of I24 (`tests/unit/test_coding_agent_boundary.py`)

What CI and the build are made of is computed, not listed by hand: the CI
workflows and actions, the commands of `scripts/verify.conf`, every script
those reach by name (transitively), `site/`, `src/`, `lean/`, `data/`,
`products/` without its learner documents, the pytest suites CI runs, and
the manifests. The test asserts:

1. the scan sees the machinery (the workflow, the build script, the
   package, the lesson pages) and is not empty by accident;
2. none of it starts a coding agent: no command line or argument list
   names a coding-agent program (Claude Code, Codex, Aider, Gemini CLI,
   Cursor agent, OpenCode, Goose, Copilot CLI, the Agentic Coding
   Template), outside material marked "not verified" on a page;
3. the one launcher of the development workflow, `scripts/lib/agent.sh`,
   is reached by no CI job, no check of `scripts/verify.conf`, and no
   build script, and no module of `src/pbc` or page starts a process with
   an agent's name;
4. none of it names a coding agent's credential (the variables and
   credential files of those tools), CI uses no secret beyond the
   workflow's own token, and the one provider key of the harness agents
   (ADR 004) is named only by its client, the pages' "not verified"
   blocks, and `.env.example`, which holds names only;
5. no file of the build or the checks depends on the Agentic Coding
   Template;
6. the transcript on the SA2 page is inside a "not verified" block that
   names the agent and the date, and no file of the repository is a
   transcript the build reads;
7. each pattern is shown to fail on a planted example (a check can fail).

## Steps

1. This plan and the handoff note.
2. `pbc.agents.specification` with its tests.
3. `simulate_driven`, `pbc.verification.driven`, `faulty_driven`, tests.
4. The example transcript session (scratch directory, outside the repo).
5. SA1's experiment, page, and experiment test.
6. SA2's experiment additions, page sections, and test.
7. The workflow document, the authoring section, the contract's "Reuse",
   `docs/architecture.md` and `docs/project-map.md`.
8. The boundary test.
9. The approval request, the summary, the completion record.
10. Verification, last: the unit tests and lesson checks of the changed
    files while working; `./scripts/verify.sh --targeted`, then `--base`
    (a new lesson and changed front matter). The complete
    `./scripts/verify.sh` is not run in the session (the Issue's session
    instructions); the script after the session runs it.

## Discoveries during the work

- **A claim of order one is refused by the model checks.** One fixed
  tolerance for the free decay and the energy balance failed a correct
  first-order method; `ModelClaim` now requires order two or more, and the
  page says why (a tolerance belongs to a claim).
- **Evidence texts show no value at round-off.** The reproduction compares
  the page with a reader's run, so `pbc.verification.driven` writes "below
  1e-12" where a measured value is under its allowance.
- **A unit mismatch ends the comparison.** `parse` does not go on to
  compare a number in another unit with the action's bounds.
- **The reach of CI is by execution, not by mention.** The scripts of the
  build name the workflow's scripts in messages and in the list of
  protected paths; the boundary test follows the paths a command runs or
  sources (and resolves the one loop that sources by a variable), and
  fails on a sourced file it cannot name.
- **A provider name as a key of a mapping is not a start.**
  `pbc.authoring.route` maps the provider names of `.agents/agents.conf`
  to the words the page "How we verify the science" shows; the Python rule
  reads argument lists and call arguments through the syntax tree.
- **Tests name provider keys only to delete them.** Several replay tests
  remove `ANTHROPIC_API_KEY` from the environment; the credential rule
  covers CI, the checks, the build, the package, and the pages, and a
  second test shows that no test reads such a variable.
- **The example session.** Run on 2026-11-18 as a subagent of the
  implementer's session, in a scratch directory outside the repository;
  the profile was given as instructions and not enforced by the harness,
  which the page says. Its file passed the provided tests on the first
  run; the review found that the tests do not cover the refusals of the
  interface, which the page and the workflow document now state. The
  agent's file is not committed.
- **`coding-agents` as a method.** The lesson now lists it beside
  `simulation`, so the path page gains the method's view with one lesson.
- **Format.** mechanics/09 stays in format 1; its new figures carry a
  status and its new results are tables.

## Where the teaching skill changed the learning experience

- SA1 opens with a plan that cannot be run and derives each part of the
  specification from the gap it leaves, instead of listing the format
  first; the full list of assumptions stays in its section, and the two
  the route depends on are recalled in "Limits".
- SA1's prediction moment is placed before the run without drag, where
  the counterintuitive point (a specification is tested by whether it can
  fail) meets the evidence; the self-check is the interpretation moment
  (a refuted hypothesis is not a failed experiment).
- SA2's extension starts from the warning its own page ended on and makes
  the learner predict which of the two "invisible" faulty steppers shows
  once the force depends on time, before any new check is explained.
- The unit check is taught through the fault that hides at a mass of one
  kilogram: the table at two masses comes before the rule.
- Code on the page: `SPECIFICATION`, `_stopping`, the unit lines of
  `_against_the_action`, `execute`, and `verdict` are shown because the
  rule or the control flow is the point; `rescaled` and `energy_balance`
  stand beside the sentence or the equation they implement; every drawing
  function is a Source link (each was read first: none computes a value
  the conclusion rests on beyond what its caption states).

## Out of scope

Running a coding agent in CI or the build; a vendor as a requirement;
instruments (F142); the bounded agent (F143); changes to the SA5 lesson;
the Agentic Coding Template's guided route itself (F139).
