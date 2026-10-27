"""The experiment of the capstone "Thermal engineering of an AI accelerator".

A hypothetical package, two compute dies and four memory stacks on a heat
spreader cooled by a cold plate (``pbc.thermodynamics.package``), solved
with the linear finite elements of ``pbc.fem`` and checked against the
finite differences of the heat-conduction lesson: the exact cosine mode, the
energy balance, mesh and time-step refinement, the explicit step's
stability limit, then cooling, material, and layout scenarios compared, the
hottest junction minimised under the mass, size, and heat-removal limits,
its sensitivity to the uncertain inputs, the trade-off table, and the
recommendation. Every number of the package is invented. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m \\
        pbc.thermodynamics.experiments.thermal_engineering_of_an_ai_accelerator out
"""

from dataclasses import replace
from functools import partial
from itertools import pairwise

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.tri import Triangulation
from scipy.linalg import eigh

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fem.transient import midpoints, theta_march
from pbc.thermodynamics.conduction import (
    Material,
    growth_per_step,
    march,
    stability_limit,
)
from pbc.thermodynamics.package import (
    CosineMode,
    Die,
    Package,
    Region,
    cross_section,
    fem_system,
    finite_differences,
    heat_to_coolant,
    junction_maximum,
    mesh_for,
    steady,
    stored_heat,
)
from pbc.verification.estimates import fitted_order

# region: package
WIDTH, HEIGHT = 0.064, 0.048  # m, the heat spreader (lid)
COMPUTE_SIZE, COMPUTE_POWER = (0.016, 0.020), 250.0  # m, W: each of two
MEMORY_SIZE, MEMORY_POWER = (0.008, 0.010), 12.0  # m, W: each of four
INSERT_SIZE = (0.020, 0.024)  # m, a copper insert under each compute die
ALUMINIUM = Material(k=167.0, rho=2700.0, c=896.0)  # an aluminium alloy
COPPER = Material(k=390.0, rho=8960.0, c=385.0)
DIE_CONTACT = 1e-5  # m^2 K / W, die to lid (a thermal interface material)
PLATE_CONTACT = 1e-5  # m^2 K / W, lid to cold plate
COOLANT = 35.0  # degrees C
COOLING = {  # W/(m^2 K), the effective coefficient under the spreader
    "air heat sink": 3000.0,
    "cold plate, nominal flow": 8000.0,
    "cold plate, full flow": 15000.0,
}
# endregion: package
# region: constraints
JUNCTION_LIMIT = 85.0  # degrees C, the hottest junction allowed
MASS_LIMIT = 0.060  # kg, the spreader
THICKNESS_LIMIT = 0.003  # m, the height the package allows
H_MAX = 15000.0  # W/(m^2 K), the most the coolant loop provides
MARGIN = 0.002  # m, between a die (or an insert) and an edge or a neighbour
# endregion: constraints
# region: studies
SPACING = 0.001  # m, the mesh of the scenarios
SPACINGS = [0.004, 0.002, 0.001, 0.0005]  # m, the cosine mode
PACKAGE_SPACINGS = [0.002, 0.001, 0.0005, 0.00025]  # m, the mesh study
STEP_FRACTIONS = [4, 8, 16, 32, 64]  # steps over the time-step study's span
STUDY_TIME = 1.0  # s, the span of the time-step study
TRANSIENT_TIME, TRANSIENT_STEP = 4.0, 0.02  # s, the power-step transient
SEPARATIONS = np.arange(0.018, 0.0441, 0.002)  # m, between the compute dies
CHANGE = 0.2  # the relative change of each input in the sensitivity study
# endregion: studies

DESIGNS = {
    "aluminium": (ALUMINIUM, None),
    "copper": (COPPER, None),
    "aluminium, copper inserts": (ALUMINIUM, COPPER),
}


