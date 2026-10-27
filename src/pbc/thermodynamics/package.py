"""A hypothetical accelerator package on a cold plate: a compact thermal model.

Dies dissipate their power into a heat spreader (the lid), a thin plate of
thickness t that conducts it sideways and passes it down through a contact
layer into a cold plate, whose coolant is at one temperature. The plate is
described by the temperature T (degrees C) of its middle plane, which per
unit area obeys

    rho c t dT/dt = div(k t grad T) + q''(x, y) - (T - T_coolant) / R_base,

with q'' the heat flux of the dies (W/m^2) and R_base the resistance from
the middle plane down into the coolant: half the plate, the contact, and the
cold plate in series, t / (2 k) + R_lid-plate + 1 / h (m^2 K / W). The edges
of the plate and its top outside the dies are insulated. A die is hotter
than the middle plane under it by its flux times the resistance of the
contact and of the upper half of the plate:
T_junction = T + q'' (R_die-lid + t / (2 k)). The halves of the plate are
crossed straight down, as if the heat did not spread within the thickness;
a cross-section of the plate that resolves its thickness checks how good
that is.

Every number of a package is invented for teaching: no die, power, or
material stack of a real product is modelled. The model is solved two ways
on the same nodes: by the linear finite elements of ``pbc.fem``, where a
part of the plate may be another material (an insert), and by the
five-point finite differences of the heat-conduction lesson, with mirrored
ghost nodes at the insulated edges, for a plate of one material. A load
shaped as one cosine mode of the plate has an exact solution, steady and
transient, against which both are checked.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.sparse.linalg import spsolve

from pbc.fem.assembly import Field, convection, edge_load, load, mass, stiffness
from pbc.fem.mesh import Mesh, rectangle
from pbc.thermodynamics.conduction import Material

Array = NDArray[np.float64]
_EDGE = 1e-12  # m: a node on the edge of a rectangle counts as on it


@dataclass(frozen=True)
class Region:
    """The rectangle [x0, x1] x [y0, y1] (m)."""

    x0: float
    x1: float
    y0: float
    y1: float

    @property
    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def inside(self, x: Array, y: Array) -> Array:
        """True strictly inside the rectangle."""
        return (x > self.x0) & (x < self.x1) & (y > self.y0) & (y < self.y1)

    def covers(self, x: Array, y: Array) -> Array:
        """True inside the rectangle or on its edge."""
        return (
            (x >= self.x0 - _EDGE)
            & (x <= self.x1 + _EDGE)
            & (y >= self.y0 - _EDGE)
            & (y <= self.y1 + _EDGE)
        )

    def overlap(self, x0: Array, x1: Array, y0: Array, y1: Array) -> Array:
        """The area (m^2) the rectangle shares with each of the rectangles
        [x0, x1] x [y0, y1]."""
        width = np.clip(np.minimum(x1, self.x1) - np.maximum(x0, self.x0), 0.0, None)
        height = np.clip(np.minimum(y1, self.y1) - np.maximum(y0, self.y0), 0.0, None)
        return width * height


@dataclass(frozen=True)
class Die:
    """A die of ``power`` (W) spread uniformly over its ``region``."""

    name: str
    region: Region
    power: float

    @property
    def flux(self) -> float:
        """q'' = P / A (W/m^2)."""
        return self.power / self.region.area


@dataclass(frozen=True)
class Package:
    """A spreader of ``width`` x ``height`` x ``thickness`` (m) of
    ``material``, with ``inserts`` of the material ``insert`` through its
    thickness; the ``dies`` on top; the contact resistances ``die_contact``
    (die to lid) and ``plate_contact`` (lid to cold plate) (m^2 K / W); the
    cold plate's heat transfer coefficient ``h`` (W/(m^2 K)) and its coolant
    temperature ``coolant`` (degrees C)."""

    width: float
    height: float
    thickness: float
    material: Material
    dies: tuple[Die, ...]
    die_contact: float
    plate_contact: float
    h: float
    coolant: float
    insert: Material | None = None
    inserts: tuple[Region, ...] = ()

    # region: resistances
    def resistance_below(self, k: float | Array) -> float | Array:
        """R_base = t / (2 k) + R_lid-plate + 1 / h (m^2 K / W): from the
        middle plane of a plate of conductivity k down into the coolant, per
        unit area."""
        return 0.5 * self.thickness / k + self.plate_contact + 1.0 / self.h

    @property
    def base_resistance(self) -> float:
        """R_base of the spreader's own material."""
        return self.resistance_below(self.material.k)

    def conductivity(self, x: Array, y: Array) -> Array:
        """k (W/(m K)) at the points: the insert's inside an insert."""
        k = np.full(np.shape(x), self.material.k)
        for region in self.inserts:
            k = np.where(region.inside(x, y), self.insert.k, k)
        return k

    def die_resistance(self, die: Die) -> float:
        """R_die-lid + t / (2 k) (m^2 K / W): from a die down to the middle
        plane, with k of the plate at the centre of the die."""
        r = die.region
        k = self.conductivity(0.5 * (r.x0 + r.x1), 0.5 * (r.y0 + r.y1))
        return self.die_contact + 0.5 * self.thickness / float(k)

    # endregion: resistances

    @property
    def power(self) -> float:
        """The heat the dies dissipate together (W)."""
        return float(sum(die.power for die in self.dies))

    @property
    def mass(self) -> float:
        """The mass of the spreader (kg), inserts included."""
        volume = self.width * self.height * self.thickness
        extra = 0.0
        if self.insert is not None:
            extra = sum(region.area for region in self.inserts) * self.thickness
            extra *= self.insert.rho - self.material.rho
        return self.material.rho * volume + extra

    def heat_flux(self, x: Array, y: Array) -> Array:
        """q''(x, y) (W/m^2): the flux of the die at each point, zero between
        the dies."""
        out = np.zeros_like(np.asarray(x, dtype=float))
        for die in self.dies:
            out = out + np.where(die.region.inside(x, y), die.flux, 0.0)
        return out

    def spreading_length(self) -> float:
        """sqrt(k t R_base) (m): the distance over which the plate of its own
        material carries heat sideways before the coolant takes it."""
        return float(np.sqrt(self.material.k * self.thickness * self.base_resistance))


