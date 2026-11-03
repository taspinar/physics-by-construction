# Discovery evaluation protocol

This is the protocol by which an agent, or a method without an agent, is
asked to discover a law of a physical system and is scored. The lessons of
the law-discovery and agent-benchmark paths follow it by name: **the
Discovery evaluation protocol**. `pbc.discovery` implements it on the agent
harness of ADR 004. It is a product document; it is not `docs/evaluation.md`,
which holds the review criteria of the development workflow.

The protocol says what a score means: how well a claim predicts settings the
agent could not probe, under a budget, recomputed by the build. It does not
say that the agent understood the physics, and a lesson does not claim so.

## The environment

An **environment** (`pbc.discovery.Environment`) wraps a model of `pbc` as a
system with

- **controls**, each with a name, a unit, and bounds;
- one **observation**, with a unit and the standard deviation of its noise;
- a **budget** of probes, a **reset** that makes it whole again, and a **seed**;
- a **hidden truth**: the law, its parameters, and the held-out settings.

No public attribute or method returns the truth. The only code that uses it
is the judge's `held_out_error`, which returns one number about a claim. The
noise is a function of the seed and the controls, so a probe repeated gives
the same reading and a replay is exact. A refused probe (unknown or
out-of-bounds control, spent budget) costs nothing.

The worked environments are the projectile (hidden gravity), the oscillator
(hidden stiffness), and the central force, whose law is modified: the force
falls as a hidden power of the distance, not necessarily the inverse square.
Two lessons add their own (F99): the gravity laboratory of D4 and the
three-body world of D5 ("Transfer" and "Unknown worlds" below).

## What the agent may do

Two tools (`pbc.discovery.environment_allowlist`): `measure`, which sets the
controls and returns the noisy observation, and `submit`, which states the
claim as the parameters of the environment's public family of laws. Nothing
else is allowed: no code execution, no file, no network, no judge call. A test
shows, for every environment, that no tool or tool description reaches the
hidden values, that names which would reach them are refused, and that the
prompts carry none of them. A page never shows the hidden values either.

## Conditions of prior knowledge

All three conditions use the same tools and submit the same parameters, so
their scores compare. They differ in the task text (`pbc.discovery.prompts`):

| Condition | The agent is told |
|---|---|
| `full` | the controls, the observation, and the form of the law |
| `partial` | the controls, the observation, and the names of the parameters to report |
| `none` | the controls and the observation only |

## Splits and held-out worlds

- **Probed settings** lie within the bounds of the controls.
- **Held-out settings** lie outside them (farther, faster, later), are fixed by
  the environment unless the protocol's `held_out` names others, and are never
  probed by the agent. A claim is scored on them against the noise-free law.
- A **held-out world** is a different hidden truth (another gravity, stiffness,
  or exponent) in the protocol's `world`. A benchmark that varies it states
  every world it ran.

## Budget, seeds, and the protocol object

A `Protocol` fixes the environment, the hidden `world`, the `budget`, the
`seeds` (one run each), the `tolerance`, the step limit, and the replay
tolerance. A result that depends on the noise is reported over all seeds, and
a failed seed stays in the table.

## Scoring

`score_transcript` takes the tool calls of a transcript and executes them
again on a fresh environment of the same seed and budget, applying the loop's
limit of calls per message (a call beyond it is refused unrun, as the loop
refused it). It counts the accepted probes and the refused calls, takes the last accepted `submit` as the
claim, and computes the **held-out error**: the root-mean-square difference
between the claim's prediction and the noise-free law on the held-out
settings, relative to the size of the observation there (to the amplitude for
the oscillator, whose displacement crosses zero). The law is **recovered**
when the error is at most the protocol's tolerance.

The score is a function of the calls and the environment. The agent's words and
the recorded tool results play no part, and a test recomputes the score from a
frozen trace. A run without a claim scores "no claim"; an unfinished run is
never reported as a recovery.

## Baselines

The same environment, the same budget, no agent (`pbc.discovery.baselines`):

