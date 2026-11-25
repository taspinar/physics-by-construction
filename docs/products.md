# The Part B products: the instrument contract and the Autonomous Physics Lab slice

The Part B capstones deliver learner-run local applications (ADR 022
decision 5, requirements decision 42). This page describes what F138
delivered for them: the instrument contract, the simulator vertical slice of
the Autonomous Physics Lab, the starter and its pin, and the decision record
of the slice, which settles the unresolved questions 19 (optional dependency
packaging) and 21 (the frontend of the local products), and the record of
F140's desk spike, a recommendation on the questions 17 (the device) and
18 (the budget), which the owner decided on #508 on 2026-11-13
(<https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-6865116429>): the
Analog Discovery 3 Pro Bundle (DigiKey NL 471-060) and a maximum budget
of EUR 1,000 ("The owner's decision" below), and the record of F140's
physical pilot of 2026-11-22: a go for the live adapter of the Analog
Discovery 3 within its operating limits (the last section). The learner's
own material is `products/physics-lab/README.md`.

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
- *live*: the Analog Discovery 3 through the vendor's WaveForms SDK,
  `pbc.instruments.analog_discovery` (F140's physical pilot, the last
  section of this page), under the live bench's envelope with its current
  bound. It is imported only by the command line's live mode, and its SDK
  is the learner's own installation, never a locked dependency. A recorded
  run may also replay a live export, the pilot's dataset `ad3-rlc-pilot`,
  under the envelope and the circuit it was recorded with.

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

**Bootstrap and the pin bumps.** A new starter's pin is `pending` and its
at-pin check is skipped; its first pin bump, a small change after its
feature merged, sets the pin to a merged commit of `main` and ends the
skip, and a pin never returns to `pending`. The physics-lab starter's first
pin bump came later than F138 planned, with Issue #610 (2026-11-23),
which set the pin to 84d1477bbfef063a0bec3ca1d92c94787a2c8fcf, the commit
of F140 on `main`.

