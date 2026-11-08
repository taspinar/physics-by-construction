"""Munich event-ready Bell test: the CHSH correlators of the run of 15 April 2016.

Status of the figure: *processed* (the experimenters' pairs file: the valid
atom-atom events of both labs, matched by time, after the attempts during
maintenance were excluded). The ideal correlators of a maximally entangled
state, +-1/sqrt(2), are drawn apart as a dotted reference line, not as data.

The record gives no uncertainty; every event is one +-1 product of two
outcomes, so a correlator over n events has the binomial standard error
sqrt((1 - E^2) / n), and S, a sum of four independent correlators, the
quadrature sum (Rosenfeld et al., PRL 119, 010402 (2017), Fig. 3).

The published result uses the stopping rule fixed before the run: the first
5000 events of each heralded state (``published_selection``). With it, this
module reproduces the paper's correlators and S values to the digits printed;
the archive holds 10,201 events, and the whole archive is evaluated beside it.

Conventions (Supplemental Material, Sec. III, Eq. S1 and S2): setting 0 of
lab 1 is alpha (0 deg), 1 is alpha' (90 deg); setting 0 of lab 2 is beta
(-45 deg), 1 is beta' (+45 deg). The correlator counts equal outcomes as +1
and unequal ones as -1. S = sum over (a, b) of g(a, b) E(a, b), where g is -1
except at (alpha', beta) for Psi- and at (alpha', beta') for Psi+. The
mapping of the file's 0 and 1 to these angles is established by reproducing
the published correlators, not stated in the archive.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.plotting import COLOURS, add_credit, label_status

PAIRS = "Bell_2016-04-15_9_pairs.csv"
LAB_1 = "Bell_2016-04-15_9_lab_1.csv"
LAB_2 = "Bell_2016-04-15_9_lab_2.csv"
README = "Readme.txt"
PAIRS_FIELDS = (
    "timestamp lab 1 (unix time ms)",
    "Bell-state",
    "setting lab 1",
    "result lab 1",
    "setting lab 2",
    "result lab 2",
    "line in lab 1 file",
    "line in lab 2 file",
)
LAB_1_FIELDS = (
    "time (Unix time in ms)",
    "setting",
    "result",
    " local timestamp",
    "Bell-state",
    "excluded from evaluation",
    " comment",
)
# The header of lab 2 ends with a delimiter: an empty eighth name.
LAB_2_FIELDS = (
    "time (Unix time in ms)",
    "setting",
    "result",
    "local timestamp",
    "excluded from evaluation",
    "comment",
    "",
)
STATES = ("Psi-", "Psi+")
SETTINGS = ((0, 0), (0, 1), (1, 0), (1, 1))
ANGLES = {0: (0, -45), 1: (0, 45), 2: (90, -45), 3: (90, 45)}  # deg, (a, b)
# The one setting pair with g = +1, per state (Eq. S1).
POSITIVE = {"Psi-": (1, 0), "Psi+": (1, 1)}
EVENTS_PER_STATE = 5000  # the stopping rule fixed before the run (PRL)
PAIRING_WINDOW_MS = 100  # the archive's Readme: clock jitter of the two PCs
LHV_BOUND = 2.0
TSIRELSON = 2 * np.sqrt(2)


@dataclass(frozen=True)
class Pairs:
    time_ms: np.ndarray  # Unix time of lab 1 [ms]
    state: np.ndarray  # "Psi-" or "Psi+", the heralded state
    a: np.ndarray  # setting of lab 1, 0 or 1
    x: np.ndarray  # result of lab 1, 0 or 1
    b: np.ndarray  # setting of lab 2, 0 or 1
    y: np.ndarray  # result of lab 2, 0 or 1
    line_1: np.ndarray  # row in the lab 1 file, from 0 after the header
    line_2: np.ndarray  # row in the lab 2 file

    def __len__(self) -> int:
        return self.time_ms.size


@dataclass(frozen=True)
class Lab:
    time_ms: np.ndarray  # Unix time of the lab's PC [ms]
    setting: np.ndarray
    result: np.ndarray
    local_timestamp: np.ndarray  # the high-precision counter of the lab
    excluded: np.ndarray  # bool
    comment: np.ndarray  # str, the reason of an exclusion
    state: np.ndarray | None  # lab 1 only


@dataclass(frozen=True)
class Run:
    pairs: Pairs
    lab_1: Lab
    lab_2: Lab


def _rows(path: Path, delimiter: str, fields: tuple[str, ...]) -> list[list[str]]:
    with Path(path).open(newline="", encoding="ascii") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    if tuple(rows[0]) != fields:
        raise ValueError(f"{path}: header {rows[0]!r} is not {fields!r}")
    return rows[1:]


def _columns(path: Path, rows: list[list[str]], width: int) -> list[list[str]]:
    if any(len(row) != width for row in rows):
        raise ValueError(f"{path}: a row without {width} fields")
    return [[row[k] for row in rows] for k in range(width)]


def _binary(values: list[str], path: Path, name: str) -> np.ndarray:
    out = np.array([int(v) for v in values])
    if not np.isin(out, (0, 1)).all():
        raise ValueError(f"{path}: {name} is not 0 or 1")
    return out


def read_pairs(path: Path) -> Pairs:
    """Read the tab-separated pairs file of the Munich archive."""
    rows = _rows(path, "\t", PAIRS_FIELDS)
    columns = _columns(path, rows, len(PAIRS_FIELDS))
    state = np.array(columns[1])
    if not np.isin(state, STATES).all():
        raise ValueError(f"{path}: a Bell state other than {STATES}")
    return Pairs(
        time_ms=np.array([int(v) for v in columns[0]]),
        state=state,
        a=_binary(columns[2], path, "setting lab 1"),
        x=_binary(columns[3], path, "result lab 1"),
        b=_binary(columns[4], path, "setting lab 2"),
        y=_binary(columns[5], path, "result lab 2"),
        line_1=np.array([int(v) for v in columns[6]]),
        line_2=np.array([int(v) for v in columns[7]]),
    )


def read_lab(path: Path, lab: int) -> Lab:
    """Read the semicolon-separated attempts file of lab 1 or lab 2."""
    rows = _rows(path, ";", LAB_1_FIELDS if lab == 1 else LAB_2_FIELDS)
    # Every row of lab 1 has 7 fields; those of lab 2 have 6 (no trailing
    # delimiter), one less than its header.
    columns = _columns(path, rows, 7 if lab == 1 else 6)
    excluded_col = 5 if lab == 1 else 4
    excluded = np.array([v.strip() for v in columns[excluded_col]])
    if not np.isin(excluded, ("yes", "no")).all():
        raise ValueError(f"{path}: 'excluded from evaluation' is not yes or no")
    return Lab(
        time_ms=np.array([int(v) for v in columns[0]]),
        setting=_binary(columns[1], path, "setting"),
        result=_binary(columns[2], path, "result"),
        local_timestamp=np.array([int(v) for v in columns[3]]),
        excluded=excluded == "yes",
        comment=np.array([v.strip() for v in columns[excluded_col + 1]]),
        state=np.array(columns[4]) if lab == 1 else None,
    )


def load(data_dir: Path) -> Run:
    data_dir = Path(data_dir)
    return Run(
        read_pairs(data_dir / PAIRS),
        read_lab(data_dir / LAB_1, 1),
        read_lab(data_dir / LAB_2, 2),
    )


def pairing_problems(run: Run) -> list[str]:
    """Where the pairs file disagrees with the two lab files it points into."""
    p, one, two = run.pairs, run.lab_1, run.lab_2
    out = []
    checks = {
        "time lab 1": p.time_ms != one.time_ms[p.line_1],
        "state": p.state != one.state[p.line_1],
        "setting lab 1": p.a != one.setting[p.line_1],
        "result lab 1": p.x != one.result[p.line_1],
        "setting lab 2": p.b != two.setting[p.line_2],
        "result lab 2": p.y != two.result[p.line_2],
        "excluded": one.excluded[p.line_1] | two.excluded[p.line_2],
        "time window": np.abs(p.time_ms - two.time_ms[p.line_2]) > PAIRING_WINDOW_MS,
    }
    for name, bad in checks.items():
        if bad.any():
            out.append(f"{name}: {int(bad.sum())} pairs")
    return out


def excluded_pairs(run: Run) -> Pairs:
    """The heralded attempts of lab 1 that the experimenters excluded, paired
    with the nearest attempt of lab 2 within the pairing window (by the
    archive's rule); those without a partner in the window are left out.
    Kept apart from the pairs file, for a sensitivity check of the exclusion."""
    one, two = run.lab_1, run.lab_2
    rows_1, rows_2 = [], []
    for i in np.flatnonzero(one.excluded):
        gap = np.abs(two.time_ms - one.time_ms[i])
        j = int(gap.argmin())
        if gap[j] <= PAIRING_WINDOW_MS:
            rows_1.append(i)
            rows_2.append(j)
    i, j = np.array(rows_1, int), np.array(rows_2, int)
    return Pairs(
        one.time_ms[i], one.state[i], one.setting[i], one.result[i],
        two.setting[j], two.result[j], i, j,
    )  # fmt: skip


def combine(*parts: Pairs) -> Pairs:
    """The events of several ``Pairs`` together."""
    return Pairs(
        *(
            np.concatenate([getattr(p, f) for p in parts])
            for f in Pairs.__dataclass_fields__
        )
    )


def products(pairs: Pairs) -> np.ndarray:
    """The +-1 product of the two outcomes: +1 for equal results."""
    return np.where(pairs.x == pairs.y, 1, -1)


def published_selection(pairs: Pairs) -> np.ndarray:
    """The first ``EVENTS_PER_STATE`` events of each state, in time order."""
    keep = np.zeros(len(pairs), bool)
    order = np.argsort(pairs.time_ms, kind="stable")
    for state in STATES:
        keep[order[pairs.state[order] == state][:EVENTS_PER_STATE]] = True
    return keep


@dataclass(frozen=True)
class Correlator:
    value: float
    stderr: float
    n: int


def correlators(pairs: Pairs, state: str, mask=None) -> dict[tuple, Correlator]:
    """E(a, b) of one state, with its binomial standard error."""
    keep = (pairs.state == state) & (True if mask is None else mask)
    c = products(pairs)
    out = {}
    for a, b in SETTINGS:
        k = keep & (pairs.a == a) & (pairs.b == b)
        n = int(k.sum())
        e = float(c[k].mean())
        out[(a, b)] = Correlator(e, float(np.sqrt((1 - e**2) / n)), n)
    return out


def sign(state: str, a: int, b: int) -> int:
    """g(a, b) of Eq. S1: -1 except at the one pair ``POSITIVE[state]``."""
    return 1 if (a, b) == POSITIVE[state] else -1


def chsh(pairs: Pairs, state: str, mask=None) -> tuple[float, float]:
    """S of one state and its standard error (quadrature of the four)."""
    terms = correlators(pairs, state, mask)
    s = sum(sign(state, *k) * e.value for k, e in terms.items())
    return float(s), float(np.sqrt(sum(e.stderr**2 for e in terms.values())))


def chsh_pooled(pairs: Pairs, mask=None) -> tuple[float, float]:
    """S of both states together: each product multiplied by g of its state
    and setting, then the four correlators over the events of both states."""
    keep = np.ones(len(pairs), bool) if mask is None else mask
    g = np.array(
        [sign(s, a, b) for s, a, b in zip(pairs.state, pairs.a, pairs.b, strict=True)]
    )
    c = g * products(pairs)
    s = var = 0.0
    for a, b in SETTINGS:
        k = keep & (pairs.a == a) & (pairs.b == b)
        e = c[k].mean()
        s += e
        var += (1 - e**2) / k.sum()
    return float(s), float(np.sqrt(var))


def running_chsh(pairs: Pairs, state: str) -> tuple[np.ndarray, np.ndarray]:
    """S and its standard error after each event of ``state``, in time order,
    from the 40th event on (ten per setting pair, on average)."""
    idx = np.flatnonzero(pairs.state == state)
    idx = idx[np.argsort(pairs.time_ms[idx], kind="stable")]
    c = products(pairs)[idx]
    a, b = pairs.a[idx], pairs.b[idx]
    s = np.zeros(idx.size)
    var = np.zeros(idx.size)
    for sa, sb in SETTINGS:
        k = (a == sa) & (b == sb)
        n = np.cumsum(k)
        total = np.cumsum(np.where(k, c, 0))
        with np.errstate(invalid="ignore", divide="ignore"):
            e = total / n
            s += sign(state, sa, sb) * e
            var += (1 - e**2) / n
    start = 39
    return s[start:], np.sqrt(var[start:])


def significance(s: float, stderr: float) -> float:
    """Distance of S above the local-realist bound 2, in standard errors."""
    return (s - LHV_BOUND) / stderr


def make_figure(data_dir: Path) -> plt.Figure:
    run = load(data_dir)
    pairs = run.pairs
    published = published_selection(pairs)
    fig, (ax_corr, ax_run) = plt.subplots(
        1, 2, figsize=(11, 4.8), constrained_layout=True
    )
    marker = {"Psi-": "o", "Psi+": "s"}
    line = {"Psi-": "-", "Psi+": "--"}

    positions = np.arange(4)
    for k, state in enumerate(STATES):
        terms = correlators(pairs, state, published)
        values = [terms[s].value for s in SETTINGS]
        errors = [terms[s].stderr for s in SETTINGS]
        s, err = chsh(pairs, state, published)
        ax_corr.errorbar(
            positions + (k - 0.5) * 0.18,
            values,
            yerr=errors,
            color=COLOURS[k],
            marker=marker[state],
            ls="none",
            capsize=3,
            label=f"{state}: S = {s:.3f} +- {err:.3f} (5000 events)",
        )
    ideal = 1 / np.sqrt(2)
    for v in (ideal, -ideal):
        ax_corr.axhline(
            v,
            color="0.5",
            lw=0.9,
            ls=":",
            label="ideal state: +-1/sqrt(2)" if v > 0 else None,
        )
    ax_corr.axhline(0, color="0.7", lw=0.6)
    ax_corr.set_xticks(positions, [f"({a}, {b:+d})" for a, b in ANGLES.values()])
    ax_corr.set_ylim(-1, 1)
    ax_corr.set_xlabel("settings (alpha, beta) of lab 1 and lab 2 [deg]")
    ax_corr.set_ylabel("correlator E(a, b) [dimensionless]")
    ax_corr.set_title(
        "Processed: correlators, first 5000 events per state (+-1 s.e.)", fontsize=10
    )
    ax_corr.legend(fontsize=8, loc="center left")

    for k, state in enumerate(STATES):
        s, err = running_chsh(pairs, state)
        n = np.arange(40, 40 + s.size)
        ax_run.plot(n, s, color=COLOURS[k], ls=line[state], lw=1.2, label=f"{state}: S")
        ax_run.fill_between(n, s - err, s + err, color=COLOURS[k], alpha=0.2, lw=0)
    ax_run.axhline(LHV_BOUND, color="0.2", lw=1.0, label="local-realist bound S = 2")
    ax_run.axhline(
        TSIRELSON, color="0.5", lw=0.9, ls=":", label="quantum maximum 2 sqrt(2)"
    )
    ax_run.axvline(
        EVENTS_PER_STATE,
        color="0.4",
        lw=0.8,
        ls="-.",
        label="stopping rule: 5000 events per state",
    )
    pooled, pooled_err = chsh_pooled(pairs, published)
    ax_run.set_ylim(1.0, 3.3)
    ax_run.set_xlabel("events of the state, in time order [count]")
    ax_run.set_ylabel("S after n events [dimensionless]")
    ax_run.set_title(
        f"Processed: running S; pooled at the stop S = {pooled:.3f} "
        f"+- {pooled_err:.3f}",
        fontsize=10,
    )
    ax_run.legend(fontsize=8, loc="lower right", ncol=2)
    add_credit(
        fig,
        "Data: Rosenfeld, Burchardt, Garthoff, Redeker, Ortegel, Rau, Weinfurter "
        "(LMU Munich), 'Experimental data and archived website material for "
        "Event-Ready Bell Test Using Entangled Atoms Simultaneously Closing Detection "
        "and Locality Loopholes', Zenodo 10.5281/zenodo.22936124, CC BY 4.0; file "
        "Bell_2016-04-15_9_pairs.csv of Bell_2016-04-15.zip, unmodified. Selection, "
        "correlators, errors and S: this figure's code "
        "(pbc.data.reference.munich_bell). Bands and bars: one binomial standard "
        "error. Per the paper, the experiment closes the detection and locality "
        "loopholes; the independence of the settings from the hidden variables is "
        "assumed, not tested.",
    )
    label_status(fig, "processed")
    return fig
