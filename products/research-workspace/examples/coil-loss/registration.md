Registration: F155 (Issue #619), the coil-loss follow-up of `ad3-rlc-pilot`.
It is frozen when this text is on `main` after the owner's approving review
of the exact head of the pull request that merges it (part 0); its sha256
is recorded after the end marker.

Circuit. The pilot's circuit of F140 on the breadboard, with the same
physical parts if they can be identified: W1 -> 100 ohm resistor -> 1 mH
inductor -> node A -> 10 nF capacitor -> ground. Scope 1- and 2- at
ground. The live input `products/physics-lab/examples/live-pilot.toml`,
unchanged (1 V, 5 kHz to 200 kHz, 13 coarse log-spaced points, channel 1
on the 5 V range, channel 2 on the 50 V range). Close WaveForms first.

Measurements, in this order, all after the freeze (one capacitor sweep
with this input was made before it, as a diagnostic that no rule reads:
see "Known before the freeze"):
Before M0 the owner reads the room temperature, and it is recorded with
its time and the instrument read. The time at which the AD3 was plugged
in is recorded, and M0 starts no earlier than 45 minutes after it. The
wait limits the strongest early movement seen in the campaigns of F145;
their crossing still moved after 45 minutes (by about 1 % up to 89
minutes), nothing shows that the circuit or the AD3 is stable after
the wait, and the cause of the movement is not known. Every sweep keeps its run record with
the input, the channel ranges, and the device's conditions at its start
and end (board temperature, USB voltage and current). No rule reads
these.
M0. Conditioning sweep, registered here as the first measurement: one
    capacitor sweep, wired as M1. No rule reads it. Its raw data and its
    run record are kept in full, as for M1, and the difference of M1 from
    M0 is reported: the -90 degree crossing and the phase at each of the
    13 coarse frequencies. M0 replaces nothing: M1 is the sweep made
    directly after M0, whatever either shows, and no sweep of M0 to M5
    is left out, repeated, or exchanged because of its result (a failed
    run is the case of "Stopping" below).
M1. Capacitor sweep: scope 1+ at W1, 2+ at node A (as pilot run 2).
M2. R-L node sweep: scope 1+ at W1, 2+ at the R-L node (as pilot run 3).
M3. Same-node sweep: scope 1+ and 2+ both at W1. The physics lab reports
    no -90 degree crossing and an inconclusive run; its raw samples at the
    13 coarse frequencies are the measurement.
M4. Output off, USB unplugged. Lift one lead of the capacitor and one of
    the resistor out of the breadboard. With the owner's multimeter, the
    Mastech MAS830BC (manual ranging, 3 1/2 digits, 1999 counts), two
    wire, on its 200 ohm range (resolution q = 0.1 ohm) for every
    reading of M4; a part whose reading overloads that range is read on
    the 2 kohm range (q = 1 ohm), and its offset then does not cancel
    (below): Z1, the leads shorted (three readings), before any part;
    the inductor across its two breadboard rows (three readings, R_dc_bb);
    the inductor out of the breadboard (three readings, R_dc); the
    resistor across its two breadboard rows with the inductor lifted
    (three readings, R_s_bb); Z2, the leads shorted again (three
    readings), after the last part. Recorded per reading: the value, the
    range, the resolution on that range (the step of the last digit), the
    meter's make and model, the registered specification on that range
    (below), the time. The meter has no capacitance range: no capacitance
    reading is made, and G3 is dropped.
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
    p the percent of reading, n the digits, registered as p = 0.8 % and
    n = 3 on the 200 ohm range and, an assumption named, on the 2 kohm
    range. These are the values of the resistance table of the manual of
    the Mastech MAS830B for its 200 ohm range (resolution 0.1 ohm), read
    by the owner on 2026-11-25. That manual names only the MAS830B: the
    owner has no manual of this meter, the MAS830BC, no table of the BC
    variant was found, and the meter is not calibrated. A third party's
    summary of the MAS830B gives 1.2 % + 3 digits; nobody read it at its
    source, and it is reported as a sensitivity (u recomputed with
    p = 1.2 %) that decides no outcome.
    a is read as the half-width of a rectangular distribution: a standard
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
without u_gain(X).

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

G3 (the capacitance) is dropped: the meter has no capacitance range (the
owner's answer of 2026-11-25). It is not evaluated and not reported as
inconclusive; the question stays in the archive, deferred.

Known before the freeze. The bench session of F145 (Issue #614) ran on
this circuit before this text was frozen: twenty-seven campaigns of the
physics lab with `products/physics-lab/examples/live-campaign-series-rlc.toml`,
three on the evening of 2026-11-25 and twenty-four between 13:14 and
14:39 on 2026-11-26 (the AD3 plugged in at about 13:10, the room at about
20 degrees C; the room was not measured on the evening or at the pilot).
By the owner's statement the parts are the pilot's and the circuit was
not changed since 2026-11-22. One diagnostic sweep with this
registration's input (`live-pilot.toml`, scope 2+ at node A, as pilot
run 2) was made at 13:36 on 2026-11-26, by the owner's decision of that
day, to compare like with like. All these data are kept. None of them is
M0 or M1, and no rule of this registration reads them.
  Comparable with the pilot's capacitor sweep: the diagnostic sweep in
  everything the run record states (the input, the node, the channel
  ranges, the device and SDK). The campaigns in the node, 1 V, the 13
  coarse frequencies with 8 periods of 64 samples each, the channel
  ranges, the device and SDK; not in the program (an adaptive route and
  ring-downs), and they record no device conditions. Observed: one
  campaign made 25 seconds after the diagnostic sweep agrees with it to
  0.1 % in the crossing. That is one pair; it does not show that the
  program has no influence. The pilot's sweep ran about 35 minutes after the AD3 was
  plugged in, its board at 48.2 degrees C; the diagnostic sweep 26
  minutes after, its board at 44.0 degrees C.
  What they showed: the diagnostic sweep has f0 48,927 Hz and Q 1.50,
  where the pilot's run record has 47,009 Hz and 1.55; at the common
  frequency 43.0 kHz its phase is -69.2 degrees, the pilot's -74.9. The
  -90 degree crossing of the campaigns moved during the session of
  2026-11-26: 49.99 kHz at 5 minutes after the plug-in, 49.52 to
  49.58 kHz at about 8 minutes (ten campaigns six seconds apart), 48.87 kHz
  at 27 minutes, a lowest 48.46 kHz at 43 minutes, then rising to
  48.92 kHz at 89 minutes. The three of the evening read 50.18, 49.83,
  and 49.67 kHz within seven minutes. The pilot's two capacitor sweeps,
  minutes apart, agreed to 5 Hz. No campaign read below 48.4 kHz. The
  two protocols of a campaign agree on f0 and give different Q (1.47 to
  1.49 from the sweep, 1.63 to 1.68 from the ring-down).
  What this does not establish: that a part changed, or why the crossing
  moves during a session. The differences are of the circuit as measured
  (the parts, the breadboard, the leads, and the instrument together).
  No cause is known, and none is assigned or proposed here. Every sweep
  named above had scope 2+ at node A, the capacitor's node. Not made: a
  multimeter reading of a part, a sweep with scope 2+ at the R-L node
  (M2), and a sweep with both scope inputs at W1 (M3).
  What follows for this registration: nothing in its rules. No rule and
  no threshold was changed after these measurements, the precondition
  (identity of the parts) included: if M2 differs from pilot run 3 as
  that rule says, its stated consequence applies. Four steps of the
  procedure were added because of them, all stated here as added after
  seeing these data. Two change how the session runs: the wait of 45
  minutes after the plug-in, and M0. Their reason: P compares the phases
  of M1 with a model from M2, and a circuit that moves between the two
  sweeps would add a phase residual that no correction of the channels
  removes. Two only record, and no rule reads them: the room temperature
  with the time of the plug-in, and the device's conditions kept with
  every sweep. M5 against M2 reports what movement remained.

Withheld part. M1 to M5 are the confirmatory measurements; the pilot's data
chose the thresholds. The analysis code that computes the outcomes is
merged into `main` (part 2) before M1 is made, with its code identity
recorded in the log; that identity covers every module that computes an
outcome or applies a rule. A change of that code after M1 is recorded as a
deviation, and its result is exploratory.

Stopping. One bench session. A failed run (an invalid capture, a refused
output) is repeated once and both are kept; a second failure stops the
session, and the follow-up is inconclusive with its reasons.

Success. The follow-up succeeds when every measurement is recorded with its
raw data and every outcome is computed by the registered rule, whatever the
outcome. An outcome that decides nothing is a result, reported as
inconclusive.
