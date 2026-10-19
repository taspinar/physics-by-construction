# Architecture Decision Records

Create ADRs only for significant architectural decisions.

Naming convention:

`NNN-short-description.md`

Examples:

- `001-rendering-approach.md`
- `002-authentication-strategy.md`
- `003-database-choice.md`

Suggested format:

```md
# ADR NNN: Decision title

## Status
Accepted

## Context
Why does this decision need to be made?

## Decision
What did we decide?

## Alternatives considered
What alternatives were considered?

## Consequences
What are the positive and negative consequences?
```
Do not create ADRs for trivial implementation details.

## Index

| ADR | Decision |
|---|---|
| [001](001-quarto-static-site-with-build-time-execution.md) | Quarto as the site generator, with build-time execution and MathML equations |
| [002](002-regenerate-artifacts-and-display-by-reference.md) | Regenerate all lesson artifacts on every build and display code by reference |
| [003](003-single-verification-entry-point-and-ci-budget.md) | One verification entry point, one verified artifact, and a fixed CI time budget |
| [004](004-agent-lessons-verified-by-replay.md) | Agent lessons run behind a provider interface with a tool allowlist and are verified by replay |
| [005](005-workflow-self-tests-run-locally-on-workflow-changes.md) | Workflow self-tests have their own file and run locally only when a workflow file changed; amends ADR 003 |
| [006](006-content-drafting-runs-on-the-maintainers-machine.md) | Agent-assisted content drafting runs on the maintainer's machine; CI holds no LLM key |
| [007](007-real-datasets-as-declared-inputs.md) | Real datasets are declared inputs behind a feasibility gate, with small committed samples under a cap and no portal access in builds; extends ADR 002 |
| [008](008-courses-and-methods-over-stable-strands.md) | Courses by subject and cross-cutting methods as metadata facets over the existing strands, whose identifiers and addresses stay |
| [009](009-external-references-outside-verification.md) | Curated external references come from a register with selection evidence; link validity is a maintenance check outside verification |
| [010](010-coding-agent-exercises-on-the-learners-machine.md) | Coding-agent exercises run only on the learner's machine under a sandbox profile; the site verifies the code, never the agent |
| [011](011-lean-exercise-stubs-outside-the-checked-library.md) | Lean exercise stubs live in `lean/Exercises/`, outside the checked library; their solutions are library modules and a check pairs them |
| [012](012-parallel-verification-jobs-behind-one-required-check.md) | Verification runs in parallel CI jobs that each run groups of the same checks, behind one required check that passes only when every job succeeded; supersedes decision 2 of ADR 003 and of ADR 005 |
| [013](013-eight-courses-and-the-reference-curriculum.md) | The eight physics courses are strands with fixed identifiers, the reference curriculum is declared data that lessons fill by slot, the method paths are a facet of the slot, and the prerequisite graph is validated as a graph while previous and next stay a reading route; supersedes decision 4 of ADR 008 |
| [014](014-verification-proportional-to-the-change.md) | A pull request executes and checks the lessons whose input digest changed against the verified result of `main`, which is restored and never committed; a page's navigation and commit are regenerated on every build and a check is reused only from a base the same check produced; `main` verifies everything, in same-machine shards that one assembly turns into the one built site, so that a full run fits the job timeout at 110 lessons; amends ADR 002 and ADR 012 and is the record ADR 003 decision 6 and ADR 012 decision 8 require |
| [015](015-typical-pull-request-budget-of-twenty-minutes.md) | The budget of a typical pull request with warm caches is 20 minutes, with 15 minutes as a non-blocking target; amends the budget row of ADR 003 decision 5, ADR 012 decision 8, and ADR 014 decision 7 |
| [016](016-learners-run-experiments-not-the-site-build.md) | Learners run a lesson's experiment through a declared, tested entry point and are never instructed to rebuild or preview the website; the footer names the activity and keeps its anchor; supersedes the learner-facing reproduction contract of ADR 002 and the setup-page rule of F39 |
| [017](017-incremental-main-from-a-chain-of-verified-bases.md) | Proposed, not accepted: a push to `main` may inherit a lesson's results from a chain of verified bases only with proof of validity for the current commit, fails closed, rebuilds and verifies the site, deploys exactly the verified artifact, and keeps an exceptional full run; states the weaker guarantee for the owner's decision; would supersede ADR 014 decision 11 |
| [018](018-scientific-atelier-asset-classes-and-the-course-atlas.md) | The scientific atelier is scoped CSS, shared templates, and self-hosted fonts on the Quarto baseline; every visual belongs to one of three asset classes (interface artwork, conceptual illustration, scientific result) with its source in the repository, superseding the blanket exclusion of decorative imagery and animation of F44, F64, and F25; the course atlas at the existing path address is generated from the curriculum file, the lesson front matter, and one validated map manifest, with three explicit edge types, planned content never linked or counted, and every lesson reachable without scripts; amends ADR 002 by one declared committed-artifact exemption (a provenance-registered authored interface-artwork SVG under `site/assets/`) and keeps lessons' conceptual illustrations code-drawn as a planning choice; extends ADR 013 |
| [019](019-agent-skills-audited-pinned-and-project-local.md) | Agent skills are audited, pinned, project-local guidance of the development workflow at `.agents/skills/`, never a site, build, or CI dependency and never evidence; each third-party skill has a provenance record; the planner selects, the implementer evidences, the reviewer verifies, and a missing required skill fails visibly; extends ADR 006 and ADR 010 |
| [020](020-risk-proportionate-verification-and-review.md) | Proposed with the change cycle `risk-proportionate-workflow`: three risk levels (the highest of the paths' minimum, the escalation triggers, and the assessment; raised freely, lowered only by the owner), one evidence lifecycle in the completion record (a gate per criterion, `pending` for later gates, `complete` only when every criterion is met), review in proportion to the level (none at Level 1, a traceable chain of delta reviews with the disposition of every finding at Level 2, full every round at Level 3), owner approval verified at the merge gate by GitHub through a second identity that only the owner holds and never from an agent's assertion, intermediate partial runs of a Level 3 change as feedback that is never evidence, budgets as measurements for the owner's decision, and ADR 017 and F113 paused; amends process statements of ADR 002, 003, 005, 012, 014, and 015 and no invariant |
