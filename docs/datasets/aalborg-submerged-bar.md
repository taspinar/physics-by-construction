# Dossier: Aalborg submerged-bar wave flume

Card: `data/registry/aalborg-submerged-bar.yaml`. Spike of 2026-10-09 (F50).

**Decision: go.** Kind: measured against modelled.

## The file inspected

| | |
|---|---|
| Source | Zenodo record 15049542, doi 10.5281/zenodo.15049542, published 2025-03-19, no version number |
| Archive | `Andersen_etal_2025.zip`, 78,610,248 bytes, md5 `982642db25f538084531200b8f2cce21` (published by Zenodo, confirmed on the downloaded file); 45 members, 234 MB unpacked |
| Accessed | 2026-10-09 |
| Read | the archive's `Readme.pdf` (text extracted with pdfminer.six, which is not a project dependency), `examplePlotData.m`, and the files named below |

Layout: `Exp/dataset/Exp_WC{1-4}_surfaceElevation.csv` (40 MB each) and, for each of `iVoF`, `Msigma`, and `DSPH`, `dataset/<model>_WC{1-4}_surfaceElevation_{A,B}.csv` and an input-file archive. Wave conditions 1-3 are regular waves of growing nonlinearity (3 with breaking), 4 is bi-chromatic with breaking (Readme).

The sample is wave condition 1, wave gauge 5, time up to 30 s, from the experiment and from the three A files; the cell text is copied unchanged by `extract_sample` in `src/pbc/data/reference/aalborg_flume.py`. Four files, 480 KB; their sha256 digests are on the card.

What the files hold, as inspected:

- Experiment: two header rows (gauge number, column name), seven columns per gauge: five repetitions, the sample mean, and the expanded uncertainty of the mean at 95 % confidence; 150 Hz; 0-180 s; no NaN. The time stamps have five significant digits, so after 10 s they are quantised to 1 ms (a jitter of 0.33 ms about k/150 s).
- i-VoF: 100 Hz, 0.01-20 s, one NaN (19.82 s at gauge 5). M-sigma: 100 Hz, 0-30 s. D-SPH: about 200 Hz, 0-14.1 s, with NaN in its last row.
- The Readme states that the repetitions were aligned on the gauge-1 signal to mitigate trigger uncertainty, and that the numerical series were upsampled and aligned to the experiment on gauge 1.
- Gauge positions are not in the archive (they are in the source paper, not read), so the spike plots against time at one gauge and makes no statement about position.

## Artifact labels

| Artifact | Type |
|---|---|
| Experiment CSVs: repetitions, mean, expanded uncertainty | `processed-measured` (aligned, downsampled, averaged) |
| A files of i-VoF, M-sigma, D-SPH | `modelled-reference` |
| B files (150 gauges) and input files | `modelled-reference`; not used |

The series are in separate files and the figure draws them apart: the measurement as a solid line with its uncertainty band, the three models dashed.

## Reference figure

```
uv run python -m pbc.data.reference aalborg-submerged-bar --out aalborg.png
```

The code is `src/pbc/data/reference/aalborg_flume.py`. To use the full download instead: `./scripts/fetch-data.sh aalborg-submerged-bar`, unzip, and run `extract_sample` on the extracted `Andersen_etal_2025` folder, then pass its output with `--data-dir`.

**Status label: processed measurement and simulated references** (the top panel mixes them on purpose, each labelled in its legend and its title; the residual panel is *simulated minus measured*, the models linearly interpolated to the experiment's 150 Hz, which is our processing).

**Caption.** *A regular wave measured at one gauge and three CFD solvers' predictions of it. Inside the shaded window, after the start-up and before any run ends, the solvers follow the measured mean to within 0.5-0.9 mm on a wave 12 mm high.*

## Physical consistency check

Asserted by `tests/unit/test_data_samples.py`:

- The dominant period over 2-14 s is 1.508 s in the experiment and 1.50 s in each model (the test allows 2 %).
- Over the window 5-14 s, where all three runs and the steady wave train overlap, the RMS of simulated minus measured is 0.54 mm (i-VoF), 0.90 mm (M-sigma), and 0.86 mm (D-SPH), against an amplitude of 12.3 mm; the test allows 15 % of the amplitude.
- The mean column equals the mean of the five repetitions (to the file's rounding), and the expanded uncertainty is positive.

Outside the window the series disagree for a stated reason: the numerical runs start from rest (the transients before 5 s reach 8 mm) and end at 14.1, 20, and 30 s with values near zero, whereas the experiment runs on. A lesson must show only the window or label these parts.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo licence field: CC BY 4.0 International, read 2026-10-09 |
| Redistribution of subsets | permitted | the same |
| Publication of figures and derivatives | permitted | the same |
| Modification and attribution | permitted with attribution | the same; creators and doi are printed on the figure; the subset and the interpolation are ours and are said to be |

## Size, runtime, payload

Sample 480 KB. Figure from the sample: 1.4 s and about 120 MB; PNG about 330 KB. From the full download: 78.6 MB to fetch, and one 40 MB CSV per wave condition (about 300 MB as an array). CI reads only the committed files; a learner's full download is a documented step.

## Open items

- Read the source paper (Andersen et al. 2025) for the gauge positions, the wave parameters of each condition, and the uncertainty analysis before a lesson states them.
- Decide whether wave condition 1 or a breaking wave condition suits the lesson; the cost of another condition's gauge is about 0.5 MB.
