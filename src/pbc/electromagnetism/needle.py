"""A compass needle in a uniform magnetic field, filmed (F142, the generated
clips of the lesson "Measurement quality and multimodal observations").

A magnetised needle with magnetic moment m and moment of inertia I, free to
turn about its centre in a uniform field B, feels the torque -m B sin(theta),
where theta is its angle from the field. With a damping torque proportional
to its angular velocity the equation of motion is

    theta'' + 2 gamma theta' + omega_0^2 sin(theta) = 0,  omega_0^2 = m B / I,

so for small swings the needle oscillates at omega_d = sqrt(omega_0^2 -
gamma^2) while the swing decays as e^(-gamma t). Timing the swing measures
the field: B = I (omega_d^2 + gamma^2) / m, the classic method of measuring a
field with a compass needle, used here on a generated clip.

The module simulates the motion, renders the frames a camera would record at
a given frame rate (greyscale, the field pointing up the image, no camera
noise and no motion blur), finds the needle's angle in each frame from its
pixels, and fits a decaying cosine to the track. Every frame is generated
from the simulation, never filmed.
"""

import base64
import io
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit

# The needle of the lesson: a small magnet on a pivot.
MOMENT = 0.125  # A m^2
INERTIA = 1.0e-7  # kg m^2
FIELD = 5.0e-4  # T: the uniform field, as a pair of coils would make it
DAMPING = 0.5  # 1/s: the decay rate gamma of the swing
START_DEG = 15.0  # the needle is released from rest at this angle

# The frame: 160 by 120 pixels, the pivot near the centre.
WIDTH, HEIGHT = 160, 120
PIVOT = (80.0, 64.0)  # x (column) and y (row) of the pivot, pixels
TIP = 44.0  # pixels from the pivot to the north tip
TAIL = 20.0  # pixels from the pivot to the south end
DIAL = (47.0, 53.0)  # inner and outer radius of the scale's ticks, pixels
BACKGROUND, NEEDLE, TAIL_GREY, SCALE = 240.0, 25.0, 160.0, 185.0
# The annulus the tracking reads: beyond the south end, inside the ticks.
TRACK = (24.0, 40.0)


@dataclass(frozen=True)
class Needle:
    """A needle of ``moment`` (A m^2) and ``inertia`` (kg m^2) in a field
    ``field`` (T), with the decay rate ``damping`` (1/s)."""

    moment: float = MOMENT
    inertia: float = INERTIA
    field: float = FIELD
    damping: float = DAMPING

    @property
    def omega0(self) -> float:
        """The angular frequency of small undamped swings (rad/s)."""
        return math.sqrt(self.moment * self.field / self.inertia)

    @property
    def frequency(self) -> float:
        """The frequency of small damped swings (Hz)."""
        return math.sqrt(self.omega0**2 - self.damping**2) / (2.0 * math.pi)