**Keeping the pin current.** The pin is bumped in a small change after a
merged feature changed what the starter imports from `pbc` or the trace
its tests replay, never inside that feature, whose commit is not yet on
`main`: the change sets `rev` to the commit of that feature on `main` (CI
passed on it) and runs the `starters` check, whose at-pin half shows that the starter's
tests pass against that commit's `src/`. A feature that changes neither
leaves the pin where it is; the at-pin check keeps running against it, so
a later change of the starter that the pinned `pbc` cannot run fails its
pull request and asks for the bump.

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
default environment, today the provider SDKs of a live agent run (OpenAI and,
since #615, Claude), and F140
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
provider SDKs. A reference run takes about 1 to 2 s on the
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
bump (made by Issue #610, 2026-11-23). The run takes its timestamps from the wall clock; only the results
are reproducible.

**The simplest viable implementation** is the one delivered: plain Python
over the existing harness, replay, evidence ledger, and RLC model, with
the standard library for the interface; no external measurement framework
(Bluesky and QCoDeS are F140's comparison).

## Decision record: the instrument desk spike (F140, 2026-11-13)

**The owner's decision (#508, 2026-11-13; recorded here by Issue #543,
2026-11-15).** Questions 17 and 18 are answered on #508
(<https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-6865116429>):
the device is the Analog Discovery 3 Pro Bundle (DigiKey NL 471-060),
and the maximum budget is EUR 1,000 for the device and the first RC or
RLC breadboard set-up. The physical pilot of F140 starts only after the
owner confirms that the device is available; the current total price
including VAT, shipping, and the needed accessories is checked before
any purchase; the owner buys, the project buys nothing. The budget this
record proposed (EUR 500, or EUR 550 for the Pro Bundle, in "Question
18" and "Purchase options" below) is superseded history, kept as
written; the record below is otherwise the desk spike's, unchanged.

**Scope.** The first part of F140 (Issue #508): a desk spike from vendor
documentation and the F138 contract with its fake live driver
(`tests/unit/test_instruments.py`), no purchase, no device, no vendor
software downloaded or installed. It ends in a recommendation on the
unresolved questions 17 (the device) and 18 (the budget); the physical
pilot, the live adapter, and the comparison with Bluesky and QCoDeS start
only after the owner's decisions are recorded on the Issue. Every source
below was accessed on 2026-11-13; the euro prices [AD10, AD11] are the
owner's own price check of that day. Prices are indicative and dated: a
shop price is not a quote, VAT and shipping vary, and they change. The
record was updated the same day with the owner's conditions of use, that
price check, a corrected description of the AD3's power, the first
experimental phase, and the possible extensions (the subsections from
"Conditions of use" on). This exploration changes neither the
curriculum, nor the risk rules, nor the implementation scope of F140.

**What the protocol asks of a device.** The bench envelope
(`pbc.products.physics_lab.protocol.bench_envelope`): excitation 0.01 to
2 V amplitude, 100 Hz to 50 kHz; acquisition 1 kS/s to 5 MS/s, 16 to
16,384 samples, two channels (source and capacitor voltage); 10 s timeout
per call. The reference input (`products/physics-lab/examples/frequency-response.toml`)
sweeps 1 to 25 kHz at 1 V with 8 periods of 64 samples (513 samples, at
most 1.6 MS/s). The bench circuit (`pbc.instruments.simulated.BENCH_CIRCUIT`:
R = 100 ohm, L = 10 mH, C = 100 nF) has f0 = 5.03 kHz and Q = 3.16, so the
capacitor voltage reaches Q times the source amplitude at resonance: 3.2 V
at 1 V, 6.3 V at the envelope's 2 V; the source current at resonance is
V / R, 10 mA at 1 V and 20 mA at 2 V (more with a smaller R).

### Comparison

Candidates: the Digilent Analog Discovery 3 (AD3) and the Red Pitaya
STEMlab 125-14 (Gen 2, since the original board's end of life is the end
of Q4 2026 [RP1]). The ADALM2000 of Analog Devices was looked at as a
third (below) and not taken further.

| Item | Analog Discovery 3 | Red Pitaya STEMlab 125-14 Gen 2 |
|---|---|---|
| Link to the computer | USB-C, with a connector for an optional external 5 V supply [AD9] (the specifications [AD1] do not list it) | 1 Gbit Ethernet (a Linux computer on the board), USB-C for power and console [RP2] |
| Host OS and driver | Windows, macOS, Linux [AD2]; the vendor's WaveForms runtime must be installed on the host [AD3] | no driver on the host: SCPI over TCP; the vendor gives Windows and Linux instructions, macOS is not mentioned [RP3] |
| Python access | the WaveForms SDK, a C library (`dwf`) called from Python through `ctypes` [AD3, AD4]; community wrappers `pydwf` 1.1.19 (MIT, 2023-10-18) and `dwfpy` 1.2.0 (MIT, 2025-01-10) [AD5] | a socket client: the vendor's `redpitaya_scpi.py` opens a plain TCP socket to port 5000 [RP4]; Python 3.10+ [RP3]; on-board C++ and Python API [RP5] |
| Licence and maintenance | wrappers MIT; the licence of the WaveForms runtime could not be read (digilent.com refuses automated access) | the repository's `COPYING` is BSD for the directories it lists, which do not name `tools/scpi`; the client file carries only a copyright line [RP4]; last release `Release_2026.1` (2026-07-07), last push 2026-10-31 [RP4] |
| Inputs | 2 differential, 14 bit, 125 MS/s, ±2.5 V or ±25 V, selected in software; 1 MΩ ‖ 24 pF; 9 MHz at -3 dB; overvoltage protection ±50 V DC or ±30 V RMS; buffer up to 32,768 samples per channel [AD1] | 2, 14 bit, 125 MS/s, ±1 V (LV) or ±20 V (HV) by jumper; 1 MΩ / 10 pF; 60 MHz; absolute maximum ±6 V (LV) and ±30 V (HV) below 1 kHz, the full-scale range above it [RP2]; buffer 16,384 samples [RP6] |
| Outputs | 2, 14 bit, 125 MS/s, ±5 V, 0 Ω (not precisely controlled), 30 mA for distortion-free output, 40 mA before cutoff, short-circuit protected [AD1] | 2, 14 bit, 125 MS/s, ±1 V into 50 Ω, ±2 V into high impedance, short-circuit protected [RP2] |
| Against the protocol | every range covered; the capacitor channel needs the ±25 V range (3.36 mV resolution instead of 0.336 mV) [AD1] | every range covered with the HV jumpers; on LV the resonant capacitor voltage (3.2 V at 1 V) exceeds the absolute maximum above 1 kHz, so the jumper setting is a hazard the software cannot read (the gain command only "refers to jumper settings" [RP6]); the 50 Ω source adds to the circuit's R |
| Sample rate | 125 MHz system clock, adjustable 50 to 125 MHz [AD1] | 125 MS/s divided by an integer decimation, 1 to 65,536 [RP6] |
| Calibration | factory calibrated; specifications after 30 min warm-up at 25 °C [AD1]; a user calibration in WaveForms is not documented in what could be read | factory calibrated; calibration app, `calib` utility, or API; Gen 2 needs no 50 Ω terminators [RP2] |
| Bill of materials | AD3 with its USB-C cable and 2×15 flywire cable [AD6]; the Pro Bundle adds a BNC adapter, two oscilloscope probes, and grabber clips [AD6, AD12]; breadboard; R 100 Ω, L 10 mH, C 100 nF | starter kit: board, SD card with the OS, 5 V 5 A supply, Ethernet cable, 2 probes, 2 SMA-BNC adapters [RP7]; BNC-to-clip leads for the two outputs (not in the kit); breadboard; R, L, C |
| Cost, device | €407.09 base kit (410-415) and €439.31 Pro Bundle (471-060), including 21 % VAT, excluding shipping (DigiKey Netherlands, the owner's check) [AD10, AD11]; $379.00 and $409.00 (DigiKey US, excluding VAT) [AD6]; $249 academic (Digilent blog, via a search result, not read) [AD7] | £580.00 (Sundance, PRO Gen 2 starter kit) [RP7]; €649 at its 2025 pre-order (CNX Software, 2025-06-24) [RP8] |
| Failure: disconnect | the AD3 can run on an optional external 5 V supply [AD9], so unplugging the USB cable is not shown to remove all power or the outputs; the behaviour on a lost link and how the outputs are switched off must be checked with the power configuration actually chosen | the board keeps running on its own supply; what the generator does when the client goes away is not documented in what was read [RP3] |
| Failure: host program ends | `DwfParamOnClose`: 0 continue, 1 stop, 2 shutdown, set by the SDK [AD8]; the default could not be read | not documented in what was read; a malformed command can leave the client's read waiting indefinitely [RP3] |
| Security of local control | USB to one computer; nothing on a network | a network instrument: SCPI on port 5000 with no authentication described [RP3, RP4], a web interface, and SSH with the default user and password `root` [RP9] |

ADALM2000 (third, not taken further): 12 bit, 100 MS/s inputs of ±2.5 V
or ±25 V and ±5 V outputs at 150 MS/s, 64k samples per channel [M1],
Python through `libm2k` (LGPL-2.1, builds for Windows, macOS, and Linux,
v0.9.1 of 2026-08-12) [M2], about £187 to €201 excluding VAT at
distributors (search results, not read) [M3]. It meets the protocol, but
it is in the AD3's class with a lower resolution, and its documentation
does not state the output current a resonant circuit draws, so it does
not change the recommendation.

### Evidence per item

- **Operating systems and drivers.** AD3: WaveForms for Windows, macOS,
  and Linux (DigiKey's product page [AD2]; the vendor's download page
  lists Windows 10 and 11 including ARM64 [AD3]), installed by the
  learner outside `uv`; it cannot be pinned in `uv.lock`, so it is a
  manual step of the product. Red Pitaya: nothing on the host; the OS
  runs on the board from its SD card.
- **Python access.** AD3: the SDK library by `ctypes`, as Digilent's own
  examples do with `dwfconstants.py` [AD4], or `dwfpy`/`pydwf` in the
  optional group `physics-lab` (question 19). Red Pitaya: the standard
  library's `socket`, no package [RP4].
- **Acquisition and excitation limits.** Both cover the envelope (table).
  Two constraints apply to both: the sample rate comes from a divided
  clock, and the generator's frequency is quantised too, while
  `pbc.electromagnetism.circuits.steady_phasor` requires samples that
  span a whole number of periods to 1e-9. A live driver therefore either
  sets the excitation to a frequency the clock divides exactly and
  reports it, or the protocol reads the phasor with a fit that does not
  need whole periods. The F138 `Driver.set_output` returns nothing, so
  the frequency actually set has no place in the contract yet: a change
  of the contract for the pilot, not for this spike.
- **Calibration.** Both devices are factory calibrated (table). The
  evaluator's closed form needs the circuit's actual R, L, and C: a 10 mH
  inductor has a winding resistance that adds to R and lowers Q, and
  parts have tolerances of a few percent, so the pilot measures them
  (an LCR meter, or the device itself against a known resistor) and the
  run record states them. The documentation read says nothing on how
  often either device needs recalibration for this use.
- **Bill of materials and cost.** AD3: €407.09 (base kit) or €439.31
  (Pro Bundle) including VAT [AD10, AD11], plus the circuit; the base
  kit's flywires reach a breadboard directly, so the Pro Bundle's
  accessories are a convenience, not a need, for the first circuit (see
  "Purchase options"). Red Pitaya: £580.00 plus leads and the circuit.
  The circuit's material (breadboard, jumper wires, resistors,
  capacitors, inductors, and a few further parts) is budgeted at €45 to
  €80 including VAT: a budget estimate of the owner, not a checked,
  complete bill of materials.
- **Realistic duration.** The physics is fast: the transient's time
  constant 2L/R is 0.2 ms, so ten time constants settle in 2 ms, and the
  reference sweep's 19 acquisitions of 8 periods take about 0.1 s of
  signal. The time is in the round trips (USB or TCP) per configuration
  and capture, which neither vendor documents; at an assumed 0.1 to 0.5 s
  per point a sweep takes 2 to 10 s. For a learner the session is the
  installation (AD3) or the network set-up (Red Pitaya), the wiring of
  the circuit, the 30 min warm-up for the AD3's specified accuracy
  [AD1], and seconds per sweep. The pilot measures the round trips.
- **Failure handling, mapped onto the F138 contract.** The contract
  already halts the instrument on a timeout or a stop and makes
  `output_off` the driver's last call (`tests/unit/test_instruments.py`:
  `test_a_timeout_switches_the_output_off_and_halts_the_instrument`,
  `test_a_stop_request_from_another_thread_is_honoured_at_once`,
  `test_a_timed_out_excitation_that_returns_late_leaves_the_output_off`).
  What it cannot do is act when the host process dies or the link drops.
  AD3: it has a connector for an optional external 5 V supply [AD9], so
  a pulled USB cable is not a guaranteed emergency stop: what the device
  and its outputs do on a lost link, and how the outputs are switched
  off, must be checked with the power configuration actually chosen
  before anything relies on it. A live driver sets `DwfParamOnClose` to
  stop instead of relying on the default; a killed process and a pulled
  cable are the cases the pilot tests. Red Pitaya: the generator is on
  a computer of its own, so a lost client or a crashed host may leave the
  output on; the documentation read describes no watchdog, so a live
  driver would need one on the board, which is more code and a second
  place where the safety envelope lives. Restart and state capture: the
  `Instrument` is made again after a halt; its `snapshot` and the run
  record (`InstrumentRun`) carry the device identity, which the driver's
  `identity` fills from the device (serial number, firmware, runtime
  version).
- **Security of local instrument control** (requirements, "Security and
  privacy constraints"). The envelope is enforced in `pbc.instruments`
  for both, outside any model. The AD3 is reached only by the process on
  the computer it is plugged into. The Red Pitaya is reachable by any
  host on its network with no authentication on SCPI and a default root
  password, so the product would have to require a direct cable or an
  isolated network, a changed password, and the SCPI server stopped
  after use; the input jumpers add an interlock only the learner can
  confirm.

### Recommendation

**Question 17: the Analog Discovery 3, the Pro Bundle (DigiKey 471-060),
with a series RLC circuit on a breadboard** (100 Ω, 10 mH, 100 nF, as the
bench). Reasons: it covers the envelope with margin; its input range is
chosen in software and protected to ±50 V, where the Red Pitaya's is a
jumper the software cannot read with an absolute maximum of ±1 V on LV
above 1 kHz; its output drives the circuit directly (0 Ω, 30 mA, against
20 mA at the envelope's maximum on the bench circuit); it is one USB
device on the learner's computer, with no network exposure; it fits
the conditions of use below; and it costs less. The Pro Bundle rather
than the base kit, for €32.22 more, subject to the final basket price:
see "Purchase options". Against it: the proprietary
WaveForms runtime is a manual installation outside the lock, whose
licence the pilot must read; the envelope must add a lower limit on the
circuit's R (or a lower amplitude) so that the current stays within
30 mA.

**Question 18 (superseded history: the owner decided a maximum of
EUR 1,000 on #508, 2026-11-13): the proposed budget of €500, including
VAT and shipping, and the open question of raising it to €550.** The estimated
starting cost is about €484 to €519 for the Pro Bundle with the RLC
material, and about €452 to €487 for the base kit with it, both before
shipping and any missing tools ("Purchase options"). The base kit fits
€500 with a margin of €13 to €48 for shipping and tools; the Pro Bundle
fits only at the lower end of the material's estimate. This record
therefore proposes €550 for the Pro Bundle with the RLC material,
shipping, and small tools: a proposal for the owner's decision, not a
decision taken. No second device; an LCR meter is not included (the AD3
measures the parts against a known resistor). If the owner decides
against a device, F140 ends here with a no-go, and no page or document
claims hardware support.

**The simplest viable implementation**, on a go: one live driver of about
150 lines in `pbc.instruments` implementing the `Driver` protocol over the
SDK (by `ctypes` or `dwfpy` in the optional group `physics-lab`), which
sets `DwfParamOnClose` to stop, uses the ±25 V input range, sets the
generator to a frequency the sample clock divides exactly and reports
it (the one contract change), captures both channels in one triggered
acquisition, and fills `identity` from the device; the envelope gains
the circuit-resistance limit. Bluesky and QCoDeS are compared in the
pilot, as the roadmap says.

**Limits of the spike.** No device was used, so every number is the
vendor's or a calculation from it. Digilent's own pages (reference
manual, WaveForms download, SDK manual, forum, shop) and Red Pitaya's
shop refused automated access: the AD3 figures come from Digilent's
specification document as served by a distributor [AD1], and some facts
come from distributors or search results, marked so above. Per-call
latency, the behaviour after a killed host process or a pulled cable
(with the power configuration chosen), the WaveForms licence, and a
checked bill of materials of the circuit are not documented in what
was read and are the pilot's to establish.

### Conditions of use (the owner, 2026-11-13)

The owner has no workbench, experiment table, or permanent lab room. The
set-up must fit on an ordinary dining or writing table, be easy to put
away and set up again, be built without soldering in the first phase,
work with low-voltage circuits, and need as little mechanical mounting as
possible. This makes an RC or RLC circuit on a breadboard the most
suitable first physical set-up: the AD3 and a breadboard fit in a box,
the parts plug in, the voltages stay within the AD3's ±5 V outputs
[AD1], and nothing has to be mounted.

### Purchase options (the owner's price check, 2026-11-13)

| Option | DigiKey part | Price, including 21 % VAT, excluding shipping | Contents |
|---|---|---|---|
| Analog Discovery 3, base kit | 410-415 | €407.09 [AD10] | the AD3, its USB-C cable, the flywire cable [AD6] |
| Analog Discovery 3 Pro Bundle | 471-060 | €439.31 [AD11] | as the base kit, plus a BNC adapter, two oscilloscope probes, and grabber clips [AD12] |

At a difference of €32.22 the Pro Bundle is the recommended variant,
subject to the final basket price. Its BNC adapter is not needed for the
first RLC set-up, which is wired with the flywires. The adapter connects
the oscilloscope single-ended, referenced to ground: it does not keep
the differential connection of the AD3's ordinary inputs, so through it
only voltages against ground can be measured.

The RLC material (breadboard, jumper wires, resistors, capacitors,
inductors, and a few further parts) is estimated at €45 to €80
including VAT: a budget estimate, not a checked, complete bill of
materials. The expected totals, before shipping and any missing tools:

| | Device | RLC material | Total |
|---|---|---|---|
| Base kit | €407.09 | €45 to €80 | about €452 to €487 |
| Pro Bundle | €439.31 | €45 to €80 | about €484 to €519 |

Against the proposed budget of €500 including VAT and shipping
(question 18): the base kit fits with €13 to €48 left for shipping and
tools; the Pro Bundle fits only at the lower end of the material's
estimate, and not once shipping or a tool is added. A budget of €550 is
proposed for the Pro Bundle, the material, shipping, and small tools;
it is a proposal for the owner's decision, not an approved budget
(superseded history: the owner decided a maximum of EUR 1,000 on #508,
2026-11-13).

### The first experimental phase

The first set-up is an RC or RLC circuit on a breadboard. Its aims: to
measure the frequency response, the phase shift, the resonance, and the
damping; to compare the model's predictions with one's own
measurements; to take the parts' tolerances, the inductor's winding
resistance, and the measurement uncertainty into account; and to use
the same set-up later for adaptive measurements and model selection by
an agent. In the first phase the parts are exchanged by hand; switching
them automatically with relays is not a requirement (automatic
switching is out of F140's scope in the roadmap).

The closest connection in the curriculum is the lesson EM5 ("RLC
circuits and resonance",
`site/lessons/electromagnetism/05-rlc-circuits-and-resonance/index.qmd`)
and the measured-data lab EM8 ("RLC circuit measurements lab",
`site/lessons/electromagnetism/08-rlc-circuit-measurements/index.qmd`).
In Part B the same set-up can serve instrument control, measurement
quality, adaptive campaigns, and system identification, starting from
the frequency-response protocol of the Autonomous Physics Lab
(`products/physics-lab/README.md`). This connection does not mean that
the existing lessons or software can already take one's own AD3
measurements: EM8 analyses its declared dataset, and the product's
*live* mode has no adapter. Three pieces of follow-up work, none of
them done or decided here:

- **the adapter**: the live driver of "The simplest viable
  implementation", in F140's physical pilot on a go;
- **the data export**: the captured traces written with device,
  calibration, configuration, timestamps, units, and operating
  conditions, and declared as a dataset with its card and decision
  (ADR 007) before anything derived from them is published;
- **the lesson integration**: whether and how EM5, EM8, or a Part B
  page take a learner's own measurement, a curriculum change for a
  later Issue.

### Possible extensions (options, in this order)

Indicative self-build budgets of the owner, 2026-11-13. None is part of
F140, whose roadmap entry excludes a second device and thermal hardware;
each would need its own decision.

| Possible extension | Connection | Estimated extra material | Status |
|---|---|---|---|
| Sound: a speaker, an amplifier, a microphone, and possibly a resonance tube | mainly W2, W9 | €50 to €100 | the logical next extension |
| A simple cooling measurement | T7 | to be budgeted separately | first without active heating |
| Polarisation with an LED, filters, and a light sensor | W4 | €40 to €90 | a compact optical extension |
| A pendulum or a mass-spring system | M15 and the mechanics lessons | €60 to €120 | later; needs a stable mount |
| An actively heated thermal set-up | T7, and possibly Part B | €70 to €140 for the whole extension kit | later; needs a supply and a control loop |
| An elastic material test with strain gauges | MAT3, MAT6 | €90 to €180 | later; the mounting and the calibration decide |

The simple cooling set-up and the later full thermal extension are not
simply added together: parts can be reused. The limits of these
connections:

- sound and polarisation connect to the ordinary wave lessons, not
  directly to the existing measured-data labs W7 (optical diffraction
  images) and W8 (wave flume);
- T7's slot is "heat transfer measurements"; its published lab analyses
  soil temperature data, so a cooling measurement connects to the
  slot's subject, not to that lab's dataset;
- an elastic bending test is not a full tensile test to fracture, and it
  may need an analysis other than MAT6's;
- this equipment replaces no microwave set-up for EM7 (a slot without a
  published lesson yet), no wave flume for W8, and no X-ray
  diffractometer for MAT5;
- the existing measured-data labs remain usable without buying any
  equipment.

The slots named in this record and their lessons:

| Slot | Lesson |
|---|---|
| EM5 | `site/lessons/electromagnetism/05-rlc-circuits-and-resonance/index.qmd` |
| EM7 | none yet (F54; its dataset has a go decision) |
| EM8 | `site/lessons/electromagnetism/08-rlc-circuit-measurements/index.qmd` |
| W2 | `site/lessons/waves/02-interference-and-resonance/index.qmd` |
| W4 | `site/lessons/waves/05-polarisation-and-maluss-law/index.qmd` |
| W7 | `site/lessons/waves/09-lycopodium-diffraction-lab/index.qmd` |
| W8 | `site/lessons/waves/08-wave-flume-lab/index.qmd` |
| W9 | `site/lessons/waves/03-sound-and-the-doppler-effect/index.qmd` |
| T7 | `site/lessons/thermodynamics/10-soil-temperature-measurements/index.qmd` |
| M15 | `site/lessons/mechanics/20-pendulum-measurements/index.qmd` |
| MAT3 | `site/lessons/materials/03-elasticity-and-deformation/index.qmd` |
| MAT5 | `site/lessons/materials/06-xray-diffraction-lab/index.qmd` |
| MAT6 | `site/lessons/materials/05-stress-strain-measurements/index.qmd` |

### Sources (accessed 2026-11-13)

- [AD1] Digilent, "Analog Discovery 3 Specifications" (PDF of 2023-12-04), <https://assets.testequity.com/te1/Documents/pdf/digilent/Digilent_Analog-Discovery-3-Specifications_1123.pdf>
- [AD2] DigiKey, Analog Discovery 3 product highlight, <https://www.digikey.com/en/product-highlight/d/digilent/analog-discovery-3>
- [AD3] Digilent, WaveForms download page (search result text only; the page refused access), <https://reference.digilentinc.com/reference/software/waveforms/waveforms-3/start>
- [AD4] Digilent, `dwfconstants.py` in Digilent/PmodAD5-Test, <https://github.com/Digilent/PmodAD5-Test/blob/master/dwfconstants.py>
- [AD5] PyPI, <https://pypi.org/project/pydwf/> and <https://pypi.org/project/dwfpy/> (JSON metadata)
- [AD6] DigiKey, as [AD2]: 410-415 at $379.00, 471-060 Pro bundle at $409.00, contents of each
- [AD7] Digilent blog, "What's Different with the Analog Discovery 3?" (search result text only), <https://digilent.com/blog/whats-different-with-the-analog-discovery-3/>
- [AD8] as [AD4], line `DwfParamOnClose = c_int(4) # 0 continue, 1 stop, 2 shutdown`
- [RP1] Red Pitaya documentation, STEMlab 125-14 (original), <https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/ORIG_GEN/125-14/top.html>
- [RP2] Red Pitaya documentation, STEMlab 125-14 Gen 2, <https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/GEN2/125-14_Gen2/top.html>
- [RP3] Red Pitaya documentation, SCPI server, <https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/scpi.html>
- [RP4] Red Pitaya, GitHub repository RedPitaya/RedPitaya (`COPYING`, `tools/scpi/redpitaya_scpi.py`, releases), <https://github.com/RedPitaya/RedPitaya>
- [RP5] Red Pitaya documentation, remote control and programming, <https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/remoteAndProg.html>
- [RP6] Red Pitaya documentation, acquisition commands, <https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list/commands-acq.html>
- [RP7] Sundance, STEMlab 125-14 PRO Gen 2 Starter Kit, <https://store.sundance.com/product/stemlab-125-14-pro-gen-2-starter-kit/>
- [RP8] CNX Software, 2025-06-24, <https://www.cnx-software.com/2025/06/24/red-pitaya-stemlab-125-14-pro-gen-2-is-an-amd-zynq-7010-7020-based-board-for-measurement-control-and-signal-processing/>
- [RP9] Red Pitaya documentation, SSH connection (search result text), <https://redpitaya.readthedocs.io/en/latest/developerGuide/software/getting_started/ssh/ssh.html>
- [M1] Analog Devices, ADALM2000 reference manual, <https://analogdevicesinc.github.io/system-level/tools/m2k/users/reference_manual/>
- [M2] Analog Devices, GitHub repository analogdevicesinc/libm2k (licence, release v0.9.1), <https://github.com/analogdevicesinc/libm2k>
- [M3] Farnell UK and DigiKey Belgium listings (search result text only), <https://uk.farnell.com/analog-devices/adalm2000/module-data-acquisition-system/dp/4032975>
- [AD9] Digilent, WaveForms reference manual 3.24.3, the device's power (given by the owner; not fetched in this session), <https://files.digilent.com/manuals/WaveForms/3.24.3/start10.html>
- [AD10] DigiKey Netherlands, Digilent 410-415, €407.09 including 21 % VAT (the owner's price check), <https://www.digikey.nl/en/products/detail/digilent-inc/410-415/19235661>
- [AD11] DigiKey Netherlands, Digilent 471-060, €439.31 including 21 % VAT (the owner's price check), <https://www.digikey.nl/en/products/detail/digilent-inc/471-060/19235252>
- [AD12] Digilent shop, Analog Discovery 3 Pro Bundle, its contents (given by the owner; not fetched in this session), <https://digilent.com/shop/analog-discovery-3-pro-bundle/>

## Decision record: the physical pilot (F140, 2026-11-22)

**Decision: go**, for the live adapter of the Analog Discovery 3 in the
Autonomous Physics Lab, within the operating limits below. Its condition,
an independent observation with the owner's multimeter that the watchdog
switches the generator off after the program is killed, is met
("Failure handling"). The physical pilot is the
second part of F140 (Issue #508). It ran on 2026-11-22 with the owner at
the bench, after the owner's decisions on questions 17 and 18 (2026-11-13)
and the owner's start of the pilot.

**Scope and limits.** One device (Analog Discovery 3 Pro Bundle,
SN:210415BFB222, WaveForms 3.25.1 on macOS, USB power only) and one circuit
on a breadboard, the owner's parts: W1 → R → L → C → ground with R 100 Ω
± 1 %, L 1 mH, C 10 nF ([the owner's circuit
decision](https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-7077711021);
f0 near 50 kHz instead of the bench's 5 kHz, the same √(L/C) and Q).
Low voltage only. No rewiring by software and no automatic switching. The
parts were exchanged and the probes moved by the owner's hands.

### What the pilot built

- **The live adapter** `pbc.instruments.analog_discovery` (about 600 lines
  with its watchdog). It implements the `Driver` protocol over the vendor's
  C library through `ctypes` of the standard library. The library is loaded
  from `/Library/Frameworks/dwf.framework/dwf` on macOS: the copy inside
  `WaveForms.app` loads but finds no device. `PBC_DWF_LIBRARY` overrides the
  path. The SDK is never in `uv.lock`, so the optional group `physics-lab`
  gains no package and the adapter needs no dependency change. It is
  imported only lazily, by the command line's live mode
  (`tests/unit/test_products_boundary.py`).
- **The envelope of the live bench**
  (`pbc.products.physics_lab.protocol.live_envelope`): the bench's
  amplitude, samples, and timeout. The frequency reaches 200 kHz and the
  sample rate 20 MS/s for the owner's circuit. A new **current bound**
  (`Envelope.current`) refuses an amplitude that could drive more than
  30 mA, the AD3's distortion-free output current, through the circuit's
  declared series resistance at its lower tolerance (a series circuit's
  current is at most V/R). The bound is model-based: it holds for the
  assumed passive series RLC circuit as wired and declared. It is not a
  measured current limit, and with wrong wiring (a short, a missing
  resistor) it need not hold.
- **The realised sample rate.** The AD3's scope runs at 100 MHz over a
  whole divider, so the capture reports the realised rate and its sample
  times. The protocol reads a record that does not span whole periods by a
  least-squares fit (`fitted_phasor`); the simulated and recorded routes
  are unchanged. The contract change the desk spike expected
  (`set_output` returning the frequency set) was not needed: the
  generator's frequency is set to about 1e-8.
- **The live mode** of the command line (`run --mode live`), the pilot's
  input (`products/physics-lab/examples/live-pilot.toml`), and a run
  record with the device, the SDK, the calibration statement, the declared
  circuit, the processing, and the device's temperatures and supply at the
  start and the end.
- **The dataset** `ad3-rlc-pilot` (card, dossier `docs/datasets/ad3-rlc-pilot.md`,
  sample, reference figure of the measured against the simulated response)
  and its **CI fixture**. The recorded mode replays the committed sweep
  without the device (`workflow.read_export`) and reproduces the live run's
  points, f0, and Q.

### Evidence

| Item | Result on the device |
|---|---|
| Physical operation | Two sweeps at 1 V, 5 kHz to 200 kHz, 19 points, about 5 s each including the 2 s warm-up: f0 47,004 and 47,009 Hz, Q 1.542 and 1.549 |
| Against the model | The nominal parts predict f0 50.3 kHz and Q 3.16. Measured apart (channel 2 moved to the R–L node): L 0.861 ± 0.010 mH, C 14.55 ± 0.15 nF, and a coil loss of 63 ± 3 Ω near the resonance. These predict 45.0 kHz and 1.50, within 5 % of the measurement. The coil's loss grows with the frequency, so no constant R fits the band (the dossier) |
| The contract tests (`pbc.instruments.conformance`) | all pass on the device; `repeatable` is not applicable to a physical device |
| The envelope's refusal | 2.5 V, 250 kHz, and 2 V into a declared 50 Ω (40 mA) refused; the adapter received no call and W1 read 1e-5 V |
| The stop | W1 0.998 V → 2e-5 V at once, also during an acquisition; every later operation refused; a new instrument restarts at 0.998 V |
| Latency of one point | excitation median 1.3 ms (max 6.9 ms), acquisition median 16 ms (max 20 ms), far below the 10 s timeout |
| Fake driver | the same refusals, the stop during an acquisition, the contract tests, and the endings, on a stand-in for the SDK in CI (`tests/unit/test_analog_discovery.py`) |

The device tests are `tests/unit/test_analog_discovery_device.py`. They
skip unless `PBC_LIVE_DEVICE=1` with the circuit wired, so no verification
and no CI job drives a device.

### Failure handling

| Case | What the pilot observed | What the adapter does |
|---|---|---|
| Stop requested | W1 off at once (above) | `output_off` waits at most 0.5 s for a running SDK call, then stops the generator anyway. `set_output` configures W1 under one hold of the lock and switches it on only when no stop arrived since it began; a stop that lands while W1 is switched on is followed by a second stop, and the call is refused (the owner's review of PR #607; fake SDK only) |
| Call that hangs | (fake driver only: not observed on the device) | each acquisition polls under its own 5 s deadline, below the envelope's 10 s timeout. A stop that finds a call still running after 0.5 s calls the SDK outside the lock; that this is safe assumes the WaveForms SDK tolerates concurrent calls on one handle, which no cited source documents and the fake SDK cannot show. With an SDK that hangs, neither that stop nor the watchdog is an emergency stop: the watchdog is an additional protection in software, not an independent hardware emergency stop, and the hardware's own way out is to unplug the USB cable |
| Wrong wiring | (not tried) | none detected: the current bound assumes the declared passive series RLC circuit, and the live confirmation says so; a short or a missing resistor can draw more than the bound, up to what the AD3's output itself limits |
| Program ends without `close` | the interpreter crashed at exit (SIGSEGV) | closes the device at exit (`atexit`), output off first; exit 0, W1 off |
| Pulled USB cable, W1 on | the next capture failed at once with a clear error, no hang; reopening reported "no device" until the cable was back; after reconnecting, W1 was off and the same serial captured | `close` treats the lost device as closed, keeps the reason (`lost`), and leaves the watchdog to stop W1 if the device comes back within its deadline |
| Program killed (`kill -9`) | **W1 kept generating** (the owner's meter: 0.9 V at 2 V, 1 kHz, still 1 min 45 s after the kill) until the device was opened again and the output switched off. `DwfParamOnClose` = stop acts only on a proper close | every opening switches W1 off first; a **watchdog** process (below) switches it off when the program dies |
| Restart | a new program opens the device with W1 off and measures normally | as above |

**The watchdog.** When the adapter opens the device it starts the same
module as a separate process (`python -m pbc.instruments.analog_discovery
--watchdog SERIAL`), in its own session and deaf to Ctrl-C, hang-up, and
terminate. The watchdog loads no SDK while the program lives: a process
that has the SDK loaded can hold a device open (the pilot). It reads its
standard input. A proper `close` sends "closed" and the watchdog ends. When
the pipe closes without it, because the program ended in any other way,
the watchdog waits for the device to come free (the pilot: 2 s after
`kill -9`), opens it by its serial, switches W1 off, and closes it. In CI a
real watchdog process acts on a parent killed with SIGKILL, without a
device. The adapter refuses the device unless the watchdog reports "ready"
within 30 s of its start, and checks before every switch-on that the
watchdog still runs; a watchdog that has ended keeps W1 off and the
output is refused (the owner's review of PR #607). The watchdog is an
additional protection in software, not an independent hardware emergency
stop: it shares the computer, the USB connection, and the vendor's SDK
with the program it guards.

**The bound of the crash case.** The watchdog cannot help when it is
killed together with the program (for example `kill -9` of both), or when
the device does not come back within 60 s. W1 then keeps the last setting
the envelope permitted (at most 2 V and 30 mA into the declared circuit)
until the device is opened again or unplugged. The learner's instruction
(`products/physics-lab/README.md`): after a crash, start the lab again or
unplug the USB cable.

**The watchdog, observed independently** ([#508, 2026-11-22](https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-7081162310)).
With the owner's multimeter (V~) across W1 and ground,
`PBC_LIVE_DEVICE=1 uv run --locked python
tests/unit/test_analog_discovery_device.py --meter` switched W1 on at 2 V,
1 kHz (the meter read about 0.9 V~) and killed the program after 15 s; the
watchdog reported W1 off, and the meter fell to 0.0 at once. The test
needs the owner at the bench and is not run unattended.

### Operating limits

| Quantity or condition | Limit |
|---|---|
| Excitation amplitude | 0.01 V to 2 V |
| Excitation frequency | 1 kHz to 200 kHz |
| Sample rate | 1 kS/s to 20 MS/s; realised as 100 MHz over a whole divider N, within 0.5/N of the rate asked (0.16 % at 5 kHz and 64 samples per period, up to 3.4 % at 147 kHz). The contract test's 1 % tolerance therefore holds only below about 2 MS/s; the protocol's fit does not need it |
| Samples per acquisition | 16 to 16,384 |
| Source current | at most 30 mA: amplitude over the declared series resistance at its lower tolerance (99 Ω for the pilot's circuit). Model-based, not measured: it holds for the assumed passive series RLC circuit, not under wrong wiring |
| One device call | at most 10 s (the acquisition's own deadline 5 s) |
| Input ranges | channel 1 ±2.5 V (the source), channel 2 ±25 V (the capacitor, up to Q times the source) |
| Power | USB only. With a powered auxiliary supply, a pulled USB cable does not remove the device's power; the run record reports the auxiliary voltage |
| Software | WaveForms installed and closed while the lab runs; on macOS `dwf.framework` copied to `/Library/Frameworks` |
| Calibration | the factory calibration; the relative gain and phase of the two channels on their different ranges are unknown (the dataset's dossier) |

### Comparison with Bluesky and QCoDeS

From their documentation only, accessed 2026-11-22; neither was installed
or run (the plan's limit). The question is what each would add to the
minimal adapter on the frequency-response protocol with this device.

| Item | The minimal adapter (`pbc.instruments`) | Bluesky with ophyd [BS1–BS6] | QCoDeS [QC1–QC5] |
|---|---|---|---|
| Physical operation of the AD3 | the adapter above, over the SDK by `ctypes` | no hardware support in Bluesky itself; no Digilent driver among the listed interface packages; one would write an ophyd `Device` around the SDK (the tutorial covers EPICS signals only) | a driver is an `Instrument` with parameters; plain `Instrument` is the documented base for a DLL device; no Digilent driver in QCoDeS or its contrib drivers |
| Limits before the device | the envelope: ranges, the current bound, the interlock, the timeout, outside any model (I34) | none enforced on `set` in the pages read; suspenders pause a plan on a condition, without switching an output | validators reject a value before it is sent; no interlock or envelope described |
| Interruption | `request_stop` switches W1 off at once from any thread; the watchdog covers a killed program | the RunEngine catches Ctrl-C: pause at the next checkpoint, then resume, stop, abort, or halt; it stops the motors it touched; an output off is the device's own `pause` cleanup, and halt does none | Ctrl-C is delayed around critical code and ends the measurement; output off on interruption is not described; actions at close run only on an explicit close |
| Valid restart | a new run on a new instrument; the SA6 campaign's checkpoints in the ledger (F143) | resume rewinds to the last checkpoint within the same process; nothing across a crash | a new run id per run; no resume or checkpoints described |
| State capture | the run record: device, serial, SDK, calibration, configuration, circuit, conditions at start and end, processing, timestamps | descriptors carry each device's configuration; the run start carries the plan and its metadata | the station snapshot (all parameters, recursively) is saved with each run |
| Measurement identity | the run record and the evidence ledger of `pbc.evidence`, exported files | a uid on every document, the run start's time, the run stop's exit status | an increasing run id and a GUID in an SQLite database |
| Footprint | the standard library and NumPy; nothing added to the lock | the bluesky, ophyd, and event-model packages, BSD-3-Clause; their dependency footprint is not stated | the qcodes package, MIT, Python 3.11+; its footprint is not stated |

**Conclusion.** For one device and one protocol, neither framework removes
work. The device code, a wrapper around the same SDK, has to be written in
each. Neither framework enforces the envelope, the current bound, or a stop
that switches the output off. Neither covers a killed process, the case the
pilot found to matter. Bluesky's documents and QCoDeS's snapshots duplicate
what the run record and the evidence ledger already hold for this product.
Both would add a large dependency to the optional group. The minimal
adapter stays. Bluesky's checkpointed resume and its suspenders are the
part worth revisiting for long campaigns over several devices, which are
out of F140's scope.

Sources (accessed 2026-11-22): [BS1] <https://blueskyproject.io/bluesky/main/hardware-interfaces.html>;
[BS2] <https://blueskyproject.io/bluesky/main/state-machine.html>;
[BS3] <https://blueskyproject.io/bluesky/main/documents.html> and
<https://blueskyproject.io/bluesky/main/event_descriptors.html>;
[BS4] <https://blueskyproject.io/ophyd/> and <https://blueskyproject.io/ophyd/tutorials/device.html>;
[BS5] <https://blueskyproject.io/event-model/main/explanations/data-model.html>;
[BS6] <https://github.com/bluesky/bluesky> (licence);
[QC1] <https://microsoft.github.io/Qcodes/examples/writing_drivers/Creating-Instrument-Drivers.html>;
[QC2] <https://microsoft.github.io/Qcodes/examples/DataSet/Performing-measurements-using-qcodes-parameters-and-dataset.html>;
[QC3] <https://microsoft.github.io/Qcodes/dataset/introduction.html> and
<https://microsoft.github.io/Qcodes/examples/basic_examples/15_minutes_to_QCoDeS.html>;
[QC4] <https://qcodes.github.io/Qcodes_contrib_drivers/>;
[QC5] <https://github.com/microsoft/Qcodes> (licence).

### Cost

| Item | Cost | Source |
|---|---|---|
| Analog Discovery 3 Pro Bundle | €439.31 including VAT at the owner's price check of 2026-11-13 | [AD11] of the desk spike; the final invoice is the owner's and not recorded here |
| The circuit's parts and breadboard | the owner's own order (TinyTronics); its amount is not recorded on the Issue | the owner's circuit decision |
| Software | none: WaveForms and its SDK are free to use with Digilent hardware (the licence in WaveForms, read on 2026-11-22) | Issue #508 |
| Time per sweep | about 5 s for 19 points, including the 2 s warm-up | the run records |

Within the owner's maximum of EUR 1,000. No second device, and no LCR
meter: the parts were measured with the AD3 itself, against the known
resistor.

### What the go does not claim

- One device and one circuit were measured; another circuit is a new
  measurement, with its own declared parts and resistance bound.
- The live adapter was run on macOS only; the library paths for Linux and
  Windows are the vendor's names, untested.
- No lesson takes a learner's own measurement; the lesson integration is
  later work.
- The pilot's run records are processed data with an unknown channel
  calibration (the dossier); the dataset's go concerns these files, not a
  calibrated instrument.

## The product, part 1 (F145, Issue #614, 2026-11-24)

Part 1 grows the slice into the product: three protocols on electronic
circuits, campaigns over them, a quality gate, intervals, an independent
check per protocol, the export, the interface, and the recording and
replay of agent campaigns. Part 2, the capstone page SA9 and the complete
`products/physics-lab/`, follows after F139. An educational and
experimental tool, not a certified laboratory instrument.

**The contract's square wave (Level 3, the safety boundary I34).** The
transient protocol needs a step. The contract gains a second waveform, a
square wave between 0 V and the amplitude, never below 0 V or above the
amplitude. An envelope permits only the sine unless it names the square
wave (`Envelope.waveforms`), and the instrument refuses a waveform that the
envelope does not permit, or that the adapter does not declare, before any
call reaches the adapter. A sine reaches an adapter as before, so the
drivers of the lessons are unchanged. The simulated bench integrates the
square drive piece by piece between its edges; the recorded adapter
matches the waveform; the Analog Discovery 3 sets the SDK's square
function with amplitude and offset each half of the amplitude (shown on
the fake SDK only: the device is the owner's bench); the conformance suite
has the waveform checks apart from its existing checks
(`tests/unit/test_instrument_waveforms.py`). The current bound keeps its
form, amplitude over the declared series resistance: a step of height A
drives at most A / R through a series RLC circuit (the step response peaks
at (A / (Q R)) e^(-alpha t*)) and through the LED pair, and the test
compares the integrated peak with that closed form. A campaign refuses a
square wave whose half period holds fewer than ten decay times of the
declared circuit, so that one ring has died before the next step.

**The three protocols** (`pbc.products.physics_lab`):

| Protocol | Physics | Interval | Simulator's check | Check of a real circuit |
|---|---|---|---|---|
| Frequency response (`resonance`) | a linear system in the steady state | f0, Q, k by a weighted fit of the second-order response to the log-gain and the phase of every valid point, widened by the reduced chi-square | the closed form of the simulated circuit, within three standard errors and F138's 1 % and 3 % | agreement with the ring-down |
| Transient response (`transient`, `ringdown`) | the same system's free decay after a step | f0 and Q of each ring-down from the fit of F139's manual route; repetitions by their weighted mean, widened by the Birge ratio | as above | agreement with the frequency response |
| Amplitude response (`nonlinear`) | a memoryless, symmetric diode characteristic: two LEDs of one colour in anti-parallel behind a resistor | the fundamental gain and the third-harmonic ratio, fitted together with the odd harmonics; n and I_s of v = n V_T asinh(i / 2 I_s) | n within 5 % and the voltage at 1 mA within 10 mV of the simulated LEDs | the held-out prediction: the characteristic fitted at the largest amplitude predicts the gain at every other one |

Two estimates agree when they differ by at most two combined standard
errors (`estimates.agreement`). The nominal closed form is the
simulator's check only: on F140's circuit it fails (L about 0.86 mH, C
about 14.5 nF, a coil loss that depends on frequency), and this feature
reports that discrepancy as `ad3-rlc-pilot` holds it, without a
resolution. The held-out check tests the model of the pair, not the
declared resistor: a wrong resistor rescales the fitted saturation current
exactly, so it cannot be seen there; two LEDs of different colours fail
it.

**The quality gate** (`quality`) passes every capture before a number is
read: clipping at the declared rails of the execution mode, lost samples
beyond 1 %, the Nyquist rate of the highest frequency the protocol reads,
the declared calibration, and a source channel that does not carry the
excitation. An invalid capture is recorded with its reason and raw
samples, exported, retried once by the adaptive policy, and never fitted.

**Campaigns** (`campaign`, `bench`, `lab`). A plan declares the circuit
(series RLC or LED pair, with its nominal parts and series resistance),
the protocols, their settings, the targets of the intervals, and the
budget. The routes reach the instrument only through `Campaign.execute`:
the classical adaptive policy (bisection of the -90 degree bracket until
the interval of f0 is at its target, repeated ring-downs until the
interval of Q is, refinement where the LED gain changes most), the
scripted sweep, and the bounded agent replayed from its trace. A
checkpoint follows every measurement and its digest goes into the
campaign's journal; a stop ends the segment with the output off, and a
resume accepts only the journal's latest checkpoint, unchanged, of the
same plan, on the same bench, from an interrupted segment. The routes are
compared by the measurements each needed for the same interval width of
f0 (`lab.compare_routes`): every agent campaign on the simulator runs the
adaptive policy and the scripted sweep on fresh benches with the same
plan and seed, and its `run.json` (`comparison`) and `report.md` put the
three routes side by side (`lab.baseline_comparison`; a plan without a
frequency response compares the measurement counts only).

**The export** of a campaign: `raw.csv` (every sample, valid or not),
`measurements.csv`, `report.md` with its figures, `run.json` (the run
record with the execution mode, the plan, the evaluator's checks, the
invalid measurements, the agent's answer labelled unverified),
`evidence.json`, and the checkpoints. The evaluator recomputes every
number from `raw.csv`. A campaign's export replays as a recorded campaign
(`lab.read_campaign_export`, the recorded adapter in order), never a new
experiment: a live campaign's export becomes a declared dataset this way
(ADR 007), after the owner confirms its licence on the Issue.

**Agent campaigns.** One allowlisted tool per protocol of the plan
(`agent_campaign`); a result gives the gate's verdict and the numbers with
their errors, never the circuit's values. The committed fixtures
`products/physics-lab/fixtures/agent-campaign-series-rlc.json` and
`products/physics-lab/fixtures/agent-campaign-led-pair.json` are
placeholders of a scripted policy, not of a model, until the owner or the
supervisor session records real campaigns with `record-campaign`; the
build replays every call against a fresh simulated bench. The recording
counts the tokens of every call, prices them at the rates the recorder
gives, adds them to a spend ledger kept outside the repository (required
with `--provider`), and stops with what was recorded at the ceiling (EUR 50
for this capstone), before a call that would cross it, or after a call
whose usage the provider does not report (unless its prices are zero, as
for a local model).

**The providers of a recording** (#615). `--provider` names a module of
`pbc.agents.clients`, each of the shape `ModelClient` with its own
`make_client()`, and each reporting the tokens of a call in `last_usage`,
which the spend count reads:

- `openai`: the default provider of the agent lessons (`PROVIDER` stays
  `"openai"`), its SDK in the optional group `openai`, the key in
  `OPENAI_API_KEY`;
- `anthropic`: Claude, through the provider's own SDK in the optional group
  `anthropic` (`uv sync --extra anthropic`), the key in `ANTHROPIC_API_KEY`,
  the model in `PBC_ANTHROPIC_MODEL` or by default `claude-opus-5-5`, the
  current Opus of the provider's model table (2026-11-24). The harness keeps
  the text and the tool calls of a turn, not the model's thinking blocks,
  and sends the conversation back without them, which the provider accepts;
  a declined request ends the campaign with a message that says so. Tokens
  written to or read from the prompt cache count as input at the full price,
  so the count never undercounts;
- `local`: an open-weights model on the learner's own machine, behind a
  server that speaks the OpenAI-compatible API (Ollama, LM Studio, a
  llama.cpp server), through the `openai` SDK and no new dependency. The
  address is `PBC_LOCAL_BASE_URL` or by default Ollama's
  `http://localhost:11434/v1`, and it must be a loopback address (`localhost`,
  127.0.0.0/8, `[::1]`); the client ignores any proxy of the environment and
  follows no redirect of the server (a redirect fails the request), so no
  prompt leaves the machine by it. The model is `PBC_LOCAL_MODEL`, which
  the recorder chooses: the project sets no default and downloads nothing.
  The tokens are counted where the server reports them, at a price of zero,
  so the recording needs no `--price-in` or `--price-out`. A server that
  leaves usage out does not stop the recording: such a call counts as zero
  tokens, and the spend summary says that usage was not reported on every
  call.

The SDKs are optional: the group `physics-lab` holds both, and the default
environment, the site build, and CI install neither. Only the modules of
`pbc.agents.clients` import an SDK, each its own, and only they read the
environment, each the variables of its own provider and through
`pbc.agents.secrets` (`tests/unit/test_agents_boundary.py`,
`tests/unit/test_coding_agent_boundary.py`). The tests use a stand-in for
each SDK: no test calls a provider or holds a key.

**The interface** gains a campaign section on the same page and under the
same loopback, Host, Origin, and token rules: the plan, the route, the
confirmation of the declared circuit, the progress measurement by
measurement, the intervals, the verdicts, the invalid measurements with
their reasons, the figures, the stop, and the export. A live campaign
starts from the command line, which prints the confirmation before the
device opens.

**Commands.**
`uv run --locked python -m pbc.products.physics_lab campaign --plan
products/physics-lab/examples/campaign-series-rlc.toml --circuit-confirmed
--out <directory>` (also `campaign-led-pair.toml`; `--route adaptive`,
`scripted`, or `agent`; `--mode recorded --sample <export>`; `--resume`).
The owner's bench sessions use
`products/physics-lab/examples/live-campaign-series-rlc.toml` (the pilot's
circuit, both protocols on one wiring) and
`products/physics-lab/examples/live-campaign-led-pair.toml` (two red LEDs
behind 100 ohm, at most 20 mA at 2 V) with `--mode live`.

**Limits.** No live campaign, model campaign, or dataset of this part has
been recorded yet: they are the owner's, at the bench and with a key. The
fake SDK shows the square wave's SDK calls, not the device's output. The
LED model has no series resistance of its own and no temperature
dependence. The coil-resistance measurement that discriminates between the
explanations of the pilot's discrepancy is reserved for F155.

## Decision record: the guided route pilot (F139, Issue #613, 2026-11-25)

**A narrower go.** The guided route with Agent Codeyard
(`taspinar/agent-codeyard`, the renamed Agentic Coding Template) at its
commit `df5430aa` is optional; the manual route is the default of Path 1.
`products/physics-lab/ROUTES.md` holds both, and the lighter option of a
coding agent under `docs/coding-agent-workflow.md`, each with only the
commands its pilot ran and with its conditions. Within the pilot's limit
of two hours of active time the Codeyard route reached no open pull
request: its feature review refuses a reviewer of the implementer's
provider, and every role of the run used one provider. The owner decided
on that record (2026-11-25); decision 42 allows a no-go or a narrower go
at an exhausted limit, never an extension.

**The feature** is the ring-down fit of the transient-response protocol:
the starter gains the skeleton
`products/physics-lab/starter/my_lab/ringdown.py`, its
`products/physics-lab/starter/SPECIFICATION.md`, and twelve provided
tests, the common task of the three runs, unchanged. The starter's
`products/physics-lab/starter/tests/conftest.py` skips them while
the skeleton raises `NotImplementedError`, so the `starters` check stays
green and still imports them at the pin;
`tests/unit/test_starter_ringdown.py` shows in a copy of the starter that
they run unchanged and pass once a working fit is in place. No solution is
committed to the starter: the reference is
`pbc.products.physics_lab.ringdown` of F145.

**What the pilot measured.** The manual route and the coding agent without
a template each passed the twelve tests within minutes (the agent: 164 s,
18 turns); the Codeyard route reached no open pull request within its
limit. Run on after the limit with a reviewer of a second provider, as a
separate observation outside the pilot's result, it reached one after
about 109 minutes of active time in all; that command is marked so in
`products/physics-lab/ROUTES.md`. Every run was made by a model or the
supervisor session, inside a subscription, with no per-call billing; no
learner was timed, so the workload of Path 1 stays open question 22, and
`products/physics-lab/ROUTES.md` gives only an estimate of the feature's
size, labelled as from one pilot. The gaps
for Agent Codeyard (a configuration check that passes a refused review,
retries of a configuration error, a planning that enlarges a small task,
the template's own red first CI run, no place for a given failing test
suite) are proposed work for that repository, recorded on the Issue. One
gap is this repository's own: rule 2 of the sandbox profile of
`docs/coding-agent-workflow.md` names commands only, and the agent's file
tool wrote outside its scratch copy; the profile is restated on the pages
of the exercises, so its change is a follow-up of its own, and
`products/physics-lab/ROUTES.md` states the precaution meanwhile.
The boundary test (`tests/unit/test_coding_agent_boundary.py`) now knows
the template by both names: no file of the build or the checks depends
on it.

## The Scientific Research Workspace, part 1 (F155, Issue #619, 2026-11-25)

Part 1 of F155 delivers the workspace and its reproduction track; the
original track, the capstone page RR8, and the starter follow in later
parts. The package is `pbc.products.research_workspace`; the learner's
material is `products/research-workspace/README.md`.

**The reproduction track.** The spectrum fit of Fixsen et al. (1996)
regenerated from the dataset `cobe-firas-monopole`, the LAMBDA file that
holds Table 4 of the paper (`docs/datasets/cobe-firas-monopole.md`). Its
goal is the published spectrum fit from the derived data, not the absolute
temperature calibration. The published values rest on words quoted on the
register entry `fixsen-1996-firas-spectrum`; a value whose words are not in
the entry's checked statement is refused (`sources.py`).

**What the workspace holds** (a project directory, `project.py`): the
questions considered, each assessed before any run (a declared dataset with
a go, at least two reachable outcomes, the stage budget) and archived with
its decision in the chain of `pbc.research.ideas` (`questions.py`); the
registered plan, refused when two explanations predict one outcome or when
it has no withheld part or stopping conditions, with its digest, and
refusing evidence measured before its freeze (`registration.py`); the run
graph over `pbc.evidence.resumable`, with the branches of the stage `fit`
in sequence and the declared criterion (a parameter continues when it
lowers chi-square by more than 4), a failed attempt kept with its reason
(`graph.py`, `firas.py`); the rows of the reproduction, each a typed
discrepancy whose type needs a supporting check (`reproduction.py`,
`discrepancy.py`); the follow-up log of findings, evidence, revisions, and
the human's decisions, where a revision never resolves a finding that asks
for evidence and an agent's finding is accepted only through a recomputed
check (`log.py`); the scripted reviewer (`review.py`); the report, whose
claims carry run and source links and evidence statuses, whose numbers
resolve to records, and whose first lines say that a report is not a proof
of success (`report.py`); and the static view, one HTML file with no
server and no JavaScript (`view.py`).

**The agent reviewer** (`agent.py`) has one allowlisted tool, `run_check`,
over the scripted reviewer's checks; the committed fixture is a placeholder
of a scripted policy until the owner or the supervisor records a model's
session, metered against the capstone's ceiling of EUR 50 with the physics
lab's `MeteredClient`.

**What part 1 does not claim.** The rows that reproduce the weighted rms
and the residual figure do so by construction, since the file's residuals
are the paper's own fit, and the figure's rule of 1 sigma is post-hoc (set
after a scratch fit had been seen; its row says so in the report and the
view, never as a confirmatory result); the absolute T0 is `not-reproduced`, typed
`method`; the statistical uncertainties of y and μ are `not-reproduced`,
typed `uncertainty` (0.60 and 0.86 of the paper's, rows added post-hoc
beside the registered bounds); the fits weight with the diagonal
uncertainties, and the review's finding that asks for the paper's
covariance between frequencies stays open.

## The product, part 2: the capstone page SA9 (F145, Issue #614, 2026-11-25)

Part 2 completes the capstone after F139's narrower go. The page
`site/lessons/agents-llm/25-autonomous-physics-lab/index.qmd` (slot SA9,
kind `product capstone`, methods simulation and measured data) teaches the
product in four parts: what lets an agent run real experiments safely and
the lesson outcomes each product feature exercises; the essential code as
excerpts of the real modules (the envelope before the device, one measured
point, a campaign step and the refinement, the ring-down fit, the nonlinear
response, the bounded tool, the evaluator's agreement); the reference
workflow run by its experiment
`src/pbc/electromagnetism/experiments/autonomous_physics_lab.py` on the
simulator (the series RLC campaign with one measurement refused by the
quality gate after a lossy link and its retry, the LED pair with its
held-out check, the agent route beside the adaptive policy and the
scripted sweep, a circuit whose parts are not the declared ones); and what
to build next. The pilot's record `ad3-rlc-pilot` is shown as it is, by
the recorded replay and a figure against the closed form of the labels
(`src/pbc/electromagnetism/pilot_record.py`, a module apart so that the
other figures are not made from a dataset), without a resolution. The page
promises no workload for a coding-agent route and points to
`products/physics-lab/ROUTES.md` once.

`products/physics-lab/` is complete: `README.md` holds the brief and the
scientific acceptance criteria of the whole product and its example
inputs, `WORKFLOW.md` the reference workflow step by step (the commands of
the fresh-clone run), and `RUBRIC.md` the assessment rubric; `ROUTES.md` and
the starter are unchanged.

**What the page does not claim.** The committed agent-campaign traces are
scripted placeholders, and the page says so wherever it shows them. Live
support is what F140's pilot showed, the frequency response on the series
RLC circuit; the ring-down and the LED pair are simulator-only until the
owner's bench sessions, and the model campaigns are recorded later, in
their own pull request, which then changes the page's wording.
