# Plan: F138 — The instrument contract and the simulator vertical slice of the Autonomous Physics Lab, Issue #360

- Issue: #360 (source: `docs/roadmap.md`, F138); "Detailed implementation
  plan expected: yes".
- Branch: `feature/360-the-instrument-contract-and`; base `683a8b3`.
- Written by the implementer: no plan existed when the feature started.
- Gates: F137 (`pbc.evidence`), F78 (`pbc.electromagnetism.circuits`, the
  RLC model of EM5), F09 (the harness of ADR 004) delivered.

## Risk

Level 3 (ADR 020 decision 1), by its paths and its triggers:

- protected paths: `.github/workflows/ci.yml` (the code job's checkout with
  the repository's history), `scripts/verify.conf` (a new check, the
  starter checks), `docs/architecture.md` (the gap line);
- triggers: `pyproject.toml` and `uv.lock` (the optional group
  `physics-lab`, dependency selection), the committed-artifact check
  (`tests/support/lesson_checks.py`, a verification guarantee), and the
  instrument safety boundary (security, I34).

An approval request `.agents/approvals/360.md` goes with the change. The
final tree gets the full `./scripts/verify.sh`, run last, and a full review
after it; intermediate rounds use `./scripts/verify.sh --only code` and the
unit tests of the new modules (never evidence).

Gates of the criteria: 1 to 8 `implementation`; the CI run of the at-pin
check with the repository's history on exactly the published head is
`pr_ci` evidence beside criterion 8; criterion 9 `implementation`. The first
pin bump is a follow-up change after the merge (recorded, not done here).

## Visual deliverables

- Page and layout: the thin local interface of the product (outside the
  site; one server-rendered HTML page from the standard library). Skills:
  frontend-design@dbd4588f. Validation: rendered by a test from the
  handler without binding a socket; accessible fallback: the same content
  as plain HTML without script, the export files (CSV, Markdown report).
- Scientific figure: the frequency response (gain and phase against
  frequency, measured points with the closed form of the model drawn apart)
  in the report. Skills: pbc-scientific-visualization (digest of its
  `PROVENANCE.yaml`, a70b5016). Validation: the closed form of
  `SeriesRLC.capacitor_phasor`; the alternative text and the report's
  table carry the same information.
- `Skills: frontend-design@dbd4588f, pbc-scientific-visualization@a70b5016`

## Design

`pbc.instruments` (the layer between callers and a device):

- `contract.py`: `Limit` (a quantity with its unit and inclusive range),
  `Envelope` (the permitted ranges of the excitation amplitude and
  frequency and of the acquisition rate and length, an interlock list,
  the operation timeout), the `Driver` protocol (what an adapter
  implements: `identity`, `set_output`, `output_off`, `capture`), and
  `Instrument`, the one object a caller gets: it validates every
  operation against the envelope and the interlocks before the driver is
  called, runs the driver call under the timeout (on expiry: output off,
  the instrument faulted, the call refused), honours a stop request (output
  off, every later operation refused), and gives a state snapshot. The run
  record `InstrumentRun` names the execution mode, the device or model, the
  calibration, the configuration, the timestamps, the units, and the
  processing; a recorded run is labelled "recorded data, not a new
  experiment" and cannot be marked as a new experiment.
