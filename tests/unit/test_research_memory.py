"""The research memory and the check of a reuse (``pbc.research.memory``,
RR7, Issue #594)."""

import pytest

from pbc.research.memory import (
    LIMITATION,
    QUESTION,
    RESULT,
    Item,
    Memory,
    ReuseRefused,
    recall,
)

LIMIT = Item("limit", LIMITATION, "a simulation", "the review", {"log": "l"})
OPEN = Item("open", QUESTION, "where?", "the review", {"log": "l"}, revisit="later")
RESULT_ITEM = Item(
    "result",
    RESULT,
    "above the bound",
    "the claim",
    {"code": "c", "configuration": "k"},
    links=("limit", "open"),
)


def kept() -> Memory:
    memory = Memory()
    for item in (LIMIT, OPEN, RESULT_ITEM):
        memory.store(item)
    return memory


def test_a_result_is_handed_over_with_what_it_was_kept_with():
    found = recall(kept(), "result", {"code": "c", "configuration": "k"})
    assert found.item == RESULT_ITEM
    assert [i.key for i in found.attached] == ["limit", "open"]


def test_a_reuse_with_another_identity_is_refused_with_every_reason():
    with pytest.raises(ReuseRefused) as refused:
        recall(kept(), "result", {"code": "other"})
    assert refused.value.reasons == (
        "the code differs from the one it was kept with",
        "the reuse presents no configuration",
    )
    with pytest.raises(ReuseRefused, match="nothing is kept"):
        recall(kept(), "missing", {})


def test_a_result_is_kept_only_with_a_limitation():
    memory = Memory()
    memory.store(OPEN)
    with pytest.raises(ReuseRefused, match="kept with its limitations"):
        memory.store(
            Item("bare", RESULT, "above", "the claim", {"code": "c"}, links=("open",))
        )


def test_the_memory_refuses_a_second_key_an_unknown_link_or_no_identity():
    memory = kept()
    with pytest.raises(ReuseRefused, match="already kept"):
        memory.store(LIMIT)
    with pytest.raises(ReuseRefused) as refused:
        memory.store(Item("x", "rumour", "t", "s", {}, links=("nowhere",)))
    assert len(refused.value.reasons) == 3
