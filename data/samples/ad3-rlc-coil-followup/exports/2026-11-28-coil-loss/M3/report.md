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
| 5000.0 | 0.9982 | -0.15 |
| 6799.5 | 0.9974 | -0.30 |
| 9246.6 | 0.9957 | -0.41 |
| 12574.3 | 0.9927 | -0.49 |
| 17099.8 | 0.9902 | -0.49 |
| 23253.9 | 0.9875 | -0.43 |
| 31622.8 | 0.9857 | -0.38 |
| 43003.6 | 0.9848 | -0.32 |
| 58480.4 | 0.9837 | -0.23 |
| 79527.1 | 0.9840 | -0.21 |
| 108148.4 | 0.9828 | -0.13 |
| 147070.3 | 0.9831 | -0.14 |
| 200000.0 | 0.9829 | -0.13 |

## What this run does not show

It is one measurement of this circuit on this device. The closed form uses the declared values of the parts, not measured ones, so a difference from it shows the parts' tolerances and losses as well as the protocol. The result stays on this machine.

## Files

`raw.csv` (every sample), `points.csv` (the route's points), `run.json` (the run record), `evidence.json` (the evidence ledger), `frequency-response.svg` (the figure).
