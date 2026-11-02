# Plan: F134 — Home as a landing page, Run the code, and How we verify the science, Issue #339

- Issue: #339 (source: `docs/roadmap.md`, F134; ADR 021 decisions 1, 4,
  and 5, superseding ADR 018 decision 4 in part).
- Branch: `feature/339-home-run-the-code-verify`; base `03c7c4b` (F133
  merged).
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 3 by trigger (the opening figure, the Part A, Part B, and
  capstone blocks of F124 leave Home with the tests that assert them; the
  capstone artwork module of F124 and its test are removed); otherwise
  Level 2. `site/_quarto.yml` (sensitive) changes: the footer link and the
  post-render list. The full `./scripts/verify.sh` runs last; the approval
  request is `.agents/approvals/339.md`.

## The hero

**Data file** `site/hero.yaml`, beside the curriculum file:

```yaml
default: "1a"
headlines:
  - id: "1"
    text: "The universe has no obligation …"
    subtexts:
      - id: a
        text: "Physics has always challenged …"
```

A pair's identifier is the headline's id and the subtext's letter. Read and
validated by `pbc.authoring.home.read_hero` (`HeroCopy`): the identifiers
are exactly 1a, 1b, 1c, 2a, 2b, 2c, 3a, 3b (a missing, a duplicate, or an
extra one fails, also a duplicate headline id); no unknown field at any
level; every text is non-empty plain text (no Markdown or HTML markup
characters, no line break); the default names one of the pairs. Lists, not
mappings, so a duplicate identifier is visible to the check (a YAML mapping
would drop it silently).

**Markup** (`HomeContent.hero()`): a `<section class="home-hero">` with

- `<div class="hero-copy" data-hero="1a">`: the default pair as
  `<h1 class="hero-headline">` and `<p class="hero-subtext">`; the only `<h1>`
  of the page (the front matter has no `title`, only `pagetitle` and a fixed
  `description`, so Quarto writes no title block);
- the two ways in: "Start learning" (the first lesson, the filled control)
  and "Open the Course Atlas" (a text link);
- `<script type="application/json" id="hero-pairs">`: every pair
  (`{"id", "headline", "subtext"}`), with `<`, `>`, and `&` escaped;
- `<script src="learner/hero.js"></script>` right after the copy:
  synchronous, so that it runs while the page is parsed, before the first
  paint;
- the hero image (below).

**Script** `site/learner/hero.js`, about ten lines, no dependency: reads
`hero` from the query; when it names a pair, takes it, else picks one with
`Math.random()`; adds one hidden, `aria-hidden` ghost of every pair to the
copy's grid cell (so that the block's height is the longest pair's at every
width) and writes the chosen pair into the `<h1>` and the `<p>`. No request,
no cookie, no storage, no timer, no event listener: nothing changes after
it has run. Without scripts the default pair stays, and nothing swaps.

## The hero image

Interface artwork (class C of ADR 021 decision 1), built by
`pbc.authoring.home` as one inline SVG at build time, composed from the
registered card illustrations of the atlas (`assets/atlas/<id>-card-228.webp`,
already in `site/assets/provenance.yaml` from F133, so every part is
registered and no new raster is committed): two constellations, the eight
courses (Part A) and the four method paths (Part B), each node one card
illustration in a rounded 4:3 frame, its name as SVG `<text>` from the
curriculum file, the nodes of a constellation joined by thin decorative
lines in curriculum order and the two constellations by one dashed line.
The positions are constants of the module; the lines imply no
prerequisite, and the alt text says so. `role="img"` with a `<title>`
naming what it shows; it holds no link (every route is an HTML link
elsewhere on the page). Below 40em the labels are set larger, since the
image is drawn at about half its size (hiding them would leave hidden text,
which the no-JavaScript check rejects); the title names every course and
path. The copy is a declared enhancement (`data-enhancement` with an id,
invariant I4): the default pair is its static content.
Not the delivered composite `pbc_hero_1920x1080` (labels in its pixels).

The visual check (composition, legibility at 1280 and 390 px, consistency
with the atlas family, no text, number, or formula in any pixel) is
recorded in the completion record; the owner's approval goes on the Issue
(criterion 3, gate `owner_approval`).

