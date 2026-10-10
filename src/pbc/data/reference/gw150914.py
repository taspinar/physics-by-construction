"""GW150914: whitened strain, spectrogram, and the chirp mass the signal implies.

Status of the figure: *processed* (measured strain, whitened and band-passed).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from pbc.data.gwosc import Strain, read_strain

EVENT_GPS = 1126259462.4  # GWOSC event record, GWTC-1 v3
PUBLISHED_CHIRP_MASS_SOURCE = 28.6  # solar masses, GWTC-1
PUBLISHED_REDSHIFT = 0.09
BAND = (35.0, 350.0)  # Hz
G_M_SUN_OVER_C3 = 4.925490947e-6  # s, G * M_sun / c^3
LAG_L1 = 0.0069  # s; L1 is shifted by the light-travel delay and inverted to overlay H1

FILES = {
    "H1": "H-H1_GWOSC_4KHZ_R1-1126259447-32.txt.gz",
    "L1": "L-L1_GWOSC_4KHZ_R1-1126259447-32.txt.gz",
}


def whiten(strain: Strain, band: tuple[float, float] = BAND) -> np.ndarray:
    """Whiten by the Welch amplitude spectrum of the full 32 s, then band-pass."""
    rate = strain.sample_rate
    window = signal.windows.tukey(strain.strain.size, alpha=0.1)
    freqs, psd = signal.welch(strain.strain, rate, nperseg=4 * int(rate))
    spectrum = np.fft.rfft(strain.strain * window)
    f = np.fft.rfftfreq(strain.strain.size, 1 / rate)
    amplitude = np.sqrt(np.interp(f, freqs, psd))
    white = np.fft.irfft(spectrum / amplitude, n=strain.strain.size)
    sos = signal.butter(4, band, btype="bandpass", fs=rate, output="sos")
    return signal.sosfiltfilt(sos, white) * np.sqrt(2 / rate)


def template_snr(strain: Strain, chirp_mass: float, fmax: float = 250.0) -> tuple:
    """Matched-filter SNR time series of a leading-order inspiral template.

    The stationary-phase template is h(f) ~ f**(-7/6) exp(-i psi(f)) with
    psi = (3/128) (pi G Mc f / c^3)**(-5/3), correlated with the data
    weighted by the inverse Welch spectrum, for
    f in [BAND[0], fmax]. The phase is maximised by taking the modulus of the
    complex correlation. Returns (gps_time, snr).
    """
    n, rate = strain.strain.size, strain.sample_rate
    data_f = np.fft.rfft(strain.strain * signal.windows.tukey(n, alpha=0.1)) / rate
    f = np.fft.rfftfreq(n, 1 / rate)
    freqs, psd = signal.welch(strain.strain, rate, nperseg=4 * int(rate))
    s_n = np.interp(f, freqs, psd)
    use = (f >= BAND[0]) & (f <= fmax)
    v = np.pi * G_M_SUN_OVER_C3 * chirp_mass * f[use]
    template = np.zeros_like(data_f)
    template[use] = f[use] ** (-7 / 6) * np.exp(-1j * (3 / 128) * v ** (-5 / 3))
    spectrum = np.zeros(n, dtype=complex)
    spectrum[: f.size] = np.where(use, data_f * np.conj(template) / s_n, 0)
    z = 4 * rate * np.fft.ifft(spectrum)
    norm = np.sqrt(4 * np.sum(np.abs(template[use]) ** 2 / s_n[use]) * rate / n)
    return strain.time, np.abs(z) / norm


def fit_chirp_mass(
    strains: dict[str, Strain], masses: np.ndarray, window: float = 0.2
) -> dict:
    """Network SNR of the template within ``window`` s of the event, per mass.

    Returns the masses, the network SNR (H1 and L1 added in quadrature, each
    maximised separately), the best mass, and the H1-L1 delay at that mass.
    """
    network = np.zeros(masses.size)
    delays = np.zeros(masses.size)
    for i, mass in enumerate(masses):
        peaks = {}
        for name, strain in strains.items():
            time, snr = template_snr(strain, mass)
            near = np.abs(time - EVENT_GPS) < window
            k = np.argmax(np.where(near, snr, 0))
            peaks[name] = (snr[k], time[k])
        network[i] = np.hypot(peaks["H1"][0], peaks["L1"][0])
        delays[i] = peaks["H1"][1] - peaks["L1"][1]
    best = int(np.argmax(network))
    return {
        "masses": masses,
        "network_snr": network,
        "best_mass": float(masses[best]),
        "best_snr": float(network[best]),
        "delay": float(delays[best]),
    }


def load(data_dir: Path) -> dict[str, Strain]:
    return {name: read_strain(Path(data_dir) / file) for name, file in FILES.items()}


def make_figure(data_dir: Path) -> plt.Figure:
    strains = load(data_dir)
    white = {name: whiten(s) for name, s in strains.items()}
    shift = EVENT_GPS - strains["H1"].gps_start
    time = strains["H1"].time - EVENT_GPS
    fit = fit_chirp_mass(strains, np.arange(15.0, 60.5, 1.0))
    expected = PUBLISHED_CHIRP_MASS_SOURCE * (1 + PUBLISHED_REDSHIFT)

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(8, 10.5),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [3, 3, 3, 0.5]},
    )
    top, middle, bottom, credit = axes
    span = (time > -0.3) & (time < 0.1)
    top.plot(time[span], white["H1"][span], label="H1", color="#0072B2")
    top.plot(
        time[span] - LAG_L1,
        -white["L1"][span],
        label=f"L1 (shifted {LAG_L1 * 1e3:.1f} ms, inverted)",
        color="#D55E00",
    )
    top.set_xlabel(f"time since GPS {EVENT_GPS} [s]")
    top.set_ylabel("whitened strain [arb. units]")
    top.set_title(
        f"Processed: GW150914, whitened and band-passed {BAND[0]:.0f}-{BAND[1]:.0f} Hz"
    )
    top.legend(loc="upper left")

    f, t, sxx = signal.spectrogram(
        white["H1"], strains["H1"].sample_rate, nperseg=256, noverlap=240
    )
    keep = (t - shift > -0.5) & (t - shift < 0.2)
    mesh = middle.pcolormesh(
        t[keep] - shift, f, np.sqrt(sxx[:, keep]), shading="auto", cmap="viridis"
    )
    middle.set_ylim(20, 400)
    middle.set_xlabel("time since the event [s]")
    middle.set_ylabel("frequency [Hz]")
    middle.set_title("Processed: H1 spectrogram of the whitened strain")
    fig.colorbar(mesh, ax=middle, label="amplitude [arb. units]")

    bottom.plot(fit["masses"], fit["network_snr"], color="#009E73")
    bottom.axvline(
        expected, color="k", linestyle="--", label="published, detector frame"
    )
    bottom.set_xlabel("template chirp mass, detector frame [solar masses]")
    bottom.set_ylabel("network matched-filter SNR")
    bottom.set_title(
        "Fitted (leading-order template): best "
        f"{fit['best_mass']:.0f} Msun, SNR {fit['best_snr']:.0f}; published "
        f"{PUBLISHED_CHIRP_MASS_SOURCE} x (1+z) = {expected:.0f} Msun"
    )
    bottom.legend()
    credit.axis("off")
    credit.text(
        0,
        1,
        "Data: GWOSC, GW150914 v3 strain, CC BY 4.0. This research has made use of "
        "data or software obtained from the\nGravitational Wave Open Science Center "
        "(gwosc.org), a service of the LIGO Scientific Collaboration, the Virgo\n"
        "Collaboration, and KAGRA.",
        fontsize=7,
        va="top",
    )
    return fig
