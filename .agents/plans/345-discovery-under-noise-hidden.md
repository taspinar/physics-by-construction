# Plan: F98 — Discovery under noise, hidden variables, and generalisation (D10, D11, D12), Issue #345

- Issue: #345 (source: `docs/roadmap.md`, F98); "Detailed implementation
  plan expected: yes, short".
- Branch: `feature/345-discovery-under-noise-hidden`; base `c94c045`.
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 3 by trigger (raised after review 03): the path minimum is
  Level 2 (three lessons, three new modules of `src/pbc/discovery`, three
  experiments, tests, docs), but publishing D10 to D12 completes the
  law-discovery path, and the existing assertion of
  `tests/unit/test_home.py` that every method path shows its planned count
  is made conditional on the path having planned lessons (a complete path
  shows none; a new test asserts that). That is the trigger "assertion
  removed or changed" (weakened test strength), assessed by the review. The
  change therefore needs the full `./scripts/verify.sh`, a full review after
  it, and the owner's approval of the exact commit; the approval request is
  the file 345.md of .agents/approvals. No tolerance, budget, check, or dependency
  changes; a new lesson's own claims are no trigger.
- Gates: F61, F62, F64, F113 (the gates of this phase), F66 (the protocol's
  force environments and run records), F81 (the benchmark and baselines)
  delivered.

## Design

Three format 2 lessons in `agents-llm`, `course: mechanics`, methods
`simulation` and `llm-agents`, each with one recorded run, the baselines
without a model, and the score recomputed by the build from the tool calls.
Each lesson's module holds its environment, protocol, run record, replay,
and analysis (one module per lesson, since each environment needs a judge
of its own and must stay out of `environment.ENVIRONMENTS`, which the F65 and
F81 tests parametrise over).

| Dir | Id | Slot | Module |
|---|---|---|---|
| `18-discovery-under-noise` | `discovery-under-noise` | D10 | `pbc.discovery.noise_lab` |
| `19-hidden-variables` | `hidden-variables` | D11 | `pbc.discovery.latent_lab` |
| `20-generalisation-to-unseen-systems` | `generalisation-to-unseen-systems` | D12 | `pbc.discovery.generalisation_lab` |

### D10: a faulty gauge

- **The gauge** (`FaultyGaugeEnvironment`): the central force
  `strength mass distance^-exponent`, read by a gauge with Gaussian noise of
  a set standard deviation, a hidden zero offset, and a hidden fraction of
  faulty readings (a large deviation fixed by the seed and the setting, so a
  repeated probe repeats it). The mass may be set to zero: the null reading
  is the calibration. A claim is the strength and the exponent; it is scored
  on the noise-free force (no offset) at distances beyond the bounds.
- **Agent rules**: `measure` and `submit` (`environment_allowlist`);
  condition `partial`, and the task adds one sentence: the gauge may read
  with an offset and some readings may be faulty. Budget 24, step limit 12,
  tolerance 0.05.
- **Baselines**: least squares of the family and sparse identification (on
  the grid and random settings), and a calibrated robust fit (the family
  plus an offset, a soft-L1 loss, readings beyond four standard deviations
  of it dropped, and a weighted refit judged by the chi-square rule).
- **Degradation under noise** (the acceptance criterion): every baseline at
  six noise levels over five seeds, the held-out error and the success
  measured at each; and a failure analysis at the lesson's noise: Gaussian
  noise alone, with the offset, with the faulty readings, and with both.

### D11: hidden forces and unobserved variables

- **The fall** (`HiddenForceEnvironment`): a body of set mass released from
  rest; the distance fallen at a set time is read with noise. The body feels
  gravity, a hidden constant force against the fall, and hidden linear drag:
  `distance = (a/k) (t − (1 − e^{−kt})/k)` with `a = g − F/m`, `k = b/m`. The
  claim is `g`, `hidden_force`, `drag`; it is scored at masses and times
  outside the bounds.
- **Agent rules**: `measure` and `submit`; condition `full` (the form is
  told), and the task adds: the body may feel forces it cannot see; an
  effect found absent is reported as zero. Budget 16, step limit 12,
  tolerance 0.05.
- **Ambiguity and the disambiguating experiment** (the page): an
  observational record at one mass and short times, fitted by four
  hypotheses (free fall, a hidden force, drag, both): every one consistent
  with the noise, their held-out errors far apart, and the family not
  identifiable. The disambiguating setting is the one where the hypotheses
  consistent with the record disagree most, in standard deviations of the
  noise; with readings there, only the true hypothesis survives.
