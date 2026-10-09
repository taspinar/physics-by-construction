# Planning Approval

Status: Approved
Approved at: 2026-10-09T13:08:17Z
Planning branch: planning/physics-next-phase
Change request: docs/changes/physics-next-phase.md
Final review: round 6, PASS WITH MINOR FINDINGS, by claude (fable)
Planning fingerprint: 47b9761c367d8ac05e7b436bee9dfae857ddbd13

Recorded by `scripts/finish-planning.sh`. The approval covers these planning
documents; any change to them invalidates it (`./scripts/finish-planning.sh --check`):

- `docs/PROJECT_DESCRIPTION.md`
- `docs/changes`
- `docs/PROJECT_REQUIREMENTS.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/decisions`

## Review rounds

- Round 1: CHANGES REQUIRED, 12 finding(s), by claude (fable)
- Round 2: PASS WITH MINOR FINDINGS, 5 finding(s), by claude (fable)
- Round 3: PASS WITH MINOR FINDINGS, 11 finding(s), by claude (fable)
- Round 4: PASS WITH MINOR FINDINGS, 6 finding(s), by claude (fable)
- Round 5: PASS WITH MINOR FINDINGS, 4 finding(s), by claude (fable)
- Round 6: PASS WITH MINOR FINDINGS, 5 finding(s), by claude (fable)

## Escalations confirmed as resolved

- Round 1: MIN7 Approved requirements still list unresolved questions 1 to 4 as open although they are settled, and the architecture now contradicts them
- Round 3: MIN9 Approved requirements still list unresolved questions 1 to 4 as open although each is settled (carried from rounds 1 and 2; concerns the approved requirements)
- Round 3: S1 The approved requirements group counterexample hunting with exercises that let a coding agent write and run code, while the change request and F16 define it as an allowlisted harness agent replayed in CI (concerns the approved requirements)
- Round 4: MIN4 Approved requirements still list unresolved questions 1 to 4 as open although each is settled (carried from rounds 1 to 3, escalated; concerns the approved requirements)
- Round 4: S1 The approved requirements group counterexample hunting with coding-agent exercises, while F16 is an allowlisted harness agent replayed in CI (carried from round 3, escalated; concerns the approved requirements)
- Round 5: MIN2 Approved requirements still list unresolved questions 1 to 4 as open although each is settled (carried from rounds 1 to 4, escalated; concerns the approved requirements)
- Round 5: S1 The approved requirements group counterexample hunting with coding-agent exercises, while F16 is an allowlisted harness agent replayed in CI (carried from rounds 3 and 4, escalated; concerns the approved requirements)

## Findings that were not adopted

