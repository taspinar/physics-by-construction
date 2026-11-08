# ADR 019: Agent skills are audited, pinned, project-local guidance of the development workflow, never a build dependency and never evidence

## Status

**Current rules: see [`docs/process.md`](../process.md) (Issue #404,
2026-11-07); this ADR is the history of the decision.** The text below is
kept as it was written. The process part of this record, decisions 1, 3,
and 5 (what a skill is, where it lives and the `skills-config` check, and
the planner's, implementer's, and reviewer's duties), is summarised there;
decisions 2, 4, and 6 (the set, the provenance, the pilots) are the content
of the atelier and stand here. No decision is superseded.

Proposed with the planning of the change cycle `scientific-atelier-atlas`;
accepted when that planning is approved. Extends
[ADR 006](006-content-drafting-runs-on-the-maintainers-machine.md)
(agent-assisted work runs on the maintainer's machine; CI holds no LLM
credential) and the boundary of
[ADR 010](010-coding-agent-exercises-on-the-learners-machine.md) that the
site and CI verify what was produced and never run an agent; changes no
accepted decision. Delivered by F122; applied by F123 to F129.

Date: 2026-10-17

## Context

The change cycle `scientific-atelier-atlas` (requirements decision 38)
introduces a small, maintained set of agent skills so that the planning,
implementation, and independent-review workflow produces coherent visual
design and reliable scientific illustrations, instead of relying on ad hoc
prompting for every visual feature. Candidates were named by the owner:
Impeccable (typography, layout, hierarchy, interface refinement),
Anthropic Frontend Design (shared interface elements, responsive
presentation, interactive components within Quarto), Diagram Design
(conceptual physics illustrations), Manim (optional animations), and a
project-owned PBC Scientific Visualization skill. FreeCAD and OpenSCAD are
not included.

A skill is a set of instructions and sometimes scripts that an agent reads
and follows. Read without an audit, it is third-party text that steers an
agent with write access to the repository: a supply-chain input of the
development workflow. Installed globally on the owner's laptop, it is
invisible to the review and absent from a feature worktree on another
machine; fetched at run time, it is mutable; silently omitted, it leaves no
trace. The workflow runs two providers from `.agents/agents.conf` (Claude
Code for the writing roles, Codex for the reviewing roles), each with its
own skill locations, and the reviewing roles run read-only without the
user's configuration (`docs/development.md`, "Configuring agents").

The owner's direction is explicit: a skill is guidance and tooling, not
evidence that the resulting physics is correct; its use must be traceable
and its output reviewed against the scientific and accessibility
requirements; no additional mandatory review agent and no change to the
owner approval hierarchy.

## Decision

1. **What a skill is.** Guidance and tooling for the roles of the
   development workflow (planner, implementer, reviewer, triage). Never a
   dependency of the site, the build, the lesson and built-site checks,
   the deployment, or any CI job: none of them invokes, installs, fetches,
   or depends on a skill, the boundary of ADR 006 and ADR 010. The one
   reader of `.agents/skills/` outside the agents themselves is the skills
   configuration check of decision 3, a structural check that validates
   the directory and the plans that name it: an ungrouped entry of
   `scripts/verify.conf`, in the group `default` beside the other
   structural checks (template structure, shell syntax, the documentation
   checks), run by the `workflow` job in CI and by the targeted run
   locally like every other check of that group.
   Never evidence that a figure, a page, or a physics claim is correct;
   never a substitute for the accepted visual quality gate (F44), the
   authoring rules, the scientific contracts, or independent review. Its use is traceable: the
   feature plan names the skills selected, the completion evidence links
   the skill to the artifact it shaped, the review checks that the
   guidance was followed or an exception approved.
2. **The set and the selection policy.** The candidates of decision 38
   with the policy of the change request's section 7: Impeccable, required
   once approved when a feature changes a major user-facing visual surface;
   Anthropic Frontend Design, required for relevant frontend changes once
   approved, never introducing a framework or bundled toolchain; Diagram
   Design, required once approved when a conceptual diagram is produced or
   substantially changed, with science and semantics checked independently;
   the project-owned PBC Scientific Visualization skill, required for new
   or substantially revised scientific figures, with exceptions justified
   in the feature plan; Manim, optional, never required for an ordinary
   lesson or the site build, and not scheduled (requirements, unresolved
   question 15). Each third-party candidate is decided individually by the
   audit of F122 (unresolved question 13): vendored at a pinned revision,
   replaced by a thin project-owned adapter that references approved source
   material, or dropped; the owner approves each outcome before the skill
   becomes required for a feature. A candidate that fails licensing,
   security, or quality review blocks no other slice.
3. **Location and discovery.** Approved skills live in the repository at
   `.agents/skills/<name>/SKILL.md`, with their supporting files beside
   them: the project's own path (the template-owned paths of
   `.agents/template.conf` do not include it), versioned with the code,
   present in every feature worktree, and the directory the planner
   expects both configured runners to discover: the documented behaviour
   of Claude Code 2.1 and Codex 0.160 is to read `.agents/skills` of the
   working directory besides their own `.claude/skills` and
   `.codex/skills`, observed on the owner's machine with the user's
   configuration but not yet shown per role, profile, and worktree. F122
   criterion 2 confirms or refutes it: from a feature worktree, for each
   role's permission profile (write, unattended, read-only) and provider,
   a recorded demonstration of what the runner discovers. The decision
   does not rest on the outcome. Whatever a profile discovers, the role's
   instructions name the skill files to read, which the Read tool of
   every profile allows, so a role whose profile does not load the
   directory (the read-only profiles run without the user's
   configuration) reads the same pinned files by path, and the location
   stays `.agents/skills/` either way. A skill is never a globally
   installed skill on the owner's machine, never fetched as mutable
   instructions at run time, and never installed by a third-party
   installer in CI. A missing required skill fails a feature's
   configuration visibly or is replaced by an explicitly approved
   alternative, never omitted silently: the skills configuration check,
   delivered by F122 as an ungrouped entry of `scripts/verify.conf` (the
   group `default`, which the `workflow` job runs in CI and the targeted
   run `./scripts/verify.sh --targeted` runs locally; no new group and no
   change to the CI workflow, so ADR 012 decision 2 holds unchanged),
   verifies that every directory under
   `.agents/skills/` has a `SKILL.md` and a provenance record with a
   matching digest and that every skill a committed feature plan names
   exists at its recorded revision. It is the only check that reads the
   directory, and it reads the skills as data to validate, never as
   instructions to follow.
