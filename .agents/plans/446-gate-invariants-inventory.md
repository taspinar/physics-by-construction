# Plan: scientific invariants versus administrative conventions in the gates (Issue #446)

Source: Issue #446 (the inventory for #396 point 6), the owner's decisions on
#396 (2026-11-07 "ja" on point 6; 2026-11-09 "point 6 started"), ADR 020
decision 1 as amended by #412 (the addendum of 2026-11-08), the inventory of
#399 (its comment of 2026-11-07), the measurements on #236 (the pilot of ADR
020 decision 10, 2026-11-08) and #389 (the durations and the 21 majors,
2026-11-06), and the tree of `origin/main` at `d64bc1d` (2026-11-09).

Skills: none (no visual deliverable: an inventory, counts, and a proposal).

Level: 1 (this plan and the Issue text; no file outside the plan changes).

Status: the inventory is complete and the proposal is written out and not
applied. Every item under "Proposal" is marked with a decision number
(D1 to D12) for the owner; nothing changes before the owner decides. The
same text is the comment of 2026-11-09 on Issue #446.

## Method

Read: `.agents/policies/guardrails.conf` and the built-in list of
`scripts/lib/guardrails.sh` (the protected and sensitive paths, the rule for
the check lists), `scripts/lib/risk.sh` (the path minimum, the detected
triggers, the readings of the record and the review), ADR 020 decision 1 with
the addenda of #383 and #412, `docs/process.md` ("Risk levels"),
`tests/risk-level-test.sh` and `tests/guardrails-test.sh` (what pins the
lists), `.github/CODEOWNERS`, `scripts/lib/planning.sh` (the planning gate),
and the readers of each protected file (which script sources, executes or
reads it; `grep` over `scripts/`, `src/`, `tests/`).

Counted: every first-parent commit of `origin/main` (217 commits, one per
merged pull request or direct commit, 2026-10-06 to 2026-11-09), each
compared with its first parent: the changed files, the findings of
`guardrails_classify` under today's rules (the rules read from `origin/main`
as it is now, so every count is "under the list as it stands"), and the
triggers `risk_triggers` detects on the diff. "The last 100 commits of
`main`" below are the last 100 of these; "all" is the 217. The count differs
from the table of #396 (which counted every commit, also those inside
merged branches) and from #399 (216 commits without merges).

The recorded level of a commit (the line `required: level N, by the X` that
`finish-feature.sh` writes) survives in only 18 of the last 100 commit
messages (7 Level 2 by paths, 6 Level 3 by paths, 5 Level 3 by triggers);
the squash merges of the early-draft pull requests carry the pull request
body instead. The share below is therefore derived again from the diff with
the scripts' own functions, not read from the messages. What it cannot
count: the triggers an agent or a reviewer named (a changed scientific
claim, security, verification guarantees) and the assessed level; those
only raise the share, so every Level 3 share below is a lower bound.

Form versus substance of a commit was judged from its subject, its files and
its diffstat on the protected paths (listed in the scratch data; the
judgement is mine and is marked "judged"). Where the review or the owner
caught a fault, the evidence is the heading of the finding in the published
round on the Issue (`Independent review and triage — round N`).

