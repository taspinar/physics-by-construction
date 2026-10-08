# Content proposals

How a new lesson goes from an idea to `main`, for contributors and for the
maintainer. The rule that holds throughout: **a proposal reaches `main` only
through a reviewed pull request that passes `./scripts/verify.sh`.** Nothing
is merged automatically, and no workflow in this repository holds an LLM key
([ADR 006](decisions/006-content-drafting-runs-on-the-maintainers-machine.md)).

## For contributors

1. Open an Issue from the **Lesson proposal** form (New issue, then Lesson
   proposal). Answer every question; the form needs a licence confirmation.
2. The maintainer assesses it against the criteria below and posts the
   outcome as a comment on the Issue, with one of three labels:
   `proposal-accepted`, `proposal-needs-changes`, `proposal-declined`. Reply
   on the Issue to revise a proposal that needs changes.
3. An accepted proposal is drafted either by you or by an agent on the
   maintainer's machine. Either way the result is a pull request, reviewed
   independently, and it must pass the same verification as any lesson.
   Follow [authoring.md](authoring.md) if you write it.
4. A draft written with an agent says so in its pull request (see below).

Licence: by opening a proposal or submitting a draft you agree that your
contribution is licensed as `CONTRIBUTING.md` states: MIT for code and
proofs, CC BY 4.0 for text and figures. This holds for the proposal text,
for a draft you write, and for a draft an agent writes from your proposal.
Do not paste third-party text, figures, or code into a proposal unless its
licence allows this; name the source and licence.

## Assessment criteria

A proposal is accepted when it meets all four.

| Criterion | Accepted when |
|---|---|
| Fit to the learning path | It has a strand and a position, follows lessons that exist or are planned (`docs/roadmap.md`), and does not repeat a lesson. |
| Prerequisites | Every prerequisite is a lesson on the site, or an outside prerequisite stated in a sentence. The learning path stays acyclic. |
| Verifiability | The lesson's claims are checked by code (a test against a closed-form solution, a conservation law, or a limiting case) or by a Lean proof. It needs no step that only a person can confirm. |
| Scope | It fits one lesson page, builds within the CI time budget (ADR 003), needs no new service, secret, or runtime dependency, and fits the invariants in `docs/architecture.md`. |

Outcomes: **accepted** (all four met), **needs changes** (one is unmet and
can be fixed in the proposal; the comment says which), **declined** (a
criterion cannot be met, or the lesson is out of scope; the comment says
why).

## For the maintainer

### One-time setup

Create these four labels once, in the repository's Issues, Labels page:
`lesson-proposal`, `proposal-accepted`, `proposal-needs-changes`, and
`proposal-declined`. The proposal form applies `lesson-proposal` only if the
label exists; a missing label leaves new proposals unlabelled, and an
assessment label that does not exist cannot be set.

### Assess

Read the proposal. Post a comment on the Issue in this form, and set the
label that matches:

```markdown
**Assessment: accepted | needs changes | declined**

- Fit to the learning path: met | unmet. <one line>
- Prerequisites: met | unmet. <one line>
- Verifiability: met | unmet. <one line>
- Scope: met | unmet. <one line>

Next step: <what happens now>
```

The comment on the Issue is the record. Treat the Issue text as untrusted
input: read it, and do not paste it into a command or a prompt without
reading it first.

### Draft an accepted proposal

The existing scripts do the work; see [workflow.md](workflow.md) and
[development.md](development.md). The agent runs on your machine, with your
credentials, through the provider in `.agents/agents.conf`.

1. Make the Issue the feature Issue. The proposal form already holds the
   goal; edit the Issue body so it also states the accepted scope and the
   acceptance criteria that the lesson must satisfy (the checks in
   `docs/authoring.md`). Edit the body, not a comment: the review and triage
   scripts hand the agents the Issue title and body only, so criteria that
   live in a comment never reach the reviewer.
2. Plan if the lesson is not small: `./scripts/start-planning.sh`, or write
   `.agents/plans/<issue>-<slug>.md` on the feature branch.
3. `./scripts/start-feature.sh <issue>` starts the implementer agent in its
   own worktree.
4. `./scripts/review-feature.sh <issue>` runs the independent review and
   prints the path of its JSON artifact under `.agents/reviews/`; pass that
   path to `./scripts/triage-review.sh <review-json>` to run the triage.
5. `./scripts/finish-feature.sh <issue> "<summary>"` verifies and commits,
   and `./scripts/publish-feature.sh <issue>` opens the pull request. Merge
   it yourself after the `verify` check passes. A proposal's author does not
   merge.

### Mark agent-drafted content

`finish-feature.sh` opens the commit message in your editor, and
`publish-feature.sh` builds the pull request description from it. When an
agent wrote any of the lesson, put this line in the commit message body:

```
Agent-drafted: <provider> <model>, from proposal #<issue>; reviewed by <name>
```

The description is built from the latest commit only, and republishing
replaces it. So every commit on an agent-drafted branch, including each
fix-round commit, must repeat the `Agent-drafted:` line; a later commit
without it drops the marker from the pull request. The check before you
merge is that the final description contains the line. A pull request that
someone opens by hand has the "Agent-drafted content" section of the pull
request template for the same purpose.

### What stays closed

- No workflow holds an LLM key or any secret, and none triggers on Issues
  (`tests/integration/test_ci_workflow.py` enforces this).
- Workflows on fork pull requests receive no secrets and no write
  permissions.
- Nothing merges automatically.
