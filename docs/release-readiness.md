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

**How these measurements are used** (ADR 020 decision 6, from F130). An
exceeded wall-clock budget recorded here, the 20 minutes of a pull request
(ADR 015), the planning budget of a full run, or a complete run on `main`
above 45 minutes, is a measurement for the owner's decision, not a failed
gate and not a mandate to optimise. The owner decides at the re-assessment
points of the decision of 2026-10-24 (ADR 014 status, Issue #278), which
raises the interim full-run gate to 110 lessons, the whole reference
curriculum, with the `build` job's timeout raised from 60 to 90 minutes:
re-measure at 75 and at 95 lessons, and decide earlier when a complete run
on `main` approaches 80 minutes, repeated runs show too little margin, or
verification failures point to a capacity problem, with the `build` job's
duration and the run's total duration reported separately (the former
points, 42 and 44 lessons or a complete run on `main` above 45 minutes, and
55 and 60 lessons or a `build` job approaching 55 minutes under the
decision of 2026-10-21, are superseded history), choosing from the responses of ADR 003 decision 6. A budget is never met by
changing scientific content, and the hard 30-second budget of a lesson page
keeps failing, with its exception table `scripts/lesson-budgets.conf`. Local
runs leave their durations in the time log of `./scripts/verify.sh`
(`docs/development.md`, "Verification"), which the evaluation of ADR 020
decision 10 reads.

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

### Parallel jobs (F58), measured 2026-10-12

F58 applied the second response: the checks run in parallel jobs behind the
one required check `verify` (ADR 012). Measured from the Actions runs of
2026-10-12, with twenty-two lessons. Wall clock is from the start of the run
to the end of its last job; runner time is the sum of the jobs.

| Run | Caches | Wall clock | Runner time | `build` | `integration` | slowest `e2e` |
|---|---|---|---|---|---|---|
| Single job before F58, seven runs of that day | warm | 30 min 34 s to 43 min 19 s | the same | | | |
| Pull request #141, run 38281376211 | warm, except the uv cache of the jobs that started first | 25 min 00 s | 47 min 13 s | 18 min 56 s | 9 min 46 s | 5 min 46 s |
| Pull request #142 (measurement only), run 38284365563 | warm | 22 min 56 s | 44 min 36 s | 16 min 55 s | 9 min 25 s | 5 min 47 s |
| Push of `aeeaa0e` to `main`, run 38284263388, with `deploy` | warm | 17 min 52 s | 38 min 55 s | 12 min 33 s | 9 min 00 s | 4 min 50 s |
| Pull request #143 (measurement only), run 38284385577 | cold: every cache key changed | 25 min 17 s | 45 min 12 s | 20 min 27 s | 9 min 00 s | 4 min 32 s |

Budgets of ADR 003: 12 minutes with warm caches, 25 minutes with cold caches.

- **A run takes 18 to 25 minutes, against 31 to 43 before.** It is still
  over the budget of 12 minutes, by 6 to 13 minutes. The cold run is 17
  seconds over its budget of 25 minutes.
- **The longest path is the `build` job and then the slowest `e2e` job.**
  `build` holds the Lean build, the site build, the second build for
  determinism, and the reproduction of every lesson; the last two compare
  bytes with the first build and have to run on its machine (ADR 012,
  decision 4). The same job took 12 min 33 s to 20 min 27 s on the same
  content: the runners differ.
- **Warm and cold differ little**, because the caches are a small part of a
  run: the time is in executing the lessons, three times each.
- **A run uses 39 to 47 runner minutes**, more than the single job in a
  good run and about as much as in a slow one: every job prepares its own
  runner.
- Two warm pull request runs were measured, not the three of the first
  acceptance criterion of Issue #130; the project owner chose that on
  2026-10-12 to close the feature. The run on `main` is a third warm run,
  but a push and with the deploy.

**Decision of the project owner (2026-10-12).** F58 is closed with this
measured state. The 12 minutes are an acceptance criterion of the feature
that makes verification proportional to what a pull request changes, which
the planning change `final-curriculum` adds; until that feature is delivered
the budget is exceeded, every new lesson adds to the `build` job, and the
response of ADR 003, decision 6, stays due.

