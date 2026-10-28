"""Required checks on the waveform comparator of the gravitational-wave lab
(F43; docs/authoring.md, "Widgets" and "On-demand data").

The component loads its data after a button press, so the checks cover what
the page does without the press (the static figure, nothing requested), what
it does after (a slider, metrics, a text export), and that what it shows is
what the build embedded, which is what the lab computed: the observed-value
test.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, Page
from support import site_checks
from support.site_checks import DESKTOP, PHONE, WCAG_TAGS, describe
from support.site_server import SiteServer

from pbc.data import SAMPLES_DIR
from pbc.data.gwosc import FILES, read_strain
from pbc.data.gwstrain import (
    correlation_with_control,
    cut_segment,
    fit_chirp,
    make_whitener,
    models_at_masses,
    noise_sigma,
)

LESSON = "lessons/mechanics/11-gravitational-wave-strain/index.html"
SOURCE = "site/lessons/mechanics/11-gravitational-wave-strain"
DATA = (
    "lessons/mechanics/11-gravitational-wave-strain/"
    "index_files/figure-html/chirp-masses.json"
)
COMPARATOR = "#waveform-comparator"
LOAD = f"{COMPARATOR} button[data-loads-ondemand]"
BAND = (35.0, 350.0)
WINDOW = (-0.2, 0.0)

# The embedded samples are rounded to five places, far below the unit noise of
# the whitened series; the metrics are rounded to the digits they are shown with.
SAMPLE_TOLERANCE = 6e-6
# Against a fresh run of the lab code: the build and this run make the same
# computation, so only the rounding of the embedded numbers differs.
METRIC_TOLERANCE = {"chi2": 0.06, "reduced_chi2": 2e-3, "rms_residual": 2e-4}


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


@pytest.fixture(scope="module")
def embedded(site_dir: Path) -> dict:
    return json.loads((site_dir / DATA).read_text(encoding="utf-8"))


def load(page: Page, server: SiteServer) -> None:
    page.goto(server.url + LESSON, wait_until="networkidle")
    page.locator(LOAD).click()
    page.locator(f"{COMPARATOR}.widget-active").wait_for()


def js(value: float) -> str:
    """A number as the browser writes it: 24.0 is "24"."""
    return str(int(value)) if value == int(value) else str(value)


def displayed(page: Page, quantity: str) -> str:
    return page.locator(f'{COMPARATOR} output[data-quantity="{quantity}"]').inner_text()


def to_slider_index(page: Page, index: int) -> None:
    slider = page.locator(f"{COMPARATOR} input[type=range]")
    slider.focus()
    page.keyboard.press("Home")
    for _ in range(index):
        page.keyboard.press("ArrowRight")


# --- Without the action -------------------------------------------------------------


def test_without_javascript_the_lesson_shows_the_static_figure(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + LESSON, wait_until="load")

    figure = page.locator(f"{COMPARATOR} img")
    assert figure.count() == 1
    assert figure.evaluate("image => image.complete && image.naturalWidth > 0")
    assert figure.get_attribute("alt")
    assert page.locator(f"{COMPARATOR} figcaption").inner_text().strip()
    assert (
        page.locator(f"{COMPARATOR} :is(input, svg, [data-loads-ondemand])").count()
        == 0
    )
    context.close()


def test_with_scripts_the_page_offers_the_data_and_requests_none_of_it(
    page: Page, server: SiteServer
):
    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))
    page.goto(server.url + LESSON, wait_until="networkidle")

    assert page.locator(LOAD).count() == 1
    assert page.locator(f"{COMPARATOR} img").count() == 1
    assert not [url for url in requested if url.endswith("chirp-masses.json")]


def test_a_failed_load_leaves_the_figure_and_says_so(page: Page, server: SiteServer):
    page.route("**/chirp-masses.json", lambda route: route.abort())
    page.goto(server.url + LESSON, wait_until="networkidle")
    page.locator(LOAD).click()

    status = page.locator(f"{COMPARATOR} [role=status]")
    status.filter(has_text="could not be loaded").wait_for()
    assert page.locator(f"{COMPARATOR} img").count() == 1
    assert page.locator(LOAD).is_enabled()


# --- After the action ----------------------------------------------------------------


def test_the_slider_moves_between_the_models_with_the_keyboard_alone(
    page: Page, server: SiteServer, embedded: dict
):
    load(page, server)
    parameters = [m["parameter"] for m in embedded["models"]]
    assert page.evaluate("document.activeElement.type") == "range"

    to_slider_index(page, 0)
    assert displayed(page, "parameter") == js(parameters[0])
    page.keyboard.press("End")
    assert displayed(page, "parameter") == js(parameters[-1])
    assert page.locator(COMPARATOR).get_attribute("data-parameter") == js(
        parameters[-1]
    )


def test_the_page_opens_on_the_best_fit_and_says_which_models_are_not(
    page: Page, server: SiteServer, embedded: dict
):
    load(page, server)

    assert displayed(page, "parameter") == js(embedded["best_parameter"])
    assert displayed(page, "best") == "yes"
    page.keyboard.press("Home")
    assert displayed(page, "best") == "no"


def test_every_trial_mass_is_listed_with_its_metrics_as_embedded(
    page: Page, server: SiteServer, embedded: dict
):
    load(page, server)
    formats = {
        "chi2": "{:.1f}",
        "reduced_chi2": "{:.3f}",
        "rms_residual": "{:.4f}",
        "correlation": "{:.4f}",
    }

    for index, model in enumerate(embedded["models"]):
        to_slider_index(page, index)
        for key, pattern in formats.items():
            assert displayed(page, key) == pattern.format(model["metrics"][key])
        assert displayed(page, "coalescence_time") == js(model["coalescence_time"])


def test_the_drawing_shows_every_sample_of_the_file_and_changes_no_value(
    page: Page, server: SiteServer, embedded: dict
):
    # The observed-value test: the points of each polyline are an affine map
    # of the embedded numbers, with the same count, and nothing else. A
    # smoothed, resampled, clipped, or shifted series would not fit a line.
    load(page, server)
    to_slider_index(page, 3)
    model = embedded["models"][3]
    expected = {
        "measured": embedded["measured"],
        "model": model["values"],
        "residual": model["residual"],
    }

    for series, values in expected.items():
        points = page.locator(
            f'{COMPARATOR} polyline[data-series="{series}"]'
        ).get_attribute("points")
        xy = np.array([[float(c) for c in p.split(",")] for p in points.split()])
        assert len(xy) == len(values) == len(embedded["time"])
        for axis, numbers in ((0, embedded["time"]), (1, values)):
            fit = np.polyfit(numbers, xy[:, axis], 1)
            error = np.abs(np.polyval(fit, numbers) - xy[:, axis])
            assert error.max() <= 0.06, f"{series}: axis {axis} is not an affine map"
        assert np.polyfit(values, xy[:, 1], 1)[0] < 0  # up is larger


def test_the_text_export_holds_exactly_the_displayed_values(
    page: Page, server: SiteServer, embedded: dict
):
    load(page, server)
    to_slider_index(page, 5)
    model = embedded["models"][5]
    page.get_by_role("button", name="Show the displayed values as text").click()

    text = page.locator(f"{COMPARATOR} textarea").input_value()
    rows = [
        line.split("\t")
        for line in text.splitlines()
        if line and not line.startswith("#")
    ]
    assert rows[0] == ["time (s)", "measured", "model", "residual"]
    assert len(rows) - 1 == len(embedded["time"])
    for row, t, y, f, r in zip(
        rows[1:],
        embedded["time"],
        embedded["measured"],
        model["values"],
        model["residual"],
        strict=True,
    ):
        assert [float(v) for v in row] == [t, y, f, r]
    assert (
        f"# chirp mass, detector frame (solar masses): {js(model['parameter'])}" in text
    )
    # Moving the slider moves the text with it.
    page.keyboard.press("End")
    page.locator(f"{COMPARATOR} input[type=range]").focus()
    page.keyboard.press("Home")
    assert (
        "(solar masses): " + js(embedded["models"][0]["parameter"])
        in page.locator(f"{COMPARATOR} textarea").input_value()
    )
    assert (
        page.locator(f"{COMPARATOR} a[download]")
        .get_attribute("href")
        .startswith("blob:")
    )


# --- Against the lab code -----------------------------------------------------------


@pytest.fixture(scope="module")
def fresh() -> dict:
    """The comparison of the lesson, recomputed from the committed sample with
    the code of src/pbc and the recipe of the page."""
    strains = {
        n: read_strain(SAMPLES_DIR / "gw150914-strain" / f) for n, f in FILES.items()
    }
    big = {n: cut_segment(s, 2.0) for n, s in strains.items()}
    white_big = {
        n: make_whitener(strains[n], big[n], BAND)(big[n].strain) for n in strains
    }
    corr = correlation_with_control(
        white_big["H1"], white_big["L1"], big["H1"].time, strains["H1"].sample_rate
    )
    seg = {n: cut_segment(s, 0.75) for n, s in strains.items()}
    white = {n: make_whitener(strains[n], seg[n], BAND) for n in strains}
    data = {n: white[n](seg[n].strain) for n in strains}
    time = seg["H1"].time
    sigma = noise_sigma(data["H1"], time, (0.3, 0.65))
    delays = {"H1": 0.0, "L1": corr["lag"]}
    fit = fit_chirp(
        time, data, white, delays, window=WINDOW, sigma=sigma,
        mc_grid=np.arange(22.0, 50.0, 1.0),
    )  # fmt: skip
    return {
        "time": time, "data": data, "white": white, "delays": delays,
        "sigma": sigma, "fit": fit,
    }  # fmt: skip


def test_the_embedded_series_and_metrics_agree_with_a_fresh_run_of_pbc(
    site_dir: Path, embedded: dict, request: pytest.FixtureRequest
):
    # A fresh run on this machine is compared with a result of the same
    # machine only. A result restored from the base was computed and compared
    # by the run that made it, on another platform whose floating point differs
    # by more than the rounding (issue 268); the tolerance stays as it is.
    try:
        reason = site_checks.inherited(site_dir, SOURCE)
    except site_checks.SelectionError as error:
        pytest.fail(f"whether this run executed the lesson is unknown: {error}")
    if reason is not None:
        pytest.skip(reason)
    fresh = request.getfixturevalue("fresh")
    time, data, fit = fresh["time"], fresh["data"], fresh["fit"]
    shown = (time >= -0.25) & (time <= 0.05)  # the window of the page
    assert shown.sum() == len(embedded["time"])
    assert embedded["time"] == pytest.approx(time[shown], abs=1e-5)
    assert embedded["measured"] == pytest.approx(
        data["H1"][shown], abs=SAMPLE_TOLERANCE
    )
    assert embedded["sigma"] == pytest.approx(fresh["sigma"], abs=1e-5)
    assert embedded["best_parameter"] == pytest.approx(fit.mc, abs=1e-3)

    masses = np.array([m["parameter"] for m in embedded["models"]])
    models = models_at_masses(
        time, data, fresh["white"], fresh["delays"], masses, window=WINDOW,
        sigma=fresh["sigma"], mc_start=fit.mc, t_c_start=fit.t_c,
    )  # fmt: skip
    for shown_model, reference in zip(embedded["models"], models, strict=True):
        assert shown_model["values"] == pytest.approx(
            reference.model["H1"][shown], abs=SAMPLE_TOLERANCE
        )
        for key, tolerance in METRIC_TOLERANCE.items():
            assert shown_model["metrics"][key] == pytest.approx(
                getattr(reference, key), abs=tolerance
            )
        assert shown_model["metrics"]["correlation"] == pytest.approx(
            reference.correlation, abs=2e-4
        )


# --- Accessibility, reduced motion, the built site -----------------------------------


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_the_accessibility_scan_passes_before_and_after_loading(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.goto(server.url + LESSON, wait_until="networkidle")
    for state in ("offered", "loaded"):
        if state == "loaded":
            page.locator(LOAD).click()
            page.locator(f"{COMPARATOR}.widget-active").wait_for()
        results = Axe().run(
            page, options={"runOnly": {"type": "tag", "values": WCAG_TAGS}}
        )
        assert results.violations_count == 0, f"{state}: {results.generate_report()}"
    context.close()


def test_the_drawing_has_a_text_alternative_in_the_page(page: Page, server: SiteServer):
    load(page, server)

    drawing = page.locator(f"{COMPARATOR} svg.widget-drawing")
    assert drawing.get_attribute("role") == "img"
    assert drawing.get_attribute("aria-label")
    described = drawing.get_attribute("aria-describedby")
    assert page.locator(f"#{described}").inner_text().strip()


def test_with_reduced_motion_nothing_in_the_component_animates(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce")
    page = context.new_page()
    load(page, server)
    page.keyboard.press("End")

    animations = page.evaluate(
        f"document.querySelector('{COMPARATOR}')"
        ".getAnimations({subtree: true}).length"
    )
    durations = page.locator(f"{COMPARATOR} *").evaluate_all(
        "elements => elements.map(e => getComputedStyle(e))"
        ".filter(s => s.animationName !== 'none'"
        " || parseFloat(s.transitionDuration) > 0).length"
    )
    context.close()
    assert animations == 0 and durations == 0


def test_loading_and_operating_the_component_writes_no_cookie_and_no_storage(
    page: Page, server: SiteServer
):
    page.add_init_script(f"({site_checks._RECORD_STORAGE_WRITES})()")
    load(page, server)
    page.keyboard.press("End")
    page.get_by_role("button", name="Show the displayed values as text").click()

    writes = [w for w in page.evaluate("window.__storageWrites") if "theme" not in w]
    assert page.context.cookies() == []
    # Quarto's own scripts keep a little state; the data of the page is not in it.
    assert not [w for w in writes if "waveform" in w or "chirp" in w]


def test_the_on_demand_data_is_within_its_budget_and_only_loads_after_an_action(
    browser: Browser, server: SiteServer, site_dir: Path
):
    files = site_checks.ondemand_files(site_dir)
    assert LESSON in files, "the check has nothing to check"
    sizes = site_checks.measure_payloads(browser, server, site_dir)

    violations = site_checks.check_ondemand_budget(site_dir, sizes)
    violations += site_checks.check_ondemand_loads_after_action(
        browser, server, site_dir
    )

    assert not violations, describe(violations)


# --- The same component on the wave flume lab (W8) -----------------------------------
#
# A family of named models instead of trial masses: the words come from the
# data, no model is the best one, and the residual is the model minus the
# measurement, as in the static figure.

FLUME = "lessons/waves/08-wave-flume-lab/index.html"
FLUME_DATA = "lessons/waves/08-wave-flume-lab/index_files/figure-html/gauge-five.json"
FLUME_FORMATS = {
    "rms_residual": "{:.3f}",
    "largest_residual": "{:.3f}",
    "correlation": "{:.4f}",
}


@pytest.fixture(scope="module")
def flume_embedded(site_dir: Path) -> dict:
    return json.loads((site_dir / FLUME_DATA).read_text(encoding="utf-8"))


def load_flume(page: Page, server: SiteServer) -> None:
    page.goto(server.url + FLUME, wait_until="networkidle")
    page.locator(LOAD).click()
    page.locator(f"{COMPARATOR}.widget-active").wait_for()


def test_the_flume_page_shows_its_static_figure_without_javascript(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + FLUME, wait_until="load")

    figure = page.locator(f"{COMPARATOR} img")
    assert figure.count() == 1
    assert figure.evaluate("image => image.complete && image.naturalWidth > 0")
    assert page.locator(f"{COMPARATOR} figcaption").inner_text().strip()
    assert page.locator(f"{COMPARATOR} :is(input, svg)").count() == 0
    context.close()


def test_the_flume_button_names_its_models_and_requests_nothing_before(
    page: Page, server: SiteServer
):
    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))
    page.goto(server.url + FLUME, wait_until="networkidle")

    assert page.locator(LOAD).inner_text() == "Compare the models one by one"
    assert not [url for url in requested if url.endswith("gauge-five.json")]


def test_every_flume_model_is_listed_by_name_with_its_metrics_as_embedded(
    page: Page, server: SiteServer, flume_embedded: dict
):
    load_flume(page, server)
    assert page.locator(f'{COMPARATOR} output[data-quantity="best"]').count() == 0
    for index, model in enumerate(flume_embedded["models"]):
        to_slider_index(page, index)
        assert displayed(page, "parameter") == model["parameter"]
        for key, pattern in FLUME_FORMATS.items():
            assert displayed(page, key) == pattern.format(model["metrics"][key])
    names = [m["parameter"] for m in flume_embedded["models"]]
    # Our predictions are simulated; every solver is labelled by its artifact.
    assert all("modelled-reference" in n for n in names if "gauge 1" not in n)


def test_the_flume_drawing_and_export_hold_exactly_the_embedded_values(
    page: Page, server: SiteServer, flume_embedded: dict
):
    load_flume(page, server)
    to_slider_index(page, 1)
    model = flume_embedded["models"][1]
    for series, values in (
        ("measured", flume_embedded["measured"]),
        ("model", model["values"]),
        ("residual", model["residual"]),
    ):
        points = page.locator(
            f'{COMPARATOR} polyline[data-series="{series}"]'
        ).get_attribute("points")
        xy = np.array([[float(c) for c in p.split(",")] for p in points.split()])
        assert len(xy) == len(values) == len(flume_embedded["time"])
        fit = np.polyfit(values, xy[:, 1], 1)
        assert np.abs(np.polyval(fit, values) - xy[:, 1]).max() <= 0.06
    legend = page.locator(f"{COMPARATOR} svg text").all_text_contents()
    assert "measured mean, gauge 5" in legend
    assert model["parameter"] in legend

    page.get_by_role("button", name="Show the displayed values as text").click()
    text = page.locator(f"{COMPARATOR} textarea").input_value()
    rows = [line.split("\t") for line in text.splitlines() if not line.startswith("#")]
    assert rows[0] == ["time (s)", "measured", "model", "residual"]
    for row, t, y, f, r in zip(
        rows[1:], flume_embedded["time"], flume_embedded["measured"],
        model["values"], model["residual"], strict=True,
    ):  # fmt: skip
        assert [float(v) for v in row] == [t, y, f, r]
    assert f"# model: {model['parameter']}" in text
    assert "# residual: model minus measured" in text


def test_the_flume_data_agree_with_a_fresh_run_of_pbc(flume_embedded: dict):
    # No skip for a result restored from the base: the flume series are
    # averages, Fourier phases and closed-form dispersion, with no fit, so
    # another platform differs far below the rounding of the page (unlike
    # the fit of issue 268), and the comparison holds for every run.
    from pbc.waves.experiments import wave_flume_lab

    fresh = wave_flume_lab.run().widget("gauge-five")
    assert flume_embedded["time"] == pytest.approx(fresh["time"], abs=1e-5)
    assert flume_embedded["measured"] == pytest.approx(fresh["measured"], abs=1e-5)
    for shown, reference in zip(flume_embedded["models"], fresh["models"], strict=True):
        assert shown["parameter"] == reference["parameter"]
        assert shown["values"] == pytest.approx(reference["values"], abs=1e-5)
        for key, value in reference["metrics"].items():
            assert shown["metrics"][key] == pytest.approx(value, abs=2e-3)


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_the_flume_comparator_passes_the_accessibility_scan(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    load_flume(page, server)
    results = Axe().run(page, options={"runOnly": {"type": "tag", "values": WCAG_TAGS}})
    assert results.violations_count == 0, results.generate_report()
    context.close()
