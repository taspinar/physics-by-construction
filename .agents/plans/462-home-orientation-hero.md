# Plan: F158, Home: orientation, the hero image from four Part A illustrations, and the first step (Issue #462)

Level 3 by trigger: the tests of the examples chosen by code, of the capstone
choice, and of the constellation image are removed or replaced (the roadmap
risk and the Issue). The approval request is
`.agents/approvals/462.md`. Implementer: Opus. No ADR, requirements, or
roadmap change: ADR 021 decision 4 as amended on 2026-11-04 already decides
the change. `docs/architecture.md` and `docs/atelier.md` are brought up to
what is delivered.

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f

- **Page and layout** (Home and its hero), with the two skills above
  (impeccable in its Persuade mode within the restraint of the brief:
  `reference/craft-floor.md`, `reference/mode-persuade.md`,
  `reference/layout.md`, `reference/adapt.md`). Expected artifact: the
  rendered `index.html` at 1280 by 800, 768, 390 by 844, 360 by 640, and
  320 CSS px, and at 200 % text scaling, with each hero image forced.
  Validation: the layout tests of `tests/e2e/test_home.py`, the payload
  check, the accessibility scan, the keyboard pass, and the reflow that
  every page gets, the rendered review, and the owner's approval of the
  hero on the rendered page (`owner_approval`). Accessible fallback: the
  default image (the double pendulum) and the whole copy without scripts;
  each image's alternative text from the hero data file.
- **Interface artwork**: four derived WebP files from the owner's masters,
  no new illustration. Validation: the visual check of ADR 021 decision 1
  (composition, legibility at the size shown, family, no text, number, or
  formula in the pixels), recorded in the completion evidence; the register
  rules of the committed-artifact check. No scientific figure, no
  conceptual diagram, no animation.

## Decisions taken in this plan

- **Hero size.** One file per image, `site/assets/hero/<id>.webp`, 1200 by
  900 px (4:3 like every master), WebP quality 88 on the page's paper, as
  `tools/illustrations/derive_assets.py` derives the atlas sizes. The image
  is drawn at most about 600 CSS px wide (the right column at 1280 px), so
  1200 px covers a 2x screen. Every master is at least 1448 px wide (the
  exoplanet transit), so nothing is upscaled. No `srcset`: the criterion
  asks for exactly one hero image request per load, and one size keeps
  the request count and the payload measurable.
- **The image parameter** is `hero-image`, separate from `hero` (the
  headline pair). Its values are the image identifiers of the hero data
  file: `double-pendulum` (default), `vortex-street`, `hot-cold-gas`,
  `exoplanet-transit`.
- **Exactly one request.** The default image stands in the HTML inside a
  `<noscript>` element of the hero's figure. With scripts the parser and the
  preload scanner treat `<noscript>` content as text, so the default is not
  requested; `site/learner/hero.js`, parser-blocking right after the figure,
  creates the one `<img>` of the image it picks (from the image data the
  build embedded beside the pairs) and so requests exactly one hero image.
  Without scripts the `<noscript>` image is shown; a crawler that reads the
  HTML sees the default. A plain `<img>` with the default in the HTML would
  be found by the preload scanner while the script loads and requested as
  well as the picked one (two requests), which the criterion forbids.
- **No layout shift.** The figure reserves the 4:3 box in CSS
  (`aspect-ratio`) with the image's `width` and `height`; the swap of the
  image fills the same box.
- **Hero data file.** `site/hero.yaml` gains one field, `images`: `default`
  (an image id) and `set`, a list of `{id, sequence, alt}`: the atlas
  sequence whose master the file is derived from, and the alternative text.
  The file path is derived from the id; the register binds the file to its
  master. Validated by `pbc.authoring.home` like the pairs: ids unique and
  plain, the default in the set, every sequence a course of Part A, the alt
  text plain and non-empty, no other field.
- **Register entries.** `hero/<id>.webp` in `site/assets/provenance.yaml`
  with the origin, licence, date, master, and SHA-256 of the atlas panel
  entry of its sequence (the masters' hashes were matched on the Issue on
  2026-11-09), the exoplanet transit by its author with no script. A unit
  test checks that each hero entry's master and hash equal its atlas
  panel's.
