# Building a feature of the lab: the routes

How you build one feature of your Autonomous Physics Lab from the starter:
by hand (the manual route, the default), or with a coding agent (the
guided routes, optional). The routes were piloted once, on one feature, in
F139 (Issue #613, 2026-11-24 and 2026-11-25); what they cost is recorded
below with the pilot's limits, and nothing more is promised.

## The feature: the ring-down fit

The transient-response protocol drives the circuit with a step and fits
the ring-down of the capacitor voltage. Your work is the body of
`fit_ringdown` in `starter/my_lab/ringdown.py`: from one recorded step
response, the decay rate and the damped frequency with their standard
errors, and from them f0 and Q. What it must do, what it may not know, and
what it must refuse is in `starter/SPECIFICATION.md`; the twelve provided
tests are `starter/tests/test_ringdown.py`. Neither the specification, the
tests, the dataclass `RingdownFit`, nor the signature is yours to change.

While `fit_ringdown` still raises `NotImplementedError`, the provided
tests are skipped with the reason "YOUR WORK"; as soon as it does not,
they run unchanged. The feature is done when all of them pass:

```bash
uv run pytest tests/test_ringdown.py
```

## The manual route (the default)

No coding agent and no model account.

1. Copy the starter and install it, as in `starter/README.md`
   ("Copy it"): `cp -R`, the trace into `fixtures/`, `uv sync`,
   `uv run pytest`. The starter's own tests pass and the twelve ring-down
   tests are skipped.
2. Read `SPECIFICATION.md`: the model, the assumptions, the interface,
   the units, the claim, and the refusals.
3. Write the body of `fit_ringdown`. The pilot's fit took starting values
   from the record's spectrum and a coarse search of the decay rate (the
   model is linear in v_inf, a, and b once alpha and omega_d are fixed),
   fitted all five parameters with `scipy.optimize.curve_fit`, propagated
   the standard errors of f0 and Q from the covariance of alpha and
   omega_d, and refused what the specification lists with `ValueError`.
4. Run the provided tests until they pass:
   `uv run pytest tests/test_ringdown.py`, then `uv run pytest` for all.

**The pilot's run.** All twelve provided tests and the starter's own
passed on the first run; about 110 lines; the tests take about 1 s. It was
written by a model, so its time (under a minute) says nothing about a
learner's.

## A coding agent, without a workflow template (lighter, optional)

A coding agent on your own machine under the sandbox profile, the budget,
and the review of `docs/coding-agent-workflow.md` in the repository of
Physics by Construction (ADR 010). Give it `SPECIFICATION.md` as its task;
its allowlist holds reading, editing, and the test command. Review what
it wrote with the rubric of that document before you keep it; the provided
tests are evidence that it works on those cases, not that it is right.

**The pilot's run.** Claude Code with Opus, non-interactive, in a scratch
copy of the starter: all twelve provided tests and the starter's own, in
164 s of its 30 minutes and 18 of its 40 turns, inside a subscription (no
per-call billing); 253 lines, tests about 20 s. It listed its assumptions
and what it tried beyond the tests. It also wrote a probe script one
directory above the scratch copy with its file tool, which an allowlist
of commands does not limit: confine the agent's file tool to the working
directory as well, or run it in a container. This route gives no planning
record and no independent review; you are its reviewer.

## The guided route with Agent Codeyard (optional)

Agent Codeyard (`taspinar/agent-codeyard`, formerly the Agentic Coding
Template) is a plan, act, and evaluate workflow for a whole project: a
planning interview, reviewed plans, a feature cycle with an independent
review, and pull requests. **The pinned revision is the commit
`df5430aa` of `taspinar/agent-codeyard`.** Only the commands below ran in
the pilot, at that commit; for their arguments and the steps around them,
follow the template's README at that commit, not a later one.

Its conditions, from the pilot:

- **Accounts with two providers.** The feature review refuses a reviewer
  of the implementer's provider. With one provider for every role the
  cycle stops before its first review.
- **About two hours of active time for one small function**, a lower
  bound: the person who ran it knew the workflow and made the setup.
- **The planning makes the work larger than the task.** In the pilot one
  function with given tests became a feature of nine criteria (an ADR,
  24 further tests, a measurement script, and the replacement of the
  template's own text).
- **The given tests wait outside `tests/`** of your project until the
  feature moves them into place unchanged: `main` must stay green, and the
  provided tests fail until the fit exists. The pilot kept the three task
  files in `task/` and put the starter at the repository root, with its
  `uv.lock` and `fixtures/starter-agent.json`.

The commands that ran, in order, in a private repository created from the
template:

1. The README's steps before the first run, then `./scripts/doctor.sh`.
2. `./scripts/start-planning.sh` (interactive: you hold the planning
   interview at a terminal), `./scripts/review-planning.sh`,
   `./scripts/revise-planning.sh`, `./scripts/finish-planning.sh`.
3. `./scripts/create-feature-issue.sh F01`.
4. `./scripts/run-feature.sh <issue>`. In the pilot it reached an open
   pull request only with a reviewer of a second provider, chosen for the
   run with `AGENT_CONFIG_FILE=<roles file> ./scripts/run-feature.sh <issue>`.

**The pilot's run.** Setup 7 minutes, planning 54 minutes (four review
rounds), feature cycle 59 minutes to the limit: the implementation passed
the twelve provided tests, the starter's own, and the 24 tests the planning
added after about 35 minutes, and the first review was refused (same
provider) and retried for 14 minutes. Within the two hours no pull
request was open. Run on after the limit with a reviewer of a second
provider, as a separate observation: 13 more minutes to an open pull
request, about 109 minutes of active time in all, 745 added lines in 18
files, the fit 307 lines. Inside a subscription; no per-call billing.

**Go or no-go.** A narrower go (the owner, 2026-11-25): the route is
optional, the manual route is the default, and no workload is promised from
it. The gaps the pilot found are proposed work for Agent Codeyard,
recorded on Issue #613; nothing here depends on that repository.

## What Path 1 costs: an estimate from one pilot

An estimate from one pilot, not a measurement of a learner: no learner was
timed. The pilot shows the size of one feature of Path 1: one function of
about 110 to 300 lines against a written specification and twelve given
tests, which a model finished by hand, and a coding agent under the
workflow document, in minutes, and which the full Codeyard workflow took
about two hours of active time to bring to a reviewed pull request. How
long a learner needs for it is not known from this pilot; the workload of
the path stays an open question of the planning (question 22), the
owner's.
