# Plan: F155, the Scientific Research Workspace and the capstone RR8 (Issue #619)

Source: `docs/roadmap.md`, F155; the change request
`docs/changes/part-b-scientific-products-and-research.md`, sections 3.4
(B4.C and its paragraphs), 4, 4.1, 4.2, and 6 (R4 to R6); requirements
decision 42; unresolved question 22 (the first reproduction paper); ADR 007
with its addendum (Issue #417), ADR 010, ADR 020, ADR 022 (decisions 3, 5,
6, 7, and 8), ADR 023; `docs/products.md`; the Issue's sections "What the
owner already decided (2026-11-24)" and "Owner's start of the plan only
(2026-11-25)". Written by the implementer session of 2026-11-25, which
was started for the plan only.

## Status of this plan

**Part 1 is approved (the owner's start of part 1, 2026-11-25, on the
Issue); parts 2, 2b, 3, and 4 are not.** The owner confirmed the review's
proposals for questions 1 to 6, 8, and 9 (the comment "Owner's decisions on
the plan's nine questions", 2026-11-25); question 7 (the multimeter) stays
open. The first two sessions wrote this plan only; the part-1 session of
2026-11-25 ran the dataset gate (see "Discoveries", the gate of
`cobe-firas-monopole`). After the owner's decision on question 10 (the
NASA basis accepted, LAMBDA asked beside it), a second part-1 session the
same day committed the sample and built part 1's steps 2 to 8 (see
"Discoveries", part 1 session 2). The owner's review of part 1
(2026-11-25) confirmed the register entry, made the residual figure's
rule post-hoc, asked for the view at phone width and 200 % text, and
approved question 11 as an optional follow-up outside part 1 (see
"Discoveries", part 1 session 3).

**The registered follow-up below is not frozen yet.** It becomes frozen as
"Freezing the registration" defines; until then nobody makes any of its
measurements.

**Revised after the owner's plan review of 2026-11-25** (the comment on
#619, "Plan review of 2026-11-25, supplied by the owner"). A later session
of the same day, again plan only, worked in its four corrections: the
FIRAS goal is the published spectrum fit from the derived data, not the
absolute calibration (the reference temperature, branch b4, the row T0,
the type `input`); the weighted rms of the paper and the statistical
against the published uncertainty; the multimeter's uncertainty model in
M4, with the shorted leads before and after; the boundary cases of the
decision rules, and the thresholds checked once more. The registration's
digest is recomputed, the review's proposals stand beside the open
questions, and "The checklist of part 0" is added. The registration is
still not frozen; the review advises against freezing until these edits
are read.

## The parts of the Issue

The block expects several Issues, the reproduction track first. As #614
and #508 did, the parts are pull requests of this one Issue, each with its
own instructions added to the Issue when it starts. Each part's completion
record is `partial` with the later parts under `remaining`, until the last.

| Part | What it delivers | Criteria it clears | What its pull request leaves open |
|---|---|---|---|
| 1. The workspace and the reproduction track | The dataset `cobe-firas-monopole` through its gate (card, dossier, sample, reader, reference figure, parsing test); the register entry of the paper; `pbc.products.research_workspace` (project state on disk, question selection, the registered plan, the run graph with its guided branch comparison, source evidence, typed discrepancies, review findings and follow-up decisions, report export with evidence statuses, the static workspace view, the command line, the scripted reviewer); the reproduction track end to end, its positive control, its bounded extension; example inputs and placeholder fixtures under `products/research-workspace/`; `docs/products.md`, `docs/architecture.md`, `docs/project-map.md` | 2 met; 3 met for the reproduction report; F145's 3 and 6 for this product (criterion 1 below) met for what part 1 contains | 4 for the original track; F145's 1, 4 (the starter), 5; the page |
| 0. The freeze (after part 1) | This plan alone, merged into `main` after the owner's approving review of its exact head (Level 1). It freezes the registration of the original track. It waits for the owner's multimeter (question 7) and comes as its own plan-only pull request after part 1. | none (the precondition of the reserved measurement) | everything |
| 2. The original track | The coil-loss investigation on `ad3-rlc-pilot`: the analysis of the existing sweeps (the parts measured apart, the sensitivity to a channel mismatch), the registration as data, copied from the frozen plan and checked against its digest, the follow-up log over more than two explanations, the decision rules, and a simulated positive control of each rule; the track runs end to end with the follow-up's evidence `not evaluated` | 4 met (both tracks end to end without a model account); 3 met for the investigation's report as far as it goes | the follow-up's measurement and verdicts; the page; the starter |
| 2b. The follow-up's evidence (small) | After the owner's bench session: the dataset `ad3-rlc-coil-followup` through its gate (owner's readings and exports, CC BY 4.0 on the owner's word); the registered rules applied, unchanged; the verdicts and the revised claim in the log | the investigation substantive, as the goal asks ("one substantive investigation completed") | the page; the starter |
| 3. The page and the learner material | The capstone page RR8; `products/research-workspace/` complete (brief, scientific criteria, example inputs, reference workflow, rubric, manual route, guided route, starter with a `pending` pin); the design of the optional materials track (criterion 5); the fresh-clone run recorded on the Issue | F145's 1, 4, 5 for this product; 5 (optional) met as design; 6 | the starter's first pin bump (the follow-up change of ADR 022 decision 5) |
| 4. The pin bump (small) | The starter's pin set to the merged commit of part 3 | the end of the at-pin skip | nothing |

Recordings of model sessions (below) are made by the owner or the
supervisor between the parts; each replaces a placeholder fixture in a
small pull request of its own.

**The order of part 1 and part 0 (the owner's split of 2026-11-25,
"Splitsing is goed").** Part 1 comes first and does not wait for the
freeze: the freeze concerns only the registration of the original track,
which part 1 does not build. The text between the registration markers
below is a **draft until part 0**: it stays as the plan-only session left
it, nobody makes any of its measurements, and this plan is committed with
part 1 without freezing anything (a plan on a feature branch is not
frozen; see "Freezing the registration").

The order 1, 2, 2b, 3 follows the block (the reproduction first) and puts
the page last, so that it shows the follow-up's real outcome. If the bench
session is delayed, part 3 may come before part 2b with the follow-up
shown as `not evaluated` (open question 6).

## Risk

The level of each part is derived from its paths and its triggers (ADR 020
decision 1); an agent may raise it and never lowers it.

| Part | Paths | Level by paths | Triggers named in advance | Level |
|---|---|---|---|---|
| 0 | `.agents/plans/619-research-workspace.md` | 1 | none | 1 |
| 1 | `src/pbc/products/research_workspace/`, `src/pbc/data/reference/cobe_firas.py`, `data/registry/cobe-firas-monopole.yaml` (sensitive), `data/samples/cobe-firas-monopole/`, `docs/datasets/cobe-firas-monopole.md`, `site/references.yaml` (one entry), `products/research-workspace/` (examples, fixtures, README), tests, `docs/products.md`, `docs/architecture.md` (sensitive), `docs/project-map.md` | 2 | none expected: no dependency file changes (NumPy and SciPy suffice; the source is plain text, so no FITS reader and no conversion script); no existing tolerance, budget, or test changes; no skip. **If** the gate finds that the data come only as FITS, a conversion script outside the build is added (ADR 007 addendum, decision 2), still no dependency. **If** the owner asks for a served local page instead of the static view, the new listening socket is the security trigger: Level 3 with an approval request .agents/approvals/619.md | 2 |
| 2 | `src/pbc/products/research_workspace/`, `products/research-workspace/examples/coil-loss/`, tests, `docs/products.md` | 2 | none: `ad3-rlc-pilot` is read through its existing reader, unchanged; its card and dossier are not changed (a pointer under its "Open items" at most, which is documentation) | 2 |
| 2b | data/registry/ad3-rlc-coil-followup.yaml (sensitive), `data/samples/ad3-rlc-coil-followup/`, docs/datasets/ad3-rlc-coil-followup.md, the outcome records under `products/research-workspace/examples/coil-loss/`, tests | 2 | **A changed scientific claim** if the outcome contradicts a statement `main` publishes in a lesson or a check: SA9 (F145 part 2) shows the discrepancy "without a resolution", and SA3, SA4, EM8 may state the channel mismatch as unknown. RR8 never edits those pages; a sentence the outcome makes untrue is a follow-up Issue of its own, Level 3 there | 2 |
| 3 | a new lesson page under `site/lessons/agents-llm/`, its experiment module, `products/research-workspace/` (documents, starter), tests | 2 (a new lesson's own claims are no trigger) | **The named skip** of the starter's `pending` pin (ADR 022 decision 5), stated in the completion record; a lesson fixture location if the page replays a recorded agent session (ADR 002 condition 2, an exemption that exists, not a new one) | 2 |
| 4 | `products/research-workspace/starter/pyproject.toml` | 2 | none | 2 |

No part touches a protected path of `.agents/policies/guardrails.conf`: no
ADR, no roadmap row (a status change of F155 in `docs/roadmap.md` would be
Level 3 and is not part of this plan), no workflow, no check of
`scripts/verify.conf`, no prompt, no policy.

## Skills

Skills: impeccable@08d5b47, frontend-design@dbd4588, pbc-scientific-visualization@a70b501
Skills: pbc-physics-teaching@7f34987

The teaching skill is for part 3, which writes the page; parts 1, 2, and
2b change no lesson's teaching (ADR 023 decision 2: not applicable to
them).

