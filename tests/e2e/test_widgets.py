"""Required checks on the interactive widgets of the built site
(architecture, "Widgets" and invariant I4; docs/authoring.md, "Widgets").

The widget in the numerical-integrators lesson is the first one. The checks
that hold for every widget (no other origin, no storage, readable without
scripts, the accessibility scan) also run on every page in test_built_site.py;
the checks here drive the widget itself.
"""

from pathlib import Path

import numpy as np
import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, Page
from support import site_checks
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP, PHONE, WCAG_TAGS, describe
from support.site_server import SiteServer

from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.explorer import STEPS_PER_PERIOD
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import energy, harmonic_motion, spring

LESSON = "lessons/mechanics/05-numerical-integrators/index.html"
WIDGET = "#integrator-explorer"

# Tolerances for the numbers the widget displays against a fresh run of the
# integrators of src/pbc. The energy is displayed with four significant
# digits (relative rounding at most 5e-4), the error with three (5e-3 at the
# worst), the evaluation count exactly.
ENERGY_TOLERANCE = 1e-3
ERROR_TOLERANCE = 1e-2

MASS, SPRING_CONSTANT, N_PERIODS = 0.5, 2.0, 5


@pytest.fixture
def page(browser: Browser):
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


def open_widget(page: Page, server: SiteServer) -> None:
    page.goto(server.url + LESSON, wait_until="networkidle")
    page.locator(f"{WIDGET}.widget-active").wait_for()


def reference(integrator, steps_per_period: int) -> dict[str, float]:
    """The numbers the widget displays, from a fresh run with pbc."""
    omega = np.sqrt(SPRING_CONSTANT / MASS)
    period = 2 * np.pi / omega
    released = State(t=0.0, x=1.0, v=0.0)
    calls = []

    def acceleration(t, x, v):
        calls.append(1)
        return newton(MASS, spring(SPRING_CONSTANT))(t, x, v)

    trajectory = simulate(
        released,
        acceleration,
        period / steps_per_period,
        steps_per_period * N_PERIODS,
        step=integrator.step,
    )
    exact = harmonic_motion(released, MASS, SPRING_CONSTANT, trajectory.t)
    e = energy(trajectory, MASS, SPRING_CONSTANT)
    return {
        "energy-ratio": float(e[-1] / e[0]),
        "max-error": float(np.max(np.abs(trajectory.x - exact.x))),
        "calls": len(calls),
        "omega-dt": float(omega * period / steps_per_period),
    }


def displayed(page: Page) -> dict[str, float]:
    return {
        quantity: float(
            page.locator(f'{WIDGET} output[data-quantity="{quantity}"]').inner_text()
        )
        for quantity in ("energy-ratio", "max-error", "calls", "omega-dt")
    }


def choose(page: Page, name: str, steps_per_period: int) -> None:
    """Select the integrator and the step count with the keyboard only."""
    page.get_by_label(name, exact=True).check()
    slider = page.locator(f"{WIDGET} input[type=range]")
    slider.focus()
    page.keyboard.press("Home")
    for _ in range(STEPS_PER_PERIOD.index(steps_per_period)):
        page.keyboard.press("ArrowRight")


# --- Without JavaScript --------------------------------------------------------


def test_without_javascript_the_lesson_shows_the_static_figure_and_the_table(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + LESSON, wait_until="load")

    figure = page.locator(f"{WIDGET} img")
    assert figure.count() == 1
    assert figure.evaluate("image => image.complete && image.naturalWidth > 0")
    assert figure.get_attribute("alt")
    assert page.locator(f"{WIDGET} figcaption").inner_text().strip()
    # No control is shown, and nothing is left that does nothing.
    assert page.locator(f"{WIDGET} :is(input, button, select, svg)").count() == 0
    # The numbers of every setting are in the page as text.
    tables = " ".join(
        page.locator("main table.result-table caption").all_text_contents()
    )
    assert "Energy after five periods relative to the initial energy" in tables
    assert "Evaluations of the acceleration" in tables
    context.close()


def test_the_site_check_for_content_only_with_scripts_covers_the_widget(
    site_dir: Path,
):
    # The check visits every page that html_pages lists, and test_built_site
    # runs it over the whole site once; the lesson being listed is what covers
    # the widget. A second run of the check here would cost half a minute.
    assert site_dir / LESSON in site_checks.html_pages(site_dir)


# --- With JavaScript -----------------------------------------------------------


def test_the_widget_responds_to_its_controls(page: Page, server: SiteServer):
    open_widget(page, server)
    before = displayed(page)
    drawing = page.locator(f"{WIDGET} svg.widget-drawing").inner_html()

    choose(page, "symplectic Euler", 4)

    after = displayed(page)
    assert after["omega-dt"] > before["omega-dt"]
    assert after["calls"] == 4 * N_PERIODS * 1
    assert page.locator(f"{WIDGET} svg.widget-drawing").inner_html() != drawing


