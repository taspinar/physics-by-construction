# Planning Change Request — Teaching by Construction

**Status:** Revised draft v3 — expanded cross-module code-presentation review for owner review — **not approved and not an implementation authorization**  
**Date:** 2026-11-13  
**Project:** Physics by Construction (PBC)  
**Proposed change-cycle name:** `teaching-by-construction`  
**Suggested repository location:** `docs/changes/teaching-by-construction.md`  
**Baseline:** PBC's current `main` as inspected on 2026-11-13; the planner must refresh branch, Issue, and feature status before editing the approved roadmap.

## 1. Decision requested
Approve a **bounded improvement to how PBC teaches and presents physics**, not a replacement of its curriculum, scientific claims, verification system, or website technology. This request has **seven workstreams**, reconciled against a cross-curriculum audit:

1. **Physics Teaching guidance:** introduce a project-owned agent skill that helps authors and reviewers reason about *how a learner understands physics*, alongside the existing Editorial Voice Guide and scientific authoring rules.
2. **Mechanics didactic pilot:** redesign the *teaching sequence*, not merely the wording, of three representative existing lessons: Mechanics 01 (kinematics), 03 (projectile motion with drag), and 05 (numerical integrators). Require independent scientific review and the owner's comparison of before and after.
3. **Cross-course teaching calibration:** test the guidance on advanced engineering/capstone, real-measurement, scientific-agent, and formal-proof lessons as different lesson archetypes, without automatically rewriting the full curriculum.
4. **Scientific figure design:** audit Matplotlib figures from multiple courses and, after a successful pilot, introduce coherent, accessible plot grammar without imposing one geometry or palette on every plot type.
5. **Figure metadata, credits and portable attribution:** eliminate needless status/credit duplication *in the chart area* while preserving enforceable source status, dataset-specific rights, traceable exported PNGs, evidence scope and optional unobtrusive PBC identity.
6. **Selective interactive experiments:** use the existing F07 widget system in a small number of lessons where parameter manipulation demonstrably teaches something. Do not rebuild the widget infrastructure or make F128 (browser-computed double pendulum) a prerequisite.
7. **Lesson reading experience and pedagogical code presentation:** reduce metadata, code, and provenance clutter; distinguish physics-bearing algorithms from implementation details; present selective, readable, syntax-highlighted code without misrepresenting transformed selections as verbatim source. Preserve authoritative source identity, evidence, reproducibility, accessibility, and learning-path relationships.

**Integration:** keep F116 as the authoring/template/review-rubric integration feature, but incorporate the outcomes of the approved Mechanics pilot **and cross-module calibration** into that integration *after* they have been evaluated. Retain F116's existing requirements, including conceptual synthesis and clear provenance of AI-lesson evidence. Avoid a second rewrite of the same authoring/template files.

**Recommended decision:** approve all seven workstreams at the *planning* level, implement them in independently reviewable feature slices, and make broad rollout conditional on the owner's review of the pilots. The items below marked **already delivered** are not new features.

## 2. Why the change is needed
F114 established an editorial voice. F115 applied it to Mechanics 01–05 with deliberately narrow **prose-only** changes and closed on 2026-11-07. It improved sentence-level explanation but could not move a visualization, change the timing of an experiment, move advanced derivations into optional depth, or revise a learning sequence. Those are pedagogical decisions, not copyediting.

The reviewed lessons also reveal a reader-experience issue. Lesson headers combine valuable orientation with substantial connections, prerequisites, and catalogue metadata; by-reference code excerpts display long repository paths and build-time explanations; and the reproduction footer repeats detailed infrastructure information in the main reading flow. Keeping all the information is valuable. Giving all of it equal visual prominence is not.

A follow-up review of by-reference Python excerpts exposed a second specific teaching issue: a lesson can include complete function signatures, several paragraphs of docstring, helper code and even 50–100 lines of Matplotlib configuration before it shows a figure. This is sometimes redundant with the prose and sometimes obscures the few lines that implement the physics. Conversely, removing every full function would harm PBC: numerical methods, data transformations, trust boundaries and formal proofs can themselves be the learning objective. The change therefore calls for **purpose-driven, provenance-preserving code presentation**, not blanket shortening.

The proposed next step is **teaching quality**, understood as whether a learner can explain the physical idea, predict a result, connect mathematics to a simulation, interpret an unexpected outcome, and distinguish a verified numerical result from a realistic physical model. This is complementary to, not a substitute for, PBC's scientific checks. The same distinction matters for dense real-data labs, engineering decisions, scientific agents and Lean proofs: one prose template will not teach them equally well.

### Non-negotiable product character

- Teach physics by *constructing* models, running code and experiments, comparing against theory and measurements, and verifying what the evidence warrants.
- Retain mathematical rigor. **Progressive disclosure does not mean deleting advanced mathematics**; a derivation needed for the main idea belongs in the main text, while an optional derivation can be placed in a clearly labelled depth section or linked section.
- Do not impose a compulsory narrative recipe such as “predict → simulate → derive” on every subject. Choose a structure appropriate to the actual physics and learner prerequisites.
- Preserve all existing scientific, reproducibility, attribution, accessibility, performance, and no-external-request guarantees unless a *separately approved planning decision* changes them.
- No new mandatory agent, model invocation, extra review round, frontend framework, backend, external CDN, or runtime AI service.

## 3. Reconciliation with the earlier visual proposals
| Earlier proposal | Verified current state | Decision in this change |
|---|---|---|
| **A — Shared Matplotlib style / `rcParams`** | `src/pbc/experiment.py` centralizes fixed rendering but `FIGURE_SETTINGS` mainly establishes figure size and DPI. `src/pbc/authoring/design.py` already centralizes `FIGURE_COLOURS`, page colors and contrast rules. `docs/authoring.md` already gives figure-design guidance; the scientific-visualization skill exists. | **Carry forward, with a figure audit and pilot first.** Fill genuine gaps (type, axes, grid, line hierarchy, sizes, annotations, suitable colormaps) rather than creating another competing palette or rewriting all plots at once without review. |
| **B — Raster interface artwork on Home, Atlas, course/capstone openings** | **Already allowed** by ADR 021, which partially supersedes ADR 018. Registered derived **WebP/PNG** interface artwork is allowed on non-lesson pages; PBC already uses it. | **Do not create a new asset-permission feature or ADR amendment.** Reuse the existing provenance and asset-class rules; audit compliance only where a new visual is actually introduced. **AVIF is not yet included in the verified allowance** and should not silently be added. |
| **C — Interactive figures by lightweight widgets** | F07 is delivered; `docs/authoring.md` defines dependency-free ES modules and an accessible static fallback. Mechanics 05 already contains the integrator explorer. F128 remains a separate, owner-gated browser-computed pendulum proposal and is no longer tied to Home. | **Carry forward only the lesson-level adoption pilot.** Reuse F07, prefer precomputed Python data and SVG/Canvas where appropriate. Keep F128 parked unless separately approved; no generic ECharts/Plotly adoption in this change. |

### Asset classes remain authoritative

The distinction established by ADR 018, as amended by ADR 021 and requirements decision 41, remains intact:

1. **Scientific result/evidence:** computation or measured data shown as a result, with reproducible sources, traceable figure status, and existing scientific checks, on *any page*.
2. **Conceptual explanation in a lesson:** represents the relationship correctly, never masquerades as measurement or simulation evidence, and follows the permitted lesson-figure forms and independent review.
3. **Interface artwork:** atmosphere/navigation on non-lesson surfaces, including approved registered WebP/PNG and SVG assets, never fabricated scientific evidence. The existing requirement forbidding numbers, formulas, and text baked into interface-artwork pixels remains in force; set text in semantic HTML instead.

**No change to those permissions is requested.** Retain the existing provenance requirements rather than introducing an independent register, arbitrary new file-size rules, or a second classification.

## 4. Evidence from the cross-curriculum audit
This change request now draws on an inventory of **104 lesson sources and 255 declared figures** across **11 course/strand directories**, not Mechanics 01–05 alone. A separate review record, Appendix B of this change request (the audit, inlined), documents the sample-based inspection and its limits. The planner should commit that record in an appropriate `docs/` audit/research location, or inline its conclusions in the change request before approval; do not silently rely on a local file the repository cannot see.

| Course or strand | Source lessons | Declared figures | Principal teaching risk identified |
|---|---:|---:|---|
| Mechanics | 20 | 58 | Early numerical theory; dense orbital derivations (M08); visually sparse dynamical topics (M13/M14); late measured-data lab (M20) |
| Thermodynamics | 11 | 28 | Transition from basic intuition to PDEs, finite elements, capstone engineering and data provenance |
| Waves and optics | 9 | 30 | Later diffraction/wave-flume labs carry processing, calibration and model uncertainty |
| Electromagnetism | 8 | 23 | EM07 phased-array capstone: six figures, complex tradeoffs, requirements introduced late |
| Fluid dynamics | 8 | 15 | From intuitive flow to numerical solver internals; measured turbulence and processing-induced comparisons |
| Quantum physics | 8 | 22 | Q01 abstraction and Q07 Bell-test measurement/statistical complexity |
| Astrophysics | 9 | 27 | AST09 folded transit data, processing, competing fitted models and residual figures |
| Materials | 5 | 13 | MAT05 loaded stress–strain figure and extended fit/hysteresis analysis |
| LLM/scientific agents | 20 | 31 | Repeated evaluation/replay protocol; distinction between model output and independent evidence; multimodal figure inputs |
| Agent-based modelling | 1 | 2 | Good example of approachable emergence from local rules; no blanket redesign indicated |
| Lean/formal proofs | 5 | 6 | Scaffold from reading proofs to editing tactics without weakening the theorem |
| **Total** | **104** | **255** | |

**Assessment:** later lessons are **not categorically worse** than Mechanics 01–05. Strong physical openings exist in Thermodynamics 01 (ink spreading), Waves 01 (plucked string), Electromagnetism 01 (charged balloon), Quantum 04 (Stern–Gerlach), and Materials 01 (lattice vibration). Some lessons are intentionally advanced, so greater length is not itself a defect. The recurring weakness is **how the information is staged**: in later labs and capstones, the essential physical question can become obscured by upfront assumptions, long derivations, processing steps, extensive legends and code/provenance details.

**Concrete calibration examples:** Mechanics 05 has roughly 5,300 source-prose words and 28 code-excerpt calls at declared difficulty 2; Mechanics 08 roughly 5,170 words, eight numbered assumptions and 33 excerpt calls at difficulty 3. Quantum 07 has roughly 4,735 source-prose words and three complex measurement figures. These are *review signals*, not word-count budgets, automatic failures or permission to simplify mathematics by deletion.

**Visual inspection limitation:** the audit examined the two user-supplied rendered screenshots and Matplotlib sources/captions for representative figures, not raster screenshots of every one of the 255 declarations. No conclusion that all images currently render accessibly is asserted. The design pilot must produce and inspect actual before/after pages at supported widths.

### Focused cross-module code-presentation review (2026-11-13)

A closer source review sampled **17 lessons from all 11 course/strand directories**, and examined the `excerpt()` call sites, nearby prose and selected implementation functions. In this sample **13 of 17 lessons** explicitly show at least one complete `draw_*` function (31 such calls in total). These are **sample counts**, not a sitewide count of every code block or proof. This is evidence of a recurring presentation pattern, **not proof that each selected listing is pedagogically unnecessary**. The published rendering was not re-run or assessed at every viewport in this review.