## The rest of Home (`site/index.qmd`, `pbc.authoring.home`)

Every link and every name is printed by `HomeContent`; the page holds no
Markdown link and no copy of the hero.

1. The hero (above).
2. "What this site is" (`#about-the-site`): three sentences, the canonical
   identity sentence (`identity.description()`) first; then one line of
   three links, "About the creator and JIDAI" (the one attribution link),
   "How we verify the science", and "The source on GitHub" (the repository
   link that `tests/e2e/test_built_site.py` requires of Home).
3. "What you can learn" (`#examples`): three example lessons from
   different courses and one capstone, each with its title (a link), one
   line, its preview (the F63 preview of `previews/<id>`, with its alt
   text), and its level ("Introductory, level 1 of 3"). The selection rule
   (`HomeContent.examples()`), over published lessons in the order of the
   learning path, never from the first course (the start link leads into
   it):
   - a *simulation*: the first lesson of level 1 with the method
     `simulation` only;
   - a *measured-data lab*: the first lesson with the method
     `measured-data` from a course not yet chosen;
   - an *AI experiment*: the first lesson with the method `llm-agents` from
     a course not yet chosen.
   At `03c7c4b` this gives Random walks and diffusion (thermodynamics), the
   wave flume lab (waves), and unknown physical worlds (astrophysics). The
   capstone (`HomeContent.capstone()`): the first published capstone of the
   curriculum file (a slot of kind applied capstone filled by a lesson) whose
   course none of the examples has, else the first published one; its one
   line is the explanation of its concept in the manifest (`site/atlas.yaml`),
   the text the atlas shows for it. At the base: EM9. One line of a lesson is
   the first sentence of its front-matter `description`.
4. "Begin" (`#begin`): the start link and the atlas link. Nothing else.

