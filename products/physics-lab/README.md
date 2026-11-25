# Autonomous Physics Lab

The product of the capstone SA9 of the path "Reliable scientific agents and
experiment automation" (ADR 022). This directory holds what a learner uses;
the reference code is the package `pbc.products.physics_lab` in `src/pbc`.
It began as the vertical slice of F138, one protocol end to end ("The first
protocol" below); the capstone (F145) grew it into the product: three
protocols, campaigns, the agent route beside classical ones, and the
capstone page, `site/lessons/agents-llm/25-autonomous-physics-lab/index.qmd`.

An educational and experimental tool, not a certified laboratory
instrument.

## Product brief

You have a prepared electronic circuit on a bench: a function generator
drives it, and a two-channel oscilloscope records the source and the
response. The lab runs measurement campaigns on it, by a scripted sweep, a
classical adaptive policy, or a bounded agent, and every route reaches the
bench only through a guarded instrument that enforces a safety envelope, a
stop, and your confirmation of the circuit. Three protocols:

- **frequency response** of a series RLC circuit: gain and phase in the
  steady state, a weighted fit of the second-order response, f0 and Q with
  standard errors;
- **ring-down** of the same circuit after a step: the free decay fitted for
  its decay rate and damped frequency, f0 and Q with standard errors over
  repetitions;
- **amplitude response** of two LEDs of one colour in anti-parallel behind a
  resistor: the gain at the fundamental and the third harmonic against the
  amplitude, and the diodes' characteristic.

A quality gate refuses every capture that is clipped, has lost samples, is
undersampled, uncalibrated, or does not see the excitation; a refused
measurement is recorded, exported, retried once, and never fitted. Every
campaign exports its raw samples, a report with figures, a run record that
names the execution mode (simulated, recorded, or live), and the
evaluator's ledger; the evaluator recomputes every result from the raw
samples. The program never rewires a circuit; a different circuit is a
manual change that you confirm.

The requirements the lab meets, its choices, and the evidence for each are
on the capstone page.

## Scientific acceptance criteria

1. **Each protocol's own check on the simulator.** The frequency response
   and the ring-down each recover f0 and Q of the simulated circuit's closed
   form within three standard errors and within 1 % and 3 %; the fitted
   characteristic of the simulated LEDs gives n within 5 % and the voltage
   at 1 mA within 10 mV. The route never sees the closed form.
2. **The independent check of a real circuit.** On a recorded or live
   series RLC circuit, where the parts differ from their labels, the
   frequency response and the ring-down agree on f0 and on Q within two
   combined standard errors; for the LED pair, the characteristic fitted at
   the largest amplitude predicts the gain at every other amplitude within
   two combined standard errors. The closed form of the labels is not a
   check there.
3. **Invalid measurements.** A capture that fails the quality gate is never
   fitted, and `measurements.csv`, `raw.csv`, and `run.json` hold it with
   its reason.
4. **Refinement and repetition are recorded.** Every measurement names its
   stage (sweep, refine, retry, repeat) and the measurements it follows
   from; a checkpoint follows every measurement, and a resume accepts only
   the journal's latest checkpoint, unchanged, of the same plan, on the same
   bench, from an interrupted segment.
5. **Routes compared fairly.** An agent campaign on the simulator stands
   beside the adaptive policy and the scripted sweep on fresh benches with
   the same plan and seed, compared by the measurements each needed for the
   same interval width of f0.
6. **Reproducible.** The same plan and seed give the same raw samples,
   report, and figures; the reference workflow, `WORKFLOW.md`, runs from a
   clean clone with no device and no model account.

## Run it

`WORKFLOW.md` is the reference workflow, step by step. Its first step,
from a clone of the repository:

```bash
uv sync --locked --no-dev
uv run --locked --no-dev python -m pbc.products.physics_lab campaign \
    --plan products/physics-lab/examples/campaign-series-rlc.toml \
    --circuit-confirmed --out run-rlc
```

`--route adaptive` (the default), `scripted`, or `agent`; `--mode
simulated` (the default), `recorded --sample <export>`, or `live`;
`--resume` continues an interrupted campaign from its checkpoint in
`--out`.

## Example inputs

| File | What it runs |
|---|---|
| `examples/campaign-series-rlc.toml` | The campaign on the series RLC circuit of the RLC lesson: frequency response and ring-down, targets of the intervals, the budget, the seed |
| `examples/campaign-led-pair.toml` | The campaign on the LED pair: the amplitudes, the refinements, the declared resistor |
| `examples/live-campaign-series-rlc.toml` | The same two protocols on the pilot's breadboard circuit, for the live mode (a bench session of the owner, not yet run) |
| `examples/live-campaign-led-pair.toml` | The LED pair (two red LEDs behind 100 ohm) for the live mode (not yet run) |
| `examples/frequency-response.toml` | The first protocol alone, the slice of F138 (below) |
| `examples/live-pilot.toml` | The input of the physical pilot's live sweep, also for its recorded replay |

## Assessment

`RUBRIC.md` is the assessment rubric of a learner's lab or of a feature
added to it.

## The first protocol: the slice of F138

### Its brief

You have a prepared series RLC circuit on a bench: a function generator
drives it with a sinusoidal source, and a two-channel oscilloscope records
the source and the voltage across the capacitor. The lab measures the
circuit's frequency response and finds its resonance frequency f0 and its
quality factor Q, either by a scripted sweep or by a bounded agent that
chooses the frequencies itself. Every run exports its raw samples, a report
with the frequency-response figure, the instrument's run record, and an
evidence record in which an evaluator, not the route, computes the result.

The circuit is the one of EM5 ("RLC circuits and resonance"): L = 10 mH,
C = 100 nF, R = 100 ohm, so f0 = 1 / (2 pi sqrt(L C)), about 5.03 kHz, and
Q = sqrt(L / C) / R, about 3.16.

### Its scientific acceptance criteria

1. The phase of V_C / V_S crosses -90 degrees at f0; the run estimates f0
   there, between the two measured points that bracket it.
2. Q is estimated from the gains of those two points through the
   second-order response |H| = 1 / sqrt((1 - x^2)^2 + (x / Q)^2),
   x = f / f0.
3. The evaluator recomputes every point from the raw samples (`raw.csv`)
   and compares f0 and Q with the closed form of the circuit: f0 within
   1 % and Q within 3 %. The route never sees the closed form.
4. A run whose sweep does not bracket the resonance is inconclusive, not
   correct; a stopped or refused run is failed, and it keeps and exports
   what it measured.
5. The same seed gives the same raw samples, points, report, and figure.

### Run the first protocol

From a clone of the repository, after the one-time setup of
`docs/development.md`:

```bash
uv run --locked --extra physics-lab python -m pbc.products.physics_lab \
    run --input products/physics-lab/examples/frequency-response.toml \
    --out physics-lab-run
```

The simulated and recorded routes need nothing beyond the default
environment, so `--extra physics-lab` may be left out; it installs what the
optional routes need (today the provider SDKs of a live agent run).

Choose the route and the execution mode:

- `--route baseline` (the default): the scripted sweep, no model;
- `--route agent`: the bounded agent, replayed from its trace in
  `fixtures/agent-frequency-response.json`; every recorded measurement is
  made again and must give the recorded result;
- `--mode simulated` (the default): the deterministic bench of
  `pbc.instruments.simulated`;
- `--mode recorded --sample <file>`: a recorded sample, replayed, never a
  new experiment. A synthetic one, declared as simulated:
  `python -m pbc.products.physics_lab sample --input <input> --out sample.json`.
  The sample may also be the directory of a live run's export: the measured
  sweep of F140's pilot replays with
  `--mode recorded --sample data/samples/ad3-rlc-pilot/capacitor`
  and the pilot's input `examples/live-pilot.toml`;
- `--mode live`: your own Analog Discovery 3 ("Your own instrument" below).

The local interface shows the same on one page, on this machine only:

```bash
uv run --locked python -m pbc.products.physics_lab serve \
    --input products/physics-lab/examples/frequency-response.toml
```

and open <http://127.0.0.1:8765/>. It listens only on the loopback
interface; any other address is refused. It also refuses a request from
another web page or another domain: only its own page, which carries a
token made anew each time the interface starts, can start or stop a run.

To record the agent's trace with a model of your own, with your key in the
environment and never in a file:

```bash
uv run --locked --extra physics-lab python -m pbc.products.physics_lab \
    record --provider openai \
    --input products/physics-lab/examples/frequency-response.toml \
    --out my-trace.json
```

`--provider anthropic` records with Claude instead (the key in
`ANTHROPIC_API_KEY`, the model in `PBC_ANTHROPIC_MODEL`), and `--provider
local` with a model on your own machine behind an OpenAI-compatible server
such as Ollama (the model in `PBC_LOCAL_MODEL`, the server's address in
`PBC_LOCAL_BASE_URL`, which must be on this machine); `docs/products.md`
describes both.

Without the confirmation of the circuit the command records nothing and
asks the model nothing, and a run in which no measurement succeeded saves
no trace; both end with the reason and a nonzero exit status. So does
`sample` without the confirmation.

The committed traces were written by a deterministic scripted policy, not a
model, and say so (`"placeholder": true`).

### Its example input

`examples/frequency-response.toml`: the sweep's bounds, the coarse and
refinement points, the amplitude, the sampling, the seed, the agent's
budget, and `circuit_confirmed`, your confirmation that the prepared
circuit is connected. Without it the instrument refuses to switch its
output on. The command line confirms nothing for you: without `--input`,
give the confirmation with the flag `--circuit-confirmed`.

## Operating limits

The safety envelope is enforced by `pbc.instruments`, before anything
reaches the device, whatever asks for it: the scripted route, the agent, or
the interface.

| Quantity | Permitted range |
|---|---|
| Excitation amplitude | 0.01 V to 2 V |
| Excitation frequency | 100 Hz to 50 kHz |
| Sample rate | 1 kHz to 5 MHz |
| Samples per acquisition | 16 to 16384 |
| One device call | at most 10 s; then the output goes off and the instrument halts |

A stop request switches the output off at once and refuses every later
operation. The product never rewires a circuit: a different circuit is a
manual change that you confirm.

## Your own instrument (live mode)

The live mode drives a Digilent Analog Discovery 3 on your own computer,
the one device F140's physical pilot measured with (`docs/products.md`,
the pilot's record). It is optional; the site, the build, and CI never use
it.

1. Install WaveForms from Digilent; its SDK comes with it and is free to
   use with Digilent hardware. It is not a Python package. On macOS, copy
   `dwf.framework` from the WaveForms installer to `/Library/Frameworks`
   (the copy inside `WaveForms.app` finds no device), or set
   `PBC_DWF_LIBRARY` to the library.
2. Build the circuit on a breadboard: W1 → R → L → C → ground; scope 1+ at
   W1, 2+ between L and C, 1− and 2− at ground. The pilot's parts:
   R 100 ohm, L 1 mH, C 10 nF (f0 near 50 kHz).
3. Close WaveForms, connect the device by USB, and run, confirming the
   circuit yourself. The confirmation covers exactly the pilot's circuit,
   W1 → 100 ohm → 1 mH → 10 nF → ground, with at least 99 ohm in series:
   the 30 mA current bound assumes it, and the program prints it before it
   opens the device. The command line takes no other circuit; with less
   series resistance the bound does not hold. The bound is computed from
   the declared circuit, not measured: a wiring mistake (a short, a
   missing resistor) can draw more current than it says.

```bash
uv run --locked python -m pbc.products.physics_lab run --mode live \
    --input products/physics-lab/examples/live-pilot.toml \
    --circuit-confirmed --out physics-lab-live
```

The live envelope differs from the simulated bench's:

| Quantity | Permitted range |
|---|---|
| Excitation amplitude | 0.01 V to 2 V |
| Excitation frequency | 1 kHz to 200 kHz |
| Sample rate | 1 kHz to 20 MHz (the device realises 100 MHz over a whole number) |
| Samples per acquisition | 16 to 16384 |
| Source current | at most 30 mA: the amplitude over the circuit's declared resistance at its lower tolerance |

The evaluator compares your result with the closed form of the declared
parts. Real parts differ from their labels, and a coil has losses, so a
live run is often "not correct" against the nominal parts. The pilot's
dossier, `docs/datasets/ad3-rlc-pilot.md`, shows how to measure the parts
apart.

**If the lab crashes.** The adapter switches the generator off when it
closes, and a watchdog process switches it off when the lab is killed or
crashes. If the watchdog cannot (it was killed too, or the device did not
come back within a minute), the generator keeps its last setting, inside
the envelope. Start the lab again, which switches it off at once, or unplug
the USB cable. The lab refuses to start without a watchdog that reports
ready, and switches the generator on only while the watchdog runs. The
watchdog is a protection in software, not an emergency stop: unplugging
the USB cable is the one that does not depend on the computer.

## Build a feature of your own

`ROUTES.md` is how you build a feature of your lab from the starter: the
ring-down fit of the transient-response protocol, by the manual route (the
default, no coding agent and no model account) or, optionally, with a
coding agent, among them the guided route with Agent Codeyard at a pinned
revision. Each route is described with what its one pilot (F139) measured
and with its conditions; no workload is promised.

## What is here

| Path | What it is |
|---|---|
| `WORKFLOW.md` | The reference workflow on the simulator, step by step, with what each step writes |
| `RUBRIC.md` | The assessment rubric |
| `ROUTES.md` | The manual route and the guided routes for one feature of the starter, with the pilot's record |
| `examples/` | The example inputs |
| `fixtures/` | The product's one replay-fixture location (ADR 022 decision 8): the replay traces of the product's and the starter's agent route, and nothing else |
| `starter/` | The starter a learner copies into their own project; see its `README.md` |