- **Home copy file.** `site/home.yaml`, read by `pbc.authoring.home`:
  `identity`, `philosophy`, `curriculum`, `integrity`, in that order, each
  with a `heading` (plain text) and, except `curriculum`, `text` (a list of
  inline-Markdown paragraphs under the journey's text rules: references
  `{sequence:}`, `{slot:}`, `{term:}` resolve, no count, no lesson named
  outside a reference, no "discover"); `curriculum` holds `examples`, a
  mapping of `part-a` and `part-b` to a slot label each (optional: absent
  means none). The page writes the four sections in the file's fixed order.
  Identity opens with the canonical sentence of `pbc.authoring.identity`
  (F57) and ends with the one attribution link; integrity ends with "How we
  verify the science" and the source. "What you can learn" is the journey's
  Part A, Part B, and relation text (`site/journey.yaml`, one source with
  the atlas and About), each part followed by its owner-chosen lesson.
- **Example validation at build time.** A Part A example names a slot of a
  course, a Part B example a slot of a method path; the slot must have a
  published lesson, or the build fails. Owner's choice on the Issue: Part A
  `M1` (`mechanics/01-kinematics-as-a-program`), Part B `SA5`
  (`agents-llm/01-an-agent-runs-an-experiment`).
- **The first step.** Home's hero: "Open the Course Atlas" (primary, the
  filled control, to `path/index.html`) and "Start with the first lesson"
  (secondary, a text link, to the first lesson of Part A). The header's
  Course Atlas link and Start learning button lead to the same two pages
  (an e2e test compares the addresses). The "Begin" section leaves: the
  first step is in the hero, and integrity is last.
- **Anchors.** `#about-the-site` stays (identity); the new sections are
  `#how-physics-is-learned`, `#what-you-can-learn`, `#integrity`. Nothing
  links to the old `#examples` or `#begin` (searched).

## Found while building (2026-11-09)

- **The phone fold.** The copy keeps the height of the longest pair (F134).
  At 360 by 640 the primary action fell below the fold with the 2rem
  headline; below 30em the headline is 1.75rem and the subtext 1.125rem,
  which keeps the message and the primary action on the screen at 360 by
  640 and 390 by 844 (the secondary is just below the fold at 360 by 640,
  as the requirements allow). At 320 by 568, where the header alone takes
  176 px, the actions follow the message below the fold; the image is not
  shrunk or moved for it. The test at 320 checks the reflow, the order,
  and the absence of overlap; the owner's pass on the rendered page
  decides the rest.
- **200 % text.** Home's content reflows without horizontal scroll at every
  size (single-column grids are `minmax(0, 1fr)`, long words break). The
  shared header of every page (F132) is wider than 320 CSS px at 200 %
  text, on About as on Home: outside this Issue, recorded for a follow-up.
- **The paper.** The masters' white is lighter than the page's paper, so
  the image showed a faint box; the figure is an isolated box on the
  paper and the image is blended with `darken`.
- **The rendered review** screenshots are in `.agents/reviews/462-rendered/`
  (ignored by Git): each image forced at 1280 by 800, 768 by 1024, 390 by
  844, 360 by 640, and 320 by 568, each size at 200 % text, and the whole
  page without scripts.

## Steps

1. Derive the four hero files with `derive_assets.py` (a `HERO` mapping and
   size added; run outside the build on the owner's masters), register them,
   and view each for the visual check.
2. Extend `site/hero.yaml` and its reader with `images`; failing tests per
   rule first.
3. `site/home.yaml` and its reader; failing tests per rule first (unknown
   field, missing section, markup in a heading, a broken reference, a count,
   "discover", an example of the wrong part, an unpublished example).
4. `pbc.authoring.home`: the page from the copy file and the journey; the
   hero figure with the `<noscript>` default and the embedded image data;
   the two actions. The constellation image, the examples, the capstone,
   and their code and CSS leave.
5. `site/learner/hero.js`: pick a pair and, independently, an image (or the
   ones the parameters name); create the one image; nothing else.
6. CSS: the hero grid (copy and actions left, the figure right from 992
   px; copy, actions, figure on a narrow screen), the figure box, the
   secondary action, the four sections at the measure.
7. Tests: unit (data files, markup, register binding, the script scan),
   the integration build test (the examples follow the copy file, not the
   lessons), e2e (one image request per load with the payload measured,
   each image forced, the default without scripts, independence from the
   pair, no shift, the layout at the five sizes and at 200 % text, the two
   destinations equal to the header's).
8. Docs: `docs/architecture.md` (Home, the textbook-layer gap list),
   `docs/atelier.md` (Home page, the composed hero row), `tools/illustrations/README.md`.
9. Rendered review: screenshots at the sizes above with each image forced,
   for the pull request; the owner's approval follows on the Issue.

## Verification

Per the Issue: no complete `./scripts/verify.sh` in the session (the script
after the session runs it); the affected tests, `--only code`,
`--only default`, and `--targeted` when it selects.
