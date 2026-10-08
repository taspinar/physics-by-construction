# Plan: Issue #31, F12 — Content proposal workflow through GitHub Issues

- Issue: #31 (source: `docs/roadmap.md`, F12)
- Branch: `feature/31-content-proposal-workflow-through`
- Base commit: `6b4a000`
- Risk: Medium (no credential is introduced; the Issue text is untrusted input)
- Written by the implementer: no plan existed when the feature started.

## Human decision (acceptance criterion 3)

Recorded 2026-10-08: no LLM key in CI; agent-assisted drafting runs on the
maintainer's machine. ADR 006 records it; architecture unresolved question 2
is marked settled; I2 holds without exception.

## Design

| Piece | Decision | Reason |
|---|---|---|
| Proposal form | `.github/ISSUE_TEMPLATE/lesson-proposal.yml`, label `lesson-proposal`, one required field per criterion and a required licence confirmation | Criterion 1; the licence terms are applied at submission |
| Criteria and path | `docs/content-proposals.md`: four criteria (fit, prerequisites, verifiability, scope), three outcomes, the maintainer's steps | Criteria 1 and 5 |
| Recording the assessment | A structured comment on the Issue plus one of three labels, by hand | No workflow may react to Issues; automation would be a new attack surface |
| Drafting | The existing `start-feature.sh`, `review-feature.sh`, `triage-review.sh`, `finish-feature.sh`, `publish-feature.sh`, unchanged | Criterion 2; reuse |
| Agent-drafted marker | An `Agent-drafted:` line in the commit message (becomes the PR description), plus a section in the PR template | Criterion 4, without changing a workflow script |
| Licence | `CONTRIBUTING.md` extended to proposals and agent drafts | Scope |
| Enforcement | `tests/integration/test_content_proposals.py`; the existing CI tests already forbid secrets and non-PR/push triggers | Criterion 3 |

## Out of scope

Automatic merging, any workflow, secrets for fork pull requests, automatic
assessment, label creation on GitHub (a manual step).

## Verification evidence

`./scripts/verify.sh` on the working tree at base commit `6b4a000` plus the
uncommitted changes (macOS): all 14 checks passed; the 16 workflow self-tests
were skipped because no workflow file changed (CI runs them). New tests:
`tests/integration/test_content_proposals.py` (7).