| Representative lesson | Source-level finding | Pedagogical decision to test |
|---|---|---|
| [Mechanics 08 — Kepler orbit](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/mechanics/08-kepler-orbit/index.qmd) | Many source excerpts and four complete orbit-plotting functions, in a mathematically dense lesson. | Prioritise the orbital equations, invariants and integrator comparison; source-link routine drawing. |
| [Thermodynamics 09 — AI-accelerator thermal design](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/thermodynamics/09-thermal-engineering-of-an-ai-accelerator/index.qmd) | Uses excerpts of finite-element assembly, the theta method and package physics; no explicit `draw_*` excerpt in this lesson. | **Positive counterexample:** implementation code is central to building and judging the engineering model, so keep appropriate complete numerical algorithms. |
| [Waves 09 — Lycopodium diffraction](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/waves/09-lycopodium-diffraction-lab/index.qmd) | Four full `draw_*` excerpts; `draw_scaling` itself computes folding, smoothing, dimensionless ratios and residuals as well as layout. | Do **not** drop the function's scientific calculation with its layout; show or extract the physically meaningful transformation, source-link its plotting machinery. |
| [Electromagnetism 07 — Phased-array beam steering](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/electromagnetism/07-adaptive-phased-array-beam-steering/index.qmd) | Shows source functions for array factors, nulling and phase quantisation, without explicit plot-function excerpts. | Keep source for the essential linear algebra; explain complex-valued arrays and interface assumptions rather than stripping all type information. |
| [Fluid Dynamics 05 — Navier–Stokes](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/fluids/05-navier-stokes-fundamentals/index.qmd) | Shows core Poisson/projection/step functions **and** drawing functions. | Keep the three-stage projection algorithm; prefer the figure and a Source link to a `draw_projection` listing unless its calculation is itself being taught. |
| [Quantum 07 — Measurement statistics](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/quantum/07-quantum-measurement-statistics/index.qmd) | CHSH computation, fit and checks coexist with three `draw_*` excerpts. | Make the counts → correlator → uncertainty → test statistic code visible; avoid letting plotting code obscure the statistical reasoning. |
| [Quantum 08 — Atomic spectroscopy](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/quantum/08-atomic-spectroscopy/index.qmd) | Four plotting-function excerpts, including a long calibration plot that also computes conversions and residual quantities. | Separate the redshift calibration and residual calculation from plotting instructions before deciding what to hide. |
| [Astrophysics 09 — Exoplanet light curves](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd) | Shows the physical flux model, data processing and covariance propagation, **not** its `draw_*` functions. | **Positive counterexample:** preserve the distinction between scientific pipeline and presentation code. |
| [Materials 05 — Stress–strain](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/materials/05-stress-strain-measurements/index.qmd) | `offset_crossing` is explained in prose and again by a long docstring. Three figure-rendering functions are shown; `draw_elastic_regime` is ~94 source lines and embeds shifted Hooke lines and residual expressions. | Keep the crossing/interpolation, fit and residual mathematics; remove redundant docstring and chart-layout boilerplate **from the lesson display**, not the source. |
| [Scientific Agents 01 — Agent experiment](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/agents-llm/01-an-agent-runs-an-experiment/index.qmd) | Full diagram-drawing functions appear alongside model-client, allowlist and replay code. | Show the trust boundary in the diagram, and the validation/allowlist/replay implementation where those are the point; source-link drawing instructions. |
| [Lean 01/04 — Proofs and exercises](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/lean/04-lean-exercises-on-your-machine/index.qmd) | Formal proof excerpts and student stubs need precise hypotheses and syntax; there are also figure-drawing excerpts. | **Separate treatment:** never silently simplify a theorem statement or proof; selectively source-link irrelevant diagrams. |

Other sampled lessons included Mechanics 13, Thermodynamics 10, Fluids 08, Agents-LLM 16 and Agent-Based Modelling 01. The **change to the earlier recommendation** is important: `draw_*` is neither automatically irrelevant nor automatically pedagogical. Some drawing functions compute physical comparisons, process measurement arrays or define residuals that the student must understand. Apply a scientific dependency check before hiding the code.

## 5. Workstream T1 — Project-owned Physics Teaching Skill
### Purpose

Create the skill in `.agents/skills/pbc-physics-teaching/` (its `SKILL.md`) with a repository-local provenance record and entry in the README of `.agents/skills/`, following ADR 019 and the current process rules. This is **agent guidance, not evidence**, and never a build or site dependency. It supplements:

- `docs/editorial-voice.md` — sentence-level clarity, register, transitions, and prose.
- `docs/authoring.md` — authoritative scientific, lesson-format and evidence constraints.
- `.agents/skills/pbc-scientific-visualization/` — scientific figure decisions and accessible visual encoding.

The new skill owns only the **pedagogical reasoning layer**: choosing what the learner must understand first, identifying missing cognitive steps, deciding when visual prediction is helpful, aligning equations and code, and explaining what evidence warrants.

### Research-informed, not copied

The skill should distill methods, with concise original examples and properly sourced references, from:

- Richard Feynman, *The Feynman Lectures on Physics*: physical intuition, fruitful questions, explanatory insight.
- Chabay & Sherwood, *Matter & Interactions*: physical modeling and computation as part of the physics itself.
- John R. Taylor, *Classical Mechanics*: clear stepwise mathematical development.
- OpenStax, *University Physics*: accessible worked examples and visible reasoning.
- McDermott & Shaffer, *Tutorials in Introductory Physics*: eliciting predictions and confronting misconceptions.
- MIT OpenCourseWare and PhET: careful sequencing of demonstrations and purposeful interactivity.

References should identify specific chapters/sections and what their *teaching practice* contributes; no copied diagrams, long extracts, or unlicensed figures. These are **exemplars, not infallible authorities**, and PBC keeps its own voice and objectives.

### What the skill must help an agent do

- Specify the target learner and what is realistically assumed at the beginning of the lesson.
- Identify the central physical question, the counterintuitive point, and the intended conceptual outcome.
- Find prerequisite gaps and avoid introducing abstractions before giving their physical meaning.
- Explain symbols and assumptions, then connect derivations to an observable prediction or program operation.
- Deliberately select one or two high-value prediction/experiment/interpretation moments; do not sprinkle questions everywhere.
- Distinguish a prediction, analytically derived property, simulation output, measured result, and inference about reality.
- Choose whether advanced derivations are essential or suitable for optional *Go deeper*, without erasing the proof or its scope.
- Make the connection between actual physics code and explanatory code. Code that only draws the picture is not automatically a teaching excerpt.
- For every displayed code block, decide *why a learner should read it now*: new physical relationship, numerical update, scientific processing/validation, engineering trade-off, agent control, formal proof, or merely rendering/housekeeping. Showing the function **just because it generated the next figure** is not a sufficient reason.
- Choose among (a) exact complete function, (b) exact selected source lines with clearly declared omissions and required context, (c) explicitly labelled simplified/schematic code whose relationship to the tested implementation is stated, or (d) Source link only. Do not treat any of these as a compulsory global default.
- Check whether the same explanation already appears immediately before or after a docstring. Keep source docstrings and annotations intact; show them only where they supply a necessary assumption, unit, interface meaning or teaching insight not already stated.
- When a long `draw_*` function embeds **scientific transformations** (for instance a residual formula, smoothing rule, offset or calibration), surface those transformations in selected verified lines or, if justified, a separately tested analysis function. Never hide the only visible calculation behind a Source link simply to shorten a page.
- Preserve complex/array/state/proof types when they **are** the concept (for example quantum state, data artifact semantics, agent-tool schema or Lean theorem); omit annotations in a pedagogical *summary* only when the reader loses no necessary information. Avoid encouraging copying a fragment that cannot run in isolation.
- Review the whole lesson and transitions across lessons, not merely prose in isolation.
- Select a *lesson archetype* before proposing a restructure: model/simulation, measured-data investigation, engineering design/capstone, AI-agent/evaluation, agent-based model, or formal proof. The main learner journey differs between them.
- For a measurement lab, make the lineage visible: recorded/calibrated values → quality/processing → model → comparison/fit → residuals/uncertainty → warranted conclusion. Do not mistake an agreement created by processing assumptions for independent validation.
- For an engineering capstone, show the design brief, constraints and success criteria before or alongside method-heavy derivations; use a decision/trade-off summary rather than a chain of unrelated numerical checks.
- For an AI experiment, distinguish written example, model transcript, tool replay, recorded run, held-out scoring and independent evaluation immediately, and explain what the *current* lesson adds beyond earlier agent protocols.
- For a proof lesson, distinguish assumptions, theorem, verified proof and exploratory numeric example, and make the learner's first proof-writing step achievable.
- Place essential assumptions when the learner needs them; retain full limitations and evidence scopes but avoid a long first encounter with detailed technical boundary conditions before any motivating calculation.

The skill contains short **before/after examples from PBC**, including one case where *no restructure* is the correct decision. The author must state why a proposed movement or new activity improves comprehension rather than aesthetic uniformity.

### Workflow incorporation

- A relevant lesson feature's plan selects the skill, or records why it is not useful. Selection follows existing ADR 019 provenance and review conventions; do not add a new mandatory review role.
- The implementer records where the skill changed the learning experience, not simply that it was read.
- The independent reviewer judges named pedagogical weaknesses with evidence and an action; no numerical “AI writing quality” score and no detector-optimization criterion.
- If the existing ADR 019 text or skill selection policy currently limits applicability to *visual* artifacts, update it through the approved planning/feature path rather than pretending the new teaching skill already falls under that rule.

**Acceptance for T1:** a readable, concise, project-owned, versioned skill; provenance and existing structural checks pass; ownership boundaries with the voice guide and authoring guide are explicit; a dry-run review shows useful decisions on at least two different kinds of physics lesson. No published lesson is modified in this slice.

## 6. Workstream T2 — Didactic pilot on Mechanics 01, 03 and 05
Each lesson gets **a separate implementation PR** and an independent scientific/editorial review, plus a comparative record that shows the existing lesson beside the proposed one. Do not open new Issues for all 94+ published lessons. Preserve canonical URLs, curriculum slots, outcomes unless changed by a separately reviewed decision, and the reproducibility contract.

### Pilot selection and intended change

| Lesson | Current teaching strength | Candidate experiment in sequencing |
|---|---|---|
| **01 — Kinematics as a program** | Relates a simple state-update rule to an exact trajectory and first-order convergence. | Make a concrete prediction and a small Euler step before discussing local/global error; put the meaning of the discrepancy ahead of the full asymptotic analysis. |
| **03 — Projectile motion with drag** | Distinguishes numerical validation from whether a model describes a real tennis ball. | Keep the best-launch-angle question visible; let the learner compare drag/no-drag trajectories early, then use convergence and limiting-case checks to answer whether the simulation is trustworthy. |
| **05 — Numerical integrators** | Strong comparison of error, force-evaluation cost, and long-run energy behavior; existing interactive explorer. | Bring the comparison or interactive explorer closer to the central question. Separate the essential choice of update rules from advanced complex-number, eigenvalue and modified-energy derivations when these are optional for the target level. |

