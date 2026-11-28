# Investigation report: the coil loss of the pilot's RLC circuit

> This report is a summary of the project's records, not a proof that the investigation succeeded.
> Claims: 7 (7 completed).

Scope: the pilot's circuit of F140 on the owner's breadboard, as measured with the AD3 (the parts, the breadboard, the leads, and the instrument together).

## Question and registration

Why does the ideal series RLC model fail on the pilot's circuit (ad3-rlc-pilot)? G1: is the loss near the resonance (about 63 ohm) the DC resistance of the parts or a loss that exists only in alternating current? G2: are the rise of that loss with the frequency and the growing phase residual properties of the circuit or of the two channels? (G3, the capacitance, is dropped: the meter has no capacitance range.)

The registration is frozen: digest `3e4cfd1ae9a4fde8`, merge commit `d4d9a16d8a71` on `main`, 2026-11-26T15:43:26+00:00. Evidence measured before that time is refused. The thresholds were chosen after seeing the pilot's data; only M1 to M5 are confirmatory.

| Question | Decision | Reason | Revisit when |
|---|---|---|---|
| coil-loss | selected | the pilot is a declared dataset with a go; the registered rules have more than two reachable outcomes; the follow-up needs one bench session | if the parts of the pilot cannot be identified at the bench (the precondition), as a question about the circuit of M1 to M5 |
| capacitance | deferred | the owner's meter, a Mastech MAS830BC, has no capacitance range (the owner's answer of 2026-11-25) | with a meter that has a capacitance range, as a new registration |
| led-pair | rejected | it is the protocol of SA9 (F145), not a question of this capstone | if the held-out prediction of SA9 fails on the owner's bench |
| die-temperature | rejected | the pilot's record holds 61.6 to 63.7 degrees C only: no variation to test, and the rule has one outcome | with a cooling or warming run |

## The explanations and their outcomes

| Explanation | Rule | Predicts | Verdict | Status |
|---|---|---|---|---|
| DC | G1 | accounted | undecided | completed |
| AC | G1 | short | undecided | completed |
| MISMATCH | G2 | artefact | undecided | completed |
| CIRCUIT | G2 | remains | undecided | completed |
| BOTH | G2 | mixed | undecided | completed |

`exceeds` (D < -3 u) is predicted by neither explanation of G1 and opens a new finding. Every case that meets no predicted outcome is `inconclusive`, a result.

## The analysis of the existing sweeps (exploratory)

Pilot run 3 read with the nominal 100 ohm: L = 0.861 mH, C = 14.55 nF, R_L0 = 62.7 ohm (u_L 1.8 ohm), Rise = 198 ohm (u_hi 4.4 ohm, no correction), P0 = 5.75 degrees. These data chose the thresholds: they confirm nothing.

| f [kHz] | R_L [ohm] | one sigma [ohm] |
|---|---|---|
| 5.0 | 183.2 | 7.95 |
| 6.8 | 133.6 | 4.21 |
| 9.2 | 115.5 | 2.37 |
| 12.6 | 103.2 | 1.28 |
| 17.1 | 93.3 | 0.65 |
| 23.3 | 77.6 | 0.32 |
| 31.6 | 66.0 | 0.14 |
| 43.0 | 60.3 | 0.06 |
| 58.5 | 61.7 | 0.10 |
| 79.5 | 70.9 | 0.27 |
| 108.1 | 97.4 | 0.73 |
| 147.1 | 151.8 | 1.72 |
| 200.0 | 258.6 | 3.95 |

The sensitivity to a channel mismatch (constant, assumed): a phase of channel 2 relative to channel 1, and a gain error, divided out of both sweeps.

| dphi [deg] | dg | R_L0 [ohm] | Rise [ohm] | P [deg] |
|---|---|---|---|---|
| -0.3 | -0.003 | 62.9 | 139 | 4.34 |
| -0.3 | 0.000 | 63.1 | 167 | 4.25 |
| -0.3 | 0.003 | 63.2 | 194 | 4.20 |
| 0.0 | -0.003 | 62.5 | 167 | 5.88 |
| 0.0 | 0.000 | 62.7 | 198 | 5.75 |
| 0.0 | 0.003 | 62.8 | 227 | 5.71 |
| 0.3 | -0.003 | 62.1 | 201 | 8.23 |
| 0.3 | 0.000 | 62.3 | 235 | 8.03 |
| 0.3 | 0.003 | 62.5 | 267 | 7.91 |

