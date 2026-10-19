# Project Requirements

Status: Approved
Approved at: 2026-10-19T10:07:11Z

Project Grill owns the Draft content. `scripts/start-planning.sh` records human
approval before project architecture and roadmap planning begins.

Source: `docs/PROJECT_DESCRIPTION.md` (human-supplied, authoritative), the
change requests `docs/changes/physics-next-phase.md` (human-supplied,
2026-10-09), `docs/changes/final-curriculum.md` (human-supplied,
2026-10-10, revision 3), and
`docs/changes/pbc-planning-change-four-workstreams.md` (human-supplied,
2026-10-14), `docs/changes/scientific-atelier-atlas.md` (human-supplied,
2026-10-17), and `docs/changes/risk-proportionate-workflow.md`
(human-supplied, 2026-10-18), plus the decisions recorded in "Major product
decisions" below.

## Project goal

Build **Physics by Construction**, a free, open-source, English-language
educational website that teaches physics by constructing it: every concept is
accompanied by runnable code, and learners construct models, analyse real
experiments, and verify what can actually be established, with Python, bounded
AI agents, and formal proofs in Lean 4 where they add scientific value.

Three scientific activities run through the content:

1. **Construct**: derive physical models, implement and compare numerical
   simulations.
2. **Investigate**: process genuine experimental measurements, quantify
   uncertainty, fit models, and design experiments.
3. **Verify**: check code, numerical results, scientific conclusions, and
   selected mathematical properties with Lean 4.

A real-data lesson follows one loop: start from an actual measurement or
calibrated observational product, disclose preprocessing and calibration,
construct a model, produce a scientifically informative comparison of
measurement and model, test discrepancies and uncertainty, and state exactly
what the evidence supports. A beautiful plot is a means to understanding, not
evidence by itself.

Why it matters: existing physics material is either prose-and-equations or
code-only. This site makes the assumptions, models, and claims of each lesson
explicit and machine-checkable, so a reader can reproduce every result,
interrogate it with agents, and, at the top of the path, see it proved.

Success for the project means a published static site with a complete,
CI-verified first mechanics course that already exercises all three pillars
(code, agents, Lean), and a repeatable workflow for growing the content.
Beyond that first release, success means lessons that are self-contained and
research-backed, and at least one lesson built on real measured data that has
passed the dataset feasibility gate described under "Data and persistence".

The long-term target is the reference curriculum of decision 23: eight
physics courses with genuine published lessons, two authentic measured-data
labs per course as a target that the dataset gate decides, four
physics-and-AI method paths with valid lessons, and the formal-verification
strand, navigable from a course-first learning path, with every published
address intact. A curriculum is complete when the actual lesson inventory
reconciles to that set with substantive lessons, not placeholder cards.

## Target users

Primary user: **advanced self-directed learners**, including undergraduate and
graduate physics students, who already have both undergraduate-level physics
(classical mechanics, calculus, linear algebra) and solid programming skills.
Lessons do not re-teach either; they teach the combination: modelling,
numerical methods, experimental analysis, agentic experimentation, and formal
verification applied to physics. Each lesson is self-contained at its declared
prerequisite level: a reader with the stated prerequisites can follow the main
physical argument, derivations, worked examples, code, and figures without
leaving the site. Lessons do not assume advanced knowledge unnecessarily when
a concept can be explained clearly, and they offer optional deeper reading
rather than a beginner textbook.

Secondary roles:

- **University educator**: reuses published lessons in teaching through
  instructor packs (lecturer guide, objectives, prerequisites, assignment,
  rubric, reference solution, a no-AI pathway), cites the project, and gives
  feedback through Issues. Educators are an important audience, never a
  mailing list.
- **Maintainer/author** (the project owner, assisted by AI agents): writes and
  reviews lessons, operates CI, merges content.
- **Outside contributor**: proposes, assesses, or drafts content through
  GitHub Issues and reviewed pull requests (later phase, see MVP scope).

There are no administrator or signed-in learner roles.

## Primary use cases and journeys

1. **Follow the learning path.** A learner opens the site, sees the ordered
   path: physics courses organised by subject (classical mechanics first;
   then thermodynamics and statistical physics, waves and optics,
   electromagnetism, fluid dynamics, quantum physics, astrophysics with
   cosmology and relativity, and condensed matter and materials physics, as
   each gains a lesson), with AI-assisted research and formal verification
   exposed as cross-cutting methods through tags, related lessons, and
   cross-links rather than as physics subjects. A secondary view shows the
   four physics-and-AI method paths (physics reasoning and scientific
   agents, scientific law discovery, physics agent benchmarking, autonomous
   scientific research) over the same lessons, never as duplicate pages.
   Since decision 36 the same page is also the course atlas: a physics map
   of the eight courses, the four method paths, and the Lean and method
   views, generated from the curriculum file and the lesson metadata, from
   which a learner reaches every published lesson with or without
   JavaScript, next to the course index that stays.
   The learner picks a course, expands it, picks the next lesson, reads it,
   runs or inspects the code, works the exercises or plays with the
   interactive visualization, and moves on. The existing strand identifiers
   (`mechanics`, `agents-llm`, `agents-abm`, `lean`) and published URLs stay
   until an approved migration plan exists; new courses receive stable
   identifiers and route rules through an approved architecture decision.
2. **Run a lesson's experiment locally.** A learner clones the repository,
   installs the pinned Python environment, and re-runs any lesson's
   experiment with the exact commands the lesson gives, regenerating its
   numerical results and figures with identical results to those shown on
   the site; optionally, with the Lean toolchain, the learner checks the
   lesson's proofs. Neither activity requires rendering, rebuilding, or
   previewing the website (decision 33).
3. **Run an agent-driven experiment.** In the agents strand, a learner runs a
   provided LLM agent locally with their own API key; the agent proposes
   hypotheses, runs the lesson's simulation code, and reports results. A
   separate strand uses agent-based modelling (multi-agent simulations without
   LLMs) as a modelling technique.
4. **Read and check a formal proof.** In the Lean strand, a learner follows a
   proof of a physics result on the site, opens it in the Lean web editor or
   locally, and sees CI evidence that it compiles.
5. **Author a lesson** (maintainer): write a lesson in the repository's lesson
   format, add its code and tests (and Lean file if any), open a pull request,
   let CI execute the code and build the proofs, review, merge; the site
   republishes automatically.
6. **Propose new content** (later phase): an outside contributor or agent opens
   a GitHub Issue proposing a lesson; it is assessed, drafted, and merged via a
   reviewed pull request.
7. **Adaptive learning** (later phase): the site recommends the next lesson or
   extra exercises based on quiz/self-check results stored only in the
   learner's browser.
8. **Investigate a real measurement** (later phase): a learner opens a lab
   built on a real dataset, reads where the data came from and what was done
   to it, reproduces the measured-versus-model comparison and its residuals
   locally from a small committed sample or a documented download, and reads
   a plain-language statement of what the evidence supports. A no-LLM path
   always exists.
9. **Build a simulation with a coding agent** (later phase, optional): a
   learner drives a coding agent (for example Claude Code or Codex) on their
   own machine with their own account, from an approved physical
   specification to a tested Python simulation, under a sandbox, an
   allowlist, a budget, and their own review. The lesson teaches how to
   verify the agent's code, assumptions, and units.
10. **Go deeper** (any lesson): a learner who wants more follows a curated
    external reference placed at the relevant concept, with a short note on
    why it is worth visiting; the lesson's principal exercise never requires
    it.
11. **Teach with a lesson** (later phase): an educator downloads a published
    lesson's instructor pack, adapts it under the content licence, cites the
    project, and reports improvements through an Issue.

## MVP scope

The first usable release is a **thin vertical slice of all three pillars**:

- A small mechanics course of roughly 6 to 10 lessons with numerical
  simulations (for example kinematics, Newton's laws, projectile motion with
  drag, energy and momentum conservation, the harmonic oscillator, and the
  numerical integrators used to simulate them). Exact lesson list is decided
  during planning.
- At least one agents lesson: an LLM agent that designs and runs an
  experiment on one of the mechanics simulations, runnable locally with the
  learner's own API key.
- At least one agent-based-modelling lesson (multi-agent simulation without
  LLMs), or an explicit roadmap slot for it if it does not fit the first
  release.
- At least one Lean 4 + Mathlib lesson proving a physics result from the
  course (for example a kinematic identity or a conservation law for a simple
  system), with CI running `lake build`.
- Every lesson contains: clear explanation, explicit assumptions, worked
  examples, reproducible code, and exercises or an interactive visualization
  where useful.
- The site is published as a static site on GitHub Pages and rebuilt from
  `main` by CI.
- CI executes all lesson Python code and builds all Lean proofs on every pull
  request and on `main`; a lesson whose code fails or whose proof does not
  compile cannot be merged.
- A documented authoring workflow (lesson template, local verification
  command) so the maintainer and agents can add lessons consistently.
- A public repository with licenses: MIT for code, CC BY 4.0 for lesson text
  and figures.

Later phases (in scope for the project, out of scope for the MVP):

- Adaptive learning (browser-local, no accounts).
- GitHub Issue workflow for proposing, assessing, and drafting new content
  through reviewed pull requests, including agent-assisted drafting.
- The reference curriculum of decision 23: the remaining seven physics
  courses and the growth of mechanics to the slots the change request
  `docs/changes/final-curriculum.md` enumerates, including the
  fundamental and numerical additions of its revision 2 (rotational motion,
  thermodynamic cycles, acoustics, finite-volume methods, special
  relativity), the finite-element bridge from the finite-difference heat
  solver, and the three applied capstones of its revision 3 (thermal
  engineering of a hypothetical AI accelerator; adaptive phased-array beam
  steering; propagation of the 2025 Kamchatka tsunami), each the culminating
  application of its own course. Lessons are delivered in dependency order
  through independently verifiable features; there is no rule that a slot
  is a feature (decision 31).
- The four physics-and-AI method paths of decision 25, reusing the models
  and measured datasets of the physics courses, including the video
  reasoning and conservation-law discovery lessons of revision 2.
- The Learning Path page redesign of decision 29, as its own feature before
  the bulk of the new lessons.
- Verification that scales with the curriculum (decision 30, delivered for
  pull requests as F61; its budget is the 20 minutes of decision 34).
- Clarity and usability of the published site: honest homepage narrative,
  a generated prerequisite graph, learning-path cards with a difficulty
  scale, a reusable lesson template, course navigation from one source of
  truth, a unified tested local-setup guide organised around running
  experiments, a glossary, self-hosted search.
- The research-backed editorial standard below, applied first as a pilot on
  the numerical-integrators lesson and one introductory mechanics lesson,
  then as lesson-by-lesson editorial and figure passes.
- The editorial voice of decision 32: an editorial style guide with
  before-and-after examples, a pilot on mechanics lessons 01 to 05 that a
  human approves before the voice reaches the rest of the curriculum, and
  the integration of the approved principles into the authoring guide, the
  lesson template, and a qualitative editorial review rubric.
- Learner instructions without a website build (decision 33): the public
  setup page, lesson footers, README, and the authoring templates that
  generate them give experiment-execution instructions, with a runnable
  entry point for every published lesson.
- The simplification of scientific verification, CI, and the agents' build
  obligations of decision 35, planned and critically reviewed before any
  change to what a push to `main` executes.
