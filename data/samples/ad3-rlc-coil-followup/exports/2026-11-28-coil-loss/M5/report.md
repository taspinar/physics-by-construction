# Frequency response of the prepared series RLC circuit

- Execution mode: live: live measurement on the learner's own instrument.
- Device or model: Digilent Analog Discovery 3.
- Route: scripted baseline (no model).
- Protocol: f138-frequency-response-1, seed 140, 13 points at 1 V.
- Status: inconclusive.
- Diagnostic: the phase does not cross -90 degrees within the sweep

## Result

Computed by the evaluator from the raw samples (`raw.csv`), compared with the closed form of the model, which the route never sees.

No estimate: the phase does not cross -90 degrees within the sweep

## Figure

![Two panels on a shared logarithmic frequency axis. Top: the gain of the capacitor voltage over the source voltage, on a logarithmic axis; the measured points as round markers and the dashed line of the closed form of the declared circuit, from which the points depart (the table gives f0 and Q of both). Bottom: the phase in degrees, falling from near zero through minus ninety towards minus one hundred and eighty, markers and the dashed closed form. A dotted vertical line marks the estimated resonance.](frequency-response.svg)

Measured points against the closed form of the model; the dotted line marks the estimated resonance. The channel noise is stated in the run record; no per-point uncertainty is estimated, so no band is drawn.

## Points

| Frequency (Hz) | Gain | Phase (degrees) |
|---|---|---|
| 5000.0 | 0.9918 | -2.50 |
| 6799.5 | 0.9886 | -3.50 |
| 9246.6 | 0.9824 | -4.80 |
| 12574.3 | 0.9719 | -6.57 |
| 17099.8 | 0.9534 | -9.10 |
| 23253.9 | 0.9133 | -13.23 |
| 31622.8 | 0.7974 | -20.33 |
| 43003.6 | 0.4508 | -16.26 |
| 58480.4 | 0.6290 | 25.22 |
| 79527.1 | 0.8640 | 17.81 |
| 108148.4 | 0.9370 | 11.35 |
| 147070.3 | 0.9607 | 7.46 |
| 200000.0 | 0.9709 | 5.11 |

## What this run does not show

It is one measurement of this circuit on this device. The closed form uses the declared values of the parts, not measured ones, so a difference from it shows the parts' tolerances and losses as well as the protocol. The result stays on this machine.

## Files

`raw.csv` (every sample), `points.csv` (the route's points), `run.json` (the run record), `evidence.json` (the evidence ledger), `frequency-response.svg` (the figure).
