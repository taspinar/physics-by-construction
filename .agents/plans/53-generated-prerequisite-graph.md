# Plan: Issue #53, F26 — Generated prerequisite graph

- Issue: #53 (source: `docs/roadmap.md`, F26)
- Branch: `feature/53-generated-prerequisite-graph`
- Risk: Medium (layout quality for a growing graph)
- Governing documents: `docs/architecture.md` ("Lesson model"), ADR 001
  (no script needed), ADR 002, ADR 008 (courses), the F03 plan
  (`12-learning-path.md`)

## Design

| Decision | Reason |
|---|---|
| `pbc.authoring.graph.PrerequisiteGraph.layout(lessons, courses)` computes columns (longest prerequisite chain), rows (course bands, then barycentre sweeps, ties by path order), and renders the SVG | Build-time and deterministic: same lessons, same bytes. No browser library (out of scope) |
| `graph.py` does not import `path.py` at run time | `PathOverview` embeds the graph; the types are only for annotations |
| Edges: `requires` from prerequisite to dependant; `related` from the lesson that lists it to the related lesson | The direction of "links are written from the prerequisite side" |
| A required and a related edge between the same two lessons are drawn 14 units apart | They would coincide; the test compares edges from `data-*` attributes |
| Required: solid line, filled arrowhead. Related: dashed line, open arrowhead | Colour is not the only distinction |
| SVG with `aria-labelledby` naming `<title>` and `<desc>`, no `role="img"`; `role="group"` only on the course bands; node = `<a href>` | Keeps the node links in the accessibility tree |
| The edges as a `visually-hidden` `<ol>` of sentences after the drawing; legend before it | Accessible and no-JavaScript alternative |
| A section at the end of the path page, after the lists | On a phone the linear lists are read first; the box scrolls (`.prerequisite-graph`, focusable) |
| Raw HTML in a ```` ```{=html} ```` block of the `asis` output | Pandoc would parse the inside of a `<div>` as Markdown |

## Known limits

- An edge spanning several columns passes behind the nodes between; there
  are no routing waypoints. Nodes are opaque and edges drawn first, so the
  drawing stays readable, but a very dense path may want waypoints.
- Layout is tested for 30 synthetic lessons for overlap and determinism,
  not for edge crossings.

## Tests

- `tests/unit/test_prerequisite_graph.py`: edges equal the relations of the
  site's front matter and of a synthetic 30-lesson path; the SVG and the
  text list agree; labelling; columns; no overlap; byte stability.
- `tests/e2e/test_learning_path.py`: graph and text list without
  JavaScript, keyboard order and visible focus, scrolling inside the box at
  320 px. The accessibility and width checks run on every page already.

## Steps

1. `graph.py`, `PathOverview` section, styles. Done.
2. Tests. Done.
3. Docs. Done.
4. `./scripts/verify.sh`.