- Round 1, ESCALATE: MIN7 [minor] Approved requirements still list unresolved questions 1 to 4 as open although they are settled, and the architecture now contradicts them. Valid, but the stale entries are in docs/PROJECT_REQUIREMENTS.md, which the planner may not modify. The architecture already records where questions 1 to 4 were settled (F09, ADR 006, F10, F11), so the planning documents are not in conflict with each other; only the requirements need the housekeeping, which is a Grill pass for the human.
- Round 3, ESCALATE: MIN9 [minor] Approved requirements still list unresolved questions 1 to 4 as open although each is settled (carried from rounds 1 and 2; concerns the approved requirements). Verified: docs/PROJECT_REQUIREMENTS.md still lists unresolved questions 1 to 4 as open while the architecture's "Requirements coverage of open choices" records each as settled (default provider in src/pbc/agents/providers.py, ADR 006, F10, F11) and its stay-open table holds only questions 5 to 7. The planning documents are consistent; the only remaining change is to the approved requirements, which the planner may not edit. It stays escalated to the human for the next Grill pass, as in rounds 1 and 2, with no planner action.
- Round 3, ESCALATE: S1 [suggestion] The approved requirements group counterexample hunting with exercises that let a coding agent write and run code, while the change request and F16 define it as an allowlisted harness agent replayed in CI (concerns the approved requirements). Verified: the requirements' Security and privacy bullet groups counterexample hunting in the parenthetical about exercises where a coding agent writes and runs code, while the change request, F16, and ADR 010 decision 1 define F16 as an allowlisted harness agent replayed in CI. The finding agrees there is no behavioural conflict and that F16 is stricter than the requirement, so no architecture, roadmap, or ADR change is needed. The only improvement is a wording change to the approved requirements, which the planner may not make, so it goes to the human's next Grill pass as a note.
- Round 4, ESCALATE: MIN4 [minor] Approved requirements still list unresolved questions 1 to 4 as open although each is settled (carried from rounds 1 to 3, escalated; concerns the approved requirements). Verified: docs/PROJECT_REQUIREMENTS.md lines 572 to 587 still list questions 1 to 4 as unresolved and line 337 refers the CI-key question there, while docs/architecture.md lines 675 to 679 record each as settled and its stay-open table (lines 691 to 695) holds only questions 5 to 7. The planning documents are consistent with each other and with the repository; the only stale text is in the approved requirements, which the planner may not modify. The human marks questions 1 to 4 as settled in the next Grill pass. No planner action.
- Round 4, ESCALATE: S1 [suggestion] The approved requirements group counterexample hunting with coding-agent exercises, while F16 is an allowlisted harness agent replayed in CI (carried from round 3, escalated; concerns the approved requirements). Verified: requirements lines 420 to 421 group counterexample hunting with coding-agent exercises, while F16 (roadmap lines 2377 to 2390) is a harness agent in the ADR 004 harness with code-writing agents out of scope, matching ADR 010 decision 1 and the change request. F16 is stricter than the requirement, so there is no behavioural conflict and nothing for the planning to change; moving the parenthetical belongs to the approved requirements, which only the human may edit in the next Grill pass.
- Round 5, ESCALATE: MIN2 [minor] Approved requirements still list unresolved questions 1 to 4 as open although each is settled (carried from rounds 1 to 4, escalated; concerns the approved requirements). Verified: docs/PROJECT_REQUIREMENTS.md lines 572-587 still list questions 1 to 4 as open and line 337 still points the CI-key question to Unresolved questions, while docs/architecture.md lines 686-690 record each as settled (F09 with the OpenAI default, ADR 006, F10, F11) and the stay-open table at lines 702-706 holds only questions 5 to 7. The planning documents are consistent; the fix is to the approved requirements, which the planner may not change. The human should mark questions 1 to 4 as settled in the next Grill pass. Same decision as rounds 1 to 4.
- Round 5, ESCALATE: S1 [suggestion] The approved requirements group counterexample hunting with coding-agent exercises, while F16 is an allowlisted harness agent replayed in CI (carried from rounds 3 and 4, escalated; concerns the approved requirements). Verified: docs/PROJECT_REQUIREMENTS.md line 420-421 groups counterexample hunting with agent-assisted simulation development and Lean proof generation as coding-agent exercises, while the roadmap's F16 and ADR 010 decision 1 treat it as an allowlisted ADR 004 harness agent replayed in CI, which is stricter and matches the change request. No behavioural conflict exists and the planning is correct as written; only the parenthetical in the approved requirements can mislead, and the planner may not edit it. The human should move counterexample hunting out of that parenthetical in the next Grill pass. Same decision as rounds 3 and 4.
- Round 6, REJECT: MIN1 [minor] The approved requirements changed after their recorded approval without a new approval record (resolves the escalated MIN2 and S1 of rounds 1 to 5; concerns the approved requirements and the process). Decided by the project owner. The owner asked for these two edits to the requirements to resolve the findings escalated in rounds 1 to 5, and the reviewer confirms they are correct. The owner approves the requirements as they are with the approval of this planning, which covers docs/PROJECT_REQUIREMENTS.md and is recorded in docs/PLANNING_APPROVAL.md; no separate approval record is added.
- Round 6, DEFER: MIN2 [minor] F45 and F46 add lessons that use F37's method tags and are expected in format 2, but depend only on F10, so they can land before the fields and the format exist. Decided by the project owner. The gap is real: F45 and F46 need the method tags of F37 and lesson format 2 of F28. It is handled when their Issues are created: F45 and F46 are not started before F37 and F28 are delivered. Changing the roadmap now would need another review round.
- Round 6, DEFER: S1 [suggestion] F57 says F25 places the canonical sentence on the home page, while F57's own check and criterion 1 require it there at F57's acceptance. Decided by the project owner. F57 adds the sentence and the link to the current home page and F25 keeps them when it rewrites the page; the wording in F57 is corrected when its Issue is created.
- Round 6, DEFER: S2 [suggestion] Labs whose datasets are survey-only after F50 need a later feasibility gate, and the roadmap places that gate "under F50" although F50 will be closed by then. Decided by the project owner. The gate procedure is clear; which Issue runs a later feasibility spike is decided when F52 or F53 is planned, as its own Issue and not by reopening F50.
- Round 6, REJECT: S3 [suggestion] The approved requirements' "Offline builds" line is still broader than the install-time carve-out the architecture and ADR 003 rely on (carried from round 3 MIN6; concerns the approved requirements). Decided by the project owner. There is no behavioural conflict: the Mathlib cache is an install-time fetch that ADR 003 records, and the planning documents read the offline-builds line consistently.