Checked, as the Issue asks: `docs/roadmap.md` says nothing about point 6
(its lines on the list describe F130's list); the comments on #396 of
2026-11-07 to 09 still say what this plan relies on (point 6 "ja"; point 2
dropped; points 1, 3, 5 delivered by #412; point 6 started as #446).

## The three classes

- **Scientific invariant**: a silent weakening can make a verification, a
  review or an approval pass that should fail, or can change what is
  verified: the claims and their evidence, the tolerances and budgets, the
  reproduction, the digest and the selection, the base and its provenance,
  the build, the gate scripts that decide or record, the review chain, the
  identity of the reviewer.
- **Administrative convention**: the form of a record, an approval request,
  a handoff note, the order or wording of fields, a convenience script whose
  wrong result a gate would catch, a document that states a rule the scripts
  enforce elsewhere.
- **Both**: a path whose content holds items of both kinds (the ADRs; the
  reviewer contract, which states what the reviewer checks and also how it
  reads the records).

## Inventory A: the protected paths of `guardrails.conf`

Columns: class; evidence (who reads it); the history under today's rules
(commits in the last 100 that touched it; of those, how many touched no other
protected path, "only"; how many were form only, judged); where a review or
the owner caught a fault in it.

| Path (line of `guardrails.conf`) | Class | Evidence | Last 100: touched / only / form-only (judged) | Faults caught |
|---|---|---|---|---|
| `docs/decisions` (the ADRs) | both | No script reads them; they are the authority the scripts implement (ADR 020 decision 1 names the list "directly and authoritatively"); the planning gate fingerprints them (`scripts/lib/planning.sh`, `PLANNING_SCOPE`). | 16 / 3 / 6: the six are dated status lines and notes of a decision taken elsewhere (`6ab0550` status lines pointing to `docs/process.md`; `0b345d9`, `f86cd65`, `3e21eb3` capacity notes on ADR 014; `36e9d3b` a note; `edb7bd7` a re-approval). The other ten add or change a decision (ADR 007 addendum `73c89b7`, the budget addendum `db9ef96`, the #412 addendum `d64bc1d`, five planning changes, ADR 017 and the digest note). | Review: #383 R2 M3 and R3 M1 (accepted decisions still stated the 30-second budget: substance, a published scientific statement). Owner: kept in any case (#396). |
| `docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md` | administrative (product governance) | `scripts/lib/planning.sh` `PLANNING_PRODUCT_SCOPE`: `finish-feature.sh` (about line 166) refuses a feature that changes them, so a script already guards them; `tests/lessons` read the roadmap rows (the curriculum test). Nothing scientific is decided there. | 6 / 0 / 1 (`db9ef96` synchronised one sentence). Always together with an ADR (a planning change). | None in the rounds read. Owner: kept in any case (#396). |
| `.github/workflows`, `.github/CODEOWNERS` | scientific | CI is the complete gate (`ci.yml`: every job runs `./scripts/verify.sh --all --only <group>`; `ci-aggregate.sh` is the one required check; the deploy job; the token permissions, invariant I15); `CODEOWNERS` is the lock of mechanism A (`merge-feature.sh` reads it, lines 208 to 211). | 4 / 0 / 0; three of the four raise the build timeout (a wall-clock budget: a measurement for the owner, ADR 020 decision 6), one adds a job step (F138). `CODEOWNERS`: 0. | #236 R1 M1 (the merge gate accepted any code owner as the identity: substance). Owner: kept in any case. |
| `:(glob)scripts/*-feature.sh` | both | Gate-critical by #399: `review-feature.sh` (makes the review artifact and records the verification it ran), `finish-feature.sh` (the commit gate), `merge-feature.sh` (the merge gate). Convenience by #399: `start-feature.sh`, `run-feature.sh` (every step decides for itself), `publish-feature.sh` (one caveat: it alone decides whether the pull request closes the Issue). | 9 / 0 / 4 (with `scripts/lib` below: 14 distinct commits, 5 form only: `2c15273`, `c8bf632`, `8b6ebd5`, `0183a47`, `3558d72`, all about the records: the `Tree:` line, the triage of an earlier round, the review input). The other nine change what is verified or reviewed (`d64bc1d`, `ee86477`, `3ffbd23`, `90d181e`, `91d3917`, `77d481d`, `5d0359c`, `2d0d84a`, `3a83ab6`). | #236 R3 M1, R4 M2, R5 M2 (the merge gate: pending owner approval, forgeable commit lines, the assessed level: substance); #389 R1 M1, R2 M1 and the owner's outside review of PR #415 (three majors: substance). Owner: the gate scripts kept in any case; point 2 (narrowing to the gate scripts) dropped on 2026-11-07 because it buys little (#399 Finding 2). |
| `:(glob)scripts/*-planning.sh` | administrative (the planning gate) | `finish-planning.sh` and `review-planning.sh` decide the planning approval (`docs/PLANNING_APPROVAL.md`); `start-planning.sh`, `revise-planning.sh` are convenience (#399). Nothing scientific: a weakening lets a plan be approved without its review. | 0 / 0 / 0 (all history: 8 / 1). | None. |
| `scripts/lib` | both | Gate-critical (#399): `guardrails.sh`, `risk.sh`, `fingerprint.sh`, `completion.sh`, `verification.sh`, `review-data.sh`, `review-run.sh`, `review-chain.sh`, `agent.sh`, `planning.sh`. Convenience: `scope.sh`, `prerequisites.sh`, `github.sh`, `check_browser.py`, `check_links.py`. | 12 / 2 / (see the row above). The two "only" commits are corrections of the trigger detector (`5d0359c`, `77d481d`: substance). | #236 R2 M1, R5 M1 (the approval request's level unchecked; added tolerances undetected: substance in `risk.sh`); #389 R1 M1 (the unattended marker in `review-data.sh`: substance). |
| `scripts/check-guardrails.sh`, `scripts/check-review.sh` | administrative | Reporting faces: no gate reads their output; the gates call the libraries themselves (#399). `tests/risk-level-test.sh` runs `check-guardrails.sh`. | 0 / 0 / 0 (all: 3 / 0). | None. |
| `scripts/ci-aggregate.sh` | scientific | The one required check `verify` (`ci.yml` lines 239 to 251): passes only when every named job succeeded and no other job was needed. | 0 (all: 1). | None. |
| `.agents/prompts/reviewer.md` | both | The reviewer contract: what the independent reviewer checks (claims, triggers, criteria) and how it reads the records (`Tree:`, what the scripts write). `review-feature.sh` gives it to the reviewer; the owner kept it protected on 2026-11-08 (#412). | 11 / 0 / 6: six commits changed only how the records are read (`2c15273`, `8b6ebd5`, `0183a47`, `3558d72`, `2d0d84a`, `90d181e`); five changed what is reviewed (`3ffbd23`, `ee86477`, `91d3917`, `3a83ab6`, `6120dac`). | The prompt is where #389 and #382 fixed the record findings (13 of 21 majors). Owner: kept (2026-11-08). |
| `.agents/schemas` | scientific | What a review, a triage and a revision must hold: `review-feature.sh` line 100, `triage-review.sh` line 181, `review-planning.sh` line 35, `revise-planning.sh` line 50 validate against them. | 2 / 0 / 0 (F130, F131). | None. Owner: kept (2026-11-08). |
| `.agents/policies` | both | `guardrails.conf` is the list itself (scientific). `autonomy.md` is on the built-in list and is prose (`finish-feature.sh` names it in a usage line only). `conflict-resolution.md`, `execution-limits.md`, `recovery.md`, `tools.md` are prose for the agents; no script reads them (administrative, like the prompts #412 made sensitive). | 3 / 0 / 0 (`guardrails.conf` and `autonomy.md` in F130, F131, #412). The four prose files: 0 in the last 100 (all: 2). | None. Owner: "guardrails.conf and policies" kept in any case (#396). |
| `AGENTS.md` | administrative | The agent contract and the Definition of Done; no script reads it (the check `template-structure` tests that it exists). A weakening weakens what the implementer does and records, not what a gate decides; the reviewer reads the diff. | 2 / 0 / 0 (F130, #220). All: 6 / 0. | None. Not in the owner's "kept" list. ADR 020 decision 1 names it under the gate. |
| `.agents/agents.conf` | scientific | The model per role (`scripts/lib/agent.sh`): the independence of the review (a different model) rests on it. | 0 (all: 4 / 1). | None. Owner: leave it as it is (2026-11-08). |
| `scripts/verify.conf` | scientific | The list of required checks: what is verified. The built-in rule of `guardrails.sh` already distinguishes: a line changed or removed is protected, a check added is sensitive. The `protected:` line of `guardrails.conf` overrides it: every change is protected. | 2 / 0 / 0; both commits only added a check (`255bb0e` the starters, `6120dac` the skills configuration), which the built-in rule alone would have read as sensitive. All: 15 / 5; 9 additions, 6 changes or removals. | None. Owner: kept in any case. |
| `scripts/verify.sh` | scientific | Runs the checks, fetches the base, makes the selection, records the pass with its tier (`scripts/lib/verification.sh`), decides the reuse. | 2 / 0 / 0. | #236 R5 M3 (the final verification not evidenced: process), the #415 review point 2 (the feedback route reused a run with fewer checks: substance). |
| `src/pbc/authoring/digest.py`, `src/pbc/authoring/selection.py` | scientific | What is verified in a run with a base (ADR 014); the check identity is in `selection.py`. | 1 / 0 / 0 (`5baea4d`, with its ADR note). | None in the rounds read. Owner: kept in any case. |
| `scripts/fetch-base.sh`, `scripts/collect-base.sh`, `src/pbc/authoring/provenance.py` | scientific | The base and its provenance: a wrong base makes the selection skip lessons that were never verified. | 3 / 1 / 0 (`7c94f80` provenance by branch, not tag: substance). | #236 R4 M1 (the cached base reused without checking its contents: substance). Owner: kept in any case. |
| `scripts/build-site.sh` | scientific | Reads the selection, writes the digests, the store and the page record that become the next base; `check-determinism.sh` builds with it again. | 1 / 1 / 0 (`5ca6c32` adds the introductions step: substance). | None. ADR 020 decision 9. |
| `.agents/skills` | both | Guidance for the agents (administrative: "never evidence", the README of `.agents/skills/`) and vendored third-party content with a provenance digest (`src/pbc/skills.py` checks the digest; "vendored skills" are named in the trigger "dependency selection"). | 1 / 0 / 0 (#220 adds them). | None. ADR 019. |
| `.agents/approvals` | administrative by design | The approval request is "the vehicle of a level, never part of the content" (ADR 020 decision 1): it is code-owned so that GitHub requires the identity's review, and `risk.sh` leaves it out of the path minimum. Its `Tree:` line is written by the scripts since #389 and #382. | 44 of the last 100 commits carry one (every Level 3 by trigger or assessment). | #368 R2 M1, R4 M1, R6; #372 R1 M2, R3 M1; #383 R2 M1 (a stale `Tree:` line: form; the class #382 and #389 closed). |

## Inventory B: the built-in list of `guardrails.sh` and the check-list rule

The built-in list protects, whatever the configuration says: the ADRs, the
workflows, `CODEOWNERS`, `guardrails.conf`, `.agents/policies/autonomy.md`,
`.agents/prompts/reviewer.md`, `.agents/schemas`, `check-guardrails.sh`,
`lib/guardrails.sh`, `.agents/agents.conf`, `lib/agent.sh`,
`lib/review-data.sh`, `lib/review-run.sh`, `lib/fingerprint.sh`,
`review-feature.sh`, `finish-feature.sh`, `publish-feature.sh`,
`run-feature.sh` (#399 Finding 1). The classes are as in Inventory A; the
two that differ from their class are `publish-feature.sh` and
`run-feature.sh` (administrative by #399, protected by the built-in list),
and `autonomy.md` (prose; the same reasoning as the prompts of #412 applies).
`tests/guardrails-test.sh` lines 138 to 145 pin the built-in list.

The check-list rule (`GUARDRAILS_CHECK_LISTS`: `scripts/verify.conf`,
`scripts/verify-workflow.conf`): a line changed or removed is protected, a
check added is sensitive. Scientific and well cut: an added check can weaken
nothing ("every listed check is required"). `verify-workflow.conf` is
guarded by this rule alone (12 commits in all, 0 only); the `paths:` line
decides when the self-tests run locally, and CI runs them always, so an
exclusion there is administrative.

## Inventory C: the sensitive paths

| Path | Class | Evidence |
|---|---|---|
| `pyproject.toml`, `uv.lock`, `lean/lakefile.toml`, `lean/lean-toolchain`, `lean/lake-manifest.json` | scientific | A different library version can change a number; the trigger "dependency file changed" (`risk.sh`, `RISK_DEPENDENCY_NAMES`) makes the change Level 3 whatever the list says. The sensitive marking only tells the reviewer. 4 of the last 100 commits (two dependabot bumps among them, Level 3 by the trigger alone). |
| `site/_quarto.yml` | both | The site configuration; its `execute:` block (`freeze: false`, `cache: false`, lines 120 to 123) is the ADR 002 rule that every build executes every page. No test pins those two values (`grep freeze tests/` finds only fixtures of the store). 6 of the last 100 commits touched it, 2 without any other Level 3 reading. |
| `docs/architecture.md`, `.agents/prompts` (other than `reviewer.md`) | administrative, with the safeguard #412 recorded | Level 2 by path since #412; a trigger in their content keeps Level 3. |

## Inventory D: the escalation triggers and the review-derived readings

The detected triggers (`risk_triggers`, on the diff against the base; the
counts are commits of the last 100 with at least one line of the kind, and
the lines by file category):

| Trigger | Class | What it reads | Last 100 | Observations |
|---|---|---|---|---|
| tolerance or budget changed | scientific | A Python or lesson line with a tolerance word and a number removed or changed; such a Python line added, except in a new test or a new source file; a data line of a budgets table. | 10 commits; 25 lines in the scientific and site tests, 13 in `scripts/lesson-budgets.conf`, 2 in other tests, 10 in tooling under `tools/illustrations/` and the product starter (not verification code: an over-reach without effect, those commits had other readings). | Budget raises by the owner's decision (`109e76e`, `4d90d46`) read as changed: by design (a narrowed tolerance reads as changed too; only the owner lowers). |
| skip or expected failure added | scientific | A new skip, skipif, xfail, importorskip; in Lean a new sorry, admit or axiom. | 1 commit (`19108b2`, a skip in the reproduction tests: substance). | #388 R2 M1 caught added skips the record had not named: the record is the form, the detection is the scripts'. |
| assertion removed or changed | scientific in intent | A Python assert, a shell-test fail or exit line or an expect_ or assert_ call (in `tests/` or `*-test.sh`), a Lean theorem, lemma, example or `#guard` line, removed and not added back as it was. | 30 commits; 574 lines in the scientific and site tests, 27 in the workflow self-tests. 8 commits had the trigger only in workflow self-tests; every one of them also touched a protected path, so the reading changed no level. | The broad reading (a reworded or stricter assertion reads as changed) is the main source of Level 3 by trigger: 23 of the last 100 commits are Level 3 by a detected trigger without a protected path, almost all lesson features (F75, F69, F80, F87, F124, F132, F133, F134, the budget and payload changes). The review found real scientific faults in exactly such changes (#368 R3 M1: the opening claimed the modified energy is exactly conserved; #392 R1 M1: a claim broader than the original). |
| test removed | scientific | A `def test_` or shell `test_` function removed, or a test file deleted. | 10 commits; 130 lines, all in the scientific and site tests. | A moved test reads as removed in its old file (the comparison is per file): over-reach by design. |
| marker changed | scientific | A pytest marker or `same_machine` added or removed on a test that is already there. | 2 commits. | `same_machine` decides whether a byte comparison runs on the machine that built the site (ADR 012). |
| dependency file changed | scientific | A manifest or lock file by name. | 4 commits. | Action versions and vendored skills are Level 3 by their paths, not detected. |

The named triggers (ADR 020 decision 1; the agent names them in the
completion record, the reviewer in `architecture_impact.escalation_triggers`;
`risk_review_reading`): **a changed or removed published scientific claim**
(scientific; not detected: the reviewer caught the omission three times,
#375 R3 M2, #394 R1 M1 and R2 M1, each a record major on a lesson feature),
**weakened test strength beyond the detected forms** (scientific),
**security** (scientific: permissions, secrets, external content, the
provenance of a base), **verification guarantees** (scientific: the gate; the
reviewer named it on #383 R3 M2 and #389), **dependency selection beyond the
files** (scientific: action versions, vendored skills, pins).

The review-derived readings: the reviewer's `architecture_impact.level`
`major` or `breaking` requires the owner (`guardrails_decision`); its
`risk_level` and its named triggers raise the level (`risk_assess`); a
criterion pending for `owner_approval` requires the identity's review at
the merge (`merge-feature.sh` lines 126 to 129). All three are the
independent reviewer's or the owner's judgement: scientific, and the
mechanism by which the triggers no script detects are enforced.

The records: the completion record (`.agents/completion/<issue>.json`) states
the level and the named triggers; the scripts refuse a level below the path
minimum and below a detected trigger (`risk_assess`), so a wrong record
cannot lower the level: the record's level is administrative, its named
triggers are the one scientific field no script derives. The approval
request: administrative by design (above). The handoff note: administrative;
fingerprinted so that it cannot change after a review (ADR 020 decision 4);
its staleness cost minor findings on #395 (R2 MIN1, R3 MIN1).

## Inventory E: scientific items that are only sensitive or unprotected today

| Item | Standing today | Why scientific | Evidence and cost |
|---|---|---|---|
| `scripts/triage-review.sh`, `scripts/apply-triage.sh` | Level 2 by path: neither matches `scripts/*-feature.sh` nor the built-in list | `triage-review.sh` decides the mechanical triage, verifies the owner's comment that bounds a class before a major may be deferred (`gh api`, since #389), publishes the reports and marks `published_at`, which `finish-feature.sh` trusts (#399). A weakening lets a major be deferred without the owner's word. `apply-triage.sh` guards the artifacts during the fix session and refreshes the request. | 11 commits in all touched them (3 in the last 100); every one also touched a protected path, so protecting them changes no level in the history. |
| `scripts/check-lean.sh`, `scripts/check-lesson-pages.sh`, `scripts/check-determinism.sh`, `scripts/fetch-built-site.sh` | Level 2 by path; their fail lines are not read by the assertion trigger (it reads `tests/` and `*-test.sh` only) | Each is the only place where its pass is decided (#399, "Owner's choice"): a `sorry` or an axiom let through, a lesson rendered outside its budget or not compared with its experiment, a build that depends on time, an e2e job on another site. | 3 commits in the last 100 (11 in all); 2 would become Level 3 by path, both already Level 3 by a trigger; in all history 1 commit would newly become Level 3. |
| `src/pbc/authoring/store.py` | Level 2 by path | Decides what a build with a base executes and what it restores (ADR 014 decisions 3, 6, 9): the third leg of digest and selection. A weakening restores a changed lesson from the base. | 1 commit in all (with a protected path): no cost. |
| `src/pbc/authoring/lean.py` | Level 2 by path | Shows proofs by reference and refuses a page built from a proof changed after the build record (checksums). A weakening displays a proof that was not compiled. | 3 commits in all, 2 would newly be Level 3. |
| `src/pbc/authoring/evidence.py` | Level 2 by path | The evidence map: every typed claim and what supports it; `verify.py` ("How we verify the science") resolves through it. A weakening lets a claim pass with evidence that names nothing. The assertion trigger reads its tests, not its logic. | 4 commits in all (2 in the last 100), 3 would newly be Level 3 (1 in the last 100, `10719a3`). |
| `src/pbc/data/check.py`, `src/pbc/skills.py`, `src/pbc/verification/checks.py` | Level 2 by path | Required checks (`verify.conf`: `dataset-checks`, `skills-config`) and the checks of the validation contract. | 1 commit each in all; `checks.py` would newly be Level 3 once. |
| `tests/e2e/conftest.py`, `tests/support/`, `tests/e2e/shards.json` | Level 2 by path, assertion trigger on the test files | `conftest.py` turns "no tests collected" into a pass for an empty selection and leaves out the reproductions of unchanged lessons; `shards.py` and `shards.json` decide which tests each CI job runs (the division is proved by collection). | `tests/support/` is touched often (17 of the last 100; 6 would newly be Level 3): protecting it would cost; the collection proof (`check-tests-*` and the e2e division tests) already catches a test that runs nowhere. |
| `scripts/lesson-budgets.conf` | Level 2 by path; a data line is the trigger "tolerance or budget changed" | The lesson time limits (ADR 020 decision 6 and the #383 addendum). | Covered by the trigger: 8 commits, 3 would newly be Level 3 by path, 0 newly Level 3 at all. Nothing to do. |
| `site/_quarto.yml` `execute:` block | sensitive | See Inventory C: no test pins `freeze: false`, `cache: false`. | 2 of the last 100 commits touched the file without another Level 3 reading. |
| `data/registry/` (the dataset cards), `site/references.yaml` | Level 2 by path | A card states the licence, the caps and the checksum of a committed sample; `pbc.data.check` validates the sample against the card, so a changed card and a changed sample pass together. The reviewer is the check. | 4 of the last 100 touched a card (the three dataset features), 3 without another Level 3 reading. |
| The trigger "changed scientific claim" | named only | The claim spans of a lesson, `[text]{.claim type=".." scope=".." evidence=".."}`, are machine-readable (`evidence.py`); a changed or removed span in a lesson `main` publishes is detectable on the diff like a tolerance. | Three record majors in the last week were about this trigger not being named. |
| `docs/validation-contract.md` and the other `docs/` statements of tolerances | Level 1 by path | A document stating a scientific rule; the code (`src/pbc/verification/checks.py`) is what runs, and the tolerance trigger reads `.py` and `.qmd` only. | Documentation; a drift between the document and the code is a review matter. |

## Where the review and the owner caught real faults versus record faults

Counted from the headings of the published rounds (each major once; the
triage repeats the heading). #389's own classification of the 21 majors of
#372, #375, #383 and #388 (13 on the records, 6 repeats of a class already
fixed, 6 substance) is relied on for the repeats.

| Issue (kind) | Rounds | Majors on substance | Majors on records or process form |
|---|---|---|---|
| #236 F130, the gate scripts | 5 | 8 (the identity, the triggers only in Python, the request's level, the pending owner approval, the cached base, the forgeable commit lines, the added tolerances, the assessed level) | 1 (the final verification not yet evidenced) |
| #389 the pipeline, plus the owner's outside review of PR #415 | 5 | 5 (the unattended marker, the bounded class, and the three of the outside review) | 0 |
| #399 the inventory (text only) | 3 | 0 | 4 (the list text, the Issue comment, the record's level) |
| #368 lesson correction | 6 | 1 (the opening's claim) | 6 (five on the `Tree:` line and the record's level, one on evidence not yet present) |
| #383 budgets | 7 | 1 (the accepted decisions still stating 30 s), plus repeats | 3 (`Tree:`, triggers not named, twice) |
| #372 introductions | 7 | 2 (the pairing not enforced, lists in prose), plus 1 repeat | 2 (`Tree:`) |
| #375 editorial pilot | 7 | 0 | 4 (reviews not on the pull request, the claim trigger not named, the full run of a feedback round, twice) |
| #388 pandoc processes | 4 | 1 (claim equivalence not evidenced) | 2 (a criterion marked met before its gate, skips not in the record) |
| #392, #394, #395 editorial pilots | 5, 2, 3 | 1 (#392: a claim broader than the original) | 3 (#394 the claim trigger not named, twice; #395 the verification not run) |

Reading: on the gate scripts, 13 of 14 majors were substance, found by the
independent review and the owner's outside review; on the content features,
7 of 27 majors were substance (four of them scientific claims or budgets)
and 20 were about the records, almost all in the two classes #382 and #389
have since closed (the `Tree:` line written by the scripts; the reviewer
told that detected triggers are the scripts') or in the one that stays open
(the changed-claim trigger named by hand). The owner caught faults the
pipeline did not: the three majors on PR #415, the F113 and ADR conflicts
of #412, and the loop of #399.

## The administrative items: what replaces the manual protection, what a silent change costs

| Item | Today | What would replace the protection | Cost of a silent change |
|---|---|---|---|
| `.agents/approvals` | protected (code-owned), no path minimum; the `Tree:` line written by the scripts (#382, #389) | A script writes it entirely: `finish-feature.sh` has every field (Issue, Level, Derived from, Tree); only a lowering's `Reason` and `Owner's word` are the agent's. Already outside the fingerprint. | None to the truth: GitHub's review requirement comes from the path, not the text; a wrong text is refused by `risk_assess`. |
| The completion record's `risk.level` and detected triggers | stated by the agent, refused when below the derivation | Already a script's: `risk_assess` derives both; since #389 the reviewer is told so. Only the named triggers stay the agent's. | None to the level; a missed named trigger is the residual risk ADR 020 states, caught by the reviewer (three times in the last week). |
| The handoff note | fingerprinted; staleness reviewed | Nothing: it is a working file. The reviewer contract could say that its staleness is at most a suggestion. | None. |
| `AGENTS.md` | protected | Sensitive, as the prompts (#412): the reviewer reads it, the owner reads the pull request. | A weaker Definition of Done weakens what the implementer records, not what a gate decides; the scripts enforce their own rules. |
| `.agents/policies/autonomy.md`, `conflict-resolution.md`, `execution-limits.md`, `recovery.md`, `tools.md` | protected (`autonomy.md` built-in) | Sensitive, as the prompts; `autonomy.md` would need the built-in list changed. | As for the prompts: a weaker instruction; no gate reads them. |
| `scripts/check-guardrails.sh`, `scripts/check-review.sh` | protected | Sensitive; `tests/risk-level-test.sh` runs the first. | None: no gate reads their output. |
| The convenience scripts and libraries of #399 (`start-feature.sh`, `start-planning.sh`, `revise-planning.sh`, `scripts/lib/scope.sh`, `prerequisites.sh`, `github.sh`, `check_browser.py`, `check_links.py`; `run-feature.sh`, `publish-feature.sh` on the built-in list) | protected | Sensitive; a wrong result is caught by a gate (#399). | None to the gate; `publish-feature.sh` alone decides whether a pull request closes the Issue (an Issue closed early: paperwork, reopened by hand). |
| `scripts/verify.conf` on the `protected:` line | every change protected | The built-in rule: an added check sensitive, a changed or removed line protected; the check identity (`selection.py`) refuses the targeted tier when the list changed. | None: an added check cannot weaken a verification. |
| `.agents/skills` | protected | Sensitive, with the trigger "dependency selection" naming vendored skills (agent-named), or kept protected as vendored content. | A changed skill changes guidance, never evidence (the README of `.agents/skills/`); a silently changed vendored file is a supply-chain question, which is why ADR 019 made it Level 3. |
| `docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md`, the `*-planning.sh` scripts | protected | Already doubled by the planning gate (`planning.sh`); kept by the owner's word. | Governance, not truth. |

## Proposal (not applied; every item is the owner's decision)

The finding first: **the protected list is no longer where the Level 3 cost
comes from.** Under today's rules 33 of the last 100 commits are Level 3 by
path and 23 more by a detected trigger alone (56 in all); 44 carry an
approval request. Every administrative item above that could leave the list
touches 0 of those 33 on its own (all history: 3 of 73). The cost sits in
the detected triggers on lesson features and in the record findings of the
review rounds, and the second of these is largely closed by #382 and #389.
The proposal therefore adds protection where a scientific item is bare,
removes it where the item is form, and replaces one manual naming by a
detection; its effect on the share is nil to one commit.

### The protected list as it would read

Every line of `.agents/policies/guardrails.conf` with the decision that
changes it; a line without a decision stays as it is.

```
protected: docs/decisions docs/PROJECT_REQUIREMENTS.md docs/roadmap.md
protected: .github/workflows .github/CODEOWNERS
protected: :(glob)scripts/*-feature.sh :(glob)scripts/*-planning.sh scripts/lib scripts/check-guardrails.sh scripts/check-review.sh scripts/ci-aggregate.sh
protected: scripts/triage-review.sh scripts/apply-triage.sh
protected: scripts/check-lean.sh scripts/check-lesson-pages.sh scripts/check-determinism.sh scripts/fetch-built-site.sh
protected: .agents/prompts/reviewer.md .agents/schemas .agents/policies .agents/agents.conf scripts/verify.sh
protected: src/pbc/authoring/digest.py src/pbc/authoring/selection.py src/pbc/authoring/store.py
protected: scripts/fetch-base.sh scripts/collect-base.sh src/pbc/authoring/provenance.py
protected: scripts/build-site.sh src/pbc/authoring/lean.py
protected: .agents/skills .agents/approvals
sensitive: site/_quarto.yml pyproject.toml uv.lock lean/lakefile.toml lean/lean-toolchain lean/lake-manifest.json
sensitive: docs/architecture.md .agents/prompts AGENTS.md
sensitive: src/pbc/authoring/evidence.py src/pbc/data/check.py src/pbc/skills.py src/pbc/verification/checks.py tests/e2e/conftest.py data/registry
```

- **D1 (add, recommended yes): `scripts/triage-review.sh scripts/apply-triage.sh` protected.** Gate-critical by #399 and by the #389 change (the owner's bounding comment is verified there). Effect on the share: 0 (every commit that touched them touched a protected path).
- **D2 (add, recommended yes): the four check scripts protected.** The only place each pass is decided; #399 recommended it as the owner's choice. Effect: 0 of the last 100 (2 are already Level 3 by trigger), 1 of 217.
- **D3 (remove, owner's call): `AGENTS.md` sensitive, Level 2 by path like the prompts.** Needs an ADR 020 addendum (decision 1 names it under the gate) and the same safeguard text as #412. Effect: 0.
- **D4 (remove, recommended yes): `scripts/verify.conf` leaves the `protected:` line**, so the built-in rule reads it (an added check sensitive, a changed or removed line protected). Needs an addendum (decision 1 names the file) and a test case. Effect: 0 of the last 100; 2 of 217 (pure additions).
- **D5 (add, recommended yes): `src/pbc/authoring/store.py` protected** with the digest and the selection (ADR 014 decisions 3, 6, 9). Effect: 0.
- **D6 (add, owner's call): `src/pbc/authoring/lean.py` protected** with the build (it decides whether a proof shown was compiled). Effect: 0 of the last 100, 2 of 217.
- **D7 (add, recommended yes): a `sensitive:` line for `evidence.py`, `data/check.py`, `skills.py`, `verification/checks.py`, `tests/e2e/conftest.py` and the dataset cards `data/registry`.** The reviewer is told to look; no level changes. Effect: 0.
- **D8 (not proposed, for the record): the convenience scripts and libraries (#399), `check-guardrails.sh`, `check-review.sh`, the prose policies and `.agents/skills` stay as they are.** Each would change 0 of the last 100 commits; the owner dropped point 2 for the same reason, said "policies kept", and the skills are vendored content. Listed so that the owner sees the full choice.

### The trigger set as it would read

The six detected triggers stay as they are (D9). One detection is added
(D10), and nothing is added to what the agent must name.

- **D9 (keep, recommended): "assertion removed or changed" keeps its broad reading.** It is the reading that puts 23 of the last 100 commits at Level 3 without a protected path; the review found scientific faults in exactly those changes (#368 R3, #392 R1), and a narrower reading (a changed expected value counted as no change) is where a silent weakening would hide. The alternative the owner may choose: not reading the workflow self-tests (`tests/*-test.sh`) for this trigger, since the scripts they test are protected by path; effect 0 on the level of any commit in the history, less noise in the statements.
- **D10 (add, recommended yes): detect the changed scientific claim.** A `{.claim ...}` span of a lesson that `main` publishes, removed or changed on the diff and not added back as it was, is reported as the trigger "changed scientific claim" by `risk_triggers`, with the span as the detail, like a tolerance. The agent still names a claim changed in prose, a figure or a check (the trigger stays named for those). Replaces the manual naming that cost three record majors in the last week (#375 R3 M2, #394 R1 M1, R2 M1). Effect on the share: it can only raise it; on the last 100 the lesson features with a changed claim were already Level 3 by the assertion trigger.
- **D11 (add a test, recommended yes): a unit test pins `execute.freeze: false` and `execute.cache: false` in `site/_quarto.yml`** (ADR 002). A pin, not a protection; the file stays sensitive.
- **D12 (reviewer contract, owner's call): the handoff note's staleness is at most a suggestion**, and the approval request is written by the scripts in full (every field but a lowering's reason and the owner's word). Closes the last administrative findings a round can be spent on. Touches `reviewer.md` and `finish-feature.sh` (protected).

### Effect on the share of Level 3 commits (the last 100 of `main`)

| Reading | Today | With D1 to D7 | With D1 to D7 and D10 |
|---|---|---|---|
| Level 3 by path | 33 | 33 (the paths D1, D2, D5, D6 add are in commits already Level 3) | 33 |
| Level 3 by path or detected trigger | 56 | 56 | 56 or more (a changed claim in a commit not yet Level 3 raises it; none of the last 100 is known to be such) |
| Commits that leave Level 3 | — | 0 (D3, D4: 0 of the last 100; 2 of 217 for D4) | 0 |

On all 217 first-parent commits: 73 Level 3 by path today, 74 with D1 to D7
(D2 and D6 add 3, D4 removes 2).

### Risks

- A new protected path needs an ADR 020 decision 1 addendum (the list is
  named "directly and authoritatively"), a line in `tests/risk-level-test.sh`
  (the `expected` list and its count, lines 668 to 678), the header comment of
  `guardrails.conf`, and the lists repeated in `docs/architecture.md`,
  `docs/process.md` and `docs/repository-setup.md`. The feature is Level 3.
- D10 reads the claim syntax of `evidence.py`; a claim written another way
  (a number in prose, a figure) is not detected and stays named. The
  detection is conservative like the others: a reworded span reads as
  changed, and only the owner lowers.
- D4 relies on the built-in rule; `tests/guardrails-test.sh` pins it. A
  future `guardrails.conf` that lists the file again silently restores the
  stricter reading, which is safe.
- D3 makes `AGENTS.md` Level 2: a weakened Definition of Done is caught by
  the reviewer and the owner's reading, not by a script; the same residual
  risk #412 accepted for the prompts.
- The measurement limits above: the share is a lower bound (named triggers
  and assessed levels are not in the diff), and the first-parent count is
  one per pull request.

## What the follow-up feature would change (after the owner's decisions)

1. ADR 020, an addendum to decision 1 with the accepted items (status
   Proposed, accepted by the merge).
2. `.agents/policies/guardrails.conf`: the lines above.
3. `scripts/lib/risk.sh`: the detection of D10; `tests/risk-level-test.sh`:
   the list, its count, a case per new path, a case for D10, the sensitive
   reports of D7; `tests/guardrails-test.sh` if the built-in list changes.
4. A unit test for D11.
5. `.agents/prompts/reviewer.md` and `scripts/finish-feature.sh` for D12.
6. `docs/process.md`, `docs/architecture.md`, `docs/repository-setup.md`:
   the lists as they then read.

Level 3 (protected paths); one change to the workflow scripts at a time (ADR
020 decision 10).

## Acceptance criteria and their gates

1. Every protected path and every trigger of current `main` is classified
   with evidence: Inventories A to E (implementation).
2. The proposal is written out and not applied, with the effect on the share
   counted on the last 100 commits: "Proposal" (implementation).
3. The result is on the Issue: the comment of 2026-11-09 on #446
   (implementation).

## Where this plan relies on #399, #236 and #389

- #399 (comment of 2026-11-07): the per-script classification gate-critical
  versus convenience and the readers of each script (Inventories A, B, E);
  Finding 1 (the built-in list cannot be narrowed by the configuration);
  Finding 2 (25 of 216 commits touched the script classes, one would have
  left Level 3), which the owner used to drop point 2.
- #236 (the pilot of 2026-11-08): no `process-miss` label exists; all five
  pilot features were Level 3; the review rounds per feature (1 to 7); the
  owner's waiting time and the misses cannot be derived (one login).
- #389 (comments of 2026-11-06): the 21 majors of #372, #375, #383 and #388
  classified (13 records, 6 repeats, 6 substance), relied on for the repeats
  and confirmed here from the published headings; the durations (a full run
  97 to 140 minutes), which make every Level 3 commit by trigger cost one
  full run and a full review per complete round.