**Lesson 02 and 04 are comparison/control cases**, not automatically a second editorial rollout. Their existing explanations and figures can be used to judge coherence; targeted scientific corrections, if needed, are separate reviewed work. After the three pilot lessons, review the complete Mechanics 01–05 sequence for progression and missing bridges before approving wider rollout.

### Acceptance for T2

1. For each lesson, record the learner, target misconceptions, and why the proposed sequence is appropriate *for that subject*.
2. Show a concise **before/after reading map**: where the main question, first physical intuition, first calculation, first experiment, interpretation, key derivation, and conclusion appear. Document what stayed unchanged and why.
3. A reader can reach the central experiment and understand its purpose without first parsing unrelated implementation or build provenance.
4. Every equation, physical scope, evidence-labelled claim, computed value, figure, exercise solution, and code excerpt remains scientifically valid. Any proposed change to a published scientific claim follows the existing escalation, independent review, and verification requirements; do not smuggle it into a UX or prose-only PR.
5. Keep all advanced material accessible; any moved proof/derivation remains linkable and discoverable and is not silently weakened.
6. Preserve usable static content and all required anchors; if moving sections, preserve documented anchors or provide compatible links.
7. Independently review each lesson's correctness and pedagogical clarity; the owner explicitly accepts or rejects the approach after viewing the rendered pages at desktop and phone widths.
8. Assess the code-reading journey for at least Mechanics 01 and 05: a learner should be able to locate the essential state update/integrator order without reading plot layout, redundant docstrings or unrelated helper details. Apply exact-source or explicitly labelled simplified modes rather than quietly changing source syntax.
9. Record whether the new approach improves comprehension *with concrete observations* (e.g., an unfamiliar reviewer can explain the purpose of the experiment and answer the self-check). Do not invent student-study data, comprehension percentages, or universal teaching-effect claims.

## 7. Workstream T3 — Cross-module teaching calibration, beyond Mechanics
Mechanics 01/03/05 alone cannot establish a universal lesson-writing method: these are simulation-heavy chapters. The calibration also tests whether the proposed **code-display policy** works in labs, engineering, fluid solvers, agent systems and proofs, not only in introductory simulations. Before F116 is finalized, **evaluate** the new skill on at least the following distinct archetypes, recording strengths and failure modes, without automatically editing their scientific content:

1. **Measured data:** Astrophysics 09 (21 folded exoplanet transits) and/or Materials 05 (NIST DP980 stress–strain experiment). Inspect the data lineage, fit assumptions, uncertainty and key comparisons; check whether a new learner can follow the observation before the statistical analysis.
2. **Engineering/capstone:** Electromagnetism 07 (adaptive phased array) and/or Thermodynamics 09 (thermal design). Compare the *placement of the design requirements*: Thermodynamics 09 brings the requirements forward, while EM07 introduces its requirements within Worked examples after Code. Choose the layout that best supports the actual design question.
3. **AI evidence:** at least one `agents-llm` lesson with recorded replay or a held-out evaluation (e.g. agents 13, 16 or 20). Check the difference between language-model explanation, tool execution, observed results and independently tested evidence.
4. **Formal proof:** at least one Lean lesson, especially `lean/04-lean-exercises-on-your-machine`, to ensure the guidance supports progressive mathematical practice instead of importing a simulation-first recipe indiscriminately.

A **source-only diagnostic** is not a content rewrite. Propose at most **one additional cross-module teaching redesign** after the calibration, in its own reviewed Issue/PR and only if it has an identifiable learner-facing problem and the owner approves the scope. This avoids expanding the Mechanics pilot into a 104-lesson migration by default.

**Acceptance for T3:** per-archetype teaching maps (physical question, required prerequisite bridge, first observable, main derivation, code role, evidence/limits, exercises); examples of both good existing practice and identified gaps; explicit decision on any additional pilot; F116 incorporates lessons that generalize while leaving subject-specific choices flexible.

## 8. Workstream V1 — Cohesive Matplotlib figure language
### The problem to solve

PBC's page typography and palette are already designed and centralized, and figure-line colors have a shared source. However, Matplotlib output largely starts from default rendering settings (apart from dimensions and DPI), and lessons manually select different text sizes, grids, labels, aspect ratios, line weights, and heatmap choices. This can make a coherent site feel like figures from unrelated papers.

### Proposed design and implementation

**Phase 1: visual audit without a site-wide change.** Select representative examples from distinct figure classes: kinematics/trajectory, multi-series numerical comparison, phase space, convergence/log-log, heatmap/field, and measured-versus-model/residuals. Capture a baseline at desktop and mobile. Judge legibility, plot-versus-page typography, legend placement, line/marker hierarchy, color-scale semantics, and file sizes.

**Phase 2: a controlled figure-style pilot.** Extend the existing design tokens and `FIGURE_SETTINGS`, or add a single associated helper module, instead of adding a second arbitrary palette:

- Reconcile Matplotlib typography with the site's published fonts and figure export environment; test fonts available to the pinned runner and deterministic rendering.
- Prefer a restrained plate background, consistent axis/label hierarchy, light grids when scientifically useful, predictable line widths, and stable default dimensions.
- Reuse `FIGURE_COLOURS`, `PAGE`, and existing contrast tests in `src/pbc/authoring/design.py`. **Also reconcile** the measurement-specific `pbc.data.plotting.COLOURS` (Okabe–Ito) as a deliberately accessible second palette. Do not blindly recolour measured data to match the brand; decide and document when each palette applies.
- Choose perceptually appropriate **sequential** and **diverging** colormaps by data semantics; do not hard-code a diverging map for all heatmaps.
- Use direct labels where they genuinely improve comprehension; preserve legends when direct labels collide, obscure curves, or fail at mobile width. Audit repeated status words, long fitted-model labels, plot titles that duplicate captions, seven-entry legends, excessive visible markers, and per-panel legends that could be one semantic legend. **Do not delete uncertainty, model identity, units or necessary trace labels.**
- Support specialized styles for phase-space plots, error/convergence plots, multi-panel measured-data comparisons, and conceptual diagrams; do not force identical aspect ratios or grid density.
- Keep color-independent distinctions for curves, high-resolution reproducible rendering, units, accessible fallbacks, and consistent alt-text meaning.

**Phase 3: scope and rollout decision.** After comparing the six pilot classes, the owner chooses whether to apply the shared defaults to all figures or use a selective migration. A global change to `src/pbc/experiment.py` and/or `src/pbc/authoring/` affects every lesson and requires the **full verification tier**, current artifact/reproduction comparison, and visual spot checks. Compute its risk from the repository's current detector and protected-path rules; **do not pre-label it Level 2 or Level 3 without assessment**.

**Acceptance for V1:** one documented design system with purpose-specific coordinated palettes; readability across six figure classes; stable units, traces and semantic meaning; documented before/after samples; contrast checks and responsive audit; figure bytes reproducible from the same source/build; payload/build cost measured and within the accepted budgets; independent science review confirms no plot misrepresents values, uncertainty, residuals or scales.

## 9. Workstream V2 — Figure status, data credits, portable provenance and PBC identity
**Why this is distinct from V1:** changing axes/line styling does not solve the hard problem of *where figure identity and third-party source credits live*. The two reviewed screenshots are examples:

- [AST09 transit fit](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/astrophysics/experiments/exoplanet_light_curves.py), `draw_transit_fit`: the science is strong (21 folded transits, fitted limb-darkened and uniform-star models, binned residuals), but the large figure status, long TESS/MAST credit at bottom, and repeated status tags in the legends crowd the graph.
- [MAT05 stress–strain](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/materials/experiments/stress_strain_measurements.py), `draw_stress_strain`: the hysteresis shading and loading landmarks are useful, but the seven legend entries, data attribution and status pill occupy substantial non-data space.

