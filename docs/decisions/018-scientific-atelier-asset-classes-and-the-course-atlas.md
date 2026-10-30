# ADR 018: The scientific atelier: three visual asset classes, and the course atlas generated from the curriculum, the lesson metadata, and one map manifest

## Status

Proposed with the planning of the change cycle `scientific-atelier-atlas`;
accepted when that planning is approved. Amends one decision of an ADR:
condition 2 of the replay-fixture decision of
[ADR 002](002-regenerate-artifacts-and-display-by-reference.md), whose
committed-artifact check exempts the replay-fixture location "and nothing
else", gains one further declared exemption (decision 2 below): an
authored interface-artwork SVG under `site/assets/` whose provenance
entry records its author and licence, the third kind of committed input
a build cannot regenerate, after the replay fixture of ADR 002 and the
dataset samples of [ADR 007](007-real-datasets-as-declared-inputs.md).
ADR 002's status names this amendment; its other decisions are
unchanged, and the exemption extends to no raster and to no other image
type anywhere. Supersedes no other decision of an ADR.
Supersedes, as far as decision 37 of the requirements says, the blanket
exclusion of decorative imagery and animation that was recorded outside
the ADRs: the requirements' non-goal before that decision, the out-of-scope
lines of the roadmap blocks F44 ("decorative imagery, any branding graphic")
and F64 ("images that are not F63 previews; animation"), and F25's
exclusion of hero imagery, for the one opening figure of the home page.
Those blocks stay as history and carry a note that names this record.
Extends [ADR 013](013-eight-courses-and-the-reference-curriculum.md): the
curriculum file stays the one declared source of the planned structure, and
the map manifest of decision 3 adds only what neither it nor the front
matter holds. Extends ADR 002 otherwise: interface artwork is produced
by code at build time or carries its authored source in the repository,
conceptual illustrations are drawn by code in executed cells; nothing
generated is committed. Reaffirms the Quarto baseline of
[ADR 001](001-quarto-static-site-with-build-time-execution.md).
Delivered by F123 to F127; the interactive pendulum of decision 4 by F128,
if the owner decides it.

Superseded in part by
[ADR 021](021-quieter-site-two-layer-atlas-and-raster-interface-artwork.md)
(2026-10-30, change cycle `site-navigation-and-atlas`, requirements
decisions 40 and 41): in decision 2, the definition, places, and sources
of interface artwork ("never a raster file") and the committed-artifact
exemption, which now also admits a registered derived raster (WebP or
PNG) under `site/assets/`; in decision 3, the map with its three edge
types, the Lean and method view bands, the switch, selection, zoom,
filters, the region selector, the course areas' illustrations drawn by
code, and the rule that the manifest holds no illustration reference,
replaced by the two-layer atlas; in decision 4, the opening headline and
figure, the Part A and Part B introduction, and the capstone highlights,
replaced by the hero and the landing page. The rest of those decisions
and decisions 1, 5, and 6 stand; ADR 021 lists what stands. Delivered by
F132 to F135.

Date: 2026-10-17

## Context

The owner adopted a visual direction for the site (requirements decision
36, "Visual direction"): a scientific atelier with the quality of a
carefully designed scientific publication and optional interactive
experiments, after considering five alternatives, and the physics-map
concept as the direction for the course atlas. The change is more than
colours: the hierarchy of the home page, the navigation, the interaction
of the course map, the shared page templates, and the presentation of
published against planned material change.

The site today has one short visual system (F44: tokens in
`site/assets/site.css`, with the colours defined once in
`src/pbc/authoring/design.py` and a contrast test) on Quarto's default
theme, a home page that names the three activities (F25), and a
course-first Learning Path page generated from the front matter and the
curriculum file (F62 to F64), with one self-hosted font (the math font).
The restriction "no decorative images" (the requirements' earlier
non-goal, F44, F64) prevented misleading, irrelevant, or unverifiable
visual material; the owner found it too broad for the direction and
replaced it by three asset classes (decision 37).

