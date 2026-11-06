# Autonomous Physics Lab

The product of the capstone SA9 of the path "Reliable scientific agents and
experiment automation" (ADR 022). This directory holds what a learner uses;
the reference code is the package `pbc.products.physics_lab` in `src/pbc`.
It is the vertical slice of F138: one protocol, end to end. The capstone
(F145) grows it to three protocols, campaigns, and the capstone page.

An educational and experimental tool, not a certified laboratory
instrument.

## Product brief

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

## Scientific acceptance criteria

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

## Run it

From a clone of the repository, after the one-time setup of
`docs/development.md`:

```bash
uv run --locked --extra physics-lab python -m pbc.products.physics_lab \
    run --input products/physics-lab/examples/frequency-response.toml \
    --out physics-lab-run
```

The simulated and recorded routes need nothing beyond the default
environment, so `--extra physics-lab` may be left out; it installs what the
optional routes need (today the provider SDK of a live agent run).

Choose the route and the execution mode:

- `--route baseline` (the default): the scripted sweep, no model;
- `--route agent`: the bounded agent, replayed from its trace in
  `fixtures/agent-frequency-response.json`; every recorded measurement is
  made again and must give the recorded result;
- `--mode simulated` (the default): the deterministic bench of
  `pbc.instruments.simulated`;
- `--mode recorded --sample <file>`: a recorded sample, replayed, never a
  new experiment. Until a measured RLC sample passes the dataset gate,
  write a synthetic one, declared as simulated:
  `python -m pbc.products.physics_lab sample --input <input> --out sample.json`.

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

Without the confirmation of the circuit the command records nothing and
asks the model nothing, and a run in which no measurement succeeded saves
no trace; both end with the reason and a nonzero exit status. So does
`sample` without the confirmation.

The committed traces were written by a deterministic scripted policy, not a
model, and say so (`"placeholder": true`).

## Example input

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
manual change that you confirm. There is no live adapter yet: real
hardware is decided by the one-instrument pilot (F140), and nothing here
claims that a physical circuit was measured.

## What is here

| Path | What it is |
|---|---|
| `examples/` | The example input |
| `fixtures/` | The product's one replay-fixture location (ADR 022 decision 8): the replay traces of the product's and the starter's agent route, and nothing else |
| `starter/` | The starter a learner copies into their own project; see its `README.md` |
