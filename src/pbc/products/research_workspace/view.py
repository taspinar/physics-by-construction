"""The static workspace view: one HTML file written from the project state.

No server, no socket, no JavaScript, no build step: the learner opens the
file in a browser. Decisions are made by commands (``select``, ``decide``,
``accept-finding``), each appended to the project's chains; the view is
written again after each. Every status is written as a word, never shown by
colour alone; every figure has alt text and its table beside it.
"""

import base64
import html
from pathlib import Path

import numpy as np

from pbc.data import SAMPLES_DIR
from pbc.data.reference import cobe_firas, reference_png
from pbc.products.research_workspace import firas, graph
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import report as rep

# The site's tokens (site/assets/site.css), so that the view reads as part
# of the course; only the ones the view uses.
_STYLE = """
:root {
  --text: #1c1b19; --background: #faf8f3; --muted: #57606a; --link: #0047ab;
  --rule: #857f73; --surface: #f1ede4; --plate: #ffffff; --focus: #0047ab;
  --warning: #7a4100; --warning-surface: #fbf0dc; --night: #0f2240;
  --night-text: #faf8f3; --night-muted: #b4c2d9;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--background); color: var(--text);
  font: 1rem/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { background: var(--night); color: var(--night-text);
  padding: 1.5rem 1rem 1.25rem; }
header .inner, main { max-width: 72rem; margin: 0 auto; }
header h1 { margin: 0 0 .5rem; font-size: 1.5rem; line-height: 1.25; font-weight: 650; }
header p { margin: .25rem 0; max-width: 70ch; }
header .banner { font-size: 1.1rem; font-weight: 600; }
header .scope { color: var(--night-muted); }
main { padding: 0 1rem 3rem; }
section { margin-top: 2.25rem; }
h2 { font-size: 1.2rem; margin: 0 0 .6rem; }
p, li { max-width: 72ch; }
.problems { background: var(--warning-surface); color: var(--warning);
  padding: .75rem 1rem; border: 1px solid var(--warning); }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums;
  background: var(--plate); }
caption { text-align: left; color: var(--muted); padding: 0 0 .4rem; }
th, td { text-align: left; vertical-align: top; padding: .4rem .6rem;
  border-bottom: 1px solid var(--rule); }
th { background: var(--surface); font-weight: 600; }
.scroll { overflow-x: auto; }
.status { font-weight: 600; white-space: nowrap; }
.status-failed, .status-not-reproduced, .status-open { text-decoration: underline;
  text-decoration-thickness: 2px; text-underline-offset: 3px; }
figure { margin: 0; }
figure img { max-width: 100%; height: auto; background: var(--plate);
  border: 1px solid var(--rule); }
figcaption { color: var(--muted); max-width: 72ch; margin-top: .4rem; }
a { color: var(--link); }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
footer { max-width: 72rem; margin: 0 auto; padding: 1rem; color: var(--muted);
  border-top: 1px solid var(--rule); }
@media (max-width: 40rem) { th, td { padding: .35rem .4rem; font-size: .92rem; } }
"""


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _status(word: str) -> str:
    css = word.replace(" ", "-")
    return f'<span class="status status-{_e(css)}">{_e(word)}</span>'


def _table(caption: str, head: list[str], rows: list[list[str]], *, raw=()) -> str:
    """A table; the cells of the column numbers in ``raw`` are HTML already."""
    out = [f'<div class="scroll"><table><caption>{_e(caption)}</caption><thead><tr>']
    out += [f'<th scope="col">{_e(h)}</th>' for h in head]
    out.append("</tr></thead><tbody>")
    for row in rows:
        cells = [c if n in raw else _e(c) for n, c in enumerate(row)]
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _figure() -> str:
    png = reference_png(cobe_firas, SAMPLES_DIR / cobe_firas.DATASET)
    data = base64.b64encode(png).decode("ascii")
    alt = (
        "Two panels against wavenumber in inverse centimetres. Top: the measured"
        " monopole intensity as dots rising to a peak near 5.5 and falling, with a"
        " dashed fitted blackbody through every dot. Bottom: the residuals with"
        " their error bars scattered about zero, the bars widening at the highest"
        " wavenumbers, and the fitted Galactic term as a dotted line close to zero."
    )
    return (
        f'<figure><img src="data:image/png;base64,{data}" alt="{_e(alt)}"'
        ' width="1200" height="1200">'
        "<figcaption>Processed: the CMB monopole of COBE FIRAS (Fixsen et al. 1996,"
        " Table 4, as LAMBDA distributes it) against a blackbody, with the"
        " residuals. The fit of dT and G is close to zero by construction: the"
        " residuals are the paper's own. Data: NASA COBE FIRAS / LAMBDA.</figcaption>"
        "</figure>"
    )


