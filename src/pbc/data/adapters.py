"""The readers' results as ``Series``, with the artifact type of their source.

Each adapter states what the card says about the data it wraps: the type of the
artifact, the unit, and where the uncertainty comes from. Labs start here and
never decide a status by hand.
"""

from typing import TYPE_CHECKING

import numpy as np

from pbc.data.flume import Elevation
from pbc.data.gwosc import Strain
from pbc.data.series import Series
from pbc.data.touchstone import Network
from pbc.data.uncertainty import standard_from_expanded

if TYPE_CHECKING:
    from pbc.data.reference.bayreuth_rlc import Spectrum
    from pbc.data.reference.dwd_soil import Readings
    from pbc.data.reference.grazing_flow_hwa import Station
    from pbc.data.reference.lycopodium import Profile
    from pbc.data.reference.nist_numisheet import Test
    from pbc.data.reference.sdss_balmer import Spectrum as SdssSpectrum
    from pbc.data.reference.tess_wasp18 import LightCurve
    from pbc.data.reference.trackpy_bulk_water import Tracks
    from pbc.data.reference.tudelft_boundary_layer import (
        Profile as BoundaryLayerProfile,
    )
    from pbc.data.reference.xu_pendulum import Run


def strain_series(strain: Strain) -> Series:
    """Calibrated strain of one detector (the LIGO calibration pipeline output)."""
    return Series(
        x=strain.time,
        y=strain.strain,
        artifact="calibrated-observation",
        x_name="GPS time",
        x_unit="s",
        y_name=f"{strain.detector} strain",
        y_unit="1",
    )


def transmission_series(network: Network) -> Series:
    """|S21| in dB against frequency in GHz of a calibrated two-port."""
    return Series(
        x=network.frequency / 1e9,
        y=20 * np.log10(np.abs(network.s[:, 1, 0])),
        artifact="calibrated-observation",
        x_name="frequency",
        x_unit="GHz",
        y_name="|S21|",
        y_unit="dB",
    )


def measured_elevation(elevation: Elevation, gauge: int) -> Series:
    """Mean of the repetitions at ``gauge`` with the standard uncertainty.

    The file gives the expanded uncertainty of the mean at 95 % confidence; the
    series carries the standard one.
    """
    return Series(
        x=elevation.time,
        y=elevation.column(gauge, "mean"),
        sigma=standard_from_expanded(elevation.column(gauge, "expanded unc")),
        artifact="processed-measured",
        x_name="time",
        x_unit="s",
        y_name="surface elevation",
        y_unit="m",
    )


def modelled_elevation(elevation: Elevation) -> Series:
    """The single column of a numerical run, as a modelled reference."""
    return Series(
        x=elevation.time,
        y=elevation.values[:, 0],
        artifact="modelled-reference",
        x_name="time",
        x_unit="s",
        y_name="surface elevation",
        y_unit="m",
    )


def impedance_series(spectrum: Spectrum, part: str) -> Series:
    """|Z| in ohm (``part="modulus"``) or the phase of Z in degrees
    (``part="phase"``) against frequency in Hz, in increasing frequency.

    The potentiostat's spectrum as its creators exported it: processed, since
    the step from the recorded voltage and current to Z is not documented.
    The record gives no uncertainty per point, so the series carries none.
    """
    order = np.argsort(spectrum.frequency)
    z = spectrum.impedance[order]
    if part == "modulus":
        y, name, unit = np.abs(z), "|Z|", "ohm"
    elif part == "phase":
        y, name, unit = np.degrees(np.angle(z)), "phase of Z", "deg"
    else:
        raise ValueError(f"part {part!r} is not 'modulus' or 'phase'")
    return Series(
        x=spectrum.frequency[order],
        y=y,
        artifact="processed-measured",
        x_name="frequency",
        x_unit="Hz",
        y_name=name,
        y_unit=unit,
    )


