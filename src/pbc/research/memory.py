"""A research memory: what an investigation leaves for the next one, and the
check of a reuse (lesson RR7).

An ``Item`` is one thing kept: an idea, code, data, a result, a limitation,
or an open question (``KINDS``), with where it comes from and its
``identity``, the digests that say what exactly was kept (the code, the
configuration a result was computed for, the record of the data, the entry
of an archive). A result names the limitations and open questions that go
with it (``links``); an idea and an open question name what would warrant
taking them up again (``revisit``).

``Memory.store`` keeps an item once, and refuses a result whose links name
no stored limitation. ``recall`` hands an item over for reuse only when
every identity it was stored with is the identity the reuse presents, and
returns a result together with its limitations and open questions, so that
a reuse cannot drop them. A mismatch refuses the reuse and names each
difference: the thing kept is not the thing the reuse would need, and it is
computed again instead.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

IDEA = "idea"
CODE = "code"
DATA = "data"
RESULT = "result"
LIMITATION = "limitation"
QUESTION = "open question"
KINDS = (IDEA, CODE, DATA, RESULT, LIMITATION, QUESTION)


class ReuseRefused(ValueError):
    """A store or a reuse that the memory refuses, with every reason."""

    def __init__(self, reasons: list[str]):
        self.reasons = tuple(reasons)
        super().__init__("; ".join(reasons))


@dataclass(frozen=True)
class Item:
    """One thing kept: its key, kind, text, where it comes from, the
    digests that identify it, the keys of the items that go with it, and
    what would warrant taking it up again."""

    key: str
    kind: str
    text: str
    source: str
    identity: Mapping[str, str]
    links: tuple[str, ...] = ()
    revisit: str = ""


@dataclass(frozen=True)
class Recalled:
    """An item handed over for reuse, with the items that go with it."""

    item: Item
    attached: tuple[Item, ...]


@dataclass
class Memory:
    """The items of one or more investigations, by key."""

    items: dict[str, Item] = field(default_factory=dict)

    def store(self, item: Item) -> None:
        reasons = []
        if item.kind not in KINDS:
            reasons.append(f"{item.key}: the kind {item.kind!r} is unknown")
        if item.key in self.items:
            reasons.append(f"{item.key} is already kept; keep a new version apart")
        if not item.identity:
            reasons.append(f"{item.key} has no identity to check a reuse against")
        unknown = [k for k in item.links if k not in self.items]
        if unknown:
            reasons.append(f"{item.key} links to {', '.join(unknown)}, not kept")
        if item.kind == RESULT and not any(
            self.items[k].kind == LIMITATION for k in item.links if k in self.items
        ):
            reasons.append(f"{item.key}: a result is kept with its limitations")
        if reasons:
            raise ReuseRefused(reasons)
        self.items[item.key] = item


def recall(memory: Memory, key: str, presented: Mapping[str, str]) -> Recalled:
    """``key`` for a reuse that presents the identities ``presented``, with
    every item it links; refused when an identity differs or is missing."""
    item = memory.items.get(key)
    if item is None:
        raise ReuseRefused([f"nothing is kept under {key}"])
    reasons = [
        f"the {name} differs from the one it was kept with"
        if name in presented
        else f"the reuse presents no {name}"
        for name, digest in item.identity.items()
        if presented.get(name) != digest
    ]
    if reasons:
        raise ReuseRefused(reasons)
    return Recalled(item, tuple(memory.items[k] for k in item.links))
