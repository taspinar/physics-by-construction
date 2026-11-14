# Plan: F175, code presentation (Issue #529)

Change request section 11 (U1b, U1f, U1g, U1i) and section 14;
requirements decision 44; ADR 023 decisions 3 to 7;
`docs/architecture.md`, "The code a lesson shows". A presentation change of
every page with an excerpt: no lesson, no source module, no displayed
number, figure, or claim changes.

**Level 3**: `src/pbc/authoring/lean.py` is a protected path (the Lean
excerpt gets the same compact Source link, acceptance criterion 3), and the
diff changes assertions of existing tests (the sentence "read from the
repository when this page was built" and the listing markup that the
excerpt tests and the e2e tests read). No assertion is weakened: each
changed one is replaced by one that checks the same fact on the new markup,
or a stronger one. Shared inputs change (`src/pbc/authoring`,
`site/assets/site.css`), so CI runs everything; the session runs the unit
and integration tests of the changed modules and a single-page render; the
full verification of the final tree runs after the session (the owner's
rule of 2026-11-08, on the Issue). The approval request
`.agents/approvals/529.md` asks for the owner's review of the exact head.

## Visual deliverables

Skills: frontend-design@dbd4588f, pbc-physics-teaching

- **Page presentation of code** (every excerpt). frontend-design for
  restraint: the site's tokens only, no new decoration; the labels are
  sentence-case words, never capitals or glyph-only marks.
  pbc-physics-teaching ("Code the learner reads": a fragment is not
  offered as a runnable whole; a docstring may be left out where the prose
  says it) for the wording of the labels. Expected artifact: a rendered
  page with a plain, an annotated, a multi-range, a docstring-omitting, and
  a generated-signature excerpt. Validation: the unit tests of
  `pbc.authoring.excerpt`, the context tests, the built-site excerpt check,
  the e2e tests of the annotated lesson. Accessible fallback: no script is
  involved; labels and omission markers are text; line numbers and note
  glyphs are generated content outside the copied text.
- No scientific figure, diagram, or animation.

## Decisions

1. **One highlighter.** Annotated and selected listings become Pandoc
   code blocks, converted by the same `quarto pandoc` run as plain ones
   (the a11y highlight style); no Pygments, no new dependency. After the
   conversion, `pbc.authoring.excerpt.number_lines` rewrites the line spans
   of a block marked `.excerpt-listing` into `span.line` with `data-line`
   (the source line) and, for a noted line, `.marked` and `data-note`.
   Line numbers and "note n" stay CSS generated content, so the copied
   text is the code.
2. **Exact selection** (ADR 023 decision 3). `lines=` takes one range or a
   sequence of ascending, non-touching ranges of the object; each range is
   its own listing, joined by an omission marker ("Lines a to b are not
   shown.") with `data-omitted`. The parts sit in one element with
   `data-source` and `data-lines="a-b,c-d"`, which the built-site check
   compares part by part, byte for byte, with the source, and whose
   markers and line numbers it checks. No whitespace rule is needed: the
   parts are the source lines as they are.
3. **Docstring omission.** `docstring=False` leaves out the docstring of a
   function or class (found by `ast`), marked "The docstring, lines a to
   b, is not shown." (`data-what="docstring"`); the built-site check
   confirms the gap is exactly the docstring.
4. **Generated signature** (decision 4). `signature=True` (a function
   only) replaces the source lines of the header with a block generated
   from the function: the parameter names and kinds from the function's
   signature, the defaults as written in its source (checked against the
   runtime values where they are literals), the units of the interface
   table as comments, ending in `: ...`. It is labelled "Generated
   signature ...; not the source text", carries `data-signature`, and the
   built-site check regenerates it independently from the source file.
5. **Labels.** A selection says it is one and that the Source link opens
   the whole object; a selection gets no copy button. The whole object
   keeps its copy button (plain or annotated).
6. **Compact Source link** (U1b). Every Python and Lean excerpt ends with a
   link "Source" (visually hidden text names the object and lines for a
   screen reader; `title` gives the path and lines), whose `href` is the
   file at the built commit with the line range, and which carries
   `data-path`, `data-lines`, `data-commit`. The range is the whole object
   (functions and classes), the shown lines (module parts, Lean regions).
   `source_link(obj, figure=True)` gives the Source-link-only form,
   "Figure source". Without a commit the link is the path and lines as text.
7. **Executed teaching code** (decision 5) is not built: no pilot (F165,
   F167, F176) has asked for it, and the ADR builds only what the pilots
   need. An executed cell of a lesson stays the form of code the build
   runs; the authoring guide says so.
8. **Lesson source check** (decision 7). A lesson may not write the markup
   of a verified form by hand: a block, div, span, or link with a class of
   the excerpt forms (`excerpt`, `excerpt-source`, `excerpt-label`,
   `excerpt-omission`, `excerpt-selection`, `excerpt-listing`,
   `excerpt-part`, `excerpt-signature`, `lean-excerpt`, `source-link`,
   `figure-source`), a `source=`, `signature=`, or `source-name=`
   attribute, or raw HTML with one of them, is a violation,
   `forged-excerpt`, also inside a "not verified" block; the "not
   verified" rule is unchanged.
9. **Marked-line contrast.** With token colours on a marked line, its
   tint is the token `--pbc-marked-line` (`#f2f6fa`, 5 % of the link blue
   on white) of `pbc.authoring.design`, whose tests check it at 4.5:1
   against the line numbers and every colour of the a11y style (the
   lightest keeps 4.66:1; the old 12 % tint would give 4.1:1).

## Steps

1. `pbc.authoring.excerpt`: the parts, the omissions, the signature, the
   labels, the Source link, `number_lines`, `source_link`; unit tests.
2. `pbc.authoring.context`: `number_lines` before the copy button; no copy
   button on a selection; context tests.
3. `pbc.authoring.lean`: the compact Source link; unit test.
4. Built-site check (`tests/support/site_checks.py`): parts, omissions,
   line numbers, docstring gap, generated signature, Source links; its
   integration tests; the e2e tests of the annotated lesson and the Lean
   links.
5. Lesson source check `forged-excerpt`; integration test.
6. CSS: the line spans in a Pandoc block, the labels, the omission
   marker, the Source link; contrast of the marked line.
7. Docs: `docs/authoring.md`, "Code"; `docs/architecture.md` (the
   delivered forms); `docs/development.md` (the check list).
8. Samples of the generated signature with the docstring left out, a
   two-range selection, and a Figure source link on
   `site/rendering-check.qmd` (the page of component samples), so that the
   built-site check and an e2e test read every form on a built page;
   single-page renders of M2 (`mechanics/02-newtons-laws`) and the
   rendering-check page; screenshots at 1280 and 320 px in the handoff
   folder `529-screenshots`.