Removed: the opening "Build a world. See if it obeys physics." with the
double-pendulum figure and its disclosure, Part A, Part B, the capstone
blocks, `FEATURED_*`, `ARTWORK_LABEL`, the activity examples
(`CONSTRUCT_EXAMPLE` …), and the capstone artwork module of F124
(`pbc.authoring.home_artwork`, `site/home-artwork.py`, its post-render
entry, its provenance entry, `tests/unit/test_home_artwork.py`): it drew a
planned capstone that Home no longer features. The code-drawn course
illustrations of `pbc.authoring.atlas`, which only Home drew (marked "until
F134"), their test, and their CSS go too. `pbc.mechanics.experiments.home_opening`
and `tests/unit/test_home_opening_experiment.py` stay; the figure is not
placed on "How we verify the science" (no scientific figure is produced by
this feature).

**Found while building.** A Jupyter-executed page without a `title` takes
its first Markdown heading as its title, and Quarto's title postprocessor
moves the first `<h1>` that is its parent's first child into a title block
of its own. So `site/index.qmd` is one cell that prints the whole page
(`HomeContent.markdown()`), and the hero starts with an empty
`<header class="quarto-title-block">`, which keeps the hero's `<h1>` in
place (`title-block-style: none` still writes an `h1.title`).

## Run the code (`site/reproduce.qmd`)

- The opening paragraph stays; its numbered list of the three things is
  replaced by three sections, the first three headings of the table of
  contents: "Run a simulation", "Replay an AI experiment", "Verify a formal
  proof", each one sentence and a jump link to its section ("Run an
  experiment", "Replay an agent lesson", "Optional: check a proof"),
  as three sibling `## … {.route}` sections, side by side from 768 px as
  inline blocks (a wrapping div would take them out of the table of
  contents); the sentences of the old numbered list that the routes do not
  carry join the opening paragraph.
- The shared installation under them, unchanged.
- "Optional: drive a coding agent" and "Troubleshooting" keep their
  headings; their content is inside a native `<details>`, closed.
- Every fenced command, its classes, and every heading the checks read
  unchanged; `tests/integration/test_setup_page.py` passes unchanged.

## How we verify the science (`site/verify.qmd`, `pbc.authoring.verify`)

- The page: why every claim is typed and checked (prose); the four claim
  types, one paragraph each, under the existing claim label (the span
  `.claim` with `data-type`, as in the lessons); three worked examples; a
  link to the Evidence map as the full list.
- The examples are data of `pbc.authoring.verify` (`EXAMPLES`): the claim
  type, the lesson id, and the evidence word:
  numerically verified, `harmonic-oscillator`, `euler-energy-ratios` (a cell);
  experimentally supported, `wave-flume-lab`, `aalborg-submerged-bar` (a
  dataset card); formal theorem, `proving-what-the-simulation-showed`,
  `euler_energy_step` (a Lean theorem). Each is resolved with the code of
  the evidence map: the published lesson, its claim of that type whose
  evidence names the word, and the word's source of the expected kind.
  Shown: the claim label, the statement (as the evidence map shows it), its
  scope, and links to the claim in the lesson, to its evidence, and to its
  row of the Evidence map; for the card its title, creator, and licence from
  the card; for the theorem its statement from the Lean file as a code
  block.
- A missing target (no such lesson, no such claim, a word that resolves to
  nothing or to another kind) raises in `verify_page()`, which the page's
  cell calls, so the build fails, as for a claim (unit tests per case and
  an integration test that renders the page in a minimal project and sees
  the build fail).
- The Evidence map gains a row anchor per claim
  (`<strand>-<lesson directory>-claim-<n>`) as an empty span in the claim
  cell; its intro is shortened to two sentences and a link back to the new
  page.
- Footer: "Scientific evidence" points at `verify.qmd`. The Evidence map
  stays at its address, reached from the new page.

## Tests

- `tests/unit/test_home.py` rewritten: the hero schema (exactly the eight,
  missing, duplicate, extra, duplicate headline, unknown field, markup,
  bad default), the hero markup (one `<h1>`, the default pair, the embedded
  pairs, the script tag), the image (twelve nodes, every href registered in
  the provenance register, labels as text, no link), the selection rule
  (three distinct courses, none the first, the kinds, deterministic, a
  fixture where a kind is missing), the capstone rule, every link generated,
  the absent heading.
- `tests/unit/test_hero_script.py`: the script's source makes no request
  and uses no storage, cookie, timer, or listener; it is short.
- `tests/unit/test_verify.py`: the examples resolve; each failure case
  raises.
- `tests/integration/test_home_build.py` rewritten: the built page follows
  the lessons (the examples change with the front matter).
- `tests/integration/test_verify_build.py`: a missing target fails the
  build.
- `tests/e2e/test_home.py` rewritten: above the fold at 1280×800 and
  390×844, one `<h1>` unchanged after load, `?hero=<id>` for each of the
  eight, no layout shift, no request or storage by the script, the default
  pair without scripts, the sections, the examples' links and previews,
  reflow at 320 px, the accessibility scan (the scan every page gets).
- `tests/e2e/test_verify_page.py`: the examples' links reach one element
  each in the lesson and the Evidence map; the footer reaches the page.
- `tests/unit/test_site_chrome.py`: the footer entry's address.

## Docs

`docs/atelier.md` ("Home page", the asset-class example of generated
artwork), `docs/authoring.md` (the home page rules). `docs/architecture.md`
is protected and was restated by the planning.

## Visual deliverables and skills

Page and layout: Home (the hero, the examples), Run the code (the routes),
How we verify the science.

Skills: impeccable@08d5b470, frontend-design@dbd4588f

Expected artifact: the built `index.html`, `reproduce.html`, `verify.html`
at 1280 px and 390 px. Scientific validation: none beyond the claims' own
(no scientific figure; the examples' statements and targets come from the
lessons through the evidence code). Accessible fallback: the default pair
without scripts; every image with alt text; native disclosures.

Interface artwork: the hero image (class C of ADR 021).

Skills: impeccable@08d5b470

Expected artifact: the inline SVG of the hero, composed of the twelve
registered card illustrations. Scientific validation: none required (class
C; the visual check instead). Accessible fallback: the `<title>` naming the
two constellations and every course and path.

The PBC Scientific Visualization skill does not apply (no scientific figure
is produced; the previews on Home are the lessons' own F63 previews);
diagram-design does not apply (no conceptual diagram).
