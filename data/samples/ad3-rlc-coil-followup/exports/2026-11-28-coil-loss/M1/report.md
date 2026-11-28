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
| f0 (Hz) | 50162 | 50329 | -0.33 % |
| Q | 1.486 | 3.162 | -53.02 % |

Verdict: outside the tolerance (f0 within 1%, Q within 3%).

## Figure

![Two panels on a shared logarithmic frequency axis. Top: the gain of the capacitor voltage over the source voltage, on a logarithmic axis; the measured points as round markers and the dashed line of the closed form of the declared circuit, from which the points depart (the table gives f0 and Q of both). Bottom: the phase in degrees, falling from near zero through minus ninety towards minus one hundred and eighty, markers and the dashed closed form. A dotted vertical line marks the estimated resonance.](frequency-response.svg)

Measured points against the closed form of the model; the dotted line marks the estimated resonance. The channel noise is stated in the run record; no per-point uncertainty is estimated, so no band is drawn.

## Points

| Frequency (Hz) | Gain | Phase (degrees) |
|---|---|---|
| 5000.0 | 1.0052 | -2.81 |
| 6799.5 | 1.0120 | -3.94 |
| 9246.6 | 1.0246 | -5.53 |
| 12574.3 | 1.0486 | -7.85 |
| 17099.8 | 1.0972 | -11.42 |
| 23253.9 | 1.1977 | -17.82 |
| 31622.8 | 1.4032 | -31.69 |
| 43003.6 | 1.6224 | -65.68 |
| 44934.2 | 1.6074 | -72.51 |
| 46951.5 | 1.5731 | -79.57 |
| 49059.3 | 1.5189 | -86.54 |
| 51261.8 | 1.4477 | -93.38 |
| 53563.1 | 1.3631 | -99.86 |
| 55967.8 | 1.2741 | -105.97 |
| 58480.4 | 1.1810 | -111.61 |
| 79527.1 | 0.6139 | -139.62 |
| 108148.4 | 0.3046 | -152.94 |
| 147070.3 | 0.1545 | -159.18 |
| 200000.0 | 0.0818 | -162.52 |

## What this run does not show

It is one measurement of this circuit on this device. The closed form uses the declared values of the parts, not measured ones, so a difference from it shows the parts' tolerances and losses as well as the protocol. The result stays on this machine.

## Files

`raw.csv` (every sample), `points.csv` (the route's points), `run.json` (the run record), `evidence.json` (the evidence ledger), `frequency-response.svg` (the figure).
