# The Part B products: the instrument contract and the Autonomous Physics Lab slice

The Part B capstones deliver learner-run local applications (ADR 022
decision 5, requirements decision 42). This page describes what F138
delivered for them: the instrument contract, the simulator vertical slice of
the Autonomous Physics Lab, the starter and its pin, and the decision record
of the slice, which settles the unresolved questions 19 (optional dependency
packaging) and 21 (the frontend of the local products). The learner's own
material is `products/physics-lab/README.md`.

## The instrument contract (`pbc.instruments`)

A caller never holds a device driver. It holds an `Instrument`, which wraps
the driver of one execution mode and enforces the safety envelope before an
operation reaches the device (invariant I34):

- **Ranges.** Every quantity has its permitted range with its unit
  (`Limit`); the excitation's amplitude and frequency and the acquisition's
  sample rate and length are checked before the driver is called. A value
  that is not a finite number in range is refused.
- **Interlocks.** A condition that must hold before the output goes on
  (`Interlock`); the product's is `circuit-confirmed`, the learner's
  confirmation that the prepared circuit is connected. The product never
  rewires a circuit.
- **Timeouts.** Each driver call runs under the envelope's timeout; a call
  that does not return in time is refused, the output is switched off, and
  the instrument halts.
- **Stop.** `request_stop` switches the output off at once, from any
  thread, also during an acquisition, whose data are then not handed out;
  every later operation is refused.
- **State.** `snapshot` gives the mode, the device or model, the output,
  the halt reason, the operation counts, and the envelope.

The limits are code, not prompt text: they hold whatever the caller is, the
scripted route, the agent's tools, or the local interface
(`tests/unit/test_instruments.py`, with a fake live driver that records
every call it receives).

**Execution modes.** Every run record (`InstrumentRun`) names its mode, the
device or model with its calibration, the configuration, the units, the
processing, and the timestamps:

- *simulated*: `pbc.instruments.simulated`, a bench over the series RLC
  circuit of `pbc.electromagnetism.circuits` (EM5's L and C, R = 100 ohm),
  integrated in time from rest through a settling time, with seeded noise;
- *recorded*: `pbc.instruments.recorded`, a declared sample replayed
  capture by capture. It answers only the settings it holds and refuses any
  other, and its run record is never a new experiment, which the record
  refuses to state. EM8's RLC data has no granted dataset gate, so the
  slice uses a synthetic sample written from the simulated bench and
  declared `simulated`; it is regenerated from its seed and never committed;
- *live*: no adapter yet. F140 decides on hardware; its driver will be
  imported only with the product's optional group.

The physical model (`pbc.electromagnetism`), the instrument layer
(`pbc.instruments`), and the orchestration (`pbc.products.physics_lab`) are
separate packages.

## The slice: one protocol end to end (`pbc.products.physics_lab`)

The frequency-response protocol measures the gain and the phase of
V_C / V_S at each frequency from the phasors of whole periods after the
transient, estimates f0 where the phase crosses -90 degrees and Q from the
two bracketing points through the second-order response, and has the
evaluator recompute every point from the exported raw samples and compare
f0 and Q with the closed form of the circuit (1 % and 3 %), which the route
never sees.

- **The scripted baseline** reaches the protocol without a model: a
  log-spaced sweep and a refinement between the two points that bracket
  -90 degrees.
- **The bounded agent** runs in the harness of ADR 004 with one allowlisted
  operation, `measure(frequency_hz, amplitude_v)`, bounded by the envelope
  and validated twice (by the harness and by the instrument), with a budget
  of measurements; it receives the gain and the phase and nothing else. Its
  route is verified by replay from `products/physics-lab/fixtures/`: every
  recorded call is executed again on a fresh bench with the same seed, and
  a mismatch fails. Its own answer is kept as an unverified candidate
  report.
- **Evidence.** Each run writes a ledger of `pbc.evidence`: the task with
  the execution mode in its environment, the attempt with its raw-data
  artifact, the evaluator's evaluation, the agent's report apart, and the
  claim with its derived status.
- **Export.** `raw.csv`, `points.csv`, `report.md` with
  `frequency-response.svg`, `run.json`, and `evidence.json`.
- **Command.** `uv run --locked --extra physics-lab python -m
  pbc.products.physics_lab run --input
  products/physics-lab/examples/frequency-response.toml --out <directory>`.

The committed replay traces (ADR 022 decision 8) live only at
`products/physics-lab/fixtures/`, the product's one fixture location, which
the committed-artifact check exempts and nothing more
(`tests/support/lesson_checks.py`). They were written by
`pbc.products.physics_lab.agent.ScriptedClient`, a deterministic policy that
is not a model, and are marked `"placeholder": true`; a learner may record a
live trace with their own key.

## The starter and its pin

`products/physics-lab/starter/` is the project a learner copies: it imports
only verified components of `pbc`, has places marked `YOUR WORK`, and its
tests replay `fixtures/starter-agent.json`. Its pin is the `rev` of `pbc`
in its `pyproject.toml`, installed by the repository's Git address.

`python -m pbc.products.starters`, the check `starters` of
`scripts/verify.conf`, checks every starter twice (ADR 022 decision 5):
against the current tree, and at its pin, by taking the pinned commit's
`src/` from the repository's own history with `git archive` (no fetch; the
CI job of the group `code` checks out the full history), confirming that
`pbc` is imported from it, and running the starter's tests. A pin must be
the full hash of a commit in the history of `HEAD`. A `pending` pin is
skipped, and the output names the skip. The pinned commit runs with the
dependencies of the current environment, and only `src/` comes from the
pin: the starter's tests and its trace in `products/physics-lab/fixtures/`
come from the current tree.

