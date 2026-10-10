# Dossier: GW150914 strain

Card: `data/registry/gw150914-strain.yaml`. Spike of 2026-10-09 (F50).

**Decision: go.** Kind: time series. The reasons are on the card and below.

## The file inspected

| | |
|---|---|
| Source | GWOSC, event GW150914, catalogue GWTC-1-confident, version v3, strain release R1 (`https://gwosc.org/eventapi/json/GWTC-1-confident/GW150914/v3/`) |
| Files | `H-H1_GWOSC_4KHZ_R1-1126259447-32.txt.gz` (1,286,320 bytes), `L-L1_GWOSC_4KHZ_R1-1126259447-32.txt.gz` (1,219,514 bytes) |
| sha256 | H1 `fefe8717306109460b6c9cff74da6beb9e80ee624824b4b09bdd2c54ce9b4dfc`; L1 `43d30a710d6ed4a8f27d13f45182f3825cbe99f87287b518618c8ff0e25e0d7c` |
| Checksum source | Computed by this project on the day of access; GWOSC publishes none for the text product. |
| Accessed | 2026-10-09 |

What the files are: three `#` header lines (event and detector, 4096 samples per second, start GPS 1126259447, duration 32), then 131,072 strain values, one per line. No NaN, no data-quality flags (the HDF5 product carries those; the spike did not need them). Strain is dimensionless, with a standard deviation of about 2e-19. The event is at GPS 1126259462.4, 15.4 s into the segment.

The plain-text product avoids an HDF5 reader, as the Issue allows: `pbc.data.gwosc.read_strain` needs only the standard library and NumPy.

## Artifact labels

| Artifact | Type |
|---|---|
| H1 strain file | `calibrated-observation` |
| L1 strain file | `calibrated-observation` |
| Whitened, band-passed series of the figure | derived from the above; the figure is labelled *processed* |

The strain is the output of the LIGO calibration pipeline, not a raw detector channel. No modelled waveform is committed; the matched-filter template is computed by the figure code.

## Reference figure

```
uv run python -m pbc.data.reference gw150914-strain --out gw150914.png
```

The code is `src/pbc/data/reference/gw150914.py`. It reads the committed sample; to use a fresh download, run `./scripts/fetch-data.sh gw150914-strain` and pass `--data-dir data/downloads/gw150914-strain`.

**Status label: processed** (calibrated strain, whitened by the Welch spectrum of the 32 s and band-passed at 35-350 Hz; both steps disclosed on the figure). Panels: whitened H1 and L1 (L1 shifted by 6.9 ms and inverted, as the figure says), the H1 spectrogram, and the network matched-filter signal-to-noise ratio against the chirp mass of a leading-order template.

**Caption.** *Two detectors, 3000 km apart, record the same rising chirp within 7 ms of each other. The fit of a simple template to the calibrated data prefers a chirp mass near 36 solar masses; the published value, shifted to the detector frame, is 31.*

## Physical consistency check

Asserted by `tests/unit/test_data_samples.py`:

- The best network signal-to-noise ratio of the leading-order template is 22 (the published network SNR is about 24 with full waveforms), at a detector-frame chirp mass of 36 solar masses. The published 28.6 solar masses (source frame, GWTC-1) times 1 + z = 1.09 is 31.2; a leading-order template is expected to overestimate, and the test accepts 1.0 to 1.25 times the published value. The result is 1.15 times.
- The Hanford and Livingston peaks differ by 7.1 ms, inside the 10 ms light travel time, and the published delay is about 7 ms.
- Control: away from the event (more than 3 s) the same template never exceeds a signal-to-noise ratio of 10.

What this does not show: it does not recover the published mass. A lesson that wants the published mass needs a higher-order template or the published waveform, and must say so.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | GWOSC event page: "Data released under a CC BY 4.0 License", read 2026-10-09 |
| Redistribution of subsets | permitted | the same, CC BY 4.0 |
| Publication of figures and derivatives | permitted | the same, CC BY 4.0 |
| Modification and attribution | permitted with attribution | the same; the acknowledgement text of `https://gwosc.org/acknowledgement/` is required and is printed on the figure |

The acknowledgement text GWOSC asks for: "This research has made use of data or software obtained from the Gravitational Wave Open Science Center (gwosc.org), a service of the LIGO Scientific Collaboration, the Virgo Collaboration, and KAGRA", with the funding sentences of that page, and a citation of one of the GWOSC data-release papers. The figure carries the first sentence; a page must carry the full text and a citation.

## Size, runtime, payload

Sample 2.5 MB (two files under the 2 MB cap). Figure: 3.7 s and about 370 MB peak memory on the development laptop; the PNG is about 250 KB. CI reads only the committed files. A learner's full download of the same two files is 2.5 MB.

## Open items for F51 and a lab

- Whitening and spectral estimation are signal-processing background that the learning path has not yet built.
- The calibration uncertainty of the strain is in the data-release papers, not in the files.
