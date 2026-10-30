# ADR 021: A quieter site: registered raster interface artwork on non-lesson pages, the two-layer course atlas, and Home as a landing page

## Status

Proposed with the planning of the change cycle `site-navigation-and-atlas`
(`docs/changes/site-navigation-and-atlas.md`, human-supplied, 2026-10-30;
requirements decisions 40 and 41, re-approved on 2026-10-30); accepted when
that planning is approved. Delivered by F132 to F135 (Issues #337 to #340).

Supersedes, in part, three decisions of
[ADR 018](018-scientific-atelier-asset-classes-and-the-course-atlas.md),
whose status names this record; the parts of them not listed here stand:

- **ADR 018 decision 2** (three visual asset classes): the definition of
  interface artwork, where it may appear, and its sources ("never a raster
  file"; produced by code at build time or an authored SVG) are replaced
  by decision 1 and decision 2 below. The conceptual-illustration and
  scientific-result classes, the animation rule, and the choice that a
  lesson's conceptual illustration stays code-drawn in an executed cell
  are unchanged.
- **ADR 018 decision 3** (the course atlas): the map with its three edge
  types, legend, and modes; the Lean and method view bands; the switch
  between map and index; selection, zoom, filters, and the phone's region
  selector; the selected-concept panels; the course areas' illustrations
  drawn by code; and the rule that the manifest holds no illustration
  reference are replaced by decision 3 below. The address, the anchors,
  the one source of truth, the manifest's concept rules, the three
  relationship types as data with their checks, the planned-content rules,
  and the capstones' planned descriptions stand.
- **ADR 018 decision 4** (the home page): the opening "Build a world. See
  if it obeys physics." with its static verified figure, the introduction
  of Part A and Part B, and the capstone highlights are replaced by
  decision 4 below. The shared header and footer, the absent section "From
  a question to a working model", and the exclusion of fake metrics,
  testimonials, and inferred progress stand.

Amends [ADR 002](002-regenerate-artifacts-and-display-by-reference.md)
once more, in the exemption ADR 018 added to condition 2 of its
replay-fixture decision: the committed-artifact check admits, besides a
registered authored SVG under `site/assets/`, a registered derived raster
(WebP or PNG) under `site/assets/` (decision 2). ADR 002's status names
this amendment. Extends [ADR 013](013-eight-courses-and-the-reference-curriculum.md)
as ADR 018 did, without changing its decision 3: the curriculum file
gains no description field. Changes no invariant beyond I6, I30, and I31
of `docs/architecture.md`, which this planning restates.

Date: 2026-10-30

## Context

The atelier of ADR 018 is delivered (F123 to F126, merged; the owner's
rendered pass outstanding on their Issues). The owner's review of the
rendered site (2026-10-29) and of the delivered illustrations
(2026-10-30) found that the site offers navigation, documentation, and
scientific accountability as if they mattered equally to every visitor.
They do not: a new visitor wants to know what PBC is and where to begin, a
researcher whether results reproduce, a contributor how to help. The
Course Atlas stacks a concept map with three edge types and a legend, the
Lean and method view bands, controls, concept panels, the course index,
the method paths, and the methods, so that a lesson appears four or five
times on a page about 8000 px tall; Home is an introduction, a course
catalogue, and a roadmap at once; the menu carries eight items.

The owner had illustrations made for the twelve sequences and the hero:
some computed by the owner's scripts, some by an image model, delivered as
raster masters with derived WebP sizes. ADR 018 decision 2 forbids every
raster and requires interface artwork to be drawn by repository code at
build time or authored as SVG. Requirements decision 41 makes a permanent
principle of what the owner decided: a visual is judged by what it claims.
Scientific results and evidence stay verified everywhere, explanations in
lessons stay correct and reviewed, and interface artwork on non-lesson
pages may be artistic, stylised, or made with an image model, provided it
claims nothing, carries no text, number, or formula in its pixels, and
keeps its provenance, licence, accessibility, and payload.

The planning was asked three questions (change request, "Open for the
planning"): whether the illustrations are rendered at build time or
committed; whether a contribution form without a GitHub account is part of
the change; where the hero's text and the sequences' one-line
descriptions live.

## Decision

1. **Asset classes by claim.** Every visual belongs to one of three
   classes, decided by what it claims, not by the page alone:
   - *A. Scientific results and evidence* (plots, simulations,
     measurements, comparisons, and any figure presented as one): the
     verified display forms, the figure-writing pattern of ADR 016, the
     F63 preview contract, on every page that shows them, Home and "How
     we verify the science" included. Unchanged.
   - *B. Explanations in lessons*: a conceptual illustration, code-drawn
     in an executed cell and labelled `conceptual` (ADR 018 decision 2,
     unchanged).
   - *C. Interface artwork*: visual identity, navigation, and atmosphere,
     in the site chrome and on non-lesson pages (Home and its hero, the
     course atlas, course, module, and capstone openings, About, and the
     other informational pages). It may be computed, stylised, abstract,
     symbolic, authored, or made with an image model, as SVG or as a
     committed raster (decision 2); it needs no numerical simulation,
     scientific validation, physical fidelity, diagnostic plate, visible
     disclaimer, or generating script, and scientific fidelity stays
     welcome where it fits. It is never placed in a lesson's body, never
     presented as a verified result, and fabricates no measurement,
     equation, or evidence: its pixels carry no formula, number, or text
     (every label is HTML or SVG text), and a decorative connection
     between subjects implies no prerequisite or scientific relationship
     the curriculum does not hold. Its alternative text names what it is,
     or is empty where it is purely decorative. Stock, hand-copied, and
     externally hosted images stay excluded. It may be adapted, cropped,
     restyled, or replaced for visual quality under these rules without
     a new decision.
   The acceptance of interface artwork is a visual check (composition,
   legibility at the sizes it is shown, consistency with its family, no
   text, number, or formula), recorded in the completion evidence and
   assessed by the reviewer on the rendered page; a scientific-correctness
   checklist is not an acceptance criterion for it.
2. **Committed derived files, bound to the provenance register.** The
   illustrations are committed as derived files, not rendered at build
   time: an image model's output cannot be regenerated by the build; the
   owner's scripts were never timed in CI and would add their run time
   and dependencies to every full run (everything under `site/assets/`
   is a shared input of ADR 014 decision 4); and the derived sizes are
   what the payload budget is measured on. A raster of interface artwork
   is a WebP file (PNG only where the plan records why) under
   `site/assets/`, at the sizes the page shows, and the provenance
   register `site/assets/provenance.yaml` names it with its origin (a
   script, with its path in the repository; an author; or an image model,
   with the model, the prompt, and the date), a licence or terms that
   permit publication, and the SHA-256 hash of its master. Where a script
   exists it is committed outside `site/` (so the build neither executes
   nor publishes it) in a place the feature's plan names, with its
   dependencies outside the pinned learner and CI environments unless
   they are already there; a regeneration check run on demand, outside
   `scripts/verify.conf` and never in CI, regenerates the master and
   compares its hash with the register (the feature's plan states how a
   script whose output is not byte-stable is compared instead). Masters, intermediates, option
   boards, and mock sources are not committed. The committed-artifact
   check of ADR 002 (as amended by ADR 018) admits a tracked `.webp` or
   `.png` under `site/assets/` only when the register names it with a
   complete raster entry, exactly as it admits a registered authored SVG;
   an unregistered raster, every other image type, and every image file
   outside `site/assets/` (a lesson directory included) stay rejected,
   with a failing test per case written before the change. An entry
   without its file fails the asset-source rule; the exemption and the
   entry stay one mechanism.
3. **The Course Atlas as a two-layer navigation page.** At the path
   address, with "Course Atlas" as its display label, the page is built at
   build time from the curriculum file, the front matter, and the atlas
   manifest:
   - Twelve sequences (the eight Part A courses, the four Part B method
     paths), each one native `<details>` element of one exclusive group
     (`name="atlas"`): the `<summary>` is the card (its illustration, its
     title, its count of published lessons, the learner's progress mark),
     the content is the panel (a larger illustration, the one-line
     description, the published and planned counts, and the lesson rows:
     label, title as a link or as a planned entry that is no link, and
     only the marks for a measured-data lab, a capstone, and Lean). A
     smaller entry holds the Lean lessons without a curriculum slot. A
     visually hidden textual equivalent lists every sequence with its
     lessons and their state.
   - On a wide screen, CSS places the cards in one column and the open
     panel beside them through `::details-content`; a browser without that
     selector shows the same disclosures as an accordion, and a phone
     always does, with the open panel under its card. One sequence is open
     at a time without a script.
   - One dependency-free module of about twenty lines in `site/learner/`
     makes the address follow the open sequence and opens the sequence an
     address names. It makes no request, sets no cookie, and uses no
     storage; `site/learner/progress.js` stays the only script that stores
     anything and keeps its contract, as do the recommendations.
   - Every existing anchor stays valid: the anchors of the courses and
     paths (today `#course-<id>` and `#path-<id>`) and the page's other
     anchors open or reach the matching sequence or the top of the page.
   - The manifest keeps its concepts, concept-to-slot associations, and
     curated conceptual connections with their rationale, under the rules
     of ADR 018 decision 3 (the display placement the map used may be
     removed with its check, since nothing draws it), and gains one
     entry per sequence: its one-line description and its illustration (a
     path the provenance register names), for every course and path of
     the curriculum file and no other. The curriculum file gains no field;
     no title, outcome, prerequisite, publication state, or count is
     written in the manifest; the capstones' planned descriptions stay the
     explanations of their concepts.
   - The three relationship types (a curated conceptual connection with
     its rationale, a prerequisite from the front matter, capstone
     membership) leave the atlas and stay as data with their checks; a
     lesson page shows its prerequisites as today and, from the manifest,
     the conceptual connections and the capstone membership of the concept
     its slot belongs to, never for a planned lesson. The prerequisite
     data, its checks, and the generation code that has other consumers
     stay; the map's drawing code, its modules, and the tests of the
     removed interaction are replaced by tests of the new interaction,
     accessibility, navigation, and data integrity, with no check of
     scientific or curriculum correctness weakened.
4. **Home as a landing page with a hero.** Home answers what makes PBC
   different, what a visitor can learn, and where to begin.
   - *The hero*: the owner's headlines and subtexts, held in one data
     file beside the curriculum file and read and validated by
     `pbc.authoring.home` (never written on a page); one fixed default pair
     in the HTML (what remains without scripts, and what search snippets
     and link previews see); one `<h1>`, which does not change after load;
     a small dependency-free script from the site's origin that picks a
     pair at random per visit and sets it before first paint, from the
     pairs the build embedded in the page; a query parameter `hero` that
     forces a pair for tests and screenshots; the text block's height
     reserved for the longest pair, so the swap shifts nothing; no storage
     and no request. No measurement of which pair works better.
   - *The hero image*: interface artwork of decision 1 showing two
     connected constellations (the eight courses and the four method
     paths), composed from the sequences' illustrations with its labels as
     HTML or SVG text; never the delivered composite whose labels are in
     its pixels, and never the only route to a page (every link is an
     HTML link).
   - The hero replaces the opening headline and the verified
     double-pendulum figure on Home; the figure's implementation, energy
     check, and provenance stay in `src/pbc` and may be shown in the
     mechanics course or on "How we verify the science". The interactive
     pendulum (F128) is no longer tied to Home.
   - Then three sentences on what the site is; three example lessons from
     different courses and one capstone (a published one), chosen by code
     from the front matter and the manifest; and a short invitation (the
     start link and the atlas). Home does not repeat the atlas's overview
     of the courses.
5. **Navigation and the supporting pages.** The header carries the
   project mark, exactly four menu items (Home, Course Atlas, About, and
   the Start learning button), and the search; the footer carries the
   attribution, the licences, and the secondary pages (Run the code,
   Glossary, Scientific evidence, For educators, Contribute, Source), with
   no link shown twice and every address unchanged. "Run the code" (the
   setup page, address unchanged) opens with three routes before the
   shared installation; a new page "How we verify the science" explains
   the four claim types with worked examples from published lessons, whose
   targets the build checks as it checks claims, and leads to the
   Evidence map. Glossary definitions appear on demand, without a script,
   in "Before you begin"; every published lesson ends with a "Suggest an
   improvement" link to the matching GitHub issue forms with the lesson's
   address pre-filled.
6. **No backend.** A form on the site that creates GitHub issues for a
   visitor without an account is not part of this change: it needs a
   server or serverless endpoint and a stored credential, which I1 and the
   requirements exclude. It stays the owner's open decision (requirements,
   unresolved question 16); a yes amends the requirements through its own
   change and Issue.

## Alternatives considered

- **Render the illustrations at build time from their scripts.** Rejected
  for now: an image model's output has no script; the scripts' run time
  and dependencies are unmeasured in CI; every build and every full run
  would carry them. The regeneration check on demand keeps the scripts
  honest without that cost; a later feature may move a script into the
  build after measuring it.
- **Keep the map and add the cards above it.** Rejected by the owner's
  review: the duplication is the problem.
- **Keep interface artwork code-drawn or authored SVG only.** Rejected by
  requirements decision 41: it would forbid what the owner decided, and
  the delivered illustrations would have to be redrawn as vector art.
- **A JavaScript tab widget for the atlas.** Rejected: native exclusive
  disclosures give the one-open behaviour, keyboard operation, and the
  no-script route without a script; `::details-content` gives the wide
  layout with the accordion as a tested fallback.
- **Store the hero variant or the open sequence in the browser.**
  Rejected: neither is learner data, and `progress.js` stays the only
  script that stores anything.
- **Measure which hero pair works better.** Rejected: it needs a
  collector, which the requirements exclude.
- **The hero copy or the sequence descriptions written on the pages, or a
  description field in the curriculum file.** Rejected: a page holds no
  hand-written catalogue, and ADR 013 decision 3 keeps the curriculum file
  free of descriptions.

## Consequences

- The committed-artifact check, the asset-source rule, and their tests
  change once more, narrowly (F133), with a failing test per case; the
  provenance register gains the raster entry. I6, I30, and I31 of the
  architecture are restated by this planning.
- The atlas loses its map, its modules, and their tests; the manifest's
  concept rules stay checked, and the relationships appear on the lesson
  pages, so F133 changes the lesson template and every lesson page's
  display: its verification is the full run, and it is not written beside
  F135, which changes the same template and CSS.
- Home loses its verified opening figure; Home and "How we verify the
  science" may still show scientific results, under class A.
- The roadmap blocks of F124, F125, F126, F127, and F128 carry a dated
  note naming the feature that replaces or changes what they delivered or
  planned; their delivered criteria stay as history.
- The derived WebP files add to the payload of Home and the atlas; the
  page budgets of the architecture hold, measured by the existing checks.
- Issue #338's correctness checklist and Issue #339's scope line that kept
  the opening figure are superseded by requirements decisions 40 and 41;
  the roadmap blocks of F133 and F134 state the criteria that apply. The
  planner brings both Issue bodies in line with those blocks right after
  this planning is approved, by the edits the roadmap's reconciliation
  notes list, and that is a pre-start gate of F133 and F134: neither
  starts while its Issue contradicts its block.
