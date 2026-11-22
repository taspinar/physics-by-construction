# Dossier: the F140 pilot, a series RLC circuit on an Analog Discovery 3

Card: `data/registry/ad3-rlc-pilot.yaml`. Recorded 2026-11-22 for F140 (Issue #508), the physical pilot of the one-instrument feasibility spike; the decision record is the F140 section of `docs/products.md`.

**Decision: go.** Kind: raw oscilloscope traces of a frequency sweep, measured with the project's own live adapter (`pbc.instruments.analog_discovery`). The measurement is the owner's, published under CC BY 4.0 by the owner's decision of 2026-11-22 on Issue #508.

## The files inspected

| | |
|---|---|
| Source | the pilot's live runs of 2026-11-22 on the owner's bench, exported by the physics lab (`python -m pbc.products.physics_lab run --mode live`); bench results on Issue #508 ([comment](https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-7080355593)) |
| Device | Digilent Analog Discovery 3, SN:210415BFB222, WaveForms SDK 3.25.1 on macOS, USB power only |
| Circuit | W1 → R → L → C → ground on a breadboard; R 100 Ω ± 1 %, L 1 mH, C 10 nF, nominal ([the owner's circuit decision](https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-7077711021)) |
| `capacitor/raw.csv` | run 2, channel 2 at the L–C node; 568,855 bytes; sha256 on the card |
| `capacitor/run.json` | its run record; 3,831 bytes |
| `rl-node/raw.csv` | run 3, channel 2 moved by the owner to the R–L node; 386,837 bytes |
| `rl-node/run.json` | its run record; 3,775 bytes |

The sample is the whole record of both sweeps, copied byte for byte from the pilot's exports. Run 1, a repeat of run 2 a few minutes earlier (f0 47,004 Hz and Q 1.542 against 47,009 Hz and 1.549), is not committed. Run 3's run record states the circuit and the configuration as run 2's; that channel 2 sat at the R–L node is recorded on the Issue and here, not in the file. The first two processing lines of both run records ("each acquisition spans a whole number of periods after the transient settled" and the projection on cos and sin, `steady_phasor`) come from the lab's processing before the live mode's fix and do not hold for these records: no acquisition spans a whole number of periods (see Cadence), and every point was read by the least-squares fit (`fitted_phasor`) that the record's last processing line names. The files are kept byte for byte; the live mode now writes the corrected lines.

Reader: `pbc.data.reference.ad3_rlc_pilot.read_traces` and `read_run` (the standard library's `csv` and `json`, and NumPy); no dependency is added.

## Schema, units, cadence, masks, coverage

| Item | What the files document | What this dossier established |
|---|---|---|
| Schema | `raw.csv`: point, frequency_hz, amplitude_v, t_s, source_v, response_v; `run.json`: the run record and the evaluator's check | 513 samples per point; 19 points (capacitor) and 13 (rl-node) |
| Units | in `run.json`: Hz, V, s, V/V, degrees | as stated |
| Cadence | 13 coarse points log-spaced from 5 kHz to 200 kHz, then up to 6 around the phase crossing; 64 samples per period asked | the realised rate is 100 MHz over the nearest whole divider, within 0.5/divider of the rate asked: 0.16 % at 5 kHz, up to 3.4 % at 147 kHz, where a record spans 8.28 periods instead of 8 |
| Masks | none | every sample finite and within its input range (channel 1 under 2.5 V, channel 2 under 25 V) |
| Coverage | the timestamps and the operating conditions in `run.json` | 11:55 to 12:58 UTC; die temperature 61.6 to 63.7 °C; auxiliary supply 0.04 V (none) |

The parsing test `tests/unit/test_data_ad3_rlc_pilot.py::test_ad3_rlc_pilot_sample_parses` asserts the columns, the shapes, the realised rates against the divider, the input ranges, and the run records.

## Artifact labels

| Artifact | Type |
|---|---|
| `raw.csv` (both sweeps) | `raw-measured` |
| `run.json` (both sweeps) | `processed-measured` |

`raw.csv` holds the samples as the device returned them, with its factory calibration. `run.json` holds the lab's processing (the evaluator's f0 and Q from the phase crossing and the comparison with the nominal closed form). For the rl-node sweep that check is not meaningful, because the evaluator expects the capacitor's voltage. The gain and phase in the figure are computed by this module from `raw.csv`, so the figure is `processed`.

## Reference figure

```
uv run python -m pbc.data.reference ad3-rlc-pilot --out pilot.png
```

The code is `src/pbc/data/reference/ad3_rlc_pilot.py`. **Status label: processed.** Panels: the gain |V_C/V_S| (log-log) and the phase of V_C/V_S against frequency, the measured points with one standard deviation of the phasor fits, and two models drawn apart (dashed and dotted); then the residuals, model minus measured, of the gain and of the phase.

Each channel's phasor is a least-squares fit of a cosine, a sine, and a constant to the 513 samples. The device's divided clock does not give whole periods, so the projection on whole periods (`steady_phasor`) does not apply. The gain and the phase are the ratio of the two phasors, and they agree with the product's evaluator to 1e-9 (test `test_the_reference_reading_agrees_with_the_products_evaluator`).

The models are the closed form of the series circuit, V_C/V_S = 1 / (1 − ω²LC + jω(R + R_L)C):

- **nominal**: R 100 Ω, L 1 mH, C 10 nF, no coil loss: f0 = 50.3 kHz, Q = 3.16;
- **parts measured apart**: L, C, and the coil loss R_L from the rl-node sweep (below): f0 = 45.0 kHz, Q = 1.50.

**Caption.** *Frequency response of the pilot's series RLC circuit, measured with the Analog Discovery 3 at 1 V. The measured gain peaks at 1.66 (at the sample 43.0 kHz), and the phase crosses −90° at 47.0 kHz. The nominal parts predict a peak of 3.20 at 50.3 kHz. The parts measured apart predict a peak of 1.59 and f0 = 45.0 kHz, within 5 % of the measured f0 and Q; their residuals stay under 0.15 in the gain and between −1.2° and −8.2° in the phase. No model with constant parts fits the whole band.*

## Parts measured apart

With channel 2 at the R–L node the response is H = Z/(R + Z), where Z is the coil and the capacitor in series, so Z = R·H/(1 − H) with the nominal R. Its imaginary part is ωL − 1/(ωC); a least-squares fit over the 13 points gives L and C. Its real part is the coil's loss R_L (with the wiring), read as the mean over the points within a factor 1.5 of the resonance:

| Quantity | Value (one s.d.: the fit's scatter and R's 1 % in quadrature) | Nominal |
|---|---|---|
| L | 0.861 ± 0.010 mH | 1 mH |
| C | 14.55 ± 0.15 nF | 10 nF |
| R_L near the resonance (31.6, 43.0, 58.5 kHz) | 63 ± 3 Ω | none |
| f0 = 1/(2π√(LC)) | 45.0 kHz | 50.3 kHz |
| Q = √(L/C)/(R + R_L) | 1.50 | 3.16 |
| Measured on the capacitor sweep (run record) | f0 47,009 Hz, Q 1.549 | |

The parts explain most of the gap between the nominal and the measured response. The low Q is the coil's loss (63 Ω beside the 100 Ω resistor) and the lower f0 is the larger capacitance; the capacitor of the owner's set is 45 % above its nominal 10 nF. The real part of Z is not constant: about 60 Ω near the resonance, rising to 97 Ω at 108 kHz and 259 Ω at 200 kHz (core and skin losses grow with the frequency). Below 20 kHz it rises again to 183 Ω at 5 kHz, but there 1 − H is under 5 %. A channel mismatch of a fraction of a percent or a degree moves the real part by tens of ohm, so these low-frequency values are not a measurement of the loss (test `test_the_coil_loss_grows_with_the_frequency`).

## Uncertainty and calibration

- **Per point: the noise of the phasor fits.** At most 5e-4 in the gain and 0.26° in the phase (one standard deviation from the residual scatter of the two fits). These bars are drawn and are too small to see beside the models' misfit.
- **The channel mismatch: unknown.** Channel 1 is on the 5 V range and channel 2 on the 50 V range. Their relative gain and phase are the factory calibration's, not stated in the record, and not measured by the pilot. The phase residual of the parts-apart model, a few degrees that grow with the frequency, may come in part from it, or from the frequency-dependent loss; these data do not separate the two. Both sweeps share the mismatch, so L, C, and R_L carry it too.
- **The parts.** L and C carry the scatter of the reactance fit and R's 1 % (Z is proportional to R). Their own tolerances are not stated by the seller. No constant R_L describes the band, so a "Q" of this circuit depends on the band it is read in.
- **Repeatability.** Two sweeps of the capacitor, minutes apart, agree to 5 Hz in f0 and 0.007 in Q (runs 1 and 2).

## The CI fixture

`pbc.products.physics_lab.workflow.read_export` turns a live export into a recorded sample, keeping the realised rate of each capture beside the rate asked (`RecordedCapture.realised_rate_hz`). The recorded mode replays it under the live envelope and the circuit of its run record. `tests/unit/test_data_ad3_rlc_pilot.py::test_the_ci_fixture_replays_the_measured_sweep_without_the_device` replays the capacitor sweep: the same 19 frequencies in the same order (the refinement follows from the replayed coarse points), and the evaluator's metrics equal the live run's record. The run record says `recorded` and not a new experiment. No device and no SDK are needed.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the owner's decision of 2026-11-22 on Issue #508 ([comment](https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-7079470015)): CC BY 4.0 |
| Redistribution of subsets | permitted | the same; legal code section 2(a)(1) |
| Publication of figures and derivatives | permitted | the same; section 2(a)(1) |
| Modification and attribution | permitted with attribution | the same; section 3(a), the credit on the figure |

## Size, runtime, payload

Sample 963 KB in four files (caps: 2 MB per file, 8 MB per dataset). Figure: about 2 s including the interpreter start, about 155 MB peak memory; PNG about 290 KB. The CI replay of the capacitor sweep takes under 1 s. No file is downloaded.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected"; sha256 and bytes on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; the figure draws both models apart, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/ad3_rlc_pilot.py`, from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the fit noise per point; the channel mismatch and the parts' tolerances stated as unknown |
| 8. This dossier with the decision | this file |

## Open items

- A measurement of L, C, and R with an LCR meter would separate the coil's loss from the channel mismatch; the pilot had none.
- No lesson uses this dataset; a lab that does is a later feature.