def test_the_widget_has_no_pointer_only_control(page: Page, server: SiteServer):
    open_widget(page, server)
    for control in page.locator(f"{WIDGET} :is(input, select, button)").all():
        # Native controls are in the tab order and take keyboard input.
        assert control.evaluate("element => element.tabIndex") >= 0


def test_the_widget_is_reachable_and_operable_with_the_keyboard_alone(
    page: Page, server: SiteServer
):
    open_widget(page, server)
    page.locator(f"{WIDGET} input[type=radio]:checked").focus()

    # Arrow keys move through the radio group and select; Tab moves on.
    page.keyboard.press("ArrowDown")
    selected = page.locator(f"{WIDGET} input[type=radio]:checked").get_attribute(
        "value"
    )
    assert selected == "1"
    assert page.evaluate("document.activeElement.type") == "radio"
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.type") == "range"
    steps = page.locator(f"{WIDGET} output[data-quantity=steps-per-period]")
    before = steps.inner_text()
    page.keyboard.press("ArrowRight")
    assert steps.inner_text() != before
    assert page.locator(f"{WIDGET} input[type=range]").get_attribute(
        "aria-valuetext"
    ) == (f"{steps.inner_text()} steps per period")


def test_a_focused_control_has_a_visible_focus_indicator(
    page: Page, server: SiteServer
):
    open_widget(page, server)
    page.locator(f"{WIDGET} input[type=range]").focus()

    outline = page.locator(f"{WIDGET} input[type=range]").evaluate(
        "element => getComputedStyle(element).outlineStyle + ' '"
        " + getComputedStyle(element).outlineWidth"
    )
    assert outline.startswith("solid") and not outline.endswith(" 0px")


