# Plan: F81 — Interactive discovery benchmarks and non-agent baselines (Issue #295)

- Issue: #295 (source: `docs/roadmap.md`, F81). Slots EV2 and EV3 of the
  benchmarking path.
- Branch: `feature/295-interactive-discovery-benchmarks-and`; base `79c58cf`.
- Written by the implementer: no plan existed when the feature started.

## Design

Two format 2 lessons in `agents-llm` with `course: mechanics`, methods
`simulation` and `llm-agents`, on `pbc.discovery` and the frozen runs of F66.

| Dir | Id | Slot | Content |
|---|---|---|---|
| `11-interactive-discovery-benchmarks` | `interactive-discovery-benchmarks` | EV2 | Three environments (projectile, oscillator, central force) times three conditions (full, partial, none): nine frozen runs, one protocol per environment, every score recomputed; the readings of each run fitted; the baselines of each environment at the same budget; the comparability check of the comparisons a reader might make |
| `12-agent-versus-non-agent-baselines` | `agent-versus-non-agent-baselines` | EV3 | On the same three protocols: the agent (the partial runs), a plain model (the same task, no `measure` tool), random selection with least squares, grid with least squares, grid with sparse identification (symbolic fitting); budgets stated; the comparability check on every row |

- **Subjects.** The oscillator runs of D2 (`06-prior-knowledge-in-discovery`)
  and the central-force run of D1 (`05-discovering-a-force-law`) are reused
  as cells of the grid: same protocol objects (`force_lab.PROTOCOLS`), read
  from their own directories (path constants, so the input digest of the new
  lessons covers them). New runs: the projectile under three conditions and
  the central force under `full` and `none` (EV2 directory), and the plain
  model on the three environments (EV3 directory).
- **New protocol.** `f81-projectile-1`: projectile, budget 20, step limit 12,
  seed 0, tolerance 0.05, as the F66 protocols. Its world (the judge's
  configuration, never on a page) is fixed in `pbc.discovery.benchmark`
  before any run is recorded.
- **Module `pbc.discovery.benchmark`**: the benchmark grid (environment and
  condition to protocol, run, fixture directory), the runs of F81 with their
  `TraceInfo`, the plain-model allowlist (only `submit`) and prompts, the
  replay of any cell, and `comparable`: the reasons two scored entries may
  not be compared (another environment, another hidden world, other held-out
  settings, another tolerance, another budget of probes), computed from the
  protocols, never typed. A live `main()` with `--record` as in `force_lab`.
  `force_lab.replay_run` is split so the replay of an entry is shared.
  The held-out settings enter the protocol (`Protocol.held_out`, the
  environment's own when `None`; `Protocol.held_out_settings`) so that
  `comparable` reads them (review 02, M1).
- **Comparisons that are not meaningful** are stated on the page by the
  check: across environments (EV2), against a run of another hidden world
  (the D3 run), the plain model (no probes: the comparison measures the
  tools and the probes together), and a baseline given a different budget
  (EV3).
- **No live call in CI.** Pages replay; a test runs every replay with the
  network refused and no key.

## Recording

As in F66 (plan of #189, "Recording"): no provider key is available, so the
eight new runs are recorded by a Claude model in a Claude Code session, a
fresh sub-agent per run given only the system prompt, the task, and the tool
specifications; the harness computes every result. The fixtures' `model`
field and the pages say so.

## Visual deliverables

Scientific figures only, no page layout, diagram, or animation.

Skills: pbc-scientific-visualization@a70b501

- EV2: held-out error of every run (log scale), grouped by environment, one
  marker per condition, with the tolerance; the fits to each run's readings
  beside them. EV3: held-out error of every method on each environment (log
  scale) with the tolerance; methods told apart by marker and position.
- Validation: the experiments' tests assert the scores the build recomputes
  and the comparability verdicts; the module's unit tests check the check.
- Fallback: alt text describing every figure; every number also in a table.

## Discoveries during the work

- **Fixture names.** The committed-files check allows `replay-[a-z]+.json`
  only, so the fixtures are `replay-projectilefull.json`, ...,
  `replay-plaincentral.json`; the run names in `RUNS` keep their hyphens.
- **The input digest cannot follow a dictionary of paths.** A `HOMES` dict of
  the lesson directories made the lesson's inputs unfollowable (a full run);
  the experiments return each path constant by name (`home(cell)`), and the
  digest then covers the fixtures of D1, D2, and D3 that the pages replay.
- **Scoring with the run's tools.** `score_transcript` takes the run's tools
  (default `environment_allowlist`), so a plain model's `measure` call would
  be refused in the score as in the run; `force_lab.replay_run` is split into
  `replay_entry`. D1 to D3 are unchanged in behaviour.
- **Recording.** Eight runs on 2026-10-26, `claude-sonnet-5-5` sub-agents.
  The first round asked for "your reasoning" in the text field and every
  request was refused by the provider's safeguards (`reasoning_extraction`);
  the wording became "a short note to the experimenter". A retry handed back
  a summary instead of the JSON message and was discarded. Then all eight ran
  to the end. The pages state both.
- **Results, reported as scored.** Seven of nine grid runs recover (the
  partial and none runs on the spring do not, as in D2); every run's readings
  support a recovery. Five claims score exactly zero because the agents
  rounded onto round hidden values (projectile gravity, central force); the
  pages state this as a limit of the benchmark's design. The plain model
  misses all three; the baselines with the full budget recover where they
  make a claim (sparse identification has no terms for the spring).
- **Architecture.** `docs/architecture.md` is a protected path; this feature
  does not edit it. The new module is listed in `docs/project-map.md`.

## Steps

1. `pbc.discovery.benchmark`, the `force_lab` split, unit tests.
2. Record the eight runs; commit the fixtures and the `TraceInfo` records.
3. The two experiments with their tests; the two pages.
4. Docs: authoring "Discovery lessons", `docs/discovery-protocol.md`
   (comparability, the plain model), `docs/project-map.md`.
5. Verification: `./scripts/verify.sh --base` (new lessons).
