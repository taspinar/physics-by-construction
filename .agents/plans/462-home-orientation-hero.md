# Plan: F158, Home: orientation, the hero image from four Part A illustrations, and the first step (Issue #462)

Level 3 by trigger: the tests of the examples chosen by code, of the capstone
choice, and of the constellation image are removed or replaced (the roadmap
risk and the Issue). The approval request is
`.agents/approvals/462.md`. Implementer: Opus (rounds 1 and 2 of the
review), Fable (round 2 of the owner, below). Round 1 needed no ADR,
requirements, or roadmap change: ADR 021 decision 4 as amended on 2026-11-04
already decided it; the owner's decisions of 2026-11-10 (options C and a)
and round 2 clarify and amend the roadmap block, the requirements, and ADR
021, as "Round 2" below records. `docs/architecture.md` and
`docs/atelier.md` are brought up to what is delivered.

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
- **The owner's decision of 2026-11-10 (review round 1, M1, option C).**
  The image is never weakened (shrunk, cropped, hidden) for a pixel rule;
  it need not be above the fold on the smallest phones. Per size: the
  image in view at 1280 by 800 (whole), 768 by 1024, and 390 by 844 (its
  top on the screen, at least 150 px visible); the message and the
  primary action in view at 390 by 844 and 360 by 640 (the secondary may
  fall just below); at 360 by 640 and 320 by 568 the image follows the
  actions below the fold, loaded, in its natural aspect, and at the size
  it has at 390 wide scaled by the width (the full content column). No
  layout change. Tests: `test_the_image_is_in_view_from_390_by_844_up`
  and `test_on_the_smallest_phones_the_image_follows_whole_and_unshrunk`
  in `tests/e2e/test_home.py`, added beside the existing assertions.
  Open: the decision also names the message and the primary action in
  view at 320 by 568, which the current layout does not give (measured:
  header 176 px, the primary's bottom at 687 px, the subtext of pairs 3a
  and 3b ends at 594 and 623 px) and which needs a layout change the
  decision rules out; asked on the Issue through the handoff note.
- **The owner's decision of 2026-11-10, second part (option a).** The
  message and the primary action are in view at 320 by 568 too; the
  layout may change at 320 px, Home first, then the shared header's
  spacing. Home alone is not enough without a smaller headline: with the
  headline at its phone size (1.75rem, which the reflow test's floor of
  28 px times the text scale requires, also at 200 %), Home's spacing
  brings the primary's bottom from 687 to 584 px. So below 22em
  (`site/assets/site.css`): on Home, main's top margin 0.5rem, no hero top
  margin, row gap 0.5rem, headline line height 1.05 and its bottom margin
  0.5rem, the subtext 1rem at line height 1.4, the primary action's line
  height 1.3 (42 px tall); in the shared header, the bar's padding 0.25rem
  and the title's line height 1.2 (header 176 to 151 px, every item
  kept). Measured at 320 by 568 for every pair: the primary ends at 548
  px (the copy, reserved at the longest pair, at 498), the same with the
  page's fonts blocked (the Times New Roman fallback, metric-equal to
  Liberation Serif on Linux); 360 by 640 and 390 by 844 unchanged. The
  320 by 568 row is added to `test_the_message_and_the_actions_are_above_the_fold`;
  the F132 header test and the site-wide page checks on Home, About, the
  Course Atlas, and the first lesson pass. At 200 % text on 320 px the
  mark overlapping the title in the shared header predates this change.
- **CI of PR #466 on fbae838 (owner's instruction of 2026-11-10).** On the
  Linux runner the primary ended at 571.97 px at 320 by 568, so the 548 px
  above depended on the font. The owner asked for the primary at 548 px or
  less (20 px above the fold) with every runner-like face and every pair.
  Measured with the text faces substituted (the copy is reserved at the
  longest pair, so every pair gives the same bottom): before, STIX 548.2,
  Times New Roman 516.9, Georgia and Liberation Sans 603.2, DejaVu Serif,
  DejaVu Sans and Verdana 659. Below 22em on Home now: the page's gutters
  1rem instead of the theme's 1.5em (a column of 286 instead of 263 px, so
  fewer lines whatever the face), the headline's line height 1, the
  subtext's 1.3. After: STIX 499.3, Times New Roman 477.2, Georgia and
  Liberation Sans 529.0, DejaVu Serif, DejaVu Sans and Verdana 580.9 to
  581.2. The three widest faces cannot reach 548 px within the owner's
  limits (the headline at least 28 px, the copy reserved at the longest
  pair, every header item kept, nothing hidden): their reserved copy alone
  is about 372 px, so the header would have to be about 100 px or less
  instead of 151; asked on the Issue through the handoff note. Measured
  alternatives: without the reservation at 320 px the longest pair alone
  still ends at 581 px with those faces; a headline of 1.5rem below 22em
  ends every face at 526 px or less (STIX 478), but lowers the reflow
  test's floor of 28 px at 320 px, which the instruction rules out.
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

