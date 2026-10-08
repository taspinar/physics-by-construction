# Plan: Issue #23, F07 — Interactive visualizations

- Issue: #23 (source: `docs/roadmap.md`, F07)
- Branch: `feature/23-interactive-visualizations`
- Base commit: `a1690fb`
- Risk: Medium (physics shown by a widget must not drift from the tested Python)
- Governing documents: `docs/architecture.md` (Widgets, invariant I4, verified
  display forms), ADR 002, `docs/authoring.md`, the existing enhancement
  convention of `tests/support/site_checks.py` (`[data-enhancement]`)
- Written by the implementer: no plan existed when the feature started.

## Goal

Establish how optional JavaScript widgets are built, tested, and degraded, and
ship one: the integrator explorer in M5, where the learner changes the time
step and the integrator and sees position and energy respond.

## Decisions

| Decision | Reason |
|---|---|
| The widget **does not compute physics**. Python cells compute every trajectory for four integrators at nine step counts at build time and embed them as JSON in the page | Criterion 4 cannot drift: the displayed numbers are `pbc` results. A test still recomputes them with `pbc` and compares them with what the widget displays, within a stated tolerance |
| The widget shows all four methods at the chosen step; the chosen integrator is emphasised and its numbers are read out | The static figure then shows the same view at the default step, so the fallback is the widget's initial state |
| The static fallback is the figure of the default state plus a table of the same quantities for every integrator and step count (outside the enhancement, so it stays with scripts) | No content is lost without JavaScript; the table carries everything the widget can show as numbers |
| The widget replaces only the `<img>` of the figure and fills a reserved controls slot; both have reserved dimensions in CSS | No layout shift (criterion 5), shown by a layout-shift measurement at desktop and phone width |
| Controls are native: radio group and range input | Keyboard operation and focus come from the platform |
| No animation | Nothing to disable for `prefers-reduced-motion`; a test shows no animation or transition runs with the preference set |
| Widget data goes through `pbc.authoring.widgets` (`widget_data`, `widget_module`) | One tested way to embed data and script with correct relative URLs and escaping |

## Steps

1. `pbc.mechanics.explorer`: build-time data (unit-tested against `harmonic_motion`, `energy`).
2. `pbc.authoring.widgets` (unit-tested).
3. `site/widgets/integrator-explorer.js`, styles in `site/assets/site.css`, `resources` in `site/_quarto.yml`.
4. Lesson M5: section "Interactive visualization" with the static figure, table, data, module.
5. Built-site checks: widget sources (no other origin, no storage API), browser storage writes after driving the controls; tests/e2e/test_widgets.py (fallback, keyboard, accessibility, reference values, layout shift, reduced motion).
6. `docs/authoring.md` section on widgets; architecture and roadmap notes if they change.

## Verification evidence

`./scripts/verify.sh` passed on the working tree (all project checks; workflow
self-tests skipped, no workflow file changed). Determinism: two builds
byte-identical. Criteria: 1 `test_without_javascript_...`; 2 widget
responds/keyboard/axe tests; 3 `check_widget_sources`,
`check_widgets_store_nothing`; 4 `test_displayed_values_agree_with_a_fresh_run_of_pbc`
(36 settings; energy rel 1e-3, error rel 1e-2, calls exact); 5 layout-shift
test and reserved `.widget-controls` height; 6 determinism check.

Review round 1, M1 (2026-10-08): the drawing now takes the image's width,
height, class and aspect ratio, so the figure keeps its geometry (606 x 489
at desktop; measured identical boxes for figure, caption, controls, following
content and page height at desktop, tablet, and phone). The stylesheet
reserves 29rem for the controls below 576px, where they stack to 479px at
320px wide (357px was reserved). The layout test now serves a stub module,
lets the page load and settle, scrolls the widget into view, starts the real
module, and asserts identical boxes and a zero shift score; the reserved-space
test runs at all three widths. Both tests fail on the previous behaviour
(checked by mutating the built copies). `tests/e2e` and `tests/integration`: 336
passed, `tests/unit`: 248 passed; ruff check and format clean.

Discovery: Quarto's own page script writes `quarto-persistent-tabsets-data` to
localStorage on every page, so the storage check compares against the same page
with `widgets/*.js` blocked and blames only what the widget adds.
