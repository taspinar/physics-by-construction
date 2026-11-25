"""The assessment and selection of a data question before any run, and the
archive of every question with its decision.

A question is feasible when every dataset it names has a card with a ``go``
whose rights permit the use; falsifiable when its registered rule has at
least two outcomes that a result can reach; within budget when the stages it
needs fit the budget. The selection follows a rule declared before the
assessment and never reads a proposer's self-rating. Every decision goes to
the archive of ``pbc.research.ideas`` with its reason and what would warrant
revisiting it; a question that cannot be written as a specification of the
throw laboratory is an ``Idea`` with ``draft=None``, as that module allows.
"""

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pbc.data.card import load_card
from pbc.research.ideas import DEFERRED, REJECTED, SELECTED, Archive, Idea

DECISIONS = (SELECTED, DEFERRED, REJECTED)


@dataclass(frozen=True)
class Question:
    key: str
    question: str
    proposer: str
    datasets: tuple[str, ...]
    outcomes: tuple[str, ...]
    stages: tuple[str, ...]
    self_ratings: Mapping[str, int]
    decision: str
    reason: str
    revisit: str


@dataclass(frozen=True)
class Assessment:
    key: str
    feasible: bool
    falsifiable: bool
    within_budget: bool
    problems: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.feasible and self.falsifiable and self.within_budget


def load(path: Path) -> tuple[int, tuple[Question, ...]]:
    """The stage budget and the questions of a project's ``questions.toml``."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    questions = tuple(
        Question(
            key=key,
            question=q["question"],
            proposer=q["proposer"],
            datasets=tuple(q.get("datasets", ())),
            outcomes=tuple(q.get("outcomes", ())),
            stages=tuple(q.get("stages", ())),
            self_ratings=dict(q.get("self_ratings", {})),
            decision=q["decision"],
            reason=q["reason"],
            revisit=q["revisit"],
        )
        for key, q in data["question"].items()
    )
    return int(data["budget"]["stages"]), questions


def assess(question: Question, cards: Mapping[str, Mapping], budget: int) -> Assessment:
    """Assess ``question`` against the cards and the budget; reads no rating."""
    found = []
    for name in question.datasets:
        card = cards.get(name)
        if card is None:
            found.append(f"no card for the dataset {name}")
            continue
        if (card.get("decision") or {}).get("value") != "go":
            found.append(f"{name} has no go")
        rights = card.get("rights") or {}
        for answer in ("local_download", "publication_of_figures"):
            if (rights.get(answer) or {}).get("answer") != "permitted":
                found.append(f"{name}: {answer} is not permitted")
    if not question.datasets:
        found.append("the question names no dataset")
    feasible = not found
    falsifiable = len(set(question.outcomes)) >= 2
    if not falsifiable:
        found.append("fewer than two reachable outcomes")
    within = 0 < len(question.stages) <= budget
    if not within:
        found.append(f"{len(question.stages)} stages, the budget is {budget}")
    return Assessment(question.key, feasible, falsifiable, within, tuple(found))


def cards_of(names: Iterable[str], registry: Path) -> dict[str, Mapping]:
    out = {}
    for name in names:
        path = Path(registry) / f"{name}.yaml"
        if path.is_file():
            out[name] = load_card(path)
    return out


def selection_problems(
    questions: Iterable[Question], assessments: Mapping[str, Assessment]
) -> list[str]:
    """The declared rule: a question is selected only when every check of
    its assessment passed; a decision is one of ``DECISIONS`` with a reason."""
    found = []
    for q in questions:
        if q.decision not in DECISIONS:
            found.append(f"{q.key}: unknown decision {q.decision!r}")
        if not q.reason.strip():
            found.append(f"{q.key}: a decision needs its reason")
        if q.decision == SELECTED and not assessments[q.key].passed:
            found.append(
                f"{q.key} is selected but fails its assessment: "
                + "; ".join(assessments[q.key].problems)
            )
    return found


def archive(questions: Iterable[Question]) -> Archive:
    """Every question with its decision, in order, in the archive of
    ``pbc.research.ideas``."""
    out = Archive()
    for q in questions:
        out.add(
            Idea(q.key, q.question, q.proposer, None, dict(q.self_ratings)),
            q.decision,
            q.reason,
            q.revisit,
        )
    return out