def mesh_for(package: Package, spacing: float) -> Mesh:
    """The rectangle of the spreader with square cells of side ``spacing``,
    each split into two triangles."""
    nx, ny = round(package.width / spacing), round(package.height / spacing)
    if not np.isclose(nx * spacing, package.width) or not np.isclose(
        ny * spacing, package.height
    ):
        raise ValueError("the spacing must divide the width and the height")
    return rectangle(package.width, package.height, nx, ny)


def materials(package: Package, mesh: Mesh) -> tuple[Array, Array]:
    """The conductivity k (W/(m K)) and the heat capacity per volume rho c
    (J/(m^3 K)) of every triangle, by where its centroid lies."""
    k = np.full(len(mesh.triangles), package.material.k)
    rho_c = np.full(len(mesh.triangles), package.material.rho * package.material.c)
    if package.insert is not None:
        x, y = mesh.nodes[mesh.triangles].mean(axis=1).T
        for region in package.inserts:
            inside = region.inside(x, y)
            k[inside] = package.insert.k
            rho_c[inside] = package.insert.rho * package.insert.c
    return k, rho_c


@dataclass(frozen=True)
class System:
    """The finite-element model of a package: C dT/dt = F - (K + S) T + S T_c,
    with the capacity C (J/K), the conduction K and the exchange with the
    coolant S (W/K), the load of the dies F (W), and the coolant temperature."""

    mesh: Mesh
    capacity: sparse.csr_matrix
    conduction: sparse.csr_matrix
    exchange: sparse.csr_matrix
    load: Array
    coolant: float

    @property
    def matrix(self) -> sparse.csr_matrix:
        """K + S."""
        return (self.conduction + self.exchange).tocsr()

    @property
    def vector(self) -> Array:
        """F + S T_c."""
        return self.load + self.exchange @ np.full(len(self.load), self.coolant)


def fem_system(package: Package, mesh: Mesh, flux: Field | None = None) -> System:
    """Assemble the plate model on ``mesh``: K with k t per triangle, C the
    mass matrix with rho c t, S the mass matrix with 1 / R_base of each
    triangle's material, F the load of the heat flux (the dies', or
    ``flux``)."""
    k, rho_c = materials(package, mesh)
    t = package.thickness
    return System(
        mesh=mesh,
        capacity=mass(mesh, rho_c * t),
        conduction=stiffness(mesh, k * t),
        exchange=mass(mesh, 1.0 / package.resistance_below(k)),
        load=load(mesh, package.heat_flux if flux is None else flux),
        coolant=package.coolant,
    )


def steady(system: System) -> Array:
    """The steady temperature of the plate at the nodes (degrees C):
    (K + S) T = F + S T_c."""
    return spsolve(system.matrix.tocsc(), system.vector)


