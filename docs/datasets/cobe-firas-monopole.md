# Dossier: COBE FIRAS CMB monopole spectrum (LAMBDA, Table 4 of Fixsen et al. 1996)

Card: `data/registry/cobe-firas-monopole.yaml`. Inspected 2026-11-25 for F155 part 1 (Issue #619), the reproduction track of the Scientific Research Workspace and the capstone RR8. The choice of the paper and the file is in the feature plan of Issue #619 ("The reproduction track: COBE-FIRAS"); the owner chose option A (the spectrum fit, the residual spectrum, the weighted rms, the bounds on y and μ) on the Issue on 2026-11-25.

**Decision: go.** Kind: a derived spectrum of a NASA mission, the CMB monopole with the residuals, uncertainties, and Galactic spectrum of the paper's Table 4. The file, the reference figure, the uncertainty, the estimates, and the rights pass, and the file is committed unchanged at `data/samples/cobe-firas-monopole/`. The rights rest on NASA's public-domain policy for mission data, accepted as `equivalent-permission` by [the owner's decision of 2026-11-25 on Issue #619](https://github.com/taspinar/physics-by-construction/issues/619) ("Owner's decision on the FIRAS data rights"); the owner has asked LAMBDA for a written confirmation beside it, which is pending.

**History of the decision.** The first session of part 1 (2026-11-25) downloaded and inspected the file, read LAMBDA's and NASA's records, and stopped at the gate: LAMBDA states no licence for the file, and the NASA statements are a general policy of the agency, not a statement about this file. Under the ADR 007 addendum a file with no stated licence is not committed without a recorded permission, so no sample was committed and no code written. The owner decided the same day to accept the NASA basis, following the precedent of the TESS card on MAST's general policy, and to ask LAMBDA for a written confirmation beside it. A refusal or a restriction in that answer reopens the gate: the sample is then removed and the track becomes link-only until the owner decides again.

## The file inspected

| | |
|---|---|
| Source | LAMBDA, `https://lambda.gsfc.nasa.gov/data/cobe/firas/monopole_spec/firas_monopole_spec_v1.txt`; product page `https://lambda.gsfc.nasa.gov/product/cobe/firas_monopole_spect.html` |
| File | `firas_monopole_spec_v1.txt`, 2,388 bytes, sha256 `df793c3dca09ebfa7dbc5aa0ec1951daa8884431bc30eff28a710d7516cf50fa` (computed; LAMBDA publishes no digest), HTTP 200 |
| Version | v1, "initial release, May 2005" (the header); the product page's file table gives 2003-03-01 |
| References in the header | "Reference1 = Table 4 of Fixsen et al. 1996 ApJ 473, 576."; "Reference2 = Fixsen & Mather 2002 ApJ 581, 817." |
| Accessed | 2026-11-25 |

The paper's Table 4 (arXiv:astro-ph/9605054, read on 2026-11-25) lists the same 43 frequencies with the same residual, uncertainty, and Galaxy values: columns 1, 3, 4, and 5 of the file equal it row for row (compared number by number in the session; the paper is not committed).

Reader: `pbc.data.reference.cobe_firas.read_spectrum` (NumPy). No conversion.

## Schema, units, cadence, masks, coverage

| Item | What the file documents | What this dossier established |
|---|---|---|
| Schema | 18 comment lines, then five columns: frequency, monopole, residual, uncertainty, Galaxy | 43 rows; residual, uncertainty, and Galaxy are integers |
| Units | cm^-1; MJy/sr for column 2; kJy/sr for columns 3 to 5 | 1 Jy = 1e-26 W m^-2 Hz^-1; frequency ν = c ν̃ |
| Grid | not stated in the file | 2.27 to 21.33 cm^-1, steps of 0.4538 cm^-1 (the paper's section 3.3) rounded to 0.01 |
| Reference temperature | "Column 2 = FIRAS monopole spectrum computed as the sum of a 2.725 K BB spectrum and the residual in column 3" | 2.725 K, recorded on the card as `reference_temperature`; the reader refuses a header that names another one |
| Masks | none | no missing value; every uncertainty positive (10 to 282 kJy/sr) |
| Coverage | the monopole over the sky; the Galaxy at the Galactic poles | one spectrum |

**The reference temperature and its source.** The 2.725 K of column 2 is not the paper's 2.728 K. LAMBDA's product page, read on 2026-11-25: "Subsequent analyses by Mather et al. (1999) and Fixsen et al. (2002) improved the FIRAS calibration accuracy and provided a best-estimate for the absolute CMB temperature of 2725 +/- 1 mK". The header names Fixsen & Mather (2002) as its second reference. So column 2 puts the 1996 residuals on the later calibration's blackbody.

**Column 2 rebuilt.** `rebuild_monopole` computes B_ν(2.725 K) plus column 3. With the CODATA 1986 constants (h = 6.6260755e-34 J s, k = 1.380658e-23 J/K) it matches column 2 within 0.8 kJy/sr at every frequency, about the rounding of column 2's three decimals (1 kJy/sr). With the exact SI 2019 constants the difference reaches 7.6 kJy/sr. The file does not say which constants were used; the closer match is the evidence for 1986. The analysis fits the residual column directly and uses the exact constants for the shapes, whose relative change between the two sets is about 1e-5 and negligible here.

## Artifact labels

| Artifact | Type |
|---|---|
| columns 3 to 5 (residual, uncertainty, Galaxy) | `calibrated-observation` |
| column 2 (monopole) | `calibrated-observation` |
| the fit and the blackbody of the reference figure | `modelled-reference`, not part of the record |

**What the residuals are.** They are not the difference between the measured spectrum and a fixed blackbody. The caption of the paper's Fig. 5 reads "FIRAS measured CMBR residuals, I0 − Bν(T0) − ∆T dB/dT − G0 g(ν)": the residuals left after the paper's own fit of a temperature shift and a Galactic term. Its section 6.1 says that for Table 4 the Galactic term is a ν² B_ν(T) model with a temperature of 9 K. The Galaxy column is labelled "Galaxy at Pole"; the paper does not say in Table 4 whether it is that fitted model or the template spectrum of section 4. So a refit of a temperature shift and a Galactic scale to column 3 returns values close to zero **by construction**, whatever the reference temperature. The reproduction track (Issue #619, part 1) reports it in these terms, and the reference figure says so.

## Reference figure

```
uv run python -m pbc.data.reference cobe-firas-monopole --out firas.png
```

The code is `src/pbc/data/reference/cobe_firas.py`. **Status label: processed** (a blackbody and a Galactic term fitted to a calibrated observation). The panels are:

- the monopole of column 2 with its 1-sigma bars (smaller than the dots), and the blackbody at T_ref + ΔT, dashed;
- the residual of column 3 with its 1-sigma bars, the fitted Galactic term G g(ν), dotted, and the residual minus the fit.

The fit is weighted least squares of column 3 against ΔT ∂B_ν/∂T + G g(ν), with weights 1/σ² from column 4 (the diagonal only):

| Quantity | Value |
|---|---|
| ΔT | 0.54 ± 8.06 µK (statistical) |
| G | −0.0018 ± 0.0251 |
| chi-square | 45.02 for 41 degrees of freedom |
| weighted rms, √(Σ(Δ/σ)² / Σ σ⁻²) | 18.89 kJy/sr |
| peak of B_ν(2.725 K) | 383.666 MJy/sr |
| weighted rms / peak | 49.25 ppm |

The paper (section 6.1, read on 2026-11-25) states for its own fit: "the weighted rms deviation in the frequency range 2 to 21 cm−1 is 50 ppm (parts per million) of the peak brightness", "The formal χ2 per degree of freedom = 46/40 = 1.15", and "The detector noise part of the temperature uncertainty is only 10 µK". The numbers above are close to these, as they must be for residuals that are the paper's own. What the agreement does and does not reproduce is the reproduction track's work, not this dossier's.

**Caption.** *The CMB monopole spectrum that COBE FIRAS measured, as LAMBDA distributes the residuals of Fixsen et al. (1996), against a blackbody: the deviations are tens of kJy/sr against a peak of 384 MJy/sr, about 50 parts per million. The fitted temperature returns the file's reference of 2.725 K, because the residuals are already those of the paper's fit.*

## Uncertainty and calibration

**Calibration** is the FIRAS team's: the sky spectra calibrated against the external blackbody calibrator (Fixsen et al. 1994b; 1996 section 3.4), the monopole separated by a fit of spatial templates (section 5), the residuals taken after a fit of ΔT and a Galactic term (section 6). The absolute temperature rests on the thermometry of the calibrator: "We conclude the absolute temperature of the CMBR is 2.728 ± 0.004 K (95% CL), entirely dominated by the systematic errors" (section 4). Neither the calibrator data nor the thermometry are in the file.

**The record documents an uncertainty per frequency**, column 4, one standard deviation. Checks of it:

- **Chi-square.** 45.0 for 41 degrees of freedom with the diagonal weights: the column describes the scatter of the residuals. The paper gives 46 for 40 with its full covariance.
- **The covariance between frequencies is not in the file.** The paper (section 3.3): "The covariance between frequencies is well approximated by Cνν′ = σν σν′ Q(|ν − ν′|)", with the 43 values of Q listed there. A fit with the diagonal alone gives statistical errors that differ from the paper's; the reproduction track names this as a difference of method, with its size.
- **Not bounded by this record.** The systematic terms of the paper's uncertainties: the thermometry of the calibrator (section 6.1: "the systematic thermometry uncertainty of 2 mK (1σ) should be included"), and the dependence on the Galactic model and the Galactic latitude cut (sections 6.1 and 6.3). They are named, not recomputed.

Asserted by `tests/unit/test_data_cobe_firas.py`: the sample parses with the card's checksum, size, header, units, grid, and reference temperature (`test_cobe_firas_sample_parses`, the card's sample test); a header with another reference temperature is refused; the Planck intensity has its Rayleigh–Jeans and Wien limits; its derivative in T matches a central difference; the peak brightness is the maximum over frequency; column 2 is rebuilt within 0.8 kJy/sr; the fit recovers an injected temperature shift and Galactic scale; and this dossier's numbers.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | NASA SPD-41 (2021), section IV, footnote 22: "Mission data are released into the public domain and non-SMD-funded activities have no requirements with respect to the usage of that data"; LAMBDA: "There is no cost involved in the use of LAMBDA" (https://lambda.gsfc.nasa.gov/contact/), both read 2026-11-25 |
| Redistribution of subsets | permitted | SPD-41 as above; NASA APD Policy-13 v1.8 (2023), section 3.2 f: "If there are no other restrictions on the data, the data shall be released with a Creative Commons Zero license"; LAMBDA states no licence for the file |
| Publication of figures and derivatives | permitted | SPD-41 section III, footnote 7: "Government works are by default in the U.S. public domain and should be used if no other license applies"; LAMBDA's acknowledgement statement asks for an acknowledgement in publications |
| Modification and attribution | permitted, with the acknowledgement | public domain under SPD-41; LAMBDA's acknowledgement statement (the card's `attribution`), which travels with the data on the figure, the page, and About (ADR 007 decision 7) |

**The basis, stated plainly.** No page of LAMBDA states a licence for this file. The four answers rest on NASA's policy for mission data, a general policy of the agency written after the file's release, and on LAMBDA's statement that its use is free of charge with an acknowledgement requested. The columns are those of a table of a journal paper (ApJ, the AAS); numbers of a table are data, and nothing of the paper's text or figures is committed beyond the short quoted statements of the register entry `fixsen-1996-firas-spectrum` in `site/references.yaml`. The owner accepted this basis as `equivalent-permission` on 2026-11-25, as the TESS card does for MAST's general policy, and asked LAMBDA for a written confirmation, which the card records as sent and pending (`rights.written_confirmation`).

## Size, runtime, payload

The file is 2,388 bytes (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 2 s with the interpreter start and about 120 MB peak memory; the PNG is about 150 kB at 150 dpi. The learner's download is the same file (`./scripts/fetch-data.sh cobe-firas-monopole`, checked against the card's sha256). CI reads the committed sample offline and never downloads.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected"; the card's `downloads` and `samples` |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration" |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels"; the figure draws the blackbody dashed and the Galactic term dotted, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/cobe_firas.py`, drawn from the committed sample; `tests/unit/test_data_cobe_firas.py` |
| 5. Rights, four answers with their source | "Rights"; the card's `rights`, with the owner's decision of 2026-11-25 and the pending written confirmation |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the diagonal 1-sigma checked by chi-square; the covariance and the systematic terms named from the paper |
| 8. This dossier with the decision | this file |

## Open items

- LAMBDA's written confirmation, requested by the owner on 2026-11-25: recorded on the card when it arrives; a refusal or a restriction reopens the gate.
- The reproduction itself (the spectrum fit, the distortions, the typed discrepancies) is the work of `pbc.products.research_workspace` in F155 part 1, not of this dossier.