- The scientific atelier and the course atlas of decision 36: the visual
  direction, the homepage, the atlas at the existing path address, and
  the shared templates, delivered in bounded slices after one end-to-end
  preview of Home, the atlas, and one existing lesson, with the asset
  classes of decision 37; the validated interactive pendulum is a separate
  later feature.
- The governed visual agent skills of decision 38: audited, pinned,
  project-local skills for visual and scientific-illustration work, a
  project-owned scientific-visualization skill, and the planner,
  implementer, reviewer, and verification contract that makes their use
  traceable, piloted on bounded features before any wider adoption.
- The risk-proportionate verification and review workflow of decision 39:
  three risk levels, an evidence lifecycle with per-criterion gates, a
  traceable chain of delta reviews for medium-risk changes, and owner
  approval that GitHub enforces at the merge, delivered as two bounded
  workflow features in strict order and evaluated on a pilot of features
  from existing artifacts.
- Trustworthy scientific coding: agent-assisted simulation development,
  independent code verification and review, a counterexample-hunting agent,
  further Lean proofs and local Lean exercises.
- Real experimental measurements: a dataset registry with a feasibility
  gate, shared experimental-methods and visualization foundations, and labs
  on measured data (candidates: gravitational-wave strain, a wave flume,
  optical diffraction, flow fields, microwave S-parameters), one lab at a
  time after a go decision.
- Instructor packs for published lessons.
- Open-source identity: discreet creator and JIDAI attribution, an About
  page, README and citation metadata, and contribution paths.
- Research capstones: autonomous experimental design, agent-assisted theorem
  proving, reproduction of an open physics paper, an optional local tutor.

## Non-goals

- No user accounts, sign-in, or server-side learner data, now or in the
  adaptive-learning phase.
- No backend or runtime server: the site is static. LLM agents run on the
  learner's machine with the learner's credentials; the site never calls an
  LLM at runtime and never holds API keys.
- No analytics, tracking, cookies, or third-party telemetry.
- No re-teaching of prerequisite physics or programming; the audience is
  advanced, and lessons may state prerequisites and link out instead. This
  does not license terse lessons: the concepts a lesson itself teaches are
  explained on the site, and a glossary defines assumed vocabulary concisely.
- No hosted or runtime LLM calls, no required model account, and no LLM
  tutor or chat on the site; any AI assistance is an optional local workflow.
- No marketing: no intrusive logos, banners, splash screens, mailing-list
  gates, lead forms, sponsor or endorsement claims, automated e-mail
  campaigns, or user-data harvesting. University adoption means teaching
  materials and feedback, not outreach campaigns.
- No repository transfer, no change of GitHub Pages URL, and no change of
  copyright or licence holders as a side effect of attribution or branding.
- No bundling of large or restricted datasets, photographs, or figures
  derived from restricted data into the repository or the site.
- No claim that a Lean proof establishes the physical accuracy of a
  measurement or the correctness of Python code, and no claim that every
  experiment has an LLM or Lean counterpart.
- No languages other than English.
- No in-browser Python execution (Pyodide) and no hosted notebook
  infrastructure for the MVP; links to external notebook services are allowed
  but not required.
- No formal verification of the Python simulation code itself; Lean proofs are
  about the physics models, not the programs.
- No certification, grading, or assessment that leaves the learner's browser.
- No mobile app.
- No lessons that build sensor experiments, record audio, collect classroom
  or smartphone data, control laboratory instruments remotely, or operate an
  autonomous physical laboratory. Measured-data labs analyse authentic,
  properly licensed, already-collected data; the acoustics lesson is
  numerical, and the video-reasoning lesson uses approved existing clips or
  reproducible generated clips, with no webcam, upload service, or
  device-control backend.
- No standalone mathematics curriculum, no physics-informed machine-learning
  track, and no generic AI-engineering or machine-learning curriculum. The
  nuclear and particle, plasma, and geophysics and climate expansions are
  outside the core curriculum until a separate decision adds them.
- No applied capstone presented as a calibrated digital twin of real
  hardware, as a fabricated or validated device, or as an operational
  forecast: the accelerator model is a digital-twin-style teaching prototype
  with hypothetical loads, the phased-array model is an array-factor model
  and not a full-wave or metasurface design, and the tsunami model is
  teaching-scale and not for warning, inundation, or hazard forecasting.
  Capstones are limited to the three the change request selects; no other
  course adopts a capstone requirement.
- No heavyweight solver (CAD, meshing, finite-element, full-wave,
  geophysical, or high-performance computing packages) as a mandatory build
  or CI dependency; such tools are optional local comparators.
- No stock, hand-copied, or externally hosted images anywhere on the site;
  every lesson preview derives from a verified generated figure or a
  repository-generated conceptual fallback (the F63 contract). The earlier
  blanket exclusion of decorative imagery and animation (this non-goal
  before decision 37, and the out-of-scope lines of F44 and F64) is
  superseded by the asset classes of decision 37: interface artwork and
  conceptual illustrations (generated by repository code or authored as
  committed SVG), and animations are allowed
  where that decision says, and nothing visual is added for decoration's
  own sake, as a scientific evidence claim it cannot support, or as a
  mandatory element of every lesson.
- No new frontend framework, Node or JavaScript bundler, second site
  generator, KaTeX or other equation renderer in place of native MathML,
  backend, authentication, hosting migration, runtime service, or paid
  model or API requirement for the atelier, the atlas, or the visual
  skills; no CAD or parametric-modelling tool (FreeCAD, OpenSCAD) as a
  skill or dependency; no routine animation rendering in CI; no generated
  raster image as the navigation surface of the map; no browser storage
  for the map's controls; no experiment gallery, empty or linking to
  experiments that do not exist, before enough real browser experiments
  exist; no JavaScript physics or illustrative motion on the homepage
  that the build did not verify.
- No editorial voice imposed as a uniform register: no rewrite of the
  whole curriculum in one feature, no conversational or informal tone
  forced on every lesson, no artificially added jokes or anecdotes, no
  identical narrative structure for every lesson, no rigid narrative
  template, no mandatory additional editorial agent, no relaxation of
  scientific standards, and no optimisation against AI-content detectors.
  The editorial voice replaces no part of the verification pipeline.
- No instruction to a learner, contributor, author, or developer in
  maintained documentation to rebuild or preview the website locally, and
  no relocation of such instructions to contributor documentation.
  Technical references to internal build behaviour, script names,
  architecture, and verification evidence may remain.
- No automatic scheduled full verification audit (nightly, weekly, or
  rotating), no new sharding mechanism, and no substantial verification
  infrastructure without separate evidence and explicit owner approval.
- No removal of the internal CI site build, the deployment of the verified
  artifact, provenance, accessibility, scientific checks, or the ability
  to run complete verification, under any verification simplification.
- No weakening of the digest, selection, base provenance, build,
  deployment, or determinism guarantees, of the complete CI run on every
  pull request and push, or of independent review by a different model,
  for the sake of lead time; no new mandatory agent and no new mandatory
  reporting gate in the feature workflow; and no workflow rule that an
  agent can satisfy with its own assertion of the owner's approval
  (decision 39).

## UX expectations

- Static, fast, readable pages; works without JavaScript for all text, code,
  equations, diagrams, proof explanations, and static figures. JavaScript is
  required only for optional enhancements (interactive visualizations,
  self-checks, self-hosted search), each of which must degrade gracefully
  (static figure, plain exercise, or navigational fallback when scripts are
  unavailable). Heavy interactive visuals load only when needed and within a
  page payload budget the planner sets.
- Responsive layout usable on phone, tablet, and desktop.
- Accessibility target: WCAG 2.1 AA for site chrome and lesson content;
  equations are rendered with accessible markup; figures have alt text.
- A visible learning path with ordering, difficulty, and prerequisites per
  lesson, so learners always know where they are and what comes next.
- Learning Path page: a calm, scientific, course-first overview of the
  physics courses, each with concise text, a verified miniature, and its
  real published-lesson count and entry point; a course's lessons behind
  native, accessible progressive disclosure (`<details>`/`<summary>` or a
  demonstrably equivalent semantic construct), closed by default except
  possibly the current course, reachable without JavaScript; compact lesson
  cards (title, one-sentence physical question, difficulty, a small verified
  thumbnail, unobtrusive chips for simulation, experimental data, and AI
  extensions) with outcomes, prerequisites, what the learner builds, related
  extensions, the capstone classification, and reproduce links on
  expansion; the method paths, agent-based modelling, and Lean as a
  secondary view or filter over the same canonical pages; the prerequisite
  graph with its textual alternative under an optional dependency-map
  disclosure, with course-scoped subsets allowed; optional filters by
  course, method, difficulty, and publication state that coordinate with
  the self-hosted search; a planned lesson is visibly distinguished or
  omitted and never shown as published. Thumbnails derive deterministically
  from the lesson's own verified figures or a repository-generated
  conceptual fallback, with alt text and no external image dependency. The
  page meets the responsive, accessibility, payload, and determinism rules
  of this section, uses no frontend framework, and keeps every existing
  link, bookmark, and graph node address valid. All of it is generated from
  the validated lesson front matter; no second hand-maintained catalogue.
- Visual direction, the scientific atelier (decision 36): every page has
  the quality of a carefully designed scientific publication with optional
  interactive experiments: warm paper-white backgrounds, nearly black
  text, cobalt blue and vermilion accents, elegant serif headings,
  readable body typography, precise monospaced annotations, thin rules,
  and generous whitespace. The direction is implemented with scoped CSS
  and shared templates and includes on the existing Quarto site, with
  self-hosted fonts whose licences are recorded, within the existing
  payload budgets measured for the complete initial page and the map
  enhancement, meeting WCAG 2.1 AA and the 320 CSS px reflow rule, with
  visible keyboard focus and respect for reduced motion. The mockups that
  chose the direction are visual references, not curriculum data or
  validated figures; the owner reviews a rendered preview of Home, the
  atlas, and one existing lesson at desktop, tablet, and phone widths
  before final visual acceptance.
- Visual asset classes (decision 37): every visual on the site belongs to
  one of three classes and is identifiable as such. Interface artwork
  (visual identity and navigation, SVG generated by repository code or
  authored for this project and committed with its author and licence
  recorded, without any scientific evidence claim) is allowed in the site chrome, on Home, on
  the atlas, and in course, module, and capstone openings. Conceptual
  illustrations (scientifically sound explanatory diagrams, not presented
  as numerical or experimental results, likewise generated by repository
  code or authored as committed SVG) are allowed in lessons when they
  genuinely improve understanding. Scientific results (plots,
  simulations, measurements) keep the reproducible generation and the
  verification of this document; the rules under "Scientifically faithful
  figures" and the F63 preview contract are unchanged. An animation is
  allowed in any class when it is pedagogically justified, accessible,
  and accompanied by a meaningful static alternative: it starts paused or
  respects the reduced-motion preference, has play, pause, and reset
  controls with units and sensible parameter limits where it has
  parameters, and is never mandatory for a lesson. A diagram presented as
  a lesson result follows the scientific generation and checking rules;
  no mockup equation, plot, or illustrated measurement ships as verified
  science.
