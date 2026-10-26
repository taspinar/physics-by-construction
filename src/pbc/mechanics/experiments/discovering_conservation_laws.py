"""The experiment of the lesson "Discovering conservation laws and invariants".

Conserved quantities found from trajectories, without an equation of motion
(``pbc.discovery.invariants``): the baseline on a test oscillator, where
it meets a drift artefact and coincidences; a language model's recorded run
on a box with a hidden force (``pbc.discovery.invariant_lab``), its
candidates judged by the build on trajectories nobody started, beside the
baseline with the same budget; the symmetry of the box seen from its
trajectories; the heavy top of the rotational-motion lesson; and the totals
of Burgers' equation in finite volumes. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.discovering_conservation_laws out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.invariant_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery.invariant_lab import (
    BUDGET,
    MAX_CANDIDATES,
    MAX_STEPS,
    TOLERANCE,
    box,
    replay_run,
)
from pbc.discovery.invariants import (
    HALF,
    OWN,
    PLANAR_LIBRARY,
    PLANAR_TERMS,
    REFERENCE,
    AxesBox,
    CentralBox,
    box_allowlist,
    find_invariants,
    judge,
    rotation_defect,
)
from pbc.experiment import Experiment, main
from pbc.fluids.burgers import godunov_flux, max_speed
from pbc.fluids.finite_volume import conservative_update, interface_fluxes, periodic
from pbc.mechanics.rigid_body import Top, simulate_top, tilted_start

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.invariant_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/11-discovering-conservation-laws"

# region: test-system
# The test oscillator: a different stiffness along each axis, integrated by
# symplectic Euler at a coarse step. Its truth is known and shown.
KX, KY = 1.0, 2.25  # N/m per kg
TEST_STARTS = (
    (1.0, 0.3, -0.2, 0.8),
    (-0.6, 1.1, 0.9, 0.2),
    (0.4, -1.2, 1.3, -0.5),
    (1.3, 0.9, -0.5, -1.0),
    (-1.1, -0.4, -0.9, 1.2),
    (0.2, 0.6, 1.4, 0.4),
)
# Starts on the x axis, at rest in y: a set that hides the y motion.
AXIS_STARTS = ((1.0, 0.0, 0.0, 0.0), (0.5, 0.0, 1.0, 0.0), (-1.2, 0.0, 0.3, 0.0))
# endregion: test-system
# The baseline on the box of the agent: the same budget, at random starts.
BASELINE_SEED = 1
# A start and an angle of the symmetry test, within the bounds when turned.
SYMMETRY_START, SYMMETRY_ANGLE = (1.0, 0.2, 0.1, 0.8), 0.7

# The heavy top of the rotational-motion lesson, integrated by the classical
# Runge-Kutta method (pbc.mechanics.rigid_body); kg, m, kg m².
TOP = Top(mass=1.0, length=0.2, i1=0.05, i3=0.02)
TOP_STARTS = ((0.5, 30.0, 0.0), (0.8, 25.0, 1.0), (0.3, 40.0, -0.5), (1.0, 20.0, 2.0))
TOP_HELD_OUT = ((0.6, 35.0, 0.5), (0.9, 22.0, -1.0), (0.4, 28.0, 1.5))
TOP_SETTINGS = {OWN: 0.004, HALF: 0.002, REFERENCE: 0.001}  # s
TOP_TIME, TOP_EVERY = 1.5, 0.1  # s
# The terms of the top's library: the angular momentum L in space and the
# symmetry axis e3 in space, state columns (Lx, Ly, Lz, e3x, e3y, e3z).
TOP_LIBRARY = {
    "Lx": lambda s: s[:, 0],
    "Ly": lambda s: s[:, 1],
    "Lz": lambda s: s[:, 2],
    "e3x": lambda s: s[:, 3],
    "e3y": lambda s: s[:, 4],
    "e3z": lambda s: s[:, 5],
    "L·e3": lambda s: np.sum(s[:, :3] * s[:, 3:], axis=1),
    "|L|²": lambda s: np.sum(s[:, :3] ** 2, axis=1),
    "(L·e3)²": lambda s: np.sum(s[:, :3] * s[:, 3:], axis=1) ** 2,
    "e3x²": lambda s: s[:, 3] ** 2,
    "e3y²": lambda s: s[:, 4] ** 2,
    "e3z²": lambda s: s[:, 5] ** 2,
}

# Burgers' equation on a periodic interval of length one from
# u = 1 + 0.5 sin(2 pi x): Godunov's flux, before and after the shock forms.
BURGERS_AMPLITUDE = 0.5
BURGERS_CELLS = (50, 100, 200, 400)
BURGERS_COURANT = 0.5
BEFORE, AFTER = 0.25, 0.8  # s; the shock forms at 1 / (pi amplitude 2) ≈ 0.318


# A coefficient below this fraction of a candidate's largest is not written.
SHOWN = 1e-3


def shown(ratio):
    """A ratio as the page prints it: what round-off or a tight integration
    sets is a bound, not digits another machine would change."""
    if ratio is None:
        return "terms vanish"
    for bound in (1e-12, 1e-8):
        if ratio < bound:
            return f"below {bound:g}"
    return f"{ratio:.2g}"


def written(candidate, symbols=PLANAR_TERMS, digits=4):
    """A candidate, a mapping from term to coefficient, as a sum."""
    parts = []
    largest = max(abs(value) for value in candidate.values())
    for term, value in candidate.items():
        if abs(value) < SHOWN * largest:
            continue
        number = f"{abs(value):.{digits}g}"
        sign = "-" if value < 0 else "+"
        word = symbols.get(term, term)
        parts.append(f"{sign} {'' if number == '1' else number + ' '}{word}")
    text = " ".join(parts) or "0"
    return text[2:] if text.startswith("+ ") else text


def verdict_row(name, candidate, verdict, trained=True):
    return (
        name,
        written(candidate),
        shown(verdict.training) if trained else "none",
        shown(verdict.settings[OWN]),
        shown(verdict.settings[HALF]),
        shown(verdict.settings[REFERENCE]),
        verdict.verdict,
    )


VERDICT_COLUMNS = [
    ("candidate", "", ""),
    ("sum of terms", "", ""),
    ("its trajectories", "", ""),
    ("held out, own step", "", ""),
    ("held out, half step", "", ""),
    ("held out, reference", "", ""),
    ("verdict", "", ""),
]


def test_system(experiment: Experiment):
    """The baseline on the test oscillator at its own setting, its verdicts,
    and the baseline again on the reference trajectories; record the
    tables and return the ratios of the figure."""
    oscillator = AxesBox(kx=KX, ky=KY, budget=len(TEST_STARTS))
    data = [oscillator.trajectory(*start) for start in TEST_STARTS]
    found = find_invariants(PLANAR_LIBRARY, data, TOLERANCE)
    rows, ratios = [], {}
    for i, row in enumerate(found.candidates, start=1):
        verdict = oscillator.judge(row, TOLERANCE, data)
        rows.append(verdict_row(f"own step {i}", found.candidate(i - 1), verdict))
        ratios[f"test, own step {i}"] = verdict.settings
    reference = find_invariants(
        PLANAR_LIBRARY, oscillator.held_out(REFERENCE), TOLERANCE
    )
    for i, row in enumerate(reference.candidates, start=1):
        verdict = oscillator.judge(row, TOLERANCE)
        rows.append(
            verdict_row(f"reference {i}", reference.candidate(i - 1), verdict, False)
        )
        ratios[f"test, reference {i}"] = verdict.settings
    experiment.table(
        "test-system",
        rows,
        VERDICT_COLUMNS,
        "The baseline on the test oscillator: at the box's own step it finds two"
        " combinations, which the build judges on held-out trajectories; at the"
        " reference it finds two others.",
    )
    experiment.number("test-dt", oscillator.settings[OWN].dt, "g")
    return ratios


def coincidences(experiment: Experiment) -> None:
    """The baseline on starts along the x axis, and the verdict of the
    build on what it found; record the table."""
    oscillator = AxesBox(kx=KX, ky=KY, budget=len(AXIS_STARTS))
    data = [oscillator.trajectory(*start) for start in AXIS_STARTS]
    found = find_invariants(PLANAR_LIBRARY, data, TOLERANCE)
    rows = []
    for term in found.constant_terms:
        c = np.array([1.0 if t == term else 0.0 for t in PLANAR_LIBRARY])
        verdict = oscillator.judge(c, TOLERANCE, data)
        rows.append((PLANAR_TERMS[term], "vanishes", verdict.verdict))
    for i, row in enumerate(found.candidates):
        verdict = oscillator.judge(row, TOLERANCE, data)
        rows.append(
            (written(found.candidate(i)), shown(verdict.training), verdict.verdict)
        )
    experiment.table(
        "coincidences",
        rows,
        [
            ("found on the axis", "", ""),
            ("its ratio there", "", ""),
            ("verdict", "", ""),
        ],
        "The baseline on three starts along the x axis of the test oscillator,"
        " and the build's verdict on trajectories off the axis.",
    )
    experiment.number("axis-found", len(found.constant_terms) + len(found.candidates))


def agent_verdicts(experiment: Experiment, score):
    """The agent's submitted candidates and the build's verdicts; record the
    table and return the ratios of the figure."""
    rows, ratios = [], {}
    for i, (candidate, verdict) in enumerate(
        zip(score.candidates, score.verdicts, strict=True), start=1
    ):
        rows.append(verdict_row(f"agent {i}", candidate, verdict))
        ratios[f"agent {i}"] = verdict.settings
    energy = score.verdicts[0].settings
    experiment.number("energy-factor", energy[OWN] / energy[HALF], ".2g")
    experiment.table(
        "agent-verdicts",
        rows,
        VERDICT_COLUMNS,
        "The agent's candidates judged by the build: the ratio on its own"
        " trajectories, and on held-out trajectories at three integration settings.",
    )
    return ratios


def baseline_on_the_box(experiment: Experiment):
    """The baseline with the agent's budget, at random starts within the
    bounds, on a fresh box; record the table and return the ratios of the
    figure."""
    world = box()
    rng = np.random.default_rng(BASELINE_SEED)
    data = [
        world.trajectory(*rng.uniform(-world.bound, world.bound, 4))
        for _ in range(BUDGET)
    ]
    found = find_invariants(PLANAR_LIBRARY, data, TOLERANCE)
    rows, ratios = [], {}
    for i, row in enumerate(found.candidates, start=1):
        verdict = world.judge(row, TOLERANCE, data)
        rows.append(verdict_row(f"baseline {i}", found.candidate(i - 1), verdict))
        ratios[f"baseline {i}"] = verdict.settings
    experiment.table(
        "box-baseline",
        rows,
        VERDICT_COLUMNS,
        f"The baseline on {BUDGET} trajectories of the same box from random"
        " starts, judged by the build on the same held-out trajectories.",
    )
    experiment.number("baseline-found", len(found.candidates))
    return ratios


def symmetry(experiment: Experiment) -> None:
    """The rotation test on the box and on the test oscillator; record the
    table."""
    central = rotation_defect(box(budget=2), SYMMETRY_START, SYMMETRY_ANGLE)
    axes = rotation_defect(
        AxesBox(kx=KX, ky=KY, budget=2), SYMMETRY_START, SYMMETRY_ANGLE
    )
    experiment.table(
        "symmetry",
        [
            ("the box of the agent", shown(central)),
            ("the test oscillator", shown(axes)),
        ],
        [("system", "", ""), ("rotation defect", "", "")],
        "The largest difference between the trajectory of a start turned by"
        f" {SYMMETRY_ANGLE:g} rad and the turned trajectory, relative to the motion.",
    )


def top_states(start, dt):
    """The angular momentum and the axis of the top in space at the sampled
    times, from ``start`` (tilt in rad, spin and precession in rad/s)."""
    q, momentum = tilted_start(TOP, *start)
    steps = round(TOP_TIME / dt)
    motion = simulate_top(TOP, q, momentum, dt, steps)
    every = np.arange(0, steps + 1, round(TOP_EVERY / dt))
    return np.hstack([motion.momentum[every], motion.axes()[every]])


def top_invariants(experiment: Experiment) -> None:
    """The baseline on the top and the build's verdicts; record the table."""
    data = [top_states(start, TOP_SETTINGS[OWN]) for start in TOP_STARTS]
    held_out = {
        name: [top_states(start, dt) for start in TOP_HELD_OUT]
        for name, dt in TOP_SETTINGS.items()
    }
    found = find_invariants(TOP_LIBRARY, data, TOLERANCE)
    rows = []
    for i, row in enumerate(found.candidates):
        verdict = judge(row, TOP_LIBRARY, data, held_out, OWN, REFERENCE, TOLERANCE)
        rows.append(
            (
                written(found.candidate(i), {}),
                shown(verdict.settings[REFERENCE]),
                shown(verdict.between),
                verdict.verdict,
            )
        )
    experiment.table(
        "top",
        rows,
        [
            ("found", "", ""),
            ("ratio, held out", "", ""),
            ("spread between trajectories", "", ""),
            ("verdict", "", ""),
        ],
        "The baseline on four trajectories of the heavy symmetric top, judged on"
        " three held-out ones.",
    )
    experiment.number("top-found", len(found.candidates))
    experiment.number(
        "top-coefficient", 1 / (2 * TOP.i1 * TOP.mass * TOP.g * TOP.length), ".5g"
    )


