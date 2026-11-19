# Plan: F169, one cross-course teaching redesign, EM9 `electromagnetism/07-adaptive-phased-array-beam-steering` (Issue #556)

Source: `docs/roadmap.md`, F169 (and F165, whose in-scope list and criteria
it takes for the approved lesson); `docs/teaching-calibration.md`,
"Engineering capstone: EM9" and "The proposal for F169"; the owner's
approval of F168's proposal on #553 (2026-11-18) and the scope recorded on
#556; requirements decision 44; ADR 023. F165 (#532), F166 (#527), and F167
(#545) are the models. Written by the implementer at the start of the work
(the Issue expects a short plan and none existed).

**Level 2.** The lesson source
`site/lessons/electromagnetism/07-adaptive-phased-array-beam-steering/index.qmd`;
its experiment
`src/pbc/electromagnetism/experiments/adaptive_phased_array_beam_steering.py`
(the input constants regrouped into the regions `requirements`, `choices`,
`errors`, and `pass`, and a function `brief` that records the brief's
numbers from those constants; no value and no study changes); one new test
in `tests/unit/test_adaptive_phased_array_beam_steering_experiment.py`; and
this plan. No protected path, no existing test assertion, no front matter,
no claim, table, figure, caption, alt text, exercise, or existing number
changed. The targeted run selects EM9 alone.

## Visual deliverables

A lesson's teaching sequence. No figure is redrawn or moved.

Skills: pbc-physics-teaching@7f34987
Skills: none (pbc-scientific-visualization: no figure moves or is redrawn)

- **Artifact:** the revised page of EM9.
- **Scientific validation:** every existing number, table, figure, caption,
  alt text, claim, and exercise is the experiment's as before; the brief's
  numbers are recorded by the experiment from the same constants the
  studies use, and a new unit test checks that the decision meets each
  requirement of the brief as the page's decision list says; the
  lesson-source checks, the experiment's unit tests, the single-page
  render, and the independent review.
- **Accessible fallback:** captions and alt text unchanged; no script is
  added; the page stays complete without scripts.

## The learner and the subject (criterion 1)

- **Learner.** Has done the interference lesson (two sources), the antenna
  lesson (pattern multiplication, the array factor of a wire of short
  elements), and Maxwell's equations with FDTD. Knows complex exponentials
  and the modulus of a sum, and the mean and variance of a random variable
  (the `outside` prerequisites, which carry the main line here: the error
  studies that decide the number of bits rest on them). Difficulty 3.
- **Central question.** Which array, with which phase shifters, keeps a
  beam on a receiver driving past and a deep null on a fixed interferer
  across a band, and where can no array of this aperture do it?
- **Counterintuitive points.** (a) The null suffers first: channel errors
  that cost the beam a few hundredths of a decibel fill a thirty-decibel
  null. (b) Past a point, more phase-shifter bits buy nothing: the channel
  errors set the floor. (c) A null is almost free in the sidelobes and
  costs almost everything inside the main lobe, so a window around the
  interferer exists that no weight can avoid.
- **Target misconceptions.** "A model that agrees with its closed forms
  says the design works" (verification is not meeting the requirements).
  "More bits always help." "If the beam is fine the null is fine." "A null
  can always be placed." "A phase set at the carrier is right across the
  band."
- **Archetype.** Engineering design or capstone. Journey: the brief (the
  requirements, the constraints, and the success criteria, kept apart from
  the design choices), the model and its assumptions, the method, the
  model checked against closed forms, each study answering one design
  question against a stated requirement, the decision recalled requirement
  by requirement with its conditions, the limits.
- **Why this sequence suits the subject.** A design study is read for what
  it decides. Before, the learner read the explanation and nine code
  listings without knowing what the array must achieve, then met the
  requirements as Python constants mixed with the design's own choices,
  with the success criterion in another region; the decision listed the
  design and did not go back through the requirements. After, the brief
  stands in words before the model, each number from the constants the
  studies use, so every derivation and every study is read knowing which
  requirement it serves (T11's placement in the same curriculum), and the
  decision checks the design against that list, naming for each
  requirement whether it is met, with what margin, or under which
  condition. The model check against closed forms stays first among the
  worked examples: it is the capstone's "small first calculation", and a
  decision will rest on it.

## Before-and-after reading map (criterion 2)

| Moment | Before | After |
|---|---|---|
| Main question | Opening: a motivation and a promise to "turn a set of requirements into a design decision" | Opening: the same, plus the design question in one sentence; answered by the decision |
| The brief | Worked examples, after the explanation and nine listings, as three code regions mixing requirements and choices | "The brief" (`#the-brief`), first part of Assumptions, before the model: requirements, constraints, success criteria, and the design's choices, kept apart, each number from the constants |
| First physical intuition | Explanation: the path difference $x_n\sin\psi$ | Unchanged |
| Key derivations | Explanation: the array factor, its closed form, the null's cost, the expected pattern, the squint | Unchanged; the two coupled formulas as `equation-pair` |
| The model in code | "Code": nine listings, each with its Source link | Unchanged |
| Inputs in code | "The requirements" (worked examples), three regions | "The brief in code" (`#the-requirements` kept), four regions, requirements apart from choices, pointing back to the brief |
| First check | "Is the model right?", the whole `model_checks` (80 lines) | Same place; an exact selection of the four comparisons, the table records behind the Source link |
| The studies | Each with its listing; `taper_and_null` (79 lines) whole; `degradation` (136 lines) whole before the quantisation table | `taper_and_null` as an exact selection; `degradation` as three exact selections, each under the study it computes (quantisation, channel errors, the choice of bits) |
| Prediction or interpretation moment | The self-check on a wider band, after the limits | Unchanged (the calibration: trade-offs are judged against requirements, not guessed) |
| Conclusion | "The decision": the design and its qualifications in one paragraph | "The decision": the design, then each requirement recalled with how the design meets it or under which condition, then the same qualifications |
| Assumptions | First section, a list of six | The same six under "The model's assumptions", after the brief |

**Stayed unchanged, and why.** Every equation, claim (text, type, scope,
evidence), value, table, figure, caption, alt text, the credibility
boundary, the Limits, the self-check, the exercises and their solutions
(their excerpts included), the reproduction section, and the front matter.
The explanation keeps its order: each derivation carries the decision
(the calibration); the onset-shift artefact is short and stays beside its
claim. The nine short model listings stay exact and whole: their control
flow and complex weights are the point. Every existing heading keeps its
identifier (the renamed "The requirements" keeps `#the-requirements`); the
new subsections get explicit ones. No page links to an anchor of EM9
(searched in `site`, `docs`, `src`, `tests`).

## Display of the code (criterion 6)

| Block | Purpose | Form |
|---|---|---|
| `arrays.factor`, `uniform_factor`, `steering_weights`, `null_weights`, `quantise`, `expected_power`, `realised_gain`, `peak_direction`, `grating_onset` | The model and its numerical checks: the direct sum, the closed form, the weights, the realisation, the measurement | Exact full, unchanged |
| `experiment`, regions `requirements`, `choices`, `errors`, `pass` | The inputs of the studies: what is required, what the design chose, what the hardware gives, the scenario | Exact regions |
| `experiment.model_checks` | Validation: the direct sum against the closed form, the peak search, the nulls, the translation symmetry | Exact selection, lines 6 to 10, 13 to 22, 34 to 42, 68 to 78; the table records behind the Source link |
| `experiment.grating_lobes` | Validation: the bisection of the onset | Exact full, unchanged (43 lines, mostly the bisection) |
| `experiment.onset_shift` | Explains the numerical artefact | Exact full, unchanged |
| `experiment.taper_and_null` | Engineering trade-off: the taper's sidelobes and width, the null's depth and cost against $1 - r^2$ | Exact selection, lines 6 to 17, 37 to 40, 43 to 58 |
| `experiment.degradation` | Validation and decision: quantisation against the expectation and rounding without insertion phases; channel errors; the fewest bits meeting the success criterion | Three exact selections: lines 8 to 17 and 54 to 61 under "Quantised phase shifters", lines 71 to 78 under "Errors of the channels", lines 107 to 118 under "The choice of phase shifter" |
| `experiment.band`, `experiment.tracking` | The squint study; the pass with the feasibility rule | Exact full, unchanged (55 and 65 lines, the loop is the content) |
| `draw_*` | None (plot the recorded curves) | Not shown, as before |
| Exercise solutions | Unchanged | Unchanged |

## Steps

1. The experiment: the constants regrouped into four regions; `brief`
   records the brief's numbers; a unit test that the decision meets each
   requirement.
2. The opening: the design question.
3. Assumptions: "The brief" (`#the-brief`), then "The model's assumptions".
4. The explanation: the two coupled formulas as `equation-pair`.
5. Worked examples: "The brief in code"; the exact selections of the
   display table.
6. The decision: each requirement recalled, then the qualifications.
7. The lesson-source checks, the experiment's unit tests, the single-page
   render; screenshots at desktop and phone widths; the targeted
   verification last.
8. Criteria 1 and 2 recorded on the Issue. Criteria 7 and 8 (the owner's
   judgement on the rendered page, comprehension observations) follow the
   session.

The M5 rollout points of #545: the `equation-pair` (step 4) fits; the
chart after the prediction does not apply (no interactive figure); every
Source link sits under its own listing; the header note on outside maths
does not fit EM9 (F168). Not in scope: the F177 interaction; a skill
change.
