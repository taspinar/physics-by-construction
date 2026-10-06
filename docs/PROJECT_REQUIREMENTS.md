# Project Requirements

Status: Approved
Approved at: 2026-10-06T09:02:01Z

Project Grill owns the Draft content. `scripts/start-planning.sh` records human
approval before project architecture and roadmap planning begins.

Source: `docs/PROJECT_DESCRIPTION.md` (human-supplied, authoritative) plus the
decisions recorded in "Major product decisions" below.

## Project goal

Build **Physics by Construction**, an English-language educational website that
teaches physics by constructing it: every concept is accompanied by runnable
code, and the learning path progresses from numerical simulation, through
experiments driven by AI agents, to formal proofs in Lean.

Why it matters: existing physics material is either prose-and-equations or
code-only. This site makes the assumptions, models, and claims of each lesson
explicit and machine-checkable, so a reader can reproduce every result,
interrogate it with agents, and, at the top of the path, see it proved.

Success for the project means a published static site with a complete,
CI-verified first mechanics course that already exercises all three pillars
(code, agents, Lean), and a repeatable workflow for growing the content.

## Target users

Primary user: **advanced self-directed learners** who already have both
undergraduate-level physics (classical mechanics, calculus, linear algebra) and
solid programming skills. Lessons do not re-teach either; they teach the
combination: modelling, numerical methods, agentic experimentation, and formal
verification applied to physics.

Secondary roles:

- **Maintainer/author** (the project owner, assisted by AI agents): writes and
  reviews lessons, operates CI, merges content.
- **Outside contributor**: proposes, assesses, or drafts content through
  GitHub Issues and reviewed pull requests (later phase, see MVP scope).

There are no administrator or signed-in learner roles.

## Primary use cases and journeys

1. **Follow the learning path.** A learner opens the site, sees the ordered
   path (mechanics with simulations, then agent-driven experiments, then Lean
   proofs), picks the next lesson, reads it, runs or inspects the code, works
   the exercises or plays with the interactive visualization, and moves on.
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

## Non-goals

- No user accounts, sign-in, or server-side learner data, now or in the
  adaptive-learning phase.
- No backend or runtime server: the site is static. LLM agents run on the
  learner's machine with the learner's credentials; the site never calls an
  LLM at runtime and never holds API keys.
- No analytics, tracking, cookies, or third-party telemetry.
- No re-teaching of prerequisite physics or programming; the audience is
  advanced, and lessons may state prerequisites and link out instead.
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
  equations, and static figures. JavaScript is required only for optional
  interactive visualizations, which must degrade gracefully (static figure or
  explanatory text when scripts are unavailable).
- Responsive layout usable on phone, tablet, and desktop.
- Accessibility target: WCAG 2.1 AA for site chrome and lesson content;
  equations are rendered with accessible markup; figures have alt text.
- A visible learning path with ordering, difficulty, and prerequisites per
  lesson, so learners always know where they are and what comes next.
- Consistent lesson structure: explanation, assumptions, worked examples, code,
  exercises/visualizations, and a "reproduce this" section pointing at the
  exact files and commands.
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
  Learners supply their own API key locally for agent lessons. Whether the
  later content-drafting workflow may hold an LLM API key as a GitHub secret
  is recorded under Unresolved questions.

## External integrations

- **GitHub**: repository, Issues, pull requests, Actions (CI and deployment),
  Pages (hosting). Required.
- **Lean 4 toolchain and Mathlib**: fetched in CI for proof checking. Required.
- **Python ecosystem** (scientific stack, exact packages chosen in planning):
  fetched in CI and by learners locally. Required.
- **LLM provider API** (for agent lessons): used only on learners' machines
  with their own keys. Lesson code should isolate the provider behind a thin
  interface so switching providers is cheap; the default provider is an
  unresolved question below. Not a site dependency.
- **Lean web editor** (live.lean-lang.org or equivalent): optional outbound
  links for exploring proofs. No integration beyond links.
- External notebook services (Colab/Binder): optional outbound links only.
- No analytics, comment, search-as-a-service, or auth providers.

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
- Domain: GitHub Pages default URL unless a custom domain is chosen later
  (unresolved question).
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
- CI workflows use least-privilege `permissions`; deployment uses the
  GitHub-provided OIDC/Pages token. Pull requests from forks must not receive
  write permissions or secrets.
- Supply chain: dependency lock files, Dependabot alerts enabled, pinned
  GitHub Actions versions.
- Licensing compliance: code MIT, content CC BY 4.0, with attribution for any
  third-party material included in lessons; contributor submissions accepted
  under the same licenses.
- Content integrity: a claim on the site is backed by code or proof that CI
  verified; lessons must mark anything not verified as such.

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

## Unresolved questions

1. **Default LLM provider for agent lessons.** Lessons will isolate the
   provider behind a thin interface, but worked examples need one concrete
   default (Anthropic, OpenAI, or a local open-weights model). Recommendation:
   pick one hosted provider as the default and show the swap point; decide
   when the first agent lesson is planned.
2. **LLM credentials in CI for the later content workflow.** Agent-assisted
   drafting of new content could run in GitHub Actions with an API key stored
   as a repository secret, or only on the maintainer's machine. Recommendation:
   maintainer's machine for the first iteration; revisit when the content
   workflow phase is planned. Until then CI holds no LLM keys.
3. **Custom domain.** GitHub Pages default URL versus a custom domain with
   HTTPS. No effect on the MVP build; decide before public launch.
4. **Agent-based-modelling lesson in the MVP or immediately after.** Decision
   8 requires an LLM-agent lesson in the MVP; the agent-based-modelling lesson
   is required in the MVP only if it fits the first release's size, otherwise
   it is the first follow-up. The planner decides based on lesson budget.
