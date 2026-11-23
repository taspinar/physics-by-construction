# Plan: F22, Agent-assisted theorem proving (Issue #609)

Source: `docs/roadmap.md`, F22 (with the note of the change cycle
`part-b-scientific-products-and-research`: the F45 profile is F141's); ADR
010 (decisions 3 to 6, decision 5 names F22); ADR 004; ADR 011; ADR 013;
ADR 023 decision 2; the owner's start and the session instructions on Issue
#609. Written by the implementer at the start of the work (the Issue
expects a detailed plan and none existed).

**Level 3** by assessment and by path: the Issue rates the risk high
(agent-written code on the learner's machine), the security review of the
profile is an acceptance criterion, and the approval request
`.agents/approvals/609.md` is a protected path. No ADR, no CI workflow, no
check of `scripts/verify.conf`, no dependency, no existing tolerance, and no
existing test changes. Sensitive path touched: `docs/architecture.md` (one
sentence at the end of the entry of I24 and of the module table rows).
Triggers named in the completion record: security (the profile for Lean).
A published claim of `main` does not change: `lean/02` keeps its text; the
new lesson only proves what `lean/02` lists as not proved.

## Revalidation of the roadmap block (2026-11-23)

Checked against `docs/architecture.md`, ADR 010, ADR 013, the requirements,
and the delivered F16, F17, F21, F141.

| Block says | Now | Consequence |
|---|---|---|
| "under the F45 profile" | F45 dropped; the profile is section 2 of `docs/coding-agent-workflow.md` (F141, #561), which section 9 already reserves for F22 | The lesson states that profile in full, in its words, and adds what Lean needs (below); the workflow document gains a section on the profile for Lean |
| "counterexample search with F16's loop" | F16 is `pbc.agents.hunter` (claim, budget, `judge`) on the harness of ADR 004 | The search is a harness hunt with replay fixtures (`replay-<name>.json`) that the build replays and judges; a harness agent never writes code (ADR 010 decision 1) |
| "Lean formalization by a coding agent" | ADR 010 decision 4: the coding agent's transcript is never replayed, never a file, never a build input; `docs/authoring.md`, "Coding-agent exercises": code an agent wrote in a session is not committed with the lesson | The coding agent's session is an example transcript inside a "not verified" block on the page (agent, model, date, how condensed, profile given as instructions). The Issue's "replayed like the other agent lessons" applies to the search, the only part of the workflow that ADR 004 lets the build replay. Not a conflict: the Issue's own source (ADR 010 decision 4) forbids the other reading |
| "proof checking with `lake build`" | `scripts/check-lean.sh`: `lake build` and the axiom audit; `lean_excerpt` refuses a file changed after the check | The reference proof is a module of the library; the page shows it with `lean_excerpt`, never the agent's text as a proof |
| "human semantic review" | The rubric of the workflow document is about code | A review rubric for a formal statement (below), on the page and in the workflow document |
| "starting from the known reference proofs of F17 and F21" | `lean/02` proves momentum for the hard-sphere rule and lists the kinetic energy for a unit direction as "a second theorem, not proved here"; `lean/04` runs Lean locally | The conjecture is that theorem; the new module imports `Collision` and reuses its definitions |
| Placement (Issue) | Lean strand, outside the slots, `lean/06`, the 127th lesson | No slot; `site/curriculum.yaml` unchanged; the atlas lists it under the Lean lessons without a slot |
| Acceptance criteria | Unchanged | Mapped below |

## The lesson

`site/lessons/lean/06-a-proof-an-agent-proposed/index.qmd`, id
`agent-proposed-proof`, strand `lean`, order 6, course `mechanics`,
difficulty 3, methods `[lean, llm-agents, coding-agents]`, format 2,
`lean-modules: [PhysicsByConstruction.Mechanics.CollisionEnergy]`,
experiment `pbc.mechanics.experiments.agent_proposed_proof`, prerequisites
`collision-momentum-proved`, `counterexample-hunter`,
`verifying-scientific-code`, `lean-exercises-on-your-machine`.

**Archetype.** Formal proof (main), with an agent part. The statement
first; assumptions, theorem, checked proof, and numeric instance kept
apart; the evidence kind of every step stated at once.

**The learner at the start.** Has read the momentum proof of `lean/02`
(definitions `dot`, `firstAfter`, `secondAfter`; `field_simp`, `ring`),
run Lean locally (`lean/04`), seen a hunt judged by the build (SA7), and
the coding-agent profile and rubric (SA2).

**Central question.** An agent hands you a Lean proof that compiles. What
do you now know about the collision?

**Counterintuitive point.** `lake build` decides whether the proof proves
*the statement*; it does not decide whether the statement is the physical
claim. A statement can compile and be true and still say nothing about a
collision (one whose hypothesis excludes every approach). And compiling an
agent's file runs the agent's code: Lean executes commands at compile time.

**Sequence.**

1. Opening: the question; the five steps of the workflow (conjecture,
   counterexample search, formalization by a coding agent, `lake build`,
   a person's review) and the kind of evidence of each, said at once.
2. Assumptions (the model of `lean/02`, unit direction as a hypothesis,
   real numbers, the agent untrusted, what the build runs).
3. Explanation: the conjecture in words and symbols; who decides each step.
4. The search: claim "conserves the kinetic energy for every direction"
   (tool with `nx`, `ny`), authored hunt replayed and judged:
   counterexample. **Prediction moment** before the verdict: which argument
   will the witness differ in? Then the refined claim with a unit direction
   (tool with an angle): inconclusive, and why a proof is needed.
5. The task for the coding agent: the claim, the definitions to import, the
   files it may write, the commands it may run, the budget.
6. The session: example transcript, "not verified", condensed.
7. The reference proof, compiled: `lean_evidence`, `lean_excerpt` of
   `kinetic_energy`, `collision_energy`, `collision_energy_change`.
8. The review of the statement: the rubric applied to the agent's
   statement, item by item, and to `energy_without_approach`, which
   compiles and says nothing about a collision.
9. What the compiled proof establishes and what it does not (claim labels).
10. A numeric instance: the witness of the hunt against the identity
    `collision_energy_change` (labelled an instance); the figure.
11. The profile for Lean (in full, the six rules and the Lean additions).
12. Conclusion; Limits; self-check (**interpretation moment**: does
    `energy_without_approach` prove the claim?); exercises (hypotheses that
    can go, the length −1 direction, a review of a given statement, drive a
    coding agent yourself, not verified); Check this proof.

**Displayed code and its purpose.** `kinetic_energy`, `collision_energy`,
`collision_energy_change`, `unit_direction_exists`, `energy_without_approach`
(formal proof, exact source by region); the claim of each hunt (agent
control: the domain and the limit, as values); `energy_change` of the
experiment (the tool's computation, exact source); the instance comparison
(validation, exact source); `draw_energy_change` behind its excerpt only if
it computes something the reading needs (it plots the normalised change;
the normalisation is stated in the prose and the caption).

## The Lean files

`lean/PhysicsByConstruction/Mechanics/CollisionEnergy.lean`, imports
`PhysicsByConstruction.Mechanics.Collision`:

- `kineticEnergy m v = 1/2 * m * dot v v`;
- `collision_energy`: `0 < m₁`, `0 < m₂`, `dot n n = 1` ⇒ the sum of the
  kinetic energies after equals the sum before;
- `collision_energy_change`: for any `n`, the change of the total kinetic
  energy is `2 m₁ m₂ / (m₁ + m₂) · s² · (dot n n − 1)` with `s` the
  approach `dot (v₁ − v₂) n`: the formal reason for the counterexample;
- `unit_direction_exists`: the hypotheses are satisfiable together (a
  review item made formal);
- `energy_without_approach`: a statement that compiles, is true, and says
  nothing about a collision (hypothesis: no approach along `n`); kept to
  show what compiling does not decide, its doc comment says so.

All without `sorry`, axioms, `#eval`, or `run_cmd`; `./scripts/check-lean.sh`
audits them.

## The profile for Lean, and its security review

The profile of `docs/coding-agent-workflow.md`, section 2, unchanged, with
these additions for Lean (a new subsection of section 9 of the workflow
document, and the same words on the page):

1. **Dependencies before the start.** The learner fetches the toolchain and
   Mathlib's build cache (`lake exe cache get`) before the agent starts. The
   agent's allowlist then holds only `lake build <its module>` and
   `lake env lean <its file>`; never `lake update`, `lake exe`, `elan`,
   `git`, or a shell.
2. **One new file.** The agent writes only the module named in the task.
   It never edits `lakefile.toml`, `lake-manifest.json`, `lean-toolchain`,
   the reference modules, or `AxiomAudit.lean`, and never creates a
   `lakefile.lean`.
3. **Compiling is running.** Lean runs code while it compiles: `#eval`,
   `run_cmd`, `initialize`, `elab` and macro definitions, and a
   `lakefile.lean` can read files, start processes, and use the network as
   the learner. Rule 6 of the profile therefore covers `lake build`: read
   the file before you build it, and refuse one that contains any of these
   commands, a `set_option` that changes checking, `axiom`, `sorry`,
   `native_decide`, `implemented_by`, `extern`, or `unsafe`.
4. **The audit after the build.** Run the axiom audit
   (`./scripts/check-lean.sh`) on the result: a proof that leans on an
   axiom or on `sorry` is no proof.

**Security review** (the acceptance criterion; recorded here and in the
completion evidence):

| Threat | Where it acts | Mitigation in the profile | Residual |
|---|---|---|---|
| Code execution at compile time (`#eval`, `run_cmd`, `initialize`, macros, tactics written in the file) | The agent's own `lake build` of its draft; the learner's build of the result | Scratch checkout (rule 1); container or separate machine for a boundary; the learner reads the file before building it and refuses the listed commands (Lean rule 3) | The agent's own builds run unread code; only isolation limits them, as for the tests of the Python profile. Stated on the page |
| A `lakefile.lean` or a changed `lakefile.toml`/manifest: build-time code, a new dependency fetched from the network | `lake build` | Lean rule 2 (no edit of the build files, no `lakefile.lean`); rule 3 of the profile (no network); dependencies fetched before the start | A setting of the agent without a container |
| Network: `lake update`, `lake exe cache get`, `require` of a new package | `lake` | Not in the allowlist (Lean rule 1) | As above |
| Credential exposure: Lean code can read files and environment variables | Compile time | Rule 4 of the profile unchanged (a shell without other credentials; files only out of reach in a container) | Unchanged from SA2 |
| A proof that is not one: `sorry`, `axiom`, `native_decide` (`Lean.ofReduceBool`), `implemented_by`, `debug.skipKernelTC` | The proof | Lean rules 3 and 4 (refused by reading; the axiom audit fails on any non-standard axiom and on `sorry`) | `set_option` that weakens checking is caught by reading, not by the audit |
| A statement that is not the claim (redefined notions, vacuous or excluding hypotheses, a special case, notation that changes meaning) | The meaning | The review rubric for a formal statement (below), human | The page says the match is a human judgement |
| The site and CI | The build | Nothing changes: no agent, no credential, no transcript file (ADR 010 decision 6); the replay fixtures are harness fixtures of ADR 004, recomputed tool by tool | None new |

**Verdict:** the profile is approved for Lean with the four additions; it
remains a way of working, not a security boundary, exactly as section 2
says. The owner's approval of the merge is the approval of this review.

**The review rubric for a formal statement** (beside the code rubric):

1. **The file.** Only the requested file; imports the library's
   definitions; no command of Lean rule 3; nothing redefined.
2. **The definitions.** The statement uses the library's `firstAfter`,
   `secondAfter`, `dot`, not its own copies; the energy is the physical one.
3. **The hypotheses.** Each names a physical assumption; together they are
   satisfiable; none excludes the case the claim is about.
4. **The conclusion.** It is the claim in words, for every value the claim
   speaks of, not a special case.
5. **The audit.** `lake build` and the axiom audit pass on the reviewer's
   machine, not in the agent's report.
6. **What it does not say.** Floating point, the Python code, and anything
   the hypotheses exclude, written down.

## The search (harness, ADR 004)

`src/pbc/agents/proof_lab.py`: the allowlist of two tools,
`energy_change_any_direction` (masses, two planar velocities, `nx`, `ny`)
and `energy_change_unit_direction` (the same with an `angle`); both return
the relative change of the total kinetic energy, computed with
`pbc.mechanics.particles.hard_sphere_collision`; the claims
`ANY_DIRECTION` (limit 1e-9, budget 6) and `UNIT_DIRECTION` (same limit,
budget 6), the system prompt of the hunter, the replay. Fixtures
`replay-any.json` and `replay-unit.json` next to the page, authored in a
Claude Code session (labelled authored, never recorded).

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| The normalised change of the kinetic energy against the length of the direction, sampled collisions on the curve `|n|² − 1` of the identity, the hunt's experiments marked | Scientific figure, `simulated` | `fig-energy-change` (the preview) | The curve is the Lean identity's right-hand side; the unit test compares each sampled point with it | `fig-alt`; the table of the instance |

No diagram, no animation, no page layout.

## Acceptance criteria and where they are met

| Criterion | Evidence |
|---|---|
| Any proof shown on the site is compiled by CI like every proof | The page shows Lean only through `lean_excerpt` of the library module (and the agent's text only in the not-verified transcript); `./scripts/check-lean.sh` |
| The agent's transcript is "not verified" | The not-verified block with agent, model, date (`tests/unit/test_coding_agent_boundary.py` reads every page); the hunts are labelled authored |
| The page states what a compiled proof does and does not establish | The section and its claim labels; a test reads the page |
| The security review approves the profile for Lean | The review above; the profile in the workflow document and on the page; owner's approval at the merge gate |

## Steps

1. Plan, handoff note.
2. The coding agent's session in a scratch copy of `lean/` without the
   reference module (a subagent, Opus, the profile given as instructions).
3. The reference module; `./scripts/check-lean.sh`.
4. `pbc.agents.proof_lab`, the authored hunts, the fixtures.
5. The experiment `pbc.mechanics.experiments.agent_proposed_proof` and its
   tests; the replay tests in a new file
   `tests/integration/test_proof_replay.py`.
6. The page.
7. Docs: `docs/coding-agent-workflow.md` (the profile for Lean, the rubric
   for a statement), `docs/authoring.md` (one line in Coding-agent
   exercises), `docs/architecture.md`, `docs/project-map.md`.
8. Checks: the changed tests, `pbc.skills`, `check-lean.sh`, the single
   page render, `verify.sh --base` with `VERIFY_JOBS=2`.

## Discoveries during the work

- **The coding agent's session** (2026-11-23, Opus through Claude Code, in a
  scratch copy of `lean/` without the reference module, the profile given as
  instructions): 7 tool calls, 2 builds. The first build failed for a
  Mathlib import the library module lacks; the agent added an import the
  specification did not name. That became a review finding (item 1) and the
  reason the rubric asks for the allowed imports in the next specification.
  The reviewer's `lake build` and `./scripts/check-lean.sh <scratch>` passed
  on the agent's file. The agent's file is not committed (ADR 010 decision
  4; `docs/authoring.md`, "Coding-agent exercises").
- **The reference module** is written apart from the session: the identity
  `collision_energy_change` first, conservation as its corollary; it needs
  `Mathlib.Algebra.BigOperators.Ring.Finset` as well.
- **Round-off in a replay.** The replay display prints the recomputed tool
  results; a change at round-off (about 1e-16) would be a number another
  machine changes. The tools report a change below `ROUND_OFF` (1e-12) as
  zero, which the page states; the authored messages were written again
  against the zeros.
- **A raw URL** is refused in a format 2 lesson even inside a not-verified
  block (the SA2 page is format 1): the exercise says to clone the
  repository as in the last section.
- **Lean modules.** A Lean file named among `reproduce_this`'s `code` must
  be listed in `lean-modules`: `Collision` is listed beside `CollisionEnergy`.

## Where the teaching skill changed the learning experience

pbc-physics-teaching@7f34987 (digest
7f34987155a20b3a0d4bf4312cbcf1932e88281660e58179b2cd1b2c1cdd68a0):

- **Archetype and kind of evidence first.** The opening names the five
  steps and the kind of evidence of each (authored hunt replay, not-verified
  transcript, compiled module, human review) before any of them is shown
  (section 2, the AI-agent and formal-proof journeys combined, formal proof
  the main one).
- **The prediction moment** is before the first verdict: which argument
  breaks the claim, and does the energy go up or down. The table of the
  instance and the figure answer it later with the identity (section 3).
- **The interpretation moment** is the self-check on
  `energy_without_approach`, placed after the limits: a compiled, audited,
  satisfiable statement that is not the claim (section 3, the
  counterintuitive point of section 1).
- **Kinds of result kept apart** (section 4): the formal theorems carry
  `formal-theorem` labels, the agreement of the program with the identity is
  a `numerically-verified` claim scoped to the samples, the instance table
  is labelled an instance and never a step of the proof, the agent's pattern
  is said to be the agent's reading.
- **Derivation.** The identity is the essential derivation (the
  counterexample and the conservation both rest on it); it stays in the
  page as the proof plus one paragraph that says where it goes.
- **Code blocks** (section 7): the proofs in full (formal proof); the tool's
  computation `energy_change` in full (the physical relationship the search
  judges); `run`'s replay region as an exact selection (agent control); the
  sampling function in full (what the figure's normalisation is); the
  drawing function only by its Source link (it plots and computes nothing
  the reading needs beyond the normalisation, which the prose and the axis
  label state).

pbc-scientific-visualization@a70b501 (digest
a70b501696ad469d06e1986ebb51083d163c684b2eada3aa984b1a59651a335b) shaped
`fig-energy-change`: the program's points and the identity's curve told
apart by marker and line style, the hunt's experiments by a third marker,
the dimensionless axes said so, guides at unit length and zero change, a
caption that states the conclusion, alt text without values, `simulated`,
a fixed seed.

## Out of scope

A live coding agent anywhere in the build; a new ADR; a change of the
existing lessons, tests, or tolerances; F56 (proofs for measured-data
labs); an energy theorem for the soft contact or for many bodies.
