# The Part B products: the instrument contract and the Autonomous Physics Lab slice

The Part B capstones deliver learner-run local applications (ADR 022
decision 5, requirements decision 42). This page describes what F138
delivered for them: the instrument contract, the simulator vertical slice of
the Autonomous Physics Lab, the starter and its pin, and the decision record
of the slice, which settles the unresolved questions 19 (optional dependency
packaging) and 21 (the frontend of the local products), and the record of
F140's desk spike, a recommendation on the questions 17 (the device) and
18 (the budget) for the owner's decision. The learner's own
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
- *live*: no adapter yet. F140 decides on hardware (its desk spike's
  record is the last section of this page); its driver will be imported
  only with the product's optional group.

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

## Decision record: the instrument desk spike (F140, 2026-11-13)

**Scope.** The first part of F140 (Issue #508): a desk spike from vendor
documentation and the F138 contract with its fake live driver
(`tests/unit/test_instruments.py`), no purchase, no device, no vendor
software downloaded or installed. It ends in a recommendation on the
unresolved questions 17 (the device) and 18 (the budget); the physical
pilot, the live adapter, and the comparison with Bluesky and QCoDeS start
only after the owner's decisions are recorded on the Issue. Every source
below was accessed on 2026-11-13. Prices are indicative and dated: a shop
price is not a quote, VAT and shipping vary, and they change.

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
| Link to the computer | USB-C; the specifications list no other power input [AD1] | 1 Gbit Ethernet (a Linux computer on the board), USB-C for power and console [RP2] |
| Host OS and driver | Windows, macOS, Linux [AD2]; the vendor's WaveForms runtime must be installed on the host [AD3] | no driver on the host: SCPI over TCP; the vendor gives Windows and Linux instructions, macOS is not mentioned [RP3] |
| Python access | the WaveForms SDK, a C library (`dwf`) called from Python through `ctypes` [AD3, AD4]; community wrappers `pydwf` 1.1.19 (MIT, 2023-10-18) and `dwfpy` 1.2.0 (MIT, 2025-01-10) [AD5] | a socket client: the vendor's `redpitaya_scpi.py` opens a plain TCP socket to port 5000 [RP4]; Python 3.10+ [RP3]; on-board C++ and Python API [RP5] |
| Licence and maintenance | wrappers MIT; the licence of the WaveForms runtime could not be read (digilent.com refuses automated access) | the repository's `COPYING` is BSD for the directories it lists, which do not name `tools/scpi`; the client file carries only a copyright line [RP4]; last release `Release_2026.1` (2026-07-07), last push 2026-10-31 [RP4] |
| Inputs | 2 differential, 14 bit, 125 MS/s, ±2.5 V or ±25 V, selected in software; 1 MΩ ‖ 24 pF; 9 MHz at -3 dB; overvoltage protection ±50 V DC or ±30 V RMS; buffer up to 32,768 samples per channel [AD1] | 2, 14 bit, 125 MS/s, ±1 V (LV) or ±20 V (HV) by jumper; 1 MΩ / 10 pF; 60 MHz; absolute maximum ±6 V (LV) and ±30 V (HV) below 1 kHz, the full-scale range above it [RP2]; buffer 16,384 samples [RP6] |
| Outputs | 2, 14 bit, 125 MS/s, ±5 V, 0 Ω (not precisely controlled), 30 mA for distortion-free output, 40 mA before cutoff, short-circuit protected [AD1] | 2, 14 bit, 125 MS/s, ±1 V into 50 Ω, ±2 V into high impedance, short-circuit protected [RP2] |
| Against the protocol | every range covered; the capacitor channel needs the ±25 V range (3.36 mV resolution instead of 0.336 mV) [AD1] | every range covered with the HV jumpers; on LV the resonant capacitor voltage (3.2 V at 1 V) exceeds the absolute maximum above 1 kHz, so the jumper setting is a hazard the software cannot read (the gain command only "refers to jumper settings" [RP6]); the 50 Ω source adds to the circuit's R |
| Sample rate | 125 MHz system clock, adjustable 50 to 125 MHz [AD1] | 125 MS/s divided by an integer decimation, 1 to 65,536 [RP6] |
| Calibration | factory calibrated; specifications after 30 min warm-up at 25 °C [AD1]; a user calibration in WaveForms is not documented in what could be read | factory calibrated; calibration app, `calib` utility, or API; Gen 2 needs no 50 Ω terminators [RP2] |
| Bill of materials | AD3 with its USB-C cable and 2×15 flywire cable [AD6]; breadboard; R 100 Ω, L 10 mH, C 100 nF | starter kit: board, SD card with the OS, 5 V 5 A supply, Ethernet cable, 2 probes, 2 SMA-BNC adapters [RP7]; BNC-to-clip leads for the two outputs (not in the kit); breadboard; R, L, C |
| Cost, device | $379.00 (DigiKey, 410-415; Pro bundle with BNC adapter and probes $409.00) [AD6]; $249 academic (Digilent blog, via a search result, not read) [AD7] | £580.00 (Sundance, PRO Gen 2 starter kit) [RP7]; €649 at its 2025 pre-order (CNX Software, 2025-06-24) [RP8] |
| Failure: disconnect | with no other power input [AD1], unplugging should remove the power and the output; the documentation read does not say so, the pilot confirms it | the board keeps running on its own supply; what the generator does when the client goes away is not documented in what was read [RP3] |
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
- **Bill of materials and cost.** AD3: $379.00 plus the circuit; the base
  kit's flywires reach a breadboard directly, so the Pro bundle is not
  needed. Red Pitaya: £580.00 plus leads and the circuit. The circuit
  (breadboard, three components, wires) is an estimate of under €25 from
  general experience, not from a source; the pilot plan prices it.
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
  AD3: a pulled cable should unpower the device (to be confirmed); a live driver sets
  `DwfParamOnClose` to stop instead of relying on the default; a killed
  process is the case the pilot tests. Red Pitaya: the generator is on
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

**Question 17: the Analog Discovery 3, the base kit (DigiKey 410-415), with
a series RLC circuit on a breadboard** (100 Ω, 10 mH, 100 nF, as the
bench). Reasons: it covers the envelope with margin; its input range is
chosen in software and protected to ±50 V, where the Red Pitaya's is a
jumper the software cannot read with an absolute maximum of ±1 V on LV
above 1 kHz; its output drives the circuit directly (0 Ω, 30 mA, against
20 mA at the envelope's maximum on the bench circuit); it is one USB
device on the learner's computer, with no network exposure; with no
other power input, losing its cable should switch it off; and it costs
less. Against it: the proprietary
WaveForms runtime is a manual installation outside the lock, whose
licence the pilot must read; the envelope must add a lower limit on the
circuit's R (or a lower amplitude) so that the current stays within
30 mA.

**Question 18: a budget of €500, including VAT and shipping**, for the AD3
($379.00 list, excluding VAT [AD6]) and the circuit's parts (estimated
under €25), with no second device; an LCR meter is not included (the AD3
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
latency, the behaviour after a killed host process or a pulled cable, the WaveForms
licence, and the circuit's cost are not documented in what was read and
are the pilot's to establish.

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