def burgers_totals(cells, t_end):
    """The times and the totals of u, u², and u³ (each the sum over the cells
    times their width) of Burgers' equation in ``cells`` finite volumes, up
    to ``t_end``."""
    dx = 1.0 / cells
    x = (np.arange(cells) + 0.5) * dx
    u = 1.0 + BURGERS_AMPLITUDE * np.sin(2 * np.pi * x)
    t, times, totals = 0.0, [0.0], [[np.sum(u**p) * dx for p in (1, 2, 3)]]
    while t < t_end:
        dt = min(BURGERS_COURANT * dx / max_speed(u), t_end - t)
        u = conservative_update(u, interface_fluxes(u, godunov_flux, periodic), dt, dx)
        t = t_end if t + dt >= t_end else t + dt
        times.append(t)
        totals.append([np.sum(u**p) * dx for p in (1, 2, 3)])
    return np.array(times), np.array(totals)


def burgers(experiment: Experiment) -> None:
    """The relative change of each total before and after the shock, for
    each number of cells; record the table."""
    rows = []
    for cells in BURGERS_CELLS:
        row = [cells]
        for t_end in (BEFORE, AFTER):
            _, totals = burgers_totals(cells, t_end)
            change = np.abs(totals[-1] - totals[0]) / np.abs(totals[0])
            row += [shown(change[0]), f"{change[1]:.3g}"]
        rows.append(tuple(row))
    experiment.table(
        "burgers",
        rows,
        [
            ("cells", "", "d"),
            (f"total of u, t = {BEFORE:g} s", "", ""),
            (f"total of u², t = {BEFORE:g} s", "", ""),
            (f"total of u, t = {AFTER:g} s", "", ""),
            (f"total of u², t = {AFTER:g} s", "", ""),
        ],
        "The relative change of two totals of Burgers' equation in finite"
        " volumes, before the shock forms and after.",
    )
    experiment.number("burgers-breaking", 1 / (2 * np.pi * BURGERS_AMPLITUDE), ".3f")


