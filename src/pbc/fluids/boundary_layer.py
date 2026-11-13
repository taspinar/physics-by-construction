"""The boundary layer on a flat plate: the laminar Blasius layer, the
integral thicknesses, and the law of the wall of a turbulent layer.

Next to a wall the incompressible Navier-Stokes equations of the lesson
"Navier-Stokes fundamentals" simplify when the layer is thin, steady, and
two-dimensional (Prandtl's boundary layer). On a flat plate without a
pressure gradient they become, with the stream function
psi = sqrt(nu x U) f(eta) and eta = y sqrt(U / (nu x)), the Blasius equation

    f''' + f f'' / 2 = 0,   f(0) = f'(0) = 0,   f'(inf) = 1,

whose solution f'(eta) = u / U is the laminar layer at every station x.
``blasius`` solves it by shooting: a classical fourth-order Runge-Kutta
march from the wall, with the wall curvature f''(0) found by the scaling
the equation admits (Toepfer), not by a search.

A turbulent layer has no such solution. Its mean velocity near the wall
depends on the friction velocity u_tau = sqrt(tau_w / rho) and the viscous
length nu / u_tau: U+ = U / u_tau against y+ = y u_tau / nu follows U+ = y+
in the viscous sublayer and, further out, the log law
U+ = ln(y+) / kappa + B, with constants that only a measurement gives.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


def _blasius_rhs(f: Array) -> Array:
    """(f, f', f'')' for the Blasius equation f''' = -f f'' / 2."""
    return np.array([f[1], f[2], -0.5 * f[0] * f[2]])


def _march(curvature: float, eta_max: float, steps: int) -> Array:
    """f, f', f'' on a uniform grid from the wall, by classical RK4."""
    h = eta_max / steps
    out = np.empty((steps + 1, 3))
    out[0] = (0.0, 0.0, curvature)
    for n in range(steps):
        f = out[n]
        k1 = _blasius_rhs(f)
        k2 = _blasius_rhs(f + 0.5 * h * k1)
        k3 = _blasius_rhs(f + 0.5 * h * k2)
        k4 = _blasius_rhs(f + h * k3)
        out[n + 1] = f + h / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return out


@dataclass(frozen=True)
class Blasius:
    """The laminar flat-plate layer in the similarity variable eta."""

    eta: Array  # y sqrt(U / (nu x))
    u: Array  # u / U = f'(eta)
    wall_curvature: float  # f''(0)
    eta99: float  # where u / U = 0.99
    displacement: float  # delta* / sqrt(nu x / U)
    momentum: float  # theta / sqrt(nu x / U)

    @property
    def shape_factor(self) -> float:
        return self.displacement / self.momentum


def blasius(eta_max: float = 10.0, steps: int = 2000) -> Blasius:
    """Solve the Blasius equation by shooting, with Toepfer's scaling in
    place of a search. March g''' + g g'' / 2 = 0 from the wall with
    g''(0) = 1 until g' has settled at a constant lambda. Then
    f(eta) = c g(c eta) with c = lambda^(-1/2) solves the same equation with
    f'(inf) = 1, so the wall curvature is f''(0) = lambda^(-3/2). The profile
    is marched again with that curvature; the thicknesses are the trapezoid
    integrals of 1 - f' and f' (1 - f') over its grid."""
    settled = _march(1.0, 2.0 * eta_max, 2 * steps)[-1, 1]
    curvature = float(settled**-1.5)
    f = _march(curvature, eta_max, steps)
    eta = np.linspace(0.0, eta_max, steps + 1)
    u = f[:, 1]
    return Blasius(
        eta,
        u,
        curvature,
        thickness_99(eta, u),
        float(np.trapezoid(1.0 - u, eta)),
        float(np.trapezoid(u * (1.0 - u), eta)),
    )


def laminar_layer(solution: Blasius, speed: float, nu: float, x: float) -> dict:
    """The laminar layer at distance ``x`` (m) from the leading edge of a
    plate in a stream of ``speed`` (m/s) and kinematic viscosity ``nu``
    (m^2/s): Re_x, delta_99, delta*, theta (m), and the skin friction
    C_f = tau_w / (rho U^2 / 2) = 2 f''(0) / sqrt(Re_x)."""
    scale = np.sqrt(nu * x / speed)
    re_x = speed * x / nu
    return {
        "Re_x": float(re_x),
        "delta99": float(solution.eta99 * scale),
        "displacement": float(solution.displacement * scale),
        "momentum": float(solution.momentum * scale),
        "skin_friction": float(2.0 * solution.wall_curvature / np.sqrt(re_x)),
    }


def integral_thicknesses(
    y: Array, u: Array, delta: float
) -> tuple[float, float, float]:
    """delta*, theta, and H = delta* / theta of the profile u / U (``u``)
    against the wall distance ``y``, by the trapezoid rule from the first
    point to ``delta``; the profile has to begin at the wall."""
    inside = y <= delta
    displacement = float(np.trapezoid((1.0 - u)[inside], y[inside]))
    momentum = float(np.trapezoid((u * (1.0 - u))[inside], y[inside]))
    return displacement, momentum, displacement / momentum


def thickness_99(y: Array, u: Array) -> float:
    """delta_99: the wall distance where u / U first reaches 0.99, linear
    between the two points around it (``y`` increasing)."""
    k = int(np.argmax(u >= 0.99))
    if k == 0:
        raise ValueError(
            "the profile does not cross u / U = 0.99 above its first point"
        )
    return float(y[k - 1] + (0.99 - u[k - 1]) / (u[k] - u[k - 1]) * (y[k] - y[k - 1]))


def sublayer(yplus: Array) -> Array:
    """U+ = y+: the viscous sublayer, where the viscous stress carries the
    wall shear stress alone."""
    return np.asarray(yplus, dtype=float)


def log_law(yplus: Array, kappa: float, b: float) -> Array:
    """U+ = ln(y+) / kappa + B: the overlap layer of a turbulent wall flow."""
    return np.log(yplus) / kappa + b


def coles_fernholz_friction(speed: float, re_theta: float) -> float:
    """u_tau (m/s) from the empirical skin friction of a zero-pressure-gradient
    turbulent layer, C_f = 2 [ln(Re_theta) / 0.384 + 4.127]^-2 (Nagib,
    Chauhan, and Monkewitz 2007), and u_tau = U sqrt(C_f / 2)."""
    cf = 2.0 * (np.log(re_theta) / 0.384 + 4.127) ** -2
    return float(speed * np.sqrt(cf / 2.0))
