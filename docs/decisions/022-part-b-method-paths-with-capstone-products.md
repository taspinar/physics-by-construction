# ADR 022: Part B as four method paths with core and extension slots, product capstones, and learner-run local products behind an instrument contract and an evidence contract

## Status

Proposed with the planning of the change cycle
`part-b-scientific-products-and-research`
(`docs/changes/part-b-scientific-products-and-research.md`,
human-supplied, 2026-11-01; requirements decision 42 and the amendments of
decisions 23, 25, 26, 28, and 31, re-approved on 2026-11-01); accepted
when that planning is approved. Delivered by F136 (the curriculum
migration), F137 (the evidence contract), F138 (the instrument contract
and the simulator vertical slice), and the product features F145, F148,
F151, and F155 of `docs/roadmap.md`, "Phase 9".

Amends two decisions of
[ADR 013](013-eight-courses-and-the-reference-curriculum.md), whose status
names this record; the other decisions of ADR 013 stand:

- **ADR 013 decision 3** (the reference curriculum as declared data): a
  slot gains the optional key `extension` and the kind `product capstone`
  (decisions 2 and 3 below); the rule that the curriculum file holds
  nothing a lesson's front matter holds is unchanged.
- **ADR 013 decision 5** (published facts from front matter, planned
  structure from the curriculum file): the counts of the reference
  curriculum are the counts of its core slots; extension slots are shown
  and counted apart (decision 2 below).

Amends one decision of
[ADR 021](021-quieter-site-two-layer-atlas-and-raster-interface-artwork.md),
whose status names this record; its other decisions, and the rest of
decision 3, stand:

- **ADR 021 decision 3** (the two-layer atlas), in the one sentence "The
  curriculum file gains no field": a slot of the curriculum file gains the
  optional key `extension` and the kind `product capstone` (decisions 2
  and 3 below), and nothing else. The curriculum file still gains no
  description field and holds nothing a lesson's front matter holds, and
  no title, outcome, prerequisite, publication state, or count is written
  in the map manifest. The same rule, recorded in ADR 013's status for
  ADR 018's extension and repeated by ADR 021, is amended alike, and ADR
  013's status says so.

Amends one condition of
[ADR 002](002-regenerate-artifacts-and-display-by-reference.md), whose
status names this record; its other decisions and conditions stand:

