# Planning change: Part B — scientific agents, model discovery, evaluation, and research products

Date: 2026-11-01. Owner: Ahmet Taspinar.
Status: Draft for owner review and subsequent Project Grill / planning reconciliation.
Proposed repository destination: `docs/changes/part-b-scientific-products-and-research.md`.

This consolidated draft supersedes the proposed curriculum in the 2026-10-31 draft `part-b-product-led-learning-paths.md` for review purposes. It incorporates the subsequent AI-Scientist discussion and the report `PBC_repository_onderzoek.md`. It does not supersede approved project requirements until adopted through the project workflow.

This document proposes a curriculum and scope change. It does not assert owner approval, create Issues, allocate feature IDs, change the repository, or authorise a hardware purchase. Planning must reconcile the live repository before implementation.

## 1. What I want

Reorganise Part B around four coherent method paths. Each has an explicit scientific outcome, a sequence of substantive lessons, and a capstone that produces a reusable software product:

1. Build reliable scientific agents and automate experiments.
2. Discover physical models through active experiments.
3. Evaluate scientific agents and establish their limits.
4. Conduct reproducible research with bounded agent assistance.

The progression is experiment execution → model discovery → system evaluation → reproducible research. Each path is independently accessible at its declared prerequisites, with prepared starter code where earlier products would otherwise be required.

Use Agentic Coding Template (ACT) as the guided development workflow for capstones, with progressively greater learner independence. Retain an equivalent manual development route. Scientific reasoning and verification remain the learning objectives; learning ACT internals is not a prerequisite.

Permit optional local hardware acquisition and instrument control for the first two capstones. Every essential learning objective must remain achievable through an interactive simulator without hardware or a paid model account.

## 2. Why change the current curriculum

The current 33 Part B slots contain valuable material, but mix foundational skills, methods, physical examples, and specialised applications. Experiment design, verification, review, and failure analysis overlap without always stating what new competence a later lesson adds. Some titles identify scenarios rather than distinct learning outcomes.

The earlier six-lessons-per-path proposal compressed important topics too far. This revision explicitly retains scientific simulation development, multimodal observation, counterexample hunting, differential-equation discovery, hidden variables, invariants, and generalisation across systems.

Products give each path a destination, but must not narrow Part B to electronics. Electronics is the recommended first capstone implementation; mechanics, thermal physics, waves, and materials remain meaningful teaching contexts. Simple oscillators remain useful exercises, not the entire capstone.

## 3. Proposed curriculum

The codes below are temporary references in this document, not replacements for existing lesson IDs, URLs, feature IDs, or curriculum labels.

The proposal contains 30 taught lesson slots and four capstone slots: 34 core Part B slots in total. This replaces the current 33-slot Part B with 34 core slots. With Part A at 81 and the reference Lean slot at one, the proposed reference curriculum becomes 116 slots. Actual retained published extras must be reconciled separately; preserving the previous count is not a goal. Optional extensions are outside this core. Published legacy pages retained beyond the revised slots must be counted separately rather than hidden or counted twice.

| Path | Existing stable path key | Taught lessons | Capstone | Core slots |
| --- | --- | ---: | ---: | ---: |
| Reliable scientific agents and experiment automation | `reasoning` | 8 | 1 | 9 |
| Physical model discovery through active experiments | `law-discovery` | 9 | 1 | 10 |
| Scientific agent evaluation and improvement | `benchmarking` | 6 | 1 | 7 |
| Reproducible research with agents | `autonomous-research` | 7 | 1 | 8 |
| Total | | 30 | 4 | 34 |

### 3.1 Path 1 — Reliable scientific agents and experiment automation

Central question: how can an agent execute several kinds of experiment while producing independently checkable results?

