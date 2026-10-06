# Plan: Issue #3, F01 — Published site skeleton with the full verification pipeline

- Issue: #3 (source: `docs/roadmap.md`, F01)
- Branch: `feature/3-site-skeleton`
- Base commit: `72a6795`
- Risk: High (CI permissions, deployment, repository settings)
- Governing documents: `docs/architecture.md`, ADR 001, ADR 002, ADR 003

## Goal

A real, nearly empty site on GitHub Pages, and one verification command that
already exercises Python, Lean with Mathlib, and the site build and gates
every pull request. Later features only add content and checks.

## Current state at the base commit

Only the agentic workflow template: `verify.sh` with template checks, a CI
workflow that calls it with an action pinned by tag and no `permissions`,
template text in README, CONTRIBUTING, CODEOWNERS, `.env.example`,
`docs/deployment.md`, and `docs/operations.md`, and no licence files. No
Python, Lean, or site code.

## Design

### Pinned versions (newest stable, mutually compatible, 2026-10-06)

| Toolchain | Version | Pinned in |
|---|---|---|
| Python | 3.14 | `.python-version`, `pyproject.toml` |
| NumPy, SciPy, Matplotlib | 2.5.3, 1.18.1, 3.11.2 | `uv.lock` |
| pytest, Ruff | 9.1.1, 0.16.10 | `uv.lock` |
| Quarto (`quarto-cli`) | 1.10.19 | `uv.lock` |
| Playwright, axe binding (axe-core 4.12.1) | 1.63.0, 0.1.8 | `uv.lock` |
| Chromium headless shell | 153.0 (Playwright build 1243) | Playwright version |
| Lean 4, Mathlib | v4.34.1, tag v4.34.1 | `lean/lean-toolchain`, `lean/lakefile.toml`, `lean/lake-manifest.json` |
| Build backend (hatchling) | 1.32.4, exact | `pyproject.toml`, because `uv.lock` does not cover build requirements |
| elan in CI | v4.2.4 with SHA-256 | `.github/workflows/ci.yml` |
| GitHub Actions | commit SHA each | `.github/workflows/ci.yml` |
| STIX Two Math font | 2.13 b171 with SHA-256 | `site/assets/fonts/README.md` |

### Checks in `scripts/verify.conf`, in order

| Check | Command | Fails on |
|---|---|---|
| `preflight` | `scripts/preflight.sh` | A missing prerequisite of the supported-machine contract; a browser build that is absent or cannot start |
| `lint`, `format` | `uv run --locked ruff …` | Lint findings, unformatted code |
| `unit-tests` | `uv run --locked pytest tests/unit` | A failing unit test |
| `lean-build` | `scripts/check-lean.sh` | Mathlib not complete from its cache; a module that does not compile; `sorry`; a project axiom |
| `check-tests` | `uv run --locked pytest tests/integration` | A check that no longer fails on its violating input; a loosened CI boundary |
| `site-build` | `scripts/build-site.sh` | A failing cell; an equation that is not MathML |
| `site-checks` | `uv run --locked pytest tests/e2e` | Any built-site rule, see below |
| `determinism` | `scripts/check-determinism.sh` | Two builds that differ in any byte |
| existing | workflow self-tests, plus `preflight-test` | — |

Decisions inside the checks:

- **Lean audit.** `lake build` only warns about `sorry`. After the build,
  `check-lean.sh` elaborates `lean/AxiomAudit.lean` with one import per
  project module. It fails when a project declaration is an `axiom` or
  depends on any axiom besides `propext`, `Classical.choice`, and
  `Quot.sound`. That covers `sorry` and `admit` (`sorryAx`) and is slightly
  stricter than I12: `native_decide` is rejected as well.
- **Mathlib is never compiled.** `lake build --no-build Mathlib` must report
  it up to date, before or after `lake exe cache get`; otherwise the check
  fails.
- **All modules build without an import list.** The library uses the glob
  `PhysicsByConstruction.+`, and the audit takes its module list from the
  directory, so a new file cannot be forgotten.
- **Built-site checks** live in `tests/support/site_checks.py` and run on the
  site served under the path of `website.site-url`
  (`/physics-by-construction/`), so they also prove the sub-path. Browser
  checks abort and report any request that leaves the local server.
  Rules: image alt text and dimensions; no resource on another origin, in
  the files and at load time; no cookie; internal links and anchors resolve
  and stay inside the sub-path; all text rendered with JavaScript disabled,
  and no text, image, equation, or drawing that only a script adds (outside
  an element declared with `data-enhancement` that has an `id` and static
  content), at desktop and phone width (320 px); no horizontal page scroll
  and no image past the screen edge at phone width; axe-core scan with the WCAG 2.0 and 2.1 A and AA tags at both
  widths.
- **Determinism.** The second build runs from a fresh copy of `site/` in
  another directory without `.quarto/`, so build time, checkout path, file
  timestamps, and caches all count.

### Site

- Quarto website in `site/`, output `site/_site/` (ignored by Git).
- Pages: home, about and licences, and a rendering-check page with sample
  equations, executed code that imports `pbc`, and a Matplotlib figure. The
  rendering-check page is the pipeline sample for criterion 12, not a lesson.
