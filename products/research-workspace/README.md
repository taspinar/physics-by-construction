# Scientific Research Workspace

A local research application for two kinds of investigation: the
**reproduction** of a published result from its documented inputs, and an
**original** question on a declared dataset, with its follow-up experiment
registered before any measurement. It keeps the question and every question
considered, the registered plan, the source evidence, the run graph with
its branches and failed attempts, typed discrepancies, review findings, the
human's decisions, and a report in which every claim has its run or source
link and its evidence status.

Parts 1 and 2 of F155 (Issue #619): the workspace, the reproduction track,
and the original track (the coil-loss question on `ad3-rlc-pilot`, its
follow-up registered and frozen before any measurement). The follow-up's
bench session, the capstone page RR8, the reference workflow, the rubric,
the manual and guided routes, and the starter come in later parts.

## Product brief

- **Who:** a learner who has finished the research path (RR1 to RR7) and
  wants to run an investigation in which every claim can be traced.
- **The reproduction track:** the spectrum fit of Fixsen et al. (1996), "The
  Cosmic Microwave Background Spectrum from the Full COBE FIRAS Data Set",
  regenerated from the monopole file that NASA's LAMBDA archive distributes
  (the dataset `cobe-firas-monopole`). The goal is the published **spectrum
  fit** from the available derived data: the shape against a blackbody, the
  weighted rms of the residuals, and the bounds on the distortions y and μ.
  It is **not** a reproduction of the absolute temperature calibration,
  which the derived columns do not carry.
- **What it is not:** an autonomous scientist, a preprint platform, or a
  claim of novelty.

## Scientific acceptance criteria

1. Every published value rests on words quoted from the paper, which stand
   in the checked statement of the register entry
   `fixsen-1996-firas-spectrum` (`site/references.yaml`); the owner
   confirms the quoted values on Issue #619 before part 1 merges.
2. The criteria of "reproduced" are registered before any fit
   (`examples/firas/registration.toml`), and every row is decided by them.
3. A discrepancy is reported and typed (`input`, `method`, `uncertainty`,
   `numerical`, `unexplained`); every type but `unexplained` needs a
   recorded check that supports it. A `not-reproduced` row with its
   evidence is a valid result.
4. Every uncertainty the fit gives is statistical; it is shown beside the
   published one, never in its place. A statistical bound below the
   published one is not a better limit.
5. The positive control (simulated spectra at the file's frequencies and
   uncertainties) must recover what was injected; if it fails, every row is
   `not evaluated`.
6. A report is a summary of records, not a proof that the investigation
   succeeded; its first lines say so and count the claims in each status.

## Run it

From a clone of the repository, with the default environment (no optional
group, no model account, no network):

```
uv run --locked python -m pbc.products.research_workspace run \
    --example products/research-workspace/examples/firas --project /tmp/firas
```

It writes the project directory with `report.md` and `view.html`, a static
page you open in a browser (no server, no JavaScript). Then:

```
uv run --locked python -m pbc.products.research_workspace verify --project /tmp/firas
uv run --locked python -m pbc.products.research_workspace review --project /tmp/firas
uv run --locked python -m pbc.products.research_workspace decide --project /tmp/firas \
    --subject b2 --decision stop --reason "..." --revisit "..."
uv run --locked python -m pbc.products.research_workspace accept-finding --project /tmp/firas \
    --finding <key>
uv run --locked python -m pbc.products.research_workspace select --project /tmp/firas \
    --question dipole --decision deferred --reason "..." --revisit "..."
```

`verify` checks every chain (the question archive, the follow-up log, the
evidence ledger) and every digest (the inputs, the sample, the states, the
code the stages run, and the outcome code: every module that decides the
rows, the claims, or the checks, so the file of a changed rule threshold is
named) and
names every problem. `review` replays the agent reviewer from its
fixture and enters the findings it proposes; each is accepted only when its
recomputed check confirms it, and only once: a replayed review leaves an
accepted finding as it is, and a second `accept-finding` is refused. Each
decision is appended to the project's
chains and the view is written again.

## What the reproduction finds (part 1)

The rows the run writes, from the committed sample:

- The weighted rms of the residuals after the fit of a temperature shift and
  a Galactic term is about 49 ppm of the peak brightness, below the
  published 50 ppm, and the residual figure is regenerated: **reproduced,
  by construction** — the residuals of the file are the paper's own fit
  (the caption of its Fig. 5), so these rows confirm that the file and the
  fit agree, not an independent fit. The figure's rule (every residual
  within 1 sigma of the published one) was set after a scratch fit had been
  seen, so its row is marked **post-hoc rule, not a confirmatory result**
  in the report and the view (`post_hoc` in `registration.toml`).
