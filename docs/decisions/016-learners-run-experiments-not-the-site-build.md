# ADR 016: Learners run a lesson's experiment; nobody is instructed to rebuild the website

## Status

Proposed with the planning of the change cycle
`pbc-planning-change-four-workstreams`; accepted when that planning is
approved. Implements requirements decision 33 ("Learner instructions
without a website build") and the amended "UX expectations" and "Runtime
and deployment constraints" of the requirements. F117 (Issue 202) delivered it:
the experiment entry points, the footer by kind, the setup page, and the
experiment check; the full-run measurement follows the merge
(`docs/release-readiness.md`).

Supersedes the learner-facing reproduction contract: the consequence of
[ADR 002](002-regenerate-artifacts-and-display-by-reference.md) that the
"Reproduce this" commands run the same files the build ran becomes a
statement about the experiment entry point of decision 2; the setup-page
rule of F39 (the required commands of the page equal those of `ci.yml`)
and the architecture's flow "Learner reproduces a lesson" are replaced by
decisions 1 and 5. Amends
[ADR 014](014-verification-proportional-to-the-change.md) decision 9 in
name only: the provenance region it regenerates on every build is the
section of decision 3. The one verification entry point of
[ADR 003](003-single-verification-entry-point-and-ci-budget.md) stands
for maintainers, agents, and CI.

Date: 2026-10-15

## Context

The published setup page ("Set up and run", `site/reproduce.qmd`) opens
with "One command rebuilds all of it" and lists, as the required setup of
every reader, Git, uv, elan, jq, the browser build, and
`./scripts/verify.sh`; a test keeps those commands equal to the commands
of CI. The "Reproduce this" section of every lesson lists a clone, a
checkout, `uv sync --locked`, for a Lean lesson `./scripts/check-lean.sh`,
the tests of the lesson's code, and `quarto render` of the page; a check
runs those commands in a fresh clone and compares the regenerated page
with the published one byte for byte within 30 seconds. The README's
"Build and verify", the development guide ("preview the site with live
reload"), the authoring guide, and the lesson template give the same
instructions. The project owner decided on 2026-10-14 to remove every
instruction to rebuild or preview the website from maintained
documentation, not to relocate it, and to give readers what they need to
read lessons, run and modify the Python experiments, and optionally check
the Lean proofs.

Every published lesson draws its figures and computes its tables in the
cells of its page, calling the tested functions of `src/pbc`. No lesson
has a runnable experiment outside its page: the only way to regenerate a
figure today is to render the page, which needs Quarto and, through the
checks, the whole toolchain. Agent lessons are verified by replaying a
recorded run without credentials (ADR 004); a live run needs a provider
account and costs money.

## Decision

1. **Three learner activities, none of which builds the site.** The public
   setup page is organised by what a reader wants to do: run an experiment
   (Git and uv; the project's pinned Python dependencies alone, decision
   2), check a proof or work on
   an exercise (in addition, elan with the pinned Lean toolchain and the
   Mathlib build cache, through `./scripts/check-lean.sh` or `lake build`),
   and replay or run an agent lesson (replay needs nothing beyond the
   Python environment; a live run needs the documented credential and
   optional dependency, is marked as such, and is never what ordinary
   reproduction does). The full verification pipeline, Quarto rendering,
   and the website preview are not learner setup. No maintained document
   for readers, contributors, authors, or developers instructs anyone to
   rebuild or preview the website locally, and the instruction is not
   relocated: a contributor who changes a lesson runs the targeted checks
   that the development and authoring guides name (the unit tests, the
   lesson source checks, the experiment of the lesson), and CI builds and
   validates the site. The targeted local checks that the requirements'
   runtime constraints permit for the change types the decision record
   of decision 35 lists (rendering, templates, navigation, site
   configuration), which is the full `./scripts/verify.sh` run of ADR
   017 decision 7, are a verification an agent or developer performs
   for those change types and not the instructional rebuild or preview
   walkthrough that this decision and requirements decision 33 remove;
   a guide may name that run as a verification tier without instructing
   anyone to rebuild or preview the website as the way to read, run, or
   check a lesson. Technical references to the internal build (the
   script names, what CI runs, the verification record) may remain where
   a document describes the architecture or evidence.
2. **Every lesson declares a runnable experiment entry point.** A module or
   script in the repository that calls the lesson's authoritative
   implementation in `src/pbc`, regenerates the lesson's numerical
   results and figure files into a directory the learner names, and
   writes the numbers the page shows. The page's cells call the same
   functions, so no scientific logic exists twice. **One encoder produces
   the figure file of the page and of the learner's directory.** Today
   every lesson figure is emitted by `plt.show()` in a cell and captured
   by the Jupyter inline backend into `index_files/figure-html`; no helper
   of the repository writes a figure file, and a `savefig` in an entry
   point and the inline backend's capture of the same figure need not
   agree byte for byte (bounding box, dpi, metadata). The contract
   therefore gives every figure one figure-writing function in the
   lesson's course-package module under `src/pbc` (the location fixed
   below), with fixed Matplotlib settings and no metadata (the
   deterministic figure output ADR 002 already requires), that the entry
   point calls to write the file into the learner's directory and that the
   page's cell calls at build time to write the same file and show it as
   the cell's output, so that the figure file of the built page holds the
   writer's bytes and not a second encoding. The display form of ADR 002
   is unchanged (the figure is produced by an executed cell during the
   build, and no image file is committed), and the preview of F63 keeps
   finding the figure of the cell. If a figure kind cannot reach byte
   identity across the two paths, the check of decision 4 compares that
   kind as an image at the page's rendered size, together with the
   numbers at displayed precision, and the feature's record documents the
   difference per figure kind; the comparison of the numbers is never
   weakened. The entry point is an
   input of the lesson's digest and has a unit test. The entry point and
   the figure-writing functions are modules of the lesson's course package
   under `src/pbc`, imported by the page's cells; the lesson directory
   holds at most a thin runner that imports them and holds no scientific
   logic. That is the location ADR 014 decision 1 follows as implemented:
   the digest follows the imports of the page's cells transitively through
   `pbc` modules only, and a module in the lesson directory is hashed as
   content without its own imports being followed, so a `src/pbc` module
   imported only by such a module would be outside the digest. If F117
   chooses the lesson directory for the entry point itself, it first
   extends the digest to follow the imports of a module in the lesson
   directory, with a test that a changed `pbc` module imported only by the
   entry point changes the lesson's digest.
   F117 fixes the calling convention once, for every
   lesson kind; a lesson without an entry point fails the lesson source
   checks once the switch of decision 3 is made. **The Lean kind is the
   one exception to the location rule, fixed here:** for a lesson whose
   methods are Lean only, the entry point is the proof check
   (`./scripts/check-lean.sh`, or `lake build` of the lesson's modules),
   which is a shell script and not a `src/pbc` module; its digest inputs
   are the displayed Lean modules (`lean-modules`), the toolchain, and
   the manifest that ADR 014 decision 1 already follows; its test is the
   Lean build together with the exercise pairing check of ADR 011
   decision 3, and no separate unit test is written for it; the lesson
   source check accepts that declaration for such a lesson. A Lean lesson
   that also computes a figure additionally declares the figure-writing
   function under `src/pbc`, with its unit test, as every other kind does. **The learner installs
   and runs the project dependencies, not the verification environment:**
   `pyproject.toml` installs its `dev` dependency group by default, and
   that group is the site generator, the Jupyter kernel, the browser, the
   accessibility scan, and the quality tools, none of which an experiment
   needs. The learner's install command is `uv sync --locked --no-dev`
   and the entry point runs under `uv run --locked --no-dev`, so that the
   locked versions of the project dependencies (NumPy, SciPy, Matplotlib,
   and what `src/pbc` imports) are installed and nothing of the `dev`
   group is. If a lesson kind needs a dependency beyond the project's,
   F117 declares a learner dependency group or extra for it, as the
   `openai` extra already does for the live agent run, named by the
   footer of that kind; the contract decides this once, in the
   entry-point contract, and never by installing the `dev` group. The
   proof-checking path of decision 1 adds the Lean toolchain and nothing
   of the `dev` group either.
3. **The footer names the activity, not the render.** The last section of
   a lesson keeps its identifier `reproduce-this`, so that every anchor
   and bookmark stays valid, and its place; its heading and content
   become, by lesson kind: "Run this experiment" for simulation and
   measured-data lessons, "Replay this experiment" for agent lessons (with
   the live run as a separate, labelled, optional block that names its
   credential and dependency), and "Check this proof" for Lean lessons. It
   lists the repository clone or download, the commit the page was built
   from with links to the files at that commit, the command that installs
   the pinned Python environment, the exact experiment command or
   commands, the source paths, and what the command regenerates. It lists
   no render and no preview command.
4. **The experiment is verified, under the selection rule of the page
   reproduction.** A check runs the experiment commands of a lesson in a
   fresh clone, with the learner's commands of decision 2, and compares
   the regenerated figure files byte for byte with the figure files of
   the built page (the bytes agree because the one figure-writing
   function of decision 2 produces both; a figure kind that the feature's
   record documents as unable to reach byte identity is compared as an
   image at the page's rendered size), and the regenerated numbers with
   the page's at displayed precision; the 30-second budget of a lesson applies to the
   run of its entry point. **The learner's environment of the check is
   one per run, never the checkout's.** The check creates one learner
   environment per verification run with `uv sync --locked --no-dev` in
   the fresh clone, outside the per-lesson budget, and runs every
   selected lesson's entry point against that environment without a
   further sync (`uv run --no-sync` against it, or the equivalent); it
   never runs the learner's commands against the environment of the
   checkout, because `uv run --no-dev` syncs the environment it runs in
   to the project dependencies alone and would remove the `dev` group
   (Quarto, pytest, Playwright) from the verification in progress. The
   assertion that the learner's environment holds nothing of the `dev`
   group belongs to the setup-page test of decision 5, not to this
   check. Which lessons it runs for is decided exactly as for the page
   reproduction (ADR 014 decision 3, the reproduction row; invariant
   I26): every lesson on a full run and on a run without options, and on
   a selective run the lessons the run executed, which are the lessons
   the selection named. Every comparison is made against the figures and
   numbers this run computed on the machine of the comparison, never
   against a result of the base; so the check joins the group `build`,
   the same-machine group of ADR 012 decision 4, as tests marked
   `same_machine` inside the existing check `site-checks-reproduction`
   of `scripts/verify.conf`, and reads
   the selection from the one place `./scripts/verify.sh` writes it, as
   that check does. The rule of ADR 012 decision 4 applies to it: the
   check of the group `build` holds exactly the tests marked
   `same_machine`, and no new group and no new check is declared,
   because every group must be run by exactly one job (ADR 012 decision
   2) and `tests/integration/test_site_check_division.py` requires every
   test of `tests/e2e` to be run by exactly one `site-checks-*` check
   and admits no new check name, so a second check of the group would
   run the tests twice or fail that test. The entry point
   is an input of the lesson's digest (decision 2), so a changed entry
   point selects its lesson and the check runs for it. On `main`, every
   lesson's experiment is checked on every push while ADR 014 decision 4
   stands; if ADR 017 is accepted, an inherited lesson's experiment
   evidence is inherited with its result under the validity conditions
   of ADR 017 decision 1 and is re-established when the lesson next
   executes (ADR 017 decision 4). The internal checks that render pages
   (the site build, the determinism build, the reproduction of the page
   in a fresh clone) stay internal: this record removes none of them.
   Whether the page reproduction remains beside the experiment check is
   a question of coverage for the audit of F118 (ADR 017), not for this
   record. **The switch that adds the check to `scripts/verify.conf` is
   gated on the full-run budget** (see "Consequences"): it waits for the
   owner's interim full-run timeout under unresolved question 10 of the
   requirements, decided on F118's record, or for the consolidation of
   F119, whichever comes first; the entry points, their unit tests, and
   the setup page are delivered before it, behind the unchanged footer.
5. **The setup page is tested by what it says and by what it installs.**
   The commands of the Python-only path are exercised by a test that
   performs them from the page's text in a fresh clone and then asserts
   two things about the environment they produced: that it holds no
   package of the `dev` group (no Quarto, no Jupyter kernel, no browser
   or accessibility package, no workflow or quality tool), and that at
   least one experiment of each non-Lean lesson kind the contract
   defines (a simulation, an analysis of a committed data sample, an
   agent replay) runs to completion in it and regenerates
   its figures and numbers. Grepping the page for forbidden tool names is
   not that test and does not replace it. The proof-checking commands
   are the ones `./scripts/check-lean.sh` runs, and they install nothing
   of the `dev` group; the live-agent and coding-agent commands stay
   marked "not verified" and name what they need. The equality of the
   page's commands with those of `ci.yml` is dropped: the preparation of
   a CI runner is the maintainers' contract (architecture, "Toolchains
   and pinning"), not the learner's setup.
6. **History stays history.** Decision records, completion records,
   release-readiness measurements, and feature plans that describe the
   earlier instructions are not rewritten; the superseded statements are
   marked where a current document would otherwise mislead.

## Alternatives considered

- **Relocate the rebuild instructions to the contributor documentation.**
  Rejected by the owner's decision.
- **Keep `quarto render` as an optional advanced step on the setup page.**
  Rejected: it brings back the toolchain for a learner activity, and the
  decision is to remove, not to demote.
- **Notebooks with stored outputs as the entry point.** Rejected: ADR 002
  rejects stored outputs because they drift; a module or script is
  runnable, testable, importable, and diffable, and a notebook can be
  generated from it later without becoming a source.
- **The page as the entry point** (render it to run the experiment).
  Rejected: that is the state this record replaces.
- **Rename the section identifier to match the heading.** Rejected: the
  anchor is part of every bookmark and of the links of other pages; the
  heading is what the reader sees.

## Consequences

- Positive: the learner's setup is Git and uv, and the environment they
  install is the project's dependencies alone (`--no-dev`); results and
  figures are regenerated without Quarto, a browser, Lean, or jq; the
  experiment code is importable and modifiable, which is what the
  requirements ask a learner to be able to do.
- The experiment check costs about what the page reproduction costs,
  less the render: one more run of the selected lessons' entry points in
  a fresh clone on the machine of the comparison, never of the unchanged
  lessons on a selective run. **On the full-run `build` job that is a
  fifth execution of every lesson's science** beside the site build, the
  determinism build, the preview test's build, and the page
  reproduction, all of which stay until F118 rules. Its expected cost,
  derived and not measured: the page reproduction of thirty-two lessons
  took about 11 min 13 s in one fast full run (change request, "CI
  measurements to reconcile"), execution and render together; the
  experiment check repeats the execution of each lesson and not the
  render, so it adds at most that much, and less by the share of the
  render, to a `build` job measured at 21 min 07 s to 31 min 15 s with
  thirty-two lessons against the 35-minute planning budget of ADR 014
  decision 7 and the 45-minute timeout. On the slower measured runs the
  sum can exceed the planning budget, and a `build` job that exceeds the
  timeout publishes nothing (ADR 014 decision 7, invariant I26).
  Therefore the switch that adds the check to `scripts/verify.conf`
  waits for the owner's interim full-run timeout (unresolved question
  10, on F118's record) or for F119's consolidation, F117 measures one
  full run on `main` after the switch against the approved timeout and
  records it in `docs/release-readiness.md`, and F118 measures the
  per-lesson cost of the check in its decomposition. Whether the
  experiment check replaces the render step of the page reproduction is
  not decided here: it is F118's coverage question, and no check is
  removed before coverage evidence (requirements decision 35, ADR 017
  decision 8).
- Every published lesson gains an entry point and its test: thirty-two at
  this planning, delivered by F117 in reviewed steps behind the unchanged
  footer, with the heading and the check switching when every lesson has
  one and the full-run gate above is met; new lessons inherit it through
  the template. A figure that moves from the inline backend's capture to
  its figure-writing function is re-encoded once by the writer, which
  changes the bytes of its file and not its content: the determinism and
  reproduction checks compare a build with itself and pass, the page's
  text and numbers are unchanged, and the pull request of that step shows
  the figure unchanged by an image comparison at the page's rendered
  size.
- The reproducibility guarantee changes shape, not strength: "the
  experiment regenerates the published figures and numbers" is checked on
  every lesson; "the page regenerates byte for byte" stays checked
  internally until F118 decides otherwise by coverage.
- The setup page's commands no longer equal CI's; what CI installs is
  documented as technical reference in the deployment and development
  guides.
- F117 touches the footer cell of every lesson page; the editorial pilot
  F115 edits mechanics lessons 01 to 05 at about the same time. The two
  features are sequenced or rebased by their plans; neither changes a
  scientific claim.

### Addendum to decision 2 (Issue #524, 2026-11-14): the provenance record of a declared figure

Decision 2 gives the figure-writing function fixed Matplotlib settings and
"no metadata". On 2026-11-14 the owner decided, in the design review of the
figure-provenance pilot (F172, Issue #524), that one exception is allowed
and asked for it to be stated here so that it is not reopened:

- **A declared figure carries a fixed, deterministic provenance record.**
  A figure whose cell declares its status, dataset, and processing
  (`Experiment.figure(provenance=)`) is written by the same one encoder
  with text chunks of the PNG that are a function of the declaration and
  the dataset's card alone: the figure's identity, status, dataset,
  artifact, licence, credit, the line painted on the image, attribution,
  and processing.
- **No timestamps and no machine-dependent fields.** The record holds no
  date, software version, author, copyright, host, or path; two encodes of
  the same figure are byte-identical, and the page's file equals the
  experiment's.
- **Every other figure is unchanged.** A figure without a declaration is
  encoded as before, with no metadata, byte for byte.

The pilot declares three figures (AST8, MAT6, the RLC lab); a wider rollout
is F173's. The other decisions keep their text.