The atlas needs information the site does not hold: concepts, their
placement on a map, which slots a concept belongs to, and the scientific
connections between concepts. The temptation is a second, hand-written
lesson catalogue, which ADR 013 and invariant I28 rule out. The mockups
that chose the direction show six regions where the curriculum has eight
courses, and their equations, plots, and illustrated measurements are not
verified science. A map can suggest relationships it cannot support, can
present a planned slot as a lesson, and can be unreachable without a
script. Everything shared (CSS, templates, assets) is a shared input of
ADR 014 decision 4, so a change to it is a full verification run.

## Decision

1. **The baseline stays; the visual system is scoped CSS, shared
   templates, and self-hosted fonts.** The Quarto site of ADR 001, the
   `.qmd` lessons, the Python generators of `src/pbc/authoring`, native
   MathML, GitHub Pages, and the verification pipeline are unchanged. The
   direction is implemented as tokens and component styles in
   `site/assets/site.css` that extend the F44 system (the colours still
   defined once in `src/pbc/authoring/design.py`, the contrast test
   kept), shared templates and includes for the header, the footer, the
   course, module, and capstone openings, and the lesson reading column,
   and fonts served from `site/assets/fonts/` with their licence texts
   beside them. No frontend framework, no Node or JavaScript bundler, no
   second site generator, no KaTeX or other equation renderer, no backend,
   authentication, hosting migration, runtime service, or paid model or
   API requirement; the payload budgets of the architecture are measured
   for the complete initial page and for the map enhancement; WCAG 2.1
   AA, the 320 CSS px reflow rule, visible keyboard focus, and reduced
   motion hold on every page.
2. **Three visual asset classes.** Every visual on the site belongs to one
   class and is identifiable as such:
   - **Interface artwork**: visual identity and navigation (the project
     mark, the map's course areas and their small illustrations, the
     openings of courses, modules, and capstones). Allowed in the site
     chrome, on the home page, on the atlas, and in course, module, and
     capstone openings. Produced by code in the repository at build time
     (as the previews and the prerequisite graph are), or an SVG source
     authored for this project and committed under `site/assets/` with
     its author and licence recorded; never a raster file, never stock,
     copied, or externally hosted. It makes no scientific evidence claim,
     carries no caption of a result, and no number: its alternative text
     names what it is or marks it decorative where it conveys nothing.
     The authored SVG is the third kind of committed input a build cannot
     regenerate, and the committed-artifact check of ADR 002 (which
     rejects every tracked image file under `site/` and `src/`) admits
     it by one declared exemption and nothing else: a tracked `.svg`
     under `site/assets/` is exempt only when the provenance register of
     the asset-source rule (F123) names it with an author and a licence;
     an unregistered `.svg`, a raster of any type anywhere, and every
     other image type stay rejected everywhere, including under
     `site/assets/`. The exemption and the provenance entry are one
     mechanism: an SVG without its entry fails both checks, and an entry
     without its file fails the asset-source rule. A generated SVG is
     written by the build and is never tracked.
   - **Conceptual illustration**: a scientifically sound explanatory
     diagram inside a lesson, allowed when it genuinely improves
     understanding, under the existing rules for conceptual diagrams
     (drawn by code in an executed cell, labelled `conceptual`, never
     presented as a numerical or experimental result). The approved
     Diagram Design guidance of ADR 019 informs it; its science and
     semantics are checked independently of any skill. Requirements
     decision 37 permits a conceptual illustration to be either generated
     by repository code or authored as a committed SVG; this record takes
     the narrower choice within that permission, as a planning choice and
     not a reading of the requirements: lessons keep conceptual
     illustrations code-drawn in an executed cell, because everything that
     verifies a lesson's figure acts on executed cells (the figure-status
     check and its `conceptual` label of F28, the figure-writing pattern
     of ADR 016 with the experiment and reproduction checks, the
     lesson-layout check under which a lesson directory holds only its
     page and its replay fixture, and the F129 pilot, which compares a
     redrawn diagram with the existing code-drawn one and preserves
     values and commands through those checks). An authored conceptual
     SVG in a lesson is a later decision, taken when a lesson feature or
     the F129 pilot shows a need the code-drawn form cannot meet; it
     would add a display form for a non-cell image with its status label,
     a lesson-directory layout rule, and an extension of the
     committed-artifact exemption above, in an ADR that names this one.
   - **Scientific result**: plots, simulations, measurements, under the
     unchanged rules of "Scientifically faithful figures", the verified
     display forms, and the F63 preview contract.
   An **animation** is allowed in any class when it is pedagogically
   justified, accessible, and accompanied by a meaningful static
   alternative: it starts paused or respects the reduced-motion
   preference, has play, pause, and reset controls with units and
   sensible parameter limits where it has parameters, is never mandatory
   for a lesson, and is never rendered in CI as a routine step. Nothing
   visual is added for decoration's own sake, as an evidence claim it
   cannot support, or as a mandatory element of every lesson. A diagram
   presented as a lesson result follows the scientific generation and
   checking rules; no mockup equation, plot, or illustrated measurement
   ships as verified science. Lesson rows keep the F63 previews; map
   artwork is a distinct class, not a replacement for them. Every asset
   of the first two classes has its generating source or its authored
   source in the repository, and the completion evidence of the feature
   that adds it links the rendered artifact to that source.
