"""The run graph of the reproduction track over ``pbc.evidence.resumable``,
and the guided branch comparison.

Two stages: ``load`` reads the committed sample (its digest is recorded, so a
changed file stops every resume), ``fit`` runs the fits of a branch. The
branch ``b1`` runs both stages; every other branch forks from it after
``load`` and changes only the keys of ``fit``. A branch whose stage raises
``ValueError`` is a failed attempt that stays in the ledger with its reason
(``b6`` fits y and mu together, which the paper rules out). The branches run
in sequence, the sequential baseline; no tree search is used, because six
branches of a linear fit are enumerated in well under a second and a search
over template subsets would cost more without asking a question the branches
leave open.
"""

import json
import platform
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from pbc.data import REPO_ROOT
from pbc.data.reference import cobe_firas
from pbc.data.reference.cobe_firas import Spectrum, read_spectrum
from pbc.evidence.records import RunRecord, digest_bytes, digest_value
from pbc.evidence.resumable import Branch, Research, Stage
from pbc.products.research_workspace import firas

SAMPLE = "data/samples/cobe-firas-monopole/firas_monopole_spec_v1.txt"
LOAD = "load"
FIT = "fit"
FIRST = "b1"
# The failed attempt the graph keeps: y and mu together.
FAILED_BRANCH = "b6"
BRANCH_ORDER = ("b1", "b0", "b2", "b3", "b4", "b5", FAILED_BRANCH)


def branch_configurations() -> dict[str, dict[str, Any]]:
    """The configuration of every branch: the sample and the keys of ``fit``."""
    out = {
        name: {"sample": SAMPLE, **configuration}
        for name, configuration in firas.BRANCHES.items()
    }
    out[FAILED_BRANCH] = {
        "sample": SAMPLE,
        "fits": [[firas.TEMPERATURE, firas.GALAXY, firas.COMPTON, firas.CHEMICAL]],
        "reference": None,
        "below": None,
    }
    return out


def _sample_files(configuration: Mapping[str, Any]) -> Mapping[str, Path]:
    return {"sample": REPO_ROOT / configuration["sample"]}


def _load(previous: Mapping, configuration: Mapping) -> Mapping:
    spectrum = read_spectrum(REPO_ROOT / configuration["sample"])
    return {
        "wavenumber": spectrum.wavenumber.tolist(),
        "residual": spectrum.residual.tolist(),
        "sigma": spectrum.sigma.tolist(),
        "galaxy": spectrum.galaxy.tolist(),
        "monopole": spectrum.monopole.tolist(),
        "t_ref": spectrum.t_ref,
        "header": list(spectrum.header),
    }


def spectrum_of(output: Mapping) -> Spectrum:
    """The spectrum a ``load`` state holds."""
    return Spectrum(
        np.asarray(output["wavenumber"], dtype=float),
        np.asarray(output["monopole"], dtype=float),
        np.asarray(output["residual"], dtype=float),
        np.asarray(output["sigma"], dtype=float),
        np.asarray(output["galaxy"], dtype=float),
        tuple(output["header"]),
        float(output["t_ref"]),
    )


def _fit(previous: Mapping, configuration: Mapping) -> Mapping:
    fits = firas.run_branch(spectrum_of(previous), configuration)
    return {"fits": [f.as_dict() for f in fits]}


STAGES = (
    Stage(LOAD, ("sample",), _load, _sample_files),
    Stage(FIT, ("fits", "reference", "below"), _fit),
)

ASSUMPTIONS = (
    "The residual, uncertainty, and Galaxy columns are Table 4 of Fixsen et al."
    " 1996 as LAMBDA distributes it, and column 2 is a 2.725 K blackbody plus the"
    " residual (the card's reference temperature).",
    "The uncertainties are independent between frequencies (the diagonal of the"
    " paper's covariance only).",
    "The residual is linear in dT, G, y, and mu near the reference temperature"
    " (the paper's Eq. 3).",
    "The fitted uncertainties are statistical only: the systematic terms of the"
    " paper (the thermometry, the Galactic model) are not in the file.",
)


