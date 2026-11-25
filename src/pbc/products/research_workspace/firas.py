"""The reproduction track's analysis: the spectrum fit of Fixsen et al. (1996)
regenerated from the LAMBDA file, its branches, and its positive control.

The goal is a reproduction of the published **spectrum fit** from the
available derived data, not of the absolute temperature calibration (the
plan of Issue #619). Near a reference temperature ``T_ref`` the residual
spectrum is linear in its parameters (the paper's Eq. 3):

    dI(nu) = dT dB_nu/dT + G g(nu) + y Y(nu) + mu M(nu)

with ``g`` the file's Galactic spectrum, ``Y = T (x coth(x/2) - 4) dB_nu/dT``
the Compton shape (Eq. 7) and ``M = -(T/x) dB_nu/dT`` the chemical-potential
shape (Eq. 5). The fit is weighted least squares with the file's 1-sigma
column, the diagonal only; every uncertainty it gives is **statistical**.

What the fit cannot give: the residuals of the file are those of the paper's
own fit (the caption of its Fig. 5), so ``dT`` and ``G`` come back close to
zero by construction; and a free ``dT`` absorbs any change of ``T_ref`` to
first order, so the fitted temperature returns the file's reference whatever
it is (branch ``b4`` shows it). The analysis reports both; it never reports
an agreement of ``T_ref + dT`` with 2.728 K as a reproduction.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np

from pbc.data.reference.cobe_firas import (
    K_B,
    KJY_PER_MJY,
    C,
    H,
    Spectrum,
    dplanck_dt,
    peak_brightness,
    planck,
    weighted_rms,
)

TEMPERATURE = "dT"
GALAXY = "G"
COMPTON = "y"
CHEMICAL = "mu"
PARAMETERS = (TEMPERATURE, GALAXY, COMPTON, CHEMICAL)
UNITS = {TEMPERATURE: "K", GALAXY: "1", COMPTON: "1", CHEMICAL: "1"}
Z95 = 1.959963984540054  # two-sided 95 % of a normal distribution
# The criterion declared in the registered plan: a branch that adds one
# parameter continues when it lowers chi-square by more than this.
DELTA_CHI2 = 4.0
# The ablation b5 drops the points above this wavenumber (cm^-1), where the
# Galactic spectrum is largest.
HIGH_CUT = 20.0


def x_of(wavenumber: np.ndarray, temperature: float) -> np.ndarray:
    """``x = h c nu~ / (k T)``, dimensionless."""
    return H * C * 100.0 * np.asarray(wavenumber, dtype=float) / (K_B * temperature)


def shapes(spectrum: Spectrum, temperature: float) -> dict[str, np.ndarray]:
    """The four templates at ``temperature`` (K), each in kJy/sr per unit of
    its parameter: dB/dT per K, the Galaxy column, the y and mu shapes."""
    derivative = dplanck_dt(spectrum.wavenumber, temperature) * KJY_PER_MJY
    x = x_of(spectrum.wavenumber, temperature)
    return {
        TEMPERATURE: derivative,
        GALAXY: spectrum.galaxy.astype(float),
        COMPTON: temperature * (x / np.tanh(x / 2.0) - 4.0) * derivative,
        CHEMICAL: -(temperature / x) * derivative,
    }


def occupation_shapes(spectrum: Spectrum, temperature: float, step: float = 1e-7):
    """The y and mu shapes from numerical derivatives of the distorted
    spectra themselves (for the test of ``shapes``): the Bose-Einstein
    spectrum ``2 h nu^3 / c^2 / (e^(x + mu) - 1)`` differentiated in mu, and
    the Kompaneets solution for small y, ``dn/dy = x^-2 d/dx (x^4 dn/dx)``
    of the Planck occupation n, which is the y shape."""
    nu = C * 100.0 * spectrum.wavenumber
    prefactor = 2 * H * nu**3 / C**2 / 1e-20 * KJY_PER_MJY  # kJy/sr
    x = x_of(spectrum.wavenumber, temperature)

    def bose(mu):
        return prefactor / np.expm1(x + mu)

    chemical = (bose(step) - bose(-step)) / (2 * step)

    def occupation(z):
        return 1.0 / np.expm1(z)

    def flux(z):  # x^4 dn/dx by a central difference
        return z**4 * (occupation(z + step) - occupation(z - step)) / (2 * step)

    d_flux = (flux(x + 1e-4) - flux(x - 1e-4)) / 2e-4
    compton = prefactor * d_flux / x**2
    return {COMPTON: compton, CHEMICAL: chemical}


@dataclass(frozen=True)
class Fit:
    """A weighted linear fit: the parameters with their statistical errors,
    chi-square, the degrees of freedom, the weighted rms of the residual it
    leaves (kJy/sr), and the reference temperature it was taken against."""

    parameters: Mapping[str, float]
    errors: Mapping[str, float]
    chi2: float
    dof: int
    weighted_rms: float
    t_ref: float
    points: int

    @property
    def temperature(self) -> float:
        """``T_ref + dT`` (K)."""
        return self.t_ref + self.parameters.get(TEMPERATURE, 0.0)

    def bound(self, name: str) -> float:
        """The regenerated two-sided 95 % bound on ``|p|``: the larger of
        ``|p +- 1.96 sigma|``, statistical only."""
        value, error = self.parameters[name], self.errors[name]
        return float(max(abs(value - Z95 * error), abs(value + Z95 * error)))

    def rms_ppm(self) -> float:
        """The weighted rms in parts per million of the peak of B_nu(T_fit)."""
        return self.weighted_rms / KJY_PER_MJY / peak_brightness(self.temperature) * 1e6

    def as_dict(self) -> dict:
        return {
            "parameters": dict(self.parameters),
            "errors": dict(self.errors),
            "chi2": self.chi2,
            "dof": self.dof,
            "weighted_rms": self.weighted_rms,
            "t_ref": self.t_ref,
            "points": self.points,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> Fit:
        return cls(
            dict(data["parameters"]),
            dict(data["errors"]),
            float(data["chi2"]),
            int(data["dof"]),
            float(data["weighted_rms"]),
            float(data["t_ref"]),
            int(data["points"]),
        )


def against(spectrum: Spectrum, temperature: float) -> Spectrum:
    """The spectrum with its residual taken against ``B_nu(temperature)``
    instead of the file's ``T_ref`` (the sensitivity branch b4): column 3
    plus ``B_nu(T_ref) - B_nu(temperature)``."""
    shift = (
        planck(spectrum.wavenumber, spectrum.t_ref)
        - planck(spectrum.wavenumber, temperature)
    ) * KJY_PER_MJY
    return replace(spectrum, residual=spectrum.residual + shift, t_ref=temperature)


# region: fit
def fit(
    spectrum: Spectrum,
    parameters: Sequence[str],
    *,
    below: float | None = None,
) -> Fit:
    """Fit the residual of ``spectrum`` by the templates ``parameters`` with
    weights ``1/sigma^2``; ``below`` keeps only the wavenumbers below it."""
    unknown = sorted(set(parameters) - set(PARAMETERS))
    if unknown or not parameters:
        raise ValueError(f"unknown or no parameters: {unknown or parameters}")
    if COMPTON in parameters and CHEMICAL in parameters:
        # The paper: "the two are too similar to fit them simultaneously".
        raise ValueError("y and mu are not fitted together")
    keep = np.ones(spectrum.wavenumber.shape, dtype=bool)
    if below is not None:
        keep = spectrum.wavenumber < below
    templates = shapes(spectrum, spectrum.t_ref)
    design = np.column_stack([templates[name] for name in parameters])[keep]
    weights = 1.0 / spectrum.sigma[keep]
    scaled = design * weights[:, None]
    values, *_ = np.linalg.lstsq(scaled, spectrum.residual[keep] * weights, rcond=None)
    covariance = np.linalg.inv(scaled.T @ scaled)
    left = spectrum.residual[keep] - design @ values
    sigma = spectrum.sigma[keep]
    result = Fit(
        dict(zip(parameters, map(float, values), strict=True)),
        dict(zip(parameters, map(float, np.sqrt(np.diag(covariance))), strict=True)),
        float(np.sum((left / sigma) ** 2)),
        int(keep.sum()) - len(parameters),
        weighted_rms(left, sigma),
        spectrum.t_ref,
        int(keep.sum()),
    )
    return result


# endregion: fit


@dataclass(frozen=True)
class Control:
    """The positive control (mode ``simulated``): over ``seeds``, how often
    the fit recovered the injected dT and y within two standard errors, and
    how often the 95 % interval of y contained zero when none was injected."""

    seeds: int
    injected: Mapping[str, float]
    recovered_t: int
    recovered_y: int
    zero_covered: int
    required: int

    @property
    def passed(self) -> bool:
        return min(self.recovered_t, self.recovered_y, self.zero_covered) >= (
            self.required
        )

    def as_dict(self) -> dict:
        return {
            "seeds": self.seeds,
            "injected": dict(self.injected),
            "recovered_t": self.recovered_t,
            "recovered_y": self.recovered_y,
            "zero_covered": self.zero_covered,
            "required": self.required,
            "passed": self.passed,
        }


def synthetic(
    spectrum: Spectrum,
    injected: Mapping[str, float],
    rng: np.random.Generator,
    noise_scale: float = 1.0,
) -> Spectrum:
    """A residual spectrum made of the injected templates and noise drawn
    from the file's 1-sigma column (times ``noise_scale``), at the file's
    frequencies. The spectrum keeps the stated 1-sigma column."""
    templates = shapes(spectrum, spectrum.t_ref)
    residual = sum(value * templates[name] for name, value in injected.items())
    residual = residual + rng.normal(0.0, noise_scale * spectrum.sigma)
    return replace(spectrum, residual=residual)


def control(
    spectrum: Spectrum,
    *,
    seeds: int = 100,
    first_seed: int = 0,
    injected: Mapping[str, float] | None = None,
    required: int = 90,
    noise_scale: float = 1.0,
) -> Control:
    """Run the positive control: recover dT and y within two standard errors
    in at least ``required`` of ``seeds`` seeds; with ``y = 0`` injected, the
    95 % interval contains zero in at least ``required`` of them.
    ``noise_scale`` draws the noise wider than the stated uncertainties: the
    control must then fail (its own test)."""
    injected = dict(injected or {TEMPERATURE: 50e-6, GALAXY: 0.5, COMPTON: 20e-6})
    recovered_t = recovered_y = covered = 0
    for seed in range(first_seed, first_seed + seeds):
        rng = np.random.default_rng(seed)
        result = fit(
            synthetic(spectrum, injected, rng, noise_scale),
            (TEMPERATURE, GALAXY, COMPTON),
        )
        t_error = result.parameters[TEMPERATURE] - injected[TEMPERATURE]
        y_error = result.parameters[COMPTON] - injected[COMPTON]
        recovered_t += abs(t_error) <= 2 * result.errors[TEMPERATURE]
        recovered_y += abs(y_error) <= 2 * result.errors[COMPTON]
        null = {**injected, COMPTON: 0.0}
        zero = fit(
            synthetic(spectrum, null, rng, noise_scale), (TEMPERATURE, GALAXY, COMPTON)
        )
        covered += abs(zero.parameters[COMPTON]) <= Z95 * zero.errors[COMPTON]
    return Control(seeds, injected, recovered_t, recovered_y, covered, required)


def pulls(
    spectrum: Spectrum,
    *,
    seeds: int = 100,
    injected: Mapping[str, float] | None = None,
) -> dict[str, np.ndarray]:
    """The positive control seed by seed, for its figure: the recovered
    minus the injected dT and y over their standard errors (dimensionless),
    with the same seeds and draws as ``control``."""
    injected = dict(injected or {TEMPERATURE: 50e-6, GALAXY: 0.5, COMPTON: 20e-6})
    out = {TEMPERATURE: [], COMPTON: []}
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        result = fit(synthetic(spectrum, injected, rng), (TEMPERATURE, GALAXY, COMPTON))
        for name in out:
            error = result.parameters[name] - injected[name]
            out[name].append(error / result.errors[name])
    return {name: np.array(values) for name, values in out.items()}


# The branches of the stage "fit" (the registered plan): what each fits and
# against which reference. ``reference`` None is the file's T_ref.
BRANCHES = {
    "b0": {"fits": [[TEMPERATURE]], "reference": None, "below": None},
    "b1": {"fits": [[TEMPERATURE, GALAXY]], "reference": None, "below": None},
    "b2": {"fits": [[TEMPERATURE, GALAXY, COMPTON]], "reference": None, "below": None},
    "b3": {
        "fits": [[TEMPERATURE, GALAXY, CHEMICAL]],
        "reference": None,
        "below": None,
    },
    "b4": {
        "fits": [
            [TEMPERATURE, GALAXY],
            [TEMPERATURE, GALAXY, COMPTON],
            [TEMPERATURE, GALAXY, CHEMICAL],
        ],
        "reference": 2.728,
        "below": None,
    },
    "b5": {"fits": [[TEMPERATURE, GALAXY]], "reference": None, "below": HIGH_CUT},
}
# A branch that adds a parameter, and the branch it is compared with.
NESTED = {"b1": "b0", "b2": "b1", "b3": "b1"}


def run_branch(spectrum: Spectrum, configuration: Mapping) -> list[Fit]:
    """The fits of one branch's configuration (``BRANCHES``)."""
    reference = configuration.get("reference")
    data = spectrum if reference is None else against(spectrum, float(reference))
    return [
        fit(data, tuple(parameters), below=configuration.get("below"))
        for parameters in configuration["fits"]
    ]