def below(value: float, bound: float) -> str:
    """A gap at the level of round-off is not shown as a number: only that it
    is smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def dies(separation: float) -> tuple[Die, ...]:
    """Two compute dies ``separation`` apart (centre to centre) across the
    middle of the spreader, each with a memory stack above and below it."""
    out = []
    (cw, ch), (mw, mh) = COMPUTE_SIZE, MEMORY_SIZE
    yc = 0.5 * HEIGHT
    for number, side in enumerate((-1, 1), start=1):
        xc = 0.5 * WIDTH + side * 0.5 * separation
        out.append(
            Die(
                f"compute {number}",
                Region(xc - cw / 2, xc + cw / 2, yc - ch / 2, yc + ch / 2),
                COMPUTE_POWER,
            )
        )
        for position, y0 in (("below", MARGIN), ("above", HEIGHT - MARGIN - mh)):
            out.append(
                Die(
                    f"memory {number} {position}",
                    Region(xc - mw / 2, xc + mw / 2, y0, y0 + mh),
                    MEMORY_POWER,
                )
            )
    return tuple(out)


def inserts(separation: float) -> tuple[Region, ...]:
    """A copper insert centred under each compute die."""
    (iw, ih), yc = INSERT_SIZE, 0.5 * HEIGHT
    return tuple(
        Region(xc - iw / 2, xc + iw / 2, yc - ih / 2, yc + ih / 2)
        for xc in (0.5 * WIDTH - 0.5 * separation, 0.5 * WIDTH + 0.5 * separation)
    )


def admissible(design: str) -> tuple[float, float]:
    """The separations (m) the size constraint allows: the compute dies, or
    the inserts, at least ``MARGIN`` apart and from the edges."""
    width = COMPUTE_SIZE[0] if DESIGNS[design][1] is None else INSERT_SIZE[0]
    return width + MARGIN, WIDTH - width - 2.0 * MARGIN


def package(
    design: str, thickness: float, h: float, separation: float = 0.5 * WIDTH
) -> Package:
    """The package of a design (a key of ``DESIGNS``) at a thickness (m), a
    cold-plate coefficient (W/(m^2 K)), and a die separation (m)."""
    material, insert = DESIGNS[design]
    return Package(
        width=WIDTH,
        height=HEIGHT,
        thickness=thickness,
        material=material,
        dies=dies(separation),
        die_contact=DIE_CONTACT,
        plate_contact=PLATE_CONTACT,
        h=h,
        coolant=COOLANT,
        insert=insert,
        inserts=() if insert is None else inserts(separation),
    )


def thickest(design: str) -> float:
    """The thickest spreader the size and the mass limits allow (m): the
    mass grows in proportion to the thickness."""
    per_metre = package(design, 1.0, H_MAX).mass
    return min(THICKNESS_LIMIT, MASS_LIMIT / per_metre)


def solve(package: Package, spacing: float = SPACING):
    """The steady finite-element solution: the system, the temperature at
    the nodes, and the hottest junction."""
    system = fem_system(package, mesh_for(package, spacing))
    temperature = steady(system)
    hottest = junction_maximum(package, *system.mesh.nodes.T, temperature)
    return system, temperature, hottest


def hottest_junction(package: Package, spacing: float = SPACING) -> float:
    return solve(package, spacing)[2]


def fd_hottest_junction(package: Package, spacing: float = SPACING) -> float:
    """The hottest junction by the finite-difference baseline."""
    model = finite_differences(package, spacing)
    return junction_maximum(package, model.grid.x, model.grid.y, model.steady())


def requirements(experiment: Experiment) -> None:
    """The heat loads and the inputs of the model; record the tables and the
    check of the plate model's assumption."""
    rows = [
        (
            die.name,
            1e3 * (die.region.x1 - die.region.x0),
            1e3 * (die.region.y1 - die.region.y0),
            die.power,
            1e-4 * die.flux,
        )
        for die in dies(0.5 * WIDTH)
    ]
    experiment.table(
        "loads",
        rows,
        [
            ("die", "", ""),
            ("width", "mm", ".0f"),
            ("height", "mm", ".0f"),
            ("power", "W", ".0f"),
            ("heat flux", "W/cm^2", ".1f"),
        ],
        "The hypothetical heat loads: two compute dies and four memory "
        "stacks, each dissipating its power uniformly over its footprint. "
        "Invented round numbers, not the data of any product.",
    )
    rows = [
        (f"{name}: conductivity", m.k, "W/(m K)")
        for name, m in (("aluminium alloy", ALUMINIUM), ("copper", COPPER))
    ]
    rows += [
        (f"{name}: density times specific heat", 1e-6 * m.rho * m.c, "MJ/(m^3 K)")
        for name, m in (("aluminium alloy", ALUMINIUM), ("copper", COPPER))
    ]
    rows += [
        ("contact resistance, die to lid", 1e6 * DIE_CONTACT, "mm^2 K/W"),
        ("contact resistance, lid to cold plate", 1e6 * PLATE_CONTACT, "mm^2 K/W"),
        ("coolant temperature", COOLANT, "degrees C"),
    ]
    rows += [(f"h, {name}", h, "W/(m^2 K)") for name, h in COOLING.items()]
    rows += [
        ("limit: hottest junction", JUNCTION_LIMIT, "degrees C"),
        ("limit: spreader mass", 1e3 * MASS_LIMIT, "g"),
        ("limit: spreader thickness", 1e3 * THICKNESS_LIMIT, "mm"),
        ("limit: cold-plate coefficient h", H_MAX, "W/(m^2 K)"),
        ("limit: clearance between dies and to the edges", 1e3 * MARGIN, "mm"),
    ]
    experiment.table(
        "inputs",
        [(name, f"{value:g}", unit) for name, value, unit in rows],
        [("input", "", ""), ("value", "", ""), ("unit", "", "")],
        "The materials, the contact and cold-plate assumptions, and the "
        "constraints of the design: typical textbook values for the materials, "
        "assumed values for the rest.",
    )
    aluminium = package("aluminium", THICKNESS_LIMIT, H_MAX)
    experiment.number("power", aluminium.power, ".0f")
    experiment.number("spreader-area", 1e4 * WIDTH * HEIGHT, ".1f")
    experiment.number("spreading-length", 1e3 * aluminium.spreading_length(), ".1f")
    half = 0.5 * THICKNESS_LIMIT / ALUMINIUM.k
    experiment.number("half-share", half / aluminium.base_resistance, ".2f")


def rms(error: np.ndarray, areas: np.ndarray) -> float:
    """The root mean square of a nodal error over the plate, each node
    weighted by the area of its control volume (a discrete L2 norm)."""
    return float(np.sqrt(np.sum(areas * error**2) / np.sum(areas)))


def cosine_mode(experiment: Experiment):
    """The cosine-mode load on a copper plate, by the elements and by the
    finite differences, against the exact solution; record the table and the
    orders, and return the spacings and the two root-mean-square errors."""
    plate = package("copper", 0.002, COOLING["cold plate, nominal flow"])
    mean_flux = plate.power / (WIDTH * HEIGHT)
    mode = CosineMode(plate, uniform=mean_flux, amplitude=mean_flux)
    rows, fem_errors, fd_errors, fem_largest = [], [], [], []
    for spacing in SPACINGS:
        system = fem_system(plate, mesh_for(plate, spacing), flux=mode.flux)
        x, y = system.mesh.nodes.T
        exact = mode.temperature(x, y)
        model = finite_differences(plate, spacing, source=mode.flux(x, y))
        fem = steady(system) - exact
        fd = model.steady() - exact
        fem_errors.append(rms(fem, model.grid.areas))
        fd_errors.append(rms(fd, model.grid.areas))
        fem_largest.append(np.max(np.abs(fem)))
        rows.append(
            (
                1e3 * spacing,
                len(x),
                fem_errors[-1],
                fd_errors[-1],
                fem_largest[-1],
                np.max(np.abs(fd)),
            )
        )
    experiment.table(
        "cosine-mode",
        rows,
        [
            ("spacing", "mm", ".1f"),
            ("nodes", "", "d"),
            ("finite elements, rms error", "K", ".2e"),
            ("finite differences, rms error", "K", ".2e"),
            ("finite elements, largest error", "K", ".2e"),
            ("finite differences, largest error", "K", ".2e"),
        ],
        "A load of one cosine mode on the insulated copper plate, 2 mm thick, "
        "on the nominal cold plate: the difference between each method's "
        "temperature and the exact solution at the nodes, as a root mean "
        "square over the plate and at its largest.",
    )
    experiment.number("cosine-fem-order", fitted_order(SPACINGS, fem_errors), ".2f")
    experiment.number("cosine-fd-order", fitted_order(SPACINGS, fd_errors), ".2f")
    experiment.number(
        "cosine-corner-order", fitted_order(SPACINGS[-2:], fem_largest[-2:]), ".2f"
    )
    return SPACINGS, fem_errors, fd_errors


