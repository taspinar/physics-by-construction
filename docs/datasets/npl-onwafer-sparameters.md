# Dossier: NPL on-wafer S-parameters

Card: `data/registry/npl-onwafer-sparameters.yaml`. Spike of 2026-10-09 (F50).

**Decision: go.** Kind: complex RF measurement.

## The file inspected

| | |
|---|---|
| Source | Zenodo record 22658069, doi 10.5281/zenodo.22658069, published 2025-09-25, no version number |
| Archive | `data.zip`, 3,130,325 bytes, md5 `3580300746156d05dbc5de8957f0b911` (published by Zenodo, confirmed on the downloaded file) |
| Accessed | 2026-10-09 |
| Contents | 20 two-port S2P files: attenuators of 3, 6, and 10 dB and a load device, each measured with a coaxial system, a single-sweep broadband system, and three banded waveguide systems |

The sample is four members, copied byte for byte and renamed to lower case: the coaxial 3, 6, and 10 dB pads (2.5-50 GHz, 191 points) and the single-sweep 3 dB pad (2.5-220 GHz, 871 points). Their sha256 digests are on the card. Format: Touchstone 1.0, option line `# Hz S RI R 50.0`, columns S11 S21 S12 S22 as real and imaginary parts, 250 MHz step, written by scikit-rf. No missing values.

Reader: `pbc.data.touchstone.read_touchstone`, a 40-line parser over NumPy. The Issue lists a locked Touchstone reader among the dependencies; this spike did not add one, because a parser that handles RI, MA, and DB two-port files is smaller than the dependency tree of a general network library, and adds no licence to track. F51 may replace it.

## Artifact labels

| Artifact | Type |
|---|---|
| `coaxial_*_CORR.s2p` | `calibrated-observation` |
| `broadband_3dB_attenuator_0601_CORR.s2p` | `calibrated-observation` |

`_CORR` marks data calibrated with multiline TRL (the archive's `readme.txt`). The un-calibrated raw VNA readings are not in the record.

## Reference figure

```
uv run python -m pbc.data.reference npl-onwafer-sparameters --out npl.png
```

The code is `src/pbc/data/reference/npl_sparameters.py`. **Status label: calibrated.** Panels: |S21| of the four files, S11 in the reflection-coefficient plane inside the unit circle, the largest singular value of S against the passivity limit of 1, and the difference between the two instruments on the same 3 dB pad.

**Caption.** *Three attenuators lose 3.9, 6.8, and 10.5 dB, flat across 2.5-50 GHz; no frequency shows gain, and two different instruments measuring the same pad agree to 0.04 dB.*

## Physical consistency checks

Asserted by `tests/unit/test_data_samples.py`:

- **Passivity.** The largest singular value of S is at most 0.78 at every frequency of every file (0.72, 0.54, 0.36, and 0.78): the devices lose energy and never create it.
- **Reciprocity.** |S21 - S12| is at most 1.3e-3 for the coaxial files and 2.5e-2 for the single sweep.
- **Order of the pads.** The mean |S21| is -3.89, -6.83, and -10.53 dB for the pads labelled 3, 6, and 10 dB.
- **Two instruments.** The single-sweep and the coaxial file of the 3 dB pad differ by at most 0.042 dB in |S21| over 2.5-50 GHz.

The measured loss of the "3 dB" pad is 3.9 dB; the pad is a real part with its own tolerance, and the dossier does not call it an error.

## Calibration context

The calibration standards, the reference plane, and the uncertainty are in the ARFTG 2025 paper (doi 10.1109/ARFTG65332.2025.11168146, free at Zenodo record 17425562), which the spike did not read. The files carry no uncertainty. A lesson that states an uncertainty must read the paper first.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo licence field and `readme.txt`: CC BY 4.0 International, read 2026-10-09 |
| Redistribution of subsets | permitted | the same |
| Publication of figures and derivatives | permitted | the same |
| Modification and attribution | permitted with attribution | the same; creators and doi are printed on the figure |

## Size, runtime, payload

Sample 230 KB. Figure: 1.4 s, about 130 MB peak memory; PNG about 190 KB. The learner's full download is 3.1 MB. CI reads only the committed files.

## Open items

- Which of the banded files and the load device are worth adding for a lesson on calibration.
- The paper's uncertainty budget.
