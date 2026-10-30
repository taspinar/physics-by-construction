# Plan: F99 — Discovering gravity and unknown physical worlds (D4, D5), Issue #336

- Issue: #336 (source: `docs/roadmap.md`, F99); "Detailed implementation
  plan expected: yes, short".
- Branch: `feature/336-discovering-gravity-and-unknown`; base `fa0e51a`.
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 2 by its paths (two lessons, four new modules of
  `src/pbc/discovery`, two experiments, tests, docs). New code goes into new
  source files; no existing tolerance, budget, test, or check changes. A new
  lesson's own claims are no trigger.
- Gates: F61, F62, F64, F113 (the gates of this phase), F66, F69 (the N-body
  model `pbc.mechanics.nbody`), F91 (`pbc.astrophysics.central_force`)
  delivered.

## Design

Two format 2 lessons in `agents-llm`, methods `simulation` and `llm-agents`,
each with one recorded run, the baselines without a model, and the score
recomputed by the build from the tool calls.

| Dir | Id | Slot | Course |
|---|---|---|---|
| `14-discovering-gravity` | `discovering-gravity` | D4 | `mechanics` |
| `15-unknown-physical-worlds` | `unknown-physical-worlds` | D5 | `astrophysics` |

Original contained tasks inspired by GravityBench (D4) and DiscoverPhysics
(D5); no asset of either is used (`docs/roadmap.md`, external benchmark
assets).

### D4: gravity in the laboratory, tested on orbits

- **The laboratory** (`pbc.discovery.gravity.GravityEnvironment`, an
  `Environment`): the agent sets a source mass, a test mass (1 to 10 kg) and
  their distance (0.5 to 2 m) and reads the attraction with noise. The public
  family is `force = G source_mass^source_power test_mass^test_power
  distance^-exponent`; the hidden world is one member of it.
- **The transfer test** (the environment's `score_predictor`): a claim is
  never scored on forces. It is scored on a world the agent never probed:
  bound orbits of a light body about a heavy one (source masses of hundreds
  to thousands of kilograms, test masses outside the laboratory's, distances
  of tens of metres), integrated by `pbc.astrophysics.central_force.orbit`
  under the claimed law and under the hidden one. The score is the
  root-mean-square relative error of the radial period (start at periapsis
  to the next periapsis). A law under which the body escapes, or does not
  return within the integration window, scores infinity. Any force predictor
  transfers, so the sparse baseline's sum is scored the same way.
- **Protocol** (`pbc.discovery.gravity_lab`, a `Protocol` whose `make`
  builds the gravity environment): budget 20, step limit 12, seed 0,
  tolerance 0.05 on the transfer error, condition `partial`, the prompt of
  `pbc.discovery.prompts`.
- **What the lesson shows beyond the score**: laws that the laboratory
  cannot tell apart are told apart by the transfer. One parameter of the
  grid fit is held at a shifted value (in standard errors) and the others
  refitted to the same readings: the laboratory's chi-square rises slowly,
  the transfer error fast, and most for the source mass, whose range the
  orbits exceed the most.

### D5: an unknown three-body world

- **The world** (`pbc.discovery.worlds.PairForceWorld`): three bodies of
  public masses in a plane; each pair attracts (positive coupling) or
  repels with a central force `k_ij r^-p`. The couplings and the exponent
  are hidden; one pair repels, so the couplings are not proportional to
  the masses and the world is not gravity.
- **The agent's tools** (`world_allowlist`): `accelerations` (the six
  coordinates of a configuration within a box, bodies at least 0.5 m
  apart; returns the six noisy acceleration components; one of a budget of
  12) and `submit` (the three couplings and the exponent; the last one
  counts).
- **The predictive test**: from held-out starts (positions and velocities,
  some beyond the box) the claim's world and the hidden world are
  integrated (DOP853), and the positions compared at fixed times; the error
  is the root-mean-square position error relative to the root-mean-square
  distance of the bodies from their centre of mass. The truth, the held-out
  starts, and the judge are in no tool; a test shows it.