def test_the_drawing_has_a_text_alternative_in_the_page(page: Page, server: SiteServer):
    open_widget(page, server)
    drawing = page.locator(f"{WIDGET} svg.widget-drawing")

    assert drawing.get_attribute("role") == "img"
    assert drawing.get_attribute("aria-label")
    described_by = drawing.get_attribute("aria-describedby")
    assert described_by and page.locator(f"#{described_by}").inner_text().strip()


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_the_accessibility_scan_passes_in_several_states_of_the_widget(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    open_widget(page, server)
    options = {
        "runOnly": {"type": "tag", "values": WCAG_TAGS},
        "resultTypes": ["violations"],
    }
    violations = []
    for name, steps in [
        ("explicit Euler", 16),
        ("velocity Verlet", 4),
        ("Runge-Kutta 4", 100),
    ]:
        choose(page, name, steps)
        results = Axe().run(page, options=options)
        violations += [
            f"{finding['id']} at {node['target']} ({name}, {steps})"
            for finding in results.response["violations"]
            for node in finding["nodes"]
        ]
    context.close()
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("integrator", INTEGRATORS, ids=lambda i: i.name)
@pytest.mark.parametrize("steps_per_period", STEPS_PER_PERIOD)
def test_displayed_values_agree_with_a_fresh_run_of_pbc(
    page: Page, server: SiteServer, integrator, steps_per_period: int
):
    open_widget(page, server)

    choose(page, integrator.name, steps_per_period)

    shown, expected = displayed(page), reference(integrator, steps_per_period)
    assert shown["calls"] == expected["calls"]
    assert shown["omega-dt"] == pytest.approx(expected["omega-dt"], rel=1e-2)
    assert shown["energy-ratio"] == pytest.approx(
        expected["energy-ratio"], rel=ENERGY_TOLERANCE
    )
    assert shown["max-error"] == pytest.approx(
        expected["max-error"], rel=ERROR_TOLERANCE
    )


def test_the_displayed_values_are_the_ones_of_the_table_in_the_page(
    page: Page, server: SiteServer
):
    # The static table and the widget come from the same embedded runs.
    open_widget(page, server)
    energy_table = page.locator("main table.result-table").filter(
        has_text="Energy after five periods"
    )
    # The first row of the table is the coarsest step; one column per method.
    first_row = energy_table.locator("tbody tr").first.locator("td").all_text_contents()
    for column, integrator in enumerate(INTEGRATORS, start=1):
        choose(page, integrator.name, STEPS_PER_PERIOD[0])
        first = float(first_row[column])
        assert first == pytest.approx(
            displayed(page)["energy-ratio"], rel=ENERGY_TOLERANCE
        )


# --- Layout and motion ---------------------------------------------------------

# Runs before the scripts of the page and records the layout shifts.
_WATCH_LAYOUT = """
() => {
  window.__shift = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__shift += entry.value;
    }
  }).observe({type: "layout-shift", buffered: true});
}
"""

# Served in place of the widget module: it loads the real module (the same
# URL, with a query the server ignores) when the test says so, after the page
# has loaded and settled as it does for a reader.
_HELD_MODULE = """
window.__startWidget = () => import(`${import.meta.url}?now`);
"""

# The boxes that must not move when the widget loads: the figure (the image,
# or the drawing that replaces it), its caption, the slot of the controls, the
# content after the widget; and the height of the page.
_BOXES = """
() => {
  const root = document.querySelector("#integrator-explorer");
  const box = (element) => {
    const b = element.getBoundingClientRect();
    return [b.x, b.y, b.width, b.height];
  };
  return {
    figure: box(root.querySelector("img, svg.widget-drawing")),
    caption: box(root.querySelector("figcaption")),
    controls: box(root.querySelector(".widget-controls")),
    following: box(root.nextElementSibling),
    page: document.documentElement.scrollHeight,
  };
}
"""


def enhancement_in_view(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
) -> tuple[dict, dict, float]:
    """Loads the lesson with the widget held back, scrolls the widget into
    view, then starts it. Returns the boxes before and after, and the layout
    shift the browser scored in between."""
    context = browser.new_context(viewport=viewport)
    context.add_init_script(f"({_WATCH_LAYOUT})()")

    def hold(route, request):
        if request.url.endswith("?now"):
            route.continue_()
        else:
            route.fulfill(body=_HELD_MODULE, content_type="text/javascript")

    context.route("**/widgets/*.js*", hold)
    page = context.new_page()
    page.goto(server.url + LESSON, wait_until="networkidle")
    page.locator(WIDGET).evaluate("root => root.scrollIntoView({block: 'start'})")
    page.wait_for_timeout(500)
    page.evaluate("window.__shift = 0")
    before = page.evaluate(_BOXES)

    page.evaluate("window.__startWidget()")
    page.locator(f"{WIDGET}.widget-active").wait_for()
    page.wait_for_timeout(500)
    after = page.evaluate(_BOXES)
    shift = page.evaluate("window.__shift")
    context.close()
    return before, after, shift


@pytest.mark.parametrize(
    "viewport", [DESKTOP, site_checks.TABLET, PHONE], ids=["desktop", "tablet", "phone"]
)
def test_the_page_does_not_shift_when_the_widget_loads(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    # The widget starts while it is in view, where a move would count, after
    # the page has loaded and settled: nothing may move, and the browser
    # scores no shift.
    before, after, shift = enhancement_in_view(browser, server, viewport)

    assert after == before
    assert shift == 0


@pytest.mark.parametrize(
    "viewport", [DESKTOP, site_checks.TABLET, PHONE], ids=["desktop", "tablet", "phone"]
)
def test_the_space_of_the_controls_is_reserved_by_the_stylesheet(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + LESSON, wait_until="load")

    reserved = page.locator(f"{WIDGET} .widget-controls").bounding_box()["height"]

    context.close()
    with_script = browser.new_context(viewport=viewport)
    scripted = with_script.new_page()
    open_widget(scripted, server)
    needed = scripted.locator(f"{WIDGET} .widget-panel").bounding_box()["height"]
    with_script.close()
    assert reserved >= needed


def test_with_reduced_motion_nothing_in_the_widget_animates(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce")
    page = context.new_page()
    open_widget(page, server)
    choose(page, "Runge-Kutta 4", 8)

    animations = page.evaluate(
        f"document.querySelector('{WIDGET}').getAnimations({{subtree: true}}).length"
    )
    durations = page.locator(f"{WIDGET} *").evaluate_all(
        "elements => elements.map(e => getComputedStyle(e))"
        ".filter(s => s.animationName !== 'none'"
        " || parseFloat(s.transitionDuration) > 0).length"
    )

    preference = page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")

    context.close()
    assert preference, "the preference was not set"
    assert animations == 0 and durations == 0


# --- The built site ------------------------------------------------------------


def test_the_widget_scripts_make_no_request_and_use_no_storage(site_dir: Path):
    assert list((site_dir / site_checks.WIDGETS).glob("*.js")), "no widget was built"
    violations = site_checks.check_widget_sources(site_dir)
    assert not violations, describe(violations)


def test_operating_the_widget_writes_no_cookie_and_nothing_to_browser_storage(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_widgets_store_nothing(browser, server, site_dir)
    assert not violations, describe(violations)


def test_the_widget_check_has_a_widget_to_check(page: Page, server: SiteServer):
    # Guards the check above: without a declared enhancement it passes on nothing.
    page.goto(server.url + LESSON, wait_until="networkidle")
    assert page.locator("[data-enhancement] input").count() > 0


def test_the_widget_source_is_the_file_that_was_published(site_dir: Path):
    published = (site_dir / "widgets" / "integrator-explorer.js").read_bytes()
    assert (
        published == (SITE_SOURCE / "widgets" / "integrator-explorer.js").read_bytes()
    )