def mesh_study(experiment: Experiment) -> None:
    """The hottest junction of the copper design by the elements and the
    finite differences on four meshes, and the heat balances of both; record
    the table, the order of their difference, and the largest gap."""
    copper = package("copper", thickest("copper"), H_MAX)
    power = copper.power
    rows, fem, fd, gaps = [], [], [], []
    for spacing in PACKAGE_SPACINGS:
        system, temperature, hottest = solve(copper, spacing)
        model = finite_differences(copper, spacing)
        fd_temperature = model.steady()
        fem.append(hottest)
        fd.append(junction_maximum(copper, model.grid.x, model.grid.y, fd_temperature))
        gap = max(
            abs(system.load.sum() - power) / power,
            abs(heat_to_coolant(system, temperature) - power) / power,
            abs(model.source @ model.grid.areas - power) / power,
            abs(model.heat_to_coolant(fd_temperature) - power) / power,
        )
        gaps.append(gap)
        rows.append(
            (
                1e3 * spacing,
                len(temperature),
                fem[-1],
                fd[-1],
                abs(fem[-1] - fd[-1]),
                below(gap, 1e-10),
            )
        )
    experiment.table(
        "mesh-study",
        rows,
        [
            ("spacing", "mm", ".2f"),
            ("nodes", "", "d"),
            ("hottest junction, finite elements", "degrees C", ".4f"),
            ("hottest junction, finite differences", "degrees C", ".4f"),
            ("difference between the methods", "K", ".1e"),
            ("largest relative gap of a heat balance", "", ""),
        ],
        "The hottest junction of the copper design on the full flow as the "
        "mesh is refined, by both methods on the same nodes, and the heat "
        "balances: the power of the dies against the heat each method's load "
        "receives and the heat it gives to the coolant.",
    )
    differences = [abs(a - b) for a, b in zip(fem, fd, strict=True)]
    experiment.number(
        "method-order", fitted_order(PACKAGE_SPACINGS, differences), ".2f"
    )
    experiment.number("method-difference", differences[-1], ".1e")
    experiment.number("balance-gap", below(max(gaps), 1e-10))


def strip(design: Package, spacing: float) -> Package:
    """The package cut down to one row of cells of height ``spacing`` with
    only the compute dies, each across the full row: a plate model whose
    temperature cannot vary along y, comparable with a cross-section."""
    dies = tuple(
        Die(
            d.name,
            Region(d.region.x0, d.region.x1, 0.0, spacing),
            d.flux * (d.region.x1 - d.region.x0) * spacing,
        )
        for d in design.dies
        if d.name.startswith("compute")
    )
    inserts = tuple(Region(r.x0, r.x1, 0.0, spacing) for r in design.inserts)
    return replace(design, height=spacing, dies=dies, inserts=inserts)


def section_junction(design: Package, cells: int, layers: int) -> float:
    """The hottest junction of the compute dies over a cross-section that
    resolves the thickness: the top surface under a die plus its flux times
    the die-to-lid contact."""
    compute = [d for d in design.dies if d.name.startswith("compute")]

    def flux(x, y):
        return sum(
            np.where((x > d.region.x0) & (x < d.region.x1), d.flux, 0.0)
            for d in compute
        )

    mesh, temperature = cross_section(design, flux, cells, layers)
    x, z = mesh.nodes.T
    top = np.isclose(z, design.thickness)
    return max(
        float(temperature[top & (x >= d.region.x0) & (x <= d.region.x1)].max())
        + d.flux * design.die_contact
        for d in compute
    )


def section_check(experiment: Experiment) -> float:
    """The plate model, cut down to a strip, against cross-sections that
    resolve the thickness, for each material at its thickest admissible
    spreader on the full flow; record the table, and return the largest
    gap."""
    rows, gaps, changes = [], [], []
    for design in DESIGNS:
        p = package(design, thickest(design), H_MAX)
        spacing = 0.00025
        cut = strip(p, spacing)
        system = fem_system(cut, mesh_for(cut, spacing))
        plate = junction_maximum(cut, *system.mesh.nodes.T, steady(system))
        cells = round(WIDTH / spacing)
        coarse = section_junction(p, cells, 12)
        fine = section_junction(p, 2 * cells, 24)
        gaps.append(plate - fine)
        changes.append(abs(fine - coarse))
        rows.append((design, 1e3 * p.thickness, plate, coarse, fine, plate - fine))
    experiment.table(
        "cross-section",
        rows,
        [
            ("spreader", "", ""),
            ("thickness", "mm", ".2f"),
            ("plate model", "degrees C", ".3f"),
            ("cross-section, 12 layers", "degrees C", ".3f"),
            ("cross-section, 24 layers", "degrees C", ".3f"),
            ("plate model minus cross-section", "K", "+.3f"),
        ],
        "The hottest junction of the compute dies when they and the inserts "
        "run across the whole spreader, so that nothing varies along y: by "
        "the plate model, and by a cross-section that resolves the thickness, "
        "on two meshes of square cells; the full flow.",
    )
    experiment.number("section-gap", max(gaps), ".2f")
    experiment.number("section-least", min(gaps), ".2f")
    experiment.number("section-change", max(changes), ".1e")
    return max(abs(g) for g in gaps)


def insert_refinement(experiment: Experiment) -> None:
    """The hottest junction of the design with inserts on four meshes, and of
    the same design with the inserts run the full height of the spreader (no
    corner inside the plate); record the table, the observed orders of the
    changes, and the largest balance gap."""
    inserted = package("aluminium, copper inserts", THICKNESS_LIMIT, H_MAX)
    strips = replace(
        inserted,
        inserts=tuple(Region(r.x0, r.x1, 0.0, HEIGHT) for r in inserted.inserts),
    )
    values = {"inserts": [], "strips": []}
    gaps = []
    for spacing in PACKAGE_SPACINGS:
        for name, design in (("inserts", inserted), ("strips", strips)):
            system, temperature, hottest = solve(design, spacing)
            values[name].append(hottest)
            power = design.power
            gaps.append(abs(heat_to_coolant(system, temperature) - power) / power)
    changes = {name: [abs(b - a) for a, b in pairwise(v)] for name, v in values.items()}
    shown = {name: [""] + [f"{c:.1e}" for c in v] for name, v in changes.items()}
    rows = [
        (
            1e3 * spacing,
            values["inserts"][i],
            shown["inserts"][i],
            values["strips"][i],
            shown["strips"][i],
        )
        for i, spacing in enumerate(PACKAGE_SPACINGS)
    ]
    experiment.table(
        "insert-refinement",
        rows,
        [
            ("spacing", "mm", ".2f"),
            ("inserts: hottest junction", "degrees C", ".4f"),
            ("change from the coarser mesh", "K", ""),
            ("full-height strips: hottest junction", "degrees C", ".4f"),
            ("change from the coarser mesh", "K", ""),
        ],
        "The hottest junction of the aluminium spreader with copper inserts "
        "on the full flow as the mesh is refined, and of the same spreader "
        "with the inserts extended to strips across its full height, whose "
        "material boundary has no corner inside the plate.",
    )
    for name in values:
        last = changes[name][-2:]
        experiment.number(f"{name}-order", float(np.log2(last[0] / last[1])), ".2f")
    experiment.number("insert-change", changes["inserts"][-1], ".1e")
    experiment.number("insert-balance-gap", below(max(gaps), 1e-10))