def draw_verdicts(ratios) -> Figure:
    """The conservation ratio of each candidate on the held-out trajectories
    at the three integration settings, on a logarithmic axis, with the
    tolerance."""
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    names = list(ratios)
    styles = {
        OWN: ("o", FIGURE_COLOURS[0]),
        HALF: ("s", FIGURE_COLOURS[3]),
        REFERENCE: ("^", FIGURE_COLOURS[1]),
    }
    floor = 1e-16
    for offset, (setting, (marker, colour)) in zip(
        (-0.2, 0.0, 0.2), styles.items(), strict=True
    ):
        ax.semilogy(
            np.arange(len(names)) + offset,
            [max(ratios[n][setting] or floor, floor) for n in names],
            marker,
            color=colour,
            linestyle="none",
            label=setting,
        )
    ax.axhline(TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance")
    ax.set_xticks(np.arange(len(names)), names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("conservation ratio (dimensionless)")
    ax.set_ylim(floor / 3, 3)
    ax.legend(fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4)
    return fig


def draw_burgers() -> Figure:
    """The relative change of the total of u² against time for each number
    of cells, with the time the shock forms."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    colours = (
        FIGURE_COLOURS[0],
        FIGURE_COLOURS[1],
        FIGURE_COLOURS[4],
        FIGURE_COLOURS[3],
    )
    for cells, style, colour in zip(
        BURGERS_CELLS, ("-", "--", "-.", ":"), colours, strict=True
    ):
        times, totals = burgers_totals(cells, AFTER)
        ax.plot(
            times,
            1 - totals[:, 1] / totals[0, 1],
            style,
            color=colour,
            label=f"{cells} cells",
        )
    ax.axvline(
        1 / (2 * np.pi * BURGERS_AMPLITUDE),
        color=FIGURE_COLOURS[2],
        linewidth=0.8,
        label="shock forms",
    )
    ax.set_xlabel("time (s)")
    ax.set_ylabel("loss of the total of u² (relative)")
    ax.legend(fontsize=8)
    return fig


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("budget", BUDGET)
    experiment.number("max-candidates", MAX_CANDIDATES)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.number("box-dt", CentralBox.settings[OWN].dt, "g")
    experiment.number("reference-dt", CentralBox.settings[REFERENCE].dt, "g")
    experiment.display(
        "allowlist", AllowlistDisplay(box_allowlist(box(), MAX_CANDIDATES)[0])
    )
    ratios = test_system(experiment)
    coincidences(experiment)

    # region: replay
    recording, transcript, score = replay_run(LESSON)
    # endregion: replay
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    experiment.number("trajectories", score.trajectories)
    experiment.number("found", score.found)
    experiment.number("known", score.known)
    experiment.number("outcome", score.outcome)
    ratios |= agent_verdicts(experiment, score)
    ratios |= baseline_on_the_box(experiment)
    experiment.figure("fig-verdicts", partial(draw_verdicts, ratios))
    symmetry(experiment)
    top_invariants(experiment)
    burgers(experiment)
    experiment.figure("fig-burgers-totals", draw_burgers)
    return experiment


if __name__ == "__main__":
    main(run)