### Selection against a base (F61), measured 2026-10-14

F61 makes a pull request verify what it changed against the verified base of
`main` (ADR 014). Measured from the Actions runs of 2026-10-14, with
twenty-two lessons, on three pull requests that each change one lesson
(measurement only, closed after the measurement), beside the runs on `main`.
Wall clock is from the creation of the run to its end; runner time is the sum
of the jobs. In every pull request run the log of the job `build` says
"selective run against base 2e0bd620566f: 1 of 22 lessons executed, 21
restored", and the `e2e` jobs select against the same base.

| Run | Base | Wall clock | Runner time | `build` | `integration` | `workflow` | slowest `e2e` |
|---|---|---|---|---|---|---|---|
| Pull request #161, run 38547877605 (`mechanics/04`) | accepted | 14 min 01 s | 36 min 05 s | 7 min 57 s | 11 min 55 s | 4 min 34 s | 5 min 49 s |
| Pull request #162, run 38547877332 (`lean/01`) | accepted | 13 min 50 s | 35 min 20 s | 7 min 31 s | 10 min 48 s | 4 min 20 s | 6 min 03 s |
| Pull request #163, run 38547883087 (`agents-llm/01`) | accepted | 14 min 43 s | 37 min 57 s | 7 min 35 s | 14 min 29 s | 4 min 13 s | 5 min 49 s |
| Pull request #161 before the base of its identity, run 38534115654 | rejected: the checks changed | 23 min 53 s | 51 min 16 s | 17 min 31 s | 14 min 08 s | 3 min 49 s | 6 min 07 s |
| Push to `main`, run 38527223459, first run with the base job, cold caches | none | 29 min 46 s | 55 min 41 s | 23 min 05 s | 13 min 41 s | 3 min 55 s | 6 min 05 s |
| Push to `main`, run 38545077253, with `deploy` | none | 21 min 59 s | 49 min 07 s | 15 min 42 s | 13 min 58 s | 4 min 46 s | 5 min 25 s |

- **A pull request that changes one lesson takes 13 min 50 s to 14 min 43 s,
  against 22 min 56 s and 25 min 00 s without a base (F58, above).** That is
  9 to 10 minutes less, about 40 percent, and 2 to 3 minutes over the budget
  of 12 minutes of ADR 003 and of acceptance criterion 1 of Issue #147. The
  budget is **not met**.