- Home page (decision 36): a shared header with a small project mark,
  concise primary navigation, and a clear start link; the opening "Build
  a world. See if it obeys physics." with a static figure generated by an
  existing verified Python implementation (the double-pendulum lesson if
  its implementation is sufficiently validated, otherwise another
  verified mechanics figure), composed in the atelier language with its
  scientific content faithful to the model and its provenance stated; the
  introduction of Part A and Part B derived from the real course
  structure, with links into the atlas; capstone highlights grounded in
  the current delivery state; a short invitation to begin; a footer with
  attribution, source, licences, and secondary navigation. The section
  "From a question to a working model" is absent and is not replaced by
  a renamed three-step teaching formula; the introduction, the course
  structure, and the actual projects communicate the approach. No fake
  metrics, testimonials, or inferred learner progress. Interactive
  controls and animation of the opening figure arrive only with the
  validated interactive pendulum, a separate feature after numerical
  validation and a cross-language reference check against the existing
  mechanics implementation.
- Course atlas (decision 36), at the existing path address with every
  existing anchor and bookmark valid and "the atlas" allowed as the
  display label: breadcrumb, title, and a short explanation; a switch
  between a physics map and the course index of the Learning Path bullet
  above, with search and filter integration where it adds value; a large
  illustrated concept map, as build-generated semantic HTML and SVG
  enhanced by small dependency-free JavaScript modules, limited to the
  approved curriculum, showing all eight Part A courses, the four Part B
  method paths as a connected research layer that does not obscure their
  distinctions, and the Lean and method views; a selected-concept panel
  with a short explanation and canonical lesson links; the complete
  accessible course, module, and lesson index with its metadata and the
  existing learner features; capstone links or explicitly labelled
  planned projects; the shared footer. The map distinguishes three edge
  types explicitly: a conceptual connection, curated with a short
  rationale; a prerequisite, generated from the existing prerequisite
  data, never invented for a planned lesson; and capstone membership,
  linked only when published; modes may show concepts and prerequisites
  separately. Course areas may have subtle boundaries and meaningful
  small illustrations, never a geography that suggests relationships it
  cannot support. The map may show the reference curriculum, with planned
  concepts and slots visibly labelled and distinguishable without colour
  alone; a planned slot is never a lesson link, is never counted as
  published, and may reveal its planned description without implying
  usable lesson content; the thermal and tsunami capstones are shown as
  planned with the roadmap's descriptions (the thermal project is a
  hypothetical accelerator, not a named commercial chip), and the EM9
  phased-array capstone stays in the index and the map. Every published
  lesson stays reachable without JavaScript through native links and
  disclosures with a semantic textual equivalent of the map; selection,
  zoom, and filters are enhancements, with visible keyboard focus,
  labelled controls, and a screen-reader reading order that works; no
  browser storage for the map's controls, and the existing progress and
  recommendation behaviour keeps its contract. On a phone, a readable
  region selector, a focused map view, and an ordinary list; a desktop
  map is never shrunk until its labels are unreadable.
- Shared templates (decision 36): course and module openings with one
  relevant scientific illustration, an introduction, prerequisites, and a
  compact lesson list, reusing existing course sections and adding routes
  only for a clear purpose within the migration plan; lessons with a
  calm reading column of appropriate line length, a table of contents,
  legible code and MathML, larger figures where useful, the current
  prerequisites, and previous and next navigation, preserving section
  identifiers, claims, calculations, results, references, and experiment
  commands; capstones with a strong project opening and a spacious model
  and results presentation, where dark navy may frame visualizations
  while instructions stay readable, and where a standalone interactive
  lab is separately scoped additional functionality; About and
  supporting pages in the same language with the glossary, evidence map,
  setup, contribution, search, and licence access preserved. The
  redesign is presentation and navigation, not a curriculum rewrite:
  lesson text, scientific code, computed values, units, reference keys,
  and claims change only through a separate reviewed change, and no
  "Observe, Predict, Build, Explain" or other narrative structure is
  imposed on lessons; the editorial programme of decision 32 is
  coordinated with, not merged into, the redesign. Lesson rows reuse the
  F63 previews; map artwork is a distinct asset class, not a replacement
  for them.
- Consistent lesson structure: explanation, assumptions, worked examples, code,
  exercises/visualizations, and a "Run this experiment" section (or an
  equivalently clear label) pointing at the exact files, source revision,
  and commands that regenerate the lesson's numerical results and figures
  without generating HTML. Where a lesson's runnable experiment exists only
  in the cells of its page, the lesson provides a runnable entry point, a
  script or notebook that calls the authoritative lesson implementation,
  without duplicating scientific logic.
- Learner setup around experiments: the public setup page describes the
  repository clone or download, the pinned Python environment, and the
  experiment commands; the optional Lean setup for checking proofs and
  exercises is clearly separated from the Python-only path; replaying a
  recorded agent experiment is distinguished from a live provider call,
  which requires explicitly documented credentials and dependencies, so
  that ordinary reproduction never calls a paid model. A Python learner
  needs no elan, Mathlib, browser-test installation, workflow tooling, or
  LLM credential unless the activity they chose needs it. The full
  verification pipeline, Quarto rendering, and the website preview are
  not presented as learner setup.
- Editorial voice: a recognisable authorial voice that combines the
  curiosity and accessibility of a personal technical blog, the
  mathematical rigour of a university-level textbook, and the
  reproducibility and verification standards of this project. The style
  guide gives principles for lesson openings, intuition, derivations,
  computational experiments, the interpretation of results, transitions,
  and conclusions, with before-and-after examples drawn from existing
  lessons and from the author's earlier articles at ataspinar.com, and
  names the recurring faults to remove: boilerplate introductions,
  repetition, needlessly defensive wording, monotonous sentence structure,
  and conclusions that do not interpret the significance of a result.
  Lessons keep structures and narratives appropriate to their subject.
  Editorial review is qualitative, naming specific weaknesses with
  evidence and actionable feedback, never only a score. No scientific
  claim, result, formula, or verified artifact changes for a stylistic
  reason; the required section identifiers, lesson contracts, and
  verification guarantees stay.
- Progressive depth, self-contained: for each major concept a lesson gives the
  physical question and why it matters, the core explanation on the site
  (intuition, definitions, assumptions, essential derivation steps, units,
  limits of applicability), a worked example that bridges the mathematics to
  the specific code (state variables, update order, tests, observable
  results), an interpretation of what each figure or table means, and one
  concise self-check. The depth of each layer follows intellectual
  difficulty, not a word count, and short lessons do not need every section.
- Purposeful external references: an external link is an optional depth path
  at the relevant concept, never a substitute for a missing core explanation.
  Every proposed link is researched at edit time (at least two candidate
  sources compared where practical, the passages opened and read, the exact
  method variant and notation checked, access and stable section URL
  verified) and its selection evidence recorded (concept, URL, author or
  publisher, section, pedagogical role, statement checked, alternatives,
  last-checked date, licence concerns). No automatic linking of technical
  nouns, no link quotas, no paywalled or sign-in-only core references, no
  "click here" link text, no rehosted third-party diagrams without permission.
- Scientifically faithful figures: every figure or animation states its
  source status (measured, calibrated, processed, simulated, or conceptual),
  has labelled axes with units, a legend, a caption that answers what the
  experiment or simulation showed, and, where relevant, measured-versus-model
  panels with residuals or uncertainties. Colour scales are accessible and do
  not conceal sign; false-colour images are never presented as natural
  colour; smoothed or interpolated data is never presented as raw. Every
  animation has a static keyframe, and browser interactions cannot alter the
  claimed observed values. Numeric outputs appear as tables with units and a
  plain-English interpretation, not console dumps.
- Typed claims: each scientific claim is marked as observational,
  experimentally supported, numerically verified, or a formal theorem, with
  its declared scope.
- Lesson navigation, course membership, and prerequisite data come from one
  source of truth; a lab belongs to one primary physics course and links to
  its AI, experimental, and Lean extensions instead of being duplicated.
- Identity: Physics by Construction is the brand, heading, and focus of every
  page. Creator and JIDAI attribution is discreet and consistent (one
  canonical description for home, footer, About, README, instructor packs,
  and citation metadata), stays legible on mobile and without JavaScript,
  and is not repeated in every lesson.
- Code shown on the site is the code that CI ran (no hand-copied snippets that
  can drift), and figures on the site are the figures that code produced.
- Lean proofs are displayed with syntax highlighting and link to the Lean web
  editor or the repository file for exploration.
- Exercises provide self-check answers or solutions on the page.
- Reading experience targets, to be verified by CI where practical: pages
  render without layout shift on figure load, and the site builds deterministic
  output.

## Data and persistence

- The repository is the single source of truth: lessons, code, tests, Lean
  sources, figures (or the code that generates them), and site configuration.
- Published site data is the static build output; it holds no learner data.
- Learner state (progress, quiz results, adaptive recommendations) exists only
  in the learner's browser (local storage) and only once the adaptive-learning
  phase lands. It is never transmitted. Clearing browser data clears it;
  no recovery is offered.
- Reproducibility requires pinned toolchains: Python version and dependency
  lock file, Lean toolchain and Mathlib version pinned per release, and any
  JavaScript dependencies locked.
- Generated artifacts (figures, simulation outputs used in lessons) are either
  regenerated by CI at build time or committed alongside the code that
  produced them with a check that they are up to date; the planner chooses.
- Retention: Git history is the retention policy; nothing else is stored.
- Real datasets are inputs, not generated artifacts. Before a dataset is
  committed to in a lesson it passes a feasibility gate: an actual small file
  has been inspected, its schema, units, calibration, and time coverage
  validated, one reproducible scientifically meaningful plot produced, its
  provenance and rights established, and its download, build, and site
  payload sizes estimated. A catalogue entry is not a validated lab.
- Every dataset a lesson uses has a metadata card: source DOI or URL,
  creator, licence or permission status (including redistribution of subsets
  and of derived figures), measurement type (raw, processed, calibrated,
  modelled reference, or synthetic test, assigned per data artifact),
  calibration details, version, units, cadence, access method, documented
  uncertainty, and checksum where available. A public download is not
  automatically licensed for redistribution.
- A small, version-pinned, rights-cleared sample may be committed at a
  declared location with its metadata card, under a size cap the planner
  sets; tests parse it and assert field names, shapes, units, masks, and
  cadence. Large or restricted datasets are never committed; learners fetch
  them locally with versioned, tested instructions, and the site links to the
  original data when redistribution is not allowed.
- The curated external-reference register (selection evidence per link) lives
  in the repository as a small maintainable file or lesson-level notes.
- The course atlas has one source of truth and one small addition: course,
  path, and slot information comes from `site/curriculum.yaml`, and
  publication state, titles, prerequisites, and canonical URLs from the
  current lesson metadata; a small validated map manifest holds only what
  those do not represent (concept identifiers, display placement,
  concept-to-slot associations, and curated conceptual connections with
  their rationale). Every course, path, slot, and lesson reference in it
  resolves, concept membership is never inferred from lesson titles
  alone, and no second hand-written lesson catalogue exists.
- Visual and scientific-illustration assets keep their sources: an
  interface illustration, a conceptual diagram, a scientific figure, or
  an animation has its source in the repository (the generating code, or,
  for interface artwork and conceptual illustrations only, an authored SVG
  with its author and licence recorded), with the figure's data and seeds
  where applicable, and the completion evidence
  of the feature links the rendered or generated artifact to that source.
