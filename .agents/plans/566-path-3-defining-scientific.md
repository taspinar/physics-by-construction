# Plan: F149, path 3 of Part B: defining scientific quality (AE1), tasks and hidden test worlds (AE2), fair baselines and comparison protocols (AE3) (Issue #566)

Source: `docs/roadmap.md`, F149, and the dropped F100 (its outcomes);
`docs/changes/part-b-scientific-products-and-research.md`, B3.1 to B3.3
and the rows of AI6, D2, D5, EV1 to EV4; the owner's start on #566
(2026-11-19). Written by the implementer at the start of the work (the
Issue expects a detailed plan and none existed).

**Level 2.** One new lesson
(`site/lessons/agents-llm/21-defining-scientific-quality/index.qmd`, slot
AE1, course mechanics), two lesson extensions (AE2,
`site/lessons/agents-llm/12-interactive-discovery-benchmarks/index.qmd`;
AE3, `site/lessons/agents-llm/13-agent-versus-non-agent-baselines/index.qmd`)
with three new replay fixtures in AE2's directory, two new library modules
in `src/pbc/discovery/`, one new and two extended experiments in
`src/pbc/mechanics/experiments/`, and new tests. No protected path. No
existing test assertion changes: new tests are added beside the old ones,
and the extension of `comparable` keeps every existing verdict (a new
optional field that existing entries leave unset). No published claim of
AE2 or AE3 is changed or removed: the new sections add their own claims
(criterion 5). If an existing assertion or claim has to change after all,
the feature becomes Level 3 and its approval request is created.

## Visual deliverables

Scientific figures and diagram-based task figures, all drawn by the build
from the verified code (never artwork, never an image file).

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501, diagram-design@550fd66e

- **Artifacts.**
  - AE2: `fig-task-launcher` and `fig-task-spring`, the two pictures of the
    diagram task (`simulated`: the trajectories and the oscillation are
    computed by `pbc.mechanics`; the wall is a drawn part of the setup
    whose height and place the key uses); `fig-drawn-world`, the held-out
    error of the agent and of the baselines on the drawn world, with the
    spread of the baselines over seeds and over drawn worlds (`simulated`).
  - AE1: `fig-probe-information`, where the three spring runs and the grid
    probed, over the information envelope of a probe, amplitude times time,
    which does not depend on the hidden stiffness (`simulated`);
    `fig-task-launcher` again, the picture the item scores are about.
  - AE3: `fig-knowledge-control`, the held-out error of the agent's three
    conditions beside least squares told the form, with the range of
    random selection over twenty seeds (`simulated`).
- **Scientific validation.** Every picture's key is computed from the
  physics code by the build and compared by a test with the key at
  recording time; every score is recomputed from the frozen traces; the
  lesson-source checks, the experiments' unit tests, the single-page
  renders, and the independent review.
- **Accessible fallback.** Every figure has a caption that states its
  conclusion and an alt text that describes it without computed values;
  every figure's numbers are also in a table on the page; no script is
  added.
- The diagram-design skill applies to the two task pictures (the setup
  drawn around computed curves: the wall, the launcher, labels); the
  visualization skill to all five figures.

## The learner and the subject (pbc-physics-teaching)

**Archetype: AI agent or evaluation** for all three lessons. The kind of
evidence is stated at once in each opening (recorded runs replayed and
scored again; deterministic baselines computed by the build; a judge), as
F168 found missing in AE3.

### AE1, Defining scientific quality (new lesson)

- **Learner.** Has done the prior-knowledge lesson (D2, MD1): a discovery
  run, its tools `measure` and `submit`, a held-out score, the three
  conditions. Least squares and the chi-square (outside prerequisite).
- **Central question.** When an agent "solved" a discovery task, what
  exactly did it do well, and what does one score hide?
