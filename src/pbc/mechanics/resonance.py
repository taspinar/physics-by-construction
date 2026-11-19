"""The damped, driven oscillator and its resonance curve.

A mass on a spring with linear drag and a sinusoidal driving force obeys

    m x'' + b x' + k x = F₀ cos(Ω t).

After the transient has died away, the mass moves at the driving frequency
with the amplitude and phase lag that this module gives in closed form; the
amplitude as a function of Ω is the resonance curve, with its peak near the
natural frequency, its width set by the damping, and the quality factor Q as
the ratio of the two. The full motion from any start, transient included, is
also known in closed form for underdamped motion, so a simulation can be
checked at every instant, and the measured resonance curve can be checked
against the amplitude formula.

This module owns the verified reference solution of the damped driven
oscillator: the course lesson on resonance (M12) and the coding-agent exercise
that builds the same simulation reuse it.

Quantities are in SI units: masses in kg, ``k`` in N/m, ``b`` in kg/s, the
force amplitude in N, angular frequencies in rad/s, amplitudes in m.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.drag import linear_drag
from pbc.mechanics.dynamics import (
    Force,
    State,
    Stepper,
    Trajectory,
    Vector,
    newton,
    simulate,
)
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.oscillator import spring


def _check(mass: float, k: float, b: float) -> None:
    if mass <= 0 or k <= 0:
        raise ValueError("the mass and the spring constant must be positive")
    if b < 0:
        raise ValueError(f"the damping constant must not be negative, got {b}")


def driving_force(amplitude: float, omega: float) -> Force:
    """The force F₀ cos(Ω t) in N, with the ``amplitude`` F₀ (N) and the
    angular frequency ``omega`` Ω (rad/s), along every coordinate."""

    def force(t: float, x: Vector, v: Vector) -> Vector:
        return np.full_like(x, amplitude * np.cos(omega * t))

    return force


def natural_frequency(mass: float, k: float) -> float:
    """The undamped angular frequency ω₀ = sqrt(k / m) in rad/s."""
    _check(mass, k, 0.0)
    return float(np.sqrt(k / mass))


def damping_rate(mass: float, b: float) -> float:
    """The decay rate gamma = b / (2 m) in 1/s of the amplitude of free motion."""
    return b / (2.0 * mass)


def quality_factor(mass: float, k: float, b: float) -> float:
    """The quality factor Q = ω₀ / (2 gamma) = sqrt(k m) / b of the oscillator: the
    number of radians of free motion over which the energy falls by a factor
    of e, and, for weak damping, the peak frequency over the peak's width."""
    _check(mass, k, b)
    if b == 0:
        return float("inf")
    return float(np.sqrt(k * mass) / b)


def steady_state_amplitude(
    mass: float, k: float, b: float, force: float, omega: ArrayLike
) -> NDArray[np.float64]:
    """The amplitude in m of the motion at the driving frequency ``omega``
    (rad/s) after the transient, for the force amplitude ``force`` (N):
    (F₀ / m) / sqrt((ω₀² - Ω²)² + 4 gamma² Ω²)."""
    _check(mass, k, b)
    omega = np.asarray(omega, dtype=np.float64)
    w0sq, gamma = k / mass, damping_rate(mass, b)
    return (force / mass) / np.sqrt((w0sq - omega**2) ** 2 + 4.0 * gamma**2 * omega**2)


def steady_state_phase(
    mass: float, k: float, b: float, omega: ArrayLike
) -> NDArray[np.float64]:
    """The phase lag δ in rad, between 0 and π, of the motion behind the
    driving force: x = A cos(Ω t - δ). It is 0 for slow driving, π/2 at the
    natural frequency, and approaches π for fast driving."""
    _check(mass, k, b)
    omega = np.asarray(omega, dtype=np.float64)
    return np.arctan2(2.0 * damping_rate(mass, b) * omega, k / mass - omega**2)


def peak_frequency(mass: float, k: float, b: float) -> float:
    """The driving frequency in rad/s at which the amplitude is largest:
    sqrt(ω₀² - 2 gamma²), a little below the natural frequency. For damping so
    strong that 2 gamma² ≥ ω₀² the amplitude only falls, and the peak is at 0."""
    _check(mass, k, b)
    value = k / mass - 2.0 * damping_rate(mass, b) ** 2
    return float(np.sqrt(value)) if value > 0 else 0.0