- Measured-data target: every mature physics course aims at two designated
  authentic-data labs, sixteen in all, as a curricular target that the
  feasibility gate decides case by case; a course may launch with
  simulations first, and no dataset is accepted because the curriculum names
  it. An applied capstone's comparison with historical observations (for
  the tsunami capstone, DART station records and bathymetry) passes the
  same gate before publication and is a validation component of the
  capstone, not a seventeenth designated lab; the capstone's simulation and
  benchmark core does not depend on that approval and is published as
  clearly simulated until it is granted.

## Authentication and authorization

- Learners: none. The site is anonymous and public.
- Maintainers and contributors: GitHub repository permissions. `main` is
  protected; changes land via pull requests with passing CI. Outside
  contributions arrive as Issues and pull requests under the repository's
  CODEOWNERS and review rules.
- Owner approval of a Level 3 change and of a lowered risk level
  (decision 39): a second GitHub identity, held only by the owner and
  never used by an agent, gives an approving review of the pull request;
  the ruleset of `main` requires a code-owner review, and `CODEOWNERS`
  assigns the protected paths of `guardrails.conf` to that identity, so
  GitHub itself refuses the merge without it. The agent's `gh` login is
  the owner's account, so nothing that login writes (a comment, a review,
  a file, a flag, or a statement in chat) is proof of the owner's
  approval. The owner creates the identity, grants it access, and changes
  the ruleset and `CODEOWNERS`; an agent never changes repository
  settings or creates accounts.
- CI: GitHub Actions deploys to GitHub Pages using the workflow's own
  short-lived token with least-privilege permissions; no long-lived deploy
  credentials.
- LLM credentials: never stored in the repository or in CI for the MVP.
  Learners supply their own API key locally for agent lessons. The
  content-drafting workflow holds no LLM API key as a GitHub secret either:
  drafting runs on the maintainer's machine (ADR 006).
- Coding-agent and Lean-generation exercises use the learner's own accounts
  and credentials on the learner's machine; none is required to read, build,
  or reproduce any lesson. No paid-model token or secret appears in static
  web assets or CI.

## External integrations

- **GitHub**: repository, Issues, pull requests, Actions (CI and deployment),
  Pages (hosting). Required.
- **Lean 4 toolchain and Mathlib**: fetched in CI for proof checking. Required.
- **Python ecosystem** (scientific stack, exact packages chosen in planning):
  fetched in CI and by learners locally. Required.
- **LLM provider API** (for agent lessons): used only on learners' machines
  with their own keys. Lesson code should isolate the provider behind a thin
  interface so switching providers is cheap; the default live provider is
  OpenAI, as an optional dependency (settled in F09). Not a site dependency.
- **Lean web editor** (live.lean-lang.org or equivalent): optional outbound
  links for exploring proofs. No integration beyond links.
- External notebook services (Colab/Binder): optional outbound links only.
- **Open-data portals** (for example Zenodo, GWOSC, CERN Open Data, NASA and
  ESA archives, as recorded in the dataset registry): read by the maintainer
  when curating and by learners locally when a lesson documents a download.
  Never contacted by the site, by the build, or by CI.
- **Coding agents** (for example Claude Code, Codex): optional tools learners
  run locally with their own accounts in agent-assisted exercises. Not a site
  or CI dependency; the site verifies only the code and tests they produce.
- **Reference solvers and discovery tools** (candidates: REBOUND, QuTiP,
  FEniCSx, Gmsh, PhiFlow, Clawpack, GeoClaw, Dedalus, PySR, PySINDy):
  optional local comparators or producers of reference artifacts with
  recorded provenance, adopted only where they improve teaching and
  verification. The required, deterministic path of every lesson runs on
  the pinned scientific Python stack; none of these tools is a mandatory
  build or CI dependency. External benchmark assets are not embedded before
  their licences and scientific assumptions are checked.
- **Curated external references**: outbound links only. Link validity is a
  separate, resilient maintenance check run periodically or on demand, never
  a build or merge requirement; builds and reading never depend on an
  external site.
- **JIDAI website** (`jidai.nl`): outbound attribution link only. The JIDAI
  portfolio or case-study page is a separate company-site task outside this
  repository.
- **Visual agent skills** (decision 38): guidance and tooling for the
  agents of the planning, implementation, and review workflow, never a
  site, build, or CI dependency and never evidence that physics is
  correct. Candidates are Impeccable (typography, layout, hierarchy, and
  interface refinement), Anthropic Frontend Design (shared interface
  elements, responsive presentation, and interactive components within
  Quarto), Diagram Design (conceptual physics illustrations), and,
  optionally, Manim (mathematical or physics animations), plus the
  project-owned PBC Scientific Visualization skill. A third-party skill
  is used only after an audit of its exact upstream `SKILL.md`, scripts,
  references, licence, security assumptions, pinned revision, and
  dependencies; it is pinned and kept in a project-local, versioned
  location that the actual runner finds in every feature worktree, or
  replaced by a thin project-owned adapter that references approved
  source material when vendoring is unsuitable; it is never a globally
  installed skill on the owner's machine, never fetched as mutable
  instructions, and never installed by a third-party installer in CI.
  Its suggestions are adapted to the Quarto, `.qmd`, CSS, SVG, native
  MathML, Python, and GitHub Pages stack. Manim, if ever piloted, is a
  local pilot dependency outside the pinned learner and CI environments.
- No analytics, comment, search-as-a-service, or auth providers; search, if
  offered, is a self-hosted index built at build time.

## Runtime and deployment constraints

- Hosting: GitHub Pages, served from a GitHub Actions build of `main`.
  Public repository (required for free Pages).
- Site is fully static: HTML, CSS, JavaScript, images, and downloadable
  source. No server-side code, no runtime secrets.
- CI on every pull request and on `main`: lint/format checks, execution of all
  lesson Python code with tests, `lake build` for all Lean sources, and the
  site build. Deployment runs only from `main` after these pass. The existing
  `./scripts/verify.sh` must run the same checks locally.
- Verification that scales with the curriculum (decision 30), refining the
  rule above for lessons: the time a pull request waits depends on what it
  changes, not on the size of the curriculum. A pull request that changes
  one lesson executes and checks that lesson and every lesson that depends
  on what it changed; a pull request that changes shared code, the locked
  environment, the site configuration, or a toolchain executes and checks
  every lesson; every push to `main` executes and checks every lesson, so
  nothing is published that was not fully verified. A lesson counts as
  unchanged only when none of its inputs changed (its source, the modules
  of `src/pbc` it imports, its dataset samples, the lock file, the Lean
  toolchain and manifest, the site configuration, and shared templates), and
  the rule fails safe: when the inputs cannot be determined with certainty,
  everything runs. No check is dropped; a check runs less often only where
  a decision record says so and always on `main`. The selection is made by
  `./scripts/verify.sh`, so a local run and CI select the same lessons; a
  local run without options still verifies everything; the published site
  is still the site that was verified. The Lean build keeps running in full
  on every pull request (unresolved question 8). The budget of 20 minutes
  for a typical pull request with warm caches holds at 110 lessons
  (decision 34); 15 minutes is a non-blocking optimisation target, and a
  run above 15 but within 20 minutes meets the budget; every measurement
  records the actual duration and whether the target was met. The
  25-minute budget for cold caches and the 45-minute timeout per job are
  unchanged by that decision. The full run at 110 lessons and the retrieval
  of the base by a pull request from a fork are unmeasured and stay
  outstanding; no budget statement rests on an estimate.
- Verification simplification under review (decision 35): the rule that
  every push to `main` executes and checks every lesson stands until the
  decision record of decision 35 is accepted. That record may let a push
  to `main` inherit content-addressed scientific results from a previous
  successfully verified `main` base, only with proof of their validity for
  the current commit (lesson inputs, shared dependencies, verification
  logic, and the relevant execution environment accounted for), failing
  closed or running complete verification whenever reuse cannot be
  established, always rebuilding the publishable site and verifying its
  actual output, and always deploying exactly the artifact CI verified.
  A directly invocable complete verification path is preserved. The
  guarantee of inherited results is weaker than, and different from,
  executing everything on the current commit; the owner approves that
  difference and its minimum mitigations explicitly before `main` becomes
  incremental, after the staged evidence of decision 35.
- Agents' local verification before a pull request is proportional to the
  change: targeted tests, the execution and rendering of the lessons the
  change affects, Lean checks for affected proofs, and a local page or
  site render only for the change types that the decision record of
  decision 35 lists (rendering, templates, navigation, site
  configuration). CI owns the validation of the publishable site and
  remains the publication gate; `./scripts/verify.sh` without options
  still runs everything.
- Risk-proportionate verification and review (decision 39): every change
  carries one of three risk levels, the highest of the minimum its paths
  imply, the escalation triggers its nature hits, and the level an agent
  or the reviewer assesses; a level is raised freely and lowered only by
  the owner's authorization verified at the merge gate. Intermediate
  rounds of a Level 3 change may run targeted partial verification as
  feedback that is never evidence; the final acceptance is the
  verification tier the change needs on the final tree (a complete
  verification for Level 3), an independent review made after it, and the
  full CI, which stays the publication gate. Each acceptance criterion of
  a feature names the gate that clears it (implementation, pull-request
  CI, owner approval, or post-merge); a criterion whose evidence belongs
  to a later gate is pending, never a met criterion and never a reason for
  an owner exception. The complete CI run on every pull request and push,
  the aggregate required check `verify`, the deployment of only the
  verified artifact, the digest, selection, base provenance, check
  identity, and the safe fall-back to executing everything are unchanged.
- CI cost and time: Mathlib builds are heavy; the pipeline must use the
  Mathlib cache (or equivalent) and dependency caching so a typical pull
  request verifies in minutes, not hours. The planner must set a concrete
  budget.
- Verification of the atelier and the atlas: a change to shared CSS,
  templates, assets, or checks may invalidate every reused result and
  require the full verification tier; the redesign is not promised to be
  a targeted-only change, no check is weakened for a visual match, and
  scientific determinism and provenance are preserved. Regression checks
  are meaningful data, link, reference, and interaction checks plus
  visual review, not tests that reproduce CSS values, screenshot pixel
  comparisons, or full renders on every ordinary lesson change. Rendered
  visual review has three parts: the implementer records rendered
  screenshots at desktop, tablet, and phone widths as evidence artifacts;
  the independent reviewer assesses them with the built HTML and the
  sources; the owner's manual pass on the preview is the final visual
  acceptance.
- Reproducibility: pinned Python, Lean, and Mathlib versions; a single
  documented command reproduces the whole site and all lesson outputs locally
  on macOS and Linux, for maintainers, agents, and CI. A learner regenerates
  a lesson's results and figures with the lesson's experiment commands and
  is never instructed to build the site (decision 33); the new experiment
  commands are exercised by verification that they regenerate the intended
  results and figures.
- Availability: best effort, as provided by GitHub Pages; no SLA, no on-call.
- Domain: the GitHub Pages default URL. No custom domain for the first
  release; a custom domain is revisited only as its own decision.
- Repository and URL continuity: the public repository stays at
  `github.com/taspinar/physics-by-construction` under the creator's personal
  account, and the published Pages URL stays unchanged. A transfer to the
  `jidai-nl` organization or a project subdomain is a separate migration
  decision covering permissions, Issues and pull-request continuity, Pages
  settings, base path, CI, branch protection, and links; it is not implied by
  attribution.
- Offline builds: the build, every check, and every lesson work with no
  access to external websites, data portals, or model APIs; CI never fetches
  large or mutable remote datasets.
