# ADR 013: Eight physics courses as strands, the reference curriculum as declared data, and method paths as a facet

## Status

Proposed with the planning of the change cycle `final-curriculum`;
accepted when that planning is approved. Supersedes decision 4 of
[ADR 008](008-courses-and-methods-over-stable-strands.md) (a new strand
only through F15) and amends its decisions 1, 3, and 5; the other decisions
of ADR 008 stand. Decision 8 replaces the rule of F02 that a prerequisite
comes earlier in the linear order with a rule over the prerequisite graph.
Extended by
[ADR 018](018-scientific-atelier-asset-classes-and-the-course-atlas.md)
(2026-10-17): the course atlas adds one map manifest beside the
curriculum file, holding only concept identifiers, display placement,
concept-to-slot associations, and curated conceptual connections with
their rationale; the curriculum file stays the one declared source of the
planned structure and gains no field (ADR 021 repeats this rule), and the
decisions below are unchanged. Decisions 3 and 5 amended by
[ADR 022](022-part-b-method-paths-with-capstone-products.md)
(2026-11-01): a slot of a method path may be an extension slot, shown and
counted apart from the core slots, and a method path's capstone slot has
the kind `product capstone`; the reference curriculum's counts are those
of its core slots. With it, the rule of ADR 018 and ADR 021 that the
curriculum file gains no field is amended in this one respect: a slot
gains the optional key `extension` and the kind `product capstone`, and
the curriculum file still gains no description field and holds nothing a
lesson's front matter holds. The other decisions below are unchanged.

Date: 2026-10-12

## Context

The re-approved requirements (decisions 23 to 26) adopt a reference
curriculum of 115 lesson slots: eight physics courses with 81 slots, four
physics-and-AI method paths with 33 slots, and the one Lean lesson of the
baseline. They keep every published address, lesson identifier, and strand
identifier, keep the course, methods, and strand facets of ADR 008, ask for
stable identifiers and placement rules for the new courses through a
superseding ADR, and want the four method paths as a secondary view over
the same lessons, never as duplicate pages. The Learning Path page must
show a course's real published-lesson count, and a planned lesson is shown,
if at all, through metadata rather than a placeholder page.

