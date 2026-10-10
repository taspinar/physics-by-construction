"""Minimal reader for two-port Touchstone (``.s2p``) files in RI, MA, or DB format."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

_FREQUENCY_UNITS = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}


@dataclass(frozen=True)
class Network:
    """Two-port S-parameters: ``s[k, i, j]`` is S(i+1)(j+1) at ``frequency[k]``."""

    frequency: np.ndarray  # Hz
    s: np.ndarray  # complex, shape (n, 2, 2)
    reference_impedance: float  # ohm
    comments: tuple[str, ...]


def _to_complex(a: np.ndarray, b: np.ndarray, form: str) -> np.ndarray:
    if form == "RI":
        return a + 1j * b
    angle = np.deg2rad(b)
    magnitude = 10 ** (a / 20) if form == "DB" else a
    return magnitude * np.exp(1j * angle)


def read_touchstone(path: Path) -> Network:
    """Read a two-port S-parameter file; other parameters and port counts fail."""
    comments: list[str] = []
    option: list[str] | None = None
    rows: list[list[float]] = []
    for raw in Path(path).read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("!"):
            comments.append(line[1:].strip())
        elif line.startswith("#"):
            option = line[1:].upper().split()
        else:
            rows.append([float(x) for x in line.split("!")[0].split()])
    if option is None:
        raise ValueError(f"{path}: no option line")
    # Option line: <unit> <parameter> <format> R <impedance>
    unit, parameter, form = option[0], option[1], option[2]
    if (
        parameter != "S"
        or form not in {"RI", "MA", "DB"}
        or unit not in (_FREQUENCY_UNITS)
    ):
        raise ValueError(f"{path}: unsupported option line {option}")
    impedance = float(option[option.index("R") + 1]) if "R" in option else 50.0
    data = np.array(rows)
    if data.ndim != 2 or data.shape[1] != 9:
        raise ValueError(f"{path}: expected 9 columns for a two-port file")
    pairs = [_to_complex(data[:, k], data[:, k + 1], form) for k in (1, 3, 5, 7)]
    # Two-port files list S11, S21, S12, S22 (the one order that is not row-major).
    s = np.stack([[pairs[0], pairs[2]], [pairs[1], pairs[3]]]).transpose(2, 0, 1)
    return Network(
        frequency=data[:, 0] * _FREQUENCY_UNITS[unit],
        s=s,
        reference_impedance=impedance,
        comments=tuple(comments),
    )
