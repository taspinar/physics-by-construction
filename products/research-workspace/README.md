# Scientific Research Workspace

A local research application for two kinds of investigation: the
**reproduction** of a published result from its documented inputs, and an
**original** question on a declared dataset, with its follow-up experiment
registered before any measurement. It keeps the question and every question
considered, the registered plan, the source evidence, the run graph with
its branches and failed attempts, typed discrepancies, review findings, the
human's decisions, and a report in which every claim has its run or source
link and its evidence status.

This is part 1 of F155 (Issue #619): the workspace and the reproduction
track. The original track (the coil-loss question on `ad3-rlc-pilot`), the
capstone page RR8, the reference workflow, the rubric, the manual and
guided routes, and the starter come in later parts.

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
code) and names every problem. `review` replays the agent reviewer from its
fixture and enters the findings it proposes; each is accepted only when its
recomputed check confirms it. Each decision is appended to the project's
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
  published ones, which hold systematic terms.
- The review keeps one finding open: the fits weight with the diagonal of
  the uncertainties, the paper with the covariance between frequencies of
  its section 3.3. It asks for a fit with that covariance, so no revision
  of the report's words resolves it.

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
  frozen on `main` (a plan on a feature branch is not frozen).
- Rights: the file is public domain under NASA's policy for mission data,
  accepted by the owner on 2026-11-25; LAMBDA's written confirmation is
  pending (the dataset's card).

## What is here

- `examples/firas/`: the inputs of the reproduction track: `questions.toml`
  (the questions considered, with their decisions), `registration.toml`
  (the registered plan), `sources.toml` (the published values and the words
  they rest on).
- `fixtures/`: the replay fixture of the agent reviewer (a placeholder).

Data: NASA COBE FIRAS / LAMBDA; Fixsen et al. 1996, ApJ 473, 576. We
acknowledge the use of the Legacy Archive for Microwave Background Data
Analysis (LAMBDA), part of the High Energy Astrophysics Science Archive
Center (HEASARC). HEASARC/LAMBDA is a service of the Astrophysics Science
Division at the NASA Goddard Space Flight Center.
