# Plan: F136 — Part B curriculum migration, Issue #370

- Issue: #370 (source: `docs/roadmap.md`, F136); "Detailed implementation
  plan expected: yes".
- Branch: `feature/370-part-b-curriculum-migration`; base `fc6da35`.
- Written by the implementer: no plan existed when the feature started
  (the precedent of F137, #359).
- Constraints: ADR 022 decisions 1 to 4 (labels, extension slots, the kind
  `product capstone`, migration by front matter and data only); ADR 013
  decisions 3, 5, 6 as amended; ADR 021 decision 3 as amended (the
  curriculum file gains only `extension` and the kind); invariant I28.
- Gates: F133 merged (#351), F134 merged (#361), F135 merged (#365); none
  in flight beside this feature in `pbc.authoring`.

## Risk

Level 3: the escalation trigger of the Issue (the curriculum test's count
assertions change; a shared input, so a full run), and the protected path
`docs/roadmap.md` (the planning correction of criterion 6 and the
inventory). Rounds take feedback from
`./scripts/verify.sh --only <groups>` and the unit tests of the changed
modules; the final tree gets the full `./scripts/verify.sh`, run last, and
a full review after it, and the owner's approval of the exact commit.

| Criterion | Gate |
|---|---|
| 1 Counts, kinds, retired labels | implementation; the file's content `owner_approval` (question 20) |
| 2 Published lessons re-slotted, addresses unchanged | implementation |
| 3 Atlas, path view, headers | implementation |
| 4 One concept per capstone; Home's choice | implementation |
| 5 Sequence descriptions | implementation (no hand-written copy); the text `owner_approval` on the Issue |
| 6 Outcome check of D7, D8, D13 | implementation (the check and the planning correction); recording on the Issue `owner_approval` |
| 7 Full verification | implementation |

## Visual deliverables

- Page and layout: the extension group of a method path's panel on the
  atlas (after the core rows, under its own heading "Optional extensions"
  with a one-line note and its own counts; no fourth row mark), the product
  capstones under the existing capstone mark, the extension wording of the
  lesson header, and the hero labels of Home for the longer path titles
  (two balanced lines of up to 26 characters; the path column a few units
  further from the right edge, and on a phone the two path columns 100
  units apart in height in a box 40 units taller, so that no label leaves
  the image or touches another; a third line was tried and ran past the
  bottom of the image). Reuses the atlas rows, marks, and tokens; no new component.
  Skills: impeccable@08d5b47, frontend-design@dbd4588
  Expected artifact: the built path page and Home at desktop and phone
  width. Validation: the unit and e2e atlas tests (rows, counts, marks,
  states, reachability without scripts). Accessible fallback: the textual
  equivalent of the atlas names every extension row as an optional
  extension; the group is a section with a real heading and list, not a
  visual mark only. Playbooks: `craft-floor.md` (the checks on the
  render), `layout.md` (grouping by proximity and a heading, no new
  container or mark), `clarify.md` (the group's wording); the automated
  detector of Impeccable did not run (the adapter forbids it).
- No figure, no diagram.

## Design

**Curriculum file.** The four path titles of decision 42 (same order and
keys); per path the core slots in teaching order with positions 1 to n
(capstone last, kind `product capstone`), then the extension slots with
`extension: true`, positions continuing after the core, working titles
unchanged. The 26 retired labels are gone.

**Schema (`pbc.authoring.path`).** `KINDS` gains `product capstone`;
`CAPSTONES` names both capstone kinds. A slot may carry `extension: true`
(nothing else): only a slot of a method path, never a capstone; no core
slot of a path after an extension slot. An `applied capstone` is homed in a
course and a `product capstone` in a path. `Slot.extension`;
`Curriculum.core_in_path`, `extensions_in_path`.

**Views.** The header: a core path slot says "number n of the m slots"
with m the core count; an extension slot says "an optional extension of
the path [title]". The atlas: a path's rows are the core rows, then the
extension rows; `AtlasSequence.published`/`planned` count the core rows,
`extension_published`/`extension_planned` the rest; the card and the
panel counts are the core's, the extension group carries its own; the
summary counts every published lesson (the extension lessons among them)
and the planned core slots, and names the extensions apart. The textual
equivalent marks each extension row "optional extension". Home: a
capstone of either kind, chosen only among published ones; a path
capstone's note names its path. `atlas_problems` checks the area of a
path capstone's concept by its path.

**Manifest.** Concept slot lists with the new labels (every Part B core
and extension slot in exactly one concept, the concept ids kept so that
the aliases stay), new concepts `instruments-and-measurement`,
`sealed-evaluation`, `research-ideas-and-plans`,
`follow-ups-and-reports`, and one concept per product capstone
(`autonomous-physics-lab`, `system-discovery-lab`,
`scientific-agent-testbench`, `scientific-research-workspace`) whose
explanation is the planned description; four sequence descriptions
rewritten for the new outcomes (proposed text, the owner approves it on
the Issue); illustrations unchanged.

**Front matter.** `lesson.slot` of the seventeen moved lessons only.

**Tests.** `test_curriculum.py`: core counts 81, 34 (9, 10, 7, 8), 1, 116;
seven extension slots; the four product capstones; none of the 26 retired
labels; the roadmap comparison reads Part A and Lean from "Slot mapping
(change cycle `final-curriculum`)" and Part B from the slot mapping of
`part-b-scientific-products-and-research`; the schema rules of the
extension and the kinds; the inventory of the 22 Part B lessons (address,
id, strand, order, course at the base, and the new slot). The atlas, home,
and e2e tests for the extension group and the product capstones; an e2e
test that every Part B lesson address of the base still serves its lesson.

**Docs.** `docs/authoring.md` (extension slot, product capstone);
`docs/roadmap.md` (the outcome check's result: D7 and D8 become *extend*,
the parts assigned to F146 and F147).

## The outcome check of criterion 6

Each part of the slot's new outcome (change request section 3.2), against
the lesson as published at the base:

**D7 `symbolic-regression` in MD3 (B2.3).**
- Complexity: met. "A grammar, a fit, and a rule for choosing" (the
  complexity count), the Pareto front `pareto`/`fig-pareto`, Limits "The
  choice of the simplest is a convention".
- Units: met. Exercise "Units as prior knowledge"; the self-check on two
  forms of equal chi-square (units as a constraint).
- Withheld prediction: met. Worked example "Held-out pendulums"
  (`held-out`), outcome 2.
- Operator choices: not met. The grammar is fixed (power laws with
  half-integer exponents); only Limits "The grammar decides what can be
  found" names a richer grammar, and no section or exercise varies the
  operators. Assigned to F146 (MD3: an investigation of operator choices
  on the transparent grammar); the action becomes *extend* (F146).
- The comparison with an optional broader engine is optional by the
  inventory (only through an integration a feature chooses) and is not
  claimed.

**D8 `discovering-differential-equations` in MD4 (B2.4).**
- Derivatives: met. "Derivatives from samples" (central differences and
  their error), outcome 1.
- New trajectories: met. Worked example "A start the regression never
  saw" (`fig-held-out`), outcome 3.
- State selection: not met. The state is fixed to position and velocity;
  the exercise "A pendulum through a polynomial library" varies the
  library, not the state. Assigned to F147 (MD4: choosing the state
  variables and detecting a missing one); the action becomes *extend*
  (F147).
- Weak formulations and PySINDy are optional routes, only through a
  chosen integration; not claimed.

**D13 `discovering-conservation-laws` in MD7 (B2.7).**
- Quantities constant along trajectories: met. "Invariants from
  trajectories" (the null space of the changes), outcome 1, worked example
  "A test system with a known answer".
- Approximate numerical constancy against a justified invariant: met.
  "Four ways to be constant without being a law", the verdicts on
  held-out starts at three integration settings (`fig-verdicts`),
  "Coincidences of the trajectories", outcomes 2 and 3.
- Reused as it is.

Until F146 and F147 merge, MD3 and MD4 show the lessons' own titles and
outcomes (the header and the atlas row never show the slot's working
title for a filled slot).

## Steps

1. Schema, views, and tests in `pbc.authoring` (path, atlas, home).
2. The curriculum file, the front matter, the manifest.
3. Unit tests; e2e tests; docs; roadmap correction.
4. Look at the built path page and Home at desktop and phone width.
5. Full `./scripts/verify.sh`, run last.

## Open questions

- The owner approves the curriculum file (question 20, the labels) and the
  four sequence descriptions on the Issue; until then those criteria are
  `owner_approval`, pending.

## Roadmap updates left for the next planning change

F136 may not edit docs/roadmap.md (only a planning cycle may). The edits that the outcome check calls for (D7 and D8 from reuse to extend, the counts 1 reused and 16 extended, MD3 gaining symbolic-regression, and the sentence about the curriculum file holding the new slots since F136) are recorded on Issue #370 with their diff and are applied by the next planning change.
