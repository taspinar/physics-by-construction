"""Inferring the geometry of a double slit from the intensity on a detector.

The forward model is the Fraunhofer pattern of two slits of width a, a
distance d apart, in light of wavelength lambda,

    I(s) = A sinc^2(a s / lambda) cos^2(pi d s / lambda) + b,

with s = sin(theta), sinc(x) = sin(pi x) / (pi x), an amplitude A, and a
background b. Photon counts on a row of pixels are Poisson numbers. The
parameters are estimated by weighted least squares, with the covariance
from the Jacobian at the minimum; the start comes from the spectrum of the
counts and a scan of the slit width, not from the true values.

The model depends on a and d only through a / lambda and d / lambda, so the
three cannot be estimated together; ``scaled_jacobian`` shows it.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import least_squares

Array = NDArray[np.float64]

NAMES = ("amplitude", "background", "width", "separation")


def double_slit_model(
    s: ArrayLike,
    amplitude: float,
    background: float,
    width: float,
    separation: float,
    wavelength: float,
) -> Array:
    """The expected counts A sinc^2(a s / lambda) cos^2(pi d s / lambda) + b
    at the directions ``s``."""
    s = np.asarray(s, dtype=float)
    envelope = np.sinc(width * s / wavelength) ** 2
    return (
        amplitude * envelope * np.cos(np.pi * separation * s / wavelength) ** 2
        + background
    )


def detector(pixels: int, pitch: float, distance: float) -> tuple[Array, Array]:
    """The centres y (m) of ``pixels`` pixels of ``pitch`` m on a flat
    detector at ``distance`` m, centred on the axis, and their directions
    s = y / sqrt(y^2 + L^2)."""
    y = (np.arange(pixels) - (pixels - 1) / 2) * pitch
    return y, y / np.hypot(y, distance)


@dataclass(frozen=True)
class Fit:
    """The estimate, its standard errors and covariance, chi^2, and the
    number of degrees of freedom."""

    values: Array
    errors: Array
    covariance: Array
    chi2: float
    dof: int

    def value(self, name: str) -> float:
        return float(self.values[NAMES.index(name)])

    def error(self, name: str) -> float:
        return float(self.errors[NAMES.index(name)])


def residuals(params: ArrayLike, s: Array, counts: Array, wavelength: float) -> Array:
    """(counts - model) / sqrt(model): the Pearson residuals, whose sum of
    squares is chi^2 for Poisson counts."""
    model = double_slit_model(s, *params, wavelength)
    return (counts - model) / np.sqrt(np.maximum(model, 1.0))


def start(s: Array, counts: Array, wavelength: float) -> Array:
    """A start for the fit from the data alone: the separation from the
    strongest frequency of the counts against s (the fringes), the amplitude
    and the background from the largest and the smallest counts, and the
    width from a scan of chi^2 with the other three held."""
    uniform = np.linspace(s[0], s[-1], s.size)
    resampled = np.interp(uniform, s, counts)
    spectrum = np.abs(np.fft.rfft(resampled - resampled.mean()))
    frequencies = np.fft.rfftfreq(s.size, uniform[1] - uniform[0])
    # The spectrum of a double-slit pattern is the autocorrelation of the
    # aperture: a peak at zero frequency, from the envelope, as wide as
    # a / lambda, and the fringe peak at d / lambda. Past the first minimum
    # of the spectrum, the strongest frequency is the fringes (for d > 2 a).
    first_minimum = 1 + int(np.argmax(np.diff(spectrum[1:]) > 0))
    strongest = first_minimum + int(np.argmax(spectrum[first_minimum:]))
    separation = frequencies[strongest] * wavelength
    amplitude = float(np.max(counts) - np.min(counts))
    background = float(max(np.min(counts), 1.0))
    widths = np.linspace(0.05, 0.95, 91) * separation
    chi2 = [
        np.sum(
            residuals((amplitude, background, w, separation), s, counts, wavelength)
            ** 2
        )
        for w in widths
    ]
    return np.array([amplitude, background, widths[int(np.argmin(chi2))], separation])


def fit(
    s: Array, counts: Array, wavelength: float, guess: ArrayLike | None = None
) -> Fit:
    """The weighted least-squares estimate of (A, b, a, d) for a known
    wavelength, from ``guess`` or from ``start``."""
    p0 = (
        start(s, counts, wavelength)
        if guess is None
        else np.asarray(guess, dtype=float)
    )
    scale = np.abs(p0)
    result = least_squares(
        lambda q: residuals(q * scale, s, counts, wavelength),
        np.ones_like(p0),
        method="lm",
        xtol=1e-12,
        ftol=1e-12,
    )
    values = result.x * scale
    jacobian = result.jac / scale  # with respect to the unscaled parameters
    covariance = np.linalg.inv(jacobian.T @ jacobian)
    chi2 = float(np.sum(result.fun**2))
    return Fit(values, np.sqrt(np.diag(covariance)), covariance, chi2, s.size - p0.size)


def scaled_jacobian(
    s: Array,
    amplitude: float,
    background: float,
    width: float,
    separation: float,
    wavelength: float,
) -> Array:
    """The Jacobian of the Pearson-weighted model with respect to the
    logarithms of (A, b, a, d, lambda), by central differences: a column is
    the change of the residuals for a relative change of one parameter. A
    singular value of zero is a direction in which the data cannot tell the
    parameters apart."""
    params = np.array([amplitude, background, width, separation, wavelength])
    weight = np.sqrt(np.maximum(double_slit_model(s, *params[:4], wavelength), 1.0))
    columns = []
    for i in range(params.size):
        step = 1e-6
        up, down = params.copy(), params.copy()
        up[i] *= 1 + step
        down[i] *= 1 - step
        columns.append(
            (
                double_slit_model(s, *up[:4], up[4])
                - double_slit_model(s, *down[:4], down[4])
            )
            / (2 * step)
            / weight
        )
    return np.column_stack(columns)