- Browser support: current versions of mainstream evergreen browsers.

## Security and privacy constraints

- No personal data is collected, stored, or transmitted by the site. No
  cookies, no analytics, no third-party scripts beyond what the site build
  itself serves (prefer self-hosted assets over third-party CDNs).
- No secrets in the repository or in the published site; `.env.example` only.
  Secret scanning and push protection stay enabled.
- Agent lessons must instruct learners to keep API keys in local environment
  variables, never in notebooks, code, or committed files, and lesson code
  must not log or print keys.
- Agent lesson code that executes model-generated actions runs only on the
  learner's machine; lessons must state what the agent is allowed to do (for
  example run the provided simulation functions) and must not grant it
  arbitrary shell or network access by default.
- Exercises that let a coding agent write and run code (agent-assisted
  simulation development, Lean proof generation) are optional local workflows
  under learner-controlled credentials. They require
  sandboxing, an explicit tool and command allowlist, budgets (steps, time,
  cost), and human review of the result before it is trusted. The site
  verifies the produced code, tests, and proofs in CI; an agent session shown
  on a page is either a replay fixture whose tool results CI recomputes or is
  visibly marked as not verified.
- Counterexample hunting is not such an exercise: its agent writes no code.
  It runs in the agent harness over an explicit allowlist of simulation and
  analysis functions, and is replayed deterministically in CI like the other
  harness agents (ADR 004).
- Content and research agents treat retrieved web pages and datasets as
  untrusted data, never as instructions. They may propose and log sources but
  never rewrite scientific citations or accept links without human review.
- CI workflows use least-privilege `permissions`; deployment uses the
  GitHub-provided OIDC/Pages token. Pull requests from forks must not receive
  write permissions or secrets.
- Supply chain: dependency lock files, Dependabot alerts enabled, pinned
  GitHub Actions versions. Agent skills are part of the supply chain:
  each third-party skill in use has a documented upstream source, pinned
  revision, licence decision, and dependency and security assessment
  before use, and a missing required skill fails a feature's
  configuration visibly or is replaced by an explicitly approved
  alternative, never omitted silently.
- Licensing compliance: code MIT, content CC BY 4.0, with attribution for any
  third-party material included in lessons; contributor submissions accepted
  under the same licenses.
- Rights of data and figures: before any sample, photograph, figure, or
  animation derived from a third-party dataset is published, its applicable
  terms are checked and recorded; restricted assets are never pushed to the
  public repository or site. Third-party diagrams are cited and linked, not
  rehosted without permission.
- Ownership accuracy: the copyright line stays "Ahmet Taspinar and the
  Physics by Construction contributors". JIDAI is acknowledged as the
  initiative's company, not as a copyright holder, funder, or university
  partner. Legal notices change only after a review of the actual code,
  content, and asset licences and with contributor consent; no university
  name or logo implies adoption or endorsement without explicit permission.
- Content integrity: a claim on the site is backed by code or proof that CI
  verified; lessons must mark anything not verified as such. Claims are
  typed (observational, experimentally supported, numerically verified,
  formal theorem). Lean never proves the physical accuracy of a measurement
  or the correctness of Python; a claim made by an LLM is tested against
  independent code or data before it is presented; measurements stay distinct
  from modelled references, fitted curves, reconstructed signals, and agent
  conclusions, with filtering, interpolation, and selection disclosed.
  A capstone's figures are generated by verified physics code, compare with
  an analytical, manufactured, independent, or trusted numerical reference,
  show refinement and genuine failure modes, and state which aspects are
  physically validated and which are only numerically checked; solver
  convergence, a colourful plot, or a digital-twin label is never physical
  validation, and model fit alone never proves a physical law.

## Major product decisions

Taken from `docs/PROJECT_DESCRIPTION.md` (given, not reopened):

1. English-language educational website about physics through programming,
   AI agents, and formal proofs in Lean.
2. Content organized as a learning path of increasing difficulty: basic
   mechanics and numerical simulation, then agent-driven experiments, then
   formal verification.
3. Every lesson has clear explanations, explicit assumptions, worked
   examples, reproducible code, and exercises or interactive visualizations
   where useful.
4. Static site on GitHub Pages; code and Lean proofs checked in CI.
5. First release is a small mechanics course; adaptive learning and the
   GitHub-Issue content workflow with reviewed pull requests come later.

Decided during Project Grill (2026-10-06):

6. **Audience is advanced**: undergraduate physics plus solid programming are
   assumed. Lessons do not re-teach prerequisites.
7. **"AI agents" means both strands**: (a) learners build LLM agents that run
   experiments against the lesson simulations, locally with their own API
   keys; and (b) agent-based modelling (multi-agent simulation without LLMs)
   as a modelling technique. They are separate strands in the learning path.
8. **MVP is a thin vertical slice**: roughly 6 to 10 mechanics lessons plus at
   least one LLM-agent lesson and at least one Lean lesson, so the full CI
   pipeline exists from day one.
9. **Python for lesson code, JavaScript for in-browser interactives**: all
   reproducible code is Python executed in CI; interactive visualizations are
   small embedded JavaScript widgets used only where they add value. No
   Pyodide, no in-browser Python.
10. **Lean scope**: Lean 4 with Mathlib, proving physics results about the
    models (kinematic identities, conservation laws, properties of integrators
    on simple systems). Proofs are shown on the site and linkable to the Lean
    web editor; CI runs `lake build`. Not verification of the Python code.
11. **No accounts; learner state stays in the browser**: progress and future
    adaptive learning use browser local storage only. No backend, no auth, no
    personal data, no sync.
12. **Public repository, open licenses, contributions welcome**: MIT for code,
    CC BY 4.0 for lesson text and figures. Outside proposals via Issues and
    reviewed pull requests.
13. **No analytics or tracking** of any kind.

Recommended defaults adopted without a separate question (reversible during
planning): WCAG 2.1 AA accessibility target; site must work without JavaScript
except for optional interactives; pinned toolchains with a single local
reproduce command; exercises carry self-check solutions on the page.

Decided during the change cycle `physics-next-phase` (2026-10-09), from
`docs/changes/physics-next-phase.md` and the answers recorded there:

14. **Three activities, real data included**: the mission is Construct,
    Investigate, Verify. Real experimental measurements and calibrated
    observations join simulation, agents, and proofs as first-class content,
    each lesson following the measurement-to-model loop under "Project goal".
15. **Courses by subject, methods cross-cutting**: physics courses are
    organised around subject matter (mechanics now, later candidates such as
    waves and optics). AI-assisted research, agent-based modelling, and
    formal verification are methods exposed through tags and cross-links,
    not physics subjects. Existing strand identifiers and URLs stay until an
    approved migration plan exists; a lab belongs to one primary course. This
    refines decision 2 without reopening it.
16. **Audience refined**: self-directed learners, including undergraduate and
    graduate physics students with the stated prerequisites, stay primary.
    University educators are an important secondary audience served through
    instructor packs. Lessons are self-contained at their declared
    prerequisite level and do not re-teach all prerequisites, but do not
    assume advanced knowledge unnecessarily.
17. **Research-backed editorial standard**: progressive-depth, self-contained
    lessons with purposeful, researched external references and recorded
    selection evidence, as specified under "UX expectations". The standard is
    piloted on the numerical-integrators lesson and one introductory
    mechanics lesson before bulk editing, with independent physics and
    pedagogy review.
18. **Dataset policy**: a feasibility gate before any lesson commitment,
    typed data artifacts, full provenance and rights cards, small
    rights-cleared samples committed under a size cap, no bulk or restricted
    data, no live portal access in builds or CI, and a visualization quality
    gate for every figure.
19. **Coding agents as optional local workflows**: learners may drive coding
    agents and Lean generation on their own machines with their own
    credentials, under sandboxing, allowlists, budgets, and human review; the
    site verifies the produced code, tests, and proofs. The allowlist model
    of decision 7 remains the default for agents shown on the site.
20. **Identity**: Physics by Construction is "an open-source educational
    initiative by JIDAI", created by Ahmet Taspinar (TU Delft Applied
    Physics alumnus, founder of JIDAI). Attribution is discreet and truthful,
    with one canonical description across home, footer, About, README,
    instructor packs, and citation metadata. The copyright line, the
    personal repository, and the Pages URL stay unchanged; JIDAI is not a
    rights holder. The `jidai-nl` GitHub organization exists with the creator
    as owner; its profile may link to the repository, and no transfer
    follows from that.
21. **Open-source-first community**: everything stays usable without an
    account, contact with JIDAI, tracking, or corporate links. No marketing
    surfaces, lead forms, mailing lists, or outreach campaigns. Contribution
    paths reuse the existing Issue workflow; instructor packs carry accurate
    citation and reuse terms.
22. **Scope controls for planning**: approved feature IDs F01 to F15 keep
    their meaning and active work on F10 to F12 is preserved; the candidate
    numbers in the change request are provisional until the roadmap is
    approved; the planner produces a deduplicated feature set, a mapping of
    every candidate to its outcome, and a first wave specified in detail,
    without creating 25 new features or strands for the dataset survey.

Recommended defaults adopted in this change cycle (reversible during
planning): the planner sets the committed-sample size cap and the page payload
budget for heavy visuals; link checking is a non-blocking maintenance check;
citation metadata (`CITATION.cff`) names the actual authors and the project
URL, without a DOI until a release policy supports one.

Decided during the change cycle `final-curriculum` (2026-10-12), from
`docs/changes/final-curriculum.md` (revision 3, 2026-10-10):

23. **Two complementary parts and a reference curriculum of 115 slots.**
    Part A, computational and experimental physics: eight subject courses
    with 81 lesson slots (classical mechanics 17, thermodynamics and
    statistical physics 12, waves and optics 9, electromagnetism 9, fluid
    dynamics 10, quantum physics 8, astrophysics with cosmology and
    relativity 10, condensed matter and materials physics 6), of which 16
    are designated measured-data labs. Part B, physics with LLMs and AI
    agents: four method paths with 33 slots. Plus the one existing Lean
    lesson. The slot labels of the change request are curriculum labels,
    not lesson identifiers or feature IDs. The planner reconciles the
    actual inventory against this structure and reports delivered and new
    totals; at this cycle 22 lessons are published, including five Lean
    lessons where the baseline counts one and agent, pipeline, and
    inverse-physics lessons that map to slots. Published lessons beyond the
    baseline are mapped to the structure, never deleted, hidden, or
    rebuilt; 115 stays the reference structure unless a real conflict
    requires a documented human decision. The 11 optional expansion slots
    (nuclear and particle, plasma, geophysics and climate) are outside the
    core curriculum.
24. **Eight physics courses, with stable identifiers.** Decision 15 is
    extended from "later candidates such as waves and optics" to the eight
    courses of decision 23. Every published URL, lesson identifier, strand
    identifier, and internal link keeps working; the course, methods, and
    strand facets of ADR 008 stay; new courses need approved stable
    identifiers and placement rules through a superseding or new ADR that
    the planner proposes, with a transparent transition from ADR 008's
    single-additional-course rule and from F15, which is reconciled through
    planning rather than rewritten or worked around. Legacy lessons map by
    metadata and cross-links only: mechanics M1 to M8 into the mechanics
    course, the published gas lesson as the thermodynamics course's T0 under
    its `agents-abm` address, the LLM projectile experiment as AI0 under its
    `agents-llm` address, and the first Lean lesson as L1 under its `lean`
    address; already delivered agent, pipeline, lab, and Lean content is
    mapped rather than rebuilt.