- **ADR 002, the replay-fixture decision, condition 2** (the fixture
  "lives at one declared fixture location inside the lesson directory",
  and the committed-artifact check exempts "that location and nothing
  else"): a Part B product, which has no lesson directory, gains one
  further declared fixture location, `products/<product>/fixtures/`, for
  the replay traces of its reference product and its starter (decision 8
  below). Conditions 1, 3, and 4 apply to those traces unchanged, and the
  committed-artifact check exempts that location as it exempts a lesson's
  (invariant I6 of `docs/architecture.md`).

Extends, without changing their decisions:
[ADR 004](004-agent-lessons-verified-by-replay.md) (an instrument
operation is an allowlisted tool of the harness, decision 5),
[ADR 007](007-real-datasets-as-declared-inputs.md) (a captured hardware
trace enters the repository only as a declared dataset, decision 5),
and [ADR 010](010-coding-agent-exercises-on-the-learners-machine.md) (the
Agentic Coding Template is a coding-agent workflow on the learner's
machine, decision 7). A product capstone is a capstone of the atlas of
ADR 021 decision 3 (decision 3 below), with the amendment above.

Date: 2026-11-01

## Context

Requirements decision 42 replaces the 33 Part B slots of decision 23 with
34 core slots: four method paths under their existing stable keys, with 30
taught slots and four capstones, each of which delivers a usable local
software product (the Autonomous Physics Lab, the System Discovery Lab,
the Scientific Agent Testbench, and the Scientific Research Workspace).
The reference curriculum becomes 116 core slots (81 Part A, 34 Part B, one
Lean). The B-codes of the change request (B1.1 to B4.C) are temporary
references, not labels; final labels are allocated after the inventory
(unresolved question 20), an old slot label never silently changes
meaning, and a retired label is never reused.

Twenty-two published lessons fill Part B slots at the base commit
`cd69524` (AI0, AI2 to AI4, AI6, AI7, D1 to D13, EV2, EV3, R1), and one
more Part B lesson has no slot (`equations-from-noisy-trajectories`).
Seventeen of the twenty-two meet, or after an extension will meet, an
outcome of the revised core. The other five stay accessible as optional
depth, but for two different reasons. D4 (gravity discovery) is one of the
three deliberate extensions the requirements name, with full video-based
inference (AI8) and materials discovery (R5). AI6, D1, D3, and D5 are not:
the change request maps their outcomes into the core (multimodal and
counterfactual interpretation to B1.4 and B3.2, a black-box force-law
exercise outside electronics to B2.1 and B2.3, the extension of a known
law to B2.6, unknown simulated worlds with withheld truth to B2.1 and
B3.2), and requirements decision 42 never lets a cross-link alone claim a
core outcome. Their published lessons are optional depth; their outcomes
are carried by acceptance criteria of the core features that absorb
them. The
inventory is in `docs/roadmap.md`, "State at the change cycle
`part-b-scientific-products-and-research`".

ADR 013 knows three kinds of slot (`lesson`, `measured-data lab`,
`applied capstone`), counts every slot of the file, and has no way to say
that a published lesson belongs to a path without being one of its core
slots: a lesson without a slot leaves every path view. The atlas of ADR
021 represents every capstone slot by exactly one concept and marks
capstones; the Part B capstones are to carry the same mark.

Until now nothing in the system ran outside a page build or a learner's
copy of a lesson's experiment: no long-running local application, no
instrument, no learner-owned project started from this repository. The
requirements now allow learner-run local products, an optional local
instrument for the first two capstones under safety rules enforced outside
the language model, three execution modes kept distinct in data and
claims, and one minimal evidence contract that the evaluator, not the
candidate, fills. They keep the site static, without accounts, secrets,
uploads, instrument connections, or runtime model calls, and keep every
verification obligation. Several of these choices are hard to reverse once
learners have started projects from a starter: where the products and
their starters live, what the instrument boundary is, and what an
evidence record contains.

## Decision

1. **New labels for the revised core; old labels keep their meaning or
   retire.** Every core slot of the revised Part B gets a new label from a
   prefix no slot has used: `SA1` to `SA8` and the capstone `SA9` for the
   path `reasoning`; `MD1` to `MD9` and the capstone `MD10` for
   `law-discovery`; `AE1` to `AE6` and the capstone `AE7` for
   `benchmarking`; `RR1` to `RR7` and the capstone `RR8` for
   `autonomous-research`. The four path keys stay; their display titles
   become those of requirements decision 42. An old Part B label survives
   only as an extension slot (decision 2) with its working title and
   meaning unchanged; every other old Part B label is retired, listed in
   the roadmap's slot mapping with its successor, and never reused. The
   labels are the planner's proposal under unresolved question 20; the
   owner approves them with the curriculum file in F136 (ADR 013 decision
   3: the human approves the file's content with the feature that changes
   it), and a different choice there changes the labels, never this rule.

2. **Extension slots.** A slot of a method path may carry `extension:
   true`. An extension slot is optional depth of its path: it is listed
   after the path's core slots, in its own position order, and shown on
   the path view and the atlas visibly marked as an optional extension;
   the lesson header names it as such instead of "number n of the m
   slots". It is never part of the reference curriculum's counts (116
   core slots: 81, 34, and 1); the curriculum test pins the core counts
   and the number of extension slots separately, and a page that counts a
   path's slots counts its core slots. A published lesson in an extension
   slot is counted among the published lessons and, where a page reports
   a path's progress, apart from the core. A course slot and the Lean slot
   are never extensions. At this cycle the extension slots are AI6, D1,
   D3, D4, and D5 (published) and AI8 and R5 (planned, filled only if the
   owner schedules F97 or F110). Only AI8, D4, and R5 are deliberate
   extensions of the requirements (video-based inference, gravity
   discovery, materials discovery), whose outcomes are optional. For AI6,
   D1, D3, and D5 only the published lesson is optional depth: each of
   their outcomes is an outcome of a core slot and is attached to an
   acceptance criterion of the core feature that teaches it (SA4 and AE2
   for AI6, MD1 for D1, MD6 for D3, MD1 and AE2 for D5; `docs/roadmap.md`,
   F142, F146, F147, and F149). A link to an extension lesson is depth
   beside that criterion, never the coverage itself.