| Ref | Lesson | Required outcome |
| --- | --- | --- |
| B1.1 | From research question to experiment specification | Define hypotheses, variables, observables, units, success criteria, permitted actions, and stopping conditions. |
| B1.2 | Building and verifying scientific simulation tools | Translate a physical model into tested numerical code; check convergence, reference limits, units, and invariants; verify coding-agent output. |
| B1.3 | Connecting simulators and instruments | Implement a small common interface for configuration, excitation, acquisition, units, validation, and instrument-state snapshots, with simulator and optional hardware adapters. |
| B1.4 | Measurement quality and multimodal observations | Address calibration, sampling, noise, clipping, and missing data; connect numerical measurements to plots, diagrams, and selected image/video observations with uncertain interpretation made explicit. |
| B1.5 | Building a bounded experiment agent | Implement planning, validated tool calls, result inspection, recovery, budgets, and stopping; compare with a scripted execution route. |
| B1.6 | Running adaptive and resumable measurement campaigns | Execute sweeps, repeats, and local refinement; link suggestions to actual measurements; handle interruptions, valid checkpoints, cleanup, and incomplete runs under a known protocol. |
| B1.7 | Counterexamples, physical constraints, and falsification | Deliberately challenge conclusions and assumptions; use dimensions, symmetries, limiting cases, and conservation checks to reject plausible errors. |
| B1.8 | Traceable explanations and experiment reports | Link each quantitative claim to runs, data, plots, assumptions, and uncertainty; distinguish observed, computed, and proposed statements. |
| B1.C | Capstone: Autonomous Physics Lab | Deliver a reusable application for multiple experiment protocols, with independent numerical checks and exportable evidence. |

Capstone requirements:

- Initial reference environment: electronic circuits and signals, using simulation and an optional programmable instrument such as Analog Discovery or Red Pitaya. Device selection remains subject to feasibility work.
- At least three distinct protocols: frequency response/resonance; transient response; amplitude-dependent response in a bounded nonlinear example. Merely changing one parameter in the same demonstration is insufficient.
- Plan and run a measurement campaign, detect invalid measurements, refine sampling, compare repetitions, and export raw data plus a report.
- A local interface exposes configuration, progress, results, and failures. The instrument adapter is a separate layer from physical models and agent orchestration.
- A prepared real circuit does not rewire itself: manual topology changes are explicit; automatic switching requires separately scoped switching hardware.
- The outcome is an educational/experimental tool with documented operating limits, not a certified laboratory instrument.

### 3.2 Path 2 — Physical model discovery through active experiments

Central question: what physical model explains an unknown system, what remains ambiguous, and which experiment should come next?

| Ref | Lesson | Required outcome |
| --- | --- | --- |
| B2.1 | Unknown systems, priors, and competing models | State system boundaries, accessible variables, candidate structures, and prior assumptions; compare knowledge-informed and restricted-prior conditions. |
| B2.2 | Parameter discovery and system identification | Fit known model structures in time and frequency domains; inspect residuals and parameter sensitivity. |
| B2.3 | Discovering functional forms with symbolic regression | Compare PBC's transparent grammar with an optional broader search engine; investigate operator choices, complexity, units, and withheld prediction. |
| B2.4 | Discovering differential equations | Infer dynamics from trajectories; compare transparent sparse methods and optional PySINDy routes, including weak formulations where useful; test state selection, derivatives, and new trajectories. |
| B2.5 | Noise, uncertainty, and identifiability | Quantify uncertainty, parameter correlations, noise sensitivity, and observationally equivalent explanations. |
| B2.6 | Hidden variables and failures of known laws | Diagnose missing states, forces, or inadequate models; compare genuinely distinguishable extensions of a known law and state unresolved ambiguity. |
| B2.7 | Discovering conservation laws and invariants | Search for quantities constant along trajectories and distinguish approximate numerical constancy from a justified physical invariant. |
| B2.8 | Active experimental design | Choose experiments to discriminate models or reduce uncertainty; compare scripted, classical adaptive, LLM, and hybrid strategies under equivalent budgets and appropriate scientific objectives. |
| B2.9 | Generalisation across signals, regimes, and systems | Separate interpolation, new excitation, new parameters, new regimes, and structurally different systems; report where transfer fails. |
| B2.C | Capstone: System Discovery Lab | Deliver an application that actively characterises unknown systems and validates an identified model on withheld experiments. |

Capstone requirements:

- Use a bounded family containing several circuit structures, coupled resonances, and at least one nonlinear case; do not promise unrestricted circuit reconstruction or arbitrary law discovery.
- Select measurements, rank candidate explanations, estimate parameters and uncertainty, and test predictions using withheld excitation signals and conditions.
- Include an underdetermined case where the correct outcome is that the measurements do not distinguish the models.
- Reuse Path 1's instrument contract, with starter adapters for independent entry. A thermal-system implementation is an alternative after feasibility validation.
- Assess symbolic discovery, equation discovery, and invariant discovery in their lessons using appropriate physical systems; not every method must be forced onto the electronics capstone.
- Include a transfer exercise outside electronics so successful circuit identification is not presented as general physical intelligence.

