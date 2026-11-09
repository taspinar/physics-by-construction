"""Particle tracking in video microscopy with NumPy and SciPy alone.

The project's own processing of the dataset ``trackpy-bulk-water`` (its card
and dossier disclose it as such): the images are measurements, the positions
and the tracks are computed here. The steps follow Crocker and Grier (J.
Colloid Interface Sci. 179, 298, 1996), the method that trackpy implements,
in their simplest form; trackpy itself is not used.

1. ``bandpass``: a Gaussian blur of width ``smoothing`` (removes the pixel
   noise) minus the mean over a square of side ``2 radius + 1`` (removes the
   background that varies across the field), negative values set to zero.
2. ``locate``: the local maxima of the band-passed image over a disk of
   ``radius``, at least ``radius`` pixels from the border; each refined to
   the intensity-weighted centroid over that disk, whose sum is the
   ``mass``; the features below ``minmass`` are dropped.
3. ``link``: between consecutive frames, a feature continues a track when
   each of the two features is the other's nearest neighbour and they are at
   most ``search_range`` pixels apart; every other feature starts a track.
   There is no memory: a track that loses its particle for a frame ends.
4. ``drift``: the mean displacement of all features linked from one frame to
   the next, summed over the frames, is the motion of the whole sample (the
   flow of the fluid or the stage) and is subtracted from the positions.
5. ``msd_sums``: the ensemble mean squared displacement at each lag, kept as
   the sum and the count of each track so that a bootstrap over tracks can
   resample them.

Pixel coordinates: x is the column and y the row of the image, both from the
centre of the top-left pixel, y downwards.
"""

from itertools import pairwise

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree


def disk(radius: int) -> np.ndarray:
    """The boolean disk of ``radius`` pixels on a square of side 2 radius + 1."""
    yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    return xx**2 + yy**2 <= radius**2


def bandpass(image: np.ndarray, radius: int, smoothing: float = 1.0) -> np.ndarray:
    """Gaussian blur minus the local mean, negative values set to zero."""
    image = np.asarray(image, dtype=float)
    blurred = ndimage.gaussian_filter(image, smoothing)
    background = ndimage.uniform_filter(image, 2 * radius + 1)
    return np.clip(blurred - background, 0.0, None)


def locate(
    image: np.ndarray,
    radius: int,
    minmass: float,
    *,
    smoothing: float = 1.0,
    invert: bool = False,
) -> np.ndarray:
    """The features of one image as rows (x, y, mass), in the row-major order
    of their peaks. ``invert`` finds dark particles on a bright background;
    negating the image is exact for that, since the band-pass removes any
    constant."""
    image = np.asarray(image, dtype=float)
    filtered = bandpass(-image if invert else image, radius, smoothing)
    footprint = disk(radius)
    peaks = (filtered == ndimage.grey_dilation(filtered, footprint=footprint)) & (
        filtered > 0
    )
    rows, cols = filtered.shape
    peaks[:radius, :] = peaks[rows - radius :, :] = False
    peaks[:, :radius] = peaks[:, cols - radius :] = False
    yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    found = []
    for y, x in np.argwhere(peaks):
        window = filtered[y - radius : y + radius + 1, x - radius : x + radius + 1]
        weights = window * footprint
        mass = weights.sum()
        if mass >= minmass:
            found.append(
                (
                    x + (weights * xx).sum() / mass,
                    y + (weights * yy).sum() / mass,
                    mass,
                )
            )
    return np.array(found, dtype=float).reshape(-1, 3)


def link(positions: list[np.ndarray], search_range: float) -> list[np.ndarray]:
    """Track numbers for the features of each frame (rows x, y, ...).

    Mutual nearest neighbours within ``search_range`` continue a track; the
    other features start new ones, numbered in order of appearance."""
    tracks = [np.arange(len(positions[0]))]
    following = len(positions[0])
    for before, after in pairwise(positions):
        new = np.full(len(after), -1)
        if len(before) and len(after):
            _, forward = cKDTree(after[:, :2]).query(
                before[:, :2], distance_upper_bound=search_range
            )
            _, backward = cKDTree(before[:, :2]).query(
                after[:, :2], distance_upper_bound=search_range
            )
            for j, i in enumerate(backward):
                if i < len(before) and forward[i] == j:
                    new[j] = tracks[-1][i]
        fresh = new < 0
        new[fresh] = np.arange(following, following + fresh.sum())
        following += int(fresh.sum())
        tracks.append(new)
    return tracks


def _sorted(frame: np.ndarray, track: np.ndarray) -> np.ndarray:
    order = np.lexsort((frame, track))
    frame, track = frame[order], track[order]
    same = track[1:] == track[:-1]
    if np.any(same & (frame[1:] != frame[:-1] + 1)):
        raise ValueError("a track skips a frame or repeats one")
    return order


def drift(frame: np.ndarray, track: np.ndarray, xy: np.ndarray) -> np.ndarray:
    """Position of the whole sample per frame [px], zero in frame 0: the sum of
    the mean displacements of the features linked between consecutive frames.
    Frames are numbered 0 to the largest ``frame``."""
    order = _sorted(frame, track)
    f, t, p = frame[order], track[order], xy[order]
    linked = t[1:] == t[:-1]
    steps = (p[1:] - p[:-1])[linked]
    into = f[1:][linked]
    count = np.bincount(into, minlength=f.max() + 1)
    if np.any(count[1:] == 0):
        raise ValueError("a frame with no feature linked from the frame before")
    mean = np.column_stack(
        [np.bincount(into, weights=steps[:, k], minlength=f.max() + 1) for k in (0, 1)]
    )
    mean[1:] /= count[1:, None]
    mean[0] = 0.0
    return np.cumsum(mean, axis=0)


def msd_sums(
    frame: np.ndarray, track: np.ndarray, xy: np.ndarray, lags: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per track: the sum of the squared displacements [px^2] and their count
    at each lag (shape tracks x lags), over every pair of frames of the
    track, and the track numbers of the rows."""
    order = _sorted(frame, track)
    t, p = track[order], xy[order]
    numbers, index = np.unique(t, return_inverse=True)
    sums = np.zeros((len(numbers), len(lags)))
    counts = np.zeros((len(numbers), len(lags)))
    for k, lag in enumerate(lags):
        same = t[lag:] == t[:-lag]
        squared = ((p[lag:] - p[:-lag]) ** 2).sum(axis=1)[same]
        owner = index[lag:][same]
        sums[:, k] = np.bincount(owner, weights=squared, minlength=len(numbers))
        counts[:, k] = np.bincount(owner, minlength=len(numbers))
    return sums, counts, numbers