- The absolute temperature 2.728 K: **not reproduced, typed `method`**. The
  fitted temperature returns the file's reference of 2.725 K; branch b4
  shows that it follows the reference, and the missing piece is the
  calibration against the external blackbody.
- The uncertainty of T0: **not reproduced, typed `uncertainty`**. The
  statistical 8 µK is shown beside the published ±0.004 K, which is
  dominated by the thermometry.
- y and μ: consistent with zero, with statistical bounds below the
  published ones, which hold systematic terms (the registered bound rule:
  reproduced, not a better limit).
- σ_y and σ_μ: **not reproduced, typed `uncertainty`**. The statistical
  uncertainties of the fits are 0.60 and 0.86 of the paper's (3.61 against
  6 × 10⁻⁶, 3.43 against 4 × 10⁻⁵), while the central values agree. The
  candidate cause is the paper's weighting with the covariance between
  frequencies (section 3.3), the review's open finding
  `review-covariance-weighting`. These two rows were added after the fits
  had been seen, so they are marked **post-hoc rule, not a confirmatory
  result**.
- The review keeps one finding open: the fits weight with the diagonal of
  the uncertainties, the paper with the covariance between frequencies of
  its section 3.3. It asks for a fit with that covariance, so no revision
  of the report's words resolves it.

## The original track (part 2)

**The question.** Why does the ideal series RLC model fail on the pilot's
circuit (`ad3-rlc-pilot`)? G1: is the loss near the resonance (about
63 ohm) the DC resistance of the parts, or a loss that exists only in
alternating current? G2: are the rise of that loss with the frequency and
the growing phase residual properties of the circuit or of the two
channels? The follow-up that answers them is registered in
`examples/coil-loss/registration.md`, the frozen text copied byte for byte
from the plan of Issue #619; `examples/coil-loss/freeze.toml` names its
digest, the merge commit on `main` that froze it, and the time of that
merge. Evidence measured before that time is refused.

```
uv run --locked python -m pbc.products.research_workspace run \
    --example products/research-workspace/examples/coil-loss --project /tmp/coil
```

The run takes about ten seconds and needs no bench and no model account. It
writes the same exports as the reproduction: `report.md`, `view.html`,
`ledger.json`, `log.json`, `run.json`. What it holds:

- **The analysis of the existing sweeps (exploratory).** The pilot's R-L
  node sweep read with the registration's quantities and the nominal
  100 ohm: R_L at the 13 coarse frequencies, R_L0, L, C, P0, and how much
  an assumed channel mismatch at the registration's thresholds would
  change them. A phase of 0.3 degrees changes Rise by more than three of
  its uncertainties: the pilot cannot separate a mismatch from a loss that
  grows with the frequency. These data chose the thresholds; they confirm
  nothing.
- **The positive controls (simulated).** Whole sessions written as the
  owner will write them and read by the same code, under each
  explanation: DC (G1 `accounted`), AC (G1 `short`, G2 `remains`), a loss
  too steep for G1 (`inconclusive`, its undecidable case), MISMATCH (G2
  `artefact`), BOTH (G2 `mixed`), the pilot's own parts (the precondition
  met) and an inductor 5 % larger (the precondition not met: the
  conclusions scoped, G1 for the pilot `not evaluated`, G2 carried over).
  The noise is the level the pilot's own phasor fits leave.
