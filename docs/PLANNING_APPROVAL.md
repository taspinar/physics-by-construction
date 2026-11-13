# Planning Approval

Status: Approved
Approved at: 2026-11-13T20:44:04Z
Planning branch: planning/reapproval-2026-11-13
Final review: round 8, PASS, by claude (opus)
Planning fingerprint: 3fabd4f8ece19eab5a617a54d2f3a968e6f10be3

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
- a17763f F67: three symbolic-regression lessons (agents-llm 08 to 10): symbolic regression, discovering differential equations, and equations from noisy trajectories, with their experiments and tests (Issue #190; review: round 2, PASS, by codex (gpt-6-luna); triage published on #190)
- 3e21eb3 Record the owner's capacity decision: the interim full-run capacity from 45 to 64 lessons, with the build timeout at 60 minutes and the re-measurement points (#258) (Issue #253; review: round 4, PASS, by codex (gpt-6-luna); triage published on #253)
- a2ebc9a Payload budget of the learning path page with its previews: from 3 MB to 4 MB (the owner's decision of 2026-10-23) (#265) (review: round 2, CHANGES REQUIRED with one major (the path page on its own still has the generic 3 MB limit, which it meets at about 1.9 MB; the 4 MB the owner decided is for the page with its previews), by codex. The review is not a PASS. Committed by hand with the owner's explicit exception (Issue #264) because finish-feature.sh refuses a latest review with a major finding.)
- f86cd65 Capacity decision: the interim full-run capacity from 64 to 110 lessons, with the build timeout at 90 minutes (the owner's decision of 2026-10-24) (#281)
- e084498 F82 - Discovering conservation laws and invariants (#300)
- 3e23775 Payload budget of the learning path page with its previews: temporarily from 4 MB to 4.5 MB (#323) (Issue #318)
- 1b9ae76 Learning path page: lighter previews, and the budget back to 4 MB (#330)
- 8428563 F137 - The capstone evidence contract and the final-evaluation pilot on one existing task (#366) (Issue #359; review: round 4, PASS, by claude (opus); triage published on #359)
- 0b345d9 Capacity: raise the timeout of the build job from 90 to 120 minutes (#386) (Issue #373; review: round 4, PASS, by claude (opus); triage published on #373)
- 255bb0e F138 - The instrument contract and the simulator vertical slice of the Autonomous Physics Lab (#387)
- db9ef96 Lesson time budgets as one rule: a warning from 30 s, a limit of 60 s, one exception (#383) (#398)
- 6ab0550 Process document: one current-state text for the verification, risk and review rules (#404, part of #396) (#413)
- 73c89b7 ADR 007 addendum: Apache-2.0 and CC BY-SA as equivalent permission, and the readers for MAT, XLSX, FITS and CIF (#417) (#427)
- d64bc1d Protected list and verification architecture: architecture.md at Level 2 by path, the prompts other than reviewer.md sensitive, F113 deferred (#412, points 1, 3 and 5 of #396) (#432)
- 76d9675 F157: the learning journey as one source for the Course Atlas and About (#436) (#445)
- 1a170aa Gates, PR 1 of 3 (D12): administrative findings stop costing review rounds; review and verification evidence stay blocking (#468)
- f8acb8e F158: Home orients a first-time visitor with one of four Part A hero images and the first step (#466)
- ad7f658 Gates PR 2 of 3 (D10, D11): a removed or changed scientific claim is a detected escalation trigger; a unit test pins execute freeze and cache (#464) (#474)
- 769a2bb Gates PR 3 of 3: the triage and check scripts, store.py and lean.py are protected, verify.conf is read by the builtin rule, and the paths a check rests on are sensitive; the lists and the tests agree (#465) (#476)
- ff9c3c3 Home: copy and structure (#481) (#484)
- d1be840 Home: the hero as one large fluid-dynamics illustration (#482) (#485)
- 3b6b5ab Course Atlas: inline expanding courses, simpler introduction, lesson rows and progress (#483) (#486)
- b2e5079 Home: the hero is the double-pendulum illustration, wider, with the left side faded into the page (#487) (#490)

## Review rounds

- Round 1: CHANGES REQUIRED, 5 finding(s), by claude (opus)
- Round 2: PASS WITH MINOR FINDINGS, 3 finding(s), by claude (opus)
- Round 3: PASS WITH MINOR FINDINGS, 1 finding(s), by claude (opus)
- Round 4: PASS WITH MINOR FINDINGS, 1 finding(s), by claude (opus)
- Round 5: PASS WITH MINOR FINDINGS, 2 finding(s), by claude (opus)
- Round 6: PASS WITH MINOR FINDINGS, 1 finding(s), by claude (opus)
- Round 7: PASS WITH MINOR FINDINGS, 1 finding(s), by claude (opus)
- Round 8: PASS, 0 finding(s), by claude (opus)

## Escalations confirmed as resolved

- Round 1: M1 Concerns the approved requirements: the Home hero files are registered without a licence, but the requirements require a licence for all interface artwork
- Round 1: MIN3 Concerns the approved requirements: 'Data and persistence' still has the learning journey used by the atlas
- Round 1: S1 Requirements were edited after approval while 'Approved at' still shows 2026-11-04
- Round 2: MIN2 Concerns the approved requirements: decision 43 and the textbook 'Later phases' bullet still describe the journey on the atlas and a hero picked from four images, without the #482/#483/#487 notes

## Findings that were not adopted

- Round 1, ESCALATE: M1 [major] Concerns the approved requirements: the Home hero files are registered without a licence, but the requirements require a licence for all interface artwork. The approved requirements ('Visual asset classes' C, 'Data and persistence', decision 41) require a licence for every interface raster. Since Issue #487, ADR 021 and the architecture register the hero without one. To resolve this, the owner must either amend the requirements to state the hero exception and which licence the hero image is under (or that it is excluded from CC BY 4.0), or decide to register the hero under the content licence. The planner cannot change the requirements, and must not silently depart from them, so this needs a human product decision.
- Round 1, ESCALATE: MIN3 [minor] Concerns the approved requirements: 'Data and persistence' still has the learning journey used by the atlas. The contradiction is in docs/PROJECT_REQUIREMENTS.md itself: the 'Data and persistence' atlas bullet still says the journey is used by the atlas. Only the owner may edit the approved requirements, so the note 'since Issue #483, used by About only' needs the owner's requirements edit. The planning documents already follow #483.
- Round 1, ESCALATE: S1 [suggestion] Requirements were edited after approval while 'Approved at' still shows 2026-11-04. The 'Approved at' header and status block of docs/PROJECT_REQUIREMENTS.md are part of the owner's approval record, which the planner may not change. Whether this reapproval updates the timestamp or adds a line listing the dated owner decisions since 2026-11-04 (Issues #462, #481, #482, #483, #487) is the owner's call.
- Round 2, ESCALATE: MIN2 [minor] Concerns the approved requirements: decision 43 and the textbook 'Later phases' bullet still describe the journey on the atlas and a hero picked from four images, without the #482/#483/#487 notes. The finding is valid, but all the stale text is in docs/PROJECT_REQUIREMENTS.md: decision 43's 'The learning journey' and 'Home' bullets, and the textbook bullet in 'Later phases'. Under the revision contract the planner may not change the approved requirements, so only the owner can make this edit. The reviewer also places it at the owner's next requirements edit. Meanwhile the planning documents follow the newer dated notes in the requirements (#482, #483, #487).
