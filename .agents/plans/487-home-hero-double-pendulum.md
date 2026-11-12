# Plan: Home, the hero image replaced by the double-pendulum illustration, wider, faded on the left (Issue #487)

Follow-up of Issue #482 (the hero as one large fluid-dynamics illustration,
merged as d1be840). The owner's request of 2026-11-12: replace the vortex
street by the new illustration of `pbc_hero_assets/` (a double pendulum at
the left, a measured trace with a model curve in the middle, a mass in a
potential well at the right, on a warm white ground), wider than the
885 px of #482, with a little transparency on the left so that the image
does not hinder the text. The owner's decision of 2026-11-12 on the
origin: the illustration is the owner's own; how it was made is not
recorded, and the plan asks nothing about it. Static, no new dependency.
The Home copy, the lessons, the verification, and every other page are
out of scope.

**Level 3.** Paths: `docs/decisions/021-…` (ADR 021 decision 4 amended by
a dated note), `docs/decisions/README.md`, `docs/PROJECT_REQUIREMENTS.md`,
`docs/roadmap.md` (protected). Triggers: assertions of the Home tests
changed or replaced (the matte, the mirror, the register, the share, and
the per-file size tests of #482; the list under "Tests"), a budget changed
(the per-file size of a hero file in the end-to-end test). The owner
approves the exact head at the merge gate; the approval request
`.agents/approvals/487.md` is written by `finish-feature.sh`.

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f, pbc-scientific-visualization@a70b5016

- **Page and layout** (the hero of Home from 992 CSS px: one
  composition, the image wider than the content column; the stacked one
  below is unchanged). Impeccable in its Persuade mode within the
  restraint of the brief (`reference/craft-floor.md`: the contrast floor
  of 4.5 and 3, measured on the render; `reference/mode-persuade.md`: the
  offer, the action, and the reading order first; `reference/layout.md`:
  one element leads, the figure, and the copy and the actions keep their
  reading order; `reference/adapt.md`: the structure changes at the
  breakpoints, nothing is scaled). Frontend-design for restraint: the
  hero stays the one bold move of the page; the sections below stay as
  #481 and #483 left them. Expected artifact: the rendered `index.html`
  at 1280×800, 768×1024, 390×844, 360×640, and 320×568, at 200 % text,
  without scripts, and under `prefers-reduced-motion: reduce`.
  Validation: the unit, integration, and end-to-end tests of Home, the
  checks every page gets (accessibility scan, keyboard pass, reflow,
  payload budget), the rendered review with screenshots for the pull
  request, and the owner's approval on the rendered page
  (`owner_approval`). Accessible fallback: the page is static HTML; the
  image is one `<img>` with its alternative text in the HTML, the same
  with and without scripts; the copy and the actions stand on their own
  without the image.
- **Interface artwork derived from the owner's master** (ADR 021
  decision 1, class C; decision 2, a committed derived raster bound to
  the register): three WebP files at 1200, 1480, and 1774 px wide, 2:1,
  derived from `pbc_hero_assets/pbc-double-pendulum-hero-original.png`
  (1774×887, the master; the sized variants and the phone crops of the
  folder are not masters) by `tools/illustrations/derive_assets.py
  --hero`. Validation: the visual check of ADR 021 decision 1
  (composition, legibility at the sizes shown, family, no text, number,
  or formula in the pixels), recorded in the completion evidence; the
  register rules of the committed-artifact check; unit tests on the
  committed bytes (the edges, the floor under the copy, the plateau, the
  orientation). The scientific-visualization skill applies through its
  section 5 only (illustration kept apart from results): the image is an
  illustration, not a result of the project; the trace and the model
  curve it shows diverge toward the right and are nobody's data; the
  hero carries no caption, axis, colour bar, or number, its alternative
  text names what is seen ("Illustration: …") and claims no measurement;
  the skill's rules for a lesson figure do not apply to interface
  artwork, which is the exception the skill allows a plan to state. No
  scientific figure, no conceptual diagram, no animation.

## Decisions taken in this plan

- **D1. The master and the phone crop.** The original (1774×887 PNG, the
  only file of the folder that is not derived from another) is the
  master, registered with its SHA-256; the sized variants and the two
  phone crops are not used. On a phone the whole 2:1 image follows the
  actions at the width of the column, as in #482 (the owner asked for no
  separate phone image; one image, one request).