- **Baselines** (same budget, random configurations): least squares of the
  family (`pbc.data.fit.fit_curve`), sparse identification over whole
  powers of each pair's distance, and the familiar law, Newton's gravity
  (`k_ij = G m_i m_j`, `p = 2`) with G fitted, which the chi-square rejects.
- **Protocol** (`pbc.discovery.world_lab`): budget 12, step limit 12, seed
  0, tolerance 0.05, condition `full` (the form of the pair force is told;
  the couplings and the exponent are not).

## Recording

As in F66, F81, F82: no provider key is available, so each run is recorded
by a Claude model in this Claude Code session: a fresh sub-agent per run,
given only the system prompt, the task, and the tool specifications, which
reads the results the harness computed from a file and answers with its
next message. The fixtures' `model` field and the pages say so; a
maintainer may replace them with `--record`. Per the owner (2026-10-29),
Opus, not Fable, for the law-discovery lessons.

## Visual deliverables

Scientific figures only, `simulated`, drawn by `draw_` functions of the
experiments from the tested code, colours from `FIGURE_COLOURS` with marker
or line style as well, alt text without computed values.

Skills: pbc-scientific-visualization@a70b501

- D4 `fig-transfer` (preview): the transfer error (log scale) against the
  shift of one parameter of the laboratory fit, in standard errors, the
  others refitted, one line style per parameter; the tolerance as a line.
  No hidden value or held-out setting is drawn.
- D5 `fig-predictive-test` (preview): the relative position error of each
  claim (agent, least squares, sparse, Newton) against time on the
  held-out starts, log scale, the tolerance as a line. No held-out
  trajectory is drawn, since it would print the held-out starts.
- Validation: the tables of the same pages print the quantities and the
  experiments' tests assert them. Fallback: the alt text and the tables.

## Steps

1. `pbc.discovery.gravity` (environment, transfer judge, library) and
   `pbc.discovery.gravity_lab` (protocol, run record, replay, sensitivity,
   live main) with unit tests.
2. `pbc.discovery.worlds` (world, tools, judge, baselines) and
   `pbc.discovery.world_lab` (protocol, run record, replay, score, main)
   with unit tests.
3. Record the two runs; commit `replay.json` next to each page.
4. The experiments `pbc.mechanics.experiments.discovering_gravity` and
   `pbc.astrophysics.experiments.unknown_physical_worlds`, their tests, and
   the two pages.
5. Docs: `docs/discovery-protocol.md` (transfer, N-body worlds), the
   authoring guide's "Discovery lessons", `docs/project-map.md`.
6. Verification: `./scripts/verify.sh --base` (new lessons).

## Discoveries during the work

- **New modules, not edits.** The gravity environment is in a new module
  (`pbc.discovery.gravity`) with its own `GravityProtocol`, rather than in
  `environment.ENVIRONMENTS`: the registry is parametrised over by the tests
  of F65 and the benchmark of F81, which list the hidden values of each
  environment, and the new environment needs a transfer judge they do not
  have.
- **The transfer's sensitivity.** With the speed at the start held, the
  period of an orbit changes by more than the strength of the law, the more
  so near escape. The orbits were set to be well bound (amplification
  nearly three) before any run.
- **Recording.** Both runs on 2026-10-29 by fresh `claude-opus-5-5`
  sub-agents that wrote each message to a file and read each result from the
  file the harness wrote; no result was copied by hand. D4: five messages,
  thirteen calls, recovered; the agent rounded its coefficient onto the
  hidden one (three significant figures), so its transfer error is exactly
  zero, which the page states with the fit to its readings. Learning from it,
  the D5 world was given couplings and an exponent of three significant
  figures and non-round values before its run. D5: three messages, five
  calls, recovered with four of twelve configurations.
- **The D5 held-out starts** were first set by hand and brought two bodies
  within a tenth of a metre (a near collision, making the test depend on the
  integration); they were replaced, before the run, by starts drawn with a
  fixed seed that keep every pair more than two metres apart for the four
  seconds.
- **Integration errors.** `np.errstate(all="raise")` made every integration
  fail on an underflow; only overflow, division, and invalid values raise.
