# Plan: F123, the atelier foundations (Issue #217)

Source: Issue #217 (the authority on what is delivered) and the owner's
override on it (plan and design specification first, then stop for the
owner's look before the implementation; within this feature only, no home
page, no atlas); the change request `docs/changes/scientific-atelier-atlas.md`
sections 1, 3, 4, 7, 8, 9; requirements decisions 36 and 37; ADR 018
decisions 1, 2, 5, 6; ADR 019 (decision 6, the pilots); ADR 002 decision 2
as ADR 018 amends it; ADR 014 decision 4 and ADR 017 decision 7 (a shared
input: the last verification is the full run). Risk: Medium (Issue). F122
(Issue #215) is merged, so its skills and contract exist.

Context: base `origin/main` at `2a1fea4`; the branch held no work when this
plan was written (2026-10-19).

## Visual deliverables and skills

| Deliverable | Class | Expected artifact | Scientific validation | Accessible fallback |
|---|---|---|---|---|
| The design specification | none (a document) | `docs/atelier.md` | none: it states presentation rules only | text |
| The shared header and footer | page or layout | the Quarto navbar and page footer of every page, restyled; `site/assets/site.css` | none; it carries no science | native links, no script, skip link first |
| The lesson reading column | page or layout | CSS scoped to `body.pbc-reading-column`, applied to "Numerical integrators" | the lesson's cells, numbers, figures, claims, identifiers, and commands unchanged (reproduction and experiment checks) | the page is the same document without the class |
| The project mark | interface artwork | the authored `site/assets/mark.svg` with its provenance entry | none: no number, no result, no caption | `alt` naming the project in the header link |

The header and footer, and the reading column:

Skills: impeccable@08d5b470, frontend-design@dbd4588f

The project mark:

Skills: frontend-design@dbd4588f

The specification itself, and the classes that do not occur:

Skills: none (the specification is a document; no conceptual diagram and no scientific figure, so diagram-design and pbc-scientific-visualization do not apply)

## Current state (inspected at 2a1fea4)

- `site/_quarto.yml`: theme `default`, `css: assets/site.css`, a navbar
  that does not collapse (entries Home, Learning path, Glossary, Evidence,
  About, Set up, Contribute; Source on the right; Quarto search in the bar),
  `page-footer` with `PBC-ATTRIBUTION` on the left (replaced after the render
  by `site/attribution.py` from `pbc.authoring.identity`) and the two
  licences in the centre. Quarto 1.10.19 (`quarto-cli` in the locked
  environment).
- `site/assets/site.css` (1229 lines): F44 tokens in `:root` (colours from
  `src/pbc/authoring/design.py`, type scale, spacing), the math font
  `@font-face`, the navbar on its theme blue `#517699`, the focus rings, the
  skip link, and every lesson component.
- `src/pbc/authoring/design.py`: `PAGE`, `CLAIM_LABELS`, `STATUS_LABELS`,
  `FIGURE_COLOURS`; `colour_pairs()` is what `tests/unit/test_design.py`
  checks. `FIGURE_COLOURS` is read by lesson cells, so a change to it changes
  lesson figures: it stays unchanged (out of scope: no figure changes).
- Fonts: `site/assets/fonts/` holds STIX Two Math 2.13 b171 and `OFL.txt`,
  recorded in `fonts/README.md` with its SHA-256; listed in `resources`.
- The lesson header (`pbc.authoring.path.LessonHeader`) already shows the
  prerequisites and the previous and next lesson; Quarto's `toc: true` gives
  the table of contents. The reading column needs CSS and a page opt-in, not
  new markup.
- Front matter: `tests/support/lesson_checks.py` admits the top-level keys
  `title`, `description`, `lesson` only (`_FRONT_MATTER_KEYS`). Quarto 1.10
  supports `body-classes` (document option, HTML).
- Committed-artifact check: `check_committed_files` in
  `tests/support/lesson_checks.py`, run by
  `tests/lessons/test_lesson_sources.py::test_no_generated_artifact_is_committed`;
  `.svg` is among `_GENERATED_SUFFIXES["figure"]` and is rejected anywhere
  under `site/` and `src/`. No `.svg` is tracked under `site/` today.
- Built-site checks of the criteria exist: navigation fit, WCAG scan, the
  keyboard pass, the payload budget (`PAYLOAD_BUDGET = 3_000_000`, printed per
  page), the reflow at phone, tablet, desktop, no other-origin request, the
  footer licences, the sample page in Chromium, Firefox, and WebKit
  (`--engine`), the identity checks (`tests/e2e/test_identity_site.py`).
- The lesson chosen: "Numerical integrators"
  (`site/lessons/mechanics/05-numerical-integrators/index.qmd`): format 2,
  the only format-2 mechanics lesson with a widget (the integrator explorer)
  besides the strain lab, with figures, code excerpts, display equations,
  and result tables.
- `docs/project-map.md` and the scripts are template-owned
  (`.agents/template.conf`); the row this feature adds to the map is a
  project row, recorded here for the template sync.

## Decisions of this plan

1. **The specification first.** `docs/atelier.md` is written before any
   CSS, and the owner looks at it and at this plan before step 3 (owner
   override). Its outline is in the file; its token table is the source the
   CSS copies.
2. **Colours.** The page palette of `design.py` (`PAGE`) changes to the
   atelier values of the specification (paper, ink, muted, cobalt, vermilion,
   rule, surface, plate); `CLAIM_LABELS`, `STATUS_LABELS`, and
   `FIGURE_COLOURS` keep their values and their meaning. New pairs join
   `colour_pairs()` (vermilion on paper, ink on plate, paper on cobalt for the
   start link, the header text and focus ring on paper); no requirement is
   lowered (the rule stays at 3:1). The navbar keys become the header keys.
3. **Fonts.** STIX Two Text (Regular, Italic, SemiBold) for the headings and
   the body, the companion of the math font already served, so prose and
   MathML share one design; IBM Plex Mono (Regular) for code and
   annotations. Both SIL OFL 1.1, from their upstream tags, subset with
   `pyftsubset` (fontTools of the locked environment; the WOFF2 writer needs
   `brotli`, taken for the one-off command with `uv run --with brotli`, not
   added to the lock) to Basic Latin, Latin-1, Latin Extended-A, General
   Punctuation, Greek, and the arrows and math operators the prose uses;
   files `site/assets/fonts/<Face>-<Style>.subset.woff2`, the command, the
   upstream tag and file, and each SHA-256 in `fonts/README.md`; licence
   texts beside them (`OFL.txt` covers STIX; `OFL-IBMPlex.txt`). Listed under
   `resources`; `font-display: swap` with metric-compatible fallbacks. The
   payload test prints the sizes; a face over budget is subset further or
   dropped (Plex Mono first, falling back to `ui-monospace`).
4. **Header and footer through Quarto's website templates, not partial
   overrides.** The navbar (`website.navbar`, with `logo: assets/mark.svg`,
   `logo-alt`, the entries, the start link as the last right entry with the
   class `pbc-start`) and `website.page-footer` (left: `PBC-ATTRIBUTION`
   unchanged; centre: the licences; right: the source link and the secondary
   navigation) are Quarto's shared templates of the header and footer; the
   CSS restyles them. No copy of Quarto's internal HTML template is
   committed (it is version-bound and would change every page on a Quarto
   update). This is the reading of "template partials and includes" this
   plan takes; see Open question 1.
5. **Navigation.** Home, Learning path (the atlas label is settled in the
   owner's preview, not here), Glossary, Evidence, About, Set up,
   Contribute, Source; the start link "Start the course" points to the first
   lesson of the learning path, and a unit test fails when it differs from
   `LearningPath`'s first lesson. Search stays in the bar. Without a script
   the entries wrap (the existing rule); nothing collapses.
6. **The reading-column opt-in** is the Quarto option `body-classes:
   pbc-reading-column` in the lesson's front matter. The schema check admits
   the top-level key `body-classes` with exactly that value and rejects any
   other, with a test per case. The CSS of the column is scoped under
   `body.pbc-reading-column`; the lesson's text, cells, and identifiers are
   untouched: its diff is that one front-matter line.
7. **The mark** is an authored SVG, `site/assets/mark.svg`, drawn for this
   project (author Ahmet Taspinar with the implementing agent, licence CC
   BY 4.0 as the site's other visual content), a geometric construction
   (compass arc, radius, and a constructed point), cobalt strokes with one
   vermilion point, no text, no number. It is decorative inside a link whose
   accessible name is the site title.
8. **The provenance register** is site/assets/provenance.yaml (a file this feature creates): a mapping
   from the path under `site/assets/` to either `{author, licence, source}`
   (authored) or `{module}` (generated at build time; none in this feature).
   The asset-source rule (`check_asset_sources` in
   `tests/support/lesson_checks.py`, a test in `tests/lessons`) fails on an
   SVG under `site/assets/` without an entry, an entry without its file, an
   authored entry without author or licence, an unknown field, and a
   `module` that does not import.
9. **The committed-artifact exemption** (ADR 018 decision 2):
   `check_committed_files` admits a tracked `.svg` exactly when its path is
   under `site/assets/` and the register names it with an author and a
   licence; everything else is unchanged. The failing tests are written
   first (fixture repositories in `tests/unit` or `tests/integration`): a
   registered SVG under `site/assets/` accepted; an unregistered SVG there
   rejected; an SVG registered without a licence rejected; a `.png` under
   `site/assets/` rejected; a `.webp` and a `.gif` there rejected; a
   registered-looking SVG outside `site/assets/` (`site/x.svg`,
   `src/pbc/x.svg`) rejected.
10. **The rendered review**: screenshots with the pinned Playwright browser
    of the built site at 1280, 768, and 375 CSS px of the home page as it
    is, the lesson, the path page, and the glossary, saved outside the
    repository under `.agents/run/217/screenshots/` (Git ignores it) and
    attached to the Issue by the human or by `publish-feature.sh`'s
    evidence; never committed.

## Steps

1. Write this plan and `docs/atelier.md`; register the specification in
   `docs/project-map.md`; point the "Visual design" section of
   `docs/authoring.md` to it. **Stop: the owner looks at both.**
2. Apply the owner's corrections to the plan and the specification.
3. Failing tests first: the committed-artifact cases of decision 9; the
   asset-source rule of decision 8; the `body-classes` schema cases of
   decision 6; the start-link test of decision 5; the new colour pairs.
4. The register and the two checks (decisions 8 and 9); the mark.
5. Tokens: `design.py` and the `:root` block of `site.css`; the header and
   footer CSS; the focus rings and the skip link kept.
6. Fonts: download, subset, record, `@font-face`, `resources`; measure.
7. `_quarto.yml`: navbar (logo, entries, start link) and footer.
8. The reading column CSS; the opt-in line in "Numerical integrators".
9. Build; run the built-site checks, the three engines on
   `rendering-check.qmd`, the keyboard pass, the reflow; take the
   screenshots; review against the specification with the Impeccable
   critique and audit playbooks and the Frontend Design self-critique;
   record what each skill changed in `docs/atelier.md` ("What the skills
   changed") and in the completion evidence.
10. Documentation: `docs/authoring.md` (opt-in, mark, register),
    `docs/architecture.md` I6 and Boundaries if their wording names the
    check, `site/assets/fonts/README.md`.
11. The full `./scripts/verify.sh` last (a shared input changes).

## Verification strategy

- Unit and lesson-source tests for the checks (each case fails before the
  change), the contrast pairs, the start link.
- Built-site tests unchanged in their requirements: WCAG scan, keyboard
  pass, navigation fit, reflow, payload (sizes of the heaviest lesson, the
  path page, and the home page recorded for the pull request), no
  other-origin request, footer licences, identity, the F117 experiment
  section tests, internal links, determinism, reproduction of the lesson.
- `rendering-check.qmd` in Chromium, Firefox, WebKit (`--engine`), with a
  screenshot of each.
- No test of CSS values or of pixels (ADR 018 decision 6).

## Risks

- Every page changes: the full run (21 to 31 minutes for `build`).
- The reflow and navigation-fit checks with the mark and a start link in the
  bar on a 320 px screen: the entries wrap; the mark shrinks to its minimum
  size and never hides an entry.
- Font payload: STIX Two Text subsets are estimated at 40 to 70 kB each;
  measured in step 6.
- Figures are white raster images on a paper page: the specification sets
  each on a white plate with a thin rule, so no figure changes.

## Owner's answers (2026-10-19)

1. Header and footer: Quarto's built-in navigation bar and page footer,
   restyled with CSS; no copied template partials (decision 4 stands).
2. Fonts: one serif, STIX Two Text, for headings and body, plus IBM Plex
   Mono (decision 3 stands).
3. The mark: credited to the owner, Ahmet Taspinar, under CC BY 4.0
   (decision 7 stands).
4. "Start the course" goes to the first lesson of the learning path,
   "Kinematics as a program" (decision 5 stands).

## Discoveries during the implementation

- Quarto's navbar items accept no `class` (the schema's
  `navigation-item-object` is closed). The start link takes its class from
  the Markdown of its `text`: `[Start the course]{.pbc-start}` renders a
  span with that class inside the link, which the CSS styles and the start-
  link test finds.
- `PAGE["muted"]` is drawn by lesson cells (two experiment modules) and one
  lesson shows that code, so it keeps its F44 value `#57606a` (6.0:1 on the
  paper); decision 2's new `muted` is dropped.
- Four colours of the `a11y` highlight style fall to 4.3 to 4.4:1 on
  `surface`, so code listings sit on the plate.
- IBM Plex Mono's licence reserves the name "Plex": served whole (45 kB),
  not subset. The STIX Two Text subsets are 73 to 78 kB each and the
  subset command is reproducible byte for byte.
- Quarto writes the navbar logo without `width` and `height`, which the
  image check requires: the post-render step `site/mark.py` adds them.
- Quarto's fixed header (headroom) covered a third of a phone screen and
  moves on scroll: the header is static. Below 768 px the theme hides the
  margin table of contents; the reading column shows it above the title.
- The conceptual fallback previews of the path page
  (`pbc.authoring.previews.fallback`, "a card in the colours of the site")
  take the new `surface` and `text`; no lesson figure reads them.
- The plate is drawn on the holder of the figure image, not the image: the
  widget's drawing sets its aspect ratio on its border box, so padding on
  the image itself moved the page by 3.7 px when the widget loaded (the
  layout-shift test of the widget).
- `site.css` had an unclosed rule (`div.not-verified div.sourceCode`) that
  swallowed the recommendation panel's rules; closed.

## Next action

Steps 3 to 11 are implemented in the worktree. The owner confirmed on
2026-10-20, in the conversation, that the answers to the four questions are
the approval of the plan and `docs/atelier.md` and that the implementation
stays in this branch (recorded on the Issue, 2026-10-20). Open: the rendered
review's three parts on the Issue (the implementer's screenshots, the
reviewer's assessment, the owner's pass), which the owner does after the
pull request exists; criterion 6 stays pending until then.