def semi_discrete_exact(system, initial, times):
    """The exact solution of C dT/dt = b - A T in time on a fixed mesh, from
    the generalised eigenproblem A v = lambda C v: every mode relaxes
    towards the steady state as exp(-lambda t)."""
    a, c = system.matrix.toarray(), system.capacity.toarray()
    rates, modes = eigh(a, c)  # modes^T C modes = I
    final = np.linalg.solve(a, system.vector)
    weights = modes.T @ c @ (initial - final)
    return np.array(
        [final + modes @ (np.exp(-rates * t) * weights) for t in np.atleast_1d(times)]
    )


def time_step_study(experiment: Experiment):
    """Backward Euler and Crank-Nicolson after a power step, against the
    exact semi-discrete solution on the 2 mm mesh of the design with
    inserts; record the table and the orders, and return the steps and the
    errors."""
    design = package("aluminium, copper inserts", THICKNESS_LIMIT, H_MAX)
    system = fem_system(design, mesh_for(design, 0.002))
    initial = np.full(len(system.load), COOLANT)
    exact = semi_discrete_exact(system, initial, STUDY_TIME)[0]
    rows, steps, euler, crank = [], [], [], []
    for count in STEP_FRACTIONS:
        dt = STUDY_TIME / count
        errors = []
        for theta in (1.0, 0.5):
            states = theta_march(
                system.capacity, system.matrix, system.vector, initial, dt, count, theta
            )
            errors.append(np.max(np.abs(states[-1] - exact)))
        steps.append(dt)
        euler.append(errors[0])
        crank.append(errors[1])
        rows.append((count, dt, errors[0], errors[1]))
    experiment.table(
        "time-step-study",
        rows,
        [
            ("steps", "", "d"),
            ("time step", "s", ".4f"),
            ("backward Euler, largest error", "K", ".2e"),
            ("Crank-Nicolson, largest error", "K", ".2e"),
        ],
        "The temperature one second after the dies are switched on, by the "
        "theta method with two choices of theta, against the exact solution "
        "of the same finite-element equations in time (2 mm mesh, the design "
        "with copper inserts on the full flow).",
    )
    # Fitted over the three smallest steps, where both are in their
    # asymptotic range.
    experiment.number("euler-order", fitted_order(steps[-3:], euler[-3:]), ".2f")
    experiment.number("crank-order", fitted_order(steps[-3:], crank[-3:]), ".2f")
    return steps, euler, crank


def explicit_limit(model) -> tuple[float, float]:
    """The explicit step's stability limit of the finite differences,
    measured by bisection on the growth per step of the homogeneous step,
    and the exact discrete limit 2 rho c t / (8 k t / dx^2 + 1 / R_base):
    the highest mode of the insulated grid has the Laplacian eigenvalue
    -8 / dx^2."""
    p = model.package
    exact = (
        2.0
        * model.capacity
        / (
            8.0 * p.material.k * p.thickness / model.grid.spacing**2
            + 1.0 / p.base_resistance
        )
    )

    def growth(dt: float) -> float:
        return explicit_growth(model, dt, 1000)

    return stability_limit(growth, 0.5 * exact, 1.5 * exact, 1e-4 * exact), exact


def explicit_growth(model, dt: float, steps: int) -> float:
    """The growth per explicit step of the finite differences, measured on
    the homogeneous problem (no source, the coolant at zero) from a random
    state: the factor of its fastest-growing mode."""
    homogeneous = replace(
        model,
        source=np.zeros_like(model.source),
        package=replace(model.package, coolant=0.0),
    )
    state = np.random.default_rng(1).standard_normal(len(model.source))
    return growth_per_step(homogeneous.step(dt), state, steps)


def power_step(design: Package):
    """The dies switched on at full power from the coolant temperature, by
    the elements and backward Euler on the 1 mm mesh: the times, the hottest
    junction at each, and the relative gap of the energy balance of each
    step (heat stored plus heat removed against heat generated)."""
    system = fem_system(design, mesh_for(design, SPACING))
    count = round(TRANSIENT_TIME / TRANSIENT_STEP)
    initial = np.full(len(system.load), COOLANT)
    states = theta_march(
        system.capacity, system.matrix, system.vector, initial, TRANSIENT_STEP, count
    )
    stored = np.diff(stored_heat(system, states))
    removed = heat_to_coolant(system, midpoints(states, 1.0)) * TRANSIENT_STEP
    generated = system.load.sum() * TRANSIENT_STEP
    times = TRANSIENT_STEP * np.arange(count + 1)
    curve = junction_maximum(design, *system.mesh.nodes.T, states)
    return times, curve, np.abs(stored + removed - generated) / generated


def explicit_power_step(model, dt: float):
    """The same power step by the explicit finite differences at the step
    ``dt``: the times, the hottest junction, and the energy-balance gaps."""
    count = int(np.ceil(TRANSIENT_TIME / dt))
    initial = np.full(len(model.source), COOLANT)
    states = march(initial, count, model.step(dt))
    stored = np.diff(model.stored_heat(states))
    removed = model.heat_to_coolant(states[:-1]) * dt
    generated = (model.source @ model.grid.areas) * dt
    curve = junction_maximum(model.package, model.grid.x, model.grid.y, states)
    return (
        dt * np.arange(count + 1),
        curve,
        np.abs(stored + removed - generated) / generated,
    )


def settling_time(times, curve) -> float:
    """The first time the hottest junction has risen by 95 per cent of its
    final rise above the coolant."""
    rise = curve[-1] - COOLANT
    return float(times[np.argmax(curve >= COOLANT + 0.95 * rise)])


