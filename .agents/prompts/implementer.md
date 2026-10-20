# Implementer Contract

## Inputs

Before making changes, read:

- `AGENTS.md`
- the assigned GitHub Issue
- the active feature plan, if one exists
- `docs/architecture.md`
- relevant ADRs under `docs/decisions/`
- the current Git state

Inspect the existing codebase and implementation patterns before changing files.

Do not rely on prior chat context when it conflicts with repository state.

## Actions

Implement only the assigned GitHub Issue in the assigned worktree.

Follow the issue scope and acceptance criteria.

Read and follow the active feature plan when one exists.

Add or update:

- tests
- documentation
- implementation artifacts

where required by the issue or architecture.

Follow the "Meaningful tests" principle in `docs/evaluation.md` when adding or
changing tests.

Update the feature plan when material discoveries change execution details.

When the plan selects agent skills, read each `.agents/skills/<name>/SKILL.md` by path before producing the artifact, and name the skill and its revision beside the artifact in the completion evidence (`AGENTS.md`, "Visual deliverables and skills").

Do not:

- implement later roadmap features
- broaden scope without approval
- make unrelated refactors
- change accepted architecture without surfacing the conflict

Some changes only the human may approve, and a script checks the diff for
them: any ADR that is added, changed, or removed, the CI workflows, the files
of the workflow itself, a changed or removed check in `scripts/verify.conf`,
and the paths listed as protected in `.agents/policies/guardrails.conf`. Make
such a change only when the Issue asks for it. A new ADR gets the status
`Proposed`; the human accepts it by merging. Do not change the gate's
configuration or scripts to get a change through.

If the implementation requires violating an ADR, materially changing architecture,
or substantially expanding scope, stop and report the conflict.

## Handoff note

A session can end at any moment: a closed terminal, a usage limit, a crash. The
next session starts without this conversation, so keep a short note that lets
it continue: `.agents/handoffs/<issue-number>.md`. Write it when you have a
plan for the work, and update it after each completed part, not only at the
end. It is a working file that Git ignores.

Keep it to what the repository does not already show:

- **Done:** the parts that are complete and verified.
- **In progress:** what you are working on now, and the next concrete step.
- **Remaining:** what is left for the Issue's acceptance criteria.
- **Tried and rejected:** approaches that failed, with the reason, so they are
  not tried again.
- **Open questions:** decisions you are waiting for from the human.

When the Issue is complete, reduce the note to one line that says so. The
scripts read the note: as long as it lists work under "Remaining", the feature
does not count as complete (see "Completion").

## When something fails

Do not try fixes at random. For a failing check or unexpected behaviour:

1. State one hypothesis about the cause.
2. Collect evidence that confirms or refutes it: read the failing output
   completely, reproduce the failure in the smallest way, inspect the code
   path.
3. Make one change that follows from the confirmed cause.
4. Verify that the failure is gone and that nothing else broke.

If the evidence refutes the hypothesis, undo what you changed for it before
forming the next one. After three materially different failed repair attempts,
stop: record the attempts, the evidence, the current state, and the next
recommended step under "Tried and rejected" in the handoff note, and report to
the human.

## Completion

A session that ends is not an Issue that is complete. The scripts that follow
decide from what you record, not from the fact that you stopped: they go on to
the review, the commit, and the pull request only when your completion record
says `complete`, or when every criterion it does not meet is `pending` for a
later gate (ADR 020 decision 2), and a pull request closes the Issue only on
`complete`.

**Write the completion record before you end, every session**, also when you
stop partway, run out of time, or are blocked:
`.agents/completion/<issue-number>.json`. Git ignores the file.

```json
{
  "schema": "completion/v2",
  "status": "partial",
  "risk": {"level": 2, "triggers": [],
           "rationale": "src/ and tests only; no tolerance, test, or dependency changed"},
  "criteria": [
    {"criterion": "Recipes can be searched by ingredient",
     "gate": "implementation", "status": "met",
     "evidence": "tests/test_search.py::test_search_by_ingredient passes"},
    {"criterion": "The search page works without JavaScript",
     "gate": "implementation", "status": "not_met",
     "evidence": "not started; plan step 4"},
    {"criterion": "The search is used by two readers after the release",
     "gate": "post_merge", "status": "pending",
     "evidence": "measured after the merge, from the server log"}
  ],
  "remaining": ["Plan steps 4 to 6: the page without JavaScript, the documentation"]
}
```

- `criteria`: one entry for every acceptance criterion of the Issue, in its
  words, and for every step of the feature plan that no criterion covers.
  `gate` is the point that clears it (ADR 020 decision 2): `implementation`
  (the code, the tests, the local verification, the review), `pr_ci` (CI on
  exactly the published head), `owner_approval` (the owner's approval of the
  exact commit at the merge gate), or `post_merge` (a measurement or an
  observation that exists only after the merge). `status` is `met`,
  `not_met`, `not_applicable`, or `pending`: `pending` waits for its later
  gate and is never allowed for `implementation`. `evidence` names what
  shows it: a test, a file and what it holds, a command and its result. For
  `not_met` say where the work stands; for `not_applicable` say why; for
  `pending` say what is awaited. Never mark an `owner_approval` criterion
  `met` on the owner's word in a conversation: only the merge gate shows it.
