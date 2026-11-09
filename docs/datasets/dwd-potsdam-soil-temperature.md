# Dossier: DWD hourly soil temperature, station 03987 Potsdam

Card: `data/registry/dwd-potsdam-soil-temperature.yaml`. Inspected 2026-11-09 for F84 (Issue #438), the measured-data lab T7; the choice of this dataset is in [the dataset research](spike-candidates-2026-11-08.md) (section T7), whose third round inspected the same archive.

**Decision: go.** Kind: measured temperature profiles in the ground, time series at five depths. Recorded under the owner's decision of 2026-11-08 on Issue #438 (work towards a `go`, judged per dossier, every requirement of ADR 007 checked here; the archive without a DOI pinned by the project's own checksum, accepted); the checklist below names the evidence for each.

## The file inspected

| | |
|---|---|
| Source | DWD Climate Data Center, open-data area, `https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/soil_temperature/historical/` |
| File | `stundenwerte_EB_03987_19510101_20251231_hist.zip`, 2,773,485 bytes, sha256 `6a968e6da83c783c4fa3a35196521021550bf56d1a64cde83cc9aeceb882329f`, md5 `7613bdc38862e060ecdf9ac07779e29b` (computed here; DWD publishes no digest). The research of 2026-11-08 recorded the same sha256. |
| Integrity | the CRC-32 of each of the 11 members verifies (`zipfile.testzip`) |
| Version | historical (quality-checked) part, 1951-01-01 to 2025-12-31; members written 2026-04-23, archive published 2026-06-10 (HTTP Last-Modified); dataset description version v24.03 |
| Station | 03987 Potsdam, 52.3812° N, 13.0622° E, 80.86 m; at this position since 1893; DWD since 1991 |
| Accessed | 2026-11-09 |

**Versioning.** DWD replaces the historical archive every year: the next one will cover 1951 to 2026 under another name, with any corrections incorporated, and the URL above will stop working. There is no DOI. The project pins this archive by its sha256 (the owner accepted this on the Issue); the committed sample is the project's extract and stays fixed. A learner who downloads a later archive gets a file that `./scripts/fetch-data.sh` refuses; the rows of 2015–2024 in it may differ only by DWD's later corrections.

The archive holds the product file `produkt_eb_stunde_19510101_20251231_03987.txt` (24,347,827 bytes, 322,776 rows) and metadata: the station's position (`Metadaten_Geographie`), its instruments with their depths (`Metadaten_Geraete_Erdbodentemperatur`), the parameters with their sources and units (`Metadaten_Parameter`), the operators (`Metadaten_Stationsname_Betreibername`), and lists of missing values and missing periods (`Metadaten_Fehlwerte`, `Metadaten_Fehldaten`), the last ones also as HTML.

**Extraction.** `tools/datasets/dwd_soil_extract.py` (standard library only) refuses any archive whose sha256 is not the one above or whose members fail their CRC, and writes whole lines of the product file, unchanged (padding, CRLF line ends, and the marker `-999` kept), the header line first and the rows in their order:

| Sample file | Rows | Bytes | sha256 | For |
|---|---|---|---|---|
| `eb_stunde_03987_2015_2024_6h.txt` | 14,610 at 00, 06, 12, 18 h of 2015–2024 | 1,110,441 | `d9fe4916f266c91a0f0ab1e42782682e12ae07a379fd1c98fe309afcfeb824d2` | the annual wave |
| `eb_stunde_03987_jja_2020_2024_1h.txt` | 11,040, every hour of June to August 2020–2024 | 839,121 | `ab6be9339237a2d66b4b552bc2ca42a6f3dbe7560c86a0803c0dcb6d067115cd` | the daily wave |

and copies the four small metadata files (`Geographie`, `Geraete`, `Parameter`, `Stationsname_Betreibername`; 6,120 bytes) unchanged. Two runs give the same bytes; `tools/datasets/README.md` says how to repeat it. Four readings a day, equally spaced, keep the sample small and still remove the daily cycle from the annual fit (a fit of the annual harmonic to samples equally spaced over each day is not biased by the daily harmonic); every hour is needed only for the daily wave, and only in summer, when it is largest.