4. **Provenance.** Every third-party skill in use has, in its directory, a
   record of its upstream source, the pinned revision, the licence and the
   redistribution decision, the dependency and security assessment (what
   scripts it carries, what they would execute, what was removed or
   adapted), the review date, and the update and re-review policy; an
   adapter records the approved source material it references instead of
   vendoring. The skill name and revision are recorded in the completion
   evidence of every feature that uses it. The project-owned skill is a
   concise, practical `SKILL.md` with representative good and bad examples
   and the references of the authoring, accessibility, and
   scientific-verification rules, covering the choice of visual, axes,
   units, scales, legends, symbols, uncertainty, captions, accessible
   palettes and colour-independent encodings, comparisons of numerical,
   analytic, and experimental results with convergence, conserved
   quantities, error sources, and stability, reproducible Python
   generation with authoritative inputs and deterministic seeds, retained
   sources and provenance, the explicit separation of decorative
   illustration from validated model or measurement with no invented
   results, and accessible static equivalents with reduced-motion
   controls. Its suggestions, like every skill's, are adapted to the
   Quarto, `.qmd`, CSS, SVG, native MathML, Python, and GitHub Pages
   stack.
5. **The workflow contract.** The planner classifies every new visual
   deliverable of a feature (page or layout, conceptual diagram,
   scientific figure, animation, or none), selects the applicable approved
   skills, marks non-applicability explicitly without requiring every
   skill on every feature, and defines the expected artifact, the
   scientific validation method, and the accessible fallback in the
   feature plan. The implementer reads and applies the selected skills
   before producing the artifact, links the output and its source in the
   completion evidence, and explains any intentional exception; listing a
   skill without observable output is not compliance. The independent
   reviewer assesses the rendered desktop and phone interface or the
   generated scientific artifact and its sources under the three-part
   rendered review of ADR 018 decision 6, verifies scientific claims
   against independent computations and tests, accessibility, and the
   source-of-truth constraints, and checks that the selected skills were
   followed or an exception approved, accepting no self-report.
   Verification adds lightweight targeted checks (missing references,
   missing artifact sources, accessible alternatives, metadata
   consistency) and no brittle pixel or full-render check on an ordinary
   lesson change; aesthetic merit and scientific interpretation stay
   visual and human review. Governance introduces this contract through
   `AGENTS.md`, `docs/authoring.md`, the skills' own README, and the role
   instructions and plan conventions only where supported and needed; a
   change to a template-owned file (`.agents/prompts`, `AGENTS.md`) is
   recorded so that a template sync keeps it. No additional mandatory
   review agent; the owner approval hierarchy is unchanged.
