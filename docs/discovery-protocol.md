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
for D4 and D5, `pbc.discovery.gravity_lab` and `pbc.discovery.world_lab`),
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

## Limits

Scores say how well a claim predicts outside the probed region of a simulated
system with a known law. They do not say that a law is true of nature, that an
agent would find it with another prompt, or that the ranking holds in another
environment. External benchmark assets are inspiration only and are not
embedded before their licences and assumptions are checked.
