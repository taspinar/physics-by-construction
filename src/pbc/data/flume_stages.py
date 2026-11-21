"""The flume analysis of the lesson "Automated analysis pipelines" as the
stages of a resumable pipeline (F153, lesson RR4; ``pbc.evidence.resumable``).

Four stages: ``load`` names the record and its time span, ``window`` cuts
the window from each of the five repetitions and takes its RMS elevation
and period, ``estimate`` takes the mean of the repetitions with its
standard error, and ``report`` writes the first lines of the published
report of the measured problem. The branches of the lesson keep the record
and change the window. Two claims are evaluated from the state files: the
main branch reproduces the committed report, and the negative one, that the
RMS elevation does not depend on the end of the window.

Elevations are in m in the states and in mm in the report, times in s.
"""

import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from pbc.data import flume_analysis
from pbc.data.flume import read_elevation
from pbc.data.pipeline import EXPECTED_DIR, Report, estimate
from pbc.evidence.records import (
    Claim,
    Evaluation,
    RunRecord,
    digest_files,
    digest_value,
)
from pbc.evidence.resumable import Research, Stage

EVALUATOR = "pbc.data.flume_stages evaluation, version 1"
EXPECTATION = EXPECTED_DIR / "flume-waves.txt"
MAIN = {"data": flume_analysis.EXPERIMENT, "window": list(flume_analysis.WINDOW)}
# The alternative branches of the lesson, each forked from the main branch
# after ``load``: the end of the window it changes to (s).
ALTERNATIVES = {"end-10": 10.0, "end-12": 12.0, "end-40": 40.0}
# The negative claim: the RMS elevation of an alternative branch lies within
# this many standard errors of the main branch's.
WITHIN = 2.0
REPORT_LINES = 7  # the title and the six quantities of the window


def _record(configuration: Mapping[str, Any]) -> Mapping[str, Path]:
    return {"record": flume_analysis.DATA_DIR / configuration["data"]}


def load(previous: Mapping[str, Any], configuration: Mapping[str, Any]):
    """The record's file and the span of its time axis (s)."""
    record = read_elevation(flume_analysis.DATA_DIR / configuration["data"])
    return {
        "file": configuration["data"],
        "span": [float(record.time[0]), float(record.time[-1])],
    }


def window(previous: Mapping[str, Any], configuration: Mapping[str, Any]):
    """RMS elevation (m) and period (s) of each repetition inside the
    window; a window that is not inside the record is refused."""
    start, end = configuration["window"]
    first, last = previous["span"]
    if not first <= start < end <= last:
        raise ValueError(
            f"the window {start:g} to {end:g} s is not inside the record,"
            f" {first:g} to {last:g} s"
        )
    record = read_elevation(flume_analysis.DATA_DIR / configuration["data"])
    rms, period = flume_analysis.repetition_results(record, (start, end))
    return {"window": [start, end], "rms": rms, "period": period}


def estimate_stage(previous: Mapping[str, Any], configuration: Mapping[str, Any]):
    """The mean of the repetitions with its standard error, and the period
    resolution of the window (s)."""
    rms, period = estimate(previous["rms"]), estimate(previous["period"])
    return {
        "window": previous["window"],
        "rms": {"mean": rms.mean, "sigma": rms.sigma, "n": rms.n},
        "period": {"mean": period.mean, "sigma": period.sigma},
        "resolution": flume_analysis.period_resolution(
            period.mean, tuple(previous["window"])
        ),
    }


def report(previous: Mapping[str, Any], configuration: Mapping[str, Any]):
    """The lines of the report of the window, as the published report
    shows them."""
    start, end = previous["window"]
    rms = previous["rms"]
    title = (
        f"Waves over a submerged bar, gauge {flume_analysis.GAUGE}, wave condition 1"
    )
    shown = (
        Report(title)
        .add("window", start, "s", decimals=1)
        .add("window end", end, "s", decimals=1)
        .add("repetitions", rms["n"], decimals=0)
        .add(
            "RMS elevation, mean of repetitions",
            rms["mean"] * 1e3,
            "mm",
            sigma=rms["sigma"] * 1e3,
            decimals=2,
        )
        .add(
            "wave period, mean of repetitions",
            previous["period"]["mean"],
            "s",
            decimals=2,
        )
        .add("period resolution of the window", previous["resolution"], "s", decimals=2)
    )
    return {"lines": shown.render().splitlines()}


