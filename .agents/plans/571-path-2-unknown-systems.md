# Plan: F146, Path 2: unknown systems and competing models; system identification; noise, uncertainty, and identifiability (Issue #571)

Source: `docs/roadmap.md`, F146; the session instructions on Issue #571;
ADR 023 decision 2. Written by the implementer at the start of the work
(the Issue expects a detailed plan and none existed).

**Level 2** by the paths (lessons, `src/`, tests, documentation). No
protected path, no ADR, no CI workflow, no check of `scripts/verify.conf`,
no dependency. The published claims of the four lessons stay as they are:
every existing claim span, number, table, figure, exercise, and test
assertion is kept, and the feature only adds sections, exercises, outcomes,
and code. Shared code changes only by addition (a new function, a field
with a default that reproduces the published behaviour); the existing tests
of that code pass unchanged. If a published claim or an existing assertion
has to change after all, the change becomes Level 3 and gets
an approval request (.agents/approvals/571.md).

The prerequisites of the four lessons are not changed. MD1 keeps
`black-box-force-law` (D1) as a prerequisite, as MD5, MD7, and MD9 do; the
two new exercises of MD1 depend on nothing of D1's or D5's page: each
states its system, its tools, and its search on MD1's page, and D1 and D5
are linked from it as depth only (criterion 3).

## What is delivered

