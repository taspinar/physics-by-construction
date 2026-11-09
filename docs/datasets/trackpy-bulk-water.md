# Dossier: trackpy-examples `bulk_water`, 1 µm spheres diffusing in water

Card: `data/registry/trackpy-bulk-water.yaml`. Inspected 2026-11-08 for F85 (Issue #439), the measured-data lab T8; the choice of this dataset is in [the dataset research](spike-candidates-2026-11-08.md). No card existed before; this one is new.

**Decision: go.** Kind: raw video frames of colloidal spheres, with tracks computed from them by this project. Recorded under the owner's decision of 2026-11-08 on Issue #439 (work towards a `go` on the strength of the research, judged per dossier, every requirement of ADR 007 checked here; the tracking is the project's own processing and is disclosed as such; the temperature is not documented, say so). The checklist below names the evidence for each.

## The files inspected

| | |
|---|---|
| Source | GitHub, `soft-matter/trackpy-examples`, directory `sample_data/bulk_water`, https://github.com/soft-matter/trackpy-examples/tree/09fb3074a173585d48b5001b5b4b7e6479999598/sample_data/bulk_water; no DOI |
| Version | git commit `09fb3074a173585d48b5001b5b4b7e6479999598` (2025-07-10) |
| Files | `bulk_water_000.png` to `bulk_water_039.png`, 7,602,501 bytes together, and the `README` (119 bytes); the directory holds 300 frames (60,484,319 bytes) |
| Integrity | the git blob SHA-1 of all 41 files equals the one of GitHub's tree at the commit; the sha256 of each was computed here and is on the card (`downloads`) and pinned in the tracking script |
| Accessed | 2026-11-08 |

The `README` says, in full: "1-micron charge-stabilized latex spheres diffusing in water, recorded at 24 frames per second. 1 micron = 2.85 pixels." Nothing else about the recording is documented: not the microscope, the objective, the exposure time, the temperature, the depth of the focal plane, the tolerance of the sphere size, or how the video was digitised. trackpy's walkthrough notebook (`notebooks/walkthrough.ipynb` at the same commit) uses the same scale and frame rate, tracks the green channel of 300 frames, and reports a power law A tⁿ for the ensemble MSD with n = 1.080 and A = 1.602 (µm² at a lag of 1 s; with n ≠ 1 the unit of A is µm²/sⁿ, so A/4 is not a diffusion coefficient and is not compared with D here); its text compares with Stokes–Einstein "in room-temperature water". The research of 2026-11-08 inspected the same 40 frames and found the same sizes and blob hashes.

**Only the first 40 frames.** The whole directory (60 MB) exceeds the sample caps and the research's download limit; 40 frames (1.6 s) give 596 tracks of at least 15 frames, enough for an ensemble MSD over lags up to 10 frames with a statistical error of 2.4 % on D.

## The tracking: the project's processing

The frames are measurements; the positions and the tracks are not in the record. They are computed by this project with NumPy and SciPy (`src/pbc/data/tracking.py`), not with trackpy, following Crocker and Grier (J. Colloid Interface Sci. 179, 298, 1996), the method trackpy implements:

