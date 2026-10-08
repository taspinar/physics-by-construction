"""A gas of hard discs in a square box: many agents, one local rule.

Each agent is a disc with a position and a velocity. Its only rules are
local: it moves in a straight line, it reverses the velocity component
normal to a wall it reaches, and when it touches another disc it collides
with it elastically (``pbc.mechanics.particles.hard_sphere_collision``, the
rule of the momentum and collisions lesson). Nothing in the rules mentions
pressure, temperature, or a distribution of speeds. The lesson measures
these from the whole, and compares them with kinetic theory.

The program steps time by a fixed ``dt``. After every step it finds the
pairs of discs that overlap and approach each other, and collides them one
after the other. All randomness comes from a ``numpy.random.Generator``
that the caller creates from a seed, so a run is a function of its inputs.

Quantities are in SI units; the box is a square of side ``side`` metres in
two dimensions, so a "pressure" is a force per length, N/m, and the
temperature is expressed as the energy ``k_B T`` in joules.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from pbc.mechanics.particles import hard_sphere_collision

Array = NDArray[np.float64]

# The gas of the lesson: 200 discs of radius 7 mm in a box of side 1 m, all
# starting at 1 m/s, stepped by 2 ms, measured after 1.5 s of relaxation for
# 3.5 s. The packing fraction is 3 %, and a disc moves 2 mm per step, a seventh
# of its diameter.
N_DISCS = 200
RADIUS = 0.007
SIDE = 1.0
SPEED = 1.0
RELAX = 1.5
DURATION = 3.5
DT = 0.002
EVERY = 10


@dataclass(frozen=True)
class Gas:
    """The state of ``n`` identical discs: one row per disc.

    ``radius`` and ``mass`` are the same for every disc, ``side`` is the side
    of the box, and ``time`` the time reached.
    """

    positions: Array
    velocities: Array
    radius: float
    mass: float
    side: float
    time: float = 0.0

    @property
    def n(self) -> int:
        return self.positions.shape[0]

    @property
    def free_side(self) -> float:
        """The side of the square that the centres of the discs can reach:
        a disc touches a wall when its centre is one radius from it."""
        return self.side - 2.0 * self.radius

    @property
    def packing_fraction(self) -> float:
        """The area of the discs as a fraction of the area their centres
        can reach, the dimensionless density of the gas."""
        return self.n * np.pi * self.radius**2 / self.free_side**2


def initial_gas(
    n: int,
    radius: float,
    side: float,
    speed: float,
    rng: np.random.Generator,
    mass: float = 1.0,
) -> Gas:
    """``n`` discs at random places that do not overlap each other or the
    walls, moving in random directions with the root-mean-square ``speed``
    (m/s).

    Every disc is first given the same speed. The mean velocity is then
    removed and the velocities are rescaled, so the gas starts with zero
    total momentum and the kinetic energy of ``n`` discs at ``speed``.
    Removing the mean velocity changes the speed of each disc a little, so
    the start is a narrow band of speeds around ``speed``, not one speed,
    and not a Maxwell distribution; the lesson watches the collisions change
    that.
    """
    if radius <= 0 or side <= 0 or speed <= 0 or mass <= 0:
        raise ValueError("radius, side, speed, and mass must be positive")
    if n < 2:  # one disc cannot have zero momentum and a positive speed
        raise ValueError("n must be at least 2")
    if n * np.pi * radius**2 > 0.5 * side**2:
        raise ValueError("the discs fill more than half of the box")
    positions = _place_discs(n, radius, side, rng)
    angles = rng.uniform(0.0, 2.0 * np.pi, size=n)
    velocities = np.column_stack([np.cos(angles), np.sin(angles)])
    velocities -= velocities.mean(axis=0)
    velocities *= speed * np.sqrt(n / np.sum(velocities**2))
    return Gas(positions, velocities, radius, mass, side)


# Placement draws candidate centres in batches of n and keeps those that do
# not overlap a placed disc. A placement that has not finished after this many
# batches is abandoned and started again from no discs; after this many
# placements the discs are judged not to fit.
PLACEMENT_BATCHES = 100
PLACEMENT_RESTARTS = 100


def _place_discs(n: int, radius: float, side: float, rng: np.random.Generator) -> Array:
    """``n`` centres of discs that overlap neither each other nor the walls,
    or a ``ValueError`` when the bounded search does not find them.

    Discs are placed one by one and never moved, so an unlucky first disc
    can leave no room for the next; the search starts over when a placement
    stalls, and gives up after a fixed number of starts. A gas that fills
    much less than half of the box is placed at the first start.
    """
    for _ in range(PLACEMENT_RESTARTS):
        positions = np.empty((0, 2))
        for _ in range(PLACEMENT_BATCHES):
            candidates = rng.uniform(radius, side - radius, size=(n, 2))
            for candidate in candidates:
                gaps = np.hypot(*(positions - candidate).T)
                if len(positions) < n and np.all(gaps >= 2.0 * radius):
                    positions = np.vstack([positions, candidate])
            if len(positions) == n:
                return positions
    raise ValueError(
        f"could not place {n} discs of radius {radius} in a box of side {side} "
        "without overlap; use fewer or smaller discs"
    )


def step(gas: Gas, dt: float) -> tuple[Gas, float]:
    """Advance the gas by ``dt`` and return it with the impulse (N s) that the
    walls gave to the discs in that time.

    The discs drift; a disc that went through a wall is reflected back into
    the box, its normal velocity reversed, and the wall gives it the impulse
    2 m |v_normal|. Then every overlapping pair that is still approaching
    collides elastically.
    """
    x = gas.positions + gas.velocities * dt
    v = gas.velocities.copy()
    low, high = gas.radius, gas.side - gas.radius
    impulse = 0.0
    for axis in range(2):
        below, above = x[:, axis] < low, x[:, axis] > high
        x[below, axis] = 2.0 * low - x[below, axis]
        x[above, axis] = 2.0 * high - x[above, axis]
        hit = below | above
        impulse += 2.0 * gas.mass * np.sum(np.abs(v[hit, axis]))
        v[hit, axis] = -v[hit, axis]

    # Squared distances of all pairs; the upper triangle holds each pair once.
    dx = x[:, 0, np.newaxis] - x[np.newaxis, :, 0]
    dy = x[:, 1, np.newaxis] - x[np.newaxis, :, 1]
    close = np.triu(dx * dx + dy * dy < (2.0 * gas.radius) ** 2, k=1)
    first, second = np.nonzero(close)
    for i, j in zip(first, second, strict=True):
        r = x[i] - x[j]
        gap = np.hypot(*r)
        if (v[i] - v[j]) @ r < 0.0:  # still approaching: a collision
            v[i], v[j] = hard_sphere_collision(gas.mass, v[i], gas.mass, v[j], r / gap)
    return Gas(x, v, gas.radius, gas.mass, gas.side, gas.time + dt), impulse


@dataclass(frozen=True)
class Run:
    """What a run recorded.

    ``times`` are the times of the snapshots, ``speeds`` has one row of disc
    speeds per snapshot, and ``wall_impulse`` the total impulse the walls
    gave between one snapshot and the next (the first entry is the impulse
    since the start of the run).
    """

    times: Array
    speeds: Array
    wall_impulse: Array
    final: Gas


def run(gas: Gas, duration: float, dt: float, every: int = 1) -> Run:
    """Step the gas for ``duration`` seconds and record a snapshot of the
    speeds every ``every`` steps."""
    if dt <= 0 or duration <= 0 or every < 1:
        raise ValueError("dt and duration must be positive and every at least 1")
    n_steps = round(duration / dt)
    times, speeds, impulses = [], [], []
    accumulated = 0.0
    for k in range(1, n_steps + 1):
        gas, impulse = step(gas, dt)
        accumulated += impulse
        if k % every == 0:
            times.append(gas.time)
            speeds.append(np.hypot(*gas.velocities.T))
            impulses.append(accumulated)
            accumulated = 0.0
    return Run(np.array(times), np.array(speeds), np.array(impulses), gas)


def wall_pressure(impulse: float, duration: float, side: float) -> float:
    """The pressure (N/m) of a two-dimensional gas: the impulse the walls
    gave in ``duration`` seconds, per second and per length of the wall,
    4 ``side``. Pass the ``free_side`` of the gas, where the centres meet the
    walls, so that the pressure and the area of ``ideal_gas_pressure`` are
    those of the same square."""
    return impulse / (duration * 4.0 * side)


def temperature(speeds: Array, mass: float) -> float:
    """The energy k_B T (J) that goes with the speeds of a two-dimensional
    gas: the mean kinetic energy per disc, m <v²> / 2, is k_B T because
    each of the two directions holds k_B T / 2."""
    return float(0.5 * mass * np.mean(np.asarray(speeds) ** 2))


def ideal_gas_pressure(n: int, kt: float, side: float) -> float:
    """The pressure N k_B T / A (N/m) of an ideal gas of ``n`` points in a
    square of the given ``side`` (the ``free_side`` of a gas of discs)."""
    return n * kt / side**2


def virial_correction(packing_fraction: float) -> float:
    """The factor 1 + 2 phi by which the area of the discs raises the
    pressure of a dilute hard-disc gas above the ideal one (the second
    virial coefficient of hard discs). Valid for a small packing fraction
    phi."""
    return 1.0 + 2.0 * packing_fraction


def rayleigh_pdf(speed: Array, kt: float, mass: float) -> Array:
    """The probability density per m/s of the speed of a disc in a
    two-dimensional Maxwell distribution at k_B T = ``kt``:
    (m v / k_B T) exp(-m v² / (2 k_B T))."""
    v = np.asarray(speed, dtype=np.float64)
    return mass * v / kt * np.exp(-mass * v**2 / (2.0 * kt))


def speed_ratio(speeds: Array) -> float:
    """<v⁴> / <v²>²: 1 when every disc has the same speed, and exactly 2 for
    the two-dimensional Maxwell distribution, whatever the temperature."""
    v2 = np.asarray(speeds) ** 2
    return float(np.mean(v2**2) / np.mean(v2) ** 2)


@dataclass(frozen=True)
class Measurement:
    """What one seeded run says about the gas once it has relaxed.

    ``speeds`` are the speeds of all discs at all snapshots after the
    relaxation, ``kt`` the energy k_B T they give, ``pressure`` the pressure
    the walls measured over the same time, ``ideal_pressure`` the pressure
    N k_B T / A of ideal point particles at that temperature, and
    ``packing_fraction`` that of the gas.
    """

    speeds: Array
    kt: float
    pressure: float
    ideal_pressure: float
    packing_fraction: float


def measure(
    seed: int,
    n: int = N_DISCS,
    radius: float = RADIUS,
    side: float = SIDE,
    speed: float = SPEED,
    relax: float = RELAX,
    duration: float = DURATION,
    dt: float = DT,
    every: int = EVERY,
) -> Measurement:
    """Start a gas from ``seed``, let it relax for ``relax`` seconds, and
    measure it for the next ``duration`` seconds.

    The relaxation must take many collisions per disc. The mean free path
    of a disc is about 1 / (sqrt(2) n_A d) with n_A the discs per area and
    d = 2 ``radius``, so a disc collides about once per mean free path
    divided by its speed.
    """
    gas = initial_gas(n, radius, side, speed, np.random.default_rng(seed))
    recorded = run(gas, relax + duration, dt, every)
    measured = recorded.times > relax + 0.5 * every * dt
    if not measured.any():
        raise ValueError(
            "duration must cover at least one snapshot interval, every * dt, "
            "after relax"
        )
    window = np.count_nonzero(measured) * every * dt
    speeds = recorded.speeds[measured]
    impulse = recorded.wall_impulse[measured].sum()
    kt = temperature(speeds, gas.mass)
    return Measurement(
        speeds=speeds,
        kt=kt,
        pressure=wall_pressure(impulse, window, gas.free_side),
        ideal_pressure=ideal_gas_pressure(n, kt, gas.free_side),
        packing_fraction=gas.packing_fraction,
    )


def mean_and_error(values: Array) -> tuple[float, float]:
    """The mean of independent ``values`` and the standard error of that
    mean, s / sqrt(k) with s the sample standard deviation of k values."""
    v = np.asarray(values, dtype=np.float64)
    if v.size < 2:
        raise ValueError("a standard error needs at least two values")
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(v.size))