ADR 008 allowed one additional course, created by F15 with the human's
choice of topic. F15 has no Issue and no lesson. Twenty-two lessons are
published in the four strands `mechanics`, `agents-llm`, `agents-abm`, and
`lean`, all with `course: mechanics`. Of them, eighteen fill a slot of the
reference curriculum and four are Lean lessons beyond its baseline (the
reconciliation is in `docs/roadmap.md`, "State at the change cycle
`final-curriculum`").

Three things are hard to reverse once published: the address of a lesson,
the identifier of a course, and where the curriculum structure lives, since
pages, tests, and the human's approval refer to it.

Since F02 the lesson source check requires every prerequisite of a lesson
to come earlier in the one linear order (strand order, then `order`), which
is also the order of previous and next. With the eight course strands
before the three method strands, that rule would forbid the prerequisite
edges the curriculum needs: the gas lesson T0 keeps its address in
`agents-abm`, after every thermodynamics lesson, while T2 builds on its
model; the Lean integrator lesson L3 stays in `lean`, after every mechanics
lesson, while M11 checks its integrator against it. Authors would have to
leave such prerequisites out to pass validation.

## Decision

1. **Eight courses with fixed identifiers.** The course vocabulary of
   `pbc.authoring.path` holds the eight courses of the requirements:

   | Course identifier | Display title | Curriculum labels |
   |---|---|---|
   | `mechanics` | Classical mechanics | M |
   | `thermodynamics` | Thermodynamics and statistical physics | T |
   | `waves` | Waves and optics | W |
   | `electromagnetism` | Electromagnetism | EM |
   | `fluids` | Fluid dynamics | FL |
   | `quantum` | Quantum physics | Q |
   | `astrophysics` | Astrophysics, cosmology, and relativity | AST |
   | `materials` | Condensed matter and materials physics | MAT |

   `mechanics` keeps its identifier; its display title changes, which ADR
   008 allows. An identifier never changes and is never reused. The eleven
   optional expansion slots of the change request (nuclear and particle,
   plasma, geophysics and climate) have no course and no identifier until a
   decision adds them.

2. **Every course is a strand with the same identifier.** A course's
   lessons live in `site/lessons/<course>/<nn>-<slug>/` and take the next
   free order there, as the mechanics lessons do today (ADR 008 decision
   3). The strand directory of a new course is created by the first feature
   that publishes a lesson of that course, never by a placeholder. The
   strand order of `pbc.authoring.path`, which defines previous and next
   (ADR 008 decision 2), lists the eight courses in the order of the table
   above and then `agents-llm`, `agents-abm`, and `lean`. The three method
   strands keep their identifiers and addresses; no method strand is added.
   Lessons whose subject is a method still live in the method's strand
   (`agents-llm` for the lessons of the four method paths whose subject is
   the method, `agents-abm`, `lean`), and the display title of `agents-llm`
   may be refined to name physics and AI.

3. **The reference curriculum is declared data, in one file.** A curriculum
   file in the site project (site/curriculum.yaml, read by
   `pbc.authoring.path`, which takes the course and path vocabularies
   from it so that there is one place to edit) lists the eight courses,
   the four method paths, and every slot of the reference curriculum: its label (`M17`, `T10`,
   `D13`, ...), its working title, the course or the method path it belongs
   to with its position in that path, and its kind (`lesson`,
   `measured-data lab`, or `applied capstone`). It holds nothing a lesson's
   front matter holds: no description, outcomes, prerequisites, difficulty,
   or methods. A lesson declares the slot it fills with the front-matter
   field `slot`; the lesson source check requires that the label exists,
   that no two lessons claim one slot, and that a slot homed in a course is
   filled only by a lesson whose `course` is that course (a slot of a
   method path may be filled by a lesson of any course). A lesson without a slot is allowed
   (the four Lean lessons beyond the baseline have none) and appears in its
   course and method views as today. The human approves the file's content
   with the planning and with the feature that changes it.

4. **The method paths are a facet derived from the slot.** A lesson that
   fills a slot of a method path belongs to that path at that position; no
   lesson belongs to two paths. The learning path page shows the four paths
   as a secondary view over the same lesson pages, after the courses; the
   existing method views (simulation, measured data, agent-based modelling,
   LLM agents, formal proofs, coding agents) stay and are derived from
   `methods` as before. A method path is never a course, a strand, or a
   directory.

5. **Published facts come from front matter; planned structure from the
   curriculum file.** A course's published-lesson count, its lesson cards,
   and every link come from the lessons that exist. The slots of a course
   that no lesson fills may be shown as planned, visibly distinguished,
   with the label and working title only, and never as a link or a count of
   published lessons. A course appears as a course on the path page only
   when it has a lesson (ADR 008 decision 5 stands); the page may name the
   courses that have none in one sentence. The home page's list of planned
   content is derived from the same file, which replaces the hand-kept list
   of `pbc.authoring.home`.

6. **A lesson may change its primary course by front matter when its course
   comes into existence.** The gas lesson of F11 keeps its address under
   `agents-abm` and its identifier, and becomes `course: thermodynamics`
   with `slot: T0` with the first thermodynamics lessons (F70), which set
   the two fields in one change; until then the lesson carries no `slot`,
   `course: mechanics` stands, and T0 is an unfilled planned slot of the
   thermodynamics course (F62 migrates the seventeen other published
   lessons that fill a slot). The same rule applies to no other published
   lesson today. Nothing else about a published lesson changes: not its
   address, identifier, strand, or order.

7. **F15 is reconciled by this decision, not rewritten.** Its goal, a
   second course, is delivered by the course architecture and the lesson
   features of the roadmap; its rule that a course has at least one agent
   and one Lean lesson is not carried, because the method paths are a view
   over the courses and proofs are added where they add physics insight.
   F15 is marked dropped in the roadmap, with this change cycle as the
   reason, and its ID is never reused.

8. **The prerequisite graph is validated as a graph; the linear order is a
   reading route, not the dependency order.** Previous and next keep
   following the strand order of decision 2 and `order`, and every
   address, identifier, strand, and order stays as it is. The lesson
   source check requires of a prerequisite that it exists, that the graph
   has no cycle, and that a prerequisite in the same strand comes earlier
   in that strand; a prerequisite in another strand may come later in the
   linear order. So T2 in `thermodynamics` may require T0 in `agents-abm`,
   M11 in `mechanics` may require L3 in `lean`, and a method-path lesson
   in `agents-llm` may require, as today, the course lessons that come
   before it. The reader who follows previous and next is told what to
   read first by the header, which links every prerequisite; the path page
   explains that previous and next walk the courses and then the method
   strands, and that the dependency map gives the order of ideas. The
   course view and the path view of the path page order a course's or a
   path's lessons by the order in which the curriculum file lists their
   slots (the teaching order, which may differ from the label order: T0
   before T1, T6 before T10 before T11), with the lessons without a slot
   after them in linear order; the related links and the graph layout
   (`pbc.authoring.graph`, columns by prerequisites) are unchanged. F62
   delivers the check and the ordering with tests over the T0 to T2
   progression and a cross-strand prerequisite, before any lesson needs
   them.

## Alternatives considered

**One `courses/<course>/` directory tree with the existing four strands
left in place.** Rejected: two directory conventions would coexist for the
same kind of content, and ADR 008's rule that a course's lessons live in
the course's strand directory already fits eight courses once each course
is a strand.

**Keep F15 and let it create the thermodynamics course.** Rejected: F15's
scope (one course of the human's choice with an agent and a Lean lesson)
no longer describes the work, and the requirements ask for a transparent
transition rather than a repurposed feature; a dropped feature with a
stated reason is the transparent record.

**Derive the planned curriculum from the roadmap document.** Rejected: the
roadmap is prose for people; the path page needs validated data, and a
test that parses a Markdown document to render a page is brittle.

**Put the planned slots in lesson front matter as placeholder pages.**
Rejected by the requirements: no placeholder lesson pages.

**A `path` field in front matter beside `slot`.** Rejected: the slot
already determines the path and the position, and a second field could
disagree with it.

**A panel for each of the eight courses on the path page, with a zero
count and a conceptual miniature for a course that has no lesson.**
Considered because the change request asks for eight panels; rejected
because the change request also forbids advertising planned content as
published, and a zero-count panel is a placeholder in another form.
Decision 5 keeps ADR 008 decision 5 and the requirements' use case 1: a
course appears as each gains a lesson, and the courses without one are
named in one sentence (F64).

**Keep the rule that a prerequisite comes earlier in the linear order, and
make the linear order a topological order of the prerequisites.** Rejected:
previous and next would then interleave method-strand lessons with course
lessons by their prerequisites, which changes the route every reader and
the F03 tests know, and a new prerequisite could move a lesson's neighbours
anywhere in the sequence. Addresses would survive, but the one linear order
would stop meaning "the courses, then the methods".

**Move T0 into the `thermodynamics` strand.** Rejected by the requirements
(decision 24): the gas lesson keeps its `agents-abm` address; a redirect
would be a second address for one page.

**A strand per method path (`law-discovery/`, ...).** Rejected: ADR 008
keeps methods as tags and paths, not places; the `agents-llm` strand holds
the method lessons, as it does today, and a path is a view.

## Consequences

Positive:

- Every published address survives; the migration of the published
  lessons is front matter only: `slot` for seventeen lessons in F62,
  `course` and `slot` for the gas lesson in F70, nothing for the four Lean
  lessons beyond the baseline (decision 6).
- The course-first path page, the method-path view, the planned slots, and
  the home page's planned list have one validated source, and a test can
  compare the page with the curriculum file and the front matter.
- A lab or a capstone has an unambiguous home and a stable address before
  it is written.

Negative, with mitigations:

- The curriculum file is a second declared file beside the front matter.
  It holds only what front matter cannot (what is planned), a check keeps
  the two consistent, and changing it is a reviewed change.
- The linear order of previous and next changes once: the lesson after the
  last mechanics lesson becomes the first thermodynamics lesson instead of
  the first agent lesson. The path page explains what previous and next
  mean, and the course and path views give the other routes.
- A reader who follows only previous and next can reach a lesson before a
  prerequisite that lives in a later strand (T2 before T0). The header
  names and links the prerequisite, the course view lists T0 first, and
  the recommendations of F14 follow the graph, not the linear order; the
  check no longer hides the edge by forbidding it.
- The `agents-llm` strand grows with every method-path lesson, in landing
  order; the path view gives the teaching order, and the header of a
  lesson can show its position in its path.
- A course with a lesson but many planned slots shows mostly planned
  entries for a while; they are visibly distinguished and never counted.