6. **Bounded pilots before wider adoption.** The home, atlas, and
   one-lesson preview with the approved design skills (F123 to F126); one
   existing mechanics concept with Diagram Design against a simpler
   verified SVG, and one existing mechanics or numerical-integration plot
   with the project-owned skill, preserving verified values and commands
   (F129); each with before-and-after artifacts, qualitative rubric
   findings, build and runtime cost, known limitations, and the owner's
   decision. Nothing is imposed retroactively on existing lessons, blocks
   an independent lesson feature, or expands to the lesson templates
   before the owner approves and the editorial work of decision 32 (F114
   to F116) is coordinated. A Manim pilot starts only when the owner names
   one concrete explanation where a static figure is inadequate; its
   dependencies stay outside the pinned learner and CI environments and
   its rendering out of normal CI unless specifically justified.

## Alternatives considered

- **Globally installed skills on the owner's machine, or the runner's
  automatic discovery of whatever is installed.** Rejected: invisible to
  review, absent from worktrees elsewhere, unpinned, and untraceable.
- **Fetching the upstream skill at run time, or a plugin manager or
  marketplace install.** Rejected: mutable instructions reaching an agent
  with write access, nothing pinned, nothing reviewable in the pull
  request.
- **Vendoring every candidate as found.** Rejected: the audit of
  licence, scripts, and security assumptions is the condition of use, and
  a candidate may be adapted or dropped.
- **No skills, ad hoc prompting as today.** Rejected by decision 38: the
  visual work of the atelier needs consistent guidance that outlives one
  session.
- **An additional mandatory review agent for visual work.** Rejected by
  the owner: the existing independent review checks the rendered artifact
  and its sources; the contract gives it what to check.
- **Making a skill's checklist a verification check.** Rejected: aesthetic
  merit and scientific interpretation are human review; checks stay
  lightweight and targeted (references, sources, alternatives, metadata).
- **CAD skills (FreeCAD, OpenSCAD).** Rejected: no established dependency
  of the atlas or the lesson programme; reconsidered only for a specific
  educational use case.

## Consequences

- The skills directory is a supply-chain input of the workflow with the
  same discipline as a locked dependency: an upstream change reaches the
  repository only through a re-audited pull request.
- Each role that uses a skill spends context on it; the planner's
  selection keeps that to the skills a feature needs.
- The first feature plan of the atelier demonstrates the selection,
  including an explicit reason where an optional skill does not apply; the
  completion evidence and the review of every visual feature name what was
  changed and what rendered or generated artifact was evaluated.
- The skills configuration check and the provenance records are
  maintained with the skills; a skill whose upstream disappears keeps
  working from its pinned copy. The build and every other check pass with
  `.agents/skills/` absent, which F122 shows on a scratch copy.
- Where a template-owned file carries the contract, the project records
  the deviation for `scripts/sync-template.sh`, or carries the contract in
  its own files instead.
- The review of a visual feature assesses rendered screenshots and the
  built HTML, which takes more of the reviewer's time than a diff; the
  roadmap keeps the visual features bounded for that reason.
