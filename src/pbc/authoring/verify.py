"""The worked examples of "How we verify the science" (F134, ADR 021
decision 5).

Each example is data: a claim type, a published lesson, and one word of the
claim's evidence, which must be a cell, a dataset card, or a Lean theorem.
The page shows the claim as the lesson states it, with its scope and every
piece of its evidence, linked to its place in the lesson, to its evidence,
and to its row of the Evidence map. The examples are resolved with the code
of the Evidence map (``pbc.authoring.evidence``), so they cannot differ from
it, and a target that is missing (no such lesson, no claim of that type
naming the word, a word that names nothing or names another kind) raises,
which fails the build, as a claim without evidence does.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.evidence import (
    EVIDENCE_PAGE,
    Claim,
    Evidence,
    Source,
    lean_theorems,
    markdown_text,
    read_claims,
)
from pbc.authoring.path import LearningPath, Lesson
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.authoring.website import page_href, project_root

VERIFY_PAGE = "verify.qmd"

# What each kind of evidence is called on the page.
_KINDS = {
    "cell": "cell",
    "reference": "reference",
    "card": "dataset card",
    "theorem": "Lean theorem",
    "replay": "recorded run",
}
_HEADINGS = {
    "cell": "A numerically verified claim and its cell",
    "card": "A claim from measured data and its dataset card",
    "theorem": "A formal theorem and its Lean module",
}
_TYPE_NAMES = {
    "observational": "Observational",
    "experimentally-supported": "Experimentally supported",
    "numerically-verified": "Numerically verified",
    "formal-theorem": "Formal theorem",
}


@dataclass(frozen=True)
class Example:
    """A claim the page works through: its type, its lesson, and the word of
    its evidence that the example is about, with the kind that word must
    name."""

    type: str
    lesson: str  # lesson id
    evidence: str
    kind: str  # "cell", "card", or "theorem"


EXAMPLES = (
    Example(
        "numerically-verified", "harmonic-oscillator", "euler-energy-ratios", "cell"
    ),
    Example(
        "experimentally-supported", "wave-flume-lab", "aalborg-submerged-bar", "card"
    ),
    Example(
        "formal-theorem",
        "proving-what-the-simulation-showed",
        "euler_energy_step",
        "theorem",
    ),
)


@dataclass(frozen=True)
class WorkedExample:
    example: Example
    lesson: Lesson
    claim: Claim
    sources: tuple[Source, ...]  # every word of the claim's evidence


def resolve(
    example: Example, path: LearningPath, evidence: Evidence, site: Path
) -> WorkedExample:
    """The claim and the evidence ``example`` names. Raises ``ValueError``
    when any part of it is missing."""
    about = f"the example {example.lesson}/{example.evidence}"
    try:
        lesson = path.lesson(example.lesson)
    except LookupError:
        raise ValueError(f"{about}: no published lesson has that id") from None
    claims = [
        claim
        for claim in read_claims(
            lesson.page, (site / lesson.page).read_text(encoding="utf-8")
        )
        if claim.type == example.type and example.evidence in claim.evidence
    ]
    if not claims:
        raise ValueError(
            f"{about}: the lesson has no {example.type} claim whose evidence"
            f" names {example.evidence!r}"
        )
    claim = claims[0]
    sources = []
    for word in claim.evidence:
        source = evidence.resolve(claim.page, word)
        if source is None:
            raise ValueError(f"{about}: the evidence {word!r} names nothing")
        sources.append(source)
    named = next(source for source in sources if source.name == example.evidence)
    if named.kind != example.kind:
        raise ValueError(
            f"{about}: {example.evidence!r} is a {named.kind}, not a {example.kind}"
        )
    return WorkedExample(example, lesson, claim, tuple(sources))


def _card_line(root: Path, name: str, href: str) -> str:
    data = yaml.safe_load(
        (root / "data" / "registry" / f"{name}.yaml").read_text(encoding="utf-8")
    )
    source = data.get("source", {})
    licence = data.get("rights", {}).get("licence", "")
    return (
        f"The dataset card [`{name}`]({href}) names the data: *{data['title']}*,"
        f" by {source.get('creator', 'its creators')}, published under"
        f" {licence}, with the address it was taken from and what the licence"
        " permits."
    )


def _theorem_block(root: Path, name: str) -> str:
    """The statement of the Lean theorem ``name``: its lines from
    ``theorem`` to the ``:=`` that starts the proof."""
    file, line = lean_theorems(root)[name]
    lines = (root / file).read_text(encoding="utf-8").splitlines()
    statement = []
    for text in lines[line - 1 :]:
        head, separator, _ = text.partition(":=")
        statement.append(head.rstrip() if separator else text)
        if separator:
            break
    return "\n".join(["```lean", *statement, "```"])


@dataclass(frozen=True)
class VerifyPage:
    examples: tuple[WorkedExample, ...]
    root: Path
    page: str = VERIFY_PAGE

    def example(self, worked: WorkedExample) -> str:
        claim, lesson = worked.claim, worked.lesson
        kind = worked.example.kind
        links = [
            f"[the claim in *{lesson.title}*]"
            f"({page_href(self.page, lesson.page, claim.anchor)})",
            *(
                f"the {_KINDS[source.kind]} [`{source.name}`]({source.href})"
                for source in worked.sources
            ),
            f"[its row in the Evidence map]"
            f"({page_href(self.page, EVIDENCE_PAGE, claim.row)})",
        ]
        named = next(s for s in worked.sources if s.name == worked.example.evidence)
        lines = [
            f"### {_HEADINGS[kind]} {{#example-{kind}}}",
            "",
            f"::: {{.verify-example data-lesson-id={lesson.id}}}",
            "",
            f'[{_TYPE_NAMES[claim.type]}]{{.claim data-type="{claim.type}"}}',
            "",
            f"> {claim.statement}",
            "",
            f"Scope: {markdown_text(claim.scope) or 'not stated'}.",
            "",
        ]
        if kind == "cell":
            lines += [
                f"The cell [`{named.name}`]({named.href}) of the lesson"
                " shows the computation behind the claim. The build runs it again"
                " every time the site is built, and the page shows what it"
                " computed; if it fails, the lesson cannot be published.",
                "",
            ]
        elif kind == "card":
            lines += [_card_line(self.root, named.name, named.href), ""]
        else:
            lines += [
                f"The theorem [`{named.name}`]({named.href}) states it in Lean;"
                " Lean checks the proof whenever the proofs are built, and a"
                " lesson whose proof does not compile cannot be published:",
                "",
                _theorem_block(self.root, named.name),
                "",
            ]
        lines += [
            "Follow " + ", ".join(links[:-1]) + f", and {links[-1]}.",
            "",
            ":::",
            "",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return "\n".join(self.example(worked) for worked in self.examples)


def verify_page(
    examples: tuple[Example, ...] = EXAMPLES,
    root: Path = REPOSITORY_ROOT,
    site: Path | None = None,
) -> VerifyPage:
    """Return the worked examples of the page being built. It raises when an
    example's target is missing, which fails the build."""
    site = site or project_root(Path.cwd().resolve())
    path = LearningPath.read(site)
    evidence = Evidence(root, VERIFY_PAGE, site)
    return VerifyPage(
        tuple(resolve(example, path, evidence, site) for example in examples), root
    )
