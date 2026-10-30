# Change request: a quieter site, a two-layer course atlas, and generated artwork on non-lesson pages

Date: 2026-10-30. Owner: Ahmet Taspinar. Written with the agent after the
review of the site's pages (2026-10-29) and of the delivered illustrations
(2026-10-30). The four feature Issues exist: #337 (F132), #338 (F133), #339
(F134), #340 (F135). The roadmap blocks of F132 to F135 are to be added by
this change cycle, and the Issue numbers recorded in them.

## What I want

The site treats navigation, documentation, and scientific accountability as
equally important to every visitor. They are not. A new visitor wants to know
what PBC is and where to begin; a researcher wants to know whether the
results reproduce; a contributor wants instructions.

1. **A four-item menu** (Home, Course Atlas, About, Start learning), with
   Run the code, Glossary, Scientific evidence, For educators, Contribute,
   and Source in the footer; About corrected and refocused (F132).
2. **The Course Atlas as a navigation page, not a map**: twelve sequence
   cards (eight courses, four method paths) and, beside them, the lessons of
   the selected one; an accordion on a phone; usable without scripts. The
   concept map with its edges, the Lean and method bands, and the lesson
   repetition go (F133).
3. **Home as a landing page**: the opening, three example lessons, one
   capstone, an invitation; **Run the code** opening with three routes; a
   readable page **How we verify the science** (F134).
4. **The glossary in context** and a **Suggest an improvement** link on every
   lesson that opens a pre-filled GitHub issue form (F135).

## Decisions already taken

- **Artwork.** The twelve illustrations of the atlas and the hero of the home
  page may be **generated raster images** (WebP): computed by scripts of the
  owner, or made by an image model, always physically correct and **without
  text, numbers, or formulas**. They are allowed on non-lesson pages (the
  home page, the atlas, course openings), never in a lesson and never as
  evidence. For these pages a diagnostic plate, a visible disclaimer, and a
  script per image are not required (they are welcome where they exist).
  This changes **requirements decision 37** ("a raster file stays excluded")
  and **ADR 018 decision 2**.
- **Atlas shape.** Mock 3 and mock 4 (held by the owner) are the design: the
  cards left, the open panel right, native `<details name="atlas">`, `::details-content`
  for the wide layout with the accordion as fallback, one module of about
  twenty lines for the hash.
- **Hero copy.** Three headlines and eight subtext pairs, shown **at random
  per visit**, one fixed default in the HTML, `?hero=` to force one. **No
  measurement** of which pair works better (it would need a collector).
- **Hero image.** Built from the computed illustrations, with the labels as
  text, not the delivered composite with its labels baked into the pixels.
- **No backend.** A form on the site that creates GitHub issues without a
  GitHub account is **not** part of this change; it needs a server and a
  stored credential and would change the requirement "no backend, no
  secrets". It is recorded as an open decision for the owner.
- **Astrophysics image**: the exoplanet transit. **Part B**: the text-free
  versions.

## What this changes

- Requirements: decision 37 (raster artwork on non-lesson pages) and the
  statements of decision 36 about the home page's opening and the atlas's
  map and views.
- ADR 018: decision 2 (a derived WebP, with its provenance, as interface
  artwork), decision 3 (the map with three edge types and the view bands are
  replaced by the two-layer atlas; the three relationship types stay in the
  manifest and on the lesson pages), decision 4 (the opening headline, and
  the home page's Part A, Part B, and capstone blocks).
- The committed-artifact check: an exemption for registered WebP under
  `site/assets/`, bound to the provenance register as the SVG exemption is.
- Architecture, "Atlas modules"; the roadmap blocks of F124, F125, F126 get a
  note naming F133.

## Order and dependencies

F132 first (the menu), then F133 (the atlas and its artwork), then F134 (the
home page, which links into the atlas), with F135 independent but sharing the
lesson template and the shared CSS with F133: not written in parallel in one
worktree.

## Open for the planning

1. Whether the illustrations are rendered at build time or committed as
   derived files with their scripts (recommended: committed, with a
   regeneration check on demand; the scripts have not been timed in CI).
2. The contribution form without a GitHub account: yes or no, as its own
   decision.
3. Where the hero's text and the courses' one-line descriptions live
   (recommended: the atlas manifest and one data file, never on a page).

## Material

The delivered illustrations and their scripts, the derived WebP sizes, the
text-free Part B masters, and the mock sources are staged for the planning
worktree under `docs/changes/site-navigation-and-atlas/`.
