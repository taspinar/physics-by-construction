# Plan: F156 — Course introductions: the source, the generator, and the pilot, Issue #372

- Issue: #372 (source: `docs/roadmap.md`, F156). Written by the implementer: no
  plan existed when the feature started.
- Branch: `feature/372-course-introductions-the-source`; base `37e5b97` (F136 merged).
- Risk: Level 2 (source, tests, lessons' shared template, prose data). Level 3
  only if an existing assertion of the atlas, lesson-header, or learner-state
  tests changed; none does (the new links are additive and tested apart).
- Verification: the full run, since a shared input (`pbc.authoring`, the shared
  CSS, the lesson header) changes.

## Decisions fixed by this plan

- **Address.** Flat `/courses/<sequence-id>/`; page source
  `site/courses/<id>/index.qmd`; identifiers unique across courses and paths
  (`sequence_ids` checks).
- **Source.** `site/introductions/<id>.yaml`: `sequence` plus the seven sections
  `why`, `questions`, `learn`, `order`, `method`, `capstone`, `next`, each a
  non-empty list of inline-Markdown texts. Unknown or missing field, a hand-written
  link, block Markdown, raw HTML, or a count of lessons or slots is an error.
- **Reference syntax.** `{sequence:<id>}`, `{slot:<label>}`, `{term:<glossary
  term>}`. A planned slot renders as `<working title> (planned)`, text, never
  a link.
- **Links.** The atlas panel ends with a paragraph `atlas-introduction` (after the
  rows and the extensions, so the first Tab into a panel still reaches the first
  lesson) for a sequence with a data file; the lesson header gains one term,
  "Introduction", after Course and Slot, that links the names of the lesson's
  course and method path that have an introduction. The Course and Slot rows
  and their links are untouched. The two e2e tests that pin the header's term
  list and the panel's tab order change by exactly these additions: that makes
  the change Level 3 (the Issue's own rule), recorded in
  `.agents/approvals/372.md`.
- **Page.** The page source carries the sequence's title as its `title` (Quarto does
  not take a generated heading as the title; `page_source_problems` keeps the
  two equal); the generated body has the breadcrumb, registered panel illustration (reused through the atlas's own
  image method, so the alternative text comes from the same place), the seven
  sections, "Prerequisites" (lessons of other sequences named by the front matter
  of the sequence's lessons, and the glossary terms of their `outside` lists), and
  "The lessons" (counts as the atlas derives them, extensions apart, planned rows
  with label and working title and no link).

## Steps

1. Tests for each rule (`tests/unit/test_introductions.py`).
2. `pbc.authoring.introductions`; helpers in `website.py`; `introduction_content`
   exported.
3. Panel link (`atlas.py`), header links (`path.py`); CSS (`.intro-*`,
   `.atlas-introduction`).
4. Page sources and the two data files.
5. `docs/editorial-voice.md` ("Pages that are not lessons"), `docs/authoring.md`
   ("The course introductions").
6. Independent scientific review of the two texts (a different model), the three-
   part rendered review, and the owner's approval of the two as the standard:
   these are `pr_ci` / `owner_approval` gates, not done in the session.

## Visual deliverables and skills

- Page and layout (the introduction page template). Expected artifact: the
  rendered pilot pages at desktop and phone widths; validation: the tests above
  and the rendered review; accessible fallback: the page itself without scripts
  and the illustration's alternative text.
- Interface artwork: the registered atlas panel illustration of each sequence,
  reused; no new image.

Skills: impeccable@08d5b470, frontend-design@dbd4588f

Applied as restraint: one column of prose at the reading measure, the existing
tokens, no new colour, no decoration beyond the registered illustration. Both
skills were read by path before the page was produced.