@dataclass(frozen=True)
class BranchDecision:
    """The guided comparison's decision about one branch: continue or stop,
    the declared criterion's number, the reason, and what would warrant
    revisiting it."""

    branch: str
    decision: str
    delta_chi2: float | None
    reason: str
    revisit: str


def decide(fits: Mapping[str, Sequence[Fit]]) -> list[BranchDecision]:
    """Apply the declared criterion to the nested branches; b4 and b5 add no
    parameter and are always run and reported."""
    out = []
    for branch, parent in NESTED.items():
        drop = fits[parent][0].chi2 - fits[branch][0].chi2
        added = sorted(
            set(fits[branch][0].parameters) - set(fits[parent][0].parameters)
        )
        if drop > DELTA_CHI2:
            out.append(
                BranchDecision(
                    branch,
                    "continue",
                    drop,
                    f"adding {', '.join(added)} lowers chi-square by {drop:.2f},"
                    f" more than {DELTA_CHI2:g}",
                    "a later fit with the frequency covariance that lowers it by"
                    f" less than {DELTA_CHI2:g}",
                )
            )
        else:
            out.append(
                BranchDecision(
                    branch,
                    "stop",
                    drop,
                    f"adding {', '.join(added)} lowers chi-square by {drop:.2f},"
                    f" not more than {DELTA_CHI2:g}: the data do not ask for it",
                    "a fit with the paper's frequency covariance, or data with"
                    " smaller uncertainties, that lowers chi-square by more than"
                    f" {DELTA_CHI2:g}",
                )
            )
    for branch, why in (
        ("b4", "the sensitivity branch adds no parameter; always run and reported"),
        ("b5", "the ablation adds no parameter; always run and reported"),
    ):
        out.append(BranchDecision(branch, "reported", None, why, "not applicable"))
    return out
