# Series RLC and LED-pair campaigns on an Analog Discovery 3, bench sessions of 2026-11-25 and 2026-11-26

Twenty-seven live campaigns on one series RLC circuit (100 ohm, nominal 1 mH and 10 nF; in each campaign a frequency response from 5 kHz to 200 kHz and ring-downs after a square-wave step) and two live campaigns on two red 5 mm LEDs in anti-parallel behind 100 ohm (the amplitude-dependent response at 1 kHz, 0.2 V to 2 V), measured with a Digilent Analog Discovery 3 by the Autonomous Physics Lab of the project Physics by Construction (F145). Every campaign is published as exported, with its raw samples, measurement table, run record, evidence log, report, figures, and checkpoints, including the failed model checks. The device's serial number is replaced by the stable identifier AD3-001. An educational and experimental tool, not a certified laboratory instrument.

- Dataset: `ad3-bench-2026-11`, version 1.0.0, published 2026-11-27
- Licence: CC-BY-4.0
- DOI: 10.5281/zenodo.24578221
- Exports: 29

## Contents

The part of the archive kept in the repository, under `exports/<export>/`: run.json, measurements.csv, evidence.json of every export, and the raw subsets listed in `MANIFEST.tsv`. The complete files are in the archive `ad3-bench-2026-11-1.0.0.zip` (38048799 bytes, SHA-256 c47d840007c5c5762933417d522a4ab1523e87e353cfdde11b0c24cfcc18286d).

## Changes to the exported files

- `run.json`, field `run.device.serial`: replaced by `AD3-001`. The device's serial number, replaced by the stable device identifier; the original files are kept unchanged by the owner.
- `checkpoints/checkpoint.json`, field `bench.serial`: replaced by `AD3-001`. The same replacement in the campaign's checkpoint.
- Digests recorded inside the files (a checkpoint digest, the SHA-256 of an artifact) refer to the original files and were not rewritten; `MANIFEST.tsv` gives the original's SHA-256 beside the published one.
- A raw subset holds the header and the rows named in its derivation, copied line by line from the published file.

## Provenance

- Measured by Ahmet Taspinar (the owner, at the bench) with the supervising agent session of the project; the circuit was built and confirmed by the owner, the product never rewires it.
- Device: Digilent Analog Discovery 3, identified as AD3-001 in every published file; WaveForms SDK 3.25.1; the factory calibration, not adjusted; channel 1 at the generator W1 on the 5 V range, channel 2 at the response node on the 50 V range, both against ground.
- Series RLC circuit: W1 -> 100 ohm -> the coil (nominal 1 mH) -> node A -> the capacitor (nominal 10 nF) -> ground; channel 2 at node A. The owner states that the circuit and its parts were not changed since the pilot of 2026-11-22 (dataset ad3-rlc-pilot of the repository).
- Session of 2026-11-25: three campaigns between 19:56 and 20:04 UTC; the time the device was plugged in and the room temperature were not recorded.
- Session of 2026-11-26: twenty-four series RLC campaigns from 12:14 to 13:39 UTC; the device was plugged in at about 12:10 UTC (13:10 local, the owner's clock), the room at about 20 degrees C. Two LED-pair campaigns started at 16:07:48 and 16:13:47 UTC (the run records' clock); the owner noted the device plugged in at about 17:08 local (16:08 UTC) by the owner's clock, which the two clocks do not reconcile with the first start, and the room at 19 degrees C.
- Every campaign used the adaptive route of the product; the plans are in each run.json. No campaign was left out and no measurement was removed.
- Licence: CC BY 4.0, the owner's decisions of 2026-11-25 and 2026-11-26 on Issue #614 of the repository.

## Software

- https://github.com/taspinar/physics-by-construction/commit/ee85ab59f6bf92ea3c110cdadbc8d5b63f87b847: the product's code of the three campaigns of 2026-11-25 (code digest f34b3d8a7faef4a15d579a04cb48da2d80c36a88d9630e69d3025729487ef9dc)
- https://github.com/taspinar/physics-by-construction/commit/b322b8d4a391101f65454da3031317c207a60294: the product's code of the campaigns of 2026-11-26 (the same code digest at d4d9a16, a plan-only commit) (code digest f62c047fde3d219564bea9533fda687942d4b552e453711fac8666c304164a6a)

## Citation

Taspinar, Ahmet (2026). Series RLC and LED-pair campaigns on an Analog Discovery 3, bench sessions of 2026-11-25 and 2026-11-26 (Version 1.0.0) [Data set]. CC-BY-4.0. https://doi.org/10.5281/zenodo.24578221
