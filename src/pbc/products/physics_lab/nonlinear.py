"""The amplitude-dependent response of a bounded nonlinear example (F145):
two LEDs of one colour in anti-parallel behind a series resistor
(``pbc.electromagnetism.led_pair``), channel ``response`` across the pair.

One point: drive the circuit with a sine of amplitude A at a fixed
frequency, pass the capture through the quality gate, and read the pair's
voltage at the fundamental and at the third harmonic
(``pbc.electromagnetism.measurement.fit_sine`` over the valid samples): the
fundamental gain G1 = |V_1| / |S_1| and the third-harmonic ratio
h3 = |V_3| / |V_1|, each with its standard error. Below the LEDs'
conduction G1 is one and h3 zero; above it G1 falls and h3 grows. The
frequency is low enough for the circuit to be memoryless, so the response
depends on the amplitude only.

Every sample also gives a point of the pair's static characteristic: the
current i = (v_s - v) / R through the declared resistor R against the
pair's voltage v. ``fit_characteristic`` fits v = n V_T asinh(i / 2 I_s) to
the samples above ``MIN_CURRENT_A``, giving n and I_s with their errors.

The checks:

- the simulator's: the fitted characteristic against the declared LEDs of
  the simulated bench (n, and the voltage at 1 mA);
- every route's, the held-out prediction: the characteristic fitted on the
  largest amplitude alone predicts G1 at every other amplitude, which is
  compared with the measured G1 within their combined errors
  (``estimates.agreement``). The prediction solves the circuit with the
  fitted LEDs; it never sees the other captures.
"""

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import curve_fit

from pbc.electromagnetism.led_pair import THERMAL_VOLTAGE_V, LEDPair, harmonics
from pbc.electromagnetism.measurement import fit_sine
from pbc.instruments import Capture, Instrument
from pbc.products.physics_lab.estimates import Agreement, Estimate, agreement
from pbc.products.physics_lab.quality import IDEAL_RAILS, Rails, Verdict, gate

PROTOCOL_VERSION = "f145-amplitude-response-1"
# The characteristic is fitted to the samples that carry at least this
# current (A): below it the channels' noise, divided by R, is comparable.
MIN_CURRENT_A = 0.5e-3
MIN_CHARACTERISTIC_SAMPLES = 20
REFERENCE_CURRENT_A = 1e-3
# The odd harmonics fitted together; the pair is symmetric, so the even
# ones vanish.
ORDERS = (1, 3, 5, 7)
# The simulator's check: the ideality within this fraction and the voltage
# at 1 mA within this many volts of the declared LEDs.
IDEALITY_TOLERANCE = 0.05
VOLTAGE_TOLERANCE_V = 0.01


@dataclass(frozen=True)
class NonlinearSettings:
    """The ``frequency_hz`` (Hz) of the sine, the acquisition's ``periods``
    and ``samples_per_period``, and the declared series resistance
    ``resistance_ohm`` (ohm) through which the current is read."""

    frequency_hz: float = 1_000.0
    periods: int = 8
    samples_per_period: int = 64
    resistance_ohm: float = 100.0

    @property
    def sample_rate_hz(self) -> float:
        return self.samples_per_period * self.frequency_hz

    @property
    def samples(self) -> int:
        return self.periods * self.samples_per_period + 1


@dataclass(frozen=True)
class AmplitudePoint:
    """One valid point: the set ``amplitude_v`` (V), the source amplitude
    read ``source_v`` (V), the fundamental gain ``gain`` (V/V) and the
    third-harmonic ratio ``h3`` (V/V), with their standard errors."""

    amplitude_v: float
    source_v: float
    gain: float
    gain_se: float
    h3: float
    h3_se: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class AmplitudeMeasurement:
    amplitude_v: float
    capture: Capture
    verdict: Verdict
    point: AmplitudePoint | None
    note: str

    @property
    def valid(self) -> bool:
        return self.point is not None


