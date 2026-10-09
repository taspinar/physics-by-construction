# MVP release readiness (F10)

Record of the checks of the first release that CI cannot make, and of the
evidence behind each acceptance criterion of Issue #29. Items marked "human"
need a person; none is recorded as done until that person has done it.

**Status: release candidate.** The site is not declared released, and Issue
#29 stays open, until every human item below is recorded and the release tag
exists. The decisions this document asked for were taken on 2026-10-08 and
are recorded in their sections: the release includes the agent-based
modelling lesson (eleven lessons, four strands); no custom domain; the two
accessibility observations and the CI budget overrun are known limits with
one follow-up Issue each; the style differences get one Issue.

## Requirements coverage

Checked on 2026-10-08 against the published site at
<https://taspinar.github.io/physics-by-construction/>, which served the merge
commit `6b4a000` of pull request #28 (CI run 37770709319, deploy job
succeeded). That commit holds all ten lessons. The pages this branch adds
(Reproduce, Contribute) reach the published site only with its merge; the
last row covers them.

Since that check, `main` has moved, and this branch merged it on 2026-10-08
at `536d234`: pull request #32 (workflow scripts and docs, no site change);
pull request #33, which merged F11, the agent-based modelling lesson
`lessons/agents-abm/01-particles-in-a-box/`; pull request #36, which fixed
the unit test of that lesson that failed on the CI runner; and pull request
#35, which merged F12, the content proposal workflow (an Issue form, the
contributing guide, `docs/content-proposals.md`, and ADR 006; no site page).
The roadmap placed F11 and F12 after the MVP, but both are on `main` before
the tag. **Decision (2026-10-08): the release includes them.** The site has
eleven lessons in four strands; the reading pass and the audit below cover
the eleventh lesson, and the Contribute page describes the proposal workflow
as it exists. The CI run of `fa12c1b` (run 37857338092) passed and deployed
on 2026-10-08 at 23:20 UTC, and the run of `536d234` (run 37859587548)
passed and deployed at 23:43 UTC, so the published site serves `536d234`
with eleven lessons, and `main` is green at the commit this branch is based
on. The rows below record the check at `6b4a000`, with the rows that F11
changed re-checked against the published `fa12c1b`.

| MVP requirement | Evidence | Status |
|---|---|---|
| Mechanics course of 6 to 10 lessons | The published learning path lists eight mechanics lessons | met |
| At least one LLM agent lesson | `lessons/agents-llm/01-an-agent-runs-an-experiment/` is published (HTTP 200) | met |
| Agent-based modelling lesson or roadmap slot | `lessons/agents-abm/01-particles-in-a-box/` is published (HTTP 200 at `fa12c1b`) | met (lesson) |
| At least one Lean lesson, CI runs `lake build` | `lessons/lean/01-proving-what-the-simulation-showed/` is published; the `lean-build` check runs `./scripts/check-lean.sh` on every verification | met |
| Every lesson has the required parts | `lesson-checks` (`tests/lessons`) passes in CI run 37770709319 | met |
| Static site on GitHub Pages from `main` | Pages is configured to publish from the workflow; the deploy job publishes the artifact the `verify` job built for the `main` commit; HTTPS is enforced; the address answers HTTP 200 | met |
| CI executes all Python and proofs | `./scripts/verify.sh --all` on every pull request and push to `main`; run 37770709319 passed every check | met |
| Documented authoring workflow | `docs/authoring.md`, `docs/lesson-template.qmd` | met |
| Public repository, MIT and CC BY 4.0 | Repository visibility is public (`gh repo view`); `LICENSE`, `LICENSE-CONTENT`; the published About page names MIT and CC BY 4.0 | met |
| Visible learning path | The published `path/` page lists all lessons with difficulty and prerequisites, generated from the lesson front matter: ten at `6b4a000`, eleven at `fa12c1b` | met |
| WCAG 2.1 AA, responsive, no JavaScript needed | Automated checks and the scripted part of the audit below pass; the screen-reader rows need a person | human: complete the audit |
| Reproduce and Contribute pages published | Added by this branch; on the published site after the merge | human: confirm after the merge |

