"""Typed interpretations of a picture (F142): a status from the fixed set, a
basis always, what would settle it exactly when it is uncertain, and a check
with evidence."""

import pytest

from pbc.electromagnetism.observations import (
    CONFIRMED,
    CONTRADICTED,
    INFERRED,
    NOT_CHECKED,
    READ,
    UNCERTAIN,
    Check,
    Interpretation,
    check,
)


def test_a_statement_has_one_of_three_statuses():
    with pytest.raises(ValueError, match="status"):
        Interpretation("the needle is fast", "obvious", "it looks fast")


def test_every_statement_names_what_it_rests_on():
    with pytest.raises(ValueError, match="rests on"):
        Interpretation("channel 2 is across C", READ, "")


def test_an_uncertain_statement_names_what_would_settle_it():
    with pytest.raises(ValueError, match="settle"):
        Interpretation("about once a second", UNCERTAIN, "twenty frames")
    reading = Interpretation(
        "about once a second", UNCERTAIN, "twenty frames", settled_by="a faster camera"
    )
    assert reading.settled_by == "a faster camera"


def test_only_an_uncertain_statement_is_settled_by_more():
    with pytest.raises(ValueError, match="only an uncertain"):
        Interpretation("channel 1 is the source", READ, "the probe", settled_by="x")


def test_a_check_has_an_outcome_and_its_evidence():
    reading = Interpretation("the peak is at f0", INFERRED, "resonance")
    assert check(reading, True, "peak at f0").outcome == CONFIRMED
    assert check(reading, False, "peak below f0").outcome == CONTRADICTED
    assert check(reading, None, "").outcome == NOT_CHECKED
    with pytest.raises(ValueError, match="evidence"):
        Check(reading, CONFIRMED, "")
    with pytest.raises(ValueError, match="outcome"):
        Check(reading, "probably", "x")