Path boundary: B1.6 refines execution of a known measurement protocol. B2.8 chooses an experiment because competing physical explanations make different predictions.

### 3.3 Path 3 — Scientific agent evaluation and improvement

| Ref | Lesson | Required outcome |
| --- | --- | --- |
| B3.1 | Defining scientific quality | Define separate metrics for correctness, reasoning, evidence, completion, cost, and measurement efficiency; include conceptual and physical-tool understanding. |
| B3.2 | Building tasks and hidden test worlds | Create numerical, conceptual, diagram-based, and interactive tasks; withhold truth and evaluation cases from agents. |
| B3.3 | Fair baselines and comparison protocols | Compare deterministic workflows, models without tools, and agents using equivalent information and budgets; control prior-knowledge access. |
| B3.4 | Independent scoring, sealed evaluation, and provenance | Have the evaluator compute scores and resource measurements; separate unverified candidate diagnostics; freeze a candidate before a final withheld evaluation and record version-bound evidence. |
| B3.5 | Robustness and statistical uncertainty | Repeat trials, perturb observations, inject tool failures, and quantify variation and uncertainty. |
| B3.6 | Failure analysis, reviewer evaluation, and regressions | Test reviewers on controlled correct/incorrect cases, classify missed errors and false alarms, run ablations, and detect evaluator overfitting and regressions. |
| B3.C | Capstone: Scientific Agent Testbench | Deliver a reusable comparison and diagnostic application with reproducible evaluation reports. |

Evaluate supplied agents or earlier capstone products. Include conceptual reasoning and diagram interpretation as well as executable experiment tasks. Expose failures, cost, sample efficiency, variation, and per-task performance rather than only one aggregate score. Heavy live evaluations are separate from ordinary CI; committed fixtures and replay evidence support deterministic checks.

### 3.4 Path 4 — Reproducible research with agents

Central question: how do we choose a worthwhile question, conduct a bounded investigation, and connect every conclusion to reproducible evidence?

| Ref | Lesson | Required outcome |
| --- | --- | --- |
| B4.1 | Generating and selecting research ideas | Formulate several candidate questions; compare scientific interest, feasibility, resources, falsifiability, and possible contribution. Use an idea archive, without treating self-ratings as objective evidence. |
| B4.2 | From a question or publication to a research plan | Scope a replication or original investigation; declare hypotheses, baselines, budgets, stopping conditions, withheld tests, and success criteria before execution. |
| B4.3 | Literature, novelty assessment, and evidence maps | Search and compare verified sources; distinguish supporting, contradicting, and insufficient evidence; link claims to passages and assumptions. A limited search cannot certify novelty. |
| B4.4 | Reproducible and resumable research pipelines | Connect data, code versions, configurations, run states, figures, and claims. Retain failed and negative results; resume only from valid states and record lineage of alternative branches. |
| B4.5 | Multi-agent investigation and scientific review | Give extraction, implementation, and critical-review roles bounded interfaces; include meaningful human steering and independent checks rather than consensus alone. |
| B4.6 | Discrepancies, ablations, and follow-up experiments | Turn a review finding into a knowledge gap, a discriminating experiment, new evidence, and a revised claim; compare alternatives and document why a branch is continued or stopped. |
| B4.7 | Independently checkable reports and research memory | Generate evidence-linked reports and reproducible bundles; validate citations and quantitative statements. Store ideas, code, data, results, limitations, and unresolved questions for checked reuse. |
| B4.C | Capstone: Scientific Research Workspace | Deliver a local research application supporting both tracks below and complete one substantive investigation. |

Two tracks share software and evidence standards:

- Reproduce one substantive published result and conduct a bounded extension.
- Investigate a bounded original question with declared baselines, independently checked claims, and reproducible evidence.

The local application must expose question/idea selection, an executable plan, source evidence, experiment history, review findings, follow-up decisions, and report export. A small run graph is sufficient; unrestricted open-ended autonomy is not required. Provide a curated feasible paper and a prepared original-question example as reference routes.