## Manual accessibility audit

Scope: site chrome (navbar, footer, home, path, about, reproduce, contribute)
and one lesson of each strand (mechanics 01, agents-llm 01, agents-abm 01,
lean 01).

What verification already checks on every page, on every run (`site-checks`,
`tests/e2e`): the axe-core rules tagged WCAG 2.0 and 2.1 A and AA, including
colour contrast, at 1280 and 320 CSS px; no two-way scrolling at 320, 768,
and 1280 CSS px (320 px is the reflow width of WCAG 1.4.10 and equals a
640 px window at 200 % zoom); every page readable without JavaScript; alt
text and dimensions on every image; the navigation entries fit a phone
screen.

Scripted pass on 2026-10-08 over the built site of this branch, in Chromium,
on the eight pages of the scope as it then was, and the same pass on the
published agent-based modelling lesson at `fa12c1b` after the decision
above. Keyboard: pressing Tab from the top of each
page visits every focusable control, each one rendered, scrolled into view,
and with a visible focus indicator (the browser ring on content links and
equations, the Bootstrap ring on the navigation), and the order returns to
the first control, so there is no trap; the navigation has no toggle button,
so every entry is reachable at phone width without JavaScript. Structure:
one `h1` per page, no skipped heading level, `main`, `nav`, `header`, and
`footer` landmarks, header cells in every table, every equation as MathML
with its TeX annotation, a caption on every figure, solutions as `details`
elements.

| Check | Chrome | Mechanics | LLM agents | Agent-based modelling | Lean |
|---|---|---|---|---|---|
| Keyboard only: every control reachable, visible focus, no trap | scripted pass | scripted pass | scripted pass | scripted pass | scripted pass |
| Screen reader: headings, landmarks, tables, equations, figure text | structure checked; human: read with a screen reader | same | same | same | same |
| Zoom to 200% and reflow at 320 CSS px without two-way scrolling | met by `site-checks` | met | met | met | met |
| Contrast: text 4.5:1, large text and controls 3:1 | met by the axe scan | met | met | met | met |

The agent-based modelling lesson, on the published page at `fa12c1b`:
pressing Tab at 1280 and at 320 CSS px visits 70 and 64 controls, each
rendered, in the viewport, and with an outline or box-shadow ring, and
returns to the first; one `h1`, no skipped heading level, `main`, `nav`,
`header`, and `footer` landmarks, both figures with a caption and both
images with alt text, all 38 equations as MathML with the TeX annotation,
both solutions as `details` elements, no table.

Observations for the human to accept or to file as Issues. Neither is a WCAG
2.1 A or AA failure:

1. There is no skip link; a keyboard user passes the seven navigation links
   before the content of every page. WCAG 2.4.1 is met by the landmarks.
2. The focus ring on the navigation links is a translucent blue halo on the
   dark bar: visible, but of low contrast. WCAG 2.2's focus appearance
   criterion is not an MVP requirement.

Open WCAG A or AA failures: none found. **Decision (2026-10-08): neither
observation blocks the release; both go to one follow-up Issue** (human:
file it and record its number here). The human records the screen-reader
rows before release.

## Reading pass over the lessons

Done on 2026-10-08 over all ten lessons then on `main`, and extended the
same day to the agent-based modelling lesson after the decision above,
against `docs/lesson-template.qmd`
and the difficulty definitions in `src/pbc/authoring/path.py`. Front matter
(id, strand, order, difficulty, prerequisites) is checked by `tests/lessons`
and the learning path is generated from it, so the structure, the strand
order, and the prerequisite graph cannot drift; the pass read the bodies.