| Part | Where |
|---|---|
| MD3: operator choices | a section of `site/lessons/agents-llm/08-symbolic-regression/index.qmd`; `grammars` and its figure in `pbc.mechanics.experiments.symbolic_regression`; the grammar step in `pbc.discovery.symbolic` (`Search.step`, `PowerLaw.step`, default one half: the published behaviour) and `candidate_search` (a stated list of forms) |
| MD5: equivalent explanations | a section and an exercise of `site/lessons/agents-llm/18-discovery-under-noise/index.qmd`; the analysis in `pbc.mechanics.experiments.discovery_under_noise`, with `fit_curve` and `pbc.data.inverse.profile` |
| MD2: the RLC circuit in time and frequency | a section and an exercise of `site/lessons/mechanics/12-inverse-physics-parameter-discovery/index.qmd`; the models and the analysis in `pbc.mechanics.experiments.inverse_physics`, with `pbc.electromagnetism.circuits` (EM5's model) and `pbc.data.inverse.recover` |
| MD1: boundary, accessible variables, competing models, priors | a section and two exercises of `site/lessons/agents-llm/06-prior-knowledge-in-discovery/index.qmd`; the towing tank, its worlds, and its routes in `pbc.discovery.towing_tank`; the analysis in `pbc.mechanics.experiments.prior_knowledge_in_discovery` |
| Tests | the experiment test of each lesson (every new claim span, statement by statement); `tests/unit/test_symbolic.py` (the step, the candidates); `tests/unit/test_towing_tank.py` (the box, the hidden truth out of the tools' reach, I27) |
| Documentation | `docs/discovery-protocol.md` ("Unknown systems and competing models"); the module rows of `docs/architecture.md` and `docs/project-map.md` |

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501, diagram-design@3f3bf78

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| The towing tank as a system: inside, controls, observation, what is outside the boundary | Conceptual diagram (`pbc.authoring.diagrams`) | `fig-tank-boundary`, MD1 | Shows no result; its labels are the controls and the observation of the environment (a test compares them) | `fig-alt` with the insight; the boundary table says the same |
| Held-out error of each condition on each design, with the tolerance | Scientific figure, `simulated`, log scale | `fig-tank-conditions`, MD1 | The judge's error of each claim; the test recomputes the verdicts | alt text; the table of the conditions |
| Impedance sweep, the fitted model, and the residuals in units of the noise | Scientific figure, `simulated`, two panels on one frequency axis | `fig-rlc-impedance`, MD2 | The model is `SeriesRLC.impedance`; the recovery table and the test | alt text; the recovery tables |
| The law chosen against the noise for three grammars | Scientific figure, `simulated`, log noise axis | `fig-grammars`, MD3 | The searches of `pbc.discovery.symbolic`; the table of the sweep | alt text; the table |
| Two explanations through the same readings, extended to the calibration and beyond the probes; residuals of each | Scientific figure, `simulated` | `fig-equivalent-explanations`, MD5 | `fit_curve` of each model; the chi-square table; the test | alt text; the table |

No animation, no widget, no page layout. No preview changes.

## The teaching of each extension

Archetypes: MD1, MD5 AI agent or evaluation (main), the new parts
model or simulation; MD2 measured-data investigation after a model or
simulation; MD3 model or simulation (a discovery lesson without an agent).
Each new part states its evidence kind at once: computed by the build,
no model run.

### MD3, `symbolic-regression`: operator choices

- **Question.** The page searched one grammar. Would a grammar with fewer
  operators, or with more, have found the same law?
- **Counterintuitive point.** A richer grammar is not a better search: it
  contains the law and still loses it at a lower noise, because it has
  simpler forms close to the law that the noise lets through.
- **Grammars.** Whole powers (multiplication and division only); half
  powers (adds the square root: the published grammar); quarter powers
  (adds the fourth root). The complexity counts the variables and the
  steps of the grammar's own grid (`step`), so it is the published one for
  half powers.
- **Prediction moment.** Before the sweep: at which noise does the
  quarter grammar lose the law, below or above that of the half grammar?
- **Result.** Clean data: no form of whole powers is consistent (a failure
  reported); half and quarter powers choose the law. Under noise: the
  quarter grammar loses it at a lower noise, to a form with a fourth root.
- **Code shown.** The `exponents` of the three grammars (the object the
  section is about, exact region); `grammars` (the loop that compares them
  on the same data, exact); the step of `Search.complexity` (exact
  selection). The drawing function is a Source link (read first: it
  computes nothing beyond the fractions of the table).
- **Unchanged.** Complexity, units, and withheld prediction as published
  (criterion 6).

### MD5, `discovery-under-noise`: observationally equivalent explanations

- **Question.** Two explanations fit the same readings within the noise:
  which is true, and what would tell?
- **Setup.** A stated synthetic gauge, apart from the agent's hidden one:
  one mass, distances over a narrow range, no null reading. Explanation A:
  the law with an offset of the gauge. Explanation B: no offset and a
  shallower law. Both fitted by `fit_curve`.
- **Counterintuitive point.** Both fits are consistent, their chi-squares
  differ by less than one, and their exponents differ by more than their
  stated errors pretend: the exponent of A has a large error because it is
  correlated with the offset (the correlation table and the profile of the
  offset show it).
- **What separates them.** A measurement on which they disagree: the null
  reading at zero mass (A predicts the offset, B nothing), or readings far
  out. The noise at which the present readings would separate them follows
  from the misfit of B on the noise-free readings, as `noise_floor` does
  for the forms of MD3.
- **Prediction moment.** Before the table of the null readings: which
  explanation does a reading at zero mass reject?
- **Exercise.** The noise below which the readings alone separate the
  explanations, and how many null readings separate them at the lesson's
  noise.

### MD2, `inverse-physics`: the RLC circuit in time and frequency

- **Question.** The oscillator of the page in another guise: the series
  RLC circuit. What does a step response determine, and what does an
  impedance sweep?
- **Counterintuitive point.** The step of the capacitor voltage has three
  element values and determines two combinations of them (the decay rate
  and the natural frequency): a ratio of voltages carries no ohms. The
  impedance, a voltage per current, determines all three.
- **Time domain.** `recover` on the step response with the rate and the
  frequency: recovered within the tolerance; the same response with R, L,
  and C as parameters: reported as not identified (`fit_curve`'s
  `identifiable` and its warnings).
- **Frequency domain.** `recover` on the real and imaginary parts of the
  impedance at a sweep of frequencies: R, L, and C recovered within the
  tolerance; residuals in units of the noise; correlation of the
  estimates (the sensitivity of each parameter).
- **Prediction moment.** Before the fit with R, L, and C: how many of the
  three can the step response fix?
- **Exercise.** A sweep only below the resonance: which parameter loses
  its precision, and why (the sensitivity of the impedance to it).

### MD1, `prior-knowledge-in-discovery`: boundary, variables, candidates, priors

- **Question.** The three runs had their family given. Before the first
  probe of a system whose law is not given, what has to be decided, and
  what does prior knowledge buy and cost?
- **The four decisions.** The boundary of the system (what is inside,
  what the experimenter holds fixed outside), the accessible variables
  (what can be set, what can be read, what cannot be reached), the
  candidate structures, and the prior (which candidates are admitted).
- **The system.** A towing tank, outside electronics: a sphere pulled
  through a fluid at a set speed, the diameter chosen from the tank's
  spheres, the drag force read with a relative noise. The fluid is outside
  the boundary: held fixed and not readable. The law is hidden
  (`TowingTankEnvironment`, `pbc.discovery`); the routes reach it only
  through its allowlist.
- **Two conditions on the same probes.** Knowledge-informed: the two drag
  laws (Stokes, linear in speed and diameter; Newton's quadratic drag,
  speed and diameter squared), each with one constant. Restricted prior:
  every power law of speed and diameter of MD3's grammar.
- **Two designs.** Speeds and diameters varied; one diameter only. The
  prior fixes the diameter's exponent that the second design cannot.
- **Counterintuitive point.** The prior helps exactly where the data are
  thin (one diameter), and the same prior fails in a world where neither
  candidate holds, where the restricted search succeeds.
- **Prediction moment.** Before the table: on one diameter, which
  condition predicts the larger spheres?
- **Exercise 3, the black-box force law.** Probe the tank yourself with a
  random design, recover the form with the grammar, predict the withheld
  probes; the build runs the route and scores it.
- **Exercise 4, the unknown world.** A second tank whose fluid is unknown:
  both conditions on the same probes; the candidates are both rejected,
  the grammar finds a form that predicts the withheld probes. A test shows
  that neither world's truth, nor its withheld probes, is reachable by the
  tools (I27).
- **Depth.** D1 (`black-box-force-law`) and D5 (`unknown-physical-worlds`)
  linked as depth.

## Steps

1. This plan and the handoff note.
2. MD3: `pbc.discovery.symbolic` step and candidates, tests; the
   experiment, the page section, the experiment test.
3. MD5: the experiment, the page section and exercise, the test.
4. MD2: the experiment, the page section and exercise, the test.
5. MD1: `pbc.discovery.towing_tank` with its tests; the experiment, the
   page section and exercises, the test.
6. Documentation: the protocol, the architecture and project map rows.
7. Summary and completion record.
8. Verification, last: the changed tests and the lesson checks while
   working; `./scripts/verify.sh --base` at the end (the front matter of
   four lessons changes: outcomes and descriptions). The complete
   `./scripts/verify.sh` is not run in the session (the Issue).

## Discoveries during the work

- **The complexity docstring was wrong.** `PowerLaw.complexity` said "1 for
  sqrt(L)"; the code (and the page, "L alone, three") gives two. The
  docstring now says two; no number changes.
- **The grammar step.** `grammar_step` reads the step from the exponents
  (one half for the published grammar), so the published complexity and
  every published number are unchanged; `power_law_search(..., forms=)`
  fits a stated list of forms, the candidates of a prior.
- **`simplest_rival` was quadratic in the number of forms.** It recomputed
  `search.chosen` for every form; with the quarter grammar (83 521 forms)
  that took minutes. It now computes it once; the result is the same.
- **`fit_curve` takes a one-dimensional `x`.** MD5's models of distance
  and mass are fitted through `at_masses`, which fixes the masses of the
  readings.
- **MD1's header links D5.** `related: [unknown-physical-worlds]` links D5
  as depth from the header; D1 is linked as a prerequisite already. The
  prose names both lessons by title as depth.
- **The unknown tank has its own seed.** With the same seed the two
  worlds draw the same relative noise at the same settings and give equal
  errors, which reads like a mistake; the unknown world uses seed one.
- **The RLC parameters are in ohm, mH, and µF**, so that the fitted
  parameters are of one size; `circuit` converts them for
  `SeriesRLC`.

## Where the teaching skill changed the learning experience

- MD3: the grammar comparison is a prediction moment (does the richer
  grammar keep the law longer?) placed after the clean-data table, where the
  learner has the predicted noise of each grammar's nearest simpler form and
  can answer before the sweep; the conclusion turns "a richer grammar" from
  a remark in Limits into a measured result.
- MD5: the section opens with a stated synthetic gauge, kept apart from the
  agent's hidden one, so the learner can compare each explanation with a
  truth; the counterintuitive point (the wrong explanation fits slightly
  better and has a small standard error) comes before the correlation and
  the profile that explain it; the prediction moment (which explanation a
  null reading rejects, and by how much) precedes the table that settles
  it, and ties back to the calibration of the lesson's first section.
- MD2: the RLC circuit is introduced as the page's own oscillator in
  another guise (inductance for mass, resistance for friction), so the
  identifiability question carries over; the prediction (how many of three
  element values a step response fixes) is asked before the fit, and the
  answer is given as a property of the observation, not of the domain.
- MD1: the four decisions are introduced through what each limits, before
  the box; the boundary diagram precedes the table; the prediction (which
  condition predicts larger spheres from one sphere) precedes the run; the
  two exercises turn the result around (a prior that wins on thin data loses
  in a world where it is false).
- Code on the pages: the models and the designs as regions (the objects
  the sections are about), the searches and routes in full (their control
  flow is the point), and every drawing function as a Source link (each was
  read first: none computes a value beyond what its caption states, except
  `draw_explanations`, whose difference in units of the noise is stated in
  its caption).

## Out of scope

New pages; an external discovery engine; a recorded agent run for the new
parts (each is computed by the build without a model); changes to D1's or
D5's lessons; the prerequisites of the four lessons.
