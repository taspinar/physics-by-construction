# Frequency response of the prepared series RLC circuit

- Execution mode: live: live measurement on the learner's own instrument.
- Device or model: Digilent Analog Discovery 3.
- Route: scripted baseline (no model).
- Protocol: f138-frequency-response-1, seed 140, 19 points at 1 V.
- Status: completed.

## Result

Computed by the evaluator from the raw samples (`raw.csv`), compared with the closed form of the model, which the route never sees.

| Quantity | Measured | Closed form | Relative difference |
|---|---|---|---|
| f0 (Hz) | 50242 | 50329 | -0.17 % |
| Q | 1.484 | 3.162 | -53.08 % |

Verdict: outside the tolerance (f0 within 1%, Q within 3%).

## Figure

![Two panels on a shared logarithmic frequency axis. Top: the gain of the capacitor voltage over the source voltage, on a logarithmic axis; the measured points as round markers and the dashed line of the closed form of the declared circuit, from which the points depart (the table gives f0 and Q of both). Bottom: the phase in degrees, falling from near zero through minus ninety towards minus one hundred and eighty, markers and the dashed closed form. A dotted vertical line marks the estimated resonance.](frequency-response.svg)

Measured points against the closed form of the model; the dotted line marks the estimated resonance. The channel noise is stated in the run record; no per-point uncertainty is estimated, so no band is drawn.

## Points

| Frequency (Hz) | Gain | Phase (degrees) |
|---|---|---|
| 5000.0 | 1.0049 | -2.80 |
| 6799.5 | 1.0117 | -3.93 |
| 9246.6 | 1.0244 | -5.52 |
| 12574.3 | 1.0484 | -7.83 |
| 17099.8 | 1.0968 | -11.38 |
| 23253.9 | 1.1967 | -17.76 |
| 31622.8 | 1.4018 | -31.59 |
| 43003.6 | 1.6199 | -65.50 |
| 44934.2 | 1.6065 | -72.32 |
| 46951.5 | 1.5725 | -79.32 |
| 49059.3 | 1.5191 | -86.31 |
| 51261.8 | 1.4485 | -93.12 |
| 53563.1 | 1.3650 | -99.61 |
| 55967.8 | 1.2762 | -105.75 |
| 58480.4 | 1.1832 | -111.40 |
| 79527.1 | 0.6162 | -139.51 |
| 108148.4 | 0.3057 | -152.78 |
| 147070.3 | 0.1555 | -159.26 |
| 200000.0 | 0.0805 | -162.31 |

## What this run does not show

It is one measurement of this circuit on this device. The closed form uses the declared values of the parts, not measured ones, so a difference from it shows the parts' tolerances and losses as well as the protocol. The result stays on this machine.

## Files

`raw.csv` (every sample), `points.csv` (the route's points), `run.json` (the run record), `evidence.json` (the evidence ledger), `frequency-response.svg` (the figure).
