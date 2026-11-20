# Plan: F147, Path 2: hidden variables and failures of known laws; active experimental design; generalisation across systems (Issue #581)

Source: `docs/roadmap.md`, F147; the session instructions on Issue #581;
ADR 023 decision 2. Written by the implementer at the start of the work
(the Issue expects a detailed plan and none existed).

**Level 2** by the paths (lessons, `src/`, tests, documentation). No
protected path, no ADR, no CI workflow, no check of `scripts/verify.conf`,
no dependency. The published claims of the four lessons stay as they are:
every existing claim span, number, table, figure, exercise, and test
assertion is kept; the feature only adds sections, exercises, outcomes, and
code. To keep the tolerance trigger away (a new tolerance or budget line in
an existing Python file), every new constant, rule, and analysis lives in a
**new module**, and the existing experiment of each lesson gains one call
(`experiment.figure(label, <new module>.extend(experiment))`) in its
`run()`, with no number on the line: `extend` records the numbers and
tables and returns the drawing, which the lesson's experiment records (the
lesson checks read the figure calls of the declared module). New test assertions are new `def test_` functions or new test files.
Shared code changes only by addition or by a behaviour-preserving
extraction, whose existing tests pass unchanged. If a published claim or an
existing assertion has to change after all, the change becomes Level 3 and
gets an approval request (.agents/approvals/581.md).

The prerequisites of the four lessons are not changed.

## What is delivered