def _ratio_se(x: float, x_se: float, y: float, y_se: float) -> float:
    """The standard error of x / y."""
    return abs(x / y) * math.hypot(x_se / x if x else 0.0, y_se / y)


def fit_harmonics(
    t: np.ndarray,
    v: np.ndarray,
    frequency_hz: float,
    orders: tuple[int, ...],
    valid: np.ndarray,
) -> dict[int, tuple[float, float]]:
    """The amplitude (V) and its standard error (V) of each harmonic
    ``orders`` of ``frequency_hz`` (Hz) in the samples ``v`` (V) at ``t``
    (s): one linear least-squares fit of a cosine and a sine of every
    order and a constant to the ``valid`` samples, so that no harmonic is
    left in the residuals of another. The errors come from the residual
    variance, as ``fit_sine``'s do."""
    keep = np.asarray(valid) & np.isfinite(v)
    tk, vk = t[keep], v[keep]
    columns = []
    for n in orders:
        omega = 2.0 * math.pi * n * frequency_hz
        columns += [np.cos(omega * tk), np.sin(omega * tk)]
    design = np.column_stack([*columns, np.ones(len(tk))])
    if len(tk) <= design.shape[1]:
        raise ValueError("too few valid samples for the harmonics")
    coefficients, *_ = np.linalg.lstsq(design, vk, rcond=None)
    residuals = vk - design @ coefficients
    variance = float(residuals @ residuals) / (len(tk) - design.shape[1])
    covariance = variance * np.linalg.inv(design.T @ design)
    found = {}
    for k, n in enumerate(orders):
        a, b = coefficients[2 * k], coefficients[2 * k + 1]
        amplitude = math.hypot(a, b)
        block = covariance[2 * k : 2 * k + 2, 2 * k : 2 * k + 2]
        gradient = np.array([a, b]) / amplitude if amplitude else np.array([1.0, 0.0])
        found[n] = (amplitude, math.sqrt(max(float(gradient @ block @ gradient), 0.0)))
    return found


def analyse_amplitude(
    capture: Capture,
    amplitude_v: float,
    settings: NonlinearSettings,
    rails: Rails = IDEAL_RAILS,
) -> AmplitudeMeasurement:
    """Gate ``capture`` and read G1 and h3 with their errors."""
    f = settings.frequency_hz
    verdict = gate(capture, amplitude_v, 3.0 * f, rails)
    if not verdict.valid:
        note = "; ".join(verdict.reasons)
        return AmplitudeMeasurement(amplitude_v, capture, verdict, None, note)
    t = np.asarray(capture.t, dtype=float)
    source = np.asarray(capture.channels["source"], dtype=float)
    response = np.asarray(capture.channels["response"], dtype=float)
    # region: harmonics
    s1 = fit_sine(t, source, f, verdict.masks["source"])
    v = fit_harmonics(t, response, f, ORDERS, verdict.masks["response"])
    (v1, v1_se), (v3, v3_se) = v[1], v[3]
    gain = v1 / s1.amplitude
    h3 = v3 / v1
    # endregion: harmonics
    point = AmplitudePoint(
        amplitude_v=amplitude_v,
        source_v=s1.amplitude,
        gain=gain,
        gain_se=_ratio_se(v1, v1_se, s1.amplitude, s1.amplitude_error),
        h3=h3,
        h3_se=_ratio_se(v3, v3_se, v1, v1_se),
    )
    return AmplitudeMeasurement(amplitude_v, capture, verdict, point, "read")


def measure_amplitude(
    instrument: Instrument,
    amplitude_v: float,
    settings: NonlinearSettings,
    rails: Rails = IDEAL_RAILS,
) -> AmplitudeMeasurement:
    """Measure one amplitude through the guarded instrument."""
    instrument.excite(amplitude_v, settings.frequency_hz)
    capture = instrument.acquire(settings.sample_rate_hz, settings.samples)
    return analyse_amplitude(capture, amplitude_v, settings, rails)