**Actual source of the clutter:** [`src/pbc/data/plotting.py`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/data/plotting.py) uses `label_status()` to draw `status: processed` *in the PNG*, and `add_credit()` to draw a wrapped source paragraph *inside the PNG below the axes*. At the same time [`site/_filters/lesson.lua`](https://github.com/taspinar/physics-by-construction/blob/main/site/_filters/lesson.lua) renders `fig-status` in the HTML caption. The problem is partly duplicate presentation across two layers.

**Existing safety contracts must be migrated, not bypassed:** `check_figure()` requires an on-figure status, a title per panel, units and legends; `tests/unit/test_data_plotting.py` explicitly asserts the status and credit positioning, and reference/lesson tests enforce the dataset card status. PBC's figure encoder produces deterministic **same-byte PNGs** for the published page and the runnable experiment. Dataset cards separately record licensing, figure-publication permission, modification and attribution rights. Removing labels alone would break scientifically meaningful checks and sometimes attribution conditions.

### V2a. Audit and choose the presentation/metadata contract

The pilot must distinguish three separate contexts:

1. **Website:** put one concise and accessible status for the complete figure near its caption, preserving `fig-status`, `fig-dataset`, `fig-artifact`, model-of relationships, and the underlying artifact types; state if a figure combines *processed measurements and simulated fitted models*. Place a short data credit below the caption, with full citation/processing/licence available as a native `<details>` block or linked dataset dossier. Keep the chart area focused on the phenomena.
2. **Standalone/shareable PNG:** attribution must travel with the image where a third-party right or the user experience needs it. Evaluate deterministic embedded PNG metadata, a validated export manifest, and optionally a *short*, readable on-image credit. An HTML caption alone is not sufficient for someone who saves a PNG and shares it without the webpage.
3. **Experiment reproducibility:** preserve the exact same image bytes between a lesson's shown figure and `Experiment` output for the same commit. Keep status, creator, original data source, version, dataset ID, licence/rights, preprocessing description, and committed code identity traceable; do not introduce a separate unversioned citation string that can drift from the dataset card.

### V2b. Minimal branding, not a compulsory watermark

The objective is *attribution and recognisability*, not preventing lawful reuse. PBC figures can be shared under the site's terms, and external TESS, NIST, university or other data remain attributed to their actual creators. A small footer such as **“Visualization: Physics by Construction · Data: TESS/MAST”** is a candidate on portable graphics; it must not imply PBC owns the original measurements. A large logo, a watermark across the data, a mandatory brand on every scientific plot, and a false ownership claim are **not** approved. The owner reviews examples with and without a small mark.

### V2c. Figure semantics and export tests

- Keep scientific marks, uncertainty bands, residuals, data/model separation, units and warnings; no hiding of data or extrapolating claim scope for a cleaner aesthetic.
- Choose shorter labels, shared legends or direct labels when accessible. Preserve equivalent machine-verifiable title/legend semantics: replacing `check_figure()` with no check is forbidden.
- If only rendered points are thinned for legibility, the computation still uses all records, the sampling/thinning is disclosed, and meaningful extrema, sparse events and uncertainty are not hidden.
- Test figure credit and status in generated HTML, portable PNG and any sidecar metadata; include dataset-specific rights tests and **the existing reference-figure tests**.
- Check [`agents-llm/16-multimodal-physics-reasoning`](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/agents-llm/16-multimodal-physics-reasoning/index.qmd) separately: some figures become *model inputs*. Changing pixels (including credits) can affect replay/benchmark evidence and must not silently mutate those inputs or the recorded claims.
- Verify desktop and phone legibility, file size, deterministic bytes, copied/downloaded image identity and correct HTML-to-image linking. All changes to shared rendering infrastructure take the applicable **full verification and owner gate**.

**Acceptance for V2:** approved before/after evidence on at least the two supplied lab cases *and one mixed measured/model figure from another course*; one validated authoritative metadata/credit strategy across HTML and export; unchanged or stronger scientific/status/rights checks; no third-party attribution lost; no incorrect ownership wording; no silent change to agent multimodal fixtures; owner-approved branding choice.

## 10. Workstream I1 — Purposeful interactive learning, using F07
### Approach

No new general JavaScript plotting framework is approved. Reuse the **existing F07 convention**: a static figure and text first, an optional dependency-free ES module, semantic native controls, a stable layout, no external requests/cookies/storage, accessible keyboard operation, reduced-motion behavior, and browser-rendered results that match authoritative Python data.

Choose **at most two additional lesson interactions in this change** after the Mechanics pilot **and cross-course calibration** determine whether they are genuinely useful. The best choices might be *outside* Mechanics. Candidates, not commitments:

- **Mechanics 01:** adjust `Δt` to compare Euler with the exact motion and see first-order convergence. If the Python precomputed step grid suffices, the browser only selects and draws those values.
- **Mechanics 03:** adjust launch angle and observe range with and without drag, using Python-generated values and an honest description of model assumptions. Do not turn a coarse precomputed angle grid into a claim of continuous numerical optimization.
- **Electromagnetism 07:** change steering direction or phase resolution to see main lobe, null and grating lobe tradeoffs; precompute reference patterns from tested Python if feasible.
- **Astrophysics 08:** change transit impact parameter and limb darkening to understand ingress/egress and transit depth, separated from AST09's measured fit.
- **Quantum 04 / Thermodynamics 04 / Fluid dynamics 04:** selectively test Stern–Gerlach analyser angle, Ising temperature or dam-break depth as alternatives *if* the reference data, controls and static fallbacks can support valid comparisons.

Mechanics 05's **integrator explorer already exists**; improve its placement and explanation in T2 rather than rebuilding it.

For each candidate, answer: *what misconception or prediction can this widget address that a static figure cannot?* If the answer is weak, use a static comparison instead. Count the shipped widget only if the new experience is clearer for a learner with the relevant prerequisites.

### Browser-computed simulations and F128

F128 is still an **independent, owner-gated feature** for a double pendulum with a browser-side numerical integrator, Python-reference trajectories, tolerance-based cross-language tests, and motion/accessibility controls. This change **does not start, depend on, or silently alter F128**, and the home hero is not made interactive. The owner may take a separate F128 decision later, potentially placing it in the Classical Mechanics course or on the scientific-verification page, as the current roadmap provides.

ECharts or Plotly are not imported in this change. A separate justified decision would be required if a future, real use case cannot be served by the existing approach, supported by bundle size, performance, static-equivalent and accessibility evidence; old rough megabyte estimates are not acceptance thresholds.

**Acceptance for I1:** pedagogical need demonstrated in the pilot record; testable alignment with `pbc` data; interactive and static views tell the same story; controls work with keyboard and screen reader; no new runtime network destinations, storage, dependencies or layout shift; performance budgets and deterministic site build hold; scientific reviewer approves the scope of what the interaction establishes.

## 11. Workstream U1 — Less cluttered lesson interface
These are **presentation changes, not removals of evidence**. Keep each small concern separately reviewable, particularly where shared generators or templates cause a full site rebuild.

### U1a. Compact lesson orientation/header

Keep visible above the lesson: title, course/lesson position, difficulty and method, a **short learner-oriented purpose**, and the most relevant outcomes. Put the detailed course/slot cross-references, full prerequisites/glossary, related lessons and connections in a native closed disclosure. Previous/Next must remain easy to locate, including at the end of the lesson. Preserve all underlying metadata, links, accessibility and anchors. Avoid repeating identical navigation in several places.

### U1b. Terse code provenance

Under or beside a by-reference code excerpt show a compact, meaningful **Source** link. Keep the exact source path, line range, commit identity, and build provenance in the generated link and machine-readable metadata; make them discoverable on demand rather than rendering a long file path and “read from repository when built” after every block. In **source-exact mode**, the code remains **the version tested and built**. Any simplified teaching representation must be labelled separately and must not claim source-exact status. Show implementation excerpts that teach the physics; hide/explain figure-rendering helper code by default if it is merely mechanics of drawing. Preserve an accessible path to the entire source.

### U1c. Figure-status presentation

This concern is **owned by V2**, because the status exists both in the Matplotlib PNG (`label_status`) and HTML caption (`fig-status`). U1 may improve surrounding CSS only; it must not delete the on-image label, change scientific status, or weaken `check_figure()` outside the V2 pilot. Preserve one clearly visible status in the reading experience and an accurate portable status/credit strategy for exported figures.

### U1d. Reproduction section

Keep the reproducibility section, its anchor, commit-pinned commands, full file and test list, and setup instructions. Show a concise reader-oriented sentence and a **closed native disclosure** for the complete steps and files; avoid repeating the same command in both an always-visible summary and the open details. Preserve copyability of commands, static/no-JS operation, and the existing independent experiment/reproduction checks. **Do not remove the reproducibility contract** simply because it is not essential to a first reading.

**Acceptance for U1:** shorter above-the-fold orientation and reduced redundant source text on Mechanics 01, Mechanics 05 and a dense lab (MAT05), demonstrated by before/after rendered screenshots; each displayed code block has a defensible educational purpose; exact and simplified presentations are clearly distinguished and traceable; the underlying complete source, comments/docstrings/type annotations, recorded data transformations, and scientific assumptions are intact; annotated Python highlighting matches ordinary excerpts; plot source is one step away without dumping unrelated rendering details into the lesson. Equivalent or better discovery of metadata, exact source and replay commands; keyboard/screen-reader usability; 320 CSS-pixel reflow; zero broken anchors/links; no change to scientific or build guarantees. Shared rendering changes take the tier the verification system requires, including full runs where applicable.

### U1e. Code selection: teach the mechanism, not every implementation detail

For **each** displayed excerpt, require a brief authoring decision: *What is this code meant to teach at this exact point in the lesson?* Prefer one clear, visible block over a procession of implementation helpers when the latter adds no conceptual understanding. Do not make minimal line count a goal; a complete stepper, simulator, conservation check, data-cleaning rule, fit, allowlist or formal proof may be essential.

Apply a common display taxonomy:

1. **Exact full source** for short/central code whose complete control flow matters, including essential data types and preconditions when scientifically relevant.
2. **Exact selected source** for a contiguous relevant body, or a verified multi-range selection showing **visible omission markers, source line numbers and any missing variable context**. This is not necessarily runnable or copy-paste-ready: label it accordingly.
3. **Pedagogical/schematic representation** only when the real code cannot be read without distracting infrastructure. Give it an unmistakable “Simplified illustration — not verbatim source” label and a nearby exact Source link. It must be checked against the authoritative implementation by a domain reviewer; illustrative code must not masquerade as executed/tested PBC code or claim exact numeric provenance.
4. **Source-only** for rendering, decoration, orchestration, file paths and other helpers whose implementation is not part of the learning objective. The figure or result remains on the page with a reachable commit-pinned Source link.

The default for core physical/numerical computation is **visible real code**, not hidden code; the default for pure plot formatting is **Source-only**, unless the lesson teaches visualisation. Do not replace implementation with pseudocode by default. **Do not blindly hide every `draw_*` function:** MAT05 `draw_elastic_regime` includes the shifted Hooke line and residual computation; Waves 09 `draw_scaling` includes smoothing, ratios and residuals; Quantum 08 calibration plots include derived velocities and residual quantities. Either show selected exact calculations, or move them to dedicated tested analysis helpers through a separately reviewed scientific refactor if necessary. No computational result or plot changes are approved by a presentation-only slice.

### U1f. Docstrings, signatures and type annotations

**Do not modify the Python source to shorten the lesson.** Retain docstrings, annotations and their use by `excerpt(..., interface=True)` and other existing checks. When the prose already introduces the operation, the lesson may suppress the long repeated docstring *in its display only*. A short docstring can remain if it introduces a needed physical condition, unit or caveat. The author must ensure such caveats are visible somewhere in the learner's main route.

For an algorithm, an exact selected body often reads better than a long type-annotated signature. An optional **interface summary** may explain inputs and units in words: for MAT05, `strain`/`stress` are arrays, the modulus is expressed in GPa, the offset is dimensionless strain, and the optional intercept is in MPa and defaults to zero. Show meaningful defaults; stripping `intercept=0.0` from the visible interface would lose real behavior. For a compact simplified signature like `def offset_crossing(strain, stress, modulus, offset, intercept=0.0):`, state plainly that it is a **display-derived signature**, not a literal excerpt.

**Concrete MAT05 pilot:** The prose already explains the 0.2% shifted-line crossing. Keep the relevant source-exact calculation from `gap = ...` through the interpolation and return, including the guard that rejects invalid crossings. Explain `e` and `s` as arrays prepared earlier. Keep the full typed function and original docstring at the exact Source link. Assess whether the learner needs the complete algorithm or whether a shorter *source-exact*, clearly marked selection plus the graph communicates it better; do **not** silently remove the guard or pretend the fragment can run without its inputs.

Types are not uniformly noise. Retain or explain them when they encode complex-valued physics, array geometry, state records, optional values, agent-tool validation, or theorem hypotheses. For Lean/proof code, source syntax and precise types are often the entire point: do not apply a generic Python “simplify signatures” transform to formal proofs.

### U1g. Syntax highlighting and code-block parity

`site/_quarto.yml` already specifies the accessible Quarto/Pandoc `a11y` highlighting style for regular Python excerpts. However, the **annotated** branch of `src/pbc/authoring/excerpt.py` emits raw escaped HTML (`<pre class="excerpt-listing"><code class="language-python">...`) with line spans and notes, bypassing the normal build-time Python-token highlighting path. A `language-python` class alone does not establish equivalent token coloring. Inspect the built result, then provide consistent **build-time, deterministic** highlighting in plain and annotated excerpts, while keeping annotated line numbers, note anchors and marked-line backgrounds distinguishable without color alone. Do not add a runtime syntax-highlighting CDN or break the offline/static contract.

Preserve copyability: a copied **full exact** excerpt should be executable given its context; a selected body should not be labelled “copy full runnable function”; line numbers/annotation glyphs should not pollute copied code. Test keyboard scrolling, screen-reader ordering, contrast (including the highlighted-line background), horizontal overflow on 320 px, and consistency with Lean formatting where applicable.

### U1h. Figure function display and transparent source linkage

**Do not require the plotting function to be displayed merely because its figure is displayed.** The learner sees the actual figure, its interpretation, and a short **Figure source** link to the commit-pinned generator. Where needed, show concise verified code for the *transformation being explained* next to the relevant interpretation, not 30–100 lines of Matplotlib `ax.plot`, `legend`, tick layout, colors, and `add_credit`/`label_status` boilerplate. This is a pedagogical decision separate from V1/V2's changes to the figures' visual styling and provenance.

Specific pilot cases:

- **MAT05:** keep the fit, 0.2% offset crossing, shifted Hooke line and residual meaning accessible; replace the **full** `draw_stress_strain` (~39 lines), `draw_elastic_regime` (~94 lines) and `draw_unloading` (~79 lines) in the main reading flow with figures, interpretation and correct Figure source links, *unless* the pilot identifies a scientific transformation that has to remain visible. The owner reviews at least the elastic-regime figure and its source-link navigation.
- **Waves 09:** avoid hiding smoothing and the `r/λ` scaling test merely because they reside in `draw_scaling` (~94 lines); disclose or extract these specific computations and their measured/processed status, then link the drawing implementation.
- **Quantum 08:** retain the physical conversion from redshift to velocity and the residual meaning without showing all `draw_calibration`/`draw_rydberg_law` layout; plot-code refactoring is a separate risk-classified decision if it moves computations.
- **Fluid Dynamics 05:** show the core pressure projection and stage/update logic but source-link routine `draw_projection` layout; preserve its false-color status, diverging scale and accurate explanation of the field.
- **Scientific Agents 01:** show allowlist validation and trusted/untrusted tool-call boundaries, not the canvas instructions that draw the diagram; the diagram remains.
- **Thermodynamics 09 and Astrophysics 09:** preserve the existing useful pattern where the primary shown code constructs/verifies a physical model or data analysis without unnecessary plot-function listings.

An author should never infer “unnecessary” simply from a function's `draw_` name, nor hide actual data selection/processing, a scientific assumption or a tested computation only because it happens to occur in plotting code.

### U1i. Evidence, rendering review and compatibility tests

All U1 code-presentation changes are **display-layer modifications** except a separately planned scientific refactor. Preserve PBC's exact-source guarantees, source digest/build commit, source line mapping, note anchors, `interface=True` unit extraction, source-visible-to-tested-code checks, `reproduce_this()`, figure identities, claim/evidence mappings and no hand-entered numerical values. The current `excerpt()` implementation already supports `lines=` and `region=` for source-exact selections; extend it only where the review demonstrates an actual need for selective docstring/signature handling and for truthful multi-range display. The existing authoring policy marks manually written, non-executed code as **not verified**; introducing a visually simplified **derived** signature/snippet changes the presentation contract and **requires the planner to evaluate, and if necessary seek owner approval for, that rule and its checker before shipping it**. Until that approval, rely on exact-source selections plus prose/interface summaries rather than silently introducing transformed code. Avoid a parallel unverified code-snippet store.

The verification plan must separately establish:

- **Exact source**: displayed lines byte-for-byte (or whitespace-normalized under an explicitly documented display policy) match the pinned source positions. If lines were omitted, omission marks and source line numbers are accurate; scientific conclusions do not depend on silently omitted setup or guards.
- **Derived teaching representation**: visibly named as simplified, compared to an authoritative implementation or reference test, source-linked and never labelled source-exact, compiled, executed or fully reproducible when it is not.
- **Default-bearing signatures**: displayed defaults match Python; units, array meaning, boundary conditions and failure paths are not accidentally hidden.
- **Highlighted variants**: plain, annotated, selected and simplified Python snippets render with accessible consistent highlighting and functioning notes; source links open the correct exact commit/line ranges, and copying cannot corrupt the code.
- **Educational outcome**: after MAT05 and Mechanics 01/05 before/after screenshots, a reviewer can name the operation each retained code excerpt teaches and can locate complete plotting code in one action. Retained code is scientifically relevant; no “shorter is always better” line-count criterion.

**U1 pilot review set:** Mechanics 01 (introductory state update), Mechanics 05 (annotated integrators), Materials 05 (long type-annotated and plotted functions), Waves 09 (analysis embedded in plot function), Fluid Dynamics 05 (numerical PDE solver), Scientific Agents 01 (validation versus diagram rendering), plus **one protected formal-proof example** (Lean 01 or 04). Only the planned pilot lessons are content-redesign candidates; other sampled lessons receive display-only prototypes or source-based checks unless separately authorised.

## 12. Integration into F116 and future authoring
### Existing F116 remains the integration point

F116's approved goal remains: integrate editorial principles into `docs/authoring.md`, `docs/lesson-template.qmd`, and the qualitative lesson review rubric, **without a rigid narrative template, new agent or extra review workflow**. Preserve its two later additions from requirements decision 43: (1) conceptual synthesis across the lesson/sequence and (2) explicit evidence provenance for AI lessons (model transcript, written example, recorded run, tool replay, independent evaluation).

### Proposed amended dependency

`F114 (delivered) → F115 (delivered and owner-approved) → T1 teaching skill → T2 Mechanics pilot + T3 cross-module calibration and owner decision → F116 integration`.

V1/V2 figure work and U1 reading-interface work can be developed independently of T2 and F116 where their shared-file conflicts are controlled. I1 requires pedagogical selection in T2/T3 but is not required before F116 if no widget is approved; F116 can state the principle that *interactivity is optional and purpose-driven*.

F116 should record the approved teaching principles **and approved code-selection rules** in existing guides and review guidance, with links to the skill. The template must demonstrate both a source-exact, scientifically important code excerpt and a figure whose renderer is accessible only by a Figure source link. Distinguish source-exact snippets, clearly selected source and simplified pedagogical representations; require an explicit reason for each exposed code block, not an automatic list of every helper. **Distinct archetype examples** (simulation, measurement, capstone, scientific agent, Lean) are more useful than five repetitions of one generic chapter structure. The template illustrates choices rather than mandating identical section sequences. The reviewer supplies named **weakness → evidence → action**, not a style score. The new skill stays a reusable tool, not a second authoritative guide.

### Lessons outside the pilot

Do **not** rewrite all existing lessons as an automatic consequence of F116. Apply the approved principles to new lesson features and to published lessons when there is a separately scoped content change or course-level review. F160's later book-wide review can assess sequence consistency once content stabilizes; do not expand F160 in this planning without a deliberate decision.

## 13. Sequencing and proposed feature slices
**The planner assigns new feature IDs; none are reserved or invented here.** Reconcile the currently approved roadmap, open Issues, and active PRs at the start of the change cycle. Prefer one Issue per independently deliverable slice; do not create Issues for every checklist item or every lesson before pilots are accepted.

| Slice | Deliverable | Main dependency | Merge/approval boundary |
|---|---|---|---|
| **P0 — Planning** | Approved change request, reconciled roadmap/dependencies and necessary amendments | Owner approval | Planning PR; no feature implementation before approval |
| **U1a–d — Reading experience** | Compact header, Source link, status typography, closed reproduction detail | P0 | Small PRs by shared component; full verification when shared inputs change |
| **U1e–i — Code presentation pilot** | Exact/derived excerpt taxonomy, selective docstrings/signatures, annotated Python highlighting, plotted-function Source links; MAT05 + Mechanics 01/05 and cross-module checks | P0; coordinate with T1/T2/T3 and scientific figure work | Separate authoring-renderer/lesson PRs; independent science review of any changed visible algorithm; owner reviews rendered examples |
| **T1 — Teaching skill** | Project-owned skill, provenance, examples, selection policy | P0, ADR 019 process | Separate feature; no lesson changes |
| **T2a–c — Didactic lessons** | Mechanics 01, 03, 05 pedagogical pilot | T1 | Separate lesson PRs and independent science review; owner reviews rendered results |
| **T3 — Cross-module calibration** | Source-based diagnosis on measured lab, engineering capstone, agent and Lean; at most one extra redesign if approved | T1; T2 findings | Owner judges archetype coverage before F116; no mass editing |
| **V1a — Figure style pilot** | Six-class visual audit and bounded prototype | P0; existing visualization skill | Approve before a global `rcParams` rollout |
| **V1b — Figure style rollout (conditional)** | Centralized selected defaults and needed plot-specific helpers | V1a owner decision | Full site/build verification; measure payload and visual differences |
| **V2a — Figure metadata/attribution pilot** | AST09 and MAT05, plus one cross-course mixed-data figure; HTML + portable PNG contract | P0, existing dataset cards and check suite | Independent rights/science review; choose branding and export strategy |
| **V2b — Credit/status rendering rollout (conditional)** | Implement chosen single-source provenance and update tests safely | V2a owner decision | Full verification; no weakened status or rights checks |
| **I1 — Selected interactions (conditional)** | Up to two lesson widgets across courses, not F128 | T2/T3 owner decision, F07 | Separate scientific/UX verification for each widget |
| **F116 — Editorial and pedagogical integration** | Updated authoring guide, template and rubric | F115 + T2/T3 owner decision, T1 | Retain original F116 scope and requirements decision 43 |
| **Later adoption** | Targeted updates in new lessons and existing course reviews | F116 | No blanket migration or extra gate |

**Coordination:** where U1, V1, V2, T2/T3 and F116 touch `src/pbc/authoring`, shared templates, CSS or the same `.qmd` files, sequence/rebase the PRs rather than merging changes in one unreviewable diff. Do not block independently approved ordinary lesson features while a visual or editorial pilot is open.

## 14. Verification, risk and performance
The following are inherited, **not weakened**:

- Published statements remain within the type/scope/evidence of the original scientific claim. A changed claim is classified and escalated under the current risk policy.
- Code-display transformations are never allowed to turn **non-verbatim or non-executable snippets into allegedly exact, executed functions**. Verified source ranges, omitted-line indicators and copied text remain truthful; the annotated-line highlighting and explanation markers remain accessible. Source docstrings, type annotations, guards and assumptions must not be changed or removed merely to improve presentation.
- Numerical values, tested Python code, exact-source excerpts, generated figures and displayed results remain traceable to their authoritative computation. **A cleaned-up plot must not change the data series, regressions, uncertainty semantics or scientific meaning; display-only marker reduction must be reviewed separately from any data filtering.** Reproduction works without rebuilding the site.
- A change to shared experiment settings, authoring generators, shared CSS, Quarto templates or other shared inputs is treated as a **whole-site dependency change** under the current selection policy. Run the full verification required by the repository, not just a successful targeted lesson check.
- Determinism, source/code digest integrity, fixed build environment, semantic MathML, full offline/no-external-request properties and accessible static fallbacks remain. For a standalone PNG, metadata/credits must be deterministic, legally sufficient, and consistent with the exact on-page artifact. Existing unit/integration checks for `check_figure`, reference figures and experiments must be migrated to equally strong or stronger assertions, never dropped.
- A third-party dataset's publication and attribution rights are evaluated **per dataset card**; the use of third-party or public-domain data is not rebranded as PBC measurement ownership. AG16 model-input figures/replay fixtures remain stable unless separately reviewed and approved.
- Scientific results are not redrawn by a visual-design model and then presented as verified. Visualization skills and the new teaching skill are guidance, never a proof or result.
- Verify on Chromium, Firefox and WebKit where existing checks apply; inspect representative layouts at desktop, tablet, 390/360/320 CSS pixels, enlarged text, high contrast where relevant, and reduced motion for interactions.
- Report **observed** figure sizes, page weights, CI/build duration and visual results against the current accepted budgets. Do not adopt the old speculative “1–2 days,” “250 KB per image,” or Plotly/ECharts size estimates as enforced thresholds without fresh measurement.
- Risk level is determined by changed paths, actual triggers and reviewer assessment. Some pilot slices may be Level 2, while protected-path or changed-claim changes may be Level 3. Do not preapprove a level or skip required owner/CI gates.

## 15. Whole-change acceptance criteria
This change is complete when all unconditional criteria below are met and every conditional slice is either delivered with evidence or explicitly declined/parked by the owner:

1. **Documented boundaries:** voice, teaching pedagogy, scientific authoring, and scientific visualization have distinct ownership; no contradictory guides or secondary palettes exist.
2. **Skill:** the project-owned teaching skill is audited as project-local input, versioned, discoverable/readable in supported workflows, and tested on realistic PBC examples, without an added agent or runtime dependency.
3. **Pilots:** Mechanics 01, 03 and 05 have reviewed before/after artifacts and a recorded owner decision; all essential scientific material remains accessible and verified.
3a. **Cross-course calibration:** the teaching principles have been tested against at least four different lesson archetypes, with concrete examples of improvements *and* good passages that should not change; no unconditional mass migration is approved.
4. **Learning quality:** reviews identify specific improvements or failures in learner motivation, prerequisite alignment, conceptual understanding, mathematical bridges, prediction, and interpretation. No unmeasured learning-outcome statistics are claimed.
5. **Figures:** a representative multi-type comparison justifies every shared style choice; if adopted, the style is coordinated across the two current palettes, accessible, reproducible and scientifically faithful, with full verification of shared changes.
5a. **Portable provenance:** source status and data credits are accessible without duplicate visual clutter; a standalone PNG/export has verified accurate status, identity, licence and source attribution; the validation suite remains strong and rights are preserved per dataset.
5b. **Figure examples:** AST09 and MAT05 are visually reviewed after changes at desktop and mobile and on export; a third mixed measured/model example and the AG16 multimodal-input constraint are checked. The owner decides whether any subtle on-image PBC credit improves, rather than harms, the result.
6. **Artwork:** no new raster permission or ADR is created; existing ADR 021 provenance, allowed formats and class restrictions continue to hold.
7. **Interactivity:** optional lesson interactions reuse F07, pass scientific and accessibility checks, retain static equivalents and preserve performance. F128 remains separately gated.
8. **Reading UI and code:** important learning context is immediately visible, technical details discoverable, and source provenance plus full reproduction untouched; no loss of screen-reader or keyboard function. Visible source blocks have pedagogical purpose, source-exact versus simplified presentations are visibly distinguished, relevant science is never concealed with plotting boilerplate, and annotated Python syntax highlighting works consistently. At minimum MAT05 and Mechanics 01/05 are reviewed as rendered examples, plus the cross-module source-level checks.
9. **F116:** its original authoring/template/reviewer obligations and two textbook-layer rubric additions are delivered, extended only by the approved pedagogical outcomes; no generic text generator or rigid lesson recipe.
10. **Governance:** approved planning changes precede new feature Issues; full/targeted checks, risk review and owner approvals follow the current repository rules. Decisions, rejections and partial deliveries are recorded transparently.

## 16. Explicitly out of scope
- No new courses, lessons, capstones or changed Part A/Part B reference curriculum.
- No mass generation or automatic restructuring of all existing lessons.
- No lower standard for reproducibility, verified figures, evidence claims, Lean proofs, accessibility, copyright or dataset licensing.
- No blanket ban on docstrings/type annotations, wholesale deletion of `draw_*` excerpts by filename alone, or forced short pseudocode in place of the core Python algorithms. Never rewrite production function signatures just to shorten a displayed lesson.
- No new requirement for every lesson to include an interaction or an animation.
- No global switch from Python-generated figures to images produced by a generative model.
- No mandatory watermark or PBC claim of ownership over TESS/MAST, NIST or other external measurements; branding is a scoped, optional form of visualization attribution.
- No removal of figure-status, required data licences or credits without an equally strong portable/HTML path and verified scientific metadata.
- No AVIF permission or new asset format; no blanket permission for raster graphics within lessons.
- No ECharts, Plotly, new frontend framework, bundler or browser-physics engine as part of this change.
- No activation or relocation of F128 without its separate existing owner decision.
- No new mandatory AI role, change to the owner approval hierarchy, weakening of CI, or optimization for AI-text detectors.

## 17. Decisions for the planning owner
For clarity, these are the **proposed defaults submitted for approval**, not decisions already recorded:

| Question | Proposed default |
|---|---|
| Should PBC adopt a new teaching skill? | **Yes**, project-owned, separate from Editorial Voice and scientific figure skills. |
| Should F116 happen before the teaching pilot? | **No**: keep F116, but integrate the lessons learned only after a small, approved pilot. |
| Which pilot lessons? | **Mechanics 01, 03, 05**, plus cross-module diagnostics on a measured lab, a capstone, a scientific-agent lesson and Lean; at most one extra approved lesson redesign. |
| Should we apply a Matplotlib style to all lessons immediately? | **No**: audit six representative figure types, pilot, then decide rollout; keep both palette systems under one documented usage rule. |
| Should `status: processed` and the long data credit remain painted inside every PNG? | **Not necessarily:** pilot one validated semantic HTML/caption + portable PNG provenance contract first; do not simply remove the tested labels/credit. |
| Should every figure get a PBC watermark? | **No:** only evaluate optional small visualization attribution on exports, never on top of plotted data; retain correct external data credit. |
| Do complex later-course lessons need their own pilot? | **Yes, for calibration** on measured labs/capstones/agents/Lean, but no automatic 104-lesson rewrite. |
| Are raster illustrations a new feature? | **No**: already covered by ADR 021; retain WebP/PNG and existing provenance rules. |
| Should we add ECharts or Plotly? | **No**, not without a demonstrated need and separate approval. |
| Should the double pendulum F128 start here? | **No**: preserve its current independent owner gate. |
| Should reading-interface clutter be improved? | **Yes**, in small shared-component PRs, preserving complete discoverable provenance. |
| Should every full function and docstring remain on the lesson page? | **No**. Show only the source necessary for the learner's physics/code objective; retain full docstrings and annotations in Python and at the Source link. Keep defaults and important units visible. |
| Should we display shorter untyped function definitions? | **Sometimes**, as clearly labelled **display-derived summaries**, never disguised as byte-for-byte source. Exact relevant body lines are preferred. **Conditional on explicit reconciliation with current `not verified`/exact-source rules and any necessary owner approval.** |
| Should every figure show its `draw_*` function? | **No**. Default to figure + explanation + exact Figure source; **first identify scientific transformations inside plotting code** and display them where relevant. |
| Does annotated Python code need a highlighting improvement? | **Yes, conditional on a rendered audit**: the raw-HTML annotated path needs the same accessible, deterministic token highlighting as ordinary Pandoc Python code. |
| Which cross-module code-presentation examples must be considered? | Mechanics 01/05, MAT05, Waves09, FL05, Agents01 and a Lean case; use Thermodynamics09/AST09 as positive counterexamples. |

## 18. Existing sources to reconcile during planning
- [PBC project requirements](https://github.com/taspinar/physics-by-construction/blob/main/docs/PROJECT_REQUIREMENTS.md) — project goal and decisions 32, 36–38, 40–43.
- [Roadmap — F114–F116](https://github.com/taspinar/physics-by-construction/blob/main/docs/roadmap.md) — original editorial program and F116 scope.
- [Roadmap — F128/F129](https://github.com/taspinar/physics-by-construction/blob/main/docs/roadmap.md) — separate pendulum gate and scientific figure pilot context.
- [Editorial Voice Guide](https://github.com/taspinar/physics-by-construction/blob/main/docs/editorial-voice.md); [F115 pilot Issue #375](https://github.com/taspinar/physics-by-construction/issues/375).
- [Authoring Guide](https://github.com/taspinar/physics-by-construction/blob/main/docs/authoring.md) — scientific authoring, figure, widget, excerpt and reproduction constraints.
- [Python source-excerpt implementation](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/authoring/excerpt.py) and [site code styling](https://github.com/taspinar/physics-by-construction/blob/main/site/assets/site.css), plus [`site/_quarto.yml`](https://github.com/taspinar/physics-by-construction/blob/main/site/_quarto.yml) — source identity, line annotations, and regular versus raw-HTML highlighting behavior.
- [Materials 05 lesson](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/materials/05-stress-strain-measurements/index.qmd), [core stress–strain computations](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/materials/stress_strain.py) and [experiment figure routines](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/materials/experiments/stress_strain_measurements.py) — `offset_crossing`, ~94-line `draw_elastic_regime`, and shift/residual calculations inside the plot.
- [Waves 09 experiment](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/waves/experiments/lycopodium_diffraction_lab.py), [Quantum 08 experiment](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/quantum/experiments/atomic_spectroscopy.py), [Fluid Dynamics 05 solver](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/fluids/navier_stokes.py), [Scientific Agents 01 experiment](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/mechanics/experiments/agent_experiment.py) — different boundaries between scientific computation and plotting/diagram construction.
- [ADR 018](https://github.com/taspinar/physics-by-construction/blob/main/docs/decisions/018-scientific-atelier-asset-classes-and-the-course-atlas.md) and [ADR 021](https://github.com/taspinar/physics-by-construction/blob/main/docs/decisions/021-quieter-site-two-layer-atlas-and-raster-interface-artwork.md) — amended asset classes and permitted raster artwork.
- [ADR 019](https://github.com/taspinar/physics-by-construction/blob/main/docs/decisions/019-agent-skills-audited-pinned-and-project-local.md), [current process](https://github.com/taspinar/physics-by-construction/blob/main/docs/process.md), [skill README](https://github.com/taspinar/physics-by-construction/blob/main/.agents/skills/README.md).
- [Figure encoding / `FIGURE_SETTINGS`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/experiment.py); [design tokens / `FIGURE_COLOURS`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/authoring/design.py).
- [Measured-data plotter: `label_status`, `add_credit`, `COLOURS`, `check_figure`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/data/plotting.py); [corresponding regression tests](https://github.com/taspinar/physics-by-construction/blob/main/tests/unit/test_data_plotting.py); [figure status HTML filter](https://github.com/taspinar/physics-by-construction/blob/main/site/_filters/lesson.lua).
- [AST09 experiment figures](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/astrophysics/experiments/exoplanet_light_curves.py); [MAT05 experiment figures](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/materials/experiments/stress_strain_measurements.py); [AG16 image-as-input lesson](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/agents-llm/16-multimodal-physics-reasoning/index.qmd).
- The companion cross-course audit, inlined as Appendix B of this change request.
- [F07 Issue #23](https://github.com/taspinar/physics-by-construction/issues/23) and [Mechanics 05](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/mechanics/05-numerical-integrators/index.qmd).
- [Planning workflow](https://github.com/taspinar/physics-by-construction/blob/main/docs/workflow.md), particularly “Changing an approved planning”.

---

**Change-cycle routing:** This document is a request to amend approved *planning*. It is not itself a roadmap update, ADR decision, GitHub Issue, or authorization to edit published lessons. The planner should reconcile the current approvals and roadmapped features, evaluate whether the existing requirements already permit every proposed slice, and use the established planning review/owner approval process. Only after approval should scoped feature Issues be created.

---

## Appendix A — Additions by the owner (2026-11-13)

The owner added the following to this change cycle on 2026-11-13 ("Alles, ook capaciteit"). They are reconciliation and decision items, not new teaching workstreams; the planner handles each and records the outcome.

### A1. Roadmap corrections that only a planning cycle may make

1. **The outcome check of F136** (#370): D7 and D8 move from "reused" to "extended" (their extensions belong to F146 and F147), the counts become 1 reused and 16 extended, MD3 gains symbolic regression, and the sentence about the curriculum file holding the slots since F136. The exact edits are recorded in `.agents/plans/370-part-b-curriculum-migration.md`, section "Roadmap updates left for the next planning change", and on Issue #370. `docs/roadmap.md` still shows MD3 and MD4 as "reused".
2. **The stale sentence** "Until F136 merges, the curriculum file still …" in `docs/roadmap.md` (F136 is merged).
3. **The build timeout:** the roadmap still states a `build` job of 90 minutes; the job's timeout is 120 minutes since #373.

### A2. Reconcile the work delivered since the approval of 2026-11-04

The planning approval (`docs/PLANNING_APPROVAL.md`, commit 2cb6641) became stale because merged features changed the roadmap and requirements; `create-feature-issue.sh` has refused since, and #454, #470, #507 and #508 were created by hand on the owner's word. Bring the roadmap's status and counts up to date with what is on main, at least: F157 (#445), F158 (#466), the lesson time budgets (#383, #398), Home and the Course Atlas (#481–#483, #487; PRs #484, #485, #486, #490), the gate chain (#463, #464, #446; PRs #468, #474, #476) and the verification changes (#430/#431, #412/#432, #404/#413); the measured-data labs EM8 (#478), Q8 (#480), AST8 (#489), MAT6 (#488), T7 (#491), M15 (#492), T8 (#493), W7 (#495), Q7 (#497), FL8 (#498), MAT5 (#499), AST9 (#502), FL7 (#503) and the figure follow-ups (#505); and, at the time of planning, in flight: FL10 (#444, PR #506), EM7 (#507, F54), the F140 desk spike (#508), and #353/#423/#494 (PR #504). The status rows of F52, F53 and F54 ("no Issue; not started") and the "slots to fill" counts are out of date.

### A3. Overlaps to resolve explicitly

- **U1 (reading experience) against F127** (the rollout of the reading template and the capstone template; no Issue). Decide whether U1 replaces, absorbs or precedes F127, so the same templates are not reworked twice.
- **V1a (figure-style pilot) against F129** (the figure and diagram skill pilots; no Issue).
- I1 against F128 and the F116 sequencing are already handled in sections 10 and 12.

### A4. Unambiguous lesson names

This request and Appendix B name lessons by **course directory and file number** ("MAT05", "AST09", "Q07"), which collide with **slot labels**: materials/05 is slot MAT6, while slot MAT5 is the X-ray lab materials/06; astrophysics/09 is slot AST8, while slot AST9 is astrophysics/10. In the approved documents and Issues, name every lesson by its slot label and its path. The mapping for the names used here (main, 2026-11-13):

| Name in this request | Path | Slot |
|---|---|---|
| Mechanics 01, 03, 05, 08 | `mechanics/01-…`, `03-…`, `05-…`, `08-kepler-orbit` | M1, M3, M5, M8 |
| M13, M14, M20 | `mechanics/13-double-pendulum-chaos`, `14-lagrangian-mechanics`, `20-pendulum-measurements` | M9, M10, M15 |
| MAT05 | `materials/05-stress-strain-measurements` | MAT6 |
| AST04, AST05, AST08, AST09 | `astrophysics/04-special-relativity`, `05-relativistic-orbits`, `08-exoplanet-transit`, `09-exoplanet-light-curves` | AST10, AST4, AST7, AST8 |
| EM07 | `electromagnetism/07-adaptive-phased-array-beam-steering` | EM9 |
| Q01, Q04, Q07, Q08 | `quantum/01-…`, `04-spin-and-stern-gerlach`, `07-quantum-measurement-statistics`, `08-atomic-spectroscopy` | Q1, Q4, Q8, Q7 |
| T04, T07, T09, T10, T11 | `thermodynamics/04-…`, `07-…`, `09-thermal-engineering-…`, `10-soil-temperature-measurements`, `11-brownian-motion-tracking` | T4, T6, T11, T7, T8 |
| W08, W09 (Waves09) | `waves/08-wave-flume-lab`, `09-lycopodium-diffraction-lab` | W8, W7 |
| FL04, FL05, FL07, FL08 | `fluids/04-shallow-water-equations`, `05-navier-stokes-fundamentals`, `07-particle-based-fluid-simulation`, `08-turbulent-boundary-layer-measurements` | FL5, FL2, FL6, FL8 |
| AG16, Agents01 | `agents-llm/16-multimodal-physics-reasoning`, `01-an-agent-runs-an-experiment` | AI6, SA5 |

The audit's inventory (104 lessons, 255 figure declarations) is a snapshot of 2026-11-13 before MAT5, AST9 and FL7 merged; keep it as a dated snapshot rather than recounting silently.

### A5. The capacity decision (#278 with #150)

The roadmap's capacity gate forbids any lesson feature to take the number of published lessons past 110 before the owner's capacity decision on #278 with #150. Facts on 2026-11-13: **107 lessons** on main; **109** after FL10 (#444) and EM7 (#507); Part B stages C and D add **17 lesson pages** (13 lessons and four capstones), about **126**. The `build` job's timeout is 120 minutes (#373); the last three successful push runs on main spent 52, 62 and 84 minutes in `build` (selective and full runs not distinguished here; measure them). F113 (#150, lesson shards, ADR 014 decision 11) and the paused part of ADR 017 (incremental main) were deferred by #412 until 95 lessons or a main run near 80 minutes; **both triggers are now met**. Put the decision to the owner with fresh measurements: shards (F113), incremental main (ADR 017), a further timeout, or keeping the cap, and what each costs. This change cycle adds no lessons itself; the decision is needed before Part B stages C and D.

### A6. Reuse of passed verification groups (#385)

The owner's parked proposal #385 (reuse a passed verification group when its inputs are unchanged) needs a planning change before it can start (what counts as a group's inputs, where passes are stored, when reuse is forbidden; a Level 3 final verification always runs in full). Record it as a decision for the owner in this cycle: keep it parked, or plan it, alongside A5.


---

## Appendix B — The cross-curriculum teaching and figure audit (inlined)

### B. Physics by Construction — Cross-curriculum teaching and figure audit

**Date:** 2026-11-13  
**Status:** Review findings and planning input; not an approval or a claim of a completed rendered-site visual audit  
**Repository:** [taspinar/physics-by-construction](https://github.com/taspinar/physics-by-construction) (`main`, as inspected)  
**Related request:** this change request, `docs/changes/teaching-by-construction.md` (the audit is its Appendix B)

### 1. Scope and evidence

The repository tree was inventoried: **104 lesson `index.qmd` source files** across 11 course/strand directories, containing **255 declarations of `fig-status`**. This count refers to figure declarations; one figure may contain multiple panels. The scan covered each source's opening, headings, lesson structure, stated difficulty, figures/captions, code excerpt usage and selected claims/limits. Selected lessons and their experiment/test implementation were examined more closely, particularly Mechanics 01–05 and 08, Thermodynamics 09, Electromagnetism 07, Astrophysics 09, Materials 05, Quantum 07, Fluids 08, Waves 09, and the LLM-agent and Lean strands. The two supplied screenshots were examined visually.

**Limit:** This is a cross-curriculum *source and sample-based didactic review*, **not** a claim that all 255 rendered figures were inspected pixel by pixel or that each of the 104 lessons underwent a full independent physics review. The live published pages could not be opened through the available website browser, and the entire Quarto site was not rebuilt in this review. The proposed planning pilot must therefore collect rendered desktop/mobile evidence and scientifically validate any modified figure. The findings below are editorial hypotheses unless supported by a quoted source/check or a supplied screenshot.

#### Course / strand inventory

| Course / strand | Lesson sources | Declared figures | Representative focus |
|---|---:|---:|---|
| Classical mechanics | 20 | 58 | Early simulations; later orbital dynamics, chaos, proofs and measurements |
| Thermodynamics | 11 | 28 | From intuitive random walks to finite elements, engineering and real data |
| Waves and optics | 9 | 30 | Clear physical hooks; later calibration and measured diffraction |
| Electromagnetism | 8 | 23 | Field and circuit models; high-density phased-array capstone |
| Fluid dynamics | 8 | 15 | Conservation and PDE solvers; later turbulent measurements |
| Quantum physics | 8 | 22 | Abstract concepts; Bell-test measurements and atomic spectra |
| Astrophysics | 9 | 27 | Dynamical models; high-density exoplanet-measurement pipeline |
| Materials science | 5 | 13 | Microscopic and mechanical models; dense stress–strain laboratory |
| LLM / scientific agents | 20 | 31 | Replay, evaluation, baselines, evidence and generalisation |
| Agent-based modelling | 1 | 2 | Kinetic intuition from particle interactions |
| Lean / formal proofs | 5 | 6 | Proof interpretation and practice |
| **Total** | **104** | **255** | |

### 2. Are later lessons worse than Mechanics 01–05?

**Not as a blanket judgement.** Several courses start with accessible physical questions that are as good as, or better than, Mechanics 01–05. Examples include Thermodynamics 01's ink-drop/random-walk story, Waves 01's plucked string, Electromagnetism 01's charged balloon, Quantum 04's Stern–Gerlach beam, and Materials 01's crystal disturbance. The technically rich courses also often distinguish what a simulation establishes from what measurements establish, which is a PBC strength.

The issue changes with **lesson archetype and complexity**, not only with position in a course. Mechanics 05 has ~5,300 source-prose words, 28 by-reference excerpt calls and five figure declarations despite being difficulty level 2. Mechanics 08 (Kepler) has ~5,170 source-prose words, eight numbered assumptions and 33 excerpt calls at difficulty 3. Quantum 07 has ~4,735 source-prose words and a substantial statistical measurement analysis. These are *review signals*, not objective limits: they indicate where a staged explanation, clearer intermediate goals, or better navigation may matter more than line editing.

Most lessons place a multi-item **Assumptions** section before their core explanation, followed by **Code**, **Worked examples**, **Limits**, and exercises. This provides scientific clarity but risks requiring students to digest every boundary condition before seeing what motivates it. The recommended change is **just-in-time explanation of essential assumptions**, not removing or hiding assumptions that determine the scope of a result.

#### Module-by-module findings

| Course | What already works | Candidate improvement not fully captured by the original Mechanics-only pilot |
|---|---|---|
| **Mechanics 06–20** | Continuity from numerical error to conservation, collisions, orbits, chaos and physical labs | M08's extended orbit derivation could use a visual roadmap; M13 (double pendulum) and M14 (Lagrangian mechanics) each have only one declared figure and merit a *selective* conceptual-visual assessment, not mandatory animation; M20 requires the measured-data teaching pattern |
| **Thermodynamics** | Strong physical openings; T09 explicitly puts requirements before its engineering model (good capstone exemplar) | T07–T09 rapidly escalate numerical methods; use intermediate checkpoints and an engineering-decision map; T10–T11 need a clear raw/processed/model/uncertainty lineage |
| **Waves and optics** | Excellent everyday hooks (string, flute, slit, polarizers) and prediction-friendly phenomena | W08–W09 can separate the main physical discovery from calibration, smoothing, fitting and provenance; W09's missing absolute calibration is an exemplary limitation that must remain prominent |
| **Electromagnetism** | Clear real-world motivation and numerical-model checks | EM07 contains six figure declarations and a substantial engineering trade-off; its **requirements appear under Worked examples after the code**. Consider introducing the design brief and success criteria before the full derivations, then refer back to them |
| **Fluid dynamics** | Conservation-first explanation and meaningful examples such as dye, shock waves, dam breaks and cylinder wakes | FL05–FL07 introduce large conceptual jumps in PDE solvers; consider diagrams of solver steps and grid/particle differences; FL08 should distinguish assumptions built into processing from independently observed agreement |
| **Quantum physics** | Q04's two-spot Stern–Gerlach contrast and Q05's Bell inequality are good conceptual hooks | Q01 requires a bridge from probability to a wavefunction; Q07's measured CHSH analysis should give a small event-count → correlation → test-statistic roadmap before full uncertainty/loophole analysis; Q08 needs the measured-line/data model distinction |
| **Astrophysics** | Strong continuity between orbit mechanics, relativity and exoplanet modeling | AST09 (the first supplied screenshot) handles **21 folded transits**, cleaning, detrending, limb-darkened fitting and residuals. A visible data-processing roadmap, less crowded plot and concise reusable source credit would help; AST04/05 could use optional derivation depth where appropriate |
| **Materials** | Clear microscopic-to-macroscopic conceptual progression | MAT05 (second supplied screenshot) combines tension/compression/fracture, hysteresis, elastic fit, unloading and necking. Keep the complete analysis but separate the learner's observations from the full fitting/statistical machinery, and simplify the legend/credit layout |
| **LLM/scientific agents** | Good epistemic discipline: replay, comparisons, held-out scores, limits, independent evaluators | Many agent lessons repeat the tool/evidence protocol. Use a short **what changed in this experiment?** bridge and link common procedural background, while preserving the exact evidence class near the opening. Test implications before changing figures used as model inputs (especially AG16) |
| **Agent-based modelling** | Intuitive emergence from local particle rules | No high-priority restructuring inferred from one source lesson; use as a positive exemplar in the teaching skill |
| **Lean** | Clearly distinguishes experimental checks from universal proofs | Provide an explicit learner pathway from *reading* a theorem to *editing* a proof and interpreting failed tactics. Do not replace formal rigor with visual explanations or require in-browser Lean |

### 3. Detailed observations on the two supplied figures

#### AST09 — Transit fit with residuals

**Source:** [`src/pbc/astrophysics/experiments/exoplanet_light_curves.py`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/astrophysics/experiments/exoplanet_light_curves.py), `draw_transit_fit`.

**Scientific strength:** raw/processed cadences, binned means, uncertainties, two competing fitted models and residuals are distinguished. The residual panel is scientifically useful and should stay.

**Presentation problems:** `status: processed` is rendered as a separate box above the axes; lengthy dataset and data-preparation credit is painted into the bottom of the PNG; legend phrases repeat statuses and processing descriptions; there are two substantial figure titles plus the lesson caption. A narrow reading column must shrink all image-embedded text together. This reduces the visual area available for the actual transit comparison. The figure-level status represents processed measurement but two model series are simulated; the caption/legend should state the roles of all three without presenting the models as independent measurements.

**Recommendation:** keep the two panels. Use concise on-plot labels such as “Limb-darkened fit”, “Uniform-star fit”, “Binned observations”; preserve marker/line-style distinctions. Put full credit in semantic text linked to the dataset card, not in the analysis axes; keep a portable provenance path for the output PNG. Keep the scientific caption's interpretation, but avoid repeating the entire title and status there.

#### MAT05 — DP980 stress–strain curve

**Source:** [`src/pbc/materials/experiments/stress_strain_measurements.py`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/materials/experiments/stress_strain_measurements.py), `draw_stress_strain`.

**Scientific strength:** the three loading phases, shaded hysteresis, stress landmarks and measured status are meaningful. The shaded loop conveys a physical phenomenon no sentence alone conveys. Keep these distinctions.

**Presentation problems:** legend includes seven entries, some describing status rather than visual encodings; it consumes a significant part of the available chart area; the long NIST credit takes a second strip below; the big status pill repeats figure metadata; abundant markers can distract from the path. The plotted data need not become less precise to show fewer decorative markers.

**Recommendation:** distinguish the three phases with concise names, use a common legend that can sit outside the axes or direct labels where legible, and move the detailed NIST source into a responsive caption/provenance disclosure. Keep a concise, accurate source credit attached to downloadable or shareable representations. Preserve the original numerical data and the scientifically meaningful extrema and hysteresis loop.

### 4. Newly discovered implementation constraints

1. **Duplicate source status:** `pbc.data.plotting.label_status(fig, ...)` paints a status box into the Matplotlib figure; the Quarto/Lua filter separately exposes `fig-status` in the HTML caption. `pbc.data.plotting.check_figure()` rejects a figure without an in-figure status marker, and specific unit tests assert the marker's existence and replacement. A visual change must **migrate the validation**, not delete a label and weaken the checks.
2. **Credit line is part of the bitmap:** `add_credit(fig, ...)` reserves bottom margin and renders a wrapped source string. `tests/unit/test_data_plotting.py` explicitly checks the presence and positioning of that inline credit. Multiple dataset/reference/experiment files repeat their own source strings. Moving attribution must address this tested contract and avoid introducing a second, drifting source of provenance.
3. **Two deliberately different plotting palettes:** lesson figures import `FIGURE_COLOURS` from `pbc.authoring.design`, while measurement plotting uses `pbc.data.plotting.COLOURS` (Okabe–Ito). The difference is not automatically a defect: the latter has distinct colour-vision/accessibility intent. A shared figure design language should coordinate their roles without deleting a scientifically clearer palette merely for branding consistency.
4. **Standalone figure contract:** `pbc.experiment.encode()` generates the same deterministic PNG bytes that a lesson shows and its runnable experiment exports. The present encoder omits PNG metadata. Any decision to move source/status to HTML needs a portable alternative for exported files, such as deterministic embedded metadata plus a concise visible attribution where useful, or a validated sidecar provenance manifest. Do not silently break the page/experiment byte-identity contract.
5. **Some figures are scientific inputs:** `agents-llm/16-multimodal-physics-reasoning` uses figures as model inputs. Removing on-image credit/status can alter the model input, recorded replay, visual question and resulting evidence. This **cannot** be handled as CSS-only refactoring; it requires separate scope/evidence review, and existing input fixtures must remain stable unless independently approved.
6. **Dataset-specific rights:** the registry checks publication of figures and attribution/modification rights individually. Some sources require acknowledgement; others are public domain or have explicit licences. A universal removal of source text from images without checking each card/permission is not acceptable.
7. **Titles and legends are checked:** `check_figure` currently requires each panel to have a title and each multi-series panel to have a legend. Shorter titles and shared or direct labels therefore require equivalent validated semantic alternatives rather than merely deleting information.

### 5. Attribution, PBC identity and image reuse

A good goal is **traceability plus unobtrusive identity**, not theft prevention. PBC's CC BY 4.0 educational content is designed to be reusable with correct attribution. A large watermark is easily cropped and may confuse the ownership of third-party scientific data.

Proposed rendering principle:

- **In-page:** scientific chart area holds measurements, models, axes, uncertainty, annotation, and only the legend needed to understand those marks. A short human-readable source line appears in semantic HTML adjacent to the caption; “Full data and method provenance” expands to the existing card/dossier, creator, citation, version, rights, preprocessing and source commit. A compact evidence-status label remains available once in the surrounding figure UI. The HTML works without JavaScript.
- **Portable PNG:** preserve source status and enough identity when the PNG travels alone. Pilot a deterministic PNG metadata field and an optional unobtrusive footer such as “Visualization: Physics by Construction · Data: TESS/MAST”, with the complete attribution available through the linked dataset card/manifest. Do not claim PBC created or owns original measured data. Verify whether the individual licence requires more visible citation.
- **Export and reproduction:** retain identical figure bytes between published page and `Experiment` output on the same commit. If adopting a sidecar manifest, its binding to figure identifier, dataset ID, license/creator, status, exact source commit and file digest must be tested. Avoid an additional unversioned human-edited credit field per plot.
- **Branding:** if an optional small PBC wordmark is used, test readability, image weight, colour independence, and scientific integrity at mobile and export sizes; it is **not** obligatory and may be omitted if it compromises the data.

### 6. Recommendations to add to the planning change

1. **T3 — Cross-module pedagogical calibration:** retain the Mechanics 01/03/05 rewrite pilot, but validate the teaching skill against an advanced engineering/capstone lesson, a complex measured-data lab and an agent/Lean lesson before adopting it globally. Use actual before/after learning maps and source-specific weaknesses; do not force a single chapter template.
2. **V2 — Scientific figure provenance and presentation:** separate authoritative figure metadata from where labels appear; consolidate credits with dataset cards; implement readable HTML source/status and portable PNG provenance; add tests that preserve or strengthen the existing scientific and rights checks.
3. **V1 enhancement — Plot grammar:** assess legend crowding, repeated panel titles, high-density markers, annotations and small-screen text legibility; reconcile `FIGURE_COLOURS` with the accessible `COLOURS` palette instead of force-replacing it.
4. **Teaching structure:** add just-in-time assumptions, concise scope roadmaps for long derivations, small outcome checkpoints and archetype-specific instruction for simulation, measurement lab, engineering capstone, scientific agents and formal proof.
5. **Interactive candidates beyond early mechanics:** consider EM07 beam steering, AST08 transit geometry, Q04 Stern–Gerlach, T04 Ising, and FL04 dam break; choose at most two based on actual teaching gain, available verified data and a static equivalent. Mechanics 01/03 remain candidates, not the automatic winners.
6. **Evaluation:** distinguish a source-structure audit from a rendered screenshot review and from scientific validation. Pilot before/after figures at desktop and mobile, screen-reader/keyboard fallback, export/download behaviour, and the unchanged numbers and claims. Include an AG16 multimodal-input regression case if on-image attribution changes.

### 7. Primary repository evidence

- [`src/pbc/data/plotting.py`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/data/plotting.py) — `label_status`, `add_credit`, `COLOURS`, `check_figure`.
- [`tests/unit/test_data_plotting.py`](https://github.com/taspinar/physics-by-construction/blob/main/tests/unit/test_data_plotting.py) — explicit presentational and evidence checks.
- [`src/pbc/experiment.py`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/experiment.py) — deterministic PNG encoding, identical display/experiment artifact.
- [`site/_filters/lesson.lua`](https://github.com/taspinar/physics-by-construction/blob/main/site/_filters/lesson.lua) — HTML caption status with dataset/artifact metadata.
- [`src/pbc/authoring/design.py`](https://github.com/taspinar/physics-by-construction/blob/main/src/pbc/authoring/design.py) — site/figure colours, contrast rules.
- [`site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd`](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd).
- [`site/lessons/materials/05-stress-strain-measurements/index.qmd`](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/materials/05-stress-strain-measurements/index.qmd).
- [`site/lessons/agents-llm/16-multimodal-physics-reasoning/index.qmd`](https://github.com/taspinar/physics-by-construction/blob/main/site/lessons/agents-llm/16-multimodal-physics-reasoning/index.qmd).
- [`docs/authoring.md`](https://github.com/taspinar/physics-by-construction/blob/main/docs/authoring.md), [`docs/PROJECT_REQUIREMENTS.md`](https://github.com/taspinar/physics-by-construction/blob/main/docs/PROJECT_REQUIREMENTS.md), [`docs/roadmap.md`](https://github.com/taspinar/physics-by-construction/blob/main/docs/roadmap.md).
