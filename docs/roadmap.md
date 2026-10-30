# Roadmap

Project direction for Physics by Construction, derived from the approved
`docs/PROJECT_REQUIREMENTS.md` (approved 2026-10-06, re-approved on
2026-10-09 with the change request `docs/changes/physics-next-phase.md`,
on 2026-10-12 with the change request
`docs/changes/final-curriculum.md`, on 2026-10-15 with the change
request `docs/changes/pbc-planning-change-four-workstreams.md`, on
2026-10-17 with the change request
`docs/changes/scientific-atelier-atlas.md`, on 2026-10-19 with the
change request `docs/changes/risk-proportionate-workflow.md`, and on
2026-10-30 with the change request
`docs/changes/site-navigation-and-atlas.md`) and consistent with
`docs/architecture.md` and ADRs 001 to 021.

Keep this high-level. GitHub Issues are the actionable backlog and the source
of truth for a feature once its Issue exists. Each feature below has a stable
ID; `./scripts/create-feature-issue.sh <ID>` copies its block into an Issue.
Detailed implementation plans are written just in time under `.agents/plans/`
when a feature becomes active, not here.

This roadmap does not choose which feature is active. It records dependencies;
the human picks the next feature among those whose dependencies are done.
Review the later-phase features against the current architecture before
starting them.

## State at the change cycle `physics-next-phase`

Checked on 2026-10-09 at the base commit `2f011ea` of the planning branch
`planning/physics-next-phase`:

- **F01 to F12 are delivered, F10 pending the human release steps.** Their
  pull requests are merged and the site publishes eleven lessons in four
  strands. The Issues of F01 to F09, F11, and F12 (#3, #7, #12, #15, #18,
  #21, #23, #25, #24, #30, #31) are closed. F10's Issue #29 was closed on
  GitHub on 2026-10-09, as read when this revision was written, although
  `docs/release-readiness.md` expects it to stay open until the release tag
  exists; no release tag and no GitHub release existed on that date, so
  F10's criterion 7 (a release tag for the MVP) is still open. The remaining
  items are the human steps recorded in `docs/release-readiness.md`: the tag
  (`mvp-v1.0.0` on the merge commit), the release note, and the follow-up
  Issues for the two accessibility observations and the style differences.
  Those steps are not roadmap features; the features that depend on F10
  need its delivered site and audit, not the tag. Two deferred review
  findings are open as Issues #8 and #34.
- **F13, F14, and F15 have no Issue.** Their blocks below are unchanged by
  the change cycle; the next-phase features that touch the same ground (F28
  self-checks, F38 hints, F26 and F27 on the path page, F15's course topic)
  name them as neighbours instead of widening them.
- **The MVP blocks F01 to F12 are records**, kept as they were approved and
  delivered. A feature that changes what one of them delivered is a new
  feature below that names it as a dependency.

**Feature IDs of the change cycle.** The change request discussed candidates
F16 to F56. Where a candidate became a feature, it keeps its candidate number
as its final ID, so that the discussion history stays traceable. The numbers
of candidates that were merged into another feature or deferred (F24, F48)
are retired and are never assigned to anything else. Features the change
cycle adds without a candidate number take the next unused IDs from F57
onward. The section "Candidate mapping" records every candidate's outcome.

## State at the change cycle `final-curriculum`

Checked on 2026-10-12 at the base commit `0580b3a` of the planning branch
`planning/final-curriculum`, against the repository, `gh issue list
--state all`, and `gh pr list --state all`. This is the reconciliation
report that section 9 of `docs/changes/final-curriculum.md` asks for; the
files are the truth, this section is their summary at that commit.

### Published lessons and their slots

Twenty-two lessons are published, all with `course: mechanics`, in the
four strands. The slot labels are the curriculum labels of the change
request (ADR 013); eighteen lessons fill a slot (seventeen take their
`slot` in F62, the gas lesson T0 in F70 together with its course) and four
are Lean lessons beyond the one Lean slot of the baseline.

| Lesson directory under `site/lessons/` | `id` | Strand, order | Methods | Feature | Slot |
|---|---|---|---|---|---|
| `mechanics/01-kinematics-as-a-program` | `kinematics` | mechanics 1 | simulation | F02 | M1 |
| `mechanics/02-newtons-laws` | `newtons-laws` | mechanics 2 | simulation | F04 | M2 |
| `mechanics/03-projectile-motion-with-drag` | `projectile-with-drag` | mechanics 3 | simulation | F04 | M3 |
| `mechanics/04-harmonic-oscillator` | `harmonic-oscillator` | mechanics 4 | simulation | F05 | M4 |
| `mechanics/05-numerical-integrators` | `numerical-integrators` | mechanics 5 | simulation | F05 (editorial F30) | M5 |
| `mechanics/06-energy-conservation` | `energy-conservation` | mechanics 6 | simulation | F06 | M6 |
| `mechanics/07-momentum-and-collisions` | `momentum-and-collisions` | mechanics 7 | simulation | F06 | M7 |
| `mechanics/08-kepler-orbit` | `kepler-orbit` | mechanics 8 | simulation | F06 | M8 |
| `mechanics/09-verifying-scientific-code` | `verifying-scientific-code` | mechanics 9 | simulation | F46 | AI2 (physics reasoning path; a mechanics lesson, no agent) |
| `mechanics/10-automated-analysis-pipelines` | `automated-analysis-pipelines` | mechanics 10 | simulation, measured-data | F47 | R1 (autonomous research path) |
| `mechanics/11-gravitational-wave-strain` | `gravitational-wave-strain` | mechanics 11 | measured-data, simulation | F60 | M16 (designated lab; primary home mechanics) |
| `mechanics/12-inverse-physics-parameter-discovery` | `inverse-physics` | mechanics 12 | simulation, measured-data | F23 | D6 (law discovery path) |
| `agents-llm/01-an-agent-runs-an-experiment` | `agent-experiment` | agents-llm 1 | simulation, llm-agents | F09 | AI0 |
| `agents-llm/02-a-counterexample-hunter` | `counterexample-hunter` | agents-llm 2 | simulation, llm-agents | F16 | AI3 |
| `agents-llm/03-three-reviewers` | `scientific-review` | agents-llm 3 | simulation, llm-agents | F18 | AI4 |
| `agents-llm/04-an-experimental-design-agent` | `experimental-design-agent` | agents-llm 4 | simulation, llm-agents | F20 | D9 (law discovery path) |
| `agents-abm/01-particles-in-a-box` | `particles-in-a-box` | agents-abm 1 | simulation, abm | F11 | T0; at `0580b3a` no `slot` until F70 sets `slot: T0` and `course: thermodynamics` together (ADR 013 decision 6). Delivered: since F70 (pull request #171, 2026-10-14) the front matter carries `slot: T0` and `course: thermodynamics`, confirmed on `main` at `0c958c8`; address unchanged |
| `lean/01-proving-what-the-simulation-showed` | `proving-what-the-simulation-showed` | lean 1 | lean | F08 | L1 |
| `lean/02-momentum-in-a-collision-proved` | `collision-momentum-proved` | lean 2 | lean | F17 | none: beyond the baseline |
| `lean/03-what-symplectic-euler-conserves` | `symplectic-euler-conserved-energy` | lean 3 | lean | F17 | none: beyond the baseline |
| `lean/04-lean-exercises-on-your-machine` | `lean-exercises-on-your-machine` | lean 4 | lean | F21 | none: beyond the baseline |
| `lean/05-the-chirp-law-proved` | `chirp-law-proved` | lean 5 | lean | F56 | none: beyond the baseline |

Three lessons (`counterexample-hunter`, `scientific-review`,
`experimental-design-agent`) declare no `format`; the format-2 default
flip of F28 is still pending for them and is not a concern of this change.

### Count reconciliation

| Count | Value |
|---|---|
| Reference curriculum (requirements decision 23) | 115 slots: 81 Part A, 33 Part B, 1 Lean |
| Published lessons at `0580b3a` | 22 |
| Published lessons that fill a slot | 18: M1 to M8, M16, T0, AI0, AI2, AI3, AI4, D6, D9, R1, L1; 17 carry `slot` from F62, T0 from F70 with its course |
| Published lessons beyond the baseline | 4 Lean lessons (F17, F21, F56); kept, mapped, never deleted or hidden |
| Slots to fill | 97, of which 6 belong to features that exist without an Issue (AI1 F45, AI5 F55, R4 F49, W7 F52, FL7 F53, EM7 F54) and 91 to the new features of Phase 4 |
| Lessons when the reference curriculum is complete | 119: 115 slots plus the 4 Lean lessons beyond the baseline, plus any further Lean lesson of F22 |
| Designated measured-data labs | 16 (M15, M16, T7, T8, W7, W8, EM7, EM8, FL7, FL8, Q7, Q8, AST8, AST9, MAT5, MAT6); 1 published (M16), 3 with existing features (W7, FL7, EM7), 12 new features |
| Datasets with a go decision | 3 (GW150914 strain, used; Aalborg wave flume, for W8; NPL S-parameters, for EM7) |

115 stays the reference structure (requirements decision 23). The
historical baseline of the change request (11 published, 104 future)
counted one Lean lesson and no agent, pipeline, lab, or inverse-physics
lesson; the actual inventory is reported above and no published lesson is
rebuilt to match a count.

### Features of the previous phases: state and role in the final curriculum

Every feature F01 to F60 keeps its block as approved; the blocks are
history. "Delivered" means the Issue is closed and the pull request
merged. The slot column is the mapping that section 9, point 3, of the
change request asks for; no feature's scope is duplicated.

| Feature, Issue | State at `0580b3a` | Role in the final curriculum |
|---|---|---|
| F01 to F09, #3 to #25 | Delivered | The site, the lesson format, M1 to M8, L1, AI0. |
| F10, #29 | Delivered; release tag still a human step | None. |
| F11, #30 | Delivered | T0 of the thermodynamics course, re-homed by front matter in F70, which sets `course` and `slot` together (ADR 013 decision 6); no slot before F70. |
| F12, #31 | Delivered | The content workflow every lesson feature uses. |
| F13, #89; F14, #94 | Delivered | Progress marks and recommendations that F64 keeps on the redesigned path. |
| F15, no Issue | Not started; **dropped by `final-curriculum`** (ADR 013 decision 7) | Its goal is delivered by F62 and the first lesson feature of each course (F70, F71, F72, F73, F89, F91, F94); its ID is never reused. |
| F16, #87 | Delivered | AI3. |
| F17, #61 | Delivered | Two Lean lessons beyond the baseline (L2, L3). |
| F18, #88 | Delivered | AI4; its reviewers are reused by F110 and F111. |
| F19, #111 | Delivered | The evidence map page; the R2 lesson that teaches it is F109. |
| F20, #128 | Delivered | D9, with the revision-2 enhancement (hypothesis-discriminating information gain) already in its design and judging; no new feature. |
| F21, #90 | Delivered | A Lean lesson beyond the baseline (L4). |
| F22, no Issue | Not started; unchanged | A Lean strand lesson outside the 115 slots; kept as approved. |
| F23, #120 | Delivered | D6, with the revision-2 enhancement (identifiability, parameter correlations, held-out uncertainty) delivered by its fitting helpers and page; no new feature. |
| F25 to F44, Issues #41 to #60, #83 to #86, #99 to #112, and #121 | Delivered | The visual system, metadata, graph, cards, format 2, search, diagrams, and components that F62 to F64 build on without reopening. |
| F45, no Issue | Not started; unchanged | AI1; coordinates with M12 of F68 on the resonance reference solution. |
| F46, #62 | Delivered | AI2 (a mechanics lesson without an agent, in the physics reasoning path). |
| F47, #123 | Delivered | R1. |
| F49, no Issue | Not started; unchanged | R4. |
| F50, #51 | Delivered | The gate every new lab and F88's comparison pass; its process is reused, the Issue is not reopened. |
| F51, #102 (follow-up #115) | Delivered | The shared analysis core of every lab. |
| F52, no Issue | Not started; unchanged | W7; its course is `waves`, created by F71 (reconciled note in its block). |
| F53, no Issue | Not started; unchanged | FL7; its course is `fluids`, created by F73. |
| F54, no Issue | Not started; unchanged | EM7; its course is `electromagnetism`, created by F72; its dataset has a go decision. |
| F55, no Issue | Not started; unchanged | AI5. |
| F56, #129 | Delivered | A Lean lesson beyond the baseline (L5). |
| F57, #49; F59, #101 | Delivered | Identity and the instructor pack; unchanged. |
| F58, #130 (follow-up #138 open) | Delivered | The parallel jobs F61 builds on. |
| F60, #122 | Delivered | M16. |

Retired IDs F24 and F48 stay retired. The seven enhancements of existing
slots named in revision 2 are recorded under "Slot mapping" below: two
are delivered (D6 by F23, D9 by F20), and five belong to the features that
create their slots (AI6 in F96, EV1 in F100, EV2 in F81, R5 in F110, and
the linked Q5/Q8 pair in F90 and F103); none adds a slot.

### Architecture decisions of this change cycle

- **ADR 013** allows all eight courses with fixed identifiers, makes every
  course a strand with the same identifier created by its first lesson
  feature, declares the reference curriculum as data that lessons fill by
  `slot`, derives the four method paths from the slot, validates the
  prerequisite graph as a graph while previous and next stay the reading
  route (a prerequisite may live in a later strand), and reconciles F15
  as dropped. It supersedes decision 4 of ADR 008 and amends its decisions
  1, 3, and 5; every published address, identifier, and link stays.
- **ADR 014** makes a pull request verify what it changed against the
  verified result of `main`, which is restored and never committed, with
  `main` verifying everything; the navigation and the commit a page shows
  are regenerated on every build, and a check is reused only from a base
  the same check implementation produced; a lesson whose inputs cannot be
  followed, a changed shared input, or changed checks make the run a full
  run, and a full run executes the lessons in same-machine lesson shards
  that one assembly turns into the one built site, so that every job fits
  the timeout at 110 lessons. It amends ADR 002 and ADR 012 and is the
  record that ADR 003 decision 6 and ADR 012 decision 8 require. F61
  delivers the selection, with F62, before the first lesson feature of
  this phase; F113 delivers the lesson shards before the lesson count
  passes the lesson-shard size.

No accepted ADR conflicts with the re-approved requirements; ADR 008's
single-additional-course rule is the one decision the requirements asked
to supersede, and ADR 013 does it.

## State at the change cycle `pbc-planning-change-four-workstreams`

Checked on 2026-10-15 at the base commit `0c958c8` of the planning branch
`planning/pbc-planning-change-four-workstreams`, against the repository,
`gh issue list --state all`, `gh pr list --state all`, and the runs of
`.github/workflows/ci.yml` on `main` read from the Actions API. This is the
reconciliation that change 3 of
`docs/changes/pbc-planning-change-four-workstreams.md` asks for
("reconcile with current main rather than blindly replacing numbers"); the
files are the truth, this section is their summary at that commit.

### Published lessons

Thirty-two lessons are published in six strands: the twenty-two of the
table under "State at the change cycle `final-curriculum`" and the ten
below, merged on 2026-10-14. The change request's count of 25 counted the
three thermodynamics lessons of F70 and predates the merges of F68 and
F71 on the same day.

| Lesson directory under `site/lessons/` | `id` | Strand, order | Course | Slot | Feature, pull request |
|---|---|---|---|---|---|
| `mechanics/13-double-pendulum-chaos` | `double-pendulum-chaos` | mechanics 13 | mechanics | M9 | F68, #174 |
| `mechanics/14-lagrangian-mechanics` | `lagrangian-mechanics` | mechanics 14 | mechanics | M10 | F68, #174 |
| `mechanics/15-hamiltonian-mechanics` | `hamiltonian-mechanics` | mechanics 15 | mechanics | M11 | F68, #174 |
| `mechanics/16-resonance` | `resonance` | mechanics 16 | mechanics | M12 | F68, #174 |
| `thermodynamics/01-random-walks-and-diffusion` | `random-walks-and-diffusion` | thermodynamics 1 | thermodynamics | T1 | F70, #171 |
| `thermodynamics/02-kinetic-theory-of-gases` | `kinetic-theory-of-gases` | thermodynamics 2 | thermodynamics | T2 | F70, #171 |
| `thermodynamics/03-entropy-from-ensembles` | `entropy-from-ensembles` | thermodynamics 3 | thermodynamics | T3 | F70, #171 |
| `waves/01-the-wave-equation` | `wave-equation` | waves 1 | waves | W1 | F71, #172 |
| `waves/02-interference-and-resonance` | `interference-and-resonance` | waves 2 | waves | W2 | F71, #172 |
| `waves/03-sound-and-the-doppler-effect` | `sound-and-the-doppler-effect` | waves 3 | waves | W9 | F71, #172 |

The gas lesson `agents-abm/01-particles-in-a-box` carries `course:
thermodynamics` and `slot: T0` since F70 (confirmed in its front matter at
`0c958c8`); its address is unchanged, and the row of the
`final-curriculum` table above records the delivery. By course the
thirty-two lessons are: mechanics 25 (the `mechanics`, `agents-llm`, and
`lean` strands), thermodynamics 4 (T0 to T3), waves 3. Twenty-eight fill
a slot of the reference curriculum (the eighteen of `final-curriculum`,
T0 now with its `slot`, and the ten above); four are Lean lessons beyond
the baseline. Slots to fill: 87 of 115 (97 at `0580b3a`, minus the ten
above). The lesson count when the reference curriculum is complete stays
119. Three lessons (`counterexample-hunter`, `scientific-review`,
`experimental-design-agent`) and `verifying-scientific-code` still declare
no `format`; not a concern of this change.

### Features of Phase 4: state

| Feature, Issue | State at `0c958c8` | Note |
|---|---|---|
| F61, #147 | Open; delivered in steps (pull requests #152, #158, #159, #160, #164, #166) and measured on 2026-10-14 | Criterion 1 was not met at 12 minutes (13 min 50 s to 14 min 43 s); it is judged against 20 minutes since ADR 015, and the record of three consecutive runs is still owed (the three ran at the same time). Criterion 9's projection of the full run was handed to F113 and is not recorded; F118 records the measured full run at the current count (criterion 9 carries a note dated 2026-10-15). The Issue decides what closes it; the Phase 5 features that list F61 as a dependency depend on its delivered selection, base, and regenerated context (pull requests #152 to #166), not on the closure of Issue #147. |
| F62, #148; F63, #153; F65, #154 | Delivered | The curriculum file, the slots, the previews, the discovery foundation. |
| F64, #167 | Open; pull request #176 merged on 2026-10-15 as partial (criteria 6 and 8 are manual verifications) | The human's manual passes remain. |
| F68, #168; F70, #169; F71, #170 | Delivered (pull requests #174, #171, #172, 2026-10-14) | The ten lessons above; the first lessons of the thermodynamics and waves courses created their strands and packages. |
| F113, #150 | **Paused** (requirements decision 35): pull request #175 closed on 2026-10-15 without a merge; the branch `feature/150-bounded-full-verification-same` is preserved; the Issue stays open | Not restarted, not duplicated, not merged before the owner's decision on ADR 017 (proposed). Its block below is kept as approved, with a banner. |
| F112, #151 | Open as a status report | Declares no completion while slots are outstanding. |
| The lesson features F66, F67, F69, F72 to F111 and the Phase 3 features without an Issue | Not started | Every one that takes the lesson count past 32 waits for the amended full-run gate (below). |

Issue #165 ("Select agent models by feature risk") concerns the agent
workflow's configuration and is no roadmap feature. The deferred review
findings #8, #34, #66, and #138 stay open.

### The full run on `main` at the current lesson count

ADR 014 decision 7 budgets 35 minutes for one job of a full run and the
roadmap's full-run gate lets the one `build` job carry at most 32 lessons
before F113. The measured full runs, read from the Actions API on
2026-10-15 (job start to job end; the cache state of each run was not read
from its log, which F118 does):

| Run on `main` | Lessons | Wall clock | `build` | `integration` | Slowest `e2e` |
|---|---|---|---|---|---|
| 38545077253, 2026-10-14 (`docs/release-readiness.md`, warm caches) | 22 | 21 min 59 s | 15 min 42 s | 13 min 58 s | 5 min 25 s |
| 38527223459, 2026-10-14 (`docs/release-readiness.md`, cold caches) | 22 | 29 min 46 s | 23 min 05 s | 13 min 41 s | 6 min 05 s |
| 38607388478, 2026-10-14, after F71 | 28 | 34 min 01 s | 26 min 57 s | 13 min 33 s | 6 min 32 s |
| 38621916706, 2026-10-14, after F68 | 32 | 40 min 48 s (`deploy` 1 min 43 s) | 31 min 15 s | 16 min 08 s | 7 min 30 s |
| 38639021950, 2026-10-14 | 32 | 37 min 27 s | 30 min 32 s | 15 min 28 s | 6 min 26 s |
| 38659296393, 2026-10-15, after F64 | 32 | 27 min 20 s | 21 min 07 s | 12 min 08 s | 5 min 48 s |
| 38687330455, 2026-10-15, after the dependency bump #173 | 32 | 35 min 08 s | 27 min 58 s | 15 min 52 s | 6 min 44 s |

At 32 lessons the `build` job of a full run takes 21 to 31 minutes: within
the 35-minute planning budget by 4 to 14 minutes, and within the
45-minute timeout by 14 to 24 minutes, on the runners of these runs. The
variation between runs of the same size (10 minutes) is larger than the
growth from 28 to 32 lessons, so a cost per lesson is not read off these
runs here; F118 separates it from the cache state and the runner. The
consequence for the roadmap is immediate: the full-run gate of Phase 4
("no lesson feature takes the count past 32 before F113") is reached, and
F113 is paused. **Until the owner decides the interim gate (requirements,
unresolved question 10: an approved timeout for the one `build` job of a
full run, from F118's record, with the lesson count it covers), or ADR
017 is accepted and F121 delivered, or F113 is resumed, no lesson feature
starts.** [Decided the same day, 2026-10-15: 60 minutes for the one
`build` job, up to 45 lessons (ADR 014 status); the sentence is history
since.] The dependency tables keep "F113" and "F113 by the lesson-shard
rule"; the amended gate under "Phase 4" says how to read them. F118 is
therefore the first feature of the verification workstream, and its
measurement record is short work: the runs above exist.

### Architecture decisions of this change cycle

- **ADR 015** records the owner's decision of 2026-10-14: the budget of a
  typical pull request with warm caches is 20 minutes, 15 minutes is a
  non-blocking target, every measurement records both; it amends the
  budget row of ADR 003 decision 5, ADR 012 decision 8, and ADR 014
  decision 7 and changes nothing else. F61's criterion 1 is amended
  accordingly (above).
- **ADR 016** (accepted when this planning is approved) makes the learner
  run a lesson's experiment through a declared, tested entry point and
  removes every instruction to rebuild or preview the website from
  maintained documentation without relocating it; the footer keeps its
  anchor and names the activity; the setup page is organised by activity;
  the page reproduction and the setup-page equality with CI are
  superseded as learner-facing contracts. F117 delivers it.
- **ADR 017** is **proposed and not accepted** by this planning: the
  critical review of an F61-based incremental `main` that the owner asked
  for, with the weaker guarantee stated for the owner's decision after
  the evidence of F118 and F120. ADR 014 decision 11 (F113) is paused;
  decisions 7 and 8 of ADR 017 (proportional local verification, removals
  by coverage) do not depend on incremental `main` and may be accepted
  separately on F118's evidence, which ADR 017's status provides for: a
  partial acceptance is a dated status line naming the accepted decisions
  and the evidence. ADR 017 decision 7 names what it amends on
  acceptance: ADR 012 decision 1, ADR 005 decision 3, and ADR 003
  decision 1 as ADR 005 decision 5 restates it (a recorded targeted run
  is the finish and review evidence of an ordinary change; only a run
  without options is a verification of the content; CI stays the
  publication gate).
- The statuses of ADR 002, ADR 003, ADR 005, ADR 012, and ADR 014 name
  these records; no decision of theirs is rewritten.

### Reconciliation notes

- The change request's F1 to F3 are local labels of the editorial proposal
  and are F114 to F116 here, as successors of the delivered editorial
  features F28 to F31, which keep their blocks.
- The change request's line numbers for the 12-minute statements had
  moved; every current statement of the typical-pull-request budget in
  this roadmap, the architecture, and the ADR statuses was found by search
  and says 20 minutes. The acceptance criteria of the delivered features
  F01 (criterion 10) and F58 (criterion 1) quote 12 minutes as the budget
  of their day; they are records and carry a bracketed note instead of a
  rewrite. The paused block of F113 (the measurement item of "In scope"
  and acceptance criterion 5) carries the same bracketed note, and its
  banner says so.
- The delivered blocks that quote the learner-facing contracts ADR 016
  supersedes carry a bracketed note in the same way and are not rewritten:
  the Phase 4 inherited rule "The definition of done of a lesson"
  (requirements decision 31; the tested "Reproduce this" path), F02's
  user-visible outcome and in-scope item (the "Reproduce this" section
  whose commands regenerate the lesson's results), F39 criterion 2 (the
  equality of the setup page's commands with `ci.yml`), and F40's
  in-scope line (the built-site check of the footer's render commands);
  the "Local execution" row of "Verification strategy for the next
  phase" carries the same note and points at the row of F117.
- The request's "25-minute cold-cache budget", the "45-minute timeout",
  and the per-check budgets are untouched by change 3; change 4 revisits
  the timeout of an exceptional full run through question 10.
- No conflict with the approved requirements was found. Requirements
  decision 30's rule that `main` verifies everything stands until the
  owner accepts ADR 017; decisions 32 to 35 are covered by F114 to F121
  and ADR 015 to ADR 017.

## State at the change cycle `scientific-atelier-atlas`

Checked on 2026-10-17 at the base commit `b4baed1` of the planning branch
`planning/scientific-atelier-atlas`, against the repository, `gh issue
list --state all`, `gh pr list`, and the runs of
`.github/workflows/ci.yml` on `main` read from the Actions API. This is
the refresh that section 10 of `docs/changes/scientific-atelier-atlas.md`
asks for ("all status claims are a dated snapshot and must be refreshed by
the planner before implementation"); the request's reviewed baseline was
`0aedaac`, one merge earlier. The files are the truth, this section is
their summary at that commit.

### Published lessons

Thirty-two lessons in six strands, the same as at `0c958c8` (the tables
under the two previous states): twenty-eight fill a slot of the reference
curriculum, four are Lean lessons beyond the baseline, 87 of 115 slots
are open, and the count when the curriculum is complete stays 119. F117
(pull request #205, merged 2026-10-17) added no lesson: it gave every
lesson a tested experiment entry point and the "Run this experiment"
footer, and changed no lesson text, printed output, number, or figure
(its pull request shows the pages unchanged in text, printed output, and
pixels). Two lesson pull requests are open, both built to the F117
contract: F66 (#208, D1 to D3) and F72 (#207, EM1 to EM3); if both merge
the count is 38, within the interim full-run gate of 45 lessons.

### Features: state

| Feature, Issue | State at `b4baed1` | Note |
|---|---|---|
| F117, #202 | Pull request #205 merged on 2026-10-17 as partial: criteria 7 (a reviewer's clean-machine walkthrough) and 8 (the measured first full run after the switch) follow the merge; the Issue is open with the follow-ups #203 and #204 | The first run on `main` after the merge (39010505705) had a `build` job of 17 min 11 s with the experiment check in it and failed in the `code` job on the stochastic unit test `tests/unit/test_particles_in_a_box_experiment.py` (Issue #206, filed by the owner); it published no base and deployed nothing, so the latest successful run on `main` is 38930410769 at `0aedaac`, whose base pull requests keep using (a base is accepted by the record of its run, never by recency). Until #206 is fixed no run on `main` passes. Criterion 8's record is the first passing full run after the switch. ADR 016's status records the delivery. |
| F114, #181 | Open; the style guide `docs/editorial-voice.md` merged (pull request #183) | The editorial programme is not complete: the guide is a draft until F116, and F115 (the pilot on mechanics 01 to 05 with the owner's approval) and F116 (the integration) have not started. |
| F118, #180; F119, #185 | Delivered; the F119 measurements after the merge are recorded (pull request #199, `docs/release-readiness.md`) | ADR 017 decisions 7 and 8 are accepted and applied; the three tiers are in use. |
| F120, #196 | Open; the staged evidence is recorded on the branch and the Issue; the owner's comment of 2026-10-16 supports incremental `main` in principle and asks for stronger enforced environment identity, runner-equivalence evidence, chain limits, provenance, fail-closed full verification, and a weekly full audit; no pull request is open | F121's preparation is permitted, its activation is not approved; ADR 017 decisions 1 to 6 and 9 stay proposed. `main` is not incremental. |
| F113, #150 | Paused, not closed, not superseded | A fallback decision, not a task to restart. |
| F61, #147 | Open; the selection is delivered and measured | Closure reconciles its remaining evidence on the Issue; the features that depend on F61 depend on the delivered selection. |
| F64, #167 | **Closed**; delivered | The dated four-workstreams state said the manual checks were outstanding; the Issue is closed since. F125 and F126 build on the page, never reopen it. |
| F62, #148; F63, #153; F65, #154; F68, #168; F70, #169; F71, #170 | Delivered | The curriculum file, the slots, the previews, the discovery foundation, and the first lessons of thermodynamics and waves; all built on by this cycle. |
| F25, #56; F26, #53; F44, #45; F57, #49 | Delivered | The home narrative, the prerequisite graph, the visual system, the identity: built on, not reopened (requirements decision 36). Their blocks carry a note where decision 37 supersedes an out-of-scope line. |
| F66, #189; F72, #187 | Open, with the pull requests #208 and #207 | Lesson features of waves C1, within the interim gate. |
| F67, #190; F73, #188 | Open, no pull request | Lesson features of wave C1. |
| F112, #151 | Open as a status report | Cannot declare completion with 87 slots open. |
| The deferred findings #8, #34, #66, #138 and the workflow Issue #165 | Open | Assessed for applicability when relevant; not prerequisites of a lesson or of the atelier. |
| #206 (new, 2026-10-17) | Open; a lesson fix, not a roadmap feature | Replaces the single-sample threshold of the gas lesson's pressure test by a statistically justified verification; until it merges, no run on `main` passes. It precedes the atelier in practice, because every feature of this cycle needs a passing `main` for its base and its deployment. |

### The verification gate

The owner's interim full-run gate (ADR 014 status, decided 2026-10-15):
the one `build` job of a full run has a 60-minute timeout with a
50-minute planning budget, approved for up to 45 lessons. The sentence of
Phase 4 "no lesson feature takes the count past 32 before F113" is
therefore superseded, as the Phase 4 gate paragraph now says: a
dependency entry "F113" or "F113 by the lesson-shard rule" is satisfied
for every lesson feature that keeps the count at or below 45; past 45 the
gate needs a further decision of the owner, or ADR 017 accepted and F121
delivered, or F113 resumed. F117 added a fourth execution of every lesson
to the `build` job; the one measured run (39010505705, 17 min 11 s, cache
state not read) is below the earlier 21 to 31 minutes, and F117's
criterion 8 records the first passing full run. Reassess the capacity
before the count approaches 45, not when the next lesson would exceed it.
The atelier's features change shared inputs and are full runs on every
pull request (ADR 014 decision 4); they add no lesson.

### Architecture decisions of this change cycle

- **ADR 018** records the scientific atelier as scoped CSS, shared
  templates, and self-hosted fonts on the Quarto baseline of ADR 001; the
  three visual asset classes of requirements decision 37 (interface
  artwork, conceptual illustration, scientific result, with animation
  allowed under conditions) with their sources in the repository; the
  course atlas at the existing path address, generated from the
  curriculum file, the front matter, and one validated map manifest,
  with three explicit edge types, planned content never linked or
  counted, every lesson reachable without scripts, and the atlas's
  controls stored nowhere; the home page with a static verified opening
  figure and without the rejected section; and the three-part rendered
  review. It supersedes the blanket exclusion of decorative imagery and
  animation that the earlier non-goal and the out-of-scope lines of F44,
  F64, and F25 recorded (those blocks stay as history and carry a note).
  It amends one decision of an ADR: condition 2 of the replay-fixture
  decision of ADR 002, under which the committed-artifact check exempts
  the fixture location "and nothing else", gains one declared exemption,
  a provenance-registered authored interface-artwork SVG under
  `site/assets/` (ADR 018 decision 2), the third committed input a build
  cannot regenerate after the replay fixture of ADR 002 and the dataset
  samples of ADR 007; no raster and no other image type is exempt
  anywhere. Otherwise it extends ADR 002 and ADR 013 and supersedes no
  other decision of an ADR. F123 to F127 deliver it; F128 the
  interactive pendulum if the owner decides it.
- **ADR 019** records the agent skills of requirements decision 38 as
  audited, pinned, project-local guidance of the development workflow at
  `.agents/skills/`, never a dependency of the site, the build, the
  deployment, or any CI job and never evidence; the provenance record of
  every third-party skill; the planner, implementer, reviewer, and
  verification contract; the skills configuration check, the one check
  that reads the directory, which fails visibly on a missing skill; and
  the bounded pilots. It extends ADR 006 and ADR 010. F122 delivers it; F123
  to F129 apply it.
- No accepted ADR conflicts with the re-approved requirements. ADR 001
  is reaffirmed; ADR 016's footer contract (the experiment section with
  its anchor) is kept by the shared footer of F123; ADR 014 decision 4
  makes every shared change of the atelier a full run, which the slices
  respect.

### Reconciliation notes

- The change request's delivery slices map to features as follows
  (section 8 of the request; IDs allocated here, none reused): slice A
  (reconciliation) is this planning, with its design specification in
  F123, its map data contract in F125, and its skill audit in F122; A2 is
  F122; B is F123; C is F124; D is F125; E is F126; F is F127, which also
  carries the publication-ready polish of G; G's validated pendulum is
  F128; H is F129. The end-to-end preview the request asks for first is
  the state after F123, F124, F125, and F126 (the home page, the atlas,
  and one existing lesson in the new template), inspected by the owner
  before F127 rolls the design out; it is a gate recorded on the Issues,
  not a feature.
- F25, F26, F44, and F64 are delivered and are built on. The out-of-scope
  lines of F25 ("hero imagery"), F44 ("decorative imagery, any branding
  graphic"), and F64 ("images that are not F63 previews; animation") are
  superseded by requirements decision 37 and ADR 018 for interface
  artwork, conceptual illustrations, the one verified opening figure, and
  accessible animation; each block carries a bracketed note and is not
  rewritten. The F63 preview contract is unchanged; map artwork never
  replaces a preview.
- The owner's answers recorded in the requirements (2026-10-17) narrow
  the request: the home opening ships as a static figure from an
  existing verified implementation (F124), the interactive pendulum is
  its own gated feature (F128, unresolved question 14), the Manim pilot
  is not scheduled (question 15), and each third-party skill's outcome is
  the owner's per-candidate approval (question 13, F122).
- The mockups that chose the direction are references; nothing of their
  equations, plots, counts, or six-region structure enters the roadmap,
  the manifest, or a page (ADR 018 decision 2 and 3).
- Lesson authoring is not blocked by the atelier: the lesson features of
  waves C1 to C4 proceed in their own worktrees within the interim gate;
  the coordination rules under "Phase 6" say how a shared-template
  change and a lesson feature in flight rebase, and no feature of this
  cycle changes a scientific claim, a computed number, a figure's data,
  or a verified artifact.
- The "Later phases" bullets of the requirements for decisions 36 to 38
  are covered by F122 to F129; nothing of the request falls outside the
  approved requirements, and nothing of it is planned around them.

## State at the change cycle `risk-proportionate-workflow`

Checked on 2026-10-19 at the base commit `36e9d3b` of the planning branch
`planning/risk-proportionate-workflow`, against the repository, `gh issue
list --state all`, `gh pr list --state all`, the runs of
`.github/workflows/ci.yml` on `main` read from the Actions API, and the
ruleset of `main` read from the GitHub API. This is the refresh that
section 9 of `docs/changes/risk-proportionate-workflow.md` asks for; the
request was written on 2026-10-18 against an earlier `main`. The files
are the truth, this section is their summary at that commit. The change
request asks for a workflow change and no change to any page of the
site; its requirements decision is 39, its decision record ADR 020, and
its features F130 and F131 (the roadmap's last identifier before this
cycle is F129; none of F130 and F131 was used).

### Published lessons

Thirty-eight lessons in seven strands (mechanics 16, agents-llm 7,
agents-abm 1, lean 5, thermodynamics 3, waves 3, electromagnetism 3):
the thirty-two of the previous state plus the six of F66 (pull request
#208, D1 to D3) and F72 (pull request #207, EM1 to EM3), both merged on
2026-10-17. The count is within the interim full-run gate of 45 lessons;
the re-assessment points of ADR 020 decision 6 (measure at 42, decide at
44) are four and six lessons away.

### Features: state

| Feature, Issue | State at `36e9d3b` | Note |
|---|---|---|
| F117, #202 | **Closed** 2026-10-17; delivered, with the measurement recorded by pull request #210 | The follow-ups #203 and #204 are open as ordinary Issues. |
| F114, #181 | **Closed** 2026-10-17 | The style guide is merged; F115 and F116 have no Issue. |
| F118, #180; F119, #185 | Delivered | ADR 017 decisions 7 and 8 are accepted and applied; the three tiers are what ADR 020 builds on. |
| F120, #196 | **Closed** 2026-10-19; pull request #224 merged as partial (the final acceptance of ADR 017 is parked) | The evidence is in `docs/incremental-main-evidence.md`; the owner amended ADR 017 without accepting it (its status, 2026-10-16). By decision 39 the feature is finished by that publication, and ADR 017 decisions 1 to 6 and 9 stay proposed and paused until the owner's triggers. |
| F121 | No Issue; not started | Conditional on ADR 017's acceptance, which is paused (ADR 020 decision 8); its block carries a dated note. |
| F113, #150 | Paused, open, not superseded | Its block carries a dated note; reopened only at the owner's triggers. |
| F61, #147 | Open; the selection delivered and measured; the follow-ups M1 to M3 (#213, #212, #211) **closed** on 2026-10-17 to 2026-10-19 (pull requests #226, #222, #216) | The base is accepted only for a provable branch push on `main` (the stamped ref of M3), the digest follows every real dependency or falls back to executing (M2), and a non-HTML difference of the site record selects every page (M1): each is part of what ADR 020 decision 9 keeps unchanged. |
| F122, #215 | **Closed** 2026-10-18; pull request #220 merged as partial (criterion 7, the owner's approval of the contract, followed on the Issue) | ADR 019 delivered; the skills are in `.agents/skills/`. |
| F123, #217 | Open since 2026-10-18; no pull request | In progress under the contracts it started with (`AGENTS.md`, ADR 003, 005, 012, 014, 015, and 017 as they stand); nothing of ADR 020 applies to it, except that a pull request it finishes after F130's merge is checked against the protected list of `guardrails.conf` as it then is and needs the owner's approval of its diff when it touches a path that list adds (the stated exception; "Phase 7"). On 2026-10-19 the owner accepted, by approving the round 4 revision of this planning's review (11:42 UTC), that the merge approval gate is the one exception to the rule of requirements decision 39 that a feature in progress finishes under the contracts it started with; the requirements are not edited for it (ADR 020, Status). |
| F124 to F129 | No Issue | Wait for F123 and the preview gate of Phase 6. |
| F66, #189; F72, #187 | **Closed** 2026-10-17; delivered | Six lessons; the count is 38. |
| F67, #190; F73, #188 | Open, no pull request | Lesson features of wave C1, within the interim gate. |
| F112, #151 | Open as a status report | Cannot declare completion with 81 slots open. |
| #206, #218, #219, #223 | **Closed**; lesson fixes and budget decisions, not roadmap features | The statistically justified pressure test (pull request #209); the parallel seeds (#218); the documented 60-second budget of the gas lesson in `scripts/lesson-budgets.conf`, read by both checks (#219, pull request #221), which is the exception table ADR 020 decision 6 names; the search index budget of 3.5 MB (#223, pull request #225). |
| The deferred findings #8, #34, #66, #138 and the workflow Issue #165 | Open | #165 ("Select agent models by feature risk") concerns the agent configuration and may be decided with F130's risk level; it is no roadmap feature. |
| Pull request #227 | Open, from a fork, a README link | Not a feature; outside this cycle. |

### The verification gate and the runs on `main`

Every push to `main` executes and checks every lesson (ADR 014 decision
4, invariant I26). The eight complete runs on `main` from 2026-10-17 to
2026-10-19 at 38 lessons (39065685718, 39079012220, 39161066259,
39164144807, 39192858558, 39198159262, 39204451130, 39226518978, read
from the Actions API as run creation to last update, which includes the
deployment; cache state not read) took 29 min 12 s to 39 min 16 s; the
`build` job of 39079012220 took 20 min 40 s. All are below the 45-minute
trigger at which the owner re-assesses the capacity (ADR 020 decision
6), and the owner's interim full-run gate of 2026-10-15 (60 minutes for
the one `build` job, up to 45 lessons; ADR 014 status) stands. The
verification matrix of that run (five executions of every lesson, three
in a page) is recorded in `docs/architecture.md`, "The verification
matrix and the risk-proportionate workflow", as the standing reference;
a complete verification on one machine is about 68 minutes.

### The ruleset and the code owners

The ruleset `protect main` (read 2026-10-19): a pull request is required
with zero required approving reviews, no code-owner review, no last-push
approval, and stale reviews not dismissed on push; the status check
`verify` is required; deletion and non-fast-forward pushes are blocked;
there are no bypass actors. `.github/CODEOWNERS` names only the owner's
own login for `AGENTS.md`, `.agents/policies/`, `.github/workflows/`,
`docs/decisions/`, and `infra/`. The agent's `gh` login is that login.
That is the state mechanism A of ADR 020 decision 3 changes by the owner's
hand, never an agent's: a second identity, a code-owner review required
with zero approving reviews, stale approvals dismissed on push, the last
push approved, the Level 3 paths of ADR 020 decision 1 (the one list,
`.agents/approvals/` and `.github/CODEOWNERS` itself among them) assigned
to the identity, and a test pull request that shows a Level 2 pull request
needs no review while a code-owned change cannot be merged without the
identity. This planning could not perform that test (no code-owner rule
exists yet, and an agent changes no setting and opens no pull request);
the recommended default of requirements decision 39 is verified by the
owner's test, recorded on F130's Issue. Because the agent's login
administers the repository, GitHub's enforcement excludes forgery and not
circumvention: the policy that an agent never changes a repository
setting holds the ruleset and the code-owners file, and the owner may
give the agent a token without administration rights (ADR 020, residual
risks). `.agents/policies/guardrails.conf` protects on this day only
`scripts/verify.sh` beyond its always protected set (the ADRs, the CI
workflows, the gate scripts, the prompts, the schemas, and itself) and
lists `docs/architecture.md` and the dependency files as sensitive; F130
brings its protected list in line with ADR 020 decision 1.

### Architecture decisions of this change cycle

- **ADR 020** records the three risk levels (the highest of the paths'
  minimum, the escalation triggers, and the assessment; raised freely,
  lowered only by the owner's authorization verified at the merge gate,
  which may lower a trigger reading or an assessed level and never the
  path minimum, with the change at its required level until the owner's
  word; a changed scientific claim is a change to or a removal of a
  published claim, so a new lesson's claims leave it at Level 2);
  the evidence lifecycle in the one completion record (a gate per
  criterion, `pending` for the later gates, `complete` only when every
  criterion is met, three readiness points derived and never stored);
  the owner-approval mechanism A (an approving review by a second GitHub
  identity that only the owner holds, enforced by the ruleset and
  `CODEOWNERS`, with a committed approval request for a Level 3 change by
  trigger or assessment and for every lowering; no script trusts an
  agent's assertion; the present practice until the setup exists); review
  in proportion to the level (none at Level 1, a traceable chain of delta
  reviews with the disposition of every finding and no changed-lines
  threshold at Level 2, full every round at Level 3; mechanical triage of
  minor and suggestion findings at Levels 1 and 2; the completion record
  and the handoff in the fingerprint); verification in proportion to the
  level (intermediate partial runs of a Level 3 change as feedback that
  is never evidence; the final acceptance a complete verification, a full
  review made after it, and the full CI); budgets as measurements for the
  owner at the chosen re-assessment points; the time log and the base
  re-fetch rule; ADR 017 decisions 1 to 6 and 9 and F113 paused with
  their triggers; what stays unchanged; the two features and the pilot.
  It amends the process statements of ADR 002 (the lesson budget), ADR
  003 decisions 5 and 6, ADR 005 decision 3 (its decisions 4 and 5
  reviewed and unamended), ADR 012 decisions 1 and 8, ADR 014 decision 7
  and its consequences, and ADR 015 decision 4, each through a dated
  status line; it changes no invariant and supersedes no decision.
- **ADR 017's status** records the pause with its reason (not justified
  by lead-time evidence), the triggers, F120 finished, F121 not started,
  and the two stale statements of its status (the experiment check joined
  the render script with F117; the F119 measurement was recorded). The
  statuses of ADR 003 and ADR 015 say that the "45 minutes per job" they
  quote has been 60 minutes for the one `build` job of a full run since
  2026-10-15; ADR 014's status says that "no lesson feature takes the
  count past 32 before F113" is history since the interim gate.
- No accepted ADR conflicts with the re-approved requirements: ADR 014's
  selection, base provenance, and check identity, ADR 012's one required
  check, ADR 003's one entry point, and ADR 017 decisions 7 and 8 are what
  ADR 020 keeps unchanged and builds on.

### Reconciliation notes

- The two deliverables of the change request's section 4 are F130
  (Deliverable 1) and F131 (Deliverable 2), the next free identifiers,
  in that order and never concurrent; F131 starts after F130 is merged
  and two features have run under it (owner's answer, 2026-10-19).
- When the new rules take effect: the change request disagrees with
  itself. Its preamble applies the new rules to features started after
  the second deliverable is merged, while its section 6 pilots two
  features under Deliverable 1 before Deliverable 2 starts, which needs
  Deliverable 1's rules to apply earlier. The approved requirements
  (decision 39) chose the staged start: F130's rules apply to features
  started after F130 is merged, F131's to features started after F131 is
  merged; ADR 020's status and the rules of Phase 7 follow them, and a
  feature in progress finishes under the contracts it started with, with
  the one stated exception of the merge approval gate: the protected
  list of `guardrails.conf` is read from the base branch and the
  code-owner rule is enforced by GitHub at the merge, so both apply to
  every pull request finished after F130's merge (ADR 020, Status;
  "Phase 7"). On 2026-10-19 the owner accepted, by approving the round 4
  revision of this planning's review (11:42 UTC), that the merge
  approval gate is the one exception to the rule of requirements
  decision 39 that a feature in progress finishes under the contracts it
  started with, for the reason stated there; the requirements are not
  edited for it, and ADR 020's status carries the same note.
- The Level 3 paths: requirements decision 39 and ADR 020 describe them
  as "the protected paths of `guardrails.conf`" and enumerate them, but
  `.agents/policies/guardrails.conf` protects on 2026-10-19 only
  `scripts/verify.sh` beyond its always protected set. The enumerated
  list is the owner's decision and the file lags; ADR 020 decision 1
  names the paths directly as the one authoritative list (with
  `docs/architecture.md`, which carries the invariants, among the
  planning documents, and `.github/CODEOWNERS` itself), F130 brings the
  file in line with it (its in-scope item and acceptance criterion 11),
  and the owner's `CODEOWNERS` action covers the same list. The
  requirements' phrase is true from F130's merge and needs no change.
- The change request's section 5 asks the planning to change
  `.agents/policies/autonomy.md` and the Definition of Done of
  `AGENTS.md`. Both are protected workflow files outside the planner's
  file scope (`scripts/lib/scope.sh`: the architecture, the roadmap, and
  the ADRs), so they are unchanged by this cycle and F130 changes them
  with the scripts (its acceptance criterion 10); ADR 020 and the
  requirements say what they will say. On 2026-10-19 the owner accepted
  this deferral by approving the round 1 revision of the planning review
  (10:56 UTC): the planning change's acceptance criterion that "the
  policy updates exist" (change request section 7) is met at F130's
  merge, the sentence of requirements decision 39 that both files refer
  to ADR 020 holds from that merge, and the requirements are not edited
  for it; ADR 020's status carries the same note.
- The status claims of the request refreshed: F120 is closed, not "still
  unpublished"; the lesson count is 38, not 32; the latest complete runs
  took 29 to 39 minutes; the ruleset is as recorded above; the roadmap's
  last identifier is F129, so F130 and F131 are confirmed.
- What this planning could not verify from the repository: the review
  rounds, triages, review files, and local verification counts and
  durations of the baseline table (the review, triage, and completion
  files are working files of the feature worktrees that Git ignores); the
  9 min 35 s of the reproduction inside the `build` job (from the CI
  logs, not re-read); the "about half of the twenty workflow gates" count;
  and the CI durations of the three lesson-fix pull requests. The lead
  times of #206 (7 h 02), F119 (12 h 04 to merge, 20 h 38 to close), F122
  (21 h 13), the lesson fixes (12 to 16 minutes from pull request to
  merge), and F61 (eight pull requests in two days, Issue open) were
  confirmed from GitHub; F120 closed 67 h after its creation. The
  verification matrix and the job durations of run 39079012220 were
  confirmed from `scripts/verify.conf` and the Actions API.
- The owner's open decisions of the request's section 10: the mechanism
  is A (requirements decision 39, the "Authentication and authorization"
  section); F131 starts after two features; the cycle was started on
  2026-10-19.

## State at the change cycle `site-navigation-and-atlas`

Checked on 2026-10-30 at the base commit `c94c045` of the planning branch
`planning/site-navigation-and-atlas`, against the repository and `gh issue
list --state all`. The files are the truth, this section is their summary
at that commit. The change request asks for a quieter site (a four-item
menu, the two-layer atlas, Home as a landing page, the glossary in
context, the improvement link) and for raster interface artwork on
non-lesson pages; its requirements decisions are 40 and 41, its decision
record ADR 021, and its features F132 to F135 (the roadmap's last
identifier before this cycle is F131; the four Issues #337 to #340 were
created from the owner's review of 2026-10-29 with these identifiers,
before this planning).

### Published lessons

Ninety-one lesson directories in eleven strands at `c94c045` (mechanics
19, agents-llm 17, thermodynamics 9, astrophysics 8, waves 8,
electromagnetism 7, fluids 7, quantum 6, lean 5, materials 4, agents-abm
1). Nothing of this cycle adds or changes a lesson's content.

### Features: state

| Feature, Issue | State at `c94c045` | Note |
|---|---|---|
| F123, #217 | Merged (pull request #237, partial); Issue open | The owner's pass on the rendered pages (criterion 6) is outstanding. F132 changes the header and footer it built. |
| F124, #238 | Merged (pull request #252); Issue open | F134 replaces its opening, its figure on Home, and its Part A, Part B, and capstone blocks; its block carries a note. |
| F125, #239; F126, #244 | Merged (pull requests #247, #255); Issues open; the follow-up #245 (a validator error on malformed field types) open | F133 replaces the map, the views, and the controls; the manifest's concept rules stay; their blocks carry a note. The owner chose the label "Course Atlas" on #244 (2026-10-22). |
| Capstones T11, EM9, FL10 | T11 (the thermodynamics lesson 09) and EM9 (the electromagnetism lesson 07) published; FL10 planned | Checked against the front matter at `c94c045`. The atlas shows T11 and EM9 as published lessons and FL10 as planned; Home shows one of the published capstones, chosen by code. The requirements' wording of the Course atlas and Home bullets said otherwise; it was corrected on 2026-10-30 as the resolution of escalated finding M1 of planning review round 1, on the owner's instruction in the planning session, and the corrected text is approved with the rest of the planning at `finish-planning.sh`. |
| F127 | No Issue; not started | Its block carries a note: it rolls out after F132 to F135, and its preview gate moves to F133 and F134. |
| F128 | No Issue; gated by question 14 | No longer tied to Home (decision 40); its block carries a note. |
| F129 | No Issue | Unchanged. |
| F130, #236; F131, #241 | Open | Unchanged; their workflow applies to F132 to F135. |
| F132 to F135, #337 to #340 | Open, no pull request | The blocks of Phase 8, written by this planning. |

### Architecture decisions of this change cycle

- **ADR 021** records the classes by claim with interface artwork on
  non-lesson pages allowed as a registered derived raster (WebP, from a
  script, an author, or an image model), committed and never rendered by
  the build, with no text, number, or formula in its pixels; the
  committed-artifact exemption widened to such a file and nothing else;
  the two-layer atlas in native exclusive disclosures with one address
  module, the manifest's sequence entries, and the relationships moved to
  the lesson pages; Home with the hero from one data file; the four-item
  menu and the supporting pages; no contribution form without an account.
  It supersedes ADR 018 decisions 2, 3, and 4 in part (ADR 018's status
  says which parts) and amends ADR 002's exemption once more (ADR 002's
  status says so). It changes the invariants I6, I30, and I31, restated
  in `docs/architecture.md`.
- No other accepted ADR conflicts with the re-approved requirements: ADR
  013 decision 3 (no description in the curriculum file) holds, since the
  descriptions go to the manifest; ADR 014 decision 4 makes each feature
  of the phase a full run; ADR 019 and ADR 020 apply unchanged.

### Reconciliation notes

- **The open questions of the change request**, answered by this planning
  (requirements decision 40, "For the planner"; ADR 021): (1) the
  illustrations are committed as derived WebP files with their scripts
  where they exist, with a regeneration check on demand outside CI, not
  rendered at build time; (2) the contribution form without a GitHub
  account is not part of this change and stays the owner's open decision
  (requirements, unresolved question 16; "Not on the roadmap"); (3) the
  hero's copy lives in one data file beside the curriculum file, and the
  sequences' one-line descriptions and illustrations in the atlas
  manifest, never on a page; which delivered illustrations are used,
  adapted, or replaced is decided by F133's and F134's visual checks and
  the owner's approval on their Issues.
- **Where the Issues differ from the requirements**, the blocks of Phase 8
  follow the requirements (precedence: the requirements before the Issue
  text). Requirements decisions 40 and 41 assign the update of #338 and
  #339 to the planner. The planning revision may edit only the planning
  documents, so the planner applies the edits below to the two Issue
  bodies right after this planning is approved, and the edits are a
  **pre-start gate** of F133 and F134 (their "Dependencies"): neither
  feature starts, and no implementation plan of either is written, until
  its Issue matches its roadmap block. The deferral from this planning to
  the step right after its approval is the planner's, approved by the
  owner with the triage of the first planning review of this cycle
  (2026-10-30, finding M2). The edits, exactly:
  - **#338 (F133).** (a) In "Design", the bullet of the twelve
    illustrations loses "each physically correct" and its parenthesised
    list of relations; it reads that each is checked visually on the card
    (76 px) and the panel (200 px) before acceptance, and that its source
    in the provenance register is a script path, an author, or an image
    model with the model, the prompt, and the date. (b) In "Kept", the
    anchors `#<course-id>` and `#<path-id>` become the existing
    `#course-<id>` and `#path-<id>`, and the bullet gains the three
    relationship types on the lesson pages (the requirements' "Course
    atlas": they "stay in the manifest and on the lesson pages") and the
    progress and recommendation behaviour of F13 and F14 with the learning
    path data `recommend.js` reads. (c) "Dependencies" gains F64, F13, and
    F14. (d) "Acceptance criteria" is replaced by the thirteen criteria of
    F133's block: the scientific-correctness checklist of criteria 5 and 7
    leaves (decision 41 replaces it by the visual check of F133 criterion
    7), criterion 3 names the existing anchor form, and criterion 9 (ADR
    018 amended, the architecture, the notes on F125 and F126) is recorded
    as met by this planning. (e) "Risk" reads High (Level 3, assessed and
    by trigger), as the block says.
  - **#339 (F134).** (a) In "Scope", *Home*, the bullet "Keep the opening:
    the computed double-pendulum figure ..." is replaced by the hero of
    F134's block (the figure leaves Home; its function, energy check, and
    provenance stay in `src/pbc`), and the hero paragraph's last sentence
    ("Whether it replaces or accompanies the computed opening figure is
    decided at planning") reads that the hero replaces it (owner's answer,
    2026-10-30). (b) In "ADR", "the opening figure rule is unchanged"
    becomes "the opening is the hero (ADR 021 decision 4, superseding ADR
    018 decision 4 in part)". (c) "Dependencies" gains F19 and F117, and
    F133 also for the illustrations the hero image is composed from. (d)
    "Acceptance criteria" is replaced by the eight criteria of F134's
    block: criterion 2 (the opening figure unchanged) and the "generous
    room for the opening figure" of criterion 1 leave; the hero criterion
    names the eight identifiers 1a, 1b, 1c, 2a, 2b, 2c, 3a, and 3b; the
    example lessons and the capstone stay chosen by code from data;
    criterion 6 (ADR 018 amended, the note on F124) is recorded as met by
    this planning. (e) "Risk" reads High (Level 3 by trigger: the tests of
    the removed opening and blocks are removed or replaced), not "Level 3
    if the amendment touches the protected paths", since the amendment is
    this planning's.
  - #337 (F132) and #340 (F135) contradict no decision, so they are no
    gate; the planner corrects them in the same pass. #337 names F127 as a
    dependency; F127 has not started and rolls out after this phase, so
    F132 depends on F123 and F57; its risk reads Level 3 by trigger, as
    the block says. #340 names F35 for the lesson's last section; F35 is
    the annotated excerpts, and the last section is F117's footer.
- **The material** the change request names as staged under
  docs/changes/site-navigation-and-atlas/ (the illustrations, their
  scripts, the derived sizes, the text-free Part B masters, the mocks) is
  not in this worktree at `c94c045`; nothing of this planning depends on
  it. The features take what they use from the owner and commit only the
  derived files, their register entries, and the scripts that exist.
- **The F125 and F126 tests** of the map, the views, and the controls are
  replaced by F133's tests, not deleted without replacement; the
  follow-up #245 on the manifest validator stays valid for the concept
  rules that remain.
- **F127's preview gate.** Phase 6 made the owner's review of the preview
  (Home, the atlas, one lesson) on the Issues of F124 and F126 the gate of
  the rollout. Home and the atlas are replaced before any rollout, so the
  gate moves to the owner's rendered pass on F133 and F134 with F123's
  lesson (the note on F127); no delivered criterion of F124 or F126
  changes.

## Overview

Phases: Phase 1 is the MVP; Phase 2 is the work the requirements placed
after the MVP; Phase 3 is the change cycle `physics-next-phase`, ordered in
waves R0 to R5 by dependency; Phase 4 is the change cycle
`final-curriculum`, ordered in waves C0 to C4; Phase 5 is the change cycle
`pbc-planning-change-four-workstreams`, the four workstreams F114 to F121;
Phase 6 is the change cycle `scientific-atelier-atlas`, the atelier, the
atlas, and the governed visual skills F122 to F129; Phase 7 is the change
cycle `risk-proportionate-workflow`, the two workflow features F130 and
F131, strictly one after the other; Phase 8 is the change cycle
`site-navigation-and-atlas`, the quieter site F132 to F135
(see "Execution order"). A wave is a suggested grouping, not a gate: a
feature may start when its
dependencies are done. The gates of Phase 4 (F61 and F62 before every
lesson feature of the phase, F64 before the lesson features of waves C2 to
C4) are dependencies, listed in the table and in each block.

| ID | Feature | Phase | Depends on | Risk |
|---|---|---|---|---|
| F01 | Published site skeleton with the full verification pipeline | 1, delivered | none | High |
| F02 | Lesson format and the first mechanics lesson | 1, delivered | F01 | Medium |
| F03 | Learning path | 1, delivered | F02 | Medium |
| F04 | Mechanics lessons: Newton's laws and projectile motion with drag | 1, delivered | F02 | Medium |
| F05 | Mechanics lessons: the harmonic oscillator and numerical integrators | 1, delivered | F04 | Medium |
| F06 | Mechanics lessons: energy, momentum, and a capstone orbit | 1, delivered | F03, F05 | Medium |
| F07 | Interactive visualizations | 1, delivered | F05 | Medium |
| F08 | Formal proofs strand: first Lean lesson | 1, delivered | F03, F05 | Medium |
| F09 | LLM agents strand: first agent-driven experiment lesson | 1, delivered | F03, F04 | High |
| F10 | MVP release readiness and launch | 1, delivered (release tag pending) | F01 to F09 | Medium |
| F11 | Agent-based modelling strand: first lesson | 2, delivered | F03, F06 | Medium |
| F12 | Content proposal workflow through GitHub Issues | 2, delivered | F10 | High |
| F13 | Self-check quizzes and browser-local progress | 2 | F03, F07, F10 | Medium |
| F14 | Adaptive recommendations | 2 | F13 | Medium |
| F15 | Second course on the three-pillar path | 2, dropped by `final-curriculum` (ADR 013) | F10 | Medium |
| F58 | Parallel verification jobs behind one required check | 3, R0 | F10 | High |
| F44 | Visual design and accessibility system | 3, R1 | F10 | Medium |
| F57 | Open-source identity, attribution, and citation | 3, R1 | F10, F12 | Medium |
| F25 | Homepage narrative: Construct, Investigate, Verify | 3, R1 | F57 | Low |
| F37 | Lesson metadata and course navigation | 3, R1 | F10, F12 | Medium |
| F26 | Generated prerequisite graph | 3, R1 | F37 | Medium |
| F27 | Learning path cards and the difficulty scale | 3, R1 | F37, F44 | Low |
| F35 | Code explanation: annotated excerpts | 3, R1 | F10 | Low |
| F36 | Numeric results as semantic tables | 3, R1 | F10 | Low |
| F28 | Lesson format 2, the reference register, and the M1 pilot | 3, R1 | F37, F44, F35, F36 | Medium |
| F30 | Editorial pass M5 to M8, with M5 as the research-backed pilot | 3, R1 | F28 | Medium |
| F29 | Editorial pass M1 to M4 | 3, R1 | F28, F30 (the M5 pilot reviewed) | Medium |
| F39 | Unified local setup, run recipes, and the link maintenance check | 3, R1 | F10 | Low |
| F50 | Experimental dataset registry and feasibility gate | 3, R3 (may start beside R1) | F10 | Medium |
| F42 | Before you begin, and the glossary | 3, R2 | F37, F28 | Low |
| F38 | Progressive hints in exercises | 3, R2 | F28 | Low |
| F40 | Reproducibility UX | 3, R2 | F28 | Low |
| F41 | Self-hosted search | 3, R2 | F37 | Medium |
| F31 | Agent and Lean editorial pass | 3, R2 | F28, F30 | Medium |
| F32 | Mechanics diagrams M1 to M4 | 3, R2 | F29 | Low |
| F33 | Mechanics diagrams M5 to M8 | 3, R2 | F30 | Low |
| F34 | Agent and Lean diagrams | 3, R2 | F31 | Low |
| F45 | Agent-assisted simulation development | 3, R2 | F10 | High |
| F46 | Scientific code verification and debugging | 3, R2 | F10 | Medium |
| F16 | Counterexample hunter | 3, R2 | F09, F46, F28 | Medium |
| F17 | Further Lean mechanics proofs | 3, R2 | F08, F28 | Medium |
| F59 | Instructor pack for one published lesson | 3, R2 | F57, F30 | Low |
| F51 | Experimental methods and visualization foundations | 3, R3 | F50 (a go decision), F28 | Medium |
| F60 | Gravitational-wave strain lab: from Kepler's orbit to a chirp | 3, R3 | F51, F06 | Medium |
| F43 | Science-first visualization components | 3, R3 | F07, F51 | Medium |
| F54 | Microwave S-parameter lab | 3, R4 | F51, a course for the lab (F72 since `final-curriculum`; see the block) | Medium |
| F53 | Flow measurement lab with PIV fields | 3, R4 | F51, F43, a course for the lab (F73 since `final-curriculum`; see the block) | Medium |
| F52 | Optical diffraction lab | 3, R4 | F51, F43, a course for the lab (F71 since `final-curriculum`; see the block) | Medium |
| F55 | Agent-assisted experimental physics | 3, R4 | F45, one of F60 or F54 | Medium |
| F23 | Inverse physics: parameter discovery with uncertainty | 3, R4 | F51, one of F60 or F54 | Medium |
| F47 | Automated analysis pipelines | 3, R4 | F51 | Medium |
| F18 | Multi-agent scientific review | 3, R4 | F09, F46 | Medium |
| F19 | Scientific evidence map | 3, R4 | F28, F29, F30, F31, F37 | Low |
| F56 | Lean proofs for the models of measured-data labs | 3, R4 | F17, F54 | Medium |
| F20 | Autonomous experimental design | 3, R5 | F16, F23 | Medium |
| F21 | Interactive Lean exercises | 3, R5 | F17 | Medium |
| F22 | Agent-assisted theorem proving | 3, R5 | F21, F45 | High |
| F49 | Research capstone: reproduce an open physics paper with a multi-agent team | 3, R5 | F18, F45, F46, F47 | High |

Retired candidate numbers: F24 (optional local tutor, deferred) and F48
(paper reproduction, absorbed into F49). See "Candidate mapping".

Phase 4, the change cycle `final-curriculum` (2026-10-12). The slots are
the curriculum labels of `docs/changes/final-curriculum.md`; the full
mapping is under "Slot mapping".

| ID | Feature | Wave | Slots | Depends on | Risk |
|---|---|---|---|---|---|
| F61 | Verification proportional to the change | C0 | none | F58 | High |
| F113 | Bounded full verification: same-machine lesson shards of the build (paused by `pbc-planning-change-four-workstreams`, requirements decision 35; superseded or resumed by the owner's decision on ADR 017) | C0 | none | F61, F58 | High |
| F62 | Eight courses and the reference curriculum | C0 | none (migrates 17 published lessons; T0 by F70) | F03, F37, F26, F27, F25 | Medium |
| F63 | Verified lesson previews | C0 | none | F62, F28, F44 | Medium |
| F64 | Learning Path redesign: course-first, compact, accessible | C0 | none | F62, F63, F26, F27, F37, F41, F44, F13, F14 | Medium |
| F65 | Physics environments and the discovery evaluation protocol | C1 | none | F09, F16, F20, F23, F46 | Medium |
| F66 | Law discovery lessons: black-box force laws | C1 | D1, D2, D3 | F61, F62, F113 by the lesson-shard rule, F65 | Medium |
| F67 | Symbolic regression and equation discovery | C1 | D7, D8 | F61, F62, F113 by the lesson-shard rule, F65, F23 | Medium |
| F68 | Advanced mechanics: chaos, Lagrangian and Hamiltonian mechanics, resonance | C1 | M9, M10, M11, M12 | F61, F62, F113 by the lesson-shard rule, F05, F06 | Medium |
| F69 | Mechanics: many-body gravitation, nonlinear dynamics, rotational motion | C1 | M13, M14, M17 | F61, F62, F113 by the lesson-shard rule, F68, F06 | Medium |
| F70 | Thermodynamics: random walks, kinetic theory, entropy | C1 | T1, T2, T3 (and T0 re-homed) | F61, F62, F113 by the lesson-shard rule, F11, F06 | Medium |
| F71 | Waves and optics: the wave equation, interference, sound | C1 | W1, W2, W9 | F61, F62, F113 by the lesson-shard rule, F05 | Medium |
| F72 | Electromagnetism: fields, charged particles, induction | C1 | EM1, EM2, EM3 | F61, F62, F113 by the lesson-shard rule, F06 | Medium |
| F73 | Fluid dynamics: advection, Burgers, finite volumes, shallow water | C1 | FL1, FL4, FL9, FL5 | F61, F62, F113 by the lesson-shard rule, F05, F06 | Medium |
| F74 | Wave flume lab | C1 | W8 | F61, F62, F113 by the lesson-shard rule, F71, F51, F43 | Medium |
| F75 | Thermodynamics: Ising model, molecular dynamics, heat engines | C2 | T4, T5, T9 | F61, F62, F64, F113, F70 | Medium |
| F76 | Heat conduction and the finite-element bridge | C2 | T6, T10 | F61, F62, F64, F113, F70 | Medium |
| F77 | Optics: refraction, polarisation, diffraction, inverse optics | C2 | W3, W4, W5, W6 | F61, F62, F64, F113, F71 | Medium |
| F78 | Electromagnetism: Maxwell's equations and FDTD, RLC circuits, waveguides | C2 | EM4, EM5, EM6 | F61, F62, F64, F113, F72, F71 | Medium |
| F79 | Fluid dynamics: Navier-Stokes, vortex shedding, particle-based fluids | C2 | FL2, FL3, FL6 | F61, F62, F64, F113, F73 | Medium |
| F80 | Applied capstone: adaptive phased-array beam steering | C2 | EM9 | F61, F62, F64, F113, F78, F71 | Medium |
| F81 | Interactive discovery benchmarks and non-agent baselines | C2 | EV2, EV3 | F61, F62, F64, F113, F65, F66, F67 | Medium |
| F82 | Discovering conservation laws and invariants | C2 | D13 | F61, F62, F64, F113, F65, F67, F69 | Medium |
| F83 | Pendulum and accelerometer data lab | C2 | M15 | F61, F62, F64, F113, F51, F68 | Medium |
| F84 | Heat transfer measurements lab | C2 | T7 | F61, F62, F64, F113, F76, F51 | Medium |
| F85 | Brownian motion tracking lab | C2 | T8 | F61, F62, F64, F113, F70, F51 | Medium |
| F86 | RLC circuit measurements lab | C2 | EM8 | F61, F62, F64, F113, F78, F51 | Medium |
| F87 | Applied capstone: thermal engineering of a hypothetical AI accelerator | C3 | T11 | F61, F62, F64, F113, F76 | Medium |
| F88 | Applied capstone: reconstructing the 2025 Kamchatka tsunami | C3 | FL10 | F61, F62, F64, F113, F73, F51 | High |
| F89 | Quantum physics: the Schrödinger equation, tunnelling, the harmonic oscillator | C3 | Q1, Q2, Q3 | F61, F62, F64, F113, F05, F71 | Medium |
| F90 | Quantum physics: spin, entanglement and Bell inequalities, open systems | C3 | Q4, Q5, Q6 | F61, F62, F64, F113, F89 | Medium |
| F91 | Astrophysics: the three-body problem, modified gravity, lensing | C3 | AST1, AST2, AST3 | F61, F62, F64, F113, F69 | Medium |
| F92 | Relativity and cosmology: special relativity, relativistic orbits, cosmic expansion | C3 | AST10, AST4, AST5 | F61, F62, F64, F113, F91 | Medium |
| F93 | Gravitational-wave chirp and exoplanet transit simulations | C3 | AST6, AST7 | F61, F62, F64, F113, F91, F60 | Medium |
| F94 | Materials physics: crystal lattices and phonons, electronic band structure | C3 | MAT1, MAT2 | F61, F62, F64, F113, F71, F89 | Medium |
| F95 | Materials physics: elasticity and deformation, defects | C3 | MAT3, MAT4 | F61, F62, F64, F113, F94, F76 | Medium |
| F96 | Multimodal physics reasoning and interpretable explanations | C3 | AI6, AI7 | F61, F62, F64, F113, F09, F46, F65 | Medium |
| F97 | Physical reasoning from video | C3 | AI8 | F61, F62, F64, F113, F96, F06 | Medium |
| F98 | Discovery under noise, hidden variables, and generalisation | C3 | D10, D11, D12 | F61, F62, F64, F113, F66, F81 | Medium |
| F99 | Discovering gravity and unknown physical worlds | C3 | D4, D5 | F61, F62, F64, F113, F66, F69, F91 | Medium |
| F100 | Physics reasoning benchmarks | C3 | EV1 | F61, F62, F64, F113, F96, F65 | Medium |
| F101 | Robustness, cost, and scientific failure analysis | C3 | EV4, EV5 | F61, F62, F64, F113, F81, F98 | Medium |
| F102 | Atomic spectroscopy lab | C3 | Q7 | F61, F62, F64, F113, F89, F51 | Medium |
| F103 | Quantum measurement statistics lab | C3 | Q8 | F61, F62, F64, F113, F90, F51 | Medium |
| F104 | Exoplanet light curves lab | C3 | AST8 | F61, F62, F64, F113, F93, F51 | Medium |
| F105 | Galaxy rotation curves lab | C3 | AST9 | F61, F62, F64, F113, F91, F51 | Medium |
| F106 | X-ray diffraction data lab | C3 | MAT5 | F61, F62, F64, F113, F94, F51 | Medium |
| F107 | Stress-strain measurements lab | C3 | MAT6 | F61, F62, F64, F113, F95, F51 | Medium |
| F108 | Turbulence and flow measurements lab | C3 | FL8 | F61, F62, F64, F113, F79, F53, F51 | Medium |
| F109 | Evidence maps and reproducible literature evidence | C4 | R2, R3 | F61, F62, F64, F113, F19, F39, F28 | Medium |
| F110 | Agent-driven materials discovery | C4 | R5 | F61, F62, F64, F113, F95, F18, F20 | Medium |
| F111 | Autonomous physics research challenge | C4 | R6 | F61, F62, F64, F113, F49, F101, F98, F65 | High |
| F112 | Curriculum completion audit | C4 | none | every scheduled lesson feature, F64 | Low |

The features of the previous phase without an Issue keep their IDs and
blocks and fill these slots when their dependencies are met: F45 (AI1),
F55 (AI5), F49 (R4), F52 (W7, after F71), F53 (FL7, after F73), F54 (EM7,
after F72); F22 stays a Lean strand feature outside the slots. Each of
them publishes a lesson in this phase and therefore starts after F61 and
F62, and after F113 under the full-run gate, like every lesson feature of
the phase (the gates under "Phase 4"); their blocks are not rewritten, the
gate is this rule. F15 is dropped.

Phase 5, the change cycle `pbc-planning-change-four-workstreams`
(2026-10-15): four independently reviewable workstreams (requirements
decisions 32 to 35). The risky verification work is never combined with
the editorial pilot in one feature.

| ID | Feature | Workstream | Depends on | Risk |
|---|---|---|---|---|
| F114 | Editorial voice: the style guide with before-and-after examples | Editorial (change 1) | F28, F29, F30, F31 | Low |
| F115 | Editorial pilot on mechanics lessons 01 to 05, with the human approval gate | Editorial (change 1) | F114, F29, F30, F32 | Medium |
| F116 | Editorial principles in the authoring guide, the lesson template, and the review rubric | Editorial (change 1) | F115 (the pilot approved) | Low |
| F117 | "Run this experiment": learner instructions without a website build | Learner instructions (change 2) | F39, F40, F61 (the switch: F118's record under question 10, or F119) | Medium |
| F118 | Verification audit and the record of the full run | Verification (change 4) | F61 | Low |
| F119 | Remove redundant verification and blanket local build obligations | Verification (change 4) | F118, the owner's acceptance of ADR 017 decisions 7 and 8 | High |
| F120 | Incremental `main`: the staged evidence and the decision record | Verification (change 4) | F61, F118 | Medium |
| F121 | Incremental `main` and the exceptional full run, if ADR 017 is accepted | Verification (change 4) | F120, F119, the owner's acceptance of ADR 017 | High |

The budget of change 3 (ADR 015) is no feature: it changes the statements
of the typical-pull-request budget in this roadmap, the architecture, and
the requirements, and the acceptance criterion 1 of F61.

Phase 6, the change cycle `scientific-atelier-atlas` (2026-10-17): the
scientific atelier, the course atlas, and the governed visual agent skills
(requirements decisions 36 to 38; ADR 018 and ADR 019). The slice letters
are those of section 8 of the change request. The preview gate (the
owner's review of the home page, the atlas, and one lesson before the
rollout) is a dependency of F127, recorded on the Issues of F124 and
F126.

| ID | Feature | Slice | Depends on | Risk |
|---|---|---|---|---|
| F122 | Governed visual agent skills: the audit, the pinned skills, the PBC Scientific Visualization skill, and the workflow contract | A (the skill audit), A2 | F119 (the targeted tier and the `verify.conf` groups the check joins); the owner's approval of each candidate's outcome (question 13) | High |
| F123 | The atelier foundations: the design specification, tokens, typography and fonts, the shared header and footer, and the lesson template on one existing lesson | A (the design specification), B | F122, F44, F57, F63, F64, F117 (the merged pull request #205, not the closure of Issue #202) | Medium |
| F124 | The home page of the atelier, with a static verified opening figure | C | F123, F125 (the curated, owner-approved map manifest, which the capstone highlights read), F25, F62, F68, F117 (the merged pull request #205, not the closure of Issue #202), F57 | Medium |
| F125 | The map manifest and the static atlas: curated concepts and connections, the generated map with its textual equivalent | A (the map data contract), D | F122, F62, F63, F64, F26, F37, F41 | Medium |
| F126 | The atlas interaction: the switch, selection, zoom, filters, and the phone's region selector | E | F123, F125, F64, F13, F14, F41 | Medium |
| F127 | The rollout: course openings, every lesson in the reading-column template, the capstone and supporting-page templates, and the final visual acceptance | F, G (the polish) | F123, F124, F126, the owner's review of the preview; since `site-navigation-and-atlas` also F132 to F135, with the preview gate on F133 and F134 | Medium |
| F128 | The validated interactive pendulum on the home page (since `site-navigation-and-atlas` no longer tied to Home; its page is the owner's decision) | G | F124, F68, F07, F43, the owner's decision (question 14) | Medium |
| F129 | The scientific-figure and conceptual-diagram skill pilots, and the owner's decision on authoring integration | H | F122, F32, F33, F05; coordinated with F114 to F116 | Medium |

Phase 7, the change cycle `risk-proportionate-workflow` (2026-10-19): the
two deliverables of `docs/changes/risk-proportionate-workflow.md`
(requirements decision 39; ADR 020), which change the development
workflow and no page of the site. Both are Level 3 under ADR 020
decision 1 and never in flight together (see "Phase 7").

| ID | Feature | Deliverable | Depends on | Risk |
|---|---|---|---|---|
| F130 | Risk-proportionate workflow, part 1: the evidence lifecycle, the risk level, the merge-gate verification, intermediate Level 3 verification, the budget policy, and the time log | 1 | This planning and ADR 020 approved; F119; F61; F122 | High |
| F131 | Risk-proportionate workflow, part 2: the review chain, the review fingerprint of the completion record and the handoff, and mechanical triage | 2 | F130 merged, and two features run under it with their effect observed | High |

Phase 8, the change cycle `site-navigation-and-atlas` (2026-10-30): the
quieter site of requirements decisions 40 and 41 (ADR 021). The four
Issues existed before the planning; each changes shared inputs and is a
full run.

| ID | Feature | Issue | Depends on | Risk |
|---|---|---|---|---|
| F132 | Quieter navigation: a four-item menu, the secondary pages in the footer, About brought up to date | #337 | F123, F57 | High (Level 3 by trigger: the header test's assertions change) |
| F133 | The Course Atlas as a two-layer navigation page: twelve sequence cards and the lessons of the selected one, with generated illustrations | #338 | F132, F123, F125, F126, F64, F13, F14, the owner's approval of the illustrations; #338 brought in line (pre-start gate) | High (Level 3) |
| F134 | Home as a landing page, Set up as Run the code, and a readable How we verify the science page | #339 | F132, F133, F124, F19, F117; #339 brought in line (pre-start gate) | High (Level 3 by trigger: tests removed or replaced) |
| F135 | The glossary in context and a Suggest an improvement link on every lesson, through pre-filled issue forms | #340 | F132, F117, F42, F12, F57; never in flight with F133 | Medium (Level 2; Level 3 if an existing assertion changes) |

Risk levels follow `.agents/policies/autonomy.md` and, since
`risk-proportionate-workflow`, ADR 020 decision 1. Every feature that adds
a lesson is Level 2 (Medium) under ADR 020 decision 1, with independent
scientific review by a different model, because physics and proof content
needs independent review, not only passing checks; the claims a new
lesson introduces are not the "changed scientific claim" trigger, and the
feature is Level 3 (High) when it changes or removes a published claim or
hits another trigger. Features that change CI, repository settings, legal
text, or let an agent write code are High.

## Product structure

From the requirements (decision 15) and ADR 008. The site has three facets,
all derived from lesson front matter; there is no second list.

| Facet | Content | Today | Next phase |
|---|---|---|---|
| **Physics courses** (by subject) | Mechanics. Later candidates: waves and optics (bridged by the wave-flume and optics datasets), Lagrangian and Hamiltonian mechanics, statistical physics, electromagnetism, fluid dynamics. | One course, implicit | `course` in every lesson (F37); a second course only through F15 with the human's explicit choice. F15 yields one course. A measured-data lab whose subject F15 does not choose waits for a later course feature, which takes the next unused ID when the human asks for it; the only other route is a `mechanics` framing its Issue justifies under ADR 008 decision 3. **Since `final-curriculum` (ADR 013):** the eight courses `mechanics`, `thermodynamics`, `waves`, `electromagnetism`, `fluids`, `quantum`, `astrophysics`, `materials` with fixed identifiers, each a strand with the same identifier created by its first lesson feature (F70, F71, F72, F73, F89, F91, F94); the reference curriculum in the curriculum file, filled by `slot` (F62); F15 dropped; a lab's home is its subject's course, and the `mechanics` framing of a lab of another subject is no longer a route. |
| **Methods** (cross-cutting, not subjects) | Simulation, LLM agents in the harness, agent-based modelling, formal verification in Lean, measured data, coding agents on the learner's machine. | Four strands in one linear path | `methods` tags, one method path per method on the learning-path page, related-lesson links (F37); no method becomes a course. |
| **Strands** (URL groups and ordering) | `mechanics`, `agents-llm`, `agents-abm`, `lean`. | Unchanged | Unchanged identifiers and addresses; display titles may be refined (for example "AI-assisted research" for `agents-llm`). A measured-data lab of the mechanics course takes the next order in the `mechanics` strand; a lesson about a method lives in that method's strand. No lesson is placed by a method tag alone (ADR 008 decision 4). **Since `final-curriculum` (ADR 013):** one strand per course in curriculum order, then the three method strands; the lessons of the four method paths live in `agents-llm`. |
| **Method paths** (since `final-curriculum`, ADR 013) | Physics reasoning and scientific agents (AI0 to AI8), scientific law discovery (D1 to D13), physics agent benchmarking (EV1 to EV5), autonomous scientific research (R1 to R6). | Not shown; six published lessons belong to them | A facet of the slot: a secondary view of the path page over the same canonical pages (F62, F64); never a course, a strand, or a page of its own. |

Rules that follow: a lab belongs to one primary course and links to its
agent, measured-data, and Lean extensions instead of being duplicated; no
lesson asserts that every experiment has an LLM or Lean counterpart; the
dataset survey (Appendix A of the change request) adds no course and no
strand; a web gallery of verified experiments (F43, F51) is a presentation,
not a strand.

## MVP lesson list

The requirements leave the exact lesson list to planning. The MVP has ten
lessons: eight in the mechanics strand, one LLM agent lesson, and one Lean
lesson. Changing this list is a roadmap change.

| # | Strand | Lesson | Feature |
|---|---|---|---|
| M1 | mechanics | Kinematics as a program: state, time step, explicit Euler, comparison with the closed form, error convergence | F02 |
| M2 | mechanics | Newton's laws as a first-order system: force models, a generic stepper, falling with linear drag against its analytic solution | F04 |
| M3 | mechanics | Projectile motion with quadratic drag: no closed form, validation by limiting cases and convergence, range against launch angle | F04 |
| M4 | mechanics | The harmonic oscillator: exact solution, phase space, what explicit Euler does to its energy | F05 |
| M5 | mechanics | Numerical integrators: explicit Euler, symplectic Euler, velocity Verlet, Runge-Kutta 4; order, stability, cost | F05 |
| M6 | mechanics | Energy conservation: work and energy, energy drift as a diagnostic, the pendulum at large amplitude | F06 |
| M7 | mechanics | Momentum conservation and collisions: pairwise forces, centre of mass, elastic collisions | F06 |
| M8 | mechanics | Capstone, the Kepler orbit: a two-body central force, conserved energy and angular momentum, long-time behaviour | F06 |
| A1 | agents-llm | An LLM agent designs and runs an experiment on the projectile-with-drag simulation | F09 |
| L1 | lean | Proving what the simulation showed: a kinematic identity and the energy growth of explicit Euler on the harmonic oscillator | F08 |

The agent-based modelling lesson was not in the MVP list; F11 delivered it
as the first follow-up, and the first release includes it (eleven lessons).

## MVP requirements coverage

| MVP requirement | Delivered by |
|---|---|
| Mechanics course of 6 to 10 lessons with numerical simulations | F02, F04, F05, F06 |
| At least one LLM agent lesson, run locally with the learner's key | F09 |
| Agent-based modelling lesson, or an explicit roadmap slot | F11 |
| At least one Lean 4 and Mathlib lesson, CI running `lake build` | F01 (pipeline), F08 (lesson) |
| Every lesson has explanation, assumptions, worked examples, reproducible code, exercises or interactives | F02 (format and checks), F07 (interactives), every lesson feature |
| Static site on GitHub Pages rebuilt from `main` by CI | F01 |
| CI executes all Python and builds all proofs; failing lessons cannot merge | F01 |
| Documented authoring workflow: lesson template, local verification command | F02 |
| Public repository with MIT and CC BY 4.0 licences | F01 |
| Visible learning path with ordering, difficulty, prerequisites | F03 |
| WCAG 2.1 AA, responsive, works without JavaScript | F01 (automated checks), F10 (manual audit) |

## Phase 1 — MVP

### F01 — Published site skeleton with the full verification pipeline

**Goal.** Put a real, if nearly empty, site on GitHub Pages and gate every
pull request with one verification command that already exercises Python,
Lean with Mathlib, and the site build. Every later feature only adds content
and checks to this pipeline.

**User-visible outcome.** A visitor to the GitHub Pages URL sees a home page
that explains the project and its three pillars, states the licences, and
links to the repository. A contributor sees one required status check on every
pull request.

**In scope.**

- Python project: `pyproject.toml`, `uv.lock`, `.python-version`, the `pbc`
  package skeleton, Ruff, pytest, and at least one real unit test.
- Lean project in `lean/` with pinned toolchain and Mathlib, and one small
  theorem that imports Mathlib, so the cache path and build time are proven.
- Quarto project in `site/` with home and about/licence pages, MathML
  equations with a self-hosted math font, an accessible highlighting theme,
  and only self-hosted assets.
- Checks added to `scripts/verify.conf`: lint and format, unit tests, Lean
  build that fails on `sorry` and project axioms, site build, built-site
  checks (no other-origin resources, no cookies, image alt text and
  dimensions, internal links, readable without JavaScript, automated WCAG 2.1
  A/AA scan), and the determinism check.
- The supported-machine contract of the architecture: a documented one-time
  setup in `docs/development.md` that provides Git, uv, elan, jq, the
  Playwright browser build pinned through `uv.lock`, and on Linux that
  browser's system libraries. Setup is the only step that may need
  administrator rights; `./scripts/verify.sh` stays unprivileged and installs
  no system packages.
- Preflight checks for that contract: a check listed first in
  `scripts/verify.conf` and `scripts/doctor.sh` both report every missing
  prerequisite, including a browser build that is absent or cannot start,
  with a fix hint.
- CI workflow: actions pinned by commit SHA, read-only default permissions,
  the same setup as a local machine, caches, job timeout, site artifact on
  every run, deploy job from `main` that publishes the verified artifact.
- Licences: `LICENSE` (MIT, code) and `LICENSE-CONTENT` (CC BY 4.0, lesson
  text and figures), stated in the README and the site footer.
- Repository hygiene: project README, CONTRIBUTING with contribution licence
  terms and the template section removed, CODEOWNERS placeholder replaced,
  `.env.example` and `.gitignore` updated, Dependabot configuration for
  Python and Actions, `docs/development.md`, `docs/deployment.md`, and
  `docs/operations.md` updated.
- A checklist of settings only the human can apply, applied with their
  approval: enable Pages with GitHub Actions as source, add the `verify`
  required check to the `main` ruleset, confirm Dependabot alerts, secret
  scanning, and push protection.

**Out of scope.** The lesson format, lessons, the learning path, widgets, Lean
display on pages, agent code, a custom domain.

**Dependencies.** None.

**Acceptance criteria.**

1. On a clean macOS and a clean Linux machine that has completed only the
   documented one-time setup (Git, uv, elan, jq, the Playwright browser
   build, and on Linux its system libraries), `./scripts/verify.sh` passes
   without administrator rights and leaves the built site in a documented,
   git-ignored directory. A test shows that verification and
   `./scripts/doctor.sh` fail with a fix hint when a prerequisite is missing,
   at least for jq and for the browser build.
2. The CI workflow runs checks only through `./scripts/verify.sh`. Each new
   check has a test showing it fails on a violating input: a failing Python
   test, a Lean file that does not compile, a Lean file containing `sorry`, a
   page that loads a resource from another origin, an image without alt text.
3. A push to `main` publishes the artifact built by the verify job of that
   commit; the deploy job contains no build step. The home page is reachable
   at the GitHub Pages URL.
4. Workflows declare `contents: read` by default; only the deploy job has
   `pages: write` and `id-token: write`; every action is pinned by commit
   SHA; no secret is referenced; triggers are `pull_request` and `push` to
   `main` only.
5. `verify` is a required status check on `main`, and a pull request with a
   failing check cannot be merged.
6. The built site requests nothing from another origin and sets no cookie.
7. The home page is fully readable with JavaScript disabled, renders a sample
   equation as MathML, is usable at phone width without horizontal scrolling
   of the page, and has zero violations in the automated WCAG 2.1 A/AA scan.
8. Two builds of the same commit on the same platform produce byte-identical
   output.
9. The site works when served from the repository sub-path of the default
   Pages URL, and the base URL is one configuration value.
10. A warm-cache pull request run finishes within 12 minutes and Mathlib is
    not compiled from source. Measured times per check are recorded in the
    pull request. (The 12 minutes are the budget of ADR 003 at delivery;
    20 minutes since ADR 015, 2026-10-15.)
11. Licence files exist; the README and site footer state MIT for code and
    CC BY 4.0 for content. No template placeholder text remains in the
    README, CONTRIBUTING, CODEOWNERS, or `.env.example`.
12. A page with sample equations, code, and a figure renders correctly in the
    current Chromium, Firefox, and WebKit engines, recorded in the pull
    request.

**Risk.** High. The feature changes CI permissions, deployment, and
repository settings, which need explicit human approval at each step.
Technical risks: Mathlib build products against GitHub's cache quota; Quarto
outputs that embed build-time values and break determinism; the Quarto binary
download at install time; accessibility defects in the default theme.

**Detailed implementation plan expected.** Yes.

### F02 — Lesson format and the first mechanics lesson

**Goal.** Define what a lesson is, enforce it with checks, document how to
write one, and prove it with the first published lesson.

**User-visible outcome.** A learner can read lesson M1, "Kinematics as a
program", with explanation, explicit assumptions, worked examples, executed
code and figures, exercises with solutions, and a "Reproduce this" section
whose commands regenerate the lesson's results from a clone (the contract
of ADR 002 at delivery; since ADR 016 and F117, 2026-10-15, the section
names the lesson's experiment entry point and never a render command). An
author can create a new lesson from a template and a guide.

**In scope.**

- Lesson directory convention, front matter schema, and required sections,
  as outlined in the architecture's lesson model.
- The verified display forms for Python: executed cells and by-reference
  excerpts from `src/pbc`, with the "not verified" marker and its visible
  label.
- Figure conventions: produced by executed cells, alt text, explicit
  dimensions, deterministic rendering.
- Exercise and solution pattern that works without JavaScript.
- "Reproduce this" section naming exact files, commands, and the built
  commit (since ADR 016 and F117, 2026-10-15, the commands end at the
  lesson's experiment entry point and never render the site).
- Lesson source checks: schema, required sections, unmarked non-executed
  code, committed generated artifacts. The last check rejects tracked
  figures, outputs, execution caches, and rendered pages. Its one exemption
  is the replay fixture location of a lesson directory, whose path convention
  this feature fixes (ADR 002); nothing else may be committed there.
- Authoring guide in `docs/` and a lesson template, including the rule for
  attributing third-party material under the content licence.
- Lesson M1 and the `pbc.mechanics` code and unit tests it needs.

**Out of scope.** The learning path page and navigation between lessons (F03),
Lean and agent display forms (F08, F09), widgets (F07), further lessons.

**Dependencies.** F01.

**Acceptance criteria.**

1. Lesson M1 is published and contains every required section.
2. Each lesson source check has a test showing it fails on a violating
   lesson: missing metadata field, missing required section, non-executed
   Python block without the "not verified" marker, figure without alt text,
   committed generated figure. A test also shows that a file at the replay
   fixture location passes the committed-artifact check.
3. A by-reference excerpt on the built page is textually identical to the
   source in `src/pbc` at the built commit, shown by a test.
4. Running the commands in M1's "Reproduce this" section on macOS and on
   Linux reproduces every number on the page at the displayed precision.
5. Every numerical claim in M1 is the output of an executed cell, and M1's
   numerical method is validated against the closed-form solution in a unit
   test with an explicit tolerance.
6. The lesson page is fully readable with JavaScript disabled, shows
   equations as MathML, passes the automated accessibility scan, and executes
   within 30 seconds.
7. Material marked "not verified" renders a visible label on the page.
8. The authoring guide lets a second lesson be created from the template
   without reading existing lesson sources; the reviewer confirms this by
   following it.

**Risk.** Medium. The format is expensive to change once several lessons use
it. The by-reference helper and the "not verified" check carry the site's
integrity guarantee, so they need direct tests.

**Detailed implementation plan expected.** Yes.

### F03 — Learning path

**Goal.** Make the ordered learning path visible everywhere, so a learner
always knows where they are and what comes next.

**User-visible outcome.** A learning path page lists strands in order and,
within each, lessons with their order, difficulty, and prerequisites. Every
lesson shows its strand, position, difficulty, linked prerequisites, and
previous and next links.

**In scope.**

- One difficulty scale defined in one place and explained on the path page.
- Path page, lesson header, and previous and next links, all generated from
  lesson front matter.
- Validation of the path: unique lesson IDs, prerequisites exist, no cycles,
  prerequisites come earlier in the path, no gaps or duplicates in order.
- A strand appears only when it has a published lesson.
- Navigation that works without JavaScript and on phone, tablet, and desktop
  widths.

**Out of scope.** Progress tracking, recommendations, and any stored learner
state (F13, F14). Site search.

**Dependencies.** F02.

**Acceptance criteria.**

1. The path page and every lesson header are generated from front matter;
   adding a lesson requires no edit to any hand-maintained list.
2. Each path validation rule has a test showing the build fails on a
   violation: duplicate ID, unknown prerequisite, cycle, prerequisite later
   in the path.
3. From the home page, a learner reaches every published lesson, and from
   any lesson its previous lesson, next lesson, and prerequisites, with
   JavaScript disabled.
4. The path page and a lesson page are usable at phone, tablet, and desktop
   widths without horizontal scrolling of the page, shown by a built-site
   check.
5. The path page passes the automated accessibility scan.

**Risk.** Medium. Quarto has no built-in validation of custom metadata, so
the generation and validation code is project-owned.

**Detailed implementation plan expected.** Yes.

### F04 — Mechanics lessons: Newton's laws and projectile motion with drag

**Goal.** Move from kinematics to dynamics: forces as functions, a generic
stepping interface, and a problem without a closed-form solution.

**User-visible outcome.** Lessons M2 and M3 are published in the mechanics
strand.

**In scope.**

- Lesson M2 and lesson M3 as listed in the MVP lesson list, each in the F02
  format.
- The `pbc.mechanics` code they need, including the stepping interface later
  lessons and the agent lesson reuse, with unit tests.

**Out of scope.** Integrators beyond what M2 and M3 need (F05). Changes to the
lesson format or checks, unless a defect is found; such changes get their own
Issue.

**Dependencies.** F02.

**Acceptance criteria.**

1. M2 and M3 are published, pass all lesson and built-site checks, and each
   executes within 30 seconds.
2. M2's simulation is validated in a unit test against the analytic solution
   for linear drag, with an explicit tolerance.
3. M3's simulation is validated in unit tests by its drag-free limit and by
   convergence under time-step refinement.
4. Each lesson states its modelling assumptions and what breaks when they do
   not hold.
5. Each lesson has at least two exercises with on-page solutions, and the
   solutions' numerical answers come from executed code.
6. The simulation functions M3 uses are importable from `pbc` with documented
   parameters and units.

**Risk.** Medium. Physics and numerical correctness need independent review;
passing checks do not prove a lesson teaches the right thing.

**Detailed implementation plan expected.** Yes, short: lesson outline, code
interface, validation strategy.

### F05 — Mechanics lessons: the harmonic oscillator and numerical integrators

**Goal.** Teach how the choice of integrator changes what a simulation can be
trusted for, using the harmonic oscillator as the test system.

**User-visible outcome.** Lessons M4 and M5 are published in the mechanics
strand.

**In scope.**

- Lesson M4 and lesson M5 as listed in the MVP lesson list.
- Explicit Euler, symplectic Euler, velocity Verlet, and Runge-Kutta 4 in
  `pbc.mechanics` behind the F04 stepping interface, with unit tests.

**Out of scope.** Adaptive step-size methods beyond a pointer to further
reading. The formal proof of the Euler energy result (F08). The interactive
comparison (F07).

**Dependencies.** F04.

**Acceptance criteria.**

1. M4 and M5 are published, pass all lesson and built-site checks, and each
   executes within 30 seconds.
2. Unit tests verify the empirical order of accuracy of each integrator on
   the harmonic oscillator.
3. M4 shows, from executed code, that explicit Euler's energy grows by the
   same factor every step, and states that factor; this is the claim F08
   proves.
4. M5 compares the four integrators on accuracy, energy behaviour, and cost,
   with every figure and number produced by executed code.
5. Each lesson states its assumptions and has at least two exercises with
   on-page solutions.

**Risk.** Medium. Same content risk as F04. The integrator interface is
reused by F06, F07, F08, and F09, so a poor interface is costly later.

**Detailed implementation plan expected.** Yes, short.

### F06 — Mechanics lessons: energy, momentum, and a capstone orbit

**Goal.** Complete the mechanics course with the conservation laws as
diagnostics and a capstone that uses everything before it.

**User-visible outcome.** Lessons M6, M7, and M8 are published; the mechanics
strand is complete at eight lessons.

**In scope.**

- Lessons M6, M7, and M8 as listed in the MVP lesson list.
- The `pbc.mechanics` code they need (pendulum, pairwise forces and
  collisions, two-body central force), with unit tests.

**Out of scope.** Many-particle simulations and emergent behaviour (F11).
Lagrangian or Hamiltonian formalism (a candidate for F15).

**Dependencies.** F03, F05. F03 provides the learning path that criterion 5
checks.

**Acceptance criteria.**

1. M6, M7, and M8 are published, pass all lesson and built-site checks, and
   each executes within 30 seconds.
2. Unit tests verify momentum conservation to round-off for pairwise forces,
   and energy and angular momentum behaviour for the orbit under a symplectic
   integrator within a stated bound.
3. M8 reuses code from earlier lessons through `pbc`, not by copying it.
4. Each lesson states its assumptions and has at least two exercises with
   on-page solutions.
5. The learning path shows eight mechanics lessons in order with consistent
   prerequisites.

**Risk.** Medium. Same content risk as F04. Three lessons make this the
largest content feature; if review shows it is too large, split M8 into its
own Issue without changing this roadmap's lesson list.

**Detailed implementation plan expected.** Yes, short.

### F07 — Interactive visualizations

**Goal.** Establish how optional JavaScript widgets are built, tested, and
degraded, and ship the first one where it adds understanding.

**User-visible outcome.** In a mechanics lesson (default: the integrator
comparison in M5), a learner changes parameters such as the time step and the
integrator and sees the trajectory and energy respond. Without JavaScript, the
same place shows a static figure and an explanation.

**In scope.**

- Widget convention: a dependency-free, self-hosted ES module that enhances a
  static figure already in the page.
- Data for widgets computed by executed Python cells at build time and
  embedded in the page; or, where the widget computes in the browser, a test
  comparing its results with `pbc` reference values.
- Keyboard operability, visible focus, text alternative, and respect for
  reduced-motion preferences.
- Built-site tests for the widget and for its fallback.
- One widget in one published lesson, and a section on widgets in the
  authoring guide.

**Out of scope.** In-browser Python. Any JavaScript package manager or
bundler. Widgets that store state (F13). A widget in every lesson.

**Dependencies.** F05.

**Acceptance criteria.**

1. With JavaScript disabled, the lesson shows a static figure and text in
   place of the widget, and no content is lost.
2. With JavaScript enabled, the widget responds to its controls, is fully
   operable by keyboard, and passes the automated accessibility scan.
3. The widget loads no code or data from another origin and writes nothing to
   cookies or browser storage, shown by a built-site check.
4. Values the widget displays agree with `pbc` reference values within a
   stated tolerance, shown by a test.
5. The page has no layout shift when the widget loads, shown by reserved
   dimensions in the markup.
6. The build remains deterministic and within the CI budget.

**Risk.** Medium. Physics duplicated in JavaScript can drift from the tested
Python; criterion 4 exists for that. The requirements ask for interactives
only "where useful", so this is the MVP feature with the least requirement
pressure: if the human wants a smaller MVP, it can move after F10 without
affecting other features.

**Detailed implementation plan expected.** Yes.

### F08 — Formal proofs strand: first Lean lesson

**Goal.** Open the third pillar: a physics result from the mechanics course,
stated and proved in Lean 4 with Mathlib, shown on the site and checked by CI.

**User-visible outcome.** Lesson L1 is published in the formal proofs strand.
A learner reads the statement and proof with syntax highlighting, sees that CI
compiled it, and can open it in the repository or in the Lean web editor.

**In scope.**

- Lean display form: excerpts included by reference from files in `lean/`,
  with a vendored Lean syntax definition for highlighting.
- Links from the lesson to the repository file at the built commit and to
  the Lean web editor loading that file, labelled as possibly running a
  different Mathlib version.
- Visible CI evidence on the page: the commit and the toolchain and Mathlib
  versions the proof was compiled with.
- Lesson L1: the kinematic identity for constant acceleration, and the
  per-step energy growth of explicit Euler on the harmonic oscillator that M4
  demonstrates numerically.
- Authoring guide section on Lean lessons, including the rule that physical
  assumptions are hypotheses, not axioms, and that proofs are about models,
  not about the Python code.

**Out of scope.** Proofs about the Python implementation. Hover or type
information on the page. Proofs involving derivatives or differential
equations, unless the plan shows they fit; they are candidates for later
lessons.

**Dependencies.** F03, F05.

**Acceptance criteria.**

1. L1 is published in the `lean` strand and passes all lesson and built-site
   checks.
2. Every Lean excerpt on the page is textually identical to its source in
   `lean/` at the built commit, shown by a test.
3. `lake build` compiles every theorem L1 displays; a `sorry` or a
   project-declared axiom in any Lean file fails verification, shown by a
   test.
4. Each theorem's physical assumptions appear as explicit hypotheses and are
   explained in the lesson's assumptions section.
5. Lean code is highlighted at build time and readable with JavaScript
   disabled, with colour contrast that passes the automated scan.
6. The repository link points at the built commit, and the web editor link
   opens the proof; the page states which is authoritative.
7. The lesson connects each theorem to the numerical observation it proves
   and says what the proof does not cover.
8. Verification stays within the CI budget.

**Risk.** Medium. The vendored syntax definition may highlight imperfectly.
The public web editor's Mathlib version can drift from the pinned one. Proof
effort is hard to estimate; the chosen theorems are algebraic to keep it low.

**Detailed implementation plan expected.** Yes.

### F09 — LLM agents strand: first agent-driven experiment lesson

**Goal.** Open the second pillar: an LLM agent that designs and runs an
experiment on a mechanics simulation, runnable by the learner with their own
key and verified in CI without any key.

**User-visible outcome.** Lesson A1 is published in the LLM agents strand. A
learner reads how the agent is built, sees a recorded run whose tool results
were recomputed by CI, and runs the agent locally with their own API key
against the projectile-with-drag simulation.

**In scope.**

- The agent harness in `pbc.agents` as decided in ADR 004: model client
  interface, tool allowlist with validated and bounded arguments, run loop
  with a step limit, transcript.
- A replay client and one live client for the default provider, with the
  provider SDK as an optional dependency.
- Agent display form: the replay run rendered on the page, recorded model
  messages labelled as recorded.
- A1's replay fixture, committed under the rule of ADR 002: recorded model
  messages and expected tool results, no credentials, at the fixture location
  F02 defined, so the committed-artifact check accepts it. The page shows the
  recomputed tool results, never the recorded ones.
- Key handling: environment variable only, documented in the lesson and in
  `.env.example` by name; nothing printed, logged, or written to transcripts.
- Lesson A1, including a plain statement of what the agent may and may not
  do, and what a learner should expect to differ in a live run.
- Authoring guide section on agent lessons and on re-recording a transcript.

**Out of scope.** Agents that write or execute code, use a shell, or access
the network. Multi-agent systems. Calling an LLM from the site or from CI.
Agent-based modelling (F11).

**Dependencies.** F03, F04. Before implementation, the human decides the
default LLM provider (unresolved question 1 of the requirements) and the
decision is recorded in the feature plan.

**Acceptance criteria.**

1. A1 is published in the `agents-llm` strand and passes all lesson and
   built-site checks.
2. Verification runs A1 with the replay client, with no network access and no
   credential, and recomputes every tool result. A test shows that a changed
   simulation result beyond tolerance fails the replay with a message that
   says how to re-record.
3. A tool call outside the allowlist, or with arguments outside their bounds,
   is rejected without being executed, shown by tests.
4. The harness has no code path that evaluates model output as code, runs a
   shell command, or opens a network connection other than the live client's
   provider request, confirmed by review and by tests of the tool dispatch.
5. A test shows that a key set in the environment appears in no log line,
   printed output, exception message, or transcript.
6. No workflow references an LLM secret, and the built site contains no
   request to an LLM provider.
7. Switching provider requires implementing one client and changing one
   configuration value; the lesson shows where.
8. The maintainer has run A1 live once with their own key and recorded the
   committed replay fixture from that run; it sits at the declared fixture
   location, contains no credential, and passes the committed-artifact check.
   The page labels the model and date.
9. The lesson instructs learners to keep keys in local environment variables
   and never in code, notebooks, or committed files.

**Risk.** High. The feature handles credentials and executes model-directed
actions. It needs security-focused independent review and explicit human
approval of the allowlist boundary. Other risks: provider API changes; replay
that is too brittle when simulation code changes.

**Detailed implementation plan expected.** Yes.

### F10 — MVP release readiness and launch

**Goal.** Confirm the first release meets the requirements a reader cannot
verify from CI alone, settle the remaining launch decision, and declare the
MVP released.

**User-visible outcome.** The site presents a complete first release: ten
lessons across three strands, a coherent learning path, and clear pages on how
to reproduce, how to contribute, and the licences.

**In scope.**

- Manual WCAG 2.1 AA audit of the site chrome and one lesson of each strand
  (keyboard, screen reader, zoom and reflow, contrast), with defects fixed or
  filed.
- Reading pass over all lessons for consistent structure, terminology,
  prerequisites, and difficulty levels.
- A cold-start reproduction on macOS and Linux following only the public
  documentation.
- The custom domain decision (unresolved question 3 of the requirements),
  taken by the human, and applied if chosen.
- Contribution information for outside readers: how to report an error, the
  licence terms for contributions, and that the content proposal workflow is
  planned (F12).
- A release tag and a release note.

**Out of scope.** New lessons or new site capabilities. The content proposal
workflow itself (F12). Announcing or marketing the site.

**Dependencies.** F01, F02, F03, F04, F05, F06, F08, F09, and F07 unless the
human has moved it after the MVP.

**Acceptance criteria.**

1. Every row of this roadmap's MVP requirements coverage table is checked
   against the published site and recorded as met in the pull request.
2. The manual accessibility audit is recorded; no known WCAG 2.1 A or AA
   failure remains open without a linked Issue and the human's acceptance.
3. A reviewer who did not write the lessons reproduces one lesson of each
   strand from a clean clone on macOS and on Linux using only the public
   documentation.
4. The custom domain decision is recorded; if a domain is chosen, the site is
   served over HTTPS from it and all internal links still resolve.
5. Every lesson's assumptions, prerequisites, and difficulty are present and
   consistent with the learning path.
6. Measured CI times for the complete MVP are within the budget in the
   architecture, or the over-budget response of ADR 003 has been applied.
7. The repository has a release tag for the MVP.

**Risk.** Medium. The audit can uncover theme-level accessibility defects
that are expensive to fix late; running the automated scan from F01 onward
limits this. A custom domain changes DNS and Pages settings and needs the
human.

**Detailed implementation plan expected.** No. A checklist in the Issue is
enough; defects found become their own Issues.

## Phase 2 — After the MVP

These features are in scope for the project and out of scope for the MVP.
Their descriptions are deliberately coarser. Revalidate each against the
architecture and the requirements before creating its Issue.

### F11 — Agent-based modelling strand: first lesson

**Goal.** Open the agent-based modelling strand: many simple interacting
agents, no LLM, and behaviour that emerges from local rules.

**User-visible outcome.** The first lesson of the `agents-abm` strand is
published, and the strand appears in the learning path.

**In scope.**

- One lesson that builds a multi-agent simulation on the mechanics course,
  default topic: many colliding particles in a box, from pairwise collisions
  to pressure and the velocity distribution.
- The `pbc` code it needs, with unit tests, and seeded randomness so the
  build stays deterministic.

**Out of scope.** LLM agents. A general agent-based modelling framework or a
third-party one, unless the plan justifies it. Statistical mechanics beyond
what the lesson needs.

**Dependencies.** F03, F06. The requirements name this lesson the first
follow-up after the MVP.

**Acceptance criteria.**

1. The lesson is published in the `agents-abm` strand in the F02 format and
   passes all lesson and built-site checks within the per-lesson budget.
2. All randomness is seeded and two builds are byte-identical.
3. Unit tests check at least one emergent quantity against its theoretical
   value within a stated statistical tolerance.
4. The lesson states its modelling assumptions and how agent-based modelling
   differs from the LLM agents strand.

**Risk.** Medium. Many-particle simulations can exceed the 30 second lesson
budget; the problem size must be chosen for it.

**Detailed implementation plan expected.** Yes, short.

### F12 — Content proposal workflow through GitHub Issues

**Goal.** Let outside contributors and agents propose new content, have it
assessed, and have it drafted and merged through reviewed pull requests.

**User-visible outcome.** A contributor opens a lesson proposal Issue from a
form, receives an assessment against published criteria, and an accepted
proposal becomes a drafted lesson in a pull request that passes the same
verification as any lesson.

**In scope.**

- Issue form for lesson proposals and published assessment criteria (fit to
  the learning path, prerequisites, verifiability by code or proof, scope).
- A documented path from accepted proposal to drafted lesson, reusing the
  repository's existing Issue, plan, implement, and review scripts where they
  fit.
- Agent-assisted drafting, with the decision on where the agent runs and
  whether CI may hold an LLM key (unresolved question 2 of the requirements)
  taken by the human during planning. The requirements recommend the
  maintainer's machine first.
- Contribution licence terms applied to proposals and drafts.

**Out of scope.** Automatic merging. Any change that gives fork pull requests
secrets or write permissions. Public discussion features beyond Issues.

**Dependencies.** F10.

**Acceptance criteria.**

1. A proposal can be opened from an Issue form and is assessed against
   written criteria, with the outcome recorded on the Issue.
2. An accepted proposal reaches `main` only through a reviewed pull request
   that passes `verify`.
3. The human's decision on LLM credentials in CI is recorded. If CI holds a
   key, a new ADR records the threat model and workflows on fork pull
   requests still receive no secrets; if not, no workflow references an LLM
   secret.
4. Agent-drafted content is identified as such in its pull request.
5. The workflow is documented for contributors and for the maintainer.

**Risk.** High if a credential is introduced into CI, otherwise Medium.
Workflows triggered by Issues or by fork pull requests are a common source of
secret exposure and need security-focused review.

**Detailed implementation plan expected.** Yes.

### F13 — Self-check quizzes and browser-local progress

**Goal.** Give learners machine-readable self-checks and a record of their
progress that never leaves their browser.

**User-visible outcome.** Lessons offer self-check questions with immediate
feedback. The learning path shows which lessons the learner has completed. A
control clears all stored state.

**In scope.**

- A self-check question format authored in lessons, with answers and
  feedback, that degrades to the existing exercise-with-solution pattern
  without JavaScript.
- Progress and self-check results stored in browser local storage under a
  versioned, site-specific key, keyed by stable lesson IDs.
- A visible explanation of what is stored and a clear-data control.
- A machine-readable export of the learning path in the built site for
  client-side use.

**Out of scope.** Accounts, sync, export to any server, grading or
certification, recommendations (F14).

**Dependencies.** F03, F07, F10.

**Acceptance criteria.**

1. Completing a self-check updates the learner's progress, which persists
   across page loads in the same browser and is removed by the clear-data
   control.
2. A built-site test shows that no network request carries learner state and
   that no cookie is set.
3. With JavaScript disabled, every self-check is still usable as an exercise
   with a visible solution.
4. A change to the stored data format migrates or safely discards old data,
   shown by a test.
5. Self-check and progress controls are operable by keyboard and pass the
   automated accessibility scan.

**Risk.** Medium. This is the first feature that stores anything in the
browser, so the privacy invariant needs a direct test.

**Detailed implementation plan expected.** Yes.

### F14 — Adaptive recommendations

**Goal.** Recommend the next lesson or extra exercises from the learner's
local self-check results.

**User-visible outcome.** The learning path and lesson pages suggest what to
do next, with the reason for each suggestion, computed entirely in the
browser.

**In scope.**

- Recommendation rules that use only the path's prerequisite graph and the
  locally stored results.
- An explanation of each recommendation and a way to ignore it.

**Out of scope.** Any server-side or LLM-based recommendation. Learner
modelling beyond the stored self-check results. Analytics.

**Dependencies.** F13.

**Acceptance criteria.**

1. Given a fixed stored state, recommendations are deterministic and covered
   by tests of the rules.
2. Each recommendation states why it was made.
3. A built-site test shows that computing recommendations makes no network
   request.
4. Without stored state or without JavaScript, the site shows the plain
   learning path with no error.

**Risk.** Medium. The value of the feature depends on recommendation quality,
which tests cannot establish; plan a review with real use.

**Detailed implementation plan expected.** Yes.

### F15 — Second course on the three-pillar path

**Dropped by the change cycle `final-curriculum` (2026-10-12; ADR 013
decision 7).** F15 was never started and has no Issue. Its goal, a course
beyond mechanics, is delivered by F62 (the eight courses and the reference
curriculum) and by the first lesson feature of each course (F70, F71, F72,
F73, F89, F91, F94), each with the human's approval of the lesson list in
its Issue, as this block asked. Its rule that a course contains an agent
lesson and a Lean lesson is not carried: the method paths are a view over
the courses, and proofs are added where they add physics insight. The ID
F15 is never reused. The block below is kept as approved, as history.

**Goal.** Grow beyond mechanics with a second course that again spans
simulation, agents, and proof.

**User-visible outcome.** A second course appears in the learning path, with
its own ordered lessons and prerequisites on the mechanics course.

**In scope.**

- The human chooses the course topic and approves its lesson list in the
  Issue (candidates: oscillations and waves, Lagrangian and Hamiltonian
  mechanics, statistical physics).
- Lessons in the existing format, including at least one agent lesson and one
  Lean lesson.
- Any extension of the learning path model needed to show more than one
  course.

**Out of scope.** Changes to the pipeline or lesson format beyond what a
second course strictly needs. A language other than English.

**Dependencies.** F10. F12 is not required, but the course may be the first
user of that workflow if it exists.

**Acceptance criteria.**

1. The approved lesson list is recorded in the Issue before drafting starts.
2. Every lesson of the course passes the same checks as the mechanics course,
   and total verification stays within the CI budget or the over-budget
   response of ADR 003 has been applied.
3. The learning path shows both courses with correct prerequisites.
4. The course contains at least one agent lesson and one Lean lesson.

**Risk.** Medium. Execution time grows with every lesson; this course is the
most likely point at which the single verify job must be split.

**Detailed implementation plan expected.** Yes, starting with a course
outline; the course will likely be delivered as several Issues.

## Phase 3 — Next phase (change cycle `physics-next-phase`)

Every feature in this phase comes from `docs/changes/physics-next-phase.md`
(2026-10-09); each block names its candidate or section there. The wave R0
and the wave R1 are specified in detail, because they are the first wave of
the change request. Waves R2 to R5 are deliberately coarser: revalidate each
feature against the architecture, the requirements, and the delivered
features before creating its Issue, and expect a feature plan to refine it.

What every feature of this phase inherits, without repeating it in each
block: the invariants of `docs/architecture.md` (static site, no other-origin
resource, readable without JavaScript, WCAG 2.1 AA, deterministic builds,
verified display forms, no credential anywhere in CI); the lesson format and
checks of `docs/authoring.md`; the CI budget of ADR 003; and the editorial
standard of the requirements ("UX expectations"): self-contained
progressive-depth lessons, purposeful researched external references,
scientifically faithful figures, typed claims.

### Wave R0 — Keep the pipeline within budget

### F58 — Parallel verification jobs behind one required check

**Source.** `docs/release-readiness.md` (F10, "CI time against the budget")
and ADR 003, decision 6; change request Section 14, point 7 (verification
strategy). No candidate number.

**Problem.** With eleven lessons the `verify` job takes about 15 minutes
with warm caches against a 12 minute budget (measured 2026-10-08, runs
37857338092 and 37859587548). The first response of ADR 003 was applied in
F10 and saved about a minute and a half. Every feature of this phase adds
pages, and every page adds execution and checking time, so the second
response is due. The roadmap recommends it before them without making it a
dependency of any feature: the per-check budgets and the over-budget
response of ADR 003 decision 6 stay the guard while the overrun lasts.

**Goal.** Apply the second response of ADR 003: run named subsets of the
same `verify.conf` checks in parallel CI jobs behind one aggregate required
status check, without changing what is checked or how a laptop verifies.

**User-visible outcome.** A contributor still sees one required check,
`verify`, on every pull request; it finishes within the budget. Locally,
`./scripts/verify.sh` is unchanged.

**In scope.**

- A subset mechanism in `scripts/verify.sh` (for example `--only <group>`),
  with groups declared in `scripts/verify.conf` by a tag on each check, so
  that every check stays declared in one file and no check is declared in
  workflow YAML. A check without a tag belongs to a default group, so a new
  check is never silently skipped.
- The workflow: one job per group in parallel, each with the setup and
  caches it needs, and one aggregate job named `verify` that fails when any
  group fails, is skipped, or is cancelled. The deploy job depends on the
  aggregate job and still publishes the artifact the site-building group
  uploaded.
- The determinism check and the built-site checks consume the site that the
  build group produced, either in the same job or through a job artifact,
  without rebuilding in a way that could differ from what is published.
- A test in `tests/integration/test_ci_workflow.py` that the union of the
  groups the workflow runs is every check of `verify.conf` and of
  `verify-workflow.conf`, that the aggregate job is the only job named
  `verify`, and that no job has write permissions except deploy.
- An ADR that amends decision 2 of ADR 003 and decision 2 of ADR 005 (the
  single verify job that is the one required status check) with the group
  design, written in this feature as ADR 005 and ADR 006 were, and the matching update of
  the CI section of `docs/architecture.md` and of `docs/deployment.md`.
- The required status check of the `main` ruleset keeps its name `verify`,
  so no ruleset change is needed; if GitHub requires one, it is a human step
  recorded in the pull request.

**Out of scope.** Dropping, filtering, or scheduling a check (not available
without a new ADR). Changing any check's content. Self-hosted runners.

**Dependencies.** F10. ADR 003 decision 6 authorises the split.

**Acceptance criteria.**

1. A warm-cache pull request run finishes within 12 minutes wall clock,
   measured on three consecutive pull requests and recorded in the pull
   request and in `docs/release-readiness.md`'s table. (Revised to a
   measured and recorded run time by the owner on 2026-10-12, ADR 012
   decision 8; the budget itself is 20 minutes since ADR 015, 2026-10-15.)
2. Every check of `verify.conf` and `verify-workflow.conf` runs in exactly
   one group; a test fails when a check is in no group or in two.
3. `./scripts/verify.sh` without arguments runs every product check locally
   as before; `--only <group>` runs one group; a test covers both.
4. A failing check in any group fails the aggregate `verify` check, shown by
   a test on a violating input per group, and a pull request with a failing
   group cannot be merged.
5. The deploy job publishes the artifact built by the build group of the
   same commit; no job builds the site twice for publication.
6. Workflow permissions stay `contents: read` by default, with write scopes
   only in the deploy job; every action is pinned by SHA.
7. The ADR amending ADR 003 and ADR 005 is accepted with the merge, and the
   status of both names it.

**Risk.** High. The feature changes the CI workflow structure, the required
status check, and the deploy chain, which need explicit human approval and
security-focused review. Technical risk: cache restores multiplied by the
number of jobs; a group that needs Mathlib and the browser both.

**Detailed implementation plan expected.** Yes.

### Wave R1 — Clarity, usability, identity, and the editorial pilots

Order within the wave, by dependency: F44 and F57 and F37 and F35 and F36
and F39 are independent of each other and may run in parallel worktrees;
F25 after F57; F26 and F27 after F37; F28 after F37, F44, F35, F36; F30
after F28; F29 after the M5 pilot of F30 has been reviewed.

### F44 — Visual design and accessibility system

**Source.** Candidate F44; Section 8.3 (component rules); Section 10.2
(footer attribution slot); Section 14 (design constraints).

**Problem.** The site runs on Quarto's default theme with one short
stylesheet. The lesson constructs the next phase adds (claim labels, figure
status, "Go deeper" blocks, self-checks, hint steps, cards, a footer
attribution line) have no visual language, and the manual audit of F10 left
two observations open: no skip link, and a low-contrast focus ring on the
navigation.

**Goal.** One coherent, accessible visual system for the site chrome and the
lesson components, defined as CSS tokens and a small set of component
styles, so that later features add components without inventing styles.

**User-visible outcome.** The site reads consistently on phone, tablet, and
desktop: clear heading hierarchy, readable figures at every width, a skip
link, visible focus everywhere, accessible colours, and a discreet footer
line that F57 fills. Nothing a reader relies on changes meaning.

**In scope.**

- Design tokens in `site/assets/site.css`: type scale, spacing, colour
  palette with contrast-checked pairs for text, links, labels, and the five
  figure-status and four claim-type labels, and the colour-blind-safe
  sequence Matplotlib figures use, exposed to lesson code through one
  `pbc.authoring` constant so figures and CSS agree.
- Component styles: lesson header, "What you'll learn", assumptions list,
  claim labels, figure status and caption, semantic result tables (F36),
  annotated excerpts (F35), "Go deeper" block, self-check and hint details,
  path cards (F27), the prerequisite graph container (F26), the footer
  attribution slot (F57).
- A skip link and a focus style for the navigation that passes the
  contrast of WCAG 2.2's focus appearance criterion, closing the two
  observations of F10's audit.
- The page payload budget check of the architecture (initial payload
  1.5 MB), added to `tests/e2e` with the measured sizes of every page
  recorded in the pull request.
- A section in `docs/authoring.md` on the components and the tokens.

**Out of scope.** A JavaScript build toolchain, a third-party CSS framework,
a theme switch, decorative imagery, any branding graphic, any marketing
surface. Content changes to lessons (the editorial passes). [Note of the
change cycle `scientific-atelier-atlas`, 2026-10-17: "decorative imagery,
any branding graphic" is superseded by the three asset classes of
requirements decision 37 and ADR 018: interface artwork (the project mark,
the map's course areas, the openings), conceptual illustrations, and
accessible animation are allowed where that record says, each with its
source in the repository; the toolchain, framework, theme-switch, and
marketing-surface exclusions stand. The tokens and components of F44 are
extended by F123, not replaced. This block is the record of what F44
delivered and is not rewritten.]

**Dependencies.** F10.

**Acceptance criteria.**

1. Every page passes the automated WCAG 2.1 A/AA scan, and the skip link and
   navigation focus pass the scripted keyboard pass of F10's audit on the
   same scope, recorded in the pull request.
2. Every colour pair used for text and labels has a contrast ratio of at
   least 4.5:1 (3:1 for large text and controls), shown by a unit test over
   the token definitions.
3. The eleven lesson pages, the path page, and the chrome pages are usable
   at 320, 768, and 1280 CSS px without two-way scrolling, and figures scale
   to the viewport, shown by the built-site checks.
4. A sample page that uses every component renders correctly in the current
   Chromium, Firefox, and WebKit engines, recorded with screenshots in the
   pull request.
5. The initial payload of every page is at most 1.5 MB, shown by the new
   built-site check, with the sizes recorded.
6. Physics content stays central: no page gains an element that is not
   content, navigation, licence, or attribution; the built-site check for
   other-origin resources and cookies still passes.
7. The build stays deterministic and within the CI budget.

**Risk.** Medium. Theme-level changes touch every page; the accessibility
scan and the three-engine check limit regressions.

**Detailed implementation plan expected.** Yes, short: tokens, component
list, and the check.

### F57 — Open-source identity, attribution, and citation

**Source.** Section 10 of the change request (unnumbered proposal); Section
3G; requirements decisions 20 and 21; unresolved questions 5 and 7.

**Decision on placement (Section 3G).** One small independently testable
feature, not deliverables scattered over F25, F44, and F12: the acceptance
checks (a) to (h) of Section 10.5 span the home page, footer, About, README,
`CITATION.cff`, and the Issue forms, and they are testable together. F25
and F44 consume the canonical text this feature defines; F12's Issue form
pattern is reused, not rebuilt. The JIDAI website page and the organization
profile are outside this repository (see "Candidate mapping").

**Decisions recorded before any copy is written** (from the requirements):

- Creator: Ahmet Taspinar, TU Delft Applied Physics alumnus, founder of
  JIDAI. Canonical description: "Physics by Construction is a free,
  open-source educational initiative by JIDAI, created by Ahmet Taspinar."
  One sentence, carried verbatim on the home page, the About page, the
  README, and in `CITATION.cff`. The footer carries a shortened attribution
  line derived from the same source, the sentence without its subject ("An
  open-source educational initiative by JIDAI, created by Ahmet Taspinar");
  no surface types either text by hand.
- Rights: the copyright line "Ahmet Taspinar and the Physics by Construction
  contributors" stays; JIDAI is the initiative's company, not a copyright
  holder, funder, or university partner; MIT for code and CC BY 4.0 for
  content are unchanged; no legal notice changes in this feature.
- Repository and address: `github.com/taspinar/physics-by-construction` and
  the Pages URL stay; the `jidai-nl` organization exists with the creator as
  owner, may link to the repository from its profile (a human action outside
  this repository), and no transfer follows.
- Citation: `CITATION.cff` names the actual authors and the project URL and
  repository, with the licence fields; no DOI until a release policy exists.
- Community: nothing requires an account, contact with JIDAI, tracking, or a
  corporate link; no marketing surface.

**Goal.** Make the creator and the JIDAI association discoverable, truthful,
and discreet, give the project citation metadata, and give contributors two
more entry points, without touching ownership, licences, or addresses.

**User-visible outcome.** An ordinary visitor understands the project from
the home page and finds one low-key link to the creator and JIDAI context;
the About page explains the creator, what JIDAI is, why the project is open
source, how to cite, and how to contribute; the footer carries one concise
line; the README has the same description; a researcher can cite the
project from `CITATION.cff`; a contributor can open a scientific correction
or a dataset suggestion from a form.

**In scope.**

- The canonical description and attribution text in one place
  (`site/_quarto.yml` metadata or a `pbc.authoring` constant) and rendered
  from there on the home page (F25 places it), the footer, the About page,
  and the README; the instructor packs (F59) and `CITATION.cff` reuse it.
- Footer line: the shortened attribution line derived from the canonical
  sentence, with one link to `https://jidai.nl`;
  readable without JavaScript and at phone width; not repeated in lessons.
- About page sections: creator and background; what JIDAI is and what it
  does for the project, distinguishing creator and maintainer from rights
  holder; why open source and editorial independence; how to cite (the
  `CITATION.cff` text); how to contribute; the existing licence and
  third-party material sections unchanged.
- `CITATION.cff` validated against the CFF schema by a test, with the
  authors, the project and repository URLs, `license: MIT` for the code and
  the content licence stated in the message, and the version left to the
  release tag once it exists.
- README: the description, the creator and JIDAI line, the homepage, the
  contribution entry points, and where the licences are; the physics
  overview stays first.
- Two Issue forms reusing the F12 pattern: `scientific-correction.yml`
  (page, the statement, the correction, the source and its licence, the
  evidence) and `dataset-suggestion.yml` (source URL or DOI, creator,
  licence, measurement type, size, what a lesson could learn from it);
  `CONTRIBUTING.md` and the Contribute page name them. A scientific
  submission requires a source, a licence, and independent review, which
  the forms say.
- A built-site check that the canonical sentence appears on the home page
  and the About page, that the footer carries the derived line, that no
  other page repeats the footer line in its content, that the home page's
  content outside the footer carries exactly one attribution link and it
  leads to the About page, and that the site still loads nothing from
  another origin.
- An "Identity and attribution" section in `docs/authoring.md` stating the
  rules above for every future page.

**Out of scope.** Changing copyright holders, licences, repository owner,
or Pages URL. A JIDAI.nl page. The organization profile. Logos, banners,
badges beyond a plain text line in the README, splash screens, forms that
collect contact details, any analytics. University names or logos.

**Dependencies.** F10; F12, whose Issue-form set, `CONTRIBUTING.md`, and
Contribute page this feature extends. The human approves the final wording
of the footer, About, README, and `CITATION.cff` on the pull request before
merge.

**Acceptance criteria.**

1. (a) From the home page, a visitor reaches the About page's creator and
   JIDAI section in one click, and that is the only attribution link in the
   home page's content, excluding the site footer, whose derived line
   carries the `https://jidai.nl` link on every page.
2. (b) Every statement about authorship, ownership, licences, JIDAI's role,
   and published versus planned content on the home, About, README, and
   `CITATION.cff` matches the decisions above; the human confirms it on the
   pull request.
3. (c) The canonical sentence is identical on the home page, the About page,
   the README, and in `CITATION.cff`, and the footer line is the shortened
   attribution derived from the same source, shown by a test that reads all
   five surfaces and compares them with the one source.
4. (d) The Contribute page and `CONTRIBUTING.md` describe how to correct,
   propose, and suggest a dataset without contacting JIDAI, and the five
   Issue forms (the existing bug, feature, and lesson-proposal forms and the
   two new ones) open with their required fields, shown by a schema test.
5. (e) No new account, analytics, lead form, mailing list, or outbound
   request; the other-origin and cookie checks pass.
6. (f) `LICENSE`, `LICENSE-CONTENT`, the repository address, and
   `website.site-url` are byte-identical to before the feature.
7. (g) The footer and About page pass the accessibility scan, the keyboard
   pass, the no-JavaScript check, and the width checks.
8. (h) All eleven lesson pages are unchanged by the feature, shown by a
   before-and-after comparison of the built pages recorded in the pull
   request. The comparison excludes the footer element and normalises the
   built commit, which every lesson page embeds and which differs between
   any two commits (the SHA in the excerpt links, in the Lean evidence box,
   and in "Reproduce this"); after that normalisation the pages are
   byte-identical. The same-commit determinism check is unchanged and still
   passes.
9. `CITATION.cff` validates and contains no DOI field.

**Risk.** Medium. Public copy about a company and a person must be accurate
and discreet; the human approves the wording. No technical risk.

**Detailed implementation plan expected.** No. The Issue holds the copy for
approval; a checklist is enough.

### F25 — Homepage narrative: Construct, Investigate, Verify

**Source.** Candidate F25; Section 1 (mission); Section 10.2 (homepage
row); Section 14, slice 1.

**Problem.** The home page presents three pillars, "Simulate, Experiment
with agents, Prove", and the requirements now state three activities,
Construct, Investigate, Verify, with real measurements as first-class
content that does not exist yet. The page must say so honestly.

**Goal.** A home page that states the mission in the approved terms, shows
what is published and what is planned without overstating either, and
leads to the learning path, the methods, and the About page.

**User-visible outcome.** A visitor learns in one screen what the site
teaches and how (Construct, Investigate, Verify), sees the eleven published
lessons and the mechanics course as published, sees the measured-data labs
and further courses as planned, with no date promised, and finds the
attribution line F57 defined.

**In scope.**

- The narrative: mission, the three activities with one concrete example
  each that exists on the site today (a simulation, an agent run, a proof),
  and a plain "what is published, what is planned" section generated from
  the lesson metadata and a short hand-maintained list of planned items
  that names this roadmap's IDs.
- The "One result, three ways" example kept or replaced by one that spans
  the three activities.
- The F57 attribution placement.
- Links to the path page by course and by method (F37, if delivered; else
  the current path page).

**Out of scope.** Any marketing tone, hero imagery, testimonials, claims of
adoption, counters, or news. Changes to lessons. [Note of the change cycle
`scientific-atelier-atlas`, 2026-10-17: the exclusion of hero imagery is
superseded for the one opening figure of the home page, a static figure
drawn by an existing verified implementation with its status and
provenance (requirements decision 36, ADR 018 decision 4, F124); marketing
tone, testimonials, claims of adoption, counters, and news stay excluded.
This block is the record of what F25 delivered and is not rewritten.]

**Dependencies.** F57 (the canonical description). F37 is not required;
the page links to what exists.

**Acceptance criteria.**

1. The page names Construct, Investigate, and Verify and links each to one
   published example, shown by a built-site test of the links.
2. The counts and names of published lessons on the page come from the
   lesson metadata, not from typed numbers, shown by a test that changes the
   lessons and rebuilds.
3. Every planned item on the page names a roadmap ID and is labelled
   planned; no planned item is linked as if it existed.
4. The page is readable without JavaScript, passes the accessibility scan,
   and fits phone width.
5. A reviewer who did not write the page confirms that every sentence about
   the site is true of the published site at that commit, recorded on the
   pull request.

**Risk.** Low.

**Detailed implementation plan expected.** No.

### F37 — Lesson metadata and course navigation

**Source.** Candidate F37; Section 1 (curriculum and navigation); Section
12 (F26 + F27 + F37 one source of truth); ADR 008.

**Decision on slicing (Section 12).** The shared source of truth, the
metadata extension and the path page by course and method, is this feature;
the prerequisite graph (F26) and the cards (F27) are separate consumers of
it, each deliverable and reviewable on its own.

**Problem.** The learning path is one linear list of four strands. The
requirements organise content as courses by subject with methods
cross-cutting, and ask that a lab belong to one primary course and link to
its extensions. There is no field for a course, a method, an outcome, or a
related lesson, and the path page cannot show them.

**Goal.** Extend the lesson metadata with `course`, `methods`, `outcomes`,
and `related`, keep the strands as URL groups and ordering, and generate
the learning path page by course with one path per method, all from front
matter.

**User-visible outcome.** The learning path page lists the mechanics course
with its eight core lessons and its agent, agent-based-modelling, and proof
extensions, then one section per method listing the lessons that use it. A
lesson header names its course, its methods, its position, its outcomes
("What you'll learn"), its prerequisites, its related lessons, and previous
and next. Every existing URL still works.

**In scope.**

- `COURSES` and `METHODS` vocabularies in `pbc.authoring.path`, next to
  `STRANDS` and `DIFFICULTIES`; the four new front-matter fields with
  validation (course exists, at least one method, two to five outcomes,
  related lessons exist and are not already among this lesson's
  prerequisites); the rule that a course appears only when it has a lesson.
- Migration of all eleven lessons: `course: mechanics` for every lesson,
  methods and outcomes written from each lesson's current description and
  text, related links one-directional from the prerequisite side: M3 → A1
  (`agent-experiment`), M7 → the gas lesson (`particles-in-a-box`), M1 → L1
  and M4 → L1 (`proving-what-the-simulation-showed`). The extension lesson
  keeps the mechanics lesson among its prerequisites and does not list it
  as related, so every pair passes the validation above. The migration
  changes front matter only.
- The path page by course and by method; the lesson header; a Quarto
  sidebar that lists the current course's lessons and works without
  JavaScript at every width, or no sidebar if the no-JavaScript check cannot
  be met.
- An explanation on the path page of what previous and next mean (the one
  linear order) against what the course order and the prerequisites mean.
- `docs/authoring.md` and the lesson template updated; the content proposal
  form's strand dropdown gains a course field; `docs/content-proposals.md`
  criteria name the course.

**Out of scope.** The graph (F26), the cards (F27), search (F41), a second
course (F15), changing any strand identifier or address, changing any
lesson body.

**Dependencies.** F10; F12, whose lesson-proposal form and
`docs/content-proposals.md` criteria this feature changes.

**Acceptance criteria.**

1. All eleven lessons carry the four new fields, and a test shows the build
   fails on a lesson that lacks `course`, has no method, has an outcome
   count outside two to five, names a related lesson that does not exist,
   or names one of its own prerequisites as related.
2. The path page shows every lesson under its course and under each of its
   methods, generated from front matter, shown by a built-site test that
   compares the page with the metadata.
3. Every lesson URL that existed before the feature resolves to the same
   lesson, shown by a test over the list of previous addresses.
4. From the home page, with JavaScript disabled, a reader reaches every
   lesson through the course list and through each method path.
5. The header of every lesson shows course, methods, outcomes, prerequisites
   with links, related lessons, previous and next, consistent with the front
   matter, shown by the existing header test extended.
6. The path page and a lesson page are usable at phone, tablet, and desktop
   widths, and pass the accessibility scan.
7. Lesson source bodies (everything below the front matter) are
   byte-identical to before, shown by the diff of the pull request.

**Risk.** Medium. The migration touches every lesson's front matter and the
header every page renders; the tests of F03 catch drift. The sidebar is the
one piece of Quarto chrome that may need JavaScript; the fallback is to
omit it.

**Detailed implementation plan expected.** Yes, short: schema, vocabularies,
migration table, page layout.

### F26 — Generated prerequisite graph

**Source.** Candidate F26; Section 14, slice 3.

**Problem.** Prerequisites are visible only lesson by lesson; a reader
cannot see the shape of the path, which lessons are required before which,
and where the extensions branch off.

**Goal.** A clickable prerequisite graph on the learning path page,
generated from front matter, accessible, with a text fallback.

**User-visible outcome.** The path page shows a directed graph of lessons
grouped by course, with arrows from prerequisite to dependant and a distinct
style for related (recommended, not required) links; each node links to its
lesson; without JavaScript the same SVG is present with a text list of
edges; on a phone the page offers the linear list first.

**In scope.**

- A layout computed at build time in Python (a layered layout of the
  prerequisite DAG, deterministic), rendered as inline SVG with a `<title>`
  and a `<desc>` that `aria-labelledby` names, and a visually hidden
  ordered list of the edges in text ("M4 requires M2") as the accessible
  alternative. The SVG does not carry `role="img"`: that role has
  presentational children, which would remove the node links from the
  accessibility tree and fail the `nested-interactive` rule of the scan;
  `role="group"` is used only where a grouping is needed.
- Arrow direction and the required-versus-recommended distinction explained
  in a legend next to the graph; colours not the only distinction.
- Keyboard focus on every node link; focus order follows path order.
- A width-aware layout: at phone width the graph scrolls inside its own box
  (as wide equations do) and the linear list stays primary.
- A test that the graph's edges equal the prerequisite and related
  relations of the front matter, and that the SVG is byte-stable.

**Out of scope.** A graph library loaded in the browser; animation;
progress overlays (F13, F14); a graph per lesson page.

**Dependencies.** F37. F44 is not a dependency: F26 ships with a minimal
style for the graph container, and F44 replaces it with the component style
when it lands.

**Acceptance criteria.**

1. The edges of the rendered graph equal the prerequisite and related
   relations of the metadata, shown by a test.
2. Every node is a link to its lesson, reachable by keyboard, with visible
   focus; the SVG is labelled by its title and description through
   `aria-labelledby`, carries no `role="img"`, and has the text list of
   edges; the accessibility scan passes.
3. With JavaScript disabled, the graph and the text alternative are present
   and nothing is lost.
4. The page has no two-way scrolling at 320 CSS px; the graph scrolls inside
   its box.
5. Two builds produce a byte-identical SVG.

**Risk.** Medium. Layout quality for a growing graph; the layered layout
must stay readable when courses and labs are added, which the feature tests
with a synthetic thirty-lesson path.

**Detailed implementation plan expected.** Yes, short.

### F27 — Learning path cards and the difficulty scale

**Source.** Candidate F27; Section 14, slice 4.

**Problem.** The path page lists each lesson as a paragraph of prose:
description, level, prerequisites. Outcomes are not stated, the level
labels are explained only at the top, and a reader cannot scan the course.

**Goal.** Compact, scannable lesson cards on the path page from the F37
metadata, and a difficulty legend that explains each level where it is
used.

**User-visible outcome.** Each lesson on the path page is a card: title,
one-sentence description, two to five outcomes, course and methods, level
with its definition on hover and in text, prerequisites as links, and the
related lessons. Cards reflow to one column on a phone.

**In scope.**

- The card component (F44 styles) rendered by the path page generator from
  front matter; the difficulty legend rendered from `DIFFICULTIES` with a
  level badge on each card that links to the legend.
- Plain headings and lists inside cards so that screen readers get the same
  structure as the linear list did.
- No text is typed by hand into a card; a test compares the cards with the
  metadata.

**Out of scope.** Progress state on cards (F13), recommendations (F14),
images on cards, cards elsewhere than the path page.

**Dependencies.** F37, F44.

**Acceptance criteria.**

1. The cards show title, description, outcomes, course, methods, level,
   prerequisites, and related lessons from the front matter, shown by a
   test over every lesson.
2. The level of every card links to the legend, and the legend text equals
   `DIFFICULTIES`.
3. The path page passes the accessibility scan, reads correctly without
   JavaScript, and reflows to one column at 320 CSS px without two-way
   scrolling.
4. The page's initial payload stays within the F44 budget.

**Risk.** Low.

**Detailed implementation plan expected.** No.

### F35 — Code explanation: annotated excerpts

**Source.** Candidate F35; Section 11.4 (F35 row).

**Problem.** Lessons show code by reference, which keeps it honest, but
several lessons show four or more excerpts under one introductory sentence
(M6 lines 224 to 260, M7 lines 240 to 280, M8 lines 240 to 277 of their
sources), and no excerpt can point at the line where the physics happens:
the update order, the unit conversion, the state variable.

**Goal.** Let a lesson show the lines of an excerpt that matter, annotate
them, and hide helpers, while the check that an excerpt equals its source
still holds.

**User-visible outcome.** An excerpt can highlight named lines with a short
margin note ("the new velocity moves the particle"), show only a named
region of a function, and state inputs, outputs, and units in a small table
above it; the full source stays one click away at the built commit.

**In scope.**

- `excerpt(..., lines=..., notes={...}, region=...)` in
  `pbc.authoring.excerpt`, rendered as a code block with marked lines and
  notes that are plain text in the page (readable without styles and by
  assistive technology), plus an optional interface table from the
  function's signature and docstring.
- The excerpt check extended: a region or a line range is still compared
  with the source file; a note cannot contain a number that the build did
  not compute.
- The authoring rule: explain why each shown step implements the physics,
  the update order, the state variables, the units, and the error modes;
  hide helpers that are not the point; link API documentation only through
  the reference register and only when it teaches more than the lesson
  explains.
- Applied to one lesson as the example (M2's stepper), leaving the others
  to the editorial passes.

**Out of scope.** Rewriting lesson prose (F29, F30, F31). Any client-side
code viewer.

**Dependencies.** F10.

**Acceptance criteria.**

1. An annotated excerpt on the built page is textually identical to its
   source region at the built commit, shown by the extended test.
2. Notes and interface tables render without JavaScript and pass the
   accessibility scan; marked lines are distinguished by more than colour.
3. A test shows the check fails when a region does not exist or when an
   excerpt's notes drift from the source after the source changes.
4. M2 uses the new form for its stepper and its page reproduces
   byte-identically through "Reproduce this".

**Risk.** Low.

**Detailed implementation plan expected.** No.

### F36 — Numeric results as semantic tables

**Source.** Candidate F36; Section 11.4 (F36 row); requirements "UX
expectations" (numeric outputs as tables with units and interpretation).

**Problem.** Every numeric result on the site is a fixed-width `print()`
block: more than forty printed tables across the eleven lessons (for
example M1 source lines 207, 275, and 322, M5 lines 333 and 409, M6 line
413, M8 line 348). Units sit in header strings, screen readers get a
preformatted block, and narrow screens scroll sideways.

**Goal.** A helper that turns arrays into a semantic table with a caption,
column units, and chosen precision, and an interpretation sentence pattern,
so that results are readable, accessible, and still computed by the build.

**User-visible outcome.** Results appear as real tables with header cells,
units in the headers, right-aligned numbers at a stated precision, a
caption that says what the table shows, and a sentence after it that says
what the reader should conclude.

**In scope.**

- `pbc.authoring.table(rows, columns=[(name, unit, format)], caption=...)`
  rendering Markdown or HTML tables from a cell, with `scope` on header
  cells, numbers formatted at a stated precision, and a wide table that
  scrolls inside its own box like a wide equation.
- The authoring rule that a result table has units, a caption, and an
  interpretation; the check function that flags a cell whose output is a
  multi-line fixed-width block of numbers, delivered with a unit test and
  enabled for no lesson yet, because the `format` field arrives with F28;
  F28 enables it for format-2 lessons and owns the lesson-level test.
- Applied to one lesson as the example (M1's four tables), leaving the
  others to the editorial passes.

**Out of scope.** Interactive sorting; rewriting other lessons.

**Dependencies.** F10.

**Acceptance criteria.**

1. Tables on M1 have header cells with units, a caption, and a stated
   precision, and the numbers equal the previous printed ones at that
   precision, shown in the pull request.
2. The tables pass the accessibility scan and cause no two-way scrolling at
   320 CSS px.
3. A unit test shows the check function flags a violating cell (a console
   block of numbers) and accepts a `table()` cell; enabling it for format-2
   lessons and the lesson-level test belong to F28.
4. M1 reproduces byte-identically through "Reproduce this".

**Risk.** Low.

**Detailed implementation plan expected.** No.

### F28 — Lesson format 2, the reference register, and the M1 pilot

**Source.** Candidate F28; Section 11 (11.1 layered design, 11.2 selection
protocol, 11.4 F28 row, 11.5 pilot); Section 14, slice 5; ADR 009.

**Problem.** The audit of the published lessons on 2026-10-09 (see "Lesson
editorial decision" below) found: no typed claims, no figure status, no
limits section except in the Lean lesson, no self-check distinct from the
exercises, no curated external reference anywhere, captions that describe
but do not interpret, and hand-typed approximate numbers in prose. M1 is a
good lesson, which is why it is the pilot: the format must add depth
without adding bulk.

**Goal.** Define lesson format 2 (the progressive-depth, self-contained
lesson with typed claims, figure status, limits, a self-check, and optional
"Go deeper" references from a register), enforce it with checks for lessons
that declare it, document it, and prove it on M1.

**User-visible outcome.** M1 opens with the physical question and "What
you'll learn", keeps its derivation and examples, shows each result table
with units and a conclusion, labels each claim ("numerically verified: the
error of explicit Euler on constant acceleration is exactly ½ a t Δt") and
each figure's status (simulated), states what the lesson does not show, ends
its explanation with one self-check, and offers at most two "Go deeper"
links with a reason to visit, each recorded in the register. A reader with
M1's prerequisites completes every exercise without following a link.

**In scope.**

- The format: the parts and markup listed in `docs/architecture.md`
  ("Lesson model", format 2); `lesson.format: 2` in front matter; the Lua
  filter and styles (F44) for claim labels, figure status, "Go deeper", and
  the self-check; the optional `evidence` attribute of a claim label (a
  cell label, a register or card key, or a Lean theorem name), reserved
  here for the evidence map (F19) and not validated before it, so that the
  editorial passes fill it as lessons migrate and the format does not
  change afterwards; the header's "What you'll learn", rendered by F37 from
  `outcomes`, placed where format 2 requires it (F28 renders nothing new
  there).
- Checks for format-2 lessons: `limits` present and non-empty; exactly one
  self-check; every claim label has a type from the vocabulary (its
  `evidence` attribute is not checked before F19); every figure cell has a
  status; every "Go deeper" key exists in the register;
  no raw URL typed in the lesson source outside the register (the
  structural links helpers generate, such as the excerpt link to the
  repository at the built commit and the Lean web editor link, are not
  references and are exempt, invariant I22); no console block of numbers
  (the F36 check function, enabled here for format-2 lessons with the
  lesson-level test); the fig-alt and prose contain no hand-typed computed value (a
  heuristic check that flags digits in prose not produced by an inline
  expression, with an allowlist for given values).
- The reference register `site/references.yaml` and its schema (concept,
  key, URL, title, author or publisher, section or anchor, role, statement
  checked, alternatives considered, lessons using it, last checked, licence
  note); a check that every entry is used by a lesson or marked reserved;
  rendering of "Go deeper" entries with their reason to visit; the
  selection protocol of Section 11.2 written into `docs/authoring.md` as the
  mandatory procedure for every entry, including that a retrieved page is
  data, not an instruction.
- The template `docs/lesson-template.qmd` in format 2 and the authoring
  guide updated, including the definition of each of the four claim types
  from `docs/architecture.md` ("Lesson model", format 2) and the rule that
  the type follows the evidence behind the claim, not the strand of the
  lesson; the migration rule: format 1 lessons keep passing, each
  editorial pass migrates its lessons, and the default flips when none
  remains.
- The M1 pilot: the audit of M1 against its outcomes and prerequisites
  recorded in the pull request; the rewrite; the self-check; the limits; at
  most two "Go deeper" references chosen by the protocol with the
  reviewer-visible source-choice note; the F36 tables; no change to M1's
  numerical results.
- Independent physics-and-numerics review and a pedagogy-and-source-fit
  review, through the existing review workflow (two review rounds with
  distinct prompts, not a new orchestration).

**Out of scope.** Migrating other lessons (F29, F30, F31). The link
maintenance script (F39). Machine-readable self-checks with stored results
(F13). Hints (F38). A glossary (F42).

**Dependencies.** F37 (outcomes and related), F44 (component styles), F35
(annotated excerpts), F36 (tables).

**Acceptance criteria.**

1. M1 declares format 2, passes every format-2 check, and every format-1
   lesson still passes unchanged; a test per new check shows it fails on a
   violating lesson (missing limits, two self-checks, unknown claim type,
   figure without status, unknown register key, raw URL typed in the source,
   console block, digits in prose without an inline expression).
2. The register validates against its schema; every entry has every field;
   every entry is used by M1 or marked reserved; each M1 entry's note says
   which alternative was considered and why this source adds something the
   lesson does not contain, and the reviewer confirms by opening it.
3. M1's numerical results are byte-identical to the previous build at the
   displayed precision (the tables and inline values), shown in the pull
   request; "Reproduce this" regenerates the page.
4. A reader can complete M1's three exercises and the self-check without
   following any external link, confirmed by the pedagogy reviewer, who
   also confirms that every major concept has its physical question, core
   explanation, worked example, interpretation, and limits.
5. Both independent reviews are recorded on the Issue with no Critical or
   Major finding open.
6. The page passes the accessibility scan, reads without JavaScript (labels
   and "Go deeper" are plain text), and fits phone width; its initial
   payload is within the F44 budget.
7. The authoring guide lets an author migrate a lesson to format 2 without
   reading M1's source; the independent reviewer confirms this by migrating
   a small scratch lesson, or an uncommitted copy of one format-1 lesson,
   using only the guide and the template, and records it on the pull
   request. Any gap the F30 M5 reviewer later finds in the guide is an F30
   finding, not a reopening of F28.

**Risk.** Medium. The format is expensive to change once lessons migrate;
the heuristic check for hand-typed numbers can produce false positives and
needs an allowlist. Content risk: more structure can make a lesson longer
without making it clearer; criterion 4 and the two reviews guard it.

**Detailed implementation plan expected.** Yes.

### F30 — Editorial pass M5 to M8, with M5 as the research-backed pilot

**Source.** Candidate F30; Section 3H; Section 11.3 (the M5 example sources);
Section 11.5 (first pilot: M5).

**Decision on the pilots (Section 3H, 11.5).** The template pilot is M1
(F28), because the template must exist before any pass. The research-backed
editorial pilot is M5, the first lesson of this feature, reviewed on its own
before M6 to M8 start; M1 is then the first lesson of F29, so both
difficulty levels are piloted before bulk editing. No new numbered feature
is invented for the pilot.

**Problem.** M5 (847 lines) is the lesson with the most method distinctions
to get right and the one lesson with a "Further reading" paragraph, which
names two books without URLs, sections, or reasons. Its symplectic Euler
updates the velocity first (as the lesson and `integrators.py` state), its
Verlet is velocity Verlet with a predicted velocity in the second
acceleration call, and its Runge-Kutta 4 is the classical fixed-step method;
any external source must match these exactly, and SciPy's adaptive RK45 is
not the same stepper. M6 to M8 state several results without derivation
(M6's series for the period, M8's orbital elements) and type numbers by
hand (M8 has no inline expression at all).

**Goal.** Migrate M5, then M6, M7, and M8 to format 2 under the editorial
standard: explain what is unmotivated, distinguish the methods accurately,
interpret every figure, replace hand-typed numbers with computed ones, and
add only the external references that demonstrably add insight.

**User-visible outcome.** Four lessons in format 2. M5's reader finds, for
each of the four methods, the physical question, the update rule with the
exact ordering, the derivation of order and energy behaviour, the
interpretation of each figure, a "Go deeper" link only where a source adds
a derivation or intuition the lesson does not contain, and a self-check on
the limits of each method.

**In scope.**

- Per lesson, in this order: M5 alone first; then M6, M7, M8 as one or
  three Issues at the human's choice. Each: an audit of gaps with examples
  before rewriting, recorded on the Issue (unmotivated equations, missing
  assumptions, unsupported assertions, terse explanations, hand-typed
  numbers, descriptive captions); the rewrite in format 2, with the
  `evidence` attribute filled on each claim label (F28); references
  researched by the protocol of F28 with at least two sources compared per
  concept where practical, and the source-choice note; no change to the
  numerical implementation to accommodate a source.
- For M5: the candidate sources of Section 11.3 are inputs to the research,
  not pre-approved links; each is re-opened and compared with alternatives;
  the velocity-first symplectic Euler ordering, the velocity Verlet variant,
  and classical RK4 versus adaptive RK45 are verified against each chosen
  source; the two books stay only if a public section or a library record
  gives the reader a reason and a way to find them.
- Independent physics-and-numerics review and pedagogy-and-source-fit
  review per lesson, through the existing review workflow; M5's reviews
  gate M6 to M8. A gap in the F28 authoring guide that M5's migration
  exposes is recorded as an F30 finding and fixed in the guide here.
- Figures keep their generating code; captions become interpretive; the
  F36 tables replace console blocks; F35 excerpts annotate the update
  order.

**Out of scope.** New figures or diagrams (F33). Changing numerical results
unless a scientific correction is justified and approved on the Issue. M1
to M4 (F29). Hints (F38).

**Dependencies.** F28.

**Acceptance criteria.**

1. M5, then M6, M7, and M8 declare format 2 and pass every format-2 check;
   the audit of each lesson is recorded on its Issue before the rewrite.
2. Every number in prose, captions, and alt text of the four lessons comes
   from an executed expression, with the given values of exercises as the
   only allowed exception, shown by the F28 check.
3. Every external reference of the four lessons is in the register with its
   full selection evidence, and the physics reviewer confirms that each
   target matches the lesson's exact method variant (for M5: the
   velocity-first symplectic Euler, velocity Verlet, classical RK4; no
   source presented as RK4 that describes RK45).
4. The numerical results of the four lessons are unchanged at displayed
   precision, or an approved scientific correction is recorded on the Issue
   with its reason.
5. A reader can complete each lesson's principal exercise without
   following a link; the self-check of each lesson tests the method's
   limits, not a fact; both reviewers confirm per lesson.
6. M5's reviews are complete with no Critical or Major finding open before
   M6's Issue is created.
7. Each page passes the accessibility scan, the no-JavaScript check, the
   width checks, and the payload budget, and executes within 30 seconds.

**Risk.** Medium. Content and source correctness need independent review;
M5 is the lesson most exposed to a wrong external source.

**Detailed implementation plan expected.** Yes, short, for M5: the audit
template and the research log format; M6 to M8 follow it.

### F29 — Editorial pass M1 to M4

**Source.** Candidate F29; Section 11.5 (second pilot: M1).

**Problem.** M2 and M3 state the exponential solution, the Reynolds-number
regime, the drag-free range, and the interpolation bound without a
justification sentence or a source (M2 lines 62 to 64, 143 to 155; M3
lines 74 to 76, 134 to 140, 170); M4 asserts "the same algebra shows" for
its per-step rotation without showing it; M2 to M4 type approximate numbers
by hand in prose; captions describe rather than interpret; no lesson
offers a deeper path.

**Goal.** Migrate M1 (already in format 2 from F28, now with the editorial
pass proper), M2, M3, and M4 under the standard, lesson by lesson, with M1
first as the beginner-level pilot.

**User-visible outcome.** Four introductory and intermediate lessons in
format 2 with every equation motivated or derived to the declared
prerequisite level, interpretive captions, computed numbers, a self-check,
and at most a few researched "Go deeper" links.

**In scope.** As F30, for M1 (the editorial pass on the F28 pilot: gaps,
references, review), M2, M3, M4; one or four Issues at the human's choice;
the same reviews.

**Out of scope.** As F30. Diagrams (F32).

**Dependencies.** F28; F30's M5 pilot reviewed, so that the lessons learned
from the intermediate pilot apply.

**Acceptance criteria.** Criteria 1 to 5 and 7 of F30 applied to M1 to M4,
with criterion 3 checking the drag regimes and the exponential solution
sources against the lesson's exact statements.

**Risk.** Medium.

**Detailed implementation plan expected.** No; F30's audit template and
research log apply.

### F39 — Unified local setup, run recipes, and the link maintenance check

**Source.** Candidate F39; Section 11.4 (F39 / CI reproducibility row);
Section 14, slice 6; ADR 009.

**Problem.** `docs/development.md` and the Reproduce page cover the build
toolchain, and every lesson lists its commands, but there is no single
learner-facing guide that separates reproducing a lesson from extending it,
no setup for the optional agent runtimes (the live client, a coding agent
of the learner's choice) and for Lean work beyond the build, no
troubleshooting, and no way to check the external links the register will
hold.

**Goal.** One setup guide with tested commands per supported system, split
into the required build toolchain and the optional learner workflows, a
"reproduce versus extend" recipe per lesson type, troubleshooting, and the
on-demand link maintenance check.

**User-visible outcome.** A learner finds one page that says what to
install for reading and reproducing (nothing beyond the supported-machine
contract), what to add for running an agent live, for a coding-agent
exercise, and for editing Lean locally, and what to do when a step fails.
The maintainer can run `./scripts/check-links.sh` and get a report of every
register link that no longer resolves to its section.

**In scope.**

- `site/setup.qmd` (or a rewritten Reproduce page) with: the required
  setup, verified on macOS and Linux from a fresh install; optional setups
  (live LLM client with the key in the environment, a coding agent under
  the sandbox profile of ADR 010, Lean editing with the pinned toolchain);
  per lesson type the "reproduce" commands (what "Reproduce this" lists)
  and the "extend" commands (edit, test, preview); a troubleshooting table
  of the failures the preflight and doctor scripts report and the first
  cold-start attempt of F10 met (unreachable Lean release host, Mathlib
  clone prompt, missing browser libraries).
- A test that every command on the page that the build can run is run in
  CI (the commands of the required setup are those of `ci.yml` and are
  checked for equality), and that the optional commands are in
  `.not-verified` blocks.
- `scripts/check-links.sh`: reads the register, opens every URL with a
  timeout, checks that the page is reachable and, when an anchor is given,
  that it exists, and prints a report with the last-checked date to update;
  it is not in `verify.conf` and has no CI job (ADR 009); a test in
  `tests/integration`, run by the existing `check-tests` entry of
  `verify.conf`, runs it against a local fixture server (ADR 005 decision
  4: a test of a project script belongs with the product checks, not with
  the workflow self-tests). As a new file under `scripts/`, it is named in
  `docs/project-map.md` (the `docs-scripts` check requires it) and is
  guarded by `scripts/verify-workflow.conf` until it is excluded there
  after confirming that no workflow self-test reads it (ADR 005 decision
  4); the first local run before that exclusion runs the workflow
  self-tests.
- The maintenance rule in `docs/authoring.md`: run the link check before an
  editorial pass and at least once a quarter; a rotten link is re-researched,
  never replaced by a title match.

**Out of scope.** Installing anything in CI that verification does not
need. A scheduled workflow (would add a trigger; needs its own review).
Windows support.

**Dependencies.** F10.

**Acceptance criteria.**

1. A reviewer who did not write the page completes the required setup and
   reproduces one lesson of each strand on a clean macOS and a clean Linux
   machine following only the page, recorded on the pull request; the
   Linux run that F10 could not complete is completed or its blocker
   recorded.
2. The required commands on the page equal the commands of `ci.yml` and of
   the Reproduce page, shown by a test. (The equality with `ci.yml` is the
   contract of ADR 003 at delivery; superseded by ADR 016 decision 5 and
   F117 since 2026-10-15, which test the page by performing its commands.)
3. Every optional command is marked "not verified" and names the account or
   credential it needs and where the key goes (environment variable).
4. `./scripts/check-links.sh` reports a dead link and a missing anchor on
   a local fixture, shown by a test, and is absent from `verify.conf`.
5. The page passes the accessibility scan, reads without JavaScript, and
   fits phone width.

**Risk.** Low.

**Detailed implementation plan expected.** No.

### F50 — Experimental dataset registry and feasibility gate

**Source.** Candidate F50; Section 8 (survey, 8.1 shortlist, 8.2 spike, 8.4
gates, 8.5 deferment); Appendix A; Section 14, slice 7; ADR 007.

**Decision on the spike (Section 8.2).** The feasibility spike is the first
deliverable of this feature, not a separate numbered feature. It may start
beside wave R1, because it changes no page and touches no lesson; its go,
defer, or reject decisions gate F51 and every lab.

**Problem.** The requirements make real measurements first-class content
and require a feasibility gate before any lesson commitment; the repository
has no dataset, card, sample, reader, or rights record. The survey of 25
sources is a shortlist of editorial estimates, not validated labs.

**Goal.** Establish the dataset registry, the card schema, the rights and
artifact-type vocabulary, the sample location and caps, the learner-side
download script, and the checks; then run the feasibility spike on three
deliberately different candidates and record a go, defer, or reject
decision for each, with the evidence.

**User-visible outcome.** Nothing on the site yet. In the repository: one
card per surveyed dataset (25 from Appendix A, including negative
findings), a dossier per spiked dataset with a reference figure generated
from actual data by source-controlled code, a decision table, and the
checks that every later lab inherits.

**In scope.**

- `data/registry/<dataset>.yaml` schema: source DOI or URL, creator,
  licence or permission status with the four rights questions (local
  download, redistribution of subsets, publication of figures and
  derivatives, modification and attribution), version and access date,
  measurement type per artifact (`raw-measured`, `processed-measured`,
  `calibrated-observation`, `modelled-reference`, `synthetic-test`),
  calibration details, schema, units, cadence, coordinate conventions,
  masks and missing values, documented uncertainty, size, format and the
  reader it needs, checksum where available, estimated local runtime and
  memory, estimated page payload, decision (`go`, `defer`, `reject`,
  `survey-only`) with reasons and date.
- `data/samples/<dataset>/` as the declared committed location with the
  caps of the architecture (2 MB per file, 8 MB per dataset, 32 MB in all),
  a card for every sample, a checksum check, a rights check that permits
  committed samples only under CC0, CC BY, or an equivalent recorded
  permission, and a parsing test per sample asserting field names, shapes,
  units, masks, and cadence. Committed in this feature only for the
  datasets with a go decision and only what the dossier's figure needs.
- `scripts/fetch-data.sh <dataset>`: learner-side download of the full
  dataset by the card's URL, version, and checksum, with the host's rate
  limits respected; never called by the build or CI; a test that the build
  passes with data portals and external web hosts blocked (criterion 2). As
  a new file under `scripts/`, it is named in `docs/project-map.md` (the
  `docs-scripts` check requires it) and
  is guarded by `scripts/verify-workflow.conf` until it is excluded there
  after confirming that no workflow self-test reads it (ADR 005 decision 4);
  its test belongs with the product checks.
- The feasibility spike on three candidates of different kinds, recommended
  first pass: GW150914 strain (time series; GWOSC, CC BY 4.0 as read on the
  record page on 2026-10-09, about 1 MB per detector for 32 s at 4096 Hz),
  the Aalborg submerged-bar wave flume (measured-versus-modelled; Zenodo
  15049542, CC BY 4.0, 78.6 MB archive, md5 recorded), and the NPL on-wafer
  S-parameters (complex RF measurement; Zenodo 22658069, CC BY 4.0, 3.1 MB
  zip of Touchstone files). Each: retrieve a real minimal sample; inspect
  the actual files; label every artifact; produce the reference
  visualization from source-controlled code, with a physical consistency
  check where applicable (for the strain, the published chirp and the
  acknowledgement text GWOSC requires; for the flume, the measured and the
  CFD series separated; for the S-parameters, passivity and the calibration
  context); establish the rights of derived figures; estimate runtime,
  memory, CI needs, and web payload; and write the dossier
  `docs/datasets/<dataset>.md` with the decision.
- The minimal locked readers the three spike samples need, added as
  ordinary locked dependencies with their licences recorded: an HDF5
  reader for the strain, unless the plain-text strain product GWOSC also
  publishes avoids the dependency, and a Touchstone reader; the flume
  archive is extracted and read with what the locked environment already
  provides where that suffices. F51 generalises these readers into
  `pbc.data`.
- Cards for the remaining 22 Appendix A sources as `survey-only`, with what
  is known and the gate each would have to pass, including the optical
  diffraction record (Zenodo 19436924, whose record page shows a CC BY 4.0
  licence field next to a copyright line, both recorded on the card as
  read, because the change request flags redistribution as unclear; RAR
  archives of 46 MB and more) and the cylinder-wake PIV (Zenodo 20765567,
  CC BY 4.0, one 1.1 GB MAT file of processed fields at 20 Hz with masked
  zeros).
- The decision table and the recommendation for the first lab, recorded in
  `docs/datasets/README.md` and summarised in this roadmap by the human when
  F51 is created.
- `docs/authoring.md` section "Measured data": the gate, the card, the
  sample rule, the figure status, the typed claims, the no-LLM path.

**Out of scope.** Readers and analysis beyond what the three reference
figures need; F51 generalises the minimal readers of this feature into
`pbc.data`. Any lesson page. Committing anything restricted or
above the caps. Contacting a portal from the build.

**Dependencies.** F10. ADR 007.

**Acceptance criteria.**

1. The card schema validates every card; a test shows the dataset check
   fails on a sample without a card, a sample above a cap, a checksum
   mismatch, a sample whose card's rights do not permit redistribution, and
   a sample without a parsing test.
2. The build and every check pass with no access to data portals, external
   web pages, or model APIs (invariant I20), shown by a test that runs
   `./scripts/verify.sh` with those hosts blocked, or with all egress
   blocked after the toolchain, package, and Mathlib caches are warm, or by
   an equivalent guard in the data readers. Fetching the pinned toolchains,
   packages, and the Mathlib cache is an install-time dependency (ADR 003
   decision 4; architecture, "Toolchains and pinning") and is not what the
   test blocks.
3. Three dossiers exist, each with: the actual file inspected (named with
   version and checksum), the artifact labels, the reference figure
   generated by a script in the repository from the committed or downloaded
   data, the rights answers with the source of each answer, the size and
   runtime estimates, and a go, defer, or reject decision with reasons.
4. The 22 remaining cards exist with `survey-only` and name the gate each
   would have to pass; no score from the survey spreadsheet is copied as a
   fact.
5. Every committed sample is under the caps, rights-cleared on its card,
   and parsed by a test; the total of `data/samples/` is reported in the
   pull request.
6. A reviewer who did not write the spike regenerates each reference figure
   from the committed sample or the documented download and confirms the
   figure's status label and caption.
7. The recommendation for the first lab is recorded with its reasons and
   its fallback.

**Risk.** Medium. Rights and format surprises (RAR, MAT, HDF5 readers;
acknowledgement texts), host rate limits, and the temptation to let a
beautiful figure decide: criterion 3 ties every decision to evidence.

**Detailed implementation plan expected.** Yes: the card schema, the three
spike plans, the figure scripts.

### Wave R2 — Finish the editorial standard, trustworthy scientific coding

### F42 — Before you begin, and the glossary

**Source.** Candidate F42; Section 11.4 (F37 and F42 row).

**Goal.** A site-wide glossary of the assumed vocabulary (mathematics,
Python, numerical methods, physics, Lean) with concise on-site definitions
and internal cross-links, and a "Before you begin" block on every lesson
generated from its outside prerequisites, linking each to its glossary entry.

**In scope.** `site/glossary.qmd` with entries in a small YAML or Markdown
structure that lessons reference by key; the header cell rendering "Before
you begin" from `prerequisites.outside` with glossary links; a check that
every outside prerequisite maps to an entry; external introductions only
through the reference register and only where they add real depth; the
authoring rule to prefer an internal link where the explanation exists.

**Out of scope.** Re-teaching prerequisites; a search index (F41).

**Dependencies.** F37, F28.

**Acceptance criteria.** Every outside prerequisite of every lesson resolves
to a glossary entry (test); the glossary page and the block read without
JavaScript, pass the accessibility scan, and fit phone width; each entry is
one to three sentences with a cross-link to the lesson that uses it.

**Risk.** Low. **Detailed implementation plan expected.** No.

### F38 — Progressive hints in exercises

**Source.** Candidate F38; Section 11.4 (F38, F13, F14 row); Section 12
(F38 + F13/F14).

**Goal.** Exercises can carry one to three hints, each a closed `details`
element before the solution, so that a reader can take one step at a time
without seeing the answer; no stored state, no quiz engine.

**In scope.** A `.hint` div inside `.exercise`, rendered by the lesson
filter as nested `details` that open without JavaScript; the lesson check
that hints come before the solution and contain no computed number that
the solution's cells did not produce; the authoring rule that "Go deeper"
references and hints are distinct and that a hint never leaks the answer;
applied to the exercises of M1 and M5 as examples.

**Out of scope.** Recording whether a hint was opened (F13); any
recommendation (F14).

**Dependencies.** F28.

**Acceptance criteria.** Hints render as nested details without JavaScript
and pass the accessibility scan; a test shows the check fails on a hint
after the solution; F13's later self-check format can wrap the same
markup, confirmed by a note on the Issue.

**Risk.** Low. **Detailed implementation plan expected.** No.

### F40 — Reproducibility UX

**Source.** Candidate F40; Section 12 (F28 + F35 + F36 + F40 + F42).

**Goal.** Keep the exact source revision and the verification evidence on
every page while making the hashes and commands unobtrusive: a short
"Reproduce this" summary with the commit and one command, and the full
listing (files, tests, Lean record, commands) in a closed `details`.

**In scope.** `reproduce_this()` renders the summary and the details; the
built-site check that the commands still regenerate the page is unchanged
(the contract of ADR 002 at delivery; since ADR 016 and F117, 2026-10-15,
the footer lists the experiment entry point's commands and no render
command, and the experiment check of ADR 016 decision 4 verifies them;
the page reproduction stays an internal check); the Lean evidence box gets
the same treatment; a "copy" affordance only if it needs no JavaScript to
read.

**Dependencies.** F28.

**Acceptance criteria.** Every lesson's reproduction test still passes; the
commit, the files, and the commands are present in the page text without
JavaScript; the section is shorter on first view and complete when opened.

**Risk.** Low. **Detailed implementation plan expected.** No.

### F41 — Self-hosted search

**Source.** Candidate F41.

**Goal.** Site search over lessons, glossary, and pages from an index built
at build time and served from the site's own origin, with the learning path
and the glossary as the navigational fallback without JavaScript.

**In scope.** Quarto's built-in search enabled with its local index and its
bundled script only (no Algolia, no other origin), or a project-owned index
if Quarto's cannot meet the origin and payload checks; a built-site check
that search makes no request to another origin and sets nothing in storage;
the search control hidden without JavaScript and the path page linked in
its place.

**Dependencies.** F37.

**Acceptance criteria.** With JavaScript, a query finds a lesson by a term
in its body; the other-origin, cookie, and storage checks pass; without
JavaScript the page shows the fallback and no broken control; the index
counts within the page payload budget; the accessibility scan passes.

**Risk.** Medium: Quarto's search integration and the no-JavaScript chrome
need care; the fallback is to not ship it.

**Detailed implementation plan expected.** No.

### F31 — Agent and Lean editorial pass

**Source.** Candidate F31; Section 11.4 (F29 to F31 row).

**Goal.** Migrate A1, the agent-based-modelling lesson, and L1 to format 2
under the standard: explain tool bounds, replay trust, theorem hypotheses,
what an LLM claim is and how it is tested, and empirical versus numerical
versus formal evidence; curate authoritative API and formal-method
references through the register after reading them; keep every proof and
explanation self-contained.

**In scope.** As F30, per lesson, with the agent lesson's physical question
(the angle of the longest throw) moved before the technique; A1's raw
dictionary outputs (source lines 443 to 447) as tables; L1's residual claim
(line 270) derived in place; typed claims on every result (the agent's
conclusion from its simulated runs as `numerically-verified` only where
the build recomputes it, never `experimentally-supported`, because no
measurement is involved; the theorems as `formal-theorem` with scope).

**Dependencies.** F28, F30.

**Acceptance criteria.** Criteria 1 to 5 and 7 of F30 for the three lessons;
in addition, L1's "What the proofs do not cover" stays and every theorem's
claim label states its scope; A1's live-run commands stay "not verified".

**Risk.** Medium. **Detailed implementation plan expected.** No.

### F32 — Mechanics diagrams M1 to M4

**Source.** Candidate F32; Section 11.4 (F32 to F34 row).

**Goal.** Conceptual diagrams drawn by code, labelled `conceptual`, where a
picture carries a physical insight the prose cannot: the state and the
update as a transition, force arrows on the falling particle, drag against
velocity, the trajectory with and without drag, the oscillator's phase
plane and energy ellipse.

**In scope.** `pbc.authoring.diagrams` helpers (arrows, labelled states,
simple geometry) over Matplotlib, deterministic, with the F44 palette; each
diagram in an executed cell with alt text and a caption that states the
insight; no image files; third-party diagrams cited and linked, never
rehosted.

**Dependencies.** F29.

**Acceptance criteria.** Each diagram is produced by the build, labelled
`conceptual`, has alt text that conveys the insight, and is byte-stable;
the pedagogy reviewer confirms each diagram answers a question the prose
raised; the pages stay within the payload and time budgets.

**Risk.** Low. **Detailed implementation plan expected.** No.

### F33 — Mechanics diagrams M5 to M8

**Source.** Candidate F33.

**Goal.** As F32 for the integrator comparison (the update orderings side
by side), energy bands versus drift, the collision geometry and the centre
of mass, and the Kepler orbit's phase drift and conserved vectors.

**Dependencies.** F30. **Acceptance criteria.** As F32. **Risk.** Low.
**Detailed implementation plan expected.** No.

### F34 — Agent and Lean diagrams

**Source.** Candidate F34.

**Goal.** As F32 for the agent tool flow (model, harness, allowlist,
simulation), replay verification (recorded messages, recomputed results),
and the theorem pipeline (statement, hypotheses, Lean, CI record, page),
each with its precise scope stated.

**Dependencies.** F31. **Acceptance criteria.** As F32. **Risk.** Low.
**Detailed implementation plan expected.** No.

### F45 — Agent-assisted simulation development

**Reconciled by the change cycle `final-curriculum` (2026-10-12).** F45
fills slot AI1 of the physics reasoning path and is unchanged; it has no
Issue. Its default exercise, a damped driven oscillator with resonance, is
also the subject of lesson M12 (F68): whichever lands first owns the
verified reference solution in `src/pbc`, and the other reuses it (see
F68).

**Source.** Candidate F45 (merged with the shared workflow of F55); Section
12 (F45 + F55); requirements use case 9; ADR 010, accepted with this
planning.

**Decision (Section 12).** One agent-assisted scientific coding workflow,
defined here and reused by F55 for experimental problems and by F22 for
proofs. Lessons stay separate from the shared workflow.

**Goal.** Teach a learner to drive a coding agent of their choice, on their
own machine with their own account, from an approved physical
specification to a tested Python simulation, and to verify the agent's
code, assumptions, and units; and define the reusable workflow and sandbox
profile every later coding-agent exercise follows.

**In scope.** The workflow document: specification format (physics,
assumptions, interface, units, tests the result must pass), the sandbox
profile (a scratch checkout, an allowlist of commands such as running the
tests and the formatter, no network beyond the agent's provider, a budget
in steps, time, and cost, review of every diff before running it), and the
review rubric (assumptions, units, update order, tests, failure modes). The
first lesson, in the `agents-llm` strand with method `coding-agents`: one
mechanics problem the course has not solved (default: a damped driven
oscillator with resonance), the specification, the verified reference
solution and tests in `src/pbc`, the rubric, and an example transcript
marked "not verified" with the agent and date. A test that no workflow
file, script, or check invokes a coding agent. The authoring guide section
"Coding-agent exercises".

**Out of scope.** Running any agent in CI or the build; replaying
agent-written code; a specific vendor as a requirement; experimental data
(F55); Lean (F22).

**Dependencies.** F10.

**Acceptance criteria.** The reference solution passes its tests and the
page executes within budget; the page states the sandbox profile and the
rubric in full; the transcript is labelled "not verified" with model and
date; a test shows CI and the build contain no coding-agent invocation and
no credential; a learner following the page with any coding agent reaches
a state where the provided tests decide, confirmed by the maintainer's own
run recorded on the Issue; the security-focused review approves the
sandbox profile.

**Risk.** High: the exercise invites a learner to run agent-written code;
the profile, the budget, and the review rule are the safeguards, and the
site never runs any of it.

**Detailed implementation plan expected.** Yes.

### F46 — Scientific code verification and debugging

**Source.** Candidate F46 (shares a validation contract with F18); Section
12 (F46 + F18).

**Goal.** A lesson on how scientific code is shown to be right: independent
physics tests (limits, conservation, convergence), deliberately faulty
reference implementations the reader must catch, negative tests that must
fail, and an objective evaluation of a piece of code against a contract;
and the written validation contract (what a verifier checks, in what order,
with what evidence) that F18's review agents and F45's rubric reuse.

**In scope.** `pbc.verification` helpers (order estimation, invariant
checks, convergence tables) with tests; a gallery of faulty steppers in
`src/pbc` marked as such; the lesson in the `mechanics` strand with method
`simulation`, at the next order there (ADR 008 decision 3), with the
previous-and-next prose of M8 checked after the insertion; the contract
document.

**Dependencies.** F10.

**Acceptance criteria.** Each faulty implementation is caught by a named
test on the page, and a correct one passes the same tests; the contract is
referenced by name in the lesson and reusable by F18; the usual lesson and
page checks.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F16 — Counterexample hunter

**Source.** Candidate F16.

**Goal.** A bounded agent in the ADR 004 harness that tests a falsifiable
physics claim through allowlisted simulations and reports either a
verified counterexample or an inconclusive outcome; every experiment is
logged and replayed in CI.

**In scope.** An allowlist over the integrators and models of the course
with bounded parameters; the claim format (a statement, a predicate the
harness evaluates on simulation output, a budget); a lesson in the
`agents-llm` strand with two claims, one false (a counterexample exists
within the budget) and one the agent cannot settle; the replay fixture;
the verdict typed `numerically-verified` only for the recomputed
counterexample, never for the agent's prose.

**Out of scope.** Code-writing agents; multi-agent debate (F18).

**Dependencies.** F09, F46 (the contract names what counts as a
counterexample), F28 (the typed claim the verdict carries).

**Acceptance criteria.** The counterexample is recomputed by the build and
the page shows the recomputed values; the inconclusive case is labelled so;
the ADR 004 boundary tests cover the new allowlist; replay passes without
credentials.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F17 — Further Lean mechanics proofs

**Source.** Candidate F17 (also the source material for F56 and F22).

**Goal.** Two or more focused Lean lessons tied to mechanics lessons:
momentum conservation of the pairwise collision rule of M7, and a property
of an integrator on the oscillator (the modified energy conserved by
symplectic Euler, or the per-step rotation), with pinned checks,
hypotheses as assumptions, and the limits stated.

**In scope.** Modules under `lean/PhysicsByConstruction/Mechanics/`; lessons
in the `lean` strand with `course: mechanics`, each listing the mechanics
lesson it proves something about (M5 or M7) among its `prerequisites`, as
L1 lists M1 and M4; M5 and M7 gain the new lesson under `related`, because
related links are one-directional from the prerequisite side and a lesson
may not list a prerequisite as related (F37); each theorem's claim typed
`formal-theorem` with its scope; the Lean build time kept within budget.

**Dependencies.** F08, F28 (the typed claims and their scope).

**Acceptance criteria.** As F08's criteria 1 to 8 for each lesson; the
connection to the numerical observation it proves and what it does not
cover are stated; the `lean-build` time is recorded.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F59 — Instructor pack for one published lesson

**Source.** Section 9 of the change request (unnumbered proposal);
requirements use case 11; Section 10.2 (For Educators row).

**Decision (Section 9).** One small feature rather than a deliverable of an
existing one: no pedagogy feature produces educator material, and the pack
is independently testable. It reuses the F37 outcomes, the F57 citation
text, and the F12 Issue path for feedback; it adds no authoring platform.

**Goal.** One reusable teaching pack for a lesson that has passed its
editorial pass (default: M5), with a lecturer guide, learning objectives,
prerequisites, approximate time, a student assignment, a rubric, a
reference solution verified by the build, accessibility notes, a no-AI
pathway, accurate citation and reuse terms, and a neutral way to suggest
improvements.

**In scope.** `docs/instructor-packs/<lesson>.md` generated in part from
the lesson's metadata (outcomes, prerequisites, difficulty) so it cannot
drift; the assignment's reference solution as executed cells in a
non-published page or in tests; a "For educators" page on the site that
lists packs, states the licence and the citation, and links to the Issue
forms; no form, no contact requirement, no claims of adoption.

**Dependencies.** F57, F30 (M5 in format 2).

**Acceptance criteria.** The pack's objectives and prerequisites equal the
lesson's metadata (test); the reference solution is verified by the build;
the citation text equals `CITATION.cff`; an educator who did not write the
lesson follows the pack and reports what was missing, recorded on the
Issue; the page passes the usual checks.

**Risk.** Low. **Detailed implementation plan expected.** No.

### Wave R3 — From measurements to models

### F51 — Experimental methods and visualization foundations

**Source.** Candidate F51 (merged with the analysis core of F47); Section
8.3; Section 8.4; Section 12 (F47 + F51).

**Decision (Section 12).** One reusable data-analysis and uncertainty core
lives here; F47 is a lesson that uses it for sweeps and reports.

**Goal.** The shared `pbc.data` package every measured-data lab uses:
readers for the formats the go decisions need (HDF5, Touchstone, CSV; MAT
or FITS only if a lab with a go decision needs them), generalised from the
minimal readers F50 locked for its spike samples, calibration and mask
handling, noise and uncertainty propagation, residuals, curve fitting with
identifiability diagnostics, and science-first plotting helpers
(measured-versus-model panels with residuals, signed colour scales, time
series with uncertainty bands, status labels), with cross-lab test fixtures
from the committed samples.

**In scope.** The package with unit tests on the committed samples; the
figure conventions of the requirements enforced by helpers (status label,
axis units, legend, residual panel, no false colour presented as natural,
no smoothing presented as raw); a page-side pattern for the measured-data
lab (format 2 plus the data card rendered on the page, the artifact labels,
the download instructions, the no-LLM path); a built-site check that a
figure from a measured sample carries `measured`, `calibrated`, or
`processed`, never `simulated`.

**Out of scope.** Any lab page (F60, F54, F53, F52); browser components
(F43); agents (F55).

**Dependencies.** F50 with at least one go decision; F28 (the format-2
page pattern, claim labels, and figure status the lab pattern and the
built-site check use), which carries to every lab built on this package.

**Acceptance criteria.** Each reader parses its committed sample and
asserts fields, shapes, units, masks, and cadence; the fitting helper
recovers known parameters of a synthetic test within stated tolerance and
reports uncertainty; a reference figure for each go dataset is regenerated
by the helpers and matches the dossier's; the no-network test of F50 still
passes; the new dependencies are locked and their licences recorded.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F60 — Gravitational-wave strain lab: from Kepler's orbit to a chirp

**Source.** Section 8.1 (LIGO GW150914 row: "later a stand-alone
gravitation/signals lab if scope allows"); Section 13, R3 ("a
planner-approved waves/signals lab"); the planner's recommendation under
"Experimental data choice". No candidate number; new ID.

**Goal.** The first measured-data lab of the mechanics course, conditional
on F50's go decision for GW150914: from the calibrated strain of the two
detectors to the chirp, and from the two-body orbit of M8 to the
Newtonian-order estimate of the chirp mass from the frequency and its rate
of change, compared with the published value, with every processing step
(bandpass, whitening, time-frequency resolution) disclosed and every claim
typed.

**In scope.** A lesson at the next order in the `mechanics` strand (ADR 008
decision 3; F46 may have taken an order before it), with `course:
mechanics`, methods `measured-data` and `simulation`, M8 among its
`prerequisites`, M8's front matter gaining the lab under `related` (links
are one-directional from the prerequisite side, F37), and the
previous-and-next prose of M8 and of the lesson before it checked after the
insertion; the committed 32 s sample
of each detector at 4096 Hz with its card and the GWOSC acknowledgement;
measured-versus-model panels (whitened strain against the Newtonian chirp
model and residuals); the spectrogram with an explained colour scale and a
static keyframe; a typed claim set: `observational` (the signal is present
in both detectors), `experimentally-supported` (the chirp-mass estimate,
an inference from the measured strain through the stated Newtonian model
with its uncertainty), and an explicit statement of what the Newtonian
model does not capture; the no-LLM path; the plain-language conclusion.

**Out of scope.** General relativity beyond the stated order-of-magnitude
model; matched filtering against a template bank; any claim of detection
significance beyond the published one, which is cited `observational`.

**Dependencies.** F51, F06. F50's go decision for the dataset.

**Acceptance criteria.** All the gates of Section 8.4 of the change
request: the sample parses with asserted fields; the reference figure is
regenerated from the committed sample with pinned settings; rights and the
acknowledgement are recorded and shown; every figure is labelled; the
measured strain stays distinct from the filtered signal and the model;
download and reproduction are versioned and tested; a no-LLM path exists;
the page is within the time and payload budgets, readable without
JavaScript, and accessible; the physical assumptions, the error metric,
and the interpretation are stated; an independent physics review confirms
the model statement and the claim types.

**Risk.** Medium: signal processing can mislead (a whitened signal is not
a measurement); the status labels and the review guard it.

**Detailed implementation plan expected.** Yes.

### F43 — Science-first visualization components

**Source.** Candidate F43; Section 8.3 (reusable visualization system).

**Goal.** At most four reusable browser components, built on the F07 widget
convention, that present verified data derived from executed cells: a field
viewer (scalar map with vector overlay and time slider over sparse verified
frames), an image-versus-model comparator (synchronized panes and
difference map on shared scales), a signal explorer (trace, filtered
signal, time-frequency view, model overlay), and a waveform comparator
(measured against simulated profiles with error metrics). A 3D viewer only
if a lab with settled rights and size needs it.

**In scope.** One component per lab that needs it, no component without a
lab; the on-demand data budget of the architecture (3 MB per page, own
origin, after a user action) with the built-site check; static keyframes
and captions in the page; keyboard and mobile operation; export of the
displayed values as text; the rule that a component never alters a claimed
observed value (a test that displayed values equal the embedded data).

**Out of scope.** A separate engine per lab; animation that cannot stop
under reduced motion; computing physics in the browser.

**Dependencies.** F07, F51; delivered component by component with F60,
F53, F52, F54 as each needs one.

**Acceptance criteria.** As F07's criteria for each component, plus the
on-demand budget check, the observed-value test, and a keyframe for every
animation.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, per
component.

### Wave R4 — Evidence and advanced labs

### F54 — Microwave S-parameter lab

**Reconciled by the change cycle `final-curriculum` (2026-10-12).** The
lab's course is `electromagnetism`, created by F72 (ADR 013); the references to
F15 below are history, F15 is dropped, and the `mechanics` framing is no
longer a route. The feature is otherwise unchanged and has no Issue; it
starts when F72 and its other dependencies are delivered.

**Source.** Candidate F54; Section 8.1 (NPL row, "strong low-friction
candidate").

**Goal.** From calibrated vector-network-analyser Touchstone `.s2p` files
to complex transmission and reflection, the Smith chart, and a fitted
transmission-line or lumped model, with the calibration assumptions,
passivity and energy context, and uncertainty quantified; power and
amplitude definitions distinguished; an optional focused Lean theorem on
the model (F56).

**Dependencies.** F51; F50's go decision; a course that exists. Every
lesson belongs to exactly one primary course and no lesson is placed by a
method tag (ADR 008 decisions 3 and 4, invariant I18), so this lab is
published only in an electromagnetism or waves-and-optics course. F15
yields one course of the human's choosing: if the human chooses one of
these subjects for F15, that course is the lab's home; otherwise the lab
waits for a later course feature, which takes the next unused ID when the
human asks for it. The only other route is the `mechanics` course if the
lab's Issue justifies that framing under ADR 008 decision 3, which the
planner does not expect because RF transmission is not the physics of the
mechanics course. The F50 dossier is evidence for the F15 choice.

**Acceptance criteria.** The gates of Section 8.4 as in F60.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F53 — Flow measurement lab with PIV fields

**Reconciled by the change cycle `final-curriculum` (2026-10-12).** The
lab's course is `fluids`, created by F73 (ADR 013); the references to
F15 below are history, F15 is dropped, and the `mechanics` framing is no
longer a route. The feature is otherwise unchanged and has no Issue; it
starts when F73 and its other dependencies are delivered.

**Source.** Candidate F53; Section 8.1 (cylinder-wake and Rostock rows).

**Goal.** From processed PIV velocity fields to vorticity, streamlines, and
the vortex-shedding frequency and Strouhal number, with the field viewer of
F43; raw frames distinguished from PIV-derived fields; masked regions and
cadence handled explicitly; a compact local subset designed from the 1.1 GB
file, or the small Sheffield or OpenPIV example, either usable only after
its `survey-only` card and a feasibility spike with a go decision under F50
(its provenance check).

**Dependencies.** F51, F43; F50's go decision; a course that exists: a
fluid-dynamics course if the human chooses that subject for F15 (F15
yields one course), otherwise a later course feature that takes the next
unused ID when the human asks for it, or the `mechanics` course if the
lab's Issue justifies that framing under ADR 008 decision 3 (vortex
shedding as the fluid mechanics of the course), the one lab for which that
framing is plausible. No placement by method tag (ADR 008 decision 4).

**Acceptance criteria.** The gates of Section 8.4; the committed subset
under the caps; the animation with a keyframe within the on-demand budget.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F52 — Optical diffraction lab

**Reconciled by the change cycle `final-curriculum` (2026-10-12).** The
lab's course is `waves`, created by F71 (ADR 013); the references to
F15 below are history, F15 is dropped, and the `mechanics` framing is no
longer a route. The feature is otherwise unchanged and has no Issue; it
starts when F71 and its other dependencies are delivered.

**Source.** Candidate F52; Section 8.1 (Fraunhofer row).

**Goal.** From a measured far-field diffraction photograph to the Fourier
optics model, side-by-side measured and simulated intensity with residuals,
uncertainty, and inference of the grating geometry, with the comparator of
F43. The record page (Zenodo 19436924) shows a CC BY 4.0 licence field next
to a copyright line and the change request flags redistribution as unclear;
the gate decides, and still verifies the terms of the photographs, the RAR
extraction in a locked environment, and the sample size.

**Dependencies.** F51, F43; F50's go decision; a course that exists: the
waves-and-optics course if the human chooses it for F15 (F15 yields one
course), otherwise a later course feature that takes the next unused ID
when the human asks for it. No placement by method tag (ADR 008 decision
4); a `mechanics` framing under ADR 008 decision 3 is not plausible for
diffraction, so this lab has no home until a waves-and-optics course
exists.

**Acceptance criteria.** The gates of Section 8.4.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F55 — Agent-assisted experimental physics

**Source.** Candidate F55 (lesson only; the workflow is F45's); Section 12
(F45 + F55).

**Goal.** One lesson that applies the F45 workflow to a measured dataset
with a go decision: inspect, specify, implement the analysis in Python with
a coding agent, visualize, validate independently against the F51
reference, and report; no second workflow and no shell access beyond the
F45 profile.

**Dependencies.** F45; one of F60 or F54.

**Acceptance criteria.** As F45's criteria on the chosen dataset; the
agent's result is compared with the verified reference analysis and the
difference reported.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F23 — Inverse physics: parameter discovery with uncertainty

**Source.** Candidate F23; Section 12 (F20 + F23).

**Goal.** Fit model parameters to measured or synthetic observations,
quantify residuals, uncertainty, and identifiability, and show when a fit
is not evidence; an optional bounded agent in the harness proposes fits.

**Dependencies.** F51; one of F60 or F54 for the measured case.

**Acceptance criteria.** The fitting helpers recover synthetic parameters
within tolerance and report a non-identifiable case as such; the measured
case states its uncertainty; claims typed; the usual lesson checks.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F47 — Automated analysis pipelines

**Source.** Candidate F47 (lesson; its core merged into F51).

**Goal.** A lesson that builds a reusable analysis and report workflow on
`pbc.data`: parameter sweeps, statistics, uncertainty, figures, and a
reproducible report generated by the build, shown on one simulated and one
measured problem.

**Dependencies.** F51.

**Acceptance criteria.** The report is regenerated by the build and
compared with a committed expectation at displayed precision; the usual
checks.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F18 — Multi-agent scientific review

**Source.** Candidate F18 (shares the contract of F46); Section 12.

**Goal.** Independent review agents in the ADR 004 harness, one for
physical assumptions, one for the numerical implementation, one for the
evidence, each with bounded local tools over `src/pbc` and the F46
contract; visible disagreement and resolution; reproducible transcripts
replayed in CI; a lesson that reviews a piece of lesson code and a faulty
variant.

**Dependencies.** F09, F46.

**Acceptance criteria.** Each reviewer's tool results are recomputed by the
build; the faulty variant is flagged by at least one reviewer through a
recomputed check, not through prose; the ADR 004 boundary holds; no new
orchestration framework beyond the harness loop run three times.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F19 — Scientific evidence map

**Source.** Candidate F19.

**Goal.** A static, accessible page that lists every typed claim of the
site with its scope and links it to its evidence: the executed cell, the
sample and card, the replayed agent run, or the Lean theorem; generated
from the claim markup of format 2 through the `evidence` attribute that
F28 reserves and the editorial passes fill, so this feature adds only the
page and the check, not a format change.

**Dependencies.** F28, F29, F30, F31 (every lesson in format 2), F37.

**Acceptance criteria.** Every claim on the site appears once with its type,
scope, lesson, and evidence link (test); the page reads without JavaScript
and passes the accessibility scan; a claim without an `evidence` attribute,
or whose attribute names no existing cell, register or card key, or Lean
theorem, fails the build.

**Risk.** Low. **Detailed implementation plan expected.** No.

### F56 — Lean proofs for the models of measured-data labs

**Source.** Candidate F56; Section 12 (F17 + F56 + F22).

**Goal.** Prove selected exact properties of the mathematical models or
numerical schemes a lab uses (for example passivity or energy relations of
the transmission-line model of F54, or a property of the fitting scheme),
never of the data or the Python; delivered as lessons in the `lean` strand
with `course` set to the lab's course and the lab among their
`prerequisites`; the lab's front matter gains the proof lesson under
`related` (links are one-directional from the prerequisite side, F37).

**Dependencies.** F17, F54 (or the first lab whose model has a provable
property).

**Acceptance criteria.** As F08 and F17; the page states that the theorem
proves nothing about the measurement.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### Wave R5 — Research capstones

### F20 — Autonomous experimental design

**Source.** Candidate F20; Section 12 (F20 + F23).

**Goal.** An agent in the harness chooses measurements and parameters under
a budget to discriminate between competing models, estimates uncertainty,
and has its conclusions independently assessed; built on the F16 loop and
the F23 fitting helpers.

**Dependencies.** F16, F23.

**Acceptance criteria.** The chosen design is recomputed and scored by the
build; the agent's conclusion is typed only as the recomputed evidence
supports; replay passes.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F21 — Interactive Lean exercises

**Source.** Candidate F21.

**Goal.** Learners complete pinned Lean exercises locally; the site shows
the statements, hints, and checked solutions without in-browser Lean.

**Note for planning.** Exercise stubs contain `sorry`, which invariant I12
forbids in `lean/`. The feature plan must propose, as a new ADR, a declared
exercise location outside the checked library (for example a second Lake
package `lean-exercises/`) whose solutions live in the checked library, with
a check that every stub has a solution that builds without `sorry`; the
site shows stubs "not verified" and solutions by reference.

**Dependencies.** F17.

**Acceptance criteria.** Every stub has a checked solution; the hints
render as details without JavaScript; the exercise package builds within
the Lean budget; the ADR is accepted.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F22 — Agent-assisted theorem proving

**Source.** Candidate F22; Section 12 (F17 + F56 + F22); ADR 010.

**Goal.** A local, constrained workflow under the F45 profile: conjecture,
counterexample search with F16's loop, Lean formalization by a coding
agent, proof checking with `lake build`, and human semantic review, starting
from the known reference proofs of F17 and F21.

**Dependencies.** F21, F45.

**Acceptance criteria.** Any proof shown on the site is compiled by CI like
every proof; the agent's transcript is "not verified"; the page states
what a compiled proof does and does not establish; the security review
approves the profile for Lean.

**Risk.** High (agent-written code on the learner's machine).
**Detailed implementation plan expected.** Yes.

### F49 — Research capstone: reproduce an open physics paper with a multi-agent team

**Source.** Candidates F48 and F49, merged (Section 12: "a single capstone
may be preferable").

**Goal.** One capstone project: reproduce a focused open-access paper (DOI,
parameter provenance, fit and figure comparison, a residual discrepancy
report) with a planner, a coder, an analyst, and independent reviewers
built from F45, F46, F47, and F18; human review required; no new
orchestration framework.

**Dependencies.** F18, F45, F46, F47.

**Acceptance criteria.** The reproduced figures are regenerated by the
build from documented inputs under the dataset rules; discrepancies are
reported as such, typed, and not explained away; the reviewers' recomputed
checks are shown; the paper's licence and the data rights are recorded.

**Risk.** High (scope). **Detailed implementation plan expected.** Yes,
likely several Issues.

## Phase 4 — Final curriculum (change cycle `final-curriculum`)

Every feature in this phase comes from `docs/changes/final-curriculum.md`
(revision 3, 2026-10-10) and the requirements re-approved with it on
2026-10-12 (decisions 23 to 31); each block names the slots of the
reference curriculum it fills and the section of the change request it
comes from. The wave C0 and the discovery foundation F65 are specified in
detail, because they are the first wave and everything else depends on
them. Waves C1 to C4 are deliberately coarser: revalidate each feature
against the architecture, the requirements, the curriculum file, and the
delivered features before creating its Issue, and expect a feature plan to
refine it. The human approves each course's concrete lesson list in the
Issues before drafting (requirements, unresolved question 6).

What every feature of this phase inherits, without repeating it in each
block:

- **The gates** (requirements decisions 29 and 30). Every feature that
  publishes a lesson in this phase depends on F61 (verification
  proportional to the change) and F62 (the courses, the curriculum file,
  and the `slot` field its lessons must carry), whether or not its block
  names them: no lesson of this phase is drafted, and no Issue for one is
  created, before both are delivered. Every lesson feature of waves C2,
  C3, and C4, which is the bulk of the new lessons, additionally depends
  on F64 (the Learning Path redesign). The dependency tables and the
  blocks repeat these gates so that `create-feature-issue.sh` sees them;
  this rule is the source when a block is terser. There is no exception
  for cost: departing from a gate is a change to the requirements, not a
  scheduling choice.
- **The full-run gate** (ADR 014 decisions 7 and 11). Every job of a full
  run must fit the job timeout, and until F113 is delivered a full run is
  the one `build` job of ADR 012, which fits the budget up to the
  lesson-shard size of 32 lessons. A lesson feature of wave C1 depends on F113 unless
  the lesson count it brings the site to is at most 32 (twenty-two today,
  so room for about ten lessons, in the order the human creates the
  Issues); every lesson feature of waves C2 to C4 depends on F113 as it
  depends on F64. The dependency table marks the wave C1 features "F113
  by the lesson-shard rule" and names F113 outright from wave C2 on; F61
  records the measured count at which the one job leaves the budget, and
  if that count is below 32 no lesson feature starts before F113.
  **Since the change cycle `pbc-planning-change-four-workstreams`
  (2026-10-15):** the site publishes thirty-two lessons, so the room is
  used up, and F113 is paused (requirements decision 35). Wherever a
  dependency table says "F113" or "F113 by the lesson-shard rule", read:
  the owner's decision on the full-run gate under unresolved question 10
  of the requirements, recorded by F118 from the measured full runs at
  the current lesson count (an approved timeout for the one `build` job
  of a full run, with the lesson count it is approved for), or F121 once
  ADR 017 is accepted and delivered, or F113 resumed by the owner. No
  lesson feature that takes the count past 32 starts before one of
  these exists; see "State at the change cycle
  `pbc-planning-change-four-workstreams`". **Since the owner's interim
  full-run gate of 2026-10-15 (ADR 014 status; recorded in this roadmap by
  the change cycle `scientific-atelier-atlas`):** the one `build` job of a
  full run has a 60-minute timeout approved for up to 45 lessons, so the
  entries "F113" and "F113 by the lesson-shard rule" are satisfied for
  every lesson feature that keeps the count at or below 45; past 45 the
  gate needs a further decision of the owner, or ADR 017 accepted and
  F121 delivered, or F113 resumed. The capacity is reassessed before the
  count approaches 45, with the cost of F117's experiment check measured
  (see "State at the change cycle `scientific-atelier-atlas`").
- **The invariants and the lesson model** of `docs/architecture.md`,
  including the reference curriculum and the slot (ADR 013), the
  verification selection (ADR 014), and the format-2 lesson checks of
  `docs/authoring.md`.
- **The definition of done of a lesson** (change request, section 11;
  requirements decision 31): substantive physics at its stated level with
  the physical question, assumptions, essential derivation, units, and
  domain of validity; runnable pinned code and figures the build
  regenerates; interpreted figures with provenance labels; honest numerical,
  epistemic, and empirical limitations; typed claims with evidence; unique
  identifier, course, slot, methods, difficulty, validated prerequisites,
  outcomes, and related links; exercises, a self-check, accessible labels,
  and a tested "Reproduce this" path (since ADR 016 and F117, a tested
  "Run this experiment" path with a runnable entry point); references from
  the register; focused
  tests for the code it adds; applicable checks passing within the budgets;
  and an independent scientific review before merge. No live LLM or API
  call is a required check.
- **A feature may deliver exactly one slot.** There is no rule that a slot
  is a feature, and none that it is not (requirements, later phases and
  decision 31; change request, section 2, point 10). Until 2026-10-13 the
  sentence of the later phases read "no feature equals one slot", against
  decision 31; the project owner corrected it on that day to the wording of
  decision 31. The features of this roadmap that deliver one slot stand.
- **The placement rule**: a lesson of a course's physics lives in the
  course's strand at the next free order, with `course` and `slot` set; a
  lesson whose subject is a method lives in `agents-llm` (the method paths),
  `agents-abm`, or `lean`, with the primary course of the physics it uses.
  The first lesson feature of a course creates its strand directory and its
  package under `src/pbc` (ADR 013). Related links are one-directional from
  the prerequisite side (F37).
- **The lab rule** (requirements decisions 18 and 27; ADR 007): a
  measured-data lab feature starts with the feasibility spike of its
  candidate dataset under the F50 process (card, inspected file, artifact
  labels, reference figure from source-controlled code, rights, sizes,
  dossier) and waits for the human's go decision; on defer or reject the
  feature records the decision on its card and dossier and stops, or
  proposes another candidate in a new spike. A lab then meets the gates of
  section 8.4 of `docs/changes/physics-next-phase.md` as F60 did: sample
  under the caps with a parsing test, regenerated reference figure, rights
  and attribution shown, every figure labelled, measurements distinct from
  processed signals and models, versioned and tested download, a no-LLM
  path, the page within the time and payload budgets, the physical
  assumptions, error metric, and interpretation stated, and an independent
  physics review of the claim types. No dataset is accepted because the
  curriculum names it; only GW150914 strain, the Aalborg wave flume, and
  the NPL S-parameters have a go decision today.
- **The capstone rule** (change request, section 4.1; requirements
  decision 26, non-goals, and "Content integrity"; architecture, "Applied
  capstone and numerical-engineering lesson"): a verified progression from
  the precursor lessons; a bounded workflow from physical requirements to a
  qualified decision; comparison with an analytical, manufactured,
  independent, or trusted numerical reference; refinement and genuine
  failure modes; the credibility boundary stated and typed; the required
  path on the pinned stack within the page budget; heavy tools optional,
  with their outputs as declared `modelled-reference` inputs.
- **The agent rule** (requirements decision 25; ADR 004; architecture,
  "Law-discovery environment and agent benchmark"): bounded allowlisted
  tools, a budget, versioned model and prompt, a frozen replay the build
  recomputes, the hidden truth never reachable, non-agent baselines,
  hold-outs, seeds where needed, visible failures, and heavy runs outside
  `verify.conf`.
- **No hardware** (requirements decision 28): no lesson builds a sensor
  experiment, records audio, collects classroom or smartphone data, or
  controls an instrument; the acoustics lesson is numerical, and the
  video-reasoning lesson uses generated or rights-cleared existing clips.

Risk levels follow `.agents/policies/autonomy.md` and, since
`risk-proportionate-workflow`, ADR 020 decision 1: every lesson feature is
Level 2 (Medium), with independent scientific review, and Level 3 (High)
when it changes or removes a published claim or hits another escalation
trigger (a new lesson's own claims are not the trigger); a feature that
changes CI, workflow permissions, or the required check is High.

### Wave C0 — Governance, verification, and the learning path

Order within the wave, by dependency: F61 and F62 are independent of each
other and may run in parallel worktrees; F113 after F61; F63 after F62;
F64 after F63. F61 and F62 precede the first lesson feature of this phase
(requirements decision 30; the gates under "Phase 4"): until F61 lands,
every new lesson would add about 45 seconds of runner time to every pull
request, and until F62 lands a lesson cannot carry a validated `slot`.
F113 precedes every lesson feature that would take the lesson count past
32 (the full-run gate), and F64 precedes the lesson features of waves C2
to C4 (requirements decision 29). Since 2026-10-15 F113 is paused and the
full-run gate reads as the amended gate under "Phase 4" says (F118's
record and the owner's decision, F121, or F113 resumed).

### F61 — Verification proportional to the change

**Source.** Change request section 15; requirements decision 30 and
"Runtime and deployment constraints"; ADR 012 decisions 8 and 9; ADR 014,
proposed with this planning and accepted when it is approved.

**Problem.** Every pull request executes every lesson three times and
checks every page. With twenty-two lessons a run takes 18 to 25 minutes
against a budget of 12; at 110 lessons the site build alone would take
about 19 minutes. The verification cost must depend on what a pull
request changes, not on the size of the curriculum, without dropping a
check, without a check that exists only in CI, and with the published site
still the site that was verified in full.

**Goal.** Implement ADR 014: a pull request executes and checks the
lessons whose input digest changed against the verified result of the
latest successful run on `main`, and every page whose bytes differ from
it; what a page shows of its context (navigation, slot, the commit it
names) is produced by every build and never taken from the base; a check
is reused only from a base the same check implementation produced;
`main` verifies everything and publishes the base; the selection lives in
`./scripts/verify.sh`.

**User-visible outcome.** A contributor who changes one lesson sees the
`verify` check finish within 12 minutes (the budget when this block was
written; 20 minutes with a 15-minute target since ADR 015, requirements
decision 34, change cycle `pbc-planning-change-four-workstreams`); a
contributor who changes shared
code, the checks themselves, or a lesson whose inputs cannot be followed
sees a full run, as before. Locally, `./scripts/verify.sh` without
options is unchanged; with the base option it runs the same selection CI
runs. Nothing on the published site changes.

**In scope.**

- The input digest of a lesson (ADR 014 decision 1) as one function in the
  authoring package, with a test that each kind of input (lesson source,
  fixture, an imported `src/pbc` module and a module it imports, a sample
  and its card, a displayed Lean module, the toolchain and manifest, the
  Python pins, each shared site file, `src/pbc/authoring`) changes the
  digest, and that a lesson with a dynamic import, a composed path, a
  non-Python cell, or a read outside the known locations has no digest.
  The digests of every lesson are written beside the built site.
- The base option of `./scripts/verify.sh`: it names a directory that
  holds the base (site checksums, executed results, digests); the script
  computes the selection once and writes it where the checks read it; a
  run without the option runs everything; `--only` and the base combine as
  CI needs; the record of a run with a base names the base.
- The site build with a base: the executed results of the base are
  restored, the entries of every changed lesson are removed, Quarto
  executes the changed lessons and renders every page; the time of each
  executed lesson is measured and compared with the 30-second budget. The
  default build writes the store, which `.gitignore` lists and the
  committed-artifact check rejects. The determinism check starts its second
  build from the same restored state. The reproduction check and the
  per-page checks read the selection: the reproduction runs for changed
  lessons; the per-page checks run for the pages whose bytes differ from
  the base, found by comparing the built site with the base's checksums
  after the build commit is normalised in both.
- The context of a page regenerated on every build (ADR 014 decision 9):
  the header (`lesson_header`: previous and next, prerequisites, related
  lessons, course, slot, path position) and the provenance helpers
  (`reproduce_this`, the excerpt and Lean helpers, which embed
  `build_commit()`) stop being replayed from the store. The feature picks
  the mechanism (the helpers move out of the executed cells into a build
  step such as a filter or a post-render over marked regions, or the
  store is written without the outputs of those cells and they run on
  every build) and changes the lesson template and the authoring helpers
  once; lesson bodies stay as they are. The store entries of the pages
  that are not lessons (home, path, evidence map, glossary, about) are
  never restored.
- The identity of the checks (ADR 014 decision 10): one digest over
  `scripts/verify.sh`, `scripts/verify.conf`, `scripts/build-site.sh`,
  `scripts/check-determinism.sh`, `tests/e2e`, `tests/support`,
  `tests/integration`, `tests/e2e/shards.json`, `pyproject.toml`,
  `uv.lock`, and the browser tooling the runner preparation installs,
  written into the base beside the lesson digests. When the current
  tree's identity differs from the base's, nothing of the base is
  restored: the run executes every lesson, checks every page, and
  reproduces every lesson against its own results, and its record says
  why; no reproduction ever compares bytes with a result of the base
  (ADR 012 decision 4). A split per check group is allowed only with a
  test that shows each group's inputs are complete.
- The workflow: a `main` run uploads the base (executed results and
  digests beside the site artifact of ADR 012) after `verify` passed; a
  `pull_request` run retrieves the latest base read-only (a read permission
  on the artifacts of earlier runs, or the cache of the default branch,
  whichever needs the smaller permission and is tested) and accepts it
  only by its provenance (ADR 014 decision 2): the run that produced it
  is a `push` run on `refs/heads/main` whose aggregate `verify` check
  concluded with success, established from that run's recorded event,
  branch, and conclusion, never from the artifact's name, its recency,
  or its contents; a pull request run, including one from a fork,
  uploads the built site for review and must not be able to supply a
  base. The contents of a base are data: the workflow and the script
  execute nothing from it and read nothing in it as configuration. The
  run then verifies that the accepted base is complete and of the
  current format and passes it to the script, or runs without it. If
  the feature chooses the cache of the default branch, its plan records
  why the cache's scoping gives the same guarantee (an entry is written
  only by a `main` run after `verify` passed, a pull request run reads
  the default branch's entries and can never write one that a later
  pull request reads, and a fork pull request writes nothing) and a test
  shows it. A run on `main` never receives a base; a test of the
  workflow file shows it.
- Tests in `tests/integration`: the selection names exactly the lessons
  whose digest differs; a lesson without a digest selects every lesson; a
  changed shared input of ADR 014 decision 4 selects every lesson, one
  test per input; a changed module of `src/pbc` selects every lesson that
  imports it directly or through another module, and every lesson when
  its importers cannot be followed; a missing, truncated, or older-format
  base selects every lesson; an artifact of a pull request run and an
  artifact of a `main` run whose `verify` did not succeed are each
  rejected as a base and the run executes every lesson, one test per
  rejected case, with the provenance read from the producing run's
  event, branch, and conclusion and not from the artifact's name or
  upload time; a failing changed lesson fails the run; a page that
  differs from the base is checked and a byte-identical page is not; the
  workflow passes a base only on pull requests and keeps `contents: read`
  with the one added read scope.
- Tests of the regenerated context, on a run with a base built from a
  fixture site: inserting a lesson between two unchanged ones updates
  their previous and next links and the path page; retitling an unchanged
  lesson updates every unchanged page that links to it (previous, next,
  prerequisites, related); adding a prerequisite or a related link to a
  changed lesson updates the unchanged page it points at where that page
  shows it; the "Reproduce this" section and every code and Lean excerpt
  of an unchanged page name the commit of the run, never the commit of
  the base, and the page the reader gets is the page that was checked.
- Tests of the check identity: a change to each input of the identity (a
  test file of `tests/e2e`, a module of `tests/support`, the verification
  script, its configuration, `tests/e2e/shards.json`, the build or
  determinism script, `uv.lock`) makes the run a full run in which every
  lesson is executed, every page checked, and every lesson reproduced
  against this run's results, with nothing restored from the base; an
  unchanged identity reuses the checks as decision 3 says; a base without
  an identity runs everything.
- The measurement: three consecutive pull requests that change one
  lesson, their wall clock and the render time per page without execution,
  recorded in the pull request and in `docs/release-readiness.md`; the
  projection to 110 lessons from the measured per-page render cost. The
  render is measured on a build that executes no scientific cell and
  runs the context cells of ADR 014 decision 9 if the feature keeps them
  as executed cells, which is the build the assembly of F113 makes, so
  the figure carries over to it. The full run on `main` as well: the
  time of the `build` job with warm and with cold caches and its cost
  per lesson on the slowest runner of those runs, projected to 110
  lessons, and the lesson count at which that one job leaves the
  full-run budget of ADR 014 decision 7 (35 minutes with cold caches),
  which is the count the full-run gate of this phase uses until F113
  lands.
- `docs/architecture.md` ("Inside one verification run", "CI pipeline and
  time budget"), `docs/deployment.md`, and `docs/development.md` updated;
  the acceptance of ADR 014 recorded in its status with the merge.

**Out of scope.** Selecting the Lean build (requirements, unresolved
question 8), the integration tests, or the workflow self-tests; a
schedule; a path filter in the workflow file; changing what any check
checks; self-hosted runners; the job timeout, which stays 45 minutes, and
the lesson shards and assembly of a full run (ADR 014 decisions 7 and 11;
F113).

**Dependencies.** F58 (the parallel jobs, the single built site, and the
checksums the comparison with the base reuses).

**Acceptance criteria.**

1. Three consecutive warm-cache pull requests that each change one lesson
   finish within 20 minutes wall clock, each recorded with its duration
   and whether the 15-minute target was met (amended from 12 minutes by
   the owner's decision of 2026-10-14, ADR 015, requirements decision 34,
   change cycle `pbc-planning-change-four-workstreams`; the three runs
   measured on 2026-10-14, 13 min 50 s to 14 min 43 s, ran at the same
   time rather than consecutively, and stay recorded as measured); the
   times, the number of lessons,
   the per-page render cost without execution, and the projection to 110
   lessons are recorded in `docs/release-readiness.md`.
2. A pull request that changes one lesson executes that lesson in the
   build and in the second build, reproduces it, and checks its page and
   every page whose bytes differ from the base, and nothing else of the
   lesson checks; shown by the run's record and by a test.
   The pages of that run show the navigation of the pull request's tree
   and name its commit: the tests of the regenerated context (lesson
   insertion, retitling, prerequisite and related links, commit
   provenance) pass, and the attached site artifact of the pull request
   is inspected for the previous, next, and "Reproduce this" of one
   unchanged page.
3. A pull request that changes a shared input of ADR 014 decision 4
   (`uv.lock`, `pyproject.toml`, `.python-version`, a file of
   `src/pbc/authoring`, `site/_quarto.yml`, a template, filter, asset, or
   shared site file, the glossary, the reference register, the curriculum
   file, the Lean toolchain or manifest) executes every lesson; one that
   changes a module of `src/pbc` executes every lesson that imports it
   directly or through another module, and every lesson when the
   module's importers cannot be followed; shown by a test per input kind.
4. A run on `main` executes and checks every lesson and publishes the base
   only after `verify` passed; a test of the workflow file shows no base
   reaches a `main` run, that a pull request run accepts a base only from
   a `push` run on `refs/heads/main` whose `verify` succeeded, and no job
   gained write permissions.
5. A run in which any lesson's inputs cannot be followed, a run whose
   base is missing or of another format, and a run offered an artifact
   of a pull request run or of a `main` run whose `verify` did not
   succeed (rejected by its provenance) execute every lesson; a test per
   case. A pull request that changes a test of the built site,
   a support module, the verification script or its configuration,
   `tests/e2e/shards.json`, the build or determinism script, or `uv.lock`
   is a full run: it executes every lesson, checks every page, and
   reproduces every lesson against its own results with the current
   checks, restoring nothing from the base; a test per input of the
   identity shows it and shows that no reproduction compared bytes with a
   result of the base, and the record of such a run says why it ran in
   full.
6. `./scripts/verify.sh` without options runs every check as before; with
   the base option it selects as CI does; a test covers both, and a local
   run of the selection on a laptop matches the selection CI made for the
   same base.
7. No check left `scripts/verify.conf`, every group still runs in exactly
   one job, and the published site of `main` is the fully verified one
   (the tests of F58 still pass).
8. ADR 014 is accepted with the merge; ADR 002, ADR 003, and ADR 012 name
   it in their status.
9. The full run on `main` is measured (the `build` job with warm and with
   cold caches, its cost per lesson taken on the slowest runner of those
   runs) and projected to 110 lessons; the projection and the lesson
   count at which the one job leaves the
   35-minute budget of ADR 014 decision 7 are recorded in
   `docs/release-readiness.md`. That count is at least the lesson-shard
   size of 32 lessons (ADR 014 decision 11), which the measured cost
   confirms or lowers and never raises; if it is lower, F113 reduces the
   lesson-shard size accordingly and no lesson feature starts before F113
   (since 2026-10-15, change cycle `pbc-planning-change-four-workstreams`:
   the measured full run and its projection are recorded by F118 under
   unresolved question 10, not by this feature, and the F113 clause is
   paused with F113 by requirements decision 35; the Phase 4 state table
   records this, and the Issue decides what closes the feature).

**Risk.** High. The feature changes the CI workflow, a workflow
permission, and the merge gate's meaning on pull requests, which need
explicit human approval and security-focused review; the digest is a new
guarantee whose completeness the tests must demonstrate; the render cost
of unchanged pages may dominate at 110 lessons, which criterion 1 measures
and reports rather than hides.

**Detailed implementation plan expected.** Yes.

### F113 — Bounded full verification: same-machine lesson shards of the build

**Still paused by the change cycle `risk-proportionate-workflow`
(requirements decision 39, ADR 020 decision 8, 2026-10-19):** not
justified by lead-time evidence; Issue #150 stays open and the branch
preserved; no work on it is scheduled; it is reopened only at the owner's
triggers (42 lessons measured, the capacity decided at 44 at the latest,
or a complete run on `main` above 45 minutes).

**Paused by the change cycle `pbc-planning-change-four-workstreams`
(requirements decision 35, 2026-10-15).** The pull request #175 of this
feature was closed on 2026-10-15 without a merge, by the owner's decision
not to merge it as designed; Issue #150 stays open and the branch
`feature/150-bounded-full-verification-same` is preserved so that the
work stays inspectable. The feature is not restarted, not duplicated, and
not merged before the owner decides on ADR 017 (proposed by that cycle):
if ADR 017 is accepted, F121 supersedes this feature and Issue #150 is
closed non-destructively with a comment naming the record; if ADR 017 is
rejected, the owner chooses between resuming this feature and the raised
full-run timeout of unresolved question 10. The block below is the record
of the feature as approved on 2026-10-12 and is not rewritten, except
that where it quotes the 12-minute budget of its day (the measurement item
of "In scope" and acceptance criterion 5) it carries the bracketed note
"20 minutes since ADR 015", as the blocks of F01 and F58 do.

**Source.** ADR 014 decisions 7 and 11; ADR 012 decisions 2, 3, 4, 6, and
9; requirements, "Runtime and deployment constraints" (every push to
`main` executes and checks every lesson; the site is served from a
verified build of `main`; the planner sets a concrete budget); change
request section 15 (the cost per lesson).

**Problem.** The `build` job of ADR 012 holds the three executions of
every lesson (the build, the second build for determinism, the
reproduction in a fresh clone), which compare bytes and have to run on one
machine. It took 20 min 27 s with cold caches at twenty-two lessons; at
about 41 seconds per lesson it leaves the full-run budget of 35 minutes
at about 40 lessons and needs about 80 at 110, against a timeout of 45.
F61 makes a pull request pay for what it changed, but a run on `main`
and a full-run pull request still execute every lesson, and a run on
`main` that times out publishes nothing.

**Goal.** Implement ADR 014 decision 11: a full run executes the lessons
in same-machine lesson shards of at most 32 lessons, each making its
comparisons of bytes on its own machine, and one assembly renders the one
built site from their results, so that every job of a full run fits the
timeout at 110 lessons without a tolerance, a dropped check, or a raised
timeout. A lesson shard is a share of the lessons that the script derives
from their count; it is not the division of the built-site tests in
`tests/e2e/shards.json` (F58, ADR 012), which this feature leaves as it
is. "Shard" alone in this block means a lesson shard.

**User-visible outcome.** A push to `main`, and a pull request that is a
full run, finish within the job timeout at any size of the curriculum up
to 110 lessons; a contributor still sees one required check, `verify`;
the published site is still one site verified in full. Locally,
`./scripts/verify.sh` without options is unchanged.

**In scope.**

- The lesson-shard and assembly modes of `./scripts/verify.sh`:
  `--shard k/N` runs the group `build` on the k-th lesson shard, which the
  script assigns from the lesson list in a stable order with at most `S`
  lessons per shard, `S = 32` declared in `scripts/verify.conf` and `N`
  the ceiling of the lesson count over `S`, never read from a file; the
  assembly mode names the parts to assemble. Both are partial runs like
  `--only` and verify nothing by themselves; a run without options
  executes everything in one build on one machine, as today.
- The shard run: the Lean build in full; the execution of the share and
  its second execution for determinism; the render of the share's pages;
  the reproduction of each lesson of the share in a fresh clone against
  the pages and figure files this shard rendered; the publication of the
  part (the share's entries of the store, its rendered pages and figure
  files) with the checksum of every file, as a job artifact.
- The assembly: retrieve the parts; require that every file is the
  recorded one and that the parts cover every lesson exactly once; render
  every page from the union of the parts (and, on a pull request, the
  base for the unchanged lessons) without executing a scientific cell of
  any lesson, with the context of ADR 014 decision 9 from the current
  tree (if F61 kept the header and provenance helpers as executed cells,
  the assembly runs those context cells and nothing else of a lesson);
  the assembly's runner prepares what those context cells read, in
  particular the Lean build record the Lean excerpt helper checks
  (architecture, "Formal proof lesson"), restored from a shard's part
  and required equal across every part, or recreated by the Lean build,
  which is cheap with Mathlib's cache, the plan stating which; the
  assembly's cost is then the render cost F61 measured on a build of
  the same shape; render a second
  time and compare the bytes on the same machine; require that each
  lesson page equals the page its shard rendered and reproduced; upload
  the one site with its checksums (ADR 012 decision 6); on `main`,
  publish the base of F61 from the assembled results.
- The workflow: `build` becomes a matrix of lesson shards and `assemble`
  a job after them; the `e2e` jobs download the assembled site and keep
  their division of `tests/e2e/shards.json`; `deploy` is unchanged. The
  number of lesson shards is derived from the lesson count by the
  script, and the workflow's lesson-shard count equals that derivation (`N` the
  ceiling of the lesson count over `S`, ADR 014 decision 11), never more
  and never fewer: either a job computes the matrix from the script's
  output, or the matrix is static and is bumped exactly when the lesson
  count crosses a multiple of `S`, and the test asserts equality between
  the workflow's shards and the script's, so that an over-covering matrix
  fails as an under-covering one does (an idle shard still prepares a
  runner, and the requirement is a bounded full run, not a padded one);
  the feature chooses the simpler one that needs no permission and tests
  it.
- Tests in `tests/integration`: the lesson shards cover every lesson
  exactly once and none exceeds `S`; the workflow's lesson shards equal
  the script's; a
  failing shard fails `verify`; a missing, extra, or altered part fails
  the assembly; a lesson page that differs from its shard's fails the
  assembly; no shard uploads a Pages artifact; the tests marked
  `same_machine` run on the machine that computed the bytes they compare
  with (ADR 012 decision 4, extended); a local run without options is
  unchanged in meaning; workflow permissions stay `contents: read` with
  write scopes only in `deploy`.
- The measurement: one full run on `main` with warm caches and one with
  cold caches (as F58 measured), the time of every shard and of the
  assembly, the cost per lesson on the slowest runner of those runs,
  recorded in the pull request and in `docs/release-readiness.md`, with
  the projection to 110 lessons (four shards) against the 35-minute
  budget of ADR 014 decision 7, and the shard size `S = 32` confirmed or
  lowered from that cost. And, by the protocol of F61 criterion 1, three
  consecutive warm-cache pull requests that each change one lesson on
  the sharded workflow: their wall clock, the assembly's time, and the
  projection to 110 lessons, recorded in `docs/release-readiness.md`,
  because the assembly is a second step on the longest path of every
  pull request and the 12-minute budget of requirements decision 30 (20
  minutes since ADR 015) must
  be established on the workflow shape that persists.
- `docs/architecture.md` ("CI pipeline and time budget", "Inside one
  verification run"), `docs/deployment.md`, and `docs/development.md`
  updated; the status of ADR 012 and ADR 014 records the delivery.

**Out of scope.** Changing what any check checks; selecting the Lean
build (requirements, unresolved question 8); a tolerance in any
comparison of bytes; raising the job timeout, which is the fallback of ADR
014 decision 11 and needs a revision of that record; self-hosted runners;
changing the pull request budget (F61 sets it; criterion 5 re-measures
it on the sharded workflow).

**Dependencies.** F61 (the store, the selection, the regenerated context,
and the base, which the shards and the assembly reuse), F58.

**Acceptance criteria.**

1. A full run on `main` at the lesson count of its day, with warm caches
   and with cold caches, finishes with every job within 35 minutes; the
   times per shard and for the assembly, the cost per lesson on the
   slowest runner of those runs, and the projection to 110 lessons with
   every job within 35 minutes are
   recorded in `docs/release-readiness.md`; that cost confirms the shard
   size of 32 lessons or the feature lowers it (ADR 014 decision 7).
2. The published site is one site rendered by the assembly; every lesson
   page of it is byte-identical to the page its shard reproduced; the
   `e2e` jobs check that site and `deploy` publishes it; a test shows
   that no shard uploads a Pages artifact.
3. The lesson shards cover every lesson exactly once, none exceeds 32
   lessons, their number is derived from the lesson count and read from
   no file, and the workflow's lesson shards equal the script's; a test
   per property.
4. A failing shard, a missing or altered part, and a lesson page that
   differs from its shard's each fail `verify`; a test per case.
5. A pull request with a base runs the same jobs; a shard with nothing
   to execute finishes in its fixed cost; three consecutive warm-cache
   pull requests that each change one lesson, measured as F61 criterion
   1 measures them, finish within 12 minutes wall clock (20 minutes since
   ADR 015) on the sharded
   workflow, with their times, the assembly's time, and the projection
   to 110 lessons recorded in `docs/release-readiness.md`.
6. `./scripts/verify.sh` without options runs every check in one process
   on one machine as before; `--shard` and the assembly verify nothing by
   themselves; a test covers both.
7. Every group runs in exactly one job or one shard matrix; the tests
   marked `same_machine` run on the machine of the bytes they compare
   with; permissions are unchanged (the tests of F58 and F61 still pass).
8. The status of ADR 012 and ADR 014 records the delivery.

**Risk.** High. The feature changes the CI workflow and the deploy chain,
which need explicit human approval and security-focused review.
Technical risk: the assembly's render of a page from a shard's results
must equal the shard's render of it on another machine; the store holds
the executed outputs and the figure files as bytes, so the render should
not depend on the machine, and criterion 2 proves it on the hosted
runners. If it does not hold, the feature records the evidence and stops,
and the fallback of ADR 014 decision 11 is decided by the human as a
revision of that record.

**Detailed implementation plan expected.** Yes.

### F62 — Eight courses and the reference curriculum

**Source.** Change request sections 2, 3, 9, and 12 (decisions 5 to 7);
requirements decisions 23 to 25 and unresolved question 6; ADR 013,
proposed with this planning and accepted when it is approved.

**Problem.** The site has one course and no record of the reference
curriculum: no stable identifiers for the other seven courses, no place
for a planned lesson that is not a placeholder page, no way to show the
four method paths, and a hand-kept planned list on the home page that
names a delivered feature and a dropped one.

**Goal.** Implement ADR 013: the eight course identifiers and the strand
order; the curriculum file with the 115 slots, the four method paths, and
every slot's home and kind; the `slot` front-matter field with its checks;
the migration of the twenty-two published lessons; the path page and the
home page reading the planned structure from the file and every published
fact from front matter.

**User-visible outcome.** The learning path page lists the mechanics
course with its published lessons and, visibly distinguished, its planned
slots; names the seven courses that have no lesson yet in one sentence;
shows the four method paths as a secondary view with their published
lessons in path order and their planned slots; keeps every method view and
every link. The home page's planned list names the courses and paths of
the reference curriculum with their real published counts. A lesson header
shows the lesson's slot and, for a method-path lesson, its position in its
path. Every existing URL still works.

**In scope.**

- `COURSES` with the eight identifiers and titles of ADR 013 decision 1;
  `STRANDS` in the order of decision 2 (courses first, then the three
  method strands), with the display title of `agents-llm` refined to name
  physics and AI; a course still appears as a course only when it has a
  lesson.
- The curriculum file (site/curriculum.yaml), read and validated by
  `pbc.authoring.path`: the eight courses, the four paths, and the 115
  slots of the requirements' decision 23 with label, working title, home,
  position in the path where applicable, and kind; a schema check that
  rejects an unknown course or path, a duplicate label, a slot without a
  home, a slot with both a course and a path, and any field that belongs
  to front matter.
- The `slot` field: optional, unique, naming an existing label; the lesson
  source check fails on an unknown label, on two lessons with one slot,
  and on a lesson whose `course` is not the home of a slot homed in a
  course (a slot of a method path may be filled by a lesson of any
  course); the seventeen published lessons that fill a slot of their own
  course or of a path migrate (M1 to M8, M16, AI0, AI2, AI3, AI4, D6, D9,
  R1, L1 as listed under "State at the change cycle `final-curriculum`");
  the gas lesson gets no slot in F62 and keeps `course: mechanics`: F70
  sets `slot: T0` and `course: thermodynamics` together (ADR 013 decision
  6), and until then T0 is an unfilled planned slot of a course that has
  no lesson, named in the one sentence and shown nowhere else; the four
  Lean lessons beyond the baseline get no slot; front matter only, bodies
  byte-identical.
- The path page: planned slots per course and per path from the file,
  visibly distinguished, with label and working title only, no link and
  no count; the four paths as a view after the courses and before the
  method views; the planned courses named in one sentence; the test that
  compares the page with the front matter and the file.
- The home page: `PLANNED` of `pbc.authoring.home` replaced by the
  courses and paths of the file with their published counts; the test of
  the home page updated to read the file instead of the roadmap table.
- `path.json` (F13) and the lesson header carry the slot and the path
  position; `docs/authoring.md` and the lesson template state the slot
  rule and the placement rule of ADR 013; the content-proposal form's
  course list gains the eight courses.
- The prerequisite rule of ADR 013 decision 8 in the lesson source check
  (`pbc.authoring.path.problems`): a prerequisite must exist, the graph
  must have no cycle, and a prerequisite in the same strand must come
  earlier in that strand; a prerequisite in another strand may come later
  in the linear order. The course view and the path view of the path page
  order lessons by the order in which the curriculum file lists their
  slots, lessons without a slot after them in linear order; previous and
  next, the graph layout, and every address stay as they are. The path
  page's explanation of previous and next (F37) says that a prerequisite
  may live in a later strand and that the dependency map gives the order
  of ideas. Tests on fixture lessons: a `thermodynamics` lesson that
  requires the gas lesson of `agents-abm` (the T0 to T2 progression)
  passes and the course view lists T0 first; a `mechanics` lesson that
  requires a `lean` lesson passes; a prerequisite later in the same strand
  fails; a cycle across strands fails; the twenty-two published lessons
  still pass unchanged.

**Out of scope.** Any new lesson or strand directory (the first lesson
feature of each course creates it); the redesign of the path page's
layout (F64) and the thumbnails (F63); changing any address, identifier,
or lesson body.

**Dependencies.** F03 (F62 replaces the "prerequisite later in the path"
check of F03 criterion 2 by the graph rule of ADR 013 decision 8), F37
(the metadata and the path page it extends), F26 and F27 (consumers that
must keep working), F25 (the home page's planned list).

**Acceptance criteria.**

1. The curriculum file holds exactly 81 Part A slots in the eight courses
   (17, 12, 9, 9, 10, 8, 10, 6), 33 Part B slots in the four paths (9, 13,
   5, 6), and the one Lean slot; 16 slots are labs and 3 are capstones;
   a test counts them, so that a change of the file is a reviewed change
   of the curriculum and this roadmap's "Slot mapping" is updated with it.
2. The seventeen published lessons that fill a slot of their course or of
   a path carry their slot; the gas lesson (T0, set by F70) and the four
   Lean lessons beyond the baseline carry none; a test shows the build
   fails on an unknown label, on a duplicated slot, and on a lesson whose
   course is not the home of the course slot it names; lesson bodies are
   byte-identical to before, shown by the diff of the pull request.
3. The path page shows every published lesson under its course and, for
   a method-path lesson, under its path at its position; every unfilled
   slot of a course that has a lesson, and of every path, appears as
   planned with no link; a course that has no lesson is named in the one
   sentence and shows no slot (so T0 is listed only from F70); a planned
   slot is never counted in a published count; shown by a test over the
   file and the front matter.
4. Every lesson URL that existed before the feature resolves to the same
   lesson, and previous and next follow the strand order of ADR 013
   (unchanged until a second course strand exists), shown by the test over
   the list of previous addresses.
   The prerequisite check accepts a prerequisite in a later strand and
   rejects a later prerequisite in the same strand and a cycle, shown by
   the fixture tests of ADR 013 decision 8 (the T0 to T2 progression and
   a cross-strand dependency), and the course view orders by the slot
   order of the curriculum file.
5. The home page's planned list is derived from the file, names no
   delivered feature, and its test reads the file.
6. From the home page, with JavaScript disabled, a reader reaches every
   lesson through the course list and through each path; the page passes
   the accessibility scan and reflows at 320 CSS px.
7. ADR 013 is accepted with the merge; ADR 008 names it in its status;
   F15 is recorded as dropped.

**Risk.** Medium. The migration touches the front matter of every lesson
and the header every page renders; the F03 and F37 tests catch drift. The
file is a new validated input that the human approves line by line.

**Detailed implementation plan expected.** Yes, short: the file schema,
the migration table, the page sections.

### F63 — Verified lesson previews

**Source.** Change request section 8.2 (items 3 and 5), 8.3, and section
10 ("Shared figure/preview infrastructure"); requirements "UX expectations"
(thumbnails) and non-goals (no decorative, stock, hand-copied, or external
images); decision 29.

**Goal.** A deterministic small preview for every published lesson,
derived from the lesson's own verified figure by the same executed cell
that produces it, with a repository-generated conceptual SVG as the
documented fallback, so that the learning path can show one verified
thumbnail per lesson without any committed, copied, or external image.

**User-visible outcome.** Nothing until F64 uses it, except that the
preview of every lesson is built, checked, and byte-stable, and the
learning path export names it.

**In scope.** The optional `preview` front-matter field naming a figure
cell label of the lesson. Introducing the field is justified (change
request section 8.3 and requirements decision 29 allow a new field only
when it is needed) because a lesson has several figures and the
representative one (a measured-versus-model panel, a phase curve) is
often not the first, which is frequently a conceptual setup diagram;
deriving the preview from the first figure cell was considered and
rejected for that reason. Declaring it stays optional per lesson, with
the conceptual fallback below for a lesson that names none, so that no
lesson is forced to declare one. The
figure helper writes, beside the full
figure, a small raster or SVG rendering at a fixed size with the same
status label in its alt text; a lesson without `preview` gets the
conceptual fallback drawn by code from its course and methods (no image
file); the built-site check that every lesson has exactly one preview,
that it comes from the named cell or the fallback, that two builds give
byte-identical previews, and that no image on the path page is loaded
from outside the build; `path.json` carries the preview path and its alt
text; the twenty-two published lessons each name a preview cell (a
trajectory, a phase curve, a measured-versus-model panel, a transcript
figure, a proof diagram) chosen in the Issue; `docs/authoring.md`.

**Out of scope.** The path page layout (F64); cropping by hand;
image files of any kind; previews of pages that are not lessons.

**Dependencies.** F62 (the field joins the validated schema), F28 (figure
status), F44 (the visual system's sizes).

**Acceptance criteria.** Every lesson has one preview that a test traces
to its named cell or to the fallback; two builds produce byte-identical
previews; the preview carries alt text with the status; the previews of all
lessons together stay within the initial payload budget of the path page
(measured by the F44 check); the authoring guide states the rule; a lesson
whose `preview` names no figure cell fails the build.

**Risk.** Medium. Matplotlib output at small sizes needs explicit,
deterministic configuration; the F02 determinism settings and the byte
test guard it.

**Detailed implementation plan expected.** Yes, short.

### F64 — Learning Path redesign: course-first, compact, accessible

**Source.** Change request section 8 (8.1 to 8.5) and section 12,
decision 8; requirements "UX expectations" (Learning Path page) and
decision 29.

**Decision on scope (section 8).** One feature, after F62 (the data) and
F63 (the previews), that rebuilds the page from the delivered F26, F27,
F37, F41, F44, F13, and F14 foundations without reopening them. It is
delivered before the bulk of the new lessons, so that the page does not
deteriorate as the catalogue grows.

**Problem.** The page exposes every card in full in every view, repeats
long cards across the course and method views, shows the whole graph
prominently, and will become unreadable at a hundred lessons. It must
look like a calm scientific publication: course-first, compact, with
detail on demand.

**Goal.** The page of the requirements' "UX expectations": course panels
with real counts and verified miniatures; a course's lessons behind native
disclosure, closed by default; compact cards with a thumbnail and chips;
details on expansion; the method paths and the methods as a secondary
view; the graph under an optional disclosure with course-scoped subsets;
optional filters that coordinate with the search; every lesson reachable
without JavaScript; every existing address valid.

**User-visible outcome.** A first-time visitor sees "Choose a physics
course" with the three activities explained, compact course panels, one
per course that has a lesson, with the courses that have none named in
one sentence (the change request asks for eight panels; the
requirements' use case 1 and ADR 013 decision 5 show a course as each
gains a lesson, so a course without one gets no panel for that reason; a
panel with a zero count and a conceptual miniature was considered and
rejected, because the change request forbids advertising planned content
as published and a zero-count panel is a placeholder in another form),
opens a course, scans its lessons as small rows with one preview each,
opens a
lesson's details when wanted, switches to the physics-and-AI paths, the
measured-data labs, agent-based modelling, or Lean as views over the same
lessons, and finds the dependency map at the bottom.

**In scope.**

- The page generator (`pbc.authoring.path`, the templates, `site/path`)
  rendering: the intro; one panel per course with description, published
  count, the F63 preview of its first or representative lesson (chosen by
  a rule in the file, not by hand), and the entry link; `<details>` and
  `<summary>` per course, closed by default, with the current course open
  when the page is reached from a lesson, if that can be done without a
  script; lesson rows in the slot order of the curriculum file (ADR 013
  decision 8) with title, one-sentence physical question,
  difficulty badge, thumbnail, chips for simulation, experimental data,
  and AI extensions, and planned slots as distinguished rows; a nested
  disclosure per lesson with outcomes, prerequisites, what the reader
  builds, related extensions, the capstone classification for T11, EM9,
  and FL10 when they exist, and the reproduce link; the four method paths
  and the method views as secondary sections that list the same lessons
  compactly and link to the canonical pages; the F13 progress marks and
  the F14 recommendations kept.
- The graph (F26) unchanged in content, under a "View dependency map"
  disclosure, with a course-scoped subset per course generated from the
  same metadata and the text alternative kept.
- Optional filters (course, method, difficulty, publication state) as a
  form that works by links without JavaScript and is enhanced with a
  script that stores nothing; coordinated with the search of F41 (the
  index keeps the page's prose).
- Responsive layout at phone, tablet, and desktop widths; focus states;
  reduced motion; the F44 design system; the payload budgets of the
  architecture measured for the new page; no framework; no external
  resource.
- The tests: the page equals the front matter and the curriculum file;
  counts equal the published lessons; every lesson reachable with scripts
  disabled through its course and through each path and method; every
  previous address and graph node address resolves; the accessibility
  scan, the keyboard pass over the disclosures and the graph, and the
  no-two-way-scroll check at 320 CSS px; the payload check; byte-stable
  rebuilds; the search index unchanged in meaning.
- A visual review before merge recorded on the Issue: an introductory
  course, the mechanics course with its planned slots, a measured-data
  lesson, an agent lesson, long titles, and the phone layout.

**Out of scope.** New lessons; changes to lesson pages beyond the header's
link to the path; a second catalogue; images that are not F63 previews;
animation; a frontend framework; changing any address. [Note of the change
cycle `scientific-atelier-atlas`, 2026-10-17: "images that are not F63
previews; animation" is superseded by requirements decision 37 and ADR
018 for the interface artwork of the atlas (the course areas and their
small illustrations, as a distinct asset class beside the previews, which
stay the lesson rows' images) and for accessible animation; the second
catalogue, the framework, and the address exclusions stand, and the page's
index of F64 is built on by F125 and F126, never reopened. This block is
the record of what F64 delivered and is not rewritten.]

**Dependencies.** F62, F63, F26, F27, F37, F41, F44, F13, F14.

**Acceptance criteria.**

1. With JavaScript disabled, a first-time visitor can choose a course,
   expand it, find every published lesson, read its prerequisites, and
   follow its canonical link; shown by a built-site test per course and
   per path.
2. The method-path view and the method views show no duplicate lesson
   content and miss no lesson; a lesson appears once as a canonical page
   and elsewhere as a link; shown by a test.
3. Every course and path count equals the published catalogue; planned
   slots are visibly distinguished and never linked or counted.
4. Every previous address, bookmark, and graph node address resolves;
   shown by the test over the list of previous addresses.
5. Every thumbnail is an F63 preview with alt text; no image loads from
   outside the build.
6. The accessibility scan passes; the disclosures and the graph work by
   keyboard and read correctly with a screen reader in the manual pass
   recorded on the Issue; the page reflows at 320 CSS px without two-way
   scrolling; reduced motion is respected.
7. The page's initial payload is within the architecture's budget, and
   its byte-stable rebuild, link, prerequisite, and search-index tests
   pass.
8. The visual review of criterion 8.4 of the change request is recorded
   on the Issue before merge.

**Risk.** Medium. The page is the site's main navigation; the tests of
F03, F26, F27, F37, F41, and F13 catch regressions, and the no-script
tests are the guard for the disclosures.

**Detailed implementation plan expected.** Yes.

### Wave C1 — Discovery foundation and the first new physics

Order within the wave, by dependency: F65 first among the discovery
features and the only feature of the wave that may start before the
gates, because it publishes no lesson; every lesson feature of the wave
after F61 and F62, and after F113 once the lesson count would pass 32
(the full-run gate: the wave adds twenty-six lessons to twenty-two, so
F113 lands within this wave, after about the first ten; since 2026-10-15
the first ten are published, F113 is paused, and the gate is the amended
gate under "Phase 4"); then F66 and
F67; the first lesson features of the
courses (F68, F70, F71, F72, F73) are independent of each other and of
F65 and may run in parallel worktrees; F69 after F68; F74 after F71 and
F51; F52, F53, F54, F45, and F55 of the previous phase as their
dependencies, including the gates, are met (see "State at the change
cycle `final-curriculum`"). This wave is the first block of new lessons;
the waves after it are the bulk that F64 gates.

### F65 — Physics environments and the discovery evaluation protocol

**Source.** Change request sections 5, 7.3, and 10 ("Law-discovery
sandbox & evaluation protocol"); requirements decision 25; ADR 004;
architecture, "Law-discovery environment and agent benchmark".

**Decision on slicing (section 10).** One shared package, `pbc.discovery`,
carries the environments, the baselines, and the protocol; the lessons of
the law-discovery and benchmarking paths are separate features that use
it. No lesson builds its own framework.

**Goal.** A reusable environment abstraction over the models of `src/pbc`
with the hidden truth kept apart from the agent; non-agent baselines; the
evaluation protocol (splits, held-out worlds, budgets, seeds, scoring,
versioned prompts and models, frozen traces, cost records); and the
harness allowlist that exposes an environment's controls and observations
to an agent and nothing else.

**User-visible outcome.** Nothing on the site; in the repository, the
package with its tests and one worked environment (the force laws of the
mechanics course with modifiable parameters and a hidden modified law),
the protocol written in its own document, docs/discovery-protocol.md
(new in this feature, as F46 added `docs/validation-contract.md`; the
feature registers it in `docs/project-map.md`), and the authoring section
"Discovery lessons". The protocol does not go into `docs/evaluation.md`,
which is the review-criteria document of the development workflow, not a
product document.

**In scope.** `Environment` (controls with bounds and units, observations
with noise, a budget, reset, a hidden truth that no public method
returns); environments for the projectile, the oscillator, the central
force, and an N-body world once F69 exists; the harness tools over an
environment (ADR 004) with tests that the allowlist cannot reach the
truth; baselines (random and grid probing, least squares in `pbc.data`,
sparse identification or symbolic regression in pure Python or as a
locked library with its licence recorded); the protocol: held-out
settings, full, partial, and no prior-knowledge conditions, budgets, seeds,
scoring, the replay fixture with model, prompt, and version, cost and call
counts recorded from the run that produced the fixture; the rule that a
full benchmark run lives outside `verify.conf` with a small deterministic
replay on the page.

**Out of scope.** Any lesson page; external benchmark assets (inspiration
only, no embedding before licences and assumptions are checked); code
execution by the agent; a neural or general machine-learning framework.

**Dependencies.** F09, F16, F20 (the harness, the counterexample loop,
and the design agent it generalises), F23 (the fitting helpers), F46 (the
validation contract).

**Acceptance criteria.** A test shows the agent's tools cannot read the
hidden truth of any environment; each baseline recovers a known law or
parameter on a synthetic environment within tolerance and reports failure
on one it cannot; the protocol's scoring is deterministic from a frozen
trace and recomputed by a test; the replay passes without credentials; a
locked discovery library, if any, has its licence and weight recorded;
docs/discovery-protocol.md (which does not exist before this feature)
states the protocol, `docs/project-map.md` lists the document, and the
authoring guide states its use; `docs/evaluation.md` is unchanged.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F66 — Law discovery lessons: black-box force laws (D1, D2, D3)

**Source.** Change request section 5 (B2: D1 to D3) and section 10
("First discovery lessons"). Slots D1, D2, D3 of the scientific law
discovery path; lessons in `agents-llm` with `course: mechanics`.

**Goal.** Three lessons on the F65 environments: discovering an unknown
force law with controlled probes (D1); the same discovery with full,
partial, and no prior knowledge compared under one protocol (D2); and
unlearning a familiar law to identify a deliberately modified one (D3);
each with a non-agent baseline, held-out tests, a frozen replay, and a
typed verdict only where the build recomputes it.

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F65.

**Acceptance criteria.** The lesson rule; the agent rule; the three
conditions of D2 scored on the same held-out settings; the modified law of
D3 recovered by the baseline and reported for the agent as it is; the
replay recomputed by the build.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F67 — Symbolic regression and equation discovery (D7, D8)

**Source.** Change request section 5 (B2: D7, D8). Slots D7 and D8;
lessons in `agents-llm` with `course: mechanics`, methods `simulation`
(and `llm-agents` only where an agent is used).

**Goal.** Interpretable functional forms recovered from simulated data
with non-LLM tools (D7), and dynamical equations inferred from
trajectories with numerical derivatives and noise (D8), on the course's
models, with the identifiability and noise limits stated; the baselines
every later discovery lesson compares with.

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F65, F23.

**Acceptance criteria.** The lesson rule; a known law and a known equation
recovered within tolerance from clean data and the failure under noise
shown and explained; any locked library's licence recorded; no claim that
a recovered form is the physical law beyond what held-out data supports.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F68 — Advanced mechanics: chaos, Lagrangian and Hamiltonian mechanics, resonance (M9 to M12)

**Source.** Change request section 4 (A1: M9, M10, M11, M12). Slots M9 to
M12 in the `mechanics` strand.

**Goal.** Four lessons: the double pendulum and sensitivity to initial
conditions with a Lyapunov estimate (M9); constrained and coupled systems
from a Lagrangian, simulated and checked (M10); phase space, symplectic
structure, and geometric integration (M11); damping, driving, resonance
curves, and their validation (M12).

**Note on F45.** F45's default coding-agent exercise is a damped driven
oscillator with resonance. Whichever lands first owns the verified
reference solution in `src/pbc`; the other reuses it; M12 is the course
lesson that teaches the physics and F45 the exercise that builds it.

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F05, F06; coordination with F45 as noted.

**Acceptance criteria.** The lesson rule; M9's Lyapunov estimate checked
against the sign expected in regular and chaotic regimes; M10's equations
checked against the Newtonian form for a case with a closed form; M11's
symplectic integrator checked for the conserved modified energy of M5 and
L3, with L3 among M11's prerequisites although it lives in the later
`lean` strand (ADR 013 decision 8); M12's resonance curve checked against
the analytic amplitude.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F69 — Mechanics: many-body gravitation, nonlinear dynamics, rotational motion (M13, M14, M17)

**Source.** Change request section 4 (A1: M13, M14, M17; M17 new in
revision 2). Slots M13, M14, M17 in the `mechanics` strand.

**Goal.** N-body orbits and long-term stability with an optional REBOUND
comparison as a declared reference artifact (M13); attractors,
bifurcations, and where linearisation fails (M14); rigid-body rotation,
inertia tensors at an introductory level, torque, angular momentum, and
gyroscopic precession as the worked example, with unit, energy, and
angular-momentum checks (M17, linked to M10, M11, and later D13).

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F68, F06.

**Acceptance criteria.** The lesson rule; M13's energy and angular-momentum
drift reported per integrator and compared with the reference artifact
where one is declared; M14's bifurcation diagram checked against a known
threshold; M17's precession rate checked against the analytic limit.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F70 — Thermodynamics and statistical physics: random walks, kinetic theory, entropy (T1, T2, T3)

**Source.** Change request section 4 (A2: T1, T2, T3) and section 3
(legacy T0). Slots T1 to T3; the first lesson feature of the
`thermodynamics` course: it creates the strand directory and
`pbc.thermodynamics`, and re-homes the gas lesson of F11 as `course:
thermodynamics`, `slot: T0` under its `agents-abm` address, setting the
two fields in one change (the lesson carries no slot before F70; ADR 013
decision 6).

**Goal.** From microscopic randomness to diffusion laws (T1); particle
collisions and the Maxwell-Boltzmann distribution, reusing the F11 gas
model (T2); entropy from ensembles with its scope and limits (T3).

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F11, F06.

**Acceptance criteria.** The lesson rule; the course appears on the path
with its four lessons (T0 to T3, T0 first by the slot order of the
curriculum file) and its eight planned slots; T0's address and identifier
unchanged and its header naming the new course; T2 lists T0 as a
prerequisite although T0 comes later in the linear order (ADR 013
decision 8); T1's
diffusion coefficient checked against the random-walk prediction; T2's
distribution checked against the analytic form at the simulated
temperature; T3's entropy checked in a case with a closed form.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F71 — Waves and optics: the wave equation, interference, sound (W1, W2, W9)

**Source.** Change request section 4 (A3: W1, W2, W9; W9 new in revision
2, numerical, no recording). Slots W1, W2, W9; the first lesson feature of
the `waves` course (strand directory, `pbc.waves`).

**Goal.** Finite-difference wave propagation with boundaries and
convergence (W1); superposition, standing waves, modes, and dispersion
(W2); numerical sound propagation, resonance, and the Doppler shift with
analytic limiting cases, with no audio or sensor requirement (W9).

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F05.

**Acceptance criteria.** The lesson rule; W1's convergence order measured
and the CFL limit shown; W2's mode frequencies checked against the
analytic values; W9's Doppler shift checked against the formula for a
moving source and a moving observer.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F72 — Electromagnetism: fields, charged particles, induction (EM1, EM2, EM3)

**Source.** Change request section 4 (A4: EM1, EM2, EM3). Slots EM1 to
EM3; the first lesson feature of the `electromagnetism` course (strand
directory, `pbc.electromagnetism`); gives F54 its home.

**Goal.** Vector fields, superposition, and potential (EM1);
charged-particle motion in given fields (EM2); time-dependent flux and the
induced electromotive force (EM3).

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F06.

**Acceptance criteria.** The lesson rule; EM1's field checked against the
closed form for a dipole; EM2's cyclotron frequency checked; EM3's induced
voltage checked against the flux derivative.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F73 — Fluid dynamics: advection, Burgers, finite volumes, shallow water (FL1, FL4, FL9, FL5)

**Source.** Change request section 4 (A5: FL1, FL4, FL9, FL5; FL9 new in
revision 2; FL5 enhanced in revision 3), section 7.1 (FL9, FL5), and
section 10 ("Conservative numerical methods"). Slots FL1, FL4, FL9, FL5 in
the teaching order FL1, FL4, FL9, FL5; the first lesson feature of the
`fluids` course (strand directory, `pbc.fluids` with the conservative
fluxes that FL5 and FL10 reuse); gives F53 its home.

**Goal.** Schemes, boundary conditions, stability, and artificial
diffusion (FL1); nonlinear steepening, shocks, and numerical dissipation
(FL4); transparent conservative fluxes with CFL limits, shock capturing,
mass and momentum budgets, convergence, and a comparison with a
non-conservative discretisation (FL9); the depth-averaged balance, a small
conservative scheme with still-water and dam-break checks, depth
positivity, boundaries, and conservation (FL5).

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F05, F06.

**Acceptance criteria.** The lesson rule; FL1's numerical diffusion
measured against the modified equation; FL4's shock speed checked against
the Rankine-Hugoniot condition; FL9's budgets conserved to round-off and
the non-conservative scheme's error shown; FL5's still water preserved and
the dam-break front checked against the exact solution; one flux
implementation shared by FL9 and FL5.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F74 — Wave flume lab (W8)

**Source.** Change request section 4 (A3: W8); the Aalborg submerged-bar
dataset with a go decision from F50 (`docs/datasets/aalborg-submerged-bar.md`).
Slot W8, a measured-data lab of the `waves` course.

**Goal.** Measured tank waves over a submerged bar compared with the
simulated propagation and dispersion of W1 and W2, with the measured and
the modelled-reference artifacts of the card kept distinct, the waveform
comparator of F43, residuals, and a qualified claim.

**Dependencies.** F61, F62 (the gates of this phase), F113 by the lesson-shard rule of the full-run gate, F71, F51, F43; the go decision exists, so no new spike
unless the committed sample needs widening within the caps.

**Acceptance criteria.** The lab rule; the measured series never labelled
`simulated` and the CFD series of the card labelled by its artifact; the
model's dispersion compared with the measured gauges with uncertainty.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### Wave C2 — Core subject expansion and numerical engineering

Order within the wave: every lesson feature of this wave after F64 (the
gates under "Phase 4"); F75 and F76 after F70; F77 after F71; F78 after
F72 and F71; F79 after F73; F80 after F78; F81 after F66 and F67; F82
after F67 and F69; the labs F83 to F86 after their course lessons and
F51, each through its gate.

### F75 — Thermodynamics: Ising model, molecular dynamics, heat engines (T4, T5, T9)

**Source.** Change request section 4 (A2: T4, T5, T9; T9 new in revision
2). Slots T4, T5, T9 in the `thermodynamics` strand.

**Goal.** Magnetisation, critical behaviour, and finite-size effects (T4);
interparticle potentials, thermodynamic observables, and drift checks
(T5); idealised Carnot and comparison cycles with heat, work, and
efficiency from p-V paths and the first and second laws checked (T9).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F70.

**Acceptance criteria.** The lesson rule; T4's critical temperature
estimated and compared with the exact two-dimensional value with
finite-size caveats; T5's energy conservation and equipartition checked;
T9's efficiency checked against the Carnot bound.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F76 — Heat conduction and the finite-element bridge (T6, T10)

**Source.** Change request section 4 (A2: T6 enhanced in revision 3; T10
new in revision 3), section 7.1 (T6/T10/T11), and section 10 ("FEM and
engineering mesh foundation"); requirements decision 26 and non-goals (no
heavyweight solver as a mandatory dependency). Slots T6 and T10 in the
`thermodynamics` strand; adds `pbc.fem`, the small triangular
finite-element solver that T11 and MAT3 reuse.

**Goal.** From lumped cooling to the one- and two-dimensional heat
equation with finite differences, conductive and convective boundaries,
stability, grid and time-step convergence, and units (T6); then weak-form
intuition, piecewise-linear elements on a small triangular mesh generated
and inspected in the lesson, assembly and solution of a sparse system with
SciPy, explicit boundary conditions, comparison with the finite-difference
solution and a manufactured solution, mesh-quality and refinement checks,
and energy and heat-flux balances (T10). Gmsh and FEniCSx are optional
reference tools whose output, if used, is a declared `modelled-reference`
input; they are not dependencies.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F70.

**Acceptance criteria.** The lesson rule; T6's stability limit and
convergence order measured; T10's error against the manufactured solution
decreasing at the expected rate under refinement, its flux balance closed
to a stated tolerance, its page within the 30-second budget on the pinned
stack, and any optional-tool artifact carrying a card; a test that
`pbc.fem` has no import outside the locked environment.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F77 — Optics: refraction, polarisation, diffraction, inverse optics (W3, W4, W5, W6)

**Source.** Change request section 4 (A3: W3 to W6). Slots W3 to W6 in
the `waves` strand; W5 prepares F52's home.

**Goal.** Propagation across an interface with Snell's law verified (W3);
polarisation states, Malus's law, and practical limits (W4); Fraunhofer
diffraction and instrument limits (W5); inferring optical parameters from
intensity data, on simulated data until F52 provides measured images (W6).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F71.

**Acceptance criteria.** The lesson rule; W3's refracted angle, W4's
transmitted intensity, and W5's fringe spacing checked against the closed
forms; W6's recovered parameters within tolerance on synthetic data with
the identifiability limit shown.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F78 — Electromagnetism: Maxwell's equations and FDTD, RLC circuits, waveguides and antenna basics (EM4, EM5, EM6)

**Source.** Change request section 4 (A4: EM4, EM5, EM6 enhanced in
revision 3). Slots EM4 to EM6 in the `electromagnetism` strand.

**Goal.** A transparent finite-difference time-domain solver for
electromagnetic waves (EM4); transient and frequency-domain circuit
behaviour (EM5); modes, boundary conditions, and transmission in
waveguides, with the bridge from superposition to element radiation
patterns that EM9 needs and the limits of the idealised models (EM6).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F72, F71 (W1's finite differences and W2's
superposition).

**Acceptance criteria.** The lesson rule; EM4's wave speed and reflection
checked and its stability limit shown; EM5's resonance checked against the
analytic response; EM6's cut-off frequencies checked and the element
pattern compared with the analytic dipole pattern.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F79 — Fluid dynamics: Navier-Stokes, vortex shedding, particle-based fluids (FL2, FL3, FL6)

**Source.** Change request section 4 (A5: FL2, FL3, FL6). Slots FL2, FL3,
FL6 in the `fluids` strand; FL3 prepares F53's physics.

**Goal.** A contained two-dimensional incompressible solver (FL2);
vorticity, shedding, and the Reynolds-regime caveats (FL3); grid versus
particle modelling and its limits (FL6).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F73.

**Acceptance criteria.** The lesson rule; FL2 checked against a
lid-driven-cavity reference at low Reynolds number declared as a
`modelled-reference` input or against a manufactured solution; FL3's
Strouhal number compared with the published range with the regime stated;
FL6's conservation checked.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F80 — Applied capstone: adaptive phased-array beam steering (EM9)

**Source.** Change request section 4 (A4: EM9), section 4.1, section 7.1
(EM9), and section 10 ("A4 selected phased-array capstone"); requirements
decision 26 and non-goals. Slot EM9, the applied capstone of the
`electromagnetism` course.

**Goal.** A finite-array complex field and array-factor model checked
against analytical steering, null, and symmetry limits; electronic
steering toward a moving receiver and a null toward an interferer where
feasible; the effect of element spacing, amplitude and phase control,
quantisation, frequency, noise, and element patterns on the main lobe,
sidelobes, and grating lobes; the trade-offs and the cases where the ideal
model fails; the page states that an array-factor model is not a full-wave
antenna or metasurface design and implies no fabricated device.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F78, F71 (W2); F54 optional for measured RF context.

**Acceptance criteria.** The capstone rule; the steering angle, the null
depth, and the grating-lobe onset checked against the analytic
expressions; the quantisation and noise degradation measured; an
optional full-wave element reference, if used, declared as a
`modelled-reference` input; deterministic preview figures from the verified
sequence, and any interactive enhancement degrading to them.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F81 — Interactive discovery benchmarks and non-agent baselines (EV2, EV3)

**Source.** Change request section 5 (B3: EV2 enhanced in revision 2,
EV3). Slots EV2 and EV3 of the agent benchmarking path; lessons in
`agents-llm` with `course: mechanics`.

**Goal.** Whether agents discover laws through simulated experiments at
full, partial, and no prior knowledge under one protocol with budgets and
held-out evaluation (EV2); whether agentic tool use outperforms a plain
model, random selection, or symbolic fitting (EV3); with the protocol of
F65 and the lessons of F66 and F67 as the subjects.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F65, F66, F67.

**Acceptance criteria.** The agent rule; the scores recomputed from frozen
traces; the baselines on the same environments and budgets; the page
states when a comparison is not meaningful because budgets or
environments differ; no live call in CI.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F82 — Discovering conservation laws and invariants (D13)

**Source.** Change request section 5 (B2: D13, new in revision 2) and
section 7.1 (D13). Slot D13 of the law discovery path; lesson in
`agents-llm` with `course: mechanics`.

**Goal.** Candidate conserved functions inferred from trajectories of
unknown systems, validated across held-out initial conditions and
integration settings, true invariants separated from integration drift and
coincidental correlations, with a non-LLM numerical baseline and the
symmetry-conservation connection explained without assuming equation
recovery; on the mechanics models of M11 and M17 and, where F73 exists,
the fluxes of FL9.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F65, F67, F69.

**Acceptance criteria.** The lesson and agent rules; the baseline finds
the known invariants of a test system and rejects a drift artefact; the
agent's candidates are tested on untouched trajectories by the build; the
withheld truth is unreachable.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F83 — Pendulum and accelerometer data lab (M15)

**Source.** Change request section 4 (A1: M15). Slot M15, a measured-data
lab of the `mechanics` course; no candidate card exists.

**Goal.** Fit the dynamics of M4, M6, and M12 to genuine already-collected
motion data (a published pendulum or accelerometer record with rights for
redistribution), with calibration, noise, residuals, and uncertainty.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F51, F68; a new candidate card and spike with a go
decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F84 — Heat transfer measurements lab (T7)

**Source.** Change request section 4 (A2: T7). Slot T7, a measured-data
lab of the `thermodynamics` course; no candidate card exists.

**Goal.** Thermal conductivity or relaxation inferred from real temperature
records against the models of T6, with uncertainty; an optional cross-link
for T11's parameters.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F76, F51; a new candidate card and spike with a go
decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F85 — Brownian motion tracking lab (T8)

**Source.** Change request section 4 (A2: T8). Slot T8, a measured-data
lab of the `thermodynamics` course; no candidate card exists.

**Goal.** Diffusion coefficients inferred from genuine tracked-particle
trajectories against T1, with the tracking disclosed as processing.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F70, F51; a new candidate card and spike with a go
decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F86 — RLC circuit measurements lab (EM8)

**Source.** Change request section 4 (A4: EM8). Slot EM8, a measured-data
lab of the `electromagnetism` course; no candidate card exists.

**Goal.** Measured impedance or time responses of a real circuit fitted
with the EM5 model, with uncertainty.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F78, F51; a new candidate card and spike with a go
decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### Wave C3 — Applied capstones, advanced physics, and the agent paths

Order within the wave: every lesson feature of this wave after F64 (the
gates under "Phase 4"); F87 after F76; F88 after F73 and F51; F89 to F95
by their dependencies, in parallel worktrees where independent; F96 after
F65; F100 after F96 and F65; F97 after F96; F98 after F66 and F81; F99 after F66, F69,
and F91; F101 after F81 and F98; the labs F102 to F108 after their course lessons, each through its
gate.

### F87 — Applied capstone: thermal engineering of a hypothetical AI accelerator (T11)

**Source.** Change request section 4 (A2: T11), section 4.1, section 7.1,
and section 10 ("A2 applied thermal capstone"); requirements decision 26
and non-goals. Slot T11, the applied capstone of the `thermodynamics`
course.

**Goal.** A hypothetical multi-hotspot package or cold-plate proxy: heat
loads, geometry and material conductivities, contact and convective
boundary assumptions, and thermal constraints stated; transient and
steady temperature fields with `pbc.fem`; cooling, material, and layout
scenarios compared; the maximum temperature optimised under stated mass,
size, and heat-removal constraints; mesh, time-step, and sensitivity
studies against the T6 finite-difference baseline; a trade-off table and
a justified recommendation; labelled a digital-twin-style teaching
prototype, not a calibrated twin or a model of a proprietary device, with
no vendor data and no full three-dimensional CFD.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F76; F84 optional for a measured cross-link.

**Acceptance criteria.** The capstone rule; the energy and flux balances
closed to a stated tolerance; the finite-element and finite-difference
solutions agreeing under refinement; the sensitivity plot and the
trade-off table generated by the build; the credibility label as a typed
claim on the page; the page within the budget with a small mesh.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F88 — Applied capstone: reconstructing the 2025 Kamchatka tsunami (FL10)

**Source.** Change request section 4 (A5: FL10), section 4.1, section 7.1
(FL10), section 7.2 (the gated comparison), section 10 ("A5 selected
tsunami capstone"), section 12 (decision 10), and section 14 (candidate
sources); requirements decision 26, "Data and persistence" (measured-data
target), and non-goals. Slot FL10, the applied capstone of the `fluids`
course.

**Decision on slicing (section 12, decision 10).** Two deliverables in
one feature, separable into two Issues: the simulation and benchmark core,
which depends on no dataset approval and is published as clearly
simulated; and the historical comparison, which starts with the F50 spike
of the DART records and the bathymetry (rights, provenance, processing,
station and time-window suitability, a tractable sample) and is published
only on a go decision. The second never blocks the first.

**Goal.** A teaching-scale, non-operational two-dimensional propagation
model from the shallow-water equations and the conservative fluxes of
FL9 and FL5: flat-bottom analytical and benchmark cases, then regional,
source-documented bathymetry on a cropped grid and a transparent assumed
initial sea-surface displacement; open boundaries, CFL and grid
convergence, mass budgets, wet-dry limits, dispersion, Coriolis, and
spherical-geometry approximations, and the source uncertainty explained;
wave-height and travel-time figures; after the gate, qualified arrival-time
and waveform comparisons with authentic July 2025 DART records with
residuals and uncertainties; the page states it is not for warning,
inundation, or hazard forecasting.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F73, F51; F50's process for the DART and bathymetry
candidates (new cards).

**Acceptance criteria.** The capstone rule; the benchmark suite (still
water, linear-wave propagation, conservation, positivity, boundary
sensitivity) deterministic and within the page budget on the cropped grid;
the bathymetry's source and licence on its card; until the gate grants it,
no measured comparison and no claim of agreement with observations; after
it, the lab rule applies to the comparison, which is a validation
component and not a seventeenth lab; heavier reruns outside `verify.conf`.

**Risk.** High. Scope, data rights, and the temptation to present a
striking animation as validation; the two-deliverable slicing, the gate,
and the review guard it.

**Detailed implementation plan expected.** Yes, likely two Issues.

### F89 — Quantum physics: the Schrödinger equation, tunnelling, the harmonic oscillator (Q1, Q2, Q3)

**Source.** Change request section 4 (A6: Q1, Q2, Q3). Slots Q1 to Q3;
the first lesson feature of the `quantum` course (strand directory,
`pbc.quantum`); QuTiP is an optional comparator only.

**Goal.** Numerical evolution of a one-dimensional wavepacket (Q1);
barrier transmission and reflection against energy (Q2); eigenstates,
energies, and numerical convergence (Q3).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F05, F71 (W1's finite differences).

**Acceptance criteria.** The lesson rule; norm conservation and the
free-particle dispersion checked (Q1); the transmission coefficient
checked against the closed form (Q2); the eigenvalues converging to the
analytic spectrum (Q3).

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F90 — Quantum physics: spin, entanglement and Bell inequalities, open systems (Q4, Q5, Q6)

**Source.** Change request section 4 (A6: Q4, Q5 enhanced in revision 2,
Q6). Slots Q4 to Q6 in the `quantum` strand; Q5's Bell and CHSH content
is the first half of the linked Q5/Q8 enhancement.

**Goal.** Spin states, probabilities, and the modelled Stern-Gerlach
apparatus (Q4); correlations, measurement, the Bell and CHSH inequalities,
and the distinction between the quantum prediction and the
local-hidden-variable bound (Q5); density matrices, decoherence, and
master equations (Q6).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F89.

**Acceptance criteria.** The lesson rule; Q5's CHSH value computed from
the simulated correlations and compared with both bounds; Q6's trace and
positivity preserved by the integrator.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F91 — Astrophysics: the three-body problem, modified gravity, lensing (AST1, AST2, AST3)

**Source.** Change request section 4 (A7: AST1, AST2, AST3). Slots AST1
to AST3; the first lesson feature of the `astrophysics` course (strand
directory, `pbc.astrophysics`, reusing the N-body code of F69).

**Goal.** Nonlinear gravitational dynamics, stability, and initial
conditions (AST1); deliberately modified central-force laws with orbit
diagnostics (AST2); simplified deflection and lensing models with the
limits of mass inference (AST3).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F69.

**Acceptance criteria.** The lesson rule; AST1's conserved quantities
tracked and a known periodic solution reproduced; AST2's precession
checked against the perturbative prediction; AST3's deflection angle
checked against the weak-field formula.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F92 — Relativity and cosmology: special relativity, relativistic orbits, cosmic expansion (AST10, AST4, AST5)

**Source.** Change request section 4 (A7: AST10 new in revision 2, AST4,
AST5). Slots AST10, AST4, AST5 in the `astrophysics` strand, in that
teaching order.

**Goal.** Lorentz transformations, the invariant interval, time dilation,
length contraction, relativistic energy and momentum with collision checks
and the low-velocity limit (AST10); post-Newtonian orbital precession with
its approximation stated (AST4); toy cosmological models and observable
relations (AST5).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F91.

**Acceptance criteria.** The lesson rule; AST10's invariants preserved
and the Newtonian limit recovered; AST4's precession checked against the
first-order formula; AST5's distance-redshift relation checked against
the analytic case.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F93 — Gravitational-wave chirp and exoplanet transit simulations (AST6, AST7)

**Source.** Change request section 4 (A7: AST6, AST7). Slots AST6 and
AST7 in the `astrophysics` strand; AST6 cross-links M16 (F60) and L5
(F56), which are not republished.

**Goal.** An approximate binary-inspiral waveform from a transparent
model, linked to the measured strain of M16 without repeating it (AST6);
transit flux curves, geometry, and duration effects (AST7), the simulated
counterpart of AST8.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F91, F60.

**Acceptance criteria.** The lesson rule; AST6's chirp law checked
against the closed form of `pbc.mechanics.chirp` and the page linking
M16 instead of showing the measured strain again; AST7's transit depth
and duration checked against the analytic geometry.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F94 — Materials physics: crystal lattices and phonons, electronic band structure (MAT1, MAT2)

**Source.** Change request section 4 (A8: MAT1, MAT2). Slots MAT1 and
MAT2; the first lesson feature of the `materials` course (strand
directory, `pbc.materials`).

**Goal.** Lattice dynamics and dispersion (MAT1); a transparent
tight-binding model (MAT2).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F71 (W2's modes), F89 (Q3's eigenproblems).

**Acceptance criteria.** The lesson rule; MAT1's dispersion checked
against the one-dimensional chain's closed form; MAT2's band structure
checked against the analytic tight-binding bands.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F95 — Materials physics: elasticity and deformation, defects (MAT3, MAT4)

**Source.** Change request section 4 (A8: MAT3, MAT4). Slots MAT3 and
MAT4 in the `materials` strand; MAT3 may reuse `pbc.fem`.

**Goal.** Stress, strain, boundaries, and a simple mechanical model (MAT3);
defect effects, diffusion, and the limits of the model (MAT4).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F94, F76 (optional reuse of the finite-element solver).

**Acceptance criteria.** The lesson rule; MAT3's solution checked against
the closed form of a loaded bar; MAT4's diffusion checked against T1.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F96 — Multimodal physics reasoning and interpretable explanations (AI6, AI7)

**Source.** Change request section 5 (B1: AI6 enhanced in revision 2,
AI7) and section 7.3. Slots AI6 and AI7 of the physics reasoning path;
lessons in `agents-llm` with `course: mechanics`.

**Goal.** Interpreting diagrams, plots, field images, and measured
pictures from the site's own verified figures; testing object properties,
spatial relations, and image-based counterfactual predictions against
known constraints, as still images (AI6); distinguishing prediction from
explanation, with units, physical consistency, and uncertainty as the
tests of an explanation (AI7).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F09, F46; F65 for the evaluation protocol.

**Acceptance criteria.** The lesson and agent rules; every image is a
verified figure of the site or a declared sample with rights; the model's
answers are scored against constraints the build recomputes; the page
distinguishes the model's explanation from the verified result.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F97 — Physical reasoning from video (AI8)

**Source.** Change request section 5 (B1: AI8, new in revision 2) and
section 7.3 ("Video reasoning"); requirements decision 28 and non-goals.
Slot AI8 of the physics reasoning path; lesson in `agents-llm` with
`course: mechanics`.

**Goal.** For short motion clips the repository generates from verified
simulations (a bounce, a pendulum, a collision), or approved existing clips
with recorded rights, compare the direct multimodal-model observation,
conventional tracking with derived velocity and acceleration, and
agent-assisted simulation and prediction against the independent ground
truth; report trajectory and prediction errors, false causal claims,
confidence, and the limits of frame and sample rates. No webcam, upload,
hosted processing, or build-time model call.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F96, F06; a rights record for any clip that is not
generated.

**Acceptance criteria.** The lesson and agent rules; generated clips
labelled as generated and reproduced by the build; the tracking's offline
output deterministic and compared with the ground truth by a test; clips
within the on-demand payload budget and loaded only after a user action;
no clip of a person.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F98 — Discovery under noise, hidden variables, and generalisation (D10, D11, D12)

**Source.** Change request section 5 (B2: D10, D11, D12). Slots D10 to
D12 of the law discovery path; lessons in `agents-llm` with `course:
mechanics`.

**Goal.** Noise, calibration, outliers, and failure analysis in discovery
(D10); hypotheses with latent effects, observational ambiguity, and
disambiguating experiments (D11); laws challenged on held-out settings,
force models, and conditions (D12).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F66, F81.

**Acceptance criteria.** The lesson and agent rules; the held-out worlds
of D12 never probed by the agent, shown by the trace; the baselines'
degradation under noise measured (D10).

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F99 — Discovering gravity and unknown physical worlds (D4, D5)

**Source.** Change request section 5 (B2: D4, D5). Slots D4 and D5 of the
law discovery path; lessons in `agents-llm` with `course: mechanics`
(D4) and `course: astrophysics` (D5, on the N-body worlds).

**Goal.** Inferring an unknown gravitational relation and testing its
transfer (D4); unknown forces and couplings in controlled N-body worlds
with predictive tests (D5), as original contained tasks inspired by the
published benchmarks, not their assets.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F66, F69, F91.

**Acceptance criteria.** The lesson and agent rules; the transfer test of
D4 on a world the agent never probed; the N-body truth of D5 unreachable
and the agent's predictions scored by the build.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F100 — Physics reasoning benchmarks (EV1)

**Source.** Change request section 5 (B3: EV1 enhanced in revision 2).
Slot EV1 of the agent benchmarking path; lesson in `agents-llm` with
`course: mechanics`.

**Goal.** Whether models reason about independently checked physics
problems, visual and tool affordances, and counterfactual predictions,
with tool-use reasoning separated from calling a software interface; on
problems from the site's own lessons with recomputed answers.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F96, F65.

**Acceptance criteria.** The agent rule; every problem's answer recomputed
by the build; the affordance and counterfactual items use verified figures;
the score and its uncertainty over seeds shown with the failures.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F101 — Robustness, cost, and scientific failure analysis (EV4, EV5)

**Source.** Change request section 5 (B3: EV4, EV5). Slots EV4 and EV5 of
the agent benchmarking path; lessons in `agents-llm` with `course:
mechanics`.

**Goal.** Performance against noise, budget, seeds, cost, and model choice
from recorded runs (EV4); categorised failures (wrong laws, leakage,
numerical mistakes, hallucinations, overfitting) as reproducible case
studies with independent audits (EV5).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F81, F98.

**Acceptance criteria.** The agent rule; costs and call counts recorded
from the runs that produced the fixtures and never measured in CI; each
failure case reproduced from a frozen trace with the recomputed check
that exposes it.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F102 — Atomic spectroscopy lab (Q7)

**Source.** Change request section 4 (A6: Q7). Slot Q7, a measured-data
lab of the `quantum` course; the NIST infrared spectra card is a
`survey-only` candidate.

**Goal.** Real spectral lines, calibration, and simple line and level
models with uncertainty.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F89, F51; a spike with a go decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F103 — Quantum measurement statistics lab (Q8)

**Source.** Change request section 4 (A6: Q8 enhanced in revision 2),
the second half of the linked Q5/Q8 enhancement. Slot Q8, a measured-data
lab of the `quantum` course; the Sandia gate-set tomography card is a
`survey-only` candidate, and a Bell-test count dataset is used only if a
rights-cleared, methodologically suitable one passes the gate.

**Goal.** Genuine documented quantum measurement data with uncertainties,
detector and selection caveats, and a qualified statistical
interpretation; Bell-test counts against the Q5 bounds if and only if the
gate approves a suitable dataset.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F90, F51; a spike with a go decision.

**Acceptance criteria.** The lab rule; the page states which loophole or
selection the data does not close.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F104 — Exoplanet light curves lab (AST8)

**Source.** Change request section 4 (A7: AST8). Slot AST8, a
measured-data lab of the `astrophysics` course; the TESS light-curve card
is a `survey-only` candidate.

**Goal.** Real photometry, cleaning, the AST7 model fitted, and the
uncertainties of the inferred geometry.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F93, F51; a spike with a go decision; a FITS reader
only if the go decision needs it.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F105 — Galaxy rotation curves lab (AST9)

**Source.** Change request section 4 (A7: AST9). Slot AST9, a
measured-data lab of the `astrophysics` course; no candidate card exists.

**Goal.** Real rotation curves against mass models, with the assumptions
and caveats of the inference stated.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F91, F51; a new candidate card and spike with a go
decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F106 — X-ray diffraction data lab (MAT5)

**Source.** Change request section 4 (A8: MAT5). Slot MAT5, a
measured-data lab of the `materials` course; the electron-diffraction
card is a related `survey-only` candidate and a new X-ray card may be
needed.

**Goal.** Measured peaks, lattice spacing, and uncertainty against MAT1.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F94, F51; a spike with a go decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F107 — Stress-strain measurements lab (MAT6)

**Source.** Change request section 4 (A8: MAT6). Slot MAT6, a
measured-data lab of the `materials` course; no candidate card exists.

**Goal.** Real material response, the elastic regime, hysteresis, and
uncertainty against MAT3.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F95, F51; a new candidate card and spike with a go
decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### F108 — Turbulence and flow measurements lab (FL8)

**Source.** Change request section 4 (A5: FL8). Slot FL8, a measured-data
lab of the `fluids` course; the Rostock, Sheffield, and OpenPIV cards are
`survey-only` candidates distinct from F53's cylinder wake.

**Goal.** Turbulence statistics, uncertainty, and the limited regimes of
the FL2 and FL3 models.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F79, F53, F51; a spike with a go decision.

**Acceptance criteria.** The lab rule.

**Risk.** Medium. **Detailed implementation plan expected.** Yes.

### Wave C4 — Research capstone and consolidation

Order within the wave: every lesson feature of this wave after F64 (the
gates under "Phase 4"); F109 after F19 and F39; F110 after F95, F18, and
F20; F111 last among the lessons, after F49, F101, and F98; F112 last,
after every lesson feature of the phase; it may be run earlier as a
status report that declares no completion (see its block).

### F109 — Evidence maps and reproducible literature evidence (R2, R3)

**Source.** Change request section 5 (B4: R2, R3). Slots R2 and R3 of the
autonomous research path; lessons in `agents-llm` with `course:
mechanics`. F19 delivered the evidence map page, not a lesson; R2 is the
lesson that teaches reading and auditing it.

**Goal.** Linking claims to figures, code, measurements, and limitations
through the evidence map of F19 (R2); curated source claims, methods,
citation and provenance, and reproduction feasibility through the
reference register, with no generic retrieval product (R3).

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F19, F39, F28.

**Acceptance criteria.** The lesson rule; every link rendered from the
register or the evidence map; no live retrieval; an agent that proposes
sources logs them for human review and never writes a citation.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F110 — Agent-driven materials discovery (R5)

**Source.** Change request section 5 (B4: R5 enhanced in revision 2).
Slot R5 of the autonomous research path; lesson in `agents-llm` with
`course: materials`.

**Goal.** Agents coordinating bounded, reproducible material-property
simulations of MAT1 to MAT4, comparing candidates against explicit
multi-objective physical constraints, with uncertainty and validation
discussed and a model's preference never treated as evidence.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F95, F18, F20.

**Acceptance criteria.** The lesson and agent rules; the constraint checks
recomputed by the build; the agent's ranking compared with the recomputed
one.

**Risk.** Medium. **Detailed implementation plan expected.** Yes, short.

### F111 — Autonomous physics research challenge (R6)

**Source.** Change request section 5 (B4: R6) and section 10 ("Part B
research capstone"). Slot R6 of the autonomous research path; lesson in
`agents-llm` with the primary course of the chosen unknown system.

**Goal.** From an unknown system to hypotheses, experiments,
falsification, and an audited report, with controls, honest limitations,
and an evidence trail; distinct from the subject capstones T11, EM9, and
FL10 and from F49's paper reproduction.

**Dependencies.** F61, F62, F64, F113 (the gates of this phase), F49, F101, F98, F65.

**Acceptance criteria.** The lesson and agent rules; the report's claims
typed and each recomputed or marked; the audit by the F18 reviewers shown
with recomputed checks; the hidden truth revealed only after the audit on
the page.

**Risk.** High (scope). **Detailed implementation plan expected.** Yes,
likely several Issues.

### F112 — Curriculum completion audit

**Source.** Change request section 11 ("Curriculum completion") and
section 10 (Wave 4, "quality consolidation"); requirements "Project goal"
(the long-term target).

**Goal.** Establish whether the published inventory reconciles to the
reference curriculum, and say so without rounding. The audit classifies
every one of the 115 slots as one of: filled by a substantive published
lesson (the definition of done of section 11); a designated lab whose
dataset gate recorded defer or reject, with its dossier (requirements
decision 27: a lab is a target that the gate decides); a slot the human
removed from the reference structure by a recorded decision that changed
the curriculum file and the requirements' decision 23 (none exists
today); or outstanding. A slot whose feature was not scheduled, not
started, or not finished is outstanding, never deferred: the audit
reports what is missing and makes no scope decision. Completion
(requirements "Project goal"; change request section 11) is declared
only when no slot is outstanding; otherwise the audit is a status report
that lists the outstanding slots with their features. The audit also
establishes: eight courses navigable; sixteen designated labs, with the
gated ones' outcomes recorded and qualified separately from the core
slots; the four paths with valid lessons; the eleven revision-2 and
revision-3 additions and the seven enhancements present and
non-duplicative; a reproducibility audit of a sample of lessons across
courses from a fresh clone; a screen-reader pass of the path and a lesson
of each course; no published address broken.

**Dependencies.** F64 and every lesson feature of this phase (F66 to
F111, and F45, F49, F52, F53, F54, and F55 of the previous phase, which
fill slots). The audit may be run earlier as a status report; such a run
declares no completion.

**Acceptance criteria.** The audit recorded in `docs/release-readiness.md`
with the slot table of this roadmap updated; a test that every slot of
the curriculum file is classified as filled, gated (with the dossier that
records the gate's decision), removed by a recorded decision, or
outstanding, that the four classes add up to 115, and that "complete" is
written only when the outstanding class is empty; the gated labs listed
apart from the core slots with their dossiers; the sampled reproductions
byte-identical at displayed precision; the manual passes recorded.

**Risk.** Low. **Detailed implementation plan expected.** No.

## Phase 5 — Four workstreams (change cycle `pbc-planning-change-four-workstreams`)

Every feature in this phase comes from
`docs/changes/pbc-planning-change-four-workstreams.md` (2026-10-14) and
the requirements re-approved with it on 2026-10-15 (decisions 32 to 35).
The four changes are independent workstreams, with one stated
exception: the switch of F117 that adds the experiment check to the
full-run `build` job waits for the owner's interim full-run timeout
(unresolved question 10, on F118's record) or for F119's consolidation,
because that job is the one the full-run gate of Phase 4 protects. Each
block names its change. What they inherit from Phase 4 without repeating it: the
invariants of `docs/architecture.md`, the definition of done of a lesson
(for the editorial pilot, with the technical content fixed), the risk
levels of `.agents/policies/autonomy.md`, and the rule that a feature that
changes CI, workflow permissions, a protected script, or the merge gate is
High and needs the owner's explicit approval. Change 3 (the 20-minute
budget, ADR 015) is no feature; its amendments are in the blocks of F61
and F113, the wave tables, and the architecture.

Two coordination rules of this phase:

- **No verification feature shares a pull request or a worktree with the
  editorial pilot** (change request, "Non-goals and guardrails").
- **F117 and F115 touch the same five lesson pages** (the footer cell and
  the prose of mechanics 01 to 05). Their plans sequence the lessons or
  rebase; neither changes a scientific claim, a computed number, a figure,
  or a verified artifact, and the checks prove it on every pull request.

### Workstream 1 — Editorial voice (change 1, requirements decision 32)

Order: F114, then F115 lesson by lesson with the human's approval of the
pilot recorded on its Issue, then F116. Expansion of the voice beyond the
five pilot lessons is not a feature of this roadmap: it needs the human's
explicit review and approval after F115, and is then planned as its own
feature or features.

### F114 — Editorial voice: the style guide with before-and-after examples

**Source.** Change 1, proposal F1 and acceptance criteria 1, 2, and 7;
requirements decision 32 and "UX expectations" (editorial voice);
non-goals ("No editorial voice imposed as a uniform register").

**Problem.** The editorial standard of Phase 3 (F28 to F31) gave every
lesson depth, typed claims, interpreted figures, computed numbers, limits,
a self-check, and curated references, and the lessons are correct and
reproducible. They still read like specifications: openings that state
the technique instead of the question, repeated framing sentences,
defensive wording around every result, sentence after sentence of the
same shape, and conclusions that report a number without saying what it
means. The project has no document that says what its prose should sound
like, and nothing to measure a draft against except the structural
checks.

**Goal.** A documented, reusable editorial style guide that combines the
curiosity and accessibility of a personal technical blog, the rigour of a
university textbook, and this project's verification standards, with
concrete before-and-after examples, and that changes nothing of what a
lesson claims or verifies.

**User-visible outcome.** None on the site in this feature. A lesson
author, a reviewer, and an agent drafting a lesson have one guide that
shows, with examples, how a lesson opens, builds intuition, derives,
experiments, interprets, moves between parts, and concludes, and what to
remove.

**In scope.**

- One guide in the docs directory, named by the feature (this roadmap
  calls it the editorial voice guide), with: the objective and the
  non-goals of requirements decision 32; principles for lesson openings,
  intuition, mathematical derivations, computational experiments, the
  interpretation of results, transitions, and conclusions; for each, at
  least two before-and-after examples drawn from existing lessons (the
  lesson and section named, the "after" written for the example only and
  not applied to the lesson) and examples of the intended register from at
  least three of the author's earlier articles at ataspinar.com, each
  named, quoted or paraphrased within fair use, and chosen for a quality
  the lesson lacks; the recurring faults with a way to spot each
  (boilerplate introductions, repetition, needlessly defensive wording,
  monotonous sentence structure, conclusions that do not interpret);
  what stays fixed (the format-2 sections and identifiers, claim types
  and evidence, figure status, computed numbers, the reference register,
  every check of `docs/authoring.md`); and the statement that structures
  and narratives vary by subject and that no identical template is
  imposed.
- A draft editorial review checklist in the guide for F115's reviews:
  specific weaknesses with their evidence and an actionable change, never
  a score alone; F116 makes it the rubric.
- A short audit, in the guide, of the openings and conclusions of the
  five pilot lessons and of one lesson of each other strand, as the
  evidence the principles answer.
- One link from `docs/authoring.md` to the guide; the integration proper
  is F116.

**Out of scope.** Editing any lesson (F115); the template and the rubric
in the review workflow (F116); an additional agent or a mandatory
narrative template; any optimisation against AI-content detectors; jokes
or anecdotes as a rule.

**Dependencies.** F28, F29, F30, F31 (the editorial standard the voice
builds on; their lessons supply the examples).

**Acceptance criteria.**

1. The guide exists, is reachable from `docs/authoring.md`, and covers
   the seven parts of a lesson named above with principles for each.
2. Each part has at least two before-and-after examples from existing
   lessons, each naming the lesson and section, and the guide names at
   least three earlier articles with what each demonstrates.
3. The recurring faults are named, each with a way to detect it in a
   draft, and the guide states what never changes for style (identifiers,
   claims, numbers, figures, references, checks) and the non-goals of
   decision 32.
4. The draft review checklist asks for named weaknesses, evidence, and an
   action, and has no numerical score as its result.
5. `./scripts/verify.sh` passes (the documentation checks read the new
   file); no lesson, template, or check changed.
6. An independent editorial review of the guide by a reviewer who did not
   write it is recorded on the pull request, with the findings resolved
   or recorded.

**Risk.** Low.

**Detailed implementation plan expected.** No; the block is the plan. The
feature records which articles and lessons it used.

### F115 — Editorial pilot on mechanics lessons 01 to 05, with the human approval gate

**Source.** Change 1, proposal F2 and acceptance criteria 3 to 7 and 9;
requirements decision 32 ("a pilot on mechanics lessons 01 to 05 ...
expanded beyond the pilot only after explicit human review and
approval").

**Problem.** A style guide is a claim until it has been applied; the five
introductory mechanics lessons (M1 to M5, migrated to format 2 by F28,
F29, and F30 and the first thing a learner reads) are where it is proven
or corrected, before any other lesson is touched.

**Goal.** Apply the guide of F114 to mechanics lessons 01 to 05 by
targeted editorial changes to their prose, review each lesson on its own
and the five as a connected sequence, record what worked, what did not,
and what the guide must change, and stop at the human's approval gate.

**User-visible outcome.** The five lessons read as one curious, rigorous
author wrote them: each opens with its question, interprets its results,
and leads into the next; every number, figure, claim, code excerpt, and
command on them is exactly what it was.

**In scope.**

- Per lesson, one reviewed pull request (or one per pair, the human's
  choice on the Issue): edits to prose cells, captions, alt text, and
  exercise wording under the guide; no change to executed code, inline
  expressions, front matter, claims and their evidence, figure status,
  references, or the footer. The pull request's evidence shows the diff
  is prose only: the executed cells and the front matter are
  byte-identical before and after (a diff over the cells, recorded), and
  every check passes, including the reproduction of the page byte for
  byte, so the figures and numbers are unchanged.
- The review of each lesson by a reviewer who did not edit it, with the
  checklist of F114: named weaknesses, evidence, action, and the physics
  reviewer's confirmation that no scientific statement changed in meaning
  (independent scientific review, as every lesson feature).
- The sequence review: the five lessons read in order once all are
  edited, for the transitions between lessons, the repetition across
  them, and the distinct structure each keeps for its subject; recorded.
- The pilot record, as a section of the guide or a file beside it: the
  changes that worked, the ones that did not and were reverted, and the
  adjustments made to the guide; the guide is amended in this feature.
- The approval gate: the human's explicit approval of the pilot recorded
  on the Issue of F115 before any lesson outside the five is edited under
  the guide. The feature creates no expansion feature and edits no sixth
  lesson.

**Out of scope.** Any lesson other than mechanics 01 to 05; wholesale
regeneration; changes to code, numbers, figures, claims, references, or
section identifiers; diagrams (F32 delivered them; their alt text may be
edited as prose); the expansion of the voice to the curriculum.

**Dependencies.** F114; F29 and F30 (the five lessons in format 2); F32
(their diagrams).

**Acceptance criteria.**

1. Mechanics lessons 01 to 05 are edited by targeted changes; for each,
   the recorded diff touches prose, captions, alt text, and exercise
   wording only, and the executed cells and front matter are
   byte-identical before and after.
2. Every existing check passes on each pull request, and the page
   reproduction (or, after F117, the experiment check) shows the figures
   and numbers unchanged; no scientific claim, result, formula, or
   verified artifact changed.
3. Each lesson has an independent editorial review with named
   weaknesses, evidence, and actions, and an independent scientific
   confirmation, recorded on its pull request.
4. The sequence review of the five is recorded, and it shows that the
   lessons keep structures and narratives appropriate to their subjects
   rather than one pattern.
5. The pilot record lists successful changes, unsuccessful changes, and
   the adjustments made to the guide, and the guide carries them.
6. The human's approval of the pilot is recorded on the Issue; until it
   is, no other lesson is edited under the guide, and the feature creates
   no expansion work.

**Risk.** Medium: prose of published scientific lessons, with independent
editorial and scientific review per lesson.

**Detailed implementation plan expected.** Yes: the per-lesson protocol,
the diff evidence, and the order relative to F117 on the same files.

### F116 — Editorial principles in the authoring guide, the lesson template, and the review rubric

**Source.** Change 1, proposal F3 and acceptance criteria 7 and 8;
requirements decision 32 ("future lessons inherit the voice through the
normal authoring workflow").

**Problem.** After the pilot the principles live in a guide that nothing
requires a lesson author, an agent, or a reviewer to read. The template
still shows the register of format 2 alone, and a lesson review has no
editorial part.

**Goal.** The approved principles, as adjusted by the pilot, become part
of `docs/authoring.md`, of the prose placeholders of
`docs/lesson-template.qmd`, and of the lesson review as a qualitative
rubric, without a rigid narrative template and without a new agent.

**User-visible outcome.** None directly; the next lesson a feature
publishes opens, interprets, and concludes in the project's voice because
its author and reviewer followed the normal workflow.

**In scope.**

- `docs/authoring.md`: an editorial section with the essentials of the
  guide, a link to it, and the editorial step in "Check it" (read the
  draft against the faults list) beside the structural checks.
- `docs/lesson-template.qmd`: prose placeholders and comments that show
  the voice at the opening, the interpretation of a result, the
  transitions, and the conclusion, while the section identifiers, cells,
  and checks of the template stay as they are (the template test still
  passes); the placeholders say that structure varies by subject.
- The editorial review rubric: the checklist of F114 as adjusted by F115,
  in the lesson review guidance of `docs/authoring.md` and named where
  the review workflow describes a lesson review, requiring named
  weaknesses with evidence and an action and giving no score as a
  verdict; the record format of a review.
- The next lesson feature's review record is the first use; the feature
  may demonstrate the rubric on a lesson drafted from the template in a
  dry run that is not merged.

**Out of scope.** Editing published lessons; expanding the pilot; a
mandatory additional agent; a narrative template that every lesson must
follow; changes to checks, identifiers, or verification.

**Dependencies.** F115 (the pilot approved by the human).

**Acceptance criteria.**

1. `docs/authoring.md` carries the principles and links the guide; the
   authoring checks of a lesson include the editorial step.
2. `docs/lesson-template.qmd` reflects the voice in its prose placeholders,
   keeps every section identifier and cell, and a lesson made from it
   passes the lesson checks (the template test).
3. The rubric exists, is required by the lesson review guidance, asks for
   weaknesses, evidence, and actions, and produces no numerical score as
   its result.
4. The guide and the rubric say that structures vary by subject, and no
   new agent, workflow step that calls a model, or mandatory narrative
   template was added.
5. `./scripts/verify.sh` passes; no check, identifier, or verification
   guarantee changed.

**Risk.** Low.

**Detailed implementation plan expected.** No.

### Workstream 2 — Learner instructions without a website build (change 2, requirements decision 33, ADR 016)

### F117 — "Run this experiment": learner instructions without a website build

**Source.** Change 2 (all of it); requirements decision 33, "UX
expectations" ("Run this experiment" section and learner setup), "Runtime
and deployment constraints" (reproducibility), non-goals (no instruction
to rebuild or preview, no relocation); ADR 016, proposed with this
planning and accepted when it is approved.

**Problem.** Every published instruction to a reader ends in rendering the
site: the setup page's required setup is CI's setup, the footer of every
lesson ends with `quarto render`, the README's one command is
`./scripts/verify.sh`, and the development and authoring guides say
"preview the site". No lesson has a runnable experiment outside its page,
because every figure and table is computed in the page's cells. A reader
who wants to run and modify an experiment is told to install Lean, jq, a
browser, and Quarto.

**Goal.** Implement ADR 016: every lesson declares a tested experiment
entry point that regenerates its results and figures without HTML; the
footer names the activity and lists its commands; the setup page is
organised by activity with the Python-only path first and the Lean and
agent paths separate; the experiment commands are verified; every
instruction to rebuild or preview the website leaves the maintained
documentation and is not relocated; everything internal keeps running.

**User-visible outcome.** A reader clones the repository, runs
`uv sync --locked --no-dev`, and runs the one experiment command of a
lesson; the figures and numbers of the page appear in a directory of
their choosing, and they can change the code and run it again. The
environment they installed holds the project's dependencies and nothing
of the site toolchain. A Lean reader additionally installs elan and
checks the proofs. Nobody is told to install a browser, jq, or Quarto, or
to build the site.

**In scope.**

- **The entry-point contract** (ADR 016 decision 2), fixed once: where an
  entry point lives (the entry point and the figure-writing functions
  below are modules of the lesson's course package under `src/pbc`,
  imported by the page's cells; the lesson directory holds at most a thin
  runner that imports them and holds no scientific logic). This is the
  one location the digest as implemented follows: ADR 014 decision 1 and
  `src/pbc/authoring/digest.py` follow the imports of the page's cells
  transitively through `pbc` modules only, and a module in the lesson
  directory is hashed as content without its own imports being followed,
  so a `src/pbc` module imported only by such a module would be outside
  the digest and a change to it would not select the lesson. If F117
  prefers the lesson directory for the entry point itself, it first
  extends the digest to follow the imports of a module in the lesson
  directory, with a test that a changed `pbc` module imported only by the
  entry point changes the lesson's digest, before any lesson is migrated.
  The contract also fixes how the entry point is
  run (one command, `uv run --locked --no-dev`, an output directory
  argument), what it writes (the figure files of the page and a results
  file with the numbers the page shows, at displayed precision), and how
  the page's cells call the same functions so that no scientific logic
  exists twice. **One figure-writing function per figure** (ADR 016
  decision 2): today every lesson figure is emitted by `plt.show()` in a
  cell and captured by the Jupyter inline backend into
  `index_files/figure-html`, and no helper writes a figure file, so a
  `savefig` in an entry point and the backend's capture need not agree
  byte for byte (bounding box, dpi, metadata). The contract gives every
  figure one function in the lesson's course-package module under
  `src/pbc` (the location fixed above), with fixed Matplotlib
  settings and no metadata, that the entry point calls to write the file
  into the output directory and that the page's cell calls at build time
  to write the same file and show it as the cell's output, so that the
  figure file of the built page holds the writer's bytes; the display
  form of ADR 002 (a figure is produced by an executed cell during the
  build, no image file is committed) and the preview lookup of F63 are
  kept. The contract names the fallback for a figure kind that cannot
  reach byte identity across the two paths: an image comparison at the
  page's rendered size plus the numbers at displayed precision, recorded
  as a documented difference per figure kind in the feature's record;
  the first migrated lesson of each figure kind verifies which applies.
  The learner's environment is the project's dependencies
  alone: `uv sync --locked --no-dev` installs them and nothing of the
  `dev` group (Quarto, the Jupyter kernel, Playwright, the accessibility
  scan, pytest, ruff), as ADR 016 decision 2 decides; a lesson kind that
  needs more than the project's dependencies gets a declared learner
  dependency group or extra, named by its footer, as the `openai` extra
  serves the live agent run, decided once in this contract. The
  contract also fixes the environment of the experiment check (ADR 016
  decision 4): one learner environment per verification run, created
  with `uv sync --locked --no-dev` in the fresh clone outside the
  per-lesson budget, against which every selected lesson's entry point
  runs without a further sync (`uv run --no-sync` or the equivalent),
  and never the checkout's environment, which `uv run --no-dev` would
  strip of the `dev` group (Quarto, pytest, Playwright) while the
  verification runs; the assertion that the learner's environment holds
  nothing of the `dev` group belongs to the setup-page test, not to the
  experiment check. The lesson
  source checks require an entry point once the switch below is made; a
  unit test per entry point. **The Lean kind** is the one exception to
  the location rule, fixed in this contract as ADR 016 decision 2 fixes
  it: for a lesson whose methods are Lean only, the entry point is the
  proof check (`./scripts/check-lean.sh`, or `lake build` of the lesson's
  modules), a shell script and not a `src/pbc` module; its digest inputs
  are the displayed Lean modules (`lean-modules`), the toolchain, and the
  manifest that ADR 014 decision 1 and `src/pbc/authoring/digest.py`
  already follow; its test is the Lean build together with the exercise
  pairing check of ADR 011 decision 3, and no separate unit test is
  written for it; the lesson source check accepts that declaration for
  such a lesson. A Lean lesson that also computes a figure additionally
  declares the figure-writing function under `src/pbc`, with its unit
  test, as every other kind does.
- **The entry points of the thirty-two published lessons**, in reviewed
  steps per strand, behind the unchanged footer: the figure and table
  code moves from the cells into the entry point's functions, the cells
  call them, and the page's text and numbers stay identical (the
  determinism and reproduction checks pass on every step); a figure that
  moves from the inline backend's capture to its figure-writing function
  is re-encoded once by the writer, which changes the bytes of its file
  and not its content, and the pull request of that step shows the figure
  unchanged by an image comparison at the page's rendered size. For an
  agent lesson the
  entry point replays the recorded run without credentials; the live run
  is a separate documented command behind the optional dependency and
  the credential. For a Lean lesson the entry point is the proof check
  (`./scripts/check-lean.sh`, or `lake build` of the lesson's modules),
  under the Lean rule of the contract above, and, where the page computes
  a figure, the figure's function under `src/pbc`.
- **The switch**: the footer's heading and content by lesson kind ("Run
  this experiment", "Replay this experiment", "Check this proof"), the
  identifier `reproduce-this` kept, the commands from the clone to the
  entry point with the commit, the files, and what is regenerated, and no
  render or preview command; `reproduce_this()` (or its successor, the
  name is the feature's) builds it through the post-render step of ADR
  014 decision 9 as today.
- **The experiment check** (ADR 016 decision 4): in a fresh clone, in
  the one learner environment per run of the contract above, the entry
  point's command regenerates the figure files byte for byte (the one
  figure-writing function of the contract produces both sides; a figure
  kind the feature's record documents as unable to reach byte identity
  is compared as an image at the page's rendered size) and the
  numbers at displayed precision, within the 30-second budget of the
  lesson; a failing or missing entry point fails `verify`. It follows
  the selection rule of the page reproduction (ADR 014 decision 3,
  invariant I26): every lesson on a full run and on a run without
  options, the lessons the run executed on a selective run, read from
  the selection file `./scripts/verify.sh` writes, as the check
  `site-checks-reproduction` reads it. It joins the group `build` of
  `scripts/verify.conf`, the same-machine group of ADR 012 decision 4,
  as tests marked `same_machine` inside the existing check
  `site-checks-reproduction` (the one route: that check holds exactly
  the tests marked `same_machine` under `tests/e2e`, and
  `tests/integration/test_site_check_division.py` requires every test of
  `tests/e2e` to be run by exactly one `site-checks-*` check and admits
  no new check name, so a second check of the group would run the tests
  twice or fail the division test), and declares no new group and no new
  check (every group is run by exactly one job, ADR 012 decision 2; the
  check of the group `build` holds exactly the tests marked
  `same_machine`, ADR 012 decision 4), so that every comparison
  is against figures and numbers this run computed on the machine of
  the comparison and never against a result of the base; the entry
  point is in the lesson's digest, so a changed entry point selects its
  lesson. The page reproduction and every other internal check stay in
  `scripts/verify.conf`; the feature removes no check and leaves the
  check identity's inputs as they are, apart from the tests it changes.
- **The cost of the check on the full-run `build` job, and the gate of
  the switch** (ADR 016, "Consequences"). On a full run the check is a
  fifth execution of every lesson's science in the `build` job, beside
  the site build, the determinism build, the preview test's build, and
  the page reproduction, all of which stay until F118 rules. Expected
  cost, derived and not measured: the page reproduction of thirty-two
  lessons took about 11 min 13 s in one fast full run (change request),
  execution and render together; the check repeats the execution and
  not the render, so it adds at most that much to a `build` job measured
  at 21 min 07 s to 31 min 15 s with thirty-two lessons ("The full run
  on `main` at the current lesson count"), against the 35-minute
  planning budget of ADR 014 decision 7 and the 45-minute timeout; on
  the slower measured runs the sum can exceed the planning budget, and
  a `build` job that exceeds the timeout publishes nothing (invariant
  I26). The entry points, their unit tests, the setup page, and the
  documents are delivered first, behind the unchanged footer; the switch
  (the footer's heading and content, the lesson source check that
  requires an entry point, and the entry of the experiment check in
  `scripts/verify.conf`) is made only after the owner's interim full-run
  timeout is recorded (unresolved question 10, from F118's record, as a
  status line of ADR 014) or after F119's consolidation has removed
  what F118 showed redundant, whichever comes first, and the first full
  run on `main` after the switch is measured against the approved
  timeout. Whether the check replaces the render step of the page
  reproduction is F118's coverage question, not this feature's.
- **The setup page** (`site/reproduce.qmd`, kept at its address or
  redirected, with every existing link valid): three activities, with the
  Python-only required setup (Git and uv), the experiment commands and
  their pattern, the optional Lean setup and proof checking clearly
  separate, the agent replay distinguished from a live call that names
  its credential and dependency, and a troubleshooting table for those
  paths; the test of the page performs the Python-only commands from the
  page's text in a fresh clone, asserts that the environment they
  produced holds no package of the `dev` group, runs at least one
  experiment of each non-Lean lesson kind in that environment to
  completion, and keeps the optional commands marked; the equality with
  `ci.yml` is dropped (ADR 016 decision 5).
- **The documents**: `README.md` ("Build and verify" becomes "Run an
  experiment" with a reference to the setup page, and the verification
  command named as what CI runs), the project part of `CONTRIBUTING.md`,
  `docs/development.md` (the preview walkthrough removed; the
  verification section kept as the technical reference of what
  `./scripts/verify.sh` verifies and CI runs, phrased as the maintainers'
  and agents' contract and not as a way to read the site), `docs/authoring.md`
  ("Check it" lists the unit tests, the lesson checks, and the lesson's
  experiment; how to write the entry point; the footer section rewritten),
  `docs/lesson-template.qmd` (the footer cell), `site/contribute.qmd`,
  `site/index.qmd` (the "Source and licence" sentence, which sends every
  visitor to "rebuild everything on your own machine", reworded around
  running an experiment with the reference to the setup page kept), the
  instructor packs under `docs/instructor-packs/` (the F59 pack's "Pathway
  without AI" names the lesson's "Reproduce this" section, a heading the
  switch renames; the sentence is in the hand-written part of the pack,
  outside the block `pbc.authoring.educators` writes, so the pack is
  edited and any later pack follows the new heading), and
  `docs/project-map.md` for any new file; a test over the maintained
  guides, the home page, the instructor packs, and the generated footers
  that their instructional command blocks and imperative setup and footer
  sections (the setup page's command blocks, the README's run section,
  the generated footers, the instructor pack's pathway, the place of the
  removed preview walkthrough) contain no render or preview command and
  that none names the superseded footer heading; a technical reference
  that names in prose what `scripts/build-site.sh` or CI runs (the
  verification section of `docs/development.md`, requirements decision
  33) is not an instruction and is not what the test forbids. Historical records (ADRs,
  completion records, `docs/release-readiness.md`, plans) are not
  rewritten; ADR 002's superseded consequence is marked in its status by
  this planning.
- `docs/architecture.md` ("Learner runs an experiment", "Inside one
  verification run" step 7) updated; the status of ADR 016 records the
  delivery.

**Out of scope.** Changing any scientific logic, result, figure, or claim
(the checks prove it); removing or consolidating an internal check (F118,
F119); the agents' local verification obligations (F119); the editorial
voice (F114 to F116); Windows; notebooks as sources.

**Dependencies.** F39 (the setup page and its test), F40 (the footer), F61
(the post-render context and the digest the entry point joins: the
selection, base, and regenerated context delivered by pull requests #152
to #166, not the closure of Issue #147); for the
switch only, the owner's interim full-run timeout under unresolved
question 10 (recorded from F118's record) or F119's consolidation,
whichever comes first.

**Acceptance criteria.**

1. No maintained user, contributor, development, or authoring guide, the
   home page, no instructor pack, and no generated footer instructs a
   reader to rebuild or preview the website locally, and none names the
   superseded footer heading; a test over the named files (the guides,
   `site/index.qmd`, `docs/instructor-packs/`, and the generated footers)
   shows it; the instructions were removed, not relocated (reviewed). The test asserts
   that the instructional command blocks and the imperative setup and
   footer sections (the setup page's command blocks, the README's run
   section, the generated footers, the instructor pack's pathway, and the
   place of the removed preview walkthrough in `docs/development.md`)
   contain no render or preview command (`quarto preview`,
   `quarto render`, `./scripts/build-site.sh`, or an imperative sentence
   that tells the reader to render or preview the site); a technical
   reference that names such a command in prose as what
   `./scripts/verify.sh` or CI runs (the verification section of
   `docs/development.md`, requirements decision 33) is permitted and the
   test does not forbid it; the full `./scripts/verify.sh` run that ADR 017
   decision 7 and F119 require of an agent or developer for the listed
   change types is the local site render the requirements' runtime
   constraints permit and is not such an instruction (ADR 016 decision
   1).
2. Every published lesson's footer gives its experiment commands with no
   render command, under the heading of its kind, with the identifier
   `reproduce-this` kept; every lesson declares an entry point with a
   unit test (for a lesson whose methods are Lean only, the proof check
   is the entry point and the Lean build with the exercise pairing check
   of ADR 011 is its test, as the contract fixes); a lesson without one
   fails the lesson checks.
3. The Python-only path needs Git, uv, and the project's locked
   dependencies and nothing else: the setup page's install command and
   every footer's commands carry `--no-dev` (or the learner group the
   contract declares) and reference no elan, Mathlib, browser, jq,
   workflow tool, or LLM credential; a test performs the page's
   Python-only commands in a fresh clone, asserts that the installed
   environment holds no Quarto, Jupyter kernel, browser, accessibility,
   workflow, or quality package, and runs one experiment of each
   non-Lean lesson kind to completion in it.
4. A Lean reader checks proofs and works on the exercises of
   `lean/04-lean-exercises-on-your-machine` with the Lean setup the page
   gives, without a website build; the Lean block is marked optional and
   separate.
5. The experiment check runs a lesson's entry point in a fresh clone with
   the learner's commands and compares its figure files byte for byte
   (through the one figure-writing function per figure of the contract;
   for a figure kind the feature's record documents as unable to reach
   byte identity, as an image at the page's rendered size) and its
   numbers at displayed precision, against what this run computed on the
   same machine, within 30 seconds: for every lesson on a full run and on
   a run without options, and for the selected lessons only on a
   selective run (a test that a run with a base checks the experiments of
   the lessons it executed and of no other); a changed result, a changed
   entry point, and a missing entry point each fail `verify`, a test per
   case.
6. No entry left `scripts/verify.conf`; the site build, the determinism
   check, the page reproduction, the deployment of the verified artifact,
   the provenance region, the accessibility scan, and the dataset and
   lesson checks pass unchanged; ADR 016's status records the delivery.
7. `README.md`, the setup page, the footer generator, the template, the
   guides, and the tests say the same thing; a reviewer who did not write
   the page follows it on a clean machine for one simulation lesson, one
   agent lesson (replay), and one Lean lesson, recorded on the pull
   request.
8. The switch was made only after the owner's interim full-run timeout
   was recorded or F119's consolidation was merged, and the pull request
   of the switch names which; one full run on `main` after the switch is
   measured against the approved timeout (its `build` job, with the run
   identifier and cache state) and recorded in
   `docs/release-readiness.md`, together with the executions per lesson
   in a full run before and after the switch.

**Risk.** Medium: every lesson page's cells move code into an entry point,
and the proof that nothing scientific changed is the unchanged text and
numbers of the page on every step with the determinism and reproduction
checks passing, and an image comparison at the rendered size for a figure
the step re-encodes; whether every figure kind reaches byte identity
between the entry point and the page is verified on the first migrated
lesson of each kind, with the documented image comparison as the fallback
(ADR 016 decision 2); the changed tests make every pull request of the feature a
full run; the switch adds an execution of every lesson to the full-run
`build` job, which is why it is gated on the approved timeout or on
F119's consolidation (criterion 8); independent review per step.

**Detailed implementation plan expected.** Yes: the contract, the order
of the strands, and the sequencing with F115 on mechanics 01 to 05.

### Workstream 3 — Verification simplification (change 4, requirements decision 35, ADR 017 proposed)

Order: F118 first; F119 and F120 after it in parallel worktrees; F121 only
if the owner accepts ADR 017. F118 is also what the amended full-run gate
of Phase 4 waits for: its measurement record is the basis of the owner's
interim decision under unresolved question 10. None of these features is
combined with the editorial pilot. Issue #150 (F113) is not touched by
F118, F119, or F120; F121 closes it non-destructively on acceptance, and
the owner decides on rejection.

### F118 — Verification audit and the record of the full run

**Source.** Change 4, "C" and "B", "Required evidence and staged
acceptance" items 5, 6, and 7, and "Why this is necessary"; requirements
decision 35 and unresolved question 10; ADR 017 (context, and decisions 7
and 8 as the proposals it tests).

**Problem.** Before a check is removed, a job divided, or an agent's
obligation lifted, the facts have to be on the table: what a full run
executes and compares and how often, whether the preview test's third
build duplicates the determinism build, which inputs of the check
identity affect what, where the `integration` job's time goes, which
local full-site builds the agent workflow demands, and what a full run
costs at the current lesson count with the cache state known. Today those
facts are spread over scripts, tests, prompts, and Actions logs, and the
roadmap's full-run gate is reached without the projection F61 and F113
were to record.

**Goal.** One audit record with coverage evidence per candidate removal,
the measured full run and one-lesson pull request decomposed into fixed
and lesson-dependent cost, and the proposal for the owner's interim
full-run gate; no change to CI, checks, or scripts.

**User-visible outcome.** None on the site. The owner receives a short,
evidenced proposal for the full-run timeout and the lesson count it
covers; F119 and F120 receive their evidence.

**In scope.**

- **The call graph of verification**, per check of the group `build` and
  of the `e2e` groups, in a full run and in a selective run: which build
  it performs, which lessons it executes, which bytes it compares with
  which, from `scripts/verify.conf`, `scripts/build-site.sh`,
  `scripts/check-determinism.sh`, `tests/support/second_build.py`, and
  the tests of `tests/e2e`; with the measured duration of each step from
  the logs of the runs named under "State at the change cycle
  `pbc-planning-change-four-workstreams`".
- **The redundancy verdict** on `test_a_second_build_gives_byte_identical_previews`
  against `scripts/check-determinism.sh`: the state each build starts
  from, the selection each honours, the files each compares, and the
  failure modes each catches; the verdict "duplicate with identical
  coverage" or "covers X that determinism does not", and in the first
  case the regression test F119 must add (a differing preview still fails
  `verify`).
- **The validity domains of the check identity**: each input of
  `check_identity` (the digest module of the authoring package) classified
  by what it affects (scientific execution, rendered output, the
  verification rule, the browser tooling), which domains could be split
  with a complete-input test and which cannot; the rule that an
  unclassified input belongs to every domain (ADR 014 decision 10).
- **The `integration` critical path**: the tests of `tests/integration`
  by duration and by what they need (the Lean packages, the browser, a
  Quarto build), a division into independent parts that runs every test
  exactly once, and what it would shorten; whether lesson reproductions
  could run in parallel is assessed from per-lesson execution budgets and
  resource contention, and `pytest-xdist` is not assumed.
- **The inventory of local build obligations** in `AGENTS.md`'s definition
  of done, `.agents/prompts/implementer.md`, the other prompts and
  policies, `scripts/finish-feature.sh` and `scripts/review-feature.sh`,
  the plans, the skills, and `docs/development.md`: each blanket demand
  to run everything, the targeted checks that would replace it, and the
  change types that still need a local page or site render (ADR 017
  decision 7); CI stays the publication gate.
- **The measurements**, recorded in `docs/release-readiness.md` with run
  identifiers: the `build` job of the full runs at 28 and 32 lessons with
  their cache state read from the logs; the one-lesson pull requests of
  F61 decomposed into runner preparation, `integration`, and
  lesson-dependent time; the growth per lesson between 22, 28, and 32
  lessons with its uncertainty; the full-run fallback at representative
  larger counts, labelled as projections; every number against the
  20-minute budget and the 15-minute target of ADR 015.
- **The proposal for the owner** (unresolved question 10): the timeout of
  the one `build` job of a full run and the lesson count it is approved
  for, with the growth per lesson stated, as the fallback of ADR 014
  decision 11 requires; posted on the Issue; the owner's decision is
  recorded as a status line of ADR 014 (an ADR change needs the owner's
  merge approval) and restates the full-run gate of Phase 4 for the
  lesson features.

**Out of scope.** Removing, dividing, or changing any check, job, script,
or prompt (F119); the same-commit comparison and the chain design (F120);
changing the timeout (the owner's decision, applied by whichever feature
the owner names); a scheduled audit.

**Dependencies.** F61 (the selection and the base the audit reads: the
delivered selection, base, and regenerated context of pull requests #152
to #166, not the closure of Issue #147, whose criterion 9 is recorded by
this feature).

**Acceptance criteria.**

1. The call-graph record names, per check, the builds, the executions per
   lesson, and the bytes compared, with measured durations from named
   runs; the number of executions of a lesson in a full run is stated.
2. The redundancy verdict on the preview test is given with the evidence
   from the code and, if it is a duplicate, the regression test F119 adds;
   if not, what it covers that the determinism check does not.
3. Every input of the check identity is classified; the inputs that cannot
   be classified are named as belonging to every domain; the splittable
   domains, if any, come with the completeness test they need.
4. The `integration` division is proposed with per-test durations and
   dependencies and a test that every test runs once; the parallel
   reproduction question is answered from budgets and contention, not
   assumed.
5. The inventory of local full-site build obligations is a table with the
   replacing targeted checks and the change types that keep a local
   render.
6. The full-run and pull-request measurements are recorded in
   `docs/release-readiness.md` with run identifiers and cache state,
   decomposed as above, projections labelled, and judged against ADR 015;
   the proposal of the timeout and the covered lesson count is on the
   Issue for the owner.

**Risk.** Low: documents, measurements, and tests that assert the audit's
facts; no CI change.

**Detailed implementation plan expected.** Yes, short.

### F119 — Remove redundant verification and blanket local build obligations

**Source.** Change 4, "C", "Required evidence and staged acceptance" items
5 and 6; requirements decision 35 and "Runtime and deployment
constraints" (agents' local verification proportional to the change);
ADR 017 decisions 7 and 8, which do not depend on incremental `main` and
which the owner may accept on F118's evidence.

**Problem.** The `build` job executes every lesson more often than its
guarantee needs if F118 confirms the duplicate, the `integration` job is
the longest fixed job on the longest path of a one-lesson pull request,
a change to any integration test turns every pull request into a full
run, and every agent finishes a feature by rebuilding the whole site
locally before CI rebuilds it.

**Goal.** Apply what F118 justified, each with regression evidence: the
consolidation of the duplicate build, the division of `integration`, the
split of the check identity where safe, and the replacement of the blanket
local full-site builds in the agent workflow by targeted checks and the
selection CI will make, with a local full run for the listed change types.

**User-visible outcome.** None on the site. A one-lesson pull request
spends less time on its longest path (measured), a pull request that
changes an unrelated integration test no longer executes every lesson
where F118 showed it safe, and an agent that changed one lesson verifies
that lesson and the selection, without building the site, before CI
builds and validates it.

**In scope.**

- The removals and consolidations F118's verdicts justify, each in its
  own reviewed step with the regression test that the violation the
  removed check caught still fails `verify`; `scripts/verify.conf`,
  `.github/workflows/ci.yml`, and the tests change only as justified; no
  independent scientific check is removed; the executions per lesson in
  a full run are listed before and after.
- The division of the `integration` job into parts that run every test
  exactly once (as `tests/e2e/shards.json` does for the built-site tests),
  if F118 showed it shortens the critical path; the F58 tests of the
  division extended.
- The split of the check identity into validity domains only for the
  domains F118 showed complete, with a completeness test per domain and
  the rule that an unclassified input belongs to every domain; no change
  lets older check logic certify a reused result.
- **The proportional local run** (ADR 017 decision 7): `scripts/fetch-base.sh`
  usable on a developer's machine with a read-only `gh` login to retrieve
  the latest base of `main` under the same provenance rule as CI (no
  base, no login, or a rejected base is reported as "CI will run
  everything", never as a wrong selection); **the targeted run**, a new
  option of `./scripts/verify.sh` (the feature names it), as the agents'
  and maintainers' pre-pull-request run for an ordinary change: it
  computes the selection CI will make and reports it, runs the checks
  that need no site build (lint, format, unit tests, lesson source
  checks, dataset checks), the experiment check and the single-page
  render of the selected lessons, and the Lean build for changed proofs,
  and performs no site build, no determinism build, and no built-site
  check; `./scripts/verify.sh --base` for a change that alters what other
  pages display of a lesson (the front-matter fields of the path and the
  headers, a new lesson); the full `./scripts/verify.sh` whenever the
  selection names a full run (the shared inputs of ADR 014 decision 4 and
  the files of the check identity, which is the listed change types:
  verification scripts and configuration, templates, filters, assets,
  shared site files, site configuration, the curriculum file, the shared
  authoring code, the Python pins); `./scripts/verify.sh` without options
  unchanged; a test per tier that the run performs exactly the checks of
  its tier and that the targeted run builds no site.
- The agent workflow: `AGENTS.md`'s definition of done, the prompts, the
  policies, `scripts/finish-feature.sh` and `scripts/review-feature.sh`,
  and `docs/development.md` express the three tiers where the workflow
  enforces them: the finish and the review of a feature run the tier the
  change type requires and record which one, its pass, and, with a base,
  the base and the selection; for an ordinary change that is the
  targeted run and no step of the finish or the review builds the site.
  Template-synced files are changed in the smallest way or through the
  configuration the template offers, and the change is recorded for the
  next template sync.
- The measurement after the change: three consecutive one-lesson pull
  requests against the 20-minute budget with the 15-minute target (ADR
  015), and one full run on `main`, recorded in
  `docs/release-readiness.md`.
- `docs/architecture.md` ("Inside one verification run", "CI pipeline and
  time budget") and `docs/development.md` updated; the statuses of ADR 014
  and ADR 017 record what was applied.

**Out of scope.** Incremental `main` (F120, F121); dropping or weakening
any scientific check; a scheduled audit; raising the job timeout (the
owner's decision under question 10, recorded by F118); selecting the Lean
build (question 8); self-hosted runners.

**Dependencies.** F118; the owner's acceptance of ADR 017 decisions 7 and
8 on F118's evidence (they are separable from incremental `main`, and the
acceptance is a dated line of ADR 017's status naming the decisions and
the evidence, as that status provides).

**Acceptance criteria.**

1. Every removed or consolidated check has the regression test F118
   named, and `verify` still fails on the violation it caught; the
   executions per lesson in a full run, before and after, are recorded.
2. No independent scientific check left `scripts/verify.conf`; the site
   build, the determinism comparison of every byte, the reproduction or
   experiment check in a fresh clone, the page checks, and the deployment
   of the verified artifact are unchanged in meaning (the F58 and F61
   tests pass).
3. If `integration` is divided, every test runs exactly once (a test) and
   the measured critical path of a one-lesson pull request is shorter
   than F118 recorded.
4. If the check identity is split, each domain has a completeness test, a
   change to an unclassified input invalidates every domain (a test), and
   no reused result is certified by older check logic (a test per
   domain).
5. No blanket demand to rebuild the whole site locally remains in the
   agent prompts, policies, workflow scripts, or guides except for the
   listed change types, whose full `./scripts/verify.sh` run is the
   local site render the requirements' runtime constraints permit and
   not the instructional rebuild or preview walkthrough the non-goal
   removes (ADR 016 decision 1, ADR 017 decision 7, F117 criterion 1);
   the targeted run exists, builds no site (a
   test), reports "CI will run everything" without an acceptable base
   instead of selecting, and is documented with the two tiers above it;
   a feature finish and a review on a one-lesson change ran the targeted
   run and nothing that builds the site, shown by their recorded pass
   naming the tier, the base, and the selection.
6. CI remains the publication gate with unchanged permissions (the
   workflow tests pass); three consecutive one-lesson pull requests and
   one full run are measured after the change and recorded with their
   durations and whether the 15-minute target was met.
7. The architecture, the development guide, and the ADR statuses record
   what was applied; the statuses of ADR 003, ADR 005, and ADR 012 record
   that ADR 017 decision 7 amended ADR 003 decision 1 (as ADR 005
   decision 5 restates it), ADR 005 decision 3, and ADR 012 decision 1 on
   acceptance, and the status of ADR 017 carries the dated line of the
   partial acceptance of decisions 7 and 8 with its evidence.

**Risk.** High: it changes the CI workflow, a protected script, and the
meaning of a feature's local verification, which need the owner's
explicit approval and security-focused review.

**Detailed implementation plan expected.** Yes.

### F120 — Incremental `main`: the staged evidence and the decision record

**Delivered and closed (pull request #224 merged, Issue #196 closed on
2026-10-19).** The evidence is published in
`docs/incremental-main-evidence.md` and ADR 017 carries the owner's
decision (amend, not yet accept); by the change cycle
`risk-proportionate-workflow` (requirements decision 39, ADR 020 decision
8) the feature is finished by that publication and no further work on
ADR 017 is scheduled until the owner's triggers. The block below is the
record of the feature as approved.

**Source.** Change 4, "A", "B", and "Required evidence and staged
acceptance" items 1 to 4, 7, 9, and 10; requirements decision 35 and
unresolved questions 9, 10, 11, and 12; ADR 017 (proposed).

**Problem.** The owner asked for a critical review of an F61-based
incremental `main`, not for its implementation, and will accept or reject
the weaker guarantee only on evidence: that a selective verification
publishes the site a full verification would publish on the same commit,
that every way reuse can go wrong fails closed, that a chain of bases
keeps per-result provenance, that deployment stays one build, what the
execution environment of the hosted runners varies, and what the costs
and the fallback are. None of that exists today, and ADR 017 says so.

**Goal.** Produce that evidence without changing what `main` executes,
complete ADR 017 with it (the residual risks quantified, the mitigations
with values), present it to the owner, and record the decision and the
next step.

**User-visible outcome.** None on the site. The owner decides question 9
on a record whose every claim has evidence behind it, and knows what is
not shown.

**In scope.**

- **The same-commit comparison** (evidence item 1): on one commit, a full
  verification and a selective verification against an accepted base,
  each producing the publishable site; the comparison of HTML, figures,
  executed outputs, site metadata, the search index, the provenance
  region, and the checksums; every difference listed and classified as a
  documented provenance-specific difference or not; the cross-runner
  uncertainty reported, not resolved by assumption. A targeted comparison
  (local runs plus the artifacts of CI, or one measurement pull request)
  is preferred to broad CI experiments; a temporary workflow change, if
  unavoidable, lives on a measurement branch and is never merged.
- **The fail-closed demonstrations** (item 2): a base that is missing,
  expired, invalid (a digest that does not match), stale (an older
  format), or incompatible (a differing check identity or environment
  identity); a changed shared input; a changed check implementation; each
  shown to execute by a test (the F61 suites extended where a case is not
  covered) or a recorded run; the full-run fallback shown to finish under
  the timeout the owner approved on F118's record.
- **The chain's provenance** (item 3): the base format extended with the
  origin of every lesson's results (run, commit, environment identity,
  depth), the derivation link to the previous base, and the provenance
  record of the published site; prototyped with tests that a pull request
  artifact, an unverified run, and a base of another format are rejected
  and that an inherited result keeps its origin through a chain of at
  least three bases.
- **The environment identity** (ADR 017 decision 3): what the hosted
  runners varied across the named runs (image version, CPU model and
  flags, locale, time zone, as read from logs); which of it the pins fix;
  a byte comparison of identical inputs executed on different runners;
  the classification into enforceable, recorded, and residual. The
  comparison needs runs in which the same lesson inputs were executed,
  not restored, on different runners: the measurement pull requests of
  F61 do not offer that (each was a selective run that executed one
  changed lesson and restored the other twenty-one from the base, whose
  bytes are the base's on every runner, as `docs/release-readiness.md`
  records), so the sources are the executed results of successive full
  runs on `main` whose bases hold lessons with equal digests (the base
  artifacts are retained 30 days) or a measurement pull request that
  forces the execution of a fixed set of lessons on several runners; the
  byte comparison rests on these two. The full run of pull request #161
  (run 38534115654, 2026-10-14, which executed every lesson after its
  base was rejected) serves only the "what varied" part: a pull request
  run publishes no base, and its built site and `built-site-record` are
  retained 7 days (`ci.yml`), so its bytes are gone by about 2026-10-21,
  before F120 can start, while its logs (image version, CPU model,
  locale) remain readable against the run on `main` that preceded it.
- **One production build** (item 4): the evidence restated with the names
  of the F58 and F61 tests that `deploy` publishes the verified artifact
  and builds nothing.
- **Costs** (item 7): the one-lesson pull request and the one-lesson
  merge under incremental `main` estimated from F61's and F118's
  measurements, with fixed and lesson-dependent cost separated and every
  estimate labelled; the full-run fallback at representative larger
  lesson counts from F118.
- **The decision record** (items 9 and 10): ADR 017 completed with the
  evidence, the residual risks quantified, the mitigations proposed with
  values (the scope of the environment identity, the chain's maximum age
  and depth, provenance on the page or in the record, the trigger and
  timeout of the exceptional full run), and the explicit statement of
  what is not shown; presented to the owner on the Issue; the owner's
  decision (accepted with mitigations, or rejected) recorded in the
  status of ADR 017 and ADR 014, with the next step named (F121; or F113
  resumed; or the raised timeout as the standing gate). The analysis of a
  scheduled audit is presented as ADR 017 states it, without a
  recommendation, for question 11. The closure or supersession of Issue
  #150 is proposed on that Issue for question 12.

**Out of scope.** Changing `.github/workflows/ci.yml` for runs on `main`
(F121); any inherited result on `main`; lesson shards; a scheduled audit;
the Lean build selection (question 8); the removals of F119.

**Dependencies.** F61 (the delivered selection, base, and regenerated
context of pull requests #152 to #166, not the closure of Issue #147),
F118.

**Acceptance criteria.**

1. The same-commit comparison is recorded with the commit, both runs or
   builds, every differing file with its classification, and the
   statement that it shows the selective site equals the full site when
   the inherited results are valid, not that they are valid.
2. Each fail-closed case is demonstrated by a named test or a recorded
   run, including a changed shared input, a changed check, and a changed
   environment identity; the full-run fallback finished under the
   approved timeout in a recorded run.
3. The chain's provenance format is specified and prototyped with the
   tests named above; no pull request artifact or unverified run is
   accepted as a base (tests).
4. The one-production-build evidence names the tests.
5. The environment identity record lists what varied across the named
   runs, the byte comparison across runners for identical inputs with its
   result, and the classification into enforceable, recorded, and
   residual.
6. The costs are recorded with measurements and labelled projections,
   against the 20-minute budget and the 15-minute target.
7. ADR 017 carries the evidence and the mitigations with values and was
   presented to the owner; the owner's decision is recorded in its status
   and in ADR 014's, with the next step named; the proposal for Issue
   #150 is on that Issue.

**Risk.** Medium: evidence and tests, no change to what `main` does; High
if a measurement needs a workflow change, which then lives on a
measurement branch only and is reviewed as such.

**Detailed implementation plan expected.** Yes.

### F121 — Incremental `main` and the exceptional full run, if ADR 017 is accepted

**Not started, by the change cycle `risk-proportionate-workflow`
(requirements decision 39, ADR 020 decision 8, 2026-10-19):** ADR 017
decisions 1 to 6 and 9 stay proposed and paused, not justified by
lead-time evidence, and this feature waits for the owner's triggers (42
lessons measured, the capacity decided at 44 at the latest, or a complete
run on `main` above 45 minutes) and the owner's acceptance.

**Conditional.** This feature starts only when the status of ADR 017 says
the owner accepted it, with the mitigations the owner required. If ADR
017 is rejected, this feature is dropped by that decision (its ID is never
reused), and the owner decides between F113 resumed and the raised timeout
of question 10.

**Source.** ADR 017 as accepted; requirements decision 35, "Runtime and
deployment constraints" (verification simplification under review),
unresolved questions 9, 10, and 12; change 4, "A", "B", and evidence items
2, 3, 4, 8, and 10.

**Goal.** Implement ADR 017 decisions 1 to 6 and 9 as accepted: a push to
`main` retrieves the previous verified base of `main` under the same
provenance rule as a pull request, inherits a lesson's results only under
the conditions of decision 1 including the environment identity, records
per-result origins and the derivation of the chain, publishes the
provenance record beside the checksums, rebuilds and verifies the whole
site, deploys exactly the verified artifact, executes everything on the
listed events and on request in one job under the approved timeout, and
supersedes F113 non-destructively.

**User-visible outcome.** None on the pages; the site's provenance record
tells an auditor, per lesson, on which commit and run its results were
executed. A push to `main` that merges a one-lesson pull request finishes
in about the time the pull request took.

**In scope.**

- The workflow: the `build` job of a `push` run on `main` fetches the
  latest accepted base (the same `scripts/fetch-base.sh` rule: a `push`
  run on `refs/heads/main` whose `verify` succeeded, by the run's record;
  `actions: read` on that job for pushes; no other permission); the
  selection with the environment identity; the record of the run says it
  verified `main` against a chain and names the base; the base candidate
  carries the origins and the derivation link; the provenance record is
  part of the site artifact.
- The forced complete execution by event: a changed shared input, a
  changed check identity, a changed environment identity (pins, image
  label), a chain older than the approved maximum age or deeper than the
  approved depth, a missing or rejected base; and on request through a
  manual dispatch of the workflow that passes no base; one `build` job
  under the approved timeout, restated as the lesson count grows.
- `./scripts/verify.sh`: a run on `main` with a base is a verification of
  `main` against a chain; a run without options is unchanged and verifies
  everything; the store, the digests, and the identities as in F61,
  extended by the environment identity and the origins.
- Tests per decision: the conditions of decision 1 (a test per
  condition), the provenance and rejection cases of decision 2, the
  environment identity of decision 3, what always executes (decision 4),
  the expiry and the chain limits (decision 5), the dispatch and the
  automatic full run (decision 6), the permissions, and that `deploy`
  publishes the verified artifact and builds nothing.
- The same-commit comparison of F120 repeated once on the delivered
  workflow and recorded; the one-lesson merge and the full run measured
  with warm caches and recorded against the budgets.
- `docs/architecture.md` ("Inside one verification run", "CI pipeline and
  time budget", the invariants that name "`main` verifies everything"),
  `docs/deployment.md`, `docs/development.md`; the statuses of ADR 014
  and ADR 017 record the delivery; Issue #150 closed with a comment that
  names ADR 017 and this feature, the branch and the closed pull request
  #175 kept; the requirements' statement that every push to `main`
  executes every lesson is amended through the owner's acceptance
  recorded in ADR 017, as the requirements provide, and any further
  wording change of the requirements is a change cycle, not this feature.

**Out of scope.** Lesson shards or any assembly; a scheduled audit;
changing what any check checks; selecting the Lean build (question 8);
self-hosted runners; a tolerance in any comparison of bytes.

**Dependencies.** F120 (the evidence and the accepted record), F119 (the
proportional local run the agents use alongside), and the owner's
acceptance of ADR 017.

**Acceptance criteria.**

1. A push to `main` that changes one lesson executes that lesson and
   inherits the others only when every condition of ADR 017 decision 1
   holds, shown by the run's record and a test per condition; any
   condition that fails executes the lesson, and the listed cases execute
   every lesson.
2. Each fail-closed case of F120 holds on the delivered workflow (tests
   and one recorded run per kind), including the environment identity and
   the chain's age and depth.
3. The provenance record of the published site names, per lesson, the
   run and commit that executed its results; the base carries origins and
   its derivation; no pull request artifact or unverified run becomes a
   base (tests); an inherited result keeps its origin through the chain.
4. `deploy` publishes the artifact CI verified and builds nothing (the
   F58 tests still pass); no second production build exists.
5. The exceptional full run is invocable by dispatch and automatic on the
   listed events, is one job, and finished under the approved timeout at
   the lesson count of the day in a recorded run.
6. The same-commit comparison repeated on the delivered workflow shows the
   documented provenance-specific differences only.
7. Workflow permissions are unchanged except `actions: read` where the
   base is read; the F58, F61, and new workflow tests pass;
   `./scripts/verify.sh` without options verifies everything (a test).
8. The one-lesson merge and the full run are measured and recorded; the
   architecture, the deployment and development guides, and the ADR
   statuses record the delivery; Issue #150 is closed non-destructively
   with the branch and pull request #175 preserved.

**Risk.** High: it changes the CI workflow, a permission, the meaning of a
run on `main`, and the publication guarantee, which need the owner's
explicit approval and security-focused review.

**Detailed implementation plan expected.** Yes.

## Phase 6 — The scientific atelier and the course atlas (change cycle `scientific-atelier-atlas`)

Every feature in this phase comes from
`docs/changes/scientific-atelier-atlas.md` (2026-10-17) and the
requirements re-approved with it on 2026-10-17 (decisions 36 to 38), with
ADR 018 (the atelier, the asset classes, the atlas) and ADR 019 (the agent
skills) as their decision records. Each block names the slice of section 8
of the change request it comes from. What they inherit from the earlier
phases without repeating it: the invariants of `docs/architecture.md`
(with I30 to I32 added by this cycle), the risk levels of
`.agents/policies/autonomy.md`, the rule that a feature that changes CI,
workflow permissions, a protected script, the merge gate, or the
instructions of a write-capable agent is High and needs the owner's
explicit approval, and the three local verification tiers of ADR 017
decision 7.

Rules of this phase:

- **Every shared change is a full run.** `site/assets/site.css`, the
  templates and includes, the fonts, `site/_quarto.yml`, and
  `src/pbc/authoring` are shared inputs (ADR 014 decision 4): a pull
  request that touches them executes every lesson, and no feature of this
  phase claims a targeted-only tier for such a change. Each feature
  changes shared inputs in as few pull requests as it can, and the
  record of its verification names the full run.
- **The preview gate.** F123 (the foundations and one lesson), F124 (the
  home page), F125 and F126 (the atlas) together are the end-to-end
  preview the change request asks for first. F127 (the rollout) starts
  only after the owner's review of that preview at desktop, tablet, and
  phone widths is recorded on the Issues of F124 and F126, with the
  display label of the atlas and the navigation wording decided. Each of
  the four also has its own three-part rendered review (ADR 018 decision
  6).
- **Skills first, never blocking.** F122 precedes every other feature of
  the phase. A feature of this phase that produces a visual deliverable
  classifies it in its plan and names the approved skills it selects, or
  why none applies (ADR 019 decision 5); the first such plan is the one
  that demonstrates deliberate selection. If F122 drops or adapts a
  candidate, the feature proceeds with the recorded fallback: for F123,
  which creates the design specification, the direction of the change
  request's section 1 as recorded in requirements decision 36 and the
  project-owned skill; for F124 to F129, the design specification
  docs/atelier.md once it exists and the project-owned skill. Nothing
  waits for a candidate that failed its audit.
- **Lesson authoring is not blocked.** The lesson features of waves C1 to
  C4 proceed in their own worktrees within the interim full-run gate. A
  feature of this phase that changes a shared template, the lesson
  header, or the CSS rebases on the lesson features that merged before
  it, and a lesson feature in flight rebases on the merged foundations;
  neither changes a scientific claim, a computed number, a figure's data,
  a reference key, or a verified artifact, and the reproduction and
  experiment checks prove it on every pull request. Nothing of this phase
  is imposed retroactively on a lesson's text.
- **Coordination with the editorial programme.** F127 and F129 touch
  lesson pages that F115 edits (mechanics 01 to 05). F127 changes the
  template and the CSS, never the prose; F129's figure pilot takes a
  figure of a lesson outside mechanics 01 to 05, or its plan sequences
  the pull requests with F115's. No "Observe, Predict, Build, Explain" or
  other narrative structure is imposed on any lesson; the voice of
  decision 32 stays F114 to F116's.
- **One writing agent per worktree**, as everywhere; the features of this
  phase that may run in parallel are named under "Execution order".

### F122 — Governed visual agent skills: the audit, the pinned skills, the PBC Scientific Visualization skill, and the workflow contract

**Source.** Change request section 7 (all of it) and section 8, slices A
(the candidate skill audit) and A2; requirements decision 38, "External
integrations" (visual agent skills), "Security and privacy constraints"
(the supply chain), and unresolved question 13; ADR 019, proposed with
this planning and accepted when it is approved.

**Problem.** Every visual feature so far was guided by ad hoc prompting.
The owner named five candidate skills, none of which is audited, pinned,
or present in the repository; the only skills on the owner's machine are
user-level ones that a feature worktree elsewhere does not see; the
workflow runs two providers (Claude Code for the writing roles, Codex for
the reviewing roles) with their own skill locations and read-only profiles
that drop the user's configuration; and nothing records which skill, if
any, shaped an artifact.

**Goal.** Implement ADR 019: each candidate audited and decided by the
owner (vendored at a pinned revision, replaced by a thin project-owned
adapter, or dropped); the approved skills at `.agents/skills/` with a
provenance record each; the project-owned PBC Scientific Visualization
skill; discovery verified for every role and profile from a worktree; the
skills configuration check, the one check that reads the directory, which
fails visibly on a missing or moved skill; and
the planner, implementer, reviewer, and verification contract introduced
where it is supported, without a new mandatory review agent and without a
change to the owner approval hierarchy.

**User-visible outcome.** Nothing on the site. For the workflow: a
feature plan names the skills it selects for each visual deliverable or
says why none applies; a completion record names the skill and revision
behind an artifact; a review checks the rendered or generated artifact
against its sources and the selected guidance; a missing required skill
stops a feature with a clear message instead of being silently omitted.

**In scope.**

- **The audit, one record per candidate** (Impeccable, Anthropic Frontend
  Design, Diagram Design): the exact upstream repository and `SKILL.md`
  at a named revision; every script and reference file it carries and
  what a script would execute; its licence and the redistribution
  decision; its dependencies and security assumptions; its compatibility
  with the Quarto, `.qmd`, CSS, SVG, native MathML, Python, and GitHub
  Pages stack and with both runners; what is removed or adapted. The
  owner approves each outcome on the Issue (unresolved question 13); a
  candidate that fails licensing, security, or quality review becomes an
  adapter that references the approved source material, or is dropped
  with the reason recorded. Manim is not audited (question 15: not
  scheduled); FreeCAD and OpenSCAD are not candidates.
- **The project-local copies** at `.agents/skills/<name>/`, with the
  provenance record beside each (upstream, revision, licence, the
  audit's findings, the review date, the update and re-review policy),
  and the digest of the copied files recorded so that the check below
  can tell a moved copy from the pinned one. Nothing is installed by a
  third-party installer, fetched at run time, or placed in a user-level
  directory.
- **Discovery verified.** From a feature worktree, for each role's
  permission profile and provider of `.agents/agents.conf` (write and
  unattended for Claude Code; read-only for Codex; the other combinations
  the configuration allows), a recorded demonstration that the runner
  lists or reads the skill directory; where a profile does not load it
  (the read-only profiles run without the user's configuration), the
  role's instructions name the skill files to read, which the Read tool
  of every profile allows.
- **The PBC Scientific Visualization skill**: a concise, practical
  `SKILL.md` with representative good and bad examples drawn from
  existing lessons (a convergence figure of M5, a measured-versus-model
  panel with residuals of M16, a conceptual diagram of F32, a preview of
  F63) and the references of the existing rules (`docs/authoring.md`:
  "Figures", "Visual design", "Lesson format 2", "Measured data";
  `docs/validation-contract.md`; the design specification of F123 once it
  exists). It covers: which visual to use (conceptual diagram, analytic
  or numerical plot, experimental data plot, uncertainty or residual
  display, animation, interface illustration); axes, units, scales,
  legends, symbols, uncertainty bounds, captions, accessible palettes and
  colour-independent encodings; comparisons of numerical, analytic, and
  experimental results, convergence, conserved quantities, error sources,
  and stability; reproducible Python generation with authoritative inputs,
  deterministic seeds, retained sources, and provenance; the explicit
  separation of decorative illustration from validated model or
  measurement, with no invented result, equation, or datum in a final
  figure; accessible static equivalents, reduced-motion controls, and no
  unnecessary browser payload. It supplements the visual quality gate,
  the authoring rules, and the scientific contracts and contradicts no
  check.
- **A README of the skills directory**: the set, the selection policy of
  ADR 019 decision 2, how a plan selects and records, how a completion
  record evidences, how a review verifies, how a pin is moved.
- **The skills configuration check**, an ungrouped entry of
  `scripts/verify.conf`, in the group `default` beside the other
  structural checks (template-structure, shell-syntax, docs-scripts,
  docs-references, documentation), run by the `workflow` job in CI and by
  the targeted run (`./scripts/verify.sh --targeted`) locally; no new
  group and no change to the CI workflow, so every group still runs in
  exactly one CI job (ADR 012 decision 2). It verifies that
  every directory under `.agents/skills/` has a `SKILL.md` and a
  provenance record with the required fields and a matching digest; every
  skill a committed feature plan under `.agents/plans/` names exists; a
  violation fails with a message that names the skill. A test per case.
  It is the one check that reads `.agents/skills/`, and it reads the
  skills as data to validate, never as instructions to follow (ADR 019
  decision 1); the site, the build, the lesson and built-site checks, the
  deployment, and every CI job stay independent of the directory.
- **The workflow contract where it is supported**: a short section of
  `AGENTS.md` (the planner's classification and selection, the
  implementer's evidence, the reviewer's verification, the rule that a
  skill is no evidence); a section "Visual deliverables and skills" of
  `docs/authoring.md`; the plan contents of `.agents/prompts/planner.md`
  and the evidence rule of `.agents/prompts/implementer.md` and
  `.agents/prompts/reviewer.md` where a line suffices, with every change
  to a template-owned file (`.agents/prompts`, `AGENTS.md` in
  `.agents/template.conf`) recorded so that `scripts/sync-template.sh`
  keeps it, or carried in the project's own files instead; the review
  criteria of `docs/evaluation.md` only if a line is needed. No new
  mandatory review agent; the owner approval hierarchy unchanged.
- **The boundary test**, created by this feature (no test under `tests/`
  checks for an agent invocation today; F45 later extends it to coding
  agents, I24): no workflow, script, check, build step, or CI job
  invokes, installs, or fetches a skill, and the build and every check
  except the skills configuration check pass with `.agents/skills/`
  absent from a scratch copy.

**Out of scope.** Any change to the site; a Manim pilot; CAD skills; the
pilots of F129 beyond the examples the skill carries; the choice of
providers and models (Issue #165); a skill that writes code or runs
tools outside the audited scripts.

**Dependencies.** F119 (the delivered workflow: the targeted tier for the
evidence and the `default` group of `verify.conf` the check joins); the owner's
approval of each candidate's outcome and of the contract. No other
roadmap feature.

**Visual deliverables and skills.** None: this feature produces no visual
artifact; it produces the skills and the contract.

**Acceptance criteria.**

1. Each of the three candidates has an audit record with the fields
   above and an owner-approved outcome on the Issue; a vendored skill is
   at its pinned revision with its licence text; an adapter names its
   approved source material; a dropped candidate has its reason.
2. Discovery is demonstrated per role, profile, and provider from a
   feature worktree and recorded; where a profile does not discover the
   directory, the role's instructions name the files to read.
3. The project-owned skill exists with the topics above, its examples
   trace to existing lessons and their figure cells, its references
   resolve, and the independent reviewer confirms that it contradicts no
   rule of `docs/authoring.md`, `docs/validation-contract.md`, or
   `scripts/verify.conf`.
4. The skills configuration check fails on a missing skill, a missing or
   incomplete provenance record, a digest that does not match, and a plan
   that names an unknown skill, a test per case; it is an ungrouped entry
   of `scripts/verify.conf` (the group `default`), runs in the targeted
   run locally and in the `workflow` job in CI with no new group and no
   workflow change, and it is the only check that reads
   `.agents/skills/`.
5. The contract is in `AGENTS.md` and `docs/authoring.md`, and in the role
   instructions where a line suffices; every changed template-owned file
   is recorded for the template sync; no new review agent exists and no
   approval step moved.
6. No workflow, script, check, build step, or CI job invokes, installs,
   or fetches a skill, shown by a test; the build and every check except
   the skills configuration check pass with `.agents/skills/` absent from
   a scratch copy.
7. The owner's explicit approval of the set and of the contract is
   recorded on the Issue (the High-risk gate).

**Risk.** High. Third-party instructions reach agents with write access
to the repository, the role instructions of the workflow change, and the
skills are a supply-chain input; the audit, the pins, the per-candidate
approval, the skills configuration check, and the boundary test limit it.

**Detailed implementation plan expected.** Yes: the audit template, the
per-candidate decision table, the discovery matrix, the check, and the
places the contract goes.

### F123 — The atelier foundations: the design specification, tokens, typography and fonts, the shared header and footer, and the lesson template on one existing lesson

**Source.** Change request sections 1, 3, 4 ("Remaining templates"),
7 (the Home, atlas, and lesson preview pilot), 8 (slices A, the design
specification, and B), and 9; requirements decision 36 ("Visual
direction", "Shared templates"), decision 37, "Runtime and deployment
constraints" (the rendered review), and the non-goals; ADR 018 decisions
1, 2, 5, and 6; ADR 019 (Impeccable and Anthropic Frontend Design, as
F122 approved them).

**Problem.** The site runs on Quarto's default theme with the F44 tokens,
one self-hosted font (the math font), Quarto's navigation bar, and no
project mark, no shared header or opening template, no atelier
typography, and no reading-column lesson layout. There is no document
that says what the atelier is, so every later feature would invent it
again.

**Goal.** The foundations every later feature of the phase uses, in one
place: the design specification; the tokens and component styles that
extend F44; the serif, body, and monospace faces self-hosted with their
licences; the shared header with the project mark, concise navigation,
and the start link; the shared footer with attribution, source, licences,
and secondary navigation; and the calm reading-column lesson template,
applied to one existing lesson. The foundations reach the chrome of every
page at once, so that the site never shows two headers; the lesson
template reaches every lesson in F127.

**User-visible outcome.** Every page shows the atelier: warm paper-white
background, nearly black text, cobalt blue and vermilion accents, serif
headings, readable body text, monospaced annotations, thin rules, and
generous whitespace; the header with the project mark, the navigation,
and a clear start link; the footer with attribution, source, and
licences. One existing lesson (chosen in the Issue: a format-2 mechanics
lesson with figures, code, equations, and a widget, for example
"Numerical integrators" or "The harmonic oscillator") reads in a calm
column of appropriate line length with a table of contents, its
prerequisites, and previous and next, with nothing of its content
changed.

**In scope.**

- **The design specification**, docs/atelier.md (a file this feature creates), registered in
  `docs/project-map.md`: the direction and its reference mockups named
  as inspiration and never as data; the tokens (colours defined once in
  `src/pbc/authoring/design.py` and copied to `site/assets/site.css`
  under the existing test; the type scale, spacing, rules); the
  components; the three asset classes with an example each; the mobile
  rule (a readable region selector, a focused view, and the list; a
  desktop map never shrunk until its labels are unreadable); the
  accessibility rules (WCAG 2.1 AA, 320 CSS px reflow, visible focus,
  reduced motion); how a feature applies it; and what the selected skills
  changed. The "Visual design" section of `docs/authoring.md` points to
  it.
- **Tokens and components** in `site/assets/site.css`, extending F44
  (claim labels, figure status, tables, excerpts, "Go deeper",
  self-checks, path rows, the graph keep their meaning and their
  contrast); the contrast test extended to every new pair.
- **Fonts**: the serif, body, and monospace faces as self-hosted woff2
  subsets under `site/assets/fonts/` with their licence texts beside
  them (an open licence such as the SIL Open Font License, recorded as
  the math font's is), listed among the resources of `site/_quarto.yml`,
  with the complete initial payload of every page measured; a face that
  does not fit the budget is subset further or dropped.
- **The shared header and footer** through Quarto's template partials
  and includes: the project mark (interface artwork: an SVG produced by
  code in the repository or an authored SVG source under `site/assets/`
  with its author and licence recorded), concise primary navigation
  (home, the atlas under the label the preview settles, glossary,
  evidence, about, set up, contribute, source) that works without a
  script, the start link; the footer with the F57 attribution line
  unchanged and its check passing, the source link, the licences, and
  secondary navigation; the skip link and the focus styles kept; the
  "Run this experiment" section of every lesson untouched (ADR 016; the
  F117 tests pass).
- **The lesson reading-column template**: line length, the table of
  contents, legible code and MathML, larger figures where useful, the
  current prerequisites, previous and next, as CSS and the existing
  header cell, applied by a page-level opt-in the plan chooses (a class
  or a front-matter flag that the schema check allows) to the one lesson
  of this feature; every executed cell, number, figure, claim, section
  identifier, and footer command of that lesson unchanged.
- **The design skills piloted**: the Impeccable and Anthropic Frontend
  Design guidance of F122 applied to the typography, layout, hierarchy,
  responsive presentation, and the components, and what they changed
  recorded in the specification and in the completion evidence (ADR 019
  decision 6); the comparison of the real responsive layouts, legibility,
  and accessibility against the direction.
- **The checks**: the contrast test; the payload check with the fonts;
  the accessibility scan; the keyboard pass of F10's audit on the new
  header; the reflow at 320 CSS px; the three-engine render of the
  component sample page (`rendering-check.qmd`); every internal link; the
  determinism check; the F57 identity check; the asset-source rule (every
  SVG under `site/assets/` has a provenance entry: author and licence, or
  the module that generates it; the register's file and format fixed in
  the plan); the committed-artifact check narrowed to the one declared
  exemption of ADR 018 decision 2 (amending ADR 002 decision 2): a
  tracked `.svg` under `site/assets/` passes only when the provenance
  register names it with an author and a licence, while an unregistered
  SVG, a raster of any type anywhere, every other image type, and every
  image file outside `site/assets/` stay rejected as today, with a
  failing test per case written before the change, in the same pull
  request as the register, so that the exemption and the provenance
  entry are one mechanism; the experiment and reproduction checks of the
  one lesson.
- **The rendered review**: screenshots at desktop, tablet, and phone
  widths of the home page as it is, the one lesson, the path page, and a
  supporting page, as evidence artifacts; the reviewer's assessment with
  the built HTML and the sources; the owner's pass recorded on the Issue.

**Out of scope.** The home page's content and figure (F124); the map
(F125, F126); the other lessons, the course openings, the capstone
template, and the supporting pages' layout beyond the shared chrome
(F127); any change to a lesson's text, numbers, or figures; a theme
switch; animation; an experiment gallery.

**Dependencies.** F122 (the approved design skills, or the recorded
fallback: this feature creates the design specification, so its fallback
is the direction of the change request's section 1 as recorded in
requirements decision 36 and the project-owned skill, never
docs/atelier.md itself), F44 (the tokens it extends), F57 (the attribution text and its
check), F63 (the preview sizes), F64 (the path page the chrome frames),
F117 (the footer contract: the entry-point contract and the footer merged
by pull request #205, not the closure of Issue #202, whose criteria 7 and
8 follow the merge; in practice a passing `main` after Issue #206, which
every feature of the cycle needs for its base and its deployment).

**Visual deliverables and skills.** Page and layout (the chrome, the
lesson column): Impeccable and Anthropic Frontend Design as approved;
interface artwork (the project mark): Anthropic Frontend Design as
approved; no conceptual diagram and no scientific figure, so Diagram
Design and the PBC Scientific Visualization skill do not apply, stated in
the plan.

**Acceptance criteria.**

1. Every page carries the shared header (mark, navigation, start link)
   and footer (attribution, source, licences, secondary navigation); the
   F57 identity check passes unchanged; every lesson's experiment section
   keeps its identifier and commands (the F117 tests pass).
2. The fonts are served from the site's own origin with their licence
   texts; no request leaves the origin; the initial payload of every page
   is within the 3 MB budget with the sizes of the heaviest lesson, the
   path page, and the home page recorded on the pull request.
3. The one lesson in the reading-column template has its executed cells,
   numbers, figures, claims, section identifiers, and footer commands
   unchanged (the diff of the pull request, the reproduction check, and
   the experiment check), and shows the table of contents, the
   prerequisites, and previous and next.
4. The accessibility scan passes on every page; the keyboard pass over
   the header and the lesson is recorded; every page reflows at 320 CSS
   px without two-way scrolling; reduced motion is respected; every new
   colour pair passes the contrast test; the component sample renders in
   the three engines, recorded with screenshots.
5. The design specification docs/atelier.md exists, is registered in `docs/project-map.md`,
   names the three asset classes with an example each, and is pointed to
   by the authoring guide; every SVG under `site/assets/` has its
   provenance entry, shown by the new check; the committed-artifact check
   accepts a tracked `.svg` under `site/assets/` only when the register
   names it with an author and a licence, and rejects an unregistered
   SVG there, a raster of any type anywhere, every other image type, and
   an image file outside `site/assets/`, each shown by a test that fails
   before the change (ADR 018 decision 2; the one amendment of ADR 002
   this cycle makes, and the only change to that check).
6. The rendered review has its three parts on the Issue: the
   implementer's screenshots at three widths, the reviewer's assessment,
   and the owner's pass; the plan's skill selection and the observable
   effect of each selected skill are recorded (ADR 019).
7. The full verification run passes with no check weakened beyond the
   declared exemption of criterion 5; the build is deterministic.

**Risk.** Medium. The chrome and the tokens touch every page; the
accessibility scan, the identity check, the payload check, the
three-engine render, and the F64 and F117 tests catch regressions; the
reading column is applied to one lesson only.

**Detailed implementation plan expected.** Yes: the specification's
outline, the token table, the partials, the font subsets, and the
page-level opt-in.

### F124 — The home page of the atelier, with a static verified opening figure

**Changed by the change cycle `site-navigation-and-atlas` (requirements
decision 40, ADR 021 decision 4, 2026-10-30):** delivered by pull request
#252, Issue #238 open for the owner's rendered pass. F134 replaces the
opening "Build a world. See if it obeys physics." with its
double-pendulum figure on Home by the hero, and the Part A, Part B, and
capstone blocks by three example lessons and one capstone; the figure's
function, energy check, and provenance stay in `src/pbc`. This block is
the record of what F124 delivered and is not rewritten.

**Source.** Change request sections 1 (the removed section), 4 ("Home"),
6 (the homepage pendulum), and 8 (slice C); requirements decision 36
("Home page"), the owner's answer of 2026-10-17 (the static figure), and
unresolved question 14; ADR 018 decision 4; F25 as the delivered record it
succeeds.

**Problem.** The home page of F25 names the three activities with one
example each, explains "One result, constructed and proved", and lists
what is published and planned; it has no opening, no project structure in
the atelier's sense, no capstone highlights, and its layout predates the
foundations. The direction asks for an opening with a figure, which must
be verified science, not an illustration that looks like one.

**Goal.** The home page of decision 36: the shared header; the opening
"Build a world. See if it obeys physics." with a static figure drawn by an
existing verified implementation; the introduction of Part A and Part B
from the real course structure with links into the atlas; capstone
highlights grounded in the current delivery state; a short invitation to
begin; the shared footer. The section "From a question to a working
model" is absent and nothing renamed takes its place.

**User-visible outcome.** A visitor sees, in one screen, what the site is
and the opening figure with its provenance; reads what Part A (the eight
courses) and Part B (the four method paths) are, with their real published
counts; sees the three capstones labelled planned with their roadmap
descriptions (the thermal project as a hypothetical accelerator, never a
named chip; the tsunami reconstruction; the phased array); and is invited
to begin with the atlas. No metric, testimonial, or progress claim.

**In scope.**

- **The opening figure**: a figure-writing function in `src/pbc` (the
  pattern of ADR 016 decision 2, beside the lesson's experiment module)
  called by an executed cell of `site/index.qmd`, drawing from the
  double-pendulum implementation of `pbc.mechanics.chaos` (validated in
  its lesson against its small-oscillation modes and its energy) if the
  plan judges that validation sufficient, otherwise from another verified
  mechanics figure, composed in the atelier language (the tokens, the
  figure colours), scientifically faithful to the model, with the
  `simulated` status, alt text, explicit dimensions, and the provenance
  (the module and the commit) stated beside it. No script computes or
  animates it; the figure is byte-stable.
- **The structure**: the introduction (the three activities Construct,
  Investigate, Verify stay named with their published examples, as the
  project goal, not as a three-step teaching formula or a section of
  steps); Part A and Part B from the curriculum file and the front matter
  (`pbc.authoring.home` extended), with links into the atlas by course
  and by path at the existing address and anchors; capstone highlights
  from the curriculum file's capstone slots, labelled planned until a
  capstone is published, their text the short explanation of each
  capstone's concept in the map manifest of F125 (ADR 018 decision 3:
  the one place that text lives, kept consistent with the roadmap's
  description, the thermal project a hypothetical accelerator), read by
  `pbc.authoring.home` through the same validated reader and typed into
  neither `site/index.qmd` nor the module; the invitation;
  the footer of F123. The sections "One result, constructed and proved"
  and the hand-written parts of the F25 page are replaced only where this
  structure replaces them; the published and planned lists stay derived.
- **The tests**: the F25 and F62 tests adapted (counts and names from the
  metadata; every planned item labelled and never linked; the examples
  link to published lessons); a test that the capstone highlights render
  only the manifest's explanation of each capstone's concept and no other
  description; a test that the heading "From a question to
  a working model" is absent; the no-script, accessibility, 320 CSS px,
  payload, and determinism checks; the figure's source traced to its
  module by the asset-source rule.
- **The rendered review** of the page at three widths; the skills of
  F122 as the plan selects them.

**Out of scope.** Interactive controls or animation of the opening
(F128); an experiment gallery; any lesson; a change to the identity text
(F57; the owner approves copy); counters, testimonials, news.

**Dependencies.** F123 (the foundations), F125 (the map manifest and its
validated reader, which the capstone highlights read: the home page waits
for the curated manifest, independently reviewed and approved by the
owner as F125 delivers it, because the three capstone explanations it
shows exist nowhere else; F125 does not land the capstone concepts
separately), F25 (the page it
succeeds), F62
(the planned structure), F68 (the double-pendulum implementation), F117
(the figure-writing pattern: the entry-point contract merged by pull
request #205, not the closure of Issue #202, whose criteria 7 and 8
follow the merge; in practice a passing `main` after Issue #206), F57
(the identity text).

**Visual deliverables and skills.** Page and layout: Impeccable and
Anthropic Frontend Design as approved; a scientific figure (the opening):
the PBC Scientific Visualization skill; no conceptual diagram.

**Acceptance criteria.**

1. The page has the header, the opening with the figure, the Part A and
   Part B introduction with links into the atlas, the capstone highlights,
   the invitation, and the footer; the heading "From a question to a
   working model" is absent and no section presents a numbered teaching
   formula, shown by a test and confirmed in review.
2. The opening figure is drawn by an executed cell calling a function of
   `src/pbc` over a verified implementation, carries its status, alt
   text, and provenance, is byte-stable, and is computed by no script;
   the plan records which implementation and why its validation suffices.
3. Every count and name comes from the lesson metadata and the curriculum
   file; every planned item, including the three capstones, is labelled
   planned and never linked; each capstone's text is the manifest's
   explanation of its concept and nothing else; the thermal capstone is
   described as a hypothetical accelerator; shown by the adapted tests.
4. The page is complete without JavaScript, passes the accessibility
   scan, reflows at 320 CSS px, and is within the payload budget.
5. A reviewer who did not write the page confirms that every sentence
   about the site is true of the published site at that commit (F25's
   criterion kept).
6. The rendered review has its three parts on the Issue, with the owner's
   pass as half of the preview gate; the selected skills and their
   observable effect are recorded.
7. The full verification run passes.

**Risk.** Medium. The page is the site's front door and shows a
scientific figure; the metadata tests, the asset-source rule, and the
independent review of the figure's provenance guard it.

**Detailed implementation plan expected.** Yes, short: the figure's
module and validation, the page structure, the adapted tests.

### F125 — The map manifest and the static atlas: curated concepts and connections, the generated map with its textual equivalent

**Changed by the change cycle `site-navigation-and-atlas` (requirements
decision 40, ADR 021 decision 3, 2026-10-30):** delivered by pull request
#247, Issue #239 open. F133 replaces the map with its three edge types,
the Lean and method views, the code-drawn course illustrations, and their
textual equivalent by the two-layer atlas; the manifest, its concept
rules, and the three relationship types as data stay, the relationships
shown on the lesson pages, and the manifest gains the sequences'
descriptions and illustrations. This block is the record of what F125
delivered and is not rewritten.

**Source.** Change request sections 4 ("Course atlas"), 5 (all of it), 7
(the conceptual-diagram guidance where useful), and 8 (slices A, the map
data contract, and D); requirements decision 36 ("Course atlas"), "Data
and persistence" (the map manifest), and "UX expectations" (the Learning
Path page); ADR 018 decision 3; ADR 013; ADR 019 (Diagram Design, as F122
approved it).

**Problem.** The path page of F64 is course-first and complete, but it
has no map: no concepts, no placement, no scientific connections, and no
illustrated view of the eight courses and the four paths. The only data
the site holds are the curriculum file and the front matter; a map needs
a small addition that must not become a second catalogue, must not infer
concepts from titles, and must not draw a relationship it cannot state.

**Goal.** The map manifest and its validation; the curated concepts and
connections, reviewed as scientific claims about the curriculum; and the
atlas as build-generated semantic HTML and inline SVG with a textual
equivalent, placed on the path page above the index of F64 behind a
switch that works without a script, with every published lesson reachable
and every planned slot labelled.

**User-visible outcome.** A reader of the path page sees, above the
familiar index, a large illustrated map of the eight courses with their
concepts, the four method paths as a connected research layer, the Lean
and method views, the three kinds of connection drawn distinctly and
explained in words, planned concepts visibly labelled, and the three
capstones as planned projects; follows a concept to its lessons by plain
links; and, without scripts, reads the same map as text.

**In scope.**

- **The map manifest**, one YAML file beside site/curriculum.yaml (named
  in the plan; the architecture calls it the map manifest), read and
  validated by `pbc.authoring`, holding exactly what the requirements
  enumerate: concept identifiers with a short explanation each; display
  placement (course area, position); the slots each concept belongs to
  (capstone membership among them: an association whose slot is a
  capstone slot); curated conceptual connections, each with its two
  concepts, its type, and a short rationale. Nothing else: no reference
  to the course areas' illustrations (the generator maps each course of
  the curriculum file to its drawing) and no lesson reference (a lesson
  reaches the map through its slot or through the Lean and method
  views). Every capstone slot (T11, EM9, FL10) is represented by a
  concept, and that concept's short explanation, kept consistent with
  the roadmap's description of the capstone, is the planned description
  the atlas reveals and the home page's highlights show (F124); it is
  the concept's explanation, not a description field of its own, and the
  curriculum file gains no field (ADR 013 decision 3 unchanged). The
  rules, each with a failing test: every course, path, slot, and concept
  reference resolves (the schema defines course, path, slot, and concept
  references only and admits no lesson reference, so the requirements'
  lesson-reference rule holds vacuously); every concept names at least one slot; every
  capstone slot of the curriculum file is represented by exactly one
  concept (the home page's highlights of F124 depend on it); no title,
  description, outcome, prerequisite, publication state, or count is
  written in it; no prerequisite edge is written in it; the schema
  rejects an unknown field. Concept membership is never inferred from a
  lesson's title.
- **The curation**: concepts for the eight Part A courses and the four
  Part B paths, limited to the approved curriculum (the 115 slots and the
  Lean view), with the connections and their rationales; reviewed
  independently as scientific claims before merge, with the owner's
  approval of the file as of the curriculum file.
- **The derivation at build time** (ADR 018 decision 3): the state of
  every concept from the lessons that fill its slots; the prerequisite
  edges between concepts from the lessons' prerequisites (an edge when a
  lesson of one concept requires a lesson of the other; a planned lesson
  has none); the capstone memberships from the manifest, linked only when
  the capstone is published; the published counts from the lessons.
- **The drawing** in Python (as the graph of F26): course areas with
  subtle boundaries and meaningful small illustrations (interface
  artwork, drawn by code, one drawing per course of the curriculum file
  mapped by the generator with no reference in the manifest, with the
  Diagram Design guidance of F122 where approved and useful), concept
  positions from the manifest, the three edge types with distinct marks
  (never colour alone), the method paths as a connected layer that keeps
  their distinctions, the Lean and method views as part of the map
  (every published lesson listed by its method tags from the front
  matter, the lessons without a slot included, as links in the SVG's
  view layer and as sentences in the textual equivalent, with no manifest
  entry; a concept's lessons still come only from its slots), planned
  concepts and slots labelled and distinguishable without colour, the
  three capstones labelled planned with their planned descriptions from
  the manifest (the explanation of each capstone's concept, consistent
  with the roadmap's; the thermal project a hypothetical accelerator; EM9
  kept in the index and on the map); no raster, no arbitrary geography.
- **The page**: breadcrumb, title, and a short explanation; the switch
  between the map and the index as anchors or native disclosures that
  work without a script; the SVG with real links; the selected-concept
  panels as native disclosures reachable by links, each with the short
  explanation, the slots with their state, the canonical lesson links,
  and the rationale of its conceptual connections; the visually hidden
  textual equivalent (every concept with its course, its slots and their
  state, and its edges as sentences); the F64 index, progress marks,
  recommendations, filters, and search unchanged in content; the address
  and every anchor and graph node address kept. Without a script on a
  narrow screen, the map scrolls in its own focusable region at its
  readable size, as the graph of F26 does, and the index is the primary
  route; F126 adds the region selector and the focused view.
- **The tests**: the manifest rules; all eight courses, four paths, and
  the Lean and method views present; the published counts equal to the
  lessons; the prerequisite edges equal to the front matter; every
  conceptual edge with its type and rationale; every capstone link only
  for a published capstone; no planned slot linked or counted; every
  published lesson reachable without scripts through the map (the
  lessons without a slot through the Lean and method views) and through
  the index; the atlas rendering only the manifest's explanation as a
  capstone's planned description; every previous address and graph node
  resolving; the textual equivalent naming every concept, every edge,
  and every lesson of the Lean and method views; the accessibility scan;
  the keyboard pass; the reflow at 320 CSS px; the payload of the page;
  byte-stable rebuilds; the search index unchanged in meaning.
- **The rendered review** of the atlas at three widths.

**Out of scope.** Selection, zoom, filters, the phone's region selector,
and the switch as a script (F126); any change to the index's content, the
progress or recommendation behaviour, or the search; new lessons; course
openings (F127); a second catalogue; a raster map; an experiment gallery.

**Dependencies.** F122 (Diagram Design as approved, or the fallback), F62
(the curriculum file and the slots), F63 (the previews the index keeps),
F64 (the page), F26 (the prerequisite graph's layout and data), F37 (the
metadata), F41 (the search index).

**Visual deliverables and skills.** Page and layout (the atlas section):
Impeccable and Anthropic Frontend Design as approved; interface artwork
(the course areas' illustrations): Diagram Design as approved, with the
science of each illustration checked independently; no scientific figure
(the previews are F63's); the PBC Scientific Visualization skill does not
apply, stated in the plan.

**Acceptance criteria.**

1. The manifest validates under the rules above, a failing test per
   violation; it holds no field the curriculum file or the front matter
   holds and no prerequisite; every reference resolves; the owner
   approved its content on the Issue after the independent review of the
   connections as scientific claims.
2. The map shows all eight Part A courses, the four Part B paths as a
   connected layer, the Lean and method views listing every published
   lesson by its method tags (the lessons without a slot included), and
   the three capstones labelled planned with their planned descriptions
   from the manifest (the explanation of each capstone's concept and
   nothing else); EM9 is on the map and in the index; shown by a test
   over the manifest, the curriculum file, and the page.
3. The three edge types are explicit in the drawing and in the words of
   the textual equivalent; the prerequisite edges equal the front matter
   and none belongs to a planned lesson; every conceptual edge has its
   type and rationale; capstone links exist only for a published
   capstone; shown by tests.
4. A planned concept or slot is labelled, distinguishable without colour
   alone, never a lesson link, and never counted; the published counts
   equal the lessons; shown by tests.
5. With JavaScript disabled every published lesson is reachable through
   the map's links and through the index; every previous address, anchor,
   and graph node address resolves; the switch works by links or native
   disclosures; shown by tests, whose cases include the lessons without
   a slot, reached through the Lean and method views.
6. The textual equivalent names every concept and every edge; the
   accessibility scan passes; the keyboard pass and the screen-reader
   reading order are recorded in the manual pass; the page reflows at
   320 CSS px; the payload is within budget; the rebuild is byte-stable;
   the search index is unchanged in meaning.
7. The rendered review has its three parts on the Issue; the selected
   skills and their observable effect are recorded; every illustration's
   generating code is in the repository.
8. The full verification run passes.

**Risk.** Medium. The manifest is a curated scientific artifact and the
page is the site's main navigation; the manifest rules, the F64 tests,
and the independent review of the connections guard it.

**Detailed implementation plan expected.** Yes: the manifest schema, the
derivation rules, the layout approach, the curation and review process,
the page sections.

### F126 — The atlas interaction: the switch, selection, zoom, filters, and the phone's region selector

**Changed by the change cycle `site-navigation-and-atlas` (requirements
decision 40, ADR 021 decision 3, 2026-10-30):** delivered by pull request
#255, Issue #244 open; the label "Course Atlas" chosen by the owner on it
stays. F133 replaces the switch, selection, modes, zoom, filters, and the
region selector by native exclusive disclosures and one address module,
and their tests by tests of the new interaction. This block is the record
of what F126 delivered and is not rewritten.

**Source.** Change request sections 4 ("Course atlas", items 2 and 4, the
mobile rule), 5 ("Accessible interactions"), and 8 (slice E);
requirements decision 36 ("Course atlas"); ADR 018 decision 3.

**Problem.** The static atlas of F125 is complete and reachable, but a
large map is read by selecting, zooming, and filtering, and a phone needs
a region at a time; without an enhancement the page is correct and
laborious.

**Goal.** Small dependency-free modules that enhance the generated atlas:
the switch between map and index, selection with the selected-concept
panel, the modes that show concepts and prerequisites separately, zoom,
filters coordinated with the index's filters and the search, and the
phone's region selector with a focused map view; storing nothing,
requesting nothing, with every lesson still reachable without them. The
display label of the atlas and the navigation wording are settled here,
in the owner's review of the preview, with the address unchanged.

**User-visible outcome.** A reader switches between the map and the
index; selects a concept by pointer or keyboard and reads its panel;
shows concepts or prerequisites apart; zooms a region; filters by course,
path, method, difficulty, or publication state, with the search finding
the same lessons; on a phone picks a region from a readable selector and
sees it focused, with the ordinary list below. Nothing is remembered
between pages; the progress marks and recommendations behave as before.

**In scope.**

- The modules in `site/learner/` under the convention of `path.js`
  (dependency-free ES modules; without them the page is complete; no
  request, cookie, or storage; nothing animated beyond the reduced-motion
  rule); the switch, selection and the panel, the modes, zoom with
  keyboard operation and visible focus, labelled controls, the filters
  coordinated with F64's filters and the search index (which is built
  from the page and never changed by a filter), the region selector and
  the focused view on narrow screens; a desktop map never shrunk until
  its labels are unreadable.
- The display label ("the atlas" or the owner's choice) in the navigation
  and the page title, decided in the owner's review and applied without
  changing the address or any anchor.
- The tests: the F125 tests pass unchanged with scripts disabled; the
  scan of I16 extended to the modules (no request, cookie, or storage
  while every control is operated); keyboard operation of every control
  with visible focus; the accessibility scan; the reflow at 320 CSS px;
  the payload of the enhancement measured apart from the page; the
  progress, recommendation, and search tests of F13, F14, and F41
  unchanged; the minimum rendered label size of the map at desktop and
  tablet widths checked by a test, with the map scrolling instead of
  shrinking below it.
- The rendered review of the atlas at three widths, as the second half
  of the preview gate.

**Out of scope.** Changing the manifest or the drawing (F125); browser
storage for any control; animation; a canvas map; new lessons; the
course openings (F127).

**Dependencies.** F123 (the foundations), F125 (the static atlas), F64
(the index and its filters), F13 and F14 (the learner state and the
recommendations keep their contract), F41 (the search).

**Visual deliverables and skills.** Page and layout (the interaction and
the phone view): Impeccable and Anthropic Frontend Design as approved; no
diagram and no scientific figure, stated in the plan.

**Acceptance criteria.**

1. With JavaScript disabled nothing is lost: the F125 tests pass
   unchanged.
2. The modules make no request, set no cookie, and write to no browser
   storage while every control is operated, shown by the extended scan;
   `site/learner/progress.js` stays the only script that stores anything.
3. Every control (switch, selection, modes, zoom, filters, region
   selector) works by keyboard with visible focus and a label; the
   accessibility scan passes; the screen-reader reading order is recorded
   in the manual pass; reduced motion is respected.
4. On a phone the region selector, the focused view, and the list are
   present and the page reflows at 320 CSS px; at desktop and tablet
   widths the map's labels stay at or above the minimum size, shown by a
   test.
5. The payload of the enhancement is measured and within budget; the
   search finds the same lessons with and without the filters; the
   progress marks and recommendations behave as before (the F13, F14, and
   F41 tests pass).
6. The display label and the navigation wording are decided by the owner
   in the review of the preview and applied with the address and every
   anchor unchanged, shown by the test over the previous addresses.
7. The rendered review has its three parts on the Issue, and the owner's
   pass over the preview (the home page of F124, this atlas, the lesson
   of F123) at desktop, tablet, and phone widths is recorded here as the
   preview gate; the selected skills and their observable effect are
   recorded.
8. The full verification run passes.

**Risk.** Medium. The modules touch the site's main navigation; the
no-script tests, the storage scan, and the keyboard tests guard them.

**Detailed implementation plan expected.** Yes, short: the modules, the
controls, the tests.

### F127 — The rollout: course openings, every lesson in the reading-column template, the capstone and supporting-page templates, and the final visual acceptance

**Changed by the change cycle `site-navigation-and-atlas` (requirements
decisions 40 and 41, ADR 021, 2026-10-30), before any Issue exists:** the
rollout starts after F132 to F135 are merged, since they change the
header, the footer, About, the setup page, the lesson template, and the
shared CSS it rolls out; the preview gate is the owner's rendered pass on
F133 (the atlas) and F134 (Home), with F123's lesson, recorded on their
Issues, in place of the review on the Issues of F124 and F126. A course
opening's illustration may be the sequence's illustration of the atlas
(interface artwork of decision 41) or a verified figure of the course; the
About and supporting pages take their content from F132 and F134 and only
their layout from this feature. The rest of the block stands.

**Source.** Change request sections 4 ("Remaining templates"), 6, 8
(slice F, and the publication-ready polish of slice G), and 9;
requirements decision 36 ("Shared templates"), decision 37, and the
non-goals; ADR 018 decisions 2, 5, and 6.

**Problem.** After the preview, the chrome is the atelier's but one
lesson reads in the new column, the courses have no opening, no capstone
template exists, and the About and supporting pages have the chrome
without the language.

**Goal.** Roll the design out across the site: course openings that reuse
the existing course sections, every lesson in the reading-column
template, the capstone template defined and sampled, the supporting pages
in the same language with every function preserved, and the owner's final
visual acceptance at desktop, tablet, and phone widths.

**User-visible outcome.** The whole site reads as one scientific
publication: each course opens with one relevant scientific illustration,
an introduction, its prerequisites, and a compact lesson list; every
lesson has the calm column, the table of contents, legible code and
equations, larger figures where useful, its prerequisites, and previous
and next; the glossary, evidence map, setup, contribution, search, and
licence pages look like the rest and work as before.

**In scope.**

- **The migration plan**, written first: which pages, in which order, in
  how many pull requests (each a full run), which routes are added (only
  for a clear purpose named here; a course's opening is its section of
  the atlas's index unless the plan justifies a page per course), and how
  the lesson features in flight and F115 are sequenced or rebased.
- **Course openings**: one relevant scientific illustration by asset
  class with its source (a verified figure of the course's lessons, its
  representative F63 preview, or interface artwork), an introduction, the
  prerequisites, and the compact lesson list, reusing the course panels
  of the index. A module is a grouping within a course that the migration
  plan finds useful (a method path's lessons inside a course, for
  example); none is invented without a purpose.
- **Every lesson in the reading-column template**: the opt-in of F123
  becomes the default; every executed cell, number, figure, claim,
  section identifier, reference, and footer command unchanged (the diff
  of the executed outputs, the reproduction check, and the experiment
  check on every lesson in a full run).
- **The capstone template**: the strong project opening and the spacious
  model and results presentation, with the rule that dark navy may frame
  visualizations while instructions stay readable (the contrast test),
  specified in the design specification docs/atelier.md, implemented in the CSS, and sampled on
  the component sample page; applied by the first capstone feature that
  publishes a capstone (F80, F87, or F88), since none is published today.
  A standalone interactive lab stays separately scoped.
- **About and the supporting pages** (about, glossary, evidence, set up,
  contribute, educators, the component sample page) in the same language
  with every function preserved: the glossary's terms and links, the
  evidence map's claims, the setup page's commands and its test, the
  contribution forms, the search, the licences; the instructor packs
  unaffected (F59).
- **The polish**: the owner's final visual acceptance across the
  representative pages at three widths, recorded on the Issue; what it
  changes is applied in the same feature.
- **The tests**: every existing page test (F41, F42, F19, F39, F57, F59,
  F62, F64, F117); the accessibility scan, the keyboard pass, the reflow
  at 320 CSS px, reduced motion, and the payload on every page; the
  asset-source rule for every illustration; every internal link, anchor,
  and previous address; determinism.

**Out of scope.** Any change to a lesson's prose (F115, F116), numbers,
figures, or claims; animation; the interactive pendulum (F128); an
experiment gallery; a route without a purpose named in the migration
plan; a published capstone (the capstone features).

**Dependencies.** F123, F124, F126, and the owner's recorded review of
the preview (the preview gate); coordinated with F115 and F116 and with
the lesson features in flight, as the rules of this phase say.

**Visual deliverables and skills.** Page and layout (the openings, the
lessons, the supporting pages, the capstone template): Impeccable and
Anthropic Frontend Design as approved; interface artwork (an opening's
illustration where it is artwork): Diagram Design as approved; a
scientific figure where an opening reuses one: the PBC Scientific
Visualization skill for its composition, with the figure's data and
values unchanged.

**Acceptance criteria.**

1. Every lesson renders in the reading-column template with its executed
   cells, numbers, figures, claims, section identifiers, references, and
   footer commands unchanged, shown by the diff of the executed outputs
   and by the reproduction and experiment checks of a full run.
2. Every course that has a lesson has an opening with one illustration
   whose class and source are recorded, an introduction, its
   prerequisites, and its compact lesson list; routes exist only as the
   migration plan says; every existing address, anchor, and link
   resolves, shown by the test over the previous addresses.
3. The supporting pages keep every function: the tests of F41, F42, F19,
   F39, F57, F59, F62, F64, and F117 pass unchanged.
4. The accessibility scan passes on every page; the keyboard pass, the
   reflow at 320 CSS px, reduced motion, and the payload hold on every
   page, with the sizes recorded.
5. The capstone template is specified, implemented, and sampled with the
   navy framing and readable instructions passing the contrast test, and
   named by the capstone features' definition of done.
6. The rendered review has its three parts for the representative pages,
   and the owner's final visual acceptance is recorded on the Issue; the
   selected skills and their observable effect are recorded.
7. Every full verification run of the feature passes with no check
   weakened; the build is deterministic.

**Risk.** Medium. Every page changes layout; the tests of every earlier
page feature, the reproduction and experiment checks, and the rendered
review catch regressions; nothing scientific changes.

**Detailed implementation plan expected.** Yes: the migration plan is the
plan.

### F128 — The validated interactive pendulum on the home page

**Changed by the change cycle `site-navigation-and-atlas` (requirements
decision 40 and unresolved question 14, 2026-10-30):** since F134 the home
opening is the hero, not the pendulum figure, so this feature is no longer
tied to Home. It is neither cancelled nor dropped: whether it is still
wanted, and where (the classical mechanics course or "How we verify the
science"), is the owner's decision when creating its Issue; the block's
validation, cross-language check, and controls stand for whichever page
is chosen, with "the home page" read as that page.

**Source.** Change request sections 4 ("Home", item 2), 6 (the homepage
pendulum), and 8 (slice G); requirements decision 36 (the owner's answer
of 2026-10-17) and unresolved question 14; ADR 018 decision 4; the widget
rules of F07 and F43 and the verified display forms. **Gate:** this
feature starts only when the owner decides question 14 by creating its
Issue; until then the home opening stays the static figure of F124.

**Problem.** The opening figure of F124 is static by decision. An
interactive double pendulum would let a visitor play with the model, but
physics computed in the browser must agree with the verified Python
implementation, must not drift from it, and must stay optional,
accessible, and honest about what is validated.

**Goal.** A widget under the F07 convention that integrates the double
pendulum in the browser, validated numerically and checked against the
Python reference across languages, with play, pause, and reset, parameter
controls with units and sensible limits, starting paused or under reduced
motion, with the static figure as its fallback and a label that says what
is validated.

**User-visible outcome.** The opening figure gains controls: a visitor
starts, pauses, and resets the pendulum, changes a parameter within its
limits, and reads what the animation does and does not establish; without
scripts, or under reduced motion, the static figure stands.

**In scope.** The numerical validation record of the model in Python
(the existing checks of M9: the small-oscillation modes and the energy;
a reference trajectory at fixed parameters and step with a stated
tolerance, and a convergence check); the browser implementation as a
dependency-free module that integrates the same equations with the same
scheme; the cross-language reference check as a built-site test (the
browser trajectory at the reference parameters compared with the Python
reference embedded by an executed cell, within the stated tolerance); the
controls, units, limits, and the paused start; the reduced-motion rule;
keyboard operation and visible focus; the static fallback kept; no
request, cookie, or storage; the payload; the label that distinguishes
the validated model from an illustration (the step, the regime, the
sensitivity to initial conditions); an independent scientific review.

**Out of scope.** A physics engine or any library; canvas without a
static equivalent; other animations; an experiment gallery; a standalone
interactive lab (separately scoped); a change to the M9 lesson beyond
reusing its code.

**Dependencies.** F124, F68 (the implementation), F07 and F43 (the widget
convention and the observed-value test), the owner's decision (question
14).

**Visual deliverables and skills.** An animation of a scientific result:
the PBC Scientific Visualization skill; the interaction: Anthropic
Frontend Design as approved; no diagram.

**Acceptance criteria.**

1. The validation record exists and the Python reference trajectory and
   tolerance are stated.
2. The browser trajectory equals the Python reference within the
   tolerance at the reference parameters, shown by the built-site test;
   a changed browser implementation that drifts fails it.
3. Play, pause, and reset work by keyboard with visible focus; the
   parameters have units and limits; the widget starts paused and stays
   static under reduced motion; the static figure is the fallback without
   scripts.
4. The widget makes no request, sets no cookie, uses no storage, and
   stays within the payload budget, shown by the F07 checks.
5. The label states what is validated and what is not; the independent
   scientific review confirms it.
6. The rendered review has its three parts on the Issue; the full
   verification run passes.

**Risk.** Medium. Physics computed in the browser; the cross-language
test and the independent review are the guard.

**Detailed implementation plan expected.** Yes, short.

### F129 — The scientific-figure and conceptual-diagram skill pilots, and the owner's decision on authoring integration

**Source.** Change request section 7 ("Bounded pilots and approval": the
conceptual-diagram pilot and the scientific-figure pilot) and section 8
(slice H); requirements decision 38 (the pilots) and unresolved question
15 (no Manim pilot); ADR 019 decision 6.

**Problem.** The project-owned skill and the approved Diagram Design
guidance of F122 are untested on real material. Whether they improve a
figure or a diagram, at what cost, and whether they should reach the
lesson templates is unknown, and must not be decided by applying them
everywhere.

**Goal.** Two bounded pilots on existing material, each with before and
after artifacts, qualitative rubric findings, build and runtime cost,
known limitations, and the owner's decision, with the verified values and
commands preserved; and the owner's decision on whether and how the
skills reach future lesson templates, coordinated with F116.

**User-visible outcome.** At most one lesson's conceptual diagram and one
lesson's figure read more clearly, with the same values, commands, and
claims; nothing else changes.

**In scope.** The conceptual-diagram pilot: one existing mechanics
concept (chosen in the Issue, from a lesson of F32 or F33), redrawn with
the Diagram Design guidance (or, if F122 dropped it, with the
project-owned skill's conceptual guidance and the design specification,
stated) and compared with the existing simpler verified SVG, for learner
value without a new heavyweight dependency; its science checked
independently. The scientific-figure pilot: one existing mechanics or
numerical-integration plot (chosen in the Issue; a lesson outside
mechanics 01 to 05, or sequenced with F115), recomposed under the
project-owned skill in its figure-writing function with the values at
displayed precision, the commands, and the claims unchanged (the
experiment check and the reproduction check), evaluated for clarity,
uncertainty display, and reproducibility. The record of both pilots
(before and after artifacts as evidence, the rubric findings, the cost,
the limitations) on the Issue or in a document registered in
`docs/project-map.md`; the owner's decision on expansion recorded; what
the decision changes in the skill, the specification, or the authoring
guide applied in the same feature, nothing applied to any other lesson.

**Out of scope.** A Manim pilot (not scheduled); any other lesson;
mandating a skill on lessons; the lesson template and the authoring
guide's editorial sections (F116); changing a value, a command, or a
claim; an authored committed SVG as the lesson's diagram (the redrawn
diagram stays an executed cell with its `conceptual` label, ADR 018
decision 2; if the pilot finds a need the code-drawn form cannot meet,
the record says so and a later ADR decides).

**Dependencies.** F122 (the skills), F32 and F33 (the diagrams), F05 (the
numerical-integration figures); coordinated with F114 to F116.

**Visual deliverables and skills.** A conceptual diagram: Diagram Design
as approved; a scientific figure: the PBC Scientific Visualization skill;
no page or layout work, so Impeccable and Anthropic Frontend Design do not
apply, stated in the plan.

**Acceptance criteria.**

1. Both pilots have before and after artifacts, the rubric findings, the
   build and runtime cost, and the known limitations recorded.
2. The piloted lesson's values at displayed precision, commands, claims,
   and references are unchanged, shown by the experiment and reproduction
   checks and the diff.
3. The diagram's science and semantics are checked independently of the
   skill and recorded.
4. The owner's decision on expansion is recorded; nothing is applied
   beyond the two pilots; whatever the decision changes in the skill, the
   specification, or the authoring guide is applied here, coordinated
   with F116.
5. The selected skills and their observable effect are recorded in the
   completion evidence; the independent review names the artifacts it
   evaluated.
6. The verification tier the change needs passes (a figure function
   change selects its lesson; a shared change is a full run).

**Risk.** Medium. One figure and one diagram of published lessons change
presentation; the experiment check and the independent scientific review
guard them.

**Detailed implementation plan expected.** Yes, short: the two choices,
the rubric, the record.

## Phase 7 — The risk-proportionate workflow (change cycle `risk-proportionate-workflow`)

Both features of this phase come from
`docs/changes/risk-proportionate-workflow.md` (2026-10-18; version 2 of
the workflow proposal with the owner's refinements R1 to R4) and the
requirements re-approved with it on 2026-10-19 (decision 39), with ADR
020 as their decision record. They change the development workflow and no
page of the site. What they inherit without repeating it: the invariants
of `docs/architecture.md`, the guarantees ADR 020 decision 9 keeps
unchanged, the three local tiers of ADR 017 decision 7, and the rule that
a feature that changes CI, a protected script, the merge gate, or the
instructions of a write-capable agent is High and needs the owner's
explicit approval of its diff before the merge.

Rules of this phase:

- **Strictly one after the other, never concurrent.** F131 starts only
  after F130 is merged and two features have run under it with their
  effect observed (owner's answer, 2026-10-19). Two changes to the
  workflow scripts (`scripts/lib/*`, `finish-feature.sh`,
  `review-feature.sh`, `triage-review.sh`, `apply-triage.sh`,
  `publish-feature.sh`, `verify.sh`) are never in flight together; a
  workflow fix outside these features waits for the one in flight.
- **Nothing before the approval.** Neither feature starts before this
  planning and ADR 020 are approved; the owner's actions of ADR 020
  decision 3 (the second identity, the ruleset, `CODEOWNERS`, the test
  pull request) are the owner's, performed when the owner chooses, and no
  agent performs or simulates them.
- **Features in progress finish under the contracts they started with**
  (`AGENTS.md`, ADR 003, 005, 012, 014, 015, and 017 as they stand on the
  day they started). The rules of F130 apply to features started after
  F130 is merged; the rules of F131 to features started after F131 is
  merged. **One stated exception, the merge approval gate** (ADR 020,
  Status): the protected list of `.agents/policies/guardrails.conf` that
  F130 widens is read by `scripts/check-guardrails.sh` from the base
  branch as it is at the check, and the code-owner rule of ADR 020
  decision 3 is enforced by GitHub at the merge, so both apply to every
  pull request finished or published after F130's merge, whatever day
  the feature started. A feature in flight that touches a path the wider
  list adds (`docs/architecture.md`, `scripts/build-site.sh`,
  `.agents/skills/`, among the others F130's in-scope item names) is
  reported as protected, is published without an agent merge, and needs
  the owner's approval of its diff; nothing else changes for it (no
  verification tier, no review, no evidence). No feature is
  grandfathered by reading the list at its merge base. On 2026-10-19 the
  owner accepted, by approving the round 4 revision of this planning's
  review (11:42 UTC), that the merge approval gate is the one exception
  to the rule of requirements decision 39 that a feature in progress
  finishes under the contracts it started with, for the reason stated
  here; the requirements are not edited for it (ADR 020, Status).
- **Each feature is Level 3** under ADR 020 decision 1 (the gate scripts,
  the prompts, the policies, the schemas, `AGENTS.md`), with a full
  review in every round, a complete verification of its final tree, a
  full review made after it, the full CI, and the owner's approval of the
  diff before the merge under the present practice (the owner's explicit
  word in the conversation, naming the head) until mechanism A exists.
- **No new mandatory agent and no new mandatory reporting gate.** The
  evaluation (ADR 020 decision 10) is derived afterwards from existing
  artifacts and the time log; a defect found after the merge in a Level 1
  or 2 change that the full process could have caught gets an Issue with
  the label `process-miss`, and a miss in an escalation-trigger category
  stops the pilot and restores full strictness at that level until the
  owner decides.
- **Template-synced files** are changed in the smallest way or through
  the configuration the template offers, and every change is recorded for
  the next template sync (`docs/development.md`, "Taking over template
  changes").

### F130 — Risk-proportionate workflow, part 1: the evidence lifecycle, the risk level, the merge-gate verification, intermediate Level 3 verification, the budget policy, and the time log

**Source.** Change request section 4, Deliverable 1 (items 1 to 7), with
sections 3.1, 3.2, 3.4, 3.5, 3.6, and 3.7; requirements decision 39 and
its "Authentication and authorization" section (mechanism A); ADR 020
decisions 1, 2, 3, 5, 6, 7, and 8.

**Problem.** A feature whose only outstanding evidence waits for CI, the
owner, or a post-merge measurement needs an owner exception to be
committed and published (five in three days); no script reads a risk
level, so every change pays the same verification and the same owner
attention; a Level 3 feature runs a complete local verification of about
68 minutes after every fix; and the owner's approval rests on an
agreement that an agent working with the owner's login could break
(`docs/development.md`, "Your approval is your own merge").

**Goal.** Deliver ADR 020 decisions 1, 2, 3, 5, 6, and 7 in the scripts,
the schemas, the prompts, the policies, and the guides, each with the
tests the acceptance criteria name, without changing what a verification
executes, what CI runs, or what a review is.

**User-visible outcome.** None on the site. A feature with pending
later-gate criteria is committed and published as a matter of course and
its Issue stays open until the evidence exists; every feature carries a
risk level the scripts derive and refuse to lower; a Level 3 feature gets
quick feedback from partial runs and one complete verification and one
full review of its final tree; the merge-gate verification refuses every
forgeable form of approval; `verify.sh` leaves a time log the evaluation
reads.

**In scope.**

- **The evidence lifecycle** (ADR 020 decision 2): the gate per criterion
  and the `pending` status in the completion record
  (`scripts/lib/completion.sh`, its documentation, the implementer's
  prompt), with `complete` meaning every criterion met; the three
  readiness points derived from the record; `finish-feature.sh` and
  `publish-feature.sh` accepting a record whose only unmet criteria are
  pending for later gates, without `--partial`, `--no-review`, or an
  owner exception, the pull request not closing the Issue while a
  criterion is pending, and the commit message and the pull request
  naming the pending criteria and their gates; the reviewer's guidance
  that a criterion whose evidence belongs to a later gate is not a
  finding and that an open major finding is never a pending criterion.
- **The risk level** (ADR 020 decision 1): derived by the scripts from
  the paths (the minimum), the mechanically detectable escalation
  triggers on the diff against the base branch (a widened tolerance or
  budget, a new skip or expected failure, a removed assertion or test, a
  changed marker such as `same_machine`, a changed dependency file), and
  the level the agent records and the reviewer assesses, raise-only;
  recorded in the completion record, the review, the commit message, and
  the pull request; the approval request's own path
  (`.agents/approvals/`) left out of the path minimum; a recorded level
  below the path minimum refused, and below a trigger reading refused
  unless the committed approval request names the lowering; a lowering
  accepted only as a request in the approval request of the feature,
  never applied by a script as an approval, and only of a trigger
  reading or an assessed level, never of the path minimum; the change
  kept at its required level by finish, review, triage, and verification
  until the owner's explicit word names the level requested, the scripts
  then recording the required level, the requested level, and the head,
  and a lowering the identity has not approved for the head redone at
  the required level before the merge (ADR 020 decision 1); the
  "changed scientific claim" trigger read as a change to or a removal of
  a published claim, so that a new lesson's claims leave it at Level 2;
  the reviewer's
  prompt assessing the triggers the scripts cannot detect with the impact
  classification it already fills, with no new agent and no new report.
- **The merge-gate verification** (ADR 020 decision 3): the committed
  approval request `.agents/approvals/<issue>.md` that a Level 3 change by
  trigger or assessment and every lowering request writes (for a
  lowering: the required level, the level requested, the reason, and the
  owner's word that let the agent proceed), and that
  `finish-feature.sh` requires for them; the scripts recording what is
  required and the head or tree it applies to, in the commit message, the
  review, and the pull request, with no repeated network request; the
  refusal, with a test, of every forgeable form (an agent-written
  assertion, a comment or review by the agent's own login, a file, a flag,
  a statement in chat); the merge step of `run-feature.sh` and the guides
  applying GitHub's decision only (the identity's approving review of the
  exact head) once mechanism A exists, and the present practice until
  then; the owner's actions documented in `docs/repository-setup.md` and
  `docs/development.md` as the owner's (the `CODEOWNERS` entries for the
  Level 3 paths of ADR 020 decision 1, `.agents/approvals/` and
  `.github/CODEOWNERS` itself among them; the option of an agent token
  without administration rights), with the test pull request recorded on
  this Issue when the owner performs it.
- **The protected list of `guardrails.conf`** (ADR 020 decision 1): the
  protected paths of `.agents/policies/guardrails.conf` brought in line
  with the Level 3 paths ADR 020 decision 1 names (the planning documents
  `docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md`, and
  `docs/architecture.md`, which moves from sensitive to protected;
  `AGENTS.md`, `.agents/agents.conf`, and `scripts/verify.conf`; the
  digest, the selection, `scripts/fetch-base.sh`, `scripts/collect-base.sh`,
  and the provenance module; `scripts/build-site.sh`; `.agents/skills/`;
  `.agents/approvals/`; and `.github/CODEOWNERS`), so that the gate's
  own list and the requirements' phrase "the protected paths of
  `guardrails.conf`" name the same paths; the dependency files stay
  sensitive (dependency selection is an escalation trigger, not a path).
  The file's header says the owner decides the list, so this is a Level 3
  change with the owner's approval of the diff, and
  `scripts/check-guardrails.sh` keeps reading the file from the base
  branch (the F58 and F61 tests pass). Because it reads the list from the
  base branch, the wider list knowingly applies to every pull request
  finished or published after F130's merge, including features started
  before it (the stated exception to the rule of this phase that a
  feature in progress finishes under its starting contracts; ADR 020,
  Status): such a feature is reported as protected when it touches a
  path the list adds, is published without an agent merge, and needs
  the owner's approval of its diff, and nothing else changes for it.
  F130 says so in the guides where the merge approval gate is described
  and does not grandfather a feature by reading the list at its merge
  base. On 2026-10-19 the owner accepted, by approving the round 4
  revision of this planning's review (11:42 UTC), that the merge
  approval gate is the one exception to the rule of requirements
  decision 39 that a feature in progress finishes under the contracts it
  started with; the requirements are not edited for it (ADR 020,
  Status).
- **Intermediate Level 3 verification** (ADR 020 decision 5): the
  intermediate fix rounds of a Level 3 change may run
  `./scripts/verify.sh --only <group>` for the groups the changed paths
  touch plus the unit tests of the changed modules, recorded as feedback
  and never as evidence; `finish-feature.sh` and `review-feature.sh`
  requiring, for Level 3, a complete verification of the final tree and
  the latest review made on that verified tree, with a review made with
  `--unverified` never counting as the final one; the targeted tier still
  refused when the check identity differs.
- **The budget policy** (ADR 020 decision 6) written in the one place the
  checks read their lesson budgets, the header of
  `scripts/lesson-budgets.conf` (an exception needs a reason and the
  owner's approval; a lesson over its budget still fails), and the
  wall-clock policy (a measurement for the owner at the re-assessment
  points, never a mandate) in `docs/development.md` and
  `docs/release-readiness.md` where the measurements are recorded.
- **The time log** (ADR 020 decision 7): `./scripts/verify.sh` appends
  one line per run (timestamp, tier, tree, duration, result) to a
  per-machine log outside the worktrees, documented, never committed, and
  read by no gate (a test that no script reads it).
- **The base re-fetch rule** (ADR 020 decision 7): `scripts/fetch-base.sh`
  does not fetch again when the latest accepted run on `main` is the one
  recorded, with the provenance rule of ADR 014 decision 2 unchanged (a
  test that recency never decides).
- **The policy and the definition of done**: `.agents/policies/autonomy.md`
  and the Definition of Done of `AGENTS.md` refer to ADR 020 and define
  the three levels and the evidence states, in the smallest change; the
  implementer's, reviewer's, and planner's prompts and `docs/workflow.md`
  and `docs/development.md` describe the behaviour; the template-synced
  changes recorded for the next sync.
- **The evaluation's first measurement**: after two features have run
  under this feature, the six measurements of ADR 020 decision 10 derived
  from the existing artifacts and recorded on this Issue (no new report),
  which is what F131 waits for.

**Out of scope.** The review chain, stable finding identifiers, the
fingerprint of the completion record and the handoff, and mechanical
triage (F131); any change to what a verification executes, to
`scripts/verify.conf`'s checks, to CI, to the digest, the selection, the
base provenance, the check identity, the build, or the deployment; the
owner's actions of mechanism A (the identity, the ruleset, `CODEOWNERS`,
the test pull request), which no agent performs; mechanism B; any work on
ADR 017, F113, or F121; a changed-lines threshold or an impact graph; a
new agent, report, or gate; optimisation of the full run.

**Dependencies.** This planning and ADR 020 approved; F119 (the three
tiers and the targeted run); F61 (the base and the selection, delivered);
F122 (the skills configuration check, which the gate scripts leave as it
is). The owner's actions of mechanism A are not a dependency of the
feature's start: the scripts are built and tested against the recorded
ruleset and the forged assertion, and relied on for the merge gate from
the day the owner's setup exists.

**Visual deliverables and skills.** None (a workflow change with no page,
diagram, figure, or animation). Skills: none (no visual deliverable).

**Acceptance criteria.**

1. The criterion gates and `pending` exist in the completion record, and
   a record whose only unmet criteria are pending for later gates is
   committed by `finish-feature.sh` and published by `publish-feature.sh`
   without `--partial`, `--no-review`, or an owner exception and without
   closing the Issue (a test per script).
2. `complete` means every criterion met; a test shows that a record with
   a pending criterion is not complete and that `pending` is refused for
   the `implementation` gate.
3. The risk level is the highest of the paths' minimum, the mechanical
   triggers on the diff, and the recorded assessment; the approval
   request's own path does not count in the path minimum; a recorded
   level below the path minimum is refused, and below a trigger reading
   is refused unless the committed approval request names the lowering;
   a lowering is accepted only as a request that needs the owner's
   authorization verified at the merge gate, may lower a trigger reading
   or an assessed level and never the path minimum, and the scripts
   record the required level, the requested level, and the head (tests
   per reading, per mechanical trigger, for a change whose only Level 3
   path is its own approval request, for a lowering of the path minimum
   that is refused, and for a lowering of a trigger reading that is
   recorded with both levels and the head).
4. No script accepts an agent-written assertion, a comment or review by
   the agent's own login, a file, a flag, or a statement in chat as the
   owner's approval (a test per form).
5. The merge-gate verification of mechanism A works in a test with a
   forged assertion that it refuses, and with a lowering request whose
   head has no approving review by the identity, which it refuses to
   merge; a Level 3 change by trigger or
   assessment and a lowering request cannot be finished without the
   committed approval request, and no script reads that request as the
   owner's decision; the merge step applies GitHub's decision
   only, and the guides say that a lowering the identity has not
   approved for the head is redone at the required level; the owner's
   actions and the test pull request are documented,
   and the owner's test is recorded on this Issue when performed.
6. Intermediate Level 3 rounds can use `--only` partial runs, recorded as
   feedback; `finish-feature.sh` and the final review require a complete
   verification of the final tree and a review made after it, and a
   review made with `--unverified` is refused as the final review (tests).
7. The time log exists with its five fields, is documented, and no gate
   reads it (a test).
8. The budget policy is written where the checks read their budgets
   (`scripts/lesson-budgets.conf`) and where the measurements are
   recorded; the base is not re-fetched when the latest accepted run is
   the one recorded (a test), and the provenance rule is unchanged (the
   F61 tests pass).
9. Every invariant and the full CI are unchanged and guarded by the
   existing tests (the F58, F61, F119, and F122 tests pass unchanged;
   `scripts/verify.conf`, `.github/workflows/ci.yml`, the digest, the
   selection, `scripts/fetch-base.sh`'s acceptance rule, and the build and
   deploy scripts are not changed except as criterion 8 says).
10. `.agents/policies/autonomy.md` and the Definition of Done of
    `AGENTS.md` refer to ADR 020 and define the three levels and the
    evidence states; the prompts and the guides describe the behaviour;
    the verification tier the change needs passes (a full run, since the
    check identity and the workflow files change), with a full review made
    after it, and the owner's approval of the diff is recorded with the
    head it applies to.
11. The protected list of `.agents/policies/guardrails.conf` names every
    Level 3 path of ADR 020 decision 1 and nothing a Level 1 or 2 change
    touches; a test shows that a change to each named path is reported as
    protected by `scripts/check-guardrails.sh`, and the owner's approval
    of the list is part of the approval of the diff.

**Risk.** High (Level 3): it changes the gate scripts, the prompts, the
policies (`guardrails.conf` among them), the schemas, and `AGENTS.md`,
which need the owner's explicit approval and a full review in every round.

**Detailed implementation plan expected.** Yes.

### F131 — Risk-proportionate workflow, part 2: the review chain, the review fingerprint of the completion record and the handoff, and mechanical triage

**Source.** Change request section 4, Deliverable 2 (items 1 to 3), with
section 3.3 (refinement R1); requirements decision 39; ADR 020 decision 4,
and decision 1 as it applies to the review.

**Problem.** Every change to a feature, however small, needs a new review
of the complete feature before it can be committed (`finish-feature.sh`
requires that the latest review is a full one), every finding needs a
triage session with the owner's approval whatever its severity, and the
completion record and the handoff note can change after the review
without making it stale.

**Goal.** Deliver ADR 020 decision 4: the traceable chain of delta
reviews for Level 2 with the disposition of every finding and a full
review whenever the reach of a delta is not certain; no review at Level 1
and a full review in every round at Level 3; the completion record and the
handoff in the review fingerprint; mechanical triage of minor and
suggestion findings at Levels 1 and 2.

**User-visible outcome.** None on the site. A Level 2 feature's later
rounds review what changed when the change's reach is certain, every
finding is followed to its disposition, and minor and suggestion findings
no longer wait for a triage session; Level 3 keeps a full review in every
round.

**In scope.**

- **The review chain** (ADR 020 decision 4): stable finding identifiers
  across rounds; each review recording the tree it compared against and
  the tree it reviewed; the disposition of every earlier open finding
  (resolved with evidence, still open, accepted) in each later review;
  `finish-feature.sh` verifying, for Level 2 only, that the chain begins
  with a full review, is contiguous, ends at exactly the current tree, and
  leaves no finding open, instead of requiring that the last review is a
  full one; a gap or a break requiring a full review.
- **The bounded-impact rule**: a delta review allowed only when the delta
  is confined to tests, documentation, lesson content, and a change to one
  source module whose importers are all among the files the baseline
  review covered, found by a plain textual search for the module name
  with the import knowledge the digest already has; anything else (a
  Level 3 path, an escalation trigger, a shared input of ADR 014 decision
  4, a changed exported interface, a file with an unresolved finding, an
  undecidable search) requiring a full review; no changed-lines threshold
  and no general-purpose impact graph.
- **The levels applied to the review**: no independent review required at
  Level 1 (recorded as such, without `--no-review` or an owner exception);
  the chain at Level 2; a full review in every round at Level 3.
- **The fingerprint**: the completion record and the handoff note included
  in what a review fingerprints (`scripts/lib/fingerprint.sh`,
  `scripts/check-review.sh`), so that a change to either after the review
  makes it stale.
- **Mechanical triage**: minor and suggestion findings at Levels 1 and 2
  triaged automatically (ACCEPT or DEFER with a reason), published once on
  the Issue, with a follow-up Issue for every DEFER; critical and major
  findings, and every finding at Level 3, keeping the full triage per
  finding with the owner's approval.
- The prompts (reviewer, triage), the schemas, `docs/development.md`,
  `docs/workflow.md`, and the policy updated; the template-synced changes
  recorded for the next sync; after the pilot of five features, the six
  measurements of ADR 020 decision 10 derived from the existing artifacts
  and recorded on this Issue.

**Out of scope.** Everything of F130 (the lifecycle, the level, the
merge-gate verification, the Level 3 verification rule, the budgets, the
time log); any change to what a verification executes, to CI, or to the
guarantees of ADR 020 decision 9; a changed-lines threshold, an impact
graph, a new agent, report, or gate; a relaxation of Level 3's full
review; any work on ADR 017, F113, or F121.

**Dependencies.** F130 merged, and two features run under it with their
effect observed and recorded on F130's Issue (owner's answer,
2026-10-19); nothing else of the workflow scripts in flight.

**Visual deliverables and skills.** None (a workflow change). Skills:
none (no visual deliverable).

**Acceptance criteria.**

1. Stable finding identifiers and the traceable chain exist: each review
   records the tree it compared against and the tree it reviewed, and
   each later review gives the disposition of every earlier open finding
   (tests).
2. `finish-feature.sh` accepts a Level 2 delta chain only when the chain
   begins with a full review, is contiguous, ends at exactly the current
   tree, and every earlier finding has a disposition with no finding
   open, and otherwise requires a full review (a test per condition).
3. A test shows that a delta whose impact cannot be bounded (a Level 3
   path, an escalation trigger, a shared input, a changed exported
   interface, an unresolved earlier finding, an undecidable importer
   search) requires a full review, and that no line-count threshold
   exists.
4. The completion record and the handoff note are in the review
   fingerprint: a change to either after the review makes it stale (a
   test per file).
5. Mechanical triage exists for minor and suggestion findings at Levels 1
   and 2, published once, with a follow-up Issue per DEFER, and a full
   triage per finding at Level 3 (tests); a critical or major finding is
   never triaged mechanically.
6. Level 3 keeps a full review in every round, and Level 1 needs no
   review, recorded without an owner exception (tests).
7. The invariants and the full CI are unchanged and guarded by the
   existing tests; the verification tier the change needs passes (a full
   run), with a full review made after it, and the owner's approval of
   the diff is recorded with the head it applies to (under mechanism A if
   the owner's setup exists by then, otherwise under the present
   practice).

**Risk.** High (Level 3): it changes the review and triage scripts, the
prompts, and the schemas.

**Detailed implementation plan expected.** Yes.

## Phase 8 — The quieter site and the two-layer atlas (change cycle `site-navigation-and-atlas`)

Every feature in this phase comes from
`docs/changes/site-navigation-and-atlas.md` (2026-10-30) and the
requirements re-approved with it on 2026-10-30 (decisions 40 and 41), with
ADR 021 as their decision record. The four Issues existed before this
planning (#337 to #340, created from the owner's review of 2026-10-29); the
blocks below are written from them and from the requirements, which win
where the two differ, and "State at the change cycle
`site-navigation-and-atlas`" lists every difference so that the Issue
bodies can be brought in line. What they inherit from the earlier phases
without repeating it: the invariants of `docs/architecture.md` (I6, I30,
and I31 restated by this cycle), the risk levels of ADR 020, the three
local verification tiers of ADR 017 decision 7, the three-part rendered
review of ADR 018 decision 6, and the skills contract of ADR 019.

Rules of this phase:

- **Order.** F132 first, so the others are designed against the new menu;
  then F133; then F134, whose home page links into the atlas and composes
  its hero image from the atlas's illustrations. F135 is independent of
  them in content but shares the lesson template and the shared CSS with
  F133: the two are never in flight together, and whichever starts second
  starts after the first is merged.
- **Every shared change is a full run** (ADR 014 decision 4, as in Phase
  6): `site/_quarto.yml`, the shared partials, `site/assets/site.css`,
  `src/pbc/authoring`, and everything under `site/assets/`. The targeted
  run reports it, and the full `./scripts/verify.sh` runs last.
- **Nothing scientific changes.** No lesson's text, scientific code,
  computed values, units, reference keys, or claims change; the
  prerequisite data and every check of scientific or curriculum
  correctness stay; obsolete tests of the removed map and controls are
  replaced by tests of the new interaction, never deleted without a
  replacement.
- **Interface artwork is accepted visually** (requirements decision 41,
  ADR 021 decision 1): a visual check (composition, legibility at the
  sizes shown, consistency with its family, no text, number, or formula
  in its pixels) recorded in the completion evidence and assessed by the
  reviewer on the rendered page; no scientific-correctness checklist, no
  diagnostic plate, disclaimer, or script required, all welcome where they
  exist. Its provenance entry records where it came from and proves
  nothing about correctness.
- **The owner's material stays the owner's.** The delivered illustrations,
  their scripts, the text-free Part B masters, and the mocks are named in
  the change request as staged for this planning; they are not in the
  repository at the base commit of this planning. Only the derived files
  the pages show, their register entries, and the scripts that exist
  enter the repository, in the feature that uses them; masters,
  intermediates, option boards, and mock sources are not committed.
- **The preview gate of Phase 6 moves.** F127 (the rollout) starts after
  F132 to F135 and the owner's rendered pass on the new Home and atlas
  (see the note on F127).

### F132 — Quieter navigation: a four-item menu, the secondary pages in the footer, About brought up to date

**Issue.** #337 (created 2026-10-29, before this planning).

**Source.** Change request "What I want", item 1; requirements decision
40 ("Menu"), "UX expectations" ("Site navigation"; "Shared templates": the
supporting pages from the footer); ADR 021 decision 5.

**Problem.** The navigation bar offers eight items, as if course
navigation, documentation, and scientific accountability mattered equally
to every visitor; Source appears twice (bar and footer). About still
describes "one path of increasing difficulty: mechanics, then agents, then
Lean", the architecture before ADR 013.

**Goal.** A primary menu of exactly four items and a footer that carries
the secondary pages; About corrected and refocused.

**User-visible outcome.** The header shows the project mark, Home, Course
Atlas, About, the search, and the Start learning button; the footer shows
Run the code, Glossary, Scientific evidence, For educators, Contribute,
and Source beside the attribution and the licences; About says who makes
PBC, why it exists, who it is for, and how its scientific reliability is
secured, and names the eight courses and four method paths.

**In scope.**

- `site/_quarto.yml` and the shared partials of F123: the navigation bar
  with Home, Course Atlas, About on the left and the Start learning button
  on the right, the search kept; Glossary, Evidence, Set up, Contribute,
  and Source removed from the bar.
- The footer: Run the code (the setup page `site/reproduce.qmd`, retitled,
  address unchanged), Glossary, Scientific evidence (the Evidence page
  until F134 points the link at "How we verify the science"), For
  educators, Contribute, Source; no link shown twice.
- `site/about.qmd`: the stale description replaced; the page restructured
  around who makes PBC and why, who it is for, what distinguishes it, and
  one short section on reproducibility; the eight courses and four method
  paths named with a link to the atlas; licences and citation kept at the
  end; every existing anchor kept (`#creator-and-jidai` is linked from the
  home page). The F57 identity text and its check unchanged.
- `site/reproduce.qmd`: the title "Run the code"; its content reordering
  is F134's.
- Every page stays reachable; the link check, the search index, and the
  home page's links are unchanged or updated with it.

**Out of scope.** The atlas (F133); Home, the content of "Run the code",
and "How we verify the science" (F134); the glossary on demand and the
improvement link (F135); a change to the attribution or identity text
(the owner approves copy).

**Dependencies.** F123 (the shared header and footer, merged by pull
request #237); F57 (the identity text and its check). F127 is not a
dependency: it has not started, and it rolls out after this phase (the
note on F127).

**Visual deliverables and skills.** Page and layout (the header, the
footer, About): the approved design skills of `.agents/skills/` as the
plan selects them; no artwork, diagram, or figure, stated in the plan.

**Acceptance criteria.**

1. The navigation bar shows exactly Home, Course Atlas, About, and the
   Start learning button, with the search; the footer shows the secondary
   links above; no link appears twice; every page stays reachable and
   every address resolves, shown by the link check and a test over the
   built header and footer.
2. About answers plainly who makes PBC, why it exists, who it is for, and
   how its scientific reliability is secured; it no longer describes a
   single ascending path, names the eight courses and four method paths,
   and links to the atlas; licences and citation stay; every existing
   anchor resolves; the F57 identity check passes unchanged. No word count
   is prescribed.
3. The keyboard order of the header is unchanged in kind (mark, items,
   Start) and the skip link still targets the main content; the
   accessibility scan and the reflow at 320 CSS px pass.
4. The rendered review has its three parts on the Issue.
5. The verification the targeted run reports passes, run last (the full
   run: `site/_quarto.yml` is a shared input); CI builds the site.

**Risk.** High (Level 3 by trigger: the assertion of
`tests/unit/test_site_chrome.py` that lists the eight items of the bar,
and the start link's text, change with the menu, a changed assertion of
ADR 020 decision 1 that the scripts detect; otherwise Level 2, site
configuration and page text, `site/_quarto.yml` being a sensitive path of
`guardrails.conf` and a shared input). The changed assertions are
replaced by the stricter test of criterion 1, which the review checks.

**Detailed implementation plan expected.** No; a short plan.

### F133 — The Course Atlas as a two-layer navigation page: twelve sequence cards and the lessons of the selected one, with generated illustrations

**Issue.** #338 (created 2026-10-29, before this planning).

**Source.** Change request "What I want", item 2, and "Decisions already
taken" (artwork, atlas shape, the exoplanet transit, Part B's text-free
versions); requirements decisions 40 ("Atlas") and 41, "UX expectations"
("Course atlas", "Learning Path page", "Visual asset classes"), "Data and
persistence" (the manifest, the raster assets); ADR 021 decisions 1 to 3,
superseding ADR 018 decisions 2 and 3 in part and amending ADR 002.

**Problem.** The atlas of F125 and F126 stacks the concept map with three
edge types and its legend, the Lean and method view bands, the controls
and modes, the concept panels, the course index, the method paths, and the
methods: a lesson appears four or five times on a page about 8000 px tall.
The owner's illustrations are raster images that ADR 018 forbade.

**Goal.** The atlas as a two-layer navigation page (the owner's mocks 3
and 4): the twelve sequences as cards, the lessons of the one open
sequence beside them, an accordion on a phone, every lesson one click
away, usable without scripts; the illustrations as registered WebP
interface artwork; the committed-artifact check widened to admit them and
nothing else.

**User-visible outcome.** On a wide screen, twelve cards (eight courses in
cobalt, four method paths in a copper ink) in one column and the open
sequence's panel beside them: a larger illustration, "Part A · Course 3"
or its Part B equivalent, the title, one sentence, "n published · k
planned", and the lesson rows; on a phone the same cards as an accordion
with the panel under its card; a smaller entry "Beyond the curriculum:
proofs in Lean". A lesson page shows, beside its prerequisites, the
concepts it connects to and the capstone it serves.

**In scope.**

- **The page** at the path address, display label "Course Atlas", built
  by `pbc.authoring` (ADR 021 decision 3): one `<details name="atlas">`
  per sequence, the `<summary>` the card (illustration, title, "n of m
  lessons", the progress hairline that `site/learner/progress.js` sets),
  the content the panel (illustration, kicker, title, description, counts,
  lesson rows: label in the monospace face, title as a link or, for a
  planned lesson, an entry marked planned that is no link, and only the
  marks Lab, Capstone, and Lean; no level or difficulty in the rows); the
  Lean entry; Part A and Part B told apart by more than colour; a semantic
  textual equivalent (a visually hidden list of every sequence with its
  lessons and their state), so that a screen reader reaches every lesson
  whichever sequence is open.
- **The layout**: at 56 em and wider, CSS grid with `::details-content`
  places the summaries in the left column and the open panel in the right
  (sticky, its height absorbed by a trailing row); without that selector
  the accordion; on a phone always the accordion.
- **The address module** in `site/learner/` (about twenty lines,
  dependency-free): the hash follows the open sequence and a hash opens
  its sequence; on a phone, opening scrolls to the card; no request,
  cookie, or storage.
- **The anchors**: every anchor the page has at the base commit resolves;
  the course and path anchors (today `#course-<id>` and `#path-<id>`) open
  their sequence; `#choose` and the page's other anchors resolve to the
  sequences or the top. The plan lists them from the built page of the
  base.
- **Removed from the atlas**: the concept map with its edges, legend, and
  modes; the Lean and method view bands; the controls, filters, zoom, the
  region selector, and the switch; the standalone concepts, method-path,
  and methods sections; the dependency-map disclosure; the lesson
  previews on this page (they stay on the course pages and Home). The
  modules of F126 that only served them are removed with their tests,
  which are replaced by the tests below.
- **The learner state on the page** (F13, F14; requirements "Course
  atlas": the progress and recommendation behaviour keeps its contract):
  the progress hairline on each card; under the sequences, the section
  that explains what is stored (its anchor `#your-progress`, which every
  lesson page links to), the control that clears it, and the "What to do
  next" recommendations panel, each as today; the page keeps carrying the
  learning path as data (each lesson's id, title, address, and
  prerequisites, in the data element `site/learner/progress.js` reads and
  passes to `site/learner/recommend.js`), so the recommendations are
  computed as before with no request; `path.json` unchanged. The
  prerequisite data and the code that writes it for these consumers stay
  when the map's drawing of it leaves.
- **The manifest** (`site/atlas.yaml`): one entry per sequence with its
  one-line description and its illustration (a path the register names),
  for every course and method path of the curriculum file and no other,
  checked with a failing test per rule; the concept rules of ADR 018
  decision 3 kept; the display placement the map used removed with its
  check if nothing reads it; the curriculum file unchanged.
- **The relationships on the lesson pages**: from the manifest, the
  conceptual connections (with their rationale) and the capstone
  membership of the concept a published lesson's slot belongs to, shown
  in the lesson header beside the prerequisites, never for a planned
  lesson; the prerequisite data, its checks, and the generation code with
  other consumers kept. Coordinated with F135, which changes the same
  template.
- **The illustrations**: twelve WebP files in one visual family (warm
  paper, cobalt, steel, copper, orange, fine lines, translucent fields),
  one per sequence, the astrophysics one the exoplanet transit and the
  Part B ones the text-free versions, at the card (about 76 px) and panel
  (about 200 px) sizes and their high-density variants, from the owner's
  delivered set, adapted, cropped, or replaced as the visual check
  decides; each registered in `site/assets/provenance.yaml` with its
  origin (script path, author, or image model with model, prompt, and
  date), licence or terms, and the SHA-256 of its master; the scripts
  that exist committed outside `site/` in a place the plan names, with a
  regeneration check on demand outside `scripts/verify.conf`; alt text
  that names each illustration, and for a Part B panel says in one line
  that it shows a toy-model example.
- **The committed-artifact check and the asset-source rule** (ADR 021
  decision 2): a tracked `.webp` or `.png` under `site/assets/` accepted
  only with its complete register entry; an unregistered raster, a raster
  with an incomplete entry, every other image type, and every image file
  outside `site/assets/` (a lesson directory included) rejected; an entry
  without its file failing the asset-source rule; a failing test per case
  written before the change.
- **The documents the feature owns**: the design specification
  docs/atelier.md and the "course atlas" section of `docs/authoring.md`
  brought in line with the new page and asset rules.

**Out of scope.** Home and its hero (F134); the glossary on demand and the
improvement link (F135); a change to the curriculum file, a lesson's
scientific content, or the prerequisite data; a dependency visualisation
elsewhere (a later decision); browser storage of the open sequence; a
canvas or an image as the only navigation surface.

**Dependencies.** F132 (the menu the page is designed against), F125 and
F126 (what is replaced, merged by pull requests #247 and #255), F123 (the
foundations), F64, F13, and F14 (the progress marks, the progress
explanation and controls, and the recommendations keep their contract),
the owner's approval of the twelve illustrations on the Issue, and the
pre-start gate: #338 brought in line with this block by the edits the
reconciliation notes list ("State at the change cycle
`site-navigation-and-atlas`"), before the feature starts.

**Visual deliverables and skills.** Page and layout (the atlas, the lesson
header line): the approved design skills of `.agents/skills/` as the plan
selects them; interface artwork (the twelve illustrations): the design
skill the plan selects for their composition and family, with the visual
check of the phase's rules; no scientific figure and no conceptual
diagram, so the PBC Scientific Visualization skill does not apply, stated
in the plan.

**Acceptance criteria.**

1. At 1280 by 800 CSS px the page shows the twelve cards and one open
   panel, and the first course's panel is readable without scrolling the
   page; at 390 by 844 it is an accordion with the open panel under its
   card; the Lean entry is present.
2. With scripts disabled every published lesson is reachable through the
   cards and by keyboard alone (Tab to a card, Enter or Space opens it,
   focus visible, the open panel next in order); with one sequence open,
   no other is; the textual equivalent names every sequence and every
   lesson with its state, shown by a test.
3. The existing course and path anchors open their sequence; the hash
   follows a click; every anchor of the base page resolves; the module
   makes no request, sets no cookie, and uses no storage while operated
   (the scan of I16), and `progress.js` stays the only storing script.
4. Published and planned lessons are distinguishable without colour
   alone; planned lessons are not links and are not counted as published;
   the counts equal the lessons; a published capstone is a link to its
   lesson (T11 and EM9 at the base commit) and a capstone without a lesson
   (FL10) shows its planned description from the manifest.
5. The manifest's sequence entries validate (one per course and path, a
   description, a registered illustration), a failing test per rule; the
   concept rules of ADR 018 decision 3 still pass; the curriculum file is
   unchanged.
6. Every published lesson whose concept has conceptual connections or a
   capstone membership shows them with the rationale, equal to the
   manifest, and no planned lesson shows any, shown by a test; every
   lesson's executed cells, numbers, claims, and section identifiers are
   unchanged (the reproduction and experiment checks).
7. The twelve illustrations are registered with their provenance, contain
   no text, number, or formula, and pass the recorded visual check
   (composition, recognisability at the card size, colour, consistency
   with the other eleven), assessed by the reviewer on the rendered page;
   a failing image is regenerated or replaced; the owner's approval is on
   the Issue; the page's complete initial payload is within the
   architecture's budget, with the size recorded.
8. The committed-artifact check accepts a registered WebP or PNG under
   `site/assets/` and rejects an unregistered raster, an incomplete entry,
   every other image type, and every image outside `site/assets/`; the
   asset-source rule fails an entry without its file; a test per case
   that fails before the change.
9. The open sequence and its lessons work in Chromium, Firefox, and WebKit
   under the project's Playwright, with the keyboard alone and with
   scripts disabled; the accordion fallback is tested by disabling the
   wide rule; a Safari behaviour WebKit does not cover has a recorded
   manual check; the accessibility scan and the reflow at 320 CSS px
   pass.
10. The tests of the removed map, views, and controls are replaced by
    tests of this interaction, the generated HTML (unit tests of
    `pbc.authoring.atlas`), the anchors, and the data; no check of
    scientific or curriculum correctness is weakened; the search index is
    unchanged in meaning; the rebuild is byte-stable.
11. The progress marks, the progress explanation and its control, and
    the recommendations keep their contract on the new page: the
    recommendations panel is present and the page carries every lesson of
    the learning path with its prerequisites as data; the F13 and F14 tests
    (`tests/e2e/test_learner_state.py`, `tests/e2e/test_recommendations.py`)
    pass unchanged, or a test that addresses the removed markup is replaced
    by an equivalent test of the same behaviour on the new page, named in
    the plan and checked by the reviewer; `progress.js` and `recommend.js`
    are unchanged in behaviour.
12. The rendered review has its three parts on the Issue; the selected
    skills and their observable effect are recorded.
13. The full verification run passes, run last.

**Risk.** High (Level 3, assessed: the feature widens the exemption of
the committed-artifact check, a guard of I6, and changes the site's main
navigation, the shared CSS, and the lesson template; and by trigger: the
tests of the removed map, views, and controls of F125 and F126 are
removed or replaced, criterion 10).

**Detailed implementation plan expected.** Yes: the page structure, the
anchors of the base, the manifest schema change, the asset entries and
the check's cases, the lesson-header line, the place of the learner-state
section and the recommendations, the tests replaced and added.

### F134 — Home as a landing page, Set up as Run the code, and a readable How we verify the science page

**Issue.** #339 (created 2026-10-29, before this planning).

**Source.** Change request "What I want", item 3, and "Decisions already
taken" (hero copy, hero image); requirements decision 40 ("Home"),
"UX expectations" ("Home page", "Site navigation"), "Data and
persistence" (the hero's data file), unresolved question 14; ADR 021
decisions 1, 4, and 5, superseding ADR 018 decision 4 in part.

**Problem.** Home has become an introduction, a course catalogue, and a
roadmap at once; "Set up" hides three clear routes behind the
installation; the reason PBC is different, that every claim is checked, is
told in fragments on Home, About, and the Evidence introduction, never in
one place.

**Goal.** Home answers what makes PBC different, what a visitor can learn,
and where to begin, opening with the owner's hero; "Run the code" offers
its three routes first; one readable page, "How we verify the science",
explains the evidence system with examples and leads to the Evidence map.

**User-visible outcome.** A visitor sees one of the owner's headlines with
its subtext and the two-constellation image, with the start button,
without scrolling; reads three sentences on what PBC is; sees three
example lessons from different courses and one published capstone; is
invited to begin. "Run the code" starts with Run a simulation, Replay an
AI experiment, and Verify a formal proof. "How we verify the science"
walks through three worked examples and the four claim types.

**In scope.**

- **The hero** (ADR 021 decision 4): the owner's three headlines and
  eight subtexts (supplied on Issue #339, 2026-10-30) in one data file
  beside the curriculum file (named in the plan; the architecture calls
  it the hero's data file), read and validated by `pbc.authoring.home`:
  exactly the eight pairs of the Issue, each a headline and one of its
  subtexts, identified by the headline's number and the subtext's letter,
  1a, 1b, 1c (headline 1), 2a, 2b, 2c (headline 2), 3a, 3b (headline 3),
  each present once and no other; one default among them; plain English
  text; one fixed default pair in the HTML with the fixed page
  title and description; one `<h1>`, unchanged after load; the hero
  script from the site's origin that picks a pair at random per visit and
  sets it before first paint from the pairs the build embedded, or the
  pair the `hero` parameter names; the height reserved for the longest
  pair; no storage, no request, no measurement.
- **The hero image**: interface artwork of decision 41, two connected
  constellations (the eight courses and the four method paths) composed
  from F133's illustrations with its labels as HTML or SVG text and its
  decorative connections implying no prerequisite; registered parts; not
  the delivered composite with labels in its pixels; every link an HTML
  link.
- **The rest of Home**: "What this site is" in three sentences; three
  example lessons from different courses (title, one line, preview,
  level) and one capstone, chosen from the published ones (T11 and EM9 at
  the base commit), chosen in
  `pbc.authoring.home` from the front matter and the manifest; "Begin"
  with the start link and the atlas, nothing else. The Part A, Part B,
  and capstone blocks of F124 and the opening "Build a world. See if it
  obeys physics." with its double-pendulum figure leave Home; the figure's
  function, energy check, and provenance stay in `src/pbc` with their
  tests and may be shown on "How we verify the science"; the capstone
  artwork module of F124 is removed or reused as the plan decides. The
  section "From a question to a working model" stays absent.
- **Run the code** (`site/reproduce.qmd`, address unchanged): three route
  cards at the top, each one sentence and a jump link; the shared
  installation under them; "Drive a coding agent" and troubleshooting
  behind disclosures; the content otherwise unchanged, the
  verified-command classes (`.required-setup`, `.experiment`, `.lean`,
  `.not-verified`) and the checks that read them unchanged.
- **How we verify the science** (a new page, site/verify.qmd, with its
  generated parts in `pbc.authoring`): three worked examples from
  published lessons (a numerically verified claim with its cell, a
  measured-data claim with its dataset card, a formal theorem with its
  Lean module), each linked to its place in the lesson and its row of the
  Evidence map, whose targets the build checks as it checks claims (a
  missing target fails the build); the four claim types, a paragraph each
  with the existing claim labels; a link to the Evidence map, whose
  introduction is shortened to point back; the footer link "Scientific
  evidence" pointed at the new page.

**Out of scope.** The atlas (F133); the interactive pendulum (F128, no
longer tied to Home); a measurement of which hero pair works better; a
change to the identity text (the owner approves copy); counters,
testimonials, news; an experiment gallery.

**Dependencies.** F132 (the menu and footer), F133 (the atlas the page
links into and the illustrations the hero image is composed from), F124
(the home page this changes, merged by pull request #252), F19 (the
Evidence map), F117 (the setup page's verified commands), and the
pre-start gate: #339 brought in line with this block by the edits the
reconciliation notes list ("State at the change cycle
`site-navigation-and-atlas`"), before the feature starts.

**Visual deliverables and skills.** Page and layout (Home, the hero, Run
the code, How we verify the science): the approved design skills as the
plan selects them; interface artwork (the hero image): the design skill
the plan selects, with the visual check; a scientific figure only if the
plan places the verified pendulum figure on "How we verify the science",
then the PBC Scientific Visualization skill with its data unchanged.

**Acceptance criteria.**

1. The central message and the primary start button are visible without
   scrolling at 1280 by 800 and at 390 by 844 CSS px; the page tells one
   story (what makes PBC different, what you can learn, where to begin)
   without repeating the atlas's overview of the courses; the example
   lessons and the capstone are chosen by code from data, and every link
   on the page is generated from data; the heading "From a question to a
   working model" is absent. No page-length limit is prescribed.
2. The hero: the data file holds exactly the eight pairs 1a, 1b, 1c, 2a,
   2b, 2c, 3a, and 3b (a unit test of the schema fails on a missing,
   duplicate, or extra identifier); each of them renders correctly (an
   end-to-end test sets the `hero` parameter to each of the eight); the HTML
   carries the one default pair, which is what remains with scripts
   disabled; the swap causes no layout shift; there is one `<h1>` and it
   does not change after load; the script makes no request and uses no
   storage; no copy is written on the page.
3. The hero image has its labels as text, no text, number, or formula in
   its pixels, registered parts, and a recorded visual check; the owner's
   approval is on the Issue.
4. "Run the code" starts with the three routes, whose headings are the
   first three in the table of contents; the verified-command checks pass
   unchanged.
5. "How we verify the science" exists with three examples whose targets
   the build checks (a test shows that a missing target fails the build);
   the Evidence map is reachable from it and from the footer.
6. Every count, name, and sentence about the site is true of the
   published site at that commit, confirmed by a reviewer who did not
   write the page; the pages are complete without JavaScript, pass the
   accessibility scan, reflow at 320 CSS px, and are within the payload
   budget.
7. The rendered review has its three parts on the Issue; the selected
   skills and their observable effect are recorded.
8. The full verification run passes, run last.

**Risk.** High (Level 3 by trigger: the opening figure and the Part A,
Part B, and capstone blocks of F124 leave Home with the tests that assert
them, a removed or changed assertion of ADR 020 decision 1 that the
scripts detect; otherwise Level 2, pages, `pbc.authoring`, a small
script, and data; ADR 018's amendment is made by this planning, not by
the feature). The tests of the figure's function, energy check, and
provenance in `src/pbc` stay.

**Detailed implementation plan expected.** Yes, short: the hero data
schema and script, the selection rule of the examples, the verify page's
examples and their checks, the tests.

### F135 — The glossary in context and a Suggest an improvement link on every lesson, through pre-filled issue forms

**Issue.** #340 (created 2026-10-29, before this planning).

**Source.** Change request "What I want", item 4, and "Decisions already
taken" (no backend); requirements decision 40 ("Glossary and
contribution"), "UX expectations" ("Shared templates"), unresolved
question 16; ADR 021 decisions 5 and 6.

**Problem.** The glossary resolves a lesson's outside prerequisites, but a
long alphabetical page is documentation, not something a learner opens.
Contributing is possible only from the Contribute page, with no way to
reach a form from the lesson where a mistake was seen.

**Goal.** The glossary as a contextual resource inside lessons, and a
discreet "Suggest an improvement" link at the end of every lesson that
opens the right GitHub issue form with the lesson already named; no
backend, no secret, no script.

**User-visible outcome.** In "Before you begin" a learner opens the short
definition of an outside prerequisite in place and follows it to the
glossary; at the end of a lesson they choose scientific correction,
report a problem, or propose a change, and land on GitHub's form with the
page field filled in.

**In scope.**

- **Glossary**: in "Before you begin", each outside prerequisite with a
  glossary entry shows its short definition in a native disclosure (or
  the `popover` attribute, if it needs no script) from
  `site/glossary.yaml`, with a link to the entry on the glossary page;
  nothing written twice; the glossary page, its address, and the checks
  that resolve prerequisites against it unchanged.
- **Suggest an improvement**: one line in the last section of every
  published lesson, three links to the matching forms of
  `.github/ISSUE_TEMPLATE/` (`scientific-correction.yml`, `bug.yml`,
  `feature.yml`, or the form the plan names for "propose a change"), each
  with the lesson's canonical address pre-filled through the query
  parameter of a field `id`; an `id` added to the page field of each form
  that lacks one, and the field added where a form lacks it.
- **Contribute**: the same three links at the top, and a sentence that a
  GitHub account is needed and that issues are public; the existing
  `forms_list()` of `pbc.authoring.educators` reused.

**Out of scope.** A form on the site that creates issues without a GitHub
account (requirements, unresolved question 16; it needs a server and a
stored credential and would amend a core requirement); a change to the
glossary's content; any lesson's scientific content.

**Dependencies.** F132 (the footer), F117 (the lesson's last section,
the experiment footer of ADR 016), F42 (the glossary and "Before you
begin"), F12 (the issue forms), F57 (the scientific-correction form, which
extended F12's set); never in flight with F133 (the same lesson template
and shared CSS).

**Visual deliverables and skills.** Page and layout (the disclosure and
the link line): the approved design skills as the plan selects them, or
none with the reason; no artwork, diagram, or figure.

**Acceptance criteria.**

1. In a published lesson with outside prerequisites, each prerequisite
   with a glossary entry shows its definition on demand without a script
   and links to the glossary page; a prerequisite without an entry is
   unchanged; the glossary and prerequisite checks pass unchanged.
2. Every published lesson ends with the improvement links, and following
   one opens the GitHub issue form with the lesson's address filled in,
   shown three ways: (a) each pre-filled field of the forms has an `id`;
   (b) a unit test fails when a generated link names a form that does not
   exist or a parameter that is not an `id` of a field of that form; (c)
   one manual check in a real browser on github.com, recorded in the
   completion evidence, that the page field shows the lesson's address
   (CI cannot reach github.com).
3. The Contribute page carries the three links and says that a GitHub
   account is needed and issues are public.
4. No new script, no storage, and no request from the page; the
   accessibility scan passes.
5. The verification the targeted run reports passes, run last (the base
   run at least, since every lesson page's display changes; the full run
   where `pbc.authoring` or the template makes it a shared change).

**Risk.** Medium (Level 2: the lesson template, `pbc.authoring`, and the
issue forms under `.github/ISSUE_TEMPLATE/`, which `guardrails.conf` does
not protect at the base commit). The test trigger of ADR 020 decision 1
does not fire by design: the feature adds tests and removes or replaces
none, since its criteria keep the glossary, prerequisite, and
educators' checks unchanged and the forms only gain a field `id`. If the
implementation changes an existing assertion, the scripts raise it to
Level 3, as for any other trigger.

**Detailed implementation plan expected.** No; a short plan.

## Candidate mapping

Every candidate of the change request and its outcome. "Kept" means a
feature with the candidate's number; "extends" means the work is an
obligation of an existing feature; "absorbed" means another feature
carries it; "deferred" means no feature until a trigger (see "Deferred
research candidates").

| Candidate | Outcome | Final ID | Consolidation decision |
|---|---|---|---|
| F16 Counterexample hunter | Kept | F16 | Inside the ADR 004 harness; depends on the F46 contract for what counts as a counterexample. |
| F17 Additional Lean mechanics proofs | Kept | F17 | Also the source material for F56 and F22. |
| F18 Multi-agent scientific review | Kept | F18 | Shares the validation contract with F46; harness loop run per reviewer, no new framework. |
| F19 Scientific evidence map | Kept | F19 | Generated from the claim markup of F28 (its reserved `evidence` attribute); waits for all lessons in format 2. |
| F20 Autonomous experimental design | Kept | F20 | Built on F16 and F23 rather than separate tools. |
| F21 Interactive Lean exercises | Kept | F21 | Needs an ADR for exercise stubs outside the checked library. |
| F22 Agent-assisted formal theorem proving | Kept | F22 | Under the F45 workflow and ADR 010. |
| F23 Inverse physics / parameter discovery | Kept | F23 | Shares `pbc.data` fitting with F51; teaches a different question than F20. |
| F24 Optional local AI physics tutor | Deferred | retired | Not selected: an expensive optional workflow that must not block the deterministic F13 and F14; trigger below. |
| F25 Homepage narrative | Kept | F25 | Consumes the F57 attribution text; coordinated with F44 styles. |
| F26 Generated prerequisite graph | Kept | F26 | Consumer of the F37 metadata. |
| F27 Learning path cards and difficulty scale | Kept | F27 | Consumer of the F37 metadata and F44 styles. |
| F28 Reusable lesson introduction/template | Kept, widened to format 2 | F28 | Carries the Section 11 standard, the reference register, claim and figure labels, the self-check, and the M1 pilot. |
| F29 Mechanics editorial pass M1 to M4 | Kept | F29 | M1 as the beginner pilot of the standard, after the M5 pilot. |
| F30 Mechanics editorial pass M5 to M8 | Kept | F30 | M5 first as the research-backed pilot, reviewed before M6 to M8. |
| F31 Agent/Lean editorial pass | Kept | F31 | |
| F32 Mechanics diagrams M1 to M4 | Kept | F32 | Diagrams drawn by code, labelled conceptual; no image files. |
| F33 Mechanics diagrams M5 to M8 | Kept | F33 | |
| F34 Agent/Lean diagrams | Kept | F34 | |
| F35 Code explanation and snippets | Kept, as tooling | F35 | Annotated excerpts; the prose work is in the editorial passes. |
| F36 Numeric tables/output | Kept, as tooling | F36 | The table helper; applied by the editorial passes. |
| F37 Course navigation | Kept, widened | F37 | Owns the metadata extension (course, methods, outcomes, related) as the single source of truth for F26 and F27. |
| F38 Progressive hints and solutions | Kept | F38 | Markup only, no quiz or progress; F13 may wrap it. |
| F39 Unified local setup and run recipes | Kept, plus link check | F39 | Also carries `scripts/check-links.sh` (Section 11.4, F39 row). |
| F40 Reproducibility UX | Kept | F40 | |
| F41 Self-hosted search | Kept | F41 | |
| F42 Before you begin and glossary | Kept | F42 | |
| F43 More interactive physics widgets | Kept, as science-first components | F43 | At most four components, one per lab that needs it (Section 8.3). |
| F44 Visual design and accessibility system | Kept | F44 | Includes the footer slot for F57 and the payload check. |
| F45 Agent-assisted simulation development | Kept, plus the shared workflow | F45 | The one coding-agent workflow (Section 12: F45 + F55). |
| F46 Scientific code verification and debugging | Kept | F46 | Owns the validation contract F18 and F45 reuse. |
| F47 Automated scientific analysis pipelines | Kept, as a lesson | F47 | Its analysis core is F51's (Section 12: F47 + F51). |
| F48 Reproduce an open physics paper | Absorbed | retired, into F49 | One capstone whose subject is a paper reproduction (Section 12: F48 + F49). |
| F49 Multi-agent computational research capstone | Kept, merged with F48 | F49 | |
| F50 Experimental dataset registry + feasibility | Kept, includes the spike of Section 8.2 | F50 | The spike is its first deliverable, not a new feature. |
| F51 Experimental methods and visualization foundations | Kept, merged with F47's core | F51 | |
| F52 Optical diffraction lab | Kept, conditional | F52 | The record page shows a CC BY 4.0 licence field next to a copyright line; the change request flags redistribution as unclear; the gate decides. Needs a waves-and-optics course (F15 if the human chooses it, else a later course feature). |
| F53 Flow measurements / PIV lab | Kept, conditional | F53 | Needs a compact subset and a course that exists (F15 if the human chooses fluid dynamics, a later course feature, or a `mechanics` framing its Issue justifies under ADR 008). |
| F54 Electromagnetic wave measurement lab | Kept | F54 | The compact fallback first lab if F60 is deferred, once F15 or a later course feature has given it a course; no placement by method tag (ADR 008). |
| F55 Agent-assisted experimental physics | Kept, as a lesson | F55 | Uses the F45 workflow; no second workflow. |
| F56 Experimental model formal verification | Kept | F56 | Lessons in the `lean` strand tied to a lab; no new strand. |
| Section 8.2 feasibility spike | Extends | F50 | |
| Section 8.3 visualization system | Extends | F43, F51, F44 | |
| Section 8.5 long-term dataset candidates | Deferred | none | Cards as `survey-only` in F50; triggers below. |
| Section 9 Instructor packs | New feature | F59 | Independently testable; reuses F28, F57, F12. |
| Section 10 JIDAI identity and community (repository surfaces) | New feature | F57 | One small feature; F25 and F44 consume its text. |
| Section 10 JIDAI.nl portfolio page | Not selected | none | A company-site task outside this repository. |
| Section 10 `jidai-nl` organization profile link | Not selected | none | A human action on GitHub outside this repository; no transfer. |
| Section 10 repository transfer or subdomain | Not selected | none | A separate migration decision; excluded by the requirements. |
| Section 11 research-backed editorial standard | Extends | F28, F29, F30, F31, F35, F36, F42, F39; ADR 009 | No new numbered feature for the standard (Section 3H). |
| Section 11.4 F12 research stage | Extends | F12 (delivered) by F28's protocol | The protocol in `docs/authoring.md` applies to agent-drafted content; no workflow change. |
| Section 13 R0 "finish active work" | Done | F10, F11, F12 delivered | Remaining human steps in `docs/release-readiness.md`. |
| CI budget overrun (release readiness) | New feature | F58 | The second response of ADR 003. |
| Gravitational-wave lab (Section 8.1, 13) | New feature | F60 | The planner's recommended first lab, conditional on F50. |

## Slot mapping (change cycle `final-curriculum`)

Every slot of the reference curriculum (requirements decision 23) with the
lesson that fills it or the feature that will. "Published" names a lesson
`id`. A lab is published only after its dataset's go decision; a capstone's
historical comparison (FL10) is gated separately and is not a lab. The
teaching order inside a course may differ from the label order, as the
change request states (T6, T10, T11; EM4 and EM6 to EM9; FL1, FL4, FL9,
FL5, FL10; AST10 before AST4).

### Part A, 81 slots

| Course | Slot | Working title | Kind | Status, feature |
|---|---|---|---|---|
| mechanics | M1 | Kinematics as a program | lesson | Published, `kinematics` (F02) |
| mechanics | M2 | Newton's laws | lesson | Published, `newtons-laws` (F04) |
| mechanics | M3 | Projectile motion with drag | lesson | Published, `projectile-with-drag` (F04) |
| mechanics | M4 | Harmonic oscillator | lesson | Published, `harmonic-oscillator` (F05) |
| mechanics | M5 | Numerical integrators | lesson | Published, `numerical-integrators` (F05, F30) |
| mechanics | M6 | Energy conservation | lesson | Published, `energy-conservation` (F06) |
| mechanics | M7 | Momentum and collisions | lesson | Published, `momentum-and-collisions` (F06) |
| mechanics | M8 | Kepler orbits | lesson | Published, `kepler-orbit` (F06) |
| mechanics | M9 | Double pendulum and chaos | lesson | F68 |
| mechanics | M10 | Lagrangian mechanics | lesson | F68 |
| mechanics | M11 | Hamiltonian mechanics | lesson | F68 |
| mechanics | M12 | Resonance and driven oscillators | lesson | F68 (coordinated with F45) |
| mechanics | M13 | Many-body gravitation | lesson | F69 |
| mechanics | M14 | Nonlinear dynamics and bifurcations | lesson | F69 |
| mechanics | M17 | Rotational motion, torque, and angular momentum | lesson, revision 2 | F69 |
| mechanics | M15 | Experimental: real pendulum or accelerometer data | lab | F83, gated |
| mechanics | M16 | Experimental: GW150914 gravitational-wave strain | lab | Published, `gravitational-wave-strain` (F60) |
| thermodynamics | T0 | Gas from simple agents | lesson | Published, `particles-in-a-box` (F11); `course` and `slot` set together by F70, no slot before |
| thermodynamics | T1 | Random walks and diffusion | lesson | F70 |
| thermodynamics | T2 | Kinetic theory of gases | lesson | F70 |
| thermodynamics | T3 | Entropy and thermodynamic equilibrium | lesson | F70 |
| thermodynamics | T4 | Ising model and phase transitions | lesson | F75 |
| thermodynamics | T5 | Molecular dynamics | lesson | F75 |
| thermodynamics | T6 | Heat conduction and diffusion | lesson, enhanced in revision 3 | F76 |
| thermodynamics | T9 | Heat engines and thermodynamic cycles | lesson, revision 2 | F75 |
| thermodynamics | T10 | From finite differences to finite elements and meshes | lesson, revision 3 | F76 |
| thermodynamics | T11 | Applied capstone: thermal engineering of an AI accelerator | capstone, revision 3 | F87 |
| thermodynamics | T7 | Experimental: heat transfer measurements | lab | F84, gated |
| thermodynamics | T8 | Experimental: Brownian motion tracking | lab | F85, gated |
| waves | W1 | The wave equation | lesson | F71 |
| waves | W2 | Interference and resonance | lesson | F71 |
| waves | W3 | Refraction and Snell's law | lesson | F77 |
| waves | W4 | Polarisation and Malus's law | lesson | F77 |
| waves | W5 | Diffraction and imaging | lesson | F77 |
| waves | W6 | Inverse optics | lesson | F77 |
| waves | W9 | Sound waves, resonance, and the Doppler effect | lesson, revision 2 | F71 |
| waves | W7 | Experimental: real optical diffraction images | lab | F52, gated (unchanged feature; home `waves`) |
| waves | W8 | Experimental: wave flume measurements | lab | F74 (go decision exists) |
| electromagnetism | EM1 | Coulomb's law and electric fields | lesson | F72 |
| electromagnetism | EM2 | Lorentz force and charged particles | lesson | F72 |
| electromagnetism | EM3 | Faraday's law and induction | lesson | F72 |
| electromagnetism | EM4 | Maxwell's equations and FDTD | lesson | F78 |
| electromagnetism | EM5 | RLC circuits and resonance | lesson | F78 |
| electromagnetism | EM6 | Waveguides and electromagnetic resonances | lesson, enhanced in revision 3 | F78 |
| electromagnetism | EM7 | Experimental: microwave S-parameters | lab | F54 (go decision exists; unchanged feature; home `electromagnetism`) |
| electromagnetism | EM8 | Experimental: real RLC circuit measurements | lab | F86, gated |
| electromagnetism | EM9 | Applied capstone: adaptive phased-array beam steering | capstone, revision 3 | F80 |
| fluids | FL1 | Advection and diffusion | lesson | F73 |
| fluids | FL2 | Navier-Stokes fundamentals | lesson | F79 |
| fluids | FL3 | Vortex formation and flow around obstacles | lesson | F79 |
| fluids | FL4 | Shock waves and Burgers' equation | lesson | F73 |
| fluids | FL5 | Shallow-water equations | lesson, enhanced in revision 3 | F73 |
| fluids | FL6 | Particle-based fluid simulation | lesson | F79 |
| fluids | FL9 | Finite-volume methods and conservation laws | lesson, revision 2 | F73 |
| fluids | FL7 | Experimental: particle image velocimetry | lab | F53, gated (unchanged feature; home `fluids`) |
| fluids | FL8 | Experimental: real turbulence or flow measurements | lab | F108, gated |
| fluids | FL10 | Applied capstone: reconstructing the 2025 Kamchatka tsunami | capstone, revision 3 | F88 (comparison gated) |
| quantum | Q1 | Schrödinger equation | lesson | F89 |
| quantum | Q2 | Quantum tunnelling | lesson | F89 |
| quantum | Q3 | Quantum harmonic oscillator | lesson | F89 |
| quantum | Q4 | Spin and Stern-Gerlach measurements | lesson | F90 |
| quantum | Q5 | Quantum entanglement, Bell and CHSH | lesson, enhanced in revision 2 | F90 |
| quantum | Q6 | Open quantum systems and decoherence | lesson | F90 |
| quantum | Q7 | Experimental: atomic spectroscopy | lab | F102, gated |
| quantum | Q8 | Experimental: quantum measurement statistics | lab, enhanced in revision 2 | F103, gated |
| astrophysics | AST1 | Three-body problem | lesson | F91 |
| astrophysics | AST2 | Modified gravity | lesson | F91 |
| astrophysics | AST3 | Gravitational lensing | lesson | F91 |
| astrophysics | AST10 | Special relativity and spacetime | lesson, revision 2 | F92 |
| astrophysics | AST4 | Relativistic orbits | lesson | F92 |
| astrophysics | AST5 | Cosmic expansion and redshift | lesson | F92 |
| astrophysics | AST6 | Gravitational-wave chirp simulation | lesson | F93 (cross-links M16, L5) |
| astrophysics | AST7 | Exoplanet transit simulation | lesson | F93 |
| astrophysics | AST8 | Experimental: real exoplanet light curves | lab | F104, gated |
| astrophysics | AST9 | Experimental: galaxy rotation curves | lab | F105, gated |
| materials | MAT1 | Crystal lattices and phonons | lesson | F94 |
| materials | MAT2 | Electronic band structure | lesson | F94 |
| materials | MAT3 | Elasticity and deformation | lesson | F95 |
| materials | MAT4 | Defects and material properties | lesson | F95 |
| materials | MAT5 | Experimental: X-ray diffraction data | lab | F106, gated |
| materials | MAT6 | Experimental: stress-strain measurements | lab | F107, gated |

Count: 17 + 12 + 9 + 9 + 10 + 8 + 10 + 6 = 81, of which 16 labs and 3
capstones.

### Part B, 33 slots

| Path | Slot | Working title | Status, feature |
|---|---|---|---|
| physics reasoning and scientific agents | AI0 | LLM agent designs a projectile experiment | Published, `agent-experiment` (F09) |
| physics reasoning and scientific agents | AI1 | Agent-assisted physics simulation development | F45 (unchanged feature) |
| physics reasoning and scientific agents | AI2 | Scientific code verification and debugging | Published, `verifying-scientific-code` (F46) |
| physics reasoning and scientific agents | AI3 | Counterexample hunting | Published, `counterexample-hunter` (F16) |
| physics reasoning and scientific agents | AI4 | Multi-agent scientific review | Published, `scientific-review` (F18) |
| physics reasoning and scientific agents | AI5 | Agent-assisted real experimental physics | F55 (unchanged feature) |
| physics reasoning and scientific agents | AI6 | Multimodal physics reasoning (still images; enhanced in revision 2) | F96 |
| physics reasoning and scientific agents | AI7 | Interpretable physics explanations and constraints | F96 |
| physics reasoning and scientific agents | AI8 | Physical reasoning from video (revision 2) | F97 |
| scientific law discovery | D1 | Black-box physics: discovering force laws | F66 |
| scientific law discovery | D2 | Physics without prior knowledge | F66 |
| scientific law discovery | D3 | Discovering modified physical laws | F66 |
| scientific law discovery | D4 | Discovering gravity from experiments | F99 |
| scientific law discovery | D5 | Unknown physical worlds | F99 |
| scientific law discovery | D6 | Inverse physics: parameter discovery and uncertainty (enhanced in revision 2) | Published, `inverse-physics` (F23) |
| scientific law discovery | D7 | Symbolic regression for physical laws | F67 |
| scientific law discovery | D8 | Discovering differential equations | F67 |
| scientific law discovery | D9 | Active experimental design (enhanced in revision 2) | Published, `experimental-design-agent` (F20) |
| scientific law discovery | D10 | Scientific discovery under measurement noise | F98 |
| scientific law discovery | D11 | Hidden forces and unobserved variables | F98 |
| scientific law discovery | D12 | Generalisation to unseen physical systems | F98 |
| scientific law discovery | D13 | Discovering conservation laws and physical invariants (revision 2) | F82 |
| physics agent benchmarking | EV1 | Physics reasoning benchmarks (enhanced in revision 2) | F100 |
| physics agent benchmarking | EV2 | Interactive discovery benchmarks (enhanced in revision 2) | F81 |
| physics agent benchmarking | EV3 | Agent versus non-agent baselines | F81 |
| physics agent benchmarking | EV4 | Robustness, cost, and sample efficiency | F101 |
| physics agent benchmarking | EV5 | Scientific failure analysis | F101 |
| autonomous scientific research | R1 | Automated physics analysis pipelines | Published, `automated-analysis-pipelines` (F47) |
| autonomous scientific research | R2 | Scientific evidence maps | F109 (the page is F19, delivered) |
| autonomous scientific research | R3 | Scientific literature and reproducible evidence | F109 |
| autonomous scientific research | R4 | Reproducing a physics paper with multiple agents | F49 (unchanged feature) |
| autonomous scientific research | R5 | Agent-driven materials discovery (enhanced in revision 2) | F110 |
| autonomous scientific research | R6 | Autonomous physics research challenge | F111 |

Count: 9 + 13 + 5 + 6 = 33.

### The Lean slot and the lessons beyond the baseline

| Slot | Working title | Status |
|---|---|---|
| L1 | Proving what the simulation showed | Published, `proving-what-the-simulation-showed` (F08) |
| none | Momentum in a collision, proved | Published, `collision-momentum-proved` (F17) |
| none | What symplectic Euler conserves | Published, `symplectic-euler-conserved-energy` (F17) |
| none | Lean exercises on your machine | Published, `lean-exercises-on-your-machine` (F21) |
| none | The chirp law, proved | Published, `chirp-law-proved` (F56) |
| none | Agent-assisted theorem proving | F22 (unchanged feature) |

Total: 81 + 33 + 1 = 115 slots; 119 lessons and more when complete, the
Lean lessons beyond the baseline included and never hidden.

### Enhancements of existing slots (revision 2), no new slot

| Enhancement | Where it is delivered |
|---|---|
| D6 identifiability, parameter correlations, held-out uncertainty | Delivered by F23 (`pbc.data.fit` and `pbc.data.inverse`) |
| D9 hypothesis-discriminating information gain under a budget, simulated only | Delivered by F20 (`pbc.agents.design`) |
| AI6 still-image affordances and counterfactuals | F96 |
| EV1 physical-tool understanding separated from software interfaces | F100 |
| EV2 full, partial, and no prior-knowledge comparisons under one protocol | F81, on F65's protocol |
| R5 physical multi-objective constraints | F110 |
| Q5 Bell and CHSH inequalities, with Q8 using eligible data only if the gate approves it | F90 (Q5) and F103 (Q8) |

## Experimental data choice

Planner's recommendation for the first measured-data lab, to be confirmed
or overturned by the evidence of the F50 spike:

1. **First lab: GW150914 strain (F60), as a mechanics-course extension of
   M8.** Reasons: the data is small (about 1 MB per detector for 32 s at
   4096 Hz), calibrated, CC BY 4.0 with a stated acknowledgement, in HDF5
   and plain text (readers that lock as ordinary Python dependencies); the
   physics connects to the published course through the two-body orbit of
   M8 and a Newtonian-order chirp model, so it belongs to a course that
   exists instead of waiting for a second course; the measurement-to-model
   loop is complete (measured strain, disclosed filtering, model, residuals,
   a typed claim); the visual is immediately understandable. Risk to
   verify in the spike: the processing steps must be explained so that a
   whitened signal is never presented as the measurement, and the model's
   scope must be stated honestly.
2. **Fallback: NPL S-parameters (F54), after F15.** (Since
   `final-curriculum`: F15 is dropped and F54's course is `electromagnetism`,
   created by F72; the rest of this item is history.) The most compact and
   technically robust dataset (3.1 MB, Touchstone, CC BY 4.0), but it needs
   RF background the course does not teach and has no published course to
   belong to, and ADR 008 allows no lesson without a primary course. It
   becomes the first lab only if F60 is deferred or rejected by the spike
   and F15 has chosen an electromagnetism or waves-and-optics course for it;
   the fallback path therefore runs through F15 before F54, and the F50
   dossiers are the evidence for that choice.
3. **Bridge for F15: the Aalborg wave flume.** (Since `final-curriculum`:
   F15 is dropped; the flume is W8 of the `waves` course created by F71, and
   F52's home is the same course; the rest of this item is history.) The strongest
   measured-versus-modelled set (CC BY 4.0, measured and CFD series), but
   78.6 MB and a waves subject; it is the natural first lab of a waves and
   optics course if the human chooses that topic for F15, and the spike's
   dossier is the evidence for that choice. Once F15 chooses waves, the
   flume is the bridge: its course is the home F54 publishes in, and the
   fallback of item 2 no longer waits.
4. **Not first:** optical diffraction (RAR archives, 46 MB and more,
   photographs), cylinder-wake PIV (1.1 GB MAT), and every Section 8.5
   candidate, for size, format, or course reasons recorded in their cards.

Permissions, sample-file evidence, plotting approach, visual accessibility,
and the size and CI budgets are the spike's deliverables (F50 acceptance
criteria 3 and 5), not assumptions of this roadmap.

## Lesson editorial decision

The Section 11 standard is adopted as written into the requirements and
the architecture (format 2), with ADR 009 for the references. The audit of
the eleven published lessons on 2026-10-09, from their sources at `2f011ea`,
found these evidence-backed improvements, which the pilots and passes
address:

- **No external reference anywhere.** No lesson body contains a URL; M5's
  "Further reading" names two books without a section, a URL, or a reason.
  The standard asks for curated depth paths at the relevant concept, with a
  reason, from the register.
- **Console tables everywhere.** More than forty fixed-width `print()`
  tables carry the numeric results; none is a semantic table with header
  cells (F36).
- **Descriptive captions.** Every figure has a caption and alt text, but
  the interpretation sits in the prose after it, and captions do not
  state the figure's status (F28 figure status, interpretive captions).
- **Hand-typed numbers.** M8 has no inline expression and types every
  number in prose; M2, M3, M4, M6, M7, and A1 type approximate values
  ("about one per cent", "about forty thousand steps") and some alt texts
  carry digits (M6 line 376, M8 line 458, A1 line 339) (F28 check).
- **Unmotivated statements.** The exponential drag solution and the
  Reynolds regimes in M2, the drag law and interpolation bound in M3, the
  "same algebra shows" rotation in M4, the period series and the symplectic
  bound in M6, the elastic-collision formulas in M7, the orbital elements
  and Kepler's equation in M8, the virial correction and the Rayleigh
  distribution in the gas lesson, the residual claim in L1 (editorial
  passes).
- **Limits.** Only L1 has a dedicated "What the proofs do not cover"
  section; M6 and the gas lesson have a subsection; the others state limits
  only inside the assumptions (format 2 `limits`).
- **Openings.** Most lessons open with a physical question or a link to an
  earlier result; A1 and the gas lesson open with the technique (F31).
- **Code sections.** M6, M7, and M8 show four or more excerpts under one
  sentence; no excerpt points at the physically important line (F35).
- **Method distinctions are correct today.** M5 states and implements
  velocity-first symplectic Euler, velocity Verlet with a predicted
  velocity, and classical fixed-step Runge-Kutta 4, and nothing uses
  SciPy's adaptive solver; the passes must keep it so when sources are
  added.

The change cycle `pbc-planning-change-four-workstreams` (requirements
decision 32) adds the editorial voice on top of this standard: F114 (the
style guide), F115 (the pilot on mechanics 01 to 05, human-approved
before expansion), and F116 (the principles in the authoring workflow),
under "Phase 5" below. They change how a lesson reads, never what it
claims.

Candidate sources for M5 (Section 11.3) enter the F30 research as inputs
with documented fitness to check, not as links to insert: each is reopened,
compared with at least one alternative, and recorded in the register only
if it adds a derivation, intuition, or figure the lesson lacks and matches
the exact variant the lesson implements.

## Deferred research candidates

Not features. Each has a trigger for revisiting; until then no Issue.

| Candidate | Why deferred | Trigger to revisit |
|---|---|---|
| F24 Optional local AI physics tutor | Optional, expensive, and must not block the deterministic F13 and F14; the requirements forbid a hosted tutor | F13 and F14 delivered and a learner need recorded in Issues that hints (F38) and recommendations (F14) do not meet |
| CERN CMS event displays (Section 8.1) | A showcase, not a course commitment; CC0 on record | A particle-physics course chosen for F15 or a later course, and F43's 3D viewer justified by it |
| Solar, stellar, and exoplanet observations (SDO, Gaia, TESS) | Observational labs with calibration and selection effects beyond mechanics | A course that needs them; F51 readers for FITS justified by a go decision |
| Rostock PIV + fluorescence | Phase-averaged data; advanced fluid visualization | F53 delivered and a demand for a second fluid lab |
| ALMA DSHARP, ALMA HL Tau, Euclid Q1 | Large files, specialist calibration | An astrophysics course under F15 |
| Electron diffraction, UKAEA MAST, superconducting-qubit tomography, IR interferograms, NIST IR spectra, LenslessPiCam, Haidinger rings, shock-tube schlieren | Size, specialism, rights, or provenance questions recorded in their `survey-only` cards | A course or lab that needs them and a feasibility spike with a go decision |
| JIDAI.nl portfolio page | Outside this repository | A company-site task, tracked there |
| `jidai-nl` organization profile link, repository transfer, project subdomain | Outside this repository; transfer excluded by the requirements | A separate migration decision with its own review |
| A scheduled link-check workflow | Would add a workflow trigger | Link rot found faster than quarterly manual runs catch it, and a review of the trigger |

Deferred by the change cycle `final-curriculum` (2026-10-12), with no
feature and no Issue (change request sections 1, 4.1, and 12, decision 11;
requirements non-goals):

| Candidate | Why deferred | Trigger to revisit |
|---|---|---|
| Nuclear and particle physics (4 slots), plasma physics (3), geophysics and climate physics (4): the 126-slot extension | Outside the core curriculum by the requirements | A separate planning decision after the reference curriculum is substantially published |
| Battery thermal runaway, Formula 1 aerodynamics | Inspiration for T11 and FL2/FL3 only; not selected | A separate planning decision; never an implicit capstone |
| JWST atmospheric retrieval for A7 | Discussed, not selected; A7's exoplanet lessons stay as enumerated | A separate planning decision |
| Any capstone for A1, A3, A6, A7, or A8 | The requirements limit capstones to T11, EM9, and FL10 | A requirements change |
| Physics-informed machine learning, a mathematics curriculum, a generic AI or machine-learning curriculum | Excluded by the requirements | A requirements change |
| Embedding external benchmark assets (NewtonBench, PhysGym, DiscoverPhysics, GravityBench, PhysBench, PhysToolBench, ...) | Inspiration for original contained tasks; licences and assumptions unchecked | A licence and assumption review recorded on a card, lesson by lesson |
| Selecting the Lean build with ADR 014 | Requirements, unresolved question 8 | The human's decision with or after F61 |

## Execution order and first-wave release plan

By dependency, not by number. A wave is a grouping for planning; the human
picks the next feature among those whose dependencies are done.

| Wave | Order within the wave | Outcome |
|---|---|---|
| R0 | F58 | CI within budget, recommended before pages are added but not a gate for R1 (the per-check budgets and ADR 003 decision 6 stay the guard); the release of the MVP tagged by the human (`docs/release-readiness.md`) |
| R1 | F44, F57, F37, F35, F36, F39 in parallel worktrees; then F25 (after F57), F26 and F27 (after F37); then F28 (M1 template pilot); then F30's M5 pilot; then F29 (M1 editorial), F30 (M6 to M8), F29 (M2 to M4) | A clear, honest, identified site with the editorial standard proven on both pilots and the mechanics course migrated; a release "clarity" tagged after it |
| R1, beside | F50 spike (no page) | The go, defer, or reject decisions and the first-lab confirmation |
| R2 | F42, F38, F40, F41, F31, F32, F33, F34, F59; F46, F45, F16, F17 | All lessons in format 2 with diagrams, hints, glossary, search, one instructor pack; trustworthy scientific coding with one counterexample lesson and further proofs |
| R3 | F51, then F60 (or F54 as the fallback, after F15 has chosen its course; since `final-curriculum`, F15 is dropped and F54 waits for F72), F43's first component | The first measured-data lab published after its gate |
| R4 | F54, F53, F52 as their courses exist (F15 gives at most one of them a course; the others wait for a later course feature, or for F53 a justified `mechanics` framing; since `final-curriculum`, F15 is dropped and the courses are F72, F73, and F71, with no `mechanics` framing); F55, F23, F47, F18, F19, F56 | Evidence and advanced labs |
| R5 | F20, F21, F22, F49 | Research capstones |

Phase 4, by dependency; the first wave stays reviewable because every
feature in it is a tooling change with tests (F61, F113, F62, F63) or one
page with accuracy checks (F64). No lesson of the phase is drafted before
F61 and F62 have landed, no lesson that takes the count past 32 before
F113 has [since 2026-10-15: past 45 before the owner's further decision,
under the interim full-run gate that replaced this sentence; F113 stays
paused], and no lesson of waves C2 to C4 before F64 and F113 have (the
gates under "Phase 4"); there is no cost exception.

| Wave | Order within the wave | Outcome |
|---|---|---|
| C0 | F61 and F62 in parallel worktrees; F113 after F61 (paused since 2026-10-15); then F63; then F64 | Verification proportional to a change within the typical-pull-request budget (12 minutes when planned, 20 minutes since ADR 015); a full run that fits the timeout at 110 lessons (open: F113 paused, ADR 017 proposed, the interim gate under question 10); eight courses, the reference curriculum, and the slots; verified previews; the course-first Learning Path, before the bulk of the lessons |
| C1 | F65 (may start during C0); after F61 and F62, and after F113 once the lesson count would pass 32: F66 and F67; F68, F70, F71, F72, F73 in parallel worktrees; F69 after F68; F74 after F71; F52, F53, F54, F45, F55 as their dependencies are met | The discovery foundation and its first lessons; the first lessons of thermodynamics, waves, electromagnetism, and fluids; advanced mechanics; the second measured-data lab (W8, go decision in hand) and the already planned labs as their courses exist |
| C2 | After F64 and F113: F75, F76 after F70; F77 after F71; F78 after F72; F79 after F73; F80 after F78; F81, F82 after the discovery lessons; F83 to F86 through their gates | Core subject expansion, the finite-difference to finite-element bridge, conservative fluid methods, the phased-array capstone, the first benchmarks, invariant discovery, and gated labs |
| C3 | After F64 and F113: F87 after F76; F88 after F73; F89 to F95 by dependency; F96, F97, F98, F99, F100, F101; F102 to F108 through their gates | The thermal and tsunami capstones (the tsunami comparison only after its gate), quantum, astrophysics with relativity, materials, the remaining reasoning, discovery, and benchmarking lessons, and gated labs |
| C4 | After F64 and F113: F109, F110, F111; F49 and F22 as their dependencies are met; F112 after every lesson feature of the phase | The research capstone, the last path lessons, and the completion audit, which declares completion only when no core slot is outstanding |

Phase 5, the change cycle `pbc-planning-change-four-workstreams`
(2026-10-15), as four workstreams that run beside each other in separate
worktrees. The budget and documentation work does not wait for the
approval that expands the editorial pilot; the verification work never
shares a feature with the editorial pilot. Where F117, F118, and F120
depend on F61, "F61" means its delivered selection, base, and regenerated
context (pull requests #152 to #166), not the closure of Issue #147: F61's
criterion 9 is recorded by F118 under unresolved question 10 and its F113
clause is paused, so the rule that a feature starts when its dependencies
are done is met for them by the delivered pull requests.

| Workstream | Order within it | Outcome |
|---|---|---|
| Editorial (change 1) | F114; then F115 (one pull request per lesson or per pair, the human's choice), reviewed individually and as a sequence; the human's approval of the pilot recorded on F115's Issue; then F116 | A documented, reusable editorial voice, proven on mechanics 01 to 05, inherited by future lessons through the authoring workflow; expansion beyond the pilot is a later decision, not a feature of this roadmap |
| Learner instructions (change 2) | F117 in reviewed steps: the entry-point contract and the setup page, the entry points of the published lessons behind the unchanged footer, then the switch of the footer and the check | Every published lesson runs its experiment from a clone with Git and uv alone; no maintained document instructs anyone to rebuild or preview the website |
| Verification (change 4) | F118 first and quickly (its record of the measured full run at the current lesson count is what the owner's interim full-run gate rests on); then F119 and F120 in parallel worktrees; F121 only after the owner accepts ADR 017 | The audit with coverage evidence, the measured full run and the interim gate, the removals with regression evidence, the staged evidence and the decision record; incremental `main` only if accepted |

Every lesson feature of waves C1 to C4 that takes the count past 32
waits for the interim gate F118 records and the owner approves, for
F121, or for F113 resumed (the amended full-run gate under "Phase 4");
since 2026-10-15 that gate is recorded (60 minutes for the one `build`
job, up to 45 lessons).

Phase 6, the change cycle `scientific-atelier-atlas` (2026-10-17), by
dependency. The skills come first; the preview (the foundations with one
lesson, the home page, the static atlas, the interaction) is inspected by
the owner before the rollout; the pilots run beside the preview once the
skills exist; the pendulum waits for the owner's decision. Every feature
of the phase that changes a shared input is a full run on each pull
request and adds no lesson.

| Wave | Order within the wave | Outcome |
|---|---|---|
| Atelier 0 | F122, with the owner's approval of each candidate's outcome; nothing else of the phase before it | The audited, pinned skills, the project-owned visualization skill, the skills configuration check, and the contract |
| Atelier 1, the preview | F123 and F125 in parallel worktrees after F122; F124 after F123 and F125 (its capstone highlights read the manifest); F126 after F123 and F125; the owner's review of the preview (home, atlas, one lesson) at desktop, tablet, and phone widths recorded on the Issues of F124 and F126, with the display label and the navigation wording decided | The atelier's foundations on every page, the home page with its verified opening figure, the atlas with its manifest and its interaction, one lesson in the reading column: the end-to-end preview, inspected before any broad rollout |
| Atelier 2 | F127 after the preview gate, by its migration plan, sequenced with F115 and the lesson features in flight; F129 after F122, beside the preview, with its figure pilot outside mechanics 01 to 05 or sequenced with F115 | The rollout to every course, lesson, and supporting page with the owner's final visual acceptance; the two skill pilots and the owner's decision on authoring integration |
| Atelier 3, optional | F128 when the owner decides unresolved question 14 | The validated interactive pendulum on the home page |

Beside the atelier, the order the change request suggests (section 11)
for the rest of the roadmap: the fix of Issue #206 and F117's post-merge
evidence (criteria 7 and 8, the follow-ups #203 and #204), because no run
on `main` passes until #206 merges and every feature needs a passing
`main`; F114's tracking reconciled and the editorial pilot F115 and the
integration F116; the runner-equivalence evidence and the owner's decision
on F120 and F121, with F113 paused unless resumed; the eligible lesson
features within the interim capacity, reassessed before 45 lessons; and
F112 for completion reporting only when the slots and the checks support
it. This is a scheduling recommendation, not a gate: nothing of the
atelier requires the verification work to finish first, and no lesson
waits for the atelier.

Phase 7, the change cycle `risk-proportionate-workflow` (2026-10-19):
two features, strictly one after the other, never beside another change
to the workflow scripts, each Level 3 with the owner's approval of its
diff. Nothing of it starts before this planning and ADR 020 are approved;
features in progress (F123) finish under the contracts they started with,
except that the protected list of `guardrails.conf` and the code-owner
rule apply at the merge gate to every pull request finished after F130's
merge (ADR 020, Status; "Phase 7"). On 2026-10-19 the owner accepted, by
approving the round 4 revision of this planning's review (11:42 UTC),
that the merge approval gate is the one exception to the rule of
requirements decision 39 that a feature in progress finishes under the
contracts it started with; the requirements are not edited for it.
Lesson features and the atelier are not blocked by it and run beside it
in their own worktrees, under the workflow of the day they started.

| Wave | Order within the wave | Outcome |
|---|---|---|
| Workflow 1 | F130, after the approval of this planning; then two features of any kind run under its rules and their effect is recorded on its Issue | Pending later-gate evidence committed and published without an owner exception; the risk level derived and refused to lower; the merge-gate verification that refuses every forgeable approval; quick partial feedback for Level 3 with an unchanged final acceptance; the budget policy where the checks read it; the time log |
| Workflow 2 | F131, after F130 is merged and the two features are observed; then the pilot of five features and the six measurements recorded on its Issue | The traceable chain of delta reviews for Level 2 with every finding's disposition, the fingerprint closed, mechanical triage of minor and suggestion findings, Level 3 full in every round |

The owner's actions of mechanism A (ADR 020 decision 3) are performed by
the owner at any time; from the day they exist the merge gate is GitHub's,
and until then the present practice continues.

Phase 8, the change cycle `site-navigation-and-atlas` (2026-10-30), by
dependency. Each feature changes shared inputs and is a full run; F133 and
F135 change the same lesson template and CSS and are never in flight
together; lesson features run beside the phase in their own worktrees and
rebase on what merged before them. F127 (the rollout) waits for the
phase.

| Wave | Order within the wave | Outcome |
|---|---|---|
| Navigation 1 | F132 | The four-item menu, the footer with the secondary pages, About up to date |
| Navigation 2 | F133 after F132, once #338 matches its block (the pre-start gate of the reconciliation notes), with the owner's approval of the twelve illustrations; F135 after F132, before F133 starts or after it is merged | The two-layer Course Atlas with its registered illustrations and the relationships on the lesson pages; the glossary on demand and the improvement links |
| Navigation 3 | F134 after F133, once #339 matches its block (the pre-start gate); then the owner's rendered pass on F133 and F134, the new preview gate of F127 | Home as a landing page with the hero, Run the code with three routes, How we verify the science |

Features F13 (#89) and F14 (#94) are delivered with their approved scope;
F64 keeps their progress marks and recommendations on the redesigned path.
F15 is dropped by `final-curriculum` (ADR 013 decision 7) and is never
scheduled: the courses of the labs F54, F53, and F52 are created by F72,
F73, and F71, and each lab starts when its course feature and its other
dependencies are delivered (the Phase 4 waves above). F12's workflow is
unchanged; the reference protocol of F28 applies to agent-drafted content
through `docs/authoring.md`.

The first wave stays reviewable because every feature in it is one of:
a tooling change with tests (F58, F35, F36, F37, F44, F39), a page with
accuracy checks (F25, F57, F26, F27), or one lesson at a time with two
independent reviews (F28, F30, F29). No feature in R1 implements a lab,
sends outreach, or creates content for the JIDAI website.

## Verification strategy for the next phase

What each new kind of artifact is checked by, extending `docs/architecture.md`
("Inside one verification run"). Every check is an entry in
`scripts/verify.conf`, runs identically locally and in CI, and fails on a
violating input shown by a test; the one deliberate exception is named.

| Artifact | Check | Feature |
|---|---|---|
| Lesson metadata (course, methods, outcomes, related, format) | Lesson source check: vocabulary, counts, existence; path page and header generated from it | F37, F28 |
| Format 2 parts: limits, self-check, claim labels, figure status, "Go deeper" keys, tables, computed numbers | Lesson source check for lessons that declare format 2; the default flips when every lesson has migrated | F28 |
| Reference register | Schema; every key used or reserved; no raw URL typed in a lesson source, with the helper-generated structural links of I22 exempt | F28 |
| External link validity | `scripts/check-links.sh`, on demand, never in `verify.conf` and never a merge gate (ADR 009) | F39 |
| Dataset cards and samples | Schema; caps; checksum; rights; a parsing test per sample; the build passes with data portals and external web hosts blocked | F50 |
| Measured-data figures | Status label from the sample's artifact type; measured-versus-model helpers; review | F51 |
| Diagrams | Executed cells, `conceptual` label, byte-stable | F32 to F34 |
| Page payload | Built-site check: initial 3 MB (raised from 1.5 MB by the project owner on 2026-10-10; the F44 block above is the historical record of the 1.5 MB that feature delivered and measured), on demand 3 MB, 5 MB in all; the budget table of `docs/architecture.md` is authoritative | F44, F43 |
| Widgets and components | The F07 checks plus the observed-value test and the keyframe | F43 |
| Coding-agent exercises | A test that no workflow, script, or check invokes an agent; the produced reference code and tests verified like any code (ADR 010) | F45 |
| Harness lessons | Replay without credentials; the ADR 004 boundary tests on every allowlist | F16, F18, F20 |
| Identity text | Built-site check that the canonical text is where it must be and nowhere else; `CITATION.cff` schema | F57 |
| CI structure | Every check in exactly one group; one aggregate required check; permissions | F58 |
| Local execution | `./scripts/verify.sh` unchanged in meaning; the setup page's required commands equal CI's (superseded by ADR 016 decision 5 and F117 on 2026-10-15: the page's Python-only commands are performed from its text in a fresh clone and the equality with `ci.yml` is dropped; see the row "The experiment entry point of a lesson" under the change cycle `pbc-planning-change-four-workstreams` below); optional workflows "not verified" | F39 |

Added by the change cycle `final-curriculum`:

| Artifact | Check | Feature |
|---|---|---|
| Lesson input digests and the selection | The digest changes for every input kind and is absent for an unfollowable lesson; the selection equals the changed lessons, or every lesson when a lesson has no digest or a shared input changed; a run on `main` and a run without a base verify everything; the published site is the fully verified one | F61 |
| The base of a pull request run | Published only after `verify` passed; retrieved read-only and accepted only when the run that produced it is a `push` run on `refs/heads/main` whose `verify` concluded with success, established from that run's recorded event, branch, and conclusion and never from the artifact's name or recency; its contents are data, nothing in it executed or read as configuration; complete and of the current format; an artifact of a pull request run or of a failed `main` run is rejected, and a missing or rejected base runs everything | F61 |
| The context of a page on a run with a base | An inserted or retitled lesson, or a changed prerequisite or related link, updates the unchanged pages that show it; every page names the commit of the run; the pages that are not lessons are never restored | F61 |
| The identity of the checks | A change to any input of the identity makes the run a full run that restores nothing from the base; no reproduction compares bytes with a result of the base; a base without an identity runs everything | F61 |
| The lesson shards and the assembly of a full run | The lesson shards (shares of the lessons derived from their count, not the division of `tests/e2e/shards.json`) cover every lesson exactly once within the lesson-shard size and equal the workflow's; every comparison of bytes is on the machine that computed them; the assembled site's lesson pages equal the shards' reproduced pages; a failing shard or an incomplete assembly fails `verify`; every job of a full run within 35 minutes at the measured size and in the projection to 110 lessons | F113 |
| The curriculum file and the `slot` field | Schema; 115 slots in the agreed counts; every slot known; no slot filled twice; a planned slot never linked or counted; the home page's planned list derived from it | F62 |
| The prerequisite graph across strands | A prerequisite in a later strand is accepted (the T0 to T2 progression, a mechanics lesson on a Lean lesson); a later prerequisite in the same strand and a cycle are rejected; the course view orders by the slot order of the curriculum file; every previous address resolves | F62 |
| Lesson previews | Exactly one per lesson, traced to its figure cell or the fallback, byte-stable, with alt text, within the path page's payload | F63 |
| The Learning Path page | Equals front matter and the curriculum file; every lesson reachable without scripts through its course and each path; every previous address and graph node resolves; accessibility, keyboard, payload, and width checks | F64 |
| Discovery environments and benchmark scores | The hidden truth unreachable through the allowlist; scores recomputed from frozen traces; baselines on the same environment and budget; no live call in CI | F65 and every path lesson |
| Capstone and finite-element lessons | The credibility claim and figure labels present; the reference comparison and the refinement figures generated by the build; the required path within the page budget on the pinned stack; an optional tool's artifact carries a card | F76, F80, F87, F88 |
| Generated motion clips | Reproduced by the build, labelled generated, within the on-demand budget, loaded after a user action | F97 |
| Curriculum completion | Every slot classified as filled, gated, removed by a recorded decision, or outstanding, adding up to 115; "complete" only with no outstanding slot; gated labs listed apart with their dossiers; sampled reproductions from a fresh clone; the manual passes recorded | F112 |

Added by the change cycle `pbc-planning-change-four-workstreams`:

| Artifact | Check | Feature |
|---|---|---|
| The editorial style guide and the rubric | Reviewed documents, not checks: the guide's examples name their source lessons and articles; the rubric names a weakness with evidence and an action, never only a score; the existing lesson source checks, claim and figure checks, and reproduction checks pass unchanged on every piloted lesson, and no scientific claim, result, formula, or verified artifact changed for style (independent review per lesson) | F114, F115, F116 |
| The experiment entry point of a lesson | Every lesson declares one; it is an input of the lesson's digest and has a unit test; run in a fresh clone with the learner's `--no-dev` commands, it regenerates the lesson's figure files byte for byte (one figure-writing function per figure serves the entry point and the page's cell, which shows the written file; a figure kind documented as unable to reach byte identity is compared as an image at the page's rendered size) and its numbers at displayed precision within 30 seconds, against what the run computed on the same machine, for every lesson on a full run and for the selected lessons on a selective run; the footer lists its commands and no render or preview command; the setup page's Python-only commands run from the page's text, produce an environment without the `dev` group, and run one experiment of each non-Lean lesson kind; no maintained document instructs a reader to rebuild or preview the site (a test over the maintained guides, the home page, the instructor packs, and the generated footers) | F117 |
| The verification call graph and its removals | Each removed or consolidated check has a coverage argument and a regression test that the violation it caught still fails `verify`; the check identity is split only with a test per domain that its inputs are complete; the `integration` division runs every test exactly once; the targeted run builds no site and reports the selection CI will make (a test); the agent workflow's local obligation per change type is tested where a script enforces it | F118, F119 |
| The full run and the interim gate | The measured `build` job of a full run at the lesson count of the day, recorded with the run identifiers and the cache state, and the lesson count the approved timeout covers; a projection is labelled as one | F118 |
| Inherited results on `main` (only if ADR 017 is accepted) | A full and a selective verification of the same commit produce the same publishable site except the documented provenance fields; a missing, expired, invalid, stale, or incompatible base, a changed shared input, a changed check, and a changed environment identity each fail closed to execution, a test per case; every inherited result carries its origin and no pull request artifact or unverified run is accepted as a base; `deploy` publishes the verified artifact and builds nothing; the exceptional full run is invocable and finishes under its approved timeout | F120 (evidence), F121 (delivery) |

Added by the change cycle `scientific-atelier-atlas`:

| Artifact | Check | Feature |
|---|---|---|
| The agent skills | The skills configuration check, the one check that reads `.agents/skills/` (as data to validate; an ungrouped entry of `scripts/verify.conf` in the group `default`, run by the `workflow` job in CI and by the targeted run locally): every directory under it has a `SKILL.md` and a provenance record with the required fields and a matching digest, and every skill a committed feature plan names exists; the boundary test: no workflow, script, check, build step, or CI job invokes, installs, or fetches a skill, and the build and every check except the skills configuration check pass with the directory absent from a scratch copy; a test per case. Discovery per role, profile, and provider is a recorded demonstration, not a check | F122 |
| The map manifest | Schema (course, path, slot, and concept references only: no illustration reference, no lesson reference); every course, path, slot, and concept reference resolves (the requirements' lesson-reference rule holds vacuously); every concept names at least one slot; every capstone slot of the curriculum file represented by exactly one concept; no field the curriculum file or the front matter holds; no prerequisite written; an unknown field rejected; a failing test per rule | F125 |
| The atlas | All eight courses, the four paths, and the Lean and method views present, the views listing every published lesson by its method tags; the published counts equal the lessons; the prerequisite edges equal the front matter and none belongs to a planned lesson; every conceptual edge has its type and rationale; a capstone link only for a published capstone; no planned slot linked or counted, and planned content distinguishable without colour alone; a capstone's planned description is the manifest's explanation of its concept and nothing else; every published lesson reachable without scripts through the map (the lessons without a slot through the Lean and method views) and through the index; every previous address, anchor, and graph node address resolving; the textual equivalent naming every concept and edge; the accessibility scan, the keyboard pass, the reflow at 320 CSS px; the payload of the page and of the enhancement; the modules making no request, cookie, or storage while every control is operated, and `progress.js` the only storing script; the map's labels at or above the minimum size at desktop and tablet widths; the search index unchanged in meaning; byte-stable rebuilds | F125, F126 |
| Visual assets and their sources | Every SVG under `site/assets/` has a provenance entry (author and licence, or the generating module); the committed-artifact check exempts a tracked `.svg` under `site/assets/` only when the register names it with an author and a licence, and rejects an unregistered SVG, every raster, every other image type, and every image file outside `site/assets/` as before (ADR 018 decision 2 amending ADR 002; a failing test per case); no raster committed; no other-origin resource; every figure cell carries its status; an illustration in an opening has its class and source recorded; a conceptual illustration in a lesson is an executed cell, never a committed file; no image presents artwork or a mockup as a result (review) | F123, F127 |
| The home page | Counts and names from the metadata and the curriculum file; every planned item labelled and never linked; the opening figure drawn by an executed cell of a verified module with its status, alt text, and provenance, byte-stable, computed by no script; the heading "From a question to a working model" absent; every sentence true (review) | F124 |
| Fonts and payload | Every font served from the site's origin with its licence text; the initial payload of every page within 3 MB with the sizes recorded; every new colour pair passing the contrast test | F123 |
| The lesson template | On every lesson it reaches, the executed cells, numbers, figures, claims, section identifiers, references, and footer commands unchanged: the diff of the executed outputs, the reproduction check, and the experiment check in a full run | F123, F127 |
| Rendered review | Three parts on every feature that changes a user-facing visual surface: the implementer's screenshots at desktop, tablet, and phone widths as evidence artifacts (never committed site assets); the independent reviewer's assessment with the built HTML and the sources; the owner's manual pass, which is the final visual acceptance. Never a pixel comparison or a full render on an ordinary lesson change | F123 to F128 |
| The interactive pendulum, if decided | The browser trajectory equal to the Python reference within the stated tolerance at the reference parameters (a built-site test); starts paused; reduced motion; the controls by keyboard; the static fallback; no request, cookie, or storage; the payload | F128 |
| The skill pilots | The piloted lesson's values at displayed precision, commands, claims, and references unchanged (the experiment and reproduction checks); the diagram's science reviewed independently; the record with before and after artifacts, cost, limitations, and the owner's decision | F129 |

Added by the change cycle `risk-proportionate-workflow`:

| Artifact | Check | Feature |
|---|---|---|
| The completion record with criterion gates | A record whose only unmet criteria are pending for a later gate is committed and published without an owner exception and without closing the Issue; `complete` only when every criterion is met; `pending` refused for the `implementation` gate; the record and the handoff note in the review fingerprint (a test per rule) | F130, F131 |
| The risk level of a change | The highest of the paths' minimum (the approval request's own path not counted), the mechanical triggers on the diff, and the recorded assessment; a level below the path minimum refused, and below a trigger reading refused unless the approval request names the lowering; a lowering accepted only as a request for the owner's authorization at the merge gate, of a trigger reading or an assessed level and never of the path minimum, with the required level kept until the owner's word and the required level, the requested level, and the head recorded; no script accepts an agent's assertion, a comment or review by the agent's own login, a file, a flag, or a chat statement as the owner's approval; a forged assertion refused (a test per form) | F130 |
| Level 3 verification | Intermediate `--only` runs recorded as feedback, never evidence; the final review made on a complete verification of the final tree and never with `--unverified`; the targeted tier refused when the check identity differs (tests) | F130 |
| The time log and the base re-fetch | Five fields per run, read by no gate (a test); the base not re-fetched when the latest accepted run is the one recorded, with the provenance rule unchanged (the F61 tests) | F130 |
| The review chain | A Level 2 chain accepted only when it begins with a full review, is contiguous, ends at the current tree, and every finding has a disposition; a delta whose reach is not certain (a Level 3 path, a trigger, a shared input, an exported interface, an unresolved finding, an undecidable search) requires a full review; no line-count threshold; Level 3 full in every round; Level 1 without a review (a test per rule) | F131 |
| Mechanical triage | Minor and suggestion findings at Levels 1 and 2 accepted or deferred with a reason, published once, a follow-up Issue per DEFER; critical and major, and everything at Level 3, triaged in full (tests) | F131 |
| The guarantees that stay | The complete CI run, the required check `verify`, the deployment of the verified artifact, the digest, the selection, the base provenance, the check identity, the determinism check, and independent review unchanged: the F58, F61, F119, and F122 tests pass unchanged on both features | F130, F131 |

Added by the change cycle `site-navigation-and-atlas`:

| Artifact | Check | Feature |
|---|---|---|
| Navigation | Exactly four menu items and the search in the header; the secondary pages in the footer; no link twice; every page reachable and every address resolving; the F57 identity check unchanged | F132 |
| The two-layer atlas | Twelve sequences and the Lean entry; one open at a time without a script; every published lesson reachable without scripts and by keyboard; the existing anchors opening their sequence; the counts equal to the lessons; no planned slot linked or counted, and planned content distinguishable without colour; the three engines and the accordion fallback with the wide rule disabled; no request, cookie, or storage from the module; the search index unchanged in meaning; byte-stable rebuilds; the progress marks, the progress explanation and controls, and the recommendations of F13 and F14 on the page, with the learning path data `recommend.js` reads (their tests unchanged or replaced by equivalent ones) | F133 |
| The manifest's sequence entries and the relationships | One entry per course and path with a description and a registered illustration, a failing test per rule; the concept rules of F125 kept; the conceptual connections and capstone membership on a published lesson's page equal to the manifest, none on a planned lesson | F133 |
| Raster interface artwork | Every WebP or PNG under `site/assets/` registered with origin, licence or terms, and master hash; the committed-artifact check admitting it only through its entry and rejecting an unregistered raster, an incomplete entry, every other image type, and every image outside `site/assets/` (a failing test per case); no text, number, or formula in the pixels and the visual check recorded (review); a regeneration check on demand where a script exists, never in CI | F133, F134 |
| The hero | One default pair and one `<h1>` in the HTML; each of the eight pairs 1a, 1b, 1c, 2a, 2b, 2c, 3a, and 3b present in the data file and rendered through the `hero` parameter; no layout shift; no storage or request; the copy only in its data file, validated | F134 |
| How we verify the science | Every worked example's target checked by the build, a missing target failing it; the Evidence map reachable from the page and the footer | F134 |
| The improvement links | Every link names an existing form and a parameter that is an `id` of a field of that form (a unit test); one manual check on github.com recorded | F135 |

Manual gates that stay manual: independent physics and pedagogy reviews per
lesson (through the existing review workflow); the human's approval of
identity copy, of the sandbox profile, of any CI or ruleset change, of
every go decision on a dataset, of each course's lesson list in its
Issues, and of the curriculum file; a screen-reader pass per release;
since `pbc-planning-change-four-workstreams`, also the human's approval of
the editorial pilot before the voice reaches another lesson, the owner's
decision on the interim full-run gate (unresolved question 10), and the
owner's acceptance or rejection of ADR 017 (question 9); since
`scientific-atelier-atlas`, also the owner's approval of each skill
candidate's outcome and of the workflow contract (question 13, F122), the
owner's review of the map manifest as a curriculum artifact (F125), the
owner's review of the preview before the rollout and the final visual
acceptance (decision 36, F126, F127), the owner's decision on the
interactive pendulum (question 14, F128), the owner's naming of an
explanation for a Manim pilot (question 15), and the owner's decision
after the skill pilots (F129); since `risk-proportionate-workflow`, also
the owner's approval of the diff of F130 and of F131 before their merges,
the owner's actions of mechanism A (the second identity, the ruleset,
`CODEOWNERS`, the test pull request; ADR 020 decision 3), the owner's
authorization of every lowered risk level and approval of every Level 3
change as a GitHub review by that identity, the owner's decisions at the
re-assessment points (42 lessons measured, 44 decided, or a complete run
on `main` above 45 minutes), and the owner's decision after a
`process-miss` in an escalation-trigger category; since
`site-navigation-and-atlas`, also the owner's approval of the atlas
illustrations and the hero image (F133, F134), the owner's rendered pass
on the new atlas and Home as the preview gate of F127, the owner's
decision on where the interactive pendulum belongs, if anywhere (question
14, F128), and the owner's decision on a contribution form without a
GitHub account (question 16).

## Not on the roadmap

The requirements' non-goals stay excluded: accounts and server-side learner
data, any backend, analytics and tracking, in-browser Python and hosted
notebooks, formal verification of the Python code, certification or grading
that leaves the browser, languages other than English, a mobile app, hosted
or runtime LLM calls and any tutor or chat on the site, marketing surfaces
of any kind, outreach campaigns, a repository transfer or a changed Pages
URL, changed copyright or licence holders, bundled large or restricted
datasets, and any claim that a proof establishes a measurement or that
every experiment has an LLM or Lean counterpart. Since the change cycle
`final-curriculum`, also: lessons that build sensor experiments, record
audio, collect classroom or smartphone data, control instruments, or
operate a physical laboratory; a mathematics curriculum, a
physics-informed machine-learning track, or a generic AI or
machine-learning curriculum; the nuclear and particle, plasma, and
geophysics and climate expansions; a capstone presented as a calibrated
digital twin, a fabricated or validated device, or an operational
forecast, and any capstone beyond T11, EM9, and FL10; a heavyweight
solver as a mandatory build or CI dependency; and stock, hand-copied, or
externally hosted images (the exclusion of decorative images and
animation that stood here until 2026-10-17 is superseded by the asset
classes of requirements decision 37 and ADR 018 since the change cycle
`scientific-atelier-atlas`: interface artwork, conceptual illustrations,
and accessible animation are allowed where that record says, nothing for
decoration's own sake). Since the change cycle
`pbc-planning-change-four-workstreams`, also: a uniform editorial register
forced on every lesson, a rewrite of the whole curriculum in one feature,
a mandatory editorial agent, optimisation against AI-content detectors;
any instruction in maintained documentation to rebuild or preview the
website locally, relocated or not; an automatic scheduled full
verification audit, a new sharding mechanism, or substantial verification
infrastructure without separate evidence and the owner's approval; and the
removal of the internal CI site build, the deployment of the verified
artifact, provenance, accessibility, scientific checks, or the ability to
run complete verification. Since the change cycle
`scientific-atelier-atlas`, also: a frontend framework, a Node or
JavaScript bundler, a second site generator, KaTeX or another equation
renderer in place of native MathML, a backend, authentication, a hosting
migration, a runtime service, or a paid model or API requirement for the
atelier, the atlas, or the skills; a CAD or parametric-modelling tool
(FreeCAD, OpenSCAD) as a skill or dependency; routine animation rendering
in CI; a generated raster image as the map's navigation surface; browser
storage for the map's controls; an experiment gallery before enough real
browser experiments exist, empty or linking to experiments that do not
exist; JavaScript physics or illustrative motion on the home page that
the build did not verify; a globally installed or run-time-fetched agent
skill, a third-party installer in CI, or a skill as a dependency of the
build, the deployment, or any CI job; an additional mandatory review agent or a change to the owner
approval hierarchy; a Manim pilot without the owner's named explanation;
a narrative structure imposed on every lesson by the redesign; and a
curriculum change by way of the map manifest. Since the change cycle
`risk-proportionate-workflow`, also: any weakening of the digest, the
selection, the base provenance, the build, the deployment, or the
determinism guarantees, of the complete CI run on every pull request and
push, or of independent review by a different model, for the sake of lead
time; a new mandatory agent or a new mandatory reporting gate in the
feature workflow; a workflow rule that an agent can satisfy with its own
assertion of the owner's approval, or an approval mechanism that rests on
the authorship of a comment or on a flag; a changed-lines threshold or a
general-purpose impact graph for delta reviews; mandatory optimisation
work started by an exceeded time budget, or any budget response that
changes scientific content; further work on ADR 017, F113, F120, or F121
before the owner's triggers; concurrent changes to the workflow scripts;
and an agent that changes repository settings, creates accounts, or sets
up the owner-approval mechanism. Since the change cycle
`site-navigation-and-atlas`, also: a form on the site that creates GitHub
issues for a visitor without an account, or any server, serverless
endpoint, or stored credential for it, until the owner decides question
16 through its own change; a measurement of which hero headline works
better, or any collector for it; browser storage of the open sequence or
the hero's variant; an image as the only navigation surface of the atlas
or the hero; text, numbers, or formulas in the pixels of interface
artwork; raster artwork in a lesson's body or presented as evidence;
rendering the illustrations in the build or in CI; and committed masters,
intermediates, or option boards. The exclusion of "a generated raster
image as the map's navigation surface" and "browser storage for the map's
controls" of the change cycle `scientific-atelier-atlas` is read for the
atlas and the hero as this sentence states it. Adding any of them is a
requirements change that returns to Project Grill.
