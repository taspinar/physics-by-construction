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
An N-body environment follows when the N-body model exists (F69).

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
  the environment, and are never probed by the agent. A claim is scored on
  them against the noise-free law.
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
beside the protocol (for D1 to D3, `pbc.discovery.force_lab`), and a test
checks the two against each other.

## Cost

The **cost record** (model calls, tool calls, input and output tokens, money)
is written from the run that produced the trace, as that run measured it. A
count the run did not report is recorded as none, not as zero. A build never
measures a cost and never shows one as its own.

## Where a benchmark runs

A full benchmark (many seeds, conditions, worlds, and live models) is not part
of `scripts/verify.sh` and not in `scripts/verify.conf`. It runs on the
maintainer's machine and is marked "not verified" where shown. What is
verified is a small deterministic replay: one frozen trace per page, scored
again and compared with the baselines.

## Limits

Scores say how well a claim predicts outside the probed region of a simulated
system with a known law. They do not say that a law is true of nature, that an
agent would find it with another prompt, or that the ranking holds in another
environment. External benchmark assets are inspiration only and are not
embedded before their licences and assumptions are checked.
