# Plan: F103 — the Munich Bell test: phase 1 (card, dossier, sample) and phase 2 (the Q8 lab) (Issue #419)

Phase 1 (merged 2026-11-08, commit 90b7f0d): the card, the dossier, the
committed sample, its parsing test, and the reference figure, towards a `go`
judged per dossier (owner's decision of 2026-11-08 on the Issue). Phase 2
(the owner's word of 2026-11-10): the Q8 lab lesson, planned at the end of
this file.

## Steps

1. Download `Bell_2016-04-15.zip` and `README.txt` of Zenodo 22936124,
   confirm the md5s, inspect the three CSV files and the Readme.
2. Commit the four members unmodified as the sample
   `data/samples/munich-bell-event-ready/` (1.2 MB, within the caps).
3. Reader and reference figure `src/pbc/data/reference/munich_bell.py`:
   the correlators and S per state (Eq. S1 and S2 of the Supplemental),
   pooled, with binomial standard errors; the stopping rule of 5000 events
   per state; the pairing check against the lab files; the maintenance
   exclusions as a sensitivity check.
4. Tests in `tests/unit/test_data_samples.py` (parsing: field names,
   shapes, units, cadence, masks; the reproduction of the published
   correlators and S; the whole archive and the exclusions) and
   `tests/unit/test_data_plotting.py` (status and conventions).
5. The card `data/registry/munich-bell-event-ready.yaml`, the dossier
   `docs/datasets/munich-bell-event-ready.md` with the ADR 007 checklist and
   the loopholes closed and not closed, the row in `docs/datasets/README.md`.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (correlators per
  state with standard errors; running S with its band, the bound 2, the
  quantum maximum, the stopping rule). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: the correlators and S equal the PRL's Fig. 3 and text, asserted
  by tests. Accessible fallback: the dossier's caption and table give every
  plotted number in text.

## Out of scope

The card-count test (relaxed by #418), ADR 007, the card schema, any new
state before `go`, the lesson page.

# Phase 2: the lab lesson Q8 (the owner's word of 2026-11-10)

## The lesson

`site/lessons/quantum/07-quantum-measurement-statistics/index.qmd`, id
`quantum-measurement-statistics`, slot `Q8` (kind "measured-data lab"),
strand and course `quantum`, order 7 (the strand has 1 to 6), difficulty 3,
methods `[measured-data, simulation]`, prerequisite lesson
`quantum-entanglement` (Q5), outside prerequisites "Probability: the
binomial count of independent trials, its mean and its standard deviation"
and "Statistics: least squares and the chi-square of residuals" (glossary
terms exist), `related: []`, format 2, preview `fig-running-s`, experiment
`pbc.quantum.experiments.quantum_measurement_statistics`. Title: "Quantum
measurement statistics lab". The slot of the course path is declared in the
front matter, so the tier the change needs is `--base` (a new lesson).

**Learning outcomes.** (1) Estimate the four correlators of a Bell test and
S from recorded event counts, with the binomial standard error of each, and
reproduce a published value; (2) test the model of Q5 (a singlet of
visibility V, S = 2 sqrt(2) V) against the correlators with a least-squares
fit and its reduced chi-square, and extend it only as far as the data
require; (3) check the statistics of a real Bell test: the balance of the
random settings, no-signalling marginals, the selections of the run and
their effect on S; (4) state what a violation of the CHSH bound establishes,
which loopholes the experiment closes by its design, and which assumptions
and selections the data cannot remove.

**Sections.** Opening (the physical question: does nature break the bound
that Q5 derived, and what does the record of one experiment allow one to
say). Assumptions (independent events, the binomial error, the mapping of
the bits to the angles established by reproducing the paper, the stopping
rule, no correction of the outcomes, the settings as recorded). Explanation
`{#explanation}`: the correlator from counts; S per heralded state with the
sign pattern g (Eq. S1, S2 of the paper's Supplemental); the Q5 model at the
Munich angles: E = -V cos(alpha - beta) for Psi-, -V cos(alpha + beta) for
Psi+, S = 2 sqrt(2) V, the threshold V = 1/sqrt(2); the one extension the
data ask for, an offset eps of lab 2's analysis basis, S = 2 sqrt(2) V cos
eps; what the standard-error count means under independence and what the
paper's P-value bounds add. The program `{#code}` (excerpts of
`pbc.quantum.bell_test` and the reader). Worked examples
`{#worked-examples}`: the data (the card, the run: `fig-run`), the counts
and the correlators (table `counts`, `fig-correlators`), S against the Q5
bounds (table `chsh`, `fig-running-s`), fitting the model of Q5 (tables
`fit-one`, `fit-two`), the statistics checked (tables `settings`,
`no-signalling`, the sensitivity rows of `chsh`), and the section "What the
data do not close" (the acceptance criterion: freedom of choice and the
independence of the random number generators from their past are assumed;
the selections heralding, maintenance exclusions, stopping rule, pairing
with their checks; the detection and locality loopholes closed by the design
as the paper's claim, not tested by these files). Limits `{#limits}`.
Self-check (why the exclusions cannot have made the violation). Exercises:
the visibility below which the fitted model's S falls to 2; the number of
events a 5-standard-error result needs at this S; the first event from
which the running S of Psi+ never returns below 2. Run this experiment
`{#reproduce-this}`.

## The model and its place

`src/pbc/quantum/bell_test.py` (new, Level 2): the angles of the Munich
settings, the predicted correlator of a heralded state at a visibility and a
basis offset (`predicted_correlator`, checked against
`pbc.quantum.bell.joint_probabilities` of the Werner mixture with lab 2's
angle shifted), the CHSH value of the model (`model_chsh` = 2 sqrt(2) V cos
eps), the fits of the one- and the two-parameter model with
`pbc.data.fit.fit_curve` (`fit_visibility`), the setting balance
(`setting_balance`), the no-signalling marginals (`no_signalling`), and the
events a given significance needs (`events_for_sigmas`). The reader, the
selection, the correlators, S and the running S stay in
`pbc.data.reference.munich_bell` (phase 1), which the experiment imports.
The experiment `src/pbc/quantum/experiments/quantum_measurement_statistics.py`
computes every number, table and figure of the page.

## The fit and the uncertainty

Each correlator has the binomial standard error sqrt((1 - E^2) / n) and S
the quadrature sum, as the paper (Fig. 3). The fits are weighted least
squares with these errors as absolute sigma: the reduced chi-square tests the
model (one parameter: 6.4 and 7.8 on 3 degrees of freedom, rejected; two
parameters: 0.03 and 2.17 on 2, the first with the helper's warning, which
the page explains). Standard errors of V and eps from the fit; the predicted
S of the fitted model against the measured S, its standard error the
gradient of 2 sqrt(2) V cos eps through the full covariance of the fit
(review round 4, M2: V and eps come from one fit and may be correlated). The "6.7 standard errors" of
the pooled S assume independent events; the paper's P-value bounds that do
not are quoted as given values from the card and never recomputed.

## Visual deliverables

Three scientific figures, each `fig-status: processed` and
`fig-dataset: munich-bell-event-ready` (the pairs file is
`processed-measured`), each with `label_status`, `add_credit` (the card's
attribution), a unit on every axis, a title, a legend, colour never the only
encoding; measurements as points with bars or lines with bands, the model
and the reference lines apart (open markers, dotted lines) and named as such.
Skills: pbc-scientific-visualization@a70b501

- `fig-run`: the valid events of each state accumulated over the 3.7 days
  of the run, the maintenance pauses visible, the excluded attempts marked,
  the stopping rule marked. Validation: the counts and times are the ones
  the parsing test asserts. Fallback: the table of the run in the prose
  (coverage, counts, pauses) and the alt text.
- `fig-correlators`: the eight correlators with one standard error, the
  ideal +-1/sqrt(2) as a dotted reference, the fitted two-parameter model as
  open markers apart. Validation: the test asserts the published values of
  Fig. 3 of the paper and the fit. Fallback: the `counts` and `fit-two`
  tables hold every plotted number.
- `fig-running-s` (the preview): S of each state after each event with its
  band, the bound 2, 2 sqrt(2), the stopping rule. Validation: the test of
  phase 1 (`test_the_running_bell_s_ends_at_the_whole_state_value`) and the
  experiment test. Fallback: the `chsh` table and the prose.

No conceptual diagram; no widget (the no-LLM, no-script path is the whole
page).

## Claims and their evidence

- observational: the run (coverage, counts, pauses, exclusions); evidence
  the cell `the-run` and the card.
- observational: the eight correlators and S of the published selection
  equal the paper's; evidence `counts`, `chsh`, the card.
- observational: the pooled S is 6.7 standard errors above 2 under
  independence; evidence `chsh`, the card.
- experimentally-supported: the one-parameter model of Q5 is rejected at
  these errors; the two-parameter model describes both states with V about
  0.79 and eps about -5 deg, and its S equals the measured S; evidence
  `fit-one`, `fit-two`, the card.
- observational: settings balanced, no marginal of one lab moved by the
  other's setting beyond its error, the exclusions and the stopping rule
  move S by less than a thirtieth of its error; evidence `settings`,
  `no-signalling`, `chsh`.
- observational (quoted): the loopholes closed by the design and the
  assumptions left, from the paper via the card; evidence the card.
- observational (review round 1, M1): the meaning of the bits is the only
  one of eight readings that reproduces the published correlators
  (`counts`, the card); the two heralded states split evenly within the
  binomial error and every excluded attempt of either lab falls in a pause
  (`the-run`, `fig-run`); the correlator sizes as a fraction of the ideal
  and the excess of the two larger over the two smaller together, more than
  four standard errors (`counts`); the running S of Psi+ below 2 once and
  its band clear of 2 from event 295 (`fig-running-s`); the pairing; the
  assumptions left, quoted (the card). Each computed one is asserted by the
  experiment's tests. The one-parameter fit's visibility is
  experimentally-supported (`fit-one`).
- review round 4, M1: what the setting and no-signalling checks show
  (observational; `settings`, `no-signalling`); the shift of S by the
  maintenance exclusions and, separately computed (`stop-shift-in-errors`),
  by the stopping rule (observational; `chsh`); the exclusion of the local
  hidden-variable models under the stated assumptions with the pooled
  standard-error count and the worst marginal (experimentally-supported;
  `chsh`, `no-signalling`). The Bell bound is attributed to the entanglement
  lesson and the design statements (heralding before the settings, the
  loopholes shut, the rules fixed in advance) to the paper.
No claim wider than the data and the model: a violation is a statement
about local hidden-variable models under the stated assumptions and
selections; the significance under independence is not the probability
that local realism holds.

## Tests

- `tests/unit/test_bell_test.py`: the predicted correlator equals the Q5
  code's for both states, visibilities and offsets; model S equals the sum
  of the signed predicted correlators; the fit recovers V and eps from
  synthetic correlators; the setting balance and no-signalling helpers on a
  hand-made `Pairs`; `events_for_sigmas` scales as the square.
- `tests/unit/test_quantum_measurement_statistics_experiment.py`: the
  command writes what the page shows; the published values are reproduced;
  the one-parameter fit is rejected and the two-parameter fit accepted with
  eps agreeing between the states; S of the model within one error of the
  measured; the no-signalling and balance numbers within bounds; the
  sensitivity rows; `check_figure` on every figure.

## Runtime and payload

The reader parses the three files in under 0.5 s; the running S, the fits
and the three figures take about 3 s in total (phase 1 measured about 2 s
for the reference figure). Far inside the 30 s warning. Payload: three PNGs
of about 100 to 170 KB each, no widget, under 1 MB against the 3 MB budget.

## Accessible fallback

Every plotted number is in a table or in the prose; each figure has alt text
that describes the shape; the page needs no script.

## Documents

`docs/authoring.md` ("Measured data": the fourth lesson that uses measured
data); the dossier's open items (phase 2 delivered, the lab page). No ADR,
no check, no protected path, no changed assertion in an existing test.

## Verification (the owner's instruction on the Issue)

The lesson's tests, `pbc.data.check`, `./scripts/verify.sh --only code` and
`--only default`, the targeted run for the page render of the new lesson
(which reports that a new lesson needs `--base`); the full run and `--base`
are left to the script after the session. The page is rendered and inspected
at 1280 x 800 and 390 x 844.
