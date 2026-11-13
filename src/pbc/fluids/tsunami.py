"""The two-dimensional shallow-water equations on a grid of cells (capstone
FL10): the HLL flux and the hydrostatic reconstruction of FL5
(``pbc.fluids.shallow_water``) through the faces of a rectangular grid, in a
plane or on a sphere.

The state of a cell is (h, h u, h v): the depth (m) and the two depth-averaged
momenta (m^2/s), u to the east (x) and v to the north (y). Each face is a
one-dimensional Riemann problem across it: the HLL flux of FL5 gives the mass
and the momentum normal to the face, and the momentum along the face is
carried by the mass flux with the velocity of the upstream side. A cell
changes by what flows through its four faces, each flux times the length of
its face, divided by the cell's area, as in the finite volumes of FL9:

    q <- q - dt / A (F_e L_e - F_w L_w + G_n L_n - G_s L_s) + dt S.

On a sphere of radius R a cell between the longitudes lambda +- d lambda / 2
and the latitudes phi +- d phi / 2 has the area R^2 d lambda (sin phi_n - sin
phi_s); its east and west faces have the length R d phi, its north and south
faces R cos(phi) d lambda. The faces of one cell differ in length, so the
pressure g h^2 / 2 on its north and south faces does not cancel even when the
water is at rest; the source of the hydrostatic reconstruction, taken with the
same face lengths, cancels it exactly (``fluxes_and_source``). The momentum
terms of the curvature, of order u^2 / R, are left out; the Coriolis force
f k x (h u, h v), with f = 2 Omega sin(phi), is a source that can be switched
on.

The source of a tsunami is an initial state: the sea floor is lifted by the
vertical displacement ``uplift`` at once, the water column keeps its depth, so
the sea surface is lifted by the same amount (``initial_state``).
"""

from dataclasses import dataclass, field, replace

import numpy as np

from pbc.fluids.finite_volume import Array
from pbc.fluids.shallow_water import GRAVITY, hll_flux

__all__ = [
    "EARTH_RADIUS",
    "LIMITERS",
    "OMEGA",
    "WET",
    "Gauge",
    "Grid",
    "Run",
    "coarsen",
    "fluxes_and_source",
    "initial_state",
    "minmod",
    "monotonized_central",
    "plane_grid",
    "simulate",
    "sphere_grid",
    "surface",
    "time_step",
]

EARTH_RADIUS = 6371.0e3  # m, mean radius
OMEGA = 7.2921e-5  # rad/s, the Earth's rotation
# Below this depth (m) a cell's water carries no momentum: a film left on
# land by the reconstruction would otherwise get any velocity.
WET = 1e-3


@dataclass(frozen=True)
class Grid:
    """A rectangular grid of ``bed.shape`` = (ny, nx) cells, row 0 southmost.

    ``bed`` is the height of the bed (m, positive up, sea level 0) at each
    cell; ``east`` (ny,) the length of the east and west faces of each row,
    ``north`` (ny + 1,) the length of the faces between rows, the first south
    of row 0; ``area`` (ny,) the area of a cell of each row; ``width`` (ny,)
    and ``height`` the distances between neighbouring cells in x and in y
    (m), for the CFL condition; ``coriolis`` (ny,) the parameter f of each
    row (1/s), zero in a plane; ``lat`` and ``lon`` (degrees) the centres,
    or ``None`` in a plane."""

    bed: Array
    east: Array
    north: Array
    area: Array
    width: Array
    height: float
    coriolis: Array
    lat: Array | None = None
    lon: Array | None = None

    @property
    def shape(self) -> tuple[int, int]:
        return self.bed.shape

    def volume(self, h: Array) -> float:
        """The volume of water (m^3) of the depths ``h``."""
        return float(np.sum(h * self.area[:, None]))