- **The boundary cases.** Values below, at, and above every threshold,
  each with the outcome the registration's text gives at that value, and
  the meter model on constructed readings.
- **The follow-up.** `not evaluated` until the bench session: G1, G2, and
  the precondition are claims on missing runs. The follow-up log begins
  with the freeze and the identity of the outcome code.

**The bench session** is the owner's, after part 2 is merged into `main`.
Its records go in a folder `session/` beside the example's inputs:
`session.toml` from `examples/coil-loss/session-template.toml` (the time
the AD3 was plugged in, the room temperature with its time and the
thermometer, one entry per run of M0, M1, M2, M3, M5), `readings.toml` from
`examples/coil-loss/readings-template.toml` (the multimeter's readings of
M4), and the physics lab's export of every sweep. The workspace refuses a
template that is not filled in, a malformed or incomplete file, a meter,
range, resolution, or specification other than the registered ones, a run
record without the live input and the device's conditions, a valid sweep
repeated, and any measurement made before the freeze. It reports, without
changing any rule, a wait shorter than 45 minutes and a measurement out of
its registered order. A run that failed twice stops the session; the
follow-up is then `inconclusive` with its reasons.

## The routes

- **Scripted:** the commands above. The scripted reviewer recomputes a fixed
  list of checks from the records (`review.py`).
- **Agent reviewer:** one allowlisted tool, `run_check`, which recomputes a
  check of the scripted reviewer. The committed fixture
  `fixtures/reproduction-reviewer.json` is a **placeholder** written by a
  scripted policy, not by a model. The owner or the supervisor session
  records real ones:

  ```
  uv run --locked --extra anthropic python -m pbc.products.research_workspace record \
      --project /tmp/firas --provider anthropic \
      --price-in <EUR per million> --price-out <EUR per million> \
      --spend-ledger <a file outside the repository> \
      --out products/research-workspace/fixtures/reproduction-reviewer-claude.json
  ```

  The recording counts every call's tokens at the prices given, adds them
  to the spend ledger, and stops at EUR 50 counted across every recording
  of this capstone. `--provider openai` or `local` use the `openai` group.

## Limits

- The data are derived: Table 4 of the paper as LAMBDA distributes it. The
  calibrator data, the thermometry, and the covariance between frequencies
  are not in the file.
- The fits are linear and weighted with the diagonal uncertainties.
- The registration of the reproduction is recorded by digest; it is not
  frozen on `main` (a plan on a feature branch is not frozen). The
  registration of the original track is frozen (`examples/coil-loss/freeze.toml`).
- The original track has no agent reviewer yet: `review` and `record`
  refuse its projects, and its outcomes are decided by the registered rules.
- The original track's thresholds were chosen after seeing the pilot's
  data; only the follow-up's measurements M1 to M5 are confirmatory.
- Rights: the file is public domain under NASA's policy for mission data,
  accepted by the owner on 2026-11-25; no written confirmation was
  requested from LAMBDA (the dataset's card).

## What is here

- `examples/firas/`: the inputs of the reproduction track: `questions.toml`
  (the questions considered, with their decisions), `registration.toml`
  (the registered plan), `sources.toml` (the published values and the words
  they rest on).
- `examples/coil-loss/`: the inputs of the original track:
  `registration.md` (the frozen registration), `freeze.toml` (its digest,
  commit, and time), `registration.toml` (the same registration as the
  workspace's data: five explanations, each with the outcome it predicts),
  `questions.toml` (the questions considered), and the two templates of the
  bench session.
- `fixtures/`: the replay fixture of the agent reviewer (a placeholder).

Data: NASA COBE FIRAS / LAMBDA; Fixsen et al. 1996, ApJ 473, 576. We
acknowledge the use of the Legacy Archive for Microwave Background Data
Analysis (LAMBDA), part of the High Energy Astrophysics Science Archive
Center (HEASARC). HEASARC/LAMBDA is a service of the Astrophysics Science
Division at the NASA Goddard Space Flight Center.