# The modules of this package that decide what a project records as its
# outcome or apply one of its rules, beside the stages: the rows and their
# rule constants (reproduction), the type rules (discrepancy), the claims
# and their status (report), the reviewer's checks (review), the checks of
# the registration, the sources, and the questions, the decision log, and
# the run with its evaluator (project). ``outcome_code_digest`` covers them
# with the stage code; a module that records nothing is in ``NOT_OUTCOME``,
# and a test requires every module of the package in one of the two.
OUTCOME_MODULES = (
    "reproduction.py",
    "discrepancy.py",
    "report.py",
    "review.py",
    "registration.py",
    "sources.py",
    "questions.py",
    "log.py",
    "project.py",
)
# The static view, the agent reviewer (its findings enter only when a
# recomputed check of ``review`` confirms them), the command line, and the
# package's docstring.
NOT_OUTCOME = ("view.py", "agent.py", "__main__.py", "__init__.py")
PACKAGE = Path(__file__).parent


def _stage_files() -> tuple[Path, ...]:
    return (Path(firas.__file__), Path(cobe_firas.__file__), Path(__file__))


def _digest_files(files) -> str:
    return digest_value([digest_bytes(Path(p).read_bytes()) for p in files])


def code_digest() -> str:
    """The digest of the code the stages run; a state written by other
    stage code is not resumed."""
    return _digest_files(_stage_files())


def outcome_code_digest() -> str:
    """The digest of every module that computes an outcome of the project
    or applies one of its rules: the stage code and ``OUTCOME_MODULES``.
    ``project.verify`` compares it with the run's, so a changed rule (a
    threshold of ``reproduction``, say) is named, never silently applied
    to rows decided by the old one."""
    return _digest_files(
        (*_stage_files(), *(PACKAGE / name for name in OUTCOME_MODULES))
    )


def outcome_file_digests() -> dict[str, str]:
    """The digest of each file of ``outcome_code_digest``, by its name, so
    ``project.verify`` names the file that changed and no other."""
    files = (*_stage_files(), *(PACKAGE / name for name in OUTCOME_MODULES))
    return {Path(p).name: digest_bytes(Path(p).read_bytes()) for p in files}


def run_record(registration_digest: str) -> RunRecord:
    return RunRecord(
        task="Regenerate the published spectrum fit of Fixsen et al. (1996) from the"
        " LAMBDA monopole file: the shape against a blackbody, the weighted rms,"
        " and the bounds on y and mu; not the absolute temperature calibration",
        hypothesis="The derived data reproduce the published spectrum fit",
        assumptions=ASSUMPTIONS,
        protocol_version="F155 part 1",
        split={
            "probed": "the 43 frequencies of the committed sample",
            "held out": "none: a reproduction of a published fit on its own data",
        },
        seeds=(0,),
        budgets={"stages": len(STAGES), "branches": len(BRANCH_ORDER)},
        code=code_digest(),
        configuration=registration_digest,
        environment={"python": platform.python_version(), "numpy": np.__version__},
    )


def new_research(root: Path, registration_digest: str) -> Research:
    return Research(STAGES, run_record(registration_digest), Path(root))


def run_all(research: Research) -> None:
    """Run ``b1``, then fork and run every other branch after ``load``, in
    sequence (the sequential baseline)."""
    configurations = branch_configurations()
    research.start(FIRST, configurations[FIRST])
    research.run(FIRST)
    for name in BRANCH_ORDER[1:]:
        changes = {k: v for k, v in configurations[name].items() if k != "sample"}
        research.fork(FIRST, name, LOAD, changes)
        research.run(name)


def fits_of(research: Research) -> dict[str, list[firas.Fit]]:
    """The fits of every branch whose ``fit`` stage completed."""
    out = {}
    for name in research.branches:
        attempt = research.ledger.attempt(f"{name}/{FIT}")
        if attempt is not None and attempt.status == "completed":
            output = research.state(attempt.id).output
            out[name] = [firas.Fit.from_dict(f) for f in output["fits"]]
    return out


def save_branches(research: Research, path: Path) -> None:
    data = {name: asdict(branch) for name, branch in research.branches.items()}
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def load_branches(path: Path) -> dict[str, Branch]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {name: Branch(**branch) for name, branch in data.items()}
