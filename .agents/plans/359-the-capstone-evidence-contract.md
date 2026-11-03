# Plan: F137 — The capstone evidence contract and the final-evaluation pilot on one existing task, Issue #359

- Issue: #359 (source: `docs/roadmap.md`, F137); "Detailed implementation
  plan expected: yes, short, with the pilot's compute and time limits".
- Branch: `feature/359-the-capstone-evidence-contract`; base `edb7bd7`.
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 2 (a new package `src/pbc/evidence/`, its tests, and
  documentation). No published lesson imports the package, so no page's
  output changes; no tolerance, check, test assertion, or dependency
  changes; no protected path. Verification: `./scripts/verify.sh
  --targeted`.
- Gates: F65 (the protocol and frozen traces), F81 (the benchmark of EV2
  and EV3), F20 (replay, ADR 004) delivered.
- Visual deliverables: none (a library and a document).
  Skills: none (no visual deliverable).

## The pilot task

The agent-versus-baseline task of EV3 on the projectile environment
(`pbc.discovery.benchmark`, protocol `f81-projectile-1`): find the hidden
gravity from at most 20 noisy range probes, scored on the held-out settings
of the protocol. The candidates are the committed frozen runs
`projectile-full` (the agent told the form, fixture on the EV2 page) and
`plain-projectile` (the plain model without a `measure` tool, fixture on the
EV3 page), and the evaluator-run baseline `grid + least squares`. The pilot
reuses `benchmark.replay_cell` (replay of ADR 004 with the recorded tool
results recomputed) and `score_transcript` (the existing judge); it reads
the fixtures where the pages hold them and writes nothing there. Tests copy
fixtures to a temporary directory before changing them.

**Limits.** No model call, no network, no new recording. Compute: one
replay per evaluated attempt (each well under one second) and one baseline
fit; the pilot's tests together within 10 s of wall time on the
maintainer's machine. Time: one implementation session.

## Design: `pbc.evidence`

- `records.py`: digests (SHA-256 of a file, of canonical JSON); the
  `RunRecord` (task, hypothesis, assumptions, protocol version, split
  description, seeds, budgets, code and configuration identities,
  environment); `Artifact` (a path with its digest when recorded, raw or
  derived); `Attempt` (candidate, cycle, status `completed`, `failed`,
  `inconclusive`, `invalid`, `missing`, diagnostics, artifacts, prior
  attempts); `Evaluation` (evaluator-computed correctness, metrics, and
  resource use, with the artifacts it depended on); `CandidateReport`
  (what the candidate says, labelled unverified, stored apart); `Claim`
  (text, scope, runs with the correctness each asserts, sources); the
  `FrozenCandidate` (digest over its artifacts, version, cycle) and the
  `FinalEvaluation` (bound to that digest and version, the evaluator's
  version, the isolation assumptions). The `Ledger` holds them, refuses
  what the contract forbids (a second final evaluation of a candidate in a
  cycle, a final evaluation of a changed candidate, an attempt of a
  finally evaluated candidate in the same cycle), and records a new cycle
  with its reason. `check` re-digests every artifact an evaluation depended
  on and returns the invalidations; `claim_status` derives each claim's
  evidence status (completed, failed, inconclusive, not evaluated,
  independently checked); `summary` counts every attempt status, keeps
  every attempt in the denominator, and renders as text. JSON save and
  load, with a format number.
- `pilot.py`: the EV3 projectile task as a `RunRecord`; evaluating a
  candidate fixture by replay into an attempt and an evaluation; the
  candidate's own report (its last message, its cost record) as an
  unverified report; the baseline as an evaluator-run attempt; freezing and
  the final evaluation.

## Steps

1. `pbc.evidence` (records, ledger, check, claim status, summary,
   persistence) with unit tests.
2. The pilot on the EV3 task with tests: a fabricated high score fails
   (AC1), a changed artifact invalidates (AC2), every outcome stays visible
   (AC3), final evaluation bound to digest and version and a new cycle
   after a change (AC4).
3. Docs: the contract as the section "The evidence contract" of
   `docs/discovery-protocol.md` with the pilot's isolation assumptions
   (AC5) and the go or no-go decision record (AC6); `docs/project-map.md`
   registers `src/pbc/evidence/`; the gap line of `docs/architecture.md`.
4. Verification: `./scripts/verify.sh --targeted`.

## Discoveries during the work