Consistent: every lesson opens without a heading and has the template's
sections in the template's order; every Assumptions list is numbered with a
bold name per item; every listed lesson prerequisite is used by the body,
and every cross-lesson use is covered by a listed prerequisite or
transitively, with one exception, defect 4 below; "the previous lesson" and "the next
lesson" always point at the right lesson; the symbol $\Delta t$, "explicit
Euler", "per cent", "round-off", SI units, and British spelling are used
throughout; every number quoted across lessons agrees with the lesson that
derives it. Difficulty today: mechanics 1, 2, 2, 2, 2, 2, 2, 3; LLM agents
2; agent-based modelling 2; Lean 2; each matches its definition, with the
capstone (3) and the integrators lesson (2) borderline.

Defects found, and how each is fixed on this branch (criterion 5):

1. `mechanics/02-newtons-laws` said the harmonic oscillator lesson introduces
   the steppers that avoid energy growth; it now names the numerical
   integrators lesson.
2. The level 1 definition printed on the learning path said "A strand starts
   here", but the agents and Lean strands start at level 2 with lesson
   prerequisites; the sentence is removed from the definition in
   `src/pbc/authoring/path.py`.
3. `mechanics/07-momentum-and-collisions` referred twice to an agent-based
   modelling strand that, at the time, had no lesson; this branch first
   removed the strand's name from both places. With F11 merged and included
   in the release, the strand has a lesson whose prerequisite is this one,
   so both references are restored unchanged.
4. The Lean lesson named symplectic Euler, velocity Verlet, and Runge-Kutta 4
   without the numerical integrators lesson in its prerequisite chain; its
   "not covered" entry now attributes the three to that lesson as a forward
   reference, and the exercise that uses symplectic Euler already defines
   the rule in full, so the prerequisite chain is unchanged.
5. Outside prerequisites added to the front matter: the base-2 logarithm and
   log-log plots in `mechanics/01`; the dot product and the gradient in
   `mechanics/06`; Newton's root-finding method in `mechanics/08`.
6. The one "Runge--Kutta" in the Lean lesson, which rendered with an en dash,
   is now "Runge-Kutta".
7. The agent-based modelling lesson relies on the Gaussian distribution and
   on Student's t distribution without listing them; both are now outside
   prerequisites in its front matter.
8. The same lesson wrote "5 %" where every other lesson writes "per cent";
   it now reads "5 per cent".

