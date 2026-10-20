# Risk-Based Autonomy

The three levels and the evidence states are defined by ADR 020
(`docs/decisions/020-risk-proportionate-verification-and-review.md`); the
scripts derive the level (`scripts/lib/risk.sh`) and refuse to lower it.

## Level 1: low risk
Documentation and process files only (outside the ADRs and the planning
documents), with no escalation trigger. Self-check + CI may be sufficient.

## Level 2: medium risk
Lessons, `src/`, tests, and scripts that are not Level 3; normal features,
business logic, APIs, non-destructive DB changes. Require independent AI
review by a different model + CI.

## Level 3: high risk
The protected paths of `guardrails.conf` (ADRs, planning documents,
workflows, the gate, digest, selection, base provenance, build and deploy,
skills), or an escalation trigger: a changed or removed published scientific
claim, weakened test strength, security (authentication/authorization,
secrets, IAM, network, external content), verification guarantees,
production data or infrastructure, or dependency selection. Require a full
verification of the final tree, a full independent review made after it,
relevant security evaluation, CI, and the owner's explicit approval of the
exact commit at the merge gate.

## Evidence states
Each acceptance criterion names its gate (`implementation`, `pr_ci`,
`owner_approval`, `post_merge`) and is `met`, `not_met`, `not_applicable`,
or `pending` for a later gate (never for `implementation`). `complete` means
every criterion met.