def heat_to_coolant(system: System, temperature: Array) -> Array:
    """The heat the plate gives to the coolant (W) at each of the given
    states (one per row, or one state): the integral of (T - T_c) / R_base."""
    rise = np.atleast_2d(temperature) - system.coolant
    out = rise @ system.exchange.T @ np.ones(rise.shape[1])
    return out if np.ndim(temperature) > 1 else float(out[0])


def stored_heat(system: System, temperature: Array) -> Array:
    """The heat stored in the plate above the coolant temperature (J): the
    integral of rho c t (T - T_c), at each of the given states."""
    rise = np.atleast_2d(temperature) - system.coolant
    out = rise @ system.capacity.T @ np.ones(rise.shape[1])
    return out if np.ndim(temperature) > 1 else float(out[0])


def junction_maximum(package: Package, x: Array, y: Array, temperature: Array):
    """The hottest junction of the package (degrees C): the largest over the
    dies and the nodes each covers of T + q'' (R_die-lid + t / (2 k)); with
    several states (one per row), the hottest of each."""
    values = [
        np.max(temperature[..., die.region.covers(x, y)], axis=-1)
        + die.flux * package.die_resistance(die)
        for die in package.dies
    ]
    out = np.max(np.array(values), axis=0)
    return float(out) if np.ndim(out) == 0 else out


# --- The finite-difference baseline ------------------------------------------


@dataclass(frozen=True)
class Grid:
    """The node-centred grid of the finite differences: the node coordinates
    (flattened row by row, as ``pbc.fem.mesh.rectangle`` numbers its nodes),
    the area of each node's control volume (m^2), and the spacing (m)."""

    x: Array
    y: Array
    areas: Array
    spacing: float


def fd_grid(package: Package, spacing: float) -> Grid:
    """The nodes of the spreader at ``spacing``; the control volume of a node
    is the square of side ``spacing`` around it, cut by the edges."""
    mesh = mesh_for(package, spacing)
    x, y = mesh.nodes.T
    half = 0.5 * spacing
    width = np.minimum(x + half, package.width) - np.maximum(x - half, 0.0)
    height = np.minimum(y + half, package.height) - np.maximum(y - half, 0.0)
    return Grid(x, y, width * height, spacing)


def fd_laplacian(package: Package, spacing: float) -> sparse.csr_matrix:
    """The five-point Laplacian (1/m^2) with an insulated edge on every side:
    the ghost node beyond an edge mirrors the node inside it,
    T_ghost = T_inside, so that dT/dn = 0 there to second order."""

    def second_difference(cells: int) -> sparse.csr_matrix:
        d = sparse.diags(
            [np.ones(cells), -2.0 * np.ones(cells + 1), np.ones(cells)],
            [-1, 0, 1],
            format="lil",
        )
        d[0, 1] = 2.0  # the mirrored ghost node
        d[cells, cells - 1] = 2.0
        return d.tocsr() / spacing**2

    nx, ny = round(package.width / spacing), round(package.height / spacing)
    return (
        sparse.kron(sparse.identity(ny + 1), second_difference(nx))
        + sparse.kron(second_difference(ny), sparse.identity(nx + 1))
    ).tocsr()


def fd_die_source(package: Package, grid: Grid) -> Array:
    """The heat flux of the dies averaged over each node's control volume
    (W/m^2), so that the grid receives exactly the power of every die."""
    half = 0.5 * grid.spacing
    x0, x1 = np.maximum(grid.x - half, 0.0), np.minimum(grid.x + half, package.width)
    y0, y1 = np.maximum(grid.y - half, 0.0), np.minimum(grid.y + half, package.height)
    heat = sum(die.flux * die.region.overlap(x0, x1, y0, y1) for die in package.dies)
    return heat / grid.areas


@dataclass(frozen=True)
class FiniteDifference:
    """The plate model by finite differences, one equation per node:
    rho c t dT/dt = k t laplacian(T) + q - (T - T_c) / R_base."""

    grid: Grid
    laplacian: sparse.csr_matrix
    source: Array
    package: Package

    @property
    def capacity(self) -> float:
        """rho c t (J/(m^2 K))."""
        m = self.package.material
        return m.rho * m.c * self.package.thickness

    # region: rate
    def rate(self, temperature: Array) -> Array:
        """dT/dt at every node (K/s)."""
        p = self.package
        return (
            p.material.k * p.thickness * (self.laplacian @ temperature)
            + self.source
            - (temperature - p.coolant) / p.base_resistance
        ) / self.capacity

    # endregion: rate

    def step(self, dt: float):
        """The explicit (FTCS) step T + dt dT/dt, as a function of the state."""
        return lambda temperature: temperature + dt * self.rate(temperature)

    def steady(self) -> Array:
        """The steady temperature: (1 / R_base - k t laplacian) T =
        q + T_c / R_base, one sparse system."""
        p = self.package
        n = len(self.source)
        matrix = sparse.identity(n) / p.base_resistance - (
            p.material.k * p.thickness * self.laplacian
        )
        return spsolve(matrix.tocsc(), self.source + p.coolant / p.base_resistance)

    def heat_to_coolant(self, temperature: Array) -> Array:
        """The sum over the control volumes of (T - T_c) / R_base (W)."""
        p = self.package
        return (
            (np.asarray(temperature) - p.coolant)
            @ self.grid.areas
            / (p.base_resistance)
        )

    def stored_heat(self, temperature: Array) -> Array:
        """The sum over the control volumes of rho c t (T - T_c) (J)."""
        rise = np.asarray(temperature) - self.package.coolant
        return self.capacity * rise @ self.grid.areas


