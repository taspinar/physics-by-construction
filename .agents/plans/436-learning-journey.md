# Plan: F157, the learning journey (Issue #436)

Level 2. Implementer: Opus. No ADR, roadmap, requirements, or architecture
change (`docs/architecture.md` already describes F157 and is protected).

## Visual deliverables

Skills: impeccable@08d5b470, frontend-design@dbd4588f

- Page and layout: the opening section of the Course Atlas and the About
  page, with the two skills above. Expected artifact: the rendered `path/index.html` and `about.html`. Validation: the
  tests and the three-part rendered review (screenshots at 1280, 768, 390,
  and 320 CSS px in the pull request, the reviewer's assessment, the owner's
  pass). Accessible fallback: both pages are complete without scripts; the
  journey is a native disclosure with no script. No scientific figure, no
  conceptual diagram, no new artwork.

## The constraint that shapes the atlas opening

F133's acceptance criterion 1 and its test
`tests/e2e/test_atlas.py::test_a_wide_screen_shows_the_cards_and_the_first_panel_beside_them`
require the first course's panel title, description, and third row inside
a 1280 by 800 window without scrolling. Measured on the base page, the
third row ends at 722 px: 78 px of headroom. The five points of decision 43
cannot be shown open before the cards without changing that assertion,
which the Issue makes Level 3 ("say so and stop").

Chosen (Level 2, no assertion changes): the journey stands before the
cards, after the breadcrumb and before the atlas summary, as one native
`<details>` (closed by default, not in the cards' exclusive group, no
script) whose summary names it; opening it shows the whole journey. A
heading id inside it (`#journey-*`) opens it on navigation in browsers that
expand details for a fragment. The alternative, the journey open by default
with the F133 window assertion moved, is recorded for the owner's pass on
the rendered page; it is a Level 3 change and is not made here.

Owner decision (2026-11-09, after the outside review's major that the
disclosure is closed at load): option A. The disclosure stays closed at
load, and acceptance criterion 1 is relaxed to say so: the Course Atlas
offers the learning journey before the cards behind a native disclosure
that is closed at load, with its summary line always visible; opened, it
covers the five points of decision 43. The F133 test is unchanged.

## Steps

1. `site/journey.yaml`: prose and references only, the fields `part-a`,
   `part-b`, `relation` (the Part A and Part B text shared with About),
   `background`, `routes`, `capstones`, and `evidence` (a mapping of
   exactly `numerical`, `empirical`, `formal-proof`). Draft identity copy,
   for the owner's approval.
2. `pbc.authoring.journey`: the reader and its rules, reusing the text and
   reference rules of `pbc.authoring.introductions` (inline Markdown, one
   paragraph per text, no count of lessons or slots, no lesson named outside
   a reference, every reference resolves) and adding two: no count of
   courses or method paths, and no form of "discover" outside a reference
   (a guard against presenting an AI result as a discovery; the review
   decides the rest). Failing test per rule first (criterion 3).
3. The reference resolution of an introduction moves into a small resolver
   that the introductions and the journey share; the introduction pages
   stay byte for byte as they are (their tests).
4. The atlas: `AtlasSection` gains an optional journey, emitted after the
   breadcrumb; without it the section is what it was (a test).
   `course_atlas()` reads `site/journey.yaml`.
5. About: the mission (under the kept anchor `#why-it-exists`) and the
   educational philosophy; the Part A, Part B, and relation text from the
   source under `#what-this-site-is` with the generated lists of courses
   and paths; the attribution cell unchanged; the verification account
   replaced by a link to "How we verify the science" under the kept anchor
   `#how-the-site-is-built`, which keeps the facts about how the site is
   built (static files, no cookies, readable without scripts). Every
   existing anchor kept (a test).
6. CSS in `site/assets/site.css` for the disclosure and the journey's
   reading layout; tokens of the site only.
7. Docs: `docs/authoring.md` gains the journey file's rules.
8. Verification: unit tests of the changed modules, `--only` of the touched
   groups, `--targeted`; the full run is the script's after the session
   (the Issue's instruction).

## For the pull request description

The full text of the journey (`site/journey.yaml`) and of the new About
sections (`site/about.qmd`, "Why it exists", "The educational philosophy",
"How the curriculum is organised", "How the site is built") goes into the
pull request description for the owner's reading, marked as a draft of
identity copy that is not approved.