Reader of the sample: `pbc.data.reference.dwd_soil.read_readings` (NumPy).

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Schema | `STATIONS_ID;MESS_DATUM;QN_2;V_TE002;V_TE005;V_TE010;V_TE020;V_TE050;V_TE100;eor`, `;`-separated, CRLF (the dataset description, "application schema") | the same in both sample files; every row of station 3987 and ending in `eor` |
| Units | temperatures in °C (description and `Metadaten_Parameter`), one decimal; `MESS_DATUM` as `YYYYMMDDHH` | every value a multiple of 0.1 K; at 5 cm the 6-hourly minimum is −10.0 °C and the hourly summer maximum 40.4 °C |
| Depths | `Metadaten_Geraete`: sensors at −0.05, −0.1, −0.2, −0.5, −1 m, PT100 (electrical) since 1978-03-01, conventional soil thermometers before; a 2 cm thermometer listed for 1951–1991, values (`Metadaten_Parameter`) for 1951–1972 only | `V_TE002` is −999 in every row of the sample (and of the file after 1972); the analysis uses the other five |
| Time reference | not stated, in the files or the description | not needed: the analysis uses the period and differences between depths only |
| Cadence | `Metadaten_Parameter`: from 2001-04-01 hourly values from the SYNOP report; 1951–1991 three or four readings a day, 1991–2004 three climate readings | sample 1: four readings a day, 2015-01-01 00 h to 2024-12-31 18 h; sample 2: every step 1 h within each summer |
| Quality | `QN_2` per row: 1 formal control only, 3 automatic control and correction, 10 quality control finished (description, "Quality Information") | every row of the sample has QN 3; QN 1 and 10 occur in the file only up to 2004 and 2005 |
| Missing values | −999 (description); `Metadaten_Fehlwerte` lists the gaps | absent rows 2023-09-05 12 h and 18 h; 2023-09-04 12 h without 5, 10, 20 cm; 2023-08-24 14–16 h without 5 and 10 cm; nothing else |
| Coverage | the archive 1951–2025 | 2015–2024 complete but for the above; of the 460 summer days, 459 complete at 5–50 cm |

The parsing test `tests/unit/test_data_dwd_soil.py::test_dwd_soil_sample_parses` asserts the field names, the shapes, the cadence, the hours and months, the missing rows and values, the 0.1 K resolution, the quality level, the depths and sensors of `Metadaten_Geraete`, the unit of each column in `Metadaten_Parameter`, the station's position, and the operator.

## Artifact labels

| Artifact | Type |
|---|---|
| `stundenwerte_EB_03987_19510101_20251231_hist.zip` (the product file) | `raw-measured` |
| `eb_stunde_03987_2015_2024_6h.txt`, `eb_stunde_03987_jja_2020_2024_1h.txt` (the sample) | `processed-measured` |
| the four `Metadaten_*.txt` files | `raw-measured` (record metadata, unchanged) |

The readings are what the thermometers recorded, after DWD's automatic control and correction (QN 3), which the record names but does not itemise per value. The sample selects rows without changing a value, and selection makes it `processed-measured`. The daily means, harmonics, diffusivities, and model lines are not artifacts of the record: `pbc.data.reference.dwd_soil` computes them, and the figure draws the model dashed and apart from the measured points, with its residuals.

## Reference figure

```
uv run python -m pbc.data.reference dwd-potsdam-soil-temperature --out dwd.png
```

The code is `src/pbc/data/reference/dwd_soil.py`. **Status label: processed** (rows selected, daily means, harmonics fitted). Panels: the daily mean of the four readings at each depth, 2015–2024; the hourly readings of the week from 2024-07-01; the amplitude of the annual and of the daily harmonic against depth (log scale), with the model; the phase lag behind 5 cm against depth, with the model; and the residuals of both straight lines.

The model is the heat equation of T6 (`pbc.thermodynamics.conduction`), ∂T/∂t = κ ∂²T/∂z², in a homogeneous half-space whose surface temperature is a cosine of angular frequency ω. Its periodic solution is a wave that decays and lags with depth by the same length, the damping depth d = √(2κ/ω):

