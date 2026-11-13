# Plan: Issue #437, F83 phase 2 — Pendulum measurements lab (M15)

- Issue: #437 (source: `docs/roadmap.md`, F83); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`
  (`.agents/plans/437-m15-pendulum-dossier.md`). Phase 2 started by the
  owner's word of 2026-11-12 on the Issue.
- Branch: `feature/437-m15-pendulum-lab`
- Base commit: `1182770`
- Written by the implementer: no plan for phase 2 existed when it started.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F83 is
  present and not retired.
- Risk: Level 3 (owner's decision of 2026-11-12 on Issue #437). Filling
  M15 broke the example of
  `tests/unit/test_introductions.py::test_a_reference_to_a_planned_slot_in_prose_is_text`,
  which used M15 as a planned slot; by the owner's word its example moves
  to FL10 (the capstone, planned longest), a changed assertion in an
  existing test. The test keeps `_content("mechanics")`: a slot resolves
  across the whole atlas, and the fluids course has no introduction file
  to build its content from; the second assertion (a published slot is a
  link) is unchanged, and
  `test_a_slot_that_becomes_published_is_linked_and_counted` passes
  unchanged. Otherwise the change is of Level 2: one new lesson, a new model module
  `src/pbc/mechanics/damped_pendulum.py`, a new experiment module, one
  adapter added at the end of `src/pbc/data/adapters.py`, new tests, and
  thirteen more files of the record in the committed sample with their
  entries on the card (`data/registry` is a sensitive path, not a protected
  one). No other assertion, tolerance, budget, protected path, or
  published claim changes. The lesson fills the planned slot M15 with
  `lesson.slot`; `site/curriculum.yaml` and `site/atlas.yaml` (which
  already lists M15) are not edited, but the learning path and the course
  headers change (a new lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007 and its
  addendum (#417), ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of
  `docs/roadmap.md`; section 8.4 of `docs/changes/physics-next-phase.md`;
  the dossier `docs/datasets/xu-damped-pendulum.md` and the card
  `data/registry/xu-damped-pendulum.yaml`.

## Findings that shape the design

- The sample of phase 1 holds one trial per length, in air. The Issue asks
  for a holdout trial and the dossier makes the spread of the trials the
  uncertainty of a period and leaves to phase 2 "which further files of the
  record to commit". The lab adds the creators' cleaned files (125 kB each,
  the raw rows 5 s <= t < 65 s, angle unchanged; checked against the raw
  file for all eighteen runs at inspection) of the other two air trials of
  every length and of the three large-baffle trials of the shortest length:
  thirteen files, 1.63 MB; the sample grows from 1.74 to 3.37 MB (cap 8 MB;
  all samples 23.6 MiB to 25.2 MiB of 32). Cleaned rather than raw files:
  the raw ones would take 4.2 MB of the 8.4 MiB left to all samples while
  another lab runs in parallel. The shortest length is chosen for the
  damping because the lab follows that pendulum throughout (the dossier's
  figure run, the most cycles); the choice is stated on the page.
- Every run is analysed over the creators' window (the cleaned file, or the
  same rows of the raw file for the five first trials), so the trials are
  treated alike; windowed T0 differs from the dossier's whole-record T0 by
  at most 0.27 ms (the test bounds it).
- Numbers (prototype, the reference module's cycle code): T0 of the three
  air trials per length 0.99543, 1.16684, 1.31824, 1.45240, 1.56921 s with
  trial standard deviations 0.21 to 0.86 ms. With those uncertainties the
  line T0^2 = a L + b has reduced chi-square 30 (g from the slope 9.99);
  the simple pendulum with the stated L is rejected outright (L_eff exceeds
  L by 4.2 to 9.9 mm); L_eff = L + c/L (a physical pendulum, g known) has
  reduced chi-square 36 but residuals below 1 mm of length, the last digit
  of the stated lengths. The page reports that the periods are more precise
  than the lengths and that no length model passes within the trial
  spread.
- Damping, shortest length: in air the exponential (linear) envelope leaves
  3.5 mrad rms on trial 1, the linear-plus-quadratic one 2.2 mrad; with the
  rates of trial 1 the other two trials (released 10 degrees higher) are
  predicted to 10 mrad (linear) and 5 mrad (both). Large baffle: 5.0 against
  3.2 mrad in the fit, 22 and 19 against 13 and 8 mrad in the holdout. The
  quadratic coefficient differs between trials by much more than its fit
  standard error; the trial spread is the reported uncertainty.

## Design

One lesson, `pendulum-measurements`, slot M15, strand and course
`mechanics`, order 20 (the next free order), directory
`site/lessons/mechanics/20-pendulum-measurements`, difficulty 2,
`methods: [measured-data]`, prerequisites `harmonic-oscillator`,
`energy-conservation`, `resonance`.

Learning outcomes:

1. Read a rotary-encoder record for what it is: an angle in steps of the
   encoder, everything else derived from it, and no length definition or
   uncertainty given by the record.
2. Measure the period cycle by cycle, correct it to small amplitude with the
   exact period of the energy-conservation lesson, and judge the correction
   by what amplitude dependence remains.
3. Test 2 pi sqrt(L/g) across five lengths with the spread of repeated
   trials as the uncertainty, and say what an effective length can and
   cannot tell about the pendulum.
4. Fit linear and linear-plus-quadratic damping to the decay of the
   amplitude, and test them on held-out trials.

Code:

- `src/pbc/mechanics/damped_pendulum.py` (new): the model the lab tests,
  built from M4, M6, M12: `small_amplitude_period` (T pi / (2 K)),
  `damped_pendulum` (the acceleration of theta'' = -w0^2 sin theta
  - 2 gamma theta' - beta |theta'| theta' for the course's steppers),
  `amplitude_envelope` (the averaged decay A' = -gamma A - kappa A^2 in
  closed form, kappa = 4 beta w / (3 pi)), `effective_length`.
- `src/pbc/data/adapters.py`: `pendulum_angle_series`, the recorded angle
  as a `raw-measured` `Series` (processed once a window is selected).
- `src/pbc/mechanics/experiments/pendulum_measurements.py` (new): the
  experiment of the page: the simulated check of the analysis, the cycles,
  the amplitude correction, the trials and the length models, the damping
  fits and their holdouts, the residual check, four figures, exercises.
  Tests assert that its periods equal the reference module's.
- Card and sample: the thirteen cleaned files, their downloads and
  checksums, an artifact entry; `test_data_xu_pendulum.py` gains a parsing
  test of the added files (no existing assertion changes); the dossier's
  "Open items" records what phase 2 committed.

Page sections: opening question; assumptions; explanation (what the encoder
measures; the period at small and large amplitude, M4 and M6; damping,
M12's linear law and quadratic drag, the averaged envelope; the effective
length of a physical pendulum); code; worked examples (the analysis checked
on a simulated record; the data card and the record; period against
amplitude; repeated trials and the period against length; the damping and
the holdout; what the lab shows); limits; self-check; exercises; run this
experiment.

Claims (typed): numerically-verified for the analysis on a simulated record
(T0, gamma and kappa recovered at the record's cadence and encoder step);
observational for the record's facts (release, amplitudes, cycles);
experimentally-supported for the correction's effect, the trial spread, the
length models and their chi-square, L_eff - L, the damping fits and the
holdout, each scoped to these runs with the length's definition unknown;
the physical cause of L_eff stays unattributed (the dossier). The
independence of the envelope residuals, which the fit errors assume, is
checked (autocorrelation at lag 1); the trial spread is the stated
uncertainty where it exceeds the fit's.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-record` (the preview): the raw angle of the shortest pendulum's first
  trial with the release and the window, and the cycle amplitudes.
  `fig-status: processed`, `fig-artifact: raw-measured`.
- `fig-period-amplitude`: period of each cycle and corrected T0 against
  amplitude for the three air trials of the shortest length, 2 pi sqrt(L/g)
  dotted; residual panel (T0 minus the run's mean). `processed`.
- `fig-length`: T0^2 of each trial against the stated L, the simple
  pendulum, the fitted line, L + c/L; residual panel as L_eff - L in mm with
  trial bars. `processed`, `fig-artifact: processed-measured`.
- `fig-damping`: cycle amplitudes against time for air and baffle, three
  trials each, the two laws fitted to trial 1 (dashed) and predicted for 2
  and 3; residual panels. `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_pendulum_measurements_experiment.py`; `check_figure` on
each; byte-identical redraws. Accessible fallback: alt text without computed
values; the trial, length-model and damping tables carry the numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: about 20 s (eighteen runs of 6,000 rows, a simulation of 60 s at
  2 ms steps with RK4, twenty small fits, four figures; the rest is
  Quarto's fixed cost). Measured: see the handoff note.
- Payload: four PNGs under 0.6 MB together (asserted with a margin below
  0.75 MB), the HTML about 0.2 MB.

## Verification

- `tests/unit/test_damped_pendulum.py`: the model functions (correction
  against its series, envelope against its limits and a simulation,
  effective length).
- `tests/unit/test_pendulum_measurements_experiment.py`: the page and the
  results agree; periods equal the reference module's; the numbers of every
  claim; figure conventions and identical bytes; no numeric console block;
  figure payload; the adapter's status.
- `tests/unit/test_data_xu_pendulum.py`: the added files parse.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson M15 testing M4, M6, M12 against the card's measurements | implementation |
| Period against amplitude with the elliptic correction | implementation |
| Period against length against 2 pi sqrt(L/g), the effective length as the dossier states it | implementation |
| Damping fitted, linear and quadratic, with residuals, uncertainty and a holdout trial | implementation |
| Measured angle distinct from derived quantities and the model; every claim typed with evidence | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