Record a bounded exploration of alternatives. A simple guided branch comparison can satisfy this requirement; tree search is an optional advanced method whose extra cost must be justified against a sequential baseline. Preserve why ideas were rejected, which attempts failed, and what would warrant revisiting them.

Make evidence status visible: completed, failed, inconclusive, not evaluated, or independently checked for a specified claim. Producing a paper is not proof that the investigation succeeded. Revising prose after review does not count as resolving a request for new scientific evidence.

Materials discovery remains an advanced extension, including physical feasibility and multiple competing objectives, rather than a compulsory domain. A negative or non-reproduced result can pass when the evidence and analysis justify it; novelty is not guaranteed. No public preprint platform is required.

### 3.5 Prerequisites, breadth, and independent entry

The recommended progression is Path 1 to 2 to 3 to 4. It is not a requirement to finish all of Part A or all earlier products. Each lesson declares the specific physics, mathematics, and code it needs. The planner maps these prerequisites to actual published lessons and validates the graph; do not assume a planned Part A lesson is already available.

Use mechanics and numerical-methods examples for initial agent and verification exercises, circuits/waves for the initial lab product, and a thermal or other physical context for transfer. Equation and invariant discovery may use different systems from the capstone. Curate one complete independent-entry starter per path, with already-verified lower-level components and clear boundaries on what the student must build.

Published lessons must remain substantial and self-contained at their stated prerequisite level. A repository README, framework installation guide, or link to an external tutorial is not a replacement for the physical argument, worked examples, and interpreted results. Capstones should name which lesson outcomes each product feature exercises; advanced variants cannot silently become prerequisites for the core route.

## 4. ACT and software-product delivery

Distinguish a coding agent used to build an application from a scientific agent executed inside it. ACT supports development; it does not establish scientific truth.

Each capstone provides a version-pinned starter, a product brief, scientific acceptance criteria, example inputs, a local run command, a reference workflow, an assessment rubric, and a manual/no-paid-model route. Prefer a thin local interface over spending the course on generic frontend infrastructure. No compulsory cloud deployment, user management, billing, or hosted service is introduced.

| Path | Development autonomy |
| --- | --- |
| 1 | Guided specification, small features, supplied scientific criteria, and focused review. |
| 2 | Learner-defined feature breakdown and model-validation criteria. |
| 3 | Evaluation evidence used to assess changes and prevent regression. |
| 4 | Independent bounded planning, implementation, review, and reproducible delivery. |

Use ACT at a pinned, demonstrated version and document only the commands the learner needs. Do not assume proposed lightweight ACT capabilities already exist. If ACT cannot support the intended teaching flow without modification, scope that work separately rather than making PBC depend on an unimplemented feature. Follow ACT's applicable approval rules without adding repeated gates to ordinary learner actions.

All products must demonstrate a usable end-to-end workflow, useful export, documented failures, and a reproducible installation. They are applications, not notebooks with a product name. Shared components should be extracted only when actual reuse warrants them; four microservices or one general scientific platform are not prerequisites.

### 4.1 Existing PBC components are the starting point

Reuse the existing bounded agent loop, tool allowlists, replay infrastructure, experimental-design scoring, discovery protocols, hidden worlds, baselines, power-law symbolic regression, and scientific review lab. The review lab already compares a correct and a deliberately faulty integrator; reviewer benchmarking extends its fault coverage and repeated assessment rather than recreating it.

Do not replace these components merely to align with an external framework. Distinguish research-agent autonomy from coding-agent permissions. A guided optional exercise may let an agent change experiment code in an isolated simulator workspace, with independent validation before the code is admitted to a scientific workflow. Unreviewed generated code must not gain direct instrument access.

### 4.2 One minimal capstone evidence contract

Extend existing PBC protocols only where capstone products need additional structure. Pilot before generalising. The contract records:

- Task, hypothesis, assumptions, protocol version, dataset split, seeds, budgets, code/configuration identities, and environment.
- Per-attempt status, failure diagnostics, raw or derived artifact references, and links to prior attempts.
- Evaluator-computed correctness and performance, separately from candidate-reported diagnostics.
- Claim-to-run and claim-to-source links, with a stated evidence status and scientific scope.
- A frozen selected candidate and a versioned final evaluation whose feedback is not used to tune that same candidate.

