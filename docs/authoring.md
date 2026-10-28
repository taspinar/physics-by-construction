# Authoring a lesson

How to write a lesson for Physics by Construction. Following this guide and
the template is enough to add a lesson; you do not need to read another
lesson's source. The rules come from `docs/architecture.md` ("Lesson model",
"Verified display forms") and ADR 002, and `./scripts/verify.sh` enforces
them.

The one idea behind every rule: **a page shows only what the build produced
or checked.** Code is executed or read from the tested package, numbers and
figures are the output of that code, and anything else is visibly marked "not
verified".

For how the prose of a lesson should read (openings, intuition, derivations,
experiments, interpretation, transitions, conclusions), see the editorial
voice guide, `docs/editorial-voice.md`. It changes none of the rules below.

## Create a lesson

1. Pick the course, the strand, the slot, and the position of the lesson.
   The eight courses are `mechanics`, `thermodynamics`, `waves`,
   `electromagnetism`, `fluids`, `quantum`, `astrophysics`, and `materials`;
   every course is a strand with the same identifier, and the strands are
   those eight, then `agents-llm`, `agents-abm`, and `lean`, in learning path
   order (ADR 013). A lesson about the physics of a course lives in the
   strand of that course (a measured-data lab of the mechanics course is a
   mechanics lesson); a lesson about a method itself lives in the strand of
   the method. Either way it names its course. The strand directory of a
   course that has no lesson yet is created by the first lesson of that
   course, never by a placeholder. The slot is the lesson's place in the
   reference curriculum, `site/curriculum.yaml`: take the slot the lesson
   fills from that file and name it in `lesson.slot`. A slot homed in a
   course is filled only by a lesson of that course; a slot of a method path
   may be filled by a lesson of any course. `docs/roadmap.md` lists the
   planned lessons and their features.

2. Create the lesson directory and copy the template into it. The directory
   name is the two-digit position in the strand, a hyphen, and a short name
   in lowercase words joined by hyphens:

   ```bash
   mkdir -p site/lessons/agents-abm/01-particles-in-a-box
   cp docs/lesson-template.qmd site/lessons/agents-abm/01-particles-in-a-box/index.qmd
   ```

3. In the front matter of the new `index.qmd`, set `id` and `order` first.
   The template leaves both invalid on purpose, so the checks report a lesson
   that still carries them. Then fill in the other fields (next section).
   The learning path page, the header of the lesson, and its previous and
   next links are generated from these fields; there is no list to add the
   lesson to.

4. Put the reusable code of the lesson in `src/pbc/<course>/` with unit tests
   in `tests/unit/`. For a numerical method, one test compares it with a
   closed-form solution or a limiting case, with an explicit tolerance.

5. Write the page. Replace every part of the template; keep its section
   headings or their identifiers, and keep the header cell at the top.

6. Check it:

   ```bash
   uv run --locked pytest tests/unit                                                # the code and the experiment
   uv run --locked pytest tests/lessons                                             # the lesson source checks
   uv run --locked python -m pbc.<course>.experiments.<lesson> results              # the experiment of the lesson
   ./scripts/verify.sh --targeted                                                   # before a pull request: the targeted run
   ```

   The experiment writes the figures and numbers of the page into `results/`
   ("The experiment of a lesson"). `docs/development.md` has the one-time
   setup these commands need, and under "Verification" the three tiers. The
   targeted run computes what CI will execute, runs the checks that need no
   site build, and checks the changed lessons alone; it builds no site. A new lesson, or a change to the
   front-matter fields that form the learning path and the headers of its
   neighbours, needs `./scripts/verify.sh --base`; when a change needs the
   full `./scripts/verify.sh`, the targeted run says so.

## Front matter

```yaml
---
title: "Kinematics as a program"
description: >-
  One sentence that says what the lesson builds and what it checks.
lesson:
  id: kinematics
  strand: mechanics
  order: 1
  difficulty: 1
  course: mechanics
  methods: [simulation]
  outcomes:
    - Write motion along a line as a state and an update rule
    - Check a simulation against the exact solution
  related: [proving-what-the-simulation-showed]
  prerequisites:
    lessons: []
    outside:
      - "Calculus: derivatives, integrals, and Taylor expansion to second order"
  lean-modules: []
---
```

| Field | Required | Rule |
|---|---|---|
| `title` | yes | The lesson title. |
| `description` | no | One sentence; shown under the title and used as the page description; the learning path also shows it as "What you build" in the details of the lesson. |
| `lesson.id` | yes | Stable identifier: lowercase words joined by hyphens, starting with a letter. Unique across the site. Other lessons name it as a prerequisite, so it never changes and is never reused. Do not put the position in it. |
| `lesson.strand` | yes | One of the eight course identifiers (`mechanics`, `thermodynamics`, `waves`, `electromagnetism`, `fluids`, `quantum`, `astrophysics`, `materials`), then `agents-llm`, `agents-abm`, `lean`, in learning path order. Must be the strand directory the lesson is in. |
| `lesson.order` | yes | Position in the strand, 1 to 99. Must equal the number the directory name starts with. The orders of a strand run from 1 without a gap or a duplicate. |
| `lesson.difficulty` | yes | 1, 2, or 3 on the one difficulty scale of the site: introductory, intermediate, advanced. The scale is defined in `pbc.authoring.path` and explained on the learning path page. |
| `lesson.course` | yes | The one primary course of the lesson, from the `COURSES` vocabulary in `pbc.authoring.path` (the eight courses of ADR 013). A course appears on the learning path page once it has a lesson. Every lesson names a course, also an agent, agent-based, or proof lesson: it is the course whose results the lesson uses. |
| `lesson.slot` | no | The label of the slot of the reference curriculum (`site/curriculum.yaml`) that the lesson fills, such as `M1` or `AI0`. The label must exist, no two lessons claim one slot, and a slot homed in a course is filled only by a lesson whose `course` is that course. A lesson without a slot is allowed and appears in its course and method views. The slot decides the lesson's position in its method path, if the slot belongs to one; it never changes the address. |
| `lesson.methods` | yes | List of the ways of working the lesson uses, from the `METHODS` vocabulary: `simulation`, `llm-agents`, `abm`, `lean`, `measured-data`, `coding-agents`. At least one, none twice. The path page has one path per method. |
| `lesson.outcomes` | yes | List of two to five sentences: what the reader can do after the lesson. Shown in the header as "What you'll learn". Write what the reader does, not what the lesson contains. |
| `lesson.related` | yes | List of the `id`s of lessons the header links as extensions, such as the agent, measured-data, or Lean counterpart of a lab. May be empty. Each must exist, must not be the lesson itself, and must not already be among its prerequisites. Write the link on the lesson that is built on, towards the extension; the extension keeps that lesson as a prerequisite and does not list it back. |
| `lesson.prerequisites.lessons` | yes | List of the `id`s of lessons a reader needs first. Each must exist; a prerequisite in the same strand must come earlier in it, and one in another strand may come later in the linear order (ADR 013 decision 8). The prerequisites form no cycle. May be empty. |
| `lesson.prerequisites.outside` | yes | List of texts `Term: what exactly`: what a reader must know that no lesson on the site teaches. The text before the first colon must be the `term` of an entry of `site/glossary.yaml` (see "Glossary"). May be empty. |
| `lesson.lean-modules` | no | List of the Lean modules the lesson displays, such as `PhysicsByConstruction.Mechanics.Kinematics`. A lesson that shows Lean lists exactly the modules it names: each must exist in `lean/`, and the page names no other. |
| `lesson.format` | no | `1` (the default: the MVP template) or `2` (the progressive-depth template, see "Lesson format 2"). The checks of format 2 apply to the lessons that declare it. |
| `lesson.experiment` | yes | The lesson's experiment, see "The experiment of a lesson": the module `pbc.<course>.experiments.<name>`, where `<name>` is the `id` with hyphens as underscores; or `./scripts/check-lean.sh` for a lesson whose methods are `[lean]` only and that computes nothing it shows. |

No other key is allowed, neither at the top level nor under `lesson`. Options
that apply to every page belong in `site/_quarto.yml`. An option that changes
how one page is executed (`execute`, `freeze`, `jupyter`) would undermine the
checks and is rejected with the rest.

## Glossary

`site/glossary.yaml` defines the vocabulary the lessons assume; `site/glossary.qmd`
renders it, and the header of every lesson renders a "Before you begin" list
from `prerequisites.outside`, with the term of each item linked to its entry.

```yaml
entries:
  - term: Calculus
    definition: >-
      One to three sentences that say what the lessons mean by the term.
    see: numerical-integrators   # optional: id of the lesson that explains it
```

Write an outside prerequisite as `"Calculus: the chain rule"`: the term, a
colon, and the detail this lesson needs. Add an entry when a lesson needs a
term that has none. An entry has one to three sentences, a term appears once,
and a term that no lesson assumes is rejected, so the glossary lists nothing
that is not used. The page lists the lessons that assume each entry; do not
write that list by hand.

Prefer an internal link: when a lesson on the site explains the topic, name it
in `see` and the entry links it. Link an introduction elsewhere only through
the reference register (a `go-deeper` block in a lesson) and only where it adds
real depth; the glossary itself contains no external link.

## The learning path

The learning path is the lessons in order: the strands in the order above,
and within a strand the lessons by `order`. Previous and next follow this one
linear order, the courses and then the method strands; it is a reading
route, not the dependency order. The course view and the path view order the
lessons by the order of their slots in `site/curriculum.yaml` (the teaching
order), the lessons without a slot after them, and the prerequisites say what a
lesson needs. It is all derived from the front
matter when the site is built, so there is no list to maintain:

- The page `site/path/index.qmd` lists each course that has a lesson, with
  its core lessons (the lessons of the strand named like the course) and its
  extensions (its lessons in other strands), then one path per method that
  has a lesson. For each lesson it gives the difficulty, description, and
  prerequisites. It shows the slots of a course that has a lesson and of every
  method path that no lesson fills as planned entries (a label and a working
  title, no link, never counted as published), shows the four method paths of
  the curriculum as a view over the same lessons, names the courses that have
  no lesson yet in one sentence, and explains the difficulty scale and what
  previous and next mean.
- The first cell of every lesson writes the header of the lesson: its course
  and position in the course, its slot and, for a method-path lesson, its
  position in the path, its methods, its difficulty, what you will
  learn, its prerequisites and related lessons with links, and links to the
  previous and next lesson of the path. The template has the cell; keep it
  before the introduction:

  ````markdown
  ```{python}
  #| echo: false
  from pbc.authoring import lesson_header

  lesson_header()
  ```
  ````

The site has no sidebar. Quarto's sidebar hides behind a JavaScript toggle
on narrow screens, and a sidebar per course would need a list of lessons in
`site/_quarto.yml`, which would be a second source of truth. The header and
the path page give the course navigation without JavaScript.

A check validates the path as a whole: ids are unique, the orders of a strand
run from 1 without gaps or duplicates, every prerequisite exists, a
prerequisite in the same strand comes earlier in it, the prerequisites form no
cycle, and every course, slot, method, and related lesson follows the rules
of the table above. The same check validates `site/curriculum.yaml`: an
unknown course or path, a duplicate label, a slot without a home or with two,
and any field that belongs to a lesson's front matter fail it. A violation fails verification, and
the build of a page fails on it too.