- **random** and **grid probing**: the whole budget at random or regular
  settings;
- **least squares** (`pbc.data.fit.fit_curve`) of the environment's family to
  those probes, from several starts;
- **sparse identification**: sequentially thresholded least squares over a
  library of terms, in pure Python with NumPy.

Two baselines work on data rather than on an environment, and every later
discovery lesson can compare with them (F67, lessons D7 and D8):

- **symbolic regression over power laws** (`pbc.discovery.symbolic`): an
  exhaustive search of the products of the variables with exponents on a
  fixed grid, each fitted in logarithms; it chooses the simplest form whose
  chi-square passes the rule below, reports every form as good as the best
  (the forms the data cannot tell apart), and reports a failure when no form
  passes;
- **equations of motion from trajectories** (`pbc.discovery.equations`):
  velocity and acceleration from sampled positions by central differences or
  a Savitzky-Golay filter, and sequentially thresholded least squares over a
  polynomial library in position and velocity, with the singular values of
  the library as the test of whether the data determine the equation.

A baseline succeeds only when its chi-square is within three standard
deviations of what the noise gives and its parameters are determined. Otherwise
it reports why, and its claim is not a result: sparse identification fails on a
law that is not a sum of its terms, and least squares on a law outside its
family. Failures are shown beside the agent. No symbolic-regression library is
locked: PySR needs Julia and is never required (architecture, dependencies);
a pure-Python library such as PySINDy would be locked only with its licence
and weight recorded here, and neither F65 nor F67 adds one: the baselines
above use NumPy and SciPy, which are locked already.

## Comparability

Two scores compare only when nothing but the thing compared differs:
the same environment, the same hidden world and seeds, the same held-out
settings and tolerance, and the same number of probes **allowed**
(`pbc.discovery.benchmark.comparable`). The check reads the protocols of the
two entries, never the transcripts, and names what differs without its value.
A page that sets two scores side by side shows its verdict, and says what a
comparison it marks "not meaningful" measures instead. Examples of the
lessons EV2 and EV3: conditions across environments; a run against one of
another hidden world; a baseline given another budget.

A benchmark is a grid of environments and conditions, one protocol per
environment (`benchmark.GRID`): within an environment only the task text
differs, and across environments only the shared numbers (budget, step limit,
seed, tolerance) are equal, so its results are read per environment.

## The plain model

A **plain model** is the agent's model with the agent's task (the `partial`
task) and only the `submit` tool, so it states a claim without a probe
(`benchmark.plain_allowlist`, `plain_prompts`; its system prompt says that it
cannot measure). It is the control for what the probes add to what the model
knows. It is allowed no probe, so the comparability check marks its
comparison with the agent as one of different budgets: it measures the tools
and the probes together. Its run is replayed and scored with its own tools
(`score_transcript(..., tools=...)`), so a `measure` call it attempted would
be refused in the score as it was in the run.

## Invariants

A discovery of conserved quantities (lesson D13, `pbc.discovery.invariants`
and `pbc.discovery.invariant_lab`, F82) follows the same rules with a claim
of another kind: a candidate is a combination of a public library of terms of
the state, and no equation of motion is fitted or assumed.

- **The box** is a particle in a plane under a hidden force, integrated by its
  own method and step. The agent starts it from bounded starts, one of a
  budget of trajectories each, and reads the state at fixed times; a
  `variation` tool gives the conservation ratio of a candidate on the agent's
  own trajectories; `submit` states a candidate, a bounded number of them.
- **The conservation ratio** of a candidate is the root-mean-square change of
  its value about its mean on each trajectory, divided by the square root of
  the sum of each coefficient squared times the mean square of its term.
- **The verdict**, fixed before any run, is given on held-out starts (some
  beyond the bounds) at three integration settings: the box's own, half its
  step, and a reference (classical Runge-Kutta at a fine step). A candidate is
  an **invariant** when its ratio at the reference is at most the tolerance
  and its value differs between trajectories; an **identity** when it is
  conserved with one value on every trajectory; an **integration artefact**
  when it is conserved at the box's own setting only; a **coincidence** when
  it is conserved on its own trajectories only; otherwise **not conserved**.
