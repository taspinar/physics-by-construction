# Agent Instructions

This repository uses a plan → act → evaluate workflow. Git and GitHub are the system of record.

## Before non-trivial work
1. Read this file and relevant docs/architecture.md and accepted ADRs.
2. Read the GitHub issue and active `.agents/plans/<issue>-*.md`.
3. Inspect the repository; do not rely on stale chat context.
4. Work only in the assigned feature branch/worktree.

## Source precedence
1. Explicit current human instruction
2. Accepted ADRs
3. Current GitHub issue acceptance criteria
4. AGENTS.md
5. Current architecture documentation
6. Active feature plan
7. Handoff documents
8. Previous agent assumptions

If a material conflict remains, stop and report it.

## Definition of Done
- Acceptance criteria are satisfied, and the completion record
  (`.agents/completion/<issue-number>.json`) says so with evidence for each.
  A session that ends is not a finished Issue: work that is not complete is
  recorded as `partial` or `blocked`.
- Evidence states (ADR 020 decision 2): each criterion names the gate that
  clears it (`implementation`, `pr_ci`, `owner_approval`, `post_merge`) and
  is `met`, `not_met`, `not_applicable`, or `pending` for a later gate, never
  for `implementation`. `complete` means every criterion met; a feature whose
  only unmet criteria are pending is ready for a pull request that does not
  close the Issue.
- Risk levels (ADR 020 decision 1): every change carries Level 1
  (documentation and process files), 2 (lessons, source, tests, other
  scripts), or 3 (the protected paths of `.agents/policies/guardrails.conf`,
  or an escalation trigger), the highest of its paths, its triggers, and the
  assessed level. An agent may raise a level and never lowers one; only the
  owner's approving review of the exact head lowers a trigger reading or an
  assessed level. A Level 3 change ends with a full verification, a full
  review made after it, and the owner's approval of the exact commit.
- Tests are added/updated where appropriate.
- The verification tier the change needs passes, run last (ADR 017
  decision 7; `docs/development.md`, "Verification"): `./scripts/verify.sh
  --targeted` for an ordinary change, which computes the selection CI will
  make and builds no site; `./scripts/verify.sh --base` for a change that
  alters what other pages display of a lesson (the front-matter fields of
  the path and the headers, a new lesson); the full `./scripts/verify.sh`
  when the targeted run reports that CI will run everything (a shared input
  or a file of the checks changed). CI builds and validates the site on
  every pull request and push.
- No unrelated changes are included.
- Docs/ADRs are updated when architecture or behavior changed.
- Verification evidence is recorded in the commit message and the pull request, which `finish-feature.sh` and `publish-feature.sh` write.
- Required independent review is complete and no Critical or Major findings
  remain unresolved.
- Required review findings have an approved triage, published on the feature
  Issue by `triage-review.sh`.
- Deferred findings have a linked follow-up Issue; accepted findings have an
  explicit rationale.

## Boundaries
- Never push directly to `main`.
- Never access or mutate production data, secrets, IAM, or production infrastructure without explicit human approval.
- Never broaden the task merely to make implementation easier.
- One writing agent per worktree. Parallel writers require separate worktrees/branches.
- After three materially different failed repair attempts, stop and record the attempts, the evidence, and the next recommended step in the handoff note of the Issue (`.agents/handoffs/<issue-number>.md`).

## Context freshness
When resuming work, check the plan and the handoff note against the current repository state: the files are the truth, the note is a summary. Revalidate assumptions before continuing and update stale artifacts.

## Branch and worktree policy

Agents must not make repository changes directly on `main`.

This applies to:

- application code
- architecture documentation
- roadmap changes
- ADRs
- feature plans
- CI/CD configuration
- infrastructure configuration

Before modifying repository files, work on an appropriate branch.

Examples:

- `planning/project-bootstrap`
- `planning/issue-12-authentication`
- `feature/12-authentication`
- `fix/27-login-error`

For substantial implementation work, prefer a dedicated Git worktree.

If the current branch is `main`, do not modify files before creating or
switching to an appropriate branch.

## Roadmap, Issues and Plans

Use each artifact for its intended purpose:

- `docs/roadmap.md` — project direction and future features
- GitHub Issues — active actionable backlog items
- `.agents/plans/` — detailed technical execution plans

Do not duplicate detailed implementation plans into GitHub Issues.

Do not create separate Issues for every plan step.

Do not assume future roadmap items are still valid without reviewing the current
architecture and roadmap first.

## Visual deliverables and skills

The audited, pinned agent skills are in `.agents/skills/` (ADR 019); its
README lists them and when each is required. They are guidance, never
evidence, and never a dependency of the build or CI.

- **Planner:** classify every new visual deliverable of the feature (page or
  layout, conceptual diagram, scientific figure, animation, or none); name the
  skills it selects on a line `Skills: <name>[@<revision>], ...`, or
  `Skills: none (<reason>)`; state the expected artifact, its scientific
  validation, and its accessible fallback.
- **Implementer:** read `.agents/skills/<name>/SKILL.md` of each selected
  skill, and the files it points to, by path before producing the artifact
  (the runner may not offer it by name); in the completion evidence, name the
  skill and its revision beside the artifact and its source, and explain any
  exception.
- **Reviewer:** read the same files by path; assess the rendered page or the
  generated figure and its source, not the self-report; check that the
  guidance was followed or an exception approved.
- Use no skill that is not in `.agents/skills/`, run none of a skill's
  scripts, and install or fetch none. A missing selected skill stops the
  feature (`skills-config` in `scripts/verify.conf`); it is never omitted
  silently.