3. **The course atlas at the existing path address, from one source of
   truth and one map manifest.** The Learning Path page becomes the
   course atlas ("the atlas" may be its display label; the address
   `/path/` and every existing anchor, bookmark, and graph node address
   stay valid). Course, path, and slot information comes from
   site/curriculum.yaml; publication state, titles, prerequisites, and
   canonical addresses from the lesson front matter. One small validated
   map manifest (a YAML file beside the curriculum file, read by
   `pbc.authoring`) holds only what those do not represent, in the words
   of the requirements: concept identifiers (each with its short
   explanation), display placement, concept-to-slot associations, and
   curated conceptual connections with their rationale. Nothing else: the
   course areas' illustrations are interface artwork drawn by code, and
   the generator maps each course of the curriculum file to its drawing,
   so the manifest holds no illustration reference; capstone membership
   is a concept-to-slot association whose slot is a capstone slot; the
   manifest admits no lesson reference (a lesson reaches the map through
   its slot, or through the Lean and method views below). Rules, each
   enforced by a check that fails the build: every course, path, slot,
   and concept reference in the manifest resolves (the schema defines
   course, path, slot, and concept references only, and rejects any field
   it does not define; it admits no lesson reference, so the requirements'
   lesson-reference rule holds vacuously); a concept names at least one slot and membership
   is never inferred from a lesson's title; every capstone slot of the
   curriculum file is represented by exactly one concept; no title, description,
   outcome, prerequisite, or count is written in the manifest; no second
   lesson catalogue exists. The map distinguishes three edge types
   explicitly, each with its own mark and its own words in the textual
   equivalent: a **conceptual connection** (curated, with its rationale
   shown on selection), a **prerequisite** (generated from the existing
   prerequisite data of the front matter, never written in the manifest
   and never invented for a planned lesson), and **capstone membership**
   (the concepts a real project integrates, linked only when the capstone
   is published). Modes may show concepts and prerequisites separately.
   Course areas may have subtle boundaries and meaningful small
   illustrations, never a geography that suggests a relationship the
   manifest does not state. The Lean and method views are part of the
   map: they list every published lesson by its method tags from the
   front matter, the lessons without a slot included (the Lean lessons
   beyond the baseline), as links in the SVG's view layer and as
   sentences in the textual equivalent, derived from the front matter
   with no manifest entry; a concept's lessons still come only from the
   slots it names, so no concept-to-lesson association exists. The map
   shows the reference curriculum: a planned concept or slot is visibly
   labelled and distinguishable without colour alone, is never a lesson
   link, is never counted as published, and may reveal its planned
   description without implying usable content; published counts come
   from actual lessons. Every capstone slot (T11, EM9, FL10) is
   represented by a concept of the manifest, and the short explanation of
   that concept, kept consistent with the roadmap's description of the
   capstone, is the planned description: the one place that text lives,
   which the atlas reveals and the home page's capstone highlights show,
   read by `pbc.authoring.home` through the same validated reader; the
   curriculum file gains no description field (ADR 013 decision 3 is
   unchanged) and no page carries the text by hand. The thermal (T11) and
   tsunami (FL10) capstones are shown as planned with those descriptions,
   the thermal project as a hypothetical accelerator and never a named
   commercial chip, and the EM9 phased-array capstone stays in the index
   and on the map. The generator writes, at build time, semantic HTML,
   inline SVG with real links and text, and a visually hidden textual
   equivalent of the map (every concept, its course, its slots, and its
   edges as sentences; every lesson of the Lean and method views), beside
   the complete
   course, module, and lesson index of F64 with its metadata, progress
   marks, recommendations, filters, and search integration, and the
   capstone links or labelled planned projects. Small dependency-free
   ES modules enhance the structure (selection, the selected-concept
   panel, zoom, filters, the switch between map and index, and the phone's
   region selector); they make no request, set no cookie, and use no
   browser storage; `site/learner/progress.js` stays the only script that
   stores anything, under its existing contract. Every published lesson
   stays reachable with scripts disabled through native links and
   disclosures. On a phone the page offers a readable region selector, a
   focused map view, and the ordinary list; a desktop map is never shrunk
   until its labels are unreadable. No generated raster image is the
   navigation surface.
