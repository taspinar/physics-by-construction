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

Decision 3 amended by
[ADR 022](022-part-b-method-paths-with-capstone-products.md)
(2026-11-01) in one respect: a slot of the curriculum file gains the
optional key `extension` and the kind `product capstone`. The curriculum
file still gains no description field, and no title, outcome,
prerequisite, publication state, or count is written in the manifest. The
other decisions below are unchanged.

Decision 3 amended again on 2026-11-11 by the owner's redesign decision of
Issue #483 (the Course Atlas with inline expanding courses), through the
dated note under it: the two-layer layout of the wide screen is reversed,
every sequence expands inline beneath its own row on every viewport, the
learning journey of F157 leaves the page, and the opening, the rows, the
progress presentation, and the explanations are the owner's. The page's
address, its anchors, the one source of truth, the manifest's rules, the
planned-content rules, the learner state's contract, and the relationships
on the lesson pages stand.

Decision 4 amended by requirements decision 43 (change cycle
`textbook-layer`, `docs/changes/textbook-layer.md`, human-supplied,
2026-11-03; requirements re-approved on 2026-11-04) through the dated note
under decision 4, without a new ADR, as the change request and the
requirements decide: the change is content and presentation inside this
record and ADR 018. Decisions 4 and 5 amended again on 2026-11-10 by the
owner's decisions of round 2 of F158 (Issue #462: one fixed hero text, the
compact header with a native menu below 640 CSS px, the measurable
above-the-fold rule), through the dated notes under them; decision 4
amended on 2026-11-11 by the owner's copy of Issue #481 and by the owner's
decision of Issue #482 (one large fluid-dynamics hero, mirrored and faded,
in the HTML without a script), through the dated notes under it; decisions 2 and
4 amended on 2026-11-12 by the owner's request of Issue #487 (the owner's
double-pendulum illustration as the hero, wider, lifted under the copy,
and carrying no licence in the register), through the dated notes under
them. Delivered by F158; the course introductions of F156
and the learning journey of F157 add pages and text within decisions 1 to
3 without changing them. The text of decision 4 stays as the record of
what F134 delivered.

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

   *Amended on 2026-11-12 by the owner's decision on Issue #487 (Home: the
   hero image replaced by the double-pendulum illustration).* The hero of
   the home page carries no licence in the register: the entries of its
   files under `site/assets/hero/` name their origin (the owner as the
   author, with the date), their master, and its hash, and no licence or
   terms, since the owner publishes the owner's own illustration and
   states no licence for it ("Ik wil helemaal geen licentie op de hero
   pagina", 2026-11-12). The strict provenance conditions of lesson
   content do not apply to the hero. The committed-artifact check and the
   asset-source rule admit without a licence exactly the files the hero's
   data file `site/hero.yaml` declares (one per width, named by the hero's
   identifier), and keep requiring one of every other raster entry, also
   any other file under `site/assets/hero/`, with a test per case (review
   round 2 of Issue #487 narrowed the exemption from the directory to the
   declared files). Everything else in this decision stands.
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

   *Amended on 2026-11-11 by the owner's redesign decision of Issue #483
   (the Course Atlas with inline expanding courses).* The layout of the
   second bullet is reversed: no `::details-content` rule, no panel beside
   the cards, no sticky element; every sequence is one native `<details>`
   of the exclusive group whose content expands inline beneath its own row,
   the same on desktop, tablet, and phone, none open at load. The
   `<summary>` is the row (the card illustration, the title, "n published ·
   k planned", the progress hairline shown once a lesson is completed, a
   drawn chevron); the content is the title, the manifest's one line, the
   link to the introduction where one exists (F156; before the lessons,
   never at the bottom), the lesson rows in teaching order (label, title as
   a link or a planned entry that is no link and takes no focus, the
   difficulty of the front matter, and the marks Lab, Capstone, Lean,
   planned, in words), and a path's optional extensions. The learning
   journey of F157 leaves the page: the atlas opens with the owner's
   subtitle, two fixed paragraphs on Part A and Part B held in
   `pbc.authoring.atlas`, and three figures derived from the curriculum
   file and the front matter (the courses, the method paths, the published
   lessons); About keeps the journey's Part A and Part B text from the one
   source. The address module keeps its contract and gains the fallback
   that closes the other rows in a browser without exclusive disclosures
   (none before Chromium 120, Firefox 130, Safari 17.2). "Your progress"
   keeps its anchor, its storage, and its clear control, with the owner's
   sentence and a compact count; "How the lessons work" replaces "About
   the lessons" with the same anchors. The textual equivalent, the
   anchors, the aliases, and the manifest's rules stand; the tests of the
   two-layer layout are replaced by tests of the inline layout at three
   viewports.
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

   *Amended on 2026-11-04 by requirements decision 43 (change cycle
   `textbook-layer`; delivered by F158).* The hero copy, its data file, its
   script, and their rules above stand. Three parts are replaced:
   - *The hero image* is no longer the two connected constellations. It is
     one of four existing Part A illustrations, interface artwork of
     decision 1 already in the provenance register, each derived at hero
     size from its master with its own register entry, alternative text,
     and test: the double pendulum (classical mechanics, the one fixed
     default in the HTML), the vortex street (fluid dynamics), the hot and
     cold gas (thermodynamics), and the exoplanet transit (astrophysics);
     the owner may change the set when F158 starts. The hero script picks
     one per visit, independently of the headline pair and before the
     image is requested; its own query parameter, separate from the
     `hero` parameter that forces a headline pair, forces one for tests; no
     storage, no other request, no animation, and no measurement of which
     works better. None is presented as a verified result.
   - *The copy* is no longer three sentences with three examples and a
     capstone chosen by code. It follows the order identity, educational
     philosophy, curriculum (Part A and Part B), and integrity, from one
     Home copy file, with no sentence limit; "What you can learn" explains
     Part A, Part B, and their relation from the one source of the
     learning journey, with at most one owner-chosen published lesson per
     part, validated at build time, or none.
   - *The first step* is two actions with the same destinations on Home and
     in the header: the Course Atlas (primary on Home) and the first lesson
     of Part A (secondary). The header keeps its four items (decision 5).
     The above-the-fold rule is the responsive, content-first rule of the
     requirements' "Home page", approved by the owner on the rendered page.

   *Amended on 2026-11-10 by the owner's decisions of round 2 of F158
   (Issue #462, the critique of the rendered Home).* Of the hero copy rule
   above two parts change: the text is one fixed headline (the first of the
   owner's three, kept exactly) and one fixed subtext (the owner's new
   words), written into the HTML by the build and never changed by a
   script, the same with and without scripts and after a reload; no pair is
   picked at random, and the `hero` parameter is gone (the `hero-image`
   parameter stays). The three headlines and eight subtexts of F134 stay in
   the hero data file as an editorial reference that nothing shows. The
   above-the-fold rule gains a measurable part: at 390 by 844 CSS px at
   least 40 % of the image's height is above the fold; at 360 by 640 and
   320 by 568 the primary action ends at least 24 px above it. The data
   file, its validation, the one `<h1>`, no storage and no request, and no
   measurement of which text works better stand.

   *Amended on 2026-11-11 by the owner's copy of Issue #481 (Home: copy and
   structure).* The hero's one fixed subtext is replaced by the owner's new
   words ("Explore physics by building simulations, working with
   experimental data, and investigating how AI could help us understand the
   physical world."); the headline and the two actions stand. The copy
   after the hero is the owner's fixed text in the Home copy file, in the
   same order: "What is Physics by Construction?", "Build. Experiment.
   Understand.", "From computational physics to artificial intelligence"
   (replacing "What you can learn"; Part A, Part B, and the transition
   "First understand the physics. Then challenge the AI.", each with its
   own text in the Home copy file, while the journey file's longer text
   stays on the atlas and About), and "How we verify what we teach"
   (replacing "How the results are kept honest"), the quietest section.
   Home shows no example lesson: the at most one owner-chosen lesson per
   part of the amendment of 2026-11-04 is withdrawn, since lesson discovery
   belongs to the Course Atlas. After Part A the eight course subjects are
   named compactly from the curriculum, plain text, a course without a
   published lesson marked as planned. The introduction no longer opens
   with the canonical attribution, which About and the footer keep, and
   keeps the one link to About. The word "discover" has no rule on Home,
   which is not part of the curriculum (owner's decision, Issue #481); the
   journey file and the lessons keep the strict rule.

   *Amended on 2026-11-11 by the owner's decision of Issue #482 (Home: the
   hero as one large fluid-dynamics illustration).* The hero image is one
   illustration, not one of four picked at random: the vortex street of
   fluid dynamics, interface artwork of decision 1 derived from the master
   of its atlas illustration (ADR 021 decision 2: registered with the
   master's origin and hash) as the master's middle 2:1 band, mirrored so
   that the flow runs from right to left with the cylinder toward the
   right, and faded in the file's own alpha channel toward the left and at
   every edge, so that no rectangular boundary shows on the paper; one file
   per width (1200, 1800, and 2400 px), the browser requesting the one
   sized for its viewport through `srcset`. The image stands in the HTML as
   one `<img>`: the hero script and the `hero-image` parameter are gone,
   the page with and without scripts is the same, nothing in the hero
   runs, blocks, moves, or animates (a static image; no GIF, video,
   canvas, or animation dependency), and exactly one hero file is
   requested per load. The three other hero-size files leave the site and
   the register; their masters stay registered through the atlas entries
   of their courses. From 992 CSS px the hero is one composition: the
   image is the ground of the hero at 78 % of its width (the owner's 70 to
   80 %), aligned to the right edge of the column, and the headline, the
   subtext, and the two actions stand in the left column over the faint
   end of the trail, where the fade keeps the ink at a quarter at most; the
   text's contrast is measured on the render, not assumed. Below 992 px
   the composition is stacked, not shrunk: the copy, the actions, then the
   image at the full width of the column. A mirror image of the flow is a
   valid flow (the equations are invariant under reflection; the shedding
   still alternates, and only the sign of the vorticity, which nothing on
   the page states, is reversed); the alternative text names what is seen
   and claims no result. The fixed text, the data file, its validation,
   the one `<h1>`, the two actions, the measurable above-the-fold rule of
   2026-11-10 (now with a 2:1 image), no storage, no request beyond the
   image, and no measurement of what works better stand.

   *Amended on 2026-11-12 by the owner's request of Issue #487 (Home: the
   hero image replaced by the double-pendulum illustration, wider, with a
   fade on the left).* The hero image is the owner's own illustration of a
   double pendulum at the left, a dotted trace with a dashed curve through
   the middle, and a ball in a glowing well at the right, in place of the
   vortex street: interface artwork of decision 1, registered (decision 2)
   as a derived raster from the owner's master
   `pbc_hero_assets/pbc-double-pendulum-hero-original.png` with its hash,
   by its author and date, with no statement of how it was made and no
   licence (decision 2 as amended on 2026-11-12: the hero carries none in
   the register; the owner's decision of 2026-11-12); the vortex street
   stays registered
   through the atlas entries of fluids. The files are the master's frame
   (2:1; 1774 px wide at most, the master's width, so nothing is upscaled)
   blended over the paper: the illustration's ground keyed to the paper,
   the part under the copy of a wide screen (the left 47 %) lifted pixel
   by pixel toward the paper by what the text's contrast needs, so that
   the pendulum stays a pale drawing rather than vanishing, and every edge
   faded in the alpha channel; no mirror and no crop. From 992 CSS px the
   image is wider than before: it starts at the left edge of the content
   column and runs past the column to the right edge of the viewport (the
   column plus its gutter, 1207 px at 1280 against 885 px before, by a
   container unit of the page grid and never `100vw`), with the copy and
   the actions in the left 46 % of the column over the lifted part; the
   text's contrast is measured on the render, as before. The image is an
   illustration, not a result of the project: the trace and the curve it
   shows are nobody's data, and its alternative text names what is seen
   and claims no measurement. One file per width (1200, 1480, and 1774
   px), one request per load, no script, nothing moves; the stacked
   composition below 992 px, the fixed text, the data file, the measurable
   above-the-fold rule, and the rest of the amendment of 2026-11-11 stand.
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

   *Amended on 2026-11-10 by the owner's decisions of round 2 of F158
   (Issue #462).* The four menu items, the mark, and the search stay on
   every page. Below 640 CSS px the header is one line, the mark, the site
   name shortened visually to "PBC" (the full name stays the home link's
   accessible name), the search control, and a menu toggle; the four items
   are in a native `<details>` menu, open in the HTML so that a reader
   without scripts has them under the bar, and closed at load by a small
   script that also closes it on Escape; the toggle is named and exposes
   its state. From 640 CSS px the items stand in the bar as before. No
   new dependency; Quarto's own collapse, which needs its script, stays
   off.
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