- **Baselines**: least squares of the family (grid, random), sparse
  identification over terms in the time and the inverse mass, and the
  familiar law (free fall, `g` only), which the chi-square rejects.

### D12: generalisation to unseen systems

- **The force** (`ShortRangeForceEnvironment`): the central force
  `strength mass distance^-exponent` plus a hidden short-range term
  `c mass e^{−r/λ}` that lies below the noise everywhere within the bounds.
- **The suite of held-out worlds**, none in a tool or on a page: unprobed
  settings within the bounds (interpolation), distances beyond them
  (settings), test masses far outside them (conditions), periods of circular
  orbits under the force (another system, a force model), and distances
  below the bounds, where the short-range term matters (beyond the data).
  The claim is recovered when the largest error of the first four is within
  the tolerance; the fifth is reported apart and fails every claim, agent and
  baselines alike.
- **Agent rules**: `measure` and `submit`; condition `partial`, the task of
  `pbc.discovery.prompts`. Budget 20, step limit 12, tolerance 0.05.
- **Never probed, shown by the trace** (the acceptance criterion): a table
  of the nearest accepted probe of the trace to each held-out world, in units
  of the controls' ranges, and a test that every probe of the fixture lies in
  the bounds and none on a held-out setting.

## Recording

As in F66, F81, F82, F99: no provider key is available, so each run is
recorded by a Claude model in this Claude Code session: a fresh sub-agent
per run, given only the system prompt, the task, and the tool
specifications, which reads the results the harness computed from a file
and answers with its next message. The fixtures' `model` field and the pages
say so; a maintainer may replace them with `--record`. Per the owner
(2026-10-29), Opus, not Fable, for the law-discovery lessons. The hidden
values have three significant figures and are not round, fixed before any
run.

## Visual deliverables

Scientific figures only, `simulated`, drawn by `draw_` functions of the
experiments from the tested code, colours from `FIGURE_COLOURS` with marker
or line style as well, alt text without computed values.

Skills: pbc-scientific-visualization@a70b501

- D10 `fig-degradation` (preview): the median held-out error (log scale) of
  each baseline against the noise's standard deviation (log scale), one
  colour, line style and marker per method, the random settings dotted with
  open markers, the tolerance as a line.
- D11 `fig-disambiguation` (preview): the largest disagreement of the
  hypotheses consistent with the observational record, in standard
  deviations of the noise, against the mass, one line per time; the chosen
  setting marked.
- D12 `fig-generalisation` (preview): the error of each claim (agent and
  baselines) in each held-out world, grouped bars with hatching per claim,
  log scale, the tolerance as a line. No held-out setting is drawn.
- Validation: the tables of the same pages print the quantities and the
  experiments' tests assert them. Fallback: the alt text and the tables.

## Steps

1. The three modules with unit tests (environment, judge, protocol, run
   record, replay, analysis, live main).
2. Record the three runs; commit `replay.json` next to each page.
3. The three experiments, their tests, and the three pages.
4. Docs: `docs/discovery-protocol.md` (noise, latent effects,
   generalisation), the authoring guide's "Discovery lessons",
   `docs/project-map.md`.
5. Verification: `./scripts/verify.sh --base` (new lessons).

## Discoveries during the work

- **Recording.** All three runs on 2026-10-30 by fresh `claude-opus-5-5`
  sub-agents that wrote each message to a file and read each result from the
  file the harness wrote; no result was copied by hand. D10: eight messages,
  twenty-five calls, recovered; the agent calibrated with two null readings,
  named as faulty exactly the two faulty settings among its readings (one
  probed twice), and its claim is less accurate than the calibrated robust
  fit to the same readings, since its offset came from the two null readings
  alone. D11: six messages, seventeen calls, recovered; its first four probes
  were the two extreme masses at two times. D12: six messages, seventeen
  calls, recovered; every probe within the bounds and on no held-out setting.
- **Repeated probes.** Every agent found that a repeated probe returns the
  same reading (noise fixed per setting, as in F65) and spent one to four
  probes learning it.
- **The degradation's least squares.** On the faulty gauge, plain least
  squares passes the chi-square rule on some seeds at the largest noise:
  there the faults are hidden in the scatter. The page says so; no threshold
  was changed for it.
- **The `range` keyword** of the short-range term shadowed the built-in and
  was renamed `length` before any run.
