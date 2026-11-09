# Dossier: Ost, de Paula and Möller, hot-wire velocity in cylinder wakes

Card: `data/registry/ost-hotwire-cylinder-wakes.yaml`. Inspected 2026-11-09 for F53 (Issue #454), the measured-data lab FL7, as the companion of the PIV wake [piv-cylinder-wake](piv-cylinder-wake.md): the PIV record gives a velocity field at one Reynolds number, this one the Strouhal number over a range of Reynolds numbers and blockages. The choice is in [the dataset research](spike-candidates-2026-11-08.md). No card existed before; this one is new.

**Decision: go**, for use beside `piv-cylinder-wake`. Kind: hot-wire velocity time series, shortened by this project. Recorded under the owner's approval of 2026-11-09 on Issue #454 (dataset B, a separate yes, with its ten downloads; a `go` judged per dossier, every requirement of ADR 007 checked here). The record alone has no velocity field, so no vorticity or streamlines: by the Issue, it is a `go` only next to the PIV record.

## The files inspected

| | |
|---|---|
| Source | Mendeley Data, "Turbulent flow past cylinders", https://data.mendeley.com/datasets/xy8ggx9hn6/1, doi 10.17632/xy8ggx9hn6.1, Ana Paula Ost, Alexandre V. de Paula, Sergio Viçosa Möller (Universidade Federal do Rio Grande do Sul) |
| Version | 1, published 2019-11-01; the record links no article |
| Files | ten, `Velocity_1C25_5ms-1.txt` to `Velocity_1C50_16ms.txt`, 4,456,448 bytes each |
| Integrity | the SHA-256 of each equals the one the Mendeley Data API publishes; recorded on the card (`downloads`) and pinned in the extraction script |
| Accessed | 2026-11-09, each file downloaded once into its own new empty directory outside the repository (the ten downloads the Issue approves); read as plain text only |

The record's description and method say: hot-wire measurements in the wake of single cylinders of 25.1, 32 and 50 mm in an aerodynamic channel, Re from 8.25 × 10³ to 5.17 × 10⁴, sampled at 1000 Hz with a 300 Hz low-pass filter, 2¹⁷ samples (131.072 s) per series; a DANTEC StreamLine anemometer, a 16-bit A/D board (NI 9215-A), StreamWare 3.4; an acrylic channel 0.147 m high and 0.193 m wide, air at room temperature, a centrifugal blower, grids, honeycombs and screens reducing the turbulence intensity to about 1 %; the reference velocity from a Pitot tube before the test section, with the diameter used for the Reynolds number. **Each run's parameters are only in the description of its file** (diameter, "impinging velocity", Reynolds number, aspect ratio L/D, probe position x/D downstream and w/D across); the extraction copies them to `runs.csv`.

## The extraction: what the sample is

The ten files (44.6 MB) exceed the caps, so `tools/datasets/ost_hotwire_extract.py` shortens them once, outside the build, from the files it pins by SHA-256 (any other file is refused), in about 2 s; two runs give the same bytes; `tools/datasets/README.md` says how to repeat it. It writes to `data/samples/ost-hotwire-cylinder-wakes/`:

- `ost_hotwire_16s.csv` (1,087,139 bytes): the first 16,384 of 131,072 samples (16.384 s) of each run, one column per run, the velocity rounded to 0.001 m/s, after three comment lines (the record and its licence, the extraction, the time base and the units) and a header of the run names. The record's time column, k/1000 s printed to eight significant digits, is replaced by the row number: the script checks that every file's time is k ms within 2 × 10⁻⁵ s.
- `runs.csv` (1,364 bytes): per run the file, its SHA-256, D [mm], the reference velocity U [m/s], the record's Re, L/D, x/D, w/D. The decimal comma of two descriptions ("5,08 m/s") is read as a point; nothing else is changed.

**The rounding** to 1 mm/s is 1/730 to 1/5400 of the standard deviation of each run (0.73 to 5.4 m/s); it changes no spectral peak. **The shortening** keeps 16.4 s, 400 to 2,200 shedding periods per run: the sample's peak frequency differs from that of the whole 131 s series by at most 0.71 Hz (1.0 %, table below).

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Files | time and velocity | two space-separated E-notation columns with 8 significant digits, CRLF, 131,072 lines; identical time columns in all ten |
| Units | velocity m/s (implied), time s | velocity positive in every sample, 0.32 to 28.5 m/s: a single wire measures speed, so reversed flow does not appear as negative |
| Cadence | 1000 Hz, low-pass 300 Hz, 131.072 s | confirmed; the sample keeps samples 0–16,383; the shedding (24 to 135 Hz) is resolved 7 to 41 times per period, below the filter |
| Probe position | x/D, w/D per file | the mean speed at the probe is 1.05 to 1.50 times the reference velocity: the probe sees the accelerated flow beside the near wake, not the wake axis; the origin and side of w are not defined |
| Blockage | channel 0.193 m wide, 0.147 m high | the cylinders span the height (L/D × D = 146 mm), so D/W = 0.130, 0.166, 0.259; no correction applied |
| Masks | none | no missing value, no NaN |
| Reynolds number | per file | U D / Re gives one viscosity for nine runs (1.543 × 10⁻⁵ m²/s, within 1.2 %, air near 20–25 °C); **`Velocity_1C50_5ms.txt` states Re = 5.17 × 10⁴**, the value of the 16 m/s run of the same cylinder, 3.2 times what its own D and U give. `runs.csv` copies the record; the analysis uses Re = U D / ν with the median ν, 1.64 × 10⁴ for that run |

The parsing test `tests/unit/test_data_ost_hotwire.py::test_ost_hotwire_sample_parses` asserts the header (record, extraction, cadence, units), the column names in both files, the shape and the three decimals, that every value is finite, positive and below 30 m/s, the diameters and velocities, and that the probe's mean speed exceeds the reference; `test_the_card_and_the_tool_pin_the_same_files` checks the card, the tool, and `runs.csv` against each other and the samples against the card; `test_the_record_states_one_reynolds_number_that_its_own_values_contradict` asserts the viscosity and the one inconsistent run.

## Artifact labels

| Artifact | Type |
|---|---|
| the ten `Velocity_1C*.txt` files (not committed) | `processed-measured` |
| `ost_hotwire_16s.csv` | `processed-measured` |
| `runs.csv` | `processed-measured` |
| Roshko's Strouhal–Reynolds correlation | `modelled-reference` |

The velocity is the anemometer's calibrated output, not the bridge voltage, so the record is processed already; the sample shortens and rounds it. The spectra and the Strouhal numbers are this project's processing (`pbc.data.reference.ost_hotwire`).

## Reference figure

```
uv run python -m pbc.data.reference ost-hotwire-cylinder-wakes --out ost_hotwire.png
```

The code is `src/pbc/data/reference/ost_hotwire.py`; it also reads the committed sample of `piv-cylinder-wake` for the PIV point. **Status label: processed.** Panels: (a) the Welch spectra (Hann windows of 4.096 s, half overlap) of the three runs at 10.5 m/s, one per diameter, on a log scale, with the 300 Hz filter dotted; (b) St = f D / U against Re = U D / ν on a log axis for the ten runs, a marker per diameter, the PIV wake at Re = 413 (`piv-cylinder-wake`), and Roshko's correlation St = 0.212 − 2.7/Re over its range 200–2000, dashed (it does not reach these runs); (c) St against the blockage D/W.

The analysis: the peak of each run's Welch spectrum above 5 Hz, refined by a parabola through the logarithm of three bins (`pbc.data.reference.cylinder_wake.peak`); its uncertainty the standard deviation of the peaks of four 4.096 s blocks over √4; St with the record's D and reference U.

**Caption.** *Strouhal numbers of ten hot-wire runs in the wakes of cylinders of 25.1, 32 and 50 mm at Re from 8 × 10³ to 5 × 10⁴, with the PIV wake at Re = 413. The hot-wire values lie between 0.21 and 0.24 and group by cylinder rather than by Reynolds number: the 50 mm cylinder, which blocks a quarter of the channel's width, sheds at the highest St, as expected when the flow past it is faster than the reference velocity used in St. The PIV wake's St of 0.194 lies below Roshko's correlation for long cylinders at its Re. The spectra are this project's; the error bars, from four 4 s blocks, are smaller than the markers.*

| Run | D [mm] | U [m/s] | Re (U D / ν) | D/W | f, sample [Hz] | ± (blocks) | f, full 131 s [Hz] | sd of eight 16 s segments [Hz] | St |
|---|---|---|---|---|---|---|---|---|---|
| 1C25_5ms-1 | 25.1 | 5.08 | 8,260 | 0.130 | 44.82 | 0.05 | 44.80 | 0.06 | 0.2215 |
| 1C25_10.5ms | 25.1 | 10.5 | 17,080 | 0.130 | 93.27 | 0.11 | 93.22 | 0.30 | 0.2230 |
| 1C25_16ms | 25.1 | 16 | 26,020 | 0.130 | 135.46 | 0.10 | 135.54 | 0.45 | 0.2125 |
| 1C32_5ms | 32 | 5.08 | 10,530 | 0.166 | 36.69 | 0.06 | 36.78 | 0.10 | 0.2311 |
| 1C32_8.3ms | 32 | 8.3 | 17,210 | 0.166 | 56.03 | 0.04 | 56.25 | 0.10 | 0.2160 |
| 1C32_10.5ms | 32 | 10.5 | 21,770 | 0.166 | 75.64 | 0.19 | 75.41 | 0.28 | 0.2305 |
| 1C32_16ms | 32 | 16.0 | 33,170 | 0.166 | 109.84 | 0.13 | 110.07 | 0.27 | 0.2197 |
| 1C50_5ms | 50 | 5.05 | 16,360 | 0.259 | 24.36 | 0.02 | 24.36 | 0.11 | 0.2412 |
| 1C50_10.5ms | 50 | 10.5 | 34,020 | 0.259 | 50.06 | 0.07 | 50.07 | 0.29 | 0.2384 |
| 1C50_16ms | 50 | 16 | 51,830 | 0.259 | 74.22 | 0.21 | 73.51 | 0.56 | 0.2319 |

The "full" and "eight segments" columns were computed during the inspection from the downloaded files with the same peak finder; they are not reproducible from the sample and are not asserted by a test. The St of each 25.1 mm run is below that of every 50 mm run (asserted).

## Uncertainty and calibration

**Calibration** is the record's: the hot wire's own (not documented), the Pitot tube's reference velocity (no uncertainty given), and the diameters. St is proportional to D / U: 1 % in U is 1 % in St. The **record documents no uncertainty**; the following are derived here.

- **The peak frequency.** The four-block error of the sample, 0.02–0.21 Hz, understates the spread: across eight 16 s segments of the full record the peak moves by 0.06–0.56 Hz (standard deviation), up to 0.8 % of the frequency, and the sample's peak differs from the full series' by up to 0.71 Hz (1.0 %). A lab should quote St to about ±1 % per run, not to the four-block error.
- **Blockage.** The largest effect. With 13 %, 17 % and 26 % of the width blocked, the flow past the cylinder is faster than the reference velocity, and St formed with the reference velocity rises with D/W: the three 50 mm runs give 0.232–0.241, the three 25.1 mm runs 0.213–0.223. The record applies no correction and none is applied here; a correction model (for example Maskell's or Allen and Vincenti's) would be a modelled step to be disclosed.
- **Reynolds number.** Within one cylinder, St does not follow Re monotonically (25.1 mm: 0.2215, 0.2230, 0.2125); over 8 × 10³ to 5 × 10⁴ the subcritical St of a cylinder is nearly constant, so the scatter of ±0.01 is the run-to-run uncertainty of this setup, not a trend. The record's Re of one run is wrong by a factor 3.2 and is recomputed.
- **Not bounded here:** the hot wire's calibration and its response to the flow direction beside the wake, the Pitot tube's accuracy, the air temperature (ν), and the effect of the short aspect ratios (L/D = 2.9 to 5.8) and of the walls on the shedding.

Asserted by `tests/unit/test_data_ost_hotwire.py`: the frequency and St of each run, the four-block errors below 0.25 Hz, the blockages, the ordering of St by blockage, the viscosity and the inconsistent Re.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the record https://data.mendeley.com/datasets/xy8ggx9hn6/1, licence "CC BY 4.0" (Mendeley Data API `data_licence`, read 2026-11-09: "You can share, copy and modify this dataset so long as you give appropriate credit, provide a link to the CC BY license, and indicate if changes were made, but you may not do so in a way that suggests the rights holder has endorsed you or your use of the dataset. Note that further permission may be required for any content within the dataset that is identified as belonging to a third party."); CC BY 4.0 legal code, https://creativecommons.org/licenses/by/4.0/legalcode, section 2(a)(1)(A) |
| Redistribution of subsets | permitted | the same; section 2(a)(1)(A): share the material in whole or in part |
| Publication of figures and derivatives | permitted | the same; section 2(a)(1)(B): produce and share adapted material |
| Modification and attribution | permitted, with the credit | the same; section 3(a): the creators, the licence with a link, the changes indicated; no endorsement implied (section 2(a)(6)); the record identifies no third-party content. The card's `attribution` says what was changed and the figure prints it |

## Size, runtime, payload

Sample 1.09 MB (caps: 2 MB per file, 8 MB per dataset; with the PIV sample 2.76 MB for the lab). The reference figure takes about 2.2 s with the interpreter start and 195 MB peak memory; its PNG is about 230 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the CSV is read at build time and not shipped. The learner's full download is the ten files, 44.6 MB (`./scripts/fetch-data.sh ost-hotwire-cylinder-wakes`, each checked against the card's SHA-256), and the extraction repeats the sample byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. Actual files inspected, checksum, size, version | "The files inspected": version 1, ten files, SHA-256 matched |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "The extraction"; the parsing tests |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; Roshko's correlation `modelled-reference`, dashed over its own range and not compared with these runs |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/ost_hotwire.py`, from the committed samples; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the peak's spread between segments, the blockage, the inconsistent Re, what the record does not give |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the FL7 lab, starts only when the owner says so (Issue #454).
- The record links no article; the probe's distance from the wake axis and the hot wire's calibration may be in the creators' publications, which were not searched.
- A blockage correction is not chosen; the lab may show the uncorrected St and name the effect.
