# Dataset research of 2026-11-08: spike candidates per measured-data lab

This page records the dataset research of 2026-11-08 for the measured-data labs: its summary, and the outcome of the third round, in which the small spike files were downloaded and inspected. The research itself is a long report kept outside the repository; this page keeps its tables and numbers, not its search logs.

**What this page is not.** It is no decision. Every "first spike" below is a recommendation of the research to run a feasibility spike (ADR 007, decision 3); **no `go` has been given** for any dataset on this page. The round-3 inspection is the inspection part of the gate only (an actual file, schema, units, cadence, masks, labels, and a physics sanity check with numbers). It is not the full gate: there are no cards, dossiers, or reference figures from source-controlled code for these datasets yet. The only decisions recorded here are the owner's, in "Decisions", and they are marked as such.

**Where the evidence is.** The downloaded files, the inspection scripts, and the diagnostic figures of round 3 are kept outside the repository, in the research session. No data file of this research is in the repository. Every file matched its stated size, and every published checksum matched (Zenodo md5, NIST sha256, SDSS sha1, git blob SHA-1).

The research had three rounds:

1. **Round 1:** five parallel research passes over record pages, repository API metadata, READMEs and licence pages; no data file was downloaded in this round.
2. **Round 2:** a comparison with a second researcher's report (also kept outside the repository), which changed the first spike of some labs.
3. **Round 3:** download and inspection of the small spike files, with the owner's approval.

Where the rounds differ, the later one holds: the round-3 table supersedes the statements of rounds 1 and 2 that no file was downloaded, and the round-2 choices supersede the round-1 summary table.

## Current state (round 3)

| Lab | Dataset and file | Verdict | Key result | Open item |
|---|---|---|---|---|
| M15 | Xu pendulum `len1_cond1_1.csv`, raw (329 kB) and cleaned (125 kB), commit `cbf8267` | ready with caveats | Amplitude ≈ 44°; after the elliptic-integral correction every window gives T₀ = 0.9942 s; 2π√(L/g) with L = 0.236 m gives 0.975 s, so the effective length is 4 % longer | The README does not define L; the licence (Apache-2.0) is now accepted by the owner (see "Decisions") |
| T7 | DWD Potsdam 03987 hourly soil temperature (2.77 MB zip) | ready with caveats | Diffusivity 1.00 / 1.12 × 10⁻⁶ m²/s from the annual wave (amplitude / phase) and 1.09 / 1.06 from the daily wave | 2 cm is not measured hourly after 1972, so five depths (5–100 cm); no sensor accuracy in the files |
| T8 | trackpy `bulk_water` frames 000–039 (7.60 MB, commit `09fb3074`; all git blob SHA-1s matched) | ready with caveats | Own NumPy/SciPy tracking (no trackpy): about 476 particles per frame, 483 tracks of at least 15 frames, drift of about 0.5 µm/s subtracted. **D = 0.402 ± 0.011 µm²/s** (bootstrap), matching the notebook's 0.40; Stokes–Einstein gives 0.429 at 20 °C and 0.491 at 25 °C | Systematics about ±0.02 (link step, lag range, mean or median); motion blur gives a negative MSD offset; exposure time and temperature are not documented. Proposed sample: the project's tracks CSV (`processed-measured`, about 0.3–0.5 MB) plus 3 grey frames, about 0.8 MB in total |
| EM8 | Bayreuth `rlc_circuit.json` (9 kB) | **ready for dossier** | R = 9.54 ± 0.02 Ω, L = 4.849 mH, C = 2.183 µF, resonance at 1547 ± 2 Hz | The record's "9.7 mΩ" is a typo for 9.7 Ω |
| W7 | Lycopodium XLSX profiles (89 and 43 kB) + morphometry CSV (20 kB) | ready with caveats | Spore diameter 29.9 ± 0.3 µm; ratio of first-minimum radii between the wavelengths 0.671 ± 0.035 against the expected 0.640 | x-axis unit and screen distance not stated; the Area column is µm², not pixels |
| FL8 | TU Delft `PIV.zip` (79 kB) + `PTV.zip` (10 kB) | ready with caveats | Log law κ = 0.400–0.410, B = 4.8–5.2; H = 1.33–1.37 against 2.59 for Blasius; Re_τ = 1351–4647 | The readme is wrong on the struct layout and on PTV units (mm) |
| FL8 | VKI `HWA_PROFILES_v2.zip` (121 kB) + `BL_PARAMETERS.zip` (6.8 kB, md5 matched) | ready with caveats | H ≈ 1.37–1.39. With u_τ from Coles–Fernholz Cf(Re_θ), within 2.4 % of a Clauser fit, the solid-wall profiles give κ = 0.40–0.41 and B = 4.9–5.0 | The files give no u_τ; the column `x/L` is x in metres; the provider fitted the wall position to canonical profiles, so the log-law agreement is partly imposed. "Unc. TI" columns are bounds |
| FL10 | NCEI `dart21416_20250727to20250803_meter.txt` (127 kB) + `dart21415_20250727to20250803_meter.txt` + NDBC `21416t2025.txt.gz` | ready with caveats | **Double conversion confirmed**: NCEI height / NDBC height = 0.67000 over about 1,700 matched timestamps. The NDBC mean equals the station depth, and 21415 gives the same factor. Corrected peaks: 21416 0.818 m at +32.1 min; 21415 0.352 m at +69.1 min (onset about +64 min against 65.8 min from √(gh)) | Divide NCEI heights by 0.670, or use NDBC raw heights and NCEI's method; disclose either on the page. NCEI files end 07-31 12:00 and have duplicated timestamps. Notifying NCEI is the owner's action |
| FL10 | USGS finite fault `complete_inversion.fsp` (49 kB) + `surface_deformation.disp` (123 kB) | ready with caveats | Three segments, 620 km × 150 km; max slip 39 m; uplift +8.1 m, subsidence −4.4 m | The `.disp` grid is coarse (40 × 40) |
| FL10 | ETOPO 2022 60″ crop 140E–180E, 35N–60N, stride 4 (2.46 MB text) | ready with caveats | 375 × 600 cells, −9573 to +3808 m; 450 kB as int16 `.npy` | Commit the converted `.npy`, not the raw text |
| Q7 | SDSS `spec-1949-53433-0480.fits` (173 kB) | ready with caveats | R_H = 1.0968086(67) × 10⁷ m⁻¹, 3 × 10⁻⁵ above the accepted value | z and R are degenerate; wavelength calibration limits accuracy to a few km/s |
| Q8 | Munich `Bell_2016-04-15.zip` (370 kB) | **ready for dossier** | S = 2.2210 ± 0.0329 from 10,201 events, equal to the published 2.221 ± 0.033; this is the published run | — |
| AST8 | TESS WASP-18 sector 29 `tess2020238165205-s0029-0000000100100827-0193-s_lc.fits` (1.9 MB) | **ready for dossier** | Depth 10,549 ± 21 ppm, T14 = 2.185 h, 21 transits; a four-column CSV extract is 570 kB | The error column is `PDCSAP_FLUX_ERR` |
| MAT5 | NIST SRM 660c CIF zip `srm_660c_cifs_20201029_081700.zip` (1.7 MB) | ready with caveats | a = 4.156498 Å from 20 files (SD 0.000012), 69 ppm below the certified 4.156826 Å | The CIFs carry no wavelength (Cu Kα1 taken from the certificate); simple profiles miss the instrument asymmetry |
| MAT6 | NIST Numisheet DP980 R01 CSV (132 kB) | **ready for dossier** | Tension, then compression, then tension again: a real load reversal with loop area 75.8 MJ/m³; E = 196 ± 5 GPa, 0.2 % yield ≈ 778 MPa | The BAM excerpt is no longer needed |

