# Roadmap

Project direction for Physics by Construction, derived from the approved
`docs/PROJECT_REQUIREMENTS.md` and consistent with `docs/architecture.md` and
ADRs 001 to 004.

Keep this high-level. GitHub Issues are the actionable backlog and the source
of truth for a feature once its Issue exists. Each feature below has a stable
ID; `./scripts/create-feature-issue.sh <ID>` copies its block into an Issue.
Detailed implementation plans are written just in time under `.agents/plans/`
when a feature becomes active, not here.

This roadmap does not choose which feature is active. It records dependencies;
the human picks the next feature among those whose dependencies are done.
Review the later-phase features against the current architecture before
starting them.

## Overview

| ID | Feature | Phase | Depends on | Risk |
|---|---|---|---|---|
| F01 | Published site skeleton with the full verification pipeline | MVP | none | High |
| F02 | Lesson format and the first mechanics lesson | MVP | F01 | Medium |
| F03 | Learning path | MVP | F02 | Medium |
| F04 | Mechanics lessons: Newton's laws and projectile motion with drag | MVP | F02 | Medium |
| F05 | Mechanics lessons: the harmonic oscillator and numerical integrators | MVP | F04 | Medium |
| F06 | Mechanics lessons: energy, momentum, and a capstone orbit | MVP | F03, F05 | Medium |
| F07 | Interactive visualizations | MVP | F05 | Medium |
| F08 | Formal proofs strand: first Lean lesson | MVP | F03, F05 | Medium |
| F09 | LLM agents strand: first agent-driven experiment lesson | MVP | F03, F04 | High |
| F10 | MVP release readiness and launch | MVP | F01 to F09 | Medium |
| F11 | Agent-based modelling strand: first lesson | After MVP | F03, F06 | Medium |
| F12 | Content proposal workflow through GitHub Issues | After MVP | F10 | High |
| F13 | Self-check quizzes and browser-local progress | After MVP | F03, F07, F10 | Medium |
| F14 | Adaptive recommendations | After MVP | F13 | Medium |
| F15 | Second course on the three-pillar path | After MVP | F10 | Medium |

Risk levels follow `.agents/policies/autonomy.md`. Every feature that adds a
lesson is at least Medium, because physics and proof content needs independent
review, not only passing checks.

Possible parallel work after F02: F03 and F04 are independent of each other.
After F05: F06, F07, and F08 are independent of each other; F06 and F08 also
need F03.

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

The agent-based modelling lesson is not in the MVP. Unresolved question 4 of
the requirements lets the planner place it in the MVP or make it the first
follow-up. With ten lessons the MVP is at the top of the size the requirements
describe, and the lesson needs no pipeline capability the MVP does not already
exercise, so it has the explicit slot F11 as the first follow-up.

## MVP requirements coverage

| MVP requirement | Delivered by |
|---|---|
| Mechanics course of 6 to 10 lessons with numerical simulations | F02, F04, F05, F06 |
| At least one LLM agent lesson, run locally with the learner's key | F09 |
| Agent-based modelling lesson, or an explicit roadmap slot | F11 (slot) |
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

## Not on the roadmap

The requirements' non-goals stay excluded: accounts and server-side learner
data, any backend, analytics and tracking, in-browser Python and hosted
notebooks, formal verification of the Python code, certification or grading
that leaves the browser, languages other than English, and a mobile app.
Adding any of them is a requirements change that returns to Project Grill.
