# Plan: compact code display (Issue #536)

Follow-up of F175 (#529); the owner's requirements of 2026-11-15 on the
Issue. A presentation change of the shared excerpt display
(`pbc.authoring.excerpt`, `site/assets/site.css`) and of its checks; no
lesson, no source module, no displayed number, figure, or claim changes.
The content correction of MAT6 stays in #535.

**Level 3**: the diff changes assertions of existing tests (the label
sentences, the omission sentence, the multi-line generated signature, the
Source link text of a selection). No assertion is weakened: each changed
one checks the same fact on the compact markup, or a stronger one. Shared
inputs change, so CI runs everything; the session runs the unit and
integration tests of the changed modules and a single-page render, and the
full verification of the final tree runs after the session (the owner's
rule on the Issue). The approval request is `.agents/approvals/536.md`.

## Visual deliverables

Skills: frontend-design@dbd4588f, pbc-physics-teaching@7f34987

- **Page presentation of code** (every selection of a function, every
  excerpt with an omission). frontend-design for restraint: the site's
  tokens, no new colour, sentence-case labels, no glyph-only marks without
  text for a screen reader. pbc-physics-teaching ("Code the learner reads")
  for what the reader needs around a fragment: the interface on one line,
  the line numbers, where lines are missing, and the way to the whole
  function. Expected artifact: `site/rendering-check.qmd` and MAT6 rendered
  at desktop, 390 px, and 320 px. Validation: the unit tests of
  `pbc.authoring.excerpt`, the integration tests of the built-site excerpt
  check, the e2e tests. Accessible fallback: every `(...)` marker carries
  the omitted lines as visually hidden text and in `data-omitted`; a
  selection carries a visually hidden label; no script.

## The display

1. **Header.** Above every selection of a function whose shown lines do
   not include its header as written, a header generated at build time on
   one line: `def name(a, b, c=0.0):`, the defaults as the source writes
   them, no annotations, and the units of the docstring as one trailing
   comment (`# dt (s), return (m)`) when it gives any (ADR 023 decision 4
   keeps every default and unit). No line number; the label "Shortened
   function" beside it. A header shown as written is shown once, exact.
   `signature=True` replaces a shown header with the generated one.
   Long headers wrap at the spaces after the commas on a narrow screen.
2. **Labels.** The "Generated signature of …" and "Selected lines of …"
   paragraphs go; a visually hidden sentence keeps the selection labelled
   for a screen reader (ADR 023 decision 3).
3. **Omissions.** Every gap, including before the first and after the last
   part, is a `(...)` line of its own, outside the code blocks, muted; the
   sentence "Lines m to n are not shown." (or the docstring's) is visually
   hidden text, the range in `data-omitted`.
4. **Link.** Under a selection of a function or class: "Full function on
   GitHub" ("Full class on GitHub"), opening the whole object at the built
   commit; whole excerpts, module regions, Lean excerpts, and the Source
   link alone keep "Source".
5. **Checks.** The built-site check reads the one-line header (parameters,
   defaults, units, what it replaces), the omissions at both ends, the
   visible `(...)`, and the new link text; the lesson source check lists
   the new classes as forged markup.
6. **Docs.** `docs/authoring.md` (the forms table) and
   `docs/architecture.md` ("The code a lesson shows").
7. **Screenshots** (criterion 7) of MAT6's two sections after #535 merges
   into the branch; until then of `site/rendering-check.qmd` and the
   current MAT6.