def simulate(needle: Needle, t: NDArray[np.float64], start_deg: float = START_DEG):
    """The angle of the needle (rad) at the times ``t`` (s), released from
    rest at ``start_deg`` (deg), by an eighth-order Runge-Kutta method with
    error control (SciPy's DOP853)."""
    t = np.asarray(t, dtype=float)

    def rates(_: float, state: NDArray[np.float64]) -> list[float]:
        theta, spin = state
        return [
            spin,
            -2.0 * needle.damping * spin - needle.omega0**2 * math.sin(theta),
        ]

    solution = solve_ivp(
        rates,
        (0.0, float(t[-1])),
        [math.radians(start_deg), 0.0],
        method="DOP853",
        t_eval=t,
        rtol=1e-11,
        atol=1e-12,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    return solution.y[0]


def field_from_frequency(
    frequency_hz: float, damping: float, needle: Needle = Needle()
) -> float:
    """The field (T) that makes the needle swing at ``frequency_hz`` (Hz)
    with the decay rate ``damping`` (1/s), for small swings:
    B = I ((2 pi f)^2 + gamma^2) / m."""
    omega = 2.0 * math.pi * frequency_hz
    return needle.inertia * (omega**2 + damping**2) / needle.moment


def _segment_coverage(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    start: tuple[float, float],
    end: tuple[float, float],
    half_width: float,
) -> NDArray[np.float64]:
    """How much of each pixel a line of ``half_width`` pixels from ``start``
    to ``end`` covers, from the distance of the pixel's centre to the line,
    with a soft edge one pixel wide."""
    (x0, y0), (x1, y1) = start, end
    dx, dy = x1 - x0, y1 - y0
    along = np.clip(((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    distance = np.hypot(x - (x0 + along * dx), y - (y0 + along * dy))
    return np.clip(half_width + 0.5 - distance, 0.0, 1.0)


def render_frame(theta: float) -> NDArray[np.uint8]:
    """The greyscale frame (rows by columns) of the needle at the angle
    ``theta`` (rad, clockwise from the field, which points up the image):
    the scale's ticks every ten degrees, the dark north half to the tip, the
    grey south half."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(float)
    image = np.full((HEIGHT, WIDTH), BACKGROUND)

    def paint(coverage: NDArray[np.float64], level: float) -> None:
        nonlocal image
        image = image * (1.0 - coverage) + level * coverage

    px, py = PIVOT
    for tick in range(-60, 61, 10):
        a = math.radians(tick)
        inner = DIAL[0] - (3.0 if tick == 0 else 0.0)
        paint(
            _segment_coverage(
                x,
                y,
                (px + inner * math.sin(a), py - inner * math.cos(a)),
                (px + DIAL[1] * math.sin(a), py - DIAL[1] * math.cos(a)),
                0.5,
            ),
            SCALE,
        )
    s, c = math.sin(theta), math.cos(theta)
    paint(
        _segment_coverage(x, y, (px, py), (px - TAIL * s, py + TAIL * c), 1.5),
        TAIL_GREY,
    )
    paint(_segment_coverage(x, y, (px, py), (px + TIP * s, py - TIP * c), 1.5), NEEDLE)
    paint(np.clip(3.0 + 0.5 - np.hypot(x - px, y - py), 0.0, 1.0), NEEDLE)
    return np.round(image).astype(np.uint8)


def track_angle(frame: NDArray[np.uint8]) -> float:
    """The angle of the needle (rad, clockwise from up) in ``frame``: the
    direction from the pivot to the darkness-weighted centre of the pixels in
    the annulus between the radii of ``TRACK``, where only the north half of
    the needle lies. The line is symmetric about its axis, so the centre lies
    on the axis."""
    y, x = np.mgrid[0 : frame.shape[0], 0 : frame.shape[1]].astype(float)
    dx, dy = x - PIVOT[0], y - PIVOT[1]
    radius = np.hypot(dx, dy)
    inside = (radius >= TRACK[0]) & (radius <= TRACK[1])
    weight = np.where(inside, np.clip(BACKGROUND - frame.astype(float), 0.0, None), 0.0)
    return math.atan2(float((weight * dx).sum()), float((weight * -dy).sum()))


@dataclass(frozen=True)
class Clip:
    """A generated clip: its frame rate (frames/s), the times of its frames
    (s), the simulated angles (rad), and the frames."""

    frame_rate: float
    t: NDArray[np.float64]
    theta: NDArray[np.float64]
    frames: tuple[NDArray[np.uint8], ...]


def film(needle: Needle, frame_rate: float, duration: float) -> Clip:
    """The clip of ``needle`` at ``frame_rate`` (frames/s) for ``duration``
    (s): one instantaneous frame at each frame time from zero."""
    count = round(duration * frame_rate)
    t = np.arange(count) / frame_rate
    theta = simulate(needle, t)
    return Clip(frame_rate, t, theta, tuple(render_frame(a) for a in theta))


@dataclass(frozen=True)
class TrackFit:
    """A decaying cosine A e^(-gamma t) cos(2 pi f t + phi) fitted to a track:
    the frequency (Hz), the decay rate (1/s), the amplitude (rad), and the
    RMS of the residuals (rad)."""

    frequency: float
    damping: float
    amplitude: float
    residual_rms: float


def _decaying_cosine(t, amplitude, damping, frequency, phase):
    return (
        amplitude * np.exp(-damping * t) * np.cos(2.0 * np.pi * frequency * t + phase)
    )


def fit_track(t: NDArray[np.float64], angle: NDArray[np.float64]) -> TrackFit:
    """Fit a decaying cosine to the angles ``angle`` (rad) at the times ``t``
    (s), starting from the strongest frequency of the track's spectrum below
    half the frame rate: the fit sees only the frames, as a person reading
    the clip would."""
    t, angle = np.asarray(t, dtype=float), np.asarray(angle, dtype=float)
    rate = 1.0 / (t[1] - t[0])
    padded = 64 * len(t)
    spectrum = np.abs(np.fft.rfft(angle - angle.mean(), padded))
    frequencies = np.fft.rfftfreq(padded, 1.0 / rate)
    start = float(frequencies[1 + int(np.argmax(spectrum[1:]))])
    guess = (float(np.max(np.abs(angle))), 0.1, start, 0.0)
    found, _ = curve_fit(_decaying_cosine, t, angle, p0=guess, maxfev=20_000)
    amplitude, damping, frequency, _ = (float(v) for v in found)
    if amplitude < 0:
        amplitude = -amplitude
    residual = angle - _decaying_cosine(t, *found)
    return TrackFit(
        frequency=abs(frequency),
        damping=damping,
        amplitude=amplitude,
        residual_rms=float(np.sqrt(np.mean(residual**2))),
    )


def png(frame: NDArray[np.uint8]) -> bytes:
    """The frame as a greyscale PNG, with no metadata."""
    buffer = io.BytesIO()
    Image.fromarray(frame, mode="L").save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def data_url(frame: NDArray[np.uint8]) -> str:
    """The frame as a data URL of its PNG, for the on-demand file."""
    return "data:image/png;base64," + base64.b64encode(png(frame)).decode("ascii")