- **The longest path is `build` and then `e2e` (about 7.5 plus 6 minutes),
  or `integration` alone (11 to 14.5 minutes, the longest job in #163).** Both
  are about 14 minutes. What the selection removed is the execution of the
  unchanged lessons; what remains is fixed cost: every job prepares its own
  runner (about 100 s), the Lean build runs in full, and the checks that are
  not per lesson (`integration`, `workflow`, the built-site checks of
  `e2e-other`) run as before.
- **The first measurement found a defect, which is fixed.** The first three
  pull requests (runs 38530560443, 38530560503, 38530570255) failed in
  `build`: `test_a_second_build_gives_byte_identical_previews` built a copy
  without the selection of the run and compared previews restored from a
  base made on another runner with previews computed on this one. The fix
  starts the second build from the state of the run (pull request #164) and
  the test still compares every preview byte for byte.
- **A change to the checks makes the run a full run, as designed.** Pull
  request #161 with the fix (run 38534115654) found the checks different from
  the base's, rejected the base and executed every lesson (22 of 22): 23 min
  53 s. Once `main` published the base of the new checks, the selection
  applied.
- **The run on `main` is a full run with a base published after it.** With
  warm caches it took 21 min 59 s; the first run, with cold caches, 29 min
  46 s, against 17 min 52 s on 2026-10-12 before F61. The difference to
  that run is the Quarto store and the regenerated context; this has not been
  separated from the runner differences measured on 2026-10-12.
- **Not measured, and not claimed:** whether the token of a fork pull request
  can read the base (it needs a pull request from a fork), the full-run
  budget at 110 lessons (F113), and three consecutive runs: the three pull
  requests ran at the same time (a start 3 seconds apart), on separate
  runners.

**Corrective actions proposed, to decide before F113 or in a follow-up of
F61 (none is applied):**

1. Split the job `integration` in two parts like `e2e` (it is the longest job
   in two of three runs, 10 to 14.5 minutes) without dropping a test.
2. Start the checks of the built site that need the base only after `build`,
   as now, but let the `e2e-other` part (5 to 6 minutes) take the checks that
   do not depend on the lessons in a job that runs beside `build`.
3. Cut the preparation of the runner (about 100 s in each of 8 jobs) with the
   caches already present: measure what is not cached before changing it.
4. Accept the budget as 15 minutes for a pull request until the fixed cost is
   reduced: this is a change of ADR 003 decision 5 and the owner's decision.

### The full run and the one-lesson pull request, decomposed (F118), measured 2026-10-15

F118 reads the jobs of the runs the roadmap names ("State at the change
cycle `pbc-planning-change-four-workstreams`") and the three one-lesson pull
requests of F61 from the Actions API and from their logs, and separates the
cost of a lesson from the cost of the runner. The call graph behind the
numbers, the verdict on the third build, the validity domains of the check
identity, the division of `integration`, the inventory of local build
obligations, and the proposal for the owner are in
`docs/verification-audit.md`. Times are job start to job end unless a column
says otherwise; "group build" is the step "Verify the group build" of the job
`build`, from the log; "prepare" is the step "Run ./.github/actions/prepare".

**The `build` job of a full run, with the cache state read from each log.**
Every full run below is a run on `main` without a base: the step that
verifies against a base did not run, so every lesson executed and the Quarto
store started empty. The four caches of the runner preparation are the uv
cache, the elan toolchain, the Lean packages with the Mathlib build products,
and the Playwright browser build.

| Run (build job) | Lessons | Job | Prepare | Group build | Lean build | `site-build` | `determinism` | Reproduction tests (count) | Caches of the preparation |
|---|---|---|---|---|---|---|---|---|---|
| 38545077253 (115789003862) | 22 | 15 min 42 s | 1 min 52 s | 13 min 36 s | 13 s | 2 min 43 s | 2 min 30 s | 8 min 02 s (23) | all four hit |
| 38527223459 (115730318530) | 22 | 23 min 05 s | 1 min 06 s | 21 min 49 s | 16 s | 4 min 13 s | 3 min 57 s | 13 min 11 s (23) | all four hit |
| 38607388478 (116001653330) | 28 | 26 min 57 s | 1 min 49 s | 24 min 57 s | 20 s | 4 min 55 s | 4 min 33 s | 14 min 58 s (29) | all four hit |
| 38621916706 (116051313541) | 32 | 31 min 15 s | 1 min 28 s | 29 min 32 s | 16 s | 5 min 49 s | 5 min 31 s | 17 min 47 s (33) | all four hit |
| 38639021950 (116109491079) | 32 | 30 min 32 s | 1 min 05 s | 29 min 18 s | 18 s | 5 min 41 s | 5 min 29 s | 17 min 39 s (33) | all four hit |
| 38659296393 (116176479806) | 32 | 21 min 07 s | 1 min 57 s | 18 min 59 s | 12 s | 3 min 51 s | 3 min 37 s | 11 min 12 s (33) | all four hit |
| 38687330455 (116265066825) | 32 | 27 min 58 s | 2 min 06 s | 25 min 31 s | 15 s | 5 min 00 s | 4 min 42 s | 15 min 22 s (33) | uv cache and Playwright build missed (`uv.lock` changed by the dependency bump #173); elan and lake hit |

- **The label "cold caches" of run 38527223459 does not hold.** All four
  caches of the runner preparation hit in that run, as in the warm run
  38545077253 of the same day; the only difference between the two is the
  speed of the runner (13 min 36 s against 21 min 49 s for the same work,
  22 lessons, the same commit family). The same holds for the runs at 28 and
  32 lessons: a cache miss cost at most about a minute (the preparation took 2 min 06 s
  in the one run that missed two caches, against 1 min 05 s to 1 min 57 s in
  the runs that hit all four), and the spread of 10 minutes between runs of equal
  size is the runner, not a cache.
- **The Quarto store is empty in a full run by design** (ADR 014 decision
  3), so the lessons execute in all four places of the call graph
  (`docs/verification-audit.md`, "Call graph"): the first build, the
  determinism build, the third build of
  `test_a_second_build_gives_byte_identical_previews`, and the reproduction of
  the lesson. A lesson executes **four times** in a full run, not the three of
  ADR 014 decision 11.
- **The reproduction tests are most of the group**: 8 min 02 s to 17 min 47 s,
  that is 59 to 60 percent of the group build in every run. They include the
  third build, which costs about as much as `determinism` (the same build from
  a fresh copy): 2 min 30 s to 5 min 31 s, or 18 to 19 percent of the group
  build. The per-test duration of a reproduction is not in the logs; the
  figure below is the group's reproduction time minus the `determinism` time,
  divided by the number of lessons (an estimate).

**Cost per lesson and growth, from the same runs.**

| Run | Lessons | Group build per lesson | `site-build` per lesson | `determinism` per lesson | Reproduction per lesson (estimate) |
|---|---|---|---|---|---|
| 38545077253 | 22 | 37.1 s | 7.4 s | 6.8 s | 15.1 s |
| 38527223459 | 22 | 59.5 s | 11.5 s | 10.8 s | 25.2 s |
| 38607388478 | 28 | 53.5 s | 10.5 s | 9.8 s | 22.3 s |
| 38621916706 | 32 | 55.4 s | 10.9 s | 10.3 s | 23.0 s |
| 38639021950 | 32 | 54.9 s | 10.7 s | 10.3 s | 22.8 s |
| 38659296393 | 32 | 35.6 s | 7.2 s | 6.8 s | 14.2 s |
| 38687330455 | 32 | 47.8 s | 9.4 s | 8.8 s | 20.0 s |

- **The cost of a lesson in one job is 36 to 60 seconds, and it does not
  grow with the lesson count.** The runners fall in two classes: a fast one
  (37.1 s per lesson at 22 and 35.6 s at 32) and a slow one (59.5 s at 22,
  53.5 s at 28, 54.9 to 55.4 s at 32). Within a class the cost per lesson is
  flat from 22 to 32 lessons, so the group build is linear in the lesson
  count, with a fixed part of 1.8 to 4.4 minutes and a marginal cost of 32 to
  46 s per lesson: the cost per lesson of the bounds below (36 and 60 s)
  therefore overstates the marginal cost, which is the safe direction. A line through the two fast runs has a slope
  of 32 s per lesson and an intercept of 105 s, one through the four slow runs
  a slope of 46 s per lesson and an intercept of 266 s. **Uncertainty:** the
  fits rest on two and four points; the 1.7 fold difference between the
  classes is larger than any trend between 22 and 32 lessons, and a third
  class slower than the slowest measured is not excluded. The projections
  below therefore use the bounds, not the fits.
- The page times in the build logs say the same: the executed lesson pages
  took 5.1 to 8.2 s on average in the first build (the two fast runs 5.1 s,
  the slow runs 7.5 to 8.2 s, the run that missed two caches 6.8 s) and no
  more than 21.4 s for the slowest lesson, against the budget of 30 s for one page.

**Projections, not measurements.** One `build` job of a full run in seconds is
prepare (up to 126 s, the slowest measured) plus the lesson count times a
cost per lesson of 36 s (fast bound) to 60 s (slow bound, 59.5 s measured);
the fixed part of the group is inside the 60 s at these counts.

| Lessons | Fast bound | Slow bound | Against the 45-minute timeout |
|---|---|---|---|
| 32 (measured: 21 to 31 min, above) | 21 min | 34 min | within |
| 40 | 26 min | 42 min | within by 3 min at the slow bound |
| 47 | 30 min | 49 min | beyond at the slow bound; within a 60-minute timeout |
| 64 | 41 min | 66 min | beyond at the slow bound |
| 110 (the curriculum, 119 with the reference slots) | 68 min | 112 min | beyond at both bounds |

The 35-minute planning budget of ADR 014 decision 7 holds 32 to 33 lessons at
the slow bound (the ADR assumed about 40 at 41 s per lesson: the slowest
measured runner costs 59.5 s per lesson, 45 percent more, so the derivation
of S = 32 holds with no margin at that bound, not the 8 minutes it states).
Removing the third
build would take about a fifth off these figures (the per-lesson cost 36 to
60 s drops to about 29 to 49 s); that is F119's change and is not applied.

**One-lesson pull requests of F61, decomposed.** The three runs of 2026-10-14
(`mechanics/04`, `lean/01`, `agents-llm/01`; 22 lessons; each "selective run
against base 2e0bd620566f: 1 of 22 lessons executed, 21 restored"; all caches
of the preparation hit). Wall clock is the run from creation to end.

| Run (build, integration jobs) | Wall clock | `build` job: prepare, then group build | Group build: Lean, `site-build`, `determinism`, reproduction tests (2) | `integration` job: prepare, then tests | Slowest `e2e` job |
|---|---|---|---|---|---|
| 38547877605 (#161; 115798328928, 115798329152) | 14 min 01 s | 7 min 57 s: 1 min 41 s, then 6 min 00 s | 14 s, 1 min 46 s, 1 min 33 s, 2 min 06 s | 11 min 55 s: 1 min 43 s, then 10 min 06 s | 5 min 49 s (`other`) |
| 38547877332 (#162; 115798328326, 115798327987) | 13 min 50 s | 7 min 31 s: 1 min 08 s, then 6 min 12 s | 15 s, 1 min 44 s, 1 min 29 s, 2 min 21 s | 10 min 48 s: 1 min 39 s, then 9 min 03 s | 6 min 03 s (`other`) |
| 38547883087 (#163; 115798347207, 115798347900) | 14 min 43 s | 7 min 35 s: 1 min 20 s, then 5 min 59 s | 14 s, 1 min 46 s, 1 min 33 s, 2 min 04 s | 14 min 29 s: 1 min 29 s, then 12 min 52 s | 5 min 49 s (`other`) |

- **Runner preparation** is 65 to 126 s in the `build` job of a full run and
  68 to 103 s in the jobs of these three runs, about 100 s in each of the
  eight jobs of a run: 13 minutes of runner time that do not depend on the
  change.
- **Lesson-dependent time in `build`** is small: the executed lesson's page
  took at most 4.3 to 8.4 s in the first build (the slowest page of the
  build), executed four times, plus the render of its reproduction: about
  40 to 60 s of the 6 minutes. The other 21 lessons are restored and cost
  1.2 to 1.4 s each to render, three times (first build, determinism build,
  third build): about 4 s per additional unchanged lesson in the job. The
  rest of `build` is fixed: the Lean build (14 to 15 s), the render of the 9
  pages that are not lessons, the Quarto start of three builds.
- **`integration` is the longest job in one of three runs** (14 min 29 s in
  #163) and is fixed cost: it executes no lesson, and its duration in full
  runs (12 min 08 s to 16 min 08 s at 22 to 32 lessons) shows no trend with
  the lesson count against the spread of the runners.
- **The critical path** of the two quicker runs is `build` then the slowest
  `e2e` job (13 min 46 s and 13 min 34 s), of the third `integration` (14 min
  29 s) plus the aggregate job.

**Judged against ADR 015.** A typical pull request (one lesson, an accepted
base) took 13 min 50 s, 14 min 01 s, and 14 min 43 s: **the budget of 20
minutes is met by 5 min 17 s at the least, and the 15-minute target is met
in all three** (by 17 s in the slowest). The three ran at the same time, so
the record of three consecutive runs that F61 owes is still not made. The growth per lesson of such a pull request is about 4 s of `build` for each
unchanged lesson, on the critical path of two of three runs: the slowest of
them (13 min 46 s of `build` and `e2e`) has 74 s to the target, which about 18
more lessons use, so the target is likely to be lost at about 40 lessons if
nothing else changes, and the budget of 20 minutes not before several times
that. A **full run** has no budget in
ADR 015; its wall clock is 21 min 59 s to 40 min 48 s at 22 to 32 lessons
(the table under "State at the change cycle" of `docs/roadmap.md`), and the
proposal for its timeout is in `docs/verification-audit.md`, "Proposal for
the owner".

### F119, measurements after the merge

Measured on 2026-10-16, after the workflow of #185 (PR #191) was merged and
the `main` run after it had published a base. The evidence below is
recorded here; whether it satisfies criteria 3, 5 and 6 of #185 and
criterion 1 of #147 is for the independent assessment and the owner, and
neither Issue is closed by this record.

**Three consecutive one-lesson pull requests** (no other pull request was
merged to `main` between them; each ran against the base published by the
`main` run of the previous merge):

| Pull request | Lesson | Wall clock | Base (`main` run) | Selection |
|---|---|---|---|---|
| #195 (Issue #192) | agents-abm/01 | 14 min 05 s | 38868679531 | 2 of 32 lessons: agents-abm/01, mechanics/09 |
| #197 (Issue #193) | lean/02 | 14 min 52 s | 38876222290 | 2 of 32 lessons: lean/02, mechanics/09 |
| #198 (Issue #194) | waves/01 | 12 min 27 s | 38882391600 | 2 of 32 lessons: mechanics/09, waves/01 |

Wall clock is the time from the creation of the pull request to the last
check. All three are within the budget of 20 minutes and the 15-minute
target of ADR 015 (by 8 s at the least). All three changed one lesson file,
no workflow, and every check was green with `mergeStateStatus` `CLEAN`.
Each pull request executed two lessons: the changed lesson and
mechanics/09, which the selection added each time (the reason is not
investigated here).

**The critical path of the integration part, before and after** (criterion
3). Before: the single `integration` job of F118 took 14 min 29 s in the
slowest of three runs (#163) and 12 min 08 s to 16 min 08 s in full runs.
After, on the three pull requests: `integration-quarto` 5 min 38 s to
6 min 00 s, `integration-browser` 5 min 00 s to 5 min 22 s,
`integration-other` 5 min 22 s to 6 min 30 s; the slowest of the three was
5 min 38 s to 6 min 30 s. The critical path of a pull request is now
`build` (5 min 32 s to 7 min 25 s) followed by the slowest `e2e` job (`e2e (other)`,
6 min 35 s to 7 min 08 s), then `verify`; the integration jobs
end before `build` does and are off the critical path.

**Full runs on `main`** (criterion 6), 32 lessons: 28 min 01 s (run
38868679531, the merge of #191), 34 min 14 s (38876222290, after #195),
31 min 32 s (38882391600, after #197), and 31 min 18 s (38888399762, after
#198). Each published a base and deployed.

**A real one-lesson `finish-feature.sh` and `review-feature.sh`**
(criterion 5): for #192, #193 and #194 the review passed and the finish
recorded a targeted pass naming the base ("the artifact of the push run ...
on `main`, whose job `verify` succeeded") and the selection (2 of 32
lessons executed, 30 restored). The targeted tier built no site in these
runs. The review of #192 first returned a major because the Issue asked for
pull request CI evidence that cannot exist before the pull request; the
Issues were reworded so that this measurement is recorded here and not as
an acceptance criterion of the fix.

**Not measured here:** the invalidation of a reused targeted verification
when the base changes (it must fail closed) is not demonstrated by these
runs; F120 (#196) covers the fail-closed cases in its evidence. No pull
request without an accepted base, a fork pull request, and a cold-cache run
were measured.

### F117, measurement after the merge

Measured on 2026-10-17, after the merge of F117 (#205). The first complete
`main` run after the merge (39010505705, 06:35 UTC) failed on a statistical
test of the lesson `agents-abm/01` that depends on the runner class, not on
F117 (fixed by #209); it is not a duration measurement. The complete runs
that followed, all with the experiment contract of F117 on `main`:

| Run | After | Lessons | Total | Build job | `e2e (other)` |
|---|---|---|---|---|---|
| 39041682506 | #209 (the fix) | 32 | 34 min 12 s | 26 min 52 s | 6 min 49 s |
| 39047093749 | #207 (F72) | 35 | 25 min 07 s | 18 min 14 s | 6 min 25 s |
| 39049941041 | #208 (F66) | 38 | **35 min 18 s** | **27 min 16 s** | 7 min 35 s |

The owner asked for the 38-lesson run to be the recorded figure: **35 min
18 s for the complete `main` run and 27 min 16 s for the build job**, against
the interim gate of 60 minutes approved for up to 45 lessons. The spread
between the runs is larger than the growth with the lesson count: the build
job took 18 min 14 s on one run of 35 lessons and 27 min 16 s on one of 38,
which is the runner-class difference found by F120 (its evidence document is
published with that feature), not the six lessons. The growth with the
lessons is therefore not separable from the runner spread in these three
runs; read the 60-minute gate against the upper figure. The number of
executions of each lesson in the build was not measured separately here.

**Capacity of the temporary 45-lesson gate.** At 38 lessons the slowest
measured complete run (35 min 18 s) leaves 24 min 42 s of the 60 minutes.
The owner's rule of 2026-10-17 was: re-measure at 42 lessons, decide the
capacity at 44 lessons at the latest, or earlier if a complete run exceeds
45 minutes (Issue #150). On 2026-10-21 the owner extended the gate to 64
lessons with the 60 minutes unchanged (ADR 014 status, Issue #253): 64 was
a planning boundary, with capacity to be re-measured at 55 lessons and the
next decision due by 60 lessons at the latest, or earlier if the `build` job
approached 55 minutes (superseded history: these points are replaced by
those of the decision of 2026-10-24 below); the `build` job's duration and
the run's total duration are reported separately. On 2026-10-24 the owner raised the gate to
110 lessons, the whole reference curriculum, with the `build` job's timeout
raised from 60 to 90 minutes and every other job at 45 (ADR 014 status,
Issue #278). The evidence is the measured cost of 39 to 46 s per lesson over
about 2 minutes of preparation (F120, `docs/incremental-main-evidence.md`),
which projects the `build` job at 110 lessons at about 73 to 86 minutes (a
projection, not a measurement). 110 is a planning boundary that no check
enforces; capacity is re-measured at 75 and at 95 lessons, and the next
decision is the owner's earlier if a complete run on `main` approaches 80
minutes, repeated runs show too little margin, or verification failures
point to a capacity problem. The cost the owner accepted: a run on `main`
can last up to about 90 minutes, so the publication after a merge comes
later; pull requests are not affected, since they pay for what they change
(F61).

**Learner walkthrough (criterion 7).** A fresh subagent that did not write
the pages followed the published instructions on a clean clone of the merged
content for a simulation lesson (mechanics/01), an agent-replay lesson
(agents-llm/01) and a Lean lesson (lean/01), without building the website:
every command worked as written, no blocker and no substantive discrepancy,
six minor points (recorded on pull request #205). It was agent-run; the owner
accepted it as the independent walkthrough on 2026-10-17.

### Incremental `main`: the staged evidence (F120), measured 2026-10-16

The evidence for ADR 017 is in `docs/incremental-main-evidence.md`: the
same-commit comparison of a full and a selective verification (run
38876222290 on `main` against a local run with its base), the byte
comparison of identical inputs across the runners of eleven push runs on
`main` (two byte classes; 7 of 32 lessons differ across them), the costs,
and the full-run fallback under the 60-minute timeout. One measurement
there belongs to this record as well: the first one-lesson pull request
after F119, run 38874606240 (pull request #195, 32 lessons, 1 executed and
31 restored), took 14 min 05 s of wall clock with `build` at 7 min 15 s
and `integration-other` the longest fixed job at 6 min 30 s, so the
20-minute budget was met by 5 min 55 s and the 15-minute target by 55 s;
the record of three consecutive runs that F119 owes is still not made.
The full runs on `main` of the same day took 28 min 01 s and 34 min 14 s
(`build` 20 min 50 s and 25 min 52 s).

## Release (human)

After the items above: tag the merge commit (`git tag -a mvp-v1.0.0`) and
publish a GitHub release whose note lists the eleven lessons, the four
strands, the content proposal workflow, and the known limits, using the open
Issues from the audit, the reading pass, and the CI budget. Link the tag and
the release note from Issue #29, then close it.