3. **The kind `product capstone`.** A method path's capstone slot has the
   kind `product capstone`. It is filled, like every slot, by one lesson
   page, in the `agents-llm` strand, that teaches the product: the product
   brief, the scientific acceptance criteria, the outcomes of the path
   each product feature exercises, the reference workflow run on the
   interactive deterministic simulator through the verified display forms
   (the page's experiment), the run command of the product and the
   starter in the page's last section (ADR 016), the manual and the
   guided development routes, and the documented operating limits. The
   atlas, Home, and the path view treat `applied capstone` and `product
   capstone` alike wherever they mark or choose a capstone; every capstone
   slot of either kind is represented by exactly one concept of the map
   manifest (ADR 021). A product capstone is never homed in a course, and
   the three applied capstones of Part A are unchanged.

4. **The migration is front matter and data only.** F136 rewrites the
   Part B part of the curriculum file, sets `lesson.slot` of the seventeen
   lessons that move to a core slot, keeps the slot of the five extension
   lessons, and updates the concept-to-slot associations and the four
   sequence descriptions of the map manifest. No address, lesson
   identifier, strand, order, or course changes (ADR 013 decision 6 is the
   precedent). A filled core slot shows the lesson's own title and
   outcomes; the new outcome of the slot is claimed only when the feature
   that extends the lesson has delivered it, and the roadmap names that
   feature. An unfilled slot is planned, never linked or counted, as
   today.

5. **Products are learner-run local applications, built on `src/pbc`,
   with an instrument contract and three execution modes.**
   - *Layout.* The reference product's code is a package
     `pbc.products.<product>` in `src/pbc`, tested by pytest and
     imported by its capstone page; its learner material lives in
     `products/<product>/`: the product brief, the scientific acceptance
     criteria, the example inputs, the reference workflow, the assessment
     rubric, the manual route, the guided route, `fixtures/`, the
     product's one replay-fixture location (decision 8), and `starter/`,
     the version-pinned starter a learner copies into their own project. The
     starter contains only already-verified lower-level components and
     clearly marked places for the learner's work.
   - *The pin.* `pbc` is not published as a package, so the starter's pin
     is a revision of this repository: the full commit hash of a commit
     on `main` whose `verify` passed (optionally named by a tag), from
     which the starter installs `pbc` by its Git address. CI checks the
     starter twice: against the current tree, so that a change which
     breaks the interface the starter imports fails its pull request; and
     at its pin, by installing that commit from the repository's own
     history without an external fetch and running the starter's tests,
     so that what a learner installs is what was verified. A change that
     alters the starter's dependency surface (the `pbc` modules and names
     it imports) keeps the current-tree check passing and, in the same
     feature, records the pin bump as its follow-up: the pin moves, in a
     small change after the feature merged, to the merged commit; a pin
     never names an unmerged commit. Between the two changes the old pin
     stays valid, since its check still passes. *Bootstrap:* a new
     starter (the first, of F138, and the first of each later product)
     depends on code that reaches `main` only when its own feature
     merges, so it has no valid pin yet. Its pin is declared `pending`;
     the at-pin check then skips that starter, names the skip in its
     output, and the feature's completion record states it, while the
     current-tree check runs as always. The first pin bump after the
     feature merged sets the pin to the merged commit and ends the skip;
     a pin never returns to `pending`, and a skip is never recorded for a
     starter whose pin is set. The at-pin check needs the repository's
     history in the CI checkout, a workflow change that F138 makes with
     the check (Level 3 by its paths).
   - *Run.* A product runs on the learner's machine by one documented
     command; its thin local interface (unresolved question 21, settled
     in F138) binds to the loopback interface of the learner's own
     process, is never part of `site/`, and adds no JavaScript build
     toolchain or bundler; its extra dependencies are an optional group of
     `pyproject.toml` (unresolved question 19, settled in F138), never
     installed by the site build or CI.
   - *Instrument contract.* `pbc.instruments` defines one small interface
     for configuration with units and validated ranges, excitation,
     acquisition, validation, and instrument-state snapshots, with
     adapters for the three execution modes: *simulated* (a deterministic
     model of `src/pbc`, for example the RLC circuit of the
     electromagnetism course), *recorded* (a declared dataset sample under
     ADR 007, never presented as a new experiment), and *live* (an
     optional driver adapter, imported only when its optional group is
     installed). The safety envelope (permitted ranges, interlocks,
     timeouts, and stop behaviour) is enforced by the adapter layer before
     any operation reaches a device, whatever the caller; the physical
     models, the instrument adapters, and the agent orchestration are
     separate layers. A scientific agent reaches an instrument only
     through allowlisted, validated operations of the contract (ADR 004
     harness), never through a driver, a shell, or generated code; code an
     agent wrote enters a workflow only after independent validation in an
     isolated simulator workspace (ADR 010).
   - *Execution modes in data.* Every run record names its mode, device or
     model, calibration, configuration, timestamps, units, and processing.
     The site shows simulated results and, after the dataset gate,
     recorded measured data; a live result stays on the learner's machine,
     and a captured trace enters the repository only as a dataset sample
     with its card, rights, and feasibility decision (ADR 007). Live
     results vary within declared tolerances and uncertainty; no global
     reproducibility tolerance is introduced for them. Real hardware
     support is called demonstrated only after a physical pilot (F140).

