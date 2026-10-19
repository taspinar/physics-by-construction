"""pbc.discovery.equations: the differentiators against known derivatives
and known noise, the sparse regression on an equation it must find, the
library's singular values on data with a relation, and the integration
against an exact motion."""

import numpy as np
import pytest

from pbc.discovery.equations import (
    Derivatives,
    Equation,
    central_differences,
    combine,
    evaluate,
    integrate,
    polynomial_library,
    savitzky_golay,
    singular_values,
    sparse_regression,
)


def test_central_differences_are_second_order():
    errors = []
    for dt in (0.02, 0.01):
        t = np.arange(0.0, 6.0, dt)
        d = central_differences(np.sin(t), dt)
        assert d.x == pytest.approx(np.sin(t[1:-1]))
        errors.append(
            (
                np.max(np.abs(d.v - np.cos(t[1:-1]))),
                np.max(np.abs(d.a + np.sin(t[1:-1]))),
            )
        )
        # The leading errors: dt^2 / 6 times x''' and dt^2 / 12 times x''''.
        assert errors[-1][0] <= dt**2 / 6
        assert errors[-1][1] <= dt**2 / 12
    for coarse, fine in zip(*errors, strict=True):
        assert coarse / fine == pytest.approx(4.0, rel=0.01)


def test_central_differences_amplify_noise_by_the_square_of_the_step():
    rng = np.random.default_rng(0)
    sigma, dt = 1e-3, 0.01
    d = central_differences(sigma * rng.standard_normal(200_000), dt)

    assert np.std(d.v) == pytest.approx(sigma / (np.sqrt(2) * dt), rel=0.02)
    assert np.std(d.a) == pytest.approx(np.sqrt(6) * sigma / dt**2, rel=0.02)


def test_savitzky_golay_is_exact_on_a_cubic_and_drops_half_a_window_each_side():
    dt = 0.05
    t = np.arange(0.0, 3.0, dt)
    x = 1.0 - 2.0 * t + 0.5 * t**2 - 0.25 * t**3

    d = savitzky_golay(x, dt, window=9, order=3)

    inner = t[4:-4]
    assert d.x == pytest.approx(1.0 - 2.0 * inner + 0.5 * inner**2 - 0.25 * inner**3)
    assert d.v == pytest.approx(-2.0 + inner - 0.75 * inner**2)
    assert d.a == pytest.approx(1.0 - 1.5 * inner)


def test_savitzky_golay_smooths_noise_and_biases_a_curve():
    rng = np.random.default_rng(1)
    dt = 0.01
    t = np.arange(0.0, 20.0, dt)
    sigma = 1e-3
    noisy = central_differences(sigma * rng.standard_normal(t.size), dt)
    smooth = savitzky_golay(sigma * rng.standard_normal(t.size), dt, window=41)
    assert np.std(smooth.a) < np.std(noisy.a) / 100

    narrow = savitzky_golay(np.sin(3 * t), dt, window=11)
    wide = savitzky_golay(np.sin(3 * t), dt, window=61)
    bias_narrow = np.max(np.abs(narrow.a + 9 * narrow.x))
    bias_wide = np.max(np.abs(wide.a + 9 * np.sin(3 * t[30:-30])))
    assert bias_wide > 10 * bias_narrow


def test_a_window_must_be_odd_and_longer_than_the_polynomial():
    with pytest.raises(ValueError, match="odd"):
        savitzky_golay(np.zeros(50), 0.1, window=10)
    with pytest.raises(ValueError, match="odd"):
        savitzky_golay(np.zeros(50), 0.1, window=3, order=3)


def test_the_library_lists_every_term_up_to_its_degree():
    assert polynomial_library(2) == ("1", "x", "v", "x^2", "x v", "v^2")
    assert len(polynomial_library(3)) == 10
    columns = evaluate(("1", "x v^2", "x^3"), np.array([2.0]), np.array([3.0]))
    assert columns.tolist() == [[1.0, 18.0, 8.0]]


def test_sparse_regression_finds_a_sparse_equation_and_drops_the_rest():
    rng = np.random.default_rng(2)
    x, v = rng.uniform(-2, 2, 500), rng.uniform(-2, 2, 500)
    data = Derivatives(x, v, -2.0 * x + 0.5 * x * v - 0.1 * v**3)

    equation = sparse_regression(polynomial_library(3), data)

    assert equation.coefficients == pytest.approx({"x": -2.0, "x v": 0.5, "v^3": -0.1})
    assert equation.residual < 1e-12
    assert equation.formula() == "a = -2 x + 0.5 x v - 0.1 v^3"


def test_a_term_below_the_threshold_is_dropped():
    rng = np.random.default_rng(3)
    x, v = rng.uniform(-1, 1, 500), rng.uniform(-1, 1, 500)
    data = Derivatives(x, v, -4.0 * x + 0.01 * v)

    assert set(sparse_regression(polynomial_library(1), data).coefficients) == {"x"}
    kept = sparse_regression(polynomial_library(1), data, threshold=1e-4)
    assert kept.coefficients == pytest.approx({"x": -4.0, "v": 0.01})


def test_singular_values_reveal_a_relation_of_the_data():
    angle = np.linspace(0.0, 2 * np.pi, 400)
    on_circle = Derivatives(np.cos(angle), np.sin(angle), np.zeros(400))
    rng = np.random.default_rng(4)
    scattered = Derivatives(rng.normal(size=400), rng.normal(size=400), np.zeros(400))

    # x^2 + v^2 = 1 on the circle: 1, x^2, v^2 are dependent (and so are
    # x, x^3, x v^2 and v, x^2 v, v^3 after multiplying by x and by v).
    assert np.sum(singular_values(polynomial_library(3), on_circle) < 1e-12) == 3
    assert singular_values(polynomial_library(3), scattered).min() > 1e-2


def test_integrate_follows_an_exact_motion():
    t = np.linspace(0.0, 10.0, 501)

    x = integrate(lambda x, v: -4.0 * x, 1.0, 0.0, t)

    assert x == pytest.approx(np.cos(2.0 * t), abs=1e-8)


def test_an_equation_evaluates_its_terms_and_combine_joins_samples():
    equation = Equation({"x": -4.0, "v": -0.3}, 0.0)
    assert equation.acceleration(np.array([1.0]), np.array([2.0])) == pytest.approx(
        -4.6
    )
    assert Equation({}, 0.0).formula() == "a = 0"

    one = Derivatives(np.array([1.0]), np.array([2.0]), np.array([3.0]))
    joined = combine([one, one])
    assert joined.x.tolist() == [1.0, 1.0]
    assert joined.a.tolist() == [3.0, 3.0]
