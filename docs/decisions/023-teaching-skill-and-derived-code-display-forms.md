# ADR 023: The Physics Teaching skill joins the governed skills, and code on a lesson page may be an exact selection, a generated signature, or executed teaching code

## Status

Proposed with the planning of the change cycle `teaching-by-construction`
(`docs/changes/teaching-by-construction.md`, human-supplied, 2026-11-13,
revised draft v3 with its Appendix A of owner additions; requirements
decision 44 and its amendments of decisions 32, 38, and 43 and of the UX
expectation "Code shown on the site is the code that CI ran", re-approved
on 2026-11-13); accepted when that planning is approved. Delivered by
F164 (the skill and the workflow contract) and F175 (the display forms) of
`docs/roadmap.md`, "Phase 11".

Amends two accepted records, whose statuses name this one; their other
decisions stand:

- **[ADR 019](019-agent-skills-audited-pinned-and-project-local.md)
  decisions 2 and 5** (the set and the selection policy; the workflow
  contract): the governed set gains one project-owned skill that is not a
  visual skill, `pbc-physics-teaching`, and the contract gains the lesson's
  teaching as a deliverable the planner classifies (decisions 1 and 2
  below). Decisions 1, 3, 4, and 6 of ADR 019 apply to the new skill
  unchanged.
- **[ADR 002](002-regenerate-artifacts-and-display-by-reference.md),
  the decision "Displayed material reaches a page only through verified
  display forms", item 1** (Python code): the by-reference excerpt gains
  an exact multi-range selection with visible omission markers and a
  display that omits a docstring, and two derived forms are added, a
  signature generated from the source and simplified teaching code that
  the build executes as shown (decisions 3 to 5 below). Items 2 to 5 of
  that decision, the "not verified" marker included, are unchanged; so are
  ADR 002's other decisions and the amendments of ADR 007, 014, 016, 018,
  020, 021, and 022.

Date: 2026-11-13

## Context

Requirements decision 44 asks for better teaching without weaker
science. Two of its workstreams change accepted decisions.

The first is the Physics Teaching skill (T1). ADR 019 governs a set of
skills chosen for visual work: its decision 2 names the set and when each
is required, and its decision 5 makes the planner classify every new
*visual* deliverable. The new skill guides how a lesson is taught, which
is not a visual deliverable, so neither the set nor the contract as
written covers it. Decision 44 amends requirements decision 38 so that it
does: same location, provenance, pinning, and review contract, no new
mandatory review role.

The second is how code reaches a lesson page (U1). ADR 002 allows Python
code on a page in two forms only: an executed cell, or an excerpt included
by reference from `src/pbc/`, optionally a named region or a line range.
The cross-curriculum audit of the change request (Appendix B) found
lessons that show complete plotting functions of 40 to 100 lines, and long
docstrings that repeat the prose, before the few lines that carry the
physics. It also found plotting functions that compute residuals,
smoothing, or calibrations a learner must see. The owner decided on
2026-11-13 (decision 44, "Derived code on the page") that exact fragments
stay the default and that two derived forms are allowed where they
demonstrably clarify: a derived interface or signature generated from the
source, and simplified runnable teaching code executed exactly as shown by
CI against stated checks. Reviewer-checked code that nothing executes is
not one of them. Without a record, a contributor would read ADR 002 as
forbidding both forms, or read the forms as licence to paraphrase code.

## Decision

1. **The set.** `.agents/skills/pbc-physics-teaching/` is a project-owned
   skill of the governed set, with its provenance record (project-owned,
   its revision, the sources it distils, its review and update policy)
   and its entry in `.agents/skills/README.md`. It owns the pedagogical
   reasoning layer only: the target learner, the central physical
   question, prerequisite gaps, one or two deliberate prediction or
   interpretation moments, the distinction between prediction, derived
   property, simulation output, measurement, and inference, essential
   versus optional derivations, the teaching purpose of every displayed
   code block, and the lesson archetype (model or simulation,
   measured-data investigation, engineering design or capstone, AI agent
   or evaluation, agent-based model, formal proof). The editorial voice
   guide (`docs/editorial-voice.md`) keeps sentences and register, the
   authoring guide (`docs/authoring.md`) keeps the scientific and format
   rules, and the scientific-visualization skill keeps figures; where they
   meet, the skill points to them and repeats no rule of theirs. Like
   every skill it is guidance, never evidence, and never a dependency of
   the site, the build, or CI (ADR 019 decision 1, I32).
2. **The contract.** Besides the visual deliverables of ADR 019
   decision 5, the plan of a feature that writes or revises a lesson's
   teaching (its sequence, its explanations, its exercises, or the code
   it displays) selects `pbc-physics-teaching` or records why it is not
   useful, on the same `Skills:` line. The implementer records where the
   skill changed the learning experience, not that it was read; the
   reviewer reports named weaknesses with evidence and an action, never a
   score. No review role, agent, model call, or review round is added.
   A plan that changes no lesson's teaching (a check, a figure style, the
   chrome) records the skill as not applicable.
