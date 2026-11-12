# Plan: Home, the hero as one large fluid-dynamics illustration (Issue #482)

Follow-up of F158 (Issue #462) after the sibling Issue #481 (the copy and
the structure, merged as ff9c3c3). The owner's decision of 2026-11-11: the
hero is one large fluid-dynamics illustration, the vortex street of the
Part A fluids atlas master, mirrored so that the flow runs from right to
left, faded toward the left and at every edge, integrated with the
headline, the subtext, and the two actions. Static, no new dependency.
The copy and the sections below the hero are out of scope.

**Level 3.** Paths: `docs/decisions/021-…` (ADR 021 decision 4 amended),
`docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md` (protected). Triggers:
tests and a script removed or replaced (the list under "Tests"; the hero
script `site/learner/hero.js` with its unit tests). The owner approves the
exact head at the merge gate; the approval request `.agents/approvals/482.md`
is written by `finish-feature.sh`.

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f, pbc-scientific-visualization@a70b5016

- **Page and layout** (the hero of Home: one composition on a wide
  screen, a stacked one below 992 CSS px). Impeccable in its Persuade mode
  within the restraint of the brief (`reference/craft-floor.md`,
  `reference/mode-persuade.md`, `reference/layout.md`,
  `reference/adapt.md`, `reference/typeset.md`); frontend-design for
  restraint: the hero is the one bold move of the page, everything below
  stays as #481 left it. Expected artifact: the rendered `index.html` at
  1280×800, 768×1024, 390×844, 360×640, 320×568, at 200 % text, with the
  keyboard, without scripts, and under `prefers-reduced-motion: reduce`.
  Validation: the unit, integration, and e2e tests of Home, the checks
  every page gets (accessibility scan, keyboard pass, reflow, payload
  budget), the rendered review with screenshots in the pull request, and
  the owner's approval on the rendered page (`owner_approval`).
  Accessible fallback: the page is static HTML; the image is one `<img>`
  with its alternative text in the HTML, the same with and without
  scripts; the copy and the actions stand on their own without the image.
- **Interface artwork derived from a computed master** (ADR 021 decision
  1, class C): three WebP files at 1200, 1800, and 2400 px wide, 2:1,
  derived from the fluids master `pbc_fluid_dynamics_vortex_street.webp`
  by `tools/illustrations/derive_assets.py --hero`; no new illustration.
  Validation: the visual check of ADR 021 decision 1 (composition,
  legibility at the sizes shown, family, no text, number, or formula in
  the pixels), recorded in the completion evidence; the register rules of
  the committed-artifact check; unit tests on the committed bytes (the
  matte, the mirror). The scientific-visualization skill applies through
  its section 5 only (illustration kept apart from results): the hero is
  not presented as a result, carries no caption, axis, colour bar, or
  number, and its alternative text claims no direction of a physical
  quantity; the skill's rules for a lesson figure (axes, units, status,
  `fig-alt` of a plot) do not apply to interface artwork, which is the
  exception the skill allows a plan to state. No scientific figure, no
  conceptual diagram, no animation.

## Decisions taken in this plan

- **D1. Blending by a derived image with an alpha matte, not a CSS mask.**
  The fade is baked into the derived file as its alpha channel (WebP
  carries alpha): a geometric matte, zero on all four edges of the file,
  rising smoothly inside the computed domain of the master, low under the
  left third (the end of the trail, where the copy lies on a wide screen),
  one over the right half (the cylinder and the first vortices). Why not
  a CSS `mask-image`: a browser without masks would draw the unfaded
  trail under the headline, so the readability would depend on a style;
  with the matte in the file, every reader (a browser without masks, a
  link preview, a crawler, the page without CSS) sees the faded image,
  the same bytes decide at every viewport, and the two readability
  criteria become tests of the committed bytes (the edges are
  transparent; the left region is faint; the right region is opaque)
  beside the tests on the render. The page keeps no blend mode: the matte
  is zero where the master's paper would otherwise show a box, so
  `mix-blend-mode: darken` is no longer needed.
