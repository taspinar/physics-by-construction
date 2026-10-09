# Roadmap

Project direction for Physics by Construction, derived from the approved
`docs/PROJECT_REQUIREMENTS.md` (approved 2026-10-06, re-approved on
2026-10-09 with the change request `docs/changes/physics-next-phase.md`) and
consistent with `docs/architecture.md` and ADRs 001 to 010.

Keep this high-level. GitHub Issues are the actionable backlog and the source
of truth for a feature once its Issue exists. Each feature below has a stable
ID; `./scripts/create-feature-issue.sh <ID>` copies its block into an Issue.
Detailed implementation plans are written just in time under `.agents/plans/`
when a feature becomes active, not here.

This roadmap does not choose which feature is active. It records dependencies;
the human picks the next feature among those whose dependencies are done.
Review the later-phase features against the current architecture before
starting them.

## State at the change cycle

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

## Overview

Phases: Phase 1 is the MVP; Phase 2 is the work the requirements placed
after the MVP; Phase 3 is the change cycle `physics-next-phase`, ordered in
waves R0 to R5 by dependency (see "Execution order"). A wave is a suggested
grouping, not a gate: a feature may start when its dependencies are done.

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
| F15 | Second course on the three-pillar path | 2 | F10 | Medium |
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
| F54 | Microwave S-parameter lab | 3, R4 | F51, a course for the lab (F15; see the block) | Medium |
| F53 | Flow measurement lab with PIV fields | 3, R4 | F51, F43, a course for the lab (F15; see the block) | Medium |
| F52 | Optical diffraction lab | 3, R4 | F51, F43, a course for the lab (F15; see the block) | Medium |
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

Risk levels follow `.agents/policies/autonomy.md`. Every feature that adds a
lesson is at least Medium, because physics and proof content needs independent
review, not only passing checks. Features that change CI, repository
settings, legal text, or let an agent write code are High.

## Product structure

From the requirements (decision 15) and ADR 008. The site has three facets,
all derived from lesson front matter; there is no second list.

| Facet | Content | Today | Next phase |
|---|---|---|---|
| **Physics courses** (by subject) | Mechanics. Later candidates: waves and optics (bridged by the wave-flume and optics datasets), Lagrangian and Hamiltonian mechanics, statistical physics, electromagnetism, fluid dynamics. | One course, implicit | `course` in every lesson (F37); a second course only through F15 with the human's explicit choice. F15 yields one course. A measured-data lab whose subject F15 does not choose waits for a later course feature, which takes the next unused ID when the human asks for it; the only other route is a `mechanics` framing its Issue justifies under ADR 008 decision 3. |
| **Methods** (cross-cutting, not subjects) | Simulation, LLM agents in the harness, agent-based modelling, formal verification in Lean, measured data, coding agents on the learner's machine. | Four strands in one linear path | `methods` tags, one method path per method on the learning-path page, related-lesson links (F37); no method becomes a course. |
| **Strands** (URL groups and ordering) | `mechanics`, `agents-llm`, `agents-abm`, `lean`. | Unchanged | Unchanged identifiers and addresses; display titles may be refined (for example "AI-assisted research" for `agents-llm`). A measured-data lab of the mechanics course takes the next order in the `mechanics` strand; a lesson about a method lives in that method's strand. No lesson is placed by a method tag alone (ADR 008 decision 4). |

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
    pull request.
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
whose commands regenerate the lesson's results from a clone. An author can
create a new lesson from a template and a guide.

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
  commit.
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
   request and in `docs/release-readiness.md`'s table.
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
surface. Content changes to lessons (the editorial passes).

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
adoption, counters, or news. Changes to lessons.

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
   the Reproduce page, shown by a test.
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
built-site check that the commands still regenerate the page is unchanged;
the Lean evidence box gets the same treatment; a "copy" affordance only if
it needs no JavaScript to read.

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
2. **Fallback: NPL S-parameters (F54), after F15.** The most compact and
   technically robust dataset (3.1 MB, Touchstone, CC BY 4.0), but it needs
   RF background the course does not teach and has no published course to
   belong to, and ADR 008 allows no lesson without a primary course. It
   becomes the first lab only if F60 is deferred or rejected by the spike
   and F15 has chosen an electromagnetism or waves-and-optics course for it;
   the fallback path therefore runs through F15 before F54, and the F50
   dossiers are the evidence for that choice.
