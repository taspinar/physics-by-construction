# Plan: F135 — The glossary in context and Suggest an improvement, Issue #340

- Issue: #340 (source: `docs/roadmap.md`, F135; requirements decision 40;
  ADR 021 decisions 5 and 6).
- Branch: `feature/340-the-glossary-in-context`; base `b6b754f` (F134
  merged).
- Written by the implementer: no plan existed when the feature started
  (the Issue asks for a short plan).
- Risk: Level 2 (the lesson regions of `pbc.authoring`, the shared CSS,
  the Contribute page, the issue forms). No existing assertion is changed
  or removed: the glossary, prerequisite, header, educators, identity,
  and context tests stay as they are, and the new behaviour has new tests.

## The glossary in "Before you begin"

Both the header and the last section of a lesson are post-render regions
(`pbc.authoring.context`): they are rebuilt from the current sources after
the render, so no lesson is executed again for this change.

- The list of outside prerequisites stays exactly as `before_you_begin()`
  writes it: each term linked to its entry on the glossary page, with its
  detail. That link is the "link to the glossary page" of criterion 1.
- After the list, `glossary.definitions()` writes one native
  `<details class="glossary-definition">` per glossary entry the lesson
  names (once per entry, in the order of the list), the term as its
  summary and the entry's definition from `site/glossary.yaml` as its
  body, under the line "Definitions from the glossary:". A prerequisite
  without an entry gets none and its item is unchanged. Text is
  HTML-escaped; nothing is written twice (the definition is read, not
  copied).
- Why after the list and not inside each item: the summary of a disclosure
  inside an item would change the item's text, which the end-to-end test
  of the header compares with the front matter, and a second link inside
  it would change the item's links; the Issue keeps those checks
  unchanged (criterion 3, and the Risk paragraph: no assertion changes).
  The disclosures are compact, one row of summaries that wraps; an open
  one takes the full width.

## Suggest an improvement

- `pbc.authoring.improvement`: the three forms (scientific correction →
  `scientific-correction.yml`, report a problem → `bug.yml`, propose a
  change → `feature.yml`), the field id `page`, `form_url()` (the
  repository's `issues/new?template=<form>.yml&page=<address>`, the
  address URL-encoded), and `suggestion()`, the Markdown line of the
  lesson: "Suggest an improvement: scientific correction · report a
  problem · propose a change".
- The address is the lesson's canonical URL: `website.site-url` of
  `site/_quarto.yml` and the built page (`…/index.html`), read by
  `website.site_url()` in the post-render step; a project without a
  `site-url` (test fixtures) gets the page's path in the site instead.
- `Reproduction` gains the field `address` (default ""), filled by
  `context.markdown()`; its `markdown()` ends with the line inside the
  `.reproduce` block, after the live run, so it is the last line of the
  last section of every lesson.
- The forms: `id: page` on the Page field of `scientific-correction.yml`;
  an optional Page input with `id: page` added to `bug.yml` and
  `feature.yml` (not required, so an issue not about a page is still
  possible). No other field changes.
- Contribute page (`site/contribute.qmd`): at the top, the sentence that
  a GitHub account is needed and issues are public, and the three links,
  printed by the existing `forms_list()` of `pbc.authoring.educators`,
  which gains an optional `forms` argument (default: the educators' forms,
  unchanged) and builds each link with `form_url()`.

## Tests

- `tests/unit/test_improvement.py`: every generated link of a lesson
  names an existing template and only parameters that are `id`s of a
  field of it (and the test fails for a missing template or an unknown
  parameter, shown on fixtures); the page parameter carries the address;
  each prefilled field has an `id`; the Contribute list has the three
  forms without a page.
- `tests/unit/test_glossary_definitions.py`: `definitions()` (one per
  entry, none for an unknown term, escaped, no link) and the header with
  the definitions after the unchanged list.
- `tests/unit/test_improvement.py` also: the post-render last section
  ends with the line, with the address from `site-url`.
- `tests/e2e/test_glossary_and_improvement.py`: every built lesson's
  last line is the three links with its public address and the forms'
  field ids; the definitions of three lessons open without scripts and
  show the glossary's text; the Contribute page opens with the three
  forms and the sentence on the account and public issues.
- New tests are in new files, so that no existing test line changes.

## Docs

`docs/authoring.md` ("Glossary", "The last section", the `site-checks`
row). `docs/architecture.md` is protected and already
describes F135.

## Visual deliverables and skills

Page and layout: the disclosures in "Before you begin" and the link line
of the last section, small additions to existing components.

Skills: none (two small text components in the existing lesson layout;
no new page, artwork, diagram, or figure; the existing disclosure style
of the last section is reused).

Expected artifact: a built lesson page. Scientific validation: none (the
definitions are the glossary's text). Accessible fallback: native
disclosures and plain links; no script.

## Manual check (criterion 2c)

Open one generated link on github.com in a real browser and see the Page
field filled with the lesson's address. GitHub reads issue forms from the
default branch, so the field `id`s take effect only after the merge, and an
unattended session has no browser: the check is `pending` at the gate
`post_merge`, recorded in the completion evidence when it is made.
