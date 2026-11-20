# Plan: F142, Path 1: SA3 "Connecting simulators and instruments" and SA4 "Measurement quality and multimodal observations" (Issue #570)

Source: `docs/roadmap.md`, F142; ADR 022 decision 5 (the instrument
contract, invariant I34); ADR 023 decision 2; F97's acceptance criteria
(the rules of generated clips); the session instructions on Issue #570.
Written by the implementer at the start of the work (the Issue expects a
detailed plan and none existed).

## Risk

**Level 3 by trigger: an existing test assertion changes.**
`tests/unit/test_products_boundary.py::test_no_check_script_workflow_or_page_starts_a_product`
asserts that no page names `pbc.instruments`. The Issue asks for SA3 "built
on `pbc.instruments` as F138 delivered it", so the two pages import the
contract and its simulated and recorded adapters. The assertion is narrowed
to what its docstring states (no page starts a product), and replaced for
`pbc.instruments` by a stronger, specific one: a page may name only the
contract, `pbc.instruments.simulated`, `pbc.instruments.recorded`,
`pbc.instruments.conformance`, and `pbc.instruments.channels`, never the
live mode, and every experiment module a page runs that imports
`pbc.instruments` is scanned for the forbidden imports (driver, network,
process, provider) like the package itself. The alternative, reaching the
contract only through the experiment module so that the page source never
names it, was rejected: it would satisfy the regular expression while
defeating its purpose. Approval request `.agents/approvals/570.md`.

Other paths: two new lessons, new modules under `src/pbc/`, new unit tests,
a new widget `site/widgets/clip-viewer.js` with its style in
`site/assets/site.css` and its built-site tests in `tests/e2e/` (check
identity and a shared input: the targeted run will report that CI runs
everything), `docs/authoring.md` ("Widgets"), `docs/project-map.md`,
`docs/architecture.md` (the module table; sensitive). No ADR, CI workflow,
check of `scripts/verify.conf`, dependency, or budget changes. The payload
budget is not raised.

## What is delivered

| Part | Where |
|---|---|
| SA3, a new lesson | `site/lessons/electromagnetism/10-simulators-and-instruments/index.qmd`, id `simulators-and-instruments`, slot SA3, course and strand electromagnetism, format 2, difficulty 2 |
| The contract tests every adapter passes | `src/pbc/instruments/conformance.py` (`check_driver`, findings in a fixed form); `tests/unit/test_instrument_conformance.py` runs them on the simulated, recorded, and channel adapters and on the fake live driver that stands in for the optional hardware adapter |
| A call log adapter for the page | `pbc.instruments.conformance.CallLog`: wraps any driver and records what reaches it, so the page can show that a refused operation reached nothing |
| SA3's experiment | `src/pbc/electromagnetism/experiments/simulators_and_instruments.py`; test `tests/unit/test_simulators_and_instruments_experiment.py` |
| SA4, a new lesson | `site/lessons/electromagnetism/11-measurement-quality/index.qmd`, id `measurement-quality`, slot SA4, course and strand electromagnetism, format 2, difficulty 2 |
| A realistic acquisition chain | `src/pbc/instruments/channels.py`: `ChannelChain` (gain, offset, full scale, bits, dropped samples) and `ImperfectChannels`, a driver that wraps another and passes the same contract tests |
| Measurement-quality analysis | `src/pbc/electromagnetism/measurement.py`: the least-squares sine fit with a mask of valid samples and its standard errors, the quality report (clipped and missing fractions, the Nyquist margin, the calibration), two-point calibration, the alias frequency |
| Typed interpretations | `src/pbc/electromagnetism/observations.py`: `Interpretation` with the status `read`, `inferred`, or `uncertain`, its basis, and what would settle it; `Check` against a simulated measurement (`confirmed`, `contradicted`, `not checked`) |
| The generated clips | `src/pbc/electromagnetism/needle.py`: the compass needle in a uniform field (the equation of motion, its simulation), the frames rendered from the simulation, the tracking of the needle from the pixels, the frequency and the field inferred from the track, the alias of a frame rate |
| SA4's experiment | `src/pbc/electromagnetism/experiments/measurement_quality.py`; test `tests/unit/test_measurement_quality_experiment.py` |
| The clip viewer | `site/widgets/clip-viewer.js`, loaded on demand; tests `tests/e2e/test_clip_viewer.py` |
| Unit tests of the modules | `tests/unit/test_instrument_channels.py`, `tests/unit/test_measurement.py`, `tests/unit/test_needle.py`, `tests/unit/test_observations.py` |
| Documents | `docs/authoring.md` ("Widgets": the clip viewer), `docs/project-map.md`, `docs/architecture.md` (the module table) |

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501, diagram-design@550fd66

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| The layers of the interface: caller, `Instrument` (envelope, interlocks, timeout, stop, snapshot, run record), the `Driver` protocol, the three adapters, the live one dashed and optional | Conceptual diagram (`pbc.authoring.diagrams`) | `fig-instrument-layers`, SA3 | Shows no result; the adapter names are the modes of `MODES` (a test compares) | `fig-alt` with the insight; the prose lists the layers |
| The response measured through the instrument on the simulated and recorded adapters against the closed form | Scientific figure, `simulated` | `fig-response-through-the-contract`, SA3 (preview) | `SeriesRLC.capacitor_phasor`; the unit test compares within the stated tolerance | alt text; the result table |
| The measurement set-up of SA4's still-image exercise: generator, series R, L, C, the two probes | Conceptual diagram | `fig-bench-setup`, SA4 | Shows no result; the reading is checked against the simulated bench | alt text; the exercise states the circuit in words |
| One capture through an imperfect chain as the converter wrote it: clipped, quantised, with gaps, over the ideal chain's record | Scientific figure, `simulated` | `fig-imperfect-capture`, SA4 (the first observation, before any processing) | the chain's steps (unit tests of `channels`); the quality flags (experiment test) | alt text; the quality table |
| The spread of the fitted amplitude against the record length, with the reference slope minus one half | Scientific figure, `simulated`, log-log | `fig-noise-and-length`, SA4 | the standard error of the fit; the slope is a reference line, not a fit | alt text; the table |
| The two clips frame by frame (contact sheet), the static figure of the clip viewer | Scientific figure, `simulated` (frames rendered from the simulation, labelled generated) | `fig-needle-frames`, SA4 | the frames are drawn from the simulated angles; tracking test | alt text; the track table |
| The tracked angle of both clips on the simulated motion | Scientific figure, `simulated` | `fig-needle-tracks`, SA4 (preview) | tracking against the simulated angle (test) | alt text; the table |
| The clip viewer | Widget, on demand | element `#needle-clips`, SA4 | shows the frames of the file unchanged (e2e test) | the static contact sheet and the tables; nothing animates |