| Part | Where |
|---|---|
| MD4: state selection | a section of `site/lessons/agents-llm/09-discovering-differential-equations/index.qmd`; the search on a named state and the consistency test of a state in `pbc.discovery.state_selection`; the coupled oscillators and the analysis in `pbc.mechanics.experiments.state_selection` |
| MD6: a known law that fails | a section and an exercise of `site/lessons/agents-llm/19-hidden-variables/index.qmd`; the falling-ball viscometer, the extensions, the discriminating experiment in `pbc.mechanics.experiments.failing_law` |
| MD8: four strategies under one budget | a section of `site/lessons/agents-llm/04-an-experimental-design-agent/index.qmd`; the seeded rig, the scripted, adaptive, LLM, and hybrid strategies, and the evaluator's ledger in `pbc.agents.strategy_lab`; the page's tables and figure in `pbc.mechanics.experiments.design_strategies`; five recorded LLM sessions `replay-one.json` to `replay-five.json` next to the page |
| MD9: levels of transfer, a thermal case | a section of `site/lessons/agents-llm/20-generalisation-to-unseen-systems/index.qmd`; the thermal box, the scripted discoverer with its probe trace, the held-out thermal worlds in `pbc.discovery.thermal_transfer`; the page's tables and figure in `pbc.mechanics.experiments.thermal_transfer` |
| Tests | a unit test file per new module; new tests in each lesson's experiment test (each new claim span) |
| Documentation | `docs/discovery-protocol.md` (a section on F147's parts); the module rows of `docs/architecture.md` and `docs/project-map.md`, added at the end of an entry |

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501

Archetypes: MD4 model or simulation (a discovery lesson without an agent);
MD6 and MD9 AI agent or evaluation (main), the new parts model or
simulation, computed by the build without a model run; MD8 AI agent or
evaluation (the evidence kind stated at once: recorded sessions replayed
and scored by the evaluator, strategies without a model computed by the
build).

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| Position of the first mass from a held-out start: truth, the equation of the one-mass state, the equation of the two-mass state | Scientific figure, `simulated` | `fig-missing-state`, MD4 | Both equations from the search; the test recomputes the held-out errors | alt text; the table of the two states |
| Terminal speed relative to Stokes' law against the effective weight: the record, the discriminating readings, the fitted extensions | Scientific figure, `simulated`, log weight axis | `fig-extensions`, MD6 | `fit_curve` of each extension; the tables before and after; the test | alt text; the two tables |
| Chi-square difference of each strategy at each seed, with the threshold | Scientific figure, `simulated` (strip plot) | `fig-strategies`, MD8 | The evaluator's metrics; the summary table; the test | alt text; the table |
| Error of the found cooling law in each thermal held-out world, with the tolerance | Scientific figure, `simulated`, log error axis | `fig-thermal-transfer`, MD9 | The judge of the thermal worlds; the table; the test | alt text; the table |

No animation, no widget, no page layout. No preview changes.

## The teaching of each extension

### MD4, `discovering-differential-equations`: the choice of state variables

- **Question.** The search was given the position and the velocity of the
  mass as its state. What if the state it is given is not one?
- **Counterintuitive point.** The search still returns a tidy equation with
  a few terms; nothing in the regression says the state is incomplete. The
  failure shows only in a test of the state itself.
- **System.** Two equal masses on springs, coupled by a third spring; the
  camera tracks the first mass only. True: `a1 = -(k + kc) x1 + kc x2`.
- **Detection.** (1) the residual of the found equation against the error
  floor of the central differences; (2) the state test: two samples whose
  state (x1, v1) is nearly the same have accelerations that differ by a
  large fraction of the root-mean-square acceleration, so (x1, v1) does not
  determine what happens next; (3) the held-out start fails.
- **The state that removes it.** (x1, v1, x2, v2): the second mass tracked.
  The search on it keeps exactly the two true terms, the state test finds no
  inconsistent pair, and the equations of both masses integrated from a
  held-out start follow the truth.
- **Prediction moment.** Before the table: will the search on (x1, v1)
  return an error, a long equation, or a short wrong one?
- **Code shown.** The state test (exact, its control flow is the point);
  the search on a named state (exact selection: the library over named
  variables); the system as a region; the drawing function as a Source link
  (read first: it computes nothing).
- **Unchanged.** Derivatives, held-out test, singular values, pendulum, as
  published.

### MD6, `hidden-variables`: a known law that fails, and its extensions

- **Question.** The family of the lesson named its latent effects. What
  does an experimenter do when a known law, not a family, fails on the
  data?
- **Section, diagnosis.** A falling-ball viscometer (stated synthetic
  world, apart from the agent's): spheres of one size and several
  densities fall at their terminal speed through an oil. Stokes' law says
  the terminal speed is proportional to the effective weight. The record
  rejects it; the residuals grow with the speed. Two diagnoses are fitted:
  a missing constant force (an offset of the weight) and an inadequate drag
  law. The missing force is rejected; the inadequate model is the
  diagnosis. A missing state, the third kind, is named with MD4 as the
  place where it is tested.
- **Exercise (D3's outcome, self-contained).** Two genuinely
  distinguishable extensions of Stokes' law, a quadratic correction of the
  drag and a power-law drag, each with two parameters, both consistent with
  the record; the discriminating experiment chosen where their predictions
  part most in units of the noise; readings there reject the power law; the
  remaining ambiguity stated: a three-parameter extension with a constant
  force also fits, and the force is bounded, not determined; nothing is
  said beyond the probed weights. D3's lesson (`modified-force-law`) is
  linked as depth from the prose and the header (`related`).
- **Prediction moment.** Before the discriminating readings: which
  extension predicts the faster heavy sphere?
- **Code shown.** The extensions (exact region: the object of the
  section); the choice of the experiment (exact); the drawing function as a
  Source link.

### MD8, `experimental-design-agent`: four strategies under one budget

- **Question.** The agent's design separated the models. Is choosing
  readings with a language model better than a fixed plan or a classical
  adaptive rule, under the same budget?
- **Rig.** A medium rig: a launcher of at most 4 m/s, where a good design
  of eight readings reaches the threshold and a poor one may not. The
  instrument's noise depends on a seed as well as on the arguments.
- **Strategies, eight readings each.** Scripted: a grid fixed before any
  reading. Classical adaptive: two opening readings, then each reading
  where the two models fitted so far disagree most (the sequential rule of
  Box and Hill). LLM: a fresh model session per seed, recorded. Hybrid: the
  model's first four readings of the same seed, then the adaptive rule.
- **Evaluator.** Every attempt is a record of the ledger of F137
  (`pbc.evidence`): the evaluator recomputes the readings from the
  arguments, the judge's outcome, and the resources (readings, messages);
  the session's own words are its unverified report. Correct: discriminated,
  in favour of the true model.
- **Uncertainty over seeds.** Five shared seeds for all four strategies;
  the success count with its exact interval (`success_interval` of AE5),
  the mean chi-square difference with its standard error, the median
  relative uncertainty of the parameter. The two strategies without a
  model also over forty seeds, to show how wide five seeds leave the
  interval.
- **Counterintuitive point.** On five seeds the intervals overlap: the
  comparison cannot rank the strategies by success, even where their mean
  differences differ.
- **Prediction moment.** Before the table: which strategy has the
  largest chi-square difference on average, and can five seeds rank them?
- **Code shown.** The adaptive rule (exact: its control flow is the
  point); the hybrid (exact); the evaluation of one attempt (exact
  selection); the drawing function as a Source link.
- **Unchanged.** The two authored runs, their assessments, the threshold,
  the exercises.

### MD9, `generalisation-to-unseen-systems`: levels of transfer and a thermal case

- **Question.** The suite of the page mixes kinds of held-out world. Which
  kinds are there, and does the separation carry to a system that is not
  mechanical?
- **Levels.** Interpolation, new excitation, new parameters, new regime,
  structurally different system: each defined, with the worlds of the page
  placed in it (interpolation; heavier: new parameters; farther and closer:
  new regimes; orbits: another system).
- **Thermal case.** A small aluminium sphere cooling in air; a scripted
  discoverer sets the start temperature and reads the temperature at set
  times through the box's allowlist, at a fixed air temperature. It finds
  Newton's law of cooling, `dT/dt = -k (T - T_air)`. Five held-out thermal
  worlds: interpolation (an unprobed start), new excitation (air
  temperature that oscillates), new parameters (colder air), new regime (a
  start at several hundred degrees, where radiation is not linear), another
  structure (the sphere in a sheath, a second heat capacity). The trace of
  the discoverer's probes shows that none of them was probed.
- **Result.** The first three transfer within the tolerance; the new
  regime and the other structure fail, reported as results with their
  cause.
- **Prediction moment.** Before the table: which of the five fail?
- **Code shown.** The box's judge of a world (exact region); the trace
  check (exact); the drawing function as a Source link.

## Steps

1. This plan and the handoff note.
2. MD8: `pbc.agents.strategy_lab` and its tests; the harness of the
   recordings (outside the repository); five recorded sessions; the
   experiment module, the page section, the experiment tests.
3. MD4: `pbc.discovery.state_selection` and its tests; the experiment
   module, the page section, the experiment tests.
4. MD6: the experiment module, the page section and exercise, the tests.
5. MD9: `pbc.discovery.thermal_transfer` and its tests; the experiment
   module, the page section, the tests.
6. Front matter: one outcome per lesson for the new part; `related` of
   MD6 gains `modified-force-law`.
7. Documentation: the protocol, the architecture and project map entries.
8. Summary and completion record.
9. Verification, last: the changed tests and the lesson checks while
   working; `./scripts/verify.sh --base` with `VERIFY_JOBS=2` at the end
   (the front matter of four lessons changes). The complete
   `./scripts/verify.sh` is not run in the session (the Issue).

## Discoveries during the work

- **The search cannot reuse `sparse_regression`'s loop by extraction.**
  Extracting it into a helper would change what MD4's page shows of
  `sparse_regression` (an exact excerpt of the published function), so
  `state_selection.search` carries its own loop, and a test checks that it
  gives the published search's coefficients on (x, v).
- **Strategies as clients.** The scripted and adaptive strategies are put
  through `pbc.agents.loop.run` as clients that ask for one reading per
  message, so all four strategies share the allowlist, the budget, the
  message limit, and the judge.
- **The rig.** On the full rig of A4 every spread of start speeds clears the
  threshold by far; a launcher of 4 m/s gives a best eight-reading score of
  about fifty against the threshold of twenty-five, so designs differ.
- **Recordings.** Five fresh Opus sub-agents (2026-11-20), each given only
  the system prompt, the task, and the tool, sent every message through a
  harness command in the session's scratchpad (not committed), which ran
  the calls through `strategy_lab.tools(seed)` with `pbc.agents.loop.run`
  and wrote the fixture with `save_recording`. Each session used only that
  command (four calls each). One session stopped at seven readings.
- **Fixture names.** The lesson checks accept `replay-[a-z]+.json` only, and
  the evidence word `replay-<name>` likewise: the fixtures are named
  `replay-one.json` to `replay-five.json`.
- **MD6's world.** With a Schiller-Naumann drag as the truth the quadratic
  extension fails on the record; the world's drag is Stokes' term plus
  Oseen's inertial correction, and the fitted coefficient comes out close to
  Oseen's.
- **Thermal worlds.** The oscillating air equals the room's temperature at
  some instants, so a world states its still air explicitly instead of the
  trace check sampling the air.
- **A nested helper hid a new test from the trigger scan**: a `pytest.approx`
  line below a nested `def` inside a new test read as a tolerance added
  outside a test; the helper was inlined.

## Where the teaching skill changed the learning experience

- MD4: the section opens with what a state is ("what you need to know to
  say what happens next") before the coupled masses; the prediction (an
  error, a long sum, or a short equation?) is asked before the search's
  answer, where the counterintuitive point lies (the regression returns a
  tidy wrong equation); the witness pair is read physically (the second
  mass on opposite sides) so that the test names the cure, not only the
  failure; three symptoms are compared at the end and only one points to
  the cure.
- MD6: the three kinds of missing thing (state, force, form) are named
  before the example, and the example is a stated world so each conclusion
  can be compared with a truth; the residual pattern is read before the
  diagnosis, and the Reynolds number ties the diagnosis to physics the
  learner met in the drag lesson; D3's outcome is an exercise with a hint
  that makes the prediction (which extension predicts the faster heavy
  sphere) before the solution's table; the ambiguity is stated as three
  concrete open items, not as a disclaimer.
- MD8: the evidence kinds are stated at once (build-computed strategies,
  recorded sessions, recomputed readings); the prediction (which strategy
  has the largest margin, and can five seeds rank them?) precedes the
  table; the counterintuitive point, that five seeds cannot rank by success
  while the continuous margin does separate, is the conclusion, with forty
  seeds to show how slowly a rate's interval narrows.
- MD9: the five levels are defined first and the page's existing worlds
  placed in them before the new case, so the thermal case reads as filling
  the empty level (new excitation) and the prediction (which worlds fail)
  comes before the table; each failure is explained by the level's reason
  (radiation's share computed; the sheath as MD4's missing state).
- Code on the pages: the state test, the adaptive rule, the hybrid, the
  discoverer, and the trace check in full (their control flow is the
  point); the systems, the strategies' settings, the extensions, the
  choice of experiment, the judge, and the uncertainty over seeds as
  regions; every drawing function as a Source link (each read first: none
  computes a value the caption or the prose does not state; MD6's divides
  by Stokes' law fitted to the record, which the caption states).

## Out of scope

New pages; the discovery capstone; changes to D3's lesson; the
prerequisites of the four lessons; an external engine.