6. **One minimal evidence contract, evaluator-owned.** `pbc.evidence`
   extends the protocol of `docs/discovery-protocol.md` and the replay of
   ADR 004 only where the products need it, after a pilot on one existing
   task (F137): a record of the task, hypothesis, assumptions, protocol
   version, dataset split, seeds, budgets, code and configuration
   identities, and environment; per-attempt status, failure diagnostics,
   artifact references, and links to prior attempts; evaluator-computed
   correctness and resource use, stored apart from anything the candidate
   reports; claim-to-run and claim-to-source links with an evidence status
   (completed, failed, inconclusive, not evaluated, independently checked)
   and a scope; and a frozen selected candidate, identified by digest,
   with a versioned final evaluation whose feedback never tunes that
   candidate (a change after it starts a new development and evaluation
   cycle). A digest establishes identity, not scientific truth. A hidden
   or final evaluation states its actual isolation assumptions; a test the
   agent can read is not private. Where a product result is shown on the
   site, it is typed by the claim types of the lesson model (I21), and the
   evidence status is shown beside it, never instead of it.

7. **Verification and the development workflow.** CI verifies the offline
   route of every product and starter deterministically within the
   existing contracts: pytest over the product packages and the starters
   with the committed replay traces of decision 8 (simulated inputs are
   regenerated from their seeds; recorded inputs are dataset samples under
   `data/samples/`, ADR 007), and each capstone page
   executing its simulator route within the page budget. Live hardware,
   paid or local models, and heavy live evaluations run outside
   `verify.conf`, are never required by the build or CI, and are evidenced
   separately in the feature's completion record. No check is weakened to
   accommodate them. The Agentic Coding Template (ACT) is a coding-agent
   workflow on the learner's machine under ADR 010: the products' guided
   route names a pinned, demonstrated ACT revision and only the commands a
   learner needs; no file of this repository's build or checks depends on
   ACT, and ACT work PBC would need is scoped as its own change in ACT,
   never assumed. The boundary test of I24 covers ACT as it covers every
   coding agent.

8. **Where the products' replay traces live, under ADR 002's
   conditions.** The bounded agent route of a reference product and of
   its starter is verified by replay (ADR 004) from traces committed at
   one declared fixture location per product,
   `products/<product>/fixtures/`, never in `src/pbc/`, in `starter/`
   outside it, or anywhere else; the starter's tests read their traces
   from it, and the starter's documented copy step names the traces a
   learner copies with it. A capstone page is a lesson and keeps its own
   fixture location of ADR 002 condition 2. The traces follow ADR 002's
   replay-fixture conditions: they contain only the recorded model
   messages and the tool results expected for the recorded tool calls,
   with no credential, header, or other provider request data (condition
   1); their recorded tool results are never displayed, exported as a
   product result, or written into a run record as evaluation, and every
   replay, in pytest or on a capstone page, re-executes the tool calls
   and compares the recomputed results with the recorded ones within the
   stated tolerance, a mismatch failing the test or the build (condition
   3); their recorded model messages are shown only with the "recorded"
   label of ADR 004 (condition 4). Nothing else is committed at that
   location: a simulated input is regenerated from its seed, and a
   recorded or captured measurement is a dataset sample under
   `data/samples/` with its card (ADR 007). The committed-artifact check
   exempts each product's fixture location as it exempts a lesson's, and
   nothing more (I6); F138 adds that exemption with the first product.

