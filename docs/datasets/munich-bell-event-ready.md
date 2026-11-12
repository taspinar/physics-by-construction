# Dossier: Munich event-ready Bell test

Card: `data/registry/munich-bell-event-ready.yaml`. Inspected 2026-11-08 for F103 (Issue #419), the measured-data lab Q8; the choice of this record is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: event counts of a Bell test (settings and outcomes of two distant labs). Recorded under the owner's decision of 2026-11-08 on Issue #419: Q8 may become `go` if the inspection supplies all the evidence ADR 007 requires, judged on this dossier alone. The checklist at the end names the evidence for each requirement.

## The file inspected

| | |
|---|---|
| Source | Zenodo record 22936124, doi 10.5281/zenodo.22936124, published 2026-09-24, no version number; creators W. Rosenfeld, D. Burchardt, R. Garthoff, K. Redeker, N. Ortegel, M. Rau, H. Weinfurter, the authors of the paper |
| Paper | Rosenfeld et al., "Event-Ready Bell Test Using Entangled Atoms Simultaneously Closing Detection and Locality Loopholes", Phys. Rev. Lett. 119, 010402 (2017), doi 10.1103/PhysRevLett.119.010402; read as arXiv:1611.04604v2 with its Supplemental Material |
| File | `Bell_2016-04-15.zip`, 369,992 bytes, md5 `53544819317d4dcfbe5c63e039a8aa38` (published by Zenodo, confirmed on the downloaded file) |
| Members | `Bell_2016-04-15_9_pairs.csv` (375,815 B), `Bell_2016-04-15_9_lab_1.csv` (449,879 B), `Bell_2016-04-15_9_lab_2.csv` (400,255 B), `Readme.txt` (1,302 B); sha256 of each on the card |
| Accessed | 2026-11-08 |
| Record | four files: this archive, the archive of the public run of 14 June 2016 (391,935 B), a PDF of the former website, and a README |

The record's README says that the archives were recovered in 2026 from the group's computers at LMU Munich, after the former website `bellexp.quantum.physik.uni-muenchen.de` closed, and deposited without modification. The creators of the record are the paper's authors. The README does not say which archive gives the published result; the paper does (its Apr. 15 run), and the reproduction below confirms it. The sample is the four members of the archive, copied byte for byte (1.2 MB).

Reader: `pbc.data.reference.munich_bell.load`, the standard library's `csv` module and NumPy; no dependency is added.

## Schema, units, cadence, masks, coverage

| Item | What the files document | What this dossier established |
|---|---|---|
| Schema | `Readme.txt` names the columns: time, setting, result, local timestamp, Bell state (lab 1 and pairs), exclusion flag, comment, and for pairs the line in each lab file | pairs file tab-separated, 8 columns; lab files semicolon-separated; the lab 2 header ends with a delimiter and its rows have 6 fields, one fewer than its header |
| Units | time in Unix milliseconds; nothing else | settings and results are bits; the local timestamp is a hardware counter without a stated unit (not used); lines count from 0 after the header |
| Meaning of the bits | none | setting 0/1 of lab 1 is α = 0°/α′ = 90°, of lab 2 β = −45°/β′ = +45°; equal outcome bits count as +1 in the correlator. Established by reproducing the paper's eight correlators (Fig. 3), the only assignment that does |
| Cadence | events "at a rate of about 1/min" for the later public run (paper) | event driven: median 20.5 s between valid events, mean 31 s; three pauses of 1.6 to 1.8 h, the daily maintenance |
| Masks, missing values | an exclusion flag with a reason; the pairs file has the valid events | 17 attempts of lab 1 and 45 of lab 2 excluded, all "Maintenance"; no missing or malformed value; every pair agrees with the two lab rows it names, within the ±100 ms pairing window; two valid attempts at the end of lab 2 have no partner |
| Time coverage | Unix times | 2016-04-15 14:19:57.751 UTC to 2016-04-19 07:03:43.045 UTC, 3.70 days; 10,201 valid events, 5054 heralded as Ψ− and 5147 as Ψ+ |

The parsing test `tests/unit/test_data_samples.py::test_munich_bell_sample_parses` asserts the field names and delimiters, the shapes, the time coverage and order, the cadence, the bits, the exclusions, and the consistency of the pairs with the lab files.

## Artifact labels

| Artifact | Type |
|---|---|
| `Bell_2016-04-15_9_lab_1.csv` | `raw-measured` |
| `Bell_2016-04-15_9_lab_2.csv` | `raw-measured` |
| `Bell_2016-04-15_9_pairs.csv` | `processed-measured` |

The lab files are each lab's record of every attempt: the random setting bit and the outcome bit of the state detection, as recorded. The pairs file is derived from them by the experimenters (pairing by time, dropping the excluded attempts), so it is processed. The correlators, S, the standard errors, and the selection of 5000 events per state are computed by `pbc.data.reference.munich_bell` and are not part of the record; the figure draws the ideal correlators ±1/√2 as a dotted reference line, apart from the measured points, and labels it as such.

## Reference figure

```
uv run python -m pbc.data.reference munich-bell-event-ready --out bell.png
```

The code is `src/pbc/data/reference/munich_bell.py`. **Status label: processed** (it reads the pairs file). Panels: the eight correlators E(a, b), four per state, with one binomial standard error, for the first 5000 events of each state; and S of each state as the events accumulate, with its one-standard-error band, the local-realist bound 2, the quantum maximum 2√2, and the stopping rule marked.

The CHSH value of each state follows the paper's Eq. S1 and S2: S = Σ g(a, b) E(a, b), with g = −1 for every setting pair except (α′, β) for Ψ− and (α′, β′) for Ψ+, where g = +1. The pooled S multiplies each event's ±1 product by g of its own state and setting pair and forms the four correlators over both states.

**Caption.** *Correlations of two atoms 398 m apart, measured after each heralded entanglement. With the first 5000 events of each heralded state, the four correlators give S = 2.240 ± 0.047 for Ψ− and 2.204 ± 0.047 for Ψ+, and both states pooled 2.221 ± 0.033, 6.7 standard errors above the local-realist bound 2 and below the quantum maximum 2√2 ≈ 2.83 that an ideal state would reach. From the 40th event on, the running S of Ψ− never falls below 2, that of Ψ+ once (its 160th event); the one-standard-error band of Ψ+ lies wholly above 2 from its 295th event on.*

| Quantity | This code | Published (PRL) |
|---|---|---|
| E(α, β), E(α, β′), E(α′, β), E(α′, β′), Ψ− | −0.511, −0.615, 0.608, −0.507 | the same (Fig. 3a) |
| the same, Ψ+ | −0.535, −0.603, −0.603, 0.463 | the same (Fig. 3b) |
| S, Ψ− (5000 events) | 2.240 ± 0.047, 5.1 σ above 2 | 2.240 ± 0.047, 5.1 σ |
| S, Ψ+ (5000 events) | 2.204 ± 0.047, 4.3 σ | 2.204 ± 0.047, 4.3 σ |
| S, pooled (10,000 events) | 2.221 ± 0.033, 6.7 σ | 2.221 ± 0.033, 6.7 σ |
| S, pooled, whole archive (10,201 events) | 2.2210 ± 0.0329 | (not published) |
| S per state, whole archive | 2.2462 (Ψ−), 2.1977 (Ψ+) | (not published) |

The research of 2026-11-08 evaluated the whole archive and found 2.2210 ± 0.0329, equal to the published pooled value by coincidence of rounding; its per-state values (2.246, 2.198) differ from the published ones (2.240, 2.204). The difference is the stopping rule: the paper fixed 5000 events per state before the run, and the archive holds 54 Ψ− and 147 Ψ+ events after it. Taking the first 5000 of each state in time order reproduces every published number above to the digits printed. Asserted by `tests/unit/test_data_samples.py::test_the_bell_selection_reproduces_the_published_correlators_and_s`.

## Uncertainty and calibration

The archive gives **no uncertainty** and **no calibration**. Neither is missing in the sense of a defect:

- **Statistical.** Each event contributes one product ±1, so a correlator over n events has the binomial standard error √((1 − E²)/n), and S, the sum of four independent correlators, the quadrature sum. This is the paper's error (Fig. 3: "Displayed errors are equal to one standard deviation"), and the code reproduces it. It assumes independent, identically distributed events.
- **Beyond the standard error.** The paper does not rely on the Gaussian count of standard errors: its P-values are upper bounds that allow memory in a local-realist model and a bounded predictability of the random settings (martingale bound Pm = 2.57 · 10⁻⁹, game bound Pg = 1.74 · 10⁻¹⁰ for this run; Supplemental Sec. III). This dossier cites those bounds and does not recompute them: they need the predictability bound τ < 6.3 · 10⁻⁴ of the random number generators, which the archive does not contain. A lab must not present "6.7 σ" as the probability that local realism holds.
- **Calibration.** None applies. The outcomes are the detection results as recorded; the readout fidelity and the imperfect entangled state lower the correlators (|E| ≈ 0.5 to 0.6 instead of 1/√2 ≈ 0.71), and a Bell test must not correct for that. Correcting outcomes for detector inefficiency would reintroduce the fair-sampling assumption that the event-ready scheme exists to avoid. The angles and the meaning of the bits are not in the archive; they are established by the reproduction of Fig. 3 (table above).

## What the data close, and what they do not

The Q8 page must state which loophole or selection the data do not close. From the paper and the inspection:

**Closed by the design (the paper's claim, not tested by these files):**
- *Detection loophole.* The test is event-ready: a heralding signal from the Bell-state measurement announces each entangled pair, and every heralded event produces an outcome in both labs, so no fair-sampling assumption is needed (PRL, p. 1). The files show it: every valid heralded attempt of lab 1 has an outcome and a partner in lab 2.
- *Locality loophole.* The labs are 398 m apart, which gives 1328 ns; each measurement, from the random bit to the recorded result, takes at most 948 ns (lab 1) and 1094 ns (lab 2), leaving margins of 340.7 ns and 267.4 ns (Supplemental Sec. I.C). The files carry no timing at that resolution; this is the paper's evidence.

**Not closed: assumptions the data cannot remove:**
- *Freedom of choice (setting independence).* The random settings are generated inside the future light cone of the Bell-state measurement, which happens 10.7 µs before the choice; their independence of the hidden variables is assumed, not enforced (PRL, p. 5).
- *Independence of the random number generators from their past.* The analysis assumes that the bits for each event depend only weakly on anything in their backward light cone, including earlier settings and outcomes; the paper names this as a remaining assumption, removable only with spacelike-separated, for example extraterrestrial, sources of randomness (PRL, p. 5).

**Selections in these data (documented, each checked):**
- *Heralding.* Only heralded attempts are recorded. This is the event-ready selection: the herald precedes the setting choice, so the settings cannot influence it, and it opens no detection loophole.
- *Maintenance exclusions.* The experimenters excluded 17 heralded attempts of lab 1 and 45 attempts of lab 2, all marked "Maintenance"; maintenance every 24 h was fixed before the run (PRL, p. 4). 13 of the 17 have a partner in lab 2 within 100 ms; added back, they change the pooled S of the whole archive from 2.2210 to 2.2201, less than a thirtieth of its standard error. The exclusion does not make the violation. Asserted by `test_the_whole_bell_archive_and_the_excluded_attempts_change_s_little`.
- *Stopping rule.* 5000 events per state, fixed before the run; the 201 later events of the archive, included, leave the pooled S at 2.2210 ± 0.0329.
- *Pairing.* The two labs' PC clocks are matched within ±100 ms (the archive's Readme); every pair is consistent with its lab rows, and only two lab-2 attempts at the end of the run remain unpaired.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo licence field of https://zenodo.org/records/22936124, CC BY 4.0, read 2026-11-08; https://creativecommons.org/licenses/by/4.0/legalcode |
| Redistribution of subsets | permitted | the same; legal code section 2(a)(1), sharing in whole or in part |
| Publication of figures and derivatives | permitted | the same; section 2(a)(1), producing and sharing adapted material |
| Modification and attribution | permitted with attribution | the same; section 3(a): creators, licence, link, and an indication of changes, printed on the figure; the record's README asks to cite both the record and the PRL, which the card's attribution does |

The README of the record and the archive's `Readme.txt` state no licence; the licence is the record's metadata field, as for the other Zenodo cards.

## Size, runtime, payload

Sample 1.2 MB in four files, the largest 450 KB (caps: 2 MB per file, 8 MB per dataset); the full download is the same archive, 370 KB packed (`./scripts/fetch-data.sh munich-bell-event-ready`). Figure: about 2 s including the interpreter start, about 125 MB peak memory; PNG about 170 KB. A lesson page that reads the sample and draws this figure stays far inside the 30 s warning, the 60 s limit, and the 3 MB payload: the data are read at build time and only the figure reaches the browser. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | the table "The file inspected"; md5 of the archive and sha256 of each member on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from models | "Artifact labels"; the ideal correlators are a dotted reference line, labelled |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/munich_bell.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the binomial standard errors of the paper, reproduced; the P-value bounds cited, not recomputed; no calibration applies |
| 8. This dossier with the decision | this file, including the loopholes closed and the assumptions and selections that remain |

## The lab (phase 2)

The lesson `site/lessons/quantum/07-quantum-measurement-statistics/` (Q8, started on the owner's word of 2026-11-10) reads the committed sample through `pbc.data.reference.munich_bell`, reproduces the published correlators and S with the stopping rule, evaluates the whole archive and the excluded attempts, fits the model of the entanglement lesson (`pbc.quantum.bell_test`: the visibility, then the visibility with an offset of lab 2's analysis basis), checks the balance of the settings and the no-signalling marginals, and states the loopholes and selections of the section above. Its figures are `processed` (the pairs file). The one-parameter model is rejected (reduced chi-square 6.4 and 7.8 on 3 degrees of freedom); the two-parameter model describes both states with a visibility of about 0.79 and an offset of about −5°, the same for both states, and reproduces the measured S. The offset is a parameter of the model: the record gives nothing that identifies its cause, and the page says so.

## Open items

- The public run of 14 June 2016 (`Bell_2016-06-14.zip`, S = 2.134 ± 0.048 and 2.057 ± 0.048 in the paper) is in the same record and is not inspected; it would show a weaker violation from a run with a lower trapping rate.
- The runner-up, NIST's CH-Eberhard tables (`Diagnostic Statistics/19-45.xlsx`), is not inspected.
