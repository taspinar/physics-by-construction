# Planning Approval

Status: Approved
Approved at: 2026-10-19T11:55:48Z
Planning branch: planning/risk-proportionate-workflow
Change request: docs/changes/risk-proportionate-workflow.md
Final review: round 6, PASS, by claude (opus)
Planning fingerprint: 76efaed007bf95a542e49b4100380f5ef8dd8ece

Recorded by `scripts/finish-planning.sh`. The approval covers these planning
documents. A change to the description, the requirements, a change request, or the
roadmap makes it stale; the architecture and the ADRs may be updated by features
(`./scripts/finish-planning.sh --check`):

- `docs/PROJECT_DESCRIPTION.md`
- `docs/changes`
- `docs/PROJECT_REQUIREMENTS.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/decisions`

## Updates by merged work

These commits changed the architecture or the ADRs between approvals, each
under its own review. This approval covers the documents including them.

- 09a1050 F28 — Lesson format 2, the reference register, and the M1 pilot (Issue #52; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #52)
- 89647be F50 — Experimental dataset registry and feasibility gate (Issue #51; review: round 1, PASS WITH MINOR FINDINGS, by codex (gpt-6-luna); triage published on #51)
- 192ab2b F25 — Homepage narrative: Construct, Investigate, Verify (Issue #56; review: round 1, PASS, by codex (gpt-6-luna))
- 575441f F26 — Generated prerequisite graph (Issue #53; review: round 1, PASS WITH MINOR FINDINGS, by codex (gpt-6-luna); triage published on #53)
- 9dda90c F41 — Self-hosted search (Issue #55; review: round 1, PASS, by codex (gpt-6-luna))
- 51f4af7 F42 — Before you begin, and the glossary (Issue #58; review: round 1, PASS, by codex (gpt-6-luna))
- 49b227b F46 — Scientific code verification and debugging (Issue #62; review: round 3 (changes since round 2 only), PASS, by codex (gpt-6-luna); triage published on #62)
- 7ec0cd0 Leave code and printed output out of the search index
- e357f11 Measure the page payload reliably and raise its limit to 3 MB
- 7c97567 F13 — Self-check quizzes and browser-local progress (Issue #89; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #89)
- bcca871 F18 — Multi-agent scientific review (Issue #88; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #88)
- 704b905 F14 — Adaptive recommendations (Issue #94; review: round 1, PASS, by codex (gpt-6-luna))
- c8b7cbc F21 — Interactive Lean exercises (Issue #90; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #90)
- b0eb183 Raise the budget of the search index to 1 MB
- 3e41817 F51 — Experimental methods and visualization foundations (Issue #102; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #102)
- 787f1ad F51 follow-up — the dataset check of a figure cannot be bypassed (Issue #115; review: round 3 (changes since round 2 only), PASS, by codex (gpt-6-luna); triage published on #115)
- add23db F19 — Scientific evidence map (Issue #111; review: round 3 (changes since round 2 only), PASS, by codex (gpt-6-luna); triage published on #111)
- 2be53d4 Record the raised limit in the test and the architecture
- 48e95dc F43 — Science-first visualization components (Issue #121; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #121)
- 893320f F20 — Autonomous experimental design (Issue #128; review: round 1, PASS, by codex (gpt-6-luna))
- 42397f5 Run verification in parallel CI jobs behind one required check (F58, step 3) (Issue #130; review: round 4 (changes since round 3 only), PASS, by codex (gpt-6-astra); triage published on #130)
- d77d976 Record the measured run times of the parallel jobs (F58, step 4) (Issue #130)
- 8968711 Make the timeout and the measured state consistent across the records
- 7ae72f2 F62 — Eight courses and the reference curriculum (Issue #148; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #148)
- fd47641 F63 — Verified lesson previews (Issue #153; review: round 2 (changes since round 1 only), PASS, by codex (gpt-6-luna); triage published on #153)
- d9a2d9f CI workflow with a verified base artifact, and documentation (F61, steps 7 and 8 of 9, partial) (Issue #147; review: no independent review (low risk: partial delivery, steps 7 and 8 of 9, approved by the owner on 2026-10-14; independent review round 1 found only M1 (AC1, AC2, AC9 need the measurements of step 9) and M2 (AC4 and AC8 need the merged workflow and live evidence), both open by design, and no finding on the workflow itself; the complete feature gets the full independent review at the end))
- abef2a3 F70 — Thermodynamics and statistical physics: random walks, kinetic theory, entropy (T1, T2, T3) (Issue #169; review: round 5, PASS, by codex (gpt-6-luna); triage published on #169)
- 3121b52 F68 — Advanced mechanics: chaos, Lagrangian and Hamiltonian mechanics, resonance (M9 to M12) (Issue #168; review: round 6, PASS, by codex (gpt-6-luna); triage published on #168)
- 3743037 F64 — Learning Path redesign: course-first, compact, accessible (partial: criteria 6 and 8 are manual verifications) (Issue #167; review: no independent review (low risk: partial delivery of F64 (variant B of the owner, 2026-10-14): an independent review was run and its only open findings M1 (criterion 6, screen reader pass) and M2 (criterion 8, visual review) are the manual verifications the owner decided to keep open; M3 (what the reader builds) was fixed; the Issue stays open until both verifications are recorded on it))
- 18b5ecd Record the owner's decisions of 2026-10-15: interim full-run gate of 60 minutes, and ADR 017 decisions 7 and 8
- 2e0e24d Accept ADR 014 decisions 1 to 10; keep decision 11 paused and unaccepted
- 6825641 F119 — Remove redundant verification and blanket local build obligations (partial: the post-merge measurements of criteria 3, 5 and 6 follow the merge) (Issue #185; review: no independent review (low risk: partial delivery of F119, approved by the owner on 2026-10-16; an independent review ran in two rounds: round 1 found M4 (targeted reuse against the current base), fixed and covered by tests; round 2 has only the post-merge measurements and the live one-lesson finish and review evidence (criteria 3, 5 and 6) open, which need the merged workflow and a new base; the full ./scripts/verify.sh passed on this content; the measurements are made after the merge together with criterion 1 of F61 and recorded in docs/release-readiness.md))
- 1d4bf17 F117 - Run this experiment: an experiment entry point per lesson, learner instructions without a website build (partial: criteria 7 and 8 follow the merge) (Issue #202; review: no independent review (low risk: the only open major is process evidence for criteria 7 and 8 that can only exist after the pull request and the merge; two complete reviews were done and every real finding was resolved (owner's explicit word, 2026-10-17)))
- a660d90 F66 - Law discovery lessons: black-box force laws (D1, D2, D3), built to the F117 experiment contract (Issue #189; review: no independent review (low risk: the only major of review round 1 was the F117 experiment contract, which is now merged and applied; round 2 on the complete content had no findings; round 1 can no longer be triaged because it is stale (owner's explicit word, 2026-10-17)))
- a0c284f F122 - Governed visual agent skills: the audited, pinned skills (frontend-design vendored, impeccable as a project-owned SKILL.md over unmodified references, diagram-design as a thin adapter), the PBC Scientific Visualization skill, the skills-config check and the workflow contract (partial: criterion 7, the owner's approval of the contract and the diff, follows) (Issue #215; review: no independent review (low risk: the only open major finding is the owner's own pending approval of the contract and the diff (criterion 7); two review rounds were done and every other finding was resolved (owner's explicit word, 2026-10-18)))
- 1e86974 F61 M2: the lesson digest follows every real dependency (paths exported by pbc modules outside data/), and an exported constant it cannot resolve makes the lesson count as depending on everything (Issue #212; review: round 2, PASS, by codex (gpt-6-luna); triage published on #212)
- 6010f02 F120 - The staged evidence for incremental main: identical inputs give different numerical results on GitHub runners (two byte classes), the chain-provenance prototype, and the owner's decision to amend ADR 017 without accepting it (partial: the final acceptance is parked) (Issue #196; review: no independent review (low risk: review round 5: criterion 7 is the owner's final acceptance decision, pending by design, and the recorded runner facts are not validated by a prototype that nothing calls, which is recorded as a known limitation; five review rounds were done and every other finding resolved (owner's explicit word, 2026-10-19)))
- e1900cd Search index: one budget of 3.5 MB for the planned curriculum (derived from the measured size per lesson and the measured query times, with checkpoints at 60 and 90 lessons), and the Learning path page is no longer indexed (Issue #223; review: round 1, PASS, by codex (gpt-6-luna))
- 9b43ac2 F61 M1: a difference in any non-HTML file of the site record selects every page for the per-page checks (and no lesson for execution), with a dated amendment note in ADR 014 decision 3 (Issue #213; review: round 2, PASS, by codex (gpt-6-luna); triage published on #213)

## Review rounds

- Round 1: CHANGES REQUIRED, 7 finding(s), by claude (opus)
- Round 2: CHANGES REQUIRED, 3 finding(s), by claude (opus)
- Round 3: PASS WITH MINOR FINDINGS, 2 finding(s), by claude (opus)
- Round 4: PASS WITH MINOR FINDINGS, 1 finding(s), by claude (opus)
- Round 5: PASS WITH MINOR FINDINGS, 1 finding(s), by claude (opus)
- Round 6: PASS, 0 finding(s), by claude (opus)

## Escalations confirmed as resolved

- Round 1: MIN2 The planning change's acceptance criterion for 'the policy updates' is deferred to F130 rather than met
- Round 4: MIN1 Concerns the approved requirements: the planned exception for the merge approval gate departs from requirements decision 39, which says features in progress finish under the contracts they started with, and nothing records the owner's acceptance of that departure

## Findings that were not adopted

- Round 1, ESCALATE: MIN2 [minor] The planning change's acceptance criterion for 'the policy updates' is deferred to F130 rather than met. Verified: change request sections 5 and 7 make the updates of .agents/policies/autonomy.md and the Definition of Done of AGENTS.md part of the planning change's acceptance, and requirements decision 39 says both 'refer to ADR 020 and define the levels and the evidence states'. The planner's file scope (scripts/lib/scope.sh; the revision contract: the architecture, the roadmap, and the ADRs) excludes both files, so this planning cannot meet that criterion itself; the roadmap's reconciliation notes and F130's acceptance criterion 10 record the deferral, but the owner has not decided it. Only the owner can either accept the deferral to F130 (the recommendation: both are protected workflow files that change with the scripts, F130 is Level 3 with the owner's approval, and until it merges every feature finishes under the contract it started with, so no feature runs under conflicting rules) or authorize a small owner-approved edit of the two files outside the planner's scope in this cycle. The owner's approval of this decision is the acceptance of the deferral, which phase 2 then records as a dated note in ADR 020's status and the roadmap's reconciliation notes.
- Round 4, ESCALATE: MIN1 [minor] Concerns the approved requirements: the planned exception for the merge approval gate departs from requirements decision 39, which says features in progress finish under the contracts they started with, and nothing records the owner's acceptance of that departure. Verified: the preamble of requirements decision 39 (docs/PROJECT_REQUIREMENTS.md, 'Decided during the change cycle risk-proportionate-workflow') says without qualification that 'features already in progress finish under the contracts they started with', and the change request's section 8 says the same. ADR 020's Status, the Phase 7 rules, F130's in-scope item for the protected list, the F123 row of the state section, and the architecture's verification-matrix section all state 'one stated exception, the merge approval gate': the wider protected list of guardrails.conf and the code-owner rule of decision 3 apply to every pull request finished or published after F130's merge, including features started before it. The exception is technically correct and was adopted to resolve round 3's MIN1: scripts/check-guardrails.sh reads the list from the base branch at the check by the file's own design, and GitHub enforces CODEOWNERS at the merge whatever day the feature started, so grandfathering by merge base would change nothing at the merge and would let a feature choose the rules it is checked by. But it is a departure from the approved requirements sentence, and the revision contract says the planner may not resolve a finding by departing from the requirements on its own word; only the owner can accept it. The planner cannot adopt this finding, because adopting would mean either recording an owner acceptance that has not been given or removing the exception and leaving the planning silent about a behaviour that will in fact apply to F123, which round 3 already judged unacceptable. The owner has three choices: accept the exception as stated (the recommendation, since it adds only the owner's approval of the diff and changes no verification tier, no review, and no evidence a feature in flight must produce, and since the alternative cannot be enforced at the merge); amend the requirements sentence through re-approval so that it names the merge-gate exception; or reject the exception and ask for a grandfathering mechanism, which the planning explains cannot hold at the merge. As with round 1's MIN2 for the autonomy.md/AGENTS.md deferral, the owner's approval of this decision is the acceptance of the exception; phase 2 then records it as a dated note in ADR 020's Status that names the approval and its time, mirrors the note in the roadmap's Phase 7 rules and reconciliation notes, and keeps the wording identical across ADR 020, Phase 7, F130, the F123 row, and the architecture. The requirements are not edited for it unless the owner chooses the second option.