def transient(experiment: Experiment):
    """The power step of the copper design by the elements (backward Euler)
    and the finite differences (explicit, below the measured limit), and of
    the design with inserts by the elements; record the tables and numbers,
    and return the curves and the energy-balance gaps."""
    copper = package("copper", thickest("copper"), H_MAX)
    inserted = package("aluminium, copper inserts", THICKNESS_LIMIT, H_MAX)
    times, fem_curve, fem_gap = power_step(copper)
    _, insert_curve, insert_gap = power_step(inserted)
    model = finite_differences(copper, SPACING)
    measured, exact = explicit_limit(model)
    dt = 0.9 * measured
    fd_times, fd_curve, fd_gap = explicit_power_step(model, dt)
    experiment.table(
        "explicit-limit",
        [
            (
                1e3 * SPACING,
                1e3 * exact,
                1e3 * measured,
                1e3 * dt,
                1e3 * TRANSIENT_STEP,
                explicit_growth(model, TRANSIENT_STEP, 50),
            )
        ],
        [
            ("spacing", "mm", ".1f"),
            ("exact limit of the explicit step", "ms", ".4f"),
            ("measured limit", "ms", ".4f"),
            ("explicit step used", "ms", ".4f"),
            ("implicit step used", "ms", ".0f"),
            ("growth per explicit step at the implicit step", "", ".3g"),
        ],
        "The largest stable step of the explicit finite differences on the "
        "copper design, exact and measured by bisection on the growth of the "
        "highest mode, and what happens to the explicit step at the step the "
        "implicit elements take.",
    )
    rows = [
        (
            t,
            float(np.interp(t, times, fem_curve)),
            float(np.interp(t, fd_times, fd_curve)),
            float(np.interp(t, times, insert_curve)),
        )
        for t in (0.25, 0.5, 1.0, 2.0, TRANSIENT_TIME)
    ]
    experiment.table(
        "transient",
        rows,
        [
            ("time", "s", ".2f"),
            ("copper: elements, backward Euler", "degrees C", ".2f"),
            ("copper: finite differences, explicit", "degrees C", ".2f"),
            ("copper inserts: elements, backward Euler", "degrees C", ".2f"),
        ],
        "The hottest junction after the dies are switched on at full power, "
        "from the coolant temperature, on the 1 mm mesh and the full flow.",
    )
    gap = np.abs(fem_curve - np.interp(times, fd_times, fd_curve))
    experiment.number("explicit-steps", len(fd_times) - 1, "d")
    experiment.number("implicit-steps", len(times) - 1, "d")
    experiment.number("transient-gap", float(gap.max()), ".2f")
    experiment.number("late-gap", float(gap[times >= 1.0].max()), ".2f")
    experiment.number("settle-copper", settling_time(times, fem_curve), ".2f")
    experiment.number("settle-insert", settling_time(times, insert_curve), ".2f")
    largest = max(fem_gap.max(), fd_gap.max(), insert_gap.max())
    experiment.number("energy-gap", below(largest, 1e-10))
    experiment.number("step-ratio", TRANSIENT_STEP / measured, ".0f")
    curves = (times, fem_curve, fd_times, fd_curve, insert_curve)
    return curves, (fem_gap, fd_gap, insert_gap)


def layout_search(experiment: Experiment):
    """The hottest junction against the separation of the compute dies for
    every material at its thickest admissible spreader on the full flow;
    record the table and the optimum, checked on a finer mesh, and return
    the curves."""
    curves = {}
    rows = []
    for design in DESIGNS:
        low, high = admissible(design)
        allowed = [s for s in SEPARATIONS if low - 1e-9 <= s <= high + 1e-9]
        thickness = thickest(design)
        values = [
            hottest_junction(package(design, thickness, H_MAX, s)) for s in allowed
        ]
        curves[design] = (np.array(allowed), np.array(values))
        best = int(np.argmin(values))
        fine = [
            hottest_junction(package(design, thickness, H_MAX, s), 0.0005)
            for s in allowed[max(best - 1, 0) : best + 2]
        ]
        rows.append(
            (
                design,
                1e3 * low,
                1e3 * high,
                1e3 * allowed[best],
                values[best],
                values[0],
                "yes" if int(np.argmin(fine)) == min(best, 1) else "no",
            )
        )
    experiment.table(
        "layout",
        rows,
        [
            ("design", "", ""),
            ("smallest separation allowed", "mm", ".0f"),
            ("largest separation allowed", "mm", ".0f"),
            ("best separation", "mm", ".0f"),
            ("hottest junction there", "degrees C", ".2f"),
            ("hottest junction, dies closest", "degrees C", ".2f"),
            ("same optimum on the 0.5 mm mesh", "", ""),
        ],
        "The search over the admissible layouts: the hottest junction at every "
        "separation of the compute dies (2 mm apart) for each material at its "
        "thickest allowed spreader on the full flow.",
    )
    experiment.number("best-separation", rows[0][3], ".0f")
    return curves


def bounds(experiment: Experiment) -> None:
    """The hottest junction of the design with inserts against the thickness
    and against the cold-plate coefficient: both only lower it, so the
    optimum lies on the limits; record the table."""
    rows = []
    for thickness in (0.001, 0.002, THICKNESS_LIMIT):
        rows.append(
            (
                1e3 * thickness,
                1e3 * package("aluminium, copper inserts", thickness, H_MAX).mass,
                *[
                    hottest_junction(package("aluminium, copper inserts", thickness, h))
                    for h in COOLING.values()
                ],
            )
        )
    experiment.table(
        "bounds",
        rows,
        [
            ("thickness", "mm", ".0f"),
            ("mass", "g", ".1f"),
            *[
                (f"hottest junction, h = {h:g}", "degrees C", ".1f")
                for h in COOLING.values()
            ],
        ],
        "The hottest junction of the aluminium spreader with copper inserts, "
        "dies 32 mm apart, against its thickness and the cold-plate coefficient.",
    )


def sensitivity(design: Package, solver) -> list[tuple[str, float, float]]:
    """The change of the hottest junction (K) when each uncertain input is
    lowered and raised by ``CHANGE``, the others held."""

    def scaled_dies(factor: float) -> tuple[Die, ...]:
        return tuple(
            replace(d, power=d.power * factor) if d.name.startswith("compute") else d
            for d in design.dies
        )

    def scaled(material: Material, factor: float) -> Material:
        return replace(material, k=material.k * factor)

    changes = {
        "compute-die power": lambda f: replace(design, dies=scaled_dies(f)),
        "cold-plate coefficient h": lambda f: replace(design, h=design.h * f),
        "contact, die to lid": lambda f: replace(
            design, die_contact=design.die_contact * f
        ),
        "contact, lid to cold plate": lambda f: replace(
            design, plate_contact=design.plate_contact * f
        ),
        "conductivity of the spreader": lambda f: replace(
            design, material=scaled(design.material, f)
        ),
    }
    if design.insert is not None:
        changes["conductivity of the inserts"] = lambda f: replace(
            design, insert=scaled(design.insert, f)
        )
    base = solver(design)
    return [
        (name, solver(change(1.0 - CHANGE)) - base, solver(change(1.0 + CHANGE)) - base)
        for name, change in changes.items()
    ]