"Ready for dossier" and "ready with caveats" are the verdicts of the inspection, not decisions.

**Not done in round 3:**
- FL7: the 1.1 GB PIV file, by the owner's choice, and the Ost hot-wire files.
- AST9: SPARC, which needs the authors' permission first.
- EM7: no round-3 spike; its `go` of 2026-10-09 stands ([dossier](npl-onwafer-sparameters.md)).

## Final choices (round 2)

The choice of a first feasibility spike per lab after the comparison with the second report. These are recommendations to spike, not `go` decisions. Sizes in this round came from repository APIs or HTTP HEAD requests.

| Lab | First spike (file, size) | Runner-up | Changed? | Why |
|---|---|---|---|---|
| M15 | **Xu et al. damped pendulum**, GitHub `EnzeXu/Damped_Pendulum_Dataset` at commit `cbf8267`, `raw_data/len1_cond1_1.csv` (329,379 B) | Echiburu & Fernández, Zenodo 22760051 | **yes**, the other report's pick | The design is 5 lengths × 3 damping settings × 3 trials of 60 s from a PASCO encoder, with local g stated. That gives period against length and damping fits with a holdout. Apache-2.0 is stated by the README to govern the data. It counts as "equivalent recorded permission" only once the owner records it so (since decided, see "Decisions"). There is no DOI, so the spike pins the commit. |
| T7 | **DWD hourly soil temperature** (CC BY 4.0) | KIT experimental building, Zenodo 21157950 (CC BY 4.0) | no | KIT's heating ran throughout, so it supports only a lumped cooling fit, not a T6 heat-equation test. The other report's hot-wire record 23645337 was deleted. It reappeared as Zenodo 23644861 (CC BY 4.0, 44.7 MB, DOI field points to an unrelated 1997 paper), and its calibration is circular. |
| T8 | **trackpy `bulk_water`** | Spot-On, as a contrast case | no | Confirmed by the owner. |
| EM7 | **NPL S-parameters** (`go` stands) | — | no | — |
| EM8 | **Bayreuth `rlc_circuit.json`**, Zenodo 10794584 (9,119 B, CC BY 4.0) | Tours, Zenodo 23259842 | no | ExpEYES `lcr.csv` (25,265 B) has no data licence anywhere. The site licenses only its software (GPL) and hardware (CERN OHL), and the file is in no public repository. Usable only with written permission. |
| W7 | **Lycopodium spores**, Zenodo 15846643 | Fraunhofer microstructures, Zenodo 19436924 | no | Confirmed by the owner. |
| FL7 | **Shang & Tu `cylinder_vel.mat`** (1,082,404,799 B, CC BY 4.0) + Ost hot-wire TXT runs for St(Re) | Ree & Hwang, Mendeley jfjz6zfxwg (CC BY 4.0) | no | Ree & Hwang is one 542 MB zip: the real PIV cannot be fetched apart from the synthetic DNS folder, and the record gives no Re, D, U or cadence. The CaltechDATA set has 8.9–17.7 GB HDF5 files. |
| FL8 | **TU Delft boundary layer `PIV.zip`** (78,642 B) + **VKI `HWA_PROFILES_v2.zip`** (121,193 B) | Rostock, Zenodo 17720136 | no | A turbulent boundary layer against Blasius tests the limits of FL2 and FL3 directly. By Rostock's own README every `.npy` needs `allow_pickle=True`, which executes code on load. The other report's md5 for `F_stormy.zip` is that of `F_calm.zip`. |
| Q7 | **SDSS Balmer spectrum** | Hannover Rb absorption (CC BY-SA 3.0) | no | ShareAlike was outside ADR 007's CC0 / CC BY rule and would bind derived figures (the owner has since accepted CC BY-SA, see "Decisions"). The data omit the absolute frequency offset and the cavity's free spectral range. |
| Q8 | **Munich `Bell_2016-04-15.zip`** (369,992 B, CC BY 4.0) | NIST `Diagnostic Statistics/19-45.xlsx` (20,005 B) | runner-up changed | The NIST tables give 16 setting × outcome totals per run under NIST's reuse grant. But the test is CH-Eberhard, not CHSH, and NIST documents its no-click/no-click column as buggy. Munich's README does not say which archive gives the published result, so the spike had to establish it (round 3: it is the 04-15 archive). |
| AST8 | **TESS SPOC, WASP-18 sector 29 `lc.fits`** | Pi Mensae, sector 1 | no | Deep transit of about 1 % with many transits per sector. Pi Mensae c (about 0.03 %) is a second example. |
| AST9 | **SPARC `Rotmod`**, after written permission | PROBES, Zenodo 10456320 | no | — |
| MAT5 | **NIST SRM 660c (LaB6)** | Exler `ElMi60-0_bulk_xrd.txt` (38,813 B, CC BY 4.0) | runner-up changed | The certified lattice constant gives a real calibration. Exler is a mineral mixture with no standard and no stated uncertainty. Ahmed & Fatema is rejected (no instrument or sample description). |
| MAT6 | **NIST Numisheet DP980 R01** (131,777 B; record now v1.2.0) | + one cycle cropped from BAM P92 `Data_RF.lis` (6.8 MB, CC BY 4.0) for hysteresis | runner-up changed | The companion report lists "Cyclic" among its keywords; the spike checks for a load reversal. If there is none, BAM supplies the hysteresis loop as a second, separately carded excerpt (round 3: there is one, so BAM is not needed). CRAPPY (hardware test, no specimen data) and Wu (fitted curves) are rejected. |
| FL10 | **NCEI event file `dart21416_20250727to20250803_meter.txt`** (127,275 B: raw, NCEI tide fit, residual) + **ETOPO 2022 60″** crop (CC0, ERDDAP/OPeNDAP) + USGS finite fault | GEBCO_2026 via CEDA OPeNDAP | DART source **changed** | The event file is small enough to commit whole and keeps measurement, modelled tide and residual as three labelled series. No third-party-rights clause was found in ETOPO's metadata; its ocean layer is GEBCO_2022. |