## The positive controls (simulated)

Seeded sessions at the pilot's noise level (channel 1 0.40 mV, channel 2 3.42 mV), 5 seeds each, evaluated through the follow-up's own reader. With ideal channels the largest |dphi| was 0.033 degrees and the largest |dg| 0.0005, below the thresholds 0.3 degrees and 0.003: the same-node sweep resolves a measurable mismatch on the simulated bench.

| Control | Seed | G1 | G2 | Precondition | G1 for the pilot | D [ohm] | u [ohm] | Rise [ohm] | u_hi [ohm] | Missed |
|---|---|---|---|---|---|---|---|---|---|---|
| AC | 0 | short | remains | True | short | 43.37 | 3.82 | 50.2 | 3.28 | nothing |
| AC | 1 | short | remains | True | short | 43.29 | 3.83 | 48.2 | 3.25 | nothing |
| AC | 2 | short | remains | True | short | 43.40 | 3.83 | 48.5 | 3.43 | nothing |
| AC | 3 | short | remains | True | short | 43.37 | 3.84 | 41.4 | 3.40 | nothing |
| AC | 4 | short | remains | True | short | 43.32 | 3.86 | 50.8 | 3.33 | nothing |
| AC-steep | 0 | inconclusive | remains | True | inconclusive | 42.35 | 5.49 | 71.9 | 3.31 | nothing |
| AC-steep | 1 | inconclusive | remains | True | inconclusive | 42.26 | 5.51 | 70.0 | 3.29 | nothing |
| AC-steep | 2 | inconclusive | remains | True | inconclusive | 42.37 | 5.51 | 70.5 | 3.46 | nothing |
| AC-steep | 3 | inconclusive | remains | True | inconclusive | 42.34 | 5.51 | 63.0 | 3.44 | nothing |
| AC-steep | 4 | inconclusive | remains | True | inconclusive | 42.29 | 5.54 | 72.5 | 3.36 | nothing |
| BOTH | 0 | inconclusive | mixed | False | not evaluated | 43.62 | 6.83 | 50.3 | 3.26 | nothing |
| BOTH | 1 | inconclusive | mixed | False | not evaluated | 43.54 | 6.84 | 48.2 | 3.24 | nothing |
| BOTH | 2 | inconclusive | mixed | False | not evaluated | 43.65 | 6.85 | 48.2 | 3.41 | nothing |
| BOTH | 3 | inconclusive | mixed | False | not evaluated | 43.61 | 6.85 | 41.6 | 3.39 | nothing |
| BOTH | 4 | inconclusive | mixed | False | not evaluated | 43.57 | 6.87 | 50.9 | 3.32 | nothing |
| DC | 0 | accounted | inconclusive | False | not evaluated | 0.04 | 0.10 | 0.5 | 3.22 | nothing |
| DC | 1 | accounted | inconclusive | False | not evaluated | -0.05 | 0.07 | -1.6 | 3.20 | nothing |
| DC | 2 | accounted | inconclusive | False | not evaluated | 0.06 | 0.08 | -1.7 | 3.37 | nothing |
| DC | 3 | accounted | inconclusive | False | not evaluated | 0.03 | 0.07 | -7.9 | 3.35 | nothing |
| DC | 4 | accounted | inconclusive | False | not evaluated | -0.02 | 0.10 | 1.2 | 3.27 | nothing |
| MISMATCH | 0 | accounted | artefact | False | not evaluated | 0.09 | 2.90 | 0.6 | 3.21 | nothing |
| MISMATCH | 1 | accounted | artefact | False | not evaluated | 0.00 | 2.91 | -1.6 | 3.18 | nothing |
| MISMATCH | 2 | accounted | artefact | False | not evaluated | 0.11 | 2.91 | -2.0 | 3.35 | nothing |
| MISMATCH | 3 | accounted | artefact | False | not evaluated | 0.08 | 2.92 | -7.7 | 3.33 | nothing |
| MISMATCH | 4 | accounted | artefact | False | not evaluated | 0.03 | 2.94 | 1.4 | 3.26 | nothing |
| other-parts | 0 | short | remains | False | not evaluated | 42.72 | 1.77 | 198.6 | 3.95 | nothing |
| other-parts | 1 | short | remains | False | not evaluated | 42.63 | 1.74 | 196.8 | 3.92 | nothing |
| other-parts | 2 | short | remains | False | not evaluated | 42.73 | 1.78 | 198.4 | 4.13 | nothing |
| other-parts | 3 | short | remains | False | not evaluated | 42.71 | 1.73 | 188.2 | 4.09 | nothing |
| other-parts | 4 | short | remains | False | not evaluated | 42.66 | 1.69 | 198.8 | 4.01 | nothing |
| pilot-parts | 0 | short | remains | True | short | 42.72 | 1.78 | 198.5 | 3.62 | nothing |
| pilot-parts | 1 | short | remains | True | short | 42.63 | 1.74 | 197.0 | 3.59 | nothing |
| pilot-parts | 2 | short | remains | True | short | 42.74 | 1.78 | 198.6 | 3.78 | nothing |
| pilot-parts | 3 | short | remains | True | short | 42.71 | 1.73 | 189.1 | 3.75 | nothing |
| pilot-parts | 4 | short | remains | True | short | 42.66 | 1.69 | 198.7 | 3.67 | nothing |