4. **The home page.** A shared header with a small project mark, concise
   primary navigation, and a clear start link; the opening "Build a world.
   See if it obeys physics." with a static figure produced by an existing
   verified Python implementation through the figure-writing pattern of
   ADR 016 (the double-pendulum lesson's implementation if its validation
   is judged sufficient by the feature, otherwise another verified
   mechanics figure), composed in the atelier language, scientifically
   faithful to the model, carrying its status label and provenance; the
   introduction of Part A and Part B derived from the real course
   structure with links into the atlas; capstone highlights grounded in
   the current delivery state; a short invitation to begin; the shared
   footer with attribution, source, licences, and secondary navigation.
   The section "From a question to a working model" is absent and is not
   replaced by a renamed three-step teaching formula. No fake metrics,
   testimonials, or inferred learner progress; no JavaScript physics or
   illustrative motion that the build did not verify. Interactive
   controls and animation of the opening figure arrive only with the
   validated interactive pendulum: its own feature, after a numerical
   validation and a cross-language reference check of the browser
   implementation against `src/pbc` (the test of the verified display
   forms for a widget that computes in the browser), decided by the
   owner.
5. **The remaining templates** keep every scientific and navigational
   contract: lessons keep their section identifiers, claims, calculations,
   results, references, and the experiment section with its anchor
   (ADR 016); course and module openings reuse the existing course
   sections and add a route only for a clear purpose named in the
   migration plan; capstones may frame visualizations in dark navy with
   instructions readable; the About and supporting pages keep the
   glossary, the evidence map, the setup page, contribution, search, and
   the licences. The redesign changes presentation and navigation, never
   lesson text, scientific code, computed values, units, reference keys,
   or claims, which change only through a separate reviewed change; no
   narrative structure is imposed on lessons; the editorial programme of
   decision 32 (F114 to F116) is coordinated with, not merged into, it. An
   experiment gallery is deferred until enough real browser experiments
   exist; no empty gallery and no link to an experiment that does not
   exist.
6. **Verification and review.** Shared CSS, templates, includes, fonts,
   and generators are shared inputs of ADR 014 decision 4: a pull request
   that changes them is a full run, and the redesign is never promised to
   be a targeted-only change. No check is weakened for a visual match;
   determinism and provenance are preserved. The regression checks are
   data, link, reference, and interaction checks (the manifest rules
   above; every lesson reachable without scripts; every previous address
   and graph node address; the published counts; the edge types against
   the front matter; the accessibility scan; the keyboard pass; the
   reflow at 320 CSS px; the payload; the absence of browser storage and
   requests; the asset-source rule of decision 2), never tests that
   reproduce CSS values, screenshot pixel comparisons, or full renders on
   an ordinary lesson change. Rendered visual review has three parts:
   the implementer records screenshots at desktop, tablet, and phone
   widths as evidence artifacts of the feature (never as committed site
   assets); the independent reviewer assesses them with the built HTML
   and the sources; the owner's manual pass on the preview is the final
   visual acceptance. The first delivery is one end-to-end preview of the
   home page, the atlas, and one existing lesson, inspected by the owner
   at desktop, tablet, and phone widths before any broad rollout; the
   display label of the atlas and the navigation wording are settled in
   that review.

## Alternatives considered

- **Astro or another site generator for the new pages.** Rejected: ADR 001
  and the whole verification pipeline (execution, reproduction, digests,
  the context cells, the built-site checks) are built on Quarto; a second
  generator would duplicate the display forms and the checks. The earlier
  Astro suggestion was exploratory.