def driven_motion(
    initial: State,
    mass: float,
    k: float,
    b: float,
    force: float,
    omega: float,
    t: ArrayLike,
) -> Trajectory:
    """The exact motion of the underdamped driven oscillator (b below
    2 sqrt(k m)) from the one-dimensional ``initial`` state, at the times
    ``t`` (s), on the same clock as ``initial.t`` and as ``driving_force``: the
    steady state plus the decaying free motion that fits the initial position
    and velocity."""
    _check(mass, k, b)
    gamma, w0sq = damping_rate(mass, b), k / mass
    if gamma**2 >= w0sq:
        raise ValueError("the closed form is for underdamped motion, b < 2 sqrt(k m)")
    wd = np.sqrt(w0sq - gamma**2)
    amp = float(steady_state_amplitude(mass, k, b, force, omega))
    delta = float(steady_state_phase(mass, k, b, omega))
    x0, v0 = float(initial.x[0]), float(initial.v[0])
    phase0 = omega * initial.t - delta
    c1 = x0 - amp * np.cos(phase0)
    c2 = (v0 + amp * omega * np.sin(phase0) + gamma * c1) / wd
    times = np.asarray(t, dtype=np.float64)
    t = times - initial.t
    decay = np.exp(-gamma * t)
    free, free_rate = (
        c1 * np.cos(wd * t) + c2 * np.sin(wd * t),
        -wd * c1 * np.sin(wd * t) + wd * c2 * np.cos(wd * t),
    )
    x = amp * np.cos(omega * times - delta) + decay * free
    v = -amp * omega * np.sin(omega * times - delta) + decay * (
        free_rate - gamma * free
    )
    return Trajectory(t=times, x=x[:, None], v=v[:, None])


def simulate_driven(
    initial: State,
    mass: float,
    k: float,
    b: float,
    force: float,
    omega: float,
    dt: float,
    n_steps: int,
    step: Stepper = rk4_step,
) -> Trajectory:
    """The motion of the damped driven oscillator from the one-dimensional
    ``initial`` state, simulated in ``n_steps`` steps of ``dt`` (s): the
    spring ``k`` (N/m), the linear drag ``b`` (kg/s), and the driving force
    of amplitude ``force`` (N) and angular frequency ``omega`` (rad/s) on the
    ``mass`` (kg), with the classical Runge-Kutta method unless another
    ``step`` is given. The driving force is on the clock of ``initial.t``."""
    _check(mass, k, b)
    return simulate(
        initial,
        newton(mass, spring(k), linear_drag(b), driving_force(force, omega)),
        dt,
        n_steps,
        step=step,
    )


def fit_amplitude(
    trajectory: Trajectory, omega: float, after: float
) -> tuple[float, float]:
    """The amplitude (m) and phase lag (rad) of the motion at ``omega``
    (rad/s), by least squares of x ≈ a cos Ω t + c sin Ω t over the instants
    after the time ``after`` (s), when the transient has died away:
    x = A cos(Ω t - δ) with A = sqrt(a² + c²) and δ = atan2(c, a)."""
    late = trajectory.t >= after
    t, x = trajectory.t[late], trajectory.x[late, 0]
    basis = np.column_stack([np.cos(omega * t), np.sin(omega * t)])
    (a, c), *_ = np.linalg.lstsq(basis, x, rcond=None)
    return float(np.hypot(a, c)), float(np.arctan2(c, a))


def measured_resonance_curve(
    mass: float,
    k: float,
    b: float,
    force: float,
    omegas: ArrayLike,
    steps_per_period: int = 100,
    decay_times: float = 10.0,
    fit_periods: int = 10,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """The amplitude in m and the phase lag in rad at each driving frequency
    of ``omegas`` (rad/s), measured on a simulation with the classical
    Runge-Kutta method.

    Each run starts at rest and lasts ``decay_times`` decay times of the free
    motion (so the transient is below e to the power minus ``decay_times``)
    rounded up to a whole number of driving periods, then ``fit_periods``
    periods more, over which the amplitude is fitted; ``steps_per_period``
    steps resolve one driving period.
    """
    _check(mass, k, b)
    amplitudes, phases = [], []
    for omega in np.asarray(omegas, dtype=np.float64):
        period = 2.0 * np.pi / omega
        settle = np.ceil(decay_times / damping_rate(mass, b) / period) * period
        dt = period / steps_per_period
        n_steps = round((settle + fit_periods * period) / dt)
        run = simulate_driven(
            State(t=0.0, x=[0.0], v=[0.0]), mass, k, b, force, omega, dt, n_steps
        )
        amplitude, phase = fit_amplitude(run, omega, settle)
        amplitudes.append(amplitude)
        phases.append(phase)
    return np.array(amplitudes), np.array(phases)


def half_power_width(omegas: ArrayLike, amplitudes: ArrayLike) -> float:
    """The width in rad/s of a resonance curve at half of its peak power,
    where the power is proportional to the amplitude squared, by linear
    interpolation between the samples on either side of the peak. The curve
    must fall below half power on both sides of the highest sample."""
    omegas = np.asarray(omegas, dtype=np.float64)
    power = np.asarray(amplitudes, dtype=np.float64) ** 2
    peak = int(np.argmax(power))
    half = power[peak] / 2.0
    below, above = power[: peak + 1], power[peak:]
    if below.min() >= half or above.min() >= half:
        raise ValueError("the curve does not fall below half power on both sides")
    left = int(np.where(below < half)[0][-1])
    right = peak + int(np.where(above < half)[0][0])
    low = np.interp(
        half, [power[left], power[left + 1]], [omegas[left], omegas[left + 1]]
    )
    high = np.interp(
        half, [power[right], power[right - 1]], [omegas[right], omegas[right - 1]]
    )
    return float(high - low)
