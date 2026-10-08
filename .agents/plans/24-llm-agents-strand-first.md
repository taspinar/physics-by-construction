# Plan: Issue #24, F09 — LLM agents strand: first agent-driven experiment lesson

- Issue: #24 (source: `docs/roadmap.md`, F09)
- Branch: `feature/24-llm-agents-strand-first`
- Base commit: `a1690fb`
- Risk: High (credentials; model-directed actions)
- Governing documents: ADR 004 (harness, replay), ADR 002 (replay fixture),
  `docs/architecture.md` (invariants I2, I6), `docs/authoring.md`
- Written by the implementer: no plan existed when the feature started.

## Decision recorded: default provider

**OpenAI**, decided by the human on 2026-10-08 in answer to the implementer's
question (unresolved question 1 of the requirements). The model name
(`MODEL` in `src/pbc/agents/clients/openai.py`) is a configuration value to
confirm before the live recording. The planning documents (requirements,
architecture, ADR 004) still call the question unresolved: they are covered by
`docs/PLANNING_APPROVAL.md`, so they were not edited here (manual step).

## Decision recorded: the recorded run

**Accepted by the human on 2026-10-08**, in answer to the implementer's
question: the committed `replay.json` is a run by Claude (`claude-sonnet-5-5`)
in a Claude Code session, not a run through the OpenAI client. The OpenAI
account had no credit. This accepts the fixture for acceptance criterion 8 and
leaves the manual check of the live OpenAI client (ADR 004) undone. An OpenAI
recording may replace the fixture later with `--record`.

## Design

`src/pbc/agents/`:

| Module | Contents |
|---|---|
| `messages.py` | Plain data (`ToolCall`, `ModelMessage`, `ToolResult`, `ToolSpec`) and the `ModelClient` protocol, the only provider-facing surface |
| `tools.py` | `Parameter` (bounded number), `Tool`, `Allowlist.dispatch`: validation, then execution |
| `loop.py` | `run`: step limit, at most 4 calls per message, transcript |
| `replay.py` | `Recording` (the fixture), `ReplayClient`, `replay` (recompute and compare), `save_recording`, `load_recording` (strict schema) |
| `secrets.py` | `Secret` (never prints), `redact` |
| `providers.py` | `PROVIDER`, `load_client`: the one configuration value |
| `clients/openai.py` | Live client; request/response functions tested without the SDK; SDK imported lazily; optional extra `openai` |
| `display.py` | `RunDisplay`, `AllowlistDisplay` for the page |
| `projectile_lab.py` | Lesson A1: system prompt, task, allowlist, tolerance, live entry point with `--record` |

Lesson A1: `site/lessons/agents-llm/01-an-agent-runs-an-experiment/` with
`index.qmd` and `replay.json`. The agent finds the best launch angle of the
tennis ball of M3.

## Allowlist boundary (for the human to approve)

Two tools only, both functions of `pbc.mechanics.projectile`:

- `range_with_drag(speed 1..50 m/s, angle 1..89 deg, dt 0.001..0.05 s)`; the
  ball (mass, drag constant) is fixed in lesson code;
- `range_without_drag(speed 1..50, angle 1..89)`.

Arguments must be exactly the declared ones, finite numbers (booleans and
strings refused) within the bounds. The lower bound on `dt` bounds the cost of
one call. The loop stops after 12 model messages and refuses calls beyond 4 per
message. No tool reads or writes a file, starts a process, or uses the network.

## Decisions

| Decision | Reason |
|---|---|
| Fixture holds recorded results; the page shows recomputed ones | ADR 004. The replay compares with a relative and absolute tolerance of 1e-6; a refusal is compared by accepted/rejected only, not wording |
| The replay also fails when task or system prompt differ from the recording | A recording of another question must not be shown under this one |
| Model text is shown only inside a fenced block | Model output is untrusted; it cannot become markup |
| Chat completions API, SDK imported lazily | Stable, simple request shape; the build and tests never need the SDK |
| The committed `replay.json` is a recorded run by Claude (`claude-sonnet-5-5`) in a Claude Code session, accepted by the human for acceptance criterion 8 (see "Decision recorded: the recorded run") | The model chose the tool calls and the harness computed the results; the fixture's `model` field states the provenance and the page prints it. It replaced an earlier hand-written placeholder (flagged `"placeholder": true`) on 2026-10-08. The live OpenAI client check (ADR 004, verified manually by the maintainer) remains undone: the OpenAI account had no credit |
| A check refuses a placeholder fixture in the published lesson (review 01, M1) | `tests/integration/test_agent_replay.py` fails, and with it `./scripts/verify.sh`, if the fixture is flagged as a placeholder or its `model` field says so. The check passes on the accepted recording; the placeholder flag and the visible notice stay in the code for any future placeholder |
| The loop removes the client's secrets from every model message before it is kept (review 01, M2); the client exposes them as `secrets`, and the entry point reads no key variable itself (M3); SDK set-up errors are redacted like request errors (M4) | Acceptance criterion 5: the key must reach no transcript, and criterion 7: switching provider must need only the new client and `PROVIDER` |
| Not done: edits to requirements, architecture, ADR 004 | Covered by the planning approval |

## Verification

- Unit tests: `tests/unit/test_agents_{tools,replay,secrets,openai,boundary}.py`
  (criteria 2, 3, 4, 5, 7).
- `tests/integration/test_agent_replay.py`: replay with network calls
  forbidden and no key; no credential in the fixture; no workflow references
  an LLM secret (criterion 6).
- `tests/e2e/test_built_site.py`: the built site names no LLM provider host.
- `./scripts/verify.sh`: see "Evidence".

## Evidence

`./scripts/verify.sh` passed on 2026-10-08 (base `a1690fb`, uncommitted
changes): 298 unit tests, 195 integration tests, 7 lesson-source checks, 78
built-site checks (including the WCAG scan and the determinism build).

Discoveries during implementation: the excerpt check reads only regular
modules, so provider selection lives in `src/pbc/agents/providers.py`, not in
a package `__init__.py`; the allowlist is shown as a list, not a table, to
avoid a scroll region on a phone; the template test counted path-page links
for mechanics lessons only and now counts every prerequisite link into
mechanics.

Criterion 8 (recorded run): `replay.json` was replaced on 2026-10-08 by a run
in which Claude (`claude-sonnet-5-5`, in a Claude Code session, not through the
provider API) chose the tool calls and the harness computed the results. The
fixture's `model` field says so and the page prints it. The human accepted this
fixture for criterion 8 on 2026-10-08 (see "Decision recorded: the recorded
run"). `./scripts/verify.sh` passes on it.

Still undone, and separate from that acceptance: the manual end-to-end check of
the live OpenAI client that ADR 004 assigns to the maintainer. The attempt
failed with `insufficient_quota` (no credit). The step, with the `--record`
command that would also produce an OpenAI recording to replace the fixture, is
in `.agents/manual-steps/24.md`.