def finite_differences(
    package: Package, spacing: float, source: Array | None = None
) -> FiniteDifference:
    """The finite-difference model of a plate of one material at
    ``spacing``, with the dies' control-volume source or the node values
    ``source`` (W/m^2)."""
    if package.insert is not None:
        raise ValueError("the finite-difference baseline takes one material")
    grid = fd_grid(package, spacing)
    return FiniteDifference(
        grid=grid,
        laplacian=fd_laplacian(package, spacing),
        source=fd_die_source(package, grid) if source is None else source,
        package=package,
    )


# --- The exact cosine mode ---------------------------------------------------


@dataclass(frozen=True)
class CosineMode:
    """The load q0 + q1 cos(pi x / W) cos(pi y / H) (W/m^2) on the insulated
    plate of a package of one material: its uniform part and its mode each
    relax independently, so the temperature is known exactly."""

    package: Package
    uniform: float
    amplitude: float

    def flux(self, x: Array, y: Array) -> Array:
        p = self.package
        return self.uniform + self.amplitude * np.cos(np.pi * x / p.width) * np.cos(
            np.pi * y / p.height
        )

    def conductances(self) -> tuple[float, float]:
        """The rates (W/(m^2 K)) at which the uniform part and the mode lose
        heat: 1 / R_base, and k t pi^2 (1/W^2 + 1/H^2) + 1 / R_base."""
        p = self.package
        exchange = 1.0 / p.base_resistance
        spreading = (
            p.material.k
            * p.thickness
            * np.pi**2
            * (1.0 / p.width**2 + 1.0 / p.height**2)
        )
        return exchange, spreading + exchange

    def temperature(self, x: Array, y: Array, time: float = np.inf) -> Array:
        """T(x, y, t) from the coolant temperature at t = 0; the steady state
        at t = infinity: each part rises to its load over its conductance,
        with the time constant rho c t over that conductance."""
        p = self.package
        rho_c_t = p.material.rho * p.material.c * p.thickness
        g0, g1 = self.conductances()
        rise0 = self.uniform / g0 * -np.expm1(-time * g0 / rho_c_t)
        rise1 = self.amplitude / g1 * -np.expm1(-time * g1 / rho_c_t)
        shape = np.cos(np.pi * x / p.width) * np.cos(np.pi * y / p.height)
        return p.coolant + rise0 + rise1 * shape


# --- The cross-section that resolves the thickness ---------------------------


def cross_section(
    package: Package, flux: Field, cells: int, layers: int
) -> tuple[Mesh, Array]:
    """The steady temperature in a vertical cut through the spreader, x
    across its width and z through its thickness, with no variation along
    the cut's normal: -div(k grad T) = 0 with the flux q''(x) entering the
    top, the contact and the cold plate below (h_below = 1 / (R_lid-plate +
    1 / h) to the coolant), and insulated ends; ``cells`` across, ``layers``
    through the thickness. The inserts are the material of their x range at
    the middle of the spreader's height. Returns the mesh and the
    temperature (degrees C)."""
    mesh = rectangle(package.width, package.thickness, cells, layers)
    x_centre = mesh.nodes[mesh.triangles].mean(axis=1)[:, 0]
    k = package.conductivity(x_centre, np.full_like(x_centre, 0.5 * package.height))
    h_below = 1.0 / (package.plate_contact + 1.0 / package.h)
    below, into_coolant = convection(
        mesh,
        mesh.boundary["bottom"],
        h_below,
        lambda x, y: np.full_like(x, package.coolant),
    )
    vector = into_coolant + edge_load(mesh, mesh.boundary["top"], flux)
    return mesh, spsolve((stiffness(mesh, k) + below).tocsc(), vector)
