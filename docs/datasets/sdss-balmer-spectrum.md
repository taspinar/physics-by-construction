# Dossier: SDSS spectrum with the Balmer series (plate 1949, fibre 480)

Card: `data/registry/sdss-balmer-spectrum.yaml`. Inspected 2026-11-09 for F102 (Issue #442), the measured-data lab Q7; the choice of this file is in [the dataset research](spike-candidates-2026-11-08.md), section "Q7: SDSS DR17 spectrum with Balmer lines". The owner accepted, on the Issue on 2026-11-08, a stellar or galactic Balmer spectrum from SDSS in place of a laboratory lamp, and asked that the SDSS data-policy sentence be confirmed to cover spectra.

**Decision: go.** Kind: calibrated optical spectrum of a starburst galaxy, with hydrogen and forbidden emission lines. The file, the conversion, the reference figure, the uncertainty, the estimates, and the rights pass, and the converted sample is committed at `data/samples/sdss-balmer-spectrum/`. The rights rest on the current SDSS data policy, which calls all SDSS data of the public data releases public domain. The SDSS-I/II page of SDSS Classic states a non-commercial approval clause by the Astrophysical Research Consortium (ARC) that contradicts that policy for this file; the owner decided that the current policy governs ([the owner's decision of 2026-11-09, second round, in the body of Issue #442](https://github.com/taspinar/physics-by-construction/issues/442)). "Rights" gives both statements and their URLs.

**History of the decision.** The first round of 2026-11-09 recorded `defer` (ADR 007 decision 2) for an inspected dossier whose rights were unclear: the two SDSS statements disagree, and under the addendum of 2026-11-08 to [ADR 007](../decisions/007-real-datasets-as-declared-inputs.md) a non-commercial term keeps a sample out of the repository without written permission. The owner's decision of the same day (second round) takes the current policy as the governing term, so the clause does not apply, and the card records `go`. The science, the file, and the conversion are unchanged; the dossier's numbers are now asserted on the committed sample.

## The file inspected

| | |
|---|---|
| Source | SDSS Science Archive Server, `https://data.sdss.org/sas/dr17/sdss/spectro/redux/26/spectra/lite/1949/spec-1949-53433-0480.fits` |
| File | `spec-1949-53433-0480.fits`, 172,800 bytes, sha256 `0f9aa3f5f187dde1fb42e6b58ab9b428e48a2d45f73e7254d954f48121a6a813`, md5 `d2fb551f179a3aba00f017d828de47a0` (computed here) |
| Integrity | sha1 `e288a7d8c1fa38d11d83757fce03038ab183a012`, equal to the line for this file in the SAS checksum list `26_spectra_lite_1949.sha1sum` of the same directory. The file has no FITS `CHECKSUM` or `DATASUM` keywords. |
| Version | Data Release 17, `RUN2D` 26; idlspec2d `v5_3_12`, co-added 2008-02-18; first released in DR7; SDSS-I/II Legacy survey, plate 1949, chunk99, plate quality "good" |
| Observation | 2.5 m Sloan Foundation Telescope, spectrograph 2, fibre 480, MJD 53433 (2005-03-04); three exposures per camera, 3000 s in all; RA 149.49866°, Dec 32.239656° |
| Object | pipeline class GALAXY, subclass STARBURST, `Z` = 0.014990165 ± 0.0000060 (template fit), `ZWARNING` 0 |
| Accessed | 2026-11-09 |

The file has four HDUs: the primary header (no data), the binary table `COADD` (3,843 rows), `SPECOBJ` (one row of 126 columns), and `SPZLINE` (29 rows). The research of 2026-11-08 inspected the same file and found the same size and a matching sha1.

**Conversion (ADR 007, addendum of #417).** FITS is converted once, outside the build. `tools/datasets/sdss_spec_to_csv.py` reads the file with NumPy alone, using the header and table reader of `tools/datasets/tess_lc_to_csv.py` (AST8), which is already tested. It refuses any input whose sha256 or SAS sha1 is not the one above, and any file whose wavelengths are not vacuum or whose flux unit is not `BUNIT` `1E-17 erg/cm^2/s/Ang`. It writes the `COADD` columns `loglam`, `flux`, `ivar`, `and_mask`, and `wdisp` of every pixel, in order, each float as the shortest decimal that reads back to the same float32. Five comment lines give the source and its checksum, the conversion, the units, and the pipeline's class, redshift, and heliocentric correction. The output is 153,300 bytes, sha256 `90dff68b9df582a8deba83f21f0eefbd510d00866481c875abf4202ebdb1b163`, and two runs give the same bytes; the committed sample is this file, and the dataset check compares its sha256 with the card. No FITS library is added.

The columns not kept are `or_mask` (bits set in any exposure), `sky` (the subtracted sky), and `model` (the pipeline's best-fit template, a model). The analysis needs none of them. The line list of `SPZLINE` gives the laboratory vacuum wavelengths that the reference module copies, with that source named, as `FORBIDDEN` and `BALMER_LAB`. `SPZLINE`'s own line redshifts come from a fit with the lines tied together (0.014987 to 0.014989, ± 0.0000006 each), so they are not independent measurements and are not used.

Reader of the converted file: `pbc.data.reference.sdss_balmer.read_spectrum` (NumPy).

## Schema, units, cadence, masks, coverage

| Item | What the file documents | What this dossier established |
|---|---|---|
| Schema | `COADD`: `flux`, `loglam`, `ivar`, `and_mask`, `or_mask`, `wdisp`, `sky`, `model` (TFORM `E` or `J`; no `TUNITn`) | five columns kept; 3,843 rows |
| Units | primary header: `BUNIT` 1E-17 erg/cm^2/s/Ang; `VACUUM` T; `WFITTYPE` LOG-LINEAR with step `COEFF1` 1e-4; `HELIO_RV` 10.566 km/s | `loglam` is log10 of the vacuum, heliocentric wavelength in Å; `ivar` is in the inverse square of the flux unit |
| Grid | log-linear in wavelength | every step is 1.0000e-4 in log10 (69.0 km/s); 3802.77 to 9210.86 Å. `loglam` is stored as float32, whose rounding (at most 1.2e-7 in log10, 0.08 km/s) is negligible here |
| Cadence | not a time series | one co-added spectrum |
| Masks | `and_mask`: SPPIXMASK bits set in every exposure, defined in the SDSS bitmask documentation (https://www.sdss4.org/dr17/algorithms/bitmasks/), not in the file | 27 pixels, all bit 23 BRIGHTSKY ("sky level > flux + 10*(flux_err)"), at the sky lines 5577–5580, 7914–7916, and 8344–8962 Å; none inside a line window. No pixel has `ivar` 0 |
| Resolution | `wdisp`: line-spread sigma in pixels of the log grid (SDSS spec data model) | median 0.83 pixel, 0.67 to 1.09. At 5000 Å that is about 0.96 Å or 57 km/s; the lines fit at 70 to 77 km/s (86 for [Ne III]), so they are resolved only barely |
| Signal | | median flux 86, median signal-to-noise 39 per pixel |

The analysis keeps the 3,816 pixels with `ivar` > 0 and `and_mask` 0.

## Artifact labels

| Artifact | Type |
|---|---|
| `spec-1949-53433-0480.fits` | `calibrated-observation` |
| `spec-1949-53433-0480.csv` (the converted file, the committed sample) | `calibrated-observation` |

The co-added spectrum is the pipeline's calibrated observation: flux-calibrated on standard stars, wavelength-calibrated on arc lamps and sky lines, and converted to vacuum and the heliocentric frame. The conversion changes no value, so the CSV keeps the type. The line fits, the redshift calibration, and the Rydberg constant are not artifacts of the record. `pbc.data.reference.sdss_balmer` computes them, and the figure draws every model dashed and apart from the measured points, with residuals.

## Reference figure

```
uv run python -m pbc.data.reference sdss-balmer-spectrum --out sdss.png
```

The sample is reproduced from the learner's download with
`./scripts/fetch-data.sh sdss-balmer-spectrum` and
`tools/datasets/sdss_spec_to_csv.py` (`tools/datasets/README.md`), byte for
byte.

The code is `src/pbc/data/reference/sdss_balmer.py`. The figure is drawn from the committed sample. The numbers below were first produced on 2026-11-09 from a learner's download and its conversion, and the same numbers come from the committed sample, which is that conversion's output. **Status label: processed** (lines fitted, redshift calibrated). The panels are:

- the whole spectrum on a log flux scale, with the four Balmer lines marked;
- each Balmer line's pixels with error bars, the fitted Gaussian on a straight continuum (the panel spans the fit window), and the residuals over the pixel error;
- the velocity of each forbidden line about the calibration, with the fitted line z(λ) and the single-z alternative;
- each Balmer line's Rydberg constant relative to CODATA R_H: from the calibrated z(λ) and from one z, with the weighted mean, the laboratory-hydrogen value, and R_H.

The steps, each in the code:

1. **Lines.** Every line is fitted where its brightest good pixel lies, within ±4 Å of its expected place, so the window is set by the data. The fit covers ±12 Å beyond the outermost line of its group: a straight continuum (its levels at the two window edges) plus one Gaussian per line, each averaged over its pixel's width in wavelength. It is weighted by `ivar`. The groups are H α with [N II] 6550 and 6585, and the [S II] doublet; every other line is fitted alone. Initial guesses come from the peak of [O III] 5008 and from Balmer's own constant of 1885 (B = 3645.6 Å). A guess off by ±3 × 10⁻⁴ in z (90 km/s) gives the same centres to 10⁻⁶ Å (tested).
2. **Lines used.** Thirteen. The hydrogen lines are H α, H β, H γ, H δ (n = 3 to 6, all falling to level 2). H ε falls on [Ne III] 3969, and n = 8 on He I 3889, which the SDSS line list names "H_epsilon". The forbidden lines are [Ne III] 3870, [O III] 4960 and 5008, [O I] 6302, [N II] 6550 and 6585, [S II] 6718 and 6733, and [Ar III] 7138, with the rest wavelengths of the SDSS line list (vacuum). The [O II] 3727 doublet lies at 3783 Å observed, below the spectrum.
3. **Calibration.** z of each forbidden line is λ_obs/λ_rest − 1. A weighted straight line z(λ) = z0 + z1 (λ − 5500 Å)/1000 Å is fitted through them. It calibrates the wavelength scale and the gas velocity together, as lamp lines would calibrate a laboratory spectrometer.
4. **Rydberg constant.** Each Balmer line's rest wavelength is λ_obs / (1 + z(λ_obs)), and its R is 1/(λ_rest (1/4 − 1/n²)). R is the weighted mean of the four, and the chi-square of the four about it tests the 1/n² law. The hydrogen rest wavelengths are never used. From the hydrogen lines alone only (1 + z)/R is measured: scaling every forbidden rest wavelength by a factor scales R by the same factor (`test_the_redshift_and_r_are_degenerate_without_the_forbidden_lines`).

**Caption.** *Four Balmer lines of hydrogen in the spectrum of a starburst galaxy at z = 0.015, each fitted as a Gaussian. With the redshift calibrated on nine forbidden lines of other elements, the four lines follow 1/λ = R (1/4 − 1/n²) with one constant, R = 10,968,065 ± 41 m⁻¹, within their errors. A single redshift for all lines leaves a trend from H α to H δ. The value lies 2.8 × 10⁻⁵ above the laboratory R_H. The Bohr formula's neglect of fine structure explains 1.1 × 10⁻⁵ of that; the rest is a velocity of 5 km/s that this spectrum cannot separate from R.*

| Line | Observed centre [Å] | Error, scaled [Å] | Width σ [km/s] | Reduced chi-square of its fit |
|---|---|---|---|---|
| H α | 6663.034 | 0.028 | 75 | 16.7 (with [N II]) |
| H β | 4935.476 | 0.011 | 72 | 1.3 |
| H γ | 4406.627 | 0.025 | 74 | 4.6 |
| H δ | 4164.245 | 0.042 | 74 | 5.8 |

The research of 2026-11-08 found 6663.034, 4935.476, 4406.626, and 4164.240 Å for the same lines with its own code.

| Calibration on the forbidden lines | Value |
|---|---|
| z0 (at 5500 Å) | 0.0149937 ± 0.0000030 |
| slope | 4.2 ± 1.0 km/s per 1000 Å |
| chi-square | 40.4 for 7 degrees of freedom |
| velocities about it [km/s] | [Ne III] 3870 −9.3; [O III] 4960 +1.0, 5008 +1.4; [O I] 6302 +3.0; [N II] 6550 −2.5, 6585 −1.8; [S II] 6718 −0.6, 6733 +0.6; [Ar III] 7138 −4.8 |

| Rydberg constant | Value |
|---|---|
| per line, n = 3, 4, 5, 6 [m⁻¹] | 10,968,088 ± 46; 10,968,054 ± 23; 10,968,091 ± 63; 10,968,100 ± 109 |
| R (weighted mean) | **10,968,065 ± 41 m⁻¹** |
| chi-square of the four lines | 0.74 for 3 degrees of freedom |
| R_H = R∞/(1 + mₑ/mₚ), CODATA 2018 | 10,967,758.34 m⁻¹ |
| R − R_H | +2.80 × 10⁻⁵ relative (7.4 standard errors) |
| the same formula on the laboratory wavelengths (fine-structure centroids) | 10,967,881 m⁻¹, +1.12 × 10⁻⁵ relative to R_H |
| R − laboratory value | +1.67 × 10⁻⁵ relative, 5.0 km/s (4.4 standard errors) |
| with one z for all lines instead | 10,968,138 ± 85 m⁻¹, chi-square 29.6 for 3; per line 10,967,929 (H α) rising to 10,968,328 (H δ) |

The pipeline's template redshift (0.0149902) lies 1.0 km/s below the calibration's z0. It is a different method and is not used.

## Uncertainty and calibration

**Calibration** is the pipeline's: the record documents its steps (the header keywords above and the SDSS documentation). None is redone. The record documents **an uncertainty per pixel**, `ivar`, which is propagated through every line fit. The checks of it, in order:

- **The line fits.** Faint lines fit with reduced chi-square near 1 ([S II] 1.1, [Ne III] 0.7, [Ar III] 1.2, H β 1.3). Bright lines do not: H α with [N II] 16.7, [O III] 5008 9.4, H γ 4.6, H δ 5.8. At this signal-to-noise a line is not exactly a Gaussian on a straight continuum. The residual panels show it, and under H γ and H δ they show the broad absorption troughs of the galaxy's young stars, which the straight continuum does not follow. Each centre's error is therefore scaled by √(reduced chi-square) when that is above 1. The H α error becomes 0.028 Å instead of 0.007 Å.
- **The forbidden lines.** They scatter about the calibration with chi-square 40.4 for 7 degrees of freedom, 2.4 times their scaled errors: the ions differ in velocity by a few km/s ([Ne III] −9, [Ar III] −5). The calibration's covariance is scaled by that ratio and propagated into R.
- **The Balmer lines.** The four values of R agree with chi-square 0.74 for 3 degrees of freedom with the calibrated z(λ), and 29.6 with one z. The calibration is fitted only to the forbidden lines, so this agreement is a test it passes, not a fit.
- **Sensitivity to the choices.** `sensitivity` repeats the analysis:

| Choice | R [m⁻¹] | ± | chi-square (3 dof; 2 without H δ) | calibration chi-square |
|---|---|---|---|---|
| the figure: ±12 Å, four lines, z(λ) | 10,968,065 | 41 | 0.74 | 40.4 for 7 |
| window ±9 Å | 10,968,065 | 46 | 0.88 | 39.9 for 7 |
| window ±16 Å | 10,968,072 | 40 | 0.58 | 38.6 for 7 |
| without H δ (most stellar absorption) | 10,968,064 | 41 | 0.64 | 40.4 for 7 |
| without [Ne III] in the calibration | 10,968,101 | 25 | 1.65 | 5.7 for 6 |
| one z for all lines | 10,968,138 | 85 | 29.6 | 153.8 for 8 |

The window and H δ move R by under 8 m⁻¹. [Ne III], the bluest calibration line and the one that sets most of the slope, moves R by 36 m⁻¹, within one standard error. These rows are a **sensitivity range of the choices**, not an uncertainty interval. The last row is the single-z comparison.

- **Not bounded by this record.** First, R and (1 + z) appear in the hydrogen lines only as their ratio. A common velocity offset between the hydrogen and the forbidden-line gas, or a constant error of the wavelength scale, moves R one for one, and nothing in the spectrum separates the two. The 1.67 × 10⁻⁵ (5.0 km/s) between R and the laboratory value is of that size: a few km/s, the floor the research of 2026-11-08 expected. Second, the Bohr formula is not hydrogen: the laboratory Balmer lines are fine-structure multiplets, whose centroids give 1.12 × 10⁻⁵ more than R_H by the same formula. A lab that reports these numbers must say that R is measured to about 3 × 10⁻⁵ against R_H. It must say what part of the difference the Bohr formula explains and what part a velocity explains, and that the line errors are scaled by the fits' reduced chi-square.

Asserted by `tests/unit/test_data_sdss_balmer.py` on a synthetic spectrum that the test writes as a FITS file and sends through the same conversion: the conversion keeps every value and refuses an unpinned or non-vacuum file, the lines are found where they were put, and the calibration recovers the injected z and slope. It also asserts that R comes back within three standard errors with the 1/n² law holding, that one z is biased by an injected slope in the same direction as here, the z–R degeneracy, independence from the starting guess, and the figure's status and conventions. On the committed sample it asserts this dossier's numbers: the field names, shapes, units, masks, and grid of the record (`test_the_committed_sample_parses`, the card's sample test), the four line centres, their scaled errors, widths, and the fits' reduced chi-square, the calibration and its velocities, R with its error and chi-square, the per-line values, the relative differences, and the sensitivity table.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the current SDSS data policy, https://www.sdss.org/collaboration/image-use-policy/, read 2026-11-09: "All SDSS data released in our public data releases are considered in the public domain"; the file is on the public Science Archive Server under DR17, without login |
| Redistribution of subsets | permitted | the same policy: public-domain data carry no restriction on redistribution. https://classic.sdss.org/collaboration/credits.html, read 2026-11-09, which the current https://www.sdss.org/collaboration/citing-sdss/ links as the "SDSS-I/II acknowledgment (SDSS-I, SDSS-II Legacy, SDSS-II SEGUE-1, SDSS-II Supernova, DR 1-7)", states: "Data from the SDSS public archive may not be used for any commercial publication or other commercial purpose except with explicit approval by the Astrophysical Research Consortium (ARC)". For this file that contradicts the current policy; [the owner decided on 2026-11-09](https://github.com/taspinar/physics-by-construction/issues/442) that the current policy governs |
| Publication of figures and derivatives | permitted | https://www.sdss.org/collaboration/image-use-policy/ (public domain); the contradicting clause of https://classic.sdss.org/collaboration/credits.html does not govern, by the same decision |
| Modification and attribution | permitted, with the acknowledgement | https://www.sdss.org/collaboration/image-use-policy/: public-domain data may be modified, and the page asks that SDSS be credited; https://www.sdss.org/collaboration/citing-sdss/ asks for the SDSS-I/II acknowledgement (the card's `attribution`) and the survey citations |

**The owner's question: does the sentence cover spectra?** Yes. It reads "All SDSS data released in our public data releases", with no exception for older releases or for spectra, and this spectrum is SDSS data released in DR7 and again in DR17. It sits on the image-use page, and no spectra-specific licence page exists, as the research found.

**The contradiction, stated plainly.** The SDSS-I/II page of SDSS Classic (https://classic.sdss.org/collaboration/credits.html), which the current citation page links for DR1–7 data, says that data from the SDSS public archive may not be used commercially without ARC's explicit approval. For this file that contradicts the current policy, and the two cannot both hold for a commercial reuse. The owner decided on 2026-11-09 that the current policy governs ([the owner's decision in the body of Issue #442](https://github.com/taspinar/physics-by-construction/issues/442), "Owner's decision of 2026-11-09 (second round)"). The card therefore records the licence as `equivalent-permission` (public domain, which ADR 007 decision 4 admits as an equivalent of CC0, as the TESS card does for MAST data), and all four answers `permitted`. The site credits SDSS with the card's `attribution`.

## Size, runtime, payload

The FITS file is 172,800 bytes and the converted CSV 153,300 bytes (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 2 s with the interpreter start (the thirteen line fits under 0.1 s) and about 130 MB peak memory. The PNG is about 340 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays far inside the 30 s warning, the 60 s limit, and the 3 MB payload; the CSV is read at build time and not shipped. The learner's download is the 173 KB FITS file (`./scripts/fetch-data.sh sdss-balmer-spectrum`, checked against the card's sha256), and the conversion repeats the CSV byte for byte. CI reads the committed 153 KB sample offline and never downloads.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected": size, sha256, md5, the SAS sha1, data release and pipeline version; the card's `downloads` |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration" |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels"; the figure draws every model dashed, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/sdss_balmer.py`, drawn from the committed sample, the output of the pinned conversion; `tests/unit/test_data_sdss_balmer.py` runs the same chain on a synthetic file, checks the figure's status and conventions, and asserts this dossier's numbers on the sample |
| 5. Rights, four answers with their source | "Rights"; the card's `rights`: all four `permitted` on the current SDSS policy, the contradicting SDSS-I/II clause named, and the owner's decision that the current policy governs cited |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": `ivar` propagated, errors scaled by the fits' reduced chi-square, the calibration tested by the Balmer lines' agreement, the choices as a sensitivity analysis, the z–R degeneracy and the fine structure stated |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the Q7 lab, starts only after a `go` and when the owner says so (Issue #442).
- The runner-up, the Hannover Rb absorption spectra (CC BY-SA 3.0, accepted by #417), is not inspected; its science caveats (no absolute frequency offset, no free spectral range) stand.