Round 2 also re-checked four claims of the second report: the Xu repository licence Apache-2.0 (GitHub API) and the README's dataset-licence line; Zenodo 23644861, CC BY 4.0, 44,662,987 B; the DART file's Content-Length, 127,275 B; and the Ree & Hwang licence CC BY 4.0 (Mendeley API).

## Summary of round 1: the best option per lab

The round-1 table, with the licence as read and the main obstacle. Where it differs from the round-2 choices above (M15, and the DART source of FL10), round 2 holds. Its obstacles are those known before round 3; several were settled by the inspection (EM8's resistance, Q8's run, MAT6's reversal, FL10's DART cadence).

| Lab | Best option to spike | Licence (as read) | Main obstacle | Fallback |
|---|---|---|---|---|
| M15 (F83) | Echiburu & Fernández pendulum video tracks, 120 fps, doi 10.5281/zenodo.22760051 v1.0.0 (858 KB zip of CSV `t_s, x_m, y_m`, sha256 manifest) | CC BY 4.0 | Pendulum length is nominal with no uncertainty; the scale calibration is undocumented; amplitude is small, so there is no large-amplitude test for M6 | Mass-spring set, doi 10.5281/zenodo.23121777 (CC BY 4.0; pixels, smoothed by the app with an unstated filter) |
| T7 (F84) | DWD (German Weather Service) hourly soil temperature at 2–100 cm depth: diffusivity from amplitude decay and from phase lag | CC BY 4.0, stated in DWD's dataset description | No DOI and no published checksum; the archive is re-versioned yearly, so the lab must pin and checksum its own extract; sensor accuracy is only inside the zips (round 3: the files state none) | NOAA USCRN soil profiles (rights unconfirmed: CC0 on data.gov but marked "non-public") |
| T8 (F85) | trackpy-examples `bulk_water`: raw images of 1 µm spheres, 24 fps, 2.85 px/µm | BSD-3 or CC BY 3.0, at the user's choice | Images only, so tracking is project processing and must be disclosed; temperature not stated (needed for Stokes–Einstein); no DOI | Spot-On tracks (CC BY 4.0, live-cell contrast case); AnDi is synthetic, usable only as a `synthetic-test` |
| EM7 (F54) | `npl-onwafer-sparameters`: **`go` stands**, rechecked | CC BY 4.0 | The ARFTG paper (Zenodo 17425562) has **no uncertainty budget**: only TRL calibration, a drift check of at most 0.06 dB, and repeatability from 10 probe landings. The research proposes that the dossier's open item can be closed on that basis | — |
| EM8 (F86) | Bayreuth impedance collection, Zenodo 10794584 v1.0.0, file `rlc_circuit.json` (≈9 kB): measured parallel 2.2 µF / 5 mH, 100 Hz–10 kHz | CC BY 4.0 | The stated 9.7 mΩ series resistance is implausible and must be checked against the data; the JSON schema has not been seen | Tours broadband impedance of passive components, Zenodo 23259842 (CC BY 4.0, 5.8 MB zip, mostly MAT, no readme) |
| W7 (F52) | Lycopodium spores, Zenodo 15846643: diffraction photographs, intensity-profile XLSX, microscope diameters in CSV. Particle size from the Airy rings, checked against an independent measurement, at two wavelengths | CC BY 4.0 | Screen distance and image scale are not in the record (perhaps in the Eur. J. Phys. article, not read); XLSX reader | Fraunhofer microstructures, Zenodo 19436924 (rights settle as CC BY 4.0; RAR archives of 4–85 MB remain the obstacle) |
| FL7 (F53) | Shang & Tu cylinder-wake PIV, Zenodo 20765567 (one 1.1 GB MAT), **paired with** the Ost et al. hot-wire cylinder wakes, Mendeley doi 10.17632/xy8ggx9hn6.1 (plain text, 10 runs, Strouhal number against Re) | CC BY 4.0 / CC BY | MAT v5 or v7.3 is unknown (v7.3 needs h5py); a subset with masks needs a learner-side extraction script; cylinder diameter and flow speed are in the paper | — |
| FL8 (F108) | TU Delft turbulent boundary layer, 4TU (PIV and PTV profiles, 88 kB together), **paired with** the VKI grazing-flow hot-wire benchmark, Zenodo 15044105 v3 (121 kB profiles zip, uncertainty stated) | CC BY 4.0 | The 4TU hot-wire time series are in a 5.9 GB zip, so spectra and statistics need a learner download plus a small extract | Rostock (needs `allow_pickle`, which can execute code; no time-resolved data); Sheffield (undocumented; its discharge value looks wrong) |
| Q7 (F102) | One SDSS spectrum of a nearby star or Galactic emission-line object, showing the Balmer series, giving the Rydberg constant | SDSS: released data "considered in the public domain" | Confirm the sentence covers spectra; FITS only, unless a CSV export exists; it is a stellar or nebular spectrum, not a lamp | Ångström's wavelengths in Balmer's 1885 paper, Zenodo 1423807 (CC0), as a historical companion. **No openly licensed measured H, Hg or Ne lamp spectrum was found** |
| Q8 (F103) | Munich event-ready Bell test (Rosenfeld et al. 2017), Zenodo 22936124: two zips of 370 and 392 kB plus a README | CC BY 4.0 | Zip contents not seen; confirm the authors made the deposit; the page must state which loophole or selection remains | Weihs 1998 strict-locality Bell test, Zenodo 7185335 (CC BY 4.0, but two zips of 483 and 598 MB) |
| AST8 (F104) | TESS SPOC 2-minute light curve, e.g. WASP-18 sector 29 `lc.fits` (1,915,200 B per MAST metadata) | MAST: most data public domain | FITS only, so a one-time documented extract to CSV, or a FITS reader; per-mission terms must be cited | Kepler light curve (same terms) |
| AST9 (F105) | SPARC `Rotmod` files (110 kB, text, with disk, bulge and gas components) | **No licence stated** on the original site | Written permission from the authors is needed to commit them. A 2025 Zenodo CC BY copy by an unidentified account is not a reliable grant | PROBES, Zenodo 10456320 v1.0.0 (CC BY 4.0, authors' deposit; no gas component) |
| MAT5 (F106) | NIST SRM 660c (LaB6) diffraction data, doi 10.18434/mds2-2315 (1.7 MB CIF); certified a = 0.4156826 ± 0.000008 nm | NIST open data licence | A CIF parser is needed; MAT1 is a 1D-chain dispersion lesson, so the Bragg model needs a home | — |
| MAT6 (F107) | NIST Numisheet 2020 tension and compression CSVs, doi 10.18434/M32202 (110–175 kB each, repeats, two DIC strain gauges) | NIST open data licence | Whether any test reverses the strain path (hysteresis) | Copper loading–unloading, Zenodo 17486793 (CC BY 4.0, 5.5 MB XLSX, almost undocumented) |
| FL10 (F88) | Bathymetry: ETOPO 2022 v1, doi 10.25921/fd45-gt74 (crop 140E–180E, 35N–60N at 4′ is ≈0.45 MB as int16 .npy). DART: NDBC annual files 21416t2025, 21419t2025, 21415t2025, and 46402. Source: USGS finite fault us6000qw60 v5 | ETOPO CC0-1.0; NDBC and USGS US-government public domain | The DART files are total water column with tides included, so de-tiding is project processing; event-mode cadence and gaps are unseen; NCEI's QC'd 15 s archive does not yet cover July 2025 | GEBCO_2026 (public domain with attribution, but a copyright footer and an interactive download app only) |

Round 1 found no lab without a workable option, but three rest on an open question that a spike or a letter must settle before a `go`: AST9 (the rights of SPARC; without permission only PROBES, which has no gas component), Q7 (no lamp spectrum under an open licence; the SDSS route changes the lab from "calibrate a lamp" to "measure Balmer lines in a star"), and MAT6 hysteresis (settled in round 3: the NIST file reverses the load).

## Corrections to existing cards

Found by the research; **none is applied yet** (no card is changed by this page). The verdicts in brackets are the research's recommendations, not decisions.

- `data/registry/fraunhofer-microstructure-diffraction.yaml`:
  - The record is version 2.
  - The copyright line is a separate metadata field naming the licensors, so the licence is CC BY 4.0 with no conflict.
  - The smallest archive (4.1 MB, `08 Randomly_oriented_squares_(PDS_numerical_only)`) holds no photographs.
- `data/registry/electron-diffraction-crystals.yaml`: its "0.5 MB" file is the processing code, not data; the dataset is single-crystal zeolite data, unsuited to MAT5 (recommended: reject for MAT5).
- `data/registry/gaia-dr3-astrometry.yaml`: Gaia data are CC BY-NC 3.0 IGO, so NC: no committed sample.
- `data/registry/nist-experimental-ir-spectra.yaml`: the subject is molecular IR, not atomic lines, so it fails Q7's scope; it is Standard Reference Data marked "All rights reserved", not US-government public domain (recommended: reject).
- `data/registry/sandia-qubit-gate-set-tomography.yaml`: CC BY, but it needs gate-set-tomography inference, a poor fit for Q8's statistics lab.
- `data/registry/rostock-piv-fluorescence.yaml`: the NPY files need `allow_pickle`, which runs code on load (a security reason to defer); no time-resolved data.
- `data/registry/sheffield-piv-flume.yaml`: undocumented, and a reported discharge value looks inconsistent.
- `data/registry/npl-onwafer-sparameters.yaml`: the record is at revision 6 with unchanged data; the dossier's calibration-uncertainty item can be closed as "no budget published; drift and repeatability only".

## Rejected during the search

- IBM double pendulum: CDLA-Sharing licence; the DAX host is deprecated.
- Coupled-pendulum Tracker CSV, Zenodo 16237020: CC BY-NC.
- KIT phyphox handout and the yunkiyau optical-tweezers tracks (GitHub): no licence.
- Murata component S-parameter libraries: their terms restrict use.
- Delft loophole-free Bell test 2015 (4TU): its terms allow remixing only non-commercially.
- AM Bench IN625: the README and the licence field give different rights (mixed).
- IOC Sea Level Station Monitoring Facility: non-commercial and not QC'd.
- NOAA NCTR tsunami inversion: fitted to the same DARTs, so it cannot validate them.

Rejected in round 2, with the reasons in the table above: ExpEYES `lcr.csv` for EM8 (no data licence), Ree & Hwang for FL7 (one 542 MB zip, no Re, D, U or cadence), Exler and Ahmed & Fatema for MAT5, CRAPPY and Wu for MAT6.

## Decisions

### Taken by the owner (2026-11-08)

- **Readers.** MAT: add a reader; `scipy.io.loadmat` is already a dependency for MAT v5, and `h5py` is added only if the file proves to be MAT v7.3. XLSX, FITS and CIF: a one-time conversion to CSV or NumPy by a documented, checksum-pinned script outside the build, with no new build dependency for these formats.
- **Licences.** Apache-2.0 and CC BY-SA count as equivalent permission under ADR 007 (decision 4). A ShareAlike dataset is carded and shown as separately licensed material: its sample and the figures adapted from it carry CC BY-SA, and the rest of the site does not. ADR 007 itself still names only CC0 and CC BY, so this decision must be recorded in the repository, as an amendment to ADR 007 or a new ADR, before the first such sample is committed (Issue #417).
- **Downloads for the spikes.** The small files now; the 1.1 GB FL7 PIV later. The report states that the round-3 downloads were made with the owner's approval; they include the later `BL_PARAMETERS.zip` for FL8 and frames 000–039 of `bulk_water` for T8, which had first been held back for that approval.
- **First spikes of T8 and W7:** trackpy `bulk_water` and the Lycopodium spores (confirmed).

What follows from the licence decision, as the research reads it:

- **SPARC (AST9):** a link-only lab needs nothing. A committed sample needs the authors' written permission, because the site states no licence. Meanwhile PROBES (CC BY 4.0) is the fallback.
- **Hannover Rb (Q7):** no permission is needed under CC BY-SA 3.0. The science caveats remain (no absolute frequency offset, no free spectral range of the cavity), so SDSS stays the first spike and Hannover is a laboratory alternative.
- **Voronkin & Lushchin (W7):** the Zenodo API gives `license: cc-by-4.0` at record level for both 19436924 and 15846643, which covers the files; round 3 found an empty copyright field on 15846643. A letter would only be for the missing screen distance and image scale, which is science, not rights.

### Still open

- **A `go` for any dataset on this page.** None has been given; each needs the full gate of ADR 007 (card, labels, a reference figure from source-controlled code, rights, sizes, dossier).
- **Permission letter to the SPARC authors** (Lelli et al.), only if AST9 should commit a sample.
- **Notifying NCEI** of the ×0.670 double conversion in its DART event files (an owner action).
- Items of round 1 that the report does not record as decided:
  - Q7: accept a stellar Balmer spectrum (SDSS) in place of a laboratory lamp, or defer Q7 until a licensed lamp spectrum is found.
  - T7: whether DWD's yearly-versioned archive without a DOI is acceptable if the project pins and checksums its own extract.
  - FL7 and FL8 as pairs (a large learner download plus a small committed text set): accept the pairing pattern or not.
  - MAT5: where the Bragg model lives, since MAT1 is a chain-dispersion lesson.
- The FL7 download (1.1 GB PIV) and the Ost hot-wire files, deferred by the owner.

## Round-3 inspection per lab

What was checked, the number, and the open item, from the round-3 sections of the report. The scripts and figures named there are kept outside the repository.

### M15: Xu et al. damped pendulum

- **Checked:** `raw_data/len1_cond1_1.csv` (329,379 B) and `cleaned_data/len1_cond1_1.csv` (125,070 B) at commit `cbf82673641ecd65e902ad5c38a048387649a2a0` of `EnzeXu/Damped_Pendulum_Dataset`, and its README. No published checksum; the recomputed git blob SHA-1s equal the tree's. PASCO export, 6,896 rows at dt = 0.01 s; the cleaned file is raw rows 5.00–64.99 s re-zeroed, with no value changed. Angle quantised in 3–4 mrad steps.
- **Number:** a global damped sinusoid fits poorly (amplitude 0.775 rad, about 44°). In 10 s windows T falls from 1.0301 s to 1.0091 s; with the exact finite-amplitude correction every window gives **T₀ = 0.9942 ± 0.0003 s**, against 2π√(L/g) = 0.9751 s for L = 0.236 m: 2.0 % longer, L_eff = 0.2453 m. γ = 0.008–0.011 s⁻¹.
- **Open:** the README does not define the pendulum length and gives no uncertainty for L or the angle; the lab must treat L_eff as fitted or model the bob and rod. Proposed sample: 15 cleaned files (about 1.9 MB) plus 1 or 2 raw files, or all 45 cleaned files (5.62 MB).

### T7: DWD hourly soil temperature, Potsdam 03987

- **Checked:** `stundenwerte_EB_03987_19510101_20251231_hist.zip` (2,773,485 B, Last-Modified 2026-06-10, sha256 `6a968e6da83c783c4fa3a35196521021550bf56d1a64cde83cc9aeceb882329f`; DWD publishes no checksum), the station list, and the description PDF, whose page 4 states CC BY 4.0. Hourly from 2001-04; 2010–2025 100 % complete at 5, 10, 20 and 50 cm, about 99.9 % at 100 cm. PT100 sensors since 1978.
- **Number:** 2010–2024 annual wave: **κ = (1.00 ± 0.03) × 10⁻⁶ m²/s** from amplitude decay and **(1.12 ± 0.03) × 10⁻⁶** from phase lag; diurnal wave (June–August 2015–2024): **1.09 and 1.06 × 10⁻⁶ m²/s**.
- **Open:** 2 cm exists only for 1951–1972, never hourly, so five depths; no sensor accuracy in the files; UTC is not stated (the diurnal maximum is consistent with it); the archive is re-versioned yearly, so pin by sha256. Proposed sample: daily means 2010–2024 (about 0.2 MB) and one hourly year (about 0.5 MB).

### T8: trackpy-examples `bulk_water`

- **Checked:** the full directory (300 PNGs, 60,484,319 B) failed the 10 MB download limit, and the first 50 frames (9,617,783 B) the 8 MB limit; frames 000–039 (7,602,501 B) at commit `09fb3074a173585d48b5001b5b4b7e6479999598` were downloaded, all 40 git blob SHA-1s matching. 640 × 424 RGBA, colour-tinted rather than grey (converted to luminance), low contrast. Own pipeline with NumPy and SciPy: band-pass, threshold, centroid, mutual nearest-neighbour linking at 3 px, drift subtraction, ensemble MSD over lags 1–10.
- **Number:** 454–485 particles per frame, 483 tracks of at least 15 frames; **D = 0.402 ± 0.011 µm²/s** (bootstrap, statistical), intercept −0.033 µm². Other estimators give 0.372–0.416 (systematic about ±0.02); without drift subtraction 0.438. The notebook gives 0.40; Stokes–Einstein 0.429 (20 °C), 0.453 (22 °C), 0.491 (25 °C).
- **Open:** temperature, exposure time, objective and depth are not documented, so the comparison with Stokes–Einstein is limited to about ±10–15 %; the negative intercept is consistent with motion blur (lag-1 step correlation +0.16). Licence: BSD-3 or CC BY 3.0, at the user's option; for data the report reads CC BY 3.0 as the natural choice. Proposed sample: the tracks CSV (529 kB, about 300 kB trimmed) and three grey frames (73, 85, 86 kB), about 0.77 MB.

### EM8: Bayreuth `rlc_circuit.json`

- **Checked:** Zenodo 10794584 v1.0.0, CC BY 4.0; `rlc_circuit.json`, 9,119 B, md5 matching Zenodo. 81 log-spaced points from 99.97 Hz to 10,002 Hz; all impedance representations mutually consistent; no NaN, no per-point uncertainty.
- **Number:** fit of C ∥ (R + jωL): **R = 9.537 ± 0.021 Ω, L = 4.849 ± 0.007 mH, C = 2.1832 ± 0.0031 µF, f₀ = 1546.9 ± 1.6 Hz**, Q ≈ 4.9; relative residual rms 1.1 %, systematic. With R fixed at 9.7 mΩ the residual is 52 % and the predicted |Z|max about 96 kΩ against the measured 223 Ω.
- **Open:** the record's "9.7 mΩ" is a unit typo for 9.7 Ω, to be stated in the dossier as a documented discrepancy; errors are statistical only. Proposed sample: the whole file.

### W7: Lycopodium spores

- **Checked:** Zenodo 15846643, CC BY 4.0; `Intensity_profile_diffraction_lambda0.6328um.xlsx` (88,771 B), `Intensity_profile_diffraction_lambda0.405um.xlsx` (43,485 B) and `Lycopodium_Morphometry_x160.csv` (19,837 B), all md5s matching. Each XLSX is a single horizontal scanline, saturated at 255 in the centre; the CSV is cp1252, 150 particles.
- **Number:** for d > 15 µm, **n = 72, mean d = 29.91 µm, sem 0.34** (sd 2.87). First-minimum radii r₁ = 16.76 ± 0.23 (633 nm) and 11.25 ± 0.56 (405 nm) in x-units; **ratio 0.671 ± 0.035 against the wavelength ratio 0.640**. Implied screen distance 649 and 680 x-units, the same within about 5 %.
- **Open:** the unit of x and the screen distance are not on the record (the article probably has them; not read), so only the scale-free test works; the Area column is µm², not "pixels²" as the record says; the outer rings are ambiguous.

### FL8: TU Delft boundary layer and VKI benchmark

- **Checked (TU Delft, 4TU doi 10.4121/d0af5e8b-6bde-4c02-a165-c752b5ab435a.v1):** `PIV.zip` (78,642 B), `PTV.zip` (10,144 B), `readme.txt`, all md5s matching 4TU; MAT v5, read with `scipy.io.loadmat`, four cases U05–U20.
- **Number (TU Delft):** Re_τ = 1351–4647; log fit **κ = 0.400–0.410, B = 4.77–5.17**; H = 1.331–1.367 (file) against 2.591 for Blasius; −u′v′⁺ plateaus at 0.91–0.97.
- **Checked (VKI, Zenodo 15044105 v3, CC BY 4.0):** `HWA_PROFILES_v2.zip` (121,193 B) and `BL_PARAMETERS.zip` (6,755 B), md5s matching; all profiles normalised.
- **Number (VKI):** solid wall at x = 0, H = 1.326–1.356 from `BL_PARAMETERS.zip`; u_τ from Coles–Fernholz within −1.3 % to +2.4 % of a Clauser fit, and with it **κ = 0.399–0.408, B = 4.88–5.00**.
- **Open:** the TU Delft readme is wrong on the variable layout (top level, not a struct) and on PTV y (mm, not m), and its DOI is a placeholder; no uncertainty in its files. The VKI files give no u_τ, the column labelled `x/L [-]` is x in metres, the upstream "Velocity" is not their Ue, the "Unc. TI" columns are bounds, and the provider fitted the solid-wall y to canonical profiles, so the log-law agreement is partly imposed and is no independent measurement of κ.

### FL10: DART records, USGS finite fault, ETOPO 2022

- **Checked (DART):** NCEI `dart21416_20250727to20250803_meter.txt` (127,275 B) and `dart21415_20250727to20250803_meter.txt` (132,075 B), and NDBC `21416t2025.txt.gz` (173,424 B); no published checksums.
- **Number (DART):** the NCEI mean raw height divided by the station depth is 0.67008 (21416, 5788 m) and 0.67005 (21415, 4720 m); NCEI raw / NDBC height at 1,723 matched timestamps is **0.670003, std 1.1 × 10⁻⁶**: NDBC metres multiplied a second time by NDBC's 670 mm/psia factor. Corrected peaks: **21416 0.818 m at +32.1 min** (NCTR reports 0.85 m); **21415 0.352 m at +69.1 min**, onset about +64 min against 65.8 min from √(gh) over 849.4 km.
- **Open (DART):** divide the NCEI heights by 0.670 or use the NDBC heights with own de-tiding (which agreed with NCEI's tide to 1.8 cm rms); NCEI files end 2025-07-31 12:00, not 08-03; 13 (21416) and 18 (21415) duplicate timestamps with conflicting values; NDBC 1-minute records repeated at +15 s as padding; notifying NCEI is the owner's action.
- **Checked (USGS):** `complete_inversion.fsp` (49,217 B) and `surface_deformation.disp` (123,312 B) of product `us6000qw60_1`, version 5; no published checksum. The inversion uses no DART data.
- **Number (USGS):** Mw 8.835 (summed subfault moment matches the header); three segments, 620 km along strike, 150 km down-dip; maximum slip 39.3 m; uplift +8.11 m, subsidence −4.40 m. Uplift about 380–390 km from 21416 predicts an arrival of about 28–30 min, consistent with the DART onset.
- **Open (USGS):** the `.disp` grid is 40 × 40 (about 20 km), slightly irregular in lon, and misses the southern fault tip; hypocentre and origin time differ from ComCat; the product can be revised.
- **Checked (ETOPO):** an OPeNDAP ASCII crop of `ETOPO_2022_v1_60s_N90W180_bed.nc` from NCEI's THREDDS (2,463,031 B), CC0.
- **Number (ETOPO):** 375 × 600 cells, −9573.4 to +3808.4 m, 91.9 % ocean; 450,128 B as int16; path-integrated √(gh) time from the epicentre to 21416 is 40.1 min.
- **Open (ETOPO):** the stride decimates rather than averages; a generated response may not be byte-stable, so checksum the parsed array too; commit the converted array, not the 2.46 MB text.

### Q7: SDSS DR17 spectrum with Balmer lines

- **Checked:** `spec-1949-53433-0480.fits` (172,800 B), sha1 matching the SAS-published checksum; a starburst galaxy at z = 0.0149902 ± 0.0000060; vacuum, heliocentric wavelengths; read with a minimal NumPy FITS reader.
- **Number:** Balmer centres Hα 6663.034, Hβ 4935.476, Hγ 4406.626, Hδ 4164.240 Å; with the header z, **R_H = (1.0968086 ± 0.0000067) × 10⁷ m⁻¹**, +3.0 × 10⁻⁵ relative to 1.0967758 × 10⁷ m⁻¹; with the forbidden-line z (0.0150024 ± 0.0000038), 1.0968219 × 10⁷ m⁻¹.
- **Open:** R and (1+z) are exactly degenerate, so z must come from the forbidden lines; wavelength calibration and the underlying stellar absorption set a floor of a few km/s (χ²_r = 17 for the 1/n² law); the rights sentence sits on SDSS's image-use page and no spectra-specific licence page exists.

### Q8: Munich event-ready Bell test

- **Checked:** Zenodo 22936124, CC BY 4.0 per the API; `Bell_2016-04-15.zip` (369,992 B) and `README.txt`, md5s matching; 10,201 valid pair events over 3.70 days. `Bell_2016-06-14.zip` was not needed.
- **Number:** pooled **S = 2.2210 ± 0.0329**, equal to the published 2.221 ± 0.033 (Rosenfeld et al., PRL 119, 010402); per state 2.246 ± 0.046 (Psi−) and 2.198 ± 0.046 (Psi+).
- **Open:** the pooling rule for Psi+ and Psi− is not in the archive, so the dossier must cite the PRL Supplemental; the lab and pairs files use different delimiters; the Zenodo README states no licence (the API does).

### AST8: TESS WASP-18, sector 29

- **Checked:** `tess2020238165205-s0029-0000000100100827-0193-s_lc.fits` (1,915,200 B) from MAST; the FITS CHECKSUM keywords of all three HDUs verify. 18,864 rows at 120 s; 14,358 good rows over 23.9 days.
- **Number:** depth **10,549 ± 21 ppm** (Rp/R★ ≈ 0.103), **T14 = 2.185 ± 0.004 h**, ingress 18.1 ± 0.2 min, 21 transits; O−C against the archive ephemeris +4.8 min.
- **Open:** the flux error column is `PDCSAP_FLUX_ERR`, not `FLUX_ERR`; PDCSAP ends about 2.3 days before SAP. Proposed sample: a four-column CSV with all rows, 569,708 B.

### MAT5: NIST SRM 660c (LaB6)

- **Checked:** `srm_660c_cifs_20201029_081700.zip` (1,719,632 B), sha256 matching the record; 20 CIFs of about 433 kB each, read with a small stdlib CIF reader; the certificate PDF (certified a = 0.4156826 ± 0.000008 nm at 22.5 °C, k = 2).
- **Number:** Nelson–Riley extrapolation over 18 peaks: **a = 4.156498 Å over all 20 files, SD 0.000012 Å**; corrected from 20.85 °C to 22.5 °C about 4.15654 Å, **−69 ppm** from the certified 4.156826 Å, about 3.6 U.
- **Open:** the CIFs carry no wavelength (Cu Kα1 from the certificate); pseudo-Voigt fits miss the asymmetric instrument profile that NIST's fundamental-parameters approach models, so a simple-fit lab will not reach the certified value within U; "corrected" 2θ is not explained.

### MAT6: NIST Numisheet 2020 DP980 R01

- **Checked:** `C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv` (131,777 B, record v1.2.0), sha256 matching the record, and its 265 B attribute file. 1,607 rows over 0–1418 s.
- **Number:** tension to ε = 0.0575 (991 MPa), compression to ε ≈ −0.0004 (−1007 MPa), reload to fracture at ε = 0.177; loop area **75.8 MJ/m³**; **E ≈ 196 ± 5 GPa** (window-dependent); 0.2 % yield about 778 MPa; unloading modulus 98–134 GPa.
- **Open:** one cycle only, so no cyclic softening; sparse sampling during the elastic unloading; no uncertainty in the file. The BAM excerpt was not downloaded, because the reversal is present.
