# Plan: F140 — the physical pilot with the Analog Discovery 3, Issue #508

- Issue: #508, the second part of F140 (criteria 2 to 5). The desk spike
  (criterion 1) is merged (#509; its plan is
  `.agents/plans/508-f140-instrument-desk-spike.md`, kept as history).
- Branch: `feature/508-one-instrument-feasibility-spike`; base `dcc9b5f`.
- Gate: the owner's decisions on questions 17 (the AD3 Pro Bundle) and 18
  (EUR 1,000), recorded on #508 on 2026-11-13; the owner's start of the
  pilot (2026-11-22); the circuit decision R 100 ohm, L 1 mH, C 10 nF
  (2026-11-22); the supervisor's confirmation that `FDwfEnum` finds the AD3
  from `/Library/Frameworks/dwf.framework/dwf` (2026-11-22).

## Risk

**Level 3 by assessment**: a physical device's safety boundary (the
envelope of the live adapter). `.agents/approvals/508.md` is written. No
dependency file changes: the live driver uses `ctypes` of the standard
library and the vendor's SDK, which the learner installs with WaveForms and
which is never in `uv.lock`; so the optional group `physics-lab` gains no
package (its comment names the driver). A security-focused review of the
envelope is part of the review.

## Visual deliverables

Scientific figure: the measured frequency response (gain and phase of
V_C / V_S) against the simulated response of the circuit, with its status
`measured` and the model drawn apart. Skills: pbc-scientific-visualization.
Validation: the plotted points are those the evaluator recomputes from the
committed sample; the model curve is the closed form of the stated circuit.
Accessible fallback: the points table and the figure's alt text with the
numbers. `Skills: none` for teaching (no lesson's teaching changes).

## Design decisions (from the device, 2026-11-22)

- **The sample clock.** The AD3's scope runs at 100 MHz divided by an
  integer (measured: 64 x 25 kHz = 1.6 MS/s is realised as 1.5873 MS/s,
  -0.8 %); the generator's frequency is set to about 1e-8. Setting the
  system clock (`DwfParamFrequency`) does not make a requested rate exact
  (tried, rejected). So the live driver samples at the realised rate and
  reports it (`Capture.sample_rate_hz`, `t`), and the protocol reads the
  phasor by least squares (cos, sin, constant) when a record does not span
  a whole number of periods; on whole periods it keeps
  `steady_phasor`, so the simulated and recorded routes are unchanged bit
  for bit. The conformance check `capture-shape` accepts a realised rate
  within 1 % of the request when the times follow it.
- **The envelope.** A current bound: the excitation's amplitude over the
  circuit's declared series resistance (its lower tolerance) stays within
  30 mA, the AD3's distortion-free output current; a series RLC circuit's
  current is at most V / R. The live envelope's frequency range is 1 kHz
  to 200 kHz (f0 is about 50 kHz with the owner's parts) and its sample
  rate up to 20 MS/s; amplitude 0.01 to 2 V as the bench.
- **The driver** (`pbc.instruments.analog_discovery`): the SDK by `ctypes`
  from `/Library/Frameworks/dwf.framework/dwf` on macOS (overridable by
  `PBC_DWF_LIBRARY`); `DwfParamOnClose` = 1 (stop) before the device is
  opened; W1 sine; channel 1 on the 5 V range (source), channel 2 on the
  50 V range (capacitor); one simultaneous acquisition; a polling deadline
  below the envelope's timeout; `output_off` callable from any thread;
  `identity` from the device (name, serial, SDK version). It is reached
  only through `Instrument`; `make_instrument(..., LIVE)` builds it.
- **Tests.** A fake SDK object stands in for the library, so the driver's
  calls, its refusals, and the conformance checks run in CI. The device
  tests skip unless `PBC_LIVE_DEVICE=1` and the library and a device are
  present, with the reason stated, so no verification drives a device.

## Discoveries on the device (2026-11-22)

- Opening the device finds W1 off, even after a program that closed with
  `DwfParamOnClose` continue: the AD3 alone cannot observe what W1 did
  between one program and the next; that needs an independent observation
  (the owner's meter or an LED), pending.
- A process that has the SDK loaded keeps a killed child's device opened
  until it ends itself (25 s and more); so the ending cases run from the
  shell (`tests/unit/test_analog_discovery_device.py` as `__main__`), not
  under pytest, and the skip check probes the SDK in a subprocess.
- A program that ended without `close` crashed at exit (SIGSEGV); the
  driver now closes at exit (`atexit`, weakly), and the exit is clean.
- `output_off` waits at most 0.5 s for a running SDK call before it stops
  the generator anyway (a stop must not wait behind a hung call).
- The figure's text alternative claimed agreement with the closed form
  for every run; it now says so only when the check passes (`alt_text`).

## Discoveries at the bench and after (2026-11-22, second session)

- **The killed program** (the owner's meter): after `kill -9`, W1 kept its
  output until the device was opened again; `DwfParamOnClose` acts only on
  a proper close. Mitigation: every opening switches W1 off first; a
  watchdog process (the same module, `--watchdog SERIAL`, its own session,
  no SDK loaded until needed) switches W1 off when the program dies; the
  learner's instruction for a crash. The re-test with the meter is the
  owner's (the decision record, "Pending"); the boundary test allows
  `subprocess` in the adapter only, for the watchdog.
- **The pulled cable**: the stop fails ("did not confirm"); `close` now
  treats a lost device as closed and keeps the watchdog.
- **The realised rate** departs up to 0.5/divider from the request (3.4 %
  at 147 kHz), so the conformance check's 1 % holds only below about
  2 MS/s; an operating limit in the decision record, the protocol's fit
  does not need it.
- **The replay**: a recorded capture keeps the realised rate beside the
  rate asked (`RecordedCapture.realised_rate_hz`), and the recorded mode
  replays a live export directory (`workflow.read_export`) under the live
  envelope and the circuit of its run record. The live run record's
  processing no longer claims whole periods.
- **The parts** measured apart (channel 2 at the R-L node) explain the low
  Q and the lower f0 to within 5 %; the coil's loss grows with the
  frequency. The figure and its numbers: the dataset `ad3-rlc-pilot`.

## The owner's review of PR #607 (2026-11-23)

Four findings, fixed before the merge
([#508 comment](https://github.com/taspinar/physics-by-construction/issues/508#issuecomment-7090028254)):

- **A stop during `set_output`**: the configuration now runs under one
  hold of the lock; a stop counter, raised by `output_off` before it waits
  for the lock, is checked before W1 is switched on and again after; W1
  stays off and the call is refused (`Stopped`). A stop that lands before
  `set_output` begins is answered by the `Instrument`, which switches the
  output off again when the call returns (unchanged).
- **The watchdog's availability**: it reports `ready` after it has ignored
  its signals; the adapter refuses the device without it (30 s) and refuses
  a switch-on while the watchdog does not run. The switch-off path
  (`_stop_generator`, `watch`, `switch_off`, the watchdog's `switch`) is
  unchanged.
- **The current bound is model-based** and **the watchdog is a software
  protection, not a hardware emergency stop**: stated in the decision
  record, the live confirmation, and the README.

## Steps

1. The envelope's current bound and the live envelope; the phasor fit;
   the conformance tolerance; tests.
2. The live driver with the fake SDK and its tests; the opt-in device
   tests.
3. On the device: calibration notes, the pilot sweep (1 V, 5 kHz to
   200 kHz), the envelope's refusal and the stop on the real device, a
   killed process, a restart, the per-call latency. Raw results kept in
   `.agents/handoffs/508-pilot/` (ignored) until they are declared.
4. The dataset: card, dossier (ADR 007 gate), the sample under
   `data/samples/`, its parse test, the reference figure; the recorded
   adapter replays it in CI.
5. The comparison with Bluesky and QCoDeS from their documentation
   (physical operation, interruption, restart, state capture,
   measurement identity) on the same protocol.
6. The decision record (go or no-go, evidence, cost, operating limits) as
   a section of `docs/products.md`; additive rows in
   `docs/architecture.md` and `docs/project-map.md`.
7. `./scripts/verify.sh --targeted`, last.

## Limits

- One device, one circuit (the owner's parts), low voltage only (at most
  2 V amplitude, 30 mA); no rewiring by software, no automatic switching.
- The owner's actions are needed for: measuring R, L, and C apart (a
  rewiring), the pulled-cable case, and any other wiring. Until they are
  done they are recorded as pending, not inferred.
- No package is installed; Bluesky and QCoDeS are compared from their
  documentation, not run, unless the owner decides otherwise.
- No full `./scripts/verify.sh` in a session.
