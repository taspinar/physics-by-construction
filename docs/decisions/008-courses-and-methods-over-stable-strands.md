# ADR 008: Courses by subject and cross-cutting methods as metadata facets over the existing strands

## Status

Proposed with the planning of the change cycle `physics-next-phase`;
accepted when that planning is approved.

Date: 2026-10-09

## Context

The MVP organises content as one linear learning path of four strands
(`mechanics`, `agents-llm`, `agents-abm`, `lean`), generated from lesson
front matter. Lesson directories, URLs, and the `strand` and `order` fields
follow it, and eleven lessons are published under those addresses.

The re-approved requirements (decision 15) organise content as physics
courses by subject, with AI-assisted research, agent-based modelling, and
formal verification as cross-cutting methods exposed through tags, related
lessons, and cross-links, not as physics subjects. A lab belongs to one
primary course and links to its agent, measured-data, and Lean extensions
instead of being duplicated. The existing strand identifiers and published
URLs stay until an approved migration plan exists, and no such plan is
requested. Measured-data labs and coding-agent exercises are new kinds of
lesson that need a place.

The decision that is hard to reverse is where new lessons live, because
their addresses are public once published.

## Decision

1. **Three facets, one source of truth.** Every lesson's front matter
   carries, besides the existing fields, a `course` (its one primary
   physics subject), `methods` (the ways of working it uses, from a fixed
   vocabulary: `simulation`, `llm-agents`, `abm`, `lean`, `measured-data`,
   `coding-agents`), `outcomes` (what the reader can do afterwards), and
   `related` (lesson ids it cross-links as extensions). The vocabularies
   live in `pbc.authoring.path` next to the strands and the difficulty
   scale. The learning path page, the lesson header, the cards, and the
   prerequisite graph are generated from these fields; no hand-maintained
   list exists.
2. **Strands stay what they are.** `strand` and `order` keep defining the
   one linear order (previous and next), the directory, and the address.
   No identifier or address changes. A strand's display title may be
   refined (for example "AI-assisted research" for `agents-llm`) without
   changing its identifier.
3. **Placement of new lessons.** A lesson whose subject is the physics of a
   course, including a measured-data lab of that course, lives in the
   course's strand directory and takes the next order there (for example
   `mechanics/09-...`). A lesson whose subject is a method itself lives in
   that method's strand directory (`agents-llm` for harness and coding-agent
   lessons, `agents-abm`, `lean`). Every lesson, wherever it lives, names
   its primary course.
4. **No new strand without a course.** A new strand directory is created
   only by a roadmap feature that adds a course (F15), never for a method,
   a dataset, or a gallery. Methods are tags and paths, not places.
5. **A course appears when it has a lesson**, as a strand does today; the
   path page lists courses first, with each course's lessons in path
   order, and then one path per method across courses.

## Alternatives considered

**Migrate directories to `courses/<course>/...` and redirect the old
addresses.** Rejected: the requirements keep identifiers and URLs until a
migration plan is approved, GitHub Pages offers no server-side redirects,
and a client-side redirect page would make the site depend on JavaScript
for navigation.

**Make methods courses (an "AI agents" course, a "Lean" course).** Rejected
by the requirements: methods are not physics subjects.

**Put method lessons under the course directory too (for example
`mechanics/10-lean-...`).** Rejected: the existing method strands would
stop growing and would hold only their first lesson, and a method path
would mix two directory conventions.

**Keep the linear path only and add a tag page.** Rejected: a lab must
belong to one course, and a reader must be able to see a course as a unit;
a tag page alone does not give the course order.

## Consequences

Positive:

- Every published address survives; the eleven lessons migrate by front
  matter only.
- The path page can show a course as a unit and a method as a path across
  courses, from one source of truth.
- A measured-data lab has an unambiguous home: its course.

Negative, with mitigations:

- Two orderings coexist, the linear strand order and the course view; the
  path page explains what previous and next mean, and the prerequisite
  graph shows the dependencies.
- A reader who follows "next" from the last mechanics lesson still reaches
  the agent strand, as today; the course view and the related links give
  the alternative route.
- The strand vocabulary and the method vocabulary overlap in name; the
  authoring guide states the rule of decision 3 with examples.