The digests of `PROVENANCE.yaml` that `uv run --locked python -m pbc.skills
--digest .agents/skills/<name>` printed on 2026-11-25: impeccable
`d6a4996d…`, frontend-design `180ab393…`, pbc-scientific-visualization
`a70b5016…`, pbc-physics-teaching `7f349871…`; `uv run --locked python -m
pbc.skills` accepts all five skills. The implementer of each part prints
them again and names them in its completion evidence.

| Deliverable | Class | Skills | Scientific validation | Accessible fallback |
|---|---|---|---|---|
| The workspace view: the project's question and its archive, the plan and its freeze, the run graph with branch statuses, the source evidence, the discrepancies with their types, the findings and decisions, the report with every claim's evidence status (part 1, extended in 2) | Page and layout: one static HTML file written by the command line, no server, no JavaScript (open question 2) | impeccable (mode Operate for the interface, within the brief), frontend-design | built from the project state only; a test compares every status shown with the state | it is HTML text with tables; every figure has alt text |
| The FIRAS spectrum: the measured monopole with its uncertainty, the fitted blackbody, the residuals with the fitted Galactic and distortion components (part 1) | Scientific figure, `processed` (from a `calibrated-observation` sample) | pbc-scientific-visualization (`measured_vs_model`, residual panel, the LAMBDA credit) | drawn from the fit of `research_workspace.firas`, recomputed from the committed sample | alt text; the table of fitted parameters with standard errors |
| The positive control: recovered T and y against the injected ones over seeds (part 1) | Scientific figure, `simulated` | pbc-scientific-visualization | the coverage computed, never asserted | alt text; the coverage table |
| The branch comparison: chi-square and the parameters per branch (part 1) | Table first; a figure only if it reads better | pbc-scientific-visualization | recomputed per branch | the table |
| The coil loss: the real part of Z against frequency from the R–L node sweep, before and after the follow-up's corrections, with the measured DC resistance as a reference line (parts 2 and 2b) | Scientific figure, `processed` | pbc-scientific-visualization (models dashed and apart, the measurement solid) | recomputed from `ad3-rlc-pilot` and the follow-up's sample | alt text; the table of R_L per frequency |
| The evidence map of the coil-loss question: explanations, the registered outcomes, the verdict per explanation with its status (parts 2 and 2b) | Table (a conceptual diagram only if the page needs one) | pbc-scientific-visualization | computed from the follow-up log | the table is the fallback |
| The page RR8 (part 3) | Page and layout (a lesson page in the site's frame) | impeccable (mode Read), pbc-physics-teaching, pbc-scientific-visualization | the lesson checks | as every lesson |

## What is reused, and what the package adds

Nothing listed here is replaced or changed. Several modules of F152 to
F154 are written for the throw laboratory of `pbc.agents.specification`
(a `Laboratory`, a `Specification`, the scripted route's `Record`). Neither
track's experiment is a run of that route, so the workspace reuses the
generic parts as they are and applies the same rules to its own records in
new modules.

| Reused as it is | From | What the workspace uses it for |
|---|---|---|
| `pbc.evidence.records` (`Ledger`, `RunRecord`, `Attempt`, `Artifact`, `Evaluation`, `CandidateReport`, `Claim`, `EVIDENCE_STATUSES`, `claim_status`, `check`, `summary`, `digest_value`, `digest_file`) | F137 | every run of a stage is an attempt with its artifacts; every claim of a report has a run link and an evidence status; an agent's own report is a `CandidateReport`, labelled unverified; a changed artifact invalidates what rested on it |
| `pbc.evidence.report` (`Statement`, `validate`, `problems`, `trace`) | F137 | the report export refuses a statement whose claim has no recorded evidence |
| `pbc.evidence.resumable` (`Research`, `Stage`, `Branch`, `State`, `resume`, `fork`) | F153, RR4 | the run graph: stages, branches, resume only from a valid state, failed attempts kept |
| `pbc.agents.investigation` (the roles and their bounded interfaces, the human steering actions) | F153, RR5 | extraction, implementation, and review roles over the project; the human's decisions; reused if its `INTERFACES` can be given the workspace's fields, otherwise its rule is applied by the workspace's own board (decided in part 1, recorded in "Discoveries") |
| `pbc.research.ideas` (`Idea` with `draft=None`, `Judgement`, `Archive`, `verify_archive`, `SELECTED`, `DEFERRED`, `REJECTED`) | F152, RR1 | the archive of questions with every decision, its reason, and what would warrant revisiting it |
| `pbc.research.plan` (`freeze`, and the refusal rules: a plan without withheld tests or stopping conditions is refused) | F152, RR2 | the digest of a registered plan; its rules re-applied by `registration.check` to plans that are not throw specifications |
| `pbc.research.followup` (`Finding`, `Explanation`, the kinds `EVIDENCE` and `WORDING`, the rule of `discriminates` and `decided`, the rule of `status`) | F154, RR6 | the findings and their kinds; the rule that no outcome may be predicted by two explanations; the rule that a revision of the prose never resolves a finding that asks for evidence |
| `pbc.research.report` (`resolve_number`, `Quantity`, `Recipe`, `bundle`, `reproduce`, `code_identity`) | F154, RR7 | every number of a report resolves to a record's field; the bundle is computed again and compared |
| `pbc.research.memory` (`Item`, `Memory`, `recall`) | F154, RR7 | what an investigation leaves for the next one, a result only with its limitations |
| `pbc.data.reference.ad3_rlc_pilot` (`read_traces`, `read_run`) and the phasor fit it uses | F140 | the original track reads the pilot's sweeps through the existing reader |
| `pbc.agents.loop`, `pbc.agents.tools` (allowlists), `pbc.agents.replay`, `pbc.agents.providers` and the clients (OpenAI, Claude, local) | ADR 004, #615 | the agent roles, bounded and replayed |
| `pbc.products.physics_lab.agent_campaign.MeteredClient` and the spend ledger | F145 part 1 | the spend count and the stop at the ceiling of EUR 50; imported as it is, and moved to `pbc.agents` only when a third product needs it (change request section 4: extract on actual reuse) |
| `pbc.products.starters` | F138 | the starter's two checks |

**What `pbc.products.research_workspace` adds** (module names proposed;
the implementer may merge two where one is small, recorded under
"Discoveries"):

- `project.py`: the project as a directory (the question archive, the
  registered plan and its freeze digest, the run graph's states, the
  ledger, the follow-up log, the decisions), `load`, `save`, and `verify`,
  which checks every chain and digest and names every problem.
- `questions.py`: the assessment of a data question before any run:
  feasible (every dataset it names has a card with a `go` and rights that
  permit the use), falsifiable (its registered rule has at least two
  reachable outcomes), within budget (the stages it needs); selection by a
  rule declared before the assessment, never reading a self-rating.
- `registration.py`: a registered plan: question, hypotheses, the
  explanations (two or more), each with the outcomes it predicts, the
  outcome rule, the withheld (confirmatory) part, the success criteria,
  the stopping conditions, the freeze digest and the freeze commit;
  `discriminates` over n explanations (no outcome predicted by two);
  refuses evidence whose measurement time precedes the freeze.
- `graph.py`: the run graph over `evidence.resumable.Research`, and the
  guided branch comparison (the branches, the declared criterion, the
  decision to continue or stop each with its reason and what would warrant
  revisiting it), with the sequential baseline.
- `discrepancy.py`: typed discrepancies between a published and a
  regenerated value (the types below); a type other than `unexplained`
  needs a recorded check that supports it.
- `sources.py`: source evidence: a published value, the register key of
  its source, the statement a person checked, and the claim it is linked
  to.
- `log.py`: the follow-up log of the workspace, with the rules of
  `research.followup` applied to evidence that is a record of an analysis
  or a dataset digest, not a scripted route's `Record`.
- `review.py`: the scripted reviewer (a fixed list of recomputed checks)
  and the agent reviewer's tools; a finding an agent proposes is accepted
  only through a recomputed check.
- `report.py`: the report export: sentences with typed numbers, every
  claim with its run or source link and its evidence status, the banner
  that a report is not a proof of success, the bundle.
- `view.py`: the static workspace view.
- `firas.py`: the reproduction's analysis (Planck spectrum, distortion
  shapes, the linear fit, the bounds, the positive control).
- `coil.py`: the original track's analysis (the impedance of the R–L node
  sweep, the corrections, the outcome quantities of the registration).
- `agent.py`: the agent roles and their tools; `__main__.py`: the commands.

## Part B's capstone pattern: what RR8 takes over from SA9, and where it differs

Read from `pbc.products.physics_lab` and `products/physics-lab/` as part 1
of F145 left them (part 2 has not started).

**Taken over.** The package layout `pbc.products.<product>` with a
command line in `__main__.py` (subcommands for a run, a recording, the
interface); an export directory with raw or input records, `report.md`
with its figures, `run.json` (the run record with the execution mode of
every segment), and `evidence.json` (the ledger of `pbc.evidence`);
`products/<product>/` with `examples/`, `fixtures/` (the one replay
location), and `starter/`; the README's sections (product brief,
scientific acceptance criteria, run it, the routes, the limits); the
recording command with `--provider`, prices given on the command line,
the `MeteredClient`, and the spend ledger outside the repository, refused
without it; placeholder fixtures of the scripted route, labelled as such,
until the owner records real ones; the replay that re-executes every
recorded tool call and compares; the agent's baselines run beside it.

**Differs.**

