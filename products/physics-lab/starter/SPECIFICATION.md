# Specification: the ring-down fit of the transient-response protocol

Written before the work starts, with the parts of
`docs/coding-agent-workflow.md`, section 1. The same text serves the manual
route: it is what you build, with or without an agent.

## Physics

A series RLC circuit at rest whose source steps to a constant voltage at
t = 0. If the circuit is underdamped, the capacitor voltage rings:

    v(t) = v_inf + e^(-alpha t) (a cos(omega_d t) + b sin(omega_d t))

with the decay rate alpha = R / (2 L) and the damped angular frequency
omega_d = sqrt(omega_0^2 - alpha^2). From the two fitted rates:

    f0 = sqrt(omega_d^2 + alpha^2) / (2 pi)      Q = omega_0 / (2 alpha)

## Assumptions

- The record is one ring-down of an underdamped circuit, sampled at
  increasing times, with additive noise of unknown, constant size.
- The step's size, the final voltage v_inf, and the time of the step are
  not known to the fit: the record may start after the step, and v_inf,
  a and b are free.
- The circuit's parts are not known to the fit. It may not take R, L, C,
  f0 or Q as an argument or import them.
- Nothing may be assumed about the sample rate except that it resolves
  the oscillation (at least 8 samples per period).

## Interface

File `my_lab/ringdown.py`. The dataclass `RingdownFit` is given; the work is
the body of

    fit_ringdown(t_s, v) -> RingdownFit

- `t_s`, `v`: one-dimensional sequences of equal length.
- Returns the fitted values and their standard errors. The standard errors
  come from the fit's residuals and its covariance; those of f0 and Q are
  propagated from alpha and omega_d, with their covariance.
- Raises `ValueError` when the lengths differ, when fewer than 16 samples
  are given, when a value is not finite, when the times do not increase,
  and when the record shows no oscillation (an overdamped or critically
  damped response, or a flat record).
- No global state, no printing, no files, no network. NumPy and SciPy may
  be used.

## Units

`t_s` in s, `v` in V. `decay_rate` and its standard error in 1/s,
`damped_frequency_hz` and `f0_hz` with theirs in Hz, `q` and its standard
error without unit.

## Claim

On the simulated bench circuit (f0 about 5.03 kHz, Q about 3.16), with
2,000 samples over 2 ms: without noise f0 within 0.1 % and Q within 0.5 %;
with noise of 1 % of the step, f0 and Q within their stated standard
errors as often as a calibrated standard error predicts.

## Tests the result must pass

    uv run pytest tests/test_ringdown.py

The named tests of `tests/test_ringdown.py`. Each compares the fit with the
closed-form step response of a circuit the fit never sees.

## Not allowed

- Changing `tests/`, `SPECIFICATION.md`, the dataclass `RingdownFit`, or
  the signature of `fit_ringdown`.
- Importing `pbc.electromagnetism.circuits`, `pbc.instruments.simulated`,
  or anything else that holds the circuit, in `my_lab/ringdown.py`.
- Adding a dependency.
