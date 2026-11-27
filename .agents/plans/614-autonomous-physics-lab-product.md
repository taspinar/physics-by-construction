# Plan: F145, the Autonomous Physics Lab, part 1: the product (Issue #614)

Source: `docs/roadmap.md`, F145; the change request section 3.1 (B1.C);
requirements decision 42 and use case 12; ADR 022 (decisions 5 and 8);
ADR 007 (declared datasets); ADR 004 (replay); the Issue's "Owner's start
(2026-11-24)", its refinements, the owner's parts, the session
instructions for part 1, and the reference solution of the ring-down fit
in the Issue's comment. Written by the implementer at the start of part 1
(the Issue expects a detailed plan and none existed).

Part 1 is the product, criteria 2, 3, 4 and 6. Part 2 (the page SA9 and the
complete `products/physics-lab/`, criteria 1 and 5) waits for part 1 and
F139 (#613); its instructions are added to the Issue when it starts. Part 1
changes nothing under `products/physics-lab/starter/` and none of the route
documents of `products/physics-lab/`.

## Risk

**Level 3 by assessment: the safety boundary (I34).** The transient
protocol needs a step excitation that `Driver` does not offer (sine only).
The contract gains a second waveform, a square wave between 0 V and the
amplitude, in `pbc.instruments.contract`, the three adapters, and the
conformance suite together. That changes what a driver may output, which
the session instructions assess as Level 3. Approval request
`.agents/approvals/614.md`. The limits stay in `pbc.instruments`: the
envelope names the waveforms it permits (`Envelope.waveforms`, default sine
only, so every existing envelope refuses the square wave unchanged), the
instrument refuses a waveform the envelope or the driver does not permit
before any driver call, and the current bound keeps its form: a step of
height A into a series RLC circuit drives at most A / R (the step response
peaks at (A / (Q R)) e^(-alpha t*) <= A / R for Q >= 1/2, and at A / R
when overdamped), and through the LED pair at most A / R (the diodes only
take voltage away). The square wave is never below 0 V or above the
amplitude, so no new range is permitted. Both statements are model-based,
as the bound already is, and assume the declared passive circuit; a step
train whose half period is shorter than a few decay times adds the
previous ring to the next step, so the protocol keeps the half period at
least `MIN_HALF_PERIOD_DECAYS` decay times of the declared circuit and the
live envelope's square-wave frequency range stays at the sine's.

**No dependency change in part 1.** The Claude client is written on the
standard library's `urllib.request` inside `pbc.agents.clients`, which is
the one package allowed a network import, so `pyproject.toml` and `uv.lock`
do not change. If that proves impossible the client moves to its own small
pull request (the Issue's instruction).

Other paths: new modules under `src/pbc/products/physics_lab/` and
`src/pbc/electromagnetism/`, changed `pbc.instruments` modules, new unit
tests, product fixtures at `products/physics-lab/fixtures/`, example inputs
at `products/physics-lab/examples/`, `docs/products.md`,
`docs/architecture.md` (sensitive), `docs/project-map.md`. No ADR, CI
workflow, check of `scripts/verify.conf`, lesson page, lesson experiment,
or existing tolerance changes. The conformance suite's existing `CHECKS`
are kept as they are, because SA3 ("Connecting simulators and instruments")
shows their findings; the waveform checks are a separate tuple.

Verification: the full `./scripts/verify.sh` is the Level 3 tier and is
not run in the session (the owner's rule and the Issue's instruction); the
session runs the changed tests, `--only` groups, and `--targeted`. The
full run is the script's after the session, or CI's (`pr_ci`).

## Skills

Skills: impeccable@08d5b47, frontend-design@dbd4588, pbc-scientific-visualization@a70b501
Skills: none (part 1 changes no lesson's teaching; ADR 023 decision 2: not applicable; part 2 selects pbc-physics-teaching)

| Deliverable | Class | Skills | Validation | Accessible fallback |
|---|---|---|---|---|
| The local interface: configuration of a campaign (circuit, protocols, route, mode), progress, results per protocol with intervals, invalid measurements and failures with what to do, stop | Page and layout (a thin server-rendered page of the standard library, no JavaScript toolchain, ADR 022 decision 5) | impeccable, frontend-design | `interface.App.handle` tests without a socket; the page read at desktop and phone width | every result is also a table; the figures have alt text |
| The ring-down figure: the response after the step, the fitted curve, the envelope e^(-alpha t) | Scientific figure, per execution mode | pbc-scientific-visualization | the curve is the fit's, recomputed by the evaluator from `raw.csv` | alt text; the table of alpha, f_d, f0, Q with standard errors |
| The amplitude-response figure of the LED pair: fundamental gain and third-harmonic ratio against amplitude, with the held-out prediction | Scientific figure | pbc-scientific-visualization | recomputed from `raw.csv`; the prediction from the fit on the largest amplitude only | alt text; the table per amplitude |
| The consistency figure: f0 and Q of the two protocols with their intervals | Scientific figure | pbc-scientific-visualization | the intervals of the two fits; the verdict computed, never asserted | alt text; the verdict table |
| The frequency-response figure | Kept from F138 | (unchanged) | unchanged | unchanged |

## The three protocols and their independent checks

The three are distinct in physics: a linear system in the frequency domain
(steady state), the same linear system in the time domain (free decay
after a step), and a memoryless nonlinearity in the amplitude domain.

1. **Frequency response** (F138's protocol, kept). New: an interval for f0
   and Q from a least-squares fit of the complex transfer function
   H(f) = k / (1 - x^2 + j x / Q), x = f / f0, to every valid point, with
   standard errors from the covariance scaled by the residuals
   (`resonance.py`). F138's bracket estimator stays the route's own
   estimate and the evaluator's F138 check is unchanged.
2. **Transient response** (`transient.py`). The source is a square wave
   between 0 V and A at a frequency low enough that each half period holds
   many decay times; one acquisition spans one whole period of the square
   wave. The rising edge is found on the source channel; the response from
   just after the edge to the next edge is fitted by the reference
   solution of the Issue (v_inf + e^(-alpha t)(a cos omega_d t + b sin
   omega_d t), nonlinear least squares started from the spectrum and a
   coarse search), giving alpha, f_d, f0 = sqrt(omega_d^2 + alpha^2) / 2 pi
   and Q = omega_0 / 2 alpha with standard errors. Repetitions are
   combined by their weighted mean, with the spread compared with the
   standard errors.
3. **Amplitude-dependent response of a bounded nonlinear example**
   (`nonlinear.py`, model `pbc.electromagnetism.led_pair`). W1 -> R -> two
   LEDs of one colour in anti-parallel -> ground; channel 2 across the
   pair. At each amplitude A (sine, 1 kHz) the fundamental gain
   G1(A) = |V_1| / A and the third-harmonic ratio h3(A) = |V_3| / |V_1| of
   the pair's voltage. Below the LEDs' conduction the pair is an open
   circuit (G1 = 1, h3 = 0); above it the voltage is held near the forward
   voltage (G1 falls, h3 grows).

| Protocol | Simulator's check | Live and recorded routes' check |
|---|---|---|
| Frequency response | f0 and Q against the closed form of the simulated circuit (F138's 1 % and 3 %), and the interval covers the closed form | agreement with the transient protocol on the same circuit within the combined interval (below) |
| Transient | f0 and Q against the closed form within their intervals (k = 3) and within F138's tolerances | agreement with the frequency response within the combined interval |
| Nonlinear | the static characteristic fitted from the samples (n and I_s of v = n V_T asinh(i / 2 I_s), i = (v_s - v) / R) against the simulated LEDs' declared values; the simulator solves the implicit circuit equation per sample by bracketing, the check reads the samples only | a held-out prediction: the characteristic fitted on the largest amplitude predicts G1 at every other amplitude (solved over a period), compared with the measured G1 within their standard errors plus a stated model allowance |

**The consistency check** (`consistency.py`): two estimates agree when
|a - b| <= k sqrt(se_a^2 + se_b^2), k = 2 stated in the result, for f0
and for Q separately. The nominal closed form is the simulator's check only;
on the pilot circuit it fails (F140: L about 0.86 mH, C about 14.5 nF, a
coil loss that depends on frequency). The discrepancy between the ideal
model and `ad3-rlc-pilot` is shown from the declared dataset as it is,
without a resolution (no resistance reference is measured: reserved for
F155, RR8).

## The contract extension (Level 3)

- `pbc.instruments.contract`: `SINE`, `SQUARE`, `WAVEFORMS`;
  `Envelope.waveforms` (default `(SINE,)`), in `describe`;
  `Instrument.excite(amplitude_v, frequency_hz, waveform=SINE)`: an unknown
  or not permitted waveform is `OutOfEnvelope` before the driver; a
  driver that does not declare the waveform (`waveforms` attribute, default
  sine only) is refused before any call; a sine is sent as
  `set_output(a, f)`, as before, so drivers written for sine only (SA3's
  and SA4's lesson drivers) keep working unchanged; a square wave as
  `set_output(a, f, waveform=SQUARE)`. The snapshot names the waveform.
- `simulated`: the RLC bench integrates a square drive piecewise between
  its edges (the state carried across), so that no edge falls inside an
  integration step; a new `SimulatedLEDBench` over
  `pbc.electromagnetism.led_pair` (sine only).
- `recorded`: `RecordedCapture.waveform` (default sine, so the committed
  samples and `ad3-rlc-pilot` load unchanged); matching includes it.
- `analog_discovery`: `FUNC_SQUARE`; amplitude A / 2 and offset A / 2, so
  W1 stays within 0 V to A; the calibration statement names both
  waveforms. Shown on the fake SDK; the device is the owner's bench.
- `channels.ImperfectChannels`: passes the waveform through.
- `conformance`: `CallLog` passes it; `WAVEFORM_CHECKS` with
  `check_waveforms`: the square wave on the source channel (low level near
  0, high level near A, edges at the frequency), a waveform the envelope
  does not permit refused before the adapter, and a driver that does not
  declare it refused before any call. `CHECKS` unchanged.

## The measurement-quality gate

`quality.py` wires `pbc.electromagnetism.measurement.quality` into every
protocol: each capture's two channels are checked (clipping at the
declared rails of the execution mode, lost samples, the Nyquist rate,
calibration as declared) before a number is read. An invalid capture is
recorded with its flags and its raw samples, exported, counted, and never
fitted; the campaign re-measures it once (a repetition) and records both.
Example invalid causes in the simulator: `ImperfectChannels` with
dropouts or a small full scale (the clipping of a large ring-down).

## The campaign: plan, checkpoints, resume

`campaign.py`: a `CampaignPlan` names the circuit (declared topology: the
RLC circuit or the LED pair; a topology change is a new plan with a new
confirmation, never automatic), the protocols in order, each with its
settings, the repetitions, the target interval widths, and the budget of
measurements. Execution is step by step through the guarded instrument;
after each measurement a checkpoint (the plan's digest, the measurements
so far, their raw-data digest) is written; a stop ends the segment with
the output off and the measurement in flight discarded; `resume` accepts
only the latest checkpoint of the same plan and bench, unchanged, from an
unfinished campaign (the rule of F143's SA6 campaign, written for the
product, not imported from a lesson module). Refinement: the frequency
response bisects the -90 degree bracket and adds points near f0 until the
interval of f0 is below its target; the transient protocol repeats until
the interval of Q is below its target or the budget ends; the nonlinear
protocol adds amplitudes between the two where G1 changes most.

**The comparison of routes** (`policies.py`): for the frequency response,
the scripted sweep, the classical adaptive policy, and the agent are
compared by the number of measurements each needs to reach the same
interval width of f0 (the width each reached at its end, and the count at
which each first reached the common target).

## The export

A campaign's directory: `raw.csv` (every sample of every acquisition, with
the protocol, the step, the waveform, valid or not), `measurements.csv`,
`invalid.csv`, `report.md` with the figures, `run.json` (the run record
with the execution mode of each segment, the plan, the checks, the
consistency verdict), `evidence.json` (the ledger of `pbc.evidence`), and
`checkpoints/`. The evaluator recomputes every number from `raw.csv`.
The evidence package names the execution mode of every run in it.

## The interface

`interface.py` grows from F138's page, still one server-rendered page of
the standard library with the same loopback, Host, Origin, and token
rules: the campaign's configuration (circuit, protocols, route, mode), its
progress (step n of m, the current protocol), the results per protocol with
intervals, the consistency verdict, invalid measurements and failures with
what to do, the stop, and the export.

## The agent campaigns: recording and replay

- The agent's tools are one allowlisted tool per protocol
  (`measure_point`, `measure_ringdown`, `measure_amplitude`), each bounded by
  the envelope and returning the gate's verdict with the numbers, never the
  circuit's values. A campaign's trace is its replay fixture at
  `products/physics-lab/fixtures/`; the build re-executes every recorded
  tool call against the recorded bench (simulated, seeded; or a declared
  dataset for a live campaign).
- Clients: the existing OpenAI client; a Claude client
  (`pbc/agents/clients/anthropic_messages.py`, standard library HTTP, key
  from `ANTHROPIC_API_KEY`); a local open-weights model through the same
  interface (an OpenAI-compatible local server, base URL from the
  environment), tried by the owner; failure to hold the tool protocol is a
  result, not a criterion.
- The command records a campaign, counts the tokens of every call, and
  writes the spend at the prices the owner gives on the command line, and
  stops at the ceiling (EUR 50 for this capstone, counted across
  recordings in a ledger file the owner keeps outside the repository).
  The recordings are the owner's or the supervisor session's; the
  implementer holds no key and records none.

## Bench sessions the owner attends

No session opens the device. Each session is the owner's, with the
declared series resistance on the breadboard and WaveForms closed.

1. **RLC, two protocols, one wiring** (the pilot's circuit, unchanged): W1
   -> 100 ohm -> 1 mH -> node A -> 10 nF -> ground; scope 1+ at W1, 2+ at
   node A, both minus at ground. Commands: the frequency-response campaign
   and the transient campaign (square wave 0 to 1 V at 1 kHz), live; the
   export is declared as a dataset (card, dossier, gate) after the owner
   confirms CC BY 4.0 on the Issue.
2. **LED pair**: W1 -> 100 ohm (1 %) -> two red 5 mm LEDs in anti-parallel
   -> ground; scope 1+ at W1, 2+ across the pair. Amplitudes 0.2 to 2 V
   at 1 kHz; at 2 V the current is at most 20 mA (the bound A / R).
   Another colour needs a wider envelope, the owner's decision on the
   Issue.
3. **Optional, a live agent campaign** at the bench, on the same wirings,
   within the EUR 50 ceiling.

## Steps

1. Plan, approval request, handoff note.
2. The contract extension (contract, simulated, recorded, AD3 adapter,
   channels, conformance) with its tests.
3. The quality gate.
4. The transient protocol (fit from the reference solution) and its
   simulator check.
5. The frequency-response interval and the consistency check.
6. The LED-pair model, its simulated adapter, the nonlinear protocol and
   its checks.
7. The campaign (plan, checkpoints, resume, refinement, repetitions,
   invalid detection) and the comparison of routes.
8. The export and the report with the new figures.
9. The interface.
10. The agent tools, the recording command with the spend count, the Claude
    client, the replay of campaign fixtures, and placeholder fixtures of
    the scripted policy until the owner records real ones.
11. The command line, the example inputs.
12. Documents: `docs/products.md` (a section of F145 part 1),
    `docs/architecture.md`, `docs/project-map.md`, extended at the end of
    their rows.
13. Draft pull request; targeted verification.

## Out of scope

Automatic rewiring; a second device; a hosted service; any claim of
physical operation beyond F140's go; the coil-resistance measurement
(F155); the speaker (optional, below the live envelope's 1 kHz, the
owner's decision); the starter and the route documents (F139, part 2); the
page SA9 (part 2).

## Discoveries during the work

- **The Claude client is not part of part 1.** The project's Claude API
  guidance requires the provider's official SDK in a Python project, not a
  standard-library HTTP client; that is a dependency change
  (`pyproject.toml`, `uv.lock`, an optional group), which the Issue allows
  as its own small pull request. Part 1 delivers the provider-neutral
  parts: the recording command, the spend count over any client that
  reports its tokens (`MeteredClient`, `last_usage`; the OpenAI client now
  reports them), and the spend ledger. The Claude client is recorded as
  remaining. A local open-weights client (an OpenAI-compatible local
  server) was written and removed: the boundary tests of the agent package
  (`tests/unit/test_agents_boundary.py`,
  `tests/unit/test_coding_agent_boundary.py`) allow no module there but the
  provider client to read the environment or a key variable, and those
  tests are not weakened here; it needs its own change with that decision.
- **The consistency check lives in `estimates.py`** with the estimates and
  the comparison of repetitions; the plan's `consistency.py` is not a
  separate module. The consistency verdict is a table in the report and
  the interface, not a figure (a two-row comparison reads better as a
  table).
- **The plan declares the RLC circuit's nominal parts** (`inductance_h`,
  `capacitance_f`): the simulator's circuit, the closed form of its check,
  and the rule that a half period of the square wave holds ten decay times
  all come from them.
- **The held-out check cannot see a wrong declared resistor**: v_s = R i + v
  holds for any R with i = (v_s - v) / R, so a wrong R rescales the fitted
  saturation current exactly. It tests the model of the pair (symmetric,
  memoryless, of the Shockley form); two LEDs of different colours fail it.
- **The harness takes at most four tool calls per message**; the scripted
  placeholder policy sends its amplitudes in groups of four.
- **A campaign repeats settings** (the ring-downs), so the recorded adapter
  gains a `sequential` mode that answers each capture once, in order.
- **No separate `invalid.csv`.** An invalid measurement is a row of
  `measurements.csv` with `valid = 0` and its reason in `note`, its samples
  are in `raw.csv` with `valid = 0`, and `run.json` lists it under
  `invalid`; a fourth file would repeat them (triage of review 01, S1).
- **The ring-down figure draws no envelope curve e^(-alpha t)**: it shows
  the response after the step, the fitted damped oscillation, and the
  residuals; the fitted decay rate reaches the report as f0 and Q with
  their standard errors (triage of review 01, S1).
- **The agent route runs its baselines** (triage of review 01, M1): an
  agent campaign on the simulator also runs the adaptive policy and the
  scripted sweep on fresh benches with the same plan and seed, and its
  `run.json` (`comparison`) and `report.md` compare the three routes by the
  measurements each needed for the same interval width of f0
  (`lab.baseline_comparison`). A plan without a frequency response
  compares the measurement counts only; a recorded or live agent campaign
  has no baseline (it would need the circuit again).
- **A live recording needs the spend ledger** (triage of review 01, MIN2):
  `record-campaign --provider` refuses without `--spend-ledger`, and the
  metered client stops before a call that would cross the ceiling
  (estimated at the dearest call so far) and after a call whose usage the
  provider does not report.
- **The draft pull request** of the Issue's instructions is not opened in
  this session: the session's instruction is not to commit or push, and
  `scripts/finish-feature.sh` and `scripts/publish-feature.sh` do it.

# Part 2: the page SA9 and the complete `products/physics-lab/` (2026-11-25)

Source: the Issue's "Owner's start of part 2", "Scope of part 2", and
"Session instructions (part 2)"; ADR 022 decisions 3 and 5; F139's
narrower go (`docs/products.md`, the decision record of 2026-11-25).
Part 1 (802c4a9, #616), the clients (09d95b7, #617), and F139 (d15e1d8,
#620) are merged. Criteria 1 and 5, and 6 for this change.

## Risk (part 2)

**Raised to Level 3 by assessment during the work** (see "Discoveries
(part 2)"): the boundary test of the products, which no page could pass
before, is extended for the capstone. Before that, Level 2 by its paths: a new lesson page, a new experiment module
`src/pbc/electromagnetism/experiments/autonomous_physics_lab.py` and its
unit test, comment lines (`# region:`) in one product module for an
excerpt, the learner documents of `products/physics-lab/`, and
`docs/products.md` / `docs/project-map.md` extended at the end. No
dependency file, envelope, driver output, watchdog, stop, protected path,
ADR, CI workflow, verification check, tolerance, or skip changes; the
starter and `ROUTES.md` are not changed. A new lesson changes what other
pages show of the path (the header neighbours, the atlas, Home), so the
tier is `./scripts/verify.sh --base`; if it selects every lesson it is
stopped in the session and criterion 6 is recorded `pr_ci` pending.

## Skills (part 2)

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501

`impeccable` and `frontend-design` are not selected: the page uses the
site's lesson layout and the local interface gets no new layout.

| Deliverable | Class | Skills | Validation | Accessible fallback |
|---|---|---|---|---|
| The page SA9 | Lesson (capstone archetype) | pbc-physics-teaching | the lesson checks, the review of the rendered page | the site's lesson layout; every figure has alt text and a table beside it |
| `fig-frequency-response`, `fig-ringdown`, `fig-amplitude-response`, `fig-routes` | Scientific figures, `simulated` | pbc-scientific-visualization | drawn from the campaign's own records and the evaluator's fits; models dashed and apart; residual panel for the ring-down | alt text; the measurement, consistency, and comparison tables |
| `fig-pilot-discrepancy` | Scientific figure, `processed`, `fig-dataset: ad3-rlc-pilot` | pbc-scientific-visualization | the dataset's own reference figure (`pbc.data.reference.ad3_rlc_pilot.make_figure`, its declared provenance), drawn as the dossier draws it | alt text; the table of the recorded replay against the nominal closed form |

## Teaching decisions (pbc-physics-teaching)

- **Learner.** Has worked through SA1 to SA8 of the path (specification,
  verified code, the instrument contract, measurement quality, a bounded
  agent, campaigns, falsification, checkable reports) and EM5 (the series
  RLC circuit). Prerequisites in the front matter: the campaign lesson
  (SA6), the measurement-quality lesson (SA4), and the bounded agent (SA5).
- **Central question.** What has to be in place before a program, a person
  or an agent, may run experiments on a real circuit, and how does anyone
  know that the numbers it reports are right when there is no closed form
  to check them against?
- **Counterintuitive point.** The check that makes a simulator trustworthy,
  agreement with the closed form, is the wrong check for a real circuit: on
  F140's circuit it fails though the measurement is sound, because the
  parts are not what their labels say. The independent check of a real
  circuit is the agreement of two physically different protocols on the
  same circuit. Second point: an agent route that matches the adaptive
  policy shows nothing about a language model here, since the committed
  traces are scripted placeholders.
- **Archetype.** Engineering design or capstone (main), with the agent and
  evaluation archetype for the route comparison. The page opens with the
  brief and its credibility boundary, states requirements apart from the
  choices, and ends by walking the requirements one by one ("What the lab
  shows").
- **Moments.** (1) A prediction before the worked example "A circuit that
  is not what was declared": which of the two checks fails when the
  declared inductance and capacitance are off by the pilot's amounts?
  (2) The self-check after the route comparison: what the comparison shows
  about a model, given the placeholder trace.
- **Kinds of result.** Simulation outputs (the campaigns), derived
  properties (the closed form of the simulated circuit), a processed
  measurement (the pilot's sweep), and an inference about reality only
  where the pilot warrants it (the nominal model does not describe the
  circuit); claim labels and figure statuses mark them.

## The page's sequence

`site/lessons/agents-llm/25-autonomous-physics-lab/index.qmd`, id
`autonomous-physics-lab`, strand `agents-llm`, order 25, course
`electromagnetism`, slot SA9, methods `[simulation, measured-data]`
(no `llm-agents`: the page replays no model transcript; the agent route
is a scripted placeholder trace replayed through the product), format 2,
experiment `pbc.electromagnetism.experiments.autonomous_physics_lab`.

1. Opening: the question; the kind of evidence (every campaign is the
   build's, on the simulated bench; one figure and one table are the
   pilot's measured record; the agent traces are scripted placeholders);
   the sentence of the block.
2. Assumptions, the brief first (the requirements in words, then the
   choices), then the assumptions of the protocols.
3. Understand (`#explanation`): what lets an agent run real experiments
   safely: the instrument contract with its envelope and stop
   (`Instrument.excite`), the confirmed circuit (no rewiring), the quality
   gate, the three protocols and their independent checks, the evidence
   package, the evaluator; the lesson outcomes each product feature
   exercises (criterion 5).
4. Construct (`#code`): excerpts by region: one measured point
   (`resonance.analyse_point`, `point`), the step of a campaign
   (`Campaign.execute`, `execute`) and the sweep with its refinement
   (`run_segment`, `segment`; `next_step` shown whole), the ring-down fit
   (`ringdown.fit_ringdown`, `fit`), the nonlinear response
   (`nonlinear.analyse_amplitude`, `harmonics`; `predict_gain`, `predict`),
   the bounded tool (`agent_campaign.campaign_tools`, a new region `tool`
   around its one call into the campaign), and the evaluator
   (`lab.consistency`, `consistency`; `estimates.agreement`, `agreement`).
   The reader's own construction: the starter's ring-down fit by the
   manual route (an exercise).
5. Experiment (`#worked-examples`): the reference workflow on the
   simulator: (a) the series RLC campaign of
   `campaign-series-rlc.toml`, adaptive, with a link that loses a burst
   of samples in one acquisition (a refused measurement, its retry), the
   refinement, the repeated ring-downs; the measurement table, the
   frequency-response and ring-down figures, the simulator's checks and
   the consistency of the two protocols; (b) the LED pair of
   `campaign-led-pair.toml`: the amplitude-response figure, the
   characteristic, the held-out check; (c) the agent route replayed from
   its placeholder trace beside the adaptive policy and the scripted
   sweep, the comparison table and `fig-routes`; (d) a circuit that is
   not what was declared (the pilot's ratios of L and C and a coil loss):
   the closed-form check fails, the two protocols agree; (e) the pilot's
   record `ad3-rlc-pilot` (data card, the recorded replay through F138's
   protocol against the nominal closed form, the reference figure) shown
   as it is, without a resolution.
6. Explore and extend (`#extend`): the bench sessions not yet made (the
   transient protocol and the LED pair are simulator-only), the optional
   routes in one sentence pointing to `products/physics-lab/ROUTES.md`,
   ideas for extending the lab; "What the lab shows" walks the brief.
7. Limits, the self-check, the exercises, the last section (the product's
   commands in the `data` note of `reproduce_this`, inside "Setup and
   commands").

**Executed cells and time.** One `experiment.run()` in the header cell:
the RLC campaign (~3 s), the agent route with its two baselines (~4 s),
the LED campaign (~2 s), the mismatched circuit (~3 s), the pilot replay
and its figure (~2 s); the cold render is measured and must stay well
under 60 s.

**Exercises.** (1) The starter's ring-down fit by the manual route (the
commands not verified; the solution names the product's reference fit and
what the twelve tests check). (2) How many measurements each route needs
for the plan's own target width of f0 (`lab.needed` on the routes'
histories): the scripted sweep never reaches it.

## `products/physics-lab/` complete

`README.md` gains the brief of the whole product, its scientific
acceptance criteria (per protocol, with the checks), the example inputs
(every file of `examples/`), and a link to the two new documents:
`WORKFLOW.md`, the reference workflow on the simulator (the commands of
the fresh-clone run, in order, with what each writes and what to read in
it), and `RUBRIC.md`, the assessment rubric of a learner's lab. The
F138 parts of the README stay; `ROUTES.md` and the starter are unchanged.

## The fresh-clone run (criterion 1)

In a scratch directory, without a key in the environment and without a
device:

    git clone <repository> pbc && cd pbc && git checkout <this branch's commit or the working tree's copy>
    uv sync --locked --no-dev
    uv run --locked --no-dev python -m pbc.products.physics_lab campaign --plan products/physics-lab/examples/campaign-series-rlc.toml --circuit-confirmed --out run-rlc
    ... (the commands of WORKFLOW.md)

The session clones the local repository with its uncommitted part 2 tree
copied in (the branch is not committed by the session), runs the
commands, and records the commands and their output in the handoff note
for the Issue; the supervisor repeats it from the published branch and
posts it on the Issue.

## Discoveries (part 2)

- **The boundary test of the products** (`tests/unit/test_products_boundary.py`)
  held that no page imports `pbc.products` and that three experiments run
  the instrument contract; its docstring foresaw that F145's capstone page
  "changes this test with it". It now allows exactly the capstone page, its
  experiment, and `src/pbc/electromagnetism/pilot_record.py` to name the
  product modules of `CAPSTONE_PRODUCT_MODULES`, never `LIVE`, and checks
  that those modules reach no command line, local server, provider client,
  or live adapter through their imports. Assessed as Level 3 (a possible
  weakened test strength); approval request `.agents/approvals/614.md`.
- **Data use is followed by name across a whole module**, so the pilot's
  replay and figure live in `src/pbc/electromagnetism/pilot_record.py`;
  otherwise every figure of the experiment counts as made from the dataset.
- **The dataset's reference figure is not reused**: a 2x2 grid ten inches
  wide is unreadable on a phone, and it draws a second model (the parts
  measured apart). The page draws the measurement against the closed form of
  the labels alone, in stacked panels.
- **A docstring's ``` ``name`` (text) ``` is read as a unit by the site's
  excerpt check** even where the build does not take it for one:
  `estimates.agreement` said ``` ``a`` (from ``first``) ``` and failed
  the check; reworded. Fourteen other docstrings of the product have such a
  parenthesis, none on a page; recorded, not changed.
- **`reproduce_this` has no field for a product's commands**; they are in
  its `data` note, inside "Setup and commands" of the last section.

## Part 3: the bench datasets (2026-11-27)

The owner's decisions of 2026-11-27 on Issue #614 (issuecomment-7210910945): the two bench sessions are published, completely on Zenodo with a DOI and in part in the repository; the device serial becomes `AD3-001`; CI never depends on Zenodo; F155 is untouched. Not criteria of the Issue; the recorded model campaigns stay under `remaining`.

### Risk (part 3)

Level 3 by an escalation trigger no script detects (named in round 1 of the review of part 3, M1): a changed published scientific claim. SA9 replaces main's statements that only the frequency response has run on the real device, that the ring-down and the LED pair are simulator-only, that the two protocols' agreement on the real coil has not been measured, and that live support means the frequency response on the series RLC circuit, by live support for all three protocols and the measured results of the bench sessions; the Limits bullet changes with them. The owner's decisions of 2026-11-26 and 2026-11-27 release those measurements, with their failed checks; the owner's approval of the exact head decides the new statements (`.agents/approvals/614.md`). By its paths alone the part is Level 2: `src/` (a new module `pbc.data.publish`, a new reference module, `lab.py` and `__main__.py` of the product, `pilot_record.py` and two added numbers in the capstone's experiment), tests, data (a new card in the sensitive `data/registry/`, a new sample folder, a new declaration under `data/publish/`), docs, the page SA9's prose and one data card, and comments in two example plans. No dependency file, protected path, ADR, envelope, driver output, watchdog, stop, protocol or protocol version, precondition, tolerance, budget, or skip changes; no test is weakened. The pilot path `run` (`workflow.py`) is unchanged.

### Skills (part 3)

Visual deliverables: one scientific figure (the dataset's reference figure, `pbc.data.reference.ad3_bench_2026_11.make_figure`, status processed, no model drawn); the page SA9 gets prose and a data card, no new layout and no new figure.
Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501
Accessible fallback: the figure is a reference figure of the dossier, not shown on a page; the dossier states its content in its caption and tables.

### Decisions

- **One dataset** `ad3-bench-2026-11` (RLC and LED together): one device, one owner decision chain, one archive. It is about 3.3 MB of the 8 MB cap; the largest file, the RLC raw subset, is 1.6 MB of 2 MB.
- **The replay of the frequency-response subset.** The raw samples are filtered to protocol `frequency-response`, and the plan is narrowed to that protocol with `dataclasses.replace`. The adaptive route measures that protocol first, so the replay asks for the same 31 settings and gives the recorded fit exactly. No protocol changes.
- **The packager** `pbc.data.publish`. It replaces fields by key path, with the removed value read from the input. It rewrites JSON only in the `json.dumps` layout the file already has, and writes a deterministic ZIP (sorted, fixed time and mode). It checks the output for leaks: the removed values, the input path, and the home directory, inside the archive too. It writes MANIFEST.tsv with the original's SHA-256, a README, CITATION.cff, and zenodo.json, and has no network code.
- **The DOI** was a placeholder in `data/publish/ad3-bench-2026-11.toml` until the owner reserved 10.5281/zenodo.24578221 in the Zenodo draft (2026-11-27). The supervisor then filled it in and ran the packager again on the original exports. `tests/unit/test_data_ad3_bench_2026_11.py::test_the_archive_doi_is_the_reserved_one` asserts it in the declaration, the README, the citation file, and the card.
- **Bench conditions.** A live `run_campaign` adds `bench` (plugged_in, room_temperature_c, as given or "not recorded") and, where the driver has `conditions()`, `conditions_at_start` and `conditions_at_end` to the run record's configuration. The values come from the plan file's `[bench]` table (`lab.load_bench`) or from `--plugged-in` and `--room-temperature`. The simulated and recorded modes are unchanged.
- **SA9.** The sentences that said the ring-down and the LED pair were simulator-only now state neutrally what was measured, beside a data card of the new dataset. The two counts in the prose are computed from the dataset by `pilot_record.bench_sessions` and recorded by the experiment.

### Teaching (pbc-physics-teaching)

The page raised a question it could not answer: whether the two protocols agree on the real coil. The bench sessions now answer it in the same place, right after the pilot's record. That is the counterintuitive point of the page's independent check, made concrete on a real circuit: the protocols agree on f0 and not on Q, and the check fails. The new sentences keep the kinds of result apart (section 4 of the skill): measurements and the lab's checks on them are stated; no inference about a cause is drawn ("they warrant no statement about why").

### Discoveries (part 3)

- f0 agrees between the protocols in 25 of 27 campaigns, not in all (`2026-11-25-series-rlc` 2.91 combined s.e., `2026-11-26-series-rlc-run16` 2.14).
- The LED session's plug-in note (about 17:08 local) is after LED run 1's recorded start (16:07:48 UTC), so no minutes after plug-in are computed for the LED runs.
- The pilot's recorded f0 equals its −90° crossing interpolated in log frequency (47,008.7 Hz), so the crossing is the quantity comparable with the campaigns.
- The live measurement tables hold numbers from full-precision samples; a replay from `raw.csv` (12 significant digits) reproduces them to 1e-9 and the evaluations exactly.