No animation that plays by itself: the viewer steps frame by frame under the
reader's control, so the reduced-motion rule holds by construction.

## SA3: the learner and the subject

- **Learner.** Has done EM5 (`rlc-circuits-and-resonance`: the series
  circuit, its resonance, the capacitor's phasor) and SA1
  (`experiment-specification`: permitted actions, units, stopping). Has
  not seen `pbc.instruments`. Difficulty 2.
- **Central question.** One program should measure the resonance of the
  circuit whether the samples come from a model, from a recording, or from
  a real oscilloscope. What must the layer between the program and the
  device guarantee, so that nothing the program asks can reach the device
  outside its limits, and nothing a recording returns is taken for a new
  measurement?
- **Counterintuitive points.** (a) The limits are enforced below the caller,
  not in the caller: a tool whose own bounds allow 230 V is accepted by the
  allowlist and still refused by the instrument, and the device sees
  nothing. (b) A recorded adapter refuses a setting it did not record
  rather than interpolate: an interpolated answer would be a new
  experiment the recording never made. (c) The same contract tests run on
  every adapter; a live adapter that passes them is still not demonstrated
  until it ran on a device.
- **Target misconceptions.** "A simulator is a fake instrument, so it needs
  no safety checks." "A replayed run is as good as a new one." "Interface
  code is plumbing, not physics."
- **Archetype.** Model or simulation (the measurement of a model through an
  interface), with the evidence kind stated at once: every run on the page
  is a simulated or a recorded run made by the build; no live hardware.
- **Journey.** The measurement as a person does it (set the generator, read
  the scope, write down the ratio); the six things a program needs from an
  instrument (configuration, excitation, acquisition, units, validation,
  snapshots); the layers diagram; the code of the contract; the response
  through the simulated adapter against the closed form; the same
  procedure on the recorded adapter, and the prediction moment (a setting
  between two recorded ones: interpolate, nearest, or refuse?); refusals
  with the call log; the stop; the contract tests on every adapter; the
  optional hardware adapter (what it must implement, why it is optional, not
  demonstrated until F140's go); limits; self-check.
- **Deliberate moments.** (1) The prediction before the recorded adapter is
  asked for an unrecorded frequency. (2) The self-check: a live adapter
  passes every contract test; is live hardware support demonstrated?
- **Code the learner reads.** `Driver` (exact, the protocol is the
  interface), `Limit.check` (exact: the rule that refuses), `Instrument.excite`
  (exact: validation, interlocks, then the driver, then the halt check),
  `measure_response` of the experiment (exact: the procedure that does not
  know which adapter it holds), `RecordedBench.capture` (selection: the
  refusal rather than interpolation), `check_driver` (selection: the list of
  checks). Drawing code: Source links.
- **Exercises.** (1) An adapter that forgets to switch its output off
  (`ForgetfulBench` of the experiment): which contract test fails, and why
  it matters on a device. (2) The recorded sample at three frequencies, the
  procedure asked for a fourth: what happens and what to do instead. (3) A
  caller asks for 5 V with a tool whose bounds allow 10 V: what reaches the
  driver, and what the snapshot says.

## SA4: the learner and the subject

- **Learner.** Has done SA3 (the contract, the simulated bench, the
  capture with its units). Difficulty 2.
- **Central question.** A number from an instrument passes through a probe,
  an amplifier, a converter, and a clock; a picture passes through a camera.
  How does one tell a property of the circuit, or of the needle, from a
  property of the measurement, and when is an interpretation of a picture
  a measurement at all?
- **Counterintuitive points.** (a) A clipped record still determines the
  amplitude: the samples between the rails carry it, and a fit that leaves
  the clipped ones out recovers it, while the peak reading cannot. (b)
  Missing samples cost precision, not truth, when the analysis knows they
  are missing; filling them with zeros biases the result. (c) A clip at five
  frames per second shows a smooth, slow swing of a needle that swings four
  times a second, and the tracking of every frame is correct: the error is
  in the interpretation, not in the frames.
- **Archetype.** Measured-data investigation in its lineage (raw capture,
  calibration, quality, processing, model, comparison, warranted
  conclusion), on simulated and recorded measurements, with the evidence
  kind stated at once: every capture and every clip is generated by the
  build from a model, labelled simulated or generated; no measurement of a
  real circuit or needle is shown.
- **Journey.** The first observation (one raw capture through an imperfect
  chain, as the converter gives it); calibration against a known reference;
  sampling and the alias; noise and the length of the record; clipping;
  missing data; the quality report as a gate before a number is used; the
  still image of the set-up (affordances and counterfactuals, typed, then
  checked against the simulated bench); the clips (tracking, the field
  inferred, the frame rate's limit, the interpretation of the slow clip
  typed as uncertain); the conclusion; limits; self-check.
- **Deliberate moments.** (1) Before the slow clip's track is compared with
  the simulation: what field does a swing of about one per second imply,
  and should it be trusted? (2) The self-check: the fit of a clipped
  record agrees with the model; was the clipping harmless?
- **Code the learner reads.** `ChannelChain.record` (exact: gain, offset,
  rails, quantisation, gaps, in order), `fit_sine` (exact: the least squares
  over the valid samples only), `quality` (selection: the flags), `alias`
  (exact), `Interpretation` (exact: the type is the concept), `track_angle`
  (exact: the angle from the pixels), `field_from_frequency` (exact).
  Drawing and frame-rendering code: Source links, read first.
- **Exercises.** (1) The still-image exercise of acceptance criterion 4: the
  learner reads the set-up diagram, states what it affords (what can be
  measured, what cannot), and the counterfactual "what changes if the
  second probe is moved from the capacitor to the resistor", with the
  status of each statement; the solution checks each against the simulated
  bench with the probe moved. (2) A capture with 30 % of its samples
  missing: fit with the mask and with zeros. (3) The frame rate needed to
  see the needle's swing without alias, and the field read at that rate.

## The generated clips (F97's rules)

- Generated by the build from the simulation of `pbc.electromagnetism.needle`,
  labelled "generated" on the page and in the file; no clip of a person,
  no camera, no upload, no model call.
- Two clips of one needle: 30 frames per second for two seconds (60
  frames) and 5 frames per second for four seconds (20 frames); 160 by 120
  pixels, greyscale PNG frames, no pixel noise (it would not compress and
  the point is the frame rate). The page's payload is counted with the
  frames: the on-demand file must stay below 0.3 MB (a unit test) and the
  page within the 3 MB budget and 5 MB with the clips (the built-site
  checks); measured values under "Discoveries".
- Loaded only after the reader presses the button of `#needle-clips`
  (`data-ondemand`, `data-loads-ondemand`), from the site's own origin, by
  `site/widgets/clip-viewer.js`, which shows the frames of the file as they
  are, one at a time, with a slider and buttons; it never plays them.
- The tracking (`track_angle`) is deterministic and compared with the
  simulated angle by a unit test (acceptance criterion 3).

## Steps

1. This plan and the handoff note.
2. `pbc.instruments.conformance`, `pbc.instruments.channels`, and their tests.
3. SA3's experiment, page, and experiment test.
4. `pbc.electromagnetism.measurement`, `observations`, `needle`, tests.
5. SA4's experiment, page, and experiment test.
6. The clip viewer, its style, its e2e tests.
7. The boundary test change, the documents, the approval request.
8. The summary, the completion record; verification last
   (`./scripts/verify.sh --targeted`, which will report a full run; the
   full run is not made in the session, by the Issue's instructions).

## Out of scope

Live hardware results; the live adapter (F140); the video extension F97; a
new dataset; changes to AI6's or D10's lessons (linked as depth only).

## Discoveries during the work

- **The products boundary test forbade any page to name `pbc.instruments`.**
  Recorded above under "Risk"; the change is the Level 3 trigger.
- **A response probe on the resistor needs no change of F138's bench.** The
  capture of `SimulatedRLCBench` now calls a hook `_probe(charge, current)`,
  which returns the capacitor voltage as before (the bench's samples are
  unchanged, `tests/unit/test_instruments.py` passes untouched);
  `ResistorProbeBench` overrides it. Its identity adds `probe`; the bench's
  own identity is unchanged, so the product's fixtures are not affected.
- **The page needs no new style.** The clip viewer uses the widget classes of
  `site/assets/site.css` as they are (`widget-controls`, `widget-drawing`,
  `widget-panel`, `widget-choices`, `widget-slider`, `widget-readout`); no
  shared asset changes.
- **A fit at a known frequency does not see an alias.** The samples of a
  sinusoid and of its alias are the same, so the sampling example reads the
  frequency from the record (`dominant_frequency`), which is where the alias
  misleads; the page says so.
- **The small-swing formula reads the field a few parts in a thousand low**
  at the needle's start of fifteen degrees; the page names the cause.
- **Measured sizes.** The clip file is 87 KB (80 greyscale frames of 160 by
  120 pixels); the initial payload of SA4 is 2.36 MB and of SA3 1.64 MB
  (single-page renders, `test_every_page_loads_within_the_payload_budget`
  on them), both under the 3 MB budget; with the clips SA4 can load 2.45 MB,
  under 5 MB. The budget is unchanged.
- **The built-site checks of one page pass on both pages** (another origin
  and cookies, readable without JavaScript, widths, the WCAG scan, the
  payload, the on-demand budget and loading after an action, the widget
  sources and storage), run on single-page renders in a scratch copy; the
  clip viewer's own tests pass there too.
- **Two planned exercises became worked examples** (recorded after review
  01, MIN2). SA3's exercise (3), the tool with wide bounds, is the last of
  the five requests of the worked example "What the envelope stops", with a
  tool whose bounds allow a thousand volts instead of 10 V; SA4's exercise
  (2), the lost samples, is the worked example "Lost samples" (about a third
  of the samples lost in bursts instead of 30 %). The reason: each case is
  the evidence of a claim span of its page (`refusal-table`,
  `missing-table`), asserted by the page's experiment test, and on SA4 the
  lost samples are one of the three imperfections of the first capture,
  which the worked examples read one by one; as an exercise its result
  would have stood in a solution without a claim. Each page keeps a
  self-check and two exercises with solutions (SA3: the forgetful adapter,
  the recording asked for more; SA4: reading the set-up, the frame rate for
  the needle), so the lesson rule is met.

## Where the teaching skill changed the learning experience

- SA3 opens with the person at the bench and derives the six parts of the
  interface from what they do without thinking, before any code; the layers
  diagram then answers one question (where can a limit be enforced so that
  no caller gets past it?).
- SA3's prediction moment is placed where the counterintuitive point meets
  the evidence: the recorded adapter asked for a frequency between two
  recorded ones refuses instead of interpolating, and the page says why an
  interpolated value would be a new experiment in disguise.
- SA3's exercise on the forgetful adapter turns the contract tests into the
  point of the limits section: the stop check passes while the circuit is
  still driven, which only a check of the signal finds.
- SA4 follows the measured-data lineage with the first observation before
  the assumptions: the raw record as the converter wrote it, with one
  sentence on what is visible without a model; the remedies then follow the
  chain backwards, calibration first.
- SA4's two deliberate moments: the prediction of the noise scatter for a
  record thirty-two times longer, and the field implied by the slow clip,
  asked before the figure that shows the alias; the self-check is the
  interpretation moment (a clipped record that agrees with the model).
- Code on the pages: the contract's `Driver`, `Limit`, and the lines of
  `Instrument.excite` (the rule and the order: validate, interlock, call,
  check the halt); the measurement procedure that does not know its adapter;
  the recorded adapter's refusal; `fit_sine`, `valid_samples`, the flags of
  `Quality`, `alias`, `Interpretation`, `track_angle`, each at the step it
  explains. Every drawing and frame-rendering function is a Source link,
  read first: `draw_imperfect_capture` drew a fit in its first version,
  removed so that no processed result appears before the step that produces
  it, and none of them computes anything a conclusion rests on.