- **The score** counts the independent invariants among the candidates
  against the number the box has in the library (the baseline's count at the
  reference, a number the judge returns and nothing else), recomputed from
  the tool calls on a fresh box.
- **The baseline** is the null space of the terms' changes, each column scaled
  by the size of its term, by the singular value decomposition, with the
  tolerance as its threshold; its candidates are judged by the same rules.

## Transfer

A law may be scored on a system other than the one probed (lesson D4,
`pbc.discovery.gravity` and `pbc.discovery.gravity_lab`, F99). The **gravity
laboratory** is an environment: the agent sets a source mass, a test mass,
and their distance and reads the attraction with noise; the claim is the
coefficient and the three powers of the public family
`G source_mass^a test_mass^b distance^-p`. Its held-out settings are not
settings of the controls but **orbits**: a light body about a fixed heavy one,
with masses and distances far outside the laboratory's, started at an apsis
with the velocity perpendicular to the radius. The environment's
`score_predictor` integrates each orbit under the predicted force and under
the hidden one (`pbc.astrophysics.central_force.orbit`) and returns the
root-mean-square relative error of the radial period; a law under which the
body escapes or does not come round twice in the window scores infinity. Any
force predictor transfers, so the baselines of this protocol are scored the
same way. Its protocol is a `Protocol` whose `make` builds the laboratory
(`GravityProtocol`), so that `score_transcript` scores it unchanged.

## Unknown worlds

A world of several bodies with hidden pair forces (lesson D5,
`pbc.discovery.worlds` and `pbc.discovery.world_lab`, F99) follows the same
rules with a box of its own, as the invariants do:

- **The world** holds three bodies of public masses; each pair attracts or
  repels along its line with `k_ij r^-p`, the couplings and the exponent
  hidden. Newton's gravity is the case `k_ij = G m_i m_j`, `p = 2`, and a test
  checks the accelerations against `pbc.mechanics.nbody`.
- **The tools**: `accelerations` places the bodies at rest within a box (no
  pair closer than a set distance; one of a budget) and returns their six
  noisy acceleration components; `submit` states the couplings and the
  exponent, the last claim counting.
- **The predictive test**: from held-out starts, positions and velocities
  some outside the box, the bodies are integrated under the claim and the
  hidden law (DOP853) and compared at fixed times; the error is the
  root-mean-square position error relative to the root-mean-square distance
  of the bodies from their centre of mass. The held-out starts are never
  drawn on a page.
- **The baselines** spend the same budget at random configurations: least
  squares of the family, sparse identification over whole powers of each
  pair's distance, and Newton's gravity with `G` fitted, each judged by the
  chi-square rule and scored by the same test.

## Noise, calibration, and faulty readings

Lesson D10 (`pbc.discovery.noise_lab`, F98) reads the central force through a
**faulty gauge**: Gaussian noise of a stated standard deviation, a hidden
constant offset, and, at a hidden fraction of settings, a fault of at least a
set size. The fault, like the noise, is a function of the seed and the
setting, so a repeated probe repeats it. The mass may be set to zero, where
the true force vanishes: the null reading is the calibration. The claim is
scored on the noise-free force without the offset. The task of
`pbc.discovery.prompts` gets one sentence about the gauge (its noise, and
that it may read with an offset and some readings may be faulty).

- **The calibrated robust fit** is a baseline of its own: the family plus an
  offset, fitted with a soft-L1 loss, the readings beyond a stated number of
  standard deviations of it dropped, and the rest refitted by weighted least
  squares and judged by the chi-square rule.
- **The failure analysis** runs every method on the grid of the gauge with
  one failure at a time (noise only, with the offset, with the faults, with
  both), so that each failure is matched to its remedy.
- **The degradation** runs every baseline (every method on the grid, and
  least squares and the calibrated robust fit on random settings drawn anew
  for each seed) at several standard deviations of the noise, the offset and
  faults held, over several seeds, and reports the median and largest
  held-out error and the seeds recovered.

