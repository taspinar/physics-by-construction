"""Required checks on the clip viewer of the lesson "Measurement quality and
multimodal observations" (F142, acceptance criterion 3 of Issue #570;
docs/authoring.md, "Widgets" and "On-demand data").

The viewer loads the generated clips after a button press, so the checks cover
what the page does without the press (the static frames, nothing requested),
what it does after (the frames one at a time, by keyboard), that what it shows
is the file as the build wrote it, and that the file's frames show the
simulated needle: the observed-value test.
"""

import base64
import json
import math
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from axe_playwright_python.sync_playwright import Axe
from PIL import Image
from playwright.sync_api import Browser, Page
from support import site_checks
from support.site_checks import DESKTOP, PHONE, WCAG_TAGS
from support.site_server import SiteServer

from pbc.electromagnetism import needle as compass

LESSON = "lessons/electromagnetism/11-measurement-quality/index.html"
SOURCE = "site/lessons/electromagnetism/11-measurement-quality"
DATA = (
    "lessons/electromagnetism/11-measurement-quality/"
    "index_files/figure-html/needle-clips.json"
)
VIEWER = "#needle-clips"
LOAD = f"{VIEWER} button[data-loads-ondemand]"
PREFIX = "data:image/png;base64,"


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
    page.locator(f"{VIEWER}.widget-active").wait_for()


def shown(page: Page, quantity: str) -> str:
    return page.locator(f'{VIEWER} output[data-quantity="{quantity}"]').inner_text()


def frame_src(page: Page) -> str:
    return page.locator(f"{VIEWER} img[data-frame]").get_attribute("src")


# --- Without the action -------------------------------------------------------------


def test_without_javascript_the_lesson_shows_the_static_frames(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + LESSON, wait_until="load")
    figure = page.locator(f"{VIEWER} img")
    assert figure.count() == 1
    assert figure.evaluate("image => image.complete && image.naturalWidth > 0")
    assert figure.get_attribute("alt")
    assert page.locator(f"{VIEWER} :is(input, [data-loads-ondemand])").count() == 0
    assert "generated frames" in page.locator(f"{VIEWER} .widget-controls").inner_text()
    context.close()


def test_with_scripts_the_page_offers_the_clips_and_requests_none_of_them(
    page: Page, server: SiteServer
):
    requested: list[str] = []
    page.on("request", lambda request: requested.append(request.url))
    page.goto(server.url + LESSON, wait_until="networkidle")
    assert page.locator(LOAD).inner_text() == "Load the two clips"
    assert page.locator(f"{VIEWER} img").count() == 1
    assert not [url for url in requested if url.endswith("needle-clips.json")]


def test_a_failed_load_leaves_the_frames_and_says_so(page: Page, server: SiteServer):
    page.route("**/needle-clips.json", lambda route: route.abort())
    page.goto(server.url + LESSON, wait_until="networkidle")
    page.locator(LOAD).click()
    status = page.locator(f"{VIEWER} [role=status]")
    status.filter(has_text="could not be loaded").wait_for()
    assert page.locator(f"{VIEWER} img").count() == 1
    assert page.locator(LOAD).is_enabled()


# --- After the action ---------------------------------------------------------


def test_the_viewer_opens_on_the_first_frame_of_the_first_clip(
    page: Page, server: SiteServer, embedded: dict
):
    load(page, server)
    first = embedded["clips"][0]
    assert frame_src(page) == first["frames"][0]["src"]
    assert shown(page, "clip") == first["title"]
    assert shown(page, "frame") == f"1 of {len(first['frames'])}"
    assert shown(page, "time") == "0.000"
    assert embedded["label"] in page.locator(VIEWER).inner_text()


def test_every_frame_of_every_clip_is_shown_as_the_file_holds_it(
    page: Page, server: SiteServer, embedded: dict
):
    """With the keyboard alone: the radio buttons choose the clip, the slider
    steps through its frames, and each frame is the file's, at its time."""
    load(page, server)
    for clip in embedded["clips"]:
        page.get_by_label(clip["title"], exact=True).check()
        slider = page.locator(f"{VIEWER} input[type=range]")
        slider.focus()
        page.keyboard.press("Home")
        for index, frame in enumerate(clip["frames"]):
            if index:
                page.keyboard.press("ArrowRight")
            assert frame_src(page) == frame["src"]
            assert shown(page, "time") == f"{frame['t']:.3f}"
            assert shown(page, "frame") == f"{index + 1} of {len(clip['frames'])}"
        assert shown(page, "frame-rate") == f"{clip['frame_rate']:g}"