def _control_figure() -> str:
    """The positive control seed by seed (simulated), as a PNG in the page."""
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from pbc.data.plotting import COLOURS
    from pbc.data.reference.cobe_firas import read_spectrum

    spectrum = read_spectrum(SAMPLES_DIR / cobe_firas.DATASET)
    values = firas.pulls(spectrum)
    fig, ax = plt.subplots(figsize=(8, 3.6), constrained_layout=True)
    seeds = np.arange(len(values[firas.TEMPERATURE]))
    ax.axhspan(-2, 2, color="0.9", label="within two standard errors")
    ax.plot(
        seeds,
        values[firas.TEMPERATURE],
        "o",
        ms=3.5,
        color=COLOURS[0],
        label="dT: (recovered - injected) / its standard error",
    )
    ax.plot(
        seeds,
        values[firas.COMPTON],
        "^",
        ms=3.5,
        color=COLOURS[1],
        label="y: (recovered - injected) / its standard error",
    )
    ax.axhline(0, color="0.4", lw=0.6)
    ax.set_xlabel("seed")
    ax.set_ylabel("pull (dimensionless)")
    ax.set_title(
        "Positive control: 100 simulated spectra at the file's frequencies"
        " and uncertainties",
        fontsize=10,
    )
    ax.legend(fontsize=7, loc="upper right", ncol=1)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, metadata={"Software": None})
    plt.close(fig)
    data = base64.b64encode(buffer.getvalue()).decode("ascii")
    alt = (
        "A scatter of two series of pulls against the seed number from 0 to 99,"
        " circles for the temperature shift and triangles for y, scattered about"
        " zero inside a grey band from -2 to 2, with a few points outside it."
    )
    return (
        f'<figure><img src="data:image/png;base64,{data}" alt="{_e(alt)}"'
        ' width="880" height="396"><figcaption>Simulated: the fit recovers the'
        " injected dT and y; the table above counts the seeds within two standard"
        " errors.</figcaption></figure>"
    )


