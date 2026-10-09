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