@dataclass(frozen=True)
class Characteristic:
    """The fitted static characteristic of the pair: the ideality ``n``,
    the natural logarithm of the saturation current ``log_is`` (ln A), the
    voltage at 1 mA ``v_ref`` (V), their covariance of (n, log_is), and the
    number of samples used."""

    n: Estimate
    log_is: Estimate
    v_ref: Estimate
    covariance: tuple[tuple[float, float], tuple[float, float]]
    samples: int

    def pair(
        self, resistance_ohm: float, n: float | None = None, log_is: float | None = None
    ) -> LEDPair:
        return LEDPair(
            resistance=resistance_ohm,
            saturation_current=math.exp(
                self.log_is.value if log_is is None else log_is
            ),
            ideality=self.n.value if n is None else n,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "n": self.n.to_dict(),
            "log_is": self.log_is.to_dict(),
            "v_ref": self.v_ref.to_dict(),
            "reference_current_a": REFERENCE_CURRENT_A,
            "samples": self.samples,
        }


def _inverse(i: np.ndarray, n: float, log_is: float) -> np.ndarray:
    return n * THERMAL_VOLTAGE_V * np.arcsinh(i / (2.0 * math.exp(log_is)))


def characteristic_samples(
    measurements: Sequence[AmplitudeMeasurement], resistance_ohm: float
) -> tuple[np.ndarray, np.ndarray]:
    """The current (A) and the pair's voltage (V) of every valid sample of
    the valid ``measurements``, folded onto positive current (the pair is
    symmetric)."""
    currents, voltages = [], []
    for m in measurements:
        if not m.valid:
            continue
        keep = m.verdict.masks["source"] & m.verdict.masks["response"]
        vs = np.asarray(m.capture.channels["source"], dtype=float)[keep]
        v = np.asarray(m.capture.channels["response"], dtype=float)[keep]
        currents.append((vs - v) / resistance_ohm)
        voltages.append(v)
    if not currents:
        return np.array([]), np.array([])
    i, v = np.concatenate(currents), np.concatenate(voltages)
    sign = np.sign(i)
    return i * sign, v * sign


def fit_characteristic(
    measurements: Sequence[AmplitudeMeasurement], resistance_ohm: float
) -> Characteristic | None:
    """Fit v = n V_T asinh(i / 2 I_s) to the samples above
    ``MIN_CURRENT_A``, or None with too few of them."""
    i, v = characteristic_samples(measurements, resistance_ohm)
    keep = i >= MIN_CURRENT_A
    if keep.sum() < MIN_CHARACTERISTIC_SAMPLES:
        return None
    i, v = i[keep], v[keep]
    # A start from the two ends of the range: the slope of v against ln i
    # is n V_T, and v = n V_T ln(i / I_s) there.
    slope, intercept = np.polyfit(np.log(i), v, 1)
    n0 = max(slope / THERMAL_VOLTAGE_V, 0.5)
    log_is0 = -intercept / slope if slope > 0 else -40.0
    # region: characteristic
    try:
        values, covariance = curve_fit(_inverse, i, v, p0=[n0, log_is0], maxfev=20_000)
    except RuntimeError:
        return None
    # endregion: characteristic
    if not np.all(np.isfinite(covariance)):
        return None
    n, log_is = (float(x) for x in values)
    # The voltage at 1 mA and its error, from the gradient of _inverse.
    v_ref = float(_inverse(np.array(REFERENCE_CURRENT_A), n, log_is))
    gradient = np.array([v_ref / n, -n * THERMAL_VOLTAGE_V])
    v_ref_se = math.sqrt(max(float(gradient @ covariance @ gradient), 0.0))
    return Characteristic(
        Estimate(n, math.sqrt(covariance[0, 0])),
        Estimate(log_is, math.sqrt(covariance[1, 1])),
        Estimate(v_ref, v_ref_se),
        (
            (float(covariance[0, 0]), float(covariance[0, 1])),
            (float(covariance[1, 0]), float(covariance[1, 1])),
        ),
        int(keep.sum()),
    )


