"""The event counts of a Bell test against the model of the entanglement
lesson.

The entanglement lesson (``pbc.quantum.bell``) predicts the correlator of two
spins in the singlet measured at the angles alpha and beta in one plane,
E = -cos(alpha - beta), and the CHSH value S = 2 sqrt(2) at the right
settings; a local hidden-variable model keeps |S| <= 2. The Munich
event-ready Bell test (``pbc.data.reference.munich_bell``) heralds one of two
Bell states and measures at the settings alpha = 0 or 90 deg (lab 1) and
beta = -45 or +45 deg (lab 2). For the singlet Psi- the correlator is
-cos(alpha - beta); for Psi+, whose amplitudes have the same sign, it is
-cos(alpha + beta) in this plane. Both give +-1/sqrt(2) at these settings,
with the sign pattern g of the reference module, and S = 2 sqrt(2).

A real pair is not a pure Bell state and a real readout is not perfect. The
one-parameter model of the lesson's first exercise, the state mixed with
white noise at the visibility V, scales every correlator by V and gives
S = 2 sqrt(2) V; it breaks the bound only for V > 1/sqrt(2). The one
extension the data ask for here is an offset eps of the analysis basis of
lab 2: the correlator becomes -V cos(alpha -+ (beta + eps)), so that the two
correlators at beta = -45 deg and at +45 deg differ in size, and
S = 2 sqrt(2) V cos(eps). Both models are fitted to the four correlators of
a heralded state with ``pbc.data.fit.fit_curve``, weighted by the binomial
standard errors, and the reduced chi-square says whether they describe the
data. The offset is a parameter of the model, not a measurement of the
apparatus: the record gives nothing that identifies its cause.

Two checks of the statistics of a Bell test are here as well: the balance of
the random settings and the no-signalling marginals (the fraction of one
lab's outcomes that are 1 must not depend on the other lab's setting).
"""

from dataclasses import dataclass

import numpy as np

from pbc.data.fit import FitResult, fit_curve
from pbc.data.reference.munich_bell import (
    LHV_BOUND,
    SETTINGS,
    TSIRELSON,
    Correlator,
    Pairs,
    sign,
)

# The angles of the settings, in radians: setting 0 and 1 of each lab
# (the dossier of the card: established by reproducing the paper's Fig. 3).
ALPHA = {0: 0.0, 1: np.pi / 2}  # lab 1
BETA = {0: -np.pi / 4, 1: np.pi / 4}  # lab 2
# The sign of beta in the correlator: -cos(alpha - beta) for the singlet,
# -cos(alpha + beta) for Psi+ in the x-z plane.
PARITY = {"Psi-": 1, "Psi+": -1}
IDEAL = 1 / np.sqrt(2)  # |E| of a pure Bell state at these settings


def predicted_correlator(
    state: str, a: int, b: int, visibility: float = 1.0, offset: float = 0.0
) -> float:
    """E(a, b) of the heralded ``state`` mixed with white noise at
    ``visibility``, with the analysis basis of lab 2 turned by ``offset``
    (radians): -V cos(alpha_a -+ (beta_b + eps))."""
    return float(-visibility * np.cos(ALPHA[a] - PARITY[state] * (BETA[b] + offset)))


def model_chsh(visibility: float, offset: float = 0.0) -> float:
    """S of the model: 2 sqrt(2) V cos(eps), the signed sum of its four
    correlators for either state."""
    return float(TSIRELSON * visibility * np.cos(offset))


def _model(state: str, with_offset: bool):
    """The model of ``fit_curve``: ``x`` indexes the setting pairs."""

    def model(x, visibility, offset=0.0):
        k = np.asarray(x).astype(int)
        return np.array(
            [
                predicted_correlator(
                    state, *SETTINGS[i], visibility, offset if with_offset else 0.0
                )
                for i in k
            ]
        )

    return model


def fit_visibility(
    terms: dict[tuple, Correlator], state: str, *, with_offset: bool
) -> FitResult:
    """Fit the visibility, and with ``with_offset`` the basis offset of
    lab 2, to the four correlators ``terms`` of ``state``, weighted by their
    standard errors. The reduced chi-square tests the model."""
    x = np.arange(len(SETTINGS), dtype=float)
    y = np.array([terms[k].value for k in SETTINGS])
    sigma = np.array([terms[k].stderr for k in SETTINGS])
    model = _model(state, with_offset)
    if with_offset:
        return fit_curve(
            model,
            x,
            y,
            [0.8, 0.0],
            sigma=sigma,
            names=["visibility", "offset"],
            bounds=([0.0, -np.pi / 4], [1.0, np.pi / 4]),
        )
    return fit_curve(
        lambda x, v: model(x, v),
        x,
        y,
        [0.8],
        sigma=sigma,
        names=["visibility"],
        bounds=([0.0], [1.0]),
    )


