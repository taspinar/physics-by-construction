# Plan: F28 lesson format 2, reference register, M1 pilot (Issue #52)

Source: Issue #52, ADR 009, docs/architecture.md "Lesson model" (format 2).

## Markup (decided)
- Front matter `lesson.format: 1|2` (optional; absent = 1).
- Claim: `[text]{.claim type="numerically-verified" scope="..." evidence="..."}`
  or a `::: {.claim type=...}` div. Lua adds a plain-text label.
- Figure status: cell option `#| fig-status: simulated` (vocabulary
  measured, calibrated, processed, simulated, conceptual); Lua prepends the
  F44 `span.figure-status[data-status]` to the figure caption.
- Claim: Lua renders the F44 label `span.claim[data-type]` with the type
  name (and scope), followed by the statement; F44 CSS styles all of it.
- Self-check: `::: {.exercise .self-check}` with a `.solution`; titled
  "Self-check." and not numbered, so the numbered exercises stay 1..n.
- Limits: `## Limits {#limits}` level-2 section.
- Go deeper: `::: {.go-deeper ref="key"}` reason to visit `:::`; Lua reads
  `site/references.yaml` (via pandoc.read of the YAML as metadata) and renders
  title, author/publisher, section, link, then the reason.
- Given values in prose: `[0.1 s]{.given}`.

## Checks (tests/support/lesson_checks.py; each with a violating test in
tests/integration/test_lesson_checks.py)
limits, one self-check (with solution), claim type, figure status, register
key exists, raw URL, hand-typed numbers (prose and fig-alt), register schema
and usage; console block is a built-site check (site_checks) because it
needs cell output; enabled for format-2 pages only.

## Docs
authoring.md (format 2, claim types, selection protocol, migration rule),
lesson-template.qmd in format 2, architecture note on self-check numbering.

## M1 pilot
Audit recorded in the PR (see handoff for text); rewrite; limits; self-check;
claims; fig status; <=2 Go deeper chosen by protocol; numbers unchanged
(compare built tables with the pre-change build).
