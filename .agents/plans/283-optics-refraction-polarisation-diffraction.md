# Plan: Issue #283, F77 — Optics: refraction, polarisation, diffraction, inverse optics (W3, W4, W5, W6)

- Issue: #283 (source: `docs/roadmap.md`, F77)
- Branch: `feature/283-optics-refraction-polarisation-diffraction`
- Base commit: `ec5b90e`
- Risk: Level 2 by path (four new lessons, their code under
  `src/pbc/waves/`, and tests); Level 3 by the trigger "tolerance or budget
  changed", which the scripts read on the tolerances that the new
  experiments state (as for F75). The tolerances are new code of new
  lessons, not a widened check; no published claim changes. Level 3 asks for
  the full verification and the owner's approval of the exact head.
- Governing documents: `docs/architecture.md` (lesson model),
  `docs/authoring.md` (format 2, the experiment of a lesson), ADR 013 (slots),
  ADR 016 (the experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64, F71 delivered; F113 read as the owner's interim
  full-run capacity, since 2026-10-24 up to 110 lessons (#281). The site has
  51 lessons; 55 after this feature.

## Design

Four lessons in the `waves` strand at the next free orders (4 to 7), one slot
each. The course view orders by the curriculum file (W3 to W6 before W9).
Quantities in SI units.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `refraction-and-snells-law` (order 4) | W3 | `refraction.py`: Snell's law; the path of least time across a flat interface found by a golden-section search of the travel time (Fermat), no use of Snell's law; the Fresnel amplitudes from solving the two boundary conditions as a linear system, also beyond the critical angle; a pulse across a step of the refractive index on a grid, with its own leapfrog scheme for a speed that changes in space | the refracted angle of the least-time path against arcsin(n1 sin(theta) / n2) for air to water, air to glass, and glass to air below the critical angle; the solved reflection coefficients against the closed Fresnel forms, R + T = 1, the Brewster angle (zero of r_p, found by bisection) against arctan(n2 / n1), R = 1 beyond the critical angle; the reflected and transmitted parts of the grid pulse against (n1 - n2) / (n1 + n2) and 2 n1 / (n1 + n2), with the error falling under refinement |
| `polarisation-and-maluss-law` (order 5) | W4 | `polarisation.py`: Jones vectors and matrices (polariser with a finite extinction ratio, retarder), the intensity measured as the time average of the sampled real field, the Stokes parameters from six analyser intensities, an ensemble of random states for unpolarised light | the transmitted intensity through an analyser at a range of angles against I0 cos^2(theta), and with a leak epsilon against cos^2 + epsilon sin^2; unpolarised light through one polariser at one half within four standard errors of the ensemble; a chain of N polarisers between crossed ends against cos^(2N)(pi / 2N); the degree of circular polarisation behind a quarter-wave plate used at another wavelength against sin(Gamma0 lambda0 / lambda) |
| `diffraction-and-imaging` (order 6) | W5 | `diffraction.py`: the field on a screen as a direct Huygens sum of wavelets from a sampled aperture (no diffraction formula); a radial integral of the circular pupil with the Bessel function J0 for the Airy pattern; the Rayleigh dip of two points | the zeros of a single slit against sin(theta) = m lambda / a; the zeros of a double slit and their spacing against the exact far-field positions and lambda L / d; the principal maxima of a grating against d sin(theta) = m lambda; the first zero of the Airy pattern against 1.21967 lambda / D; the departure of the direct sum from the Fraunhofer pattern as the Fresnel number grows (the domain of validity); grating resolving power lambda / (m N) shown on a doublet |
| `inverse-optics` (order 7) | W6 | `inverse.py`: the Fraunhofer model of a double slit on a detector, synthetic photon counts drawn from the direct Huygens sum of W5 with Poisson noise, a weighted least-squares fit (`scipy.optimize.least_squares`) with the covariance from the Jacobian, the singular values of the Jacobian | the slit width and separation recovered within four standard errors and a stated relative tolerance; the pulls of many independent synthetic data sets with mean near zero and spread near one; identifiability: with the wavelength free, the Jacobian is singular (only d / lambda and a / lambda enter), shown by its singular values and a flat valley of chi^2; an aperture and its mirror image give the same intensity, so the side of the wider slit of an unequal pair is not identified |

## Decisions

| Decision | Reason |
|---|---|
| Fermat's principle by a golden-section search of the travel time, not a root of its derivative | The derivative of the travel time is Snell's law itself; the search uses only the time |
| Fresnel amplitudes by solving the boundary conditions numerically | The closed forms are the comparison; R + T = 1 checks the energy flux independently |
| A grid pulse with its own scheme for a speed that varies in space | `pbc.waves.wave.solve` takes one speed; the new scheme is short and reduces to it for a uniform speed (tested) |
| Intensity as the time average of the sampled real field | Malus's law is then a result of projecting the field, not an input |
| Diffraction by a direct Huygens sum | The same superposition as W2's two sources; the formulas are the comparison |
| W6's data generated by the direct sum at a finite distance, fitted with the Fraunhofer formula | The generator is not the fit model, as for a measurement; the bias this leaves is below the noise at the chosen Fresnel number and is stated |
| W6 on simulated data only | Until F52 delivers measured images (the Issue) |
| W5's grating maxima checked to five per cent of their width, not to round-off (discovered in implementation) | The envelope of one slit pulls each principal maximum towards the centre by a few per cent of its width (up to about 3.4 % at the third order of a ten-slit grating); the zeros of slits are exact and keep a 1e-9 tolerance. The page states the shift |
| W6's start from the spectrum past its first minimum, then a scan of the width (discovered in implementation) | The strongest frequency of the counts is the envelope, not the fringes; past the first minimum of the spectrum the fringe peak at d / lambda is the largest for d > 2 a |
| W6's pulls over 1000 data sets, and a fit to the noise-free counts (discovered in implementation) | With 200 data sets the mean pull of the width of the project seed was about three standard errors off zero, while other seeds gave none; the noise-free fit measures the generator-against-model bias directly (about -0.02 standard errors), and 1000 sets keep the page within 10 s |
| No reference register entries (`go-deeper`) | Optional; the lessons are complete without them |
| No change to the architecture, ADRs, CI, or the curriculum file | The lessons fit format 2 and their slots exist. The package layout line of `docs/architecture.md` (a protected path) is left to a change the owner approves, as for F75 |

## Visual deliverables

Scientific figures, each `simulated`, drawn by a `draw_` function from the
tested code, colours from `FIGURE_COLOURS` with line style or marker as well,
alt text without computed values:

- W3: `fig-refraction` (preview; refracted angle against the angle of
  incidence, Snell's law as lines, the least-time paths as markers, the
  critical angle marked), `fig-fresnel` (R_s and R_p against angle for
  air to glass and glass to air, Brewster and critical angles marked),
  `fig-interface-pulse` (the grid pulse before and after the interface).
- W4: `fig-malus` (preview; transmitted intensity against analyser angle,
  linear and log scale, ideal and leaky polariser), `fig-polariser-chain`
  (transmission against the number of polarisers), `fig-wave-plate`
  (circular degree against wavelength).
- W5: `fig-slits` (preview; intensity of a single and a double slit and a
  grating against sin(theta), zeros marked from the closed forms),
  `fig-airy-rayleigh` (the Airy pattern and two points at three separations),
  `fig-doublet` (the sodium doublet through gratings of three sizes),
  `fig-fraunhofer-limit` (departure from the Fraunhofer pattern against the
  Fresnel number, log-log).
- W6: `fig-fit` (preview; synthetic counts with their Poisson error, the fit,
  and the residuals), `fig-pulls` (histogram of the pulls against a unit
  normal), `fig-degeneracy` (chi^2 over the separation and the wavelength,
  the valley of d / lambda).

Scientific validation: each figure shows quantities that a check of the same
lesson asserts. Accessible fallback: the alt text and the result tables.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_optics.py`: each new component against a closed form or a
  limit.
- `tests/unit/test_<name>_experiment.py`, one per lesson.
- `tests/unit/test_curriculum.py` computes the progress from the files
  (#277), so it needs no edit.
- `tests/lessons`, the single-page render of the four lessons.
- The full `./scripts/verify.sh` (Level 3), run last.