## The boundary cases

24 of 24 cases give the outcome the registration's text gives at the value; the meter model passes 5 of 5 constructed checks.

| Rule | Inputs | Expected | Got | Holding |
|---|---|---|---|---|
| G1 | 4, 2 | accounted | accounted | accounted |
| G1 | -4, 2 | accounted | accounted | accounted |
| G1 | 4.001, 2 | inconclusive | inconclusive | none |
| G1 | 6, 2 | inconclusive | inconclusive | none |
| G1 | 6.001, 2 | short | short | short |
| G1 | 5, 1 | inconclusive | inconclusive | none |
| G1 | 5.001, 1 | short | short | short |
| G1 | -6, 2 | inconclusive | inconclusive | none |
| G1 | -6.001, 2 | exceeds | exceeds | exceeds |
| G1 | 0, 5 | accounted | accounted | accounted |
| G1 | 0, 5.001 | inconclusive | inconclusive | accounted |
| G1 | 100, 5.001 | inconclusive | inconclusive | short |
| G1 | -100, 5.001 | inconclusive | inconclusive | exceeds |
| G2 | 0.3, 0, 0, 1, 2, 0 | inconclusive | inconclusive | none |
| G2 | 0.301, 0, 2, 1, 2, 1 | artefact | artefact | artefact |
| G2 | 0.301, 0, 2, 1, 2, 1.001 | inconclusive | inconclusive | none |
| G2 | 0.301, 0, 2.001, 1, 2, 0 | inconclusive | inconclusive | none |
| G2 | 0.301, 0, 3, 1, 2, 0 | inconclusive | inconclusive | none |
| G2 | 0.301, 0, 3.001, 1, 2, 0 | mixed | mixed | mixed |
| G2 | 0, 0.003, 3.001, 1, 2, 0 | remains | remains | remains |
| G2 | 0, 0.003, 3, 1, 2, 0 | inconclusive | inconclusive | none |
| G2 | 0, 0.003001, 3.001, 1, 2, 0 | mixed | mixed | mixed |
| G2 | 0, 0.003001, 1, 1, 2, 0.5 | artefact | artefact | artefact |
| G2 | 0.3, 0.003, 1, 1, 2, 0.5 | inconclusive | inconclusive | none |

## The follow-up

Status: computed.

- Deviation: M0 started 4 minutes after the plug-in, earlier than the registered 45 minutes
- R_s_bb reads 3.08 ohm, outside 97.9 to 102.1 ohm: a gross error of the meter or of the contacts (reported beside G1; it decides no outcome)
- the precondition is not met: the conclusions are scoped to the circuit of M1 to M5; the pilot's discrepancy stays not evaluated for G1, and G2 (a property of the instrument) carries over

