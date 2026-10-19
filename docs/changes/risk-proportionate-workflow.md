# Planning change: a risk-proportionate verification and review workflow

**Date:** 2026-10-18  
**Type:** One coordinated planning change request, delivering two bounded implementation features  
**Owner decisions:** Version 2 of the workflow proposal is approved in principle as the basis for this planning change, with the four final refinements of 2026-10-18 recorded below. The owner prepared this request to be started with `start-planning.sh`. Nothing of the new workflow is implemented before the planning and the ADR are approved.

```bash
./scripts/start-planning.sh risk-proportionate-workflow --change /Users/ataspinar/Documents/projects/physics-by-construction/.agents/handoffs/risk-proportionate-workflow.md --grill
```

This document requests planning changes, not implementation and not automatic merging. Reconcile it against the current `main` and the features in flight. **Features already in progress continue under the workflow contracts they started with** (the contracts of AGENTS.md, ADR 003, 005, 012, 014, 015 and 017 as they stand today). The new rules apply to features started after the implementation of the second deliverable is merged. Never merge two changes to the workflow scripts (`scripts/lib/*`, `finish-feature.sh`, `review-feature.sh`, `triage-review.sh`, `apply-triage.sh`, `publish-feature.sh`, `verify.sh`) concurrently.

## 1. Why this change exists

The scientific, reproducibility, security and independent-review guarantees of the project are strong and must stay exactly as strong. What has grown is the time it takes to deliver a feature under them. Measured on recent features (GitHub times in UTC and the review files of the worktrees; estimates are marked):