def hot_wire_intensity_series(station: Station) -> Series:
    """The streamwise turbulence intensity TI in % of a hot-wire profile of
    the grazing-flow benchmark against the wall distance y/delta, in
    increasing y.

    Processed, as for :func:`hot_wire_profile_series`. The record gives the
    lower and upper bounds of a 95 % interval of TI, statistical only; the
    series carries, as a standard uncertainty, the larger distance from TI to
    either bound, so an asymmetric interval is not narrowed. The hot wire's
    calibration uncertainty is not in the record and not included.
    """
    half_width = np.maximum(
        station.TI_upper - station.TI, station.TI - station.TI_lower
    )
    return Series(
        x=station.y_over_delta,
        y=station.TI,
        sigma=standard_from_expanded(half_width),
        artifact="processed-measured",
        x_name="y/delta",
        x_unit="1",
        y_name="TI",
        y_unit="%",
    )


def hot_wire_profile_series(station: Station) -> Series:
    """The mean velocity U/Ue of a hot-wire profile of the grazing-flow
    benchmark against the wall distance y/delta, in increasing y.

    Processed, as the card labels the file: statistics of the hot-wire time
    series, normalised by the creators, with the y of the solid-wall
    profiles refined by a fit to canonical profiles. The record's
    uncertainty is a 95 % half-width of the mean, statistical only; the
    series carries the standard one. The hot wire's calibration uncertainty
    is not in the record and not included.
    """
    return Series(
        x=station.y_over_delta,
        y=station.U_over_Ue,
        sigma=standard_from_expanded(station.U_uncertainty),
        artifact="processed-measured",
        x_name="y/delta",
        x_unit="1",
        y_name="U/Ue",
        y_unit="1",
    )


def stress_strain_series(test: Test) -> Series:
    """Engineering stress in MPa against engineering strain of a NIST
    Numisheet test, in the order of the rows (the strain goes up and down).

    Processed, as the card labels the file: the stress is the mean of two
    load cells over the original area, the strain a virtual extensometer of
    image correlation. The record gives no uncertainty per point.
    """
    return Series(
        x=test.strain,
        y=test.stress,
        artifact="processed-measured",
        x_name="engineering strain e",
        x_unit="mm/mm",
        y_name="engineering stress S",
        y_unit="MPa",
    )


def sdss_flux_series(spectrum: SdssSpectrum) -> Series:
    """The flux density of an SDSS spectrum in 1e-17 erg/cm^2/s/Angstrom
    against the vacuum, heliocentric wavelength in Angstrom, every pixel of
    the co-added spectrum as released.

    A calibrated observation: the SDSS pipeline calibrated the flux on
    standard stars and the wavelengths on arc lamps and sky lines, and
    converted them to vacuum and the heliocentric frame. The uncertainty is
    one standard deviation per pixel from the pipeline's inverse variance;
    the AND mask is not applied, so a selection of good pixels is a step the
    page states.
    """
    sigma = np.full(spectrum.ivar.shape, np.inf)
    positive = spectrum.ivar > 0
    sigma[positive] = 1.0 / np.sqrt(spectrum.ivar[positive])
    return Series(
        x=spectrum.wavelength,
        y=spectrum.flux,
        sigma=sigma,
        artifact="calibrated-observation",
        x_name="vacuum wavelength, heliocentric",
        x_unit="Angstrom",
        y_name="flux density",
        y_unit="1e-17 erg/cm^2/s/Angstrom",
    )


def light_curve_series(lc: LightCurve) -> Series:
    """The PDCSAP flux of a TESS light curve in e-/s against the barycentric
    time in days (BJD - 2457000), every cadence of the file as released.

    A calibrated observation: the SPOC pipeline calibrated the pixels,
    subtracted the background, and corrected the aperture photometry for
    systematics and crowding before the release. The uncertainty is the
    pipeline's PDCSAP_FLUX_ERR, one standard deviation per cadence. Missing
    values stay NaN and the quality flags are not applied: a figure of this
    series shows the file, and a selection of good cadences is a step the
    page states.
    """
    return Series(
        x=lc.time,
        y=lc.flux,
        sigma=lc.flux_err,
        artifact="calibrated-observation",
        x_name="time",
        x_unit="BJD - 2457000, d",
        y_name="PDCSAP flux",
        y_unit="e-/s",
    )