### The course atlas

Since F125 the path page opens with the course atlas (ADR 018 decision 3):
a map of the eight courses, the four method paths, and the Lean and method
views, written by `pbc.authoring.atlas` when the page is built, above the
course index. Its data come from three places and nowhere else: courses,
paths, and slots from `site/curriculum.yaml`; titles, publication,
prerequisites, and addresses from the front matter; and from the map
manifest `site/atlas.yaml` only what neither holds:

- `concepts`: each with an `id` (lower case and hyphens; the map shows it
  in words, so it is the concept's name), an `area` (a course or a path),
  a `position` `[column, row]` in the area's grid of 2 by 4, its `slots`,
  and a one-sentence `explanation`;
- `connections`: two `concepts`, a `type` (`same-mathematics`, `limit`,
  `same-method`, or `application`; `limit` and `application` read "the
  first is a limit of / applies the second"), and a `rationale`.

A concept whose only slot is a capstone slot represents that capstone: its
explanation is the capstone's planned description, the one place that text
lives, kept consistent with the roadmap. A concept that names a capstone
slot beside its own slots is a member of that capstone. The build derives
everything else: a concept's lessons from its slots (never from a title),
its state and counts, the prerequisite edges between concepts from the
lessons' prerequisites, and capstone membership.

The lesson source checks reject a manifest with an unknown field, a field
that the curriculum file or the front matter holds (a title, a description,
an outcome, a prerequisite, a state, a count, a lesson), an illustration
reference, a connection of type `prerequisite` or `capstone`, a reference
that does not resolve, a concept without a slot or with a slot outside its
area, two concepts on one position, and a capstone slot that is not
represented by exactly one concept. A new slot in the curriculum file needs
its concept here (a unit test checks that every course and path slot is on
the map). Every concept-to-slot association and every connection is a
scientific claim about the curriculum: it is reviewed independently, and
the owner approves the file.

When scripts run, `site/learner/atlas.js` (F126) adds the atlas's controls:
selection with the selected concept's panel under the map, what the map
shows (every relationship, the concepts alone, the prerequisites, or the
conceptual connections), zoom from the natural size upwards, a region
selector with the region's list, and filters in step with the course
index's (`site/learner/path.js`). It reads only what the page holds: the
edges' `data-kind`, `data-from`, and `data-to`; on each concept box
`data-area`, `data-lessons`, and `data-planned`; on each lesson plate of the
views `data-course`, `data-path`, `data-methods`, and `data-difficulty`; and
the concept panels it copies. A change to the generator keeps those
attributes, and the two places the page declares for the script
(`#atlas-controls` and `#atlas-selection`, each with its sentence for a
reader without scripts). The modules store nothing and request nothing;
nothing on the page depends on them.

## Sections

A lesson opens with a short introduction without a heading, followed by
level-2 sections. These are required, and none may be empty:

| Section | Identifier | Content |
|---|---|---|
| Assumptions | `assumptions` | Every assumption of the model and of the program, each with what goes wrong when it does not hold. |
| Explanation | `explanation` | The physics and the method. |
| Code | `code` | The reusable code of the lesson, shown by reference from `src/pbc`. |
| Worked examples | `worked-examples` | Executed examples that compare the result with something known. |
| Exercises | `exercises` | At least one exercise; every exercise has its solution on the page. A lesson with an interactive visualization may have the section `interactive-visualization` instead or as well (see "Widgets"). |
| Run this experiment, Replay this experiment, or Check this proof | `reproduce-this` | The output of `reproduce_this()`, see "The last section" below. Keep it last. |

The header (`lesson_header()`), the last section, and every code or
Lean excerpt (`excerpt`, `lean_excerpt`, `lean_evidence`) name things outside
the lesson: the other lessons and the commit of the build. You write the cells
as shown here; what they leave in the page while it renders is a marker, and the
build replaces it afterwards with the header and the excerpt of the tree and
the commit it builds (ADR 014 decision 9). So a lesson that the build did not
execute again, because nothing it depends on changed, still shows the
navigation and the commit of the current build.

A section is found by its identifier. Pandoc derives the identifier from the
heading text, so `## Worked examples` has the identifier `worked-examples`.
To give a section a title of its own, state the identifier:

```markdown
## From rates of change to an update rule {#explanation}
```

The recommended order is the order of the table. Further sections and
level-3 headings inside a section are allowed.

## Code

Python reaches a page in two ways.

**An executed cell.** The build runs it and shows its code and its output.
Use cells for the story of this one lesson: setting up an example, running
it, printing and plotting results.

````markdown
```{python}
from pbc.mechanics.kinematics import State, simulate

trajectory = simulate(State(t=0.0, x=0.0, v=2.0), lambda t: -1.0, dt=0.25, n_steps=8)
print(f"position after {trajectory.t[-1]:.1f} s: {trajectory.x[-1]:.3f} m")
```
````

- Write the fence exactly as <code>```{python}</code> and put options on
  `#|` lines at the top of the cell (`#| echo: false` hides the code,
  `#| label:` names the cell).
- Put cells at the top level of the page, inside a div (an exercise or a
  solution), or in a list item.
- Variables carry over from cell to cell, top to bottom.

**An excerpt by reference.** Code that is reused, tested, or imported by
learners lives in `src/pbc`. Show it with `excerpt`, which reads the source
file when the page is built and adds the file, the lines, and a link to them
at the built commit:

````markdown
```{python}
#| echo: false
from pbc.authoring import excerpt
from pbc.mechanics import kinematics

excerpt(kinematics.euler_step)
```
````

`excerpt` takes a function or class defined at the top level of a module of
`pbc`. A check compares every excerpt on the built site with the source file.

**An annotated excerpt.** When a lesson shows several excerpts under one
sentence, or the point is one line, say which lines matter:

````markdown
```{python}
#| echo: false
excerpt(
    dynamics.euler_step,
    lines=(8, 12),
    interface=True,
    notes={"x=state.x + state.v * dt,": "The old velocity moves the particle."},
)
```
````

- `lines=(first, last)` shows only those lines of the object, counted from 1
  at its first line. `region="name"` shows the lines between
  `# region: name` and `# endregion: name` in the source. Give one of them,
  not both. A part that does not exist fails the build.
- `notes` maps a line of what is shown, written without its indentation, to
  a note. The line is marked (bold, a rule at its left, and "note 1" after
  it, so it does not depend on colour) and the note is listed under the
  listing as text of the page, with its line number. A note whose line is not
  shown exactly once fails the build, and the site check fails when the
  source changed after the page was built.
- A note holds no digits. Write a number the build computed as `{name}`, with
  `values={"name": value}`, so a note cannot state a number that nothing
  computed.
- `interface=True` adds a table of the inputs and the output from the
  signature. Units come from the docstring, written as ``` ``dt`` (s) ```.
- The text of the notes follows the rule of the lesson: say why each shown
  step implements the physics, then the update order, the state variables,
  the units, and how the step fails. Hide helpers that are not the point with
  `lines` or `region`. Link API documentation only through the reference
  register, and only when it teaches more than the lesson does.

Any other code block is not run by the build: a plain <code>```python</code>
block, a block in another language, shell commands, pasted output, a cell
with `eval: false`. Each needs the "not verified" marker below, or the check
fails. `include` and `embed` shortcodes are not allowed: a lesson is one
page.

## Lean lessons

A lesson in the `lean` strand states and proves a result of the models of
another course. It follows the same format as every other lesson (sections,
header, exercises, the last section); this section covers what is different.

### Write the proof

The proofs live in the Lake project, one module per topic, in
`lean/PhysicsByConstruction/<Course>/<Topic>.lean`. Every file under that
directory is a module of the library, so `lake build` compiles a new file
without a list to extend. Import only the Mathlib files the proof needs; the
Mathlib version is pinned in `lean/lakefile.toml`.

Mark each piece the page will show with a pair of comment lines, and give the
region a name:

```lean
-- ANCHOR: velocity_sq_of_constant_acceleration
theorem velocity_sq_of_constant_acceleration ... := by
  ...
-- ANCHOR_END: velocity_sq_of_constant_acceleration
```

A region holds the declaration with its doc comment. The marker lines are
ordinary comments, so they do not change the proof, and they are not part of
what the page shows.

Two rules decide what a proof may contain.

- **Physical assumptions are hypotheses, not axioms.** What the model assumes
  is a hypothesis of the theorem, or a field of a structure, with a name that
  says what it constrains (`hnewton`, `hx'`). Then the statement on the page
  shows every assumption, and the lesson's "Assumptions" section can name the
  hypothesis that carries each one. The check fails on a `sorry`, on an
  `axiom` declared in the project, and on any declaration that depends on an
  axiom besides Lean's three standard ones, so an assumption cannot be hidden.
- **Proofs are about models, not about the Python code.** A theorem is about
  real numbers and a rule written in Lean. The program computes with
  floating-point numbers. A lesson says which model the theorem is about, shows
  the number the program printed next to what the theorem says, and says what
  the proof does not cover (the code, round-off, anything not stated). It never
  claims that `src/pbc` is verified.

### Show the proof

```` markdown
```{python}
#| echo: false
from pbc.authoring import lean_evidence, lean_excerpt

MODULE = "PhysicsByConstruction.Mechanics.Kinematics"

lean_evidence(MODULE)
```

```{python}
#| echo: false
lean_excerpt(MODULE, "velocity_sq_of_constant_acceleration")
```
````

- `lean_excerpt(module, anchor)` shows the region between the markers. The
  text is read from the file when the page is built; the file and lines
  below the listing link to them at the built commit. The helper refuses a
  file that changed after `scripts/check-lean.sh` compiled it, so the page
  never shows a proof that was not checked. Run `./scripts/check-lean.sh`
  after every change to a Lean file, before a page render or a build.
- `lean_evidence(module, ...)` writes the box that states what compiled the
  proofs: the commit, the versions of Lean and Mathlib, a link to each file
  in the repository at the built commit, and a link that opens it in the Lean
  web editor. It says that the repository file and the CI result are
  authoritative, and that the web editor runs its own version of Mathlib. The
  first view is two lines (the versions and the commit); the rest is in a
  closed `details`. Put it once, at the start of the section that shows the
  proofs.
- The Lean code is coloured when the site is built, with the definition in
  `site/assets/lean.xml`. It colours tokens only; there is no hover or type
  information. If a construct you use is coloured wrongly, extend the
  definition rather than working around it in the lesson.
- `reproduce_this` lists the Lean files among its `code` (as
  `lean/PhysicsByConstruction/...lean`). The commands then include
  `./scripts/check-lean.sh` before the page is rendered.

A code block of Lean that is not an excerpt, such as the shape of a
declaration, is not verified and carries the marker of the section above.

### Lean exercises

An exercise for the learner to complete on their own machine is a pair of
files (ADR 011): the stub `lean/Exercises/<Name>.lean`, whose theorems end in
`sorry`, and the checked solution
`lean/PhysicsByConstruction/Exercises/<Name>.lean`, which states the same
theorems with the same text and proves them. Mark the region of each theorem
with the same `-- ANCHOR: <theorem>` in both files. `./scripts/check-lean.sh`
fails on a stub without a solution, on a differing statement, on a stub
without `sorry`, and on a stub that does not compile.

On a page, show the stub with `lean_stub(name, anchor)` from
`pbc.authoring.exercises`, which marks it "not verified", and the solution with
`lean_excerpt`. Put the hints in `.hint` divs as for any exercise, and list the
solution modules in `lesson.lean-modules`.

## Numbers

Every result on the page is computed by the build.

- Print results from a cell with an explicit format, and say the unit:
  `print(f"{error:.3f} m")`.
- Put a result into a sentence with an inline expression:
  `` `{python} f"{error:.3f}"` `` m. An inline expression does not work
  inside an equation.
- Do not type a result by hand, not in a sentence, a table, a caption, or
  alternative text. Values an example starts from are set in a cell and
  referred to the same way. The given values of an exercise may be typed
  where the exercise is stated.
- Choose the displayed precision deliberately. A reader on another machine
  gets the same digits as the page, and may get different ones beyond them,
  because floating-point libraries differ. Do not display a value at the
  level of round-off; show that it is below a bound instead.
- Fix the seed of anything random, and print nothing that changes between
  builds (times, paths, object addresses). Two builds of the same commit must
  be byte-identical.

### Result tables

A table of numbers is a result table, built by `table()` from a cell and not
printed as a block of fixed-width text. It has

- a caption that says what the table shows and at what precision;
- a header cell for every column, with the unit in it: a column is
  `(name, unit, format)`, where the unit is `""` for a pure number and the
  format is a format specification such as `".3f"` or `"d"`;
- numbers right-aligned, formatted at the stated precision (a `None` cell is
  left empty);
- after it, a sentence that says what the reader should conclude from it.

```python
from pbc.authoring import table

table(
    [(n, duration / n, errors[i]) for i, n in enumerate(step_counts)],
    columns=[("steps", "", "d"), ("time step", "s", ".6f"), ("error", "m", ".6f")],
    caption="Error of the final height for each time step, to six decimals.",
)
```

A table wider than the screen scrolls inside its own focusable box. The
function `is_numeric_console_block` reports a cell whose printed output is a
block of numbers in several lines; the site checks apply it to the built page
of every format 2 lesson.

## Figures

A figure is drawn by an executed cell. Image files are never part of a
lesson.

A lesson with an experiment draws the figure in a `draw_` function of its
experiment and the cell shows it with `result.show(label)` (see "The
experiment of a lesson"); the options of the cell below are the same.

````markdown
```{python}
#| label: fig-ball-thrown-up
#| fig-cap: "Height of the ball: explicit Euler against the exact motion."
#| fig-alt: "Line plot of height against time. The exact motion is a parabola. The explicit Euler points start on it and then lie above it, by a distance that grows with time."
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.plot(trajectory.t, trajectory.x)
ax.set_xlabel("time (s)")
ax.set_ylabel("height (m)")
plt.show()
```
````

- `label` starts with `fig-`; the figure is numbered and can be referred to
  as `@fig-ball-thrown-up`.
- `fig-alt` is required. Describe what the figure shows to a reader who
  cannot see it: the kind of plot, the axes, and what the curves do. Do not
  type computed values into it.
- Set the size with `figsize`; the build writes the width and height into
  the page, so the page does not shift when the image loads.
- Label the axes with units. Do not tell curves apart by colour alone: vary
  the line style or the marker as well.

## The experiment of a lesson

Every number, table, and figure of a lesson comes from its experiment: one
module under `src/pbc/<course>/experiments/`, named after the lesson's `id`
(`kinematics` for `id: kinematics`, `particles_in_a_box` for
`id: particles-in-a-box`), declared in the front matter as
`lesson.experiment`. The page's cells call it, and a reader runs it without
the website (ADR 016):

```bash
uv sync --locked --no-dev
uv run --locked --no-dev python -m pbc.mechanics.experiments.kinematics results
```

writes every figure of the page as `results/<label>.png` and every number
and table cell, as the page shows it, into `results/results.json`. The
experiment needs the project's dependencies only, never the `dev` group.
These are a reader's commands, in a clone of their own. In the checkout you
develop in, leave out `--no-dev`: `uv run --locked python -m
pbc.mechanics.experiments.kinematics results`, because `--no-dev` would
remove the development tools from the environment it runs in.
`pbc.mechanics.experiments.kinematics` is the model to copy; the template
starts from `pbc.mechanics.experiments.lesson_template`.

The module

- imports the lesson's code from `src/pbc` and holds the experiment: the
  values the examples start from, the functions that compute the examples
  and the exercise solutions, and one function per figure that draws it and
  returns the Matplotlib figure (`draw_<what>`);
- defines `run()`, which computes everything and records it in a
  `pbc.experiment.Experiment` by name: `number(name, value, format)` for a
  number in the text, `table(name, rows, columns, caption)` for a result
  table (the columns of `table()`, see "Result tables"), and
  `figure(label, draw)` for a figure, under the `fig-` label of its cell;
- ends with `if __name__ == "__main__": main(run)`.

Three more records cover the other things a page shows:
`with experiment.capture(name):` records what a block prints, which the page
prints with `print(result.output(name), end="")`; `widget(name, data)`
records the JSON data of an interactive figure, which the page passes to
`widget_data` or `widget_asset` as `result.widget(name)` and the program
writes as `<name>.json`; `display(name, shown)` records the Markdown of a
display object, such as the replayed run of an agent lesson, which the page
shows as `result.display(name)`. The experiment of an agent lesson replays
its recording and names its live run as `LIVE`, the module the last section
gives for the run with a model. A figure drawn from a dataset is found by
what its experiment records it with: the lesson checks follow the names in
`experiment.figure(label, ...)` through the module, as they follow the
cells, and ask for `fig-dataset` when they reach a dataset reader.

The page runs it once, in the header cell, and shows what it recorded:

````markdown
```{python}
#| echo: false
from pbc.authoring import excerpt, lesson_header, reproduce_this
from pbc.mechanics.experiments import kinematics as experiment

result = experiment.run()
lesson_header()
```

```{python}
#| echo: false
excerpt(experiment.thrown_ball)
```

```{python}
#| echo: false
result.table("thrown-ball")
```

After `{python} result["end-time"]` s the ball is ...

```{python}
#| label: fig-ball-thrown-up
#| echo: false
#| fig-cap: "..."
#| fig-alt: "..."
result.show("fig-ball-thrown-up")
```
````

Code the reader should read is shown with `excerpt` of the experiment's
function, not typed into a cell, so no computation exists twice. The values
an example starts from are top-level names of the module between
`# region: <name>` and `# endregion: <name>`, shown with
`excerpt(experiment, region="<name>")`. A figure is
encoded once by `pbc.experiment.encode`, with fixed Matplotlib settings
(the defaults, with the figure size and resolution of the page) and no
metadata: the figure file of the built page and the reader's file are the
same bytes. Do not call `plt.show()`, and do not set Matplotlib settings in
the page; set them on the figure in its `draw_` function.

The experiment has a unit test, `tests/unit/test_<name>_experiment.py`: it
runs the command into a temporary directory (`support.experiments`), checks
that it writes every figure the page labels and every name the page reads,
and asserts the lesson's science on the result. The lesson source checks
report a declared experiment that is not at its place, not imported by the
page, or without its test.

## Visual design

The look of the site is one set of tokens and a small set of component styles
in `site/assets/site.css`. A new component uses the tokens; it does not
introduce a colour, a size, or a font of its own.

The design specification, `docs/atelier.md`, says what the look is and why:
the direction, every token and component, the three asset classes, and the
mobile and accessibility rules. This section says how a lesson uses it.

**Tokens.** The `:root` block of `site.css` declares the colours, the faces
(`--pbc-font-text`, STIX Two Text, and `--pbc-font-code`, IBM Plex Mono,
self-hosted under `site/assets/fonts/` with their licences), the type scale
(`--pbc-text-*`, `--pbc-heading-*`), the spacing scale (`--pbc-space-*`),
the measure, the rules, and the focus ring. The colours are defined once, in
`src/pbc/authoring/design.py`; `tests/unit/test_design.py` fails when the
stylesheet differs from the module, when a hex colour is used outside the
`:root` block, and when a pair of text and background has less than 4.5:1
contrast (3:1 for controls and lines). A change to a colour is made in the
module and copied to the stylesheet.

**Figure colours.** A figure takes its colours from the sequence
`pbc.authoring.FIGURE_COLOURS`, so that figures and page agree:

```python
from pbc.authoring import FIGURE_COLOURS

ax.plot(t, x, color=FIGURE_COLOURS[0], label="exact")
ax.plot(t, y, color=FIGURE_COLOURS[1], linestyle="--", label="Euler")
```

Colour never tells two series apart alone; vary the line style or the marker.
Lesson cells also draw axes and annotations in the page's muted grey
(`PAGE["muted"]`), so that colour keeps its value when the page palette
changes: a change to it would change figures and displayed code.

**The reading column.** A lesson reads in the calm column of the specification
when its front matter has the line `body-classes: pbc-reading-column` (a
top-level key; the lesson source checks admit that key with exactly that
value and no other). The prose keeps a measure of about 68 characters, the
lesson header sits on the surface, and equations, listings, figures, tables,
and widgets keep the full width of the main column. Nothing of the lesson's
text or cells changes. "Numerical integrators" uses it; F127 brings it to
every lesson.

**Interface artwork.** The project mark, `site/assets/mark.svg`, is an
authored SVG. Every SVG under `site/assets/` has its entry in the provenance
register, `site/assets/provenance.yaml`: under `assets`, its path relative
to that directory, mapped either to `author`, `licence`, and an optional
`source` (authored) or to `module` (generated by that module at build time).
The lesson source check `test_every_svg_under_site_assets_has_its_provenance`
fails on an SVG there without an entry, an entry without its file, an entry
without an author and a licence or a module, an unknown field, and a module
that does not import. The mark is the navigation bar's `logo` in `site/_quarto.yml`; Quarto writes
it without dimensions, so the post-render step `site/mark.py` adds them.
The committed-artifact check admits a committed SVG
only there and only with an authored entry; a raster, every other image type,
and an image anywhere else stay rejected (ADR 018 decision 2).

**Conceptual diagrams.** A diagram that shows an idea, not a result, is
drawn by an executed cell with the helpers of `pbc.authoring.diagrams`:
`canvas` (or `frame`, for a figure of several panels) makes a frameless
axes in data units, and `arrow`, `state_box`, `circle`, `line`, and `text`
draw on it with the figure colours. The cell has `#| fig-status: conceptual`,
alt text that conveys the insight, and a caption that states it. The diagram
is a sketch: the sentence after it says so and says what question it
answers. Nothing is stored as an image file.

**Components.** `rendering-check.qmd` holds one sample of each; copy its markup.

| Component | Markup |
|---|---|
| What you'll learn, assumptions | `.learn-box`, `.assumptions` div with a bold first line and a list |
| Claim label | `[text]{.claim data-type="observational"}` (span) or a `.claim` div; the four types of `pbc.authoring.CLAIM_TYPES` |
| Figure status | `[simulated]{.figure-status data-status="simulated"}` at the start of the caption; the five statuses of `FIGURE_STATUSES` |
| Result table | The markup of `pbc.authoring.table`: `div.table-scroll` with `tabindex="0"`, `role="region"`, and an `aria-label`, around a `table.result-table` with a `caption`; numeric cells carry `.num` |
| Annotated excerpt | `.annotated-excerpt` div: the listing, then an ordered list of notes |
| Go deeper | `.go-deeper` div |
| Self-check and hint | `.exercise.self-check` div; a hint is a `.hint` div in an exercise, rendered as `details.hint`; the choices of a self-check are `ol.choices` of `li.choice[data-correct]`, inside `#self-check-controls` |
| Lesson rows | Generated by `pbc.authoring.path` on the path page: `ol.path-rows` of `li.path-card` (thumbnail, title, question, level badge, chips, and a nested `details.lesson-details`) and `li.planned-slot` for a slot no lesson fills; method and path views are `ol.path-links` of `li.path-link`, one link per lesson |
| Prerequisite graph | Generated by `pbc.authoring.graph` on the path page, not written by hand: `.prerequisite-graph` with `tabindex="0"`, `role="region"`, and an `aria-label`, around an SVG with no `role="img"` |
| Footer attribution | `.footer-attribution` paragraph (filled by F57) |

A label is always words in the page; its colour only supports it. A box that
scrolls sideways is focusable, so that the keyboard can scroll it.

**Header, footer, skip link, and focus.** The header and the footer of every
page are Quarto's navigation bar and page footer, configured in
`site/_quarto.yml` and restyled by `site.css`: the mark and the title, the
primary navigation, and the start link "Start the course" (its class
`pbc-start` comes from the Markdown of its text, since Quarto's navbar items
take no class; `tests/unit/test_site_chrome.py` keeps it pointed at the first
lesson of the learning path); the footer holds the attribution, the licences,
the source, and the secondary navigation. `site/skip-link.py` runs after the
render and puts a skip link before the navigation bar of every page. The
header takes the page's cobalt focus ring, which the built-site check `test_skip_link_and_navigation_focus_pass_the_keyboard_pass`
measures. Browsers other than Chromium: run `pytest tests/e2e --engine firefox`
(WebKit on macOS does not Tab to links, so the keyboard checks do not apply).

**Search.** `site/_quarto.yml` enables Quarto's own search with its local
index: the build writes `search.json` into the site, and the page script
fetches it from the site's own origin. It needs JavaScript. `site/search-fallback.py`
runs after the render and puts a link to the learning path, inside `noscript`,
in the place of the search control, so a reader without scripts finds lessons
there. The search box takes the page's focus ring (`site/assets/site.css`). The
built-site checks `test_search_*` run a query in a browser and fail on a request
to another origin, a cookie, or a write to browser storage.

**Payload.** Every page, opened on its own, loads at most 3 MB (`test_every_page_loads_within_the_payload_budget`
prints the sizes; run it with `-s`).

## Visual deliverables and skills

A feature that produces a page or layout, a conceptual diagram, a scientific
figure, or an animation uses the agent skills of `.agents/skills/` that its
plan selects (ADR 019; the README there lists the set and when each is
required). The rules of this document, `docs/validation-contract.md`, and
the checks come first: a skill supplements them and never overrides them,
and following a skill is no evidence that a figure or a page is correct.

- **The plan** classifies each new visual deliverable, names the skills on a
  line `Skills: <name>[@<revision>], ...` or says `Skills: none (<reason>)`,
  and states the expected artifact, how its science is validated, and its
  accessible fallback (alt text, a static equivalent of anything that moves).
- **The work** reads `.agents/skills/<name>/SKILL.md` of each selected skill
  before drawing or styling; the completion evidence names the skill and its
  revision beside the figure cell or page it shaped and that artifact's
  source, and explains any deliberate exception.
- **The review** looks at the rendered page at desktop and phone width, or at
  the generated figure and the code and data behind it, checks the physics
  against independent computations and tests, and checks that the guidance
  was followed.

A scientific figure follows the PBC Scientific Visualization skill (the
choice of visual, axes and units, uncertainty, captions, accessible
encodings, reproducible generation, and no invented result); a conceptual
diagram also follows Diagram Design. Nothing is imposed on an existing
lesson that a feature does not change. The skills configuration check
(`skills-config`) fails when a selected skill is missing or at another
revision.

## Not verified

Material that the build neither ran nor checked must say so. Wrap a block in
a div with the class `not-verified`, or a phrase in a span:

````markdown
::: {.not-verified}
```python
state = step(state)  # a sketch that is not executed
```
:::

The measured value is [9.81 m/s² in Delft]{.not-verified}.
````

The page then shows the label "Not verified" on the block, or "(not
verified)" after the phrase. Use it for pseudocode, for code in another
language, for shell commands, and for results quoted from elsewhere or
computed outside the build. Prefer executing the code or computing the value;
the marker is for what cannot be.

## Lesson format 2

A lesson that declares `format: 2` under `lesson` keeps every section of
format 1 and adds the parts below. **Migration rule:** format 1 lessons keep
passing unchanged; each editorial pass migrates its lessons to format 2, and
the default flips to 2 when no format 1 lesson remains. Start from
`docs/lesson-template.qmd`, which is in format 2.

Depth follows difficulty, not word count: a short lesson has short parts, and
a part that has nothing to say is a sign that the lesson does not need it, not
a place to pad.

| Part | How to write it | Checked |
|---|---|---|
| Physical question | The opening paragraphs, before any equation or code: the problem the lesson answers and where it appears. | by review |
| What you'll learn | Comes from `lesson.outcomes`; the header cell renders it. | front matter |
| Interpretation | After every figure and table, a sentence that says what it means, where its data came from, and what it was checked against. Captions state the conclusion, not only the content. | by review |
| Limits | A level-2 section `## Limits {#limits}`: what the result does not show, where the model or the method fails, what was not measured or proved. One paragraph or a short list. | present, non-empty |
| Self-check | Exactly one `::: {.exercise .self-check}` div with a `.solution`: one conceptual question, distinct from the exercises, placed after the limits so that it closes the explanation. It is titled "Self-check." and has no number, so the exercises keep theirs. | exactly one, with a solution |
| Go deeper | Optional `::: {.go-deeper ref="key"}` div: the text inside is the reason to visit, the link comes from the register (see "References"). | key exists |
| Claim labels | `[text]{.claim type="..." scope="..." evidence="..."}` | type in the vocabulary |
| Figure status | `#| fig-status: simulated` in every figure cell | value in the vocabulary |

### Claim labels

Label each statement that a reader could take for a scientific result. The
build prints the type in words before the statement, so the label reads
without styles and without scripts. `scope` is optional and says under what
conditions the claim holds. `evidence` is required: it names what supports the
claim, as one or more words separated by spaces or commas. Each word is one of

- the label of an executed cell of the same lesson (`#| label: ..`); give the
  cell that produces the table or figure the claim rests on a label of its own,
  and make it unique on the page, also against the heading identifiers;
- a key of the reference register or the name of a dataset card
  (`data/registry/<name>.yaml`);
- the name of a Lean theorem of `lean/PhysicsByConstruction`;
- `replay` or `replay-<agent>`, the recorded run of an agent lesson.

The lesson source checks fail a claim without `evidence` and a word that names
none of these ("the table above" names nothing). The evidence map
(`site/evidence.qmd`) lists every claim with its type, scope, lesson, and
links to its evidence, and fails the build on the same grounds. The build
gives each claim the identifier `claim-N`, N counting the claims of the page
from 1. Use a div (`::: {.claim type="..."}`) for a claim of several
paragraphs.

```markdown
[The position error of explicit Euler for a constant acceleration is exactly
$-\tfrac12 a t_n \Delta t$.]{.claim type="numerically-verified"
scope="constant acceleration" evidence="fig-ball-thrown-up"}
```

The type follows the evidence behind the claim, not the strand of the lesson
(invariant I21):

| Type | Use it when |
|---|---|
| `observational` | The statement says what a measurement or observation shows, or quotes a published measured value with its source. No model is needed to state it. |
| `experimentally-supported` | The statement is an inference from measured data through a stated model, with its uncertainty. The data and the model are both shown, and the claim is about the measured system. |
| `numerically-verified` | The statement is the result of a computation that the build runs again, about the model that was computed. An agent's conclusion from simulated runs has this type where the build recomputes it, and is not a claim where it does not. |
| `formal-theorem` | The statement is a Lean theorem about a model, with its hypotheses as the scope. It proves nothing about a measurement. |

### Figure status

Every figure cell has `#| fig-status:` with one of `measured`, `calibrated`,
`processed`, `simulated`, or `conceptual`. The build puts the status, as a
coloured word, at the start of the caption. The alt text describes the shape of the figure; leave
computed values to the table and the prose.

### Lesson preview

Every lesson has one small preview, which the learning path shows beside the
lesson. It is never an image file: the build makes it.

- Name the figure cell that represents the lesson in the front matter,
  `lesson.preview: fig-oscillator-phase-space`. Choose the figure a reader
  would recognise the lesson by (a trajectory, a phase curve, a
  measured-versus-model panel, a transcript figure, a proof diagram), not
  necessarily the first one: the first is often a conceptual setup sketch.
  The cell needs a `fig-status` and a `fig-alt`, as every figure does.
- After the render, `site/lesson-previews.py` scales the figure that this
  cell drew to 320 by 200 pixels, on a white canvas, and writes it to
  `previews/<lesson id>.png` of the built site. Nothing is cropped by hand,
  and two builds give the same bytes. The alt text in `path.json` is the alt
  text of the figure, started by `Preview, <status>:`, so the status travels
  with the picture.
- A lesson without `lesson.preview` gets a conceptual card in
  `previews/<lesson id>.svg`, drawn by code from its course and its methods,
  with the status `conceptual`. It shows no result. Declaring `preview` is
  optional, but every published lesson declares one.
- A `preview` that names no figure cell of the page, or a cell without a
  status or alt text, fails the lesson checks; a named cell that drew no
  figure fails the build. The built-site check requires one preview per
  lesson, traced to its cell or to the fallback, and the previews together
  fit in the payload budget of the learning path page: 4.5 MB for the page
  with its previews, temporary, to be reduced (owner's decision of
  2026-10-28, Issue #318: the page with its previews measured 4,022,544
  bytes at 75 lessons; 4 MB from Issue #264, 3 MB before that), while every
  other page keeps 3 MB.

### Numbers in prose

In a format 2 lesson a number that the program computed reaches the prose
through an inline expression, like everywhere else (see "Numbers"). The check
reports a word with a digit in the prose, and a decimal or multi-digit number
in the alt text or caption of a figure, unless it is

- inside math or inline code, a heading, or material marked "not verified";
- in the statement of an exercise (not in its solution): the given values of
  the problem;
- marked as a given value in the prose: `[0.1 s]{.given}`.

A method or a symbol whose name holds a digit (Runge-Kutta 4, `RK45`) counts
as a number in prose. Write the name without the digit ("the classical
Runge-Kutta method", "the fourth-order method"), put the exact identifier in
code font, or mark it `{.given}`; in a table cell, a caption, or math the name
is free. (A finding of the M5 editorial pass, F30.)

A unit with an exponent (`yr²/AU³`, `m/s²`) counts as a number in prose too.
Write it in math (`$\mathrm{yr}^2/\mathrm{AU}^3$`), where it is free. A
quantity that is at the level of round-off is not shown as a number: a table
cell says "below 1e-12", built from a stated bound with a small helper in the
cell, so that the page never prints a digit that another machine would change.
(Findings of the M8 editorial pass, F30.)

The check is a heuristic. Write small whole numbers that are not results as
words ("first order", "slope one") and mark a number you really give as
`{.given}`; do not rewrite a correct sentence to please it.

### Result tables and printed output

A cell of a format 2 lesson does not print a block of numbers: the built page
is checked with `is_numeric_console_block`, and a result goes through
`table()` (see "Result tables").

## References

External links are optional depth paths. The core explanation, the
derivation, the worked example, the interpretation, and the principal
exercise stay on the page: a reader with the prerequisites completes the
lesson without following any link. A link never replaces a missing
explanation (ADR 009).

A lesson links only through the register `site/references.yaml`. A raw URL
anywhere in the source of a format 2 lesson fails the check. The links that
helpers generate (the repository file behind an excerpt, the Lean web editor
link of a proof) are not references and are exempt. In the lesson, write

```markdown
::: {.go-deeper ref="euler-local-global-error"}
Why the sum of the local errors still gives a first-order global error. The
lesson does not need it.
:::
```

The block shows the title as a link, the author or publisher, the section, and
the role of the source, then your reason to visit. Write the reason as what
the reader gains, not "click here". At most two blocks per lesson, no adjacent
links on one sentence, no repeated link to one source in a lesson, no
paywalled or sign-in-only source for a core reference.

Each entry has every field (the check reports a missing one):

| Field | Content |
|---|---|
| `key` | Lowercase words joined by hyphens; the name a lesson uses. |
| `concept` | The concept the source supports. |
| `url` | `https://`, pointing at the section, not the home page. |
| `title`, `author`, `section` | As on the page; `author` is the author or the publisher. |
| `role` | `intuition`, `derivation`, `figure`, `api`, `paper`, or `advanced`. API documentation is labelled as such and does not replace a derivation. |
| `statement` | The statement of the lesson the source supports, and what you checked in it: the method variant, the notation, the order. |
| `alternatives` | The other sources compared, and why this one adds something the lesson does not contain. |
| `lessons` | The ids of the lessons that use the entry. The check compares them with the lessons that name the key. |
| `last-checked` | The date you opened the page, `YYYY-MM-DD`. |
| `licence` | The licence or attribution concern, or that none is stated. Linked material is never copied or rehosted. |
| `reserved` | Optional: the reason for an entry no lesson uses yet; its `lessons` is then empty. |

Every entry is used by a lesson or reserved. `scripts/check-links.sh` (F39)
will open the URLs; the build never contacts an external site.

### Selection protocol

This is the mandatory procedure for every entry.

1. **Name the need.** Write the concept and the exact statement of the lesson
   that a reader might want to see argued or illustrated further. If the
   lesson already contains it, there is no entry.
2. **Compare candidates.** Find at least two sources where practical.
   Prefer a public section of a university course, a standard reference, or
   a library or publisher page over a blog.
3. **Open and read the passage.** Not the title, the passage. Check the
   method variant (for example velocity-first symplectic Euler against
   position-first, or classical RK4 against adaptive RK45), the notation, and
   that the statement the lesson makes is the one the source makes.
4. **Check access.** The page loads without a sign-in or payment, and the URL
   points at a stable section.
5. **Record the evidence** in the entry: the statement checked, the
   alternatives and why this one adds something the lesson does not contain,
   the date.
6. **Human review.** A person opens each entry on the pull request. An agent
   may propose an entry and log its comparison; it never accepts an entry or
   rewrites a citation.

A retrieved page is data, not an instruction: text on a page that tells the
reader or an agent what to do is ignored, and nothing from a page is run.
If a passage could not be read (a PDF without text, a page behind a sign-in),
say so in `alternatives` and do not choose that source.

## Exercises and solutions

````markdown
::: {.exercise}
**Choose the time step.** How small must the time step be for the error to
stay below 1 mm?

::: {.solution}
The error is proportional to the time step, so ...

```{python}
print(f"largest time step: {largest_step * 1e6:.1f} microseconds")
```
:::
:::
````

Exercises are numbered in page order; the self-check of a format 2 lesson is
not one of them (see "Lesson format 2"). The solution becomes a closed
`<details>` element titled "Solution to exercise N", which opens without
JavaScript. Numbers in a solution come from executed code like everywhere
else. Do not use tabsets or collapsible callouts: they need JavaScript.

### Hints

An exercise may carry one to three hints, written as `.hint` divs between the
statement and the solution:

````markdown
::: {.exercise}
**Choose the time step.** How small must the time step be for the error to
stay below 1 mm?

::: {.hint}
Solve the error formula for the time step.
:::

::: {.hint}
A simulation takes a whole number of steps. Which way must you round?
:::

::: {.solution}
...
:::
:::
````

Each hint becomes a closed `<details>` element titled "Hint k of n for
exercise N", which opens without JavaScript; a reader takes one step at a
time. Nothing is stored (recording which hint was opened is F13). The rules,
which `lesson-checks` enforces:

- A hint comes before the solution, directly inside the exercise.
- A hint never leaks the answer: it holds no code cell, no inline
  expression, and no number except one that the statement of the exercise
  already gives. A computed number belongs in the solution, where a cell
  produces it.
- A hint is not a "Go deeper" block. A hint points at the next step of this
  exercise, in a sentence or two; "Go deeper" sends the reader to outside
  reading and cannot be inside a hint.
- A self-check may carry hints in the same way. Recording which hint was
  opened is not part of the stored state (see "Self-checks and progress").

## Self-checks and progress

The self-check of a format 2 lesson (`.exercise.self-check`) can be answered
in the page, and the site can remember in the reader's browser which lessons
they completed. Nothing is sent anywhere and no cookie is set (invariant I16).

**Choices.** A self-check may hold a `.choices` div between the question and
the solution: two or more `.choice` divs, exactly one with `correct="true"`,
each with a `.feedback` div that says why the option is right or wrong.
Without a script the choices are a list with the explanation of each, and the
solution opens as in any exercise; with the script the choices become radio
buttons, and "Check answer" shows the feedback of the chosen one.

```
::: {.exercise .self-check}
The question.

::: {.choices}
::: {.choice}
A wrong option.

::: {.feedback}
Why it is wrong.
:::
:::

::: {.choice correct="true"}
The right option.

::: {.feedback}
Why it is right.
:::
:::
:::

::: {.solution}
The answer, as for any exercise.
:::
:::
```

Write each feedback so that it reads without the others: a reader without
scripts sees all of them. A self-check without choices stays a question with a
solution; with scripts the reader can mark it as done. `lesson-checks` reports
choices outside a self-check, fewer than two, a number of correct choices
other than one, a choice without feedback, and choices after the solution.

**What is stored.** `site/learner/progress.js`, loaded by the header cell of
every lesson and by the learning path page, keeps one record in local storage
under the key `physics-by-construction:learner-state`:
`{"version": 1, "lessons": {"<lesson id>": {"completed": true, "selfCheck":
{"done": true, "attempts": 2}}}}`, keyed by the stable lesson ids. It is
written only when the reader acts: answering a self-check, marking a lesson, or
clearing. The learning path page explains this in the section "Your progress"
and has the clear-data control, which removes the record.

**Changing the format.** Raise `VERSION` in the script and add to `MIGRATIONS`
the function that turns the previous version into the new one. Data of a
version that has no migration, and data that does not have the shape of the
current version, is discarded and removed: the reader loses their progress, the
page keeps working. The built-site tests seed older, newer, and malformed data.

**The learning path in data.** The build writes `path.json` at the root of the
site: lesson ids with title, page, strand, order, course, slot, path and position (null without a slot or outside a method path), methods, difficulty,
prerequisites, and related lessons (`pbc.authoring.progress.path_export`).
It holds nothing about a learner. The learner-state script does not fetch it;
later client-side features can.

**Rules for the script.** It is the only script of the site that uses browser
storage, and it lives in `site/learner/`, not in `site/widgets/`, whose scripts
may not store anything. It contains no request, no other origin, and no storage
but local storage. What it adds to a page sits in a `data-enhancement` element
that the page has without it (`#learner-panel`, `#self-check-controls`,
`#progress-controls`, `#recommendations`), so that nothing required depends on
scripts.

### Recommendations

The learning path and every lesson page suggest what to do next, with the
reason of each suggestion. The rules are in `site/learner/recommend.js`, a pure
module that reads no storage and no page; `progress.js` shows its result in
`#recommendations`. The rules use only the prerequisite graph and the stored
results, which the page carries as data (`pbc.authoring.progress.progress_markup`
puts the lessons, with links relative to the page, in the JSON element), so that
computing them makes no request. With no stored result there is no suggestion
and the page is the plain learning path.

In rank order, a lesson gets the first rule that applies, and at most three
suggestions are shown, ties in the order of the path:

1. **prerequisite**: the reader completed a lesson that builds on this lesson,
   which is not completed.
2. **retry**: the reader checked an answer to its self-check and has not got it
   right.
3. **next**: the lesson is not completed and all its prerequisites are.

The reader can ignore a suggestion. The record then holds an optional
`"ignored": ["<lesson id>"]` (still version 1: absent means none), and the
button "Show ignored suggestions again" removes it; the clear-data control
removes it with the rest. A new rule is a new entry of `RULES` with a test in
`tests/e2e/test_recommendations.py`. Whether the suggestions are useful cannot
be shown by those tests; judge it by following the path as a learner.

## Widgets

A widget is an interactive visualization that enhances a figure the page
already has. Use one only where changing a parameter teaches something a
fixed figure does not; most lessons need none. The lesson "Numerical
integrators" has the first one, the integrator explorer, in its section
`interactive-visualization`; copy its structure.

**The rules**

- The page is complete without the widget. The static figure, its caption,
  and the numbers (a printed table) are in the page; a reader without
  JavaScript loses nothing.
- A widget is one dependency-free ES module in `site/widgets/`, loaded by a
  relative URL. No package manager, bundler, or third-party code. It makes no
  request (except the one load of its own on-demand data, see "On-demand
  data"), loads nothing from another origin, and writes no cookie and
  nothing to browser storage. It does not animate, so the preference for
  reduced motion is respected by construction; if a widget ever animates,
  it must stop when `prefers-reduced-motion: reduce` matches.
- **No physics in the widget.** A widget draws results; it does not compute
  them. The numbers come from an executed cell that calls the tested code in
  `src/pbc` when the page is built, and they are embedded in the page. A
  widget that has to compute in the browser needs a test that compares its
  results with `pbc` reference values; the Issue that adds it states the
  tolerance.
- The controls are native elements (radio buttons, sliders, selects,
  buttons) with visible labels, so that the keyboard, focus, and assistive
  technology work as on any form. The drawing has `role="img"`, an
  `aria-label`, and an `aria-describedby` pointing at text in the page that
  states the numbers.
- The page does not move when the widget loads. The script replaces the
  `<img>` of the figure by a drawing that takes the image's box (its width
  and height attributes, its class, and its aspect ratio) and fills a slot
  whose height the stylesheet reserves at every width the site supports.

**The markup**

````markdown
::: {#integrator-explorer data-widget="integrator-explorer" data-enhancement=""}
```{python}
#| label: fig-integrator-explorer
#| fig-cap: "..."
#| fig-alt: "..."
... the static figure, drawn from the same data the widget gets ...
```

::: {.widget-controls}
One or two sentences for the reader without JavaScript.
:::
:::
````

- `id` names the widget; the data element is `<id>-data`. `data-widget` is
  the name the module looks for. `data-enhancement` declares what a script
  may add: the built-site checks accept content that appears only with
  scripts inside this element, and nowhere else. The element must hold static
  content (the figure) in the page.
- Embed the data and load the module in two cells with `#| echo: false`,
  after the figure:

  ````markdown
  ```{python}
  #| echo: false
  from pbc.authoring import widget_data, widget_module

  widget_data("integrator-explorer", explorer)
  ```

  ```{python}
  #| echo: false
  widget_module("integrator-explorer.js")
  ```
  ````

  `widget_data` writes the data as JSON that no script runs; `widget_module`
  writes the script tag with a URL relative to the page. The module is
  listed under `resources` in `site/_quarto.yml` (the pattern `widgets/*.js`
  covers a new one).
- Name the module, `pbc.authoring.widgets`, and the code that computes the
  data under `code` in `reproduce_this()`.

**What the checks do**

| Check | Reports |
|---|---|
| `site-checks` | A script in `widgets/` that contains a request, another origin, or a use of browser storage; a widget that, with its controls operated by keyboard, writes a cookie or anything to Web Storage, IndexedDB, the Cache API, or a service worker; content that appears only with scripts outside a `data-enhancement` element; the accessibility scan of the page; and the widget-specific tests in `tests/e2e/test_widgets.py` (fallback, keyboard operation, values against `pbc`, layout shift, reduced motion). |

### On-demand data

A component whose data is too large to embed (a series for many parameter
values, the frames of a field) loads it after the reader asks for it. The
first such component is the waveform comparator of the gravitational-wave
strain lab, `site/widgets/waveform-comparator.js`: a measured series against
model profiles (here, the chirp for a range of chirp masses) with the error
metrics of each, a slider, and the displayed values as text.

- A cell writes the file with `widget_asset(name, data)` from
  `pbc.authoring`; it returns the URL relative to the page, and the file is
  published beside the page (`index_files/figure-html/<name>.json`: Quarto
  publishes that directory with the page, also when the page is rendered alone). The data is computed by `src/pbc`
  (for the comparator, `pbc.data.comparison.waveform_comparison`), never by
  the widget.
- The element of the widget names the file in `data-ondemand` (space-separated
  relative addresses). Until the reader presses a button inside that element,
  the widget requests nothing; the static figure stays and the controls slot
  holds one sentence and the button. A failed load leaves the figure and says
  so.
- Budget: 3 MB per page on demand, from the site's own origin, and 5 MB for
  everything the page can load with the initial payload.
- A component never alters a claimed observed value: it draws and lists the
  numbers of the file as they are (no smoothing, resampling, or rounding of
  its own), and a test shows that the drawn points are an affine map of the
  embedded values and that the text export equals them.
- Every state a component can show has the static figure as its keyframe, and
  nothing animates.
- One component per lab that needs it. A new component copies the pattern and
  adds its tests in `tests/e2e/`, as `tests/e2e/test_comparator.py` does.

| Check | Reports |
|---|---|
| `site-checks` | An on-demand file that is missing from the built site, is not a relative address, or whose page loads more than 3 MB (5 MB with the initial payload); a page that requests its on-demand data before an action, has no button (`data-loads-ondemand`) that asks for it, or whose button loads nothing or reaches another origin (`check_ondemand_budget`, `check_ondemand_loads_after_action`, run in `tests/e2e/test_comparator.py`). |

When you add a widget, add the tests for it to `tests/e2e/test_widgets.py`
the way the explorer's are written: displayed values against a fresh run of
`src/pbc` with a stated tolerance, the keyboard path through every control,
and the fallback with scripts off.

## The last section

The last section names what a reader does with the lesson on their own
machine, and keeps the identifier `reproduce-this`, which every link to it
uses. Its heading depends on the methods of the lesson (ADR 016 decision 3):
"Run this experiment" for a simulation or a lesson of measured data,
"Replay this experiment" for an agent lesson, and "Check this proof" for a
lesson whose methods are `[lean]` only. The section is one cell:

````markdown
## Run this experiment {#reproduce-this}

```{python}
#| echo: false
reproduce_this(
    code=[
        "src/pbc/mechanics/kinematics.py",
        "src/pbc/mechanics/experiments/kinematics.py",
        "src/pbc/experiment.py",
    ],
    tests=[
        "tests/unit/test_kinematics.py",
        "tests/unit/test_kinematics_experiment.py",
    ],
)
```
````

`code` names the modules the page imports and `tests` the tests of those
modules, relative to the repository root. The cell writes the commit the page
was built from, links to the files at that commit, and the commands from a
clone to the experiment: check out the commit, install the project's
packages (`uv sync --locked --no-dev`), and run the experiment the front
matter declares. A Lean lesson adds `lake build` of the modules it shows; an
agent lesson adds the live run as a separate block marked "not verified",
which names its key and the optional dependency `openai`, and its experiment
module names that run as `LIVE`. No command of the section renders or
previews the website. A build from a checkout with uncommitted changes says
so on the page. The lesson source checks require the heading of the kind of
the lesson, and a check of the built site runs the experiment of every lesson
with these commands and compares its figure files, byte for byte, and its
numbers, at the precision the page shows them, with the published page.

## Equations

Write equations in LaTeX between `$...$` or `$$...$$`. They are converted to
MathML when the site is built, and the build fails on an equation that
cannot be converted. Stay with standard LaTeX and `amsmath` constructs such
as `aligned`, `\frac`, `\sum`, and `pmatrix`; do not define macros.
`site/rendering-check.qmd` shows constructs that are known to work.

## Agent lessons

A lesson in the `agents-llm` strand shows an LLM agent running an experiment
(ADR 004). The page never calls a model. It replays a recording, and the build
recomputes every tool result. The first such lesson,
`site/lessons/agents-llm/01-an-agent-runs-an-experiment/index.qmd`, is the
example to copy.

What a lesson of this kind has:

- **An experiment module** in `src/pbc/agents/`, like `projectile_lab.py`: the
  system prompt, the task, the step limit, the tolerance, the allowlist, and a
  `main()` that runs it live. The allowlist wraps functions of `src/pbc` with
  bounded numeric parameters (`pbc.agents.tools`). Choose the bounds to limit
  the cost of one call as well as what it may touch.
- **A plain statement on the page** of what the agent may and may not do
  (`AllowlistDisplay` renders the table), what a learner should expect to
  differ in a live run, and how to keep keys: in an environment variable of
  the shell, never in code, notebooks, or committed files. The live commands
  go in a `.not-verified` block.
- **A replay fixture**, `replay.json` next to `index.qmd` (see "What is
  committed"). The page replays it with `replay_fixture()` and shows it with
  `RunDisplay`, which labels the model messages as recorded, with the model
  and the date, and shows the recomputed tool results only.
- **Tests** of the experiment's allowlist in `tests/unit`. The harness tests
  of the boundary already cover every allowlist.

Never put a credential in the lesson, the fixture, or a test. The harness
removes the client's key from every model message before it is kept, printed,
or saved, but the fixture is reviewed before it is committed. A fixture
flagged `"placeholder": true` (written by hand, not recorded) may stand in
while a lesson is developed; a check refuses it in the published lesson.

### Re-record a transcript

Re-record when the replay fails because a recomputed result differs from the
recorded one beyond the tolerance, or because the task, the system prompt, or
the allowlist changed. The failure message says so.

1. Check that the change of the simulation is intended.
2. Install the optional provider package and export your key in the shell,
   not in a file:

   ```bash
   uv sync --extra openai
   export OPENAI_API_KEY="..."
   ```

3. Run the agent and record it over the fixture:

   ```bash
   uv run --extra openai python -m pbc.agents.projectile_lab --record
   ```

4. Read `replay.json`. Check that it holds no credential, that the model and
   the date are right, and that the agent's conclusion is correct. The page
   shows the model's words as they are.
5. Run `./scripts/verify.sh --targeted` (the agent lesson is a selected
   lesson, and its page renders alone), then commit the file.

### Counterexample hunts

A hunt (`pbc.agents.hunter`, lesson `agents-llm/02-a-counterexample-hunter`)
puts a **falsifiable claim** to the agent: a statement, a domain (fixed
choices and bounded numbers), a predicate on one number the tool returns (at
most a limit), and a budget of experiments. The allowlist counts the calls that
pass validation (`Allowlist(..., budget=n)`) and refuses the ones beyond it.

The verdict is computed by `judge`, never read from the agent's text or from
the results stored in the fixture. It runs each accepted experiment inside the
domain again and evaluates the predicate on the new value:

- a recomputed value that breaks the predicate is a **counterexample**, and
  `VerdictDisplay` prints it as a claim of type `numerically-verified`, scoped to
  that experiment, with the recomputed numbers;
- otherwise the outcome is **inconclusive**: the page labels it so, gives it no
  claim type, and does not say that the claim is true.

A lesson with several runs names each fixture `replay-<name>.json`
next to `index.qmd`, and replays each with its own task. Re-record one with
`--claim <name> --record` of the experiment module
(`python -m pbc.agents.hunter_lab`). Choose the limit of a claim and the
tolerance of the replay before you record, and never change a limit to
obtain a verdict. Messages written by an author or an assistant, not produced
by a model through a provider API, are authored examples: the page passes
`authored=True` to `RunDisplay` and never calls them recorded.

The experimental design lesson (F20, `pbc.agents.design`, re-recorded with
`python -m pbc.agents.design_lab --rig <name> --record`) puts two models to an
agent that chooses where to measure. The build recomputes each reading from the
arguments, scores the design from them alone, and fits both models. The
statement that one model is favoured is typed `numerically-verified`, scoped to
the readings, only when one model fits within the noise and the other is worse
by the threshold fixed before the run; otherwise the outcome is inconclusive,
has no claim type, and is never "the models are equal".

To use another provider, write one client module that reads its own key
variable and change `PROVIDER` in `src/pbc/agents/providers.py`; the lesson
page explains it. Only that provider's key is needed then.

## Discovery lessons

A lesson of the law-discovery or agent-benchmark paths uses `pbc.discovery`; it
does not build its own environment, baselines, or scoring. The rules are in
`docs/discovery-protocol.md`, the Discovery evaluation protocol.

- **Environment and tools.** Use an environment of `pbc.discovery` (or add one
  there, with its tests) and its `environment_allowlist`. Show the allowlist
  with `AllowlistDisplay`, and say that the law, its parameters, and the
  held-out settings are hidden from the agent. Never print them on the page.
- **Condition and prompt.** State the condition of prior knowledge (`full`,
  `partial`, `none`) and take the prompt from `pbc.discovery.prompts`.
- **Frozen trace.** Commit the replay fixture next to `index.qmd`:
  `replay.json`, or `replay-<condition>.json` for a lesson with several runs.
  A lesson directory holds nothing else (ADR 002; "What is committed"), so the
  record that versions the run, the `TraceInfo` with the protocol, the
  condition, the seed, the prompt version and SHA-256, the model, the date,
  and the cost, lives in the lesson's module beside the protocol, and a test
  checks it against the fixture. `save_trace` writes both files for a
  benchmark kept outside `site/`. Replay the fixture with `replay()` as in
  "Agent lessons", in the lesson's experiment (see "The experiment of a
  lesson"), whose `LIVE` names the live run with its arguments, and label the
  model's messages as recorded, with the model and the date. The lessons D1
  to D3 (`site/lessons/agents-llm/05-discovering-a-force-law/index.qmd` and
  the two after it, module `pbc.discovery.force_lab`, experiment
  `pbc.mechanics.experiments.black_box_force_law` and the two beside it) are
  the example to copy. A lesson whose claim is not the parameters of a
  law adds its own box and tools in `pbc.discovery` and its own score, as D13
  does for conserved quantities
  (`site/lessons/agents-llm/11-discovering-conservation-laws/index.qmd`,
  modules `pbc.discovery.invariants` and `pbc.discovery.invariant_lab`;
  `docs/discovery-protocol.md`, "Invariants").
- **Without an agent.** A discovery lesson that uses no model (methods
  `[simulation]`, no `llm-agents`) has no fixture, no prompt, and no live
  run; its last section is "Run this experiment". It still states the
  grammar or library it searches, fixes its tolerance, threshold, and seeds
  in its experiment before any result is read, tests what it finds on
  held-out cases, shows when the data admit several answers, and reports a
  failure as a result. The lessons D7 and D8
  (`site/lessons/agents-llm/08-symbolic-regression/index.qmd` and the two
  after it, modules `pbc.discovery.symbolic` and `pbc.discovery.equations`)
  are the example to copy.
- **Recomputed score and baselines.** Show the held-out error from
  `score_transcript` and the table of `comparison` with `run_baselines`, failures
  included. State a claim about a law only as far as that evidence supports it.
- **Benchmarks and comparisons.** A lesson that compares runs or methods
  (the agent-benchmark path) lays them out on `pbc.discovery.benchmark`: one
  protocol per environment, its grid of conditions, the plain model as the
  control without probes, and the baselines with the same budget. Every score
  set beside another carries the verdict of `comparable`, and the page says
  what a comparison marked "not meaningful" measures instead; it never ranks
  conditions or methods from one run per cell. The lessons EV2 and EV3
  (`site/lessons/agents-llm/12-interactive-discovery-benchmarks/index.qmd` and
  the one after it) are the example to copy; EV2 replays the fixtures of D1
  and D2 from their pages through path constants of its experiment, each used
  by name: a dictionary of paths cannot be followed by the input digest, and
  the lesson would then have no digest.
- **Cost.** Quote the cost record of the trace as recorded by the run that
  produced it, never as measured by the build. A count the run did not report
  (a Claude Code session reports no tokens or price) is `None`, and the page
  says it was not reported.
- **Not verified.** A full benchmark run stays outside `scripts/verify.conf` and
  is marked "not verified" where shown; the page replays one small trace.

## Measured data

Real measurements are inputs that no build can regenerate (ADR 007). A lesson
may use one only after the dataset has passed the feasibility gate and holds a
`go` on its card. Two lessons use measured data: the analysis pipelines lesson
(`site/lessons/mechanics/10-automated-analysis-pipelines`), with the wave
gauges of the flume, and the gravitational-wave lab
(`site/lessons/mechanics/11-gravitational-wave-strain`), the first lab built
around one dataset. `site/rendering-check.qmd` shows the pattern in the
smallest form.
Evidence and decisions are in `docs/datasets/`.

**The gate.** Before any lesson commitment a dataset gets a dossier,
`docs/datasets/<dataset>.md`: an actual small file inspected, named with its
version and checksum; every artifact labelled; one reference figure generated
by source-controlled code; the four rights questions answered with the source
of each answer; size, runtime, and payload estimated; and a decision, `go`,
`defer`, `reject`, or `survey-only`, with reasons. A score from a survey is
not evidence, and a beautiful figure does not decide.

**The card.** `data/registry/<dataset>.yaml` records the source, the licence,
the four rights answers (local download, redistribution of subsets,
publication of figures and derivatives, modification and attribution), the
type of every artifact, and the calibration, schema, units, cadence,
coordinates, masks, uncertainty, estimates, and downloads. The dataset check
(`uv run python -m pbc.data.check`, part of `./scripts/verify.sh`) validates
every card. Artifact types:

| Type | Meaning |
|---|---|
| `raw-measured` | What the instrument recorded |
| `processed-measured` | Measured, then aligned, averaged, filtered, or selected |
| `calibrated-observation` | A calibrated product of an instrument or a pipeline |
| `modelled-reference` | The output of a simulation or a model |
| `synthetic-test` | Generated for a test, whatever its origin |

**The sample rule.** A small sample may be committed under
`data/samples/<dataset>/`, only for a `go` and only what the figure needs,
and only when the card's licence is CC0, CC BY, or a recorded equivalent
permission and its answer on redistribution of subsets is `permitted`. The
caps are 2 MB per file, 8 MB per dataset, and 32 MB for all samples. Every
sample is declared on the card with its checksum, how it derives from the
source, and a parsing test that asserts the field names, shapes, units, masks,
and cadence. Anything restricted or larger is never committed: the page links
to the original and uses a documented download, `./scripts/fetch-data.sh
<dataset>`, which a learner runs and the build, CI, and verification never do.
Lesson cells read only committed samples.

**The figure status.** Every figure from data carries one of `measured`,
`calibrated`, `processed`, `simulated`, or `conceptual`, from the type of its
source artifact, next to the figure. A measurement is never merged with a
modelled reference, a fitted curve, or a reconstructed signal: draw them apart
and label them. Say on the page what was filtered, interpolated, or selected,
and carry the card's attribution text, and its acknowledgement text where the
source requires one.

**Typed claims.** A claim about the data is `observational`,
`experimentally-supported`, `numerically-verified`, or `formal-theorem`, and a
page states in plain language what the evidence supports and what it does not.

**The no-LLM path.** Everything a learner needs to reproduce a figure from a
committed sample or a documented download works with no model and no account.
An agent may help a learner explore, but its conclusions are never data.

**The page pattern.** A measured-data lab is a format 2 lesson that

1. shows the card with `data_card("<dataset>")` from a cell with `#| echo:
   false`: source and version, licence, the attribution text, calibration,
   masks, uncertainty, the artifact types with the figure status each gives,
   where the committed sample is, the download command, and the no-LLM path.
   It refuses a dataset without a `go`;
2. reads the data with a reader of `pbc.data` and wraps it with
   `pbc.data.adapters` (`strain_series`, `transmission_series`,
   `measured_elevation`, `modelled_elevation`) so that the series carries the
   artifact type of its source;
3. changes the series only through `Series.select`, `smooth`,
   `interpolate_to`, and `drop_masked`, each of which records a step the page
   states in plain words (`Series.disclosure()`). `interpolate_to` propagates the uncertainty of the two
   neighbouring samples as independent; where they share an error, such as
   a common calibration offset, say on the page that the interpolated
   uncertainty is a lower bound; the status becomes
   `processed` after the first one, so smoothed data cannot be shown as raw;
4. draws with `pbc.data.plotting`: `measured_vs_model` (the measurement with
   its band, the models dashed and apart, the residuals), `series_with_band`,
   `signed_image` (colours centred on zero; masks grey; "false colour" in the
   colour bar), `label_status`, `add_credit`. The figure cell names the card
   with `#| fig-dataset: <dataset>` next to `#| fig-status:`; the source check
   rejects a status the card's artifact types do not allow (a measured
   dataset's figure is never `simulated`), and the built-site check does the
   same on the built page. For a dataset whose card holds measurements and a
   modelled artifact, add `#| fig-artifact: <artifact type>`: the status
   has to be that of the artifact the figure shows, so the measurements of
   such a dataset are not `simulated` either. A figure that draws only a model fitted to the
   data, and none of the measurements, is `simulated` and names the dataset
   with `#| fig-model-of: <dataset>` instead. Leaving both out does not avoid
   the check: it follows the names of the lesson from the readers, loaders,
   and sample directories to the figure cell, also through earlier cells,
   and fails a figure that is made from a dataset and names none. What that
   analysis cannot see is listed in `docs/architecture.md` ("Measured-data
   lab"); a reviewer checks those cases by reading;
5. fits with `pbc.data.fit.fit_curve` and reports `FitResult.stderr`,
   `reduced_chi2`, and `warnings`. A parameter the data cannot tell apart is
   reported as not identified, with an infinite standard error, and the page
   says so; it never prints it as a value with an uncertainty. Uncertainties
   go through `pbc.data.uncertainty` (`propagate`, `standard_error`,
   `standard_from_expanded`, `robust_sigma`) and masks through
   `pbc.data.calibration` (`mask_to_nan`, `valid_fraction`);
6. runs `check_figure(fig, residuals=True)` in a test of the lab: it returns
   the missing status label, unit in `[...]`, title, legend, residual panel,
   or "false colour" note.

The helpers cover the formats of the three `go` datasets: GWOSC plain text,
Touchstone two-port, and the flume CSV. A lab whose `go` dataset needs HDF5,
MAT, or FITS adds the reader and its locked dependency with that lab. The
in-repository Touchstone parser stays (Issue #66; the NPL dossier has the
reasons).

To add a dataset, copy the card of a spiked one, read the record and the
files, and write the dossier; do not copy the rights answers of another card.

## Analysis pipelines

A lesson that reports numbers from an analysis (a sweep, a statistic with its
uncertainty) builds the analysis as a function and collects its results in a
`Report` of `pbc.data.pipeline`. The report lists quantities in a fixed order,
each with its unit, an optional standard uncertainty, and the number of
decimals it is shown with. The build compares the report as shown with a
committed expectation:

```python
from pbc.data.pipeline import EXPECTED_DIR, check_report

check_report(report, EXPECTED_DIR / "projectile-range.txt")  # raises ReportMismatch
```

- `sweep(name, values, func)` evaluates a function that returns named results
  at each value; `estimate(repetitions)` is a mean with its standard error;
  `Report.rows()` gives the pairs for a result table.
- The comparison is on the rendered text, so a change below the displayed
  precision passes and a change of a shown digit fails, naming the line.
  Choose the decimals well above round-off so another machine shows the same
  text.
- An expectation lives in `reports/expected/<name>.txt`, not in the lesson
  directory (which holds only its page). Write it with
  `uv run python -m pbc.data.reports --update`, read the diff, and commit it;
  `uv run python -m pbc.data.reports` says which reports differ. Register a
  new report in `pbc.data.reports.REPORTS`.
- A function that draws random numbers takes a seed. An expectation records
  that the analysis still gives the numbers someone accepted; whether they are
  right is shown by tests against something independent of the code.
- A module of `pbc.data` that reads a sample is a data source for the figure
  check; `pipeline.py` reads nothing and is listed among the tools in
  `tests/support/data_use.py`.

## Link maintenance

External links live in the reference register, `site/references.yaml`
(ADR 009). The build and reading never contact another site, so a link can
rot unseen. Run the maintenance check on your machine, with a network
connection:

```bash
./scripts/check-links.sh
```

It opens every URL of the register with a timeout and prints one line per
entry. `BROKEN` names a page that does not answer or an anchor the page no
longer has; `OK` names the `last_checked` date to set. It changes nothing, is
not in `scripts/verify.conf`, has no CI job, and never blocks a merge.

- Run it before an editorial pass and at least once a quarter.
- A rotten link is re-researched with the selection protocol and replaced by
  an equivalent whose passage you read and whose section URL you verified.
  Never replace it by a title match, and never drop a link and leave the
  sentence it supported without its reason.
- After a run, update `last_checked` of the entries that resolved.

## Identity and attribution

The project's description, "Physics by Construction is a free, open-source
educational initiative by JIDAI, created by Ahmet Taspinar.", is defined once
in `src/pbc/authoring/identity.py`. Rules for every page:

- Never type the sentence or the footer line by hand. Pages call
  `pbc.authoring.identity.description()`; the footer line comes from the
  `PBC-ATTRIBUTION` token in `site/_quarto.yml`, replaced after the render.
  `python -m pbc.authoring.identity` writes the README block and the
  `abstract` of `CITATION.cff`; `--check` compares.
- The home page has one attribution link, to the About page. The footer line,
  with its one link to `https://jidai.nl`, is not repeated in lessons or in
  any page content. Lessons do not mention JIDAI.
- The home page states what is published from the lesson front matter and
  what is planned from the curriculum file (`pbc.authoring.home_content()`,
  F124): Part A and Part B list every course and method path with its
  published and planned counts; one with a published lesson links to its
  place on the path page (`#course-<id>`, `#path-<id>`), and one without is
  labelled planned and is not linked. The capstone projects come from the
  capstone slots of the curriculum file, and each is described only by the
  explanation of its concept in `site/atlas.yaml`: no title, count, or
  description of a lesson or a capstone is typed into the page. A sentence
  about the site that is not generated must be true of the published site;
  the examples of the three activities, and the lesson of the opening
  figure, are lessons named by id in the same module.
- The opening figure of the home page is drawn by
  `pbc.mechanics.experiments.home_opening` from the double pendulum of
  `pbc.mechanics.chaos`, through the figure-writing pattern of a lesson
  (ADR 016 decision 2): the page's cell shows the bytes its `run()` encodes,
  and `uv run --locked --no-dev python -m
  pbc.mechanics.experiments.home_opening out` writes the same file. Its
  status is `simulated`; the page states the module and the commit it was
  built from. Its second figure, the change of the energy, sits with the
  provenance and the run's numbers in a native disclosure below the caption.
  It moves only with the validated interactive pendulum, a separate feature
  (requirements decision 36).
- The home page's composition is the owner's (Issue #238, 2026-10-21):
  three courses featured with the course illustrations of the atlas
  (`FEATURED_COURSES`), the other five in a compact row; Part B under the
  editorial heading "Physics + AI"; one capstone (`FEATURED_CAPSTONE`) on the
  dark navy ground under its editorial heading (`FEATURED_HEADING`), the
  others smaller. The editorial headings never replace the manifest's
  explanation. The artwork beside the featured capstone is conceptual
  interface artwork drawn by `pbc.authoring.home_artwork`, written into the
  built site by the post-render script `site/home-artwork.py` and registered
  with its module in `site/assets/provenance.yaml`; it carries no axis,
  scale, number, or measurement label, and its label says it shows no data
  and no simulation.
- JIDAI is the initiative's company, not a copyright holder, funder, or
  university partner. The copyright line, the licences (MIT for code, CC BY
  4.0 for content), the repository address, and `website.site-url` do not
  change with the wording.
- Nothing requires an account, contact with JIDAI, tracking, or a corporate
  link, and no surface advertises. `CITATION.cff` has no DOI until a release
  policy exists.

## Instructor packs

An instructor pack (`docs/instructor-packs/<lesson id>.md`, F59) is a
teaching pack for one published lesson. Its block between the
`pack:start` and `pack:end` markers (objectives, prerequisites, difficulty,
and the citation) is written from the lesson's front matter and from
`CITATION.cff` by `python -m pbc.authoring.educators` (`--check` only
compares); `tests/unit/test_educators.py` fails when a pack differs from its
lesson. Everything else in the pack is written by hand. The assignment's
reference solution is a test (`tests/unit/test_instructor_pack_<lesson>.py`)
that asserts the figures the pack states. The "For educators" page of the
site lists every pack that exists. A pack makes no claim about who uses it
and asks for no contact.

## Third-party material

Lesson text and figures are published under CC BY 4.0 and code under MIT
(`LICENSE-CONTENT`, `LICENSE`). Material that is not your own may go into a
lesson only under these rules:

- **Its licence allows it.** The material is in the public domain or under a
  licence that permits redistribution and adaptation under CC BY 4.0 (text,
  data) or MIT (code): for example CC0, CC BY, MIT, or BSD. Material under
  share-alike, non-commercial, or no-derivatives terms is not included.
- **It is attributed where it is used.** Name the title, the author, the
  source with a link, and the licence, and say what you changed, next to the
  material on the page.
- **It is listed on the About page.** Add an entry under "Third-party
  material" in `site/about.qmd`, and name the source and licence in the pull
  request.
- **Figures are redrawn.** An image file cannot be committed. Draw the
  figure with code from data you may use, and credit the original in the
  caption ("after ...").
- **Quoted results are marked.** A number or statement taken from a source
  is not checked by the build, so it carries the "not verified" marker next
  to its citation.
- **Code keeps its notice.** Third-party code goes into `src/pbc` with its
  copyright and licence notice, not into a cell.

Short quotations with a citation and facts as such need no licence. When in
doubt, link to the source instead of including it.

## What is committed

A lesson directory holds `index.qmd` and nothing else. Figures, outputs,
rendered pages, notebooks, and execution caches are regenerated by every
build; the checks reject them under `site/` and `src/`, and `.gitignore`
keeps the usual build output out of Git.

The one exception is reserved for lessons in which an LLM agent runs an
experiment (ADR 004): the recording of the model's messages is committed as
the replay fixture `replay.json` next to the `index.qmd` of that lesson.
That location is exempt from the check, and no other file may be placed
there or carry recordings elsewhere.

The other committed input is a dataset sample under `data/samples/<dataset>/`
(ADR 007; "Measured data"), declared on its card and checked by the dataset
check. It lives outside `site/` and `src/`.

## Limits

- A lesson page executes and renders within 30 seconds. Reduce the problem
  size when a computation takes longer.
- Lessons are in English.
- The page must read completely with JavaScript turned off, not scroll
  sideways at phone, tablet, or desktop width, and pass the automated
  accessibility scan. The built-site checks cover this for every page.

## What the checks report

| Check | Reports |
|---|---|
| `lesson-checks` (`tests/lessons`) | Front matter outside the schema; a Lean module that the page shows and `lean-modules` does not list, or that it lists without showing or without a file; a missing or empty required section; a lesson without the `lesson_header()` cell before its first heading; an exercise without a solution; a last section without `reproduce_this()` or with another heading than the one of the kind of the lesson; a lesson without `lesson.experiment`, or with an experiment that is not at its place, not imported by the page, or without its unit test; an outside prerequisite that names no glossary entry, an entry that no lesson assumes or whose definition is not one to three sentences, a missing or unknown course, a lesson without a method, a number of outcomes outside two to five, a related lesson that does not exist or is a prerequisite, a duplicate id, a gap or duplicate in the orders of a strand, a slot that does not exist, is claimed twice, or is homed in another course, a prerequisite that does not exist, comes later in its own strand, or forms a cycle, a curriculum file outside its schema; code that is neither an executed `{python}` cell nor marked "not verified"; a figure cell without `fig-alt`; an image file in a page; for a format 2 lesson, a missing or empty `limits` section, a number of self-checks other than one (or one without a solution), choices that break the rules of "Self-checks and progress", a claim of an unknown type, a claim without `evidence` or whose evidence names no executed cell, register or card key, Lean theorem, or recorded run, a figure without a valid `fig-status`, a `go-deeper` key that the register lacks, a URL typed in the source, and a hand-typed number in prose or alt text; a register entry with a missing or malformed field, a duplicate key, or no lesson using it that is not reserved; a generated artifact or a stray file under `site/` or `src/`. |
| `site-build` | A cell that raises, including the header cell of a lesson whose path is inconsistent; an equation that cannot become MathML. |
| `site-checks` (`tests/e2e`) | A learner-state script with a request, another origin, or storage other than local storage; a request, cookie, or write that carries or keeps learner state outside local storage; a self-check that is not usable with scripts disabled; stored data of another version that is not discarded; progress controls without keyboard operation or that fail the accessibility scan (`tests/e2e/test_learner_state.py`); A lesson without a built page or a required section; a lesson the home page does not lead to without JavaScript; a format 2 page whose cell printed a block of numbers; a header whose course, methods, outcomes, prerequisites, "Before you begin" list, related lessons, or previous and next links differ from the front matter; a glossary page that lacks an entry or does not link the lessons that assume it; an evidence map that lacks a claim, lists it more than once, or links an element the lesson page does not have once; a path page that does not list every lesson under its course and each of its methods; a lesson address that existed before the courses and no longer resolves; an excerpt that differs from its source, a Python object or a region of a Lean file; a cell or inline expression that was not executed; "not verified" material without a visible label; a last section whose heading or commands are not those of the kind of the lesson, or that names a render; an experiment that fails, takes longer than 30 seconds, or writes a figure file or a number that is not the published page's; the internal render of a page in a clone that does not regenerate the published page; a widget script that makes a request, names another origin, or uses browser storage, or a widget that writes to cookies or storage when operated; a widget that does not respond to its controls, cannot be operated by keyboard, shows values that differ from `pbc`, or moves the page when it loads; and the checks every page gets (images, links, JavaScript, widths, accessibility). |
| `determinism` | A page that differs between two builds. |

Fix the lesson when a check fails. Do not weaken a check to make a lesson
pass.