def plane_grid(bed: Array, dx: float, dy: float) -> Grid:
    """A plane grid of cells ``dx`` by ``dy`` (m), without rotation."""
    ny, _ = bed.shape
    return Grid(
        bed=np.asarray(bed, dtype=float),
        east=np.full(ny, dy),
        north=np.full(ny + 1, dx),
        area=np.full(ny, dx * dy),
        width=np.full(ny, dx),
        height=dy,
        coriolis=np.zeros(ny),
    )


def sphere_grid(bed: Array, lat: Array, lon: Array, rotating: bool = True) -> Grid:
    """A latitude-longitude grid on the sphere of radius ``EARTH_RADIUS``,
    with cell centres at the evenly spaced ``lat`` (ny,) and ``lon`` (nx,)
    (degrees); f = 2 Omega sin(lat) if ``rotating``, else zero."""
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
    d_lat = np.radians(lat[1] - lat[0])
    d_lon = np.radians(lon[1] - lon[0])
    phi = np.radians(lat)
    edges = np.concatenate([phi - d_lat / 2, [phi[-1] + d_lat / 2]])
    r = EARTH_RADIUS
    return Grid(
        bed=np.asarray(bed, dtype=float),
        east=np.full(len(lat), r * d_lat),
        north=r * np.cos(edges) * d_lon,
        area=r * r * d_lon * (np.sin(edges[1:]) - np.sin(edges[:-1])),
        width=r * np.cos(phi) * d_lon,
        height=r * d_lat,
        coriolis=2.0 * OMEGA * np.sin(phi) if rotating else np.zeros(len(lat)),
        lat=lat,
        lon=lon,
    )