def boundary_layer_profile_series(profile: BoundaryLayerProfile) -> Series:
    """The mean streamwise velocity in m/s of a TU Delft boundary-layer
    profile (PIV or PTV) against the wall distance in m, every point of the
    file, PTV y converted from millimetres.

    Processed, as the card labels the files: profiles averaged by the
    creators from PIV or PTV fields. The record gives no uncertainty, so the
    series carries none.
    """
    return Series(
        x=profile.y,
        y=profile.U,
        artifact="processed-measured",
        x_name=f"wall distance y ({profile.technique})",
        x_unit="m",
        y_name="mean velocity U",
        y_unit="m/s",
    )


def luma_profile_series(profile: Profile) -> Series:
    """The luma (camera brightness, 0 to 255) along the scanline of one
    Lycopodium diffraction photograph against Tracker's coordinate x, whose
    unit the record does not state, every row of the sample.

    Processed, as the card labels the profile: extracted from a photograph
    by the creators with Tracker and averaged across the line. The record
    gives no uncertainty and no tone curve of the camera, so the series has
    no uncertainty, and the saturated centre stays in it.
    """
    return Series(
        x=profile.x,
        y=profile.luma,
        artifact="processed-measured",
        x_name="x along the scanline",
        x_unit="unit of the record, not stated",
        y_name="luma",
        y_unit="0-255, camera brightness",
    )


def pendulum_angle_series(run: Run) -> Series:
    """The angle in rad of a rotary-encoder record of the Xu damped
    pendulum against the time in s, every row of the raw file.

    Raw measured, as the card labels the angle: the encoder's counts in
    steps of 2 pi / 2000 rad, written by the PASCO software with 3
    decimals. The record gives no uncertainty; the encoder step is the
    resolution. A window of the record is a selection the page states.
    """
    return Series(
        x=run.time,
        y=run.angle,
        artifact="raw-measured",
        x_name="time",
        x_unit="s",
        y_name="angle",
        y_unit="rad",
    )


def soil_temperature_series(readings: Readings, column: int) -> Series:
    """The soil temperature in degC at one depth of a DWD station (``column``
    0 to 4: 5, 10, 20, 50, 100 cm) against the time in days since
    1970-01-01 00 h of the record's time stamp (MESS_DATUM, whose time zone
    the files do not state), every row of the sample.

    Processed, as the card labels the sample: the thermometer readings after
    DWD's automatic quality control, rows selected without changing a value.
    The record gives no sensor accuracy, so the series has no uncertainty;
    missing readings (-999 in the file) stay NaN.
    """
    hours = readings.time.astype("datetime64[h]").astype(np.int64)
    return Series(
        x=hours / 24.0,
        y=readings.temperature[:, column],
        artifact="processed-measured",
        x_name="time since 1970-01-01 00 h (MESS_DATUM)",
        x_unit="d",
        y_name="soil temperature",
        y_unit="degC",
    )


def track_series(tracks: Tracks, particle: int, axis: int) -> Series:
    """One coordinate (``axis`` 0 for x, 1 for y) of one track of the
    trackpy ``bulk_water`` video in pixels of the frame against the frame
    number, as the committed CSV holds them (no drift subtracted).

    Processed, as the card labels the tracks: the positions are this
    project's location of the spheres in the recorded frames (band-pass,
    local maxima, centroid, mass cut) and its linking of them, not the
    provider's. The record gives no localisation error, so the series has no
    uncertainty.
    """
    rows = tracks.particle == particle
    order = np.argsort(tracks.frame[rows], kind="stable")
    return Series(
        x=tracks.frame[rows][order].astype(float),
        y=tracks.xy[rows][order, axis],
        artifact="processed-measured",
        x_name="frame (24 per second)",
        x_unit="frame",
        y_name="xy"[axis],
        y_unit="px",
    )