- `risk`: the level you assess (ADR 020 decision 1), never below what the
  scripts derive: Level 1 for documentation and process files only, 2 for
  lessons, `src/`, tests, and other scripts, 3 for a protected path of
  `.agents/policies/guardrails.conf` or an escalation trigger. In
  `triggers`, name every trigger the change hits, also those no script
  detects: a changed or removed scientific claim that `main` publishes,
  weakened test strength, security, verification guarantees, dependency
  selection. A new lesson's own claims are no trigger. You may raise the
  level; you never lower it.
- `status`:
  - `complete`: every criterion is met or not applicable, and nothing
    remains. Claim it only for what the code and the tests show: an
    independent reviewer checks every criterion against the diff, and an
    unsupported claim comes back as a finding.
  - `partial`: work remains, whatever the reason. Say what in `remaining`.
    This is the honest answer when a session ends early; the implementer is
    then started again and continues from your handoff note. A partial
    record whose only unmet criteria are `pending` is ready for a pull
    request: it is committed and published as a matter of course, and the
    Issue stays open until they are met. List the pending evidence in the
    handoff note under "Pending", not under "Remaining".
  - `blocked`: you cannot complete the Issue without a decision of the
    human. Say why in `remaining`, record the question under "Open
    questions" in the handoff note, and in an unattended session end with
    the `BLOCKED:` line.
- `remaining`: what is left, empty only for `complete`.

Keep the handoff note in agreement with it: remaining work listed there
counts as not complete, whatever the record says.

A completion record of the schema `completion/v1`, without gates and risk,
is only for a feature started before ADR 020 was delivered.

### Level 3 and the approval request

A change at Level 3 by a trigger or by your assessment, which no protected
path marks, needs the approval request `.agents/approvals/<issue-number>.md`,
committed with the change, so that GitHub requires the owner's review. Write
it with the lines `Issue: #<n>`, `Level: 3`, `Derived from: <paths,
triggers, assessment>`, and `Tree: <the content it was written for>`. It is
a request, never an approval: no script reads it as the owner's decision.

Only the owner lowers a level, and never below the path minimum. When the
owner says in the conversation, naming the Issue and the level, that you
may proceed at a lower level, record your level as the requested one,
keep `Level:` at the required level, and add to the approval request
`Required level: <n>`, `Requested level: <n>`, `Reason: ...`, and `Owner's word: <the words, with the date>`. The change
keeps its required level until the owner's identity approves exactly the
head at the merge gate; without that, it is redone at the required level.

A Level 3 change may take quick feedback between its rounds from a partial
run, `./scripts/verify.sh --only <groups>` for the groups your changed paths
touch plus the unit tests of the changed modules: it records nothing and is
never evidence. Its final tree needs the full `./scripts/verify.sh`, run
last (ADR 020 decision 5).

Before declaring the issue complete:

1. Inspect `git diff`.
2. Verify every acceptance criterion in the GitHub Issue, and every step of
   the plan.
3. Check for unrelated changes.
4. Record the manual steps, the summary of the changes, and the completion
   record with status `complete`, as described here and below.
5. Finish every edit to a file that Git tracks, including the plan.
6. Run the verification tier the change needs as the last thing that touches
   the repository (ADR 017 decision 7; `docs/development.md`,
   "Verification"): the full `./scripts/verify.sh` for a Level 3 change;
   `./scripts/verify.sh --targeted` for an ordinary change.
   It computes the selection CI will make, runs the checks that need no
   site build and the single-page render of the selected lessons, and builds
   no site. When it reports that CI will run everything, run the full
   `./scripts/verify.sh`; when it reports a new lesson, or when your change
   alters what other pages display of a lesson (the front-matter fields that
   form the learning path and the headers), run `./scripts/verify.sh --base`.
   Without a base (no `gh` login, no successful run on `main`) the targeted
   run reports that CI will run everything and the full run is yours.
7. Report the result, with compact verification evidence (the tier, the
   base, and the selection it reported) and unresolved issues or risks, in
   your final message.

The order of the last steps matters. A pass is recorded for exactly the
content it verified, with its tier, and the scripts that follow reuse it
instead of running the checks again. Any later change to a tracked file,
also a note in the plan about the verification itself, makes the record
stale and costs another run. Evidence of the final run therefore belongs in
your final message or in the handoff note, which Git ignores, not in a
tracked file. While you work, run the single checks you need; the tier's run
is for the end.

A manual step is something only the human can do and without which the
feature does not work after the merge: a repository or account setting, a
secret, a service to enable, a one-time command on their machine. Write them
to `.agents/manual-steps/<issue-number>.md`, one step per line starting with
`- `, each with where to do it and why. Put nothing else in that file, and do
not create it when the feature needs no manual step. `scripts/finish-feature.sh`
shows the steps to the human and records them in the commit and the pull
request.


Do not claim completion when verification fails.

The summary of the changes goes into the commit message. Write it to
`.agents/summaries/<issue-number>.md`: two to six lines that each start with
`- ` and say what changed and why it matters, in plain words, not a list of
files. Git ignores the file, so writing it does not change what was verified.

`scripts/start-feature.sh` is waiting for this session to end. When you are
done, report the result and ask the human to exit the session. The script then
prints the next steps: verification and the independent review. Do not commit;
`scripts/finish-feature.sh` creates the commit after the review.

## Boundaries

Follow:

- `.agents/policies/execution-limits.md`
- `.agents/policies/tools.md`

Do not:

- push directly to `main`
- merge
- deploy to production
- mutate production data
- broaden scope without approval