25. **Part B is a method view, not a set of courses.** The four paths
    (physics reasoning and scientific agents, 9 slots; scientific law
    discovery, 13; physics agent benchmarking, 5; autonomous scientific
    research, 6) are learning paths over lessons that each keep one primary
    physics course, reuse the simulation environments and measured datasets
    of Part A, and keep the legacy `agents-llm` addresses. The paths
    progressively distinguish solving a known problem, running a
    tool-assisted experiment, identifying parameters in a known model,
    discovering an unknown functional form, active experiment selection,
    inference with hidden variables, explanation and falsification, robust
    generalisation, agent benchmarking, and independent report
    verification. Agents stay bounded, independently checked, and optional;
    the agent's hypotheses are separated from the simulator truth, withheld
    answers, and measured evidence; benchmarks have non-agent baselines,
    hold-outs, budgets, frozen replay traces, and no build-time or runtime
    dependence on hosted models; heavy benchmark runs stay outside the
    pull-request critical path. External benchmark projects are
    inspiration for original contained tasks, not embedded assets.
26. **Revision-2 and revision-3 additions.** Seven new slots from
    revision 2 (rotational motion M17, heat engines T9, acoustics W9,
    finite-volume methods FL9, special relativity AST10, physical reasoning
    from video AI8, conservation-law discovery D13) and seven enhancements
    of existing slots without new slots (D6 identifiability, D9
    hypothesis-discriminating information gain, AI6 still-image affordances
    and counterfactuals, EV1 physical-tool understanding, EV2 controlled
    prior-knowledge comparisons, R5 physical multi-objective constraints,
    the linked Q5/Q8 Bell-inequality and eligible-data enhancement).
    Revision 3 adds exactly four Part A slots: T10, a finite-element and
    meshing bridge from the finite-difference heat solver (a shared
    computational method, not a capstone and not a mathematics course), and
    the three applied capstones T11 (thermal engineering of a hypothetical
    AI accelerator), EM9 (adaptive phased-array beam steering), and FL10
    (reconstructing the 2025 Kamchatka tsunami). Each capstone teaches a
    bounded professional workflow from physical requirements to a
    qualified decision, with the deliverables and credibility boundaries of
    the change request's section 4.1, and is displayed as the culminating
    application of its own course. The learning sequences T6 to T10 to
    T11, EM4 and EM6 with W2 to EM9, and FL1 to FL4 to FL9 to FL5 to FL10
    are preserved. Battery thermal runaway, Formula 1 aerodynamics, and
    JWST atmospheric retrieval are deferred inspiration, not features.
27. **Measured-data labs stay sixteen and gated.** Two per course as a
    target; the feasibility gate (decision 18, F50) decides every dataset,
    the shared experimental-methods foundations (F51) are reused, the
    already planned labs (optical diffraction, PIV, microwave S-parameters,
    gravitational-wave strain, agent-assisted measured data) are mapped and
    not cloned, and no dataset approval is claimed that was not granted.
    A capstone's historical-observation comparison is gated the same way
    and is not a designated lab.
28. **No hardware expansion.** No sensor, recording, instrument-control, or
    physical-laboratory lessons; the labs use already-collected licensed
    data (non-goals).
29. **Learning Path redesign as an independent feature.** The course-first,
    accessible, no-JavaScript page of "UX expectations" is one explicit
    follow-on feature with a new ID, delivered before the bulk of the new
    lessons, built on the delivered path, graph, cards, metadata, and visual
    system features rather than reopening them, generated from the
    validated front matter, with verified deterministic thumbnails and a
    planned schema for an optional thumbnail reference only if required.
30. **Verification scales with the curriculum.** The rule under "Runtime and
    deployment constraints": a pull request verifies what it changes and
    what depends on it, `main` always verifies everything (under review by
    decision 35), no check is dropped, the selection lives in
    `./scripts/verify.sh`, and the budget for a typical pull request,
    20 minutes since decision 34, holds at 110 lessons. This changes what
    ADR 002 and ADR 003 decided and needs a new decision record that
    settles what "unchanged" means, where the earlier result comes from,
    what stays
    unconditional, and how the three executions per lesson reduce; it
    follows F58 and precedes the first block of new lessons.
31. **Delivery and quality.** The planner produces a dependency-ordered
    backlog with Issues created just in time, each independently
    demonstrable; no rule that a slot is a feature, shared environments,
    readers, harnesses, and figures are reused, retired IDs (including F24
    and F48) are never reassigned, delivered feature blocks stay history,
    and a scope change to a delivered feature is a new dependent feature.
    Every new lesson meets the definition of done in the change request's
    section 11: substantive physics at its stated level, runnable pinned
    code, interpreted figures with provenance labels, honest limitations,
    front-matter integration, exercises and a tested reproduce path,
    focused tests, independent scientific review, and, for data and agent
    work, the gate and boundary rules of this document. The site stays
    static, English, open, free of accounts, analytics, uploads, and
    runtime LLM backends; creator and JIDAI attribution and legal notices do
    not change with this cycle.

Recommended defaults adopted in this change cycle (reversible during
planning): the planner allocates the next free feature IDs after a live
reconciliation of lessons, features, Issues, and ADRs against `main`;
planned lessons are shown on the path, if at all, through metadata rather
than placeholder lesson pages; capstone and FEM lessons use small meshes and
bounded tests in ordinary CI, with heavier reruns outside pull-request
checks.

Decided during the change cycle `pbc-planning-change-four-workstreams`
(2026-10-15), from `docs/changes/pbc-planning-change-four-workstreams.md`
(human-supplied, 2026-10-14). The four changes are independently
reviewable workstreams of one planning request; existing features are
amended where they exist, and new features are proposed only where
necessary.

32. **Editorial voice and pedagogical storytelling** (change 1). The
    project develops the recognisable editorial voice of "UX expectations"
    in three steps that keep decision 17 and extend it: an editorial style
    guide with concrete before-and-after examples; a pilot on mechanics
    lessons 01 to 05, with targeted editorial changes rather than
    regeneration, reviewed individually and as a connected sequence, with
    the successful changes, the unsuccessful ones, and the adjustments to
    the guide documented, and expanded beyond the pilot only after
    explicit human review and approval; and the integration of the
    approved principles into the authoring guide, the lesson template, and
    reviews through a qualitative editorial rubric, so that future lessons
    inherit the voice through the normal authoring workflow. Technical
    content, lesson contracts, section identifiers, and every existing
    verification requirement are preserved; nothing scientific changes
    silently for style. The objective is better teaching, not optimisation
    against AI-content detectors. The labels F1 to F3 of the proposal are
    local labels, not repository feature identifiers.
33. **Learner instructions without a website build** (change 2). Every
    instruction to rebuild or preview the website locally is removed from
    maintained documentation (the public setup page, lesson footers,
    README, development and contributor documentation, authoring guidance,
    and the templates that generate such instructions) and not relocated.
    Readers read lessons, run and modify Python experiments, and
    optionally check Lean proofs, none of which requires rebuilding the
    website; the setup page is rewritten around running experiments and
    the "Reproduce this" footers become "Run this experiment"
    instructions, as "UX expectations" specifies. The existing contracts
    that tie learner instructions to regenerating a page (ADR 002's and
    ADR 014's reproduce contracts, the setup-page tests, the footer
    generation, the authoring templates, the reproduction tests) are
    identified and explicitly superseded through the ADR process, with
    verification that the new experiment commands reproduce the intended
    numerical results and figures. Internal website generation,
    publishing, Lean verification, scientific tests, provenance, and
    accessibility stay operational; internal tests may still render pages
    and compare website artifacts. Historical decision records and
    completed feature records remain history: superseded decisions are
    marked, obsolete walkthroughs are removed from current guides, and
    past acceptance evidence is not falsified.
34. **The budget of a typical pull request is 20 minutes** (change 3,
    owner decision of 2026-10-14). The wall-clock budget of a typical pull
    request with warm caches is 20 minutes in place of 12, with 15
    minutes retained as a non-blocking optimisation target, as "Runtime
    and deployment constraints" states; the F61 acceptance criterion
    becomes three consecutive one-lesson pull requests within 20 minutes
    with recorded evidence. The basis is the measurement of F61 recorded
    in `docs/release-readiness.md` on 2026-10-14 (three one-lesson pull
    requests at twenty-two lessons in 13 min 50 s to 14 min 43 s, against
    22 min 56 s and 25 min 00 s without a base), which stays exactly as
    measured; the remaining fixed costs (runner preparation in each job,
    the full Lean build, the checks that are not per lesson) stay
    eligible for later optimisation, and a later owner decision may lower
    the budget again; the 20 minutes have no automatic expiry. Only the
    budget number and its current statements change: in these
    requirements, the roadmap, the architecture, and ADR 003 decision 5
    and ADR 014 decision 7 through a status line that references this
    decision and keeps the older wording as history. No check is dropped,
    no guarantee changes, and the cold-cache budget and the job timeout
    are not touched by this decision. The published-lesson inventory is
    reconciled with `main`: F70 delivered T0 to T3 on 2026-10-14 (the
    `agents-abm/01-particles-in-a-box` row now carries `slot: T0` and
    `course: thermodynamics`), and `main` publishes 32 lessons at this
    cycle (the change request's count of 25 predates the merged mechanics
    M9 to M12 and waves W1 to W3 lessons); the planner reconciles against
    `main` rather than replacing numbers.
35. **Simpler scientific verification, CI, and agent build obligations**
    (change 4). F113 (Issue #150, the closed pull request #175, and its
    branch) is paused and is not merged as designed; its work stays
    inspectable until a replacement decision is accepted, and its Issue
    and pull request are closed or superseded through the normal process,
    non-destructively, never restarted or duplicated. The planner plans
    and critically reviews, without implementing or declaring equivalence
    proven, a simpler F61-based architecture in which every published
    version has a complete, traceable verification basis without
    executing every unchanged lesson on every merge, under the conditions
    of "Runtime and deployment constraints": trusted-base retrieval and
    selection extended to pushes on `main` with a chain of incremental
    bases whose per-result provenance, validity, retention, expiry,
    supersession, and failure recovery are defined, inherited scientific
    results distinguished from checks executed on the new commit, the
    execution environment part of the reuse decision, fail-closed
    behaviour, the site rebuilt and its output verified, and exactly the
    verified artifact deployed; a directly invocable exceptional full
    verification without default sharding, with a single job under a
    measured and explicitly approved timeout, sharding only if
    measurements demonstrably justify it, and no scheduled audit unless
    its precise defect, cost, and residual risk are shown and the owner
    approves; and the removal of redundant verification and local build
    obligations after an audit of the verification call graph (the second
    preview render against `check-determinism.sh`, the check identity's
    validity domains, the integration job's critical path, the agents'
    blanket full-site build demands), with coverage evidence before any
    check is removed and no independent scientific check removed. The
    staged evidence of the change request (equivalence of full and
    selective verification on the same commit, fail-closed demonstrations,
    chained-base provenance, one production build, redundancy by coverage,
    the inventory of replaced local build obligations, cost measurements
    at warm caches and a defensible full-run fallback at larger lesson
    counts, explicit updates of decision 30, ADR 003, ADR 014, roadmap F61
    and F113, and the agent-workflow instructions, and a short decision
    record that states the weaker guarantee for owner approval) gates each
    step; all 110- and 125-lesson durations are projections until
    measured. A risky CI redesign is never combined with the editorial
    pilot in one feature.

