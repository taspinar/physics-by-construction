# Dossier: the coil-loss follow-up, the registered bench session of 2026-11-28 on an Analog Discovery 3

Card: `data/registry/ad3-rlc-coil-followup.yaml`. Recorded 2026-11-28 for F155 part 2b (Issue #619): the evidence of the registered follow-up of the coil loss of `ad3-rlc-pilot`, measured by the owner at the bench with the supervising agent session attending. The procedure is the registration in `.agents/plans/619-research-workspace.md`, frozen at the merge commit d4d9a16d8a71fdaefb27c4b684dba622e5f82280 (2026-11-26T15:43:26+00:00, digest 3e4cfd1ae9a4fde8…). The owner's start of part 2b is in the Issue's description ("Owner's start of part 2b: the follow-up's evidence", 2026-11-28).

**Decision: go.** Kind: the project's own registered measurement: six frequency-response sweeps of the physics lab, fifteen readings of a hand multimeter, the session's records and notes, the evaluation of the frozen registration's rules made the same day, and one diagnostic sweep of 2026-11-26. CC BY 4.0 by the owner's standing decision of [2026-11-27](https://github.com/taspinar/physics-by-construction/issues/614#issuecomment-7210910945) for the project's own measurements, applied to this dataset in the start of part 2b; the owner confirms it for this dataset on Issue #619 before the merge.

This dossier states what was measured, what was recorded, and what the registered rules computed. It assigns no cause to any reading, to any difference between sweeps, or to the readings of the meter.

## The files, and the split between the repository and the archive

The complete record is two folders, 51 files: `2026-11-28-coil-loss` (the session) and `2026-11-26-pilot-input-diagnostic` (the one diagnostic sweep made before the freeze, which the registration discloses under "Known before the freeze" and which no rule reads). They go to a Zenodo record with a DOI. The owner reserved the DOI `10.5281/zenodo.24622131` in the Zenodo draft on 2026-11-28; the declaration `data/publish/ad3-rlc-coil-followup.toml` carries it, and the card's `archive` entry gives the archive's size and digest. The owner checks the draft's metadata and files and publishes it.

| In the repository (`data/samples/ad3-rlc-coil-followup/`) | Only in the archive |
|---|---|
| `session.toml`, `readings.toml`, `M4-first-attempt-invalid.md`, `meter-check-exploratory.md` | |
| of every sweep (M0, M0-repeat, M1, M2, M3, M5, and the diagnostic): `run.json`, `points.csv`, `evidence.json` | `frequency-response.svg` and `report.md` of every sweep (the physics lab's figure and its report, renderings of `points.csv` and `evidence.json`) |
| `raw.csv` of M0-repeat, M1, M2, M3, M5 (the attempts the registered rules and reports read) | `raw.csv` of the early M0 (attempt 1, recorded as failed) and of the diagnostic sweep |
| `evaluation-2026-11-28/`: `run.json`, `ledger.json`, `log.json`, `report.md` | `evaluation-2026-11-28/view.html` (a rendering of the other four, 100,137 bytes) |
| `MANIFEST.tsv`, `README.md`, `CITATION.cff` (the packager's) | the archive's own `MANIFEST.tsv`, `README.md`, `CITATION.cff` |

The rule depends on no result: the raw samples of the attempts that `session.toml` records as the valid ones are kept, and the raw samples of the two sweeps no registered rule or report reads are not, with the renderings: the evaluation's HTML view, and the figure and the report of every sweep. The repository commits no generated image outside `site/assets/` (the rule `committed-artifact` of `tests/lessons`), and each report links to its figure, which the documentation check requires to exist. Every number of a report is in the committed `points.csv`, `run.json`, and `evidence.json`. Before this dataset, `data/samples` held 30,666,280 of the 33,554,432 bytes the dataset check allows (`src/pbc/data/check.py`). The committed part is 2,406,842 bytes in 37 files, the largest 568,534 bytes, so 481,310 bytes remain. That is within the caps of 2 MB per file and 8 MB per dataset. The archive is `ad3-rlc-coil-followup-1.0.0.zip`, 1,194,207 bytes; its SHA-256 is on the card and in the committed `README.md`.

**The packager.** Both parts are the output of `pbc.data.publish`, run with the declaration ("Publishing a measured dataset" in `docs/datasets/README.md`). The committed files are not edited by hand. The session's folder holds a folder per sweep, so this part added two things to the packager, both without a change of its output for `ad3-bench-2026-11`: a list of the files of one export kept in the repository (`[[repository.export]]`, paths or patterns, each pattern required to name a file), and a replaced field's file given as a pattern (`M*/run.json`). The originals stay unchanged outside the repository (the owner's read-only copy); this session ran the packager on that copy.

**Reader.** `pbc.data.reference.ad3_rlc_coil_followup` (`attempts`, `used`, `readings`, `points`, `read_run`; the standard library's `tomllib`, `csv`, and `json`). The registered rules are not in the reader: they are `pbc.products.research_workspace.followup.evaluate` with the pinned outcome code, and the session folder of the repository's part is a session that function reads unchanged. No dependency is added.

## The device identifier

The device's serial number is replaced in every published file, in the repository and in the archive, by the stable identifier **AD3-001**. It occurs in one field of each sweep's `run.json`, `run.device.serial`. The packager replaces that field where the declaration names it and then searches every output file, the archive included, for the removed value; it found none. The original files stay unchanged on the owner's machine. Digests recorded *inside* the files refer to the original files and were not rewritten: the SHA-256 of `raw.csv` in each `evidence.json`, and the SHA-256 of every file of the session in `evaluation-2026-11-28/run.json`. `MANIFEST.tsv` gives the original's SHA-256 beside the published one for each of the seven changed `run.json` files.

## Software

| What | Commit | Code digest |
|---|---|---|
| The sweeps of 2026-11-28 | a1109da3e40da9366026699dea31a66fc4b94375 | d21f41b578f9… (the physics lab's, `evidence.json` `record.code`) |
| The diagnostic sweep of 2026-11-26 | b322b8d4a391101f65454da3031317c207a60294 | 7d9ca4253839… (the same) |
| The evaluation of 2026-11-28 | a1109da3e40da9366026699dea31a66fc4b94375 | 974bf992ec24… (the Research Workspace's outcome code, equal to the pin recorded on Issue #619 after part 2's merge) |

The physics lab's digests were recomputed for this dossier from the files of those commits (`workflow._code_identity`: the instrument modules and the product's modules), and each equals the digest the evidence logs record. The diagnostic's digest is also that of d4d9a16 and 52b3322, commits that did not change the physics lab.

## The session

Times are local (+01:00) as the owner recorded them, and UTC as the run records state them.

| Step | Time | What was recorded |
|---|---|---|
| Plug-in | 06:57 | the AD3 plugged in (`session.toml`) |
| Room | 07:00 | 18.5 °C, read on the room's wall thermostat |
| M0, attempt 1 | 07:01:25 (06:01:25 UTC) | the conditioning sweep, started 4 minutes after the plug-in instead of after the registered 45, by mistake; it completed and its capture is valid; recorded as `failed` with its reason and kept in full |
| M0, attempt 2 | 07:45:10 | the repeat after the wait (`M0-repeat`), by the owner's decision |
| M1 | 07:45:41 | capacitor sweep, probe 2 at node A |
| M2 | 07:46:22 | R-L node sweep |
| M3 | 07:47:19 | both probes at W1 |
| M4, first set | 07:51 to 07:58 | fifteen readings with the dial on 200 mV DC instead of 200 Ω, every value 0.0; kept in `M4-first-attempt-invalid.md`, used by no rule |
| M4 | 08:13 to 08:20 | the repeat on the 200 Ω range (`readings.toml`); the AD3 unplugged for M4 at about 07:50 |
| M5 | 08:25:54 | M2 again, the parts put back, shortly after the AD3 was plugged in again; the registration prescribes no wait before M5 |
| Meter check | about 08:30 to 08:45 | outside the registration (`meter-check-exploratory.md`) |

The owner states that the RLC parts were not touched since 2026-11-26; the AD3's leads were moved back from the LED circuit before the session. `M4-first-attempt-invalid.md` also records that for the second set the parts were seated one more time than registered. Its section "Second attempt" appears twice, word for word; the file is published as recorded.

The device's conditions at the start of each sweep, as its run record states them (no rule reads them):

| Sweep | Started (UTC) | Board [°C] | Die [°C] | The physics lab's check |
|---|---|---|---|---|
| M0, attempt 1 | 06:01:25 | 18.8 | 29.1 | f0 51,863 Hz, Q 1.465 |
| M0-repeat | 06:45:10 | 43.4 | 57.2 | f0 50,242 Hz, Q 1.484 |
| M1 | 06:45:41 | 43.5 | 57.5 | f0 50,162 Hz, Q 1.486 |
| M2 | 06:46:22 | 43.6 | 57.3 | inconclusive: the phase does not cross −90° within the sweep |
| M3 | 06:47:19 | 43.6 | 57.6 | inconclusive, as the registration states for M3 |
| M5 | 07:25:54 | 22.2 | 32.6 | inconclusive, as M2 |
| diagnostic, 2026-11-26 | 12:36:51 | 44.0 | 57.8 | f0 48,927 Hz, Q 1.502 |

The physics lab's f0 and Q are its own fit against the closed form of the nominal circuit, as recorded; no registered rule reads them.

## The readings of M4

The fifteen readings of `readings.toml`, on the 200 Ω range of the Mastech MAS830BC (resolution 0.1 Ω), as the owner read them:

| Quantity | Readings [Ω] | Time (local) |
|---|---|---|
| Z1, the leads shorted, before any part | 3.9, 3.9, 3.9 | 08:13 |
| R_dc_bb, the inductor across its breadboard rows | 5.3, 4.4, 4.7 | 08:15 |
| R_dc, the inductor out of the breadboard | 5.4, 5.4, 5.4 | 08:17 |
| R_s_bb, the resistor across its rows, the inductor lifted | 8.3, 7.6, 8.8 (the owner: the display "fluctuated a lot") | 08:19 |
| Z2, the leads shorted again | 6.4, 6.4, 6.4 | 08:20 |

By the registered model the zero is z = 5.15 Ω with dz = 2.5 Ω, so the net values are R_dc_bb = −0.35 Ω, R_dc = 0.25 Ω, and R_s_bb = 3.08 Ω (u = 0.80 Ω). The registration's check of the meter reads R_s_bb against 97.9 to 102.1 Ω, the band of the 100 Ω ± 1 % resistor within the meter's limit; 3.08 Ω is outside it. The registration names what that points to: a gross error of the meter or of the contacts. The check after M5, outside the registration, read the loose 100 Ω resistor (bands brown, black, black, black, brown) at 10.1 Ω on the 200 Ω range three times and the shorted leads at 9.3 Ω, with no battery symbol. The meter did not measure resistance correctly in this session. **The cause is not established** (the meter, the leads, or the contacts); no third set of readings was made in the registered session.

## The evaluation by the registered rules

The supervisor evaluated the session on 2026-11-28 with the Research Workspace of `main` at a1109da, whose outcome code is the pinned one (`evaluation-2026-11-28/`). This part applied the same rules, unchanged, to the session folder of the repository's part, copied beside the example `products/research-workspace/examples/coil-loss/`. The follow-up's state it computes has the same SHA-256 as the evaluation's (`dcf9d3d0ac39…`, recorded in its `ledger.json`), and its `report.md`, `ledger.json`, and `log.json` are the evaluation's byte for byte. Its `run.json` differs in the SHA-256 of the six run records whose serial was replaced, in the absent `M0/raw.csv` of the early M0, a failed attempt that no rule reads, and in the absent figure `frequency-response.svg` and report `report.md` of each of the six sweeps, which no rule reads. Those are the only differences.

| Outcome | Value | As the registration words it |
|---|---|---|
| G1, the loss near the resonance | **inconclusive** | D = R_L0 − R_dc_bb = 2.77 Ω with u = 1.00 Ω: neither |D| ≤ 2 u ("accounted", 2.01 Ω) nor D > 3 u and D > 5 Ω ("short"); an outcome that decides nothing is a result |
| G2, the frequency dependence and the phase residual | **inconclusive** | the mismatch is measurable (below); Rise = −0.53 Ω with u_hi = 0.22 Ω, so Rise ≤ 2 u_hi, but P1 = 5.82° is not ≤ P0 / 2 = 3.19° ("artefact" not met), and Rise is not > 3 u_hi ("mixed" not met) |
| The precondition, the identity of the parts | **not met** | M2 against pilot run 3: L differs by −2.4 % and C by −7.7 %, beyond 2 %; R_L0 by 0.49 Ω. The conclusions are scoped to the circuit of M1 to M5; the pilot's discrepancy stays not evaluated for G1, and G2 (a property of the instrument) carries over |
| Deviation | M0 started 4 minutes after the plug-in, earlier than the registered 45 minutes | the earliest attempt of M0 counts; it changes no rule |
| Reported beside G1 | R_s_bb reads 3.08 Ω, outside 97.9 to 102.1 Ω | a gross error of the meter or of the contacts; it decides no outcome |

Every registered quantity that rests on R_s_bb (R_L, R_L0, L, C, Rise, D, through Z = R_s_bb H / (1 − H)) rests on the reading that the registration's check puts outside its band. The rules were applied as written; no threshold, rule, or reading was changed, and the outcomes are not re-computed with another resistance. The sensitivity the registration names, u recomputed with p = 1.2 %, gives u = 1.0042 Ω and changes no outcome. M5 against M2 (repeatability, read by no rule): L −0.7 %, C +6.4 %, R_L0 −0.21 Ω.

## What the sweeps show without the meter

Two results of the session rest on the sweeps alone and not on R_s_bb. They are reported as measured, scoped to this session, and decide no outcome by themselves:

- **M1 against M0.** The −90° crossing of M1 lies 67.9 Hz below that of M0-repeat (50,605.3 Hz against 50,673.2 Hz, interpolated linearly in log frequency between the bracketing coarse points, as the workspace computes it). The phase of M1 minus that of M0-repeat lies between −0.21° and +0.09° at the 13 coarse frequencies.
- **The channels' relative response (M3).** With both probes at W1, the largest |dphi| over the 13 frequencies is 0.49° and the largest |dg| is 0.017, above the registered thresholds 0.3° and 0.003: the mismatch is measurable on this device at this input. dg falls from −0.002 at 5 kHz to −0.017 above 100 kHz; dphi is largest near 12.6 to 17.1 kHz.

The early M0, made 4 minutes after the plug-in with the board at 18.8 °C, has f0 = 51,863 Hz by the physics lab's fit, against 50,242 Hz for M0-repeat; the diagnostic sweep of 2026-11-26 has 48,927 Hz. Both are reported, and neither is read by a rule. Why the crossing differs between sweeps is not established here.

## Schema, units, cadence, masks

| Item | What the files document | What this dossier established |
|---|---|---|
| Schema | `run.json`: product, protocol, route, status, run (mode, device, configuration with the conditions, units, processing, started, finished), sample, check, evidence; `points.csv`: frequency_hz, amplitude_v, gain, phase_deg; `raw.csv`: point, frequency_hz, amplitude_v, t_s, source_v, response_v; `session.toml` and `readings.toml` by the templates of `products/research-workspace/examples/coil-loss/` | as stated; the parsing test reads every file, and `followup.load` accepts the session |
| Units | in `run.json`: Hz, V, s, V/V, degrees; the readings in Ω; temperatures in °C | as stated |
| Cadence | 13 coarse log-spaced points from 5 kHz to 200 kHz at 1 V, 8 periods of 64 samples each; 6 refinements near the crossing at the capacitor node | 19 points in M0, M0-repeat, M1, and the diagnostic; 13 in M2, M3, M5 |
| Masks | none | every attempt and every reading kept; the roles are in `session.toml` and the notes |

## Artifact labels

| Artifact | Type |
|---|---|
| `raw.csv`, `readings.toml`, `session.toml`, the two notes | `raw-measured` |
| `run.json`, `points.csv`, `evidence.json`, the evaluation's files, and in the archive `report.md` and `frequency-response.svg` of every sweep | `processed-measured` |

## Reference figure

The code is `src/pbc/data/reference/ad3_rlc_coil_followup.py`. **Status label: processed.** There are four panels, all against frequency on a log axis, from the points each sweep recorded (`points.csv`). The first plots the phase at the capacitor node of both attempts of M0, of M1, and of the diagnostic sweep of 2026-11-26, from 30 kHz to 80 kHz around the −90° crossing. The second plots the phase at the R-L node of M2 and of its repeat M5. The last two plot the channels' relative phase and relative gain from M3, with the registered thresholds of a measurable mismatch as dotted reference lines. The figure draws no model and no outcome, and nothing that rests on the meter's readings.

**Caption.** *The registered sweeps of 2026-11-28 on the series RLC circuit of the F140 pilot, Analog Discovery 3. Near the −90° crossing at the capacitor node, M0-repeat and M1 nearly coincide, the early M0 (4 minutes after the plug-in) crosses at a higher frequency, and the diagnostic sweep of 2026-11-26 at a lower one. M2 and M5 at the R-L node nearly coincide. With both probes on one node (M3), the channels' relative gain exceeds the registered threshold of a measurable mismatch at 11 of the 13 frequencies, and their relative phase at 6.*

## Uncertainty and calibration

- **The readings.** The registered model (the registration's "Meter readings"): the repeat, the resolution, the contact term from dz, and the specification of 0.8 % + 3 digits, which is the MAS830B manual's and not this meter's own; the meter is not calibrated. In this session its readings are not consistent with the 100 Ω resistor, and the cause is not established.
- **The sweeps.** The phasor fits' standard errors, as the workspace propagates them (u_L, u_hi); `points.csv` carries no per-point uncertainty, so the figure draws none.
- **The device.** The factory calibration, not adjusted. M3 measures the two channels' relative gain and phase at this input; their absolute calibration is not measured.

## The CI evaluation

`tests/unit/test_data_ad3_rlc_coil_followup.py` applies the registered rules in the build to the repository's part, with no device, no meter, no network, and no Zenodo. It copies the example and the session folder into a temporary project and runs the original track (`pbc.products.research_workspace.original.run`). It asserts the outcomes (G1 and G2 `inconclusive`, the precondition not met, the deviation, the R_s_bb report) and the follow-up's quantities to `agent_campaign.TOLERANCE` (1e-6) relative, without an absolute floor above the values compared. It also asserts that the report, the ledger, and the log are the evaluation's, and that the evaluation's `run.json` differs only as stated above, each changed digest being the original's in `MANIFEST.tsv` and each absent file being one the archive alone holds. On the machine that recorded the evaluation (macOS) the recomputation is the evaluation byte for byte.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the owner's decision of 2026-11-27 for the project's own measurements, CC BY 4.0, applied in the start of part 2b on Issue #619 |
| Redistribution of subsets | permitted | CC BY 4.0, section 2(a)(1); the split is the start of part 2b |
| Publication of figures | permitted | CC BY 4.0, section 2(a)(1) |
| Modification and attribution | permitted, with attribution and an indication of changes | CC BY 4.0, section 3(a); the changes: the device identifier, in `MANIFEST.tsv` and `README.md` |

## Size, runtime, payload

The repository part is 2.8 MB, none of it sent to a reader's browser. The reference figure takes about 3 s. The tests of the dataset run the original track once, its simulated controls included, in about 10 s. The archive is 1.2 MB and lives outside the repository; no check reads it.

## The requirements of ADR 007 and where they are met

| Requirement | Where |
|---|---|
| 1. A card | `data/registry/ad3-rlc-coil-followup.yaml` |
| 2. An actual file inspected | "The files", "Schema, units, cadence, masks"; the parsing test |
| 3. Artifact labels | "Artifact labels"; the card's `artifacts` |
| 4. Rights read from the record | "Rights"; the owner's decisions |
| 5. A reference figure by source-controlled code | "Reference figure" |
| 6. Sizes estimated | "Size, runtime, payload"; the card's `size` and `estimates` |
| 7. Uncertainty and calibration | "Uncertainty and calibration" |
| 8. A decision | go (the card) |

## Open items

- The DOI: the owner reserves it in the Zenodo draft; the supervisor writes it into the declaration, runs the packager again, and updates the card's `archive` entry and the test's constant.
- The owner confirms CC BY 4.0 for this dataset on Issue #619 before the merge.
- The cause of the meter's readings is not established. A new measurement of the parts would be a new registration; nothing of it is planned here.