- No instrument and no safety envelope. The workspace analyses data; its
  execution modes are `recorded` (a declared dataset sample), `simulated`
  (the positive controls, generated from a seed), and `replayed` (an agent
  session from its fixture). It opens no device; the owner's bench
  session uses the physics lab's existing live mode.
- A project, not a campaign: a directory that lives across sessions, with
  append-only chains (archive, log, ledger) and resume from valid states.
- Two tracks with one record format; the human's decisions (selection,
  continue or stop a branch, accept a finding) are central, not a
  confirmation step.
- The interface is a static view written by the command line, with the
  decisions made by commands (open question 2), because nothing in the
  workspace runs for long or needs a stop button.

## The reproduction track: COBE-FIRAS

**The paper.** D. J. Fixsen, E. S. Cheng, J. M. Gales, J. C. Mather,
R. A. Shafer, and E. L. Wright, "The Cosmic Microwave Background Spectrum
from the Full COBE FIRAS Data Set", *The Astrophysical Journal* 473, 576
(1996), doi:10.1086/178173, arXiv:astro-ph/9605054. Its abstract states,
as remembered by this session and **to be quoted from the paper and checked
by a person on its register entry in part 1**: the temperature T0 = 2.728
± 0.004 K (95 % confidence), deviations from a blackbody below 50 parts
per million of the peak, and the limits |y| < 15 × 10^-6 and
|μ| < 9 × 10^-5 (95 % confidence). Later work (Fixsen 2009, ApJ 707, 916)
gives T0 = 2.72548 ± 0.00057 K; it is cited for the reference temperature
of the data file, not reproduced. The paper's uncertainty of T0 is
dominated by the calibration and the systematics (the thermometry of the
calibrator), not by the statistical scatter of the spectrum.

**The goal of the track.** A reproduction of the published **spectrum fit**
from the available derived data: the shape of the monopole against a
blackbody, the deviation from it, and the distortion parameters y and μ.
It is **not** an independent reproduction of the absolute temperature
calibration: the derived columns carry a blackbody at a stated reference
temperature, not the calibrator data from which the paper set T0. The
report, the register entry, and the page state this scope in these words.

**The source file.** The FIRAS monopole spectrum as NASA's LAMBDA archive
distributes it (expected address
`https://lambda.gsfc.nasa.gov/data/cobe/firas/monopole_spec/firas_monopole_spec_v1.txt`,
to be confirmed at the gate): a plain-text table of 43 frequencies from
about 2.27 to 21.33 cm^-1 with, per frequency, the monopole spectrum
(MJy/sr), the residual from a reference blackbody (kJy/sr), the
one-standard-deviation uncertainty (kJy/sr), and the modelled Galactic
spectrum at the poles (kJy/sr), the columns taken from Table 4 of the
paper. Expected size a few kilobytes. The LAMBDA monopole file is
expected to hold a reference blackbody of about 2.725 K (the later
recalibration) plus the residuals, not the paper's 2.728 K. **The gate
records the reference temperature the sample actually states**, in its
header's words, with the source of that value (which paper set it), on
the card and in the dossier; the analysis reads T_ref from the card, never
a constant in the code. Nothing below assumes which value it is.

**Licence and data rights (ADR 007 decision 2; the gate of part 1).**
LAMBDA is a NASA archive; NASA's media and data usage guidelines and
LAMBDA's own acknowledgement text are read at the gate, and the card
records the four answers (local download, redistribution of subsets,
publication of derived figures, modification and attribution) with their
sources, as the TESS card does for MAST. Expected: public domain or no
restriction, with an acknowledgement requested; the card then records
`equivalent-permission` with the sources, and the acknowledgement travels
with the data (decision 7: on the figure, the page, and About). The
paper's text is the publisher's: nothing of it is committed beyond the
short checked statements of its register entry, and the page cites it.
If the rights cannot be established from the records, the sample is not
committed and the track stops at the gate for the owner (open question 4).

**How the data reach the build.** The implementer of part 1 downloads the
file once by the card's address (a part-1 step, which this session did not
take), inspects it, and commits it byte for byte at
`data/samples/cobe-firas-monopole/` with its checksum on the card. The
reader in `src/pbc/data/reference/cobe_firas.py` uses the standard
library and NumPy. The build and CI read only the committed sample;
`scripts/fetch-data.sh` is the learner's documented download. No FITS file
is involved; if the gate finds otherwise, the FITS file is converted once
by a documented script outside the build whose input and output checksums
are on the card and the dossier (the owner's reader policy, ADR 007
addendum decision 2), and the build reads only the extract.

**What is computed.** With x = h ν / (k T) and ν = c ν̃ (ν̃ in cm^-1),
the Planck intensity B_ν(T) = (2 h ν^3 / c^2) / (e^x − 1), converted to
MJy/sr (1 Jy = 10^-26 W m^-2 Hz^-1). Near a reference T_ref, the residual
spectrum is linear in the parameters:

ΔI(ν) = ΔT ∂B_ν/∂T + G g(ν) + y Y(ν) + μ M(ν),

