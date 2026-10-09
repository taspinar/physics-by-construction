# Project map

What each part of the repository is for. The product is described in
`docs/architecture.md`; the development workflow that connects the scripts is
in `docs/workflow.md`.

## Product

| Path | Purpose |
|---|---|
| `site/` | The website source, a Quarto project. `_quarto.yml` configures it, including the public address in `website.site-url`; `_filters/` holds its Pandoc Lua filters; `assets/` its stylesheet, self-hosted font, and Lean syntax definition |
| `site/lessons/<strand>/<nn>-<slug>/index.qmd` | One lesson per directory, in the format of `docs/authoring.md`. An agent lesson may also hold its replay fixture `replay.json`; nothing else is committed there |
| `site/path/index.qmd` | The learning path page, generated from the lesson front matter when the site is built |
| `site/_site/` | The built site. Written by `scripts/build-site.sh`, ignored by Git |
| `src/pbc/` | The Python package with the reusable lesson code: `mechanics/` for the mechanics course, `authoring/` for the helpers pages use to show Python and Lean code by reference, to write "Reproduce this", and to generate the learning path page and lesson headers; `authoring/path.py` defines the strands and the difficulty scale |
| `lean/` | The Lean project: `lean-toolchain`, `lakefile.toml`, and `lake-manifest.json` pin Lean and Mathlib; proofs live in `PhysicsByConstruction/`; `AxiomAudit.lean` is the audit run by `scripts/check-lean.sh` |
| `pyproject.toml`, `uv.lock`, `.python-version` | The Python toolchain pins, including Quarto and the browser for the site checks |
| `LICENSE`, `LICENSE-CONTENT` | MIT for code, CC BY 4.0 for lesson text and figures |

## Verification

| Path | Purpose |
|---|---|
| `scripts/verify.sh` | Runs the checks in `scripts/verify.conf`, and the workflow self-tests when a workflow file changed or with `--all`; records a pass and skips a repeated run with `--reuse`; used by humans, agents, and CI |
| `scripts/verify.conf` | The required verification checks of the project |
| `scripts/verify-workflow.conf` | The self-tests of the workflow scripts and the workflow files they guard |
| `scripts/preflight.sh` | First check: reports every missing prerequisite of the one-time setup with a fix hint |
| `scripts/check-lean.sh` | Builds every Lean module against Mathlib from its build cache, fails on `sorry` and project axioms, and records what compiled the proofs for the pages that show them |
| `scripts/build-site.sh` | Builds the site with Quarto; fails on a failing cell or an equation that is not MathML |
| `scripts/check-determinism.sh` | Builds the site a second time and requires byte-identical output |
| `scripts/doctor.sh` | Read-only check of the local prerequisites, including those of the development workflow |
| `scripts/lib/prerequisites.sh`, `scripts/lib/check_browser.py` | The prerequisite checks shared by `preflight.sh` and `doctor.sh` |
| `tests/unit/` | pytest: behaviour of `src/pbc` |
| `tests/integration/` | pytest: every check fails on a violating input; a lesson made from the template passes; boundaries of the CI workflow |
| `tests/lessons/` | pytest: the required checks on the lesson sources |
| `tests/e2e/` | pytest with a headless browser: the required checks on the built site and its lesson pages |
| `tests/support/` | Helpers of the tests: the lesson source checks, the built-site checks, the sub-path test server, the `verify.conf` reader |
| `tests/*.sh` | Shell tests of the workflow scripts, of `doctor.sh`, and of `preflight.sh` |
| `.github/workflows/ci.yml` | CI: prepares the runner, runs `./scripts/verify.sh --all`, and on `main` deploys the verified site |
| `.github/dependabot.yml` | Update proposals for Python packages and GitHub Actions |
| `.github/ISSUE_TEMPLATE/lesson-proposal.yml` | The Issue form for lesson proposals |

## Rules and configuration

| Path | Purpose |
|---|---|
| `AGENTS.md` | Durable working rules for every agent: source precedence, Definition of Done, boundaries, branch policy |
| `.agents/agents.conf` | Provider and model per workflow role |
| `.agents/template.conf` | Where the workflow comes from, which files belong to it, and the template version the project has |
| `.agents/policies/` | Risk-based autonomy, execution limits, recovery, conflict resolution, and tool permissions |
| `.github/` | CI workflow, Dependabot configuration, Issue templates, PR template, and code owners |
| `CONTRIBUTING.md`, `SECURITY.md` | How to contribute and how to handle security-sensitive findings |

## Project documents

