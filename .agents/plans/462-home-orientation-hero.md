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

## Correction of round 2 (the owner, 2026-11-10): the subtitle and the headline at 200 % text

The owner approved round 2 and asked for two things (Issue body "Owner's
decisions, round 2, correction"): the new subtitle, and a responsive
reduction of the headline's size at 200 % text on narrow columns instead
of words breaking inside, with the reflow test's hard minimum replaced by
meaningful assertions. Nothing else changes. Skills as in round 2:
impeccable@08d5b470 (`reference/typeset.md`, `reference/adapt.md`),
frontend-design@dbd4588f; the automated detector does not run.

### Decisions (the session's choices, stated)

- **The subtitle** is exactly "Explore physics by building models, testing
  predictions against real data, and discovering what AI might make
  possible." in `site/hero.yaml`; the unit test quotes it; the documents
  that describe the subtext as "the owner's words" stand, and the roadmap
  note names the text.
- **The cause of the broken words:** below 30em the headline is 1.75rem,
  which at 200 % text is 56 px, while the copy's column at 200 % is 212 px
  wide at 320 CSS px (the theme's gutters scale with the text), 252 at 360
  and 282 at 390; the longest word, "intelligence.", is 5.6 em wide in the
  page's face (313 px at 56 px), so `overflow-wrap: break-word` split it
  (and "universe", "obligation" at 320). Measured before the change:
  three words broken at 320, two at 360, one at 390 at 200 %; none at 768
  and 1280, and none at normal text.
- **The size follows the column**, not the text scale or the device: the
  copy block is a size container (`container-type: inline-size` on
  `.hero-copy`) and the headline is `min(<its size>, 17.5cqi)`, at most
  17.5 % of the column's width, which holds the longest word (100 / 5.6 =
  17.9 %) with a small margin. At normal text the cap is far above the
  size (a 263 px column at 320 px allows 46 px against 29.75), so the
  typography is unchanged at every size; at 200 % it gives 37 px at 320,
  44 px at 360, 49 px at 390 (the owner's 40 to 44 px where the column
  allows it; at 320 the 212 px column cannot hold "intelligence." above
  38 px). The plain size is declared before the capped one, so a browser
  without container units keeps today's size. `overflow-wrap: break-word`
  stays as the last resort for an unknown face; the test asserts that it
  is never used.
- **The reflow test** (`test_the_hero_reflows_without_overlap_at_every_size_and_at_200_percent_text`):
  the assertion "headline at least 28 px times the text scale" is kept at
  normal text (at least 28 px) and replaced at 200 % by: the headline is
  at least 1.35 times its size at normal text (1.2 at 320 px, where 1.27
  is the ceiling; measured 1.25 at 320, 1.48 at 360, 1.66 at 390, 1.41 on
  the desktop, where the size is CSS arithmetic in rem and vw); no word
  of the headline or the subtext is drawn in more than one line box
  (`Range.getClientRects()` per word), and every word lies within the
  copy's column; the existing assertions (no horizontal scroll of the
  page or the content, no overlap of the copy, the actions, and the
  image, the reading order, the tab order) stay. The new assertions are
  stronger in kind: the old floor passed with three words broken.
- **390 px and the desktop:** unchanged at normal text (the cap is above
  the size); at 200 % the desktop keeps 67.2 px (the cap is 85) and 390
  gets 49 px instead of 56 with "intelligence." whole.
- **Outside this change** (recorded in the handoff note for the owner, as
  asked): at 200 % text About's licence table at 360 px and, at 768 px,
  the theme's content column and the "On this page" sidebar are wider
  than the screen on their own.

### Steps of the correction

1. `site/hero.yaml` (the subtext), `tests/unit/test_home.py`.
2. `site/assets/site.css` (the container and the capped size),
   `tests/e2e/test_home.py` (the reflow test).
3. Render Home, measure the words at the five sizes and both scales, run
   the affected tests, the site-wide page checks on Home and one other
   page, `--only code` and `--only default`.
4. The documents (the roadmap note, `docs/architecture.md`,
   `docs/atelier.md`), the approval request, this plan; the screenshots
   at 320 and 360 px at 100 % and 200 % text (and the set of round 2 again
   with the new subtitle), and what they show.

## Round 2, third part (the owner, 2026-11-10): the bar on one line at 320 x 568 and 200 % text

The owner approved the hero visually (Issue #462, "Owner's decision, round
2, third part") and asked for one small correction: at 320 x 568 with 200 %
text the search icon fell to a second line of the header, which made the
bar needlessly tall; the navigation is to stay on one line there too,
without hiding the search, without a toggle target below 44 px, without
losing an accessible name, and without horizontal overflow; if one line is
not possible without an accessibility problem, say so with the
measurements and stop. No other visual change.

### Cause (measured on the render)

At 320 px and 200 % text the bar's row is 189 px wide (320 less the 29 px
gutter and the 102 px the toggle's square and its gutters reserve). The
mark (44 px), "PBC" (70 px at 36 px), the search control (32 px), and the
gaps between them need 194 px, because the gaps, `--pbc-space-2`
(0.5rem), double with the text to 16 px, and Quarto's empty tools box
costs a gap of its own: the search control wrapped. At 100 % the same row
needs 133 px.

### Decision (the session's choice, stated)

The gaps are capped like the gutter and the toggle already are, which the
rule's own comment states as the design (the text grows, the chrome's
spacing does not): a token `--pbc-bar-gap: min(var(--pbc-space-2), 9px)`
for the container's and the brand's `column-gap` below 40em. At 100 % the
gap is 8.5 px, as before, so nothing moves at normal text (the 320 x 568
double-pendulum screenshot retaken is byte-identical to the one of the
correction); at 200 % the row needs 173 px of its 189 and the bar is one
line of 74 px at 320, 360, and 390 px (it was 134 px at 320). No part of
the bar changes size or name: the toggle stays 44 px, the search control
its 32 by 55 px, the mark 44 px, the names "Physics by Construction"
(twice), "Search", and "Menu". Not chosen: a smaller right reservation for
the toggle (it would move the search control at 100 %, a visual change);
hiding the empty tools box (it would hide a tool the site may configure
later); a smaller title or mark at 200 % (a change of the typography the
owner approved).

### Steps

1. `site/assets/site.css`: the token and the two gaps; the rule's comment.
2. `tests/e2e/test_header.py`:
   `test_at_200_percent_text_the_bar_is_still_one_line_on_a_phone` (320,
   360, 390 px x Home, About, the first lesson): the four parts' middles
   within 12 px and each inside every other's extent, left to right in
   order, no overlap, within the screen and the header, the header at most
   80 px; the toggle 44 px, the names, the search button visible, Home's
   width. Shown to fail on the site without the cap (the search control's
   middle 60 px below the mark's box; the header 134 px).
3. `docs/atelier.md` ("Header"), the approval request, this plan; the
   screenshots at 320 and 360 px at 200 % text retaken (closed, the full
   page, the menu open), and 320 x 568 at 100 % compared.
4. The affected tests, the site-wide page checks on Home and About,
   `--only code` and `--only default`.