def predict_gain(
    characteristic: Characteristic, resistance_ohm: float, source_v: float
) -> Estimate:
    """G1 at the source amplitude ``source_v`` (V) predicted from the
    fitted characteristic: the circuit solved over one period with the
    fitted LEDs, its error propagated from the fit's covariance by finite
    differences."""

    # region: predict
    def gain(n: float, log_is: float) -> float:
        pair = characteristic.pair(resistance_ohm, n, log_is)
        return harmonics(pair, source_v, (1,))[1] / source_v

    n, log_is = characteristic.n.value, characteristic.log_is.value
    value = gain(n, log_is)
    # endregion: predict
    dn = max(characteristic.n.se, 1e-6)
    dl = max(characteristic.log_is.se, 1e-6)
    gradient = np.array(
        [
            (gain(n + dn, log_is) - gain(n - dn, log_is)) / (2 * dn),
            (gain(n, log_is + dl) - gain(n, log_is - dl)) / (2 * dl),
        ]
    )
    covariance = np.array(characteristic.covariance)
    se = math.sqrt(max(float(gradient @ covariance @ gradient), 0.0))
    return Estimate(value, se)


@dataclass(frozen=True)
class HeldOut:
    """The held-out check: the characteristic fitted on ``fitted_on`` (the
    largest valid amplitude, V), and the agreement of predicted and measured
    G1 at every other valid amplitude."""

    fitted_on: float
    characteristic: Characteristic
    agreements: tuple[tuple[float, Agreement], ...]

    @property
    def agree(self) -> bool:
        return all(a.agree for _, a in self.agreements)


def held_out_check(
    measurements: Sequence[AmplitudeMeasurement], resistance_ohm: float
) -> HeldOut | None:
    """Fit the characteristic on the largest valid amplitude and predict
    G1 at the others. None without two valid amplitudes or a fit."""
    valid = sorted((m for m in measurements if m.valid), key=lambda m: m.amplitude_v)
    if len(valid) < 2:
        return None
    largest = valid[-1]
    characteristic = fit_characteristic([largest], resistance_ohm)
    if characteristic is None:
        return None
    agreements = []
    for m in valid[:-1]:
        point = m.point
        assert point is not None
        predicted = predict_gain(characteristic, resistance_ohm, point.source_v)
        measured = Estimate(point.gain, point.gain_se)
        agreements.append(
            (
                m.amplitude_v,
                agreement("G1", "measured", measured, "predicted", predicted),
            )
        )
    return HeldOut(largest.amplitude_v, characteristic, tuple(agreements))


@dataclass(frozen=True)
class NonlinearCheck:
    correct: bool
    metrics: dict[str, float]
    note: str


def check_against_model(
    characteristic: Characteristic, pair: LEDPair
) -> NonlinearCheck:
    """The simulator's check: the fitted ideality within
    ``IDEALITY_TOLERANCE`` and the voltage at 1 mA within
    ``VOLTAGE_TOLERANCE_V`` of the declared LEDs of the simulated bench."""
    declared_v = pair.forward_voltage(REFERENCE_CURRENT_A)
    metrics = {
        "n": characteristic.n.value,
        "n_se": characteristic.n.se,
        "reference_n": pair.ideality,
        "v_ref": characteristic.v_ref.value,
        "v_ref_se": characteristic.v_ref.se,
        "reference_v_ref": declared_v,
        "n_relative_error": characteristic.n.value / pair.ideality - 1.0,
        "v_ref_error": characteristic.v_ref.value - declared_v,
    }
    correct = bool(
        abs(metrics["n_relative_error"]) <= IDEALITY_TOLERANCE
        and abs(metrics["v_ref_error"]) <= VOLTAGE_TOLERANCE_V
    )
    note = (
        f"{'within' if correct else 'outside'} the tolerance of the declared"
        f" LEDs (n within {IDEALITY_TOLERANCE:.0%}, the voltage at 1 mA within"
        f" {VOLTAGE_TOLERANCE_V * 1e3:g} mV)"
    )
    return NonlinearCheck(correct, metrics, note)
