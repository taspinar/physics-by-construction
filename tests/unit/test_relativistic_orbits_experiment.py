"""The experiment of "Relativistic orbits" (astrophysics 05)."""

import re
from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.astrophysics import relativistic_orbits

MODULE = "pbc.astrophysics.experiments.relativistic_orbits"
PAGE = "astrophysics/05-relativistic-orbits"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("relativistic_orbits")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def _stated_cubic(text: str, pattern: str):
    """The factors of the first integral as a text states it, as a function
    of m, u, u1, u2, u3 (LaTeX subscripts and spacing removed)."""
    match = re.search(pattern, text)
    assert match, "the first integral is not stated"
    factors = re.sub(r"[_\\, ]", "", match.group(1)).replace(")(", ")*(")
    return lambda m, u, u1, u2, u3: 2 * m * eval(factors)


@pytest.mark.parametrize(
    ("source", "pattern"),
    [
        (
            Path(__file__).parents[2]
            / "site/lessons/astrophysics/05-relativistic-orbits/index.qmd",
            r"= 2m\\,(\(u - u_1\)\([^)]*\)\([^)]*\)),",
        ),
        (
            Path(relativistic_orbits.__file__),
            r"\(u'\)² = 2 m (\(u - u1\)\([^)]*\)\([^)]*\)),",
        ),
    ],
    ids=["page", "module"],
)
def test_the_stated_cubic_is_the_first_integral_and_positive_on_the_orbit(
    source, pattern
):
    m, p, e = 0.02, 1.0, 0.4
    u1, u2 = (1 - e) / p, (1 + e) / p
    u3 = 1 / (2 * m) - u1 - u2
    h2 = relativistic_orbits.angular_momentum(m, p, e) ** 2
    cubic = _stated_cubic(source.read_text(), pattern)
    u = np.linspace(u1, u2, 201)[1:-1]
    # (u')² is a square: positive strictly between the turning points ...
    assert np.all(cubic(m, u, u1, u2, u3) > 0)
    # ... and, up to the constant of integration, 2 m u³ - u² + 2 m u / h².
    polynomial = 2 * m * u**3 - u**2 + 2 * m * u / h2
    assert np.ptp(cubic(m, u, u1, u2, u3) - polynomial) < 1e-12


def test_the_strong_field_orbit_turns_by_the_exact_amount(results):
    _, found = results

    numbers = found["numbers"]
    assert numbers["strong-turn"] == numbers["strong-exact"]
    assert float(numbers["strong-first"]) == pytest.approx(6 * np.pi * 0.04, abs=1e-4)
    assert float(numbers["strong-turn"]) > 1.1 * float(numbers["strong-first"])


def test_the_turn_follows_the_first_order_formula_to_second_order(results):
    _, found = results

    second = 1.5 * np.pi * (18 + 0.5**2)
    rows = found["tables"]["precession"]["rows"]
    for field, first, _, integrated, scaled, pn, pn_scaled in rows:
        x = float(field)
        assert float(first) == pytest.approx(6 * np.pi * x, rel=1e-4)
        assert integrated.startswith("below")
        # The gap of the exact turn tends to the second-order coefficient,
        # with a third-order remainder.
        assert float(scaled) == pytest.approx(second, rel=20 * x)
        assert abs(float(pn) / float(first) - 1) < 10 * x
        assert abs(float(pn_scaled)) < 200
    numbers = found["numbers"]
    assert float(numbers["exact-order"]) == pytest.approx(2.0, abs=0.1)
    assert float(numbers["pn-order"]) == pytest.approx(2.0, abs=0.1)
    assert numbers["gauss-gap"].startswith("below")


def test_stable_circular_orbits_exist_only_outside_six_m(results):
    _, found = results

    rows = found["tables"]["circular"]["rows"]
    for _, h2, numerical, closed, _ in rows:
        if float(h2) < 12:
            assert numerical == closed == ""
        else:
            assert numerical == closed
            assert float(closed) > 6
    assert float(rows[1][3]) < 8  # just above the critical angular momentum


def test_the_exercises(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["mercury-century"]) == pytest.approx(43.0, abs=0.1)
    for _, exact, formula, first in found["tables"]["near-circular"]["rows"]:
        assert float(exact) == pytest.approx(
            float(formula), abs=2e-5 * float(exact) + 1e-5
        )
        assert float(first) < float(exact)
    assert 0.01 < float(numbers["ten-percent"]) < 0.03