- `html-math-method: mathml`, `highlight-style: a11y`, default theme (system
  fonts, no web font), self-hosted STIX Two Math for equations.
- Search and the collapsing menu are off: both need JavaScript.
- Base URL is one value: `website.site-url` in `site/_quarto.yml`. Pages link
  relatively.

### CI

One workflow. `verify` job: checkout, uv, caches (`~/.elan`, `lean/.lake`,
browser), elan, `uv sync --locked`, browser with system libraries,
`./scripts/verify.sh`, upload of `site/_site` as the Pages artifact on every
run that built a site, also after a failed check. `deploy` job: only on push to `main`, needs `verify`, one step
(`actions/deploy-pages`), `pages: write` and `id-token: write` only.
`tests/integration/test_ci_workflow.py` holds these boundaries.

## Discoveries during implementation

| Finding | Resolution |
|---|---|
| Quarto stamps every sitemap entry with the build time | `build-site.sh` drops `<lastmod>` |
| An executed cell without a label gets a random `id` on every build | `site/_filters/cell-ids.lua` removes that identifier |
| Wide equations and code blocks scroll sideways at 320 px; axe requires a scrollable region to be keyboard-reachable | `site/_filters/scroll-regions.lua` wraps display equations in a focusable box and makes code blocks focusable |
| A figure wider than a phone screen was clipped by its container, without making the page scroll, so the scroll rule did not see it | `site/assets/site.css` scales images to the screen; new rule `image-overflow` with its own violating test |
| Quarto hides the table of contents at phone width | The no-JavaScript rule exempts `nav[role="doc-toc"]`, which only repeats the headings |
| Pandoc only warns about an equation it cannot convert | `build-site.sh` fails on that warning |
| A font URL in a theme SCSS file is resolved against the project root and breaks the build | The `@font-face` rule is in plain `site/assets/site.css`; the font is a project resource |
| `quarto-cli` requires the full `jupyter` metapackage | Accepted: 119 locked packages |
| Ruff also lints the Python scripts inside fetched Lean packages | `extend-exclude = ["lean/.lake"]` |
| uv 0.9.4 wrote the lock; uv 0.12.23 accepts it unchanged (`uv lock --check`) | No uv pin needed |

## Deliberately not done

- Linting of Python cells inside `.qmd` pages (architecture, verification
  step 1). The only executed page is the rendering sample; the lesson format
  and its checks are F02.
- `scripts/verify.sh` is unchanged, so it does not print the duration of each
  check. Per-check times come from the CI log timestamps or from timing the
  commands of `verify.conf`.
- No planning document (`docs/architecture.md`, `docs/roadmap.md`, ADRs) is
  changed: a change would invalidate `docs/PLANNING_APPROVAL.md`.

## Steps

1. Python project: `pyproject.toml`, `uv.lock`, `.python-version`,
   `src/pbc`, unit tests. Done.
2. Lean project with Mathlib, one theorem, `check-lean.sh`, axiom audit.
   Done.
3. Quarto site, font, filters, `build-site.sh`, `check-determinism.sh`. Done.
4. Built-site checks and their tests on violating sites. Done.
5. Supported-machine contract: `prerequisites.sh`, `check_browser.py`,
   `preflight.sh`, `doctor.sh`, shell tests. Done.
6. CI workflow, Dependabot, workflow boundary tests. Done.
7. Licences and repository hygiene; `docs/development.md`,
   `docs/deployment.md`, `docs/operations.md`, `docs/project-map.md`. Done.
8. Human-only steps, each with explicit approval. Open, see below.

## Human-only steps

State read from GitHub on 2026-10-06, read-only: Pages is not enabled; `main`
has no ruleset; default workflow permissions are read; secret scanning and
push protection are enabled; Dependabot alerts and security updates are
disabled.

In this order:

1. Push the branch and open the pull request. The `verify` job runs for the
   first time.
2. Enable Pages with GitHub Actions as the source:
   `gh api -X POST repos/taspinar/physics-by-construction/pages -f build_type=workflow`
3. Create the ruleset for `main` (restrict deletions, block force pushes,
   require a pull request) with `verify` as a required status check, after
   step 1 has produced that check.
4. Enable Dependabot alerts and security updates:
   `gh api -X PUT repos/taspinar/physics-by-construction/vulnerability-alerts`
   and
   `gh api -X PUT repos/taspinar/physics-by-construction/automated-security-fixes`
5. Confirm that secret scanning and push protection are still enabled.
6. Merge. The deploy job publishes the artifact of the `main` run.

## Acceptance criteria that need the pull request or the human

| Criterion | What is still needed |
|---|---|
| 1, clean Linux machine | The first CI run is the clean Linux machine. Local evidence is macOS only. |
| 3 | A push to `main` with Pages enabled; then open the Pages URL. |
| 5 | The ruleset of step 3; then confirm a pull request with a failing check cannot be merged. |
| 10 | Times of a warm-cache pull request run, per check, recorded in the pull request. Also the size of the `lean/.lake` cache against the 10 GB quota. If the cache is too large or slow, cache `~/.cache/mathlib` instead and let `lake exe cache get` unpack it. |
| 12 | Copy the cross-engine result below into the pull request. |

