"""Projectile motion in a vertical plane: launch, flight until landing, and
the range.

The plane has x horizontal in the direction of the throw and y upward, both
in metres; the ground is y = 0. A flight is simulated with the stepping
interface of ``pbc.mechanics.dynamics`` under the weight and quadratic drag
of ``pbc.mechanics.drag``, with explicit Euler unless another stepper is
given. There is no closed form for this motion; the drag-free range is given
for the limiting case.

Angles are in degrees above the horizontal, speeds in m/s, masses in kg, the
drag constant in kg/m, and the time step in s.
"""

from dataclasses import dataclass

import numpy as np
from scipy.constants import g as STANDARD_GRAVITY  # 9.80665 m/s²

from pbc.mechanics.drag import quadratic_drag
from pbc.mechanics.dynamics import (
    Acceleration,
    State,
    Stepper,
    Trajectory,
    euler_step,
    newton,
    simulate,
    weight,
)


def launch(speed: float, angle: float, height: float = 0.0) -> State:
    """The state at the moment of launch, at time 0.

    ``speed`` is in m/s, ``angle`` in degrees above the horizontal, and
    ``height`` the height above the ground in m.
    """
    if speed < 0:
        raise ValueError(f"speed must not be negative, got {speed}")
    radians = np.radians(angle)
    return State(
        t=0.0,
        x=[0.0, height],
        v=[speed * np.cos(radians), speed * np.sin(radians)],
    )


def fly(
    initial: State,
    acceleration: Acceleration,
    dt: float,
    step: Stepper = euler_step,
    max_steps: int = 1_000_000,
) -> Trajectory:
    """Simulate from ``initial`` in steps of ``dt`` (s) until the particle has
    come down to the ground.

    The trajectory ends with the first state below the ground (y < 0), so
    that ``landing`` can interpolate the crossing. Raises ``RuntimeError``
    when the particle has not landed after ``max_steps`` steps.
    """

    def below_ground(state: State) -> bool:
        return state.x[1] < 0.0

    trajectory = simulate(initial, acceleration, dt, max_steps, step, below_ground)
    if trajectory.x[-1, 1] >= 0.0:
        raise RuntimeError(f"not landed after {max_steps} steps of {dt} s")
    return trajectory


@dataclass(frozen=True)
class Landing:
    """Where and when a flight meets the ground."""

    t: float  # time of flight, s
    x: float  # horizontal distance travelled, m: the range


def landing(trajectory: Trajectory) -> Landing:
    """The landing point of a flight, interpolated linearly between the last
    state above the ground and the first below it.

    ``trajectory`` is the result of ``fly``: its last state is the first one
    below the ground, and the state before it is on or above the ground.
    """
    y = trajectory.x[:, 1]
    if len(y) < 2 or y[-1] >= 0.0 or y[-2] < 0.0:
        raise ValueError(
            "the trajectory does not end with its first state below the ground;"
            " simulate the flight with fly()"
        )
    fraction = y[-2] / (y[-2] - y[-1])  # of the last step, until the crossing
    t = trajectory.t[-2] + fraction * (trajectory.t[-1] - trajectory.t[-2])
    x = trajectory.x[-2, 0] + fraction * (trajectory.x[-1, 0] - trajectory.x[-2, 0])
    return Landing(t=float(t), x=float(x))


def projectile_range(
    speed: float,
    angle: float,
    mass: float,
    drag: float,
    dt: float,
    *,
    height: float = 0.0,
    g: float = STANDARD_GRAVITY,
    step: Stepper = euler_step,
) -> float:
    """The horizontal distance in m a projectile travels before it lands.

    The projectile of ``mass`` (kg) is launched at ``speed`` (m/s) and
    ``angle`` (degrees above the horizontal) from ``height`` (m) above flat
    ground, under gravity ``g`` (m/s², downward) and quadratic drag with the
    constant ``drag`` (kg/m; 0 for no drag). The flight is simulated in time
    steps of ``dt`` (s) with the stepper ``step``, explicit Euler by default,
    and the landing point is interpolated within the last step. The result
    depends on ``dt``: with explicit Euler its error is proportional to
    ``dt``, so halve ``dt`` until the digits you need stop changing.
    """
    acceleration = newton(mass, weight(mass, [0.0, -g]), quadratic_drag(drag))
    return landing(fly(launch(speed, angle, height), acceleration, dt, step)).x


def drag_free_range(speed: float, angle: float, g: float = STANDARD_GRAVITY) -> float:
    """The exact range in m without drag, for a launch from the ground:
    v² sin(2 theta) / g, with ``speed`` v in m/s, ``angle`` theta in degrees,
    and gravity ``g`` in m/s²."""
    return speed**2 * np.sin(np.radians(2.0 * angle)) / g