## Latent effects

Lesson D11 (`pbc.discovery.latent_lab`, F98) hides effects rather than
parameters: a body falls under gravity, a constant force against the fall,
and linear drag, the last two hidden, and the claim names all three, an
absent effect as zero (condition `full`, with one sentence of the task saying
that the body may feel forces it cannot see).

- **Hypotheses** are members of the family with some effects held at zero,
  each fitted and judged by the chi-square rule and by whether the readings
  determine its parameters.
- **The observational record** is a fixed set of readings at one mass and
  short times, taken by the build: every hypothesis is consistent with it.
- **The rivals** of a record are the laws of a grid of the hidden effects,
  gravity fitted to the record, whose chi-square passes. **The
  disambiguating experiment** is the setting where the rivals' predictions
  spread most, in standard deviations of the noise.

## Generalisation

Lesson D12 (`pbc.discovery.generalisation_lab`, F98) challenges a claim on a
**suite of held-out worlds**, each with its own error, none in a tool, a
prompt, or a page: settings within the bounds that the run did not probe
(drawn with a fixed seed), distances beyond the bounds, test masses far
beyond them, orbits under the claimed force (radial periods, as in
"Transfer"), and distances below the bounds. The hidden law is the family
plus a short-range term below the noise within the bounds. The score is the
largest error of the first four worlds; the last is reported apart, since no
probe can reach it, and fails every claim of the family.

- **Never probed.** The trace is read probe by probe: every accepted probe
  lies within the bounds and on no held-out setting, and the page shows the
  nearest probe to each world in units of the controls' ranges. A test
  checks the same on the committed fixture.

## The frozen trace and the replay

A **frozen trace** (`pbc.discovery.save_trace`) is a directory with
`replay.json`, the replay fixture of ADR 004, and `trace.json`, which versions
the run: the protocol, the environment, the condition, the seed, the prompt
version and its SHA-256, the model, the date, and the cost record. The page
labels the model's messages as recorded output of that model on that date; the
scores, the tool results, and the comparison with the baselines are recomputed.
The replay needs no credential and no network.

A lesson commits only the fixture next to its page, because a lesson directory
holds nothing else (ADR 002): its `TraceInfo` is kept in the lesson's module
beside the protocol (for D1 to D3, `pbc.discovery.force_lab`; for D13,
`pbc.discovery.invariant_lab`; for EV2 and EV3, `pbc.discovery.benchmark`;
for D4 and D5, `pbc.discovery.gravity_lab` and `pbc.discovery.world_lab`;
for D10 to D12, `pbc.discovery.noise_lab`, `pbc.discovery.latent_lab`, and
`pbc.discovery.generalisation_lab`),
and a test checks the two against each other. A lesson may replay the
fixtures of another lesson's page (EV2 replays those of D1 and D2) through a
path constant of its experiment, so that the input digest of the lesson
covers them.

## Cost

The **cost record** (model calls, tool calls, input and output tokens, money)
is written from the run that produced the trace, as that run measured it. A
count the run did not report is recorded as none, not as zero. A build never
measures a cost and never shows one as its own.

## Where a benchmark runs

A full benchmark (many seeds, conditions, worlds, and live models) is not part
of `scripts/verify.sh` and not in `scripts/verify.conf`. It runs on the
maintainer's machine and is marked "not verified" where shown. What is
verified is a small deterministic replay: a few frozen traces per page (one
per cell of a benchmark grid), scored again and compared with the baselines.
No build or test calls a model: a replay needs no credential and no network,
and a test runs every replay with the network refused.

## The evidence contract

The Part B products extend this protocol with one minimal record that the
evaluator, not the candidate, fills (ADR 022 decision 6; the requirements'
"Data and persistence"). `pbc.evidence` implements it (F137); a product
depends on it only after the pilot below.

