# Plan: Issue #87, F16 — Counterexample hunter

- Issue: #87 (source: `docs/roadmap.md`, F16)
- Branch: `feature/87-counterexample-hunter`
- Risk: Medium
- Governing documents: ADR 004 (harness, replay), ADR 002 (replay fixture),
  `docs/validation-contract.md` (what a verdict means), `docs/authoring.md`
  (claim types)
- Written by the implementer: no plan existed when the feature started.

## Design

| Piece | Where | Decision |
|---|---|---|
| Claim | `pbc.agents.hunter.FalsifiableClaim` | Statement, domain (fixed choices, bounded numbers), predicate "result at most limit", budget. An experiment outside the domain is not evidence |
| Verdict | `pbc.agents.hunter.judge` | Runs each accepted experiment of the domain again from its arguments; never reads the agent's text or the stored results. First recomputed violation is the witness: `numerically-verified`. Otherwise `inconclusive`, with no claim type. A non-finite value is not evidence (validation contract, rule 5) |
| Budget | `Allowlist(..., budget=n)` | Counts calls that pass validation; a call beyond it is refused unexecuted. A fresh allowlist has a fresh budget, so replay is deterministic |
| Allowlist | `pbc.agents.hunter_lab.tools` | One function: largest energy drift of the course's oscillator for one of the four integrators, with `steps_per_period` 4 to 200 and `periods` 1 to 50 (at most 10 000 steps per call), budget 8. New `Choice` argument for the method: a value outside the list is rejected |
| Claims | `FALSE_CLAIM`, `OPEN_CLAIM` | Symplectic Euler within 5 per cent (false: 5.16 per cent at 64 steps per period); velocity Verlet within 4 per cent (no counterexample in the box: 3.855 per cent at 16 steps per period). Limits fixed before recording |
| Lesson | `site/lessons/agents-llm/02-a-counterexample-hunter/` | Format 1, two fixtures `replay-false.json` and `replay-open.json`; the layout check accepts `replay-<name>.json` |

## Decision recorded: the two fixtures

No live provider key was available in the unattended session. As for lesson A1
(see plan 24), the fixtures are authored examples, not recorded model runs: Claude
(`claude-sonnet-5-5`) wrote the messages in a Claude Code session after
looking at the tool results, the harness computed the results, and the page
labels them as authored examples (`RunDisplay(..., authored=True)`; review
01, M1). The human has not yet accepted these fixtures; they
can be replaced with `--claim <name> --record`.

## Verification

- `tests/unit/test_agents_hunter.py`: the allowlist boundary of the new tool
  (names, types, bounds, extra and missing arguments, budget), the domain, the
  verdict (prose ignored, stored results ignored, outside the domain, budget,
  non-finite), the display, replay of both fixtures.
- `tests/integration/test_agent_replay.py`: both hunts replay with network
  forbidden and no key; fixtures hold no credential; the lesson holds only its
  page and fixtures.
- `tests/unit/test_agents_boundary.py` already scans every module of
  `src/pbc/agents/`, including the two new ones.
- `./scripts/verify.sh`: see the handoff note for the result.

## Discoveries during implementation

- The lesson-layout check allowed only `replay.json`; it now also allows
  `replay-<name>.json` (`tests/support/lesson_checks.py`, with a test).
- The template test counted the path-page links of prerequisites into
  mechanics; the new lesson also lists a mechanics lesson as related, so the
  count includes related lessons.
- The theme keeps inline code on one line; a verdict or run with a full tool
  call widened the page on a 320 px screen. `site/assets/site.css` lets code
  inside `.agent-run` and `.verdict` wrap.
