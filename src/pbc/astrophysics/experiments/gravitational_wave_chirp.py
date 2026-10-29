"""The experiment of the lesson "Gravitational-wave chirp simulation".

The wave of two bodies spiralling together computed from their motion
(``pbc.astrophysics.gravitational_waves``): the waveform of the quadrupole
formula against the closed forms of ``pbc.mechanics.chirp`` and their
first correction, the two polarisations at several inclinations, three
binaries of one chirp mass, and the time and the cycles between a low
frequency and the innermost stable orbit. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.gravitational_wave_chirp out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.astrophysics.gravitational_waves import (
    GM_SUN,
    MPC,
    cycles_in_band,
    inspiral,
    isco_frequency,
    mass_for_chirp_mass,
    polarisations,
    positions,
    quadrupole,
    second_derivative,
    strain_amplitude,
    wave_phase,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.mechanics.chirp import (
    chirp_frequency,
    chirp_mass,
    chirp_phase,
    shrink_rate,
    time_to_coalescence,
)

# region: setup
masses = (30.0, 30.0)  # solar masses
f_start = 20.0  # Hz, the wave frequency at the start
distance = 400 * MPC  # m
rate = 2**15  # samples per second
# endregion: setup

# region: inclinations
inclinations = [0, 30, 60, 90]  # degrees from the orbit's axis
# endregion: inclinations

# region: same-chirp-mass
first_masses = [30.0, 45.0, 60.0]  # solar masses; the second gives one chirp mass
# endregion: same-chirp-mass

# region: band
f_low = 10.0  # Hz, the low end of a ground-based detector's band
binaries = [
    ("two neutron stars", 1.4, 1.4),
    ("a neutron star and a black hole", 10.0, 1.4),
    ("two black holes", 30.0, 30.0),
]
# endregion: band


def waveform(m1: float, m2: float, inclination: float = 0.0):
    """The strain of the binary from ``f_start`` to the innermost stable
    orbit at the inclination in degrees: the orbit integrated, the positions,
    the quadrupole, its second derivative by finite differences, the
    polarisations. Returns the times, the separations, the orbital phases,
    the two polarisations, and the time the inspiral ends."""
    end, _, _ = inspiral(m1, m2, f_start)
    t = np.arange(0.0, end[0], 1.0 / rate)
    t, a, phi = inspiral(m1, m2, f_start, t)
    x1, x2 = positions(a, phi, m1, m2)
    q_ddot = second_derivative(quadrupole(x1, x2, m1, m2), 1.0 / rate)
    h_plus, h_cross = polarisations(q_ddot, distance, np.radians(inclination))
    return t[2:-2], a[2:-2], phi[2:-2], h_plus, h_cross, float(end[0])


def slowness(a, m1: float, m2: float):
    """The fraction eps = |da/dt| / (a omega) by which the orbit shrinks in
    one radian of its turn."""
    omega = np.sqrt((m1 + m2) * GM_SUN / a**3)
    return np.abs(shrink_rate(a, m1, m2)) / (a * omega)


def chirp_check(experiment: Experiment):
    """The face-on waveform against the closed forms: the amplitude against
    ``strain_amplitude`` at ``chirp_frequency``, with its first correction
    for an orbit that shrinks during a turn; the phase in two steps, twice
    the orbital phase against ``chirp_phase`` (both grow at 2 pi f), and the
    phase of the wave against twice the orbital phase, signed; record the
    table and return what the figure draws and the page quotes."""
    m1, m2 = masses
    mc = chirp_mass(m1, m2)
    t_c = time_to_coalescence(f_start, mc)
    t, a, phi, h_plus, h_cross, end = waveform(m1, m2)
    eps = slowness(a, m1, m2)
    f = chirp_frequency(t, mc, t_c)
    amplitude_gap = np.hypot(h_plus, h_cross) / strain_amplitude(f, mc, distance) - 1
    phase = wave_phase(h_plus, h_cross)
    reference = chirp_phase(t, mc, t_c)
    # The orbit turns as the closed form says; the wave leads the orbit.
    orbit_gap = 2 * (phi - phi[0]) - (reference - reference[0])
    lead = phase - 2 * phi
    phase_gap = (phase - phase[0]) - (reference - reference[0])
    # The first corrections: amplitude (57/32) eps², phase +(5/4) eps.
    assert np.max(np.abs(amplitude_gap / eps**2 - 57 / 32)) < 0.01
    assert np.max(np.abs(orbit_gap)) < 1e-8
    assert np.max(np.abs(lead / eps - 5 / 4)) < 0.01

    rows = [
        (
            t[k],
            f[k],
            eps[k],
            amplitude_gap[k],
            amplitude_gap[k] / eps[k] ** 2,
            orbit_gap[k],
            lead[k],
            lead[k] / eps[k],
        )
        for k in np.linspace(0, len(t) - 1, 6).astype(int)
    ]
    experiment.table(
        "chirp-check",
        rows,
        [
            ("time", "s", ".3f"),
            ("frequency, closed form", "Hz", ".1f"),
            ("slowness eps", "", ".2e"),
            ("amplitude / closed form - 1", "", ".2e"),
            ("the same / eps^2", "", ".3f"),
            ("2 x orbital phase - closed form", "rad", ".0e"),
            ("wave phase - 2 x orbital phase", "rad", ".2e"),
            ("the same / eps", "", ".4f"),
        ],
        "The face-on strain of two 30 solar-mass bodies at 400 Mpc, computed "
        "from their motion by the quadrupole formula, against the closed forms "
        "of the chirp: the amplitude h0 at the closed-form frequency; twice the "
        "orbital phase against the closed-form phase, both counted from the "
        "start; and the phase of the wave, arg(-(h+ + i hx)), against twice the "
        "orbital phase, positive where the wave is ahead; "
        "eps = |da/dt| / (a omega).",
    )
    measured = np.gradient(phase, t) / (2 * np.pi)
    return {
        "t": t,
        "h_plus": h_plus,
        "f": f,
        "measured": measured,
        "mc": mc,
        "end": end,
        "t_c": t_c,
        "eps": eps,
        "amplitude_gap": amplitude_gap,
        "orbit_gap": orbit_gap,
        "lead": lead,
        "phase_gap": phase_gap,
    }


def draw_waveform(t, h_plus, f, measured, mc, end) -> Figure:
    """Top: the face-on plus polarisation against time with the closed-form
    amplitude. Bottom: the frequency of the computed wave, from its phase,
    against the closed form, and the frequency of the innermost stable
    orbit."""
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 5.0), sharex=True)
    scale = 1e-22
    top.plot(
        t,
        h_plus / scale,
        color=FIGURE_COLOURS[0],
        linewidth=0.8,
        label="h+ from the motion",
    )
    envelope = strain_amplitude(f, mc, distance) / scale
    top.plot(
        t,
        envelope,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=1.2,
        label="closed-form amplitude",
    )
    top.plot(t, -envelope, color=FIGURE_COLOURS[1], linestyle="--", linewidth=1.2)
    top.set_ylabel("strain h+ (units of 1e-22)")
    top.legend(fontsize="small", loc="upper left")
    step = len(t) // 30
    bottom.plot(
        t[::step],
        measured[::step],
        "o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        label="from the computed wave",
    )
    bottom.plot(
        t,
        f,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        linewidth=1.2,
        label="closed form",
    )
    bottom.axhline(
        isco_frequency(sum(masses)),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="innermost stable orbit",
    )
    bottom.set_xlabel("time from the start (s)")
    bottom.set_ylabel("wave frequency (Hz)")
    bottom.set_xlim(0, end)
    bottom.legend(fontsize="small", loc="center left")
    fig.tight_layout()
    return fig


def inclination_scan(experiment: Experiment):
    """The two polarisations at each inclination against the face-on ones:
    the least-squares factor of each against (1 + cos² i) / 2 and cos i;
    record the table and return the largest gap."""
    m1, m2 = masses
    _, _, _, plus0, cross0, _ = waveform(m1, m2, 0.0)
    rows = []
    for degrees in inclinations:
        _, _, _, plus, cross, _ = waveform(m1, m2, degrees)
        c = np.cos(np.radians(degrees))
        rows.append(
            (
                degrees,
                plus @ plus0 / (plus0 @ plus0),
                (1 + c**2) / 2,
                cross @ cross0 / (cross0 @ cross0),
                c,
            )
        )
    gap = max(max(abs(r[1] - r[2]), abs(r[3] - r[4])) for r in rows)
    # What is left is of the order eps²: the shrinking orbit's quadrupole
    # along its axis, which the plus polarisation sees away from the axis.
    assert gap < 1e-5
    experiment.table(
        "inclinations",
        rows,
        [
            ("inclination", "degrees", "d"),
            ("plus / face-on plus", "", ".6f"),
            ("(1 + cos^2 i) / 2", "", ".6f"),
            ("cross / face-on cross", "", ".6f"),
            ("cos i", "", ".6f"),
        ],
        "The size of each polarisation computed from the motion, relative to "
        "the face-on wave (a least-squares factor over the whole record), "
        "against the dependence on the inclination that the quadrupole formula "
        "predicts for a circular orbit.",
    )
    return gap


def same_chirp_mass(experiment: Experiment):
    """Three binaries of the chirp mass of ``masses``: the second mass for
    each first one, the waveform of each, the largest difference from the
    first before the earliest end, and where each ends; record the table and
    return the frequency tracks and the difference."""
    mc = chirp_mass(*masses)
    tracks, rows, waves = [], [], []
    for m1 in first_masses:
        m2 = mass_for_chirp_mass(m1, mc)
        t, _, _, h_plus, h_cross, end = waveform(m1, m2)
        frequency = np.gradient(wave_phase(h_plus, h_cross), t) / (2 * np.pi)
        tracks.append((m1, m2, t, frequency, end))
        waves.append(h_plus)
        rows.append((m1, m2, chirp_mass(m1, m2), m1 + m2, isco_frequency(m1 + m2), end))
    shortest = min(len(w) for w in waves)
    peak = np.max(np.abs(waves[0][:shortest]))
    difference = (
        max(np.max(np.abs(w[:shortest] - waves[0][:shortest])) for w in waves[1:])
        / peak
    )
    assert difference < 1e-6
    experiment.table(
        "same-chirp-mass",
        rows,
        [
            ("m1", "M_sun", ".1f"),
            ("m2", "M_sun", ".2f"),
            ("chirp mass", "M_sun", ".3f"),
            ("total mass", "M_sun", ".2f"),
            ("frequency at the innermost orbit", "Hz", ".1f"),
            ("time from 20 Hz to it", "s", ".4f"),
        ],
        "Three binaries of one chirp mass, each computed from its motion from a "
        "wave frequency of 20 Hz to its innermost stable circular orbit.",
    )
    return tracks, difference


def draw_same_chirp_mass(tracks) -> Figure:
    """The wave frequency of the three binaries against time, each ending at
    its innermost stable orbit (marked): the whole record on the left, its
    last tenth of a second on the right."""
    fig, (whole, last) = plt.subplots(1, 2, figsize=(6.4, 3.6), sharey=True)
    end = max(track[-1] for track in tracks)
    for k, ((m1, m2, t, frequency, _), line, marker) in enumerate(
        zip(tracks, ("-", "--", ":"), ("o", "s", "^"), strict=True)
    ):
        inner = slice(2, -2)
        for ax in (whole, last):
            ax.plot(
                t[inner],
                frequency[inner],
                color=FIGURE_COLOURS[k],
                linestyle=line,
                linewidth=1.5,
                label=f"{m1:.0f} + {m2:.1f} M_sun",
            )
            ax.plot(
                t[-3],
                frequency[-3],
                marker,
                color=FIGURE_COLOURS[k],
                markersize=8,
                markerfacecolor="none",
            )
    whole.set_xlabel("time from 20 Hz (s)")
    whole.set_ylabel("wave frequency (Hz)")
    whole.legend(fontsize="small", loc="upper left")
    last.set_xlim(end - 0.1, end + 0.005)
    last.set_xlabel("time from 20 Hz (s), the last 0.1 s")
    fig.tight_layout()
    return fig


def band(experiment: Experiment):
    """For each binary, the time and the number of cycles from ``f_low`` to
    the innermost stable orbit, integrated and in closed form; record the
    table and return the largest relative gap."""
    rows = []
    for name, m1, m2 in binaries:
        mc = chirp_mass(m1, m2)
        f_end = isco_frequency(m1 + m2)
        end, _, phi = inspiral(m1, m2, f_low)
        time = time_to_coalescence(f_low, mc) - time_to_coalescence(f_end, mc)
        cycles = phi[0] / np.pi  # the wave turns twice per orbit
        rows.append(
            (name, mc, f_end, end[0], time, cycles, cycles_in_band(f_low, f_end, mc))
        )
    gap = max(max(abs(r[3] / r[4] - 1), abs(r[5] / r[6] - 1)) for r in rows)
    assert gap < 1e-8
    experiment.table(
        "band",
        rows,
        [
            ("binary", "", ""),
            ("chirp mass", "M_sun", ".3f"),
            ("frequency at the innermost orbit", "Hz", ".0f"),
            ("time from 10 Hz, integrated", "s", ".4f"),
            ("time, closed form", "s", ".4f"),
            ("wave cycles, integrated", "", ".1f"),
            ("wave cycles, closed form", "", ".1f"),
        ],
        "The time and the number of wave cycles from 10 Hz to the innermost "
        "stable circular orbit, from the integrated orbit and from the closed "
        "forms of the chirp.",
    )
    return rows, gap


def neutron_star_amplitude():
    """Exercise 1: the amplitude of two 1.4 solar-mass neutron stars at
    40 Mpc, face on, at 100 Hz, and the change of length of a 4 km arm."""
    h0 = float(strain_amplitude(100.0, chirp_mass(1.4, 1.4), 40 * MPC))
    return h0, h0 * 4e3


def slowness_at_isco():
    """Exercise 2: eps at the innermost stable orbit for several mass
    ratios, from the separation, and the closed form (64/5) eta 6^(-5/2)."""
    rows = []
    for ratio in (1.0, 4.0, 10.0):
        m1, m2 = ratio, 1.0
        a = 6 * (m1 + m2) * GM_SUN / 299_792_458.0**2
        eta = m1 * m2 / (m1 + m2) ** 2
        rows.append((ratio, eta, float(slowness(a, m1, m2)), 64 / 5 * eta * 6**-2.5))
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    check = chirp_check(experiment)
    experiment.figure(
        "fig-waveform",
        partial(
            draw_waveform,
            check["t"],
            check["h_plus"],
            check["f"],
            check["measured"],
            check["mc"],
            check["end"],
        ),
    )
    experiment.number("chirp-mass", check["mc"], ".2f")
    experiment.number("isco", isco_frequency(sum(masses)), ".1f")
    experiment.number("end", check["end"], ".3f")
    experiment.number("t-c", check["t_c"], ".3f")
    experiment.number("left", 1e3 * (check["t_c"] - check["end"]), ".1f")
    experiment.number(
        "left-closed",
        1e3 * time_to_coalescence(isco_frequency(sum(masses)), check["mc"]),
        ".1f",
    )
    experiment.number("eps-start", check["eps"][0], ".1e")
    experiment.number("eps-end", check["eps"][-1], ".3f")
    experiment.number("amplitude-gap-end", check["amplitude_gap"][-1], ".1e")
    experiment.number("phase-gap-end", check["phase_gap"][-1], ".3f")
    experiment.number("coefficient", 57 / 32, ".4f")
    ratios = check["amplitude_gap"] / check["eps"] ** 2
    experiment.number(
        "coefficient-spread", np.max(np.abs(ratios / (57 / 32) - 1)), ".0e"
    )
    experiment.number(
        "orbit-gap",
        f"below {1e-8:.0e}"
        if np.max(np.abs(check["orbit_gap"])) < 1e-8
        else np.max(np.abs(check["orbit_gap"])),
    )
    experiment.number("lead-end", check["lead"][-1], ".3f")
    experiment.number(
        "lead-spread",
        np.max(np.abs(check["lead"] / check["eps"] / (5 / 4) - 1)),
        ".0e",
    )
    experiment.number("peak-strain", np.max(np.abs(check["h_plus"])), ".1e")

    gap = inclination_scan(experiment)
    experiment.number("inclination-gap", gap, ".0e")

    tracks, difference = same_chirp_mass(experiment)
    experiment.figure("fig-same-chirp-mass", partial(draw_same_chirp_mass, tracks))
    experiment.number(
        "same-difference", f"below {1e-6:.0e}" if difference < 1e-6 else difference
    )

    rows, band_gap = band(experiment)
    experiment.number("band-gap", f"below {1e-8:.0e}" if band_gap < 1e-8 else band_gap)
    experiment.number("bns-cycles", rows[0][5], ".0f")
    experiment.number("bns-minutes", rows[0][3] / 60, ".1f")
    experiment.number("bbh-cycles", rows[-1][5], ".0f")

    h0, change = neutron_star_amplitude()
    experiment.number("ns-strain", h0, ".1e")
    experiment.number("ns-change", change, ".1e")
    isco_rows = slowness_at_isco()
    experiment.table(
        "slowness-at-isco",
        isco_rows,
        [
            ("mass ratio m1 / m2", "", ".0f"),
            ("symmetric mass ratio eta", "", ".4f"),
            ("eps at the innermost orbit", "", ".5f"),
            ("(64/5) eta 6^(-5/2)", "", ".5f"),
        ],
        "The fraction by which the orbit shrinks in one radian of its turn at "
        "the innermost stable circular orbit, for three mass ratios.",
    )
    experiment.number("eps-isco-equal", isco_rows[0][2], ".4f")
    return experiment


if __name__ == "__main__":
    main(run)