1. **Image.** The green channel of each RGBA frame (grey levels 0–255), as in trackpy's notebook. The spheres are dark on a bright field, so the image is negated.
2. **Band-pass.** A Gaussian blur of 1 px minus the mean over 11 × 11 px, negative values set to zero.
3. **Features.** The local maxima over a disk of radius 5 px (diameter 11 px, the notebook's feature size), at least 5 px from the border; each refined once to the intensity-weighted centroid over the disk, whose sum is the mass. Features of mass below 90 are dropped: the mass histogram of frame 000 has a noise peak below 30 and a particle peak near 180, with its minimum between 75 and 90.
4. **Linking.** Between consecutive frames, a feature continues a track when each of the two is the other's nearest neighbour within 3 px (the rms step is 0.52 px per axis, so 3 px is about six of them, and the mean spacing of the features is about 20 px). There is no memory: a track whose particle is not found in one frame ends, and a new one starts.

`tools/datasets/bulk_water_tracks.py` runs this once, outside the build, on the 40 frames whose sha256 it pins, and writes two files to `data/samples/trackpy-bulk-water/`; two runs give the same bytes, and `tools/datasets/README.md` says how to repeat it:

- `bulk_water_tracks.csv` (667,420 bytes, sha256 `e676e8bb6ab18a48c789dfc0444bf0a716ae13b3548d75d32f03c3b74d88d586`): every feature with its frame and track number, after four comment lines that name the commit, the processing and its parameters, and the units;
- `bulk_water_green_000-002.npy` (814,208 bytes, sha256 `2e0c8355f5426c1fc23a23da8bc6f3a215747a8eee65faf5f16cf7d320feb6b7`): the green channel of frames 000–002, grey levels unchanged, uint8, shape (3, 424, 640).

**Why an array and not the PNGs.** The repository commits no image file outside `site/assets/` (invariant I6, enforced by the committed-artifact check of the lesson checks, which rejects a `.png` anywhere else), so the frames are committed as data: the one channel the analysis reads, its values unchanged. The research had proposed three grey frames; this is that, without a luminance mix. The PNGs themselves remain the learner's download.

**The build repeats it.** The rows of frames 000–002 depend only on those frames, whose green channel is committed; `test_the_build_repeats_the_tracking_of_frames_000_to_002` detects and links them again and gets the CSV's lines byte for byte. The tracking is also tested on synthetic images and walks whose answer is known: dark Gaussian spheres located to 0.1 px, the linking rules, the drift and the MSD of a simulated walk.

Readers of the sample: `pbc.data.reference.trackpy_bulk_water.read_tracks` (NumPy) and `read_frames` (`numpy.load` without pickle). The downloaded PNGs are read by `read_frame` (`matplotlib.image.imread`, with Pillow, which matplotlib already locks), in the one-time tracking only; `test_read_frame_takes_the_green_channel_of_an_rgba_png` checks it on a PNG the test writes. No new dependency.

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Frames | PNG images | 640 × 424 px, RGBA, 8 bits per channel, alpha 255 everywhere; tinted, not grey: in frame 000 the red channel spans 114–165, the green 94–142, the blue 26–75 grey levels |
| Scale | 2.85 px per µm, no uncertainty | the field is 224.6 × 148.8 µm |
| Cadence | 24 frames per second | 40 frames, 1.625 s; every frame has 582 to 603 features (mean 592) |
| Tracks CSV | (the project's) | columns `frame,particle,x,y,mass`; 23,685 rows; frame 0–39, particle an integer numbered in order of appearance, x and y in px from the centre of the top-left pixel (y downwards), mass in grey levels of the band-passed image |
| Masks | none | no missing value; features at least 5 px from the border and of mass ≥ 90; 1,268 tracks, of which the analysis keeps the 596 of at least 15 frames (21,200 features) |
| Coverage | 300 frames in the directory | frames 000–039 tracked; the green channel of frames 000–002 committed |

**Compression.** The frames show the edges of 8 × 8 pixel blocks: the mean absolute difference between horizontally neighbouring pixels across a column boundary at a multiple of 8 is 1.4 to 1.7 times that elsewhere (1.12 against 0.53–0.83 grey levels in frame 000), and alternate columns differ too. The video was block-compressed (as JPEG or MPEG are) before the PNGs were written; the record does not say so, and its effect on sub-pixel positions is not known. `test_the_frames_show_the_edges_of_8_pixel_compression_blocks` asserts the pattern. The x positions show no preference for whole pixels (their fractional parts are uniform to within 5 % in tenths).

The parsing test `tests/unit/test_data_bulk_water.py::test_trackpy_bulk_water_sample_parses` asserts the field names, the shapes, the units, the cadence, the masks, and the counts above; `test_the_readme_is_the_providers_and_the_green_frames_parse` checks the git blob SHA-1 of the README and the type, shape, and range of the committed frames; `test_the_tool_pins_the_frames_of_the_card_and_refuses_others` checks that the script pins the card's 40 digests.

## Artifact labels

| Artifact | Type |
|---|---|
| `bulk_water_000.png` to `bulk_water_039.png` (not committed) | `raw-measured` |
| `bulk_water_green_000-002.npy` (committed) | `raw-measured` |
| `README` (committed) | `raw-measured` |
| `bulk_water_tracks.csv` (committed) | `processed-measured` |

The frames are the measurement; the committed array selects one channel of three and changes no value, so it keeps the type. The tracks are measurements processed by this project (located, selected by mass, linked). The drift subtraction, the selection of tracks by length, the MSD, and the fitted line are not artifacts of the record: `pbc.data.reference.trackpy_bulk_water` computes them, and the figure draws the fitted line and Stokes–Einstein dashed and dotted, apart from the measured points, with the residuals.

## Reference figure

```
uv run python -m pbc.data.reference trackpy-bulk-water --out bulk_water.png
```

The code is `src/pbc/data/reference/trackpy_bulk_water.py`. **Status label: processed** (located, linked, drift-corrected, and fitted). Panels: the top-left 200 × 200 px of frame 000 (green channel, grey levels) with the features located in it and the tracks of at least 15 frames that stay in that corner over the 40 frames, as measured, drift included; the drift-corrected ensemble MSD at lags of 1 to 10 frames with bootstrap error bars, the fitted line dashed, and Stokes–Einstein at 20 and 25 °C dotted (drawn with the fitted intercept, to compare slopes); the residuals of the fit; and the distribution of the one-frame steps in x and y after the drift, on a log scale, against the Gaussian of their measured variance.

The analysis, each step in the code:

1. **Selection.** Tracks of at least 15 frames: 596 of 1,268.
2. **Drift.** The mean displacement of all features linked from one frame to the next, summed over the frames, is the motion of the whole sample; it is subtracted from every position. Over the 40 frames it is (0.861, 0.262) µm, a mean velocity of (0.530, 0.161) µm/s, 0.55 µm/s in all. The four halves of the field (left, right, top, bottom) drift alike within two standard errors, so a uniform drift is subtracted; the per-frame mean step scatters 1.25 to 1.5 times more than the particles' steps alone would make it, so the drift is subtracted frame by frame, not as a constant velocity.
3. **MSD.** The ensemble mean squared displacement over every pair of frames of every track, at lags 1 to 10 frames (41.7 to 416.7 ms), in µm² with the README's scale.
4. **Fit.** The straight line MSD(τ) = 4Dτ + c by ordinary least squares on the ten points; D is the diffusion coefficient in two dimensions, c takes the localisation noise (+4σ²) and the motion blur (−4Dτₑ/3 for an exposure τₑ) together.
5. **Uncertainty.** A bootstrap over tracks (1,000 resamples, fixed seed): the tracks are drawn with replacement, the MSD and the line recomputed. The ten MSD points share their tracks and are correlated, so the least-squares error of the fit would be too small; the drift is not resampled.

**Caption.** *Twenty-one thousand positions of 1 µm spheres in water, tracked over 1.6 s by this project in a published video. After the drift of the whole sample (0.55 µm/s) is subtracted, the mean squared displacement grows in proportion to the lag time, as diffusion predicts, with D = 0.403 ± 0.010 µm²/s, 6 % below Stokes–Einstein for water at 20 °C and 18 % below it at 25 °C. The record does not give the temperature. The residuals are not random: the curve bends upwards over the ten lags, and the line meets the axis below zero.*

| Lag τ [ms] | MSD [µm²] (± bootstrap) | Residual, measured − fit [µm²] |
|---|---|---|
| 41.7 | 0.0439 ± 0.0007 | +0.0122 |
| 83.3 | 0.0995 ± 0.0015 | +0.0005 |
| 125.0 | 0.1628 ± 0.0025 | −0.0035 |
| 166.7 | 0.2270 ± 0.0036 | −0.0064 |
| 208.3 | 0.2942 ± 0.0050 | −0.0065 |
| 250.0 | 0.3638 ± 0.0067 | −0.0042 |
| 291.7 | 0.4335 ± 0.0085 | −0.0017 |
| 333.3 | 0.5021 ± 0.0104 | −0.0003 |
| 375.0 | 0.5734 ± 0.0125 | +0.0037 |
| 416.7 | 0.6430 ± 0.0147 | +0.0061 |

| Quantity | Value |
|---|---|
| D (slope / 4), lags 1–10 | 0.403 ± 0.010 µm²/s (bootstrap) |
| intercept c | −0.036 ± 0.003 µm² |
| Stokes–Einstein kT/(6πηr), r = 0.5 µm, 20 °C (η = 1.0016 mPa s) | 0.429 µm²/s |
| Stokes–Einstein, 25 °C (η = 0.8900 mPa s) | 0.491 µm²/s |
| viscosity that D implies at 20 °C | 1.064 mPa s |
| correlation of successive one-frame steps of a track (per axis) | +0.142 |
| excess kurtosis of the one-frame steps (0 for a Gaussian) | 3.23 |
| relative spread of the step variance of the 469 tracks of ≥ 30 steps | 0.33 (0.16 for identical Gaussian walkers) |

The viscosities are those of IAPWS R12-08 (2008) for water at 0.1 MPa; k is exact (SI 2019). D is not compared with the notebook's power law: its A belongs to a fit with n = 1.08 on 300 frames and has another unit. D lies 0.026 µm²/s (6 %) below Stokes–Einstein at 20 °C, about the size of the processing's sensitivity range of ±0.02 below, which is not a standard deviation, so no number of standard deviations is given; at 25 °C D is 18 % below, too far unless the spheres are larger than nominal. A temperature near 18 °C, or spheres 6 % larger than 1 µm, or a viscosity raised near a wall would each account for the 20 °C difference, and the record decides none of them.

## Uncertainty and calibration

**Calibration** is the README's two numbers, without uncertainty. The scale enters D squared: a 1 % error in 2.85 px/µm is a 2 % error in D. The frame rate enters D linearly. The **record documents no uncertainty**; the following are derived here.

- **Statistical.** ±0.010 µm²/s (2.4 %), the bootstrap over tracks.
- **Sensitivity to the processing.** `sensitivity` repeats the analysis with other choices; the linking and the mass cut are redone from the features in the CSV:

| Choice | D [µm²/s] |
|---|---|
| as in the figure (mass ≥ 90, link 3 px, tracks ≥ 15 frames, lags 1–10, drift subtracted) | 0.403 |
| link range 2 px | 0.382 |
| link range 4 px | 0.411 |
| mass ≥ 120 | 0.395 |
| tracks ≥ 10 frames | 0.403 |
| tracks ≥ 25 frames | 0.403 |
| lags 1–5 | 0.377 |
| lags 2–10 | 0.410 |
| no drift subtracted | 0.438 |

The processing choices move D between 0.377 and 0.411, about ±0.02 µm²/s: a **sensitivity range of the processing**, not an uncertainty interval and not a standard deviation; it has no statistical interpretation and is not combined with the bootstrap error. The track length does not matter; the link range and the lag range do. A link range of 2 px (four rms steps) cuts the largest steps and lowers D; 4 px admits more of them. Without the drift subtraction D would be 0.438, 9 % higher: the drift must be removed, and the lab has to say so. The research's own pipeline (luminance instead of the green channel, a percentile threshold) gave 0.402 ± 0.011, with other estimators between 0.372 and 0.416.

- **The short lags are not understood.** The MSD bends upwards: the increase per frame grows from 0.056 µm² (lag 1 to 2) to about 0.070 µm² (lags 5 to 10), so a local slope would give D from 0.33 to 0.43, and the line through all ten points meets the axis at c = −0.036 µm². Motion blur lowers the intercept by 4Dτₑ/3, at most 0.022 µm² for an exposure of a whole frame (1/24 s), and localisation noise raises it, so the intercept is more negative than blur alone can make it. Successive steps are positively correlated (+0.14), as blur makes them (+0.25 for an exposure of a whole frame), and as frame blending or temporal compression of the video would; the record documents neither the exposure nor the compression. D is therefore quoted from the slope over lags 1–10 with this caveat, and the lag-range rows of the table above bound what the choice changes.
- **The particles are not all alike.** The one-frame steps are not Gaussian: their excess kurtosis is 3.2 (2.1 after each track's steps are divided by that track's own rms), so the tails hold more large steps than a Gaussian, as the figure's log scale shows; and the step variances of the long tracks spread twice as much as identical walkers would make them (relative standard deviation 0.33 against 0.16). Spheres of different sizes or at different depths (nearer a wall, where diffusion is slower), aggregates, and occasional mislocations all contribute; they are not separated here. The ensemble D is the mean over this population.
- **Not bounded here.** The temperature, which Stokes–Einstein needs (about 2.7 % in D per kelvin near room temperature, mostly through the viscosity); the sphere size tolerance; the depth of the focal plane and the distance to the cover glass (hindered diffusion near a wall); the exposure time; and the effect of the compression on sub-pixel positions. A lab that reports these numbers must say that the tracking is this project's processing, that the drift is subtracted, that the uncertainty is a bootstrap over tracks with a processing range of about ±0.02 µm²/s beside it, that the short-lag MSD is not explained, and that the temperature is not documented, so the comparison with Stokes–Einstein is no better than about 15 %.

Asserted by `tests/unit/test_data_bulk_water.py`: the counts, D and its bootstrap error, the intercept, the first and last MSD points and the lag-1 residual, the drift velocity, the step correlation, the kurtosis, the spread of the track variances, Stokes–Einstein at 20 and 25 °C, the sensitivity table, and the block pattern.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the repository's `LICENSE` at the commit, https://github.com/soft-matter/trackpy-examples/blob/09fb3074a173585d48b5001b5b4b7e6479999598/LICENSE, read 2026-11-08: "The content is released under two licenses. You may at your option use one of them or both": a BSD 3-clause licence and Creative Commons BY 3.0. This project uses CC BY 3.0, https://creativecommons.org/licenses/by/3.0/legalcode, section 3 |
| Redistribution of subsets | permitted | CC BY 3.0 legal code sections 3(a) and 3(c): reproduce the Work, incorporate it in Collections, distribute it, with the URI of the licence (section 4(a)) |
| Publication of figures and derivatives | permitted | CC BY 3.0 legal code sections 3(b) and 3(d): create and distribute Adaptations that identify the changes made |
| Modification and attribution | permitted, with the credit | CC BY 3.0 legal code section 4(b): keep the copyright notice ("Copyright (c) 2013-2014 trackpy-examples contributors"), name the title and the URI, and credit the use of the Work in an Adaptation; the card's `attribution` does so and says what is unchanged and that the tracks are this project's processing; the figure prints it |

The card records the licence as `equivalent-permission` (ADR 007 decision 4): CC BY 3.0 is a CC BY licence, which decision 4 names, but not the identifier `CC-BY-4.0` that the dataset check lists. It grants all four rights with attribution and the URI of the licence. The BSD option would also permit it, with the copyright notice and its disclaimer reproduced; the project does not rely on it.

## Size, runtime, payload

Sample 1.48 MB: the tracks CSV 667 KB, the green channel of three frames 814 KB, the README (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 1.5 s with the interpreter start (the analysis with the bootstrap 0.1 s) and about 185 MB peak memory; the sensitivity analysis adds 0.2 s. The PNG is about 280 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the CSV and the frames are read at build time and not shipped. The learner's full download is the 40 frames and the README, 7.6 MB (`./scripts/fetch-data.sh trackpy-bulk-water`, each file checked against the card's sha256), and the tracking (about 3 s, 275 MB) repeats the CSV and the array byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected": the commit, sizes, git blob SHA-1s matched, sha256 of every file on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "The tracking"; "Uncertainty and calibration"; the parsing tests |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels": the frames `raw-measured`, the tracks `processed-measured`; the figure draws the fit and Stokes–Einstein apart, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/trackpy_bulk_water.py` with `src/pbc/data/tracking.py`, regenerated from the committed sample; the build repeats the tracking of the committed frames (their green channel); `tests/unit/test_data_plotting.py` checks the figure's status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the README's scale and frame rate; a bootstrap over tracks; the processing as a sensitivity range; the short-lag MSD, the non-Gaussian steps, and what the record does not document stated |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the T8 lab, starts only when the owner says so (Issue #439).
- The temperature, the exposure time, and the compression are not documented; asking the trackpy maintainers is possible but not required for the `go`, since the lab can state them as unknown.
- Frames 040–299 are not tracked; more frames would reduce the statistical error and reach longer lags, at the cost of the download.
- The runner-up, the Spot-On tracks (CC BY 4.0, live-cell, a contrast case), is not inspected.