def test_the_buttons_step_one_frame_and_stop_at_the_ends(
    page: Page, server: SiteServer, embedded: dict
):
    load(page, server)
    previous = page.locator(f"{VIEWER} button", has_text="Previous frame")
    following = page.locator(f"{VIEWER} button", has_text="Next frame")
    assert previous.is_disabled()
    following.focus()
    page.keyboard.press("Enter")
    assert frame_src(page) == embedded["clips"][0]["frames"][1]["src"]
    page.locator(f"{VIEWER} input[type=range]").focus()
    page.keyboard.press("End")
    assert following.is_disabled() and previous.is_enabled()


def test_the_frame_has_a_text_alternative_and_keeps_the_box_of_the_figure(
    page: Page, server: SiteServer
):
    page.goto(server.url + LESSON, wait_until="networkidle")
    box = page.locator(f"{VIEWER} img").bounding_box()
    page.locator(LOAD).click()
    page.locator(f"{VIEWER}.widget-active").wait_for()
    frame = page.locator(f"{VIEWER} img[data-frame]")
    assert "frame 1 of" in frame.get_attribute("alt")
    described = frame.get_attribute("aria-describedby")
    assert page.locator(f"#{described}").inner_text().strip()
    after = frame.bounding_box()
    assert abs(after["width"] - box["width"]) < 1.0
    assert abs(after["height"] - box["height"]) < 1.0


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
            page.locator(f"{VIEWER}.widget-active").wait_for()
        results = Axe().run(
            page, options={"runOnly": {"type": "tag", "values": WCAG_TAGS}}
        )
        assert results.violations_count == 0, f"{state}: {results.generate_report()}"
    context.close()


def test_with_reduced_motion_nothing_in_the_viewer_moves(
    browser: Browser, server: SiteServer, embedded: dict
):
    """The viewer never plays a clip: without input the frame stays, and
    nothing in it animates."""
    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce")
    page = context.new_page()
    load(page, server)
    before = frame_src(page)
    page.wait_for_timeout(1000)
    assert frame_src(page) == before
    animations = page.evaluate(
        f"document.querySelector('{VIEWER}').getAnimations({{subtree: true}}).length"
    )
    context.close()
    assert animations == 0


# --- The file against the simulation --------------------------------------------


def test_the_on_demand_file_is_labelled_generated_and_within_the_budget(
    site_dir: Path, embedded: dict
):
    assert LESSON in site_checks.ondemand_files(site_dir)
    assert (site_dir / DATA).stat().st_size < site_checks.ONDEMAND_BUDGET / 10
    assert embedded["schema"] == "clip-frames-1"
    assert "Generated" in embedded["label"]


def test_the_frames_of_the_file_show_the_simulated_needle(
    site_dir: Path, embedded: dict
):
    """The observed-value test: the needle found in every frame of the file is
    at the angle the simulation gives for the frame's time."""
    try:
        reason = site_checks.inherited(site_dir, SOURCE)
    except site_checks.SelectionError as error:
        pytest.fail(f"whether this run executed the lesson is unknown: {error}")
    if reason is not None:
        pytest.skip(reason)
    needle = compass.Needle()
    for clip in embedded["clips"]:
        times = np.array([frame["t"] for frame in clip["frames"]])
        np.testing.assert_allclose(np.diff(times), 1.0 / clip["frame_rate"], atol=1e-6)
        truth = compass.simulate(needle, times)
        for frame, angle in zip(clip["frames"], truth, strict=True):
            assert frame["src"].startswith(PREFIX)
            pixels = np.asarray(
                Image.open(BytesIO(base64.b64decode(frame["src"][len(PREFIX) :])))
            )
            assert pixels.shape == (clip["height"], clip["width"])
            found = compass.track_angle(pixels)
            assert abs(found - angle) < math.radians(0.05)