- **D2. The mirror is in the file.** The derived image is the master
  flipped horizontally, cropped to the middle 2:1 band (the master's
  computed domain, rows 300 to 1500 of 1800, with a paper margin above
  and below for the fade), so that the HTML's own image flows from right
  to left for every reader and no CSS transform is involved. A mirror
  image of a flow is a valid flow: the governing equations are invariant
  under reflection, the inflow comes from the right, the cylinder stands
  toward the right, and the shedding still alternates; what the
  reflection reverses is the sign of the vorticity, so the colour-to-sign
  convention of the master's README (blue negative, copper positive) does
  not hold for the mirrored picture. Nothing on the page states that
  convention: the hero has no legend, colour bar, axis, scale, label, or
  text (ADR 021 decision 1 forbids text in the pixels), and the
  alternative text names only what is seen ("a fluid flowing from right
  to left past a cylinder, leaving a trail of alternating swirls that
  fades away to the left"). The pull request says so.
- **D3. One image, three widths, WebP only.** `srcset` with 1200w, 1800w,
  and 2400w (the master is 2400 px wide, so nothing is upscaled) and
  `sizes="(min-width: 1280px) 885px, (min-width: 992px) 74vw, 94vw"`, measured on the built page (review round 1, MIN1);
  `width="2400" height="1200"` with the figure's `aspect-ratio: 2 / 1` so
  that the box is reserved before the bytes arrive; `fetchpriority="high"`
  and `decoding="async"` on the image, which is the largest element of the
  page and is in the HTML, where the preload scanner finds it at once; no
  script in the hero, so nothing blocks the parser (the hero script of
  F158 was parser-blocking by design). WebP is the modern format the
  project fixed (ADR 021 decision 2) and every browser in use decodes it;
  no second format: a PNG fallback would be fetched by no browser, would
  add a registered file of several hundred kilobytes, and would need the
  resource list of `site/_quarto.yml` widened; AVIF would amend ADR 021
  and the committed-artifact check. The fallback of the hero is its
  alternative text and the copy, which stands on its own paper. Recorded
  for the owner under "Limits and decisions for the owner".
- **D4. One consistent hero: the four-image set and the script leave.**
  `site/learner/hero.js`, its unit tests (`tests/unit/test_hero_script.py`),
  the `hero-image` parameter, the embedded image data, the `<noscript>`
  wrapper, and `images.default`/`images.set` of `site/hero.yaml` are
  removed; the file gains `image` (one mapping of `id`, `sequence`,
  `alt`), validated as the set was (a plain id, a course of Part A, plain
  non-empty alt text, no other field). The page with and without scripts
  is byte-identical in the hero. The three other hero files
  (`double-pendulum.webp`, `hot-cold-gas.webp`, `exoplanet-transit.webp`)
  and the old `vortex-street.webp` leave `site/assets/hero/` and the
  register; their masters stay registered through the atlas entries of
  their courses (`atlas/<course>-panel-*.webp`, `atlas/<course>-card-*.webp`),
  which Home does not show. `derive_assets.py --hero` derives the one
  image only; `tools/illustrations/README.md` says so.
- **D5. Layout.** From 992 CSS px one unified hero: the figure is the
  ground of the hero's grid (it spans both columns and all rows), 78 % of
  the hero's width, aligned to the right edge of the content column; the
  copy and the actions stand in the left column (46 % of the width) above
  it, so that the left 31 % of the image lies under the copy, where the
  matte keeps it faint. The hero's height is the image's (2:1 of 78 %:
  about 460 px at 1280). Below 992 px (tablet and phone) the composition is
  stacked, not shrunk: the copy, the actions, and then the image at the
  full width of the column, whole and unshrunk at 360 and 320 (the
  owner's decision of 2026-11-10 stands), the matte giving it no edge;
  no text stands over the image there. No bleed beyond the content
  column: the page's gutters are the theme's and a wider box would risk a
  horizontal scroll; 78 % of a 1180 px column at 1280 is 920 px.
- **D6. The F158 contract.** The compact header, the 37 px headline at
  320 px and 200 % text, the above-the-fold rule (the message and both
  actions at 1280×800, 768×1024, 390×844; the message and the primary
  action with 24 px to spare at 360×640 and 320×568), the image in view
  from 390×844 up (at least 40 % of its height, whole on the desktop), and
  the reflow without a broken word hold unchanged. One assertion of the
  reflow test changes in kind: "the copy, the actions, and the image do
  not overlap" becomes "on a wide screen the copy and the actions lie
  over the faint part of the image, and the text keeps its contrast,
  measured on the render" (the copy and the actions still never overlap
  each other, and below 992 px the image still follows the actions). The
  contrast is measured, not assumed: a test screenshots the hero with the
  text made transparent, takes the darkest pixel behind each text box
  (the headline, the subtext, both actions), and requires the WCAG ratio
  of the text's colour against it to be at least 4.5 (3 for the headline,
  large text), at the five sizes and at 200 % text. A second test samples
  the pixels along the figure's four edges on the render and requires the
  paper, at every size: no rectangular boundary.
