# Development

## One-time setup

A supported machine runs macOS or Linux. The setup below runs once for each
machine and is the only step that may need administrator rights. Everything
after it, including `./scripts/verify.sh`, runs as a normal user and installs
no system packages.

1. Install the tools:

   | Tool | Purpose | macOS | Linux |
   |---|---|---|---|
   | Git | Source control | Xcode command line tools, or `brew install git` | System package manager |
   | [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python, the Python packages, and Quarto, all pinned in `uv.lock` | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
   | [elan](https://lean-lang.org/install/manual/) | The Lean toolchain pinned in `lean/lean-toolchain` | `brew install elan-init`, or the command for Linux | `curl -sSf https://elan.lean-lang.org/elan-init.sh \| sh` |
   | jq 1.6 or later | Used by the workflow self-tests | `brew install jq` | `sudo apt-get install jq` |

   Make sure `~/.elan/bin` is on your `PATH` afterwards; the elan installer
   offers to add it.

2. Install the locked Python environment and the browser build that the
   built-site checks use. The browser build is fixed by the Playwright
   version in `uv.lock` and is downloaded into your user cache.

   ```bash
   uv sync --locked
   uv run --locked playwright install --only-shell chromium
   ```

   On Linux the browser also needs system libraries. Add `--with-deps` to the
   second command to let Playwright install them on the distributions it
   supports (it asks for administrator rights):

   ```bash
   uv run --locked playwright install --with-deps --only-shell chromium
   ```

   On other distributions install the libraries by hand; the preflight check
   reports a browser that cannot start.

3. Check the result:

   ```bash
   ./scripts/doctor.sh
   ```

   It reports each prerequisite as `OK`, `WARNING`, or `FAILED` with a fix
   hint, exits non-zero when a required prerequisite is missing, and never
   modifies anything. Besides the tools above it checks what the agentic
   development workflow needs and verification does not: the GitHub CLI
   (`gh`), installed and authenticated, and the Codex or Claude CLI. A
   missing agent CLI fails when `.agents/agents.conf` assigns it to a role
   and is a warning otherwise. It also warns when a pull request into `main`
   can be merged while its checks fail, because no ruleset requires the
   `verify` status check; see `docs/deployment.md`.

This setup is the maintainers' and agents' contract, not a reader's. For
readers, `site/reproduce.qmd` (published as the "Set up" page) is the single
guide, organised by what they do: run an experiment with Git and uv, replay
an agent lesson or run it live with their own key, and check a proof with
elan (ADR 016). A test (`tests/integration/test_setup_page.py`) performs its
Python-only commands in a fresh clone, requires that they install nothing of
the `dev` group, and runs an experiment of each kind in that environment. The external links of the reference register are checked on
demand with `./scripts/check-links.sh`; see "Link maintenance" in
`docs/authoring.md`.

The first verification run downloads the Lean toolchain and the Mathlib build
cache: about 0.5 GB of downloads that unpack to roughly 8 GB in `lean/.lake/`
and 3 GB in `~/.elan/`. Later runs reuse them. CI prepares its runner with the
same steps.

## Verification

Verification has three tiers (ADR 017 decision 7). Which one a change needs
depends on what it touches, and the targeted run says so when it is not the
right one:

```bash
./scripts/verify.sh --targeted   # an ordinary change: no site build
./scripts/verify.sh --base       # a change to what other pages display of a lesson
./scripts/verify.sh              # a shared input or a file of the checks changed
```

- **The targeted run** (`--targeted`) is the run before a pull request for an
  ordinary change: a lesson, its code and tests, a proof, a document. It
  retrieves the base of the latest successful run on `main` read-only
  (`scripts/fetch-base.sh`, with your `gh` login and the same provenance rule
  as CI; see "Selection against a base"), computes the selection CI will make
  and reports it (the lessons CI will execute, or that CI will run
  everything), and runs the checks of the groups that the entry `targeted:`
  of `scripts/verify.conf` names: the supported-machine contract, lint and
  format, the unit tests, the lesson source checks, the dataset checks, the
  documentation and workflow structure checks, the workflow self-tests when a
  workflow file changed, and `lesson-pages`, the single-page render of each
  selected lesson in a clone of the working tree with the Lean build for
  changed proofs (`scripts/check-lesson-pages.sh`). It performs no site
  build, no determinism build, and no built-site check. It never guesses:
  without an acceptable base (no `gh` login, no successful run on `main`, a
  rejected artifact) it reports "No base" and that CI will run everything;
  when the selection names a full run it reports "CI will run everything"
  with the reason; when a selected lesson is new to the base it names
  `--base`. In each case it verifies nothing, and you run the tier it names.
- **The run with a base** (`--base`, with or without a directory) is for a
  change that alters what other pages display of a lesson: the front-matter
  fields that form the learning path and the headers of neighbouring pages
  (the id, strand, order, prerequisites, related lessons, title, course, and
  slot), or a new lesson. It renders every page from the base's results,
  executes the selected lessons, and checks the pages whose bytes differ,
  with every other check: it builds the site.
- **The full run** (no options) runs every check and executes every lesson.
  It is required when the selection cannot bound the change to lessons: a
  shared input of ADR 014 decision 4 (`src/pbc/authoring`; the templates,
  filters, assets, and shared site files; `site/_quarto.yml`; the curriculum
  file; the Python pins; the Lean toolchain and manifest) or a file of the
  check identity (the verification script and its configuration, the build
  and determinism scripts, `tests/e2e`, `tests/support`, the pins, the
  runner preparation). The targeted run reports exactly this. CI runs it
  without a base on every push to `main`, as `./scripts/verify.sh --all`,
  which also runs the workflow self-tests described below, and on every pull
  request against a base. It leaves the built site in `site/_site/`, which
  Git ignores.

A pass is recorded with its tier, and with a base the base and the selection
("Recorded verification"). `scripts/review-feature.sh`,
`scripts/apply-triage.sh`, and `scripts/finish-feature.sh` gate on
`./scripts/verify.sh --reuse --targeted`, which takes a recorded pass for the
content (a targeted one only against the same current base and selection) and otherwise runs the targeted run; the commit message
and the review name the tier, the base, and the selection. CI stays the
publication gate: it builds and validates the site on every pull request and
push, whatever tier ran locally.

**A Level 3 change** (ADR 020 decisions 1 and 5; "The risk level" below) is
accepted on a complete verification of its final tree: `finish-feature.sh`
runs `./scripts/verify.sh --reuse` and takes only a full pass, and the latest
review must have been made on a full pass of that tree, after it. Its
intermediate fix rounds may take quick feedback from a partial run instead,
`./scripts/verify.sh --only <groups>` for the groups the changed paths touch
plus the unit tests of the changed modules (typically `code` and
`integration-other`, about 13 minutes against about 68): `apply-triage.sh`
runs the groups `default`, `code`, and `integration-other` for a fix round
of a Level 3 change, and `review-feature.sh --feedback` reviews an
intermediate round on them. A partial run records nothing and is never
evidence; a review made with `--feedback` or `--unverified` is never the
final review. The targeted tier is unchanged and stays refused when the
check identity differs from the base's.

**The time log** (ADR 020 decision 7). Every run of `./scripts/verify.sh`
appends one line, `<UTC time> | <tier> | <tree> | <seconds> | <result>`, to
`verify-time.log` in the Git directory that every worktree of the clone
shares (`git rev-parse --git-common-dir`), or to the file
`VERIFY_TIME_LOG` names. The tier is `full`, `base`, `targeted`, or
`only:<groups>`; the result `passed`, `failed`, `refused`, or `reused`. The
log is per machine, never committed, and read by no gate: the evaluation of
ADR 020 decision 10 reads it afterwards. A log that cannot be written
changes nothing about the run.

**Budgets** (ADR 020 decision 6). The 30-second budget of a lesson page is a
hard check: a lesson over its budget fails, and `scripts/lesson-budgets.conf`
is the table of exceptions, each with a reason and the owner's approval (a
new or a raised entry is the escalation trigger "a budget widened"). A
budget is never met by changing scientific content. A wall-clock budget of a
whole run, the 20 minutes of a pull request (ADR 015), the planning budget
of a full run, or a complete run on `main` above 45 minutes, is a
measurement for the owner when it is exceeded, not a failed gate and not a
mandate to optimise: the owner decides at the re-assessment points, choosing
from the responses of ADR 003 decision 6. Since the owner's decision of
2026-10-24 (ADR 014 status, Issue #278), which raises the interim full-run
gate to 110 lessons, the whole reference curriculum, with the `build` job's
timeout raised from 60 to 90 minutes, they are: re-measure at 75 and at 95
lessons, and decide earlier when a complete run on `main` approaches 80
minutes, repeated runs show too little margin, or verification failures
point to a capacity problem, with the job's duration and the run's total
duration reported separately (the former points of 42 and 44 lessons, and
of 55 and 60 lessons under the decision of 2026-10-21, are superseded
history). The 110 lessons are a planning boundary, not a check. The owner
accepted the cost: a run on `main` can last up to about 90 minutes, so the
publication after a merge comes later; a pull request is not affected, since
it pays for what it changes. `docs/release-readiness.md` records the
measurements.

The checks are declared in `scripts/verify.conf`, and the workflow self-tests
in `scripts/verify-workflow.conf`. They run in this order:

| Check | What it does |
|---|---|
| `preflight` | Reports every missing prerequisite of the one-time setup with a fix hint, and confirms that the pinned browser build starts. |
| `preflight-test` | `tests/preflight-test.sh`: the preflight reports each missing prerequisite and is the first check. |
| `lint`, `format` | Ruff on the Python sources. |
| `unit-tests` | pytest on `tests/unit`: the behaviour of `src/pbc`. |
| `skills-config` | `python -m pbc.skills`: every agent skill under `.agents/skills/` has its `SKILL.md` and a provenance record with the required fields whose digest matches its files, the README of the directory lists exactly those skills, and every skill a feature plan names on a `Skills:` line exists at the revision it gives (ADR 019). The one check that reads the directory, as data. |
| `lean-build` | `scripts/check-lean.sh`: takes Mathlib from its build cache and never compiles it from source, builds every module under `lean/PhysicsByConstruction/`, then audits every declaration. A declared `axiom`, a `sorry`, or any axiom besides Lean's three standard ones fails the check. A passed check writes `lean/.lake/pbc-build-record.json` (the versions and a checksum of every module), which the pages of the `lean` strand read; a failed check removes it. |
| `check-tests-quarto`, `check-tests-browser`, `check-tests-other` | Three checks that together are pytest on `tests/integration`: every check fails on an input that violates it, a lesson made from the template passes, and the CI workflow keeps its permission boundaries. The first names the files that build fixture sites with Quarto, the second the files that need the browser, and the third runs every other file, so a new file runs without a change; CI runs them in three jobs that prepare only what each part needs (`docs/verification-audit.md`, "Division into independent parts"). `tests/integration/test_site_check_division.py` proves by collection that every test runs exactly once. |
| `lesson-checks` | pytest on `tests/lessons`: the lesson sources follow the format of `docs/authoring.md`. Front matter follows the schema, the required sections and the generated header are present, the lessons form one learning path (unique ids, orders without gaps or duplicates, prerequisites that exist, come earlier, and form no cycle), displayed code is an executed cell or marked "not verified", figure cells have alternative text, and no generated artifact is committed under `site/` or `src/`. |
| `lesson-pages` | `scripts/check-lesson-pages.sh`: in the targeted run, the single-page render of each selected lesson in a clone of the working tree with its own locked environment (so the page reads the clone's files, as a reader's clone would), within the budget of a lesson page (30 seconds; `scripts/lesson-budgets.conf` lists the lessons with a budget of their own, each with its reason, and an exception needs a reason and the owner's approval), after the Lean build in the clone when a selected lesson displays Lean modules, and after the Lean build of the checkout when a file under `lean/` changed; then the experiment of each selected lesson with a reader's commands, in one learner environment of the clone (`uv sync --locked --no-dev`), within the budget, compared with the page it rendered (figure files byte for byte, numbers at their displayed precision). In a run that builds the site it has nothing to do and says so: the build, the determinism check, and the reproduction cover every lesson. |
| `site-build` | `scripts/build-site.sh`: Quarto executes every page in the locked environment and renders `site/_site/`. A failing cell or an equation that cannot become MathML fails the build. |
| `site-checks-*` | Four checks that together are pytest on `tests/e2e` ("The checks of the built site" below), on the built site served under its sub-path: nothing is loaded from another origin, no cookie is set, images have alt text and dimensions, internal links resolve, pages are readable without JavaScript and a script adds no content to them (except inside an element with `data-enhancement`, an `id`, and static content of its own), do not scroll sideways at phone, tablet, or desktop width and keep every image on the screen, and the axe-core scan finds no WCAG 2.1 A or AA violation. For lessons: every lesson has a built page with the required sections, the home page leads to every lesson without JavaScript, the learning path page and every lesson header show what the front matter says (order, difficulty, prerequisites, previous and next), excerpts are identical to their source in `src/pbc` or in `lean/` (for a Lean excerpt, the region between its anchors), the formal proofs lesson states the commit, Lean, and Mathlib versions and links to the proofs at the built commit, "not verified" material shows its label, the last section of each lesson is headed by its activity and lists the commands from a clone to its experiment and no render, the experiment of each lesson, run with those commands in one learner environment per run (`uv sync --locked --no-dev` in a fresh clone), writes the published figure files byte for byte and the published numbers at their displayed precision within 30 seconds, and the internal render of each page in a fresh clone regenerates the published page. |
| `determinism` | `scripts/check-determinism.sh`: builds a fresh copy of the site sources a second time and requires byte-identical output. |
| Workflow self-tests | The shell tests of the agentic development workflow in `tests/*-test.sh`. Run in CI always, and locally only when a workflow file changed; see "Workflow self-tests" below. |

Run one check on its own with the command from `scripts/verify.conf`, for
example `uv run --locked pytest tests/unit`. The `site-checks-*` checks and
`determinism` need the output of `site-build`. To see what a lesson you are
changing computes, run its experiment, which writes the figures and numbers
of its page into a directory:

```bash
uv run --locked python -m pbc.<course>.experiments.<lesson> results
```

In this checkout the command keeps the development tools; a reader's
`--no-dev` would remove them from the environment. Then run the targeted
tier, which checks the page of the lesson in a clone (ADR 016, ADR 017
decision 7).

How to write a lesson is described in `docs/authoring.md`; the template is
`docs/lesson-template.qmd`.

### The checks of the built site

`pytest tests/e2e` runs every check of the built site and is what you run
while working on one. Verification runs the same tests as four checks, so
that CI can run them side by side (see "Groups of checks"):

| Check | Group | Runs |
|---|---|---|
| `site-checks-reproduction` | `build` | The tests marked `same_machine`: the reproduction of every lesson, which compares the regenerated page byte for byte with the built one. A selective run reproduces the lessons it executed; one that executes no lesson (a change to the documentation only) has nothing to reproduce and passes, while every other run that selects no test fails. |
| `site-checks-pages-1`, `site-checks-pages-2` | `e2e-pages-1`, `e2e-pages-2` | `tests/e2e/test_built_site.py`; part 2 is the three slowest tests. |
| `site-checks-other` | `e2e-other` | Every other test of `tests/e2e`. It names the file it leaves out, so a new test file runs without a change. |

**Mark a test that compares bytes with the built site** with
`@pytest.mark.same_machine`. Numerical output can differ in the last digit
between processors, and the jobs of CI run on different machines. A marked
test runs in the group `build`, in the job that built the site, like the
second build of `determinism`. A test that compares bytes and is not marked
passes locally and fails in CI now and then.

**A test that recomputes a lesson's result on the checking machine** and
compares it with the data embedded in the page asks
`support.site_checks.inherited` first, as
`tests/e2e/test_comparator.py` does for the gravitational-wave lesson
(issue 268). It compares when this run executed the lesson (a run without
a base, a full run, or a selection that executes it) and skips with the
reason when the selection restored it from the base, whose run executed
and compared it on its own machine. A selection that cannot be read or
does not name the lesson once as executed or restored, or the base it
restores from by its id and identity, fails the test; it never skips it. The tolerance is not widened for another platform.

`--shard <part>/<parts>` selects a part of `tests/e2e/test_built_site.py`.
What a part holds is written in `tests/e2e/shards.json` and does not follow
from the order in which pytest finds the tests. A new test of that file runs
in part 1 without a change; an entry that names a test that no longer exists
is an error.

`tests/integration/test_site_check_division.py` collects what the four checks
run and requires that it is every test of `tests/e2e`, each exactly once, and
that the check in the group `build` holds exactly the marked tests. It does
the same for the three `check-tests-*` checks and `tests/integration`.

### Other browser engines

Verification uses Chromium. To run the built-site checks in Firefox or WebKit
as well, install those engines once and name the engine:

```bash
uv run --locked playwright install firefox webkit
uv run --locked pytest tests/e2e --engine firefox
uv run --locked pytest tests/e2e --engine webkit
```

### Updating the pinned toolchains

Every update is an ordinary pull request that has to pass verification.

- **Python packages, Quarto, Playwright, and GitHub Actions**: Dependabot
  proposes updates. By hand: `uv lock --upgrade`. A new Playwright version
  pins a new browser build; install it with the command of the one-time
  setup.
- **Lean and Mathlib** are bumped together by hand: set the Mathlib tag in
  `lean/lakefile.toml`, run `lake update` in `lean/` (it also updates
  `lean/lean-toolchain` and `lean/lake-manifest.json`), and commit all three
  files.
- **elan in CI** is pinned by version and checksum in
  `.github/workflows/ci.yml`.
- **The math font** is vendored; see `site/assets/fonts/README.md`.

## Configuring verification

`./scripts/verify.sh` runs the checks declared in `scripts/verify.conf`, one
per line:

```text
<name>: <command>
```

Every listed check is required. Each command runs with `bash -eo pipefail`
from the repository root, so a failing step in a pipeline or command sequence
fails the check. Its first word is the required tool. Verification fails
when that tool is missing or not executable, when a command exits non-zero, or
when the configuration is missing, empty, or malformed. All checks run even
after a failure, and a summary lists each check as `PASS` or `FAIL`.

There is no automatic stack detection and no optional check: remove a check
from `scripts/verify.conf` rather than letting it be skipped. CI declares no
check of its own; a check that is in neither `scripts/verify.conf` nor
`scripts/verify-workflow.conf` does not exist.

### Groups of checks

A check may name a group in square brackets after its name:

```text
lint [code]: ruff check .
unit-tests [code]: pytest tests/unit
site-build [build]: ./scripts/build-site.sh
tests-in-a-browser [e2e]: pytest tests/e2e
```

- `./scripts/verify.sh` runs every check, whatever its group. Nothing changes
  for the developer and for the workflow scripts.
- `./scripts/verify.sh --only code` runs the checks of one group, and
  `--only code,build` those of several, in the order of the file.
- `./scripts/verify.sh --groups` prints the groups that have a check.
- A check without a group is in the group `default`.
- An unknown group is an error, so a renamed group cannot pass unnoticed.

Groups exist for a CI that has outgrown one job: each job runs
`./scripts/verify.sh --all --only <group>`, and one job that needs all of them
is the required check. Every check stays declared in `scripts/verify.conf`
or `scripts/verify-workflow.conf`; none is declared in the workflow file.
Such a CI has to run **every** group, `default` included, or a check that is
added without a group runs on a laptop and never in CI. Compare the output of
`--groups` with the groups of the workflow file in a test of the project.

A partial run is never a verification. With `--only` nothing is recorded as
passed and `--reuse` is refused, so `review-feature.sh` and
`finish-feature.sh` still run the tier the change needs ("Verification"). A
failing partial run removes an existing record, like any failing run. The
workflow self-tests keep their own rule with `--only`: they run when a
workflow file changed, or with `--all`.

The targeted run is not a partial run in this sense: the reserved entry
`targeted: <group>[,<group>...]` of `scripts/verify.conf` declares the groups
it performs, and its pass is recorded with its tier. A project without that
entry has one tier, and `./scripts/verify.sh --targeted` runs every check.

### Selection against a base

CI takes the base from the artifact of an earlier run of `main` with
`scripts/fetch-base.sh` and publishes it with `scripts/collect-base.sh`
(see [deployment](deployment.md)). Locally you give a directory with
the same three parts (`digests.json`, `pages.json`, `freeze/`; the build
leaves them beside the site as `site/_digests.json`, `site/_pages.json`, and
`site/_freeze/`).

`./scripts/verify.sh --base <directory>` (ADR 014) names the directory of a
verified base; without a directory, `--base` and `--targeted` retrieve it
with `scripts/fetch-base.sh` into `.agents/verification/base`, using the
`gh` login of your machine read-only (`GH_TOKEN` and `GITHUB_REPOSITORY`
when set, as in CI), under the same provenance rule as CI. The base is `digests.json` (the input digest of every lesson and the
identity of the checks, written by `python -m pbc.authoring.digest`) and
`freeze/` (the executed results). The script computes the selection once with
`pbc.authoring.selection` and writes it to `.agents/verification/selection.json`,
the one place the checks read it. A lesson is executed when its digest differs
from the base's; a base that is missing, truncated, of another format, or
without an identity, a lesson without a digest, and a change to the checks
themselves give a full run, and the reason is printed and recorded. The
option combines with `--only`, not with `--reuse` or `--groups`. A run
without it removes an earlier selection and verifies everything. The record
of a run with a base carries a `selection:` line that names the base, and
`--reuse` never takes such a record for a verification of the content alone.

What the selection controls (ADR 014 decision 3):

- **The build** (`scripts/build-site.sh`) writes the executed results of every
  page to `site/_freeze/` (the store, which Git ignores; Quarto's `freeze`,
  switched on by the profile `site/_quarto-store.yml`). It starts by removing
  the store. With a base it restores the entries of the lessons the selection
  says are unchanged and leaves every other page, including every page that is
  not a lesson, to be executed. It also writes `site/_digests.json` (the input
  digest of every lesson), `site/_pages.json` (the checksum of every file of
  the built site with the build commit normalised, `pbc.authoring.pages`),
  and `site/_timings.json` (the seconds of every page, compared with the
  30-second budget of a lesson page). The store, the digests, and the page
  record are the files of a base; a restored entry must be plain files and
  JSON, or the base is not used.
- **The determinism check** copies the sources without the store and builds
  again from the same restored state, so the lessons that were executed
  execute twice and the comparison still covers every byte of the site.
- **The context of a page** is never taken from the store. The header
  (`lesson_header`), the last section (`reproduce_this`), and the code and
  Lean excerpts (`excerpt`, `lean_excerpt`, `lean_evidence`) leave a marker
  in the result of their cell: the kind of region and what it is built from,
  with no commit and no other lesson. The post-render script `site/context.py`
  (the first of `post-render`) replaces every marker by its region, built from
  the front matter of every lesson as it is now and the commit of the run, so
  a page restored from the store shows the navigation and the commit of this
  run. It fails the build for a marker that is not valid, for a lesson page
  without a header or a last section, and for a marker that stays.
  A lesson author writes the same cells as before.
- **The checks of one page** (reading without JavaScript, widths,
  accessibility, payload) run for the pages whose normalised bytes differ from
  the base's and for every page of an executed lesson
  (`site_checks.checked_pages`). A page links the files that are not pages
  (the style sheet, the scripts, the fonts, the images) without a checksum, so
  a difference in any of them, or one added or removed, checks every page; it
  executes no lesson. The checks write which pages they ran for, and why
  (`differs`, `executed`, `asset`, or `every` when there is no usable base or
  record), to `.agents/verification/checked-pages.json`. **The reproduction in a fresh clone** runs for
  the executed lessons, and compares bytes with the page this run built. Every
  other check runs as before.

### Recorded verification

A run in which every check passed is recorded in `.agents/verification/passed`,
a working file that Git ignores, together with the fingerprint of the content
it verified. Any change to a file that Git does not ignore makes the record
stale, and a failing run removes it.

The record names the tier of the run (`tier: full`, `base`, or `targeted`)
and, with a base, where the base came from (`base: run <id>`, or the
directory) and the selection. `./scripts/verify.sh --reuse` skips the run
when the record of a full run matches the current content exactly, and says
so; `./scripts/verify.sh --reuse --targeted` takes a record of a full or base
run for the content, and a record of a targeted run only after it has
retrieved the current base and recomputed the selection and both match the
record (main may have advanced); otherwise it runs the targeted run. `review-feature.sh`, `apply-triage.sh`, and
`finish-feature.sh` call it that way, so in a feature the checks run once per
version of the content instead of once per step: the agent verifies its final
result in the tier the change needs, and the scripts that follow reuse that
pass and record the tier. Plain `./scripts/verify.sh` always runs every check.

Two limits:

- The fingerprint does not cover files that Git ignores. A check that depends
  on ignored state, such as an installed dependency or a build cache, is not
  run again when only that state changed. CI runs every check on a clean
  checkout.
- A run inside an agent session counts like any other. The implementer and
  the triage implementer run the verification after their last change, and
  the review, `apply-triage.sh`, and the commit that follow reuse that pass.
  An agent could write the record instead of running the checks; that is
  accepted, because CI runs every check on a clean checkout, and
  `publish-feature.sh` and a ruleset on `main` make it the gate before a
  merge.

A record made without the workflow self-tests does not stand in for a run that
needs them, such as `--reuse --all`.

### References in the documentation

`./scripts/check-docs.sh` checks that the tracked Markdown files name files
that exist: every relative link (inline, with or without a title, and the
definition of a reference link; also one that leaves the repository), and
every path in backticks that starts with
a tracked top-level directory and names a `.md`, `.sh`, `.conf`, `.json`,
`.yml`, or `.yaml` file. It does not check anchors or external links, it
skips a path with a placeholder and a path that Git ignores, and it does not
read links that are shown as an example in a fenced code block or in inline
code. Name the files
that come later, or a directory that will hold them, after `--later`:

```text
docs-references: ./scripts/check-docs.sh --later docs/PLANNING_APPROVAL.md docs/changes
```

The template has such a line in its own `scripts/verify.conf`. It catches a
document that one change still names after another change removed it.

### Workflow self-tests

The tests of the workflow scripts (`tests/*-test.sh`) are declared separately,
in `scripts/verify-workflow.conf` (ADR 005). They test the workflow, not the
site, the Python package, or the proofs, so a change can break them only by
touching a workflow file. That file names those files in its `paths:` entry,
as Git pathspecs. `scripts/` is guarded as a whole, except the files excluded
there because no self-test reads them: `scripts/verify.conf` and the
project's own check scripts. Adding a check to `scripts/verify.conf`
therefore does not start the self-tests. Exclude a new project script there
when no self-test reads it.

`./scripts/verify.sh` runs the self-tests only when one of those files differs
from the base branch (`origin/main`, or `main`), counting uncommitted and
untracked files, or when it cannot tell, for example outside a Git repository.
Otherwise the summary reports them as `SKIP`. `./scripts/verify.sh --all`
always runs them, and CI uses it, so every pull request runs the self-tests.

The self-tests start `jq`, `git`, and `bash` thousands of times. On an Apple
Silicon Mac an x86_64 `jq`, such as the one Anaconda installs, runs under
Rosetta and roughly doubles their duration; `file "$(command -v jq)"` shows
which one is first on your `PATH`.

## Configuring agents

`.agents/agents.conf` assigns a provider and model to each workflow role, one
per line:

```text
<role>: <provider> <model>
```

| Role | Used by |
|---|---|
| `project-grill`, `project-planner` | `start-planning.sh` |
| `planning-reviewer` | reserved for planning review |
| `implementer` | `start-feature.sh` |
| `reviewer` | `review-feature.sh` |
| `triage` | `triage-review.sh` |
| `triage-implementer` | `apply-triage.sh` |

Supported providers are `codex` and `claude`. Set each model to one your
account supports, and use a different provider for a reviewing role than for
the role whose work it reviews.

Every workflow script accepts `--agent <agent>` and `--model <model>` to
override the configuration for one run. Overriding the provider requires a
model as well. The model is always passed to the provider, for Claude as well
as Codex, and is never replaced: an unknown provider, missing CLI, missing
model, or malformed configuration fails before the script creates a branch,
worktree, or file, and a model the provider rejects fails the run.

Agents run with one of three permission profiles. The profile follows from
the role and from how the script is run, not from the provider or model: a
reviewing role is always read-only; a writing role gets `write`, or
`unattended` when you run the step with `--unattended`, as described under
"Running feature steps without questions".

- `write`: an interactive session that may modify its worktree and use the
  network, for example to install dependencies and run builds. Anything beyond
  that needs your permission. Claude accepts edits automatically and asks you
  before it runs a shell command. Codex works without asking inside a
  workspace-write sandbox with network access and asks you when a command
  needs to leave that sandbox, for example to write outside the worktree;
  Codex has no setting that asks per command without a sandbox. Used for
  planning, implementation, and applying triage.
- `unattended`: the reach of `write` without a terminal. The session asks
  nothing and ends by itself, and the script stores its final message. What
  `write` would ask you is decided without you. Codex stays inside its
  workspace-write sandbox and is refused a command that leaves it. Claude runs
  in its `auto` permission mode, in which its own check allows or denies each
  action, and anything that would still prompt is denied. As in a read-only
  session, no MCP servers, apps, or other tools from your configuration are
  loaded, since they act outside the sandbox: Codex runs without your
  `config.toml` and with apps, browser use, and computer use disabled, and
  Claude without MCP configuration. An unattended agent runs commands on your
  machine while you are not watching: it is meant for work whose result you
  read afterwards.
- `read-only`: a non-interactive session that cannot modify files and gets no
  MCP servers, apps, or other tools from the user's configuration. Codex runs
  in a read-only sandbox without the user's `config.toml`, with apps, browser
  use, computer use, and web search disabled. Claude runs restricted: without user, project, or MCP
  configuration, with only its Read, Glob, and Grep tools, and without asking
  for any further permission. The script stores the agent's result. Used for
  review and triage.

A profile that a provider cannot enforce is an error; an agent is never started
with broader permissions instead.

## Project bootstrap workflow

Run project bootstrap from a clean checkout after recording the initial project
idea and completing `docs/repository-setup.md`:

```bash
./scripts/start-planning.sh
```

The full interface is:

```text
./scripts/start-planning.sh [name] [--description <file>] [--agent <agent>] [--model <model>]
./scripts/start-planning.sh <name> --change <file> [--grill] [--agent <agent>] [--model <model>]
```

The second form changes a planning that is already approved; see "Changing an
approved planning" below.

If you already have a project description, pass it with `--description`:

```bash
./scripts/start-planning.sh --description ~/notes/project-idea.md
```

The file may be anywhere, including outside the repository. An uncommitted
description inside the repository is the one change the clean-checkout check
allows.
The script copies it to `docs/PROJECT_DESCRIPTION.md` in the planning worktree
before the first session. Project Grill reads it first and asks only about
what it leaves unresolved. Neither planning phase may modify it, and it is
committed with the planning branch as the recorded input. A missing, empty, or
non-regular file fails before a branch or worktree is created.

Project Grill uses role `project-grill` and the planning session uses role
`project-planner`; `--agent` and `--model` override both. The optional name
defaults to `project-bootstrap`. A custom planning cycle such as:

```bash
./scripts/start-planning.sh architecture-refresh
```

creates `planning/architecture-refresh` in a sibling worktree named
`../<repository>-planning-architecture-refresh`.

The script fetches `origin/main` and creates the planning branch from that
remote ref without switching or modifying the primary checkout. It refuses a
dirty checkout, unsafe name, missing agent or prompt, unavailable base,
duplicate branch, or existing target path.

Bootstrap has two separate interactive agent sessions:

1. Project Grill reads the project context, asks only questions that materially
   affect product or technical direction, and refines
   `docs/PROJECT_REQUIREMENTS.md` in Draft state.
2. The script validates and displays the requirements. It records Approved
   status and a UTC timestamp only after explicit human confirmation.
3. A fresh project-planner session consumes the approved requirements and
   creates or updates `docs/architecture.md`, `docs/roadmap.md`, and only
   necessary ADRs under `docs/decisions/`.

Declining requirements approval or an agent failure stops the workflow and
leaves the planning worktree intact. Inspect or revise it there; the script
never substitutes another model or removes user work automatically.

After successful planning, continue in the planning worktree with the planning
review, revision, and approval described below. `finish-planning.sh` prints
the exact commit and push commands.

### Planning review

Before committing the planning, let an independent agent review it from the
planning worktree:

```bash
./scripts/review-planning.sh
```

It uses role `planning-reviewer` with the `read-only` profile; configure a
different provider than for `project-planner`. The reviewed file set is the
planning documents: `docs/PROJECT_DESCRIPTION.md` when present,
`docs/PROJECT_REQUIREMENTS.md`, `docs/architecture.md`, `docs/roadmap.md`, and
the ADRs in `docs/decisions/`. The script supplies their contents and their
diff against `origin/main`. The requirements must be approved first.

Each round is stored as `.agents/reviews/planning-<name>-review-NN.json` with
a generated report, in the same format as feature reviews but without an Issue.
The review covers only the planning documents, so it becomes stale when one of
them is added, changed, or deleted, and stays current otherwise
(`./scripts/check-review.sh`). A planning review is not triaged; it is
revised.

### Planning revision

Let the original project planner handle the findings of a current planning
review:

```bash
./scripts/revise-planning.sh --review .agents/reviews/planning-project-bootstrap-review-01.json
```

It uses role `project-planner` in two phases:

1. **Decide.** Read-only, the planner returns one decision per finding with a
   rationale: `ADOPT`, `REJECT`, `DEFER` (belongs to a later feature), or
   `ESCALATE` (needs a human product decision or a change to the approved
   requirements). Critical and major findings may only be adopted or
   escalated. The decisions are validated like review results, shown to you,
   and recorded only after your approval, as
   `.agents/reviews/<review>-revision.json` with a generated report.
2. **Revise.** A write session resolves exactly the adopted findings. It may
   change only `docs/architecture.md`, `docs/roadmap.md`, and direct Markdown
   ADRs. Any other change, including to the requirements, the description, or
   a review artifact, and any commit fails the run and keeps the worktree for
   inspection.

Escalated findings are listed with the next step: change the requirements
through Project Grill and approve them again, or decide that the finding does
not apply. When the write session fails, the approved decisions stay recorded;
while the review is still current, running the script again applies them
without deciding again.

After a revision the review is stale by design. Run `review-planning.sh` for
the next round, and repeat until the review passes.

### Planning approval

When the latest review round is resolved, approve the planning:

```bash
./scripts/finish-planning.sh
```

The script refuses when a required document is missing, the requirements are
not approved, there is no planning review, the latest review is stale, the
latest round has a critical or major finding, a finding of the latest round
has no revision decision, an adopted finding is not applied yet, or a finding
of the latest round is escalated. It shows every rejected, deferred, and
escalated finding of all rounds, also before a refusal. A finding escalated in
an earlier round is not resolved by a newer review alone: you confirm that it
was resolved, and the approval records that. The approval covers exactly the
reviewed planning; a document that changes while the script waits for your
answer is refused.

The approval is recorded in `docs/PLANNING_APPROVAL.md`, which is committed with
the planning: the time, the planning branch, the final review round, the
review rounds, the findings that were not adopted, and the fingerprint of the
planning documents. Use it for the planning PR description, because review
and revision files are not committed.

Whether the approval is still current:

```bash
./scripts/finish-planning.sh --check
```

exits 0 when it is and 1 when it is missing or stale. `create-feature-issue.sh
<feature-id>` refuses to create a feature Issue from a roadmap without a
current approval.

What makes the approval stale depends on the document:

| Document | Changed after the approval |
|---|---|
| `docs/PROJECT_DESCRIPTION.md`, `docs/PROJECT_REQUIREMENTS.md`, `docs/roadmap.md`, `docs/changes/` | Stale. What the product is and which features it gets changes only through a planning cycle, with a review and your approval |
| `docs/architecture.md`, `docs/decisions/` | Still current. Features keep these up to date, as the Definition of Done asks, and the feature review covers the change. `--check` lists the commits that changed them since the approval |

So a feature that describes what it built in the architecture, or records a
decision in an ADR, does not stop the next feature. The approval file itself
is not touched by a feature, so features that run side by side cannot conflict
in it. The next approval or amendment covers those updates and names their
commits in the record, with the Issue and the review of each, under "Updates
by merged work" or with the amendment. A later approval keeps the entries of
the earlier ones. Until then `--check` lists them. A feature that changes the
roadmap or the requirements is refused by `finish-feature.sh` before its
commit, with the command of the change cycle.

The script finds the approved state from the commit that last changed
`docs/PLANNING_APPROVAL.md`: the planning documents in that commit must have
the recorded fingerprint. Change that file only through `finish-planning.sh`;
after a change by hand that does not match, any difference counts as stale.

Open and merge a planning PR before creating Issues for actionable roadmap
features. The script never implements features, creates Issues, commits,
pushes, opens or merges a PR, or deploys.

## Changing an approved planning

A project changes while it runs: a new feature, a requirement that turns out
different, another technical direction. A change to the planning documents
goes through the same review and approval as the first planning, in its own
planning worktree, while feature work continues in its own worktrees.

Which route a change needs:

| Kind of change | Example | What changes | Command |
|---|---|---|---|
| Fits a feature that is not built yet | Sorting within the recipe list of F03 | Only the feature Issue | None; edit the Issue |
| New feature within the approved requirements | A shopping list the requirements already allow | Roadmap | `--change` |
| New or changed requirement | Sharing between households when one household was agreed | Requirements, and usually architecture, roadmap, and ADRs | `--change --grill` |
| Technical change only | From local storage to a server database | Architecture and an ADR that supersedes the old one | `--change` |
| Small technical amendment | One ADR gets an addition | Architecture and ADRs only | `finish-planning.sh --amend`, without a review |

Write the change down in a short file, in your own words, and start the cycle
from a clean primary checkout:

```bash
./scripts/start-planning.sh shopping-list --change ~/notes/shopping-list.md
```

The name is required. It names the branch `planning/shopping-list` and the
change request, which the script copies to `docs/changes/shopping-list.md`.
The original `docs/PROJECT_DESCRIPTION.md` stays as it is. The script requires
that the planning on `origin/main` has a current approval
(`./scripts/finish-planning.sh --check`).

Without `--grill` the requirements keep their approval and only the planner
runs. It changes what the change requires: the roadmap, the architecture, an
ADR, or several of them. With `--grill`, Project Grill runs first and asks
about the change only. When it changes the requirements, the script shows the
difference and asks for your approval before the planner starts; when it finds
that the approved requirements already allow the change, it leaves them
untouched and no approval is asked.

A change keeps what exists:

- **Feature IDs are stable.** A new feature gets the next unused ID. The
  script refuses a result that removed or renumbered a feature; a feature that
  is no longer wanted stays in the roadmap, marked as dropped.
- **Features with an Issue are not rewritten.** They may be in progress or
  delivered. A change to their behaviour is a new feature that depends on
  them.
- **ADRs are superseded, not removed.** A changed decision is a new ADR that
  names what it supersedes; the old one only gets a status line that says so.
  The script refuses a deleted ADR.

After the session, continue as after the first planning, in the planning
worktree:

```bash
./scripts/review-planning.sh
./scripts/revise-planning.sh --review .agents/reviews/planning-shopping-list-review-01.json    # when the review has findings
./scripts/finish-planning.sh
```

The reviewer receives the change request and the complete planning with the
difference against `main`, and checks the rules above. The approval records
the change request and covers it. Commit, push, and merge the planning pull
request; `cleanup-worktree.sh planning/shopping-list` then removes the
worktree and an untracked original of the change request.

A change to the requirements, the roadmap, the description, or a change
request makes the planning approval stale until the new one is merged. In
between, `create-feature-issue.sh` creates no new Issue. A feature that is
already in progress is not affected.

### A small technical amendment

A change that touches only `docs/architecture.md` and the ADRs in
`docs/decisions/`, such as amending one decision, can be approved without an
agent and without a review round. Make the change by hand on a branch
`planning/<name>` and run:

```bash
git switch -c planning/cache-adr
# edit docs/architecture.md, add or edit an ADR
./scripts/finish-planning.sh --amend "Add a cache in front of the storage."
```

The script shows the difference against `main` and asks for your approval. It
then adds the amendment to the existing `docs/PLANNING_APPROVAL.md`, with the
date, the branch, your reason, and the changed files, and updates the
fingerprint, so the approval is current again. The earlier review rounds stay
in the record, and the entry says that no independent review took place.
Commit, push, and merge as the script prints.

Your approval is the only check here, so the route is narrow. The script
refuses, and points to the change cycle, when:

- the requirements, the roadmap, the project description, or a change request
  changed;
- an ADR was deleted, since a decision is superseded, not removed;
- the planning on `main` has no current approval. An amendment does not repair
  a missing or stale approval;
- the branch does not contain the latest `main`, because the amendment is
  shown and approved against the planning as it is now;
- a required planning document is missing or empty afterwards.

## Creating a feature Issue from the roadmap

When a roadmap feature becomes active, create its Issue from its block in
`docs/roadmap.md`:

```bash
./scripts/create-feature-issue.sh F03
```

The script finds the heading that starts with the feature ID, such as
`### F03 — Sharing`, and uses everything up to the next heading of the same or
a higher level as the Issue body, unchanged. The heading becomes the title, so
the feature ID stays visible and review triage can use it for follow-up
provenance. The script shows the proposed Issue and creates it only after your
approval.

It refuses a feature ID that is missing, used for more than one heading, or
has an empty block, and it does not create a second Issue for a feature that
already has one, open or closed. When the block refers to another feature
whose Issue is still open, it warns before asking.

Create Issues one feature at a time, only for work that is about to start. An
Issue that is not a roadmap feature can still be created from a title and a
body file:

```bash
./scripts/create-feature-issue.sh "Issue title" path/to/body.md [label]
```

## Canonical feature workflow

Start with an actionable GitHub Issue. Create a detailed implementation plan
under `.agents/plans/` for non-trivial work when warranted.

From a clean primary checkout, create the feature worktree and start the
implementation agent:

```bash
./scripts/start-feature.sh 12 player-movement
```

The full interface is:

```text
./scripts/start-feature.sh <issue> [slug] [base-branch] [--agent <agent>] [--model <model>]
./scripts/start-feature.sh <issue> --resume [--agent <agent>] [--model <model>]
```

The slug names the branch and the worktree. Without one, the script derives it
from the Issue title: the title without its feature ID, in lowercase, as at
most four words joined by hyphens. The script fetches the selected remote base,
creates `feature/<issue>-<slug>` in a sibling worktree, and starts the agent
of role `implementer` inside that worktree. Untracked files in the checkout do
not matter; modified tracked files do, because they would not be part of the
new worktree. After the session it prints the worktree path and the next
commands.

The implementer verifies its result itself: it finishes every edit to a
tracked file and then runs the verification tier the change needs
(`./scripts/verify.sh --targeted` for an ordinary change; "Verification").
That pass is recorded with its tier and reused by the review that follows, so
you do not run the verification by hand between the two.

A new worktree has none of the ignored files of the primary checkout.
`start-feature.sh` therefore runs `scripts/worktree-setup.sh` in the new
worktree before the agent starts, with the path of the primary checkout as its
argument. It copies `lean/.lake/`, Lean's packages and the unpacked Mathlib
build cache of about 8 GB, from the primary checkout, so the worktree does not
fetch and unpack them again. On macOS the copy shares its disk space with the
original. Run verification once in the primary checkout to have something to
copy. The script only saves time: when it fails, `start-feature.sh` reports
that and starts the agent anyway.

### Resuming an interrupted feature

A session can end before the work is complete: a closed terminal, a usage
limit, an agent that got stuck. Continue with:

```bash
./scripts/start-feature.sh 12 --resume
```

Run it from any checkout of the repository. It finds the worktree whose branch
is `feature/12-*` and starts a new implementer session there; it creates
nothing. `--agent` and `--model` let another provider or model continue.

The new session does not have the earlier conversation. It is told to read
the state from the repository: the Issue, the plan, `git status` and the diff
against the base, the latest review or triage if the interrupted session was
resolving findings, and the handoff note.

The handoff note is `.agents/handoffs/<issue>.md`, a working file that Git
ignores. The implementer keeps it while it works, updated after each completed
part and not only at the end, with what is done, what is in progress, what
remains, and what was tried and rejected. A session that ends abruptly may not
have updated it, so the script compares it with the files: changed files that
are newer than the note are named to the new session as not described by it.
Resuming also works without a note.

After a resumed session, continue as after `start-feature.sh`: review, triage,
fixes. When the interrupted session was `apply-triage.sh`, the partial fixes
have made its review stale; resume, then run `review-feature.sh` again.

### The completion gate

A session that ends is not a feature that is complete. An implementer can
stop after two of nine plan steps and end normally, and nothing in the exit
status says so. The scripts therefore decide from what the implementer
recorded, not from the fact that it stopped.

The implementer writes a completion record before it ends, in every session:
`.agents/completion/<issue>.json`, a working file that Git ignores.

```json
{
  "schema": "completion/v2",
  "status": "partial",
  "risk": {"level": 2, "triggers": [], "rationale": "src/ and tests only"},
  "criteria": [
    {"criterion": "Recipes can be searched by ingredient",
     "gate": "implementation", "status": "met",
     "evidence": "tests/test_search.py::test_search_by_ingredient passes"},
    {"criterion": "CI passes on the published head",
     "gate": "pr_ci", "status": "pending",
     "evidence": "the checks of the pull request"}
  ],
  "remaining": ["CI on the pull request"]
}
```

`status` is `complete`, `partial`, or `blocked`. Each criterion names the gate
that clears it (ADR 020 decision 2): `implementation` (tests, the local
verification, the review), `pr_ci` (CI on exactly the published head),
`owner_approval` (the owner's approval of the exact commit, verified at the
merge gate), or `post_merge` (a measurement or an observation that exists
only after the merge). A criterion is `met`, `not_met`, `not_applicable`, or
`pending`, each with evidence; `pending` names a later gate and is never
allowed for `implementation`. `complete` means every criterion met or not
applicable and nothing remaining; a record with a pending criterion is
`partial`, and the other two need something that remains. `risk` is the
level the implementer states ("The risk level" below). A record that breaks
these rules is invalid. A record of the schema `completion/v1`, without
gates and risk, is the contract of a feature started before ADR 020 was
delivered (F130) and stays valid for it.

The gate passes when the record is valid and says `complete`, and the handoff
note lists nothing under "Remaining". The note outweighs the record: remaining
work listed there means not complete, whatever the record says.

Three readiness points are derived from the record, never stored:

- **Ready for a pull request**: every `implementation` criterion is met and
  every other unmet criterion is `pending`, with nothing under "Remaining"
  in the handoff note (pending evidence goes under "Pending"). The gate says
  `pending`. The feature is reviewed, committed, and published as a matter of
  course, without `--partial`, `--no-review`, or an owner exception; the
  commit message names the pending criteria and their gates under
  `Readiness:`, and the pull request, ready for review, names them and does
  not close the Issue.
- **Ready for merge**: additionally CI passed on the exact head, the review
  is current and covers the implementation, no major finding is open, and
  for Level 3 the owner's approval of the exact commit is verified at the
  merge gate. Pending CI blocks the merge, never the pull request.
- **Done**: every criterion met, so `complete`; the Issue closes then.
  Outstanding post-merge evidence keeps the Issue open and never blocks the
  merge.

| Script | What the gate decides there |
|---|---|
| `start-feature.sh` | After the session it says whether the Issue is complete, and offers the review only then |
| `run-feature.sh` | Goes on to the review only when the gate passes, or says `pending`, and the summary of the changes exists; otherwise it resumes the implementer with the reasons in the handoff note, at most four sessions in a run. `blocked` stops the run with status 3. The gate is asked again before every later review, because a session that repairs the verification is a session of the implementer too |
| `review-feature.sh` | Gives the record to the reviewer of the complete feature, as a claim to check |
| `finish-feature.sh` | Commits a complete record, and one whose only unmet criteria are pending (`pending`). Refuses a missing, invalid, partial, or blocked record. `--partial` commits partial work as your explicit choice |
| `publish-feature.sh` | Asks the gate again. The pull request closes the Issue only when the commit says `Completion: complete` and the gate still passes; for pending criteria it is ready for review, names them, and keeps the Issue open; otherwise it is a draft that refers to the Issue and says why it does not close it |

The record is a claim of the implementer, and an implementer can claim
`complete` wrongly. The scripts only read the status. What checks the claim
is the independent review of the complete feature: the reviewer goes through
every acceptance criterion of the Issue against the diff and the tests, and
reports a criterion that is not met, or a `met` the code does not support, as
a major finding. That is why a feature is committed only on a review of the
complete feature (see "Reviewing only the changes").

When you implemented a feature yourself, write the record yourself: it is the
statement that the Issue is done, with where to see it.

### Reviewing a feature

After the implementation agent exits, enter the feature worktree. When
independent review is required by `.agents/policies/autonomy.md`, run it before
committing so the reviewer includes the complete working-tree changes:

```bash
cd ../project-12-player-movement
./scripts/review-feature.sh 12
```

A reviewer cannot run the checks, so the review starts only when the
verification tier the change needs passes for the content under review. The
script runs `./scripts/verify.sh --reuse --targeted` first, names the failing
check when it fails, and starts no agent then. The review records that
verification passed for the reviewed tree, with the tier, the base, and the
selection. To have a
failure reviewed, for example when its cause is unclear, pass
`--unverified "<reason>"`; the review then records the reason instead.

The full interface is:

```text
./scripts/review-feature.sh <issue> [base-branch] [--agent <agent>] [--model <model>] [--changes] [--unverified "<reason>"]
```

It uses role `reviewer` with the `read-only` profile. The review is
non-interactive: the reviewer cannot modify files and has no network access, so
the script supplies the GitHub Issue and the complete diff against the base
branch, including uncommitted and untracked changes. The reviewer returns its
result as JSON and the script validates and stores it. An invalid result is
retried once and then rejected, and a reviewer that changed the working tree or
created a commit is reported as an error; in both cases no review is stored.

The diff starts where the feature left its base branch. The feature was
created from `origin/<base>`, and the local `<base>` of your checkout can be
behind it, for example after pull requests were merged on GitHub. The script
therefore uses whichever of the two shares the more recent commit with the
feature, so that work merged before the feature started never counts as the
feature's own change. You do not have to pull the base branch first.

The review script must run from the matching feature worktree and needs an
authenticated GitHub CLI. Each round writes a numbered pair of files without
overwriting earlier reviews:

```text
.agents/reviews/feature-12-player-movement-review-01.json
.agents/reviews/feature-12-player-movement-review-01.md
```

See "Review and triage data" below for the two files.

Triage an explicit review artifact with an agent independent from the
implementation:

```bash
./scripts/triage-review.sh \
  .agents/reviews/feature-12-player-movement-review-01.json
```

The full interface is:

```text
./scripts/triage-review.sh <review-json> [--agent <agent>] [--model <model>]
```

The triage agent (role `triage`) classifies every finding as:

- `FIX_NOW`: resolve before the feature proceeds. Critical and Major findings
  always use this category.
- `DEFER`: valid non-blocking work proposed as a separate follow-up Issue.
- `ACCEPT`: consciously take no action, with an explicit rationale.

The script validates the decisions before showing them: every finding is
decided exactly once, Critical and Major findings are `FIX_NOW`, and a deferred
finding has a follow-up title, action, and acceptance criteria. Invalid
decisions are retried once and then rejected. A review without findings needs
no triage agent.

The script displays the complete proposal before side effects. Only after
interactive approval does it create one GitHub Issue per `DEFER` finding and
write a persistent, uniquely named artifact such as:

```text
.agents/triage/feature-12-player-movement-review-01-triage.json
.agents/triage/feature-12-player-movement-review-01-triage.md
```

That artifact maps the source review findings to their decisions and any
created Issue numbers. After storing it, the script publishes the review and
triage reports as one comment on the source Issue, so the outcome is visible in
the Issue and, through `Closes #12`, from the pull request. The reports are
rendered from the JSON. When they exceed the size of one GitHub comment, they
are published in numbered parts rather than shortened. A failed publication
keeps the stored triage and prints the command to retry each unpublished
part. Declining the proposal creates neither an artifact nor
Issues. The source review remains unchanged. The artifact is stored only after
every follow-up Issue exists; if creating one fails, nothing is stored and a
new triage reuses the Issues created so far, which it finds by their trace
token. A re-run reuses a follow-up Issue that already exists for a finding.

Deferred follow-up Issue titles include deterministic provenance:

```text
[F02][R01][S2] Concise follow-up title
```

The script obtains the feature ID from the source Issue title and the review
round and finding ID from the review. When no feature ID is available, it falls
back to the source Issue number:

```text
[#12][R01][S2] Concise follow-up title
```

Apply the approved `FIX_NOW` set from the same feature worktree:

```bash
./scripts/apply-triage.sh \
  .agents/triage/feature-12-player-movement-review-01-triage.json
```

The full interface is:

```text
./scripts/apply-triage.sh <triage-json> [--agent <agent>] [--model <model>]
```

The helper uses role `triage-implementer`. It validates the approved artifact and source review, shows the exact
`FIX_NOW` scope, and asks for confirmation before starting a write-capable
agent. It never passes `DEFER` or `ACCEPT` findings to that agent. After the
agent exits, it verifies that the review and triage artifacts are unchanged and
verifies the result with `./scripts/verify.sh --reuse --targeted`, so a pass
that the agent recorded for exactly that content is not repeated.

The helper does not commit, push, merge, deploy, or create/close Issues. Inspect
the resulting diff and run another independent review and triage when fixes
require confirmation.

### Review and triage data

Results that an agent writes and a script consumes are JSON. Each review and
each triage is stored as two files with the same name:

- `.json` is the source of truth. The scripts read only this file.
- `.md` is a report generated from the JSON for reading. It is never parsed;
  editing it has no effect.

Both are working files for the scripts during a feature and are ignored by
Git, so `git add .` does not commit them. The record that stays is the comment
on the Issue and the follow-up Issues, each of which names its source finding.

The agent's result must match a schema in `.agents/schemas/`
(`review.schema.json`, `triage.schema.json`). The schema is passed to the
provider CLI and the script checks the result again with `jq`, including rules
a schema cannot express. For a review, the verdict must follow from the
findings: `PASS` without findings, `PASS_WITH_MINOR_FINDINGS` with only minor
or suggestion findings, and `CHANGES_REQUIRED` with at least one critical or
major finding. What a reviewer could not verify belongs in `limitations` and
does not change the verdict.

The script, not the agent, numbers the findings: `C1` (critical), `M1` (major),
`MIN1` (minor), and `S1` (suggestion). Triage decisions and follow-up Issues
refer to those identifiers. When a result is invalid, the agent is asked once
more, with the reasons for the rejection.

Stored artifacts are checked with the same rules as agent results, plus the
fields the scripts own, so editing a stored artifact cannot weaken a decision.

Documents that people maintain, such as the roadmap, requirements, and
architecture, keep Markdown as their source.

### Reviewing only the changes

Every round reviews the complete feature by default, also after a fix. That
costs a full review each time, and it is what finds a problem that an earlier
round missed: a later complete round regularly reports something in code that
did not change.

A review of changes confirms fixes. It does not establish that the Issue is
done, so **a feature is committed on a review of the complete feature**:
`finish-feature.sh` refuses when the latest round reviewed only changes, and
asks for a complete round. A round of changes is for the rounds in between.

After a small fix you can limit a round to what changed since the previous
one:

```bash
./scripts/review-feature.sh 12 --changes
```

The reviewer then receives the difference between the content that the
previous round reviewed and the current content, with the findings of that
round and what an approved triage decided about each; without one, every
finding counts as to be fixed. It checks that every finding
that was to be fixed is resolved, reviews the changed lines and what they
affect, and leaves the rest of the feature alone. The review records its
scope, its report says so at the top, and the commit message of
`finish-feature.sh` names it.

Use it when the fix is small and local. Run a complete round when the fix
touches several parts, changes behaviour beyond the finding, or when you are
not sure. The script refuses `--changes` when it cannot build on the previous
round:

- there is no previous round;
- nothing changed since it;
- the base of the branch changed, for example after merging `main`, so the
  feature differs in more than your changes;
- the content that the previous round reviewed is no longer in the object
  database.

`finish-feature.sh` accepts a review of changes only as the latest round when
it builds on exactly the content of the round before it, back to a complete
review. Otherwise it asks for a complete round.

### When a review becomes stale

Every review records a fingerprint of what it reviewed (`reviewed_tree`): the
Git tree hash of the file contents at review time, including uncommitted and
untracked changes. Review and triage artifacts, the approval requests
(`.agents/approvals/`), and ignored files are not part of it, except ignored
files Git already tracks; the plans are part of it, since a plan holds the
acceptance criteria, the risk, and the selected skills the review rests on. A review may instead cover an explicit
list of files (`reviewed_paths`); then only those files count.

The fingerprint depends on content, not on commits. Committing the reviewed
content keeps the review current; changing, adding, or deleting a covered file
makes it stale. `triage-review.sh` and `apply-triage.sh` refuse a stale review
before they start an agent. After `apply-triage.sh` changes the code, the
review is stale by design: run a new review round, complete or with
`--changes`, to confirm the fixes.

Check a review yourself with:

```bash
./scripts/check-review.sh .agents/reviews/feature-12-player-movement-review-01.json
```

It exits 0 when the review is current, 1 when it is stale, and 2 on an error.
Every script that refuses a stale review, and `check-review.sh`, first lists
the files that changed since the review, as added, modified, or deleted.

### Finishing a feature

When the latest review round is resolved, finish the feature from its
worktree:

```bash
./scripts/finish-feature.sh 12 "Implement player movement"
```

The script refuses another branch than `feature/12-*` or a tree without
changes, and a feature whose completion gate does not pass (see "The
completion gate"). It verifies the result with `./scripts/verify.sh --reuse
--targeted`, records the tier, the base, and the selection of the pass in the
commit message, and checks the latest review of the
feature: it must be current, cover the complete feature, and have no critical
or major finding. Every
review round with findings needs an approved triage that was published on the
Issue (the newest triage of that round counts), and the latest round may have
no `FIX_NOW` findings left to apply. After fixes, run a new review round first;
a passed newer round confirms the fixes of earlier rounds. A failed
publication can be repeated with `./scripts/triage-review.sh --publish
<triage-json>`.

It then stages all changes (review and triage files are ignored) and opens a
structured commit message in your editor: the summary, the Issue, the list of
changes, the completion statement with the evidence per criterion, the
verification, the review round and verdict, and `Refs #12`.
Emptying the message aborts the commit and leaves the changes staged. The
script never pushes, opens a PR, or merges.

The list of changes comes from `.agents/summaries/<issue>.md`, which the
implementer writes and keeps up to date when fixes change what the feature
does: every line that starts with `- ` is taken over. Like the manual steps
it is a working file and is not committed. Without it the message has a line
for you to fill in; an unattended commit, which nobody edits, is refused.

Work that is not complete is committed only as your explicit choice:

```bash
./scripts/finish-feature.sh 12 "Add the first part of player movement" --partial
```

The completion record has to say `partial` or `blocked` itself, with what
remains: a record that says `complete` against a handoff note with remaining
work is refused also with `--partial`, because the commit message is made
from the record. The commit message
carries `Completion: partial` with the criteria and what remains, and
`publish-feature.sh` opens a draft pull request that does not close the Issue.
`run-feature.sh` never uses the option.

A change that `.agents/policies/autonomy.md` classifies as low risk may be
finished without an independent review; the reason is recorded in the commit
message:

```bash
./scripts/finish-feature.sh 12 "Fix a typo in the README" --no-review "documentation only"
```

When the feature needs a step that only you can do, such as a repository
setting or a secret, the implementer records it in
`.agents/manual-steps/<issue>.md`. `finish-feature.sh` shows those steps before
the commit and records them in the commit message under `Manual steps:`; the
file itself is a working file and is not committed.

Then publish the feature:

```bash
./scripts/publish-feature.sh 12
```

The script pushes the branch and opens a pull request whose description is
the commit message, the manual steps, and `Closes #12`. For a pull request
that is already open it pushes and replaces the description with the current
one, since a fix round can change the manual steps. It never merges.

`Closes #12` is written only for a complete feature: the commit carries
`Completion: complete` of `finish-feature.sh`, and the completion gate, asked
again, still passes. In every other case the pull request is opened as a
draft, refers to the Issue, and says why it does not close it: the feature
was committed as partial, the gate does not pass any more, or the commit was
made without `finish-feature.sh` and has no completion statement. A draft is
marked ready when a later publish finds the feature complete, and a pull
request that was ready goes back to a draft when the work published to it is
not complete.

GitHub closes an Issue on a closing keyword (`Closes`, `Fixes`, `Resolves`,
and their forms) next to its number, in a pull request description and in the
message of a merged commit. For work that may not close the Issue the script
therefore turns such a keyword in the text it takes over into `Refs`, and it
refuses to publish, before pushing, while a commit of the branch carries one:
reword that commit, or complete the feature.

The script ends once the pull request is open and prints its address. Follow
the checks there and merge after they passed. Local verification during a
feature never runs on a clean checkout, and may run on another operating
system than CI, so a failure can appear in CI only; a pull request must not be
merged while a check fails.

- When the base branch requires a passing status check, through a ruleset or
  branch protection, GitHub refuses that merge, and the script says so.
- When it does not, the script warns: nothing but your own look at the checks
  stops the merge. `docs/repository-setup.md` describes how to add the rule,
  and `./scripts/doctor.sh` reports a `main` without one.

`--wait` keeps the script running until the checks finish, to have the result
in the terminal: all checks passed, or a non-zero exit and the advice not to
merge when one failed. After a failed check, fix the cause in the worktree,
then review, finish, and publish again.

After the merge GitHub closes the linked Issue. From the primary checkout,
remove the merged worktree and its branch:

```bash
./scripts/cleanup-worktree.sh 12
```

The script asks GitHub whether the branch's pull request is merged, so it also
works after a squash merge. It refuses an unmerged worktree, a branch with
commits after its merged pull request, and a worktree with uncommitted changes;
ignored review and triage files do not count. After removing the worktree and
the local branch it fast-forwards `main` when the primary checkout is on `main`
without modified tracked files; untracked files do not prevent that. After a
merged planning it also removes an untracked file in the primary checkout that
is identical to `docs/PROJECT_DESCRIPTION.md`, such as the original idea file. A planning worktree is cleaned with
`./scripts/cleanup-worktree.sh planning/<name>`, every merged worktree at once
with `--merged`, and an abandoned, unmerged one with `--discard` after
confirmation.

### Running feature steps without questions

The steps of a feature that ask you something, or that start an agent in your
terminal, accept `--unattended`. The step then asks nothing and ends by
itself, so a script can run one step after the other.

| Step | With `--unattended` |
|---|---|
| `start-feature.sh <issue> [--resume]` | The implementer runs with the `unattended` profile instead of in your terminal. Its final message is stored in `.agents/run/<issue>-implementer.md` in the feature worktree and shown. |
| `triage-review.sh <review-json>` | The proposed triage is approved without a question. The proposal is validated as always: a critical or major finding cannot be deferred or accepted. |
| `apply-triage.sh <triage-json>` | The fixes start without confirmation, with the `unattended` profile. The final message is stored in `.agents/run/<issue>-fixes.md` and shown. |
| `finish-feature.sh <issue> "<summary>"` | The commit message is used as it is, without an editor. Without a summary of the changes the commit is refused: nobody would write one. |

`review-feature.sh` and `publish-feature.sh` ask nothing as they are. The
planning is yours to decide: its steps refuse the option.

The option needs the working files to be ignored by Git, as the template's
`.gitignore` does with `.agents/run/`, `.agents/summaries/`, and
`.agents/completion/`; a step stops
when they are not. A project that was created from an earlier version of the
template gets the rules with `./scripts/sync-template.sh`.

An unattended agent cannot ask you anything. It is told to stop when it
needs a decision of yours, or when the work conflicts with the Issue's scope,
the architecture, or an ADR: it then records the question in the handoff note
and ends its final message with a line `BLOCKED: <reason>`. The step shows
the reason and exits with status 3, which it uses for nothing else, so a
blocked session can be told apart from a failed one. Answer in the handoff note or change the Issue, and
continue with `./scripts/start-feature.sh <issue> --resume`.

`BLOCKED` is only for a decision. The agent is told not to use it when its
own run of `./scripts/verify.sh` fails on something outside its work, does not
finish within the session, or cannot run on the machine: it reports that in
its final message and ends normally. The step that follows verifies the
result itself: `review-feature.sh` and `apply-triage.sh` exit with status 4
when the verification fails, apart from every other failure, and
`run-feature.sh` repeats and repairs it as described under "Running a feature
with one command". Common causes on your side are a tool that
is not in the `PATH` of the terminal you started from, and a verification
that takes longer than one command of an agent session may.

A triage that was approved this way says so: the artifact has
`"unattended": true`, and the report and the comment on the Issue state that
no human approved the decisions. Deferred findings still become follow-up
Issues, and accepted findings keep their rationale, so you can read
afterwards what was decided without you.

The files in `.agents/run/` are working files, ignored by Git. A Codex
session also writes its complete output to a file next to its final message,
with `.log` added to the name; it is shown when the session fails.

### Running a feature with one command

`run-feature.sh` runs the steps of a feature one after the other, from the
implementation to the open pull request, without asking anything:

```bash
./scripts/run-feature.sh 12
```

```text
./scripts/run-feature.sh <issue> [slug] [base-branch] [--implemented]
```

From the primary checkout it runs:

1. `start-feature.sh <issue> [slug] [base-branch] --unattended`: the worktree
   and the implementation. The run goes on only when the completion gate
   passes and the implementer wrote the summary of the changes. Otherwise it
   resumes the implementer, with the reasons in the handoff note, for at most
   four sessions in a run (`RUN_FEATURE_SESSIONS`).
2. `review-feature.sh`, and for a review with findings `triage-review.sh
   --unattended` and, when the triage has `FIX_NOW` findings,
   `apply-triage.sh --unattended`, followed by the next review round. This
   repeats until a review of the complete feature has no findings or its
   triage has nothing to fix.
3. `finish-feature.sh --unattended`, with the title of the Issue as the
   summary of the commit, and `publish-feature.sh`.

It uses at most five review rounds. The first round reviews the complete
feature; a round after fixes reviews only what changed since the round before
it (`review-feature.sh --changes`). That review knows what was decided about
the earlier findings, so a finding that was deferred or accepted is not
reported, triaged, and turned into a follow-up Issue again in every round.
The round that ends the run reviews the complete feature again, against the
Issue and the completion record: a feature with one fix round therefore has
three reviews, the complete feature, the fix, and the complete feature.
When the base of the branch changed between two rounds, for example because
you merged `main` into it while the run was stopped, the next round reviews
the complete feature.
The agents and models are those of the roles in `.agents/agents.conf`.

What stays with you: choosing the feature and creating its Issue, reading the
pull request, following its checks, merging, and `cleanup-worktree.sh`. The
run never merges, never pushes to `main`, and never removes a worktree.

The run decides the outcome of every step itself, from exit statuses and from
the result of the checks. What an agent writes decides one outcome only, and
only together with what it recorded:

| Outcome | How the run establishes it | What it does |
|---|---|---|
| Completed | The step exits 0 | Goes on |
| Temporary | An agent or a connection fails: a usage limit, a timeout, the network | Tries the step again, three times, with a wait that doubles from two minutes. A fix session that had already changed the content is taken up with `apply-triage.sh <triage-json> --continue`: the same findings, contract, and protections, for the session of this triage that was left unfinished, and for nothing else |
| Unstable check | The verification is repeated once, and no check failed in both runs | Records the checks and goes on, at most three times in a run |
| Failed verification | A check failed in both runs | Resumes the implementer with those checks in the handoff note, at most three times (`AGENTS.md`); a review follows. A repair session is retried like any other |
| Blocked | An agent ends with `BLOCKED:` and the handoff note holds a question under "Open questions", or the completion record says `blocked` | Stops with status 3. Without such a question there is nothing to answer: the line is ignored and the run goes on |
| Not complete | The implementer ended normally, but the completion gate does not pass: no record, an invalid one, `partial`, remaining work in the handoff note, or no summary of the changes | Resumes the implementer with the reasons in the handoff note, at most four sessions in a run. Nothing is reviewed or committed before the gate passes |

Every interruption is written to `.agents/run/<issue>-log` in the feature
worktree, one line each: the time, the step, the outcome, the reason, and
what the run did. The output of the last step is kept next to it in
`<issue>-step.log`, and that of a repeated verification in
`<issue>-verify.log`. Status 4 is kept for a failed verification: the scripts
turn an agent that happens to exit with it into an ordinary failure. `RUN_FEATURE_RETRIES`, `RUN_FEATURE_RETRY_WAIT` (seconds),
and `RUN_FEATURE_REPAIRS` change the limits for one run.

The run stops with a non-zero status, and keeps the worktree, when:

| Stop | Status |
|---|---|
| An agent needs a decision of yours, or reports a conflict with the Issue's scope, the architecture, or an ADR. Its question is in the handoff note | 3 |
| An agent or a connection keeps failing after the retries | 1 |
| The verification still fails after three repairs, or checks are unstable more than three times | 1 |
| The proposed triage is invalid, for example because it defers a critical or major finding | 1 |
| Five rounds are used and the last one still has a finding that must be fixed, or reviewed only changes | 1 |
| The implementer ended four sessions without completing the Issue | 1 |
| The completion record says `blocked` | 3 |
| The fixes changed nothing, the commit is refused, or the pull request cannot be opened after the retries | 1 |

It then says why it stopped and which command resolves it. After that, run
the same command again: `./scripts/run-feature.sh <issue>`. The run reads
where the feature stands from the worktree, so every step that is done is
skipped: a current review is not repeated, a stored triage is not made again,
and a committed feature is only published. The one thing it records itself is
that the completion gate passed, in `.agents/run/<issue>-state`. As long
as that is missing, the next run resumes the implementer, as
`start-feature.sh <issue> --resume` does. The same happens after a fixing
agent stopped for a decision of yours: the implementer reads your answer in
the handoff note and continues, and a review follows. When you completed the
implementation in a session of your own, say so with `--implemented`, and the
run continues with the review without a session of the implementer; the
completion gate has to pass for that too, so write the completion record and
the summary first. You can also take over by hand at any point:
the single scripts work on the same files.

Know what you hand over before you use it:

- An unattended agent runs commands on your machine while nobody watches.
  Codex stays inside its workspace sandbox; Claude decides with its own
  permission check. Neither gets the tools of your configuration. See
  "Configuring agents".
- Nobody approves the triage. The validation still refuses to defer or
  accept a critical or major finding, but a minor finding or a suggestion
  can be accepted or deferred wrongly. You see that in the pull request and
  on the Issue, where every finding is published with its decision, instead
  of before the fixes. Read that record before you merge.
- The completion record is the implementer's own claim. The run acts on its
  status; whether the claim holds is judged by the reviewer of the complete
  feature, and by you in the pull request, where the commit message lists
  every criterion with its evidence.
- Up to four implementer sessions and up to five review rounds, each with a
  triage and a fix session, use the
  usage limits of your agents without a moment at which you can stop them.
- The commit message is not edited: its summary is the title of the Issue
  and its list of changes is what the implementer wrote.

### The merge approval gate

A feature may update the architecture and add an ADR, and in an unattended
run nobody reads a pull request before it could be merged. The gate decides
which pull requests only you may merge. It rests on what the diff contains;
the judgement of a model is a second line, never the only one.

| Source | What it looks at | Who decides |
|---|---|---|
| Rules on the diff | ADRs, protected and sensitive paths, the verification configuration | `scripts/check-guardrails.sh` |
| Independent review | The impact of the whole feature on the architecture | The reviewer, in `architecture_impact` of its result |

The heaviest of the two decides. Your approval is needed when the diff
changes a protected path, when the reviewer classifies the impact as `major`
or `breaking`, or when there is no valid classification, as for a feature
finished with `--no-review`.

**The rules on the diff.** Always protected, in every project:

- every ADR in `docs/decisions/` that is added, changed, or removed. A new
  ADR can replace an accepted one without touching its file, so no ADR passes
  without you. A feature writes a new ADR with the status `Proposed`;
- the CI workflows, and the configuration, scripts, prompts, and schemas that
  carry out the gate;
- in `scripts/verify.conf` and `scripts/verify-workflow.conf`: a changed or
  removed line. An added check is sensitive.

What is fundamental in your project you list in
`.agents/policies/guardrails.conf`, as Git pathspecs:

```text
protected: site/_quarto.yml .github/CODEOWNERS deploy
sensitive: docs/architecture.md pyproject.toml
```

A protected path needs your approval. A sensitive path does not: it is named
to the reviewer, who has to look at it. Keep the protected list short, or
every feature waits for you. In this project the protected list is the list
of Level 3 paths of ADR 020 decision 1 ("The risk level" below), so "the
protected paths of `guardrails.conf`" and the Level 3 paths are one list;
`tests/risk-level-test.sh` shows that a change to each is reported as
protected.

Because the list is read from the base branch, the wider list of F130
applies to every pull request finished or published after F130's merge,
including features started before it (ADR 020, Status: the one stated
exception to the rule that a feature in progress finishes under the
contracts it started with). Such a feature is reported as protected when it
touches a path the list added, such as `docs/architecture.md`,
`scripts/build-site.sh`, or `.agents/skills/`; it is published without an
agent merge and needs your approval of its diff, and nothing else changes
for it. No feature is grandfathered by reading the list at its merge base.

The rules are always read from the base branch as it is now, never from the
feature itself, so a feature cannot relax the rules it is checked by; a
change to them is protected. Locally the rules of your base branch and of
`origin/<base>` both apply, whichever is behind; the script does not fetch,
and CI checks every pull request against the base on GitHub.

```bash
./scripts/check-guardrails.sh                      # this worktree against its base
./scripts/check-guardrails.sh --commits main HEAD  # two commits
```

**The reviewer's classification.** A feature review must return
`architecture_impact`: `none`, `minor`, `major`, or `breaking`, with a
rationale and the ADRs and rules it was checked against. The implementer does
not classify its own change. A review without a valid classification is
rejected.

**What happens.** `finish-feature.sh` records the decision and its reasons in
the commit message, under `Merge approval:`, with the risk level under
`Risk level:`, and `publish-feature.sh` both in the pull request, with the
head they apply to. A feature that needs your approval still gets its pull
request; `run-feature.sh` ends with `MERGE APPROVAL REQUIRED`. A Level 3
change and a requested lowering need your approval too, and so does a
feature with a completion criterion pending for your approval
(`owner_approval`), at any level.

**The risk level** (ADR 020 decision 1, `scripts/lib/risk.sh`). Every change
carries one level, the highest of three readings: the path minimum (Level 1
for documentation and process files only, Level 2 for lessons, `src/`,
tests, and other scripts, Level 3 for a protected path; the approval
requests in `.agents/approvals/` do not count), the escalation triggers
(any one gives Level 3), and the level the completion record states and the
review assesses (`architecture_impact.risk_level`). The scripts detect these
triggers on the diff against the base: a changed or removed tolerance or
budget line (Python or lesson lines naming `rtol`, `atol`, `tol`,
`tolerance`, `budget`, `approx`, `isclose`, or `allclose` with a number,
a new such Python line except in a new test, that is, in a test file
(`test_*.py` or `*_test.py`) new in the diff or below a new `def test_` in
its added block, and the entries of `scripts/lesson-budgets.conf`), a
new skip or expected
failure (in a Lean proof, a new `sorry`, `admit`, or `axiom`), a removed or
changed assertion and a removed test or test file, a changed marker such as
`same_machine` (a `parametrize` added with a new test, which only structures
new cases, is none; one added to a test that is already there, and a removed
or changed one, is), and a changed dependency manifest or lock
file. Assertions
are read in the formats of this project's checks: a Python `assert`; in a
shell test, a line that calls `fail`, exits with a failure, or calls an
`expect_` or `assert_` helper; in a Lean proof, the first line of a
`theorem`, `lemma`, or `example`, and a `#guard`, `#guard_msgs`,
`#check_failure`, or `#print axioms` command. A Lean statement changed below
its first line is left to the review. The reading is conservative: a
narrowed tolerance reads as changed too. The implementer names the triggers no script can detect (a
changed or removed published scientific claim, security, verification
guarantees), and the reviewer assesses every trigger, reporting one the
record missed as a major finding. A new lesson's own claims are no trigger.

An agent may raise the level; no agent lowers it. With a `completion/v2`
record, `finish-feature.sh` refuses a stated level below the path minimum,
refuses a stated level below a trigger reading or an assessed level unless
the approval request names that lowering, refuses a lowering of the path
minimum, and refuses a Level 3 change by trigger or assessment without its
approval request. The commit message, the review, and the pull request
record the required level, what gives it, the requested level, and the
content or head they apply to.

**The approval request**, `.agents/approvals/<issue>.md`, is committed with a
Level 3 change by trigger or assessment and with every lowering request, so
that the pull request touches a code-owned path and GitHub requires your
identity's review. It names the Issue (`Issue: #<n>`), the required level
(`Level:`, which the scripts check against their derivation), how it was
derived (`Derived from:`), and the content it was written for (`Tree:`): the
content tree, which the risk statement of the review and of the commit
prints (`content tree for the approval request`). It is the fingerprint of
the worktree without `.agents/approvals/`, with the Issue's completion record
and handoff note: the request is the vehicle of a level and of a lowering,
never part of the content it is about, so editing it leaves the content tree
unchanged and it can name the tree under review, which the reviewer compares
it with. The request is no part of the fingerprint either, so correcting it
leaves a recorded verification and a review valid; instead `finish-feature.sh`
refuses at once a request whose `Tree:` (its first word) is not the content
tree, and names the value to write, and you approve the request with the diff
at the merge. A lowering adds `Required level:`, `Requested level:`
(a trigger reading or an assessed level, never the path minimum),
`Reason:`, and `Owner's word:`, your words in the conversation that let the
agent proceed. It is a request, never an approval: no script reads it as
your decision. Until you authorize a lowering, the change keeps its required
level for the finish, the review, the triage, and the verification; a
lowering your identity has not approved for the head to be merged is redone
at the required level before the merge.

**The merge-gate verification** (ADR 020 decision 3, mechanism A). Your
approval of a Level 3 change, and your authorization of a lowering, is an
approving review of exactly the head of the pull request by a second GitHub
identity that only you hold and no agent ever uses; GitHub enforces it at
the merge through the ruleset of `main` and `.github/CODEOWNERS`. No script
accepts an agent-written assertion, a comment or review by the agent's own
login, a file, a flag, or a statement in a conversation as your approval
(`tests/merge-feature-test.sh`). An agent or a queue that merges uses

```bash
./scripts/merge-feature.sh 12
```

which applies GitHub's decision only: it merges when GitHub reports the pull
request mergeable and, for one that needs you, when the latest review of
your identity approves exactly the head. Whether it needs you is derived
from the diff against the base as well as read from the commit: a protected
path or an escalation trigger that the diff shows (`scripts/lib/risk.sh`)
needs you whatever the commit's risk lines say, since those can be written
by hand and only raise the level. The assessed level is read from the
latest review of the feature in the worktree, which must be of exactly the
head: a review that assesses Level 3 or names a trigger needs you, and so
does a review of other content, or no review when the commit does not say
that it was finished without one. A change that is Level 3 by a trigger or
an assessment, without a protected path, is refused until it commits its
approval request. Your identity is the one login that the line
`owner-identity: <login>` of `.agents/policies/guardrails.conf` of the base
names, a code owner in `.github/CODEOWNERS` other than the agent's login. No
other code owner's review counts. When the pull request touches no
code-owned path, the ruleset requires no review and GitHub reports no
review decision; your identity's approving review of the head decides then.
It merges with `--match-head-commit`, so
content pushed after the approval is never merged on it. Until your identity
exists, the gate configuration has no such line, and the script merges no
such pull request: the present practice continues, and you merge it, or tell the agent
in the conversation, naming the head commit, that it may merge it.

**In this project the CI job is not installed.** It uses the trigger
`pull_request_target`, which invariant I15 of `docs/architecture.md` rules
out; `.agents/template.conf` excludes the workflow. The gate works locally
and in every commit message and pull request. The template describes the job
as follows.

**In CI.** The workflow `Guardrails` runs the gate on the actual diff of every
pull request, with the script and the rules of the base branch and without
running code of the pull request. It fails when the diff changes a protected
path. It is a signal and not the required check, so that you can merge after
reading what it lists.

**Your approval is your own review of the head.** You approve or merge the
commit you see, so an approval never carries over to content that changed
afterwards. Until your second identity, the code-owner rule, and the
ruleset change exist (your actions, `docs/repository-setup.md`, "The
owner's identity for Level 3 approvals"), this is an agreement that the
scripts and agents keep, not a lock: the agent works with your GitHub
account and could do what you can do. With them, GitHub enforces it, and
what remains is stated in ADR 020: the agent's login, which administers the
repository, could still change the ruleset; the policy that an agent never
changes a repository setting holds it back, or a token without
administration rights makes that a lock too.

## Linking a feature plan

To add or update the plan reference in an existing Issue:

```bash
./scripts/update-issue-with-plan.sh 12 .agents/plans/12-player-movement.md
```

The helper manages one delimited plan block in the Issue body. Re-running it
updates that block instead of appending duplicates. It stores only the
repository-relative plan path; the detailed plan remains in `.agents/plans/`.

## Taking over template changes

A project is created as a copy of the template and does not receive later
template changes by itself. `scripts/sync-template.sh` takes them over:

```bash
./scripts/sync-template.sh
```

Run it from the primary checkout without uncommitted changes to tracked
files. On `main` it first creates a branch `fix/sync-template-<commit>`. It
fetches the template named in `.agents/template.conf`, lists the template's
commits since the version the project has, and applies them to the files
listed under `paths:` in the template's version of that file. Every other
file is the project's own and is never touched. To keep a listed file as the
project's own, add `:(exclude)<path>` to `paths:` in the project's
`.agents/template.conf`; the project's exclusions always apply.

| Situation | What the script does |
|---|---|
| The project did not change the file | Replaces it with the template's version |
| Both changed it | Merges the two; a conflict is marked in the file and reported |
| The template added the file | Adds it |
| The template removed the file | Reports it; the project decides whether to delete it |
| The template changed a file the project deleted | Reports it and leaves it out |
| The template changed only the executable bit | Applies it to the project's file |
| The file, or a directory above it, is a symbolic link in the project | Reports it and writes nothing |

The script records the template commit the project now has in
`.agents/template.conf` and prints the next steps: resolve conflicts, run
`./scripts/verify.sh --all`, commit, and open a pull request. It never commits
or pushes, and exits 1 when it left a conflict. Running it again when nothing
changed in the template reports that the project is up to date.

A project that has no recorded version yet, because it was created before
this script existed or has never been synced, gets one on the first run: the
script uses the template commit that has the most files identical to the
project's, and says which one. When several versions match equally well and
differ in template files, it does not guess, because the newest would skip a
template change to a file the project changed too: it lists them and asks for
`--from <commit>`, where the oldest is the safe choice. A project that is
already up to date only gets its version recorded. `--to <ref>` selects
another template version than its default branch, and
`--template <url-or-path>` another location, for example a fork; that location
is recorded, so the next sync continues from it.

A template change can need a decision in the project, such as a new check or
a changed step. Read the listed commits before merging the result; the sync
only takes over files.

## Lifecycle

The complete lifecycle, with diagrams and a reference table per step, is in
`docs/workflow.md`.