def sensitivity_study(experiment: Experiment):
    """The sensitivity of the copper design by both methods and of the design
    with inserts by the elements; record the table and the largest swing,
    and return the three lists."""
    copper = package("copper", thickest("copper"), H_MAX)
    inserted = package("aluminium, copper inserts", THICKNESS_LIMIT, H_MAX)
    fem = sensitivity(copper, hottest_junction)
    fd = sensitivity(copper, fd_hottest_junction)
    ins = sensitivity(inserted, hottest_junction)
    rows = []
    for name, low, high in ins:
        match = [(a, b) for n, a, b in fem if n == name]
        match_fd = [(a, b) for n, a, b in fd if n == name]
        rows.append(
            (
                name,
                low,
                high,
                *(match[0] if match else ("", "")),
                *(match_fd[0] if match_fd else ("", "")),
            )
        )
    experiment.table(
        "sensitivity",
        [
            tuple(f"{v:+.2f}" if isinstance(v, float) else v for v in row)
            for row in rows
        ],
        [
            ("input changed", "", ""),
            ("copper inserts, elements: at -20 %", "K", ""),
            ("at +20 %", "K", ""),
            ("copper, elements: at -20 %", "K", ""),
            ("at +20 %", "K", ""),
            ("copper, finite differences: at -20 %", "K", ""),
            ("at +20 %", "K", ""),
        ],
        "The change of the hottest junction when one input is lowered or "
        "raised by a fifth, the others held, for the two designs on the full "
        "flow (1 mm mesh); the inserts have no finite-difference baseline.",
    )
    swings = sorted((max(abs(low), abs(high)) for _, low, high in ins), reverse=True)
    swing = swings[0]
    experiment.number("second-swing", swings[1], ".1f")
    agreement = max(
        max(abs(a[1] - b[1]), abs(a[2] - b[2])) for a, b in zip(fem, fd, strict=True)
    )
    experiment.number("largest-swing", swing, ".1f")
    experiment.number("sensitivity-agreement", agreement, ".2f")
    leader = max(ins, key=lambda row: max(abs(row[1]), abs(row[2])))[0]
    experiment.number("leading-input", leader)
    return fem, fd, ins


def trade_off(experiment: Experiment, gap: float) -> None:
    """Every scenario against the constraints; record the trade-off table and
    the recommendation the stated rule selects: of the designs that meet
    every constraint, the coolest, except that designs whose hottest
    junctions differ by less than ``gap``, the plate model's largest gap to
    the cross-section, are not told apart by the model, and of those the
    lightest is chosen."""
    scenarios = []
    for design in DESIGNS:
        for cooling, h in COOLING.items():
            scenarios.append((design, cooling, thickest(design), h, 0.5 * WIDTH))
    scenarios.append(
        (
            "aluminium, copper inserts",
            "cold plate, full flow",
            THICKNESS_LIMIT,
            H_MAX,
            admissible("aluminium, copper inserts")[0],
        )
    )
    scenarios.append(
        ("copper", "cold plate, full flow", THICKNESS_LIMIT, H_MAX, 0.5 * WIDTH)
    )
    rows, feasible = [], []
    for design, cooling, thickness, h, separation in scenarios:
        p = package(design, thickness, h, separation)
        hottest = hottest_junction(p)
        low, high = admissible(design)
        broken = [
            name
            for name, ok in (
                ("junction", hottest <= JUNCTION_LIMIT),
                ("mass", p.mass <= MASS_LIMIT + 1e-12),
                ("thickness", thickness <= THICKNESS_LIMIT + 1e-12),
                ("heat removal", h <= H_MAX),
                ("size", low - 1e-9 <= separation <= high + 1e-9),
            )
            if not ok
        ]
        label = (
            f"{design}, {1e3 * thickness:.2f} mm, {cooling},"
            f" dies {1e3 * separation:.0f} mm apart"
        )
        rows.append(
            (
                design,
                cooling,
                1e3 * thickness,
                1e3 * p.mass,
                1e3 * separation,
                hottest,
                JUNCTION_LIMIT - hottest,
                "meets all" if not broken else "breaks " + ", ".join(broken),
            )
        )
        if not broken:
            feasible.append((hottest, label, p.mass))
    experiment.table(
        "trade-off",
        rows,
        [
            ("spreader", "", ""),
            ("cooling", "", ""),
            ("thickness", "mm", ".2f"),
            ("mass", "g", ".1f"),
            ("die separation", "mm", ".0f"),
            ("hottest junction", "degrees C", ".1f"),
            ("margin to the limit", "K", ".1f"),
            ("constraints", "", ""),
        ],
        "Every scenario: the material and thickness of the spreader, the "
        "cooling, the layout, the hottest junction (1 mm mesh), its margin to "
        f"the limit of {JUNCTION_LIMIT:g} degrees C, and the constraints it "
        "meets or breaks.",
    )
    feasible.sort()
    coolest = feasible[0][0]
    tied = [f for f in feasible if f[0] - coolest < gap]
    chosen = min(tied, key=lambda f: f[2])
    other = min((f for f in feasible if f is not chosen), key=lambda f: f[0])
    experiment.number("recommended", chosen[1])
    experiment.number("recommended-junction", chosen[0], ".1f")
    experiment.number("recommended-margin", JUNCTION_LIMIT - chosen[0], ".1f")
    experiment.number("recommended-mass", 1e3 * chosen[2], ".1f")
    experiment.number("runner-up", other[1])
    experiment.number("runner-up-difference", abs(other[0] - chosen[0]), ".1f")
    experiment.number(
        "runner-up-direction", "warmer" if other[0] > chosen[0] else "cooler"
    )
    experiment.number("runner-up-mass", 1e3 * other[2], ".1f")
    experiment.number("feasible-count", len(feasible), "d")
    experiment.number("scenario-count", len(rows), "d")


def simple_estimates(experiment: Experiment) -> None:
    """Two estimates without the field: the power spread evenly over the
    spreader, and every die cooled straight down with no spreading; record
    the table against the elements."""
    rows = []
    for design in ("aluminium", "copper", "aluminium, copper inserts"):
        p = package(design, thickest(design), H_MAX)
        compute = p.dies[0]
        r = compute.region
        below = p.resistance_below(p.conductivity(0.5 * (r.x0 + r.x1), 0.5 * HEIGHT))
        even = (
            COOLANT
            + p.power / (WIDTH * HEIGHT) * p.base_resistance
            + compute.flux * p.die_resistance(compute)
        )
        straight = COOLANT + compute.flux * (p.die_resistance(compute) + below)
        rows.append((design, even, hottest_junction(p), straight))
    experiment.number("even-error", min(row[2] - row[1] for row in rows), ".0f")
    experiment.number("straight-error", min(row[3] - row[2] for row in rows), ".0f")
    experiment.table(
        "estimates",
        rows,
        [
            ("spreader", "", ""),
            ("power spread evenly", "degrees C", ".1f"),
            ("finite elements", "degrees C", ".1f"),
            ("no spreading", "degrees C", ".1f"),
        ],
        "The hottest junction on the full flow by two estimates without a "
        "temperature field, against the finite-element solution.",
    )


