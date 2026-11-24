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
- **The draft pull request** of the Issue's instructions is not opened in
  this session: the session's instruction is not to commit or push, and
  `scripts/finish-feature.sh` and `scripts/publish-feature.sh` do it.
