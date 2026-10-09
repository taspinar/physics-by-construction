# ADR 007: Real datasets are declared inputs behind a feasibility gate, with small committed samples and no portal access in builds

## Status

Proposed with the planning of the change cycle `physics-next-phase`;
accepted when that planning is approved. Extends ADR 002 (a second kind of
committed input a build cannot regenerate).

Date: 2026-10-09

## Context

The re-approved requirements make real experimental measurements and
calibrated observations first-class content: a learner reproduces a
measured-versus-model comparison locally "from a small committed sample or
a documented download", every dataset has a metadata card, a feasibility
gate precedes any lesson commitment, large or restricted datasets are
never committed, and the build, every check, and every lesson work with no
access to data portals. They leave the committed-sample size cap to
planning.

ADR 002 decided that generated artifacts are never committed and that the
one committed input a build cannot regenerate is the replay fixture of an
agent lesson. A measured dataset is the second such input: no build can
regenerate a measurement. The candidate datasets range from about 1 MB
(GW150914 strain, 32 s per detector) to 1.1 GB (cylinder-wake PIV), in
HDF5, text, Touchstone, MAT, FITS, zip, and RAR, under CC BY 4.0 on the
records read on 2026-10-09, with acknowledgement requirements that differ
per source. A public download is not automatically licensed for
redistribution of subsets or of derived figures.

## Decision

1. **Datasets are inputs, never generated artifacts.** They live under
   `data/`, outside `site/` and `src/`, and the committed-artifact check of
   ADR 002 does not apply to them. The architecture's invariant I6 names
   them, with replay fixtures, as the only committed inputs a build cannot
   regenerate.
2. **One card per dataset**, `data/registry/<dataset>.yaml`, for every
   dataset the project surveys, spikes, uses, or rejects. A card records:
   source DOI or URL, creator, licence or permission status with four
   explicit answers (local download, redistribution of subsets, publication
   of derived figures and animations, modification and attribution),
   version and access date, measurement type per artifact (`raw-measured`,
   `processed-measured`, `calibrated-observation`, `modelled-reference`,
   `synthetic-test`), calibration details, schema, units, cadence,
   coordinate conventions, masks and missing values, documented
   uncertainty, size, format and reader, checksum where available,
   estimated runtime, memory, and page payload, and the decision (`go`,
   `defer`, `reject`, `survey-only`) with reasons and date. A card is not a
   validated lab.
3. **The feasibility gate precedes any lesson commitment.** Before a
   dataset gets a `go`: an actual small file is inspected; schema, units,
   calibration, cadence, masks, and time coverage are validated; every
   artifact is labelled; one reproducible, scientifically meaningful plot
   is produced by source-controlled code; the rights are established from
   the record and its terms; download, build, and page payload are
   estimated; a dossier in `docs/datasets/<dataset>.md` records the
   evidence and the decision.
4. **Small samples may be committed** at `data/samples/<dataset>/` only
   when the card's rights permit redistribution (CC0, CC BY, or an
   equivalent recorded permission), under these caps: 2 MB per file, 8 MB
   per dataset, 32 MB for all samples together. Every sample has a card, a
   checksum the check compares, and a test that parses it and asserts field
   names, shapes, units, masks, and cadence. A restricted dataset is never
   committed, whatever its size; the site then links to the original and
   shows only what the learner can reproduce from a documented download.
5. **Builds, checks, and CI never contact a portal.** Lesson cells and
   `src/pbc` read only committed samples; `scripts/fetch-data.sh` is the one
   learner-side download, by the card's URL, version, and checksum,
   respecting the host's rate limits, never invoked by verification. A test
   runs verification with data portals and external web hosts blocked;
   fetching the pinned toolchains, packages, and the Mathlib cache is an
   install-time dependency (ADR 003), not portal access.
6. **Every figure from data carries a status** (`measured`, `calibrated`,
   `processed`, `simulated`, `conceptual`) from the artifact type of its
   source, and measurements stay distinct from modelled references, fitted
   curves, reconstructed signals, and agent conclusions, with filtering,
   interpolation, and selection disclosed on the page. Claims about the
   data are typed (`observational`, `experimentally-supported`,
   `numerically-verified`, `formal-theorem`).
7. **Attribution travels with the data.** The card's attribution text and
   acknowledgement requirements are rendered on the page that uses the
   sample and listed on the About page's third-party material section.

## Alternatives considered

**Fetch datasets in CI at build time.** Rejected: the requirements forbid
portal access in builds and CI; portals rate-limit and change; the build
would stop being deterministic and offline.

**Git LFS for larger samples.** Rejected: it adds a storage quota, a
toolchain step for every learner and for CI, and does not change the
rights question; the 30 second page budget already limits what a lesson can
process, so the caps above are enough for a teaching sample.

**Host samples on the site's own origin as static files, outside Git.**
Rejected: the repository would no longer be the single source of truth,
and reproduction from a clone would need a download.

**No committed samples; every lab downloads.** Rejected: the lesson's cells
must execute in CI, and a learner must be able to reproduce the figures
from a clone.

**One cap for everything.** Rejected in favour of three caps so that a
dataset cannot consume the whole budget with many small files and the
repository's growth is bounded.

## Consequences

Positive:

- A real-data lesson is held to the same merge gate as every other lesson,
  and its figures are regenerated from the same bytes on every build.
- Rights, provenance, and processing are recorded once, in a schema a
  check validates, and shown on the page.
- Negative findings are kept: a rejected dataset has a card that says why.

Negative, with mitigations:

- Samples are small, so some labs show less than the full dataset would;
  the page says so and documents the download for the "extend" path.
- Readers for some formats (MAT, FITS, RAR extraction) are extra locked
  dependencies; a format whose reader cannot be locked as a Python
  dependency is a reason to defer the dataset.
- The repository grows by up to 32 MB of binary samples over time; the cap
  and Git history make the cost explicit and bounded.
- Rights can change after a card is written; the card's access date and
  version pin what was true, and a later editorial pass rechecks before
  reuse.