Recommended defaults adopted in this change cycle (reversible during
planning): the planner names the style guide and the editorial pilot as
amendments of or successors to the existing editorial features rather than
new strands; the budget and documentation work does not wait for the
approval that expands the editorial pilot; the planner chooses the form of
the budget amendment (a short ADR or status-line amendments of ADR 003 and
ADR 014) by the repository convention.

Decided during the change cycle `scientific-atelier-atlas` (2026-10-17),
from `docs/changes/scientific-atelier-atlas.md` (human-supplied,
2026-10-17) and the owner's answers recorded here. The change is a
product and design requirement change; it amends no accepted ADR by
itself, and the planner reconciles the roadmap, the architecture, and the
decision records through the existing change cycle rather than through
one oversized styling feature.

36. **The scientific atelier and the course atlas.** The owner adopts
    visual proposal 1, a scientific atelier with the quality of a
    carefully designed scientific publication and optional interactive
    experiments, as "UX expectations" describes, and the physics-map
    concept as the direction for the atlas. The homepage, the course
    atlas at the existing path address, and the shared templates are
    specified under "UX expectations" (the bullets "Visual direction",
    "Home page", "Course atlas", and "Shared templates"); the rejected
    homepage section "From a question to a working model" is removed and
    not replaced by a renamed teaching formula. The technical baseline
    stays: the Quarto site of ADR 001, `.qmd` lessons, the Python
    generators, native MathML, GitHub Pages, and the scientific
    verification pipeline; the visual system is scoped CSS with shared
    templates and includes, the map is build-generated semantic HTML and
    SVG enhanced by small dependency-free JavaScript modules, and
    canvas, if used at all, serves only an optional animated experiment
    with a static equivalent and accessible controls. The atlas uses the
    real eight-course structure and the four method paths (never the
    six-region mockup), keeps the Lean and method views, is generated
    from the curriculum file and the lesson metadata with the small map
    manifest of "Data and persistence", and keeps every existing route,
    anchor, search, progress, recommendation, setup link, experiment
    command, attribution, and licence working. Delivered F25, F26, F44,
    and F64 are built on, not reopened; the planner allocates new
    feature identifiers and reuses no existing or retired one. The work
    is delivered in bounded slices, starting with one end-to-end preview
    of Home, the atlas, and one existing lesson inspected at desktop, tablet, and
    phone widths (for example 1440, 768, and 375 CSS pixels) before any
    broad rollout, visual acceptance requiring all three; the experiment gallery is
    deferred until enough real browser experiments exist; lesson
    authoring is not blocked on the redesign, with shared template and
    metadata changes coordinated. The homepage opening ships with a
    static figure from an existing verified Python implementation
    (owner's answer, 2026-10-17): the double-pendulum lesson if its
    implementation is sufficiently validated, otherwise another verified
    mechanics figure, styled in the atelier language with its scientific
    content faithful to the model; no temporary JavaScript physics or
    illustrative motion is introduced to meet the design, and the
    validated interactive pendulum is a separate later feature after
    numerical validation and the cross-language consistency checks.
37. **Three visual asset classes; the F44 and F64 restrictions
    superseded** (owner's answer, 2026-10-17). The blanket restrictions
    on decorative imagery and animation (the earlier non-goal, the
    out-of-scope lines of F44 and F64) are reconsidered: their purpose,
    preventing misleading, irrelevant, or unverifiable visual material,
    stands, but they are too broad for the atelier direction and are
    superseded where "Non-goals" and "UX expectations" say. Three asset
    classes are distinguished: interface artwork (visual identity and
    navigation, no scientific evidence claim), allowed on Home, the
    atlas, and course, module, and capstone openings; conceptual
    illustrations (scientifically sound explanatory diagrams, not
    presented as numerical or experimental results), allowed inside
    lessons when they genuinely improve understanding; and scientific
    results (plots, simulations, measurements), which keep reproducible
    generation and the existing scientific verification. Interface
    artwork and conceptual illustrations may be either generated by
    repository code or authored as an SVG source committed in the
    repository with its author and licence recorded (owner's decision,
    2026-10-17, in the review of the change request
    `docs/changes/scientific-atelier-atlas.md`); a raster file stays
    excluded, and a scientific result is never an authored drawing. Stock,
    hand-copied, and externally hosted imagery stay prohibited; the F63
    lesson-preview contract is preserved; animations are permitted when
    pedagogically justified, accessible, and accompanied by a meaningful
    static alternative, and are mandated in no lesson. The objective is
    visual explanation that improves physics education, not decoration.
    The planner updates the relevant requirements, roadmap entries, and
    decision records explicitly: the historical decisions of F44 and F64
    stay as history, and the record states which restrictions are
    superseded.
38. **Governed visual agent skills.** A small, maintained set of agent
    skills helps the planning, implementation, and independent-review
    workflow produce coherent visual design and reliable scientific
    illustrations. A skill is guidance and tooling, not evidence that the
    physics is correct; its use is traceable and its output is reviewed
    against the scientific and accessibility requirements of this
    document. The candidates, their scope, and their selection policy
    are those of the change request's section 7: Impeccable, required
    once approved when a feature changes a major user-facing visual
    surface; Anthropic Frontend Design, required for relevant frontend
    changes once approved, never introducing a framework or bundled
    toolchain; Diagram Design, required once approved when a conceptual
    diagram is produced or substantially changed, with science and
    semantics checked independently; Manim, optional, never required for
    ordinary lessons or the site build; and the project-owned PBC
    Scientific Visualization skill, required for new or substantially
    revised scientific figures, with exceptions justified in the feature
    plan. FreeCAD and OpenSCAD are not included. Installation,
    provenance, and compatibility follow "External integrations" and
    "Security and privacy constraints". The project-owned skill is a
    concise, practical `SKILL.md` with representative good and bad
    examples, covering the choice of visual, axes, units, scales,
    legends, symbols, uncertainty, captions, accessible palettes and
    colour-independent encodings, comparisons of numerical, analytic,
    and experimental results with convergence, conserved quantities,
    error sources, and stability, reproducible Python generation with
    authoritative inputs and deterministic seeds, retained sources and
    provenance, the explicit separation of decorative illustration from
    validated model or measurement with no invented results, and
    accessible static equivalents and reduced-motion controls; it
    supplements, never supersedes, the accepted visual quality gate,
    authoring rules, and scientific contracts. The workflow contract: the
    planner classifies every new visual deliverable (page or layout,
    conceptual diagram, scientific figure, animation, or none), selects
    the applicable approved skills, marks non-applicability explicitly,
    and defines the expected artifact, scientific validation, and
    accessible fallback in the feature plan; the implementer reads and
    applies the selected skills before producing the artifact, links
    output and source in the completion evidence, and explains any
    exception, since listing a skill without observable output is not
    compliance; the independent reviewer assesses the rendered interface
    or generated artifact and its sources under the three-part rendered
    review of "Runtime and deployment constraints", verifies scientific
    claims against independent computations and tests, accessibility,
    and source-of-truth constraints, and checks that the selected skills
    were followed or an exception approved, accepting no self-report;
    verification adds lightweight targeted checks for missing
    references, missing artifact sources, accessible alternatives, and
    metadata consistency, and no brittle pixel or full-render checks on
    ordinary lesson changes; governance introduces the contract through
    `AGENTS.md`, `docs/authoring.md`, the planner, implementer, and
    reviewer instructions, and the feature-plan schema and templates
    only where supported and needed, with no additional mandatory review
    agent and no change to the owner approval hierarchy. Bounded pilots
    precede any wider adoption: the Home, atlas, and one-lesson preview
    with Impeccable and Frontend Design guidance; one existing mechanics
    concept with Diagram Design against a simpler verified SVG; one
    existing mechanics or numerical-integration plot with the
    project-owned skill, preserving verified values and commands; each
    with before-and-after artifacts, qualitative rubric findings, build
    and runtime cost, known limitations, and the owner's decision, and
    none imposed retroactively on existing lessons, blocking independent
    lesson features, or expanding to lesson templates before the owner
    approves and the editorial work of decision 32 is coordinated. The
    Manim feasibility pilot is not scheduled (owner's answer,
    2026-10-17): it starts only when the owner names one concrete
    explanation where a static figure is inadequate, and its
    dependencies stay outside the pinned learner and CI environments.
    The acceptance criteria of the change request's section 7 (documented
    provenance of every used third-party skill, at least one feature plan
    with deliberate skill selection, evidence that names what was changed
    and what artifact was evaluated, scientific correctness of pilot
    figures with the skill unable to override tests, a Home and atlas
    pilot that is Quarto, semantic HTML, and SVG with the published and
    planned safeguards, no unapproved dependency, and reviewable slices
    with a fallback when a candidate fails review) apply.

Recommended defaults adopted in this change cycle (reversible during
planning): the planner allocates the feature identifiers of the delivery
slices after refreshing the change request's dated state against `main`
(F117's pull request #205 has since merged; the request's reviewed
baseline predates it); the display label of the atlas and the exact
navigation wording are settled in the first preview under the owner's
visual review, with the address unchanged; the planner chooses the
project-local skill location after checking what each configured runner
(Claude Code for the implementing roles, Codex for the reviewing roles)
discovers from a worktree, so that every role reads the same pinned
files; the skill audit of slice A2 decides each candidate individually,
and a candidate that fails licensing, security, or quality review gets a
project-owned adapter or is dropped, without blocking the other slices;
the three-part rendered review records its screenshots as evidence
artifacts of the feature, not as committed site assets.

Decided during the change cycle `risk-proportionate-workflow` (2026-10-19),
from `docs/changes/risk-proportionate-workflow.md` (human-supplied,
2026-10-18, version 2 of the workflow proposal with the owner's four
refinements R1 to R4) and the owner's answers recorded here. The change is
a workflow requirement change: one planning change delivered as two bounded
features; nothing of it is implemented before the planning and its decision
record are approved; features already in progress finish under the
contracts they started with; and two changes to the workflow scripts are
never in flight together.

39. **Risk-proportionate verification and review.** The objective is a
    shorter feature lead time and less rework without weakening
    scientific correctness, reproducibility, security, or independent
    review. The measured baseline is the table of the change request's
    section 1, and the exact verification matrix of that section (per
    lesson in a full run, three pages, one experiment through the
    learner path, and one experiment in the unit tests; about 68 minutes
    sequentially at 38 lessons) is recorded in the architecture as the
    standing reference. One new decision record, ADR 020, is the only
    authoritative place for the rules; the process statements of ADR
    002, 003, 005, 012, 014, 015, and 017 are amended through status
    lines, never their invariants; `AGENTS.md` and
    `.agents/policies/autonomy.md` refer to ADR 020 and define the
    levels and the evidence states.
    - *Three risk levels.* The level of a change is the highest of the
      minimum its paths imply (Level 1: documentation and process files
      outside the ADRs and the planning documents, such as plans,
      handoffs, and summaries; Level 2: lessons, `src/`, tests, and
      unprotected scripts; Level 3: the protected paths of
      `guardrails.conf`: ADRs, planning documents, workflows, gate
      scripts, prompts, `agents.conf`, `verify.conf` and `verify.sh`,
      digest, selection, `fetch-base.sh`, provenance, build and deploy,
      skills), any escalation trigger its nature hits wherever the files
      are (a changed scientific claim; weakened test strength; security;
      verification guarantees; dependency selection, as the change
      request's section 3.1 lists them), and the level an agent or the
      reviewer assesses. The scripts detect the mechanically detectable
      triggers on the diff; the agent names the rest in the completion
      record, and the independent reviewer assesses them with the impact
      classification it already fills, with no new agent and no new
      report. A level is raised at any time and never lowered without
      the owner's authorization, verified only at the merge gate.
    - *Evidence lifecycle.* The completion record stays the single
      record with its three statuses and their present meaning. Each
      criterion names the gate that clears it (`implementation`,
      `pr_ci`, `owner_approval`, or `post_merge`) and is `met`,
      `not_met`, or `pending`; `pending` names one of the last three
      gates and is never allowed for `implementation`. `complete` keeps
      one meaning: every acceptance criterion met; a record with a
      pending criterion is `partial`. Three readiness points are derived
      from the record, never stored: ready for a pull request (every
      implementation criterion met), ready for merge (additionally CI
      green on the exact published head, a current review chain, no
      open major finding, and for Level 3 the verified owner approval),
      and done (every criterion met, the Issue may close). A record
      whose only unmet criteria are pending for later gates is committed
      and published without `--partial`, `--no-review`, or any owner
      exception; its pull request does not close the Issue; pending CI
      blocks the merge, not the publication; outstanding post-merge
      evidence keeps the Issue open and never blocks the merge; an open
      major finding is never a pending criterion, and criteria whose
      evidence belongs to a later gate are not review findings.
    - *Review.* Level 1 needs no review. Level 2 allows an initial full
      review followed by a traceable chain of delta reviews: each review
      records the tree it compared against and the tree it reviewed; the
      chain begins with a full review and ends at exactly the current
      tree, and a gap or a break means a full review; every finding has
      a stable identifier; every later review gives the disposition of
      every earlier open finding (resolved with evidence, still open, or
      accepted); finish requires no open finding. A delta review is
      allowed only when the delta is confined to kinds of change whose
      reach is certain (tests, documentation, lesson content, and one
      source module whose importers are all among the files the
      baseline review covered, found by a plain textual search with the
      import knowledge of the digest); a Level 3 path, an escalation
      trigger, a shared input, a changed exported interface, a file with
      an unresolved finding, or an undecidable search requires a full
      review; there is no changed-lines threshold and no general-purpose
      impact graph. Level 3 keeps a full review in every round. Minor
      and suggestion findings at Levels 1 and 2 are triaged mechanically
      (an accept or a deferral with a reason, published once, with a
      follow-up Issue for every deferral); Level 3 keeps a full triage
      per finding. The completion record and the handoff note are part
      of the review fingerprint.
    - *Owner approval* (owner's answer, 2026-10-19): mechanism A of the
      change request. The approval of a Level 3 change and the
      authorization to lower a level are pre-merge requirements, given
      as an approving review of the pull request by a second GitHub
      identity held only by the owner, naming the head commit it applies
      to and, for a lowering, the level; GitHub enforces it at the merge
      through the ruleset of `main` and `CODEOWNERS`, as "Authentication
      and authorization" states, and the workflow scripts (finish,
      review, triage, publish) only record what is required and the head
      it applies to, without repeated network requests. No script
      accepts an agent-written assertion, a comment or review by the
      agent's own login, a flag, or a statement in chat as the owner's
      approval, and the merge-gate verification is tested with a forged
      assertion that it refuses. Until the identity, the code-owner rule,
      and the ruleset change exist, the present practice continues: an
      agent merges a Level 3 change only after the owner's explicit word
      in the conversation and states the head commit it applies to.
    - *Verification.* Intermediate rounds of a Level 3 change may use
      targeted partial verification (`verify.sh --only <group>` for the
      groups the changed paths touch, plus the unit tests of the changed
      modules) as quick feedback that is never evidence; the final
      acceptance is always a complete verification of the final tree,
      then a complete independent review of that tree made after the
      verification (a review made with `--unverified` never counts as
      the final review), then the full CI, which stays the publication
      gate. The targeted tier stays refused when the check identity
      differs. An exceeded time budget is a measurement for the owner at
      the re-assessment points already chosen (re-measure at 42 lessons,
      decide the capacity at 44 at the latest, or earlier if a complete
      `main` run exceeds 45 minutes); it starts no mandatory optimisation
      and never changes scientific content; hard checks such as the
      30-second lesson page budget keep failing, with the documented
      exception table. A small time log appended by `verify.sh`
      (timestamp, tier, tree, duration, result) serves the evaluation and
      is read by no gate; the base is not re-fetched when the latest
      accepted `main` run is the one recorded.
    - *ADR 017 and F113 stay paused.* Neither is justified by lead-time
      evidence: ADR 017 decisions 1 to 6 and 9 are not accepted, its
      status records the pause and the triggers, F113 and Issue #150
      stay paused and open, F121 is not started, and F120 is finished
      (its evidence was published by pull request #224 and Issue #196
      closed on 2026-10-19, after the change request was written). They
      are reopened only at the owner's triggers above.
    - *Unchanged.* The complete CI run on every pull request and push;
      the aggregate required check `verify` and the deployment of only
      the verified artifact; the digest, selection, base provenance (with
      the stamped ref of F61 M3) and check identity, with the safe
      fall-back to executing everything; independent review by a
      different model for Levels 2 and 3; and no scientific check removed
      without coverage evidence (ADR 017 decision 8). Any change to these
      is Level 3. No new mandatory agent and no new mandatory reporting
      gate.
    - *Delivery and evaluation.* Two roadmap features with the next free
      identifiers, F130 and F131 at this cycle: F130 delivers the
      evidence lifecycle, the risk level, the merge-gate verification,
      the intermediate Level 3 verification, the budget policy where the
      checks read their budgets, the time log, and the base re-fetch
      rule; F131 delivers the review chain, the fingerprint of the
      completion record and the handoff, and the mechanical triage. Each
      is Level 3 with the owner's approval of its diff, strictly one
      after the other; F131 starts only after F130 is merged and two
      features have run under it with their effect observed (owner's
      answer, 2026-10-19). The new rules apply to features started after
      F130 is merged, for its part, and after F131 is merged, for the
      rest. The evaluation is a pilot of five features after F131 (two
      after F130 for its own effect), with six measurements derived
      afterwards from existing artifacts and no new report, agent, or
      gate: lead time, repeated verification from the time log, review
      rounds, owner waiting time, defects missed by the reduced process
      under the Issue label `process-miss`, and the baseline; a miss in
      an escalation-trigger category stops the pilot and restores full
      strictness at that level until the owner decides. The acceptance
      criteria of the change request's section 7 apply to the planning
      change and to each deliverable.

Recommended defaults adopted in this change cycle (reversible during
planning): the planner verifies on the real ruleset of `main`, with a test
pull request, that a required code-owner review with zero required
approving reviews leaves Level 1 and 2 pull requests without a GitHub
review requirement, and records the owner actions mechanism A needs; the
lists and thresholds of the change request's section 3 are the owner's
decisions, not planning questions; the status claims of the change request
are refreshed against `main` (the roadmap's last identifier is F129; Issue
#196 closed on 2026-10-19; the ruleset of `main` requires a pull request
and the check `verify` with zero approving reviews and no code-owner
review; `CODEOWNERS` names only the owner's own login).

## Unresolved questions

Questions 1 to 4 and 6 are settled. They keep their numbers, because other
documents refer to them; questions 5, 7, 8, 9 to 12, and 13 to 15 are open.

1. **Default LLM provider for agent lessons.** Settled in F09: OpenAI is the
   default live provider, as an optional dependency behind the thin provider
   interface, which stays the swap point (ADR 004).
2. **LLM credentials in CI for the content workflow.** Settled in the
   planning of F12: content drafting runs on the maintainer's machine, and CI
   holds no LLM key (ADR 006).
3. **Custom domain.** Settled in F10: none for the first release, which uses
   the GitHub Pages default URL. A custom domain is revisited only as its own
   decision (`docs/release-readiness.md`).
4. **Agent-based-modelling lesson in the MVP or immediately after.** Settled:
   delivered as F11 and included in the first release.
5. **JIDAI B.V. as a named copyright holder.** Out of this change: decision
   20 keeps the copyright line as it is. Revisit only with a legal review of
   company formation, contributor rights, and consent, recorded as its own
   decision.
6. **Second course topic.** Settled by the change cycle `final-curriculum`
   (decisions 23 and 24): the eight courses and their reference lesson
   slots are named by the human; the planner reconciles F15 and ADR 008
   with them through a superseding ADR, and the human still approves each
   course's concrete lesson list in its Issues before drafting.
7. **Release citation and DOI.** Whether releases get a Zenodo DOI depends
   on a release policy that does not exist yet; `CITATION.cff` carries no DOI
   until then.
8. **Lean build under selective verification.** The change request's
   verification rule names the lessons, their inputs, and the Lean toolchain
   and manifest as inputs, but not the Lean build itself. Until the decision
   record of decision 30 says otherwise, every pull request keeps building
   all Lean sources, as ADR 003 decided; whether the Lean build may follow
   the same selection is for the human to decide with that record. The
   decision record of decision 35 is the next such record.
9. **Incremental `main`.** Whether the owner accepts the weaker guarantee
   of inherited scientific results in place of executing every lesson on
   the current commit, and with which minimum mitigations, is decided on
   the decision record that decision 35 requires, after the staged
   evidence exists. Until then every push to `main` executes and checks
   every lesson. The staged evidence of F120 exists (pull request #224,
   2026-10-19), the record was amended without being accepted, and by
   decision 39 it stays paused until the owner's triggers (42 lessons
   measured, 44 decided, or a complete `main` run above 45 minutes).
10. **Timeout of an exceptional full run.** The per-job timeout and the
    budget of a complete verification at representative larger lesson
    counts are set from measurements under decision 35, not from the
    45-minute timeout alone and not from projections; the owner approves
    the value.
11. **Scheduled full audits.** Not authorised. If the planner recommends
    one, it names the precise defect it detects, why event-driven checks
    cannot detect it, its cost, and the residual risk, and the owner
    decides.
12. **Closing F113.** Pull request #175 is closed and Issue #150 is open
    with its branch preserved; the planner proposes how the Issue is
    closed or superseded, non-destructively, once the replacement decision
    of question 9 is taken.
13. **Which third-party skills pass the audit.** Decision 38 names the
    candidates and their policy; whether Impeccable, Anthropic Frontend
    Design, and Diagram Design are vendored, adapted, or dropped is
    decided per candidate on the audit of slice A2 (upstream source,
    pinned revision, licence, dependencies, security, compatibility with
    the configured runners), and the owner approves each outcome before
    the skill becomes required for a feature.
14. **The validated interactive pendulum.** Whether the homepage opening
    gains interactive controls and animation is decided as its own
    feature after the numerical validation and the cross-language
    reference check of decision 36 exist; until then the opening stays a
    static verified figure.
15. **A Manim pilot.** Not scheduled. It starts only when the owner names
    one concrete explanation where a static figure is inadequate
    (decision 38), with its rendering time, dependency burden, asset
    size, static fallback, and instructional value measured and the
    rendering kept out of normal CI unless specifically justified.