def coarsen(field: Array, factor: int) -> Array:
    """The mean of each block of ``factor`` x ``factor`` cells; rows and
    columns that do not fill a block are dropped."""
    ny, nx = (s // factor * factor for s in field.shape)
    blocks = field[:ny, :nx].reshape(ny // factor, factor, nx // factor, factor)
    return blocks.mean(axis=(1, 3))


def initial_state(grid: Grid, uplift: Array) -> tuple[Grid, Array]:
    """The grid with its bed lifted by ``uplift`` (m) and the state at rest
    whose depth is the depth before the lift: the sea surface rises with the
    sea floor, everywhere at once."""
    depth = np.maximum(0.0, -grid.bed)
    q = np.zeros((*grid.shape, 3))
    q[..., 0] = depth
    lifted = replace(grid, bed=grid.bed + uplift)
    return lifted, q


def surface(grid: Grid, q: Array) -> Array:
    """The height of the sea surface (m), NaN where a cell is dry."""
    h = q[..., 0]
    return np.where(h > WET, h + grid.bed, np.nan)


def _velocities(q: Array) -> tuple[Array, Array]:
    h = q[..., 0]
    wet = h > WET
    safe = np.where(wet, h, 1.0)
    return (
        np.where(wet, q[..., 1] / safe, 0.0),
        np.where(wet, q[..., 2] / safe, 0.0),
    )


def time_step(grid: Grid, q: Array, courant: float) -> float:
    """The step (s) of the CFL condition dt (a_x / dx + a_y / dy) <= courant,
    a the largest signal speed |u| + sqrt(g h) of a cell in each direction."""
    u, v = _velocities(q)
    c = np.sqrt(GRAVITY * q[..., 0])
    rate = (np.abs(u) + c) / grid.width[:, None] + (np.abs(v) + c) / grid.height
    top = float(rate.max())
    return np.inf if top == 0.0 else courant / top


def minmod(a: Array, b: Array) -> Array:
    """The smaller of the two one-sided slopes ``a``, ``b`` in magnitude
    where they agree in sign, zero where they do not: a limited slope that
    creates no new extremum, and flattens every crest to its cell."""
    return np.where(a * b > 0, np.where(np.abs(a) < np.abs(b), a, b), 0.0)


def monotonized_central(a: Array, b: Array) -> Array:
    """The central slope (a + b) / 2, limited to twice either one-sided
    slope, zero where they disagree in sign (van Leer's MC limiter): no new
    extremum either, and less flattening of a smooth crest than minmod."""
    size = np.minimum(np.abs(a), np.abs(b))
    size *= 2.0
    np.minimum(size, 0.5 * np.abs(a + b), out=size)
    return np.where(a * b > 0, np.copysign(size, a), 0.0)


LIMITERS = {"minmod": minmod, "monotonized central": monotonized_central}


def _radiating(ghost: Array, outward: float, sea_level: float) -> None:
    """Make the copied ghost cells ``ghost`` (4, rows, 1) of one end radiate,
    in place: the Riemann invariant that leaves the domain, u_n + 2 c (u_n
    the velocity along the outward normal, of sign ``outward``, c = sqrt(g
    h)), is the cell's; the one that enters, u_n - 2 c, is that of water at
    rest at ``sea_level`` outside. A wave leaves, and the sea outside holds
    the level, so no water drains through a boundary that a copied cell
    would leave without a restoring pressure. Dry cells, and cells whose flow
    leaves faster than c (both invariants leave), keep the copy."""
    h, eta, un = ghost[0].copy(), ghost[1].copy(), outward * ghost[2]
    bed = eta - h
    c = np.sqrt(GRAVITY * h)
    c_rest = np.sqrt(GRAVITY * np.maximum(sea_level - bed, 0.0))
    leaving = un + 2.0 * c
    c_ghost = 0.25 * leaving + 0.5 * c_rest
    h_ghost = c_ghost * c_ghost / GRAVITY
    use = (h > WET) & (np.abs(un) < c)
    ghost[0] = np.where(use, h_ghost, h)
    ghost[1] = np.where(use, h_ghost + bed, eta)
    ghost[2] = np.where(use, outward * (0.5 * leaving - c_rest), ghost[2])


def _sweep(h, eta, un, ut, open_ends: bool, limiter, sea_level=None):
    """The faces along the last axis (n + 1 per row, the first at the start
    of the row): the fluxes (mass, normal momentum, transverse momentum),
    and of every cell the rebuilt depths h* of its own side at its two faces,
    its depths h and its bed heights b at the two faces.

    With a ``limiter`` (second order): h, the surface eta = h + b and the two
    velocities are reconstructed linearly in each cell with limited slopes
    (zero where the cell or a neighbour is dry), and the bed at a face is
    eta - h there, so a surface at rest stays flat. The ghost cells copy
    their neighbours (open), radiate against the sea at rest at
    ``sea_level`` outside if it is given (``_radiating``), or mirror their
    neighbours with the normal velocity reversed (wall); they are not
    reconstructed."""
    cells = np.stack([h, eta, un, ut])  # (4, rows, n)
    first, last = cells[..., :1].copy(), cells[..., -1:].copy()
    if not open_ends:
        first[2], last[2] = -first[2], -last[2]
    elif sea_level is not None:
        _radiating(first, -1.0, sea_level)
        _radiating(last, 1.0, sea_level)
    if limiter is not None:
        padded = np.concatenate([first, cells, last], axis=-1)
        jumps = np.diff(padded, axis=-1)
        slopes = limiter(jumps[..., :-1], jumps[..., 1:])
        wet = padded[0] > WET
        slopes *= wet[:, 1:-1] & wet[:, :-2] & wet[:, 2:]
        high, low = cells + 0.5 * slopes, cells - 0.5 * slopes
    else:
        high = low = cells
    # Face k lies between padded cells k and k + 1: the left side is the high
    # side of cell k - 1 (or the first ghost), the right side the low side of
    # cell k (or the last ghost).
    left = np.concatenate([first, high], axis=-1)
    right = np.concatenate([low, last], axis=-1)
    b_left, b_right = left[1] - left[0], right[1] - right[0]
    top = np.maximum(b_left, b_right)
    h_left = np.maximum(0.0, left[1] - top)
    h_right = np.maximum(0.0, right[1] - top)
    u_left, u_right = left[2].copy(), right[2].copy()
    if not open_ends:
        # A wall: the outer side of each end face mirrors the inner side, so
        # no water crosses it, also at second order.
        h_left[:, 0], u_left[:, 0] = h_right[:, 0], -u_right[:, 0]
        h_right[:, -1], u_right[:, -1] = h_left[:, -1], -u_left[:, -1]
    state_left = np.stack([h_left.ravel(), (h_left * u_left).ravel()], axis=-1)
    state_right = np.stack([h_right.ravel(), (h_right * u_right).ravel()], axis=-1)
    f = hll_flux(state_left, state_right).reshape(*h_left.shape, 2)
    mass = f[..., 0]
    carried = mass * np.where(mass > 0, left[3], right[3])
    return (
        mass,
        f[..., 1],
        carried,
        h_left[:, 1:],  # own side of the high face of each cell
        h_right[:, :-1],  # own side of the low face
        high[0],
        low[0],
        high[1] - high[0],
        low[1] - low[0],
    )


def fluxes_and_source(
    grid: Grid,
    q: Array,
    open_ends: bool = True,
    second_order: bool = True,
    limiter: str = "monotonized central",
    sea_level: float | None = None,
) -> tuple[Array, Array, Array]:
    """The rate of change dq/dt of every cell, and the mass fluxes through the
    faces (m^2/s: east-west faces (ny, nx + 1), north-south faces (ny + 1,
    nx)), from which the outflow through the boundary follows.

    The source of each direction is that of hydrostatic reconstruction at
    second order (Audusse et al., 2004): at each face of a cell the pressure
    g / 2 (h*^2 - h^2) of the rebuilt depth, minus g times the mean of the
    cell's two face depths times its bed difference; on the sphere also the
    pressure on the north and south faces of unequal length, g / 4 (h_n^2 +
    h_s^2) (L_n - L_s). For water at rest they cancel the fluxes exactly.

    ``open_ends``: each ghost cell copies its neighbour, so a wave leaves
    without a jump at the face (transmissive), or, with a ``sea_level``,
    radiates against the sea at rest at that level outside (the incoming
    Riemann invariant of the sea at rest, the outgoing one of the cell);
    otherwise the boundary is a wall that reverses the normal velocity.
    ``second_order``: reconstruct with the slope ``limiter`` of ``LIMITERS``;
    else piecewise constant, the scheme of FL5."""
    h = q[..., 0]
    eta = h + grid.bed
    limit = LIMITERS[limiter] if second_order else None
    u, v = _velocities(q)
    g2 = 0.5 * GRAVITY
    area = grid.area[:, None]
    # East-west faces.
    mx, px, tx, own_e, own_w, h_e, h_w, b_e, b_w = _sweep(
        h, eta, u, v, open_ends, limit, sea_level
    )
    ex = grid.east[:, None]
    source_x = ex * (
        g2 * ((own_e**2 - h_e**2) - (own_w**2 - h_w**2))
        - GRAVITY * 0.5 * (h_e + h_w) * (b_e - b_w)
    )
    # North-south faces: the same sweep on the transposed grid.
    my, py, ty, own_n, own_s, h_n, h_s, b_n, b_s = (
        a.T for a in _sweep(h.T, eta.T, v.T, u.T, open_ends, limit, sea_level)
    )
    ln, ls = grid.north[1:, None], grid.north[:-1, None]
    source_y = (
        g2 * ((own_n**2 - h_n**2) * ln - (own_s**2 - h_s**2) * ls)
        - GRAVITY * 0.5 * (h_n + h_s) * (b_n - b_s) * 0.5 * (ln + ls)
        + 0.5 * g2 * (h_n**2 + h_s**2) * (ln - ls)
    )
    rate = np.empty_like(q)
    rate[..., 0] = -((mx[:, 1:] - mx[:, :-1]) * ex + my[1:] * ln - my[:-1] * ls)
    rate[..., 1] = (
        -((px[:, 1:] - px[:, :-1]) * ex + ty[1:] * ln - ty[:-1] * ls) + source_x
    )
    rate[..., 2] = (
        -((tx[:, 1:] - tx[:, :-1]) * ex + py[1:] * ln - py[:-1] * ls) + source_y
    )
    rate /= area[..., None]
    f = grid.coriolis[:, None]
    rate[..., 1] += f * q[..., 2]
    rate[..., 2] -= f * q[..., 1]
    return rate, mx, my


def _dry(q: Array) -> None:
    """Zero the momentum of the cells shallower than ``WET``, in place."""
    dry = q[..., 0] <= WET
    q[..., 1][dry] = 0.0
    q[..., 2][dry] = 0.0


def _euler(grid, q, dt, open_ends, second_order, limiter, sea_level=None):
    rate, mx, my = fluxes_and_source(
        grid, q, open_ends, second_order, limiter, sea_level
    )
    q_next = q + dt * rate
    _dry(q_next)
    return q_next, mx, my


@dataclass(frozen=True)
class Gauge:
    """A point of the sea where the surface is recorded: its name and its
    position, (x, y) in cell indices (fractional, 0 at the centre of the
    first cell)."""

    name: str
    i: float  # row (y)
    j: float  # column (x)

    def weights(self, grid: Grid) -> tuple[tuple[int, int, int, int], Array]:
        """The four cells around the gauge and their bilinear weights."""
        i0, j0 = int(np.floor(self.i)), int(np.floor(self.j))
        a, b = self.i - i0, self.j - j0
        w = np.array([(1 - a) * (1 - b), (1 - a) * b, a * (1 - b), a * b])
        return (i0, j0, i0 + 1, j0 + 1), w


@dataclass(frozen=True)
class Run:
    """A run of ``simulate``: the final state ``q``; the times ``t`` (k + 1,)
    of the steps; the surface at each gauge ``records`` (name -> (k + 1,));
    the ``volume`` of water and the volume that left through the boundary up
    to each time, ``outflow`` (m^3, (k + 1,)); the largest surface height of
    each cell over the run, ``peak`` (m); the first time it rose above
    ``threshold``, ``arrival`` (s, inf if never); the smallest depth of any
    cell at any step, ``min_depth``; ``snapshots`` (time -> surface) at the
    requested times; the number of steps."""

    q: Array
    t: Array
    records: dict[str, Array]
    volume: Array
    outflow: Array
    peak: Array
    arrival: Array
    min_depth: float
    snapshots: dict[float, Array] = field(default_factory=dict)

    @property
    def steps(self) -> int:
        return len(self.t) - 1

    @property
    def budget_residual(self) -> Array:
        """The change of the volume plus what left, at each time (m^3)."""
        return self.volume - self.volume[0] + self.outflow


def simulate(
    grid: Grid,
    q0: Array,
    t_end: float,
    courant: float,
    gauges: tuple[Gauge, ...] = (),
    open_ends: bool = True,
    threshold: float = 0.01,
    snapshot_times: tuple[float, ...] = (),
    max_steps: int = 1_000_000,
    second_order: bool = True,
    limiter: str = "monotonized central",
    uplift: Array | None = None,
    onset: Array | None = None,
    sea_level: float | None = None,
) -> Run:
    """Advance ``q0`` on ``grid`` from 0 to ``t_end`` (s) in steps of the CFL
    condition (``time_step``), the last shortened to end at ``t_end`` and a
    step shortened to meet each of ``snapshot_times``. ``second_order``: the
    reconstruction of ``fluxes_and_source`` with Heun's method (the mean of
    a forward Euler step and a second Euler step from its result); else
    piecewise-constant cells and forward Euler, as in FL5.
    Records the surface at the ``gauges`` after every step, the volume and
    what left through the boundary, the largest surface of each cell
    (``peak``), and when it first exceeded ``threshold`` (``arrival``).
    Stops after ``max_steps`` steps, so that an unstable run ends.

    ``uplift`` and ``onset`` (m and s, the shape of the grid), if given, are
    a source in time: at the end of the first step that reaches ``onset`` a
    cell's bed and its surface rise by ``uplift``, its depth unchanged.
    ``sea_level``: the open boundary radiates against the sea at rest at this
    level outside (``fluxes_and_source``) instead of copying its cells."""
    q = np.array(q0, dtype=float)
    lifted = np.zeros(grid.shape, dtype=bool)
    t = 0.0
    times = [t]
    weights = {g.name: g.weights(grid) for g in gauges}

    def at_gauges(state):
        eta = state[..., 0] + grid.bed
        out = {}
        for name, ((i0, j0, i1, j1), w) in weights.items():
            cells = np.array([eta[i0, j0], eta[i0, j1], eta[i1, j0], eta[i1, j1]])
            out[name] = float(cells @ w)
        return out

    records = {g.name: [v] for g, v in zip(gauges, at_gauges(q).values(), strict=True)}
    volume = [grid.volume(q[..., 0])]
    outflow = [0.0]
    sea = q[..., 0] > WET
    peak = np.where(sea, q[..., 0] + grid.bed, np.nan)
    arrival = np.full(grid.shape, np.inf)
    arrival[sea & (peak > threshold)] = 0.0
    min_depth = float(q[..., 0].min())
    snapshots: dict[float, Array] = {}
    pending = sorted(s for s in snapshot_times if s <= t_end)
    for s in [s for s in pending if s == 0.0]:
        snapshots[s] = surface(grid, q)
        pending.remove(s)
    steps = 0
    while t < t_end and steps < max_steps:
        dt = min(time_step(grid, q, courant), t_end - t)
        if pending:
            dt = min(dt, pending[0] - t)
        step = (open_ends, second_order, limiter, sea_level)
        q_next, mx, my = _euler(grid, q, dt, *step)
        if second_order:
            q_two, mx2, my2 = _euler(grid, q_next, dt, *step)
            q_next = 0.5 * (q + q_two)
            _dry(q_next)
            mx, my = 0.5 * (mx + mx2), 0.5 * (my + my2)
        q = q_next
        if uplift is not None:
            now = ~lifted & (onset <= t + dt * (1 + 1e-12))
            if now.any():
                grid = replace(grid, bed=np.where(now, grid.bed + uplift, grid.bed))
                lifted |= now
        t = t + dt
        if pending and abs(t - pending[0]) < 1e-9 * max(1.0, t):
            t = pending[0]
        steps += 1
        times.append(t)
        for name, value in at_gauges(q).items():
            records[name].append(value)
        volume.append(grid.volume(q[..., 0]))
        leaving = np.sum((mx[:, -1] - mx[:, 0]) * grid.east) + (
            np.sum(my[-1]) * grid.north[-1] - np.sum(my[0]) * grid.north[0]
        )
        outflow.append(outflow[-1] + dt * float(leaving))
        eta = q[..., 0] + grid.bed
        np.fmax(peak, np.where(sea, eta, np.nan), out=peak)
        first = sea & (eta > threshold) & np.isinf(arrival)
        arrival[first] = t
        min_depth = min(min_depth, float(q[..., 0].min()))
        if pending and t >= pending[0]:
            snapshots[pending.pop(0)] = surface(grid, q)
    return Run(
        q=q,
        t=np.array(times),
        records={k: np.array(v) for k, v in records.items()},
        volume=np.array(volume),
        outflow=np.array(outflow),
        peak=peak,
        arrival=arrival,
        min_depth=min_depth,
        snapshots=snapshots,
    )