**Bootstrap and the follow-up pin bump.** This starter is new, so its pin is
`pending` and its at-pin check is skipped. The first pin bump, a small
change after F138 merged, sets the pin to the merged commit of `main` and
ends the skip; a pin never returns to `pending`.

## Decision record: the simulator vertical slice (F138, 2026-11-04)

**Go.** The slice proves the contract on one protocol: the scripted
baseline and the replayed agent reach the same protocol through the same
guarded instrument, the evaluator's check recovers f0 within 0.05 % and Q
within 0.1 % of the closed form on the reference input, by both routes, the same seed gives
byte-identical exports, the recorded mode replays a declared sample and is
never a new experiment, and the safety envelope, the timeout, and the stop
hold with a fake driver that records every call. Later product features
build on it.

**Question 19, optional dependency packaging: one optional group per
product in `pyproject.toml`, locked in `uv.lock`.** The product's group is
`physics-lab`; it holds what the product's optional routes need beyond the
default environment, today the provider SDK of a live agent run, and F140
adds the driver of its device there. The simulated and recorded routes and
the local interface need nothing beyond the default environment. The group
is pinned by the lock like every dependency, installed only by a learner
(`--extra physics-lab`), and never by the site build or CI: no command of
the workflow, its runner preparation, the scripts, or the checks installs
an optional group (`tests/unit/test_products_boundary.py`). Evidence: the
existing `openai` group of the agent lessons works the same way; an
extra adds no new tool, and `uv run --locked` without `--extra` leaves it
out. Rejected: a separate requirements file per product (a second lock
outside `uv.lock`) and dependency groups (not part of the package's
metadata, so a starter that installs `pbc` by its Git address could not ask
for them, while it can ask for `pbc[physics-lab]`, as the Physics Lab
starter's extra `live` does).

**Question 21, the frontend of the local products: one server-rendered
page from the standard library's `http.server`, bound to the loopback
interface.** No JavaScript, no framework, no build step, no new
dependency: the page shows the configuration, the progress (it reloads
itself while a run is going), the results with the report's figure, the
failures with what to do, a stop button, and the exported files.
`interface.App.handle` is tested without a socket, so no check starts a
server; `serve` refuses any address that is not loopback. Loopback alone does not
stop another page in the learner's browser from posting to the interface
(cross-site request forgery) or a foreign domain resolved to 127.0.0.1 from
reading it (DNS rebinding), and the interlock `circuit-confirmed` must be
the learner's own confirmation: so every request must name the interface's
loopback address and port in its Host header, and every POST must come from
the interface's own origin (Origin, or else Referer) and carry the random
token of the process that the page embeds in its forms; anything else is
refused and changes nothing (`tests/unit/test_physics_lab.py`). Evidence: the
interface needs nothing a learner must install, works offline, and is
about 500 lines. Rejected for now: a frontend framework or bundler (a
non-goal), and a notebook (the requirements ask for an application). The
design follows the frontend-design skill at its pinned revision: one bold
element, the execution-mode band, whose colour and sentence say whether
the result is a simulation or recorded data.

**Cost.** No model call, no network, no instrument, and no new package in
the default environment; the optional group adds no package beyond the
existing provider SDK. A reference run takes about 1 to 2 s on the
maintainer's machine (19 time-domain integrations), the replayed agent run
under 1 s; the new tests take about 25 s together (the starter checks'
temporary repositories most of it), and the check `starters` about 4 s.
About 2,600 lines of code (the instrument contract, the product, the
starter check), 1,000 of tests, and the learner material.

**Limits.** The slice is one protocol; the transient and nonlinear
protocols, campaigns, invalid-measurement detection, and the capstone page
are F145's. The traces are placeholders of a scripted policy, not of a
model, so the slice shows the harness, the allowlist, and the replay, not a
model's behaviour. The simulated bench has ideal channels; the recorded
sample is synthetic, not measured; nothing here shows that a physical
circuit behaves so (F140). The at-pin check runs the pinned source with the
current environment's dependencies, so a pin bump that changes a dependency
is checked by the learner's own installation of the pinned lock. It also
runs the current tree's starter tests and trace against the pinned `src/`,
not the starter as it was at the pin: after a pin bump, a change to the
starter or its trace is tested against the older `pbc`, which can fail
spuriously or hide a difference from what a learner who copies the starter
at the pin receives. The starter cannot be installed outside the repository until its first pin
bump. The run takes its timestamps from the wall clock; only the results
are reproducible.

**The simplest viable implementation** is the one delivered: plain Python
over the existing harness, replay, evidence ledger, and RLC model, with
the standard library for the interface; no external measurement framework
(Bluesky and QCoDeS are F140's comparison).
