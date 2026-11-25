"""The rows of the reproduction: the registered criteria applied to the fits
of the run graph, each a typed ``Discrepancy`` with its check.

The criteria are those the plan of Issue #619 declared before any fit
("What counts as reproduced"), copied into the project's registration. A
positive control that fails makes every row ``not evaluated``. The published
values come from the project's source evidence, never from a constant here.
"""

from collections.abc import Mapping, Sequence

import numpy as np

from pbc.products.research_workspace import discrepancy as d
from pbc.products.research_workspace import firas
from pbc.products.research_workspace.sources import Source

# The rule of the residual figure (declared in the registration): every
# regenerated residual within this many of its 1-sigma of the published one.
FIGURE_SIGMA = 1.0
# The rules of the bounds (the plan): reproduced at most 1.5 times the
# published bound; not reproduced above 3 times it.
BOUND_REPRODUCED = 1.5
BOUND_FAILED = 3.0
PAPER_REFERENCE_NOTE = (
    "the residuals of the file are those of the paper's own fit (the caption of"
    " its Fig. 5), so this criterion is met by construction: it confirms that"
    " the file and the fit are consistent, not an independent fit"
)


def _t_rows(
    fits: Mapping[str, Sequence[firas.Fit]], sources: Mapping[str, Source]
) -> list[d.Discrepancy]:
    b1 = fits["b1"][0]
    b4 = fits["b4"][0]
    sigma_t = b1.errors[firas.TEMPERATURE]
    dt = b1.parameters[firas.TEMPERATURE]
    rms = b1.rms_ppm()
    rms_source = sources["rms"]
    shape_met = abs(dt) <= 2 * sigma_t and rms < rms_source.value
    shape = d.Discrepancy(
        "the spectrum fit: dT against the file's reference",
        "the spectrum is a blackbody (the shape statement of the paper)",
        sources["shape"].register,
        f"dT = {dt * 1e6:.2f} +- {sigma_t * 1e6:.2f} microK (statistical) against"
        f" T_ref = {b1.t_ref:.3f} K; weighted rms {rms:.2f} ppm",
        d.REPRODUCED if shape_met else d.NOT_REPRODUCED,
        None if shape_met else d.UNEXPLAINED,
        note=PAPER_REFERENCE_NOTE,
    )
    shift = b4.temperature - b1.temperature
    follows = abs(shift) <= 2 * sigma_t
    t0 = sources["t0"]
    absolute = d.Discrepancy(
        "T0, the absolute temperature",
        f"{t0.value} +- {t0.uncertainty} {t0.unit} ({t0.confidence})",
        t0.register,
        f"T_fit = {b1.temperature:.6f} K, equal to the file's T_ref to first order",
        d.NOT_REPRODUCED,
        d.METHOD if follows else d.UNEXPLAINED,
        d.Check(
            "b4-follows-reference",
            "b4/fit",
            {
                "t_fit_b1": b1.temperature,
                "t_fit_b4": b4.temperature,
                "shift": shift,
                "sigma_t": sigma_t,
            },
            follows,
            "with the residuals taken against 2.728 K, the free dT moves T_fit"
            f" back to within {abs(shift) * 1e6:.1f} microK of the b1 value: the"
            " fitted temperature follows the reference, not the published T0",
        ),
        missing="the absolute calibration: the external calibrator and its"
        " thermometry (Fixsen et al. 1996, section 4, and section 6.1: 'determined"
        " by our choice of frequency and thermometry scales'), which the derived"
        " columns do not carry",
        note="an agreement of T_fit with 2.728 K within 0.004 K would not be a"
        " reproduction either",
    )
    stat = sources["t0_statistical"]
    uncertainty = d.Discrepancy(
        "the uncertainty of T0",
        f"+- {t0.uncertainty} {t0.unit} ({t0.confidence}), of which the"
        f" statistical part {stat.value:.5f} {stat.unit} (Table 2)",
        t0.register,
        f"sigma_T = {sigma_t * 1e6:.2f} microK, statistical only",
        d.NOT_REPRODUCED,
        d.UNCERTAINTY,
        d.Check(
            "statistical-beside-published",
            "b1/fit",
            {
                "sigma_t": sigma_t,
                "published_statistical": float(stat.value),
                "published": float(t0.uncertainty),
            },
            True,
            "the regenerated statistical uncertainty is reported beside the"
            " published one and never in its place",
        ),
        terms=(
            "the systematic thermometry uncertainty of 2 mK (1 sigma), section 6.1",
            "the systematic errors between the paper's three methods of setting"
            " T0, section 4",
        ),
    )
    rms_row = d.Discrepancy(
        "the weighted rms deviation from a blackbody",
        f"{rms_source.value:g} {rms_source.unit} of the peak brightness",
        rms_source.register,
        f"{rms:.2f} ppm of the peak of B_nu(T_fit), with the paper's weighted rms",
        d.REPRODUCED if rms < rms_source.value else d.NOT_REPRODUCED,
        None if rms < rms_source.value else d.UNEXPLAINED,
        note=PAPER_REFERENCE_NOTE,
    )
    return [shape, absolute, uncertainty, rms_row]