def draw_package_temperature() -> Figure:
    """The steady temperature of the plain aluminium spreader on the nominal
    flow and of the recommended design, on one colour scale, with the dies
    and inserts outlined."""
    designs = [
        (
            "aluminium, 3 mm, nominal flow",
            package("aluminium", THICKNESS_LIMIT, COOLING["cold plate, nominal flow"]),
        ),
        (
            "aluminium with copper inserts, 3 mm, full flow",
            package("aluminium, copper inserts", THICKNESS_LIMIT, H_MAX),
        ),
    ]
    solved = [(title, p, *solve(p)[:2]) for title, p in designs]
    low = min(t.min() for *_, t in solved)
    high = max(t.max() for *_, t in solved)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
    for ax, (title, p, system, temperature) in zip(axes, solved, strict=True):
        image = ax.tripcolor(
            Triangulation(*(1e3 * system.mesh.nodes.T), system.mesh.triangles),
            temperature,
            shading="gouraud",
            cmap="viridis",
            vmin=low,
            vmax=high,
        )
        for die in p.dies:
            r = die.region
            ax.add_patch(
                Rectangle(
                    (1e3 * r.x0, 1e3 * r.y0),
                    1e3 * (r.x1 - r.x0),
                    1e3 * (r.y1 - r.y0),
                    fill=False,
                    edgecolor="white",
                    linestyle="--",
                    linewidth=0.9,
                )
            )
        for r in p.inserts:
            ax.add_patch(
                Rectangle(
                    (1e3 * r.x0, 1e3 * r.y0),
                    1e3 * (r.x1 - r.x0),
                    1e3 * (r.y1 - r.y0),
                    fill=False,
                    edgecolor="white",
                    linestyle=":",
                    linewidth=1.2,
                )
            )
        ax.set_aspect("equal")
        ax.set_title(title, fontsize="small")
        ax.set_xlabel("x (mm)")
    axes[0].set_ylabel("y (mm)")
    fig.colorbar(
        image, ax=axes, label="plate temperature (°C) (false colour)", shrink=0.85
    )
    return fig


def draw_package_transient(curves, gaps) -> Figure:
    """The hottest junction after the power step, both methods, and the
    relative energy-balance gap of every step."""
    times, fem_curve, fd_times, fd_curve, insert_curve = curves
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.4, 3.4))
    left.plot(
        fd_times,
        fd_curve,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="copper, finite differences, explicit",
    )
    left.plot(
        times,
        fem_curve,
        color=FIGURE_COLOURS[0],
        marker="o",
        markevery=10,
        markersize=3.5,
        linestyle="none",
        label="copper, elements, backward Euler",
    )
    left.plot(
        times,
        insert_curve,
        color=FIGURE_COLOURS[4],
        linestyle="-.",
        label="copper inserts, elements",
    )
    left.axhline(JUNCTION_LIMIT, color=FIGURE_COLOURS[2], linestyle=":", linewidth=1.0)
    left.annotate(
        "limit",
        (times[-1], JUNCTION_LIMIT),
        xytext=(0, 3),
        textcoords="offset points",
        ha="right",
        color=FIGURE_COLOURS[2],
        fontsize="small",
    )
    left.set_xlabel("time after switch-on (s)")
    left.set_ylabel("hottest junction (°C)")
    left.legend(frameon=False, fontsize="small", loc="lower right")
    fem_gap, fd_gap, insert_gap = gaps
    floor = 1e-17  # a gap of exactly zero cannot be drawn on a log axis
    right.semilogy(
        np.arange(1, len(fem_gap) + 1),
        np.maximum(fem_gap, floor),
        color=FIGURE_COLOURS[0],
        marker="o",
        markersize=2.5,
        linestyle="none",
        label="copper, elements",
    )
    right.semilogy(
        np.arange(1, len(fd_gap) + 1),
        np.maximum(fd_gap, floor),
        color=FIGURE_COLOURS[1],
        marker=".",
        markersize=1.5,
        linestyle="none",
        label="copper, finite differences",
    )
    right.semilogy(
        np.arange(1, len(insert_gap) + 1),
        np.maximum(insert_gap, floor),
        color=FIGURE_COLOURS[4],
        marker="s",
        markersize=2.0,
        linestyle="none",
        label="copper inserts, elements",
    )
    right.axhline(
        1e-10,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        linewidth=1.0,
        label="tolerance stated, 1e-10",
    )
    right.set_xlabel("step number")
    right.set_ylabel("relative energy-balance gap (dimensionless)")
    right.legend(frameon=False, fontsize="small", loc="upper right")
    low, high = right.get_ylim()
    right.set_ylim(low, high * 1e3)
    fig.tight_layout()
    return fig


def draw_package_refinement(space, time) -> Figure:
    """Log-log: the cosine-mode error against the spacing for both methods,
    and the time-step error of the two theta methods, with reference
    slopes."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.4, 3.5))
    spacings, fem, fd = (np.array(v) for v in space)
    h = 1e3 * spacings
    left.loglog(h, fem, color=FIGURE_COLOURS[0], marker="o", label="finite elements")
    left.loglog(
        h,
        fd,
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="--",
        label="finite differences",
    )
    left.loglog(
        h,
        0.5 * min(fem[0], fd[0]) * (h / h[0]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="reference, slope two",
    )
    left.set_xlabel("spacing (mm)")
    left.set_ylabel("rms error over the plate (K)")
    steps, euler, crank = (np.array(v) for v in time)
    right.loglog(
        steps, euler, color=FIGURE_COLOURS[0], marker="o", label="backward Euler"
    )
    right.loglog(
        steps,
        crank,
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="--",
        label="Crank-Nicolson",
    )
    right.loglog(
        steps,
        0.5 * euler[-1] * (steps / steps[-1]),
        color=FIGURE_COLOURS[2],
        linestyle="-.",
        label="reference, slope one",
    )
    right.loglog(
        steps,
        0.5 * crank[-1] * (steps / steps[-1]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="reference, slope two",
    )
    right.set_xlabel("time step (s)")
    right.set_ylabel("largest error (K)")
    for ax, x in ((left, h), (right, steps)):
        ax.set_xticks(x, labels=[f"{value:.3g}" for value in x])
        ax.minorticks_off()
        low, high = ax.get_ylim()
        ax.set_ylim(low, high * 30)
        ax.legend(frameon=False, fontsize="small", loc="upper left")
    fig.tight_layout()
    return fig


def draw_package_layout(curves) -> Figure:
    """The hottest junction against the die separation for the three
    spreaders, the limit and the optimum of each marked."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    styles = {
        "aluminium": (FIGURE_COLOURS[0], "o", "-"),
        "copper": (FIGURE_COLOURS[1], "s", "--"),
        "aluminium, copper inserts": (FIGURE_COLOURS[4], "^", "-."),
    }
    for design, (separations, values) in curves.items():
        colour, marker, line = styles[design]
        label = f"{design}, {1e3 * thickest(design):.2f} mm"
        ax.plot(
            1e3 * separations,
            values,
            color=colour,
            marker=marker,
            linestyle=line,
            markersize=4,
            label=label,
        )
        best = int(np.argmin(values))
        ax.plot(
            1e3 * separations[best],
            values[best],
            marker=marker,
            markersize=10,
            markerfacecolor="none",
            color=colour,
            linestyle="none",
        )
    ax.axhline(JUNCTION_LIMIT, color=FIGURE_COLOURS[2], linestyle=":", linewidth=1.0)
    ax.annotate(
        "junction limit",
        (1e3 * SEPARATIONS[0], JUNCTION_LIMIT),
        xytext=(2, 3),
        textcoords="offset points",
        color=FIGURE_COLOURS[2],
        fontsize="small",
    )
    ax.set_xlabel("separation of the compute dies, centre to centre (mm)")
    ax.set_ylabel("hottest junction (°C)")
    ax.legend(frameon=False, fontsize="small", loc="upper center")
    low, high = ax.get_ylim()
    ax.set_ylim(low, high + 0.35 * (high - low))
    fig.tight_layout()
    return fig