def render(data: dict, *, figure: bool = True) -> str:
    status = data["status"]
    log = data["log"]
    banner = rep.banner_lines(status)
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Research Workspace: COBE FIRAS reproduction</title>",
        f"<style>{_STYLE}</style></head><body>",
        "<header><div class='inner'>",
        "<h1>The COBE FIRAS spectrum fit, regenerated from the derived data</h1>",
        f"<p class='banner'>{_e(banner[0])}</p>",
        *[f"<p>{_e(line)}</p>" for line in banner[1:]],
        f"<p class='scope'>Scope: {_e(rep.SCOPE)}.</p>",
        "</div></header><main>",
    ]
    if data["problems"]:
        parts.append(
            "<section class='problems' aria-labelledby='problems'>"
            "<h2 id='problems'>The project does not verify</h2><ul>"
            + "".join(f"<li>{_e(p)}</li>" for p in data["problems"])
            + "</ul></section>"
        )
    plan = data["registration"]
    parts.append(
        "<section aria-labelledby='question'><h2 id='question'>The question</h2>"
    )
    parts.append(f"<p>{_e(plan.question)}</p>")
    parts.append(
        f"<p>Registration <code>{_e(plan.key)}</code>, digest"
        f" <code>{_e(data['run']['registration']['digest'][:16])}</code>:"
        " registered, <strong>not frozen</strong> (a plan on a feature branch is"
        " not frozen).</p>"
    )
    parts.append(
        _table(
            "Every question considered, with its decision; rejected and deferred"
            " ones are kept with what would warrant revisiting them.",
            ["Question", "Assessment", "Decision", "Reason", "Revisit when"],
            [
                [
                    e.idea.key,
                    "passes"
                    if data["assessments"][e.idea.key]["problems"] == []
                    else "; ".join(data["assessments"][e.idea.key]["problems"]),
                    e.decision,
                    e.reason,
                    e.revisit,
                ]
                for e in data["archive"]
            ],
        )
    )
    parts.append("</section>")

    decisions = {e.content["subject"]: e.content for e in log.of(worklog.DECISION)}
    rows = []
    for name in graph.BRANCH_ORDER:
        attempt = data["research"].ledger.attempt(f"{name}/fit")
        decision = decisions.get(name, {})
        if name in data["fits"]:
            f = data["fits"][name][0]
            values = ", ".join(
                f"{k} = {f.parameters[k]:.3g} +- {f.errors[k]:.2g}"
                for k in firas.PARAMETERS
                if k in f.parameters
            )
            fit_text = f"{f.chi2:.2f} / {f.dof}"
        else:
            values, fit_text = "; ".join(attempt.diagnostics), "none"
        rows.append(
            [
                name,
                _status(attempt.status),
                values,
                fit_text,
                decision.get("decision", ""),
                decision.get("reason", ""),
                decision.get("revisit", ""),
            ]
        )
    parts.append(
        "<section aria-labelledby='graph'><h2 id='graph'>The run graph</h2>"
        "<p>Every branch forks from b1 after the stage <code>load</code>; they run"
        " in sequence, the sequential baseline, with no tree search. A failed"
        " attempt stays in the ledger with its reason.</p>"
        + _table(
            "Branches of the stage fit: status, fitted parameters (statistical"
            " errors), chi-square for its degrees of freedom, and the decision of"
            " the declared criterion.",
            [
                "Branch",
                "Status",
                "Parameters",
                "chi2 / dof",
                "Decision",
                "Reason",
                "Revisit when",
            ],
            rows,
            raw=(1,),
        )
        + "</section>"
    )
    c = data["control"]
    parts.append(
        "<section aria-labelledby='control'><h2 id='control'>The positive control"
        " (simulated)</h2>"
        + _table(
            "Synthetic spectra at the file's frequencies and uncertainties.",
            [
                "Seeds",
                "dT recovered",
                "y recovered",
                "zero covered",
                "Required",
                "Result",
            ],
            [
                [
                    str(c.seeds),
                    str(c.recovered_t),
                    str(c.recovered_y),
                    str(c.zero_covered),
                    str(c.required),
                    _status("passed" if c.passed else "failed"),
                ]
            ],
            raw=(5,),
        )
        + (_control_figure() if figure else "")
        + "</section>"
    )
    parts.append(
        "<section aria-labelledby='sources'><h2 id='sources'>Source evidence</h2>"
        + _table(
            "Each published value with the words it rests on, from the register"
            " entry fixsen-1996-firas-spectrum, checked by a person.",
            ["Source", "Quantity", "Place", "Quoted words"],
            [[s.id, s.quantity, s.place, s.quote] for s in data["sources"]],
        )
        + "</section>"
    )
    row_cells = []
    for number, row in enumerate(data["rows"], start=1):
        check = "" if row.check is None else f"{row.check.name}: {row.check.note}"
        row_cells.append(
            [
                row.quantity,
                row.published,
                row.regenerated,
                _status(row.verdict),
                row.type or "",
                check,
                "; ".join(x for x in (row.note, row.missing) if x),
                _status(status.get(f"row-{number}", "")),
            ]
        )
    parts.append(
        "<section aria-labelledby='rows'><h2 id='rows'>The reproduction, row by"
        " row</h2>"
    )
    if figure:
        parts.append(_figure())
    parts.append(
        _table(
            "Published against regenerated, with the verdict, the type of a"
            " discrepancy and the check that supports it, and the claim's evidence"
            " status.",
            [
                "Quantity",
                "Published",
                "Regenerated",
                "Verdict",
                "Type",
                "Check",
                "Note",
                "Claim status",
            ],
            row_cells,
            raw=(3, 7),
        )
        + "</section>"
    )
    findings = [
        [
            key,
            e.content["kind"],
            e.content["reviewer"],
            _status(worklog.state(log, key)),
            e.content["text"],
        ]
        for key, e in log.findings().items()
    ]
    parts.append(
        "<section aria-labelledby='findings'><h2 id='findings'>Findings and"
        " decisions</h2><p>A finding that asks for evidence stays open after any"
        " revision of the prose; a finding an agent proposes is accepted only"
        " through a recomputed check.</p>"
        + _table(
            "Findings of the review.",
            ["Finding", "Kind", "By", "State", "Text"],
            findings,
            raw=(3,),
        )
        + _table(
            "Decisions, in the order they were made.",
            ["Subject", "Decision", "By", "Reason"],
            [
                [
                    e.content["subject"],
                    e.content["decision"],
                    e.content["by"],
                    e.content["reason"],
                ]
                for e in log.of(worklog.DECISION)
            ],
        )
        + "</section>"
    )
    claims = data["research"].ledger.claims
    parts.append(
        "<section aria-labelledby='claims'><h2 id='claims'>Claims and their"
        " evidence</h2>"
        + _table(
            "Every claim with its run links, its source links, and its status.",
            ["Claim", "Status", "Runs", "Sources", "Text"],
            [
                [
                    cl.id,
                    _status(status[cl.id]),
                    ", ".join(cl.runs),
                    ", ".join(cl.sources) or "none",
                    cl.text,
                ]
                for cl in claims
            ],
            raw=(1,),
        )
        + "</section>"
    )
    parts.append(
        "</main><footer>Data: NASA COBE FIRAS / LAMBDA (firas_monopole_spec_v1.txt);"
        " Fixsen et al. 1996, ApJ 473, 576. We acknowledge the use of the Legacy"
        " Archive for Microwave Background Data Analysis (LAMBDA), part of the High"
        " Energy Astrophysics Science Archive Center (HEASARC). HEASARC/LAMBDA is a"
        " service of the Astrophysics Science Division at the NASA Goddard Space"
        " Flight Center.</footer></body></html>\n"
    )
    return "".join(parts)


def write(data: dict, path: Path, *, figure: bool = True) -> None:
    Path(path).write_text(render(data, figure=figure), encoding="utf-8")
