# M4, first attempt: invalid (the meter was not on a resistance range)

Session of 2026-11-28, Mastech MAS830BC. The owner read fifteen values with
the dial on 200 mV (DC voltage) instead of 200 ohm; the owner found this
after the last reading. Every value is 0.0 and none is a resistance. They
are kept here as read, used by no rule, and replaced by a second attempt on
the 200 ohm range (the registration allows one repeat of a failed run).

| Quantity | Reading 1 | Reading 2 | Reading 3 | Time (local, +01:00) |
|---|---|---|---|---|
| Z1 | 0.0 | 0.0 | 0.0 | 07:51 |
| R_dc_bb | 0.0 | 0.0 | 0.0 | 07:54 |
| R_dc | 0.0 | 0.0 | 0.0 | 07:55 |
| R_s_bb | 0.0 | 0.0 | 0.0 | 07:57 |
| Z2 | 0.0 | 0.0 | 0.0 | 07:58 |

During this attempt the parts were handled as M4 prescribes: one lead of
the capacitor (a20) and one of the resistor (c10) lifted, the inductor
taken out, the resistor put back in c10 and c15. For the second attempt the
inductor goes back in d15 and d20 and the resistor's lead in c10 is lifted
again, so the parts are seated one more time than registered.

## Second attempt (the readings of readings.toml)

Dial on the 200 ohm range, as the owner reports. Read at 08:13 to 08:20.
The owner's note at R_s_bb: the display "fluctuated a lot". The values are
recorded as read. They are not consistent with a 100 ohm resistor (R_s_bb
minus the zero is about 3 ohm) and the zero moved from 3.9 to 6.4 ohm; no
cause is established. No third attempt is made in the registered session.

## Second attempt (the readings of readings.toml)

Dial on the 200 ohm range, as the owner reports. Read at 08:13 to 08:20.
The owner's note at R_s_bb: the display "fluctuated a lot". The values are
recorded as read. They are not consistent with a 100 ohm resistor (R_s_bb
minus the zero is about 3 ohm) and the zero moved from 3.9 to 6.4 ohm; no
cause is established. No third attempt is made in the registered session.