The evaluator recomputes scores and relevant resource use. Candidate logs and self-reported costs are not trusted evaluation. After a change based on final-test feedback, the next result belongs to a new development/evaluation cycle; do not relabel repeated test tuning as independent final validation.

A test called “private” is not private if the agent can read its inputs, labels, evaluator answers, or aliases. State the actual isolation assumptions. Fully open teaching tasks still support a guided no-model route, but cannot substantiate a claim that an informed agent never saw public ground truth. Separate hidden-value access in a run from possible prior knowledge of public problems.

A digest establishes identity, not scientific truth. A checksum alone need not establish that a whole physical field is correct. Numerical verification uses appropriate observables, full state comparisons where needed, convergence, units, invariants, and independent reference cases. Statistical and physical uncertainty remain explicit.

## 5. Hardware and reproducibility boundary

This explicitly proposes amending requirements decision 28, which currently excludes sensor, recording, instrument-control, and physical-laboratory lessons.

Permit bounded local instrument-control extensions supporting these capstones. Keep buying hardware optional. No purchase is authorised by this document, and no device is selected solely from a product description.

The feasibility spike must establish supported OS and drivers, Python access, acquisition and excitation limits, calibration needs, equipment and accessory bill of materials, total acquisition cost, realistic experiment duration, failure handling, and a successful physical pilot. Electronics is the initial recommendation; thermal hardware and drones are alternatives/extensions, not simultaneous baseline commitments.

Separate three execution modes:

1. Interactive deterministic simulation: supports new experiments, hidden systems, active selection, and full assessment without equipment.
2. Recorded measured data: supports real noise and reproducible analysis, but cannot be represented as executing a new physical experiment.
3. Optional live hardware: executes new physical measurements locally; results vary and use declared tolerances and uncertainty.

Live hardware and paid models are never required by site builds or ordinary CI. Drivers are optional dependencies. Record device, calibration, configuration, timestamps, units, processing, and operating conditions. Captured data undergo the existing provenance/licensing/feasibility review before publication. Hardware runs are evidence of physical operation; simulator success alone is not.

Enforce permitted operating ranges, interlocks, timeouts, and stop behaviour outside the language model. The agent can request only validated bounded operations. No autonomous mains-voltage work or unrestricted actuation is included.

The public PBC website remains static and needs no account, secrets, instrument connection, upload endpoint, or runtime LLM service. Upload/import and instrument control belong to learner-run local applications. Experimental local-app outputs are distinct from deterministic published lesson artifacts; no global reproducibility tolerance is introduced to accommodate live measurements.

## 6. Coverage of all existing Part B slots

This is a learning-outcome mapping, not a claim that the mapped lessons have already been migrated or delivered.

| Existing slot | Proposed destination and treatment |
| --- | --- |
| AI0 | B1.1/B1.5; projectile experiment retained as introductory exercise. |
| AI1 | B1.2 and ACT-guided capstone development; explicit scientific simulation construction. |
| AI2 | B1.2/B1.7; retain code verification and debugging. |
| AI3 | B1.7; explicit counterexample hunting. |
| AI4 | B4.5; multi-agent scientific review. |
| AI5 | B1.3–B1.6/B1.C; measured data plus optional live experimentation. |
| AI6 | B1.4 and B3.2; images, diagrams, affordances, and counterfactual interpretation. |
| AI7 | B1.7/B1.8 and B2.3; explanations and physical constraints. |
| AI8 | B1.4 video exercise/extension, with quantitative extraction, validation, and limits; no longer a dedicated core slot. |
| D1 | B2.1/B2.3; black-box force-law exercise outside electronics. |
| D2 | B2.1/B3.3; explicit prior assumptions and controlled prior-knowledge comparisons. |
| D3 | B2.6; challenge and extend a known law. |
| D4 | B2.2/B2.3 optional gravity exercise; not a required standalone lesson. |
| D5 | B2.1/B3.2; unknown simulated worlds with withheld truth. |
| D6 | B2.2/B2.5; inverse problems, correlations, and uncertainty. |
| D7 | B2.3; symbolic regression. |
| D8 | B2.4; dedicated differential-equation discovery. |
| D9 | B2.8; hypothesis-discriminating active design. |
| D10 | B1.4/B2.5; discovery under measurement noise. |
| D11 | B2.6; hidden variables and observational ambiguity. |
| D12 | B2.9; explicit generalisation levels including different systems. |
| D13 | B2.7; dedicated invariant discovery. |
| EV1 | B3.1/B3.2; conceptual reasoning and physical-tool understanding retained. |
| EV2 | B3.2/B3.3; interactive discovery, unknown worlds, and prior-knowledge controls. |
| EV3 | B3.3; agent/non-agent baselines. |
| EV4 | B3.1/B3.5; robustness, cost, and sample efficiency. |
| EV5 | B3.6; scientific failure analysis. |
| R1 | B4.4, reusing existing pipelines. |
| R2 | B4.3; evidence maps. |
| R3 | B4.3/B4.7; verified literature and reproducible evidence. |
| R4 | B4.5/B4.C reproduction track. |
| R5 | B4.6/B4.C optional materials track; physical multi-objective constraints retained in that track. |
| R6 | B4.C original-investigation track; independent research remains possible. |

