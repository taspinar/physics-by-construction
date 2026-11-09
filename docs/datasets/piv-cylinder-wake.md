# Dossier: Shang and Tu cylinder-wake PIV, Re = 413

Card: `data/registry/piv-cylinder-wake.yaml`. Inspected 2026-11-09 for F53 (Issue #454), the measured-data lab FL7; the choice of this dataset is in [the dataset research](spike-candidates-2026-11-08.md). The card existed as `survey-only` since the survey of 2026-10-09; its gate (a MAT reader, a compact subset that keeps the masks, the cap, the creators' notes on the mask and the cadence) is passed here. Its companion for the Strouhal number against the Reynolds number is the hot-wire record [ost-hotwire-cylinder-wakes](ost-hotwire-cylinder-wakes.md).

**Decision: go.** Kind: processed PIV velocity fields (not raw images), with a crop, a time mean, and probe series extracted by this project. Recorded under the owner's approval of 2026-11-09 on Issue #454 (the dataset and its one download approved; work towards a `go`, judged per dossier, every requirement of ADR 007 checked here). The checklist below names the evidence for each.

## The file inspected

| | |
|---|---|
| Source | Zenodo record 20765567, https://zenodo.org/records/20765567, doi 10.5281/zenodo.20765567, "Particle image velocimetry (PIV) data of flow past a cylinder", Jessica Shang and Jonathan Tu, published 2026-06-19 |
| File | `cylinder_vel.mat`, 1,082,404,799 bytes, the record's only file |
| Integrity | MD5 `4cc876439c48f7970afa477ea17d217a`, equal to Zenodo's; SHA-256 `328cd8d17cd2eb42faef6e4766bc8e515e0eac06868152972adab9bdf91926e7` computed here |
| Format | MATLAB **MAT 5.0** (header "MATLAB 5.0 MAT-file, Platform: MACI64, Created on: Fri Jun 19 14:16:37 2026"), not v7.3: `scipy.io.loadmat` reads it, so no `h5py` is needed (ADR 007 addendum) |
| Accessed | 2026-11-09, downloaded once into a new empty directory outside the repository (the one download the Issue approves); nothing in it executed |

The record's description says, in substance: a 2D velocity field over time of flow past a cylinder from planar PIV, in a recirculating water channel at Re = 413; the cylinder is finite and the plane is at mid-span; the fields were computed with LaVision DaVis 8.1.2; the frequency of the dataset is 20 Hz; four variables u and v (m/s), x and y (m); "some of the values in (u,v) are exactly zeros (0s); these regions were masked out prior to PIV processing as they correspond to regions of the flow that are not illuminated by the laser: the cylinder cross-section, and the shadows cast by the cylinder." It refers to Tu et al. (Exp. Fluids 55, 1805, 2014, doi 10.1007/s00348-014-1805-6) for the details, and lists Phys. Rev. Fluids 5, 054401 as related.

**The experiment, from the paper.** The accepted text of Tu, Rowley, Kutz and Shang (arXiv 1401.7047, Section 4.1, read 2026-11-09; the published article was not read) gives what the record does not: a recirculating free-surface water channel; an anodised aluminium cylinder of **D = 9.5 mm** and L = 260 mm, suspended vertically with a gap of 1–2 mm to the floor; **U∞ = 4.35 cm/s**, Re = 413; a Nd:YAG laser sheet (Litron Nano L 50-50) imaged from below by a LaVision Imager sCMOS; 8000 image pairs 8000 µs apart at 20 Hz; hollow ceramic spheres of 10 µm; DaVis 8.1.2 cross-correlation with one pass of 128 × 128, one of 64 × 64 and two of 32 × 32 pixels, 50 % overlap, giving 135 × 80 vectors and a cylinder of about 128 pixels. It reports "a dominant spectral peak at f = 0.889 Hz, corresponding to the wake shedding frequency", with harmonics near 2f and 3f. It gives no PIV uncertainty and no water temperature.

## The extraction: what the sample is

The file holds 1.38 GB of doubles once loaded, more than 800 times the sample this dataset commits, so `tools/datasets/cylinder_wake_extract.py` extracts a small part once, outside the build, from the file it pins by MD5 and SHA-256 (any other file is refused), with `pbc.data.reference.cylinder_wake.read_mat` and `extract`. It runs in about 10 s and 1.8 GB of memory; two runs give the same bytes; `tools/datasets/README.md` says how to repeat it. It writes six files to `data/samples/piv-cylinder-wake/`:

| File | Content | Bytes |
|---|---|---|
| `wake_u.npy`, `wake_v.npy` | u and v of frames 0–59 (3 s, 2.7 shedding periods) on the crop of 61 × 46 record points, x from −58.0 to +5.0 mm and y from −51.4 to −4.1 mm (the cylinder, its recirculation, and the wake to 5 D behind it); float32, index order [frame, y, x] with x and y increasing | 673,568 each |
| `wake_mask.npy` | True where u and v are both exactly 0 in the record, the same shape, bool | 168,488 |
| `wake_mean.npy` | the mean of u and of v over the frames of all 8000 in which the point is not masked, float32, [u or v, y, x]; NaN at the 260 points masked in every frame | 22,576 |
| `probes.npy` | u and v at the record's grid points (102, 38) and (75, 38) for all 8000 frames (400 s), float32, [frame, probe, u or v]: x = −24.4 and +4.0 mm on the wake axis y = −27.2 mm, about 2 D and 5 D behind the centre of the cylinder's shadow | 128,128 |
| `wake_meta.json` | the x and y of the crop (the record's values, in m), the crop and probe indices in the record, the frames, the cadence, the units, the layout, the mask's definition, and the source file with its size and checksums | 3,681 |

1,669,009 bytes in all. **What changed and what did not.** The crop is reordered so that x increases (the record's x decreases along its first index) and transposed to [frame, y, x]; the doubles are stored as float32, which rounds them by at most 6 × 10⁻⁸ of their value (9 nm/s), far below any PIV precision; nothing is interpolated, filtered, or filled. The mask is made explicit: it is the record's zeros, which stay zero in u and v. The mean and the probe series are new arrays computed from the record, not values of it. `test_extract_reorders_the_crop_and_keeps_every_value` checks the reordering, the mask, the mean, and the probes on a synthetic record whose values encode their indices, and `test_the_probes_are_the_crop_at_their_grid_points` checks on the sample that the probes' first 60 frames are the cropped fields at their points. `read_mat` is tested on a small MAT file the test writes with `scipy.io.savemat`.

**Why `.npy`.** The sample is arrays of 60 × 46 × 61 values; NumPy's format is exact for float32, holds no Python object (read with `allow_pickle=False`), and is written byte for byte the same on each run. A CSV of the same values would be about four times larger.

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Variables | u, v (m/s), x, y (m) | u, v doubles of 135 × 80 × 8000 [i, j, frame]; x, y doubles of 135 × 80 |
| Grid | not described | uniform, 1.05035 mm in both directions; x decreases along i from +82.8 to −58.0 mm, y increases along j from −67.1 to +15.9 mm (14.8 × 8.7 D) |
| Flow direction | not stated | u > 0 everywhere outside the recirculation, the wake lies at larger x: the flow is along +x |
| Cadence | 20 Hz | 8000 frames, 400 s; no time vector, frame k is at k/20 s; the paper's 8000 µs between the images of a pair |
| Masks | exact zeros: the cylinder and its shadows | 3.4 % of the values are zero in both components: 365 points in every frame (a column below the cylinder, x from −46.4 to −40.1 mm, to the bottom edge, and an arm along y ≈ −23 mm upstream to the left edge: two shadows), 179 others in some frames, at the edge of the shadows and 47 isolated points with 83 zero frames between them; 365 to 374 masked points per frame. One component alone is zero in 2.9 × 10⁻⁶ of the values, which is not a mask and stays data. No NaN. |
| Position of the cylinder | not given | the mask's column below the cylinder is centred at x = −43.3 mm; the wake axis, where v fluctuates most and the mean u is lowest from 2 D to 13 D downstream, is at y = −27.2 mm; the mask's upstream arm is centred near y = −23 mm, so the cylinder's centre in y is uncertain by about 4 mm (0.4 D) |
| Free stream | 4.35 cm/s (paper) | mean u in the crop's top row (y = −4.1 mm, 2.2 D from the axis) 4.52 cm/s; 4.4 to 4.6 cm/s in the field's top rows |
| Coverage | 8000 frames | the sample: frames 0–59 of the crop; the mean over all frames; the probes over all frames |

The parsing test `tests/unit/test_data_cylinder_wake.py::test_piv_cylinder_wake_sample_parses` asserts the files, the dtypes and shapes, the grid and its spacing, the cadence, the units and the layout, that the mask is exactly where u and v are both zero (260 to 263 points of 2,806 per frame, 260 in every frame), that the mean is NaN only there, that the probes are on the wake axis and never masked, and the size of the velocities; `test_the_card_pins_the_record_and_the_tool` checks that the card's download, the tool, and the metadata pin the same file and that the samples match the card.

## Artifact labels

| Artifact | Type |
|---|---|
| `cylinder_vel.mat` (not committed) | `processed-measured` |
| `wake_u.npy`, `wake_v.npy`, `wake_mask.npy` | `processed-measured` |
| `wake_mean.npy`, `probes.npy`, `wake_meta.json` | `processed-measured` |
| Roshko's Strouhal–Reynolds correlation | `modelled-reference` |

The velocity fields are processed: DaVis computed them from image pairs by cross-correlation, and the record holds no image. **Raw frames are not part of this record**; a lab must not call these fields measurements of particle images, nor the vorticity a measurement. The vorticity, the streamlines, the spectra, the recirculation length, and the Strouhal number are this project's processing in `pbc.data.reference.cylinder_wake`, not artifacts of the record.

## Reference figure

```
uv run python -m pbc.data.reference piv-cylinder-wake --out cylinder_wake.png
```

The code is `src/pbc/data/reference/cylinder_wake.py`. **Status label: processed.** Panels: (a) the vorticity ω = ∂v/∂x − ∂u/∂y of frame 0, by central differences on the 1.05 mm grid, with the masked points grey and the points whose stencil touches the mask left out (NaN), the two probes marked; (b) the mean u over 8000 frames with the streamlines of the mean field and the end of the mean recirculation dashed; (c) v and u at the 2 D probe over the first 30 s, the 3 s of the committed frames shaded; (d) the Welch spectra of u and v at the 2 D probe (Hann windows of 2048 frames, 102.4 s, half overlap) on a log scale, with the paper's 0.889 Hz dotted and twice it dash-dotted.

The analysis, each step in the code:

1. **Frequency.** The 400 s of v at each probe are split into four blocks of 100 s; each block is Hann-windowed, zero-padded to 16,384 points, and its largest peak above 0.3 Hz is refined by a parabola through the logarithm of the three bins around it. The frequency is the mean of the four, its uncertainty their standard deviation over √4. The Welch peak of the whole series is reported beside it.
2. **Strouhal number.** St = f D / U∞ with the paper's D = 9.5 mm and U∞ = 4.35 cm/s; compared with Roshko's correlation St = 0.212 − 2.7/Re for 200 ≤ Re < 2000 (Roshko 1954, NACA Report 1191: St·Re = 0.212 Re − 2.7), measured on long cylinders in air.
3. **Recirculation.** The mean u on the wake axis is negative behind the cylinder; where it turns positive (linear interpolation) is the end of the mean recirculation.

**Caption.** *Processed PIV fields of the wake of a 9.5 mm cylinder at Re = 413. The cross-stream velocity on the wake axis oscillates at 0.889 Hz, the frequency the record's paper reports, and the streamwise velocity there at twice that, as vortices of alternating sign pass the axis; the Strouhal number is 0.194, 5.5 % below Roshko's correlation for long cylinders. On average the flow recirculates up to 2.1 diameters behind the centre of the cylinder's shadow. The vorticity is derived from the measured velocities by central differences, and the grey regions are the cylinder and its shadows, where the record has no data.*

| Quantity | Value |
|---|---|
| shedding frequency, v at 2 D (four 100 s blocks) | 0.8887 ± 0.0028 Hz (blocks 0.8970, 0.8856, 0.8849, 0.8874) |
| shedding frequency, v at 5 D | 0.8881 ± 0.0027 Hz |
| Welch peak of the 400 s series, 2 D / 5 D | 0.8914 / 0.8903 Hz |
| published (paper) | 0.889 Hz |
| peak of u at 2 D above 1.2 Hz | 1.792 Hz, 2.02 times the shedding frequency |
| St = f D / U∞ | 0.1941 (± 0.0006 from the frequency alone) |
| Roshko, Re = 413 | 0.2055 |
| end of the mean recirculation | x = −23.0 mm, 2.14 D behind the shadow's centre |
| 99th percentile of \|ω\| over the 60 frames | 21.4 1/s (ω D / U∞ = 4.7) |
| masked share of the crop | 9.3 % |

## Uncertainty and calibration

**Calibration** is the record's grid in metres, the 20 Hz of the record, and the paper's D and U∞; none carries a stated uncertainty. St is proportional to D / U∞: an error of 1 % in either is an error of 1 % in St. The **record and the paper document no PIV uncertainty**; the following are derived here.

- **The frequency.** ±0.0028 Hz (0.3 %) from four blocks of 100 s; the paper's 0.889 Hz lies within it. The Welch peak (0.891 Hz) and the block mean differ by 0.003 Hz, about one standard error: the peak is not a line but a band (its half-power width in the Welch spectrum is 0.03 Hz, three bins), as the shedding of a finite cylinder in a free-surface channel drifts, and the spectrum of u shows slow fluctuations below 0.1 Hz.
- **The Strouhal number.** 0.194 against Roshko's 0.2055 for long cylinders. A finite cylinder sheds more slowly than an infinite one, and the free stream in the field's top rows is 4 % faster than the paper's 4.35 cm/s (blockage, or the reference velocity measured elsewhere); with U = 4.52 cm/s, St would be 0.187. The comparison is therefore good to about 5 %, not better, and Roshko's correlation was measured in air on other cylinders: it is a reference, not a test.
- **The cylinder's position.** The mask gives x to about one grid spacing (1 mm, 0.1 D); y is uncertain by about 4 mm (the shadow's arm against the wake axis). The probes are placed on the wake axis found from the data, not from the mask.
- **The vorticity** is a derivative of two noisy fields: next to the mask single vectors are spurious (|ω| up to 120 1/s in frame 0, against 21.4 1/s at the 99th percentile), and the central differences of a 1.05 mm grid smooth the shear layers, which are about as thin as the grid. The interrogation windows of 32 pixels overlap by half, so neighbouring vectors are not independent. A lab that shows the vorticity must call it derived and say that its peaks are not resolved.
- **Not bounded here:** the PIV random error (the paper does not state it), the effect of the laser shadows on the vectors next to them, the water temperature (ν, so Re), and the three-dimensional end effects of a finite cylinder with a free surface above it.

Asserted by `tests/unit/test_data_cylinder_wake.py`: the block frequencies and their error, the Welch peaks, that 0.889 Hz lies within one standard error, the harmonic of u, St and Roshko's value, the shadow's centre, the wake axis, the recirculation length, the free stream of the top row, the vorticity percentile, the masked share; the vorticity of a solid-body rotation is twice its rate; the peak finder recovers a known frequency.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo record https://zenodo.org/records/20765567, licence field `cc-by-4.0` (API metadata, read 2026-11-09; a record-level licence, no other rights statement); CC BY 4.0 legal code, https://creativecommons.org/licenses/by/4.0/legalcode, section 2(a)(1)(A) |
| Redistribution of subsets | permitted | the same; section 2(a)(1)(A): reproduce and share the material, in whole or in part |
| Publication of figures and derivatives | permitted | the same; section 2(a)(1)(B): produce, reproduce, and share adapted material |
| Modification and attribution | permitted, with the credit | the same; section 3(a): name the creators, give the licence with a link, and indicate the changes; the card's `attribution` does so and the figure prints it |

## Size, runtime, payload

Sample 1.67 MB (caps: 2 MB per file, the largest 674 KB; 8 MB per dataset; with the hot-wire companion 2.76 MB). The reference figure takes about 2.4 s with the interpreter start and 235 MB peak memory; its PNG is about 480 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the arrays are read at build time and not shipped. An animation of the 60 frames (phase 2) would be drawn from the same arrays; its keyframe and the on-demand budget belong to the lab. The learner's full download is the one file, 1.08 GB (`./scripts/fetch-data.sh piv-cylinder-wake`, checked against Zenodo's MD5), and the extraction (10 s, 1.8 GB of memory) repeats the sample byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual file inspected, checksum, size, version | "The file inspected": the record, the MD5 matched, the SHA-256 computed, MAT 5.0 |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "The extraction"; the parsing tests |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels": the fields `processed-measured`, raw images absent from the record, the vorticity derived; Roshko's correlation `modelled-reference`, compared as a number, not drawn over the data |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/cylinder_wake.py`, from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the frequency from blocks, St against the paper's D and U, the position from the mask, the vorticity derived, what the record does not give |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the FL7 lab (the field viewer of F43, the animation with a keyframe), starts only when the owner says so (Issue #454).
- The published Exp. Fluids article and Phys. Rev. Fluids 5, 054401 were not read; the accepted text on arXiv gave the experiment. A PIV uncertainty, if one is published, would be in them.
- The harmonic near 3f that the paper mentions is not examined.