## Round 2 (the owner's critique of the rendered Home at cbd49c2, 2026-11-10)

The owner's text and the supervisor's notes are on the Issue ("Owner's
decisions, round 2"). They supersede, for this feature, the eight headline
and subtext pairs of F134, the rule that the header keeps its four items in
a row, and "the image in view from 390 by 844" (option C). Skills:
impeccable@08d5b470 (`reference/craft-floor.md`, `reference/adapt.md`,
`reference/layout.md`, `reference/mode-persuade.md`), frontend-design@dbd4588f;
the automated detector of Impeccable does not run (the adapter).

### Decisions taken in this plan step (the session's choices, stated)

- **One fixed hero text.** `site/hero.yaml` holds `headline` (the owner's
  first headline, kept exactly) and `subtext` (the owner's new subtitle),
  plain text, and the `images` of round 1. The eight pairs stay in the same
  file under `variants` as an editorial reference (the hero copy stays in
  one data file, requirements "Data and persistence"), validated as plain
  text and never written on a page or used by a script. The `hero` query
  parameter, `HERO_PAIRS`, the embedded pairs, the hidden copies (ghosts),
  and the reserved height go; the `<h1>` and the subtext are the HTML's
  and never change. `hero-image` stays as it is.
- **The cause of the empty space on a phone** (critique item 4): the copy
  block was reserved at the height of the longest pair (`.hero-ghost` in
  one grid cell), so a shorter pair left its unused height between the
  subtext and the actions. With one fixed text the reservation leaves and
  the document flow sets the distances: 1.5rem between the subtext and the
  actions, 2rem between the actions and the image on a phone; the type
  keeps its phone size (1.75rem headline below 30em). The 22em block of
  round 1 (narrower gutters, tighter lines) leaves: its reason (the
  reserved copy at 320 px under a 151 px header) is gone, and the gutters
  are consistent again.
- **The compact header below 40em (640 CSS px)**, the owner's bar
  `logo | PBC | search | menu`. A post-render script `site/navigation.py`
  (the pattern of `skip-link.py` and `search-fallback.py`: idempotent, no
  input but the built pages) rewrites Quarto's header on every page:
  the title becomes two spans, the full name and the aria-hidden short
  form "PBC", of which CSS shows one and keeps the other rendered but
  clipped (the link's accessible name stays "Physics by Construction",
  and the readable-without-scripts check sees no hidden text); the two
  navigation lists are wrapped in `<details class="pbc-menu" open>` with a
  `<summary>` toggle (an icon drawn in CSS, `aria-label="Menu"`, 2.75rem
  square); `site/learner/menu.js`, parser-blocking right after the
  details, closes the menu below 40em before the first paint, keeps it in
  step with the viewport (`matchMedia`), and closes it on Escape with the
  focus back on the toggle. Without scripts the menu stands open under the
  bar (the four items in a column: the fallback is the navigation of
  today) and the native toggle closes it; from 40em the toggle is hidden
  and the lists are inline as before. The four items stay, in the menu
  below 40em, Start learning last as the filled control; on the mobile
  Home the hero's primary action is the visible first step (the owner's
  note). Between 40em and 48em the header keeps round 1's wrapped layout
  (the full name, the entries on the rows below); from 48em nothing
  changes. The break point is where the four items, the full name, the
  search, and the start link no longer share a bar: measured on the
  render.
- **The 390 by 844 rule made measurable:** at least 40 % of the image's
  height is above the fold (the threshold chosen on the render, where the
  whole image is in view with the fixed text; 40 % leaves room for the
  fonts of another machine). At 360 by 640 and 320 by 568 the primary
  action ends at least 24 px above the fold (a floor well under the
  measured margin, so no font decides it), and the image follows whole and
  unshrunk as round 1 decided.
- **The checks that the design changes** (shown at least as strong):
  `check_keyboard_navigation` and `check_navigation_fits` in
  `tests/support/site_checks.py` open the menu when the bar has a toggle,
  so that every entry is still tabbed and measured at phone width, and the
  toggle itself is tabbed, opened by keyboard, and has a visible ring. The
  F132 header test (`test_the_built_header_has_four_items...`) is unchanged
  in its assertions; new header tests (`tests/e2e/test_header.py`) check the
  one-line bar, the closed menu at load, the toggle by pointer and keyboard,
  Escape, the accessible name and state, the fallback without scripts, the
  bar at 200 % text on 320 and 360 px with no overlap, and the shared
  header on About and a lesson. The hero tests of the pairs are replaced
  by tests of the fixed text (with and without scripts, after a reload,
  with the old parameter ignored).
- **The default image without scripts** stays the double pendulum (ADR
  021 decision 4): a change would be data only (`images.default`), and
  the owner's preference for the transit is a preference for the random
  set, which stays; no reason to move the default.
- **Documents:** the roadmap block of F158 (a dated round 2 note: the fixed
  text, the compact header with the menu, the 390 by 844 threshold) and a
  line in F132's note; ADR 021 (a dated note under decision 4 and decision
  5); requirements "Home page", "Site navigation", and "Data and
  persistence"; `docs/architecture.md` (Home, Navigation, the post-render
  scripts); `docs/atelier.md` (Header, the mobile rule); the approval
  request; this plan.

