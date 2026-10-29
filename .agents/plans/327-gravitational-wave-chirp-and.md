# Plan: Issue #327, F93 — Gravitational-wave chirp and exoplanet transit simulations

- Issue: #327 (source: `docs/roadmap.md`, F93)
- Branch: `feature/327-gravitational-wave-chirp-and`
- Base commit: `480130b`
- Risk: Medium (physics content), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

Two lessons of the `astrophysics` course, slots AST6 and AST7, at the orders
4 and 5 of the strand (AST4 and AST5 of F92 are not built yet; the course
view orders the lessons by their slots). Built to the experiment contract of
F91: one library module and one experiment module per lesson, one `draw_`
function per figure, a unit test per experiment, the library tests in
`tests/unit/test_astrophysics.py`.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `gravitational-wave-chirp` (order 4) | AST6 | `gravitational_waves.py`: the adiabatic inspiral of a circular orbit (separation and orbital phase integrated with the shrink rate of `pbc.mechanics.chirp` and Kepler's third law, stopped at the innermost stable circular orbit), the positions of the two bodies, their trace-free mass quadrupole, its second derivative by fourth-order finite differences, the two polarisations of the quadrupole formula for an observer at any inclination, the closed-form amplitude, the frequency of the innermost stable orbit, and the closed-form number of cycles in a band | the waveform computed from the moving masses against the closed forms of `pbc.mechanics.chirp` (`chirp_frequency`, `chirp_phase`, `time_to_coalescence`) and the closed-form amplitude; the polarisations against their dependence on the inclination; pairs of masses with one chirp mass giving one waveform, ending at different innermost orbits; the time and the cycles in band against the closed forms for a neutron-star pair, a mixed pair, and a black-hole pair |
| `exoplanet-transit` (order 5) | AST7 | `transit.py`: the planet's orbit integrated in three dimensions (DOP853), the contacts located as events of the projected separation, the occulted flux of a uniform or limb-darkened star by counting the cells of a grid over the planet's disk, the closed-form overlap of two disks, the analytic total and full durations, the closed-form depth of a centred planet on a limb-darkened star | the transit depth against the ratio of the areas, the simulated flux against the closed-form overlap through ingress and egress; the contacts of the integrated orbit against the analytic durations, over impact parameters up to a grazing transit; the depth of a limb-darkened star against its closed form for a central transit |

AST6 does not show the measured strain of M16 again: it names the lab (M16,
the header's prerequisite) for the measurement and the Lean lesson (L5,
`related`) for the proved algebra, and adds what M16 leaves free, the
amplitude and the polarisations from the motion of the masses, and where
the model ends. AST7 is the simulated counterpart of the measured-data lab
AST8 (F104, not built), which the page names without a link.

Units: SI with the constants of `pbc.mechanics.chirp` (`GM_SUN`, `C`) for
AST6; SI with `GM_SUN` and the Sun's nominal radius for AST7, durations in
hours. No gravitational-wave or transit package: the references are closed
forms and independent computations.

## Decisions

| Decision | Reason |
|---|---|
| The waveform from the quadrupole formula applied to the computed positions of the two bodies, differentiated numerically | An independent route to the amplitude, the factor two between the orbital and the wave frequency, and the phase; M16 checks only the frequency, with a free amplitude |
| The inspiral stopped at the innermost stable circular orbit, `6GM/c^2` | Where the model of a slowly shrinking circular orbit is commonly cut off; the frequency there depends on the total mass, not the chirp mass, which the second example shows |
| No change to M16 or L5 | The Issue says they are not republished; AST6 links them from its header |
| The transit flux by counting grid cells over the planet's disk, compared with the closed-form overlap | Independent of the formula; the same code takes a limb-darkened star |
| The orbit integrated rather than written in closed form | The contacts then come from the motion, and the analytic durations are checked, not restated |
| Circular orbits only for the durations | The arcsin formula is exact for them; eccentricity is named in the limits |
| The phase checked in two steps, in one stated convention: twice the orbital phase against `chirp_phase`, then the wave phase `arg(-(h+ + i hx))` against twice the orbital phase, signed (review 01, M1) | Both phases grow at 2 pi f; the sign of the (5/4) eps lead then follows from the quadrupole formula and is tested on its own, not only through the residual |
| The transit functions validate their domain and the solver's success (review 01, MIN1) | They are library functions a later lesson (AST8) may reuse |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; reference curves labelled, not fitted; alt text without
computed values. Accessible fallback: the alt text, and the tables that
carry the same numbers.

- AST6: the waveform with its closed-form envelope and frequency (preview);
  the frequency of three binaries of one chirp mass with their innermost
  orbits.
- AST7: the simulated light curve with the closed form and the contacts
  (preview); the light curves of several impact parameters; a uniform and a
  limb-darkened star.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_astrophysics.py`: each new function against a closed form, a limit, or an independent computation.
- `tests/unit/test_gravitational_wave_chirp_experiment.py`, `tests/unit/test_exoplanet_transit_experiment.py`: the command writes what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the two lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