Not all former standalone topics remain compulsory. Full video-based inference, gravity discovery, and materials discovery are deliberate extensions. Their published pages remain accessible if already delivered. Planning must make the distinction between core objectives and optional depth visible, not claim identical coverage from a cross-link alone.

## 7. Requirements and architecture changes

Planning must propose precise amendments after checking the live files:

- Decision 23: replace the Part B distribution with the table above. Keep Part A and Lean scope unchanged. The proposed core becomes 116 slots: 81 Part A + 34 Part B + 1 Lean; calculate actual published totals separately.
- Decision 25: preserve four stable method-path keys and single primary physics-course placement; change their teaching order and outcomes and add capstone products. They remain method views over canonical lesson pages, not four duplicate course trees.
- Decision 26: preserve video and invariant-discovery outcomes and the listed scientific enhancements, recording which move to exercises/extensions. Existing Part A capstones are unaffected.
- Decision 28 and related non-goals: replace blanket hardware exclusion with the bounded optional-local exception in section 5.
- Decision 31: retain scientific quality, static-site boundaries, and historical feature records; clarify the distinction between local learner products and the hosted educational site.
- ADR 013 and any related metadata/count decisions: reconcile curriculum slots, capstone representation, primary homes, ordering, and count assertions. Determine whether an amendment or new ADR is needed; do not invent the next ADR number.
- Retain no-JavaScript access to lesson content, current dataset gates, optional agent execution, and verification obligations. Adapt atlas/home generators from canonical metadata; do not hard-code a second curriculum in pages.

No change is requested to Part A's eight-course structure, its sixteen designated measured-data labs, Lean's existing lessons, or the site's current visual design. A capstone's hardware dataset does not automatically become a seventeenth designated lab.

## 8. Transition and delivery order

### Stage A — Reconcile and approve the planning change

Inspect current main, lesson front matter, roadmap, ADRs, Issues, PRs, and in-progress worktrees. Produce an inventory with old slot, published lesson ID/URL, feature/Issue, implementation status, proposed destination, and action: reuse, extend, link, retain as extension, or replace unimplemented scope.

The open-Issue lookup on 2026-11-01 returned #345, F98 (D10–D12), directly relevant to B2.5/B2.6/B2.9. PR #351 for F133 / #338 was open and unmerged when inspected; it changes the atlas, not the Part B scientific curriculum. Coordinate curriculum metadata and sequence descriptions with that work, without recreating the navigation. Capacity work includes #150 (F113) and #278; recheck before projecting verification cost at the revised lesson count. These observations are not a complete backlog or worktree reconciliation.

Keep published URLs, IDs, code, and evidence accessible. Reuse delivered lessons wherever they meet an outcome; extend them through new dependent work rather than rewriting delivered feature history. Never reuse retired IDs or silently change the meaning of an old slot label. Allocate final new labels and feature IDs only after the inventory. Update/close superseded unimplemented Issues with explicit successor links.

Complete requirements, ADR, curriculum, roadmap, and generator/count updates as one internally consistent planning change. Existing working pages must remain valid throughout transition; an unfilled new slot must not be labelled published.

### Stage B — Feasibility and one vertical slice

Implement the minimal evidence contract on one existing simulated task first, proving evaluator independence and version binding. Then validate one simulated and one optional physical electronics protocol through the same instrument contract. Demonstrate a scripted baseline, bounded agent route, report, deterministic CI fixture, and real captured trace. Check licence/driver constraints and actual runtime before committing to a device or general hardware framework.