| Feature | Lead time | Review rounds | Complete local verifications | CI per pull request |
|---|---|---|---|---|
| One-character lesson fixes (#192, #193, #194 as #195, #197, #198) | Pull request open to merge 12 to 16 min; work before it about 25 to 30 min (estimate) | 2 to 3 each | Targeted run | 14:05, 14:52, 12:27 |
| #206 (pull request #209) | 7 h 02 | 3 rounds, 2 triages | 3, the first 3708 s | Two runs of about 35 min |
| F119 (#185, pull request #191) | 12 h 04 to merge; 20 h 38 to close the Issue | 3 rounds, 1 triage | At least 2 | 3 h 27 open to merge |
| F120 (#196) | More than 59 h, still unpublished | 4 rounds, 2 triages | At least 5, 45 to 70 min each | None yet |
| F122 (#215, pull request #220) | 21 h 13 | 2 rounds | At least 2 | 35 min |
| F61 (#147) | 8 pull requests in 2 days, the Issue open after 5 days | 10 review files, 7 triages | Many | 15 to 45 min each |

A pull request's CI takes 12 to 35 minutes; a feature takes 7 hours to several days. The largest items are (a) a complete local verification of about an hour after every change, (b) a new full review round and triage after every change, however small, and (c) an owner exception (`--partial`, `--no-review`) needed five times in three days (F114, F119, F117, F66, F122) because a criterion's evidence can only exist after publication, after the merge, or after the owner's approval. About half of the twenty workflow gates exist only as script behaviour with no ADR or AGENTS.md authority, and `.agents/policies/autonomy.md` names three risk levels that no script reads. ADR 017 and ADR 014 decision 11 (F113) are justified only by the duration of a CI run, not by the lead time of a feature.

The exact current verification matrix (from `scripts/verify.conf`, `scripts/check-determinism.sh`, `tests/e2e/test_lessons.py`, and the CI logs of `main` run 39079012220 at 38 lessons, 29 min 08 s) is the reference of this change and is to be recorded in `docs/architecture.md`: per lesson a full run executes **three pages** (`site-build`, `determinism`, and the reproduction render of `site-checks-reproduction`), **one experiment through the learner path** (the second test of `site-checks-reproduction`; these four are all in the job `build`, 20 min 40 s, of which the reproduction is 9 min 35 s), and **one experiment in the unit tests** (job `code`), so the experiment code runs five times per lesson, three of them inside a page. Run in parallel, the CI critical path is `build` plus the end-to-end jobs; run sequentially on a machine, a full verification is about 68 minutes (about 4 `code`, 4 `workflow`, 22 `integration`, 21 `build`, 17 end-to-end).

## 2. Objective

Reduce total feature lead time and unnecessary rework **without weakening** scientific correctness, reproducibility, security, or independent review. Provide one authoritative workflow policy with three risk levels, explicit verification requirements, review-invalidation rules, owner-approval gates and evidence-reuse conditions, while preserving fail-safe behaviour for the digest, dependency selection, provenance, build and deployment.

## 3. The decisions this change asks the planning to record

These are the four final refinements of the owner (R1 to R4) and the approved parts of version 2, as requirements for the planning.

### 3.1 Three risk levels, with paths as a conservative minimum (approved)

The level of a change is the **highest** of: (1) the minimum implied by its paths; (2) any **escalation trigger** its nature hits, wherever the files are; (3) the level an agent or the reviewer assesses. An agent may raise the level at any time. **An agent must not lower a required level without the owner's explicit authorization**, and such an authorization is verified only at the merge gate (3.4), never accepted from an agent-written statement.

- **Path minimum.** Level 1: documentation and process files only (documentation outside the ADRs and the planning documents, `.agents/plans`, handoffs, summaries). Level 2: lessons, `src/`, tests, scripts that are not protected. Level 3: the protected paths of `guardrails.conf` (ADRs, planning documents, workflows, gate scripts, prompts, `agents.conf`, `verify.conf` and `verify.sh`, digest, selection, `fetch-base.sh`, provenance, build and deploy, skills).
- **Escalation triggers** (any one raises the level regardless of the path): a change of a **scientific claim** (a number, tolerance, acceptance rule, theory comparison, or what a figure shows); a change of **test strength** (an assertion weakened or removed, a tolerance or budget widened, a new skip or expected failure, a removed test, a changed marker such as `same_machine`); **security** (permissions, secrets, credentials, network access, fetching or executing external content, provenance of a base); **verification guarantees** (anything touching the check identity, selection, digest, base, determinism, build, deploy, or a gate); **dependency selection** (`pyproject.toml`, `uv.lock`, the Lean toolchain and manifest, action versions, vendored skills, pins of external tools). The scripts detect the mechanically detectable triggers on the diff (widened tolerance or budget, a new skip or expected failure, a removed assertion, a changed dependency file); the agent names the rest in the completion record and the independent reviewer assesses it with the field it already fills (the impact classification), with no new agent and no new report.

### 3.2 Evidence lifecycle: three readiness points and one meaning of `complete` (refinement R2)

Do not treat pending evidence as completion and do not add redundant state machines. The completion record stays the single record, with its three statuses and their present meaning, and gains one attribute per criterion:

- Each criterion names the **gate that clears it**: `implementation` (tests, local verification, the review chain), `pr_ci` (CI green on exactly the published head), `owner_approval` (the owner's approval of the exact commit, verified at the merge gate, 3.4), or `post_merge` (a measurement or an observation that can only exist after the merge).
- A criterion is `met`, `not_met`, or `pending`. `pending` is allowed only for the last three gates and names that gate; it is never allowed for `implementation`.
- **`complete` keeps one meaning: every acceptance criterion of the Issue is met.** A record with pending criteria is `partial`, as today; it is not complete.
- **Three readiness points are derived from the record, not stored as new states:** *ready for PR* (every `implementation` criterion is met; pending `pr_ci`, `owner_approval` and `post_merge` criteria do not stand in the way of committing and publishing); *ready for merge* (additionally the `pr_ci` criteria are met by CI on the exact head, the review chain is current and covers the implementation, no major finding is open, and for Level 3 the owner's approval of the exact commit is verified, 3.4); *done* (every criterion met, so `complete`, and the Issue may close). **Post-merge evidence still outstanding** keeps the Issue open and never blocks the merge.
- Consequences: a record whose only unmet criteria are `pending` for `pr_ci`, `owner_approval` or `post_merge` is committed and published **without** `--partial` or `--no-review` and without an owner exception; the pull request does not close the Issue while any criterion is pending; pending PR-CI blocks the **merge**, not the preparation or the publication of the pull request (it may be a draft or a ready pull request); an open major finding is never a pending criterion, and the reviewer's guidance says that criteria whose evidence belongs to a later gate are not findings.

### 3.3 Incremental review, simplified (refinement R1)

For Medium risk (Level 2), allow an initial **full review** followed by a **traceable chain of delta reviews**, with the **explicit disposition of every earlier finding**, and nothing more elaborate:

- **Traceable chain.** Each review records the tree it compared against (the reviewed tree of the previous round) and the tree it reviewed. The chain begins with a full review and ends with a review whose reviewed tree is exactly the current tree; a gap or a break means a full review.
- **Disposition of earlier findings.** Every finding has a stable identifier. Each later review states, for every earlier open finding, whether it is resolved (with the evidence), still open, or accepted. Finish requires that no finding is open.
- **Full review when the impact cannot be bounded reliably.** There is **no changed-lines threshold** and **no general-purpose impact graph**. A delta review is allowed only when the delta is confined to kinds of change whose reach is certain: tests, documentation, lesson content, and a change to one source module whose importers are all among files the baseline review already covered (a plain textual search for the module name, using the import knowledge the digest already has). Anything else — a Level 3 path, an escalation trigger, a shared input, a change to an exported interface, a file with an earlier unresolved finding, or any case where that check cannot decide — requires a full review.
- Level 3 keeps a full review in every round. Level 1 needs no review.

### 3.4 Owner authorization is verified once, at the gate, and never from an agent's assertion (refinement R3)

- Owner approval of a Level 3 change, and an authorization to lower a risk level, are **pre-merge requirements**, verified **at the merge gate** and not by repeated network requests during intermediate workflow steps (finish, review, triage and publish only record what is required and name the head they apply to).
- **An agent-written assertion, a comment or file written by an agent, a flag, or a statement in chat is never proof of the owner's approval to a script.** The agent's `gh` login is the owner's account, so a comment authored by that login proves nothing; the planning must not rely on it.
- The planning decides, with the owner, a mechanism that an agent cannot forge, from these candidates, and records it in the ADR as a pre-merge requirement: **(A)** an approving review of the pull request by a separate GitHub identity held only by the owner, enforced by GitHub itself through branch protection (a required approving review for the paths of `guardrails.conf` through a code-owners file), which GitHub checks at the merge and which needs no script to trust anything; or **(B)** an approval artifact signed with a key that only the owner can use (for example a signed tag or commit with the owner's SSH or GPG key behind a passphrase or hardware token), whose signature a local script verifies against an allowed-signers file, once, immediately before the merge. Setting up a second identity, branch protection or a signing key is an owner action; the agent never changes repository settings or creates accounts.
- Until the chosen mechanism exists, the present practice continues: an agent merges a Level 3 change only after the owner's explicit word in the conversation, and states the head commit it applies to.

### 3.5 Intermediate High-risk verification and unchanged final guarantees (approved)

For Level 3, **intermediate fix rounds may use targeted partial verification** (the groups the changed paths touch, through `verify.sh --only <group>`, plus the unit tests of the changed modules; typically `code` plus `integration-other`, about 13 minutes against about 68 for a complete run). It is quick feedback and **never evidence**. **The final acceptance is always** a complete verification of the final tree, then a complete independent review of the final tree **run after that verification** (a review made with `--unverified` never counts as the final review), and then the full CI, which stays the publication gate. The scripts require the latest review of a Level 3 change to have been made on a verified tree. The targeted tier (`targeted: default,code`) stays refused when the check identity differs, because that is the fail-safe.

### 3.6 Budgets (approved)

An exceeded time budget is recorded as a measurement and decided by the owner at the re-assessment points already chosen (re-measure at 42 lessons, decide the capacity at 44 at the latest, or earlier if a complete `main` run exceeds 45 minutes). It does not start mandatory optimisation work and never changes scientific content. Hard checks, such as the 30-second lesson page budget, remain able to fail, with the documented exception table (`scripts/lesson-budgets.conf`).

### 3.7 ADR 017 and F113 stay paused (approved)

Neither is justified by lead-time evidence. They stay paused, ADR 017 decisions 1 to 6 and 9 are not accepted, F113 and Issue #150 stay paused and open, F121 is not started, and F120 is finished by publishing its evidence. They are reopened only at the owner's triggers (42 lessons measure, 44 decide, or a complete run above 45 minutes).

### 3.8 What stays exactly as it is

The complete CI run on every pull request and push; the aggregate required check `verify` and the deployment of only the verified artefact; the digest, selection, base provenance (including the stamped ref of F61 M3) and check identity, with the safe fall-back to executing everything; independent review by a different model for Levels 2 and 3; and no scientific check removed without coverage evidence (ADR 017 decision 8). Any change to these is Level 3. **No new mandatory agents and no new mandatory reporting gates.**

## 4. Implementation in two bounded deliverables (refinement R4)

One planning change, delivered as two features, strictly one after the other, each Level 3 (the owner approves each diff before its merge). Neither starts before the planning and the ADR are approved. The second does not start until the first is merged and its effect observed on at least two features, so that two changes to the workflow scripts are never in flight together.

**Deliverable 1 — evidence lifecycle, intermediate High-risk verification, and budget policy.**
1. The completion record's per-criterion gate and `pending` status, the derived readiness points, and the meaning of `complete` (3.2); finish and publish accept a record whose only unmet criteria are pending for later gates, without an owner exception, and publish a pull request that does not close the Issue.
2. The risk level derived from paths, mechanical triggers and the assessed level, raise-only, with lowering only through the owner authorization of 3.4 (3.1).
3. Owner authorization verified at the merge gate by the mechanism the planning chose (3.4).
4. Intermediate Level 3 verification and the requirement that the final review is made on the verified final tree (3.5).
5. The budget policy of 3.6 in the ADRs and in the one place the checks read.
6. A small time log appended by `verify.sh` (timestamp, tier, tree, duration, result) for the evaluation, which no gate reads.
7. Not re-fetching the base when the latest accepted `main` run is the one recorded.

**Deliverable 2 — delta review and triage simplification.**
1. The review chain: stable finding identifiers, the traceable chain of trees, the disposition of every earlier finding, and the rule that the impact must be bounded reliably or a full review is required (3.3); `finish-feature.sh` verifies the chain instead of requiring that the last review is a full one, for Level 2 only.
2. The completion record and handoff note included in the review fingerprint (closing the gap that they can change after the review).
3. Mechanical triage for minor and suggestion findings at Levels 1 and 2 (an automatic ACCEPT or DEFER with a reason, published once, a follow-up Issue for every DEFER); a full triage per finding at Level 3.

## 5. What the planning documents change (no scripts)

- `PROJECT_REQUIREMENTS.md`: one new decision, "Risk-proportionate verification and review", recording the three levels, the escalation triggers, the evidence lifecycle, the review chain and the owner-approval requirement. No existing decision on scientific correctness, reproducibility, security or independent review is weakened.
- `architecture.md`: the verification and workflow chapters describe the levels, the evidence lifecycle, the review chain, and the exact verification matrix of section 1 as the standing reference.
- **ADR 020** (new, "Risk-proportionate verification and review"): the only authoritative place for these rules, with the decision on the owner-approval mechanism (3.4).
- Status lines and amendments of the process statements (never the invariants) of ADR 002 (the lesson budget), 003 (decisions 5 and 6), 005 (decisions 3 to 5), 012 (decisions 1 and 8), 014 (decision 7 and the consequences), 015 (decision 4) and 017 (the status: not justified by lead-time evidence, paused, the triggers, and the stale description of decisions 7 and 8), plus the consistency repairs of stale sentences ("no lesson past 32 before F113", "45 minutes per job").
- `.agents/policies/autonomy.md` and the Definition of Done of `AGENTS.md`: refer to ADR 020 and define the levels and the evidence states.
- `roadmap.md`: **two** features, the next free identifiers (the roadmap's last is F129, so F130 and F131 at the time of writing; confirm), with the acceptance criteria of section 7; no other optimisation features.

## 6. Evaluation (approved)

A pilot of five features under the new rules after Deliverable 2 is merged (or two features after Deliverable 1 for its own effect). The six measurements are **derived afterwards from existing artefacts** (GitHub, the review and verification records, the handoff notes), with no new mandatory report, no new agent and no gate:

1. **Total lead time** of each feature, from the Issue's creation to its merge and its closure.
2. **Repeated verification:** the number and total duration of verification runs per feature, from the time log of Deliverable 1.
3. **Review rounds:** the number of review files per feature, with their time stamps and chain status (full or delta).
4. **Owner waiting time:** from the moment a pull request or a question is ready for the owner to the owner's next comment or merge, from the timeline of the Issue and the pull request.
5. **Defects missed by the reduced process:** a defect found after the merge in a Level 1 or 2 change that the full process could have caught gets an Issue with the label `process-miss`. A miss in an escalation-trigger category (scientific claim, test strength, security, verification guarantee, dependency) stops the pilot and puts that level back at full strictness until the owner decides.
6. **The baseline** of the table in section 1.

## 7. Acceptance criteria

**Of the planning change:** the requirements decision, the architecture update (with the verification matrix), ADR 020 (with the owner-approval mechanism decided with the owner), the status lines and amendments of ADR 002, 003, 005, 012, 014, 015 and 017, the policy updates, and the two roadmap features exist and agree with each other; every invariant of this request is unchanged; ADR 017 and F113 are recorded as paused with the reason; the owner has approved the planning and the ADR.

**Of Deliverable 1:** (1) the criterion gates and `pending` exist, and a record with only later-gate pending criteria is committed and published without an owner exception and without closing the Issue; (2) `complete` means every criterion is met, and a test shows a record with a pending criterion is not complete; (3) the risk level is the highest of path, mechanical trigger and assessment, a lower level than the minimum is refused, and a lowering requires the verified owner authorization at the merge gate; (4) no script accepts an agent-written assertion, a comment by the agent's own login, or a flag as the owner's approval; (5) the merge-gate verification of the chosen mechanism works in a test with a forged assertion that it refuses; (6) intermediate Level 3 rounds can use `--only` partial runs, and finish and the final review require a complete verification of the final tree and a review made after it, shown by tests; (7) the time log exists and no gate reads it; (8) the budget policy is written where the checks read their budgets; (9) every invariant and the full CI are unchanged and guarded by the existing tests.

**Of Deliverable 2:** (1) stable finding identifiers and the traceable chain exist; (2) finish accepts a Level 2 delta chain only when the chain is contiguous, ends at the current tree, and every earlier finding has a disposition, and otherwise requires a full review; (3) a test shows that a delta whose impact cannot be bounded (a Level 3 path, a trigger, a shared input, an exported interface, an unresolved earlier finding, an undecidable search) requires a full review, and that there is no line-count threshold; (4) the completion record and the handoff are in the review fingerprint; (5) mechanical triage for minor and suggestion at Levels 1 and 2 with a follow-up Issue per DEFER, and a full triage at Level 3; (6) Level 3 keeps a full review in every round; (7) the invariants and the full CI are unchanged.

## 8. Non-goals and guardrails

- No weakening of the digest, selection, provenance, build, deployment or determinism guarantees, of the complete CI run, or of independent review.
- No new mandatory agent and no new mandatory reporting gate; the evaluation reads existing artefacts.
- No further work on ADR 017, F113, F120 or F121 beyond recording their status; F120 finishes by publishing its evidence.
- No implementation of any workflow change before the planning and the ADR are approved; no concurrent changes to the workflow scripts.
- Features in progress finish under the contract they started with.
- The agent never changes repository settings, creates accounts, or sets up the owner-approval mechanism; those are the owner's actions.

## 9. Instructions to the planning agent

- Reconcile this request against the current `main`, the roadmap's status section and the Issues in flight; refresh every status claim.
- Keep it one planning change with two bounded features, in the order of section 4, and confirm the next free feature identifiers.
- Decide the owner-approval mechanism (3.4) with the owner during Project Grill; do not choose a mechanism that rests on the authorship of a comment or on a flag.
- Treat the thresholds and lists of section 3 as the owner's decisions, not as open questions, except where this request names an open decision.
- Keep ADR 020 to the rules and their reasons; keep every invariant's wording as it is in the ADRs.
- Report, before finishing, which statements of this request could not be verified from the repository.

## 10. Open decisions for the owner during the planning

1. The owner-approval mechanism of 3.4 (A, B, or another that an agent cannot forge) and the owner actions it needs.
2. Whether Deliverable 2 starts after two or after more features have shown the effect of Deliverable 1.
3. The moment to start the planning cycle (the owner's request to start it now is assumed).
