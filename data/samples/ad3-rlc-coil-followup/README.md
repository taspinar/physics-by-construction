# The coil-loss follow-up on the series RLC circuit of the F140 pilot, bench session of 2026-11-28 (Analog Discovery 3, multimeter)

The registered bench session of the coil-loss follow-up of the project Physics by Construction (F155, the capstone RR8): six frequency-response sweeps of one series RLC circuit (100 ohm, nominal 1 mH and 10 nF; 13 points from 5 kHz to 200 kHz at 1 V) measured with a Digilent Analog Discovery 3 by the physics lab's f138-frequency-response-1 protocol, with the probes at the capacitor node (M0, the conditioning sweep, made twice; M1), at the R-L node (M2, and M5 after the multimeter readings), and both at the generator (M3, the channels' relative response); fifteen resistance readings of a Mastech MAS830BC hand multimeter (M4: the shorted leads before and after, the inductor in and out of the breadboard, the resistor in the breadboard); the session's own records; the evaluation of the frozen registration's rules made the same day; and one diagnostic sweep of 2026-11-26 made before the registration was frozen. Every file is published as recorded, the failed and invalid attempts included. The device's serial number is replaced by the stable identifier AD3-001. An educational and experimental tool, not a certified laboratory instrument; the multimeter is not calibrated, and in this session it did not measure resistance correctly (the cause is not established).

- Dataset: `ad3-rlc-coil-followup`, version 1.0.0, published 2026-11-28
- Licence: CC-BY-4.0
- DOI: 10.5281/zenodo.24622131
- Exports: 2

## Contents

The part of the archive kept in the repository, under `exports/<export>/`: `session.toml`, `readings.toml`, `M4-first-attempt-invalid.md`, `meter-check-exploratory.md`, `M*/evidence.json`, `M*/points.csv`, `M*/run.json`, `M0-repeat/raw.csv`, `M1/raw.csv`, `M2/raw.csv`, `M3/raw.csv`, `M5/raw.csv`, `evaluation-2026-11-28/*.json`, `evaluation-2026-11-28/report.md` of `2026-11-28-coil-loss`, and `evidence.json`, `points.csv`, `run.json` of `2026-11-26-pilot-input-diagnostic`. The complete files are in the archive `ad3-rlc-coil-followup-1.0.0.zip` (1194207 bytes, SHA-256 d892cf68bf27c9e71d27f35ce31e60a3d92b6285270576668203df44a4286273).

## Changes to the exported files

- `M*/run.json`, field `run.device.serial`: replaced by `AD3-001`. The device's serial number in the run record of every sweep of the session, replaced by the stable device identifier; the original files are kept unchanged by the owner.
- `run.json`, field `run.device.serial`: replaced by `AD3-001`. The same replacement in the run record of the diagnostic sweep.
- Digests recorded inside the files (a checkpoint digest, the SHA-256 of an artifact) refer to the original files and were not rewritten; `MANIFEST.tsv` gives the original's SHA-256 beside the published one.

## Provenance

- Measured by Ahmet Taspinar (the owner, at the bench) with the supervising agent session of the project attending; the circuit is the one of the pilot of 2026-11-22 (dataset ad3-rlc-pilot of the repository), and the owner states that its parts were not touched since 2026-11-26; the AD3's leads were moved back from an LED circuit before the session.
- The procedure is the registration of the coil-loss follow-up, frozen at the merge commit d4d9a16d8a71fdaefb27c4b684dba622e5f82280 of the repository (2026-11-26T15:43:26+00:00, digest 3e4cfd1ae9a4fde8e116df21c3b5035ef05b63322605f94e25a466ee13f0a429), in the plan .agents/plans/619-research-workspace.md.
- Device: Digilent Analog Discovery 3, identified as AD3-001 in every published file; WaveForms SDK 3.25.1; the factory calibration, not adjusted; channel 1 on the 5 V range, channel 2 on the 50 V range, both against ground. Multimeter: Mastech MAS830BC (manual ranging, 3 1/2 digits), not calibrated.
- Session of 2026-11-28 (local time, +01:00): the AD3 plugged in at 06:57; the room at 18.5 degrees C at 07:00, read on the room's wall thermostat. The conditioning sweep M0 was started at 07:01:25, 4 minutes after the plug-in instead of the registered 45, by mistake; it completed, is kept in full, and is recorded in session.toml as attempt 1 with the outcome failed and its reason. M0 was repeated after the wait (M0-repeat, 07:45:10), then M1 (07:45:41), M2 (07:46:22), and M3 (07:47:19).
- M4: a first set of fifteen readings was taken with the dial on 200 mV DC instead of the 200 ohm range (every value 0.0) and is kept in M4-first-attempt-invalid.md; readings.toml holds the repeat on the 200 ohm range, read from 08:13 to 08:20. The owner noted that the display fluctuated a lot at R_s_bb. No third attempt was made.
- M5 was started at 08:25:54, shortly after the AD3 was plugged in again after M4 (the board at 22 degrees C at its start, against 43 degrees C at M2); the registration prescribes no wait before M5.
- After M5, outside the registration: a check of the multimeter (meter-check-exploratory.md). On the 200 ohm range the loose 100 ohm resistor read 10.1 ohm and the shorted leads 9.3 ohm; no battery symbol was shown. The cause is not established.
- evaluation-2026-11-28/ is the evaluation of the session by the Research Workspace of the repository at commit a1109da3e40da9366026699dea31a66fc4b94375, whose outcome code is the pinned 974bf992ec24115be479f69046cb1d04dfc5472b3c5752a1db2d699e9b831801: G1 inconclusive, G2 inconclusive, the precondition not met, the deviation that M0 started 4 minutes after the plug-in, and R_s_bb reported at 3.08 ohm, outside 97.9 to 102.1 ohm. Its run.json records the SHA-256 of the session's original files.
- 2026-11-26-pilot-input-diagnostic/ is the one diagnostic capacitor sweep with the pilot's input made on 2026-11-26 before the freeze, by the owner's decision, and disclosed in the registration. No rule of the registration reads it.
- Nothing was selected or left out by its result: every sweep, every reading, and every note of the session is in the archive.
- Licence: CC BY 4.0, by the owner's standing decision of 2026-11-27 for the project's own measurements, applied to this dataset on Issue #619 of the repository.

## Software

- https://github.com/taspinar/physics-by-construction/commit/a1109da3e40da9366026699dea31a66fc4b94375: the physics lab's code of the sweeps of 2026-11-28 (the code digest in each evidence.json); the Research Workspace of the same commit made evaluation-2026-11-28 (code digest d21f41b578f927233cd94ca93cb7c5685c1a6834b6ffa8e16bb463ea08b56a06)
- https://github.com/taspinar/physics-by-construction/commit/b322b8d4a391101f65454da3031317c207a60294: the physics lab's code of the diagnostic sweep of 2026-11-26 (the same code digest at d4d9a16, a plan-only commit) (code digest 7d9ca42538392208d53f469f22fd1a226542d341752bf4efabb802548855630d)

## Citation

Taspinar, Ahmet (2026). The coil-loss follow-up on the series RLC circuit of the F140 pilot, bench session of 2026-11-28 (Analog Discovery 3, multimeter) (Version 1.0.0) [Data set]. CC-BY-4.0. https://doi.org/10.5281/zenodo.24622131
