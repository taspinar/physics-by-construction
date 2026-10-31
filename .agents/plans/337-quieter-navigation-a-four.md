# Plan: F132 — Quieter navigation: a four-item menu, the secondary pages in the footer, About brought up to date, Issue #337

- Issue: #337 (source: `docs/roadmap.md`, F132); "Detailed implementation
  plan expected: no; short plan".
- Branch: `feature/337-quieter-navigation-a-four`; base `e58d2ac`.
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 3 by trigger: the assertion of `tests/unit/test_site_chrome.py`
  that lists the eight items of the bar, and the start link's text, change
  with the menu (ADR 020 decision 1). Otherwise Level 2: `site/_quarto.yml`
  (sensitive, a shared input), page text, tests, docs. The full
  `./scripts/verify.sh` runs last; the approval request is
  `.agents/approvals/337.md`.

## Steps

1. `site/_quarto.yml`: the bar holds Home, Course Atlas, About on the left
   and the start link "Start learning" on the right (the search stays);
   Glossary, Evidence, Set up, Contribute, and Source leave the bar. The
   footer's right group: Run the code, Glossary, Scientific evidence, For
   educators, Contribute, Source. The licence group drops its About link,
   which the header carries, so that no link appears twice.
2. `site/reproduce.qmd`: the title "Run the code"; the address and the
   content unchanged (the reordering is F134).
3. `site/about.qmd`: restructured around who makes PBC, why it exists, who
   it is for, what makes it different (the two parts: eight courses and
   four method paths, generated from the curriculum, with a link to the
   atlas), and one short section on how the results are checked; contribute,
   citation, licences, and source at the end. Every existing anchor kept
   (`#creator-and-jidai`, `#why-open-source`, `#who-it-is-for`,
   `#what-this-site-is`, `#how-the-site-is-built`, and the unchanged
   headings); the F57 identity cell and the creator paragraph unchanged.
4. Tests: `tests/unit/test_site_chrome.py` replaces the eight-item assertion
   by exact assertions on the four items, the footer's six links, no link
   twice, and every linked page existing;
   `tests/e2e/test_built_site.py` checks the built header and footer on the
   home page, About, and the first lesson (items, links unique, every
   internal link resolves).
5. Docs: `docs/atelier.md` (header and footer components),
   `docs/authoring.md` (header, footer), `docs/development.md` (the page's
   name). `docs/architecture.md` keeps its dated gap list (protected, a
   record of the base commit).

The footer label "Scientific evidence" follows the roadmap block and
requirements decision 40; the Issue's "Evidence" names the same page.

## Visual deliverables and skills

Page and layout: the shared header and footer, and the About page's text.

Skills: frontend-design@dbd4588f

frontend-design applies to the shared interface elements (the header and
the footer). Artifact: the configured bar and footer, restyled by the
unchanged `site.css`; no new style, artwork, diagram, or figure. Scientific
validation: none needed (no scientific claim; About's course and path names
come from the curriculum file). Accessible fallback: the header and footer
are plain links without a script; the skip link and the keyboard pass are
unchanged.