- **A CSS framework, a bundler, or a web-font service.** Rejected: I3 and
  I10 (no other-origin resource, no JavaScript toolchain), and the payload
  budget; scoped CSS with tokens is what F44 already does.
- **KaTeX for nicer equations.** Rejected: MathML is script-free and read
  by assistive technology; the math font is already self-hosted.
- **A canvas or a generated raster image as the map.** Rejected: no real
  links, no selectable text, no scaling, nothing for a screen reader; SVG
  gives precise typography, links, and scalable drawing. Canvas is allowed
  only for an optional animated experiment with a static equivalent and
  accessible controls.
- **The six-region mockup as the map's structure.** Rejected: the
  curriculum has eight Part A courses and four Part B paths, and the map
  shows the approved curriculum, not a sketch.
- **Inferring concepts from lesson titles, or a hand-written lesson
  catalogue for the map.** Rejected: ADR 013 and I28 give the curriculum
  one source; the manifest holds only what nothing else holds, and every
  reference in it must resolve.
- **Storing the map's selection, zoom, and filters in browser storage.**
  Rejected: the F13 contract keeps `progress.js` the only script that
  stores anything, and the controls' state is not learner data.
- **A temporary JavaScript animation of the pendulum to meet the design.**
  Rejected: unverified physics on the home page, against I5 and the
  widget rule; the static verified figure comes first, the interactive
  pendulum is its own gated feature.
- **Keeping the blanket exclusion of decorative imagery.** Rejected by
  decision 37: its purpose is kept by the asset classes and the source
  rule; the exclusion of stock, copied, and external imagery stays.
- **Interface artwork drawn by code only, so that ADR 002's check stays
  untouched.** Rejected: requirements decision 37 permits the authored
  route, the owner chose it for the project mark, and a check that
  rejects what the requirements permit would be met by an ad hoc
  weakening in the first pull request; the declared, provenance-bound
  exemption of decision 2 is the recorded change instead.
- **Admitting an authored committed SVG as a lesson's conceptual
  illustration now.** Not chosen (decision 2): the lesson checks act on
  executed cells, no candidate of the change request asks for it, and it
  would need a new display form, a lesson-directory layout rule, and a
  wider committed-artifact exemption; it stays available to a later
  decision.
- **An experiment gallery now.** Deferred: the two widgets that exist do
  not make a gallery, and an empty one or links to nonexistent
  experiments would advertise what is not published.

## Consequences

- Every page gets the new chrome at once when the foundations land, so
  the site never shows two headers; the reading-column lesson template is
  applied to one existing lesson first and to every lesson in the rollout,
  and in between the lesson bodies differ in layout, not in content.
- Every pull request that touches shared CSS, templates, fonts, or the
  generators is a full run (the `build` job of a full run was measured at
  21 to 31 minutes with thirty-two lessons before the experiment check of
  F117 joined it); the slices of the roadmap are cut so that a feature
  changes shared inputs in as few pull requests as it can.
- Self-hosted fonts add to the shared payload of every page; the feature
  that adds them measures the complete initial page against the 3 MB
  budget and records the sizes, and subsets or drops a face that does not
  fit.
- The map manifest is a curated scientific artifact: every conceptual
  connection and every concept-to-slot association is reviewed
  independently as a scientific claim about the curriculum, with its
  rationale, before it is merged.
- The roadmap blocks of F25, F44, and F64 carry a note naming this record
  where their out-of-scope lines are superseded; their delivered criteria
  stay as history, and F62, F63, F64 are built on, never reopened.
- Two invariants are added to the architecture: the asset classes with
  their sources (I30) and the atlas's data contract (I31). Invariant I6
  and the Boundaries list name the authored interface-artwork SVG as the
  third committed input a build cannot regenerate, and F123 narrows the
  committed-artifact check to the declared exemption with a failing test
  per case (a registered SVG accepted; an unregistered SVG, a raster, and
  every other image type rejected) in the same pull request that adds
  the provenance register, so that the check is never weakened beyond
  what this record declares.
- Lesson authoring is not blocked: shared template and metadata changes
  are coordinated through the dependency tables, and an independent lesson
  feature proceeds under the verification capacity of the day.