Style differences, not blocking, for one follow-up Issue (human: file it and
record its number here): the code section's heading text ("The program",
"The proofs", "Code"); the agents lesson's exercises without bold titles and
its Assumptions without the shared opening sentence; "stepper",
"integrator", and "method", and "exact solution" and "exact motion", used
for the same things; short names for earlier lessons that vary ("the energy
lesson", "the pendulum lesson"); degrees as a symbol and as a word within
one lesson; one "timestep"; one American "visualization" in a heading;
uneven use of the `.not-verified` mark on quoted constants and hand-typed
approximate results; the agent-based modelling lesson alone divides its
Explanation into titled subsections.

## Cold-start reproduction

A reviewer who did not write the lessons follows only
`site/reproduce.qmd` (published as the Reproduce page) from a clean clone and
reproduces one lesson of each strand. The page sends the reader to
`./scripts/preflight.sh`, which checks only what the build needs;
`./scripts/doctor.sh` is for maintainers and reports their missing workflow
tools as failures.

Runs on 2026-10-08 by the round 9 agent, which wrote none of the lessons,
following the six commands of the Reproduce page in order on a clean clone
of `main` at `536d234` (eleven lessons). `./scripts/verify.sh` executes
every lesson and checks every built page, so a pass reproduces all eleven,
not one per strand. Whether an agent's run satisfies criterion 3, which
asks for a reviewer, is for the human to say (`.agents/manual-steps/29.md`).

| System | Reviewer | Lessons reproduced | Result |
|---|---|---|---|
| macOS 15.7 (Apple Silicon); Git, uv, elan, and jq already installed, the Lean toolchain already in `~/.elan` | agent, clean clone | all eleven | passed: `preflight.sh` found nothing missing; `verify.sh` passed every check in 20 min 22 s, including the Mathlib cache download |
| Ubuntu 24.04 (arm64) container from a bare image; Git, curl, jq, uv, and elan installed as the page links them | agent, clean clone | none yet | not completed: two attempts failed in `lean-build` before any lesson ran. First, GitHub refused the anonymous clone of Mathlib with a credential prompt while the macOS run was cloning it from the same address; second, the Lean release host `release.lean-lang.org` was unreachable, from the container and from the host alike, so the toolchain could not be fetched. Neither is a defect of the page; a retry is queued for when the host answers |

What the page did not say and a reader would meet: nothing on macOS. On
Linux the page's `--with-deps` note was needed and sufficient for the
browser build.

## Custom domain (human)

Unresolved question 3 of the requirements. **Decision (2026-10-08): no
custom domain for the MVP.** The site is served from `taspinar.github.io`
with HTTPS enforced, every internal link resolves there, and the site is not
being announced. GitHub Pages redirects the `github.io` address once a custom
domain is set, so the decision can be revisited without breaking links. If a
domain is chosen later: set `website.site-url` in
`site/_quarto.yml`, the Pages custom domain and DNS, enforce HTTPS, and run
`./scripts/verify.sh` so every internal link is checked under the new
address. Update the URLs in `README.md` and `docs/deployment.md`.

## CI time against the budget

Measured on 2026-10-08 from the Actions log of the `verify` job of CI run
37770709319, the push of `6b4a000` to `main` with all ten lessons and warm
caches. The budget is the one of ADR 003 and the architecture.

| Measure | Measured | Budget |
|---|---|---|
| `verify` job, wall clock | 16 min 28 s | 12 min |
| Runner setup and cache restore before `./scripts/verify.sh` | 2 min 13 s | |
| `./scripts/verify.sh --all` | 13 min 56 s | |
| `unit-tests` | 7 s | 2 min |
| `lean-build` (Mathlib cache in place) | 17 s | 3 min |
| `check-tests` (`tests/integration`) | 4 min 21 s | |
| `site-build` | 1 min 15 s | 3 min |
| `site-checks` (`tests/e2e`) | 5 min 18 s | |
| `determinism` (second site build) | 1 min 16 s | |
| Workflow self-tests and quick checks | 1 min 15 s | |

The pull request runs before that merge took 15 min 15 s (#28) and
12 min 11 s (#27). The typical run exceeds the 12 minute budget by about
four and a half minutes, while every per-check budget is met. The first
response of ADR 003 applies: reduce the cost of the offending checks, which
are `site-checks` and `check-tests`.

Two later pushes to `main`, measured the same way: the merge of pull
request #32 (run 37833854996, workflow scripts and docs only, ten lessons,
warm caches) took 12 min 11 s for the `verify` job, inside the budget. The
merge of pull request #33 (run 37845479383, F11, eleven lessons) took
13 min 20 s and failed: the unit test
`test_pressure_follows_the_gas_law_with_the_excluded_area` of
`tests/unit/test_gas.py` fails on the runner (`unit-tests`), and the
reproduction test of the new lesson repeats it (`site-checks`); `check-tests`
took 3 min 32 s, `site-checks` 4 min 10 s. The deploy job was skipped. That
failure was F11's and outside this Issue. Pull request #36 fixed it: the
test now allows a systematic model error of 0.01 in the pressure ratio
besides the statistical error (its first CI run, 37853606885, failed the
same test on the runner; its final run, 37855568647, passed). It merged on
2026-10-08 at 23:04 UTC as `fa12c1b`, and the CI run of that push to `main`
(run 37857338092, eleven lessons, warm caches, without the two changes of
this branch below) passed every check and deployed, so `main` is green
again. Measured from its Actions log the same way:

| Measure | Measured | Budget |
|---|---|---|
| `verify` job, wall clock | 15 min 36 s | 12 min |
| Runner setup and cache restore before `./scripts/verify.sh` | 1 min 59 s | |
| `./scripts/verify.sh --all` | 13 min 30 s | |
| `unit-tests` | 11 s | 2 min |
| `lean-build` (Mathlib cache in place) | 10 s | 3 min |
| `check-tests` (`tests/integration`) | 3 min 58 s | |
| `site-build` | 1 min 19 s | 3 min |
| `site-checks` (`tests/e2e`) | 4 min 57 s | |
| `determinism` (second site build) | 1 min 15 s | |
| Workflow self-tests and quick checks | 1 min 35 s | |

With eleven lessons the run is 3 min 36 s over the budget. The next push,
the merge of pull request #35 (F12, run 37859587548, workflow and docs
files, no site change), took 15 min 02 s for the `verify` job, of which
`./scripts/verify.sh --all` took 12 min 54 s, and passed. The conclusion
above stands: the first response saves about a minute and a half, and the
second response is due.

Where their time goes, measured on 2026-10-08 on a development machine with
`pytest --durations` over the tree of this branch (slower than the CI runner
in absolute terms; the shares are what matter):

- `site-checks`, 4 min 40 s: the ten reproduction tests, one per lesson,
  2 min in all, each a copy of the tree and a re-render of one page, which is
  the check of the 30 s per-page budget; the readable-without-JavaScript
  check over every page at two widths, 25 s, which a widget test ran a
  second time, another 25 s; the axe scan, 19 s; the width and request
  checks, 21 s; the rest spread over 130 short tests.
- `check-tests`, 5 min 26 s: the template lesson test, which copies the site
  and builds it with all ten lessons plus the one made from the template,
  78 s; the five tests of `check-lean.sh`, each a `lake build` of a small
  project against the shared Mathlib, 2 min in all; the rest spread over
  200 short tests.

Applied on this branch, the first response of ADR 003 in full:

- `site-checks`: the widget test no longer runs the
  readable-without-JavaScript check over the whole site a second time; it
  checks that its page is among the pages the one run in `test_built_site`
  visits. About 25 s per run; it drops no check.
- `check-tests`: the template lesson test builds the template lesson against
  copies of the other lessons reduced to their front matter. The learning
  path, the lesson header, and the path page are generated from front
  matter, so every assertion of the test is unchanged, and `site-build`
  already executes every lesson in full. Measured on the development
  machine on 2026-10-08: the build test took 85 s before the change and 18 s
  after it, and `check-tests` as a whole went from 5 min 26 s to 4 min 26 s,
  with every one of its 223 tests passing.
- The Lean check tests run one `lake build` per case and have no reduction
  that keeps every case; the ten reproduction tests are the check of the 30 s
  per-page budget and each needs its own clean copy.

The first response saves about a minute and a half of a run and leaves a
typical run near 15 min, still over the budget, so the second response of
ADR 003 is due:
split the `verify` job into parallel jobs that each run a named subset of
the same `verify.conf` checks behind one aggregate required check. That
changes `scripts/verify.sh`, the workflow, the required status check of the
`main` ruleset, and the architecture document, and amends decision 2 of
ADR 003; it is outside Issue #29, whose scope is the release checks, so it
goes to its own Issue (human: file it, and record its number here).
**Decision (2026-10-08): the release goes out with the overrun as a known
limit**, named in the release note with that Issue; the first response is
applied on this branch and the second is the Issue's. The merge of this
branch adds two pages, shortens two tests, and adds no check; the human
re-measures the `verify` job after it.

## Release (human)

After the items above: tag the merge commit (`git tag -a mvp-v1.0.0`) and
publish a GitHub release whose note lists the eleven lessons, the four
strands, the content proposal workflow, and the known limits, using the open
Issues from the audit, the reading pass, and the CI budget. Link the tag and
the release note from Issue #29, then close it.