def draw_package_sensitivity(fem, fd, ins) -> Figure:
    """Tornado charts: the change of the hottest junction for each input at
    minus and plus 20 per cent; the copper design by both methods, and the
    design with inserts by the elements."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.6, 3.6), sharex=True)
    titles = (
        f"copper, {1e3 * thickest('copper'):.2f} mm",
        f"copper inserts, {1e3 * THICKNESS_LIMIT:.2f} mm",
    )
    for ax, rows, title in ((left, fem, titles[0]), (right, ins, titles[1])):
        names = [row[0] for row in rows]
        y = np.arange(len(rows))[::-1]
        ax.barh(
            y,
            [row[1] for row in rows],
            color=FIGURE_COLOURS[0],
            hatch="//",
            edgecolor="white",
            label="-20 %, elements",
        )
        ax.barh(
            y,
            [row[2] for row in rows],
            color=FIGURE_COLOURS[1],
            label="+20 %, elements",
        )
        ax.set_yticks(y, labels=names, fontsize="small")
        ax.axvline(0.0, color=FIGURE_COLOURS[2], linewidth=0.8)
        ax.set_title(title, fontsize="small")
        ax.set_xlabel("change of the hottest junction (K)")
    y = np.arange(len(fd))[::-1]
    left.plot(
        [row[1] for row in fd],
        y,
        marker="x",
        color="black",
        linestyle="none",
        label="finite differences",
    )
    left.plot([row[2] for row in fd], y, marker="x", color="black", linestyle="none")
    handles, labels = left.get_legend_handles_labels()
    fig.legend(
        handles, labels, frameon=False, fontsize="small", loc="lower center", ncol=3
    )
    fig.tight_layout(rect=(0.0, 0.08, 1.0, 1.0))
    return fig


def burst(experiment: Experiment) -> None:
    """Exercise 1: a workload burst, the compute dies at one and a half times
    their power for two seconds from the steady state at full power, on the
    recommended design; record the table."""
    design = package("aluminium, copper inserts", THICKNESS_LIMIT, H_MAX)
    surge = replace(
        design,
        dies=tuple(
            replace(d, power=1.5 * d.power) if d.name.startswith("compute") else d
            for d in design.dies
        ),
    )
    system, temperature, _ = solve(design)
    surged = fem_system(surge, system.mesh)
    count = round(2.0 / TRANSIENT_STEP)
    states = theta_march(
        surged.capacity,
        surged.matrix,
        surged.vector,
        temperature,
        TRANSIENT_STEP,
        count,
    )
    curve = junction_maximum(surge, *system.mesh.nodes.T, states)
    _, _, surge_steady = solve(surge)
    rows = [
        (t, float(np.interp(t, TRANSIENT_STEP * np.arange(count + 1), curve)))
        for t in (0.0, 0.5, 1.0, 2.0)
    ]
    rows.append(("steady at the burst power", surge_steady))
    experiment.table(
        "burst",
        [(t if isinstance(t, str) else f"{t:.1f} s", v) for t, v in rows],
        [
            ("time after the burst starts", "", ""),
            ("hottest junction", "degrees C", ".1f"),
        ],
        "The recommended design during a two-second burst at one and a half "
        "times the compute power, from the steady state at full power.",
    )


def coolant_rise(experiment: Experiment) -> None:
    """Exercise 2: the rise of the coolant temperature across the cold plate
    for several flow rates of water, P / (m_dot c_p); record the table."""
    power = package("copper", 0.002, H_MAX).power
    water_c, water_rho = 4180.0, 997.0  # J/(kg K), kg/m^3
    rows = []
    for litres_per_minute in (0.5, 1.0, 2.0, 4.0):
        flow = litres_per_minute * 1e-3 / 60.0 * water_rho
        rows.append((litres_per_minute, power / (flow * water_c)))
    experiment.table(
        "coolant-rise",
        rows,
        [
            ("water flow", "litres per minute", ".1f"),
            ("coolant temperature rise", "K", ".1f"),
        ],
        "How much the water warms as it carries the package's power away, for "
        "four flow rates.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    requirements(experiment)
    space = cosine_mode(experiment)
    mesh_study(experiment)
    insert_refinement(experiment)
    gap = section_check(experiment)
    time = time_step_study(experiment)
    experiment.figure(
        "fig-package-refinement", partial(draw_package_refinement, space, time)
    )
    curves, gaps = transient(experiment)
    experiment.figure(
        "fig-package-transient", partial(draw_package_transient, curves, gaps)
    )
    layouts = layout_search(experiment)
    experiment.figure("fig-package-layout", partial(draw_package_layout, layouts))
    bounds(experiment)
    fem, fd, ins = sensitivity_study(experiment)
    experiment.figure(
        "fig-package-sensitivity", partial(draw_package_sensitivity, fem, fd, ins)
    )
    trade_off(experiment, gap)
    experiment.figure("fig-package-temperature", draw_package_temperature)
    simple_estimates(experiment)
    burst(experiment)
    coolant_rise(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