def model_s_of_fit(fit: FitResult) -> tuple[float, float]:
    """S of a fitted model and its standard error (first order in V and
    eps, the two taken as independent)."""
    v = fit.value("visibility")
    eps = fit.value("offset") if "offset" in fit.names else 0.0
    sv = fit.stderr[fit.names.index("visibility")]
    se = fit.stderr[fit.names.index("offset")] if "offset" in fit.names else 0.0
    s = model_chsh(v, eps)
    ds_dv = TSIRELSON * np.cos(eps)
    ds_de = -TSIRELSON * v * np.sin(eps)
    return s, float(np.sqrt((ds_dv * sv) ** 2 + (ds_de * se) ** 2))


def visibility_threshold(offset: float = 0.0) -> float:
    """The visibility at which the model's S equals the local bound 2,
    1 / (sqrt(2) cos(eps))."""
    return float(LHV_BOUND / (TSIRELSON * np.cos(offset)))


@dataclass(frozen=True)
class Balance:
    """How evenly a random setting fell: the fraction of ones, its standard
    error for a fair coin, and the distance from one half in that error."""

    fraction: float
    stderr: float
    sigmas: float
    n: int


def setting_balance(bits: np.ndarray) -> Balance:
    """The balance of the setting bits ``bits`` against a fair coin."""
    n = int(bits.size)
    fraction = float(np.mean(bits))
    stderr = float(np.sqrt(0.25 / n))
    return Balance(fraction, stderr, (fraction - 0.5) / stderr, n)


def setting_pair_counts(pairs: Pairs, mask: np.ndarray) -> tuple[list[int], float]:
    """The number of events at each setting pair among ``mask`` and the
    chi-square of the four counts against equal shares (three degrees of
    freedom)."""
    counts = [int((mask & (pairs.a == a) & (pairs.b == b)).sum()) for a, b in SETTINGS]
    expected = sum(counts) / len(counts)
    chi2 = float(sum((c - expected) ** 2 / expected for c in counts))
    return counts, chi2


@dataclass(frozen=True)
class Marginal:
    """The fraction of one lab's outcomes that are 1 at one of its own
    settings, once for each setting of the other lab, and the difference in
    units of its standard error."""

    lab: int
    own_setting: int
    fraction: tuple[float, float]  # with the other lab at setting 0, at 1
    n: tuple[int, int]
    difference: float
    stderr: float

    @property
    def sigmas(self) -> float:
        if self.stderr == 0:  # every outcome the same: no scatter to compare
            return float(np.inf) if self.difference else 0.0
        return self.difference / self.stderr


def no_signalling(pairs: Pairs, mask: np.ndarray) -> list[Marginal]:
    """The eight no-signalling comparisons of the events ``mask``: for each
    lab and each of its settings, its fraction of outcome 1 with the other
    lab at setting 0 and at 1. A local or a quantum model gives the same
    fraction; the standard error of the difference is binomial."""
    out = []
    for lab in (1, 2):
        own, other, result = (
            (pairs.a, pairs.b, pairs.x) if lab == 1 else (pairs.b, pairs.a, pairs.y)
        )
        for setting in (0, 1):
            fractions, counts = [], []
            for theirs in (0, 1):
                k = mask & (own == setting) & (other == theirs)
                counts.append(int(k.sum()))
                fractions.append(float(result[k].mean()))
            variance = sum(
                f * (1 - f) / n for f, n in zip(fractions, counts, strict=True)
            )
            out.append(
                Marginal(
                    lab,
                    setting,
                    (fractions[0], fractions[1]),
                    (counts[0], counts[1]),
                    fractions[1] - fractions[0],
                    float(np.sqrt(variance)),
                )
            )
    return out


def events_for_sigmas(s: float, stderr: float, n: int, sigmas: float) -> int:
    """The number of events at which S - 2 would be ``sigmas`` standard
    errors, if S stayed at ``s`` and the error kept falling as 1/sqrt(n)."""
    if s <= LHV_BOUND:
        raise ValueError("S is not above the bound")
    return int(np.ceil(n * (sigmas * stderr / (s - LHV_BOUND)) ** 2))


def signed_sum(state: str, terms: dict[tuple, float]) -> float:
    """S of ``state`` from correlators by setting pair, with the sign pattern
    g of the paper (Eq. S1)."""
    return float(sum(sign(state, *k) * terms[k] for k in SETTINGS))