- **The task** (`RunRecord`): the task, the hypothesis, the assumptions, the
  protocol version, the data split in words (what is probed, what is held
  out, never the held-out values), the seeds, the budgets, the digests of
  the evaluator's code and of the configuration, and the environment (the
  interpreter, the libraries, the system).
- **Attempts** (`Attempt`): each attempt of a candidate in a development
  and evaluation cycle, with its status, its failure diagnostics, its raw or
  derived artifacts (a path and its SHA-256 when recorded), and the earlier
  attempts it follows. The status is one of *completed* (evaluated),
  *failed* (it ran and gave nothing to evaluate, such as no claim),
  *inconclusive* (evaluated, but the protocol cannot decide its outcome),
  *invalid* (its artifact is not what it claims to be or does not replay),
  and *missing* (its artifact is absent).
- **Evaluations** (`Evaluation`): what the evaluator recomputed from the
  artifacts: the correctness (undecided for an invalid, missing, or
  inconclusive attempt), the metrics, and the resource use counted from the
  artifacts, with the artifacts and digests it depended on and the
  evaluator's identity and version.
- **The candidate's report** (`CandidateReport`): what the candidate says
  about its attempt (its own score, log, diagnostics, or cost), stored apart
  from the evaluations and labelled *unverified*. It is never an evaluation;
  the summary only says whether it agrees with one, disagrees, or is
  *undecided* because the evaluation has no verdict to compare it with.
- **Claims** (`Claim`): a text, a scope, links to the runs that support it
  with the correctness the claim asserts for each, and links to its sources.
  Its evidence status is derived, never written: *failed* when a linked
  evaluation contradicts it or a linked artifact was invalid; *not
  evaluated* when a run is missing, unevaluated, or its evaluation was
  invalidated; *inconclusive* when an evaluation cannot decide or
  evaluations disagree; *completed* when every linked run agrees;
  *independently checked* when evaluators of different identities agree on
  every linked run. The first of these that any linked run has is the
  claim's.
- **The frozen candidate and the final evaluation** (`FrozenCandidate`,
  `FinalEvaluation`): the selected candidate of a cycle is frozen by the
  digest of its artifacts and a version. Its final evaluation, by a
  versioned evaluator, is bound to that digest and version, states the
  isolation it actually had, keeps its status and diagnostics as an attempt
  does (an invalid, failed, or inconclusive final evaluation stays in the
  record with its reason), and runs once per cycle. The ledger refuses a
  second final evaluation of the candidate in the cycle, a final evaluation
  of a candidate whose artifacts changed since the freeze, and a further
  attempt of a finally evaluated candidate in the same cycle: a change after
  the final evaluation starts a new development and evaluation cycle, with
  its reason recorded, a new version, and a new freeze. The earlier final
  evaluation stays in the record.
- **Invalidation** (`check`): every artifact an evaluation depended on is
  digested again; a changed or removed one invalidates that evaluation, the
  summary marks it, and a claim that rested on it becomes *not evaluated*.
- **The summary** (`summary`): every attempt, with its status, the
  evaluator's verdict, and whether the candidate's report agrees; the count
  of every status, zero included; the share of correct attempts over all
  attempts, so that an invalid, missing, failed, or inconclusive attempt
  lowers it instead of leaving it; every claim with its status; every final
  evaluation with its status, verdict, diagnostics, and validity; and every invalidation.

**A digest establishes identity, not scientific truth.** It says that an
artifact is the one evaluated and unchanged since, never that what it
records is correct: two files with the same wrong claim have the same
digest. Correctness comes from the evaluator's recomputation under the
protocol, and only within the protocol's scope (see "Limits"). A digest of a
configuration with a small hidden value can be inverted by trying values,
so a sealed evaluation keeps such a digest from the candidate.

### The pilot: the agent against the baseline of EV3