- **D7. Reduced motion.** Nothing in the hero moves, transitions, or
  animates; the site-wide rule for `prefers-reduced-motion` stands and the
  rendered review runs once under it to state it.

## Tests removed, replaced, or added (the Level 3 trigger)

Removed with the script: `tests/unit/test_hero_script.py` (four tests:
no request but the image, nothing changes after it ran, only the embedded
data and its parameter are read, no text touched), since there is no
script. Replaced in `tests/unit/test_home.py`: the four-image data test
and the per-image file-and-register test (×4) by the one-image data test
and the per-width file-and-register test (×3); the duplicate-image and
default tests by the missing-or-malformed-image test; the exoplanet
author test, which belongs to a file that no longer exists; the
`<noscript>`-and-data markup test by the test of the one `<img>` with its
`srcset`, `sizes`, dimensions, priority hint, and no script; the
script-order test by the figure-between-copy-and-actions test; the
embedded-data escaping test, which has nothing to escape. Added there:
the matte on the committed bytes (edges transparent, left region faint,
right region opaque, monotone from the left edge to the plateau), the
mirror (the darkest pixels, the cylinder, stand in the right third).
Replaced in `tests/e2e/test_home.py`: the per-image parameter test (×4) by
the one-request test per viewport (the file sized for it, exactly one
hero request, within the budget); the random-pick test and the
script-before-first-paint test by the no-script test (no `<script>` and no
`<noscript>` in the hero, the image in the HTML, the same with and without
scripts, the old parameters change nothing); the swap-moves-nothing test
by the layout-stability test (the boxes with the image blocked equal the
boxes with it loaded); the script-requests-one-image test by the
one-request-and-no-storage test. Adapted: the above-the-fold, in-view,
unshrunk, and reflow tests lose their loop over four images and gain the
assertions of D5 and D6. Added: the contrast test and the edge test of
D6. `tests/integration/test_home_build.py` keeps its cases and checks that
the built hero holds the image with its `srcset` and no script.

## Documents