T(z, t) = T̄ + A₀ e^(−z/d) cos(ωt − z/d − φ₀).

So ln A falls along a straight line of slope −1/d, and the phase lag rises along one of slope +1/d; κ = ωd²/2 follows from each. `test_the_damped_wave_solves_the_t6_heat_equation` checks this formula against T6's explicit scheme (`ftcs_step`): with the surface held at a daily cosine, the scheme settles into this wave, amplitude and lag within 0.2 % and 0.002 rad at 5–50 cm.

The chain, each step in the code:

1. **Annual wave.** For each calendar year of 2015–2024, a least-squares fit of a mean and the annual harmonic (ω = 2π / 365.2425 d) to the 6-hourly readings at each depth gives an amplitude and a phase; the phase lags are taken relative to 5 cm.
2. **Daily wave.** For each complete day of June to August, a fit of a mean, a linear trend over the day, and the daily harmonic to the 24 hourly readings at 5, 10, 20, and 50 cm; the complex amplitudes of a summer's days are averaged. At 100 cm the daily wave is about 0.01 K, below the 0.1 K of the readings, and is left out.
3. **Diffusivity.** Straight lines through −ln A and the lag against depth, fitted to the mean over the years (or summers), give d and κ twice; the same fit to each year (or summer) alone gives the scatter from which the standard error of the mean is taken.

**Caption.** *The annual and the daily temperature wave in the ground at Potsdam: both decay exponentially with depth and lag in proportion to it, as the heat equation predicts for a uniform soil, with residuals of at most 0.015 in ln A and 0.05 rad. The year reaches 3.2–3.4 m before it falls by e, the day only 0.17 m; both give a thermal diffusivity of about 1.1 × 10⁻⁶ m²/s. The estimates from amplitude and phase, and from different pairs of depths, differ by more than their statistical errors: the soil is not uniform.*

| Quantity | Annual wave (2015–2024, 10 years) | Daily wave (June–August 2020–2024, 5 summers) |
|---|---|---|
| amplitude at 5, 10, 20, 50, 100 cm | 12.52, 12.40, 12.08, 11.03, 9.32 K | 6.36, 4.63, 2.63, 0.46 K (to 50 cm) |
| lag behind 5 cm | 0, 0.014, 0.040, 0.124, 0.280 rad (16.3 days at 100 cm) | 0, 0.320, 0.808, 2.577 rad (9.8 h at 50 cm) |
| amplitude at the surface (the line at z = 0) | 12.80 K | 8.39 K |
| damping depth from amplitude, from phase | 3.193 m, 3.394 m | 0.1727 m, 0.1754 m |
| κ from amplitude | (1.015 ± 0.025) × 10⁻⁶ m²/s | (1.084 ± 0.013) × 10⁻⁶ m²/s |
| κ from phase | (1.147 ± 0.009) × 10⁻⁶ m²/s | (1.119 ± 0.009) × 10⁻⁶ m²/s |
| single years or summers, from amplitude | 0.93–1.13 | 1.04–1.11 |
| single years or summers, from phase | 1.09–1.18 | 1.09–1.14 |
| largest residual, ln A and lag | 0.007, 0.006 rad | 0.014, 0.047 rad |

The research's round 3 found 1.00 and 1.12 × 10⁻⁶ m²/s from the annual wave of 2010–2024 (daily means) and 1.09 and 1.06 from the daily wave of the summers 2015–2024; these numbers are of the same size, from other years and another treatment of the depths, and are not used here.

## Uncertainty and calibration

**Calibration.** The record documents no calibration of the sensors and no accuracy; the values are the readings after DWD's automatic control and correction (QN 3), described in the dataset description ("Validation and uncertainty estimate": QualiMet, Kaspar et al. 2013, doi:10.5194/asr-10-99-2013). Nothing is calibrated or corrected here.

**Statistical uncertainty.** The errors in the table are standard errors of the mean of the single years (10) or summers (5): they contain the weather's variation of the surface forcing from year to year, the quantisation of the readings to 0.1 K (an rms of 0.03 K per reading, small against amplitudes of 0.5 to 12 K averaged over thousands of readings), and any noise of the sensors.