- **D2. The width: the content column plus the right gutter.** From 992
  CSS px the figure is the ground of the hero's grid as in #482, but it
  starts at the left edge of the content column and runs past its right
  edge to the right edge of the viewport: `width: calc(50% + 50cqw)`
  with `justify-self: start`, where the container-query unit `cqw` is
  the width of Quarto's page grid (`#quarto-content`, made a size
  container on Home only), so the figure's width is the column's plus
  the gutter without `100vw` (which counts a classic scrollbar and would
  overflow by half its width on CI's Chromium). Measured on `main`:
  the column is 934.6 px at 992, 1135 px from 1280 (capped), the gutter
  28.7 px at 992, 72.5 px at 1280, 232.5 px at 1600; the figure is
  therefore 963 px at 992, 1207.5 px at 1280 (36 % wider than the 885 px
  of #482), and 1367.5 px at 1600 (`calc(50vw + 568px)` from 1280 and
  `calc(100vw - 29px)` from 992 in `sizes`). A browser without `cqw`
  draws the figure at the column's width (the declaration before it).
  The copy and the actions keep their left column (46 % of the hero,
  the column's width), so the copy's right edge lies at 45 % of the
  figure at most (44.6 % at 992, 43.2 % at 1280, 38 % at 1600). The
  hero is as tall as the figure: 604 px at 1280×800, whole on the first
  screen with the compact header. Below 992 px nothing changes.
- **D3. The fade: the least the contrast needs, pixel by pixel, in the
  file.** As in #482 (D1 there) the fade is in the file's alpha channel,
  not a CSS mask, so every reader sees the same image and the tests
  check the bytes. The owner asked for a little transparency on the
  left and a recognisable pendulum, and acceptance 1 asks for the WCAG
  contrast of every text against the darkest pixel behind its box. The
  pendulum's bobs and rods are near-black and lie under the copy's
  column, so a uniform fade would have to leave them at a ninth of their
  ink (black over the paper has to reach the luminance 0.72 for the
  muted subtext at 4.5), which wipes the haze and the ghost positions
  too. The derivation therefore lifts each pixel by what it needs:
  under the copy (the left 47 % of the image) the composite over the
  paper is given the floor luma 223 of 255 (WCAG luminance 0.74 for a
  grey, higher for a coloured pixel), and the ink of a pixel is
  compressed by a power law (exponent 0.3) toward that floor: black
  keeps a ninth, a mid-grey a quarter to a third, the pale haze and the
  ghost positions of the pendulum two thirds and more. From 47 % to 60 %
  of the width the lift eases out to nothing; the plateau from 60 % to
  86 % is whole. What remains of the pendulum: its shape, rods, bobs,
  the orange arc, and the ghost positions, as a pale high-key drawing
  whose darkest ink is a light grey (luma 223, a contrast of 1.3 against
  the paper); it is recognisable as a pendulum, not as a dark object.
  The owner may ask for more ink there; then either the copy's column
  gets narrower or the contrast rule is relaxed, which this plan does
  not do ("Limits and decisions for the owner").
- **D4. The ground is keyed to the paper; the edges fade.** The
  illustration's ground is a warm white (251, 241, 238), the page's
  paper is (250, 248, 243): shown whole, the image would be a faintly
  pink rectangle. Every pixel within a short distance of the ground is
  made transparent (a smooth ramp over 24 levels of RGB distance), so
  the paper shows through and the content keeps its own colours; a
  geometric matte brings every edge to zero (the blue field reaches the
  right edge and the corners of the master), with a fade over the left
  8 %, the right 14 %, the top 12 %, and the bottom 12 %. No visible
  rectangle at any size (the end-to-end edge test of #482 stands).
- **D5. Widths and the loading budget.** `srcset` with 1200w, 1480w, and
  1774w (the master's width; nothing is upscaled), `sizes` as in D2,
  `width="1774" height="887"` with the figure's `aspect-ratio: 2 / 1`
  (the master is exactly 2:1), the 1480 file as the `src` of a browser
  without `srcset`, `fetchpriority="high"`, `decoding="async"`, no
  script. The browser takes the 1480 file at 1280×800 at 1x, the 1774
  file at 2x, the 1480 file on a tablet at 2x, and the 1200 file on a
  phone at 3x. WebP only, lossy colour at quality 88, lossless alpha
  (the alpha decides the contrast). Measured after, in "Found while
  building"; the per-file limit of the end-to-end test is raised to what
  the files need, with the page far under the 3,000,000-byte budget.
- **D6. The register.** Three new entries `hero/double-pendulum-<w>.webp`
  with `author`, `date` (2026-11-12, the files' date), `licence`
  (CC-BY-4.0, as every asset the owner authored), the `master`
  `pbc_hero_assets/pbc-double-pendulum-hero-original.png`, its `sha256`
  (`ac9062c7…`), and a `source` that says what the image shows and how
  the files were derived; no `script` (the master is not computed by a
  script of the repository) and no `model` (the owner's decision: a
  neutral origin). The three vortex-street hero entries and files leave;
  the vortex street stays registered through the atlas entries of
  fluids, which the atlas shows. `derive_assets.py --hero` keeps the
  atlas derivation untouched and no longer mirrors or crops.
- **D7. The data file.** `site/hero.yaml` names the image
  `double-pendulum`, the sequence `mechanics` (the course the pendulum
  belongs to; the field keeps its rule of a Part A course), and the
  alternative text "Illustration: a double pendulum swinging at the
  left, a dotted trace with a dashed curve following it through the
  middle, and a small ball resting in a glowing well at the right." It
  names what is seen and claims no measurement or result.
- **D8. Unchanged from #482.** One image in the HTML, the same with and
  without scripts; nothing moves; reduced motion unchanged; no storage,
  no request beyond the image; the F158 contract (the above-the-fold
  rule, the headline sizes, the reflow without a broken word, the image
  in view from 390×844 up, whole and unshrunk on the smallest phones).

## Tests changed (the Level 3 triggers)

Replaced in `tests/unit/test_home.py`: the owner's-image test (the id,
the sequence, the file names, the alt text's "from right to left"); the
register test (the fields now compared with the master's own entry
values, no script, no model); the matte test (the floor under the copy
measured as the composite over the paper, the plateau, the edges, the
survival of the light content, the monotone lift of equally dark pixels
across the transition); the mirror test (the pendulum's ink stands in
the left third under the copy and the well's mass, the darkest whole
ink, in the right third). Changed in `tests/e2e/test_home.py`: the
requested file per viewport (1480, 1774, 1480, 1200) and the per-file
limit; the share of the hero the figure takes (from the column's left
edge to the viewport's right edge instead of 70 to 80 % at the right
edge); the copy's right edge within the lifted part of the image (47 %
instead of 32 %); the reflow test's assertion that `main` holds no
content wider than itself (the figure now runs past the column by the
gutter, and the document still has no horizontal scroll). The contrast
test, the edge test, the one-request test, the layout-stability test,
the above-the-fold, in-view, unshrunk, and no-script tests keep their
assertions. `tests/integration/test_home_build.py` keeps its cases.

## Documents

ADR 021 decision 4 gains an amendment of 2026-11-12 (Issue #487);
`docs/decisions/README.md`, the requirements' "Home page", and the
roadmap block of F158 a dated note; `docs/architecture.md` (the Home
section, the file tree, the risk "the hero image loads twice"),
`docs/atelier.md` ("Home page", the asset table row), `docs/authoring.md`
(the hero bullets), and `tools/illustrations/README.md` are brought up
to it.

## Payload and render-time estimate

Before (`main` at d1be840): Home 1,252,684 bytes at 1280×800 at 1x with
the 1200 vortex-street file of 33,052 bytes; the three files 33, 57, and
60 kB. After: the illustration has far more colour and detail than the
vortex street's paper band, and the alpha channel is no longer a smooth
matte but follows the content, so the files are expected at about 90,
130, and 180 kB (the owner's own lossy WebP of the master is 190 kB
without alpha); a desktop at 1x takes the 1480 file, at 2x the 1774
file, so the payload of Home rises by roughly 100 to 150 kB and stays
far under the 3,000,000-byte budget; a phone at 3x takes the 1200 file.
Measured after, in "Found while building". Render time: one Python cell
as before, no script, the image found by the preload scanner from the
HTML; the largest contentful paint is the image, larger by the bytes
above on a desktop. Build time unchanged within noise; the derivation
runs outside the build, once, on the owner's master.

## Steps

1. `tools/illustrations/derive_assets.py --hero` (the key, the lift, the
   edge matte, the three widths); derive the files; the register; remove
   the three vortex-street files and their entries.
2. `site/hero.yaml` (`image`), `src/pbc/authoring/home.py` (the widths,
   the intrinsic size, the fallback, `sizes`, the docstrings).
3. `site/assets/site.css` (the figure from 992 px: the column plus the
   gutter; the container on Home).
4. Tests (unit, integration, e2e).
5. Documents (ADR 021 and its README row, requirements, roadmap,
   architecture, atelier, authoring, the tools README).
6. Render Home against the built site of `main` (the CI artifact of
   d1be840) and review it at the five sizes, 200 % text, keyboard, no
   scripts, reduced motion; measure the contrast and the payload;
   screenshots for the pull request in `.agents/handoffs/487-screenshots/`.
7. `./scripts/verify.sh --targeted`, last (it will report that CI runs
   everything: the shared CSS and `pbc.authoring` changed; the full run
   is the supervisor's).

## Found while building (2026-11-12)

- **The files, measured:** `double-pendulum-1200.webp` 53,888 bytes,
  `-1480` 73,804, `-1774` 92,938 (lossy colour at quality 88, lossless
  alpha), each under the 100,000-byte per-file limit of the end-to-end
  test, which therefore stands. An alpha channel that followed the
  content (the key and the lift as alpha, lossless) cost 397, 589, and
  788 kB, so the key and the lift are blended into the colour over the
  paper and the alpha channel holds the edge fade alone; the committed
  bytes are the same to the reader either way.
- **The floor, measured on the bytes:** the composite over the paper under
  the copy (the left 47 %) has the luma 221.4 at least (the target 228 of
  the derivation, less what the lossy colour and the resampling dip), a
  WCAG luminance of 0.726 at least, which gives the muted subtext 4.72
  and the link colour 6.2 at worst; the darkest hundredth of the
  pendulum's region is at least 16 luma levels below the paper, and a
  fifth of it is visibly inked.
- **The contrast, measured on the render** with the text transparent
  (the darkest pixel behind each box; the end-to-end test requires 4.5,
  3 for the headline): at 1280 by 800 the headline 13.2, the subtext 4.9,
  the secondary action 7.1, the primary (white on cobalt) 7.9; at 200 %
  text the subtext 4.8 (the darkest backdrop at luminance 0.75); at 768
  and on the phones the text stands on the paper (6.0 for the subtext).
  The edges of the image's box are the paper at every size.
- **The geometry:** at 1280 by 800 the column is 1135 px (x 72.5), the
  figure 1207.5 by 603.8 px from the column's left edge to the viewport's
  right edge, the copy column 522 px (43 % of the image), the image's
  bottom at 727 px, whole on the first screen; at 992 the figure 963 by
  482; at 1600 1367.5 by 684, whole on a 900 px screen; no horizontal
  scroll at any of them (`scrollWidth` equals `clientWidth`). At 768 the
  image is 711 by 355 under the actions; at 390 by 844 whole on the first
  screen (333 by 166); at 360 by 640 and 320 by 568 as before. At 200 %
  text on 1280 the copy block is taller than the image, which is centred
  on it, as in #482.
- **The payload of Home** by the payload check on the rendered page at
  1280 by 800 (the 1480 file at 1x): see the end-to-end run in the
  handoff note; the 1480 file is 73,804 bytes against the 33,052 of the
  1200 vortex-street file, so Home rises by about 41 kB at 1x and by
  about 33 kB at 2x (92,938 against 59,634).
- **Reduced motion and no scripts:** nothing in the hero moves; the render
  under `prefers-reduced-motion: reduce` and the render without scripts
  are the same as with them (screenshots).
- **Screenshots** for the pull request: `.agents/handoffs/487-screenshots/`
  (a working folder Git ignores): the five sizes at 100 % and 200 % text,
  the viewport and the full page, 1600 by 900, without scripts, and under
  reduced motion. `gh` cannot attach images to a pull request body, so the
  owner attaches them when the pull request is published.
- **Limits and decisions for the owner:** the pendulum under the copy is a
  pale drawing (its darkest ink a light grey of luma 221, a contrast of
  1.3 against the paper), which is the most the contrast rule leaves over
  the copy's column; more ink there needs a narrower copy column or a
  relaxed rule (D3). The image grows with the viewport above 1280 (1367
  px at 1600, 1527 px at 1920) since it runs to the viewport's edge; a
  cap is one line of CSS if the owner prefers a bounded height. WebP
  only, as decided on #482. The 1774 file, the master's width, serves
  every 2x desktop and is upscaled there (the owner supplied no larger
  master).
