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
| f0 (Hz) | 48927 | 50329 | -2.79 % |
| Q | 1.502 | 3.162 | -52.52 % |

Verdict: outside the tolerance (f0 within 1%, Q within 3%).

## Figure

![Two panels on a shared logarithmic frequency axis. Top: the gain of the capacitor voltage over the source voltage, on a logarithmic axis; the measured points as round markers and the dashed line of the closed form of the declared circuit, from which the points depart (the table gives f0 and Q of both). Bottom: the phase in degrees, falling from near zero through minus ninety towards minus one hundred and eighty, markers and the dashed closed form. A dotted vertical line marks the estimated resonance.](frequency-response.svg)

Measured points against the closed form of the model; the dotted line marks the estimated resonance. The channel noise is stated in the run record; no per-point uncertainty is estimated, so no band is drawn.

## Points

| Frequency (Hz) | Gain | Phase (degrees) |
|---|---|---|
| 5000.0 | 1.0056 | -2.93 |
| 6799.5 | 1.0131 | -4.10 |
| 9246.6 | 1.0264 | -5.77 |
| 12574.3 | 1.0520 | -8.19 |
| 17099.8 | 1.1040 | -11.99 |
| 23253.9 | 1.2112 | -18.73 |
| 31622.8 | 1.4282 | -33.43 |
| 43003.6 | 1.6297 | -69.23 |
| 44934.2 | 1.6048 | -76.28 |
| 46951.5 | 1.5580 | -83.40 |
| 49059.3 | 1.4925 | -90.43 |
| 51261.8 | 1.4102 | -97.24 |
| 53563.1 | 1.3169 | -103.64 |
| 55967.8 | 1.2197 | -109.57 |
| 58480.4 | 1.1208 | -115.00 |
| 79527.1 | 0.5621 | -141.12 |
| 108148.4 | 0.2773 | -153.24 |
| 147070.3 | 0.1418 | -159.25 |
| 200000.0 | 0.0754 | -162.17 |

## What this run does not show

It is one measurement of this circuit on this device. The closed form uses the declared values of the parts, not measured ones, so a difference from it shows the parts' tolerances and losses as well as the protocol. The result stays on this machine.

## Files

`raw.csv` (every sample), `points.csv` (the route's points), `run.json` (the run record), `evidence.json` (the evidence ledger), `frequency-response.svg` (the figure).