**The model is the larger uncertainty.** A uniform half-space gives one κ for all four estimates and for every pair of depths. The data do not:

| Pair of depths | Annual, from amplitude | Annual, from phase | Daily, from amplitude | Daily, from phase |
|---|---|---|---|---|
| 5–10 cm | 2.49 | 1.32 | 0.90 | 0.89 |
| 10–20 cm | 1.44 | 1.45 | 1.14 | 1.53 |
| 20–50 cm | 1.09 | 1.27 | 1.09 | 1.05 |
| 50–100 cm | 0.88 | 1.02 | — | — |

(κ in 10⁻⁶ m²/s.) The annual amplitude falls by only 1 % between 5 and 10 cm, so that pair is ill-conditioned; the others range from 0.88 to 1.53. Annual amplitude and phase differ by 5 standard errors. A soil whose water content, texture, or compaction changes with depth and season, or that freezes, is not a uniform half-space; the record says nothing about the soil, and none of this is in the model. The four estimates span 1.01 to 1.15 × 10⁻⁶ m²/s, about ±7 % around 1.09: this spread, not the standard errors, is the uncertainty to quote for "the" diffusivity of this soil.

**Not bounded here.** The record gives no tolerance of the sensor depths. κ = ωd²/2 scales with the square of the depth spacing, so a relative error ε in the spacings changes κ by 2ε; an offset common to all sensors changes nothing. The sensors' accuracy is not given either; an offset of one sensor shifts only the mean, which the fits do not use, and a gain error of a few per cent would change one amplitude by as much. A lab that reports these numbers must say that the uncertainty is the scatter between years or summers, that the homogeneous model leaves a spread of about ±7 % between the estimates, and that the depths and sensors are taken as given.

Asserted by `tests/unit/test_data_dwd_soil.py`: the amplitudes and lags at each depth, the diffusivities and their standard errors, the damping depths, the surface amplitude, the ranges of the single years, the pairs of depths, the residuals, the counts of readings per year and of complete days per summer; that the estimator returns κ for a synthetic damped wave; and that the damped wave solves T6's scheme.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | DWD terms of use for the CDC open-data area, https://opendata.dwd.de/climate_environment/CDC/Terms_of_use.pdf, read 2026-11-09: "The Creative Commons BY 4.0 - Licence "CC BY 4.0" apply"; the dataset description, https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/soil_temperature/DESCRIPTION_obsgermany_climate_hourly_soil_temperature_en.pdf, page 4 (COPYRIGHT), the same |
| Redistribution of subsets | permitted | CC BY 4.0, https://creativecommons.org/licenses/by/4.0/: share in any medium or format |
| Publication of figures and derivatives | permitted | CC BY 4.0: adapt, remix, transform, and build upon |
| Modification and attribution | permitted, with credit, the licence, and an indication of changes | CC BY 4.0; DWD's source note at https://www.dwd.de/copyright, linked from the terms of use; the card's `attribution`, which the figure prints in short |

## Size, runtime, payload

Sample 1.96 MB in six files (caps: 2 MB per file, the largest file 1.11 MB; 8 MB per dataset). The reference figure takes about 4.5 s with the interpreter start (the analysis under 2 s) and about 170 MB peak memory; the PNG is about 430 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the text files are read at build time and not shipped. The learner's full download is the 2.8 MB archive (`./scripts/fetch-data.sh dwd-potsdam-soil-temperature`, checked against the card's sha256, until DWD replaces it), and the extraction repeats the sample byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected": size, sha256 and md5, CRCs, version and its yearly replacement; sha256 of the archive and of every sample file on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels"; the figure draws the model dashed, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/dwd_soil.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the scatter between years and summers, the spread of the estimates as the model's limit, the sensors and depths stated as not given |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the T7 lab, starts only when the owner says so (Issue #438).
- The download URL lasts until DWD's next yearly archive; the card's `downloads` entry then needs the new archive inspected and pinned, or the lab relies on the committed sample alone.
- The runner-up, the KIT experimental building (Zenodo 21157950), supports only a lumped cooling fit and is not inspected.