## Alternatives considered

**Keep the old labels where the meaning carries over (D7 for symbolic
regression) and number new slots on (AI9, D14).** Rejected: about half of
the reused lessons change their path, position, or outcome (AI4 moves to
the research path, AI0 becomes the bounded experiment agent, D2 widens to
competing models), so each label would need a judgement whether its
meaning changed, and the prefixes would stop naming the path (AI4 in the
research path). New per-path prefixes keep every old label's meaning by
construction at the cost of one front-matter line per moved lesson, which
F136 makes once.

**Use the B-codes as labels.** Rejected by the change request: they are
temporary references, and `B1.1` does not match the label form of the
curriculum file (`[A-Z]+[0-9]+`).

**Drop the slot of the lessons that leave the core.** Rejected: a lesson
without a slot disappears from every path view, so gravity discovery, the
black-box force law, and multimodal reasoning would be reachable only from
their course; the change request wants them visible as optional depth and
counted honestly, not hidden.

**Count extension slots in the reference curriculum.** Rejected: the
requirements fix the core at 116 and ask that legacy extras be counted
separately, not twice.

**Give each product its own repository.** Rejected by the owner's answer
of 2026-11-01 (decision 42, "Products"): the reference product and the
starter live here, so that CI verifies them against the same `src/pbc` the
lessons use and a starter pins a revision that was verified.

**A product as a notebook, or a web application with a JavaScript
frontend framework in this repository.** Rejected: the requirements ask for
applications, not notebooks with a product name, and the non-goals exclude
a frontend framework or bundler; the thin local interface is chosen with
evidence in F138 within those limits.

**Adopt an external measurement framework (Bluesky, QCoDeS) or research
framework as the contract.** Not decided here: the requirements make every
external repository guidance only; F140 compares a minimal adapter with
Bluesky and, where helpful, QCoDeS on one protocol, and a framework is
adopted only on that evidence, behind this contract.

**Enforce instrument limits in the agent's prompt or tool descriptions.**
Rejected by the requirements' security constraints: limits are enforced
outside the language model.

## Consequences

Positive:

- Every old label keeps its meaning or retires visibly; every published
  address, identifier, strand, and order survives; the migration is one
  reviewable change of data and front matter.
- The path views show the core route and the optional depth apart, and
  the counts on every page agree with the requirements' 116.
- One instrument contract serves the simulator, recorded data, and an
  optional device, so that every essential outcome is reachable without
  hardware and a device adds only an adapter; the safety boundary does not
  depend on model behaviour.
- The evidence contract makes a fabricated score, a changed artifact, or a
  tuned final test visible by construction, and is proven on an existing
  task before the products depend on it.

Negative, with mitigations:

- Seventeen published lessons change the label in their header, and the
  path positions of all Part B lessons change; F136 is a full run and a
  Level 3 change, and the roadmap lists every old label with its successor.
- A filled core slot can, for a while, carry a lesson that does not yet
  meet the slot's new outcome. The page shows the lesson's own title and
  outcomes, never the slot's new outcome, and the roadmap names the
  extending feature.
- Two more top-level concepts (`products/`, the product packages) and two
  new packages (`pbc.instruments`, `pbc.evidence`) enter the repository.
  They are extracted only as far as the products use them; no general
  scientific platform or service is built.
- The curriculum grows to about 127 lessons when complete (116 core slots,
  the five published extension lessons, the Lean lessons beyond the
  baseline, and the unslotted noise lesson), beyond the 110 lessons of the
  owner's capacity decision of 2026-10-24 (Issue #278). The roadmap makes
  the owner's next capacity decision a gate before a lesson feature takes
  the count past 110.
- A learner's live results differ from the published ones. The site never
  shows them as the lesson's results, and the products label every run
  with its execution mode.