## Verification evidence

2026-10-06, macOS 15.7 on Apple M1 Max, working tree on base `72a6795`
(uncommitted; `finish-feature.sh` creates the commit). This section was
written after the run; no other file changed after it.

`./scripts/verify.sh`: **Verification passed**, 27 of 27 checks `PASS`.

| Check | Wall time, warm caches |
|---|---|
| `preflight`, `lint`, `format`, `unit-tests` (6 tests) | 1 s together |
| `lean-build` (Mathlib up to date, 942 jobs, audit of 1 declaration) | 20 s |
| `check-tests` (39 tests) | 49 s |
| `site-build` (3 pages, 2 executed cells) | 5 s |
| `site-checks` (12 tests) | 6 s |
| `determinism` (24 files byte-identical) | 5 s |
| All new checks together | 86 s |
| Workflow self-tests of the template | about 20 min on this machine, 64 s in CI on `main` (run 37463841854) |

The self-tests are slow only locally: the shell here runs under Rosetta and
another session was running the same tests. The first run of the one-time
setup took about 10 minutes for the Mathlib cache and 3 minutes for
`uv sync`.

Per criterion:

| # | Evidence | State |
|---|---|---|
| 1 | elan and the browser build were installed on this machine with the documented commands; verification then passed without administrator rights and left the site in `site/_site/`. Missing jq and missing browser build: `tests/preflight-test.sh` (preflight and `verify.sh`), `tests/doctor-test.sh`, `tests/integration/test_browser_check.py` (real launch with an empty browser directory) | macOS met; Linux is the first CI run |
| 2 | `test_ci_workflow.py::test_verify_job_runs_checks_only_through_verify_sh`. Violating inputs: failing Python test, lint, format (`test_python_checks.py`); Lean file that does not compile, `sorry`, project axiom (`test_lean_check.py`); other-origin resource in five forms, request at load time, cookie, image without alt text, image without dimensions, broken link, anchor, host-root link, content that needs JavaScript (revealed by a script, and created by one), wide page, clipped image, WCAG violation (`test_site_checks.py`); unconvertible equation, failing cell, non-deterministic page (`test_site_build.py`) | met |
| 3 | Deploy job has one step and `needs: verify` (`test_ci_workflow.py`) | structure met; publication needs the merge |
| 4 | `test_ci_workflow.py`: triggers, default permissions, deploy-only write scopes, SHA pins, no `secrets.` | met |
| 5 | — | needs the ruleset |
| 6 | `tests/e2e`: no other-origin reference in files, none requested at load, no cookie | met |
| 7 | `tests/e2e`: readable with JavaScript disabled at 1280 and 320 px, MathML display equation in the self-hosted font, no sideways scroll at 320 px, zero axe violations at both widths | met |
| 8 | `determinism` check | met on macOS |
| 9 | All built-site checks run on the site served under `/physics-by-construction/`, taken from `website.site-url` | met |
| 10 | Local warm run of the new checks: 86 s | CI measurement needed |
| 11 | `LICENSE`, `LICENSE-CONTENT`; README; footer test in `tests/e2e`; no match for template placeholders in README, CONTRIBUTING, CODEOWNERS, `.env.example` | met |
| 12 | `pytest tests/e2e --engine <engine>`: 12 passed in Chromium 153.0, Firefox 155.0, and WebKit 26.6 (Playwright 1.63 builds). Screenshots of the rendering-check page at 1280 and 360 px in all three engines were inspected: equations, highlighted code, cell output, and the figure render correctly. Differences are cosmetic: spacing inside fractions and the delimiter shapes of the matrix | met; copy into the pull request |

## Review round 1: approved fixes

Review `.agents/reviews/feature-3-site-skeleton-review-01.json`, triage
`.agents/triage/feature-3-site-skeleton-review-01-triage.json`.

| Finding | Fix | Evidence |
|---|---|---|
| M1 | `check_readable_without_javascript` also loads each page with scripts and reports text, images, equations, and drawings (`svg`, `canvas`) that a reader sees only then. Allowance: content inside an element with `data-enhancement` that is in the page without scripts, has an `id`, and holds static content there. | `test_site_checks.py::test_content_created_by_a_script_is_reported` (seven violating pages: text, image, equation, drawing, text written after a request, enhancement without static content, enhancement declared by a script) and `test_script_may_add_to_a_declared_enhancement_of_static_content`. The real site has no such content at either width. |
| MIN1 | The upload step runs with `!cancelled() && hashFiles('site/_site/index.html') != ''`. The job still fails on a failed check, and the deploy job still needs it. | `test_ci_workflow.py::test_built_site_is_uploaded_when_a_check_failed`. The behaviour on GitHub is seen on the first failing run. |

2026-10-06, after these fixes: `ruff check`, `ruff format --check`,
`pytest tests/unit`, `pytest tests/integration`, and `pytest tests/e2e` pass.
The full `./scripts/verify.sh` is run by `apply-triage.sh`.