### Steps of round 2

1. `site/hero.yaml`, `pbc.authoring.home` (`HeroCopy`: headline, subtext,
   images, variants; the hero markup without pairs), `site/learner/hero.js`
   (the image only); unit tests first.
2. `site/navigation.py`, `site/learner/menu.js`, the post-render list of
   `site/_quarto.yml`, the header CSS; unit tests of the script and the
   scan of the menu script.
3. The hero CSS: the distances on a phone, the 22em block removed.
4. The site checks (keyboard, navigation fits) opened for the menu; the
   e2e tests of the hero and the header.
5. Render Home (the post-render scripts rewrite every built page), run the
   tests, measure the bar and the fold at the five sizes and at 200 %
   text with the page's font and with the fallback faces of another
   machine; tune the break point and the distances on the render.
6. Documents, the approval request, the screenshots (the five sizes x four
   images; 320 and 360 at 200 % text; the opened menu; About and a lesson
   with the header; Home without scripts; the site has no dark mode), and
   the assessment of what they show.

### Found while building round 2 (2026-11-10)

- **A `details` cannot be laid out with `display: contents`** for the bar:
  a new Chromium wraps its content in the `::details-content` box, so the
  flex rules do not reach the lists, and an older one does not. The toggle
  is instead absolutely positioned in the bar (a 44 px square at the
  right gutter, the bar reserving its room), and the details is a flex
  item on a row of its own under the bar; from 40em the details is the
  flex item that holds the lists (its panel lays them out as the bar did).
- **A bare `summary` has no name and no state** in Chromium's
  accessibility tree (a details is a "group" named by its summary's text;
  an icon-only summary with `aria-label` showed nothing). The toggle is
  therefore `role="button"` with `aria-label="Menu"` and `aria-expanded`,
  which `menu.js` keeps in step on the `toggle` event (`true` in the HTML,
  where the menu is open); Enter and Space toggle it natively.
- **The break point is 40em (640 CSS px).** Measured: at 640 to 767 px the
  full name, the three items, the start link, and the search do not share
  one row (about 715 px are needed), so that step keeps round 1's two-row
  layout (the full name and the search, the entries wrapped below); from
  768 px one row holds everything.
- **200 % text on 320 px.** The bar's paddings, the mark's margins, and the
  toggle scale with the text in the theme; now the gutter is capped at
  29px, the toggle is 44 px, the mark grows to 44 px at most, and the brand
  never shrinks below its content, so the mark, "PBC", and the search
  share the row (the search wraps under them only when the row is too
  narrow) and the menu's entries wrap inside the panel. Measured at 320 px
  and 200 %: the bar 126 px tall, nothing overlapping, the page 320 px
  wide with the menu closed and open. Outside the header, at 200 % text,
  About's licence table at 360 px and, at 768 px, the theme's content
  column and the "On this page" sidebar are wider than the screen on their
  own (pre-existing; recorded for the owner, not changed).
- **The fold with the fixed text** (the page's own STIX; header 54 px):
  320 by 568, the primary action ends at 484 px (Times New Roman and the
  Liberation and DejaVu fallbacks of a Linux runner 429, Georgia and Arial
  484, Verdana 569); 360 by 640 at 473 (Verdana 531); 390 by 844 the whole
  image is above the fold with every face (100 %), so the threshold of
  40 % has ample room. The 24 px margin test holds with every face but
  Verdana, the widest installed sans-serif, which the page never gets
  (the runner loads STIX; the owner's decision A of 2026-11-10 judges on
  the page's own font and the Times/Liberation fallback).
- **The vortex street master** carries wide white margins inside the
  image, so on a phone the painted part begins about 60 px below the
  figure's box; the box itself is 2rem under the actions. Not a layout
  matter (the owner's illustrations are kept as they are).
- **Verification of round 2 (this session):** unit tests of Home, the hero
  script, the menu script, and the chrome 54 passed; e2e `test_home.py`
  and `test_header.py` 65 passed; the F132 header test and the search
  tests passed; the site-wide page checks (requests and cookies, readable
  without scripts, horizontal scroll, axe, navigation fits, keyboard,
  payload) on Home, About, the atlas, and the first lesson: no violation;
  `tests/integration/test_home_build.py` and
  `tests/integration/test_site_checks.py` run; `./scripts/verify.sh --only
  code` and `--only default` last. The complete `./scripts/verify.sh` is
  not run in the session, per the Issue's instruction.