3. **Exact source stays the default.** Python code on a lesson page is an
   executed cell or an excerpt by reference, as ADR 002 says. An excerpt
   is either the whole object or an exact selection of its lines: one
   range, a named region, or, new here, several ranges of the same object
   joined by a visible omission marker, each range with its source line
   numbers. The display may omit an object's docstring when the prose
   states what it says; the omission is marked, the docstring stays in the
   source, and the Source link opens the whole object at the built commit.
   A selection is labelled as a selection and never offered as a runnable
   or copyable whole function. The default of every Lean excerpt is
   unchanged: Lean code is never selected away from its hypotheses and
   never simplified.
4. **A generated signature.** An excerpt may show, instead of the source
   lines of a function's signature, an interface generated from the
   source at build time (its parameter names and defaults read by the
   build from the function, its units from the interface table F35
   already reads). Nothing of it is typed by hand: a hand-copied name or
   default value is not this form. It is labelled as a generated
   signature, not a literal excerpt, and it keeps every default and unit
   the function has.
5. **Executed teaching code.** A simplified teaching version of a
   computation may be shown when the real implementation cannot be read
   without distracting infrastructure, only as code the build executes
   exactly as shown: an executed cell of the lesson, or an excerpt of a
   function in `src/pbc/` that the build executes. It carries a visible
   label that it is simplified, states what it leaves out, what was
   checked, and where the full implementation is (a Source link), and
   claims no full equivalence. Its checks run in the build or the test
   suite: the stated properties within stated assumptions, against an
   analytical solution or an independent reference where one exists, or
   against the full implementation on stated inputs. Where no such check
   exists, the lesson uses an exact selection, prose, and the Source
   link. Only the support the pilot lessons of decision 44 need is built;
   there is no general facility to simplify arbitrary code.
6. **Everything else stays unverified.** Code that is neither executed
   nor an exact or generated excerpt still carries the "not verified"
   marker of ADR 002 item 5, and the check that fails the build for
   unmarked non-executed code stays as it is. A reviewer's reading is not
   an execution.
7. **The checks follow the forms.** The source-excerpt checks extend to
   the new forms: an exact selection matches the pinned source lines byte
   for byte (or under one documented whitespace rule), its omission
   markers and line numbers are accurate, and a guard or assumption the
   displayed conclusion depends on is not among the omitted lines (a
   review question, recorded); a generated signature equals what the
   build reads from the function; executed teaching code is executed and
   its checks pass. Copying a displayed block copies code only, never a
   line number or annotation glyph. No check is weakened or removed.

## Alternatives considered

- **A separate teaching guide in `docs/` instead of a skill.** Rejected
  by decision 44: authors already have the voice guide and the authoring
  guide, and a third authoritative guide would compete with them; the
  skill is reasoning guidance read in the workflow and points to both.
- **Treating the teaching skill as a visual skill under ADR 019 as
  written.** Rejected: ADR 019's contract is keyed to visual
  deliverables, and pretending a teaching decision is one would leave the
  selection rule undefined for lessons with no new visual.
- **Shorten the source (drop docstrings, annotations, or defaults) so the
  excerpt is shorter.** Rejected by decision 44: the source serves the
  tests, the interface tables, and the reader of the repository;
  presentation changes the display only.
- **Reviewer-checked simplified snippets or pseudocode.** Rejected by the
  owner's answer of 2026-11-13: code a reviewer reads but nothing
  executes can drift from the implementation, which is the failure ADR 002
  exists to prevent.
- **A general code-simplification facility (automatic type stripping,
  rewriting).** Rejected: an unbounded transformation of source is hard
  to check and not needed; the pilots name the few cases.
- **Hide every `draw_*` function by its name.** Rejected: several compute
  residuals, smoothing, or calibrations (the audit's MAT6, W7, and Q7
  cases); the decision to show code is per block, by what it teaches.

## Consequences

- `.agents/skills/` (a protected path) gains one skill; `AGENTS.md`,
  "Visual deliverables and skills", and `docs/process.md`, "Agent
  skills", gain the teaching selection rule (F164). The skills
  configuration check validates the new skill as it validates the others.
- `pbc.authoring.excerpt` gains the multi-range selection, the marked
  docstring omission, the generated signature, and the labels; the
  lesson source check and the excerpt tests gain the assertions of
  decision 7 (F175). These are shared inputs: their feature is a full
  run.
- The verified display forms of `docs/architecture.md` and invariant I5
  read the new forms; invariant I36 states the truthfulness of displayed
  code.
- A lesson that adopts a derived form is reviewed for it: the reviewer
  checks the label, the omissions, and the checks of executed teaching
  code, and that no scientific conclusion rests on omitted lines.
- The cost: the excerpt helper and its checks grow; a selection with
  omissions asks more of review than a whole function. The forms are
  optional; a lesson that shows whole functions stays valid.