ADR 021 decision 4 gains an amendment of 2026-11-11 (Issue #482); the
requirements' "Home page" and the roadmap block of F158 a dated note;
`docs/architecture.md` (the Home section, the atlas-modules row, the file
tree, the risk "the hero image loads twice"), `docs/atelier.md` ("Home
page", the asset table row), `docs/authoring.md` (the hero bullets), and
`tools/illustrations/README.md` are brought up to it.

## Payload and render-time estimate

Before (`main`, CI run of 769a2bb, measured by the payload check on Home
alone): 1,298,134 bytes before #481, 1,264,614 after it, of which the hero
image was one of four files of 19 to 57 kB (the vortex street 19,328
bytes at 1200×900) and the script 1.1 kB. After: one request of the file
sized for the viewport. Estimate: the 2:1 crop is mostly paper, so with
lossy colour at quality 88 and lossless alpha the three files are
expected at about 25, 50, and 80 kB; a 1280 px screen at 1x takes the
1800 file, at 2x the 2400 file, so the desktop payload rises by about
30 to 60 kB and stays far under the 3,000,000-byte budget; a phone at 2x
or 3x takes the 1200 or 1800 file. Measured after, in "Found while
building". Render time: the page has one Python cell as before and no
script; the parser-blocking script is gone, and the image is found by the
preload scanner from the HTML, so the largest contentful paint comes
earlier than before, not later. Build time unchanged within noise; the
derivation runs outside the build, once, on the owner's master.

## Steps

1. `tools/illustrations/derive_assets.py --hero` (the crop, the mirror,
   the matte, the three widths); derive the files; the register; remove the
   four old files and their entries.
2. `site/hero.yaml` (`image`), `src/pbc/authoring/home.py` (the schema,
   the validation, the figure markup), `site/learner/hero.js` removed.
3. `site/assets/site.css` (the unified hero from 992 px, the stacked one
   below).
4. Tests (unit, integration, e2e).
5. Documents (ADR 021, requirements, roadmap, architecture, atelier,
   authoring, the tools README).
6. Render Home on the built site of `main` and review it at the five sizes,
   200 % text, keyboard, no scripts, reduced motion; measure the contrast
   and the payload; screenshots for the pull request.
7. `./scripts/verify.sh --targeted`, last (it will report that CI runs
   everything: the shared CSS and `pbc.authoring` changed; the full run is
   the supervisor's).

## Found while building (2026-11-11)

- **The files, measured:** `vortex-street-1200.webp` 33,052 bytes,
  `-1800` 56,698, `-2400` 59,634 (lossy colour at quality 88, lossless
  alpha). **The payload of Home** by the payload check on the rendered page
  at 1280 by 800 (the 1200 file at 1x): 1,252,684 bytes, against 1,264,614
  after #481 (the 57 kB default pendulum file and the script are gone; a
  2x desktop takes the 2400 file, about 27 kB more than that).
- **The matte on the committed bytes:** every edge pixel at alpha 0; the
  left 31 % at most 64 of 255; the plateau (60 to 88 % across, 30 to 70 %
  down) at 255; the cylinder's centroid at 82 % of the width, 50 % of the
  height (unit tests).
- **The contrast, measured on the render** with the text transparent (the
  darkest pixel behind each box; the e2e test requires 4.5, 3 for the
  headline): at 1280 by 800 the headline 14.2, the subtext 5.4, the
  secondary action 7.9, the primary (white on cobalt) 7.9; at 200 % text
  the subtext 5.1 (the darkest backdrop at luminance 0.79); at 768 and on
  the phones the text stands on the paper (6.0 for the subtext). The
  edges of the image's box are the paper at every size.
- **The geometry at 1280 by 800:** the hero 1135 px wide and 475 tall, the
  copy column 522 px, the figure 885 by 443 (78 %) at the right edge, its
  left 273 px (31 %) under the copy; the headline 47.7 px, 67.2 at 200 %.
  At 768 the image is 711 by 355 under the actions; at 390 by 844 whole on
  the first screen (333 by 166, bottom at 649); at 360 by 640 and 320 by
  568 the primary action ends 220 and 131 px above the fold. At 200 % text
  on 768 the content column is wider than the screen (807 px), as on
  `main` (noted by #481: the theme's gutters scale with the text).
- **CSS order matters:** the base rule's `grid-area: figure` comes later in
  the file than a media-query placement declared before it and overrode it
  (the figure landed in implicit tracks and the copy column fell to 63
  px); the desktop block now follows the base rules.
- **The theme's script rewrites the actions' hrefs** to their absolute form
  with `data-original-href`, so the with-and-without-scripts test compares
  the copy's and the figure's HTML and the actions' resolved targets, not
  the raw HTML of the hero.
- **Reduced motion:** nothing in the hero moves; the render under
  `prefers-reduced-motion: reduce` is the same as without it (screenshot).
- **Screenshots** for the pull request: `.agents/handoffs/482-screenshots/`
  (a working folder Git ignores): the five sizes at 100 % and 200 % text,
  the viewport and the full page, without scripts, and under reduced
  motion. `gh` cannot attach images to a pull request body, so the owner
  attaches them when the pull request is published.
- **Limits and decisions for the owner:** WebP only (D3); no bleed beyond
  the content column (D5); the fade's geometry (a quarter of the ink at
  the right edge of the copy's column, one from 58 % of the image) is in
  `derive_assets.py` and can be tuned there with the tests' thresholds; a
  phone shows the whole 2:1 band at the column's width (166 px tall at
  390), a tighter art-directed crop for phones was considered and not
  done (one image, one request, the owner's "one consistent hero").