- `simulated.py`: the bench over `SeriesRLC` (EM5's L and C, R = 100 ohm):
  a source V cos(2 pi f t) switched on from rest, integrated with
  `circuits.simulate` through a settling time, sampled on two channels
  (source, capacitor voltage) with seeded Gaussian noise.
- `recorded.py`: a declared sample (a JSON file with its declaration:
  dataset, origin `measured` or `simulated`, units, provenance) replayed
  capture by capture; a request that is not in the sample is refused, never
  computed. EM8's RLC data has no granted gate, so the slice uses a
  synthetic sample written from the simulated bench and declared
  `simulated`; it is regenerated from its seed and never committed (I6).
- No live adapter (F140). The fake live driver that records every call is
  a test helper (`tests/unit/test_instruments.py`).

`pbc.products.physics_lab` (the product slice):

- `protocol.py`: the frequency-response protocol: one point = excite at
  (f, V), acquire whole periods after settling, read the phasors of both
  channels (`circuits.steady_phasor`), gain and phase of V_C / V_S; the
  analysis of a sweep (the resonance where the phase crosses -90 degrees,
  Q as the gain there); the evaluator's independent check against the
  closed form (f0 = 1/(2 pi sqrt(LC)), Q = sqrt(L/C)/R) within a stated
  tolerance, recomputed from the raw samples.
- `baseline.py`: the scripted route: a log-spaced coarse sweep and a
  refinement around the phase crossing.
- `agent.py`: the bounded agent route in the ADR 004 harness: the
  allowlist holds `measure(frequency_hz, amplitude_v)` and nothing else,
  its bounds the envelope's, a budget of measurements; every call goes
  through `Instrument`, which validates again. Replay from
  `products/physics-lab/fixtures/` re-executes every call on a fresh bench
  with the same seed. The recordings of the slice are placeholders written
  by a deterministic scripted client (`placeholder: true`, model named as
  not a model); a live recording is optional (`--provider`, extra
  `physics-lab`).
- `workflow.py`: one run: route, mode, seed, the instrument run record, the
  evidence ledger (`pbc.evidence`): the attempt with its raw-data artifact,
  the evaluator's evaluation recomputed from the raw samples, the agent's
  final message as an unverified candidate report, a claim with its
  status.
- `export.py`: raw samples (`raw.csv`), points (`points.csv`), the report
  (`report.md`, `frequency-response.svg`), `run.json`, `evidence.json`.
- `interface.py`: the thin local interface (question 21): standard-library
  `http.server` bound to 127.0.0.1 only; a pure `handle(method, path,
  form)` renders configuration, progress, results, and failures, testable
  without a socket.
- `__main__.py`: `python -m pbc.products.physics_lab run|serve|record`.

`pbc.products.starters`: the starter checks of ADR 022 decision 5 for every
`products/*/starter/`: the current-tree check (its tests against the
working tree) and the at-pin check (the pinned commit's `src/` taken from
the repository's own history by `git archive`, no fetch, put first on the
path; a full hash that is a commit in the history of HEAD; a `pending` pin
skipped and the skip named).

`products/physics-lab/`: `README.md` (the brief, the scientific acceptance
criteria, the run command, the limits), `examples/frequency-response.toml`,
`fixtures/` (the replay traces of the product's and the starter's agent
route), `starter/` (pin `pending`, already-verified components imported
from `pbc`, marked places for the learner's work, its tests).

## Steps

1. `pbc.instruments` with tests (fake driver recording every call): AC2,
   AC4.
2. `pbc.products.physics_lab` with tests: AC1, AC3, AC4.
3. `products/physics-lab/` material, the fixtures, the starter, and
   `pbc.products.starters` with tests (temporary repositories): AC7, AC8.
4. The committed-artifact check: `products/` becomes a checked tree, its
   only exempt recordings are `products/<product>/fixtures/*.json`; tests
   for accepted there and rejected elsewhere: AC7.
5. The boundary test of I32 and I24 extended to products and drivers: AC5.
6. The optional group `physics-lab` in `pyproject.toml`, `uv.lock` (offline
   lock): question 19.
7. `scripts/verify.conf` gets the check `starters [code]`; the code job of
   `ci.yml` checks out with `fetch-depth: 0`; a CI workflow test: AC8.
8. Documentation: `docs/products.md` (the contract, the slice, the decision
   record for questions 19 and 21 with go or no-go, cost, and limits, the
   follow-up pin bump); `docs/project-map.md`; the gap line of
   `docs/architecture.md`: AC6.
9. Approval request; full `./scripts/verify.sh`, run last: AC9.

## Limits of the slice (pilot)

No model call, no network, no instrument, no new dependency outside the
optional group. Compute: one reference run (19 points) under 10 s on the
maintainer's machine; the new tests together under 60 s. Time: one
implementation session; exhausting it ends with a partial record.

## Discoveries during the work

- Q as the gain interpolated between the two bracketing points
  underestimates Q when the bracket is wide (the agent's 9 % bracket gave
  3.04 against 3.16); Q now comes from the second-order response at the two
  points, averaged (within 0.1 % on both routes).
- A stopped baseline lost the points it had measured; the workflow now
  collects them as they come and exports them with the failed run.
- `socket` and `subprocess` are imported by the scientific stack itself, so
  the boundary test scans the imports of the new modules statically and
  checks at run time only for provider, driver, and server modules.
- The local uv (0.9.4) writes `revision = 3` in `uv.lock`; the header is
  kept at `revision = 5`, so the lock changes only by the lines of the
  extra.
- The recorded mode answers only the settings of its sample; the synthetic
  sample is made from the baseline's settings, so the agent route in the
  recorded mode is refused (documented in the product's README and
  `docs/products.md`).
- No model is reachable here: the committed traces were written by a
  deterministic scripted policy and are marked as placeholders.
- `docs/development.md` lists the new check and the widened
  committed-artifact rule.
