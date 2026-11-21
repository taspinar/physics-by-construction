"""A report whose every number and citation can be checked, and the bundle
of records it rests on (lesson RR7).

A report is a list of ``Sentence``s as its author wrote them, numbers
typed. The numbers written in a sentence name, in their order, the field
of a record each comes from (``numbers``), every citation ``[@key]`` names the role the
cited passage plays for a claim (``citations``, with ``claim``), and a
sentence that no record supports is ``marked``: it is shown as proposed,
not evaluated. ``check_report`` finds every number and every citation in
the text and resolves each, or names its problem:

- a number resolves when the record's field, written with as many decimals
  as the sentence writes, gives the same text (``resolve_number``);
- a citation resolves when the passage is in the corpus (its quotation
  checked against its page) and the label the rule of
  ``pbc.research.literature`` computes for the claim is the role the
  sentence gives it (``resolve_citation``).

A number with no record, a record named for no number, a record or a
field that does not exist, an unknown passage, a role the passage does
not play, and a number, a citation, or a record in a marked sentence are
problems. A number written with fewer decimals than its field
is compared at those decimals, so a rounding passes and a transposition
does not. Numbers written as words are not found: the check reads digits.

The records form a ``Bundle``: each record's fields with the digests of
its output, of the configuration that produced it, and of the code that
computed it. ``reproduce`` computes every record again from its recipe and
compares, so a record that no longer comes out of its code and
configuration is found, and so is code that changed since the record was
written. A digest establishes identity, not truth.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pbc.evidence.records import digest_bytes, digest_value
from pbc.evidence.report import MARKED
from pbc.research.corpus import Passage, Statement
from pbc.research.literature import label

CITATION = re.compile(r"\[@([a-z0-9-]+)\]")
# A number as written: digits, with a decimal part or not, not inside a word.
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")

RECORD = "record"
PASSAGE = "passage"
REFUSED = "refused"
MARKED_REFUSALS = {
    "number": "a marked sentence writes no number",
    "citation": "a marked sentence cites no passage",
}


@dataclass(frozen=True)
class Quantity:
    """Where a number of a sentence comes from: a field of a record."""

    record: str
    field: str


@dataclass(frozen=True)
class Sentence:
    """A sentence of a report as written, with the source of every number
    and the role of every citation in it. ``claim`` is the key of the claim
    the citations are judged for; ``marked`` says that no record supports
    the sentence."""

    key: str
    text: str
    numbers: tuple[Quantity, ...] = ()
    citations: Mapping[str, str] = field(default_factory=dict)
    claim: str | None = None
    marked: bool = False


@dataclass(frozen=True)
class Resolution:
    """One number or citation of a sentence, in the order of the text, and
    what it resolved to: a record field, a passage, or a refusal with its
    reason."""

    sentence: str
    token: str
    kind: str
    to: str


def resolve_number(
    written: str, quantity: Quantity | None, records: Mapping[str, Mapping[str, Any]]
) -> tuple[str, str]:
    """The number ``written`` against its ``quantity``: (``RECORD``, the
    field) when the field gives the same text at the decimals written,
    else (``REFUSED``, the reason)."""
    if quantity is None:
        return REFUSED, "a number with no record"
    fields = records.get(quantity.record)
    if fields is None or quantity.field not in fields:
        return REFUSED, f"no record field {quantity.record}.{quantity.field}"
    value = fields[quantity.field]
    decimals = len(written.partition(".")[2])
    shown = format(value, f".{decimals}f")
    if shown != written:
        return REFUSED, f"the record gives {shown}"
    return RECORD, f"{quantity.record}.{quantity.field}"


def resolve_citation(
    key: str,
    role: str | None,
    claim: Statement | None,
    passages: Mapping[str, Passage],
) -> tuple[str, str]:
    """The citation of the passage ``key`` in the ``role`` it is given for
    ``claim``: (``PASSAGE``, the key and its label) when the corpus holds
    the passage and the rule labels it so, else (``REFUSED``, the reason)."""
    passage = passages.get(key)
    if passage is None:
        return REFUSED, "the corpus holds no passage with this key"
    if role is None or claim is None:
        return REFUSED, "the citation names no role for a claim"
    computed, reason = label(claim, passage.reading)
    if computed != role:
        return REFUSED, f"the rule labels the passage {computed}: {reason}"
    return PASSAGE, f"{key}, {role}"


def check_report(
    sentences: Sequence[Sentence],
    records: Mapping[str, Mapping[str, Any]],
    passages: Sequence[Passage],
    claims: Sequence[Statement],
) -> list[Resolution]:
    """Every number and citation of the report, in order, resolved or
    refused; a marked sentence is listed once as marked, and every number,
    citation, or record in it is refused."""
    by_key = {p.key: p for p in passages}
    statements = {s.key: s for s in claims}
    found = []
    for sentence in sentences:
        cited = list(CITATION.finditer(sentence.text))
        tokens = sorted(
            [(m.start(), "citation", m.group(1)) for m in cited]
            + [
                (m.start(), "number", m.group(0))
                for m in NUMBER.finditer(sentence.text)
                if not any(c.start() <= m.start() < c.end() for c in cited)
            ]
        )
        if sentence.marked:
            # A marked sentence rests on no record: a number or a citation
            # in it would dress an interpretation as a result.
            found.extend(
                Resolution(sentence.key, token, REFUSED, MARKED_REFUSALS[kind])
                for _, kind, token in tokens
            )
            found.extend(
                Resolution(
                    sentence.key,
                    "",
                    REFUSED,
                    f"{q.record}.{q.field}: a marked sentence rests on no record",
                )
                for q in sentence.numbers
            )
            found.append(Resolution(sentence.key, "", MARKED, ""))
            continue
        sources = iter(sentence.numbers)
        for _, kind, token in tokens:
            if kind == "number":
                status, to = resolve_number(token, next(sources, None), records)
            else:
                status, to = resolve_citation(
                    token,
                    sentence.citations.get(token),
                    statements.get(sentence.claim or ""),
                    by_key,
                )
            found.append(Resolution(sentence.key, token, status, to))
        for left in sources:
            found.append(
                Resolution(
                    sentence.key,
                    "",
                    REFUSED,
                    f"{left.record}.{left.field} is named for no number",
                )
            )
    return found


def problems(resolutions: Sequence[Resolution]) -> list[Resolution]:
    """The resolutions that were refused."""
    return [r for r in resolutions if r.kind == REFUSED]


@dataclass(frozen=True)
class Recipe:
    """How a record is made: the function that computes its fields, the
    configuration it is given, and the source files of the code it runs."""

    compute: Callable[[], Mapping[str, Any]]
    configuration: Any
    code: tuple[Path, ...]


@dataclass(frozen=True)
class Entry:
    """A record of the bundle: its fields and the digests of its output,
    its configuration, and its code."""

    name: str
    fields: Mapping[str, Any]
    output: str
    configuration: str
    code: str


def code_identity(recipe: Recipe, edited: Mapping[Path, bytes] | None = None) -> str:
    """The digest of the source files of ``recipe``, in their order;
    ``edited`` replaces the bytes of the files it names, as if they had been
    changed."""
    edited = edited or {}
    parts = [
        digest_bytes(edited[path] if path in edited else path.read_bytes())
        for path in recipe.code
    ]
    return digest_value(parts)


def bundle(recipes: Mapping[str, Recipe]) -> dict[str, Entry]:
    """Compute every record of ``recipes`` and write its entry."""
    entries = {}
    for name, recipe in recipes.items():
        fields = dict(recipe.compute())
        entries[name] = Entry(
            name,
            fields,
            digest_value(fields),
            digest_value(recipe.configuration),
            code_identity(recipe),
        )
    return entries


REPRODUCED = "reproduced"
CODE_CHANGED = "the code changed since the record"
CONFIGURATION_CHANGED = "the configuration changed since the record"
DIFFERS = "computed again, the record differs"


def reproduce(
    entries: Mapping[str, Entry],
    recipes: Mapping[str, Recipe],
    edited: Mapping[Path, bytes] | None = None,
) -> dict[str, str]:
    """Each record's status when it is computed again: the code and the
    configuration are compared first, then the output."""
    found = {}
    for name, entry in entries.items():
        recipe = recipes[name]
        if code_identity(recipe, edited) != entry.code:
            found[name] = CODE_CHANGED
        elif digest_value(recipe.configuration) != entry.configuration:
            found[name] = CONFIGURATION_CHANGED
        elif digest_value(dict(recipe.compute())) != entry.output:
            found[name] = DIFFERS
        else:
            found[name] = REPRODUCED
    return found