def figure_row(spectrum, fit: firas.Fit, source: Source) -> d.Discrepancy:
    """The residual figure compared by its numbers: every regenerated
    residual within ``FIGURE_SIGMA`` of its sigma of the published one."""
    templates = firas.shapes(spectrum, fit.t_ref)
    model = sum(value * templates[name] for name, value in fit.parameters.items())
    distance = float(np.max(np.abs(model) / spectrum.sigma))
    met = distance <= FIGURE_SIGMA
    return d.Discrepancy(
        "the residual figure",
        "the residuals of Fig. 5 and Table 4",
        source.register,
        f"the residuals after the b1 fit lie within {distance:.4f} sigma of"
        " Table 4 at every frequency",
        d.REPRODUCED if met else d.NOT_REPRODUCED,
        None if met else d.UNEXPLAINED,
        note=PAPER_REFERENCE_NOTE,
    )


def _bound_row(
    name: str, branch: str, fit: firas.Fit, source: Source, scale: float, unit: str
) -> d.Discrepancy:
    value, error = fit.parameters[name], fit.errors[name]
    bound = fit.bound(name)
    published = float(source.value)
    consistent = abs(value) <= firas.Z95 * error
    regenerated = (
        f"{name} = {value / scale:.2f} +- {error / scale:.2f} x {unit}"
        f" (statistical); 95 % bound {bound / scale:.2f} x {unit}, statistical only"
    )
    head = f"|{name}| (95 %)"
    published_text = f"< {published / scale:g} x {unit} ({source.confidence})"
    if consistent and bound <= BOUND_REPRODUCED * published:
        note = ""
        if bound < published:
            note = (
                "the regenerated bound is statistical only and lies below the"
                " published one, which holds systematic terms: it is not a"
                " better limit"
            )
        return d.Discrepancy(
            head,
            published_text,
            source.register,
            regenerated,
            d.REPRODUCED,
            note=note,
        )
    if not consistent or bound > BOUND_FAILED * published:
        return d.Discrepancy(
            head,
            published_text,
            source.register,
            regenerated,
            d.NOT_REPRODUCED,
            d.UNEXPLAINED,
        )
    return d.Discrepancy(
        head,
        published_text,
        source.register,
        regenerated,
        d.NOT_REPRODUCED,
        d.UNCERTAINTY,
        d.Check(
            "statistical-beside-published",
            f"{branch}/fit",
            {"bound": bound, "published": published},
            True,
            "the central value is consistent with zero; the bound differs",
        ),
        terms=("the systematic uncertainty of the Galactic model, Table 2",),
    )


def rows(
    spectrum,
    fits: Mapping[str, Sequence[firas.Fit]],
    control: firas.Control,
    sources: Mapping[str, Source],
) -> list[d.Discrepancy]:
    """Every row of the reproduction, in the registration's order."""
    if not control.passed:
        return [
            d.Discrepancy(
                quantity,
                "see the source",
                sources[key].register,
                "not computed: the positive control failed",
                d.NOT_EVALUATED,
            )
            for quantity, key in (
                ("the spectrum fit", "shape"),
                ("T0, the absolute temperature", "t0"),
                ("the uncertainty of T0", "t0"),
                ("the weighted rms deviation from a blackbody", "rms"),
                ("the residual figure", "figure"),
                ("|y| (95 %)", "y"),
                ("|mu| (95 %)", "mu"),
            )
        ]
    out = _t_rows(fits, sources)
    out.append(figure_row(spectrum, fits["b1"][0], sources["figure"]))
    out.append(
        _bound_row(firas.COMPTON, "b2", fits["b2"][0], sources["y"], 1e-6, "1e-6")
    )
    out.append(
        _bound_row(firas.CHEMICAL, "b3", fits["b3"][0], sources["mu"], 1e-5, "1e-5")
    )
    d.validate(out)
    return out
