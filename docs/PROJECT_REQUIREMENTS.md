# Project Requirements

Status: Approved
Approved at: 2026-10-09T07:28:06Z

Project Grill owns the Draft content. `scripts/start-planning.sh` records human
approval before project architecture and roadmap planning begins.

Source: `docs/PROJECT_DESCRIPTION.md` (human-supplied, authoritative), the
change request `docs/changes/physics-next-phase.md` (human-supplied,
2026-10-09), plus the decisions recorded in "Major product decisions" below.

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
   path: physics courses organised by subject (mechanics first, later courses
   such as waves and optics), with AI-assisted research and formal
   verification exposed as cross-cutting methods through tags, related
   lessons, and cross-links rather than as physics subjects. The learner picks
   the next lesson, reads it, runs or inspects the code, works the exercises
   or plays with the interactive visualization, and moves on. The existing
   strand identifiers (`mechanics`, `agents-llm`, `agents-abm`, `lean`) and
   published URLs stay until an approved migration plan exists.
2. **Reproduce a lesson locally.** A learner clones the repository, installs
   the pinned toolchain, and re-runs any lesson's code (and Lean proof) with
   identical results to those shown on the site.
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
- Further courses beyond mechanics along the same three-pillar path.
- Clarity and usability of the published site: honest homepage narrative,
  a generated prerequisite graph, learning-path cards with a difficulty
  scale, a reusable lesson template, course navigation from one source of
  truth, a unified tested local-setup guide, a glossary, self-hosted search.
- The research-backed editorial standard below, applied first as a pilot on
  the numerical-integrators lesson and one introductory mechanics lesson,
  then as lesson-by-lesson editorial and figure passes.
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
- Consistent lesson structure: explanation, assumptions, worked examples, code,
  exercises/visualizations, and a "reproduce this" section pointing at the
  exact files and commands.
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

## Authentication and authorization

- Learners: none. The site is anonymous and public.
- Maintainers and contributors: GitHub repository permissions. `main` is
  protected; changes land via pull requests with passing CI. Outside
  contributions arrive as Issues and pull requests under the repository's
  CODEOWNERS and review rules.
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
- **Curated external references**: outbound links only. Link validity is a
  separate, resilient maintenance check run periodically or on demand, never
  a build or merge requirement; builds and reading never depend on an
  external site.
- **JIDAI website** (`jidai.nl`): outbound attribution link only. The JIDAI
  portfolio or case-study page is a separate company-site task outside this
  repository.
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
- CI cost and time: Mathlib builds are heavy; the pipeline must use the
  Mathlib cache (or equivalent) and dependency caching so a typical pull
  request verifies in minutes, not hours. The planner must set a concrete
  budget.
- Reproducibility: pinned Python, Lean, and Mathlib versions; a single
  documented command reproduces the whole site and all lesson outputs locally
  on macOS and Linux.
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
  GitHub Actions versions.
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

## Unresolved questions

Questions 1 to 4 are settled. They keep their numbers, because other
documents refer to them; questions 5 to 7 are open.

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
6. **Second course topic.** The change request names waves and optics as a
   possible second course and a bridge from the wave-flume and optics
   candidates; F15 still requires the human's explicit choice of topic and
   lesson list before drafting.
7. **Release citation and DOI.** Whether releases get a Zenodo DOI depends
   on a release policy that does not exist yet; `CITATION.cff` carries no DOI
   until then.