| Path | Purpose | Written by |
|---|---|---|
| `README.md` | What the project is and how to build it | You |
| `docs/PROJECT_DESCRIPTION.md` | Your original project idea, unchanged | `start-planning.sh --description` |
| `docs/changes/` | One change request per later change to the approved planning, unchanged | `start-planning.sh <name> --change` |
| `docs/PROJECT_REQUIREMENTS.md` | The requirements you approved | Project Grill, approved by you |
| `docs/architecture.md` | The current system design | Project planner |
| `docs/roadmap.md` | Roadmap features with stable IDs (F01, F02, …) | Project planner |
| `docs/decisions/` | Architecture decision records | Project planner |
| `docs/PLANNING_APPROVAL.md` | Your approval of the reviewed planning, with its fingerprint | `finish-planning.sh` |
| `docs/repository-setup.md` | GitHub settings for a new repository | You |
| `docs/development.md` | The one-time setup, verification, and every workflow command | Template and you |
| `docs/authoring.md`, `docs/lesson-template.qmd` | How to write a lesson, and the page a new lesson starts from | You |
| `docs/content-proposals.md` | How a lesson is proposed, assessed, drafted, and merged, for contributors and the maintainer | You |
| `docs/workflow.md` | The workflow in flow, artifact, and reference views | Template |
| `docs/example.md` | A complete run with a sample project | Template |
| `docs/agentic-workflow.md` | Principles: persistent state, roadmap versus Issues, plans versus Issues | Template |
| `docs/evaluation.md` | Review criteria, finding severities, and the testing principle | Template |
| `docs/deployment.md`, `docs/operations.md` | Deployment and operations of the project | You |
| `docs/release-readiness.md` | The record of the MVP release checks that CI cannot make | You |

## Workflow scripts

| Script | Purpose |
|---|---|
| `scripts/start-planning.sh` | Project Grill, requirements approval, and project planning in a planning worktree |
| `scripts/review-planning.sh` | Independent, read-only review of the planning documents |
| `scripts/revise-planning.sh` | The planner's decision per planning finding, then the revision |
| `scripts/finish-planning.sh` | Checks and records your approval of the planning; `--check` tests it |
| `scripts/create-feature-issue.sh` | Creates the Issue of one roadmap feature |
| `scripts/start-feature.sh` | Creates the feature worktree and starts the implementer |
| `scripts/review-feature.sh` | Independent, read-only review of the complete feature diff, or with `--changes` of what changed since the previous round |
| `scripts/triage-review.sh` | Classifies review findings, creates follow-up Issues, and publishes the reports on the Issue |
| `scripts/apply-triage.sh` | Lets an implementer resolve only the `FIX_NOW` findings |
| `scripts/finish-feature.sh` | Checks the feature and creates the commit |
| `scripts/publish-feature.sh` | Pushes the feature branch and opens its pull request; with `--wait` stays until CI finishes; never merges |
| `scripts/check-review.sh` | Reports whether a review still matches what it covers |
| `scripts/update-issue-with-plan.sh` | Links an optional feature plan to its Issue |
| `scripts/cleanup-worktree.sh` | Removes a merged worktree and its branch and updates `main` |
| `scripts/sync-template.sh` | Takes over the template's changes since the version the project has; never commits |
| `scripts/worktree-setup.sh` | Prepares a new feature worktree before the agent starts: copies `lean/.lake/` from the primary checkout |

## Script libraries

| Path | Purpose |
|---|---|
| `scripts/lib/agent.sh` | Role configuration, `--agent`/`--model` overrides, and starting agents with the `write` or `read-only` profile |
| `scripts/lib/review-data.sh` | Validation and rendering of review, triage, and revision JSON |
| `scripts/lib/review-run.sh` | Running a read-only agent with one retry, and storing a review |
| `scripts/lib/github.sh` | Questions about the repository on GitHub, such as whether a branch requires a status check |
| `scripts/lib/fingerprint.sh` | Content fingerprints of a working tree or a set of files |
| `scripts/lib/verification.sh` | The record of the last passed verification of a working tree |
| `scripts/lib/scope.sh` | File-scope enforcement for write sessions |
| `scripts/lib/planning.sh` | The planning scope and the planning approval check |

## Agent contracts and schemas

| Path | Used by |
|---|---|
| `.agents/prompts/project-grill.md` | Project Grill in `start-planning.sh` |
| `.agents/prompts/project-planner.md` | The project planner in `start-planning.sh` |
| `.agents/prompts/planning-reviewer.md` | `review-planning.sh` |
| `.agents/prompts/planning-reviser.md` | `revise-planning.sh` |
| `.agents/prompts/planner.md` | Optional feature plans in `.agents/plans/` |
| `.agents/prompts/implementer.md` | `start-feature.sh` |
| `.agents/prompts/reviewer.md` | `review-feature.sh` |
| `.agents/prompts/triage-reviewer.md` | `triage-review.sh` |
| `.agents/prompts/triage-implementer.md` | `apply-triage.sh` |
| `.agents/schemas/review.schema.json` | Results of feature and planning reviews |
| `.agents/schemas/triage.schema.json` | Triage decisions |
| `.agents/schemas/revision.schema.json` | Planning revision decisions |

## Working directories

| Path | Contents | Committed |
|---|---|---|
| `.agents/reviews/` | Review and revision results (JSON and generated reports) | No |
| `.agents/triage/` | Approved triage results (JSON and generated reports) | No |
| `.agents/verification/` | The record of the last passed verification, written by `verify.sh` | No |
| `.agents/manual-steps/` | Per Issue, the steps a feature needs from you, written by the implementer; copied into the commit message and the pull request | No |
| `.agents/plans/` | Optional feature plans | Yes |
| `.agents/handoffs/` | Per Issue, the implementer's continuation note for a session that resumes the work (`start-feature.sh <issue> --resume`) | No |
| `.agents/lessons/` | Recurring agent failures and the rules learned from them | Yes |
