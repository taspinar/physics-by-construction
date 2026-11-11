"""``pbc.quantum.bell_test``: the model of the entanglement lesson at the
settings of the Munich Bell test, its fits, and the checks of a test's
statistics."""

import numpy as np
import pytest

from pbc.data.reference.munich_bell import SETTINGS, STATES, Correlator, Pairs, sign
from pbc.quantum import bell
from pbc.quantum.bell_test import (
    ALPHA,
    BETA,
    IDEAL,
    events_for_sigmas,
    fit_visibility,
    model_chsh,
    model_s_of_fit,
    no_signalling,
    predicted_correlator,
    setting_balance,
    setting_pair_counts,
    signed_sum,
    visibility_threshold,
)

PSI_PLUS = np.array([0, 1, 1, 0], dtype=complex) / np.sqrt(2)
VECTORS = {"Psi-": bell.SINGLET, "Psi+": PSI_PLUS}


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("visibility", [1.0, 0.8])
@pytest.mark.parametrize("offset", [0.0, -0.09, 0.3])
def test_the_predicted_correlator_is_the_entanglement_lessons(
    state, visibility, offset
):
    """The closed form equals the correlator the Q5 code computes for the
    state mixed with white noise, with lab 2's angle shifted by the offset."""
    rho = visibility * bell.density(VECTORS[state]) + (1 - visibility) * np.eye(4) / 4
    for a, b in SETTINGS:
        from_code = bell.correlation(
            bell.joint_probabilities(rho, ALPHA[a], BETA[b] + offset)
        )
        assert predicted_correlator(state, a, b, visibility, offset) == pytest.approx(
            from_code, abs=1e-12
        )


@pytest.mark.parametrize("state", STATES)
def test_a_pure_state_gives_the_ideal_correlators_with_the_papers_signs(state):
    for a, b in SETTINGS:
        assert predicted_correlator(state, a, b) == pytest.approx(
            sign(state, a, b) * IDEAL
        )


@pytest.mark.parametrize("state", STATES)
def test_the_model_s_is_the_signed_sum_of_its_correlators(state):
    for visibility, offset in ((1.0, 0.0), (0.79, -0.09), (0.5, 0.2)):
        terms = {
            k: predicted_correlator(state, *k, visibility, offset) for k in SETTINGS
        }
        assert signed_sum(state, terms) == pytest.approx(model_chsh(visibility, offset))
    assert model_chsh(1.0) == pytest.approx(2 * np.sqrt(2))
    assert visibility_threshold() == pytest.approx(1 / np.sqrt(2))
    assert model_chsh(visibility_threshold(0.1), 0.1) == pytest.approx(2.0)


@pytest.mark.parametrize("state", STATES)
def test_the_fit_recovers_the_visibility_and_the_offset(state):
    """Synthetic correlators of a known model, with errors of a run of about
    1250 events per setting pair, fitted back."""
    truth = (0.79, -0.09)
    terms = {}
    for k in SETTINGS:
        e = predicted_correlator(state, *k, *truth)
        terms[k] = Correlator(e, float(np.sqrt((1 - e**2) / 1250)), 1250)
    two = fit_visibility(terms, state, with_offset=True)
    assert two.names == ("visibility", "offset")
    assert two.value("visibility") == pytest.approx(truth[0], abs=1e-6)
    assert two.value("offset") == pytest.approx(truth[1], abs=1e-6)
    assert np.isfinite(two.stderr).all() and two.identifiable == (True, True)
    s, s_err = model_s_of_fit(two)
    assert s == pytest.approx(model_chsh(*truth)) and 0 < s_err < 0.1
    # Without the offset the one-parameter model cannot describe these four
    # correlators: its reduced chi-square is far above one and it says so.
    one = fit_visibility(terms, state, with_offset=False)
    assert one.names == ("visibility",)
    assert one.reduced_chi2 > 3 and any("chi-square" in w for w in one.warnings)
    # The one-parameter model fitted to its own correlators is exact.
    exact = {
        k: Correlator(predicted_correlator(state, *k, 0.79), 0.02, 1250)
        for k in SETTINGS
    }
    assert fit_visibility(exact, state, with_offset=False).value(
        "visibility"
    ) == pytest.approx(0.79, abs=1e-8)


def _pairs(rng: np.random.Generator, n: int, signalling: bool = False) -> Pairs:
    """``n`` events with fair random settings and outcomes; with
    ``signalling``, lab 1's outcome follows lab 2's setting."""
    a, b = rng.integers(0, 2, n), rng.integers(0, 2, n)
    x, y = rng.integers(0, 2, n), rng.integers(0, 2, n)
    if signalling:  # lab 1's outcome copies lab 2's setting most of the time
        x = np.where(rng.random(n) < 0.7, b, x)
    zeros = np.zeros(n, int)
    return Pairs(np.arange(n), np.array(["Psi-"] * n), a, x, b, y, zeros, zeros)


def test_the_setting_checks_see_a_fair_coin_and_a_biased_one():
    rng = np.random.default_rng(1)
    pairs = _pairs(rng, 4000)
    mask = np.ones(len(pairs), bool)
    fair = setting_balance(pairs.a[mask])
    assert fair.n == 4000 and fair.stderr == pytest.approx(np.sqrt(0.25 / 4000))
    assert abs(fair.sigmas) < 4
    biased = setting_balance(np.ones(4000, int))
    assert biased.fraction == 1.0 and biased.sigmas > 50
    counts, chi2 = setting_pair_counts(pairs, mask)
    assert sum(counts) == 4000 and chi2 < 16
    _, skewed = setting_pair_counts(pairs, mask & (pairs.a == 0))
    assert skewed > 1000


def test_no_signalling_sees_a_lab_that_follows_the_other_labs_setting():
    rng = np.random.default_rng(2)
    pairs = _pairs(rng, 4000)
    quiet = no_signalling(pairs, np.ones(4000, bool))
    assert [(m.lab, m.own_setting) for m in quiet] == [
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1),
    ]
    assert all(abs(m.sigmas) < 4 for m in quiet)
    for m in quiet:  # every event of the lab's own setting is counted once
        own = pairs.a if m.lab == 1 else pairs.b
        assert sum(m.n) == int((own == m.own_setting).sum())
    loud = no_signalling(_pairs(rng, 4000, signalling=True), np.ones(4000, bool))
    assert all(m.sigmas > 20 for m in loud if m.lab == 1)
    assert all(abs(m.sigmas) < 4 for m in loud if m.lab == 2)


def test_the_events_a_significance_needs_scale_as_its_square():
    four = events_for_sigmas(2.2, 0.05, 5000, 4)
    eight = events_for_sigmas(2.2, 0.05, 5000, 8)
    assert four == 5000 and eight == 20000
    with pytest.raises(ValueError, match="bound"):
        events_for_sigmas(1.9, 0.05, 5000, 4)
