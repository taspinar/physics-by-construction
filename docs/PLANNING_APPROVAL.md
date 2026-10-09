# Planning Approval

Status: Approved
Approved at: 2026-10-06T11:12:01Z
Planning branch: planning/project-bootstrap
Final review: round 2, PASS, by codex (gpt-6-astra)
Planning fingerprint: 68d194761d3e0b67a8749ea66f72c50be091dc6d

Recorded by `scripts/finish-planning.sh`. The approval covers these planning
documents; any change to them invalidates it (`./scripts/finish-planning.sh --check`):

- `docs/PROJECT_DESCRIPTION.md`
- `docs/PROJECT_REQUIREMENTS.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/decisions`

## Review rounds

- Round 1: CHANGES REQUIRED, 4 finding(s), by codex (gpt-6-astra)
- Round 2: PASS, 0 finding(s), by codex (gpt-6-astra)

## Findings that were not adopted

None.

## Amendments after the approval

- 2026-10-06: ADR 005 (workflow self-tests run locally only when workflow
  files change), with the matching changes to ADR 003, the ADR index, and
  `docs/architecture.md`. Approved by the project owner with the merge of its
  pull request, without an independent planning review round. The planning
  fingerprint above was updated by hand to the documents including this
  amendment; the review rounds listed in this file cover the planning before
  it.
- 2026-10-07: decision 4 of ADR 005 rewritten. The guarded files are now
  defined by `scripts/verify-workflow.conf` instead of listed in the ADR, and
  a file that no self-test reads may be excluded there. Approved by the
  project owner with the merge of its pull request, without an independent
  planning review round; the fingerprint above was updated by hand again.
- 2026-10-09: the architecture as the features F07, F08, and F12 left it.
  F07 added what the widget tests check to `docs/architecture.md`, F08 the
  build record and the anchored proof regions of a Lean lesson, and F12 ADR
  006 (content drafting runs on the maintainer's machine; no LLM key in CI)
  with its lines in the architecture and the ADR index. Each change was
  reviewed in the review rounds of its feature and merged with its pull
  request, but not in a planning review round. Approved by the project owner
  with the merge of this pull request; the fingerprint above was updated by
  hand to the documents as they are on `main`.
