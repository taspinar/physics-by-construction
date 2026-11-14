# Agent skills of the development workflow

The audited, pinned skills that the planner, implementer, reviewer, and
triage roles may use for visual work (ADR 019) and, with the teaching
skill, for a lesson's teaching (ADR 023 decisions 1 and 2). A skill is guidance for an
agent: never a dependency of the site, the build, a check, the deployment,
or a CI job, and never evidence that a figure, a page, or a physics claim is
correct. Only the skills configuration check (`skills-config` in
`scripts/verify.conf`, `python -m pbc.skills`) reads this directory, as data
to validate.

## The set

| Skill | Kind | Pinned at | Use (ADR 019 decision 2) |
|---|---|---|---|
| [frontend-design](frontend-design/SKILL.md) | vendored as is | `anthropics/skills@dbd4588f` | Required for a relevant frontend change (shared interface elements, responsive presentation, interactive components within Quarto); never introduces a framework or a bundled toolchain |
| [impeccable](impeccable/SKILL.md) | project adapter in front of the unmodified `reference/` files | `pbakaus/impeccable@08d5b470` | Required when a feature changes a major user-facing visual surface (the home, the atlas, a lesson page's frame) |
| [diagram-design](diagram-design/SKILL.md) | project adapter, principles in project words | `cathrynlavery/diagram-design@550fd66e` | Required when a conceptual diagram is produced or substantially changed; science and semantics checked independently |
| [pbc-scientific-visualization](pbc-scientific-visualization/SKILL.md) | project-owned | the digest of its record | Required for a new or substantially revised scientific figure; an exception is justified in the plan |
| [pbc-physics-teaching](pbc-physics-teaching/SKILL.md) | project-owned | the digest of its record | Not a visual skill (ADR 023 decisions 1 and 2): selected by the plan of a feature that writes or revises a lesson's teaching (its sequence, explanations, exercises, or displayed code), or its non-use recorded with the reason on a line `Skills: none (<reason>)`; not applicable to a plan that changes no lesson's teaching |

Manim is not part of the set (not scheduled); FreeCAD and OpenSCAD are not
candidates. The audit of each third-party candidate and the owner's
decision are in `docs/skill-audits/`; each directory holds the provenance
record `PROVENANCE.yaml` (upstream, revision, licence and redistribution,
the assessment of scripts and what was removed or adapted, the review date,
the update policy, and the digest of the files).

**Precedence.** A skill never overrides the Issue, the feature plan, the
design specification of F123 once it exists, `docs/authoring.md`,
`docs/validation-contract.md`, or a check. Where a skill's advice
conflicts with them (its own fonts or palette, "confirm with the client",
a command to run), the project's rule wins; the plan is the confirmed brief.
No skill's script, launcher, installer, or hook is run, and no skill is
installed globally or fetched at run time.

## Plan, completion, review

- **The plan** classifies each new visual deliverable (page or layout,
  conceptual diagram, scientific figure, animation, or none) and, for a
  lesson whose teaching it writes or revises, the teaching; it names the
  skills it selects on a line `Skills: <name>[@<revision>], ...` per
  deliverable, or `Skills: none (<reason>)`, and states the expected
  artifact, the scientific validation, and the accessible fallback. A
  revision is a prefix of at least seven characters of the record's
  `revision` or `digest`. The check fails a plan that names a skill this
  directory lacks or at another revision.
- **The implementer** reads `.agents/skills/<name>/SKILL.md` of every
  selected skill, and the files it points to, before producing the
  artifact; the completion record names the skill and its revision beside
  the artifact and its source, and explains any intentional exception.
  Naming a skill without an observable effect on the artifact is not
  compliance.
- **The reviewer** reads the same files by path, assesses the rendered page
  at desktop and phone width or the generated figure and its source (ADR
  018 decision 6), verifies the scientific claims against independent
  computations and tests, and checks that the guidance was followed or an
  exception approved. A skill is no evidence; a self-report is not
  accepted.

## Moving a pin

1. Re-audit the upstream at the new commit, in an empty directory outside
   the repository, reading and never executing it; update its record in
   `docs/skill-audits/`.
2. Copy the files byte for byte from the new commit (a vendored skill, the
   kept files of an adapter); revise an adapter's own `SKILL.md` where the
   upstream changed.
3. Record the new `revision`, the review date, and the digest:
   `uv run python -m pbc.skills --digest .agents/skills/<name>`.
4. Open a pull request; the owner approves it. The check fails until the
   record and the files agree.

The project-owned skills change by an ordinary reviewed pull request; the
digest of each is updated with every change.

## Discovery (F122 criterion 2)

Shown from the feature worktree of F122 on 2026-10-18, with the flags of
`agent_run` in `scripts/lib/agent.sh` for each provider and profile: each
runner was asked to list the skills its environment offers and to read
`frontend-design/SKILL.md` here by path. The write profile is interactive;
its flags were run with `--print` (Claude) or `codex exec` (Codex), which
load the same configuration.

| Provider, version | Profile | Roles that run it (`.agents/agents.conf`) | Lists the skills of this directory | Reads them by path |
|---|---|---|---|---|
| Claude Code 2.1.302 | write | project-grill, project-planner, implementer, triage-implementer | no (user-level and built-in skills only, among them the user-level Impeccable plugin) | yes |
| Claude Code 2.1.302 | unattended | implementer, triage-implementer | no (user-level and built-in skills only) | yes |
| Claude Code 2.1.302 | read-only | triage | no (none at all) | yes |
| Codex 0.160.1 | write | any role with `--agent codex` | yes, all four | yes |
| Codex 0.160.1 | unattended | any writing role with `--agent codex` | yes, all four | yes |
| Codex 0.160.1 | read-only | planning-reviewer, reviewer | yes, all four | yes |

Claude Code does not discover `.agents/skills/` in any profile, and its
write and unattended profiles offer the user-level skills of the machine,
which ADR 019 rules out. The role instructions therefore name the files to
read by path in every case (`AGENTS.md`, "Visual deliverables and skills",
and the prompts of the planner, implementer, and reviewer), which every
profile's Read tool allows; a skill the runner offers by name is used only
if it is the copy of this directory.