3. **Bridge for F15: the Aalborg wave flume.** The strongest
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

## Execution order and first-wave release plan

By dependency, not by number. A wave is a grouping for planning; the human
picks the next feature among those whose dependencies are done.

| Wave | Order within the wave | Outcome |
|---|---|---|
| R0 | F58 | CI within budget, recommended before pages are added but not a gate for R1 (the per-check budgets and ADR 003 decision 6 stay the guard); the release of the MVP tagged by the human (`docs/release-readiness.md`) |
| R1 | F44, F57, F37, F35, F36, F39 in parallel worktrees; then F25 (after F57), F26 and F27 (after F37); then F28 (M1 template pilot); then F30's M5 pilot; then F29 (M1 editorial), F30 (M6 to M8), F29 (M2 to M4) | A clear, honest, identified site with the editorial standard proven on both pilots and the mechanics course migrated; a release "clarity" tagged after it |
| R1, beside | F50 spike (no page) | The go, defer, or reject decisions and the first-lab confirmation |
| R2 | F42, F38, F40, F41, F31, F32, F33, F34, F59; F46, F45, F16, F17 | All lessons in format 2 with diagrams, hints, glossary, search, one instructor pack; trustworthy scientific coding with one counterexample lesson and further proofs |
| R3 | F51, then F60 (or F54 as the fallback, after F15 has chosen its course), F43's first component | The first measured-data lab published after its gate |
| R4 | F54, F53, F52 as their courses exist (F15 gives at most one of them a course; the others wait for a later course feature, or for F53 a justified `mechanics` framing); F55, F23, F47, F18, F19, F56 | Evidence and advanced labs |
| R5 | F20, F21, F22, F49 | Research capstones |

Features F13 and F14 keep their approved scope and are scheduled by the
human after F28, so that their self-check format wraps F28's self-check and
F38's hints rather than duplicating them. F15 is scheduled when the human
chooses the course topic; the F50 dossiers inform the choice. F15 yields
one course; a lab of another subject waits for a later course feature that
takes the next unused ID when the human asks for it. F12's
workflow is unchanged; the reference protocol of F28 applies to
agent-drafted content through `docs/authoring.md`.

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
| Page payload | Built-site check: initial 1.5 MB, on-demand 3 MB, total 5 MB | F44, F43 |
| Widgets and components | The F07 checks plus the observed-value test and the keyframe | F43 |
| Coding-agent exercises | A test that no workflow, script, or check invokes an agent; the produced reference code and tests verified like any code (ADR 010) | F45 |
| Harness lessons | Replay without credentials; the ADR 004 boundary tests on every allowlist | F16, F18, F20 |
| Identity text | Built-site check that the canonical text is where it must be and nowhere else; `CITATION.cff` schema | F57 |
| CI structure | Every check in exactly one group; one aggregate required check; permissions | F58 |
| Local execution | `./scripts/verify.sh` unchanged in meaning; the setup page's required commands equal CI's; optional workflows "not verified" | F39 |

Manual gates that stay manual: independent physics and pedagogy reviews per
lesson (through the existing review workflow); the human's approval of
identity copy, of the sandbox profile, of any CI or ruleset change, and of
every go decision on a dataset; a screen-reader pass per release.

## Not on the roadmap

The requirements' non-goals stay excluded: accounts and server-side learner
data, any backend, analytics and tracking, in-browser Python and hosted
notebooks, formal verification of the Python code, certification or grading
that leaves the browser, languages other than English, a mobile app, hosted
or runtime LLM calls and any tutor or chat on the site, marketing surfaces
of any kind, outreach campaigns, a repository transfer or a changed Pages
URL, changed copyright or licence holders, bundled large or restricted
datasets, and any claim that a proof establishes a measurement or that
every experiment has an LLM or Lean counterpart. Adding any of them is a
requirements change that returns to Project Grill.