The contract was piloted on the projectile task of EV3
(`pbc.evidence.pilot`; protocol `f81-projectile-1` of
`pbc.discovery.benchmark`): find the hidden gravity from at most 20 noisy
range probes, scored on the protocol's held-out settings. The candidates are
the committed runs `projectile-full` (the agent told the form of the law)
and `plain-projectile` (the plain model without a `measure` tool), and the
baseline `grid + least squares`, which the evaluator runs itself. Each
evaluation replays the candidate's fixture with `benchmark.replay_cell`
(every tool call executed again, a recorded result that differs fails) and
scores it with `score_transcript`; the run's own cost record and last
message are its report. The pilot reads the fixtures where the pages hold
them and changes no page's output. It reproduces the outcomes of EV3: the
agent recovers the gravity, the plain model does not, the grid baseline
does.

**Isolation assumptions of the pilot task.** They are stated in the final
evaluation itself (`pilot.ISOLATION`):

- The candidate saw the system prompt, the task, and the tool
  specifications its fixture records, and the results of its own tool calls;
  the hidden gravity and the held-out settings reach no prompt, tool, or
  result (invariant I27).
- The hidden gravity and the held-out settings are in this repository
  (`pbc.discovery.benchmark.PROTOCOLS`): a candidate that can read the
  repository can read them. The evaluation is therefore not private and
  cannot show that an informed candidate never saw them. A test shows the
  consequence: a fixture that submits the hidden value without a probe is
  scored as recovered.
- The final evaluation scores on the protocol's held-out settings, the same
  as the development evaluation. It binds the result to the frozen candidate
  and its version; it is not an unseen test. (For this task an unseen split
  would add nothing: the relative error of a claimed gravity is the same at
  every setting.)
- Access to hidden values during a run and prior knowledge of the public
  problem are separate; the recording model's prior knowledge of projectile
  motion is not measured.
- Every tool result is recomputed by replay, so a fixture whose recorded
  readings were edited does not replay and is invalid.

### Decision record: the pilot (F137, 2026-11-02)

- **Decision: go.** The products may depend on `pbc.evidence` as it stands;
  a product extends it only where its own task needs more (a sealed final
  split, F150; recorded or live run records, F138).
- **Evidence.** The tests of `tests/unit/test_evidence_pilot.py` and
  `tests/unit/test_evidence_records.py`, on the committed fixtures of EV2
  and EV3 (copied before any change): a candidate that reports a held-out
  error of 0.001 and recovery fails, since the evaluator recomputes 0.39
  from its fixture and its claim's status is *failed*; a fixture with
  edited readings is *invalid* and its claim fails; resource counts come
  from the replay, not from the report; a changed or removed fixture
  invalidates the evaluations and the final evaluation that depended on it,
  visibly, and its claim becomes *not evaluated*; a ledger with one attempt
  of each status keeps all five in the counts, the rows, the text, and the
  denominator, and survives a save and a load unchanged; the final
  evaluation carries the frozen digest and version, a second one and one of
  a changed candidate are refused, and the change is recorded as cycle 2
  with a new version while the final evaluation of version 1 stays,
  marked invalidated.
- **What the pilot does not show.** It does not make an open teaching task
  private (the isolation assumptions above), and an evaluation of a
  candidate that read the hidden world passes. It covers simulated runs
  only; recorded and live runs, with their modes, devices, and
  calibrations, belong to the instrument contract (F138).
- **Cost.** No model call, no network, no new recording. One replay per
  evaluated attempt and one baseline fit: the whole pilot runs in under a
  second, and its tests in about one second, within the plan's limit of
  10 s. About 1,000 lines of code (the records and the ledger about 600,
  the pilot about 340) and 500 lines of tests; no new dependency.
- **Simplest viable implementation.** Frozen dataclasses in one ledger,
  SHA-256 over files and canonical JSON, the evidence status derived by one
  function, and JSON persistence with a format number: no database, no
  provenance or workflow framework, no service. The evaluator is the
  existing replay and judge; the contract adds only the records around
  them.

## Limits

Scores say how well a claim predicts outside the probed region of a simulated
system with a known law. They do not say that a law is true of nature, that an
agent would find it with another prompt, or that the ranking holds in another
environment. External benchmark assets are inspiration only and are not
embedded before their licences and assumptions are checked.
