# Dossier: TESS light curve of WASP-18, sector 29

Card: `data/registry/tess-exoplanet-light-curves.yaml`. Inspected 2026-11-08 for F104 (Issue #420), the measured-data lab AST8; the choice of this file is in [the dataset research](spike-candidates-2026-11-08.md). The card was a `survey-only` card of the general TESS record since 2026-10-09; it now describes the one file inspected.

**Decision: go.** Kind: calibrated photometric time series of a star with a transiting planet. Recorded under the owner's decision of 2026-11-08 on Issue #420 (work towards a `go` on the strength of the research, judged per dossier, every requirement of ADR 007 checked here); the checklist below names the evidence for each.

## The file inspected

| | |
|---|---|
| Source | MAST, `https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:TESS/product/<file>`; collection "TESS Light Curves - All Sectors", doi 10.17909/t9-nmc8-f686 (TESS Team, STScI/MAST) |
| File | `tess2020238165205-s0029-0000000100100827-0193-s_lc.fits`, 1,915,200 bytes, sha256 `c89434e50db863e589c9321cf29c93e449ef1526f1a9db19552446b721fd0949`, md5 `514a19b42d2d31a6a3edaf83784c704d` (computed here; MAST publishes no digest) |
| Integrity | the FITS `CHECKSUM` keyword of each of the three HDUs verifies (the 32-bit ones'-complement sum of the HDU is −0); the file has no `DATASUM` keywords. A changed byte makes the check fail. |
| Version | SPOC pipeline `spoc-5.0.13-20201001`, data release 43, file version 1.0, written 2020-10-04 by NASA Ames |
| Target | TIC 100100827 (WASP-18), TESS magnitude 8.83, sector 29, camera 2, CCD 2; RA 24.35431°, Dec −45.67788° |
| Accessed | 2026-11-08 |

The file has three HDUs: the primary header (no data), the binary table `LIGHTCURVE` (18,864 rows, 20 columns), and the 11 × 11 aperture image. The research of 2026-11-08 inspected the same file and found the same size and verified checksums.

**Conversion (ADR 007, addendum of #417).** FITS is converted once, outside the build: `tools/datasets/tess_lc_to_csv.py` reads the file with NumPy alone, refuses any input whose sha256 is not the one above or whose FITS checksums do not verify, and writes the columns `TIME`, `PDCSAP_FLUX`, `PDCSAP_FLUX_ERR`, `QUALITY` of every row, in the order of the table. Each value is the shortest decimal that reads back to the same binary number (float64 for the time, float32 for the fluxes), a missing value is `nan`, and four comment lines name the source, its checksum, the conversion, and the units. The output, `data/samples/tess-exoplanet-light-curves/wasp18_s0029_lc.csv`, is 703,878 bytes, sha256 `96cc3d255288b4158386e035358c7a8f4787180931fbe9863acd5113d14ecf11`; two runs give the same bytes. `tools/datasets/README.md` says how to repeat it. No FITS library is added: the project has none, and the script's reader is tested on a small FITS file written by the test.

Reader of the sample: `pbc.data.reference.tess_wasp18.read_light_curve` (NumPy).

## Schema, units, cadence, masks, coverage

| Item | What the file documents | What this dossier established |
|---|---|---|
| Schema | 20 columns: `TIME`, `TIMECORR`, `CADENCENO`, `SAP_FLUX`, `SAP_FLUX_ERR`, `SAP_BKG`, `SAP_BKG_ERR`, `PDCSAP_FLUX`, `PDCSAP_FLUX_ERR`, `QUALITY`, centroids and their errors, `POS_CORR1`, `POS_CORR2` | four are kept; 18,864 rows in each |
| Units | `TUNITn`: `TIME` in "BJD - 2457000, days" (`TIMESYS` TDB, `TIMEREF` SOLARSYSTEM); fluxes and errors in e-/s; `QUALITY` none | the median PDCSAP flux of the good cadences is 47,955 e-/s; the median error is 540 ppm of it |
| Cadence | `TIMEDEL` 2 min; 60 frames of 2 s co-added (`NUM_FRM`, `FRAMETIM`), `DEADC` 0.792 | every step between finite time stamps is 120.0 s |
| Coverage | `DATE-OBS` 2020-08-26, `DATE-END` 2020-09-21; `TSTART` 2088.2425, `TSTOP` 2114.4373 | time stamps from 2088.2377 to 2114.4366; good cadences from 2088.24 to 2112.14, none from 2098.44 to 2102.33 |
| Missing values | NaN in the table | 681 cadences without a time, contiguous between 2101.378 and 2102.325, all flagged 8; 4,503 cadences without a PDCSAP flux and error (always together) |
| Quality flags | a bit mask per cadence, defined in the TESS Science Data Products Description (not in the file) | nonzero for 4,506 cadences: 8 (681), 32 (14), 128 (232), 160 (1), 164 (6), 168 (1), 512 (3), 4096 (2,102), 32768 (1,466); every flagged cadence but the three of value 512 has no PDCSAP value |

The analysis keeps the 14,358 cadences of quality 0 with finite values; it does not interpret the bits. The parsing test `tests/unit/test_data_tess_wasp18.py::test_tess_wasp18_sample_parses` asserts the field names, the shapes, the units, the cadence, the masks, and the counts above.

## Artifact labels

| Artifact | Type |
|---|---|
| `tess2020238165205-s0029-0000000100100827-0193-s_lc.fits` | `calibrated-observation` |
| `wasp18_s0029_lc.csv` (the sample) | `calibrated-observation` |

The PDCSAP flux is the pipeline's calibrated aperture photometry, corrected for instrumental systematics (`PDCMETHD` msMAP), for the flux of other stars in the aperture (`CROWDSAP` 0.984), and for the star's flux outside it (`FLFRCSAP` 0.949). The sample changes no value, so it keeps the type. The normalised transits, the fitted model, and the mid-times are not artifacts of the record: `pbc.data.reference.tess_wasp18` computes them, and the figure draws the model dashed and apart from the measured points, with its residuals.

## Reference figure

```
uv run python -m pbc.data.reference tess-exoplanet-light-curves --out tess.png
```

The code is `src/pbc/data/reference/tess_wasp18.py`. **Status label: processed** (selected, normalised, and folded). Panels: the good cadences of the sector over their median, with the 21 transits used marked; the 21 transits folded on the measured period, with 6-minute bins, the fitted model, and the part of the window excluded from the baseline shaded; the residuals; and the mid-time of each transit against the fitted ephemeris.

The chain, each step in the code:

1. **Transits found in the data.** Runs of at least ten good cadences more than 0.5 % below the running median of 0.5 d: 21 dips, numbered by their spacing, which gives a first period of 0.94145 d. No published ephemeris is used.
2. **Normalisation.** Every transit with at least 20 good cadences on each side within ±0.16 d of its mid-time and at least 95 % of its cadences within ±0.065 d is divided by a parabola in time fitted to the flux of the window outside ±0.065 d. All 21 qualify (4,819 cadences). A parabola, not a straight line: the planet raises tides on its star, whose brightness then varies at half the orbital period and is lowest near mid-transit, so the baseline around a transit is curved.
3. **Model.** The AST7 transit of `pbc.astrophysics.transit`: a dark disk of radius p (in stellar radii) on a circular orbit of radius a and impact parameter b, over a star darkened by the quadratic law with u1, u2. The flux sums the star over 200 rings, each ring's share of the planet from the closed-form overlap of two disks (`overlap_area`), and averages the model over the 120 s exposure (5 points). It equals AST7's closed form for a uniform star to 1e-12, its central depth to 1e-5 relatively, and AST7's grid integration to 3e-6 (`test_the_transit_model_reduces_to_the_ast7_closed_forms`); 200 rings and 5 points are within 2 ppm of the limit.
4. **Fits.** The shape (p, a, b, u1, u2) is fitted to the normalised transits on a fixed ephemeris, weighted by `PDCSAP_FLUX_ERR`; then each transit's mid-time with the shape fixed; then the ephemeris t0 + nP by a weighted straight line through the 21 mid-times. Steps 2 to 4 are repeated once on the new ephemeris. The ephemeris is fitted apart because, in one joint fit, the period is known about 10⁵ times better, relatively, than u2, and the identifiability test of `pbc.data.fit.fit_curve` reports that contrast as a degeneracy; the covariance of the joint fit, computed for this dossier from the Jacobian at the final values, gives correlations of at most 0.001 in size between the ephemeris and the shape, and the same standard errors as the separate fits.

**Caption.** *Twenty-one transits of WASP-18 b in TESS sector 29, normalised to the flux around each and folded on the period measured from them. The planet blocks 1.07 % of the star's light at mid-transit; a transit lasts 2.19 h, ingress and egress 14 min each. A planet of 0.098 stellar radii crossing a limb-darkened star at impact parameter 0.40 reproduces the 4,819 cadences with reduced chi-square 1.16 on the pipeline's errors, and its residuals scatter about zero. The single transits' mid-times scatter about the fitted ephemeris by more than their errors.*

| Quantity | Fit (standard error from `PDCSAP_FLUX_ERR`) |
|---|---|
| p = Rp/R★ | 0.09795 ± 0.00039 |
| a/R★ | 3.437 ± 0.035 |
| b | 0.400 ± 0.027 |
| u1, u2 | 0.237 ± 0.047, 0.266 ± 0.088 |
| inclination arccos(b/a) | 83.32° |
| depth at mid-transit (with limb darkening; p² = 9,593 ppm) | 10,696 ppm |
| T14, T23 (`durations` of AST7) | 2.188 h, 1.720 h |
| ingress (T14 − T23)/2 | 14.0 min |
| P | 0.9414504 ± 0.0000044 d (± 0.38 s) |
| t0 (BJD − 2457000, transit 0) | 2098.205325 ± 0.000036 (± 3.1 s) |
| mean stellar density 3π a³/(G P²) | 867 kg/m³ |

The fit identifies all five shape parameters (no warning of `fit_curve`). They are strongly correlated: a with b −0.98, u1 with u2 −0.97, p with b +0.89. The data fix the depth, the total duration, and the ingress well; a, b, and the limb darkening they fix only together. The research's T14 of 2.185 ± 0.004 h, from another method, agrees with 2.188 h.

The stellar density is a check of the geometry from Kepler's third law alone, with the planet's mass neglected. The TIC values in the FITS header (`LOGG` 4.25879, `RADIUS` 1.34658 solar radii, given without uncertainty) imply 3g/(4πGR) = 693 kg/m³, 20 % lower. The dossier does not resolve the difference: the TIC values are catalogue estimates, and a and b trade off (a 1 % change in a is a 3 % change in density). Comparing these results with published values for WASP-18 b is for the lab, with the sources cited there; none is used here.

## Uncertainty and calibration

**Calibration** is the pipeline's: the record documents its steps (keywords above, and the TESS Science Data Products Description), and none is redone or applied here. The record documents **an uncertainty per cadence**, `PDCSAP_FLUX_ERR` (about 540 ppm), which is propagated through the normalisation into the fit. Three checks of it, and one sensitivity analysis:

- **The shape fit.** Reduced chi-square 1.16 for 4,814 degrees of freedom: the errors describe the scatter of the cadences to within 8 % (residual rms 583 ppm, median error 540 ppm). The standard errors in the table are from the errors as given; scaling them by √1.16 = 1.08 is the usual allowance for the excess.
- **The mid-times.** Chi-square 41.8 for 19 degrees of freedom about the linear ephemeris: the 21 mid-times scatter about 1.5 times more than their errors (median 0.23 min, largest offset 0.98 min). Noise correlated over minutes (the star, or systematics left by the pipeline) is the likely cause; it is not separated here. The errors of P and t0 above are from the timing errors as given; scaled by √(41.8/19) = 1.48 they become 0.57 s and 4.6 s.
- **Sensitivity to the normalisation.** `sensitivity` repeats the analysis with other windows and baselines:

| Normalisation | p | a/R★ | b | depth at mid-transit |
|---|---|---|---|---|
| parabola, ±0.16 d (the figure) | 0.09795 | 3.437 | 0.400 | 10,696 ppm |
| parabola, ±0.12 d | 0.09769 | 3.448 | 0.394 | 10,647 ppm |
| parabola, ±0.20 d | 0.09818 | 3.427 | 0.405 | 10,739 ppm |
| straight line, ±0.16 d | 0.09905 | 3.387 | 0.426 | 10,892 ppm |

The window moves p by less than one standard error (−0.00026 and +0.00023) and the depth by about 50 ppm either way; this is a **sensitivity range of the normalisation**, not an uncertainty interval. A straight line sits above the curved baseline and makes the transit 196 ppm deeper; it is the wrong baseline for this star, shown to say why the parabola is used.

- **Not bounded here.** The pipeline's systematics and crowding corrections are taken as released: the record states the crowding factor (1.6 % of the aperture's flux from other stars, removed) without its uncertainty, and an error in it scales the depth alike for every transit, which no fit of these data can reveal. A lab that reports these numbers must say that the uncertainties come from the pipeline's errors, that the mid-times show them too small by about 1.5, that the window and baseline are a sensitivity analysis, and that the crowding and systematics corrections are the pipeline's.

Asserted by `tests/unit/test_data_tess_wasp18.py`: the 21 dips and the first period, the fitted values and standard errors, the reduced chi-square and the correlations, the derived depth, durations, ingress, inclination and density, the ephemeris and the mid-time chi-square, the residual scatter, the sensitivity table, and the TIC density.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | MAST data use policy, https://archive.stsci.edu/publishing/data-use, read 2026-11-08: "Most data hosted at MAST are in the public domain ... and therefore do not have restrictions on use"; TESS has no exclusive access period, https://heasarc.gsfc.nasa.gov/docs/tess/faq.html ("all TESS data becomes immediately public when it arrives in the TESS archive MAST") |
| Redistribution of subsets | permitted | the same policy: the restricted classes are data under exclusive access, high-level science products under CC BY 4.0, and the copyrighted Digitized Sky Survey and Guide Star Catalogs; a TESS light curve is none of them |
| Publication of figures and derivatives | permitted | the same policy, no restrictions on use |
| Modification and attribution | permitted, with the acknowledgement | the same policy expects the mission and STScI to be acknowledged; the TESS text is at https://archive.stsci.edu/publishing/mission-acknowledgements (section TESS) and https://heasarc.gsfc.nasa.gov/docs/tess/faq.html; it is the card's `attribution`, and the figure prints a shortened form |

The card records the licence as `equivalent-permission` (ADR 007 decision 4): public domain with no restriction on use, which grants all four rights that decision 4 asks of CC0 or CC BY, with the acknowledgement as an expectation of the archive.

## Size, runtime, payload

Sample 704 KB (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 6.5 s with the interpreter start (the two passes of the fit about 4 s) and about 190 MB peak memory; the sensitivity analysis adds 11 s and is not needed by a figure. The PNG is about 300 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the CSV is read at build time and not shipped. The learner's full download is the 1.9 MB FITS file (`./scripts/fetch-data.sh tess-exoplanet-light-curves`, checked against the card's sha256), and the conversion repeats the sample byte for byte. CI reads only the committed file.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected": size, sha256 and md5, FITS checksums, pipeline and data release; sha256 of the file and of the sample on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels"; the figure draws the model dashed, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/tess_wasp18.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the pipeline's per-cadence errors, tested by the reduced chi-square and the mid-time scatter; the normalisation as a sensitivity analysis; the calibration and crowding correction stated as the pipeline's |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the AST8 lab, is the lesson `site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd` (Issue #420, started on the owner's word of 2026-11-12). It reuses the analysis of `pbc.data.reference.tess_wasp18`, adds the uniform-star comparison, the phase curve outside the transits, and the standard errors of the depth and durations propagated through the covariance of the fit, and makes no comparison with published values.
- The card keeps the id of the survey's general TESS card and now describes this one file; another TESS file would need its own inspection and conversion.
- The runner-up, Pi Mensae in sector 1 (a transit about 30 times shallower), is not inspected.
