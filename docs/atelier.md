# The scientific atelier: the design specification

Status: F123 (Issue #217). The owner approved the direction, the faces,
the mark, and the start link on 2026-10-19; this file records what was
built, and the implementation copies its values.

This is the one description of how the site looks. Every feature that
changes a page applies it (see "How a feature applies it"); a feature that
needs something this file does not define adds it here in the same pull
request. The sources it rests on: requirements decisions 36 ("Visual
direction", "Shared templates") and 37 (the asset classes), ADR 018, and
ADR 019 for the agent skills that informed it. Where this file and an ADR
disagree, the ADR wins and this file is corrected.

## The direction

A scientific atelier with the quality of a carefully designed scientific
publication and optional interactive experiments: warm paper-white
backgrounds, nearly black text, cobalt blue and vermilion accents, elegant
serif headings, readable body typography, precise monospaced annotations,
thin rules, and generous whitespace (change request, section 1).

The owner chose the direction from five visual proposals; the later
physics-map concept is the direction of the atlas. Those mockups are
inspiration, never data: their regions, equations, plots, illustrated
measurements, counts, and copy are not curriculum facts and not verified
science, and none of them is copied into a page, a test, or an asset.

What it means in practice, in three rules:

1. **The frame commits, the column stays calm.** The header, the footer,
   the page ground, the titles, and the way code, tables, figures, and
   labels are set carry the atelier. The text a learner reads sits in a
   quiet column at a real measure, with nothing behind it.
2. **One signature: the construction.** The project's name is "by
   construction", and its one memorable move is a construction drawing: the
   mark (a compass arc, a radius, and one constructed point) and the thin
   cobalt rules that structure a page. Vermilion is that constructed point:
   it marks where the reader is (the mark's point, the current navigation
   entry, the current lesson) and appears nowhere for decoration.
3. **A figure is a plate.** Figures, the widget, and result tables sit on a
   white plate with a thin rule, set into the paper page as plates are in a
   printed monograph. The figures themselves do not change: their white
   ground becomes the plate.

## Tokens

The colours are defined once in `src/pbc/authoring/design.py` and copied to
the `:root` block of `site/assets/site.css`; `tests/unit/test_design.py`
compares the two and checks every pair below. Type, spacing, and rules are
defined in `site.css` only. A component uses the tokens and introduces no
colour, size, or face of its own.

### Colours of the page

Contrast is against the ground named, computed with
`pbc.authoring.design.contrast_ratio` (WCAG 2.1); the requirement is 4.5:1
for text and 3:1 for controls and lines, unchanged from F44.

| Token (`--pbc-…`) | Value | Use | Pairs (contrast) |
|---|---|---|---|
| `background` (paper) | `#faf8f3` | the ground of every page | |
| `surface` | `#f1ede4` | the lesson header, framed boxes | |
| `plate` | `#ffffff` | the ground of figures, the widget, result tables, code listings | |
| `text` (ink) | `#1c1b19` | body text and headings | paper 16.2, surface 14.7, plate 17.2 |
| `muted` | `#57606a` (kept) | metadata, captions' secondary lines, the footer | paper 6.0, surface 5.5 |
| `link` (cobalt) | `#0047ab` | links, the start link's ground, the construction rules | paper 8.0, surface 7.2, plate 8.4 |
| `accent` (vermilion) | `#c2381d` | the current position only (see the signature) | paper 5.1, surface 4.6 |
| `rule` | `#857f73` | thin rules and borders | paper 3.8, surface 3.4, plate 4.0 |
| `focus` | `#0047ab` | the focus ring | paper 8.0, surface 7.2 |
| `warning`, `warning-surface` | `#7a4100`, `#fbf0dc` | the "not verified" mark | 7.2; ink on it 15.2 |
| `header`, `header-text` | paper, ink | the header (it replaces the navbar's blue bar) | 16.2 |
| `start`, `start-text` | cobalt, paper | the start link, the one filled control | 8.0 |

The bright vermilion of the mockups (about `#e34234`) has 3.9:1 on paper:
enough for a line or the mark's point, not for text, so text in the accent
uses `#c2381d`; the mark may use either, since it is not text.

### Colours kept as they are

The claim labels (`CLAIM_LABELS`), the figure statuses (`STATUS_LABELS`),
and the figure colours (`FIGURE_COLOURS`) keep their values and their
meaning: lesson figures read `FIGURE_COLOURS`, so a change there would
change figures, which this redesign does not do. Each label keeps its own
ground (the chips have about 1.1:1 against the paper, as they had against
white: they are words in a tinted chip, never colour alone). Every figure
colour has at least 5.5:1 against the paper and 3:1 against the plate.
`muted` keeps its F44 value, `#57606a`: lesson cells draw axes and
annotations in it, and one lesson shows that code, so a warmer grey would
change figures and displayed code. It has 6.0:1 on the paper.

### Type

Two families, both self-hosted under `site/assets/fonts/` with their
licences, beside the math font already there:

| Role | Face | Weights | Why |
|---|---|---|---|
| Headings and body | STIX Two Text | Regular, Italic, SemiBold | the companion of STIX Two Math: prose and native MathML share one design, which no generic serif pairing gives a physics text |
| Code and annotations | IBM Plex Mono | Regular | a monospace with clear `0O`, `1lI` distinctions for code, units, values, and source addresses |
| Mathematics | STIX Two Math | Regular | unchanged (F44) |

The fallbacks are metric-close local faces (`"STIX Two Text", "Times New
Roman", serif`; `"IBM Plex Mono", ui-monospace, Menlo, monospace`), with
`font-display: swap`. Only the weights listed are loaded. Monospace is for
code, numbers with units in annotations, file and command names, and the
source line of an excerpt; never for running text, headings, or labels as a
"technical" costume.

Scale (a ratio of about 1.25 from a body of 1.125rem, the larger body that
a serif with this x-height needs on screen):

| Token | Size | Leading | Use |
|---|---|---|---|
| `--pbc-text-small` | 0.875rem | 1.5 | metadata, the footer, captions' notes |
| `--pbc-text-base` | 1.125rem | 1.6 | body text |
| `--pbc-text-large` | 1.25rem | 1.5 | a lesson's opening paragraph if it has the class (none yet) |
| `--pbc-heading-3` | 1.25rem | 1.3 | h3, SemiBold |
| `--pbc-heading-2` | 1.625rem | 1.25 | h2, SemiBold, a thin rule below |
| `--pbc-heading-1` | 2.25rem | 1.15 | the page title, SemiBold |
| code | 0.9375rem | 1.5 | listings and inline code |

Headings use sentence case and their own weight: no eyebrow or kicker above
a heading, no all-caps label, no accented single word in a heading.

### Space, measure, rules

- Spacing scale: `--pbc-space-1` to `--pbc-space-5` as today (0.25, 0.5, 1,
  1.5, 2.5rem); `--pbc-space-5` is also the space between the header and
  the title of every page. More space above a heading than below it.
- Measure: `--pbc-measure: 68ch` for prose (paragraphs, lists, headings,
  block quotes) inside the reading column.
- Rules: 1px in `rule` for separators and borders; one 2px cobalt rule, the
  construction line, under the header. A new component has no coloured side
  border above 1px. The side rules of the F44 components (the exercise bar,
  a claim box, the "not verified" frame, the marked line of an excerpt)
  carry meaning the reader already knows and stay as they are; F127 reviews
  them with the other lessons.
- Radius: `--pbc-radius` 0.25rem on controls (the start link, buttons,
  inputs, chips); boxes and plates are square. No soft shadows; a plate is
  set apart by its white ground and its rule.

## Components

The markup of every lesson component stays what `rendering-check.qmd`
shows; only its styles change, and the meaning and contrast of each are
kept.

- **Header** (every page). Quarto's navigation bar, on paper, with ink
  entries and the construction line below it. Left: the mark and the site
  title (the mark 2.25rem, with the title as its link's name), both links to
  the home page. Then the primary navigation: Home, Learning path (the
  atlas's display label is settled in the owner's preview), Glossary,
  Evidence, About, Set up, Contribute. Right: Source, the start link,
  "Start the course", the one filled control of the site (paper on
  cobalt), to the first lesson of the learning path, and the search box
  (9rem from 992 CSS px, so that one line holds the bar at desktop width;
  an ink icon below that width). The current page's entry has a 2px vermilion underline and
  `aria-current`. Without a script nothing collapses: the entries wrap onto
  further lines, an entry of two words stays together, and the skip link is
  the first stop of the keyboard. The header scrolls away with the page:
  a fixed header covered a third of a phone screen and could hide the
  focused element, and the theme's reveal on scrolling is motion.
  On a phone (below 768 CSS px) the bar is compact: the mark and the title
  share a row with the search control, and the entries wrap onto two rows
  below it; the lesson's contents are one wrapped row of section names above
  the title, not a column, so that the title is on the first screen.
- **Footer** (every page). A thin rule, then three groups: the F57
  attribution line exactly as `pbc.authoring.identity` writes it; the
  licences (code MIT, text and figures CC BY 4.0) with the About page; the
  source repository and the secondary navigation (Learning path, Glossary,
  Evidence, Set up, Contribute, About). Small text in `muted`, links in
  cobalt.
- **Lesson reading column** (opt-in, see below). The title, then the lesson
  header (strand, position, difficulty, prerequisites, previous and next) on
  `surface` with a thin rule, then the body. Prose at the measure; display
  equations, code listings, figures, tables, and the widget take the full
  width of the main column, wider than the prose, so a figure is larger
  where the page has room. The table of contents is in the right margin
  from 768 CSS px (the theme's breakpoint) and, below that width, in a
  framed box above the title, never hidden; there it marks no current
  section, since the reader is at the top. The
  "Run this experiment" section and its anchor are untouched (ADR 016).
- **Links.** Cobalt, underlined in running text with an offset of 0.15em;
  the underline thickens on hover. No arrow appended to link text.
- **Code.** Listings on the plate with a 1px rule, IBM Plex Mono at the code
  size, the existing `a11y` highlight style; the excerpt's source line and
  its numbered notes as today (F35). Not on `surface`: four colours of the
  highlight style have only 4.3 to 4.4:1 there, against at least 4.8:1 on
  the paper and 5.1:1 on the plate.
- **Mathematics.** Native MathML in STIX Two Math; a wide display equation
  scrolls in its own focusable box (as today).
- **Figures.** On a white plate with a 1px rule and a small inner margin;
  the caption under the plate in the body face, the figure-status label at
  its start as today (F28).
- **Result tables** (F36). On the plate; numerals tabular and right
  aligned; header row in SemiBold over a rule; no zebra stripes.
- **Claim labels, figure status.** The chips of F44, in the body face, with
  their own colours; the figure status is no longer set in capitals.
- **"Go deeper", self-checks, hints, learning box, assumptions.** Their
  F44 shapes, with the paper and surface grounds and the rules of this
  file; the dashed rule of "Go deeper" stays its distinguishing mark.
- **Path rows, path cards, the prerequisite graph** (F26, F64). Unchanged
  in structure; on paper with the rules of this file.
- **The course atlas** (F125; F126 adds its scripts). Above the course
  index of the path page: a breadcrumb under the title, a switch of three
  plain links (map, course index, concepts) with the radius of a control,
  a legend, then the map, wider than the text column on a desktop
  (Quarto's `column-page`; the page's contents in the margin stay at the
  top instead of following the reader over it, `body.pbc-atlas`). The map
  is one inline SVG at its natural size in a focusable box with the cobalt
  construction line above it; on a narrow screen it scrolls sideways in
  that box and is never shrunk. Course areas are thin-ruled boxes on paper
  with the course title, the published count, and a small illustration in
  cobalt and rule strokes; the four path lanes sit on `surface`, joined by
  one cobalt rail. A concept is a white plate with its name as a cobalt
  link and its state in `muted`; a planned concept has a dashed rule, an
  italic name in ink, and the word planned; a capstone's concept a double
  outline. Edges run at right angles along the gutters between the nodes
  and the areas, never across a node or an area's title, each on its own
  track in a gutter and its own point on a node's side: a prerequisite
  solid in `rule` with a filled arrowhead, a conceptual connection dashed
  in cobalt with an open circle at each end, a capstone membership dotted
  in ink with an open diamond. The view layer lists every lesson as a small white plate per
  method on `surface`. Below the map: the capstone projects in dashed
  boxes, the concept panels (native disclosures in a grid of course and
  path groups; a targeted panel has a vermilion top rule, the current
  position of the signature), and the textual equivalent, visually hidden.
  **Known limitation, accepted by the owner (2026-10-21).** The static map
  draws every connection at once; about 80 of them cross and crowd one
  another, which makes the relationships hard to follow. The owner accepted
  this for F125, provided that the three relationship types stay
  distinguishable, the relationships and their directions are accurate, no
  concept, label or link is obscured, and the textual equivalent stays
  complete. Reading the relationships through selection and focused
  highlighting (a chosen concept highlights its prerequisites and conceptual
  connections, with direction and meaning, reachable by keyboard) is an
  acceptance consideration of F126, not of F125.
- **Widget.** On a plate; its controls take the radius, the focus ring,
  and the cobalt of this file.
- **Focus.** A 3px cobalt ring with a 2px offset on every focusable element,
  on the header too (the white ring on the blue bar is no longer needed).
- **Browser surfaces.** Text selection in a pale cobalt tint with ink text,
  the caret and the scrollbars of scroll regions in cobalt and rule, tabular
  numerals in tables.

## The three asset classes

Every visual belongs to one class (ADR 018 decision 2). An example of each:

| Class | Example | Source | Rules |
|---|---|---|---|
| Interface artwork | the project mark in the header | an authored SVG under `site/assets/` with its entry (author, licence) in the provenance register there | no number, no caption of a result, no evidence claim; decorative or named by its link |
| Conceptual illustration | the diagrams drawn by `pbc.authoring.diagrams` in a lesson cell | an executed cell, `fig-status: conceptual` | drawn by code, labelled `conceptual`, never a result |
| Scientific result | the phase-space figure of "Numerical integrators" | an executed cell over `pbc.mechanics.integrators` | the rules of "Scientifically faithful figures" and the F63 preview contract |

An authored SVG under `site/assets/` passes the committed-artifact check
only with its provenance entry; a raster, an unregistered SVG, and every
other image file stay rejected (ADR 018 decision 2).

Known limit: for an entry that names a generating module, the check confirms
that the module can be imported, not that it writes the registered file; the
author of such an entry keeps the two in agreement. A stronger check is a
follow-up, not part of this feature.

## The mobile rule

- Below 576 CSS px the page is one column: the header wraps, the table of
  contents comes before the body, figures and tables scale or scroll inside
  their own box, and nothing scrolls the page sideways at 320 CSS px.
- A map (F125, F126) on a phone offers a readable region selector, a
  focused view of one region, and the ordinary list; a desktop map is never
  shrunk until its labels are unreadable.

## Accessibility rules

WCAG 2.1 AA on every page; reflow at 320 CSS px without two-way scrolling;
a visible focus ring on everything focusable; no meaning by colour alone;
`prefers-reduced-motion` honoured, and no motion in the chrome at all; text
resizable to 200 percent; the skip link first; every page usable without a
script. The built-site checks enforce the scan, the reflow, the keyboard
pass, and the payload; they test behaviour, never CSS values or pixels
(ADR 018 decision 6).

## The page opt-in

A lesson adopts the reading column with one front-matter line,
`body-classes: pbc-reading-column`; the lesson-source checks admit that key
with exactly that value. F123 applies it to "Numerical integrators"; F127
applies it to every lesson and then makes it the default.

## How a feature applies it

1. Read this file and, for a page or layout, the skills its plan selects
   (the README of `.agents/skills/`).
2. Use the tokens and components here; add a new one here first, with its
   contrast pairs in `design.py`.
3. Classify every new visual by its asset class and record its source.
4. Look at the built page at 1280, 768, and 375 CSS px and record the
   screenshots as evidence of the feature (never committed); the reviewer
   and the owner look at the same pages (ADR 018 decision 6).

## What the skills changed

Recorded per ADR 019 decision 6, with the skill and its revision.

**In the plan and this specification** (impeccable at 08d5b470,
frontend-design at dbd4588f):

- Frontend Design lists a warm cream ground near `#F4F1EA`, a high-contrast
  serif, vermilion, and hairline rules among the defaults of generated
  pages. The brief pins those very traits, and the brief wins; the freedom
  left was spent on what is specific to this site: the paper is lighter and
  less yellow than that cream, the serif is the companion of the math font
  rather than a display face, the signature is the construction (mark and
  rules) with vermilion only for the current position, and the plate gives
  figures a reason to be white.
- Frontend Design and Impeccable's craft floor both reject monospace as a
  costume and all-caps or eyebrow labels: monospace is limited to code,
  values with units, and addresses; labels and headings are sentence case.
- Impeccable's Read mode set the split between the frame and the column,
  the 65 to 75 character measure (68ch here), and the larger body size for
  the serif; its typeset playbook set two families and only the weights
  used.
- Impeccable's craft floor added the browser surfaces (selection, caret,
  scrollbars, tabular numerals) and the rule of more space above a heading
  than below.
- Impeccable's shape playbook ends with a confirmed brief and no code: this
  file and the plan are that brief, and the implementation waited for the
  owner's answers.

**After the build** (step 9 of the plan), from screenshots of the built
site at 1280, 768, and 375 CSS px (home, the lesson, the path page, the
glossary, and `rendering-check.qmd` in Chromium, Firefox, and WebKit):

- Frontend Design's self-critique ("a picture is worth 1000 tokens") on the
  first render: the search box fell onto a second line of the header at
  1280 px, "Source" sat off the baseline of the start link, and the site
  title was cut off with an ellipsis at 375 px. The entries went a step
  below the body size with less padding, the search box to 9rem, the bar's
  items were centred, and the title wraps.
- Impeccable's Read mode and typeset playbook: the page description under
  the title was capped at the measure like the prose; captions too.
- Impeccable's craft floor ("browser surfaces"): the table of contents kept
  the theme's bright blue for its current entry; it is vermilion now, the
  current position of the signature.
- Impeccable's audit: the first stylesheet stopped every transition and
  animation for a reader who asks for less motion, the global kill the
  audit flags; the theme already handles its own, so the rule was narrowed
  to the chrome and to scrolling.
- Impeccable's critique, its design review run as an isolated sub-agent on
  the screenshots (the detector of its second assessment did not run):
  the fixed header covered about 240 of 812 px on a phone and the theme
  revealed it on scrolling, so the header now scrolls away; the result
  tables still showed the theme's zebra stripes, which the plate removes;
  titles sat too close to the header on every page; the search icon was
  pale grey at narrow widths and is ink now; the contents above the body
  on a phone marked a "current" section and mark none now; the footer's
  secondary navigation gained About; the mark grew to 2.25rem. Its finding
  that the construction reads faintly at header size was weighed against
  the restraint of the frame and left to the owner's preview.

**The atlas** (F125; impeccable at 08d5b470, frontend-design at dbd4588f,
diagram-design at 550fd66e), from screenshots of the built path page at
1280, 768, and 375 CSS px:

- Impeccable's adapt playbook and the mobile rule above: the first render
  in Quarto's `column-page` ran under the sticky contents in the margin; the
  contents stay at the top of the page now, and the map's width (1120) was
  cut until it fits the page column at 1280 px without scrolling, while a
  phone scrolls it in its box at full size.
- Impeccable's layout and clarify playbooks: the state line of a
  three-line concept name collided with the name (the node grew to 76
  units), a capstone's state was shortened to "capstone, planned" to stay
  in its box, the view names wrap onto two lines, and on a phone the switch
  comes before the explanation, which was cut to the facts, so the course
  index is one tap away.
- Frontend Design's "visual structure is information": the areas are a
  grid in the curriculum's order, not a geography; the only accents are the
  construction rail of the paths and the cobalt of links; no card shadows,
  no numbering, no eyebrow labels.
- Diagram Design's principles for the illustrations: one system per course
  in a 44-unit box, about nine elements at most, meaning by line and shape
  (no colour-only cue), no text and no number, `aria-hidden` because the
  course title beside it names the area; the geometry is right (the
  pendulum's arc is centred on its pivot, the star sits at a focus of the
  orbit, the oscillator's levels are equally spaced from half a spacing
  above the bottom of a true parabola, the field lines and the streamlines
  are symmetric).
- Diagram Design's "arrows mean something, and the legend says what": three
  edge types, three dash patterns, three end marks, each named in the
  legend; the remove test dropped labels on edges, which the panels and the
  textual equivalent carry. Its rule that an arrow passes behind no element
  it does not connect, raised by the independent review of the first
  render (straight edges crossed the concepts at 1280 px): the edges are
  routed along the gutters at right angles, each on its own track, and the
  gutters were widened for them.

The automated detector of Impeccable did not run and will not: the project
runs none of a skill's scripts (ADR 019).