STAGES = (
    Stage("load", ("data",), load, _record),
    Stage("window", ("data", "window"), window, _record),
    Stage("estimate", (), estimate_stage),
    Stage("report", (), report),
)

# The code the states are written with, relative to ``src``.
SOURCES = (
    "pbc/data/flume.py",
    "pbc/data/flume_analysis.py",
    "pbc/data/flume_stages.py",
    "pbc/data/pipeline.py",
    "pbc/evidence/resumable.py",
)


def code_identity() -> str:
    src = Path(__file__).parents[2]
    return digest_files([src / name for name in SOURCES], src)


def run_record(code: str | None = None) -> RunRecord:
    """The task of the investigation; ``code`` replaces the digest of the
    code (a test, or the lesson's exercise of other code)."""
    return RunRecord(
        task="The RMS elevation and period of the waves at gauge 5 of wave"
        " condition 1, from five aligned repetitions, and how they depend on"
        " the window of the analysis.",
        hypothesis="The RMS elevation does not depend on the end of the window"
        f" within {WITHIN:g} standard errors of the main branch.",
        assumptions=(
            "The repetitions are independent.",
            "The start of the window is fixed; only its end is a choice.",
            "A state is valid when it is the one recorded, with the current"
            " code, configuration, and data.",
        ),
        protocol_version="1",
        split={"data": "the committed sample; nothing is held out"},
        seeds=(),
        budgets={},
        code=code if code is not None else code_identity(),
        configuration=digest_value(MAIN),
        environment={"python": platform.python_version(), "numpy": np.__version__},
    )


def investigation(root: Path, code: str | None = None) -> Research:
    """The stages and the record, with the main branch started, not run."""
    research = Research(STAGES, run_record(code), root)
    research.start("main", MAIN)
    return research


def branch_out(research: Research) -> None:
    """Fork every alternative from the main branch after ``load`` and run it."""
    for name, end in ALTERNATIVES.items():
        start = research.branches["main"].configuration["window"][0]
        research.fork("main", name, "load", {"window": [start, end]})
        research.run(name)


def _evaluation(research: Research, attempt: str, correct: bool, metrics) -> Evaluation:
    depends = tuple(
        a
        for i in research.lineage(attempt)
        for a in research.ledger.attempt(i).artifacts
    )
    return Evaluation(
        attempt=attempt,
        evaluator=EVALUATOR,
        correct=correct,
        metrics=metrics,
        resources={"stages": len(research.lineage(attempt))},
        depends_on=depends,
        code=research.code,
        configuration=research.record.configuration,
    )


def evaluate(research: Research) -> None:
    """Evaluate both claims from the state files and record them."""
    lines = research.state("main/report").output["lines"]
    expected = EXPECTATION.read_text(encoding="utf-8").splitlines()[:REPORT_LINES]
    same = sum(a == b for a, b in zip(lines, expected, strict=False))
    research.ledger.add_evaluation(
        _evaluation(
            research, "main/report", lines == expected, {"lines that agree": same}
        )
    )
    research.ledger.add_claim(
        Claim(
            "reproduces-the-report",
            "The main branch, stopped and resumed, reproduces the published"
            " report of the window.",
            "the first seven lines of reports/expected/flume-waves.txt",
            {"main/report": True},
            ("reports/expected/flume-waves.txt", "flume-report"),
        )
    )
    runs = {}
    for name, shift in shifts(research).items():
        attempt = f"{name}/estimate"
        research.ledger.add_evaluation(
            _evaluation(
                research,
                attempt,
                abs(shift) <= WITHIN,
                {"shift in standard errors": shift},
            )
        )
        runs[attempt] = True
    research.ledger.add_claim(
        Claim(
            "window-does-not-matter",
            "The RMS elevation does not depend on the end of the window, within"
            f" {WITHIN:g} standard errors of the main branch.",
            "gauge 5 of wave condition 1, window ends of 10, 12, and 14 s",
            runs,
            ("fig-branch-shifts",),
        )
    )


def shifts(research: Research) -> dict[str, float]:
    """The RMS elevation of each completed alternative branch minus the main
    branch's, in standard errors of the main branch, from the state files."""
    main = research.state("main/estimate").output["rms"]
    found = {}
    for name in ALTERNATIVES:
        attempt = f"{name}/estimate"
        if research.ledger.attempt(attempt) is not None:
            rms = research.state(attempt).output["rms"]
            found[name] = (rms["mean"] - main["mean"]) / main["sigma"]
    return found
