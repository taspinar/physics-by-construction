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

## Create a lesson

1. Pick the strand and the position of the lesson. The strands are
   `mechanics`, `agents-llm`, `agents-abm`, and `lean`, in learning path
   order. `docs/roadmap.md` lists the planned lessons.

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
   uv run --locked pytest tests/unit                 # the code
   uv run --locked pytest tests/lessons              # the lesson source checks
   uv run --locked quarto preview site               # read the page while writing
   ./scripts/verify.sh                               # everything, before a pull request
   ```

   `docs/development.md` has the one-time setup these commands need.

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
| `description` | no | One sentence; shown under the title and used as the page description. |
| `lesson.id` | yes | Stable identifier: lowercase words joined by hyphens, starting with a letter. Unique across the site. Other lessons name it as a prerequisite, so it never changes and is never reused. Do not put the position in it. |
| `lesson.strand` | yes | One of `mechanics`, `agents-llm`, `agents-abm`, `lean`, in learning path order. Must be the strand directory the lesson is in. |
| `lesson.order` | yes | Position in the strand, 1 to 99. Must equal the number the directory name starts with. The orders of a strand run from 1 without a gap or a duplicate. |
| `lesson.difficulty` | yes | 1, 2, or 3 on the one difficulty scale of the site: introductory, intermediate, advanced. The scale is defined in `pbc.authoring.path` and explained on the learning path page. |
| `lesson.prerequisites.lessons` | yes | List of the `id`s of lessons a reader needs first. Each must exist and come earlier in the learning path. May be empty. |
| `lesson.prerequisites.outside` | yes | List of texts: what a reader must know that no lesson on the site teaches. May be empty. |
| `lesson.lean-modules` | no | List of the Lean modules the lesson displays, such as `PhysicsByConstruction.Mechanics.Kinematics`. |

No other key is allowed, neither at the top level nor under `lesson`. Options
that apply to every page belong in `site/_quarto.yml`. An option that changes
how one page is executed (`execute`, `freeze`, `jupyter`) would undermine the
checks and is rejected with the rest.

## The learning path

The learning path is the lessons in order: the strands in the order above,
and within a strand the lessons by `order`. It is derived from the front
matter when the site is built, so there is no list to maintain:

- The page `site/path/index.qmd` lists the strands that have a lesson, and
  for each lesson its difficulty, description, and prerequisites. It also
  explains the difficulty scale.
- The first cell of every lesson writes the header of the lesson: its strand
  and position, its difficulty, its prerequisites with links, and links to
  the previous and next lesson of the path. The template has the cell; keep
  it before the introduction:

  ````markdown
  ```{python}
  #| echo: false
  from pbc.authoring import lesson_header

  lesson_header()
  ```
  ````

A check validates the path as a whole: ids are unique, the orders of a strand
run from 1 without gaps or duplicates, and every prerequisite exists, comes
earlier in the path, and forms no cycle. A violation fails verification, and
the build of a page fails on it too.

## Sections

A lesson opens with a short introduction without a heading, followed by
level-2 sections. These are required, and none may be empty:

| Section | Identifier | Content |
|---|---|---|
| Assumptions | `assumptions` | Every assumption of the model and of the program, each with what goes wrong when it does not hold. |
| Explanation | `explanation` | The physics and the method. |
| Code | `code` | The reusable code of the lesson, shown by reference from `src/pbc`. |
| Worked examples | `worked-examples` | Executed examples that compare the result with something known. |
| Exercises | `exercises` | At least one exercise; every exercise has its solution on the page. A lesson with an interactive visualization may have the section `interactive-visualization` instead or as well. |
| Reproduce this | `reproduce-this` | The output of `reproduce_this()`, see below. Keep it last. |

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

Any other code block is not run by the build: a plain <code>```python</code>
block, a block in another language, shell commands, pasted output, a cell
with `eval: false`. Each needs the "not verified" marker below, or the check
fails. `include` and `embed` shortcodes are not allowed: a lesson is one
page.

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

## Figures

A figure is drawn by an executed cell. Image files are never part of a
lesson.

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

Exercises are numbered in page order. The solution becomes a closed
`<details>` element titled "Solution to exercise N", which opens without
JavaScript. Numbers in a solution come from executed code like everywhere
else. Do not use tabsets or collapsible callouts: they need JavaScript.

## Reproduce this

The last section is one cell:

````markdown
## Reproduce this

```{python}
#| echo: false
from pbc.authoring import reproduce_this

reproduce_this(
    code=["src/pbc/mechanics/kinematics.py"],
    tests=["tests/unit/test_kinematics.py"],
)
```
````

`code` names the modules the page imports and `tests` the tests of those
modules, relative to the repository root. The cell writes the commit the page
was built from, links to the files at that commit, and the commands that
check out the commit, run the tests, and render the page again. A build from
a checkout with uncommitted changes says so on the page. A check runs the
commands of every lesson and compares the regenerated page and figures with
the published ones, byte for byte.

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
5. Run `./scripts/verify.sh`, then commit the file.

To use another provider, write one client module that reads its own key
variable and change `PROVIDER` in `src/pbc/agents/providers.py`; the lesson
page explains it. Only that provider's key is needed then.

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
| `lesson-checks` (`tests/lessons`) | Front matter outside the schema; a missing or empty required section; a lesson without the `lesson_header()` cell before its first heading; an exercise without a solution; a "Reproduce this" section without `reproduce_this()`; a duplicate id, a gap or duplicate in the orders of a strand, a prerequisite that does not exist, comes later in the path, or forms a cycle; code that is neither an executed `{python}` cell nor marked "not verified"; a figure cell without `fig-alt`; an image file in a page; a generated artifact or a stray file under `site/` or `src/`. |
| `site-build` | A cell that raises, including the header cell of a lesson whose path is inconsistent; an equation that cannot become MathML. |
| `site-checks` (`tests/e2e`) | A lesson without a built page or a required section; a lesson the home page does not lead to without JavaScript; a header whose strand, position, difficulty, prerequisites, or previous and next links differ from the front matter; a path page that does not list every lesson in order; an excerpt that differs from its source; a cell or inline expression that was not executed; "not verified" material without a visible label; "Reproduce this" commands that fail, take longer than 30 seconds, or do not regenerate the published page; and the checks every page gets (images, links, JavaScript, widths, accessibility). |
| `determinism` | A page that differs between two builds. |

Fix the lesson when a check fails. Do not weaken a check to make a lesson
pass.