Pilot ACT on a small real capstone feature and verify the equivalent manual route. Use this evidence to size the backlog and set practical learner workload expectations; do not promise durations before the pilot.

### Stage C — Deliver Path 1, then Path 2

Publish useful independently verifiable slices of the experiment lab before extending it into model discovery. Develop the parameter-identification and uncertainty work from existing PBC implementations where appropriate. Validate lessons across more than one physical context.

### Stage D — Deliver the evaluation and research products

Basic baselines and scientific checks are present from Stage B, not postponed until Path 3. Path 3 then deepens them into a reusable evaluation product. Path 4 reuses evidence, data, and execution components where useful and pilots one feasible reproduction before opening the original-research route.

Create Issues just in time in dependency order. Lesson slots need not correspond one-to-one to features. This request does not mandate parallel agents, a new orchestration framework, or a large shared platform.

## 9. Acceptance of the planning change and of delivered content

Planning acceptance:

1. Every old Part B slot and every published Part B lesson has an explicit disposition; no published address disappears and no in-flight work is silently duplicated.
2. Final metadata expresses the four paths, 30 taught slots, and four capstones consistently; tests and generated pages agree, with legacy extras counted honestly.
3. Required outcomes from section 6 are attached to substantive lesson/exercise acceptance criteria, including the deliberate optional topics.
4. The hardware scope exception, local-app boundary, and optional ACT/manual routes are reflected consistently in requirements and architecture.
5. Dependencies, reusable delivered work, superseded future work, and remaining hardware decisions are recorded without preallocating conflicting IDs.

Delivery acceptance for each path:

- A learner with stated prerequisites can complete it independently using supplied starters.
- Substantive physics, derivations, runnable code, interpreted figures, exercises, and independent scientific review meet existing PBC standards.
- The capstone is a usable application with installation instructions, example inputs, a complete workflow, export, failure reporting, and a reproducible evidence package.
- Essential outcomes can be assessed without buying hardware or model access. Real hardware support is labelled demonstrated only after a physical pilot.
- Agent hypotheses are separate from measured evidence and withheld truth; numerical claims are independently checked.
- Model discovery includes withheld prediction tests and an ambiguous case; benchmarking includes non-agent baselines and uncertainty; research includes externally checkable sources and rerunnable outputs.
- Deterministic CI validates the offline route within existing verification contracts. Hardware/model experiments stay separately evidenced; no checks are weakened to fit them.

## 10. External repositories: selective adoption policy

The 16-repository report is source inspection, not execution evidence. No external framework, benchmark, paper asset, skill, cloud service, or copied implementation is adopted by this change alone. Pin versions and inspect applicable licences and dependencies for any actual reuse. Preserve citation and attribution where appropriate. A wrapper's licence does not grant rights to datasets, paywalled papers, model services, or external scientific software.

| Candidate | Proposed use | Boundary |
| --- | --- | --- |
| AI-Scientist v1/v2 | Case studies of idea generation, experiment search, reviews, and failure modes | Their custom licences differ from ordinary MIT reuse; no direct code import by default. |
| AI-Scientist v3 | Evaluator-owned evidence, final-test separation, claim grounding, and coding-agent orchestration patterns | Implement the smallest PBC-appropriate design; no wholesale pipeline migration. |
| Agent Laboratory | Human steering and reuse of previous investigations | Local checked research bundles, not a new public preprint service. |
| Robin | Separate experimental-test selection from candidate selection and feed analysis into new questions | Do not require its externally hosted analysis service. |
| Aviary | Optional environment adapter for comparing agents | Existing PBC environments remain canonical unless a demonstrated benefit supports a change. |
| PaperQA | Optional evidence-retrieval and contradiction-analysis comparison | Manual/local-corpus route and offline fixtures remain available. |
| Bluesky | Experiment state, interruption, cleanup, and valid resume | Prove on one chosen instrument before commitment. |
| QCoDeS | Parameter validation, units, and instrument snapshots | Compare with a minimal adapter; no blanket driver-support claim. |
| Bluesky Adaptive | Classical adaptive baseline and suggestion-to-measurement association | Optimising a score and discriminating hypotheses are different objectives. |
| PySINDy | Optional dynamical-equation and weak-form comparator | Use a pinned current API; keep required code independent of the package. |
| PySR | Optional broader symbolic engine with constrained grammar/complexity | Isolate Julia/runtime installation and reproducibility costs. |
| Jobflow | Optional dynamic/composable workflow execution | Ordinary Python first; require a demonstrated need. |
| Atomate2 | Materials extension showing professional simulation workflows | External solver access and compute are separate feasibility questions. |
| R&D-Agent | Hypothesis, experiment, execution, feedback, and history separation | Scientific-loop reference, not a replacement for ACT. |
| ShinkaEvolve | Optional solver/program-optimisation exercise | Independent physics checks; correctness is a hard requirement before comparing runtime. |