with g the file's Galactic spectrum, Y(ν) = T ∂B_ν/∂T · [x coth(x/2) − 4]
the Compton y shape, and M(ν) = −(2 h ν^3 / c^2) e^x / (e^x − 1)^2 the
chemical-potential shape (the forms are checked in part 1 against a
numerical derivative of the distorted occupation numbers, by a test). The
fit is weighted least squares with the file's uncertainties; standard
errors from the covariance; the 95 % bound of y or μ is the larger of
|value ± 1.96 σ| (the convention is stated beside the number, and compared
with the paper's own as the paper states it).

**What the fit can and cannot give.** The fitted temperature is
T_fit = T_ref + ΔT, with ΔT from the residuals. If T_ref was itself set
by a fit of these data, ΔT is near zero by construction, and T_fit equals
the file's reference whatever it is. Every uncertainty the fit gives is
**statistical**: it rests on the file's one-standard-deviation column
alone. The published uncertainties of T0, y, and μ also hold systematic
terms that the columns do not carry (the calibration, the Galactic model,
the covariance between frequencies); they are reported beside the
regenerated statistical ones, never replaced by them, and the published
bounds on y and μ are **not assumed to be recomputable** from the columns
alone. The positive control below tests the statistical fit only; it says
nothing about the calibration.

**What to reproduce: a decision for the owner (open question 1).**

| Option | Targets | Cost | What it teaches |
|---|---|---|---|
| A. **Recommended.** The spectrum and its distortions | the spectrum fit (ΔT against the file's reference, and the scope of T0 below); the residual spectrum and its figure; the weighted rms; the bounds on y and μ | one linear fit per branch, 43 points; well inside the page budget | a reproduction with likely typed discrepancies (the covariance between frequencies, the Galactic model, the calibration that the derived data do not carry), and a bound, not only a central value |
| B. The temperature only | the spectrum fit and the spectrum figure | smaller | little: the fitted temperature equals the file's reference by construction, so it shows the limit of derived data and nothing more |
| C. A plus the dipole spectrum | A, and the dipole amplitude from a second LAMBDA file | a second dataset through the gate | more, at the cost of a second gate and a longer page |

**What counts as reproduced** (declared here, before any fit on the file;
copied into the reproduction's registered plan in part 1):

| Quantity | Published (to be checked on the register entry) | Reproduced when | Otherwise |
|---|---|---|---|
| The spectrum fit: ΔT against the file's reference | (the shape statement of the paper: the spectrum is a blackbody) | ΔT (b1) is reported with its statistical standard error σ_T, beside T_ref and its source; the shape is reproduced when \|ΔT\| ≤ 2 σ_T and the weighted rms row below is reproduced | a typed discrepancy |
| T0, the absolute temperature | 2.728 ± 0.004 K (95 %, calibration-dominated) | only by a regenerated T0 that does **not** rest on the file's reference. A T_fit that equals T_ref by construction is no reproduction of the published value, **whatever its difference to 2.728 K**, and the report never calls an agreement within 0.004 K a reproduction | expected: `not-reproduced` for T0, typed `method` (the missing piece: the absolute calibration, with the paper's section on it named; the supporting check: b4, which shows that T_fit follows the reference to first order), unless the gate finds, with its source, that the file's monopole and T_ref rest on a calibration independent of the paper's fit; then T_fit is compared with 2.728 K within 0.004 K and the gate's finding is quoted beside the result |
| The uncertainty of T0 | ± 0.004 K (95 %, with the calibration and the systematics) | the statistical σ_T of the fit reported beside it, never substituted for it | the type `uncertainty`, with the published budget's other terms named from the paper |
| The deviation from a blackbody | below 50 ppm of the peak brightness | the **weighted rms** of the residuals after the fit of T and G, **with the paper's own definition and weights**, quoted from the paper on the register entry at the gate (not an unweighted rms), is below 50 ppm of the peak of B_ν(T_fit) | a typed discrepancy; if the paper gives no definition that can be quoted, the row is `inconclusive`, typed `method`, and no rms of this session's choice is put in its place |
| \|y\| (95 %) | < 15 × 10^-6 | the regenerated y within 1.96 of its statistical σ_y of zero, and the regenerated statistical bound at most 1.5 times the published one; both bounds are shown, the regenerated one labelled statistical only | a typed discrepancy (a statistical bound far below the published one is `uncertainty`, never "a better limit"); a y beyond 1.96 σ_y, or a bound above 3 times the published one, is also `not-reproduced` unless a supported type explains it |
| \|μ\| (95 %) | < 9 × 10^-5 | as for y | as for y |
| The residual figure | the paper's figure of the residuals (its number read at the gate) | the regenerated residuals, with uncertainties, from the documented inputs; a figure is compared by the numbers it shows, not by its look | a typed discrepancy |

A non-reproduced result passes criterion 2 when its evidence and its
analysis justify it: the regenerated value, the published one, the type,
and the check that supports the type. A transparent `not-reproduced` with
its evidence is a valid result of this track; the expected verdict on the
absolute T0 is one, by the nature of the derived data.

**Typed discrepancies** (`discrepancy.TYPES`; a discrepancy is reported,
typed, and never explained away):

| Type | Meaning | The check that must support it |
|---|---|---|
| `input` | the published inputs differ from those the paper used (a reference temperature, a version) | a sensitivity branch shows the claimed cause: the regenerated value moves to the published one when the paper's input is used instead. Kept **only** when that branch shows it; otherwise the discrepancy stays `unexplained` or takes another supported type. (For T0, b4 is not expected to show it: the free ΔT absorbs a change of the reference.) |
| `method` | the paper's method needs something the published inputs do not contain (a frequency covariance, a Galactic model, a calibration) | the missing piece named with where the paper describes it, and a sensitivity branch showing the size of its effect |
| `uncertainty` | the central value reproduces and the uncertainty does not | the regenerated statistical uncertainty beside the published one, and the published budget's other terms named from the paper |
| `numerical` | a difference at the precision of the computation | a run at a higher precision or a different implementation removes it |
| `unexplained` | none of the above is supported | none; this is the honest default and stays visible |

A `not-reproduced` verdict is a result with its evidence, not a failure of
the track; the report says so and does not soften it.

**The positive control** (mode `simulated`): synthetic spectra B_ν(T_true)
+ G g + y_inj Y + noise drawn from the file's uncertainties, seeded, at the
file's 43 frequencies; the fit must recover T_true and y_inj within two
standard errors in at least 90 of 100 seeds, and with y_inj = 0 the bound
must contain zero at the stated rate. A method that fails its control is
`failed` and the reproduction's verdict is `not evaluated`.

**The bounded extension and the guided branch comparison.** Branches of
the run graph (forks of the stage "fit"): b0, T only; b1, T and G; b2, b1
and y; b3, b1 and μ; b4, b1, b2, and b3 again with the residuals taken
against B_ν at the paper's 2.728 K instead of the file's T_ref (a
sensitivity branch); b5, b1 without the highest-frequency points, where
the Galactic spectrum is largest (an ablation). **What b4 shows:** a change
of the reference temperature is absorbed by the free ΔT of a linear fit,
so T_fit does not move to first order; b4 shows which results are
sensitive to the reference (through the second-order term of B_ν in T: the
weighted rms, y, μ, the chi-square) and by how much. The plan predicts no
value for b4 and does not expect T_fit to move to 2.728 K; b4 supports the
type `input` for a result only where that result moves to its published
value. The declared criterion: a
branch that adds a parameter continues when it lowers chi-square by more
than 4 (two standard deviations for one parameter), and stops otherwise
with its reason and what would warrant revisiting it. The sensitivity
branch b4 and the ablation b5 add no parameter; they are always run and
reported, not decided by the criterion. The branches run in
sequence, the sequential baseline; **no tree search is used**, and the
record says why: six branches of a linear fit are enumerated in under a
second, and a search over template subsets would cost more without asking
a question the branches leave open.

**Questions considered** (the archive of part 1, prepared, each with its
decision, reason, and what would warrant revisiting it): the spectrum fit
and the scope of T0 against the derived data (selected); the absolute
calibration of T0 (rejected: it needs the calibrator data, which the
derived columns do not carry; revisit if LAMBDA distributes them in a
form the dataset rules allow); the distortion bounds (selected with option A); the
dipole amplitude (deferred unless option C); the FIRAS and WMAP combined
temperature (rejected: needs a second instrument's data and the paper's
combination; revisit if a later lesson declares WMAP data); a specific
energy-release model for μ (rejected: beyond the paper; revisit as a
learner's extension in "Explore and extend").

## The original track: the coil-loss question on `ad3-rlc-pilot`

**What exists.** The pilot of F140 (`docs/datasets/ad3-rlc-pilot.md`)
measured a series RLC circuit (nominal R 100 Ω ± 1 %, L 1 mH, C 10 nF)
with the Analog Discovery 3: a sweep with channel 2 on the capacitor and a
sweep with channel 2 at the R–L node. From the second, Z = R H / (1 − H)
with the nominal R gives L = 0.861 ± 0.010 mH, C = 14.55 ± 0.15 nF, and the
real part of Z near the resonance, R_L = 63 ± 3 Ω (mean over 31.6, 43.0,
and 58.5 kHz), rising to 97 Ω at 108 kHz and 259 Ω at 200 kHz. The ideal
model with the nominal parts predicts f0 = 50.3 kHz and Q = 3.16; the
capacitor sweep gives f0 = 47,009 Hz and Q = 1.549. The model of the parts
measured apart leaves phase residuals between −1.2° and −8.2° that grow
with the frequency. The channels' relative gain and phase are unknown
(channel 1 on the 5 V range, channel 2 on the 50 V range, both fixed by the
adapter), and the dossier says the data cannot separate a mismatch from a
loss that depends on the frequency.

**The question.** Why does the ideal series RLC model fail on this
circuit? It splits into two gaps, which the registration below answers
separately: G1, is the loss near the resonance (about 63 Ω) the DC
resistance of the parts or a loss that exists only in alternating current;
G2, are the rise of that loss with the frequency and the growing phase
residual properties of the circuit or of the two channels. G3, whether the
capacitance (14.55 nF against 10 nF nominal) is the part's own tolerance,
is optional and needs a meter with a capacitance range (open question 7).

**The thresholds were chosen after seeing the pilot's data**; only the new
measurements of the registration are confirmatory, and the record says so.

### The registered follow-up

The text between the two markers is the registration. Part 2 copies it into
products/research-workspace/examples/coil-loss/registration.md byte for
byte, and a test compares the sha256 of that file with the digest recorded
after the end marker. Nothing in it changes after the freeze; a change is a
new registration with a new freeze, and the evidence of the old one stays
in the log.

<!-- registration:begin -->
Registration: F155 (Issue #619), the coil-loss follow-up of `ad3-rlc-pilot`.

Circuit. The pilot's circuit of F140 on the breadboard, with the same
physical parts if they can be identified: W1 -> 100 ohm resistor -> 1 mH
inductor -> node A -> 10 nF capacitor -> ground. Scope 1- and 2- at
ground. The live input `products/physics-lab/examples/live-pilot.toml`,
unchanged (1 V, 5 kHz to 200 kHz, 13 coarse log-spaced points, channel 1
on the 5 V range, channel 2 on the 50 V range). Close WaveForms first.

Measurements, in this order, all after the freeze:
M1. Capacitor sweep: scope 1+ at W1, 2+ at node A (as pilot run 2).
M2. R-L node sweep: scope 1+ at W1, 2+ at the R-L node (as pilot run 3).
M3. Same-node sweep: scope 1+ and 2+ both at W1. The physics lab reports
    no -90 degree crossing and an inconclusive run; its raw samples at the
    13 coarse frequencies are the measurement.
M4. Output off, USB unplugged. Lift one lead of the capacitor and one of
    the resistor out of the breadboard. With the owner's multimeter, two
    wire, on its lowest resistance range that holds the largest reading
    of the parts, one range for every reading of M4 where the meter
    allows it: Z1, the leads shorted (three readings), before any part;
    the inductor across its two breadboard rows (three readings, R_dc_bb);
    the inductor out of the breadboard (three readings, R_dc); the
    resistor across its two breadboard rows with the inductor lifted
    (three readings, R_s_bb); Z2, the leads shorted again (three
    readings), after the last part. Recorded per reading: the value, the
    range, the resolution on that range (the step of the last digit), the
    meter's make and model, its accuracy specification on that range in
    the words of its manual (percent of reading plus digits), the time.
    Optional, only if the meter has a capacitance range: the leads open on
    that range (three readings), then the capacitor out of the breadboard
    (three readings, C_meter), recorded in the same way.
M5. Put the parts back; repeat M2 (repeatability).

Derived quantities. Phasors by the least-squares fit of the pilot's
dossier (cosine, sine, constant over each record). m(f) = V2/V1 from M3 at
the 13 coarse frequencies; dg = |m| - 1, dphi = arg m in degrees.

Meter readings. The zero z = the mean of the six readings of Z1 and Z2;
dz = mean(Z2) - mean(Z1) is recorded as the change of the contact and
lead resistance during M4. For a quantity X with readings x1, x2, x3 on
range r: X = mean(x) - z. Its standard uncertainty combines in
quadrature:
  u_repeat = the standard error of the three readings, s / sqrt(3);
  u_res = q / sqrt(6), with q the resolution on r (the quantisation of
    the reading and of the zero, each rectangular of full width q);
  u_contact = |dz| / (2 sqrt(3)) (rectangular, half-width |dz| / 2);
  the specification. The accuracy limit on r is a = p |reading| + n q,
    p the percent of reading, n the digits, taken from the manual, and
    read as the half-width of a rectangular distribution: a standard
    uncertainty of a / sqrt(3) (a Type B evaluation). It is a property of
    the meter, not of the readings, and is NOT reduced by repeating or by
    averaging. Its two parts are treated apart, because the reading and
    the zero are taken with the same meter: the offset part n q (read
    as an offset of the zero, the assumption named) is common to the
    reading and the zero on the same range and cancels in the
    subtraction (if the zero was read on another range, it does not
    cancel: u_off = n q_r / sqrt(3) and n q_z / sqrt(3), in quadrature);
    the gain part does not cancel and acts on the net value:
    u_gain(X) = p |X| / sqrt(3).
u_X = sqrt(u_repeat^2 + u_res^2 + u_contact^2 + u_off^2 + u_gain(X)^2),
with u_off = 0 when the offset cancels. The non-gain part u_X,ng is u_X
without u_gain(X). The capacitance is treated in the same way, with the
open-lead readings as its zero and no contact term.

Z(f) = R_s_bb H / (1 - H) from M2, with H uncorrected (for G1) and H / m
(for G2). R_L(f) = Re Z(f). R_L0 = the mean of R_L at 31.6, 43.0, and
58.5 kHz; u_L = its standard error over the three frequencies combined in
quadrature with R_L0 u_Rs,ng / R_s_bb, the non-gain relative uncertainty
of R_s_bb. L and C from the least-squares fit of Im Z = 2 pi f
L - 1 / (2 pi f C) over the 13 points. The parts-apart model V_C/V_S = 1 /
(1 - w^2 L C + j w (R_s_bb + R_L0) C), w = 2 pi f; P = the rms over the 13
coarse frequencies of its phase minus the phase of M1, with the
uncorrected H (P0) and with H / m for both sweeps and the model refitted
(P1). Rise = R_L(200 kHz) - R_L(43.0 kHz) after the correction, u_hi its
standard uncertainty from the phasor fits and R_s_bb.

Precondition (identity of the parts). M2 agrees with pilot run 3 when L and
C each agree within 2 % and R_L0 within 3 u_L. If it does not, the
conclusions are scoped to the circuit of M1 to M5, and the pilot's
discrepancy stays not evaluated for G1 (a property of the parts); G2 (a
property of the instrument) carries over. M5 against M2 is reported as
repeatability.

Decision rules. Each rule is evaluated as written, with the inequalities
exactly as stated (a value equal to a threshold falls on the side the sign
"<=" or ">=" gives it). No two outcomes of a rule can hold together; a
case that meets no predicted outcome is "inconclusive" and is reported as
a result.

G1. The loss near the resonance. D = R_L0 - R_dc_bb. The meter's gain is
common to R_s_bb (through R_L0) and R_dc_bb and acts on D itself; so
u = sqrt(u_L^2 + u_dc,ng^2 + (p |D| / sqrt(3))^2), with u_dc,ng the
non-gain uncertainty of R_dc_bb.
  Undecidable first: if u > 5 ohm, the outcome is "inconclusive" whatever
  D is (the reference is too uncertain to decide G1).
  Explanation DC (a constant series resistance: the wire of the coil and
  the parts' own values): predicts outcome "accounted": |D| <= 2 u.
  Explanation AC (a loss of the coil that exists only in alternating
  current, from its core and the skin and proximity effects): predicts
  outcome "short": D > 3 u and D > 5 ohm.
  Every other outcome decides nothing and is "inconclusive". D < -3 u
  ("exceeds") is predicted by neither and opens a new finding: the sweep's
  model or the meter reading is wrong.

G2. The frequency dependence and the phase residual. The mismatch is
measurable when max |dphi| > 0.3 degrees or max |dg| > 0.003 over the 13
frequencies, and not measurable otherwise.
  Explanation MISMATCH (the channels' relative gain and phase): predicts
  outcome "artefact": the mismatch measurable, Rise <= 2 u_hi, and
  P1 <= P0 / 2.
  Explanation CIRCUIT (a loss that grows with the frequency): predicts
  outcome "remains": the mismatch not measurable, and Rise > 3 u_hi.
  Explanation BOTH: predicts outcome "mixed": the mismatch measurable, and
  Rise > 3 u_hi.
  Every other outcome decides nothing and is "inconclusive" (among them a
  Rise between 2 u_hi and 3 u_hi, and a Rise <= 2 u_hi without a
  measurable mismatch, which the precondition then examines).

G3 (optional; dropped, and not reported as inconclusive, when the meter
has no capacitance range). E = C_meter - 14.55 nF, u_C =
sqrt(u_Cmeter^2 + (0.15 nF)^2), with u_Cmeter by the model of the meter
readings above.
  Explanation TOLERANCE (the part's own value): predicts "agrees": |E| <=
  2 u_C.
  Explanation ELSEWHERE (the 4.5 nF come from the measurement or the
  wiring): predicts "nominal": |C_meter - 10 nF| <= 2 u_C and E < -3 u_C.
  Every other outcome decides nothing and is "inconclusive".

Withheld part. M1 to M5 are the confirmatory measurements; the pilot's data
chose the thresholds. The analysis code that computes the outcomes is
committed before M1 is made, with its code identity recorded in the log; a
change of that code after M1 is recorded as a deviation, and its result is
exploratory.

Stopping. One bench session. A failed run (an invalid capture, a refused
output) is repeated once and both are kept; a second failure stops the
session, and the follow-up is inconclusive with its reasons.

Success. The follow-up succeeds when every measurement is recorded with its
raw data and every outcome is computed by the registered rule, whatever the
outcome. An outcome that decides nothing is a result, reported as
inconclusive.
<!-- registration:end -->

Registration digest (sha256 of the bytes from the line after the begin
marker to the line before the end marker, both lines included, with their
final newline): `89973f3975b28f07c7beb0274e8e43391be0e4a96f5eac54fa4d42e294497758`
(recomputed on 2026-11-25 after the owner's review; the earlier digest
`c7c8054e…d033` is void). Recompute it with
`awk '/^<!-- registration:begin -->$/{f=1;next}/^<!-- registration:end -->$/{f=0}f' .agents/plans/619-research-workspace.md | shasum -a 256`;
any edit between the markers before the freeze requires a new digest on
this line.

**Freezing the registration.** "Frozen" means: this plan, with the text
between the markers unchanged, is in a commit on `main` that merged a pull
request after the owner's approving review of that pull request's exact
head (part 0). The registration is recorded in three places: (1) this plan
at that commit; (2) a comment on Issue #619 by the owner or the supervisor
naming the merge commit and the digest above; (3) from part 2 on, the first
entry of the follow-up log, which names the digest, the merge commit, and
its date, and a test that refuses any evidence whose measurement time
(from the run records of M1 to M3 and the readings of M4) precedes that
date. A plan file on a feature branch is not frozen: a branch can be
rewritten, and `main` cannot. The supervisor's recommendation (open
question 3) is to make the bench session after part 2 is merged, so that
the analysis code is fixed before the measurement too.

**The checklist of part 0** (from the owner's review of 2026-11-25; part 0
is its own pull request, with this plan alone):

1. The review's four corrections are in the plan (the FIRAS scope and
   T_ref, b4, the row T0, the type `input`; the weighted rms and the
   statistical against the published uncertainty; the meter's model in
   M4 with Z1 and Z2; the boundary cases and the thresholds checked).
2. The owner has read the revised registration, and has answered question
   7 (the meter's make and model, its accuracy formula on the low
   resistance range, its resolution, a capacitance range or none) on the
   Issue; G3 is dropped without a capacitance range. Answering does not
   change the registration: the readings record the meter, the rule reads
   its specification.
3. The owner has confirmed or changed the proposals for questions 1 to 6,
   8, and 9 on the Issue.
4. The digest line matches the text between the markers (the command
   above), on the exact head of the pull request.
5. The pull request changes this plan only (Level 1), and the owner's
   approving review is of its exact head; the merge is the freeze.
6. No measurement M1 to M5 has been made, and none is made before the
   merge.
7. After the merge: the comment on #619 with the merge commit and the
   digest; from then on no edit between the markers (a change is a new
   registration).

**How each rule is checked before the measurement.** Part 2's positive
controls simulate the circuit under each explanation (a constant series
resistance; a resistance that grows as the square root of the frequency
above a corner; a channel delay and a gain error applied to channel 2; both)
with the physics lab's simulated bench and `ImperfectChannels`, seeded,
and check that each rule returns the outcome its explanation predicts and
that the outcome sets are disjoint (`registration.discriminates`).

**The boundary cases.** Besides the four explanations, the controls
simulate (or, for the meter readings, construct) values just below, at,
and just above every threshold of the rules: 0.3 degrees for max |dphi|,
0.003 for max |dg|, the factors 2 and 3 of u and of u_hi, the floor of
5 ohm on D, the limit u > 5 ohm, P0 / 2, and for G3 the factors 2 and 3
of u_C. For each case they check that the outcome is the one the rule's
text gives at that value (the side of "<=" and ">"), that no two outcomes
of a rule are returned together, and that every case between the
predicted outcomes is `inconclusive`. They also check the uncertainty
model of the meter readings on constructed readings: the offset cancels
on one range and not across two, the gain part is not reduced by more
readings, and dz enters as the contact term.

**The thresholds, checked once more** (2026-11-25, before the freeze, at
the owner's review). Three changes came from the check, and are in the
registration above: G1 gets the condition u > 5 ohm, without which a large
u would make "accounted" reachable by an uninformative reference; the
meter's gain enters D once, because it is common to R_s_bb and R_dc_bb
(the earlier text combined it twice, as if independent); "artefact" of G2
needs a measurable mismatch, so that MISMATCH is predicted only when its
cause is seen (as the type `input` of the reproduction track needs its
sensitivity branch). The other thresholds stand: 2 % on L and C and 3 u_L
on R_L0 for the identity of the parts (about twice the pilot's relative
standard errors of 1.2 % and 1.0 %); 0.3 degrees and 0.003 for a
measurable mismatch (that the phasor fit of the same-node sweep resolves
them is expected, not measured: part 2's control reports the resolution it
reaches on the simulated bench, and if that is coarser, the report says
before the measurement that G2 will likely be inconclusive, without a
change of the threshold); 2 u and 3 u with the gap between them inconclusive. After
the freeze, a change of any threshold is a new registration, or the
analysis with it is exploratory and labelled so.

**Questions considered** (the archive of part 2, prepared): the coil-loss
question (selected); the capacitance (G3, deferred unless the meter has
the range); the LED pair's model (rejected: SA9's protocol; revisit if the
held-out prediction fails on the owner's bench); the die temperature's
effect (rejected: the pilot's record holds 61.6 to 63.7 °C only, no
variation to test; revisit with a cooling or warming run).

## Evidence statuses and the report

Every claim of a report is a `pbc.evidence.Claim` with a run link (an
attempt of the ledger) or a source link (a register key and its checked
statement), and one of the statuses completed, failed, inconclusive, not
evaluated, independently checked (`EVIDENCE_STATUSES`), with its scope.
`evidence.report.validate` refuses a statement without one; every number
resolves to a record's field (`research.report.resolve_number`). The
report's first lines state, generated from the ledger, how many claims are
in each status, and that a report is a summary of records, not a proof that
the investigation succeeded; a report whose claims are all `not evaluated`
says so in that place. A finding that asks for new evidence stays open
after any revision of the prose (the rule of `research.followup.status`).
"Independently checked" is used only where a check that the claim's author
did not write recomputed it (the evaluator's recomputation, the scripted
reviewer's check); an agent's agreement is never that.

## The workspace view

A static HTML file that `python -m pbc.products.research_workspace view
--project <dir> --out <file>` writes from the project state: the question
and its archive, the registered plan and its freeze, the run graph (stages,
branches, statuses, failed attempts with their reasons), the source
evidence, the discrepancies with their types, the findings and decisions,
and the report with every claim's status. Decisions are made by commands
(`select`, `decide`, `accept-finding`), each appended to the project's
chains. No server, no socket, no JavaScript, no build step; the learner
opens the file in a browser. A served page like SA9's is open question 2.

## Model calls and recordings

**Which steps would use a model** (each advisory, each with a scripted or
manual equivalent, so that both tracks run end to end without a model
account, criterion 4):

| Step | Role | Tools (allowlisted) | Its output and how it is checked | Without a model |
|---|---|---|---|---|
| Propose questions | proposer (RR1) | none | ideas with self-ratings; assessed by the build, selected by the declared rule, which reads no rating | the prepared question files |
| Extract the published values | extraction (RR5) | `read_statement(key)` | values with the words they rest on; refused when a quoted word is not in the register's checked statement; compared with the values a person entered | the values entered by a person on the register entry |
| Review the report | reviewer (RR5, RR6) | `read_section`, `read_record`, `run_check(name)` over the scripted reviewer's checks | findings, typed `EVIDENCE` or `WORDING`; a finding enters the log as proposed, and is accepted only through a recomputed check (`pbc.agents.investigation.steer`'s rule) | the scripted reviewer |

**In the build.** Each recorded session is a replay fixture at
`products/research-workspace/fixtures/` (ADR 022 decision 8): only the
recorded messages and the expected tool results; every replay re-executes
the tool calls against the project and compares. Until the owner records
them, the fixtures are placeholders of the scripted route, labelled so in
the fixture and on every page that shows them, as in F145 part 1. If the
page RR8 shows a session, a copy is at the lesson's own fixture location
(ADR 002 condition 2).

**Estimate against the ceiling of EUR 50.** Per track: the reviewer about
ten calls, its context growing to about 25,000 tokens, about 150,000 input
and 6,000 output tokens in all; the proposer and the extraction about
10,000 input and 3,000 output together. Per track about 160,000 input and
9,000 output tokens. Two tracks with two paid providers (Claude and GPT;
the local model costs nothing) are four sessions, about 640,000 input and
36,000 output tokens. At an assumed EUR 5 per million input and EUR 25
per million output tokens (the owner gives the real prices on the command
line), about EUR 4.10; three attempts each, about EUR 12. The metered
client stops before a call that would cross EUR 50 counted across all
recordings of this capstone in the owner's ledger.

**The commands the owner or the supervisor would run** (part 1 writes
them; names may change, recorded in `products/research-workspace/`):

```
uv run --locked --extra anthropic python -m pbc.products.research_workspace record \
    --track reproduction --role reviewer --provider anthropic --model <model id> \
    --price-input <EUR per million> --price-output <EUR per million> \
    --spend-ledger <file outside the repository> \
    --out products/research-workspace/fixtures/reproduction-reviewer-claude.json
```

and the same with `--track original`, `--role proposer` or `extraction`,
`--provider openai` (`--extra openai`) or `local` (`--extra openai`, a
loopback address). The existing optional groups `anthropic` and `openai`
are used; no group is added to `pyproject.toml`. The implementer session
holds no key and records nothing.

## The bench sessions the owner attends

| Session | When | On the breadboard | What it needs | Commands |
|---|---|---|---|---|
| F (the follow-up) | after the freeze; recommended after part 2 is merged (open question 3) | the pilot's circuit, the same parts where they can be identified: the 100 Ω ± 1 % resistor, the 1 mH inductor, the 10 nF capacitor; the AD3 with its two probes | the AD3 Pro Bundle, the multimeter (its make and model, its accuracy formula and resolution on the low resistance range and, for G3, the capacitance range), about one hour | `uv run --locked python -m pbc.products.physics_lab run --mode live --input products/physics-lab/examples/live-pilot.toml --circuit-confirmed --out <dir>` for M1, M2, M3, M5, the probes moved between runs as the registration says; the readings of M4 written into the CSV template that part 2 provides |

**Reserved until the freeze:** M1 to M5 entirely, and in particular every
multimeter reading of the inductor, the resistor, and the capacitor, and
any sweep with both probes on one node. F145's bench sessions (the live
campaigns of #614) may use the same circuit; they make none of these
measurements. The reproduction track needs no bench.

After session F the owner states the licence of the readings and exports
(CC BY 4.0, as for the pilot) on the Issue, and part 2b declares them as
`ad3-rlc-coil-followup`.

## The page RR8

**Slot and place.** `RR8`, path `autonomous-research`, position 8, kind
`product capstone`, unfilled (checked in `site/curriculum.yaml`, 2026-11-25).
Strand `agents-llm` (ADR 022 decision 3); its order is the next free one
when part 3 starts (24 is the last today; SA9 of F145 part 2 may take the
next), checked then, not assumed. No course home.

**Archetype.** Engineering design or capstone, with a measured-data
investigation inside "Experiment" (pbc-physics-teaching, section 2).

**The central question.** How do you know that a research report's
conclusions follow from its evidence, also when a published result does
not reproduce or an explanation is refuted?

**The counterintuitive point.** A complete, fluent report with every number
matching its record can still be unsupported: a number that matches is not
a claim that is evidenced, and a fitted temperature that matches the
published one to a thousandth of a kelvin may match it by construction,
because the data file already carries a blackbody at a reference
temperature.

**Sections.**

1. *Understand.* Why a report is not a proof; the two tracks; the evidence
   statuses; the brief and the scientific criteria of the product; the
   limits ("an educational research workspace, not a substitute for peer
   review; novelty is not assessed; a limited search certifies nothing").
2. *Construct.* Excerpts of the real modules, each with its purpose: the
   rule that no outcome is predicted by two explanations
   (`registration.discriminates`, exact full source: the decision rule is
   the point); the refusal of a discrepancy type without its supporting
   check (`discrepancy`, exact selection); the fork and the branch
   decision of the run graph (`graph`, exact selection); a report claim's
   status from the ledger (`report`, exact selection). Plotting code is a
   Source link after its transformations are checked (pbc-physics-teaching
   section 7).
3. *Experiment.* The page executes the reproduction track on the committed
   FIRAS sample (the fit, the branches, the positive control, the typed
   discrepancies) and the original track on `ad3-rlc-pilot` and, after 2b,
   `ad3-rlc-coil-followup` (the registration, the outcomes, the verdict per
   explanation with its status). The prediction moment: before the
   follow-up's outcomes, the learner reads the registration's table and
   says which outcome of G1 a coil wound of thin wire would give. The
   interpretation moment is the self-check: classify a stated discrepancy
   by its type and name the check that would support it.
4. *Explore and extend.* The run command of the product and the starter
   (ADR 016); the manual and the guided routes; the learner's own
   question; the optional materials track, labelled optional (criterion 5).

**The outcomes each product feature exercises** (the page names them):

| Product feature | Outcomes |
|---|---|
| Question selection and the archive | RR1 (candidate questions compared; self-ratings beside, never evidence; the archive with revisit conditions) |
| The registered plan and its freeze | RR2 (hypotheses, positive control, baselines, withheld part, stopping conditions declared before execution; a plan changed after it ran) |
| Source evidence | RR3 (claims linked to passages and assumptions; proposals logged for a person) |
| The run graph and the branch comparison | RR4 (states, valid resume, failed branches kept, lineage) |
| Roles and review | RR5 (bounded interfaces; a disagreement decided by a recomputed check; the human's decision) |
| Discrepancies and the follow-up | RR6 (a finding to a gap, competing explanations, a discriminating test, a revised claim; evidence against words) |
| The report and the bundle | RR7 (every number to a record; the bundle reproduced; memory with limitations) |

**Prerequisites.** RR7 (`checkable-reports-and-research-memory`), RR6
(`discrepancies-and-follow-up-experiments`), and EM8
(`rlc-circuit-measurements`); outside: "Planck's law of blackbody radiation
at the level of a first course in modern physics". No lesson of the site
teaches Planck's law (checked: only `quantum/08-atomic-spectroscopy`
mentions Planck), so the page states the law and what each symbol is before
the fit uses it, and links AST6 (`cosmic-expansion`) for the background.

**Budget.** The fits are linear over 43 points; the positive control 100
seeds; the coil analysis reads about 1 MB of the pilot's sample. Expected a
few seconds, inside the page budget; measured in part 3.

**Verification of the page.** A new lesson: `./scripts/verify.sh --base`
at least, the full run when the targeted run reports it (ADR 017 decision
7); in a session the owner's rule applies (no full run; the criterion is
then `pr_ci` pending).

## `products/research-workspace/`

Part 1: `README.md` (brief, criteria, run it, routes, limits),
`examples/` (the reproduction's project input and its question file),
`fixtures/` (placeholders). Part 2: `examples/coil-loss/` (the
registration, the question file, the readings template). Part 3: the
reference workflow, the assessment rubric, the manual route, the guided
route, `materials-track.md`, and `starter/` with a `pending` pin: the
learner writes the registration of their own question and the analysis of
one explanation, against the verified lower-level modules. The guided
route names the coding agent workflow of `docs/coding-agent-workflow.md`;
whether it also names Agent Codeyard, as optional, follows what SA9
decides (F139's narrower go; open question 8).

## The optional materials track (criterion 5)

Design only, recorded in products/research-workspace/materials-track.md
in part 3, labelled optional on the page, never a dependency of criteria
1 to 4, implemented only when the owner schedules F110 or asks.

- **The example question.** Which of a small declared set of model crystals
  is best for a stiff, light, insulating, and stable material, computed
  with the course's own models: the speed of sound a sqrt(K/m) of the chain
  (MAT1, `pbc.materials.phonons`), the band gap of the alternating
  tight-binding chain (MAT2, `pbc.materials.bands`), the stiffness of a bar
  by finite elements (MAT3, `pbc.materials.elasticity`), and the
  equilibrium vacancy fraction at an operating temperature (MAT4,
  `pbc.materials.defects`).
- **The constraints**, explicit and physical, each recomputed for every
  candidate: band gap at least a stated value; vacancy fraction at the
  operating temperature at most a stated value; a positive, finite
  stiffness; the objectives stiffness per mass and speed of sound, both to
  be maximised, with no weighting assumed: the recomputed Pareto front.
- **The comparison.** An agent's ranking (recorded, replayed) against the
  recomputed constraint checks and the Pareto front; a candidate the agent
  ranks first that fails a recomputed constraint is shown as such.
- **Its lesson.** R5 (F110) if it exists, reused and linked; otherwise the
  track stays a design. **Capacity:** R5 would be the 128th lesson; it
  needs the owner's decision on the limit of 127 (below).

It belongs in part 3, as the short design document the criterion asks for;
its implementation is later and the owner's call.

## Capacity

Checked on 2026-11-25 by reading `site/curriculum.yaml` and the front
matter: 123 lesson pages, 123 slots, 117 slots filled; unfilled SA9, MD10,
AE7, RR8 (core) and AI8, R5 (extensions). The limit is 127 lessons (the
owner's decision of 2026-11-15, Issue #543). With the four product
capstones the site has 127 lessons: RR8 fits, and it is the last lesson
inside the limit. An extension lesson (AI8, R5) or any other new page
needs the owner's decision on the limit first.

## Steps of part 1

1. Instructions of part 1 on the Issue; the handoff note.
2. The dataset gate of `cobe-firas-monopole`: download once, inspect,
   card, dossier, sample, reader, reference figure, parsing test; the
   register entry of the paper with the statements a person checked (open
   question 5).
3. `firas.py` with its tests (the Planck function against a closed-form
   limit, the distortion shapes against numerical derivatives, the fit on
   the positive control).
4. `registration.py`, `questions.py`, `discrepancy.py`, `sources.py` with
   their tests (a registration in which two explanations predict one
   outcome is refused; a discrepancy typed without its check is refused).
5. `graph.py` over `evidence.resumable` and the branch comparison; `log.py`;
   `review.py` (the scripted reviewer); `project.py`.
6. `report.py` and `view.py`; the command line; the example project.
7. `agent.py`, the recording command, the placeholder fixtures and their
   replay test.
8. Documents: `docs/products.md` (a section of F155 part 1),
   `docs/architecture.md`, `docs/project-map.md`.
9. The targeted verification, run last; `--base` or full as it reports
   (in a session: no full run, the owner's rule).

Parts 2, 2b, 3, and 4 get their steps on the Issue when they start.

## Acceptance criteria and the parts that clear them

| Criterion | Gate | Part |
|---|---|---|
| 1. As F145's criteria 1, 3, 4, 5, 6 for this product, without hardware | F145-1 `owner_approval` or a fresh-clone run recorded on the Issue before the merge (part 3); F145-3 `implementation` (parts 1, 2); F145-4 `implementation` and `pr_ci` (parts 1, 3; the starter's pending pin skipped and named); F145-5 `implementation` (part 3); F145-6 `implementation` / `pr_ci` (every part) | 1, 2, 3 |
| 2. Reproduced figures from documented inputs; discrepancies typed; a negative result can pass | `implementation` | 1 |
| 3. Every claim with a source or run link and a status; a report never shown as proof | `implementation` | 1 (reproduction), 2 and 2b (investigation) |
| 4. Both tracks end to end without a model account | `implementation` | 2 |
| 5. Optional: the materials track designed | `implementation` | 3 (design only) |

F145's criterion 3 for this product: invalid inputs and attempts detected
(a sample whose checksum changed, a fit that fails its control, a stage
that raises, a branch resumed from an invalid state), refinement and
repetition recorded (the branches and their decisions, the seeds of the
positive control, M5), and the export with the raw inputs (the samples by
digest), the report, and the evidence package naming the execution mode of
every run.

## Open questions for the owner

**Decided on 2026-11-25** (the comment "Owner's decisions on the plan's
nine questions"): questions 1 (option A), 2 (the static view), 3 (after
part 2), 4 (hold the gate, ask LAMBDA for written permission if needed;
link-only is a last resort), 5 (the implementer quotes, the owner confirms
before part 1 merges), 6 (part 2b before part 3, or part 3 first with
`not evaluated` if the bench is more than about two weeks away), 8 (at most
an optional reference), and 9 (part 0 as its own plan-only pull request)
as the review proposed. Question 7 stays open. The list below keeps the
questions as they were put.

**Open since the gate of part 1 (2026-11-25): question 10.** Is the basis
for the FIRAS rights that the gate found (see "Discoveries") sufficient
for `equivalent-permission`, or does LAMBDA's written permission come
first (question 4's decision)? *Recommendation: ask LAMBDA; the basis is a
general NASA policy, not a statement about this file, and the file has
no stated licence (ADR 007 addendum, decision 1).*

11. **The paper's covariance between frequencies** (new, part 1). A
    branch b6c that weights with the paper's Q (section 3.3, 43 numbers)
    would answer the open finding `review-covariance-weighting` and give
    the statistical errors as the paper weights them; the numbers would
    be quoted from the paper on the register entry. *Recommendation: allow
    it as a small follow-up of part 1; until then the finding stays open,
    which is the honest state.*

1. **The FIRAS targets.** Option A (the spectrum fit with the scope of
   T0 above, the residual spectrum, the weighted rms, the bounds on y and
   μ), B (the spectrum fit and the figure only), or C (A and the dipole).
   *Recommendation: A.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
2. **The interface.** A static view written by the command line (no
   socket, Level 2), or a served local page like SA9's (a new listening
   socket, the security trigger, Level 3). *Recommendation: the static
   view; nothing in the workspace runs long or needs a stop.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
3. **When the bench session F happens.** After the freeze (part 0), or
   after part 2 is merged, so that the analysis code is fixed before the
   measurement as well. *Recommendation: after part 2.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
4. **If the FIRAS rights cannot be established** from LAMBDA's and NASA's
   records: ask LAMBDA for a written permission, or keep the track
   link-only (the learner downloads; the build cannot run the track, and
   criterion 4 fails for it). *Recommendation: ask for the permission;
   do not start part 1's code until the gate decides.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
5. **Who checks the paper's statements** for the register entry: the
   implementer of part 1 reads the paper on arXiv and quotes it, and the
   owner confirms the quoted numbers on the Issue before part 1 merges.
   *Recommendation: as stated; the register's rule is a person's check.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
6. **The page before or after the measurement.** Part 3 waits for 2b, so
   the page shows a real outcome, or comes first with the follow-up
   `not evaluated`. *Recommendation: wait for 2b unless the bench is more
   than two weeks away.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
7. **The multimeter.** Its make and model; its accuracy formula on the low
   resistance range (percent of reading plus digits); its resolution on
   that range; whether it measures capacitance (G3 is dropped without a
   capacitance range). *Recommendation: tell them on the Issue before the
   freeze, so that the readings template names the meter and the
   uncertainty model of M4 can be checked against its specification.*
   *The review: stays open; it needs the owner's answer.*
8. **The guided route.** Name only the coding agent workflow, or also Agent
   Codeyard as optional. *Recommendation: follow SA9's decision in F145
   part 2.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*
9. **The freeze mechanism.** Part 0 as a pull request with this plan only,
   merged after your approving review. *Recommendation: as stated; a
   comment on a branch commit is weaker, since a branch can be rewritten.*
   *The review's proposal (2026-11-25): take over the recommendation;
   a proposal until the owner confirms it on the Issue.*

## Out of scope

Unrestricted autonomy; a public preprint platform; any claim of novelty;
materials discovery as a compulsory domain; a served page unless the owner
chooses it; changes to `pbc.research`, `pbc.evidence`, `pbc.agents`,
`pbc.products.physics_lab`, `pbc.instruments`, or the `ad3-rlc-pilot`
reader; a correction of SA9, SA3, SA4, or EM8 (a follow-up Issue if the
outcome requires it); the starter's pin bump before part 3 merges; a new
dependency group.

## Discoveries during the work

- (2026-11-25, part 1, the dataset gate of `cobe-firas-monopole`) The file
  is at the expected address: `firas_monopole_spec_v1.txt`, HTTP 200,
  2,388 bytes, sha256
  `df793c3dca09ebfa7dbc5aa0ec1951daa8884431bc30eff28a710d7516cf50fa`
  (computed; LAMBDA publishes no digest), plain text, so no FITS and no
  conversion. Header: 18 comment lines, then 43 rows of five columns,
  2.27 to 21.33 cm^-1. Its words: "Column 2 = FIRAS monopole spectrum
  computed as the sum of a 2.725 K BB spectrum and the residual in column
  3, units = MJy/sr"; columns 3 to 5 "from Table 4 of Fixsen et al.", in
  kJy/sr (residual, 1-sigma uncertainty, modeled Galaxy spectrum at the
  poles); "v1 : initial release, May 2005". LAMBDA's product page
  (`https://lambda.gsfc.nasa.gov/product/cobe/firas_monopole_spect.html`)
  names the source of T_ref: "Subsequent analyses by Mather et al. (1999)
  and Fixsen et al. (2002) improved the FIRAS calibration accuracy and
  provided a best-estimate for the absolute CMB temperature of 2725 +/- 1
  mK", and its file table gives the delivery date 2003-03-01. So
  T_ref = 2.725 K from Fixsen & Mather (2002), ApJ 581, 817, while the
  residuals are those of the 1996 paper's Table 4. Against which
  blackbody the 1996 residuals were taken is to be quoted from the paper
  at the register entry, not assumed.
- (2026-11-25, the gate's rights, read that day) LAMBDA
  (`https://lambda.gsfc.nasa.gov/contact/`, "LAMBDA's Mission and Use
  Acknowledgement Statement"): "There is no cost involved in the use of
  LAMBDA; however, if your research benefits from its use then we request
  that you include the following acknowledgement in your publications:
  ... 'We acknowledge the use of the Legacy Archive for Microwave
  Background Data Analysis (LAMBDA), part of the High Energy Astrophysics
  Science Archive Center (HEASARC). HEASARC/LAMBDA is a service of the
  Astrophysics Science Division at the NASA Goddard Space Flight
  Center.'" No licence is stated on LAMBDA's pages for the file. NASA SPD-41
  (Scientific Information Policy for the Science Mission Directorate,
  2021, as the PDF linked from
  `https://science.nasa.gov/researchers/science-information-policy/`
  holds it), section IV, footnote 22: "Mission data are released into the
  public domain and non-SMD-funded activities have no requirements with
  respect to the usage of that data"; section III, footnote 7:
  "Government works are by default in the U.S. public domain and should
  be used if no other license applies." NASA Astrophysics Scientific
  Information Management Policy (APD Policy-13, v1.8, 2023), section 3.2
  f: "If there are no other restrictions on the data, the data shall be
  released with a Creative Commons Zero license." The HEASARC FAQ asks for
  an acknowledgement in publications. NASA's media guidelines cover
  images and media, not data tables. **The gate's assessment:** the four
  answers would be "permitted" on this basis, but it is a general policy
  of the agency, written after the file's release, not a statement about
  this file, whose columns are a table of a journal paper (ApJ, the AAS);
  ADR 007's addendum keeps a dataset "with no stated licence" uncommitted
  unless a written permission is recorded. So the rights are **not
  established** to the standard of the TESS card (MAST's own statement
  for its holdings), and under the owner's decision 4 the sample is not
  committed and no fitting code is written until the owner decides
  (question 10). No card, dossier, sample, or code was written.

- (2026-11-25, the owner's review) The review read the registration's
  "stated accuracy divided by sqrt(3)" as a reduction by averaging three
  readings. The supervisor's assessment, for the owner: the division is
  the conversion of an accuracy limit of half-width a to a standard
  uncertainty under a rectangular distribution (Type B), not an
  averaging, and the earlier text already combined it with the standard
  error of the three readings. The text was rewritten anyway, as the
  review asks, because it could be misread and left real points open (the
  offset and the gain part against the zero, the drift of the zero, the
  resolution); the check of the thresholds then found that the gain of
  the meter had been counted twice in u of G1.
- (2026-11-25, the owner's review) The LAMBDA file's blackbody is at a
  reference temperature; a linear fit with a free ΔT returns that
  reference to first order whatever it is. The track's goal is therefore
  the published spectrum fit, and the absolute T0 is expected to be
  `not-reproduced`, typed `method`.

- (2026-11-25, the plan) The rules of `research.ideas.assess`,
  `research.plan.check` and `execute`, `research.followup.Log.record`, and
  `research.literature.label` are bound to the throw laboratory and its
  `Record`; the workspace applies the same rules in its own modules and
  changes none of them.
- (2026-11-25, the plan) `research.followup.FollowUp` holds exactly two
  explanations; G2 has three, so `registration.discriminates` is written
  over n explanations with the same rule.
- (2026-11-25, the plan) The live adapter fixes the input ranges (channel 1
  at 5 V, channel 2 at 50 V), so the same-node sweep M3 measures the
  mismatch of exactly the pilot's configuration with the unchanged input
  file; no physics-lab code is needed for session F.

- (2026-11-25, part 1 session 2, the gate) The paper's Table 4 (arXiv v1,
  read in the session, not committed) equals columns 1, 3, 4, and 5 of the
  file row for row. The caption of its Fig. 5 reads "FIRAS measured CMBR
  residuals, I0 - B_nu(T0) - DeltaT dB/dT - G0 g(nu)": the residuals are
  those left after the paper's own fit of dT and a Galactic term, so a
  refit returns dT and G close to zero by construction, and the rows of
  the weighted rms and the residual figure are reproduced by construction.
  The workspace says so on every such row (`reproduction.PAPER_REFERENCE_NOTE`),
  and the scripted reviewer's check `by-construction-stated` holds it.
  Column 2 rebuilds from B_nu(2.725 K) plus column 3 to within 0.8 kJy/sr
  with the CODATA 1986 constants (7.6 kJy/sr with the SI 2019 ones). The
  paper's section 3.3 lists the 43 values of Q of its covariance between
  frequencies; part 1 does not use them (the fits are diagonal), and the
  review's finding `review-covariance-weighting` stays open. Whether a
  branch with the paper's Q may be added (43 numbers quoted from the
  paper, beyond "short statements") is question 11.
- (2026-11-25, part 1 session 2) A scratch fit of the file ran in the
  session before the example registration was written, to see the sizes
  (dT 0.54 +- 8.06 microK, chi-square 45.0 for 41, weighted rms 49.25
  ppm, y 0.09 +- 3.61 x 1e-6, mu -0.90 +- 3.43 x 1e-5). The registered
  rules are this plan's, written before it, with one exception: the rule
  of the residual figure ("within 1 sigma of the published residuals at
  every frequency", `reproduction.FIGURE_SIGMA`) was set in this session,
  because the plan said only "compared by the numbers it shows"; the
  regenerated residuals lie within 0.02 sigma. The owner's review of
  part 1 (2026-11-25) keeps it as **post-hoc, not preregistered**: the
  example registration's criterion carries the reason (`post_hoc`),
  `reproduction.mark_post_hoc` copies it onto the row, and the report,
  the claim's text, and the view show the verdict as "reproduced
  (post-hoc rule, not a confirmatory result)".
- (2026-11-25, part 1 session 2) The weighted rms is read as
  sqrt(sum (Delta/sigma)^2 / sum 1/sigma^2): the PDF's text layer gives
  the formula's symbols without its layout. The owner checked it and the
  other quoted values against the typeset article and confirmed them on
  the Issue (2026-11-25); the register entry records the confirmation.
- (2026-11-25, part 1 session 2) Modules: `reproduction.py` was added (the
  rows from the registered criteria); `coil.py` is part 2's. The reference
  temperature is read from the card (`reference_temperature`), and the
  reader refuses a header that names another one. The Galactic term
  lowers chi-square by 0.00, so the declared criterion stops b1 as well;
  the rows still rest on b1, which the registration names. `pbc.agents.investigation`
  is not reused: the rule that an agent's finding is accepted only
  through a recomputed check is applied by `log.Log.accept`. The harness
  allows four tool calls per message, so the scripted reviewer spreads its
  eight checks over two messages. The positive control gained a
  `noise_scale` so that its own test shows it failing on understated
  uncertainties. The view was looked at as a desktop render only (a
  thumbnail by `qlmanage`), not at phone width; the impeccable detector
  did not run (the adapter forbids it).

