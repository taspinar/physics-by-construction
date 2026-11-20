# Plan: F143, Path 1: SA5 "Building a bounded experiment agent" and SA6 "Running adaptive and resumable measurement campaigns" (Issue #580)

Source: `docs/roadmap.md`, F143; change request
`docs/changes/part-b-scientific-products-and-research.md` (B1.5, B1.6, the
path boundary with B2.8, AI0 and AI5); ADR 004 (recorded runs), ADR 022
decisions 5 and 6 (the instrument contract, the evidence contract); ADR 023
decision 2; the session instructions on Issue #580. Written by the
implementer at the start of the work (the Issue expects a detailed plan and
none existed).

## Risk

**Level 3 by trigger: an existing test assertion changes.** SA6 runs a
measurement campaign through the instrument contract on its simulated
adapter, as SA3 and SA4 do.
`tests/unit/test_products_boundary.py::test_the_experiments_on_the_contract_are_the_two_lessons`
asserts that exactly the experiments of SA3 and SA4 import
`pbc.instruments`. SA6's experiment is added to that closed set, and the
rule the set exists for (the experiment is held to the import rule of the
contract's package, never the live mode, never a product) applies to it
unchanged through the parametrised test beside it. Reaching the contract
only through a library module, so that the experiment's text never names
`pbc.instruments`, was rejected for the reason F142 gave: it would satisfy
the scan while defeating its purpose. Approval request
`.agents/approvals/580.md`.

The published claims of `agent-experiment` are kept word for word (no claim
span of the page is edited or removed; new claims are added beside them).
SA5's new constants (the budget, the failure, the convergence threshold)
live in a new module, `pbc.agents.bounded_lab`, not in the existing
experiment file. No ADR, CI workflow, check of `scripts/verify.conf`,
dependency, payload budget, or existing tolerance changes.

Other paths: one new lesson, one extended lesson and its new replay
fixture, new modules under `src/pbc/`, new unit tests, `docs/authoring.md`
(a sentence under "Agent lessons"), `docs/project-map.md`,
`docs/architecture.md` (the module table; sensitive).

## What is delivered

| Part | Where |
|---|---|
| SA5, the extended lesson | `site/lessons/agents-llm/01-an-agent-runs-an-experiment/index.qmd`, id `agent-experiment`, slot SA5: the published projectile run stays as the introductory exercise; a second part adds the protocol, the budget, an injected tool failure, recovery, stopping, and the scripted route |
| The bounded lab | `src/pbc/agents/bounded_lab.py`: the protocol (`PROTOCOL`, the steps the agent is told), the budgeted allowlist with an injected failure (`tools()`), the protocol check recomputed from a transcript (`check_protocol`), the scripted route through the same allowlist (`scripted_route`), the live entry point; tests `tests/unit/test_bounded_lab.py` |
| SA5's recorded run | `site/lessons/agents-llm/01-an-agent-runs-an-experiment/replay-bounded.json`, recorded by a fresh Claude Opus sub-agent through a harness command (as AE5 and AE6 were, `docs/discovery-protocol.md`) |
| SA5's experiment | additions to `src/pbc/mechanics/experiments/agent_experiment.py` (no existing function or number changes); new tests in `tests/unit/test_agent_experiment_experiment.py` |
| SA6, a new lesson | `site/lessons/electromagnetism/12-measurement-campaigns/index.qmd`, id `measurement-campaigns`, slot SA6, course and strand electromagnetism, format 2, difficulty 2 |
| The campaign library | `src/pbc/electromagnetism/campaign.py`: F138's point procedure and estimator (the same numbers as `pbc.products.physics_lab.protocol`, which a page may not import; a unit test compares them), the plan of a campaign, measurements with ids, suggestions with their basis, the classical adaptive policy (bisection of the phase bracket, then repeats), the checkpoint, the resume that refuses an invalid checkpoint, cleanup on interruption, the ledger of `pbc.evidence`; tests `tests/unit/test_campaign.py` |
| SA6's experiment | `src/pbc/electromagnetism/experiments/measurement_campaigns.py`; test `tests/unit/test_measurement_campaigns_experiment.py` |
| The boundary test | `tests/unit/test_products_boundary.py`: SA6's experiment added to the experiments on the contract |
| Documents | `docs/project-map.md`, `docs/architecture.md`, `docs/authoring.md` ("Agent lessons": the injected failure and the protocol check) |

## Visual deliverables

Skills: pbc-physics-teaching@49f9f3e, pbc-scientific-visualization@a0c284f

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| The protocol the agent and the script follow: plan, choose the step, search, recover, stop, with the budget as a bar the calls use up | Conceptual diagram (`pbc.authoring.diagrams`) | `fig-bounded-protocol`, SA5 | Shows no result; the steps are those of `PROTOCOL` (a test compares) | alt text; the protocol is a numbered list in the prose |
| The calls of the agent and of the script in order, the budget used, the failed call marked | Scientific figure, `simulated` | `fig-two-routes`, SA5 | the calls of the replayed trace and of the scripted route, recomputed; the failure's position from the allowlist | alt text; the protocol-check table |
| The campaign's measurements in frequency against their order, sweep, refinement, and repeats told apart, the resonance as a reference line | Scientific figure, `simulated` | `fig-campaign-steps`, SA6 (preview) | the campaign's measurements; f0 of the closed form | alt text; the measurement table |
| The error of f0 against the number of measurements, the adaptive campaign against a fixed sweep, log scale | Scientific figure, `simulated` | `fig-adaptive-against-sweep`, SA6 | `evaluate` against the closed form (test) | alt text; the table |
| The campaign interrupted and resumed: what the checkpoint holds, the measurement lost in flight, the resume and its checks | Conceptual diagram | `fig-checkpoint-and-resume`, SA6 | shows no result; the checks are those of `resume` (a test compares their names) | alt text; the prose lists the checks |

No animation, no widget, no generated image.

## SA5: the learner and the subject

- **Learner.** Has done the projectile lesson and, on this page, its first
  half (the allowlist, the loop, the replay). Difficulty 2.
- **Central question.** The first half let a model run freely within
  bounds. What must be added so that a run follows a stated plan, spends a
  stated budget, survives a tool that fails, and stops on its own rule,
  and how can each of these be checked from the record rather than from
  the model's words?
- **Counterintuitive points.** (a) A failed call is not a result and still
  costs: the budget is spent by the attempt, so recovery has a price that
  the plan must allow for. (b) The check of the protocol is computed from
  the tool calls and their recomputed results, never from the agent's
  account of what it did. (c) A script that follows the same protocol
  reaches the same answer with no model at all: the agent's value is not
  in this protocol, which a script can run, but in what a script cannot
  do; the page says that this run does not show such value.
- **Archetype.** AI agent or evaluation; the kind of evidence stated at
  once: one recorded run of a model (a Claude Code session), replayed with
  every tool result recomputed, beside a deterministic scripted route.
- **Journey.** The first half as published; then the new question; the
  protocol written down before any run (the diagram); the budget and the
  injected failure as allowlist properties; the prediction moment; the
  recorded run replayed; the protocol check from the trace; the scripted
  route through the same allowlist and failure; the comparison table; the
  boundary with MD8; limits and an exercise.
- **Deliberate moments.** (1) Before the trace: the third simulation fails;
  how many of the ten runs can the protocol still use, and what should the
  agent do with the failed call? (2) The existing self-check stays; a new
  exercise asks whether the agent "recovered" if it repeated the failed
  call but used the failed one's missing result in its answer.
- **Code the learner reads.** `failing` (exact: the failure is injected in
  the tool, not in the prompt), the allowlist with its budget (exact),
  `check_protocol` (exact selection: each step's test from the trace),
  `scripted_route` (exact: the protocol as a program). The diagram and the
  figure: Source links, read first.
- **Exercise.** The budget set to four: what the scripted route returns
  (no answer, the budget spent, and it says so).

## SA6: the learner and the subject

- **Learner.** Has done SA3 (the contract, the simulated bench) and EM5
  (resonance, f0, Q). Difficulty 2.
- **Central question.** F138's protocol says how to measure one point and
  how to read f0 and Q from a sweep. A campaign has to decide where to
  measure next, how often to repeat, and what to do when it is
  interrupted halfway: which decisions are allowed, what makes a
  checkpoint trustworthy enough to resume from, and how is an incomplete
  run reported?
- **Counterintuitive points.** (a) Fifteen well-placed measurements locate
  f0 a thousand times better than fifteen evenly spread ones; the adaptive
  rule is a few lines of bisection, no model. (b) A resume is not a replay:
  the points before the interruption are taken from the checkpoint, the
  ones after are new measurements, and a measurement in flight when the
  stop came is lost, never half-kept. (c) A checkpoint that is a perfectly
  valid file can still be refused: one written for another plan, another
  bench, or an older state of the same campaign.
- **Archetype.** Model or simulation (a measurement procedure on a
  simulated bench), with the evidence kind stated at once: every
  measurement is made by the build on the simulated adapter; no hardware.
- **Journey.** The protocol of F138 recalled (one point, f0 from the phase,
  Q from the gain); a sweep; repeats (the noise measured, not assumed);
  the prediction moment; the local refinement and its suggestions, each
  naming the measurements it follows from; the adaptive campaign against
  the fixed sweep; the interruption, cleanup, and the incomplete run;
  the checkpoint and the valid resume recorded in the ledger; the refused
  resumes; the boundary with MD8; limits; self-check; exercises.
- **Deliberate moments.** (1) Before the comparison figure: with fifteen
  measurements, how much better than an even sweep will the adaptive
  campaign locate f0: twice, ten times, a thousand times? (2) The
  self-check: a resumed campaign reaches the same f0 as an uninterrupted
  one; were its later measurements the same measurements?
- **Code the learner reads.** `measure_point` (exact: F138's procedure),
  `suggest` (exact: the adaptive policy and the basis of each suggestion),
  `Campaign.run`'s loop (exact selection: suggestion checked, measured,
  checkpointed; the stop and the cleanup), `resume` (exact: the checks in
  order), the ledger entries (selection). Drawing code: Source links.
- **Exercises.** (1) A suggestion that cites a measurement lost in the
  interruption: refused, and why. (2) The repeats raised from three to ten:
  what changes in the uncertainty of f0 and what does not (the bias of
  the estimator).

## The boundary with MD8

Stated on both pages of this feature, in the words of the change request:
SA5 and SA6 execute and refine a *known* protocol (the question, the
measured quantity, and the stopping rule are fixed in advance); MD8
(`experimental-design-agent`, extended by F147) chooses an experiment
because competing physical explanations predict different outcomes. The
pages link MD8; F147 states the boundary on MD8's page.

## Steps

1. This plan and the handoff note.
2. `pbc.agents.bounded_lab`, its tests, the harness command; the recording
   by a fresh Opus sub-agent (in the background).
3. `pbc.electromagnetism.campaign` and its tests (the invalid resume
   refused).
4. SA6's experiment, page, and experiment test; the boundary test.
5. SA5's experiment additions, page section, and tests, once the
   recording exists.
6. The documents, the approval request.
7. The summary, the completion record; verification last
   (`./scripts/verify.sh --base` with `VERIFY_JOBS=2`, a new lesson; the full
   run is not made in the session, by the Issue's instructions, and is
   recorded as pending for `pr_ci`).

## Out of scope

Model discrimination and MD8's page (F147); live hardware (F140); a change
to the product `pbc.products.physics_lab`; a re-recording of the published
projectile run.

## Discoveries during the work

- **SA6 cannot import F138's protocol.** No page and no experiment on the
  contract may import `pbc.products` (`tests/unit/test_products_boundary.py`).
  `pbc.electromagnetism.campaign` therefore holds F138's point procedure
  and estimator again (about thirty lines); `tests/unit/test_campaign.py`
  asserts that both give the same point and the same f0, Q, and bracket
  as `pbc.products.physics_lab.protocol` to 1e-12. The product is not
  changed.
- **The noise seed is not part of the bench's identity for a resume.** A
  fresh simulated bench restarts its noise stream, so a resumed segment on
  the same seed would reuse the noise of the first measurements. The
  resumed segment uses the next seed, and the resume's bench check compares
  the device identity without the seed (`campaign.device`), which the page
  states (a resume is not a replay).
- **The standard error from the repeats is calibrated.** Over twenty seeds
  with ten repeats, (f0 - closed form) / standard error has a spread of
  1.02 and a mean of 0.05; the estimator's bias without noise is 1e-7
  relative. The page's seed (143) gives about two standard errors with ten
  repeats, which the exercise says is one draw; the unit test checks the
  spread over twelve seeds.
- **The exercise with ten repeats needs a larger budget** (35 measurements
  against the plan's 30); the exercise uses a budget of 40 and says so.
- **The recorded SA5 run.** A fresh Claude Opus sub-agent (2026-11-20) was
  given the system prompt, the task, and the tool specification, and sent
  each message as one JSON object through one harness command (a script in
  the implementer's scratchpad that runs `pbc.agents.loop.run` over the
  messages so far with the lesson's allowlist and writes the fixture with
  `save_recording` when the run ends). It used three tool calls, one per
  message, and ran nothing else. It asked for four angles in its second
  message; the run at 38 degrees failed and was not repeated, since the
  search was met without it. The protocol check finds every step met; the
  script repeats its failed run (39 degrees) and spends one run fewer.
- **Six outcomes are too many.** A lesson states two to five; the two new
  outcomes of SA5 became one, and the four published ones are unchanged.
- **SA6 needs a Code section** (`lesson-checks`): the excerpts of
  `measure_point`, `suggest`, `check_suggestion`, and `run_segment` moved
  there; the explanation keeps the reasoning in prose.

## Where the teaching skill changed the learning experience

- SA5's new part opens with what the first run lacked (a wish, "as few
  runs as you can", is not a rule), so the protocol answers a question the
  learner already holds; the diagram then separates the one step that is
  words (the plan) from the four that are checked from runs.
- SA5's prediction moment is placed before the replay: how many runs does
  the protocol need if the failed one is needed and repeated, and should a
  failed run the search does not need be repeated? The table after the
  replay answers both, with the agent and the script as the two cases.
- SA5 names what the comparison with the script does not show (that the
  agent adds anything), against the archetype's risk of reading one
  transcript as capability; a new exercise makes the limit of a check from
  runs concrete (a number misquoted in words passes every step).
- SA6 is a model-or-simulation lesson with the evidence kind stated in the
  opening; the closed form is introduced as the truth the campaign never
  sees before any campaign result.
- SA6's prediction moment comes before the comparison table (twice, ten
  times, a thousand times?), where the counterintuitive point (the factor
  is in the hundreds) meets the evidence; the self-check is the
  interpretation moment (a resume is not a replay).
- Code on the pages: SA5 shows `failing` (the failure lives in the tool),
  `tools` (the budget is an allowlist property), `check_protocol` (each
  step's test, from runs only), `scripted_route` (the protocol as a
  program), and the region that runs both routes; SA6 shows
  `measure_point` (F138's procedure), `suggest` and `check_suggestion` (the
  rule and the basis), `run_segment` (checkpoint after a complete
  measurement, the lost suggestion, `finally` switches off), `resume` (the
  five checks in order), and the regions of the interruption and the
  resume. Every drawing function is a Source link; each was read first and
  computes nothing the conclusion rests on (`draw_two_routes` and
  `draw_campaign_steps` plot recorded runs and measurements as they are;
  `draw_adaptive_against_sweep` plots the table's errors).
