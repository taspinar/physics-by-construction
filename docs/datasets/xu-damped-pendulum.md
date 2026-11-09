# Dossier: Xu et al. damped pendulum

Card: `data/registry/xu-damped-pendulum.yaml`. Inspected 2026-11-09 for F83 (Issue #437), the measured-data lab M15; the choice of this record is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: time series of a rotary encoder (the angle of a damped pendulum). Recorded under the owner's decision of 2026-11-08 on Issue #437 ([the owner's comment](https://github.com/taspinar/physics-by-construction/issues/437#issuecomment-6729724204)): work towards a `go` for this dataset, judged on this dossier alone; the README does not define the length L, and this dossier states what it can say about it. The checklist at the end names the evidence for each requirement.

## The files inspected

| | |
|---|---|
| Source | GitHub repository `EnzeXu/Damped_Pendulum_Dataset` at commit `cbf82673641ecd65e902ad5c38a048387649a2a0` (2026-09-16, "Update citation in README.md"); no DOI and no release, so the commit is the version |
| Creators | E. Xu, T. Tran, H. Zhao, Y. Wang, M. Huai, H. Shao; the README asks to cite their paper "Identifying Invariant Physical Dynamics Across Multiple Environments", Transactions on Machine Learning Research (2026), https://openreview.net/forum?id=xvQYvYEGhj (not read for this dossier; nothing here depends on it) |
| Design (README) | 5 lengths × 3 damping settings (air only; air and a small paper baffle; air and a large paper baffle) × 3 trials; angle and angular velocity from a PASCO Wireless Rotary Motion Sensor PS-3220; recorded at William & Mary, 37°16′15.16″ N, 76°42′26.66″ W, "where the gravitational acceleration is about 9.799 m/s²" |
| Sample | the first air-only trial of each length, `raw_data/len1_cond1_1.csv` to `raw_data/len5_cond1_1.csv` (312,575 to 329,379 B); `cleaned_data/len1_cond1_1.csv` (125,070 B), the file the README plots; `pendulum_length.json` (413 B); `LICENSE` (11,357 B). 1,739,510 B, every file copied byte for byte; sha256 of each on the card |
| Checksums | none published; the Git blob SHA-1 of every downloaded file equals the one in the commit's tree (GitHub API), and the card records the sha256 computed here |
| Accessed | 2026-11-09 |
| Also inspected, not committed | the other 40 raw and 40 cleaned files of the record, with the same reader, for the spread of the trials and the effect of the damping setting (below) |

The README is not committed: the card and this dossier record what it says (the design, the lengths, g, the location, the sensor). The record's `process.py` is read, not run: it writes each cleaned file from its raw file (below).

Reader: `pbc.data.reference.xu_pendulum.load`, the standard library's `csv` and `json` modules and NumPy; no dependency is added.

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Schema | `column_names.py` names three raw columns (time, angle, angular velocity); the README says the cleaned file has time, angle, angular velocity, `is_peak` | raw files: UTF-8 with a byte-order mark, seven quoted columns, the PASCO export's names with "Run #1"; a few values in scientific notation (zero angles written as floating-point noise such as `-3.0531133E-16`) |
| Units | in the column names | time s, angle rad, angular velocity rad/s, angular acceleration rad/s²; the position, velocity, and acceleration columns are the angle times a pulley radius of about 23.9 mm, a setting of the software, not a quantity of the pendulum, and not used |
| Angle | "angle … from the sensor" | every angle is a whole number of encoder steps of 2π/2000 rad (0.18°), written with 3 decimals |
| Angular velocity | "angular velocity … from the sensor" | not a second measurement: at every row away from the ends it equals (θᵢ₊₂ + θᵢ₊₁ − θᵢ₋₁ − θᵢ₋₂)/(6 Δt) of the encoder counts, rounded to 3 decimals, the software's derivative of the angle |
| Cadence | cleaned data "dt=0.01s" | 0.01 s in every raw file, from t = 0, 65.83 to 68.95 s |
| Masks, missing values | none | no angle or position missing; the velocities are empty in the first and last row and the accelerations in the first two and last three rows, as numerical derivatives are; no flag |
| Coverage | "60 s" per trial | each raw file starts with the pendulum at rest at the encoder's zero, shows the lift by hand, and the release (the largest \|θ\|) 2.42 to 3.06 s after the start; then 63 to 66 s of free swinging |
| Cleaned file | `process.py`: rows 5 ≤ t < 65 s, time shifted by 5 s, values written with 2 and 3 decimals, `is_peak` from a peak search with a seeded random choice among equal extremes | the 6,000 raw rows of that window, the angle and the angular velocity unchanged (the eleven noise-written zero angles appear as 0.000); `is_peak` marks 115 extremes of \|θ\| |
| Length | `pendulum_length.json`: 0.236, 0.330, 0.426, 0.518, 0.607 m | not defined: neither the README nor the files say from where to where L is measured (see "What the data say about L") |

The parsing test `tests/unit/test_data_xu_pendulum.py::test_xu_pendulum_sample_parses` asserts the field names and the byte-order mark, the shapes, the cadence and coverage, the empty cells, the encoder step, the angular velocity as the derivative of the angle, the pulley radius of the position column, the cleaned file as a window of the raw one, the lengths, and the licence.

## Artifact labels

| Artifact | Type |
|---|---|
| `raw_data/len<k>_cond1_1.csv`, angle column | `raw-measured` (the encoder's counts in radians) |
| the same files, the other columns | computed by the PASCO software from the angle; labelled with the file as `raw-measured` on the card, described there as derived, and not used |
| `cleaned_data/len1_cond1_1.csv` | `processed-measured` (a window and a peak marker by the creators' script) |
| `pendulum_length.json` | `processed-measured` (the stated lengths, without definition or uncertainty) |
| the cycles, corrections, envelope, and fits of `pbc.data.reference.xu_pendulum` | `modelled-reference`, not part of the record |

The figure draws the measured angle as a solid line, the fitted envelope and the fitted line dashed, and the simple-pendulum references dotted, each labelled.

## Reference figure

```
uv run python -m pbc.data.reference xu-damped-pendulum --out pendulum.png
```

The code is `src/pbc/data/reference/xu_pendulum.py`. **Status label: processed** (periods, amplitudes, and corrections derived from the raw angle). Panels: the measured angle of the shortest pendulum with the release, the cleaned window, and the fitted exponential envelope; the period of each cycle against its amplitude, before and after the large-amplitude correction, with 2π√(L/g) of the stated L and the uncertainty of the cycles (bars and band, see "Uncertainty and calibration"); the small-amplitude period squared against the stated length, with the simple pendulum 4π²L/g and the fitted line; and the residual of the simple pendulum as the effective length minus the stated one.

**Method.** A cycle runs from one upward crossing of the centre of the swing (the median angle after the release) to the next, each crossing interpolated linearly between samples; its amplitude A is half the range of the angle in it. The first cycle after the release is not used, since the hand may still touch the pendulum. Each period T is corrected to the small-amplitude period T₀ = T π / (2 K(m)), m = sin²(A/2), K the complete elliptic integral of the first kind; the correction is exact for any rigid pendulum without damping, since the equation of motion I θ̈ = −m g d sin θ has the same form as for a point mass. With these runs' Q of 375 to 543, damping changes the period by less than 10⁻⁵ of itself. A test checks the correction against its series 1 + A²/16 + 11A⁴/3072 + ….

**Caption.** *A pendulum released at 44° and swinging in air for a minute. Each cycle's period falls with its amplitude, from 1.034 s to 1.007 s; corrected for amplitude, the cycles give 0.9952 s with a scatter of 0.7 ms, 2.1 % above 2π√(L/g) = 0.9751 s of the stated length 0.236 m and the stated g = 9.799 m/s². Over the five lengths, a straight line is fitted to the small-amplitude period squared against the stated length; its slope would mean g = 9.95 ± 0.03 m/s² and its intercept adds 13 mm to every length, but the points deviate from the line by up to 5.75 × 10⁻³ s², several times more than the uncertainty of the periods (below 7 × 10⁻⁴ s²) explains, so the five lengths do not follow one straight line within that uncertainty; read with the stated g, each pendulum behaves as a simple pendulum 3.9 to 9.8 mm longer than stated.*

| Run | Stated L (m) | Cycles used | Amplitude (°) | T₀ (s) | Standard error (ms) | 2π√(L/g) (s) | L_eff = gT₀²/4π² (m) | L_eff − L (mm) |
|---|---|---|---|---|---|---|---|---|
| len1_cond1_1 | 0.236 | 62 | 43.7 → 25.6 | 0.99521 | 0.09 | 0.9751 | 0.2458 | 9.8 |
| len2_cond1_1 | 0.330 | 51 | 16.5 → 11.3 | 1.16662 | 0.11 | 1.1530 | 0.3378 | 7.8 |
| len3_cond1_1 | 0.426 | 46 | 24.1 → 18.4 | 1.31777 | 0.13 | 1.3101 | 0.4310 | 5.0 |
| len4_cond1_1 | 0.518 | 42 | 38.8 → 27.1 | 1.45284 | 0.18 | 1.4446 | 0.5239 | 5.9 |
| len5_cond1_1 | 0.607 | 39 | 22.9 → 17.9 | 1.56879 | 0.22 | 1.5638 | 0.6109 | 3.9 |

Line through the five points, T₀² = a L + b with errors from the scatter: a = 3.969 ± 0.014 s²/m, so 4π²/a = 9.947 ± 0.035 m/s², 4.3 standard errors above the stated 9.799; b = 0.0516 ± 0.0061 s², b/a = 13.0 mm. The points scatter about the line by up to 5.75 × 10⁻³ s² in T₀², far more than their standard errors allow (2T₀σ(T₀) below 7 × 10⁻⁴ s²): the five lengths do not lie on one line within the precision of the periods. Asserted by `test_the_periods_and_the_effective_lengths_are_the_dossiers` and `test_the_line_through_the_five_lengths`.

**The amplitude correction.** In the shortest run the uncorrected period rises by 1.44 ms per degree of amplitude; after the correction 0.09 ms per degree is left. Over the five runs the correction reduces the slope from 0.52 to 1.94 ms per degree to between −0.17 and +0.41 ms per degree (−0.10 and −0.17 in two runs, so it overshoots there). The remainder has no common sign, so a scale error of the angle, which would leave a slope of one sign, does not explain it; a drift of the period over the minute, or the hand's last touch, may. It is reported as a systematic effect of a few tenths of a millisecond, not removed. Asserted by `test_the_correction_removes_most_of_the_amplitude_dependence`.

**The research's number.** The research of 2026-11-08 reported T₀ = 0.9942 ± 0.0003 s for the shortest run, from damped-sinusoid fits in 10 s windows; this code gives 0.9952 s from the cycles. The difference, 1 ms or 0.1 %, is one of method (how the amplitude of a decaying, anharmonic cycle enters the correction); the research's scripts are not in the repository, so it is not resolved here. Both give a period 2 % above 2π√(L/g) and an effective length 4 % above the stated 0.236 m; the conclusion below does not depend on which.

## What the data say about L

The record does not say whether L runs from the axis to the centre of the bob, to its bottom, or to a mark on a rod, and gives no uncertainty for it. The data cannot answer that question, but they bound what a lab may assume:

- **The stated L is not the length of an equivalent simple pendulum.** With the stated g, each period defines an effective length L_eff = gT₀²/4π², and every L_eff exceeds its L, by 9.8 mm at 0.236 m falling to 3.9 mm at 0.607 m (4.2 % to 0.6 %). A lab that computes g from these L and periods gets 9.95 m/s², not the local 9.80, and must not present that as a measurement of g.
- **A fixed offset does not explain it either.** If L were measured to a point a fixed distance from the centre of oscillation, L_eff − L would be the same at every length; it falls from 9.8 to 3.9 mm, and the five points do not lie on one line within the precision of the periods.
- **A physical pendulum would.** For a rigid body, L_eff = I/(m d), the moment of inertia about the axis over the mass times the distance to the centre of mass. A bob of finite size, a rod with mass, and the rotating parts of the sensor each add to I by amounts that do not scale with L, and make L_eff − L depend on L in this way. Which of them, and by how much, the record does not say (no masses, no dimensions of the bob or rod).
- **What a lab can do.** Either take g = 9.799 m/s² as known and fit L_eff of each length, or take the stated lengths and fit g with an offset, stating that the offset absorbs an unknown geometry; it cannot determine both g and the geometry from these files. In either case the period is the measured quantity, and the length is a model input whose uncertainty is set by the residuals above, a few millimetres, not by the three decimals of the JSON file.

## Uncertainty and calibration

The record gives **no uncertainty** and **no calibration** beyond the sensor's conversion of counts to radians.

- **Angle.** The encoder step is 2π/2000 rad = 3.1 mrad (0.18°), rounded to 1 mrad in the file. The quantisation moves an interpolated crossing time by about 0.2 ms in the fastest run (len1, 44°) to 0.8 ms in the slowest (len2, 16°), comparable to the scatter of one cycle below.
- **Period of one run.** One cycle's T₀ scatters by 0.7 to 1.4 ms (standard deviation); the mean over 39 to 62 cycles has a standard error of 0.09 to 0.22 ms.
- **On the figure.** The record gives no uncertainty per cycle. The period panel draws, on each cycle, bars of one standard deviation from the encoder step alone (the step over √12 divided by the angular speed at each of the two crossings, added in quadrature: 0.27 to 0.46 ms for len1, up to 1.4 ms for len2), a lower bound, here smaller than the markers; and, as a band, the run's T₀ ± one standard deviation of one cycle (0.7 ms for len1), the run-level scatter. A note on the panel keeps the two apart and says that the spread of the trials (below) exceeds the standard error of the run's T₀.
- **Between trials.** The other two air-only trials of each length (outside the sample, same code) give T₀ within 0.35 ms (shortest length) to 1.5 ms (longest) of each other; across all settings, the three trials of one length and setting differ by 0.12 to 2.3 ms. This is larger than the standard error of a run, so the spread of the trials is the honest uncertainty of a period, and the standard error of a single run understates it.
- **The damping setting changes the period.** With a paper baffle the mean small-amplitude period of the three trials is longer than in air by up to 3.3 ms (0.25 %, the middle length with the large baffle; 0.8 to 3.3 ms with the large baffle at every length), far more than damping of these strengths shifts it (below 10⁻⁴ of the period at Q ≈ 100); the baffle adds mass and moment of inertia, and moves air with it. A lab that compares the damping settings must not treat the period as the same pendulum's. (From the files outside the sample.)
- **Damping law.** The amplitude of the shortest run decays with τ = 118.6 ± 0.6 s (exponential envelope, Q = 375). Over 60 s of air damping the law is not determined: the RMS residual of an exponential (viscous), a linear (dry friction), and a 1/(1 + kA₁t) law (drag quadratic in the speed) are 3.5, 8.9, and 4.0 mrad for the shortest run, and 2.2 to 9.2 mrad for the other four, with the linear law best in two runs, the exponential in one, and the quadratic in one. The baffle runs, whose amplitude decays 2 to 9 times faster (τ = 28 to 64 s against 110 to 271 s in air, files outside the sample), are where M12's damping models can be told apart. Asserted by `test_the_damping_of_the_shortest_pendulum` and `test_the_damping_laws_of_the_other_lengths`.
- **g.** The README gives 9.799 m/s² as "about"; the international normal-gravity formula at 37.27° N gives 9.7993 m/s² at sea level, consistent with it. It is used as given.
- **Calibration.** None is applied. The zero of the angle is the encoder's position when the recording started, with the pendulum at rest; the centre of the swing lies within 0.01 rad of it, and the analysis measures every cycle from the centre, not from zero.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | `LICENSE` at the commit, Apache License 2.0 (GitHub spdx Apache-2.0), named by the README's section License; https://www.apache.org/licenses/LICENSE-2.0 section 2 |
| Redistribution of subsets | permitted | the same, sections 2 and 4: redistribution in any medium with a copy of the licence, modified files marked, notices kept; no NOTICE file at the commit. The sample carries `LICENSE` and modifies no file |
| Publication of figures and derivatives | permitted | the same, section 2: prepare, publicly display, and distribute Derivative Works |
| Modification and attribution | permitted with attribution | the same, section 4(b) and 4(c); the README asks to cite the TMLR paper, which the card's attribution does; the figure prints the record, the commit, the licence, and what its code computed |

Apache-2.0 is an equivalent recorded permission under the ADR 007 addendum of 2026-11-08 (Issue #417). This is the first committed sample under it: the card records the licence as `equivalent-permission`, the existing value of `src/pbc/data/card.py`, and names Apache-2.0 in each rights answer, so the dataset check needs no change. Apache-2.0 is not a ShareAlike licence: the site's own licences apply to the figures, with the attribution.

## Size, runtime, payload

Sample 1.74 MB in eight files, the largest 329 KB (caps: 2 MB per file, 8 MB per dataset). The full record is 45 raw files (14.5 MB), 45 cleaned files (5.6 MB), and plots; `./scripts/fetch-data.sh xu-damped-pendulum` downloads the eight files of the sample by the card's URLs and checksums (the cleaned file as `cleaned_len1_cond1_1.csv`). Figure: about 5 s including the interpreter start, about 160 MB peak memory; PNG about 340 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays far inside the 30 s warning, the 60 s limit, and the 3 MB payload: the data are read at build time and only the figure reaches the browser. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected"; the commit as the version; the Git blob SHA-1 of each file against the tree, the sha256 on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from models | "Artifact labels"; the fits and references are dashed or dotted and labelled |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/xu_pendulum.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the encoder step, the scatter of the cycles, the spread of the trials, the remaining amplitude dependence, the damping setting; no calibration beyond the sensor's |
| 8. This dossier with the decision | this file, including what the data say about the undefined L |

## Open items

- Phase 2, the M15 lab, starts only when the owner says so (Issue #437). It decides which further files of the record to commit; the research proposed the 15 first trials or all 45 cleaned files (5.6 MB, within the cap), which a holdout of trials and the damping settings would need.
- The cause of the effective length (bob, rod, sensor) is not in the record; a question to the creators (the README gives a contact) could settle it.
- The runner-up, Echiburu and Fernández's pendulum video tracks (Zenodo 22760051, CC BY 4.0), is not inspected.
