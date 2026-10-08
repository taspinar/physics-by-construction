# ADR 006: Content drafting runs on the maintainer's machine

## Status

Accepted. The project owner decided this during F12 planning (Issue #31),
settling unresolved question 2 of the requirements.

Date: 2026-10-08

## Context

F12 lets contributors propose lessons and lets an agent help draft the
accepted ones. An agent needs an LLM credential. It could run in GitHub
Actions with the key stored as a repository secret, or on the maintainer's
machine. Workflows that react to Issues or to fork pull requests take
untrusted text as input, and a key in them is a common source of exposure and
of cost abuse. Invariant I2 says CI holds no LLM credentials.

## Decision

1. No LLM key is stored in CI. Agent-assisted drafting runs only on the
   maintainer's machine, through the existing feature scripts and the
   provider in `.agents/agents.conf`.
2. No workflow references a secret or triggers on Issues. The existing test
   on `.github/workflows/` enforces both, and a new workflow needs its own
   review.
3. Proposals are assessed by the maintainer against written criteria
   (`docs/content-proposals.md`). The outcome is a comment on the Issue.
4. Content reaches `main` only through a reviewed pull request that passes
   `./scripts/verify.sh`. Agent-drafted content is marked as such in its
   pull request.

## Alternatives considered

- **A key as a repository secret, with a drafting workflow.** Faster for
  contributors, but it needs a threat model for Issue text as prompt input,
  cost limits, and isolation from fork pull requests. Not needed for the
  expected volume of proposals.

## Consequences

- I2 holds without exception; no threat model for secrets in CI is needed.
- Drafting depends on the maintainer starting it, so the path is slower.
- Reversing this needs a new ADR that supersedes this one and records the
  threat model.
