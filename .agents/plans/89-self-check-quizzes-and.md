# Plan: F13 — self-check quizzes and browser-local progress (Issue #89)

## Design

- **Authoring.** A self-check stays the one `.exercise.self-check` div with a
  `.solution`. It may add a `.choices` div of two or more `.choice` divs, each
  with a `.feedback` div; exactly one choice has `correct="true"`. The Lua
  filter renders `.choices` as `ol.choices > li.choice[data-correct]` with the
  feedback visible inside each item. Without a script the reader sees the
  question, the options with their explanations, and the closed solution that
  opens without script: the existing exercise pattern.
- **Script.** `site/learner/progress.js`, a self-hosted ES module that makes no
  request and loads nothing. Not in `widgets/` because the widget checks forbid
  storage there. It is the only script that uses browser storage; a static
  check names it as such.
  - Self-check: choices become radios, a "Check answer" button and a live
    region with the feedback of the chosen option. A self-check without
    choices gets a "Mark self-check as done" button.
  - Lesson page: a status line and a toggle after the header: "Mark lesson as
    completed". A correct answer or a marked open self-check completes it.
  - Path page: cards show "Completed" (text, not colour only); a summary
    "N of M lessons completed"; the explanation of what is stored; the
    clear-data button (hidden without a script).
- **Storage.** Key `physics-by-construction:learner-state`, value
  `{"version":1,"lessons":{"<id>":{"completed":bool,"selfCheck":{"done":bool,
  "attempts":n}}}}`. Written only when the reader acts, never on load, except
  that unreadable or other-version data is removed. Migration table keyed by
  version; no earlier format exists, so older, newer, malformed data is
  discarded. Storage that throws leaves progress in memory with a notice.
- **Export.** `site/learning-path-export.py` (post-render) writes
  `_site/path.json`: lesson ids, titles, pages relative to the site root, order,
  course, methods, difficulty, prerequisites, related. Deterministic. The
  script does not fetch it; F14 will.
- **Wiring.** `lesson_header()` and `learning_path()` append the JSON data
  element (lesson id, link to the explanation) and the module tag, so every
  lesson and the path page load it. Cards get `data-lesson-id`.

## Tests

- Unit: export content; markup helpers.
- Lesson checks: choices rules (inside a self-check, at least two, exactly one
  correct, each with feedback).
- Built site (e2e): progress persists across reload and is removed by clear;
  no request carries state (all GET, no body, no state in URL or headers) and no
  cookie; scripts disabled shows question, options, solution; old/newer/
  corrupt stored data is discarded; keyboard operation; axe scan with the
  controls in several states; script source has no request API or other origin.
- Existing checks adjusted: the widget-source scan does not cover `learner/`;
  a separate source check does.

## Docs

`docs/authoring.md` (format), `docs/architecture.md` (learner state section,
I16 enforcement), `docs/project-map.md` if it lists site files.

## Discoveries while implementing

- The no-script check requires what a script adds to sit in a `data-enhancement`
  element with an id and static content. The self-check controls
  (`#self-check-controls`, added by the Lua filter), the lesson status
  (`#learner-panel`), and the path-page controls (`#progress-controls`) are
  such elements; completed cards are marked by `data-completed` and a CSS
  mark, plus a list of completed lessons in `#progress-controls`.
- The self-check sentence must not contain the text "Self-check." (an existing
  test counts it).