- **Counterintuitive points.** (a) A correct claim can come without
  evidence (the plain model could have guessed right; a rounded estimate
  scores zero), and evidence can be complete while the claim is wrong
  (the spring's partial run). (b) Calling the software correctly is not
  understanding the instrument: a run with refused calls can choose more
  informative settings than one with none. (c) A metric can be undefined
  for a contestant (a run with no readings has no evidence to weigh), and
  that is a result, not a zero.
- **Metrics, each computed by the build from the frozen trace, never
  added into one number** (`src/pbc/discovery/quality.py`):
  1. *correctness*: the claim's held-out error within the tolerance;
  2. *reasoning*: the claim reproduces the run's own readings within the
     noise (chi-square of the claim on its readings, the test of
     `pbc.discovery.baselines.consistent`); undefined without readings;
  3. *evidence*: least squares on the run's own readings recovers the law;
     undefined without readings;
  4. *completion*: the run submitted a claim and ended within its limits;
  5. *cost*: the model messages and tool calls the run recorded; tokens
     and price not reported by a Claude Code session, shown as such;
  6. *measurement efficiency*: the probes spent, and the fewest of the
     run's first readings whose fit already recovers the law ("probes to
     evidence");
  7. *software interface*: the calls the harness refused;
  8. *physical-tool use*: the information of the run's settings about the
     law's parameters, relative to a grid of the same number of probes
     (D-efficiency, from the derivatives of the public family at the fit
     to the run's readings; never at the hidden value);
  9. *conceptual, physical-tool, and counterfactual understanding* on
     verified figures: the item scores, by category, of the two recorded
     runs of AE2's diagram task, beside chance.
- **Contestants.** The nine runs of the benchmark grid and the three plain
  runs (fixtures on the pages of D1, D2, EV2/AE2, EV3/AE3), the drawn-world
  run of AE2, and the deterministic workflows grid + least squares and
  random + least squares on each system, so that the same metrics are seen
  to apply to methods without a model.
- **Moments.** A prediction before the metrics table: "the spring's
  partial run collected readings from which a fit recovers the law; which
  of the metrics will it fail?" A self-check at the end on which statement
  the profile table supports (the interpretation moment).
- **Code shown and why.** `reasoning` and `probes_to_evidence` and
  `design_efficiency` of `pbc.discovery.quality` (the definitions of three
  metrics, the lesson's method: validation code); the experiment's
  `profiles` (orchestration, exact selection of the lines that make one
  row); the drawing functions are Source links (they compute nothing the
  conclusion rests on; the envelope they plot is defined in the prose).

### AE2 extension, Building tasks and hidden test worlds

- **Learner.** As now (D2). The extension adds a section "Tasks beyond a
  number" after the existing grid, before the limits.
- **Central question added.** How does a benchmark ask about a picture,
  an instrument, and a world it has never shown, and still score the
  answers itself?
- **Counterintuitive point.** A task's truth must be computed, not
  written: the key of every picture is recomputed from the physics that
  draws it, so a change of the figure changes the key; and a "hidden"
  world is hidden only from the tools, not from someone reading the
  source, which the page states as its isolation assumption.
- **The diagram task** (`src/pbc/discovery/tasks.py`, its own questions
  and pictures, not AI6's): picture A, three drag-free trajectories of
  one launch speed at Earth's gravity and a wall; picture B, the
  oscillation of a mass on a spring of public stiffness at two
  amplitudes. Nine questions in four categories: reading (read a value),
  conceptual (direction of the acceleration at the top; speed at zero
  displacement), physical tool, the affordances of the apparatus (can
  the launcher reach a distance; which drawn angle clears the wall;
  where in the allowed time window a reading tells most about the
  frequency), and counterfactual (half the gravity; twice the
  amplitude). Two recorded runs, with the pictures and with their
  descriptions only (the control for what the picture adds), and the
  chance baseline with its distribution. Answered through
  `pbc.agents.vision.answer_sheet`, scored by `pbc.agents.vision.score`.
- **The drawn world.** A world of the central-force box whose strength
  and exponent are drawn by the judge from a stated distribution (not
  round numbers), with three held-out settings also drawn, beyond the
  probe bounds. Condition `none`. One recorded run; the baselines with
  the same budget; random + least squares over twenty seeds and the
  baselines over twenty further drawn worlds, so that per-task results
  carry their spread. The page states the distribution, never the drawn
  values.
- **Withheld cases unreachable, shown by tests (I27).** The tools are
  `measure` and `submit` only; no drawn value or held-out setting occurs
  in the prompt, the tool specifications, or the fixture; every held-out
  setting is refused by `measure`; no public attribute of the world holds
  a drawn value.
- **Neither task relies on AI6's or D5's lesson.** They use the library
  (`pbc.agents.vision`, `pbc.discovery`) and draw their own pictures and
  world; the page links AI6 and D5 as depth in prose.
- **Code shown and why.** `drawn_world` (how a hidden world is drawn,
  the method), the key function `diagram_key` (an exact selection: the
  physics that answers two of the questions), the I27 check
  `withheld_unreachable` (validation).
- **Moment.** A prediction before the picture run's scores: "which
  category will the run without the pictures miss?"

### AE3 extension, Fair baselines and comparison protocols

- **Learner.** As now (EV2/AE2).
- **Added.** A section "Prior knowledge as a controlled variable" after
  the existing tally: each method is labelled with what it is told
  (`knowledge`: the form of the law, the names of the parameters, a
  library of terms, nothing); `comparable` gains the reason "prior
  knowledge differs" when both entries state it. Pairs per system: the
  agent told the form against least squares told the form (equal budget,
  equal knowledge: comparable); the agent told nothing against least
  squares told the form (not meaningful; it measures the value of the
  form); the agent with names against the plain model with names (equal
  knowledge, budgets differ). Random + least squares told the form over
  twenty seeds gives the spread of the baseline per system; the agent has
  one run per cell, said so.
- **F168's gaps in AE3** addressed where the extension touches the page:
  the kind of evidence stated in the opening; the oscillator called "the
  spring (the oscillator environment)" once so both names are tied;
  `draw_methods` becomes a Source link. No existing claim, table, caption,
  or number changes.
- **Code shown and why.** `comparable` (again, now with the knowledge
  reason: the validation the section rests on), `knowledge_pairs` of the
  experiment (orchestration, exact selection of the pairs).

## Recordings

Three runs, recorded on 2026-11-19 by a Claude model (Opus) in a Claude
Code session, each a fresh sub-agent given only the system prompt, the
task, the tool descriptions (and for the picture run the two pictures,
which it opens as image files the harness wrote), told to answer in the
harness's format and to use no tool of its own otherwise. The harness
(this session) ran every call through the allowlist and passed back the
results. Cost records: model messages and tool calls; tokens and price
not reported. Fixtures `replay-picturetask.json`, `replay-texttask.json`,
`replay-drawnworld.json` in AE2's directory; their `TraceInfo` beside the
protocol in `pbc.discovery.tasks`, checked by a test.

## Steps

1. `pbc.discovery.tasks`: the diagram task (pictures, questions,
   categories, key, recorded key), the drawn world (protocol, prompts,
   runs), replay and score helpers, live entry point. Tests.
2. `pbc.discovery.quality`: the metrics. Tests (including a run whose
   correctness and evidence disagree, and a run without readings).
3. `comparable` with the optional `knowledge`. Test.
4. Record the three runs; commit the fixtures with their records.
5. AE2 experiment and page section; AE3 experiment and page section.
6. AE1 experiment and page (`order: 21`, slot AE1).
7. Tests of the three experiments (`assert_the_page_and_the_results_agree`
   and the stated results).
8. Lesson-source checks, the changed tests, then `./scripts/verify.sh
   --base` last (a new lesson).

## Acceptance criteria and where they are met

1. Lesson and agent rules, outcomes: the three pages, their front matter,
   the lesson-source checks.
2. Answers recomputed, withheld cases unreachable: `diagram_key`,
   `score_transcript`, and the I27 tests of `pbc.discovery.tasks`.
3. Equal information and budgets stated, uncertainty over seeds and
   per-task results: the AE2 world table and figure, the AE3 knowledge
   table and figure, the item tables.
4. AE2's two tasks with recomputed answers, not relying on AI6 or D5.
5. AE2 and AE3 claims unchanged: the diff keeps every existing claim span.
6. The verification the targeted run reports, run last.
