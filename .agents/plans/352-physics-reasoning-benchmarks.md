# Plan: F100 — Physics reasoning benchmarks (EV1), Issue #352

- Issue: #352 (source: `docs/roadmap.md`, F100); "Detailed implementation
  plan expected: yes, short".
- Branch: `feature/352-physics-reasoning-benchmarks-ev1`; base `cd69524`.
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 2 (one new lesson, one new module of `src/pbc/agents`, one
  experiment, tests, docs). No published claim, tolerance, budget, check, or
  dependency changes; a new lesson's own claims are no trigger.
- Gates: F61, F62, F64, F113 (the gates of this phase), F96 (pictures given
  with the task, `pbc.agents.vision`), F65 (the protocol) delivered.

## Design

One format 2 lesson in `agents-llm`, `course: mechanics`, slot EV1, methods
`simulation` and `llm-agents`:
`site/lessons/agents-llm/21-physics-reasoning-benchmarks`, id
`physics-reasoning-benchmarks`, module `pbc.agents.reasoning_benchmark`,
experiment `pbc.mechanics.experiments.physics_reasoning_benchmarks`.

- **Twelve items per seed, four kinds.** Every item is built from a lesson of
  the site and its parameters (and the order of a choice's options) are drawn
  from the seed:
  - *problems* (text): the drag-free range (M3), the period of a pendulum at
    a large amplitude (pendulum code), the speed of a released oscillator at
    equilibrium (M4), the velocity after an elastic head-on collision (M7);
  - *visual affordances* (picture B, the range against the angle of M3):
    whether a throw at that speed can reach a distance; where the best angle
    with drag lies against 45 degrees;
  - *tool affordances* (picture A, the oscillator's position of M4): how many
    periods a hand stopwatch must time for a stated precision; what a ruler
    reads when the mass hangs from the spring at rest on a planet of given g;
  - *counterfactuals* (pictures A and B): the period with the mass changed,
    the period with the amplitude changed (unchanged), the drag-free range at
    45 degrees with the speed changed, the best angle with drag for a ball of
    another mass.
- **Every answer recomputed by the build**, from the code of the lesson it
  comes from (`key`); and **independently checked** where a second route
  exists (`check`): a simulation against each closed form (range, collision,
  amplitude-independence) and a quadrature against the elliptic integral
  (pendulum). A test asserts the two routes agree for every seed. The keys of
  the pictures' items are robust to a reading within five per cent.
- **Pictures** are verified figures, drawn again by their lessons' `draw_`
  functions (as F96); a recording holds none. `RECORDED_KEY` keeps the key at
  recording time and a test compares it with the build's.
- **Tool-use reasoning separated from the software interface.** The one
  software tool is `answer` (an acknowledgement, never a score or truth;
  one answer per item). The physical tools are in the items. The score keeps
  apart interface failures (refused calls, items left without an accepted
  answer) and reasoning failures (an accepted answer that is wrong).
- **Seeds and uncertainty.** Five seeds, one recorded run each; the score per
  seed, its mean, standard deviation, and a 95 per cent Student-t interval
  over seeds, overall and by kind; every failure in a table.
- **Baseline**: uniform guessing in the stated options and ranges (exact
  expectation). The build's own solver is the reference by construction.
- **The agent rule**: one allowlisted bounded tool, a budget of twelve
  accepted calls, versioned prompt and recorded model, frozen replays
  recomputed by the build, the truth unreachable, a non-agent baseline,
  seeds, visible failures, the live run outside `verify.conf`.

## Recording

As in F96 and F98: no provider key, so each seed's run is recorded by a fresh
`claude-opus-5-5` sub-agent in this Claude Code session (owner, 2026-10-29:
Opus for agent lessons other than the named ones), given only the system
prompt, the task, the tool specification, and the two PNG files; the harness
computes every result, relayed to it. The fixtures' `model` field and the
page say so. The keys and the items are fixed before any run.

## Visual deliverables

Scientific figures only, `simulated`; pictures A and B are existing figures
reused unchanged by their `draw_` functions.

Skills: pbc-scientific-visualization@a70b501

- `fig-benchmark-scores` (preview): the fraction correct of each seed by
  kind (points), their mean with the 95 per cent interval (bars), and chance
  (a marker of another shape), with distinct markers per element.
- Validation: the tables print the same numbers; the experiment's tests
  assert them. Fallback: alt text without computed values, and the tables.

## Steps

1. `pbc.agents.reasoning_benchmark` with unit tests (items, key, checks,
   answer sheet, scoring, interface counts, statistics, replay, live main).
2. Record the five runs; commit `replay-seed-<n>.json` next to the page.
3. The experiment, its test, and the page.
4. Docs: authoring "Agent lessons", `docs/project-map.md`.
5. Verification: `./scripts/verify.sh --base` (a new lesson).

## Discoveries during the work

- **Recording.** Five runs on 2026-11-01 by fresh `claude-opus-5-5`
  sub-agents, each given only its prompt file and the two PNG files the
  module's code drew; every message written to a file, every result computed
  by the harness and relayed; no run discarded. Each run used four messages,
  twelve accepted calls, and no refused call.
- **Results, reported as scored.** Fifty-five of sixty items correct; every
  problem in words and every visual affordance correct on every seed. The
  five failures are all of reasoning, all about picture A: one run read its
  period as two pi seconds and carried the misreading into four items, one
  run took the spring constant wrongly for the ruler. No tolerance or item
  was changed after the runs.
- **The interface separation** shows nothing on these runs (no refused
  call); the module's tests check it on a scripted run with refused calls.
- **A second route** exists for six items per seed (range, pendulum,
  equilibrium speed, collision, amplitude-independence, the throw at
  45 degrees); the rest are computed by the lesson's code alone.