### 10.1 Bounded feasibility work and decision outputs

Plan the following five investigations as bounded tasks, grouping or postponing them where sensible. Each produces a go/no-go recommendation, evidence, dependency/runtime cost, and the simplest viable implementation. It must have explicit compute/time limits set in its implementation plan. Exhausting the limit produces an honest partial result and a decision; it does not authorise automatic expansion or repeated repair.

1. **Evidence and final-evaluation pilot — first.** Extend one existing task. A candidate that fabricates a high score must fail; a changed artifact invalidates the relevant evidence; invalid/missing outcomes remain visible. Reuse current replay/judging mechanisms.
2. **Model-discovery comparison.** Compare the existing baseline with PySR/PySINDy on appropriate tasks. Include noise, ambiguity, withheld predictions, and reproducible settings. These engines solve different tasks and must not be forced into an artificial common leaderboard.
3. **One-instrument measurement pilot.** Compare a minimal runner/adapter with Bluesky and, where helpful, QCoDeS on the same bounded protocol. Demonstrate physical operation, interruption, valid restart, state capture, and measurement identity.
4. **Literature-evidence pilot.** Compare a simple retrieval baseline and optional PaperQA on a small rights-cleared corpus of claims with annotated support/contradiction/insufficiency. Verify passages, not just citation syntax.
5. **Solver-improvement extension — optional.** Compare a simple optimisation and an evolutionary coding strategy with equal budgets. Test full relevant physical outputs, convergence, new cases, and honest timing; retain failed candidates.

Only the first pilot and the minimal simulator vertical slice are common platform prerequisites. Hardware feasibility gates only live-hardware delivery; package-specific comparisons gate only the corresponding optional integrations. Literature work can start independently. The optional solver exercise must not block core Part B delivery.

## 11. Decisions reserved for implementation planning

Recommended defaults: retain the four existing path keys; use electronics as the first reference hardware context; support one device initially; keep interfaces local; use a pinned ACT starter plus a manual equivalent; retain other hardware domains as extensions.

Still to settle with evidence: exact device and accessories, acquisition budget, optional dependency packaging, final curriculum labels and primary course homes, frontend choice, first reproduction paper, and realistic learner workload. These details must not block writing the curriculum mapping, and none is silently approved by this draft.

## 12. Sources and decision status

This document consolidates the owner discussion, the 2026-10-31 Part B draft, and `PBC_repository_onderzoek.md` (16 repositories; source inspection only). The research report remains supporting evidence rather than a second curriculum authority. This new document is a separate draft; the earlier files remain preserved.

Current PBC checks for this revision:

- `site/curriculum.yaml`: blob `7386d131550e305d90524341ddda8014b5ac81b6`; still the old 33-slot Part B.
- `docs/PROJECT_REQUIREMENTS.md`: blob `2f9bca737e1a9b648969aae288c87ecb8cf4046c`; approval timestamp 2026-10-30T19:50:37Z; hardware exclusion still present.
- `docs/roadmap.md`: blob `2a90d48cb175d9168be635870d172e93e823bf94`.
- Open Issues and PR #351 checked 2026-11-01; PR head `831ab24adcebd401984de12fef0d161264e71c00` at the read.

These are separately retrieved sources, not one commit-pinned snapshot. Implementation planning must reconcile main and active branches again. Writing this draft does not approve it, allocate IDs, install packages, buy hardware, update Issues, or change the repository.

The earlier draft and the research report contain their own source records. Stage A produces the authoritative implementation-time reconciliation; this draft does not turn the report's candidate integrations into approved dependencies.
