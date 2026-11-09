# Dossier: Bayreuth RLC impedance spectrum

Card: `data/registry/bayreuth-rlc-impedance.yaml`. Inspected 2026-11-08 for F86 (Issue #418), the measured-data lab EM8; the choice of this record is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: complex impedance measurement of a passive circuit. Recorded under the owner's decision of 2026-11-08 on Issue #418 (work towards a `go` on the strength of the research, every requirement of ADR 007 checked here); the checklist below names the evidence for each.

## The file inspected

| | |
|---|---|
| Source | Zenodo record 10794584, doi 10.5281/zenodo.10794584, version 1.0.0, published 2024-03-07; creators Michael A. Danzer, Christian Plank, Tom Rüther (University of Bayreuth) |
| File | `rlc_circuit.json`, 9,119 bytes, md5 `0d8f9939685d435c7475aed873a6ba99` (published by Zenodo, confirmed on the downloaded file), sha256 `5ba93aeef5570f8eaf13bf84e0d2b3bb5221f2d208ce365c9088b62873ef5cbd` |
| Accessed | 2026-11-08 |
| Record | 14 files, 164 KB: impedance spectra of batteries, fuel cells, a double-layer capacitor, and one analogue RLC circuit, each as MAT and JSON |

The sample is the whole file, copied byte for byte. The record describes the circuit as "a parallel connection of a 2.2 µF foil capacitor and a lossy inductor with 9.7 mΩ and 5 mH, factory values may vary ± 10 %", measured with a Biologic VMP300, galvanostatic, 30 mA amplitude, 100 Hz to 10 kHz. The fit below shows that "9.7 mΩ" is a unit typo for 9.7 Ω: a resistance of milliohms would give a quality factor near 5,000, the data give 4.9.

Reader: `pbc.data.reference.bayreuth_rlc.read_impedance`, the standard library's `json` and NumPy; no dependency is added.

## Schema, units, cadence, masks, coverage

| Item | What the file documents | What this dossier established |
|---|---|---|
| Schema | One object: `class_` "Impedance", `meta_` (export date 06-Mar-2024 22:24:55, MATLAB R2020b, package Impedance 0.0.3.dev), arrays `f`, `omega`, `z` (strings "a-bi"), `z_real`, `z_imag`, `z_modulus`, `z_phase` | 81 entries in each array; all representations of Z agree (modulus and phase to rounding, the strings to 6e-5 Ω) |
| Units | none | f in Hz (`omega` equals 2πf exactly); Z in Ω (|Z| is 9.9 Ω at 100 Hz, the coil's resistance and reactance); phase in radians; Im Z > 0 for an inductive response |
| Cadence | none | one sweep, 81 points from 10,002.2 Hz down to 99.97 Hz, 40 per decade |
| Masks, missing values | none | no missing or non-finite value |
| Time coverage | export time only | a single spectrum recorded on or before 2024-03-06; the measurement date and temperature are not stated |

The parsing test `tests/unit/test_data_samples.py::test_bayreuth_rlc_sample_parses` asserts the field names, the shapes, the cadence, the units, and the absence of masks.

## Artifact labels

| Artifact | Type |
|---|---|
| `rlc_circuit.json` | `processed-measured` |

The file is the instrument's impedance spectrum, exported by the creators' MATLAB package; the step from the recorded voltage and current to Z is not documented, so it is labelled processed rather than raw. The fitted curve is not an artifact of the record: `pbc.data.reference.bayreuth_rlc` computes it, and the figure draws it dashed and apart from the measured points, with its residuals.

## Reference figure

```
uv run python -m pbc.data.reference bayreuth-rlc-impedance --out rlc.png
```

The code is `src/pbc/data/reference/bayreuth_rlc.py`. **Status label: processed.** Panels: |Z| against frequency (log-log) with the fit, the phase of Z, the impedance plane (Nyquist), and the relative complex residual Z_fit/Z_measured − 1.

The model is the EM5 parallel resonant circuit: a capacitor C parallel to a coil of inductance L with series resistance R, Z = (R + jωL) / (1 + jωC(R + jωL)). It is fitted with `pbc.data.fit.fit_curve` to the real and imaginary parts of Z_model/Z − 1, so every point weighs the same relative to its own |Z| (which spans 7.6 to 223 Ω).

**Caption.** *Impedance of a coil parallel to a capacitor, measured at 81 frequencies, 40 per decade. The highest measured |Z|, 223 Ω, is at the sample 1,584.5 Hz, and the measured phase changes sign between the samples 1,496.4 Hz (+4°) and 1,584.5 Hz (−25°). A fit of three circuit values reproduces the 81 points to 1.1 % rms; the fitted |Z| peaks at 1,546.3 Hz and the fitted phase crosses zero, from inductive to capacitive, at 1,514.9 Hz. The residuals that remain are largest near the resonance.*

| Parameter | Fit (standard error from the scatter) | Nominal (record) |
|---|---|---|
| R | 9.537 ± 0.021 Ω | 9.7 Ω (as "9.7 mΩ") ± 10 % |
| L | 4.849 ± 0.007 mH | 5 mH ± 10 % |
| C | 2.1832 ± 0.0031 µF | 2.2 µF ± 10 % |
| f0 = 1/(2π√(LC)) | 1546.9 Hz | 1517 Hz |
| Maximum of the fitted \|Z\| | 1546.3 Hz | |
| Zero crossing of the fitted phase | 1514.9 Hz | |
| Q = √(L/C)/R | 4.94 | 4.9 |

The fit identifies all three parameters (no warning of `fit_curve`); the strongest correlation is −0.77 between L and C. The three resonance frequencies of the fit differ because the coil's resistance damps the circuit (Q = 4.9): 1/(2π√(LC)) is the undamped one, the fitted |Z| peaks 0.6 Hz below it, and the fitted phase crosses zero 32 Hz below it. The sweep samples 40 frequencies per decade, a step of about 5.9 % (0.025 in log10 f). The fit's maximum, 1,546.3 Hz, lies between the samples 1,496.4 Hz and 1,584.5 Hz; the highest measured |Z| is at the nearer of the two, 1,584.5 Hz, 2.5 % above the fit's maximum. The measured maximum therefore locates the resonance only to within one step of the sweep; the fit locates it between the samples.

## Uncertainty and calibration

The record gives **no uncertainty per point** and **no calibration**: it names the instrument, the mode, the amplitude, and the range, and says nothing of a calibration, a cable or fixture compensation, or the instrument's accuracy. No correction is applied. The uncertainty is derived instead, in two parts:

- **Statistical.** With no per-point uncertainty, `fit_curve` scales the covariance by the residual scatter (1.1 % rms per component). This gives the standard errors in the table: 0.2 %, 0.15 %, and 0.14 %.
- **Sensitivity of the model fit.** The residuals are not noise: they are smooth, about +1 % at 100 Hz, −1.3 % at 10 kHz, and up to 4.3 % near the resonance. The standard errors above therefore understate how well the three values are determined; they stay as stated, the standard errors of the full fit. `band_split` fits the points below and above the full fit's f0 separately, to show how much the values depend on the part of the spectrum fitted:

| Fit | Points | f0 = 1/(2π√(LC)) | R | L | C | Q |
|---|---|---|---|---|---|---|
| Full band, 100 Hz to 10 kHz | 81 | 1546.9 Hz | 9.537 ± 0.021 Ω | 4.849 ± 0.007 mH | 2.1832 ± 0.0031 µF | 4.94 |
| Below 1546.9 Hz | 48 | 1539.8 Hz | 9.456 ± 0.006 Ω | 4.807 ± 0.002 mH | 2.2226 ± 0.0016 µF | 4.92 |
| Above 1546.9 Hz | 33 | 1546.1 Hz | 10.381 ± 0.073 Ω | 4.927 ± 0.011 mH | 2.1507 ± 0.0033 µF | 4.61 |

The band fits differ from each other by 0.93 Ω in R, 0.12 mH in L, and 0.072 µF in C, more than ten standard errors each, and their resonances lie 1 and 7 Hz below the full fit's. This is a **sensitivity range of the model fit**, not an uncertainty interval: the three-value model does not describe the whole spectrum exactly, and which values it returns depends on the band. Of the four quantities, the resonance frequency changes least (0.5 %) and R, which sets the damping, most (10 %).

- **Calibration and instrument error: unknown.** Neither the standard errors nor the band fits bound the calibration or instrument error of the record, which the record does not state; the fit cannot reveal an error that scales every point alike. A lab that reports these numbers must say that their uncertainty is derived from the fit, that the band fits are a sensitivity analysis, and that the instrument's own error is not given by the record.

The likely sources of the structured residuals, not separated by these data: losses in the coil and the foil capacitor that depend on frequency (a single R does not describe them), the leads, and the instrument's own error.

Asserted by `tests/unit/test_data_samples.py`: the fit values and standard errors, the 10 % tolerance of each nominal value, f0 and Q, the measured maximum, the fit's maximum and phase zero crossing, the rms and the largest residual, and the band fits' spread and resonances.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo licence field of https://zenodo.org/records/10794584, CC BY 4.0, read 2026-11-08; https://creativecommons.org/licenses/by/4.0/legalcode |
| Redistribution of subsets | permitted | the same; legal code section 2(a)(1), sharing in whole or in part |
| Publication of figures and derivatives | permitted | the same; section 2(a)(1), producing and sharing adapted material |
| Modification and attribution | permitted with attribution | the same; section 3(a): creators, licence, link, and an indication of changes, printed on the figure |

## Size, runtime, payload

Sample 9 KB (caps: 2 MB per file, 8 MB per dataset). Figure: about 4 s including the interpreter start (1.6 s of computation), about 160 MB peak memory; PNG about 200 KB. A lesson page that reads the sample and draws this figure stays far inside the 30 s warning, the 60 s limit, and the 3 MB payload. The learner's full download is the same 9 KB file (`./scripts/fetch-data.sh bayreuth-rlc-impedance`). CI reads only the committed file.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | the table "The file inspected"; md5 and sha256 on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels"; the figure draws the fit dashed, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/bayreuth_rlc.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": none in the record; standard errors from the fit, the band fits as a sensitivity analysis, the calibration and instrument error stated as unknown |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the EM8 lab, starts only when the owner says so (Issue #418).
- The runner-up, the Tours broadband impedance of passive components (Zenodo 23259842), is not inspected; it would add an independent measurement of similar parts.