| Quantity | Value |
|---|---|
| C_F | 0.0000 |
| D | 2.7684 |
| L_H | 0.0000 |
| M5_C_relative | 0.0636 |
| M5_L_relative | -0.0069 |
| M5_R_L0_difference | -0.2087 |
| P0_deg | 6.3865 |
| P1_deg | 5.8236 |
| R_L0 | 2.4184 |
| R_dc | 0.2500 |
| R_dc_bb | -0.3500 |
| R_s_bb | 3.0833 |
| Rise | -0.5321 |
| crossing_M0_hz | 50673.1570 |
| crossing_M1_hz | 50605.2857 |
| crossing_M1_minus_M0_hz | -67.8713 |
| dz | 2.5000 |
| g1_sensitivity_differs | 0.0000 |
| identity_C_relative | -0.0766 |
| identity_L_relative | -0.0236 |
| identity_R_L0_difference | 0.4858 |
| max_abs_dg | 0.0172 |
| max_abs_dphi_deg | 0.4878 |
| mismatch_measurable | 1.0000 |
| pilot_C_F | 0.0000 |
| pilot_L_H | 0.0000 |
| pilot_R_L0 | 1.9326 |
| resistor_band_high | 102.1080 |
| resistor_band_low | 97.9080 |
| u_G1 | 1.0041 |
| u_G1_p_1_2 | 1.0042 |
| u_L | 0.6447 |
| u_R_dc | 0.7228 |
| u_R_dc_bb | 0.7697 |
| u_R_dc_bb_ng | 0.7697 |
| u_R_s_bb | 0.8024 |
| u_R_s_bb_ng | 0.8023 |
| u_hi | 0.2214 |
| z | 5.1500 |

Per coarse frequency: the phase of M1 minus the phase of M0 (read by no rule), the channels' relative response m from M3, and R_L without and with the correction H / m.

| f [kHz] | M1 - M0 [deg] | dphi [deg] | dg | R_L [ohm] | R_L corrected [ohm] |
|---|---|---|---|---|---|
| 5.0 | -0.012 | -0.153 | -0.0018 | 9.75 | 7.86 |
| 6.8 | -0.011 | -0.300 | -0.0026 | 6.92 | 5.91 |
| 9.2 | -0.018 | -0.406 | -0.0043 | 5.78 | 4.92 |
| 12.6 | -0.019 | -0.486 | -0.0073 | 4.90 | 4.02 |
| 17.1 | -0.041 | -0.488 | -0.0098 | 4.06 | 3.49 |
| 23.3 | -0.051 | -0.435 | -0.0125 | 3.35 | 3.06 |
| 31.6 | -0.099 | -0.376 | -0.0143 | 2.69 | 2.67 |
| 43.0 | -0.183 | -0.317 | -0.0152 | 2.33 | 2.41 |
| 58.5 | -0.215 | -0.228 | -0.0163 | 2.23 | 2.21 |
| 79.5 | -0.107 | -0.213 | -0.0160 | 2.36 | 2.02 |
| 108.1 | -0.152 | -0.131 | -0.0172 | 3.11 | 1.98 |
| 147.1 | 0.085 | -0.139 | -0.0169 | 4.68 | 1.96 |
| 200.0 | -0.210 | -0.125 | -0.0171 | 7.74 | 1.88 |

## Findings and decisions

| Finding | Kind | State | Text |
|---|---|---|---|
| G1 | evidence | inconclusive | Is the loss near the resonance the DC resistance or an AC loss? |
| G2 | evidence | inconclusive | Are the rise and the phase residual of the circuit or of the channels? |

| Subject | Decision | Reason | By |
|---|---|---|---|
| registration | frozen | the registration 3e4cfd1ae9a4fde8e116df21c3b5035ef05b63322605f94e25a466ee13f0a429 is frozen at the merge commit d4d9a16d8a71fdaefb27c4b684dba622e5f82280 of 2026-11-26T15:43:26+00:00 (pull request 625, after the owner's approving review of its exact head) | the owner (the merge) |
| outcome-code | the pinned code | the identity of the outcome code: 974bf992ec24115be479f69046cb1d04dfc5472b3c5752a1db2d699e9b831801; pinned for the follow-up at 2026-11-26T18:33:00+00:00: 974bf992ec24115be479f69046cb1d04dfc5472b3c5752a1db2d699e9b831801 | the workspace (this run) |

## Claims

| Claim | Status | Runs |
|---|---|---|
| pilot-loss | completed | pilot/analysis |
| pilot-sensitivity | completed | pilot/analysis |
| controls | completed | control/explanations |
| boundaries | completed | control/boundaries |
| G1 | completed | followup/G1 |
| G2 | completed | followup/G2 |
| precondition | completed | followup/precondition |

Data: A. Taspinar, F140 pilot (Analog Discovery 3), 2026-11-22, CC BY 4.0 (ad3-rlc-pilot).
