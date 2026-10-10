"""Checks on the built formal proofs lesson (architecture, "Formal proof
lesson"): the proofs are shown by reference and highlighted when the site is
built, the page states what compiled them, and its links point at the built
commit.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

import pytest
from playwright.sync_api import Browser, Page
from support import site_checks
from support.paths import LEAN_PROJECT, REPO_ROOT, SITE_SOURCE
from support.site_server import SiteServer, configured_repository_url

KINEMATICS = "PhysicsByConstruction.Mechanics.Kinematics"
EULER = "PhysicsByConstruction.Mechanics.EulerOscillator"
COLLISION = "PhysicsByConstruction.Mechanics.Collision"
SYMPLECTIC = "PhysicsByConstruction.Mechanics.SymplecticEuler"


@dataclass(frozen=True)
class LeanLesson:
    """A lesson of the lean strand: its page, the modules it shows, the
    regions it displays, and the hypotheses its assumptions section names."""

    title: str
    page: str
    modules: tuple[str, ...]
    regions: frozenset[str]
    hypotheses: tuple[str, ...]
    min_theorems: int = 2


LESSONS = {
    "L1": LeanLesson(
        "Proving what the simulation showed",
        "lessons/lean/01-proving-what-the-simulation-showed/index.html",
        (KINEMATICS, EULER),
        frozenset(
            {
                f"{KINEMATICS}:velocity_sq_of_constant_acceleration",
                f"{KINEMATICS}:displacement_of_mean_velocity",
                f"{EULER}:springEnergy",
                f"{EULER}:euler_energy_step",
                f"{EULER}:euler_energy_grows",
                f"{EULER}:euler_energy_after_steps",
            }
        ),
        ("hx", "hv", "hnewton", "hm", "hk", "hx'", "hv'", "hdt", "hE"),
        min_theorems=5,
    ),
    "L2": LeanLesson(
        "Momentum in a collision, proved",
        "lessons/lean/02-momentum-in-a-collision-proved/index.html",
        (COLLISION,),
        frozenset(
            {
                f"{COLLISION}:collision_rule",
                f"{COLLISION}:collision_momentum",
                f"{COLLISION}:collision_impulses",
            }
        ),
        ("hm₁", "hm₂"),
    ),
    "L3": LeanLesson(
        "What symplectic Euler conserves",
        "lessons/lean/03-what-symplectic-euler-conserves/index.html",
        (SYMPLECTIC,),
        frozenset(
            {
                f"{SYMPLECTIC}:modifiedEnergy",
                f"{SYMPLECTIC}:symplectic_modified_energy_step",
                f"{SYMPLECTIC}:symplectic_modified_energy_after_steps",
                f"{SYMPLECTIC}:modified_energy_nonneg",
            }
        ),
        ("hnewton", "hm", "hk", "hdt", "hx'", "hv'"),
    ),
}


@pytest.fixture(params=LESSONS.values(), ids=LESSONS.keys())
def spec(request) -> LeanLesson:
    return request.param


@pytest.fixture
def page_without_scripts(browser: Browser) -> Page:
    context = browser.new_context(
        viewport=site_checks.DESKTOP, java_script_enabled=False
    )
    yield context.new_page()
    context.close()


@pytest.fixture
def lesson(page_without_scripts: Page, server: SiteServer, spec: LeanLesson) -> Page:
    """The lesson page, opened with JavaScript off: everything below has to be
    in the page the build wrote."""
    page_without_scripts.goto(server.url + spec.page, wait_until="load")
    return page_without_scripts


def _head_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_the_lesson_is_in_the_lean_strand(site_dir: Path, spec: LeanLesson):
    assert (site_dir / spec.page).is_file()
    path = (site_dir / "path" / "index.html").read_text(encoding="utf-8")
    assert spec.title in path


def test_every_theorem_is_shown_by_reference(
    browser: Browser, server: SiteServer, spec: LeanLesson
):
    shown = set(site_checks.excerpt_sources(browser, server, spec.page))

    assert shown >= spec.regions


def test_lean_code_is_coloured_when_the_site_is_built(lesson: Page, spec: LeanLesson):
    # The page is open with JavaScript off, so the spans were written by the
    # build. A listing that was not highlighted would be one text node.
    for listing in lesson.locator(".lean-excerpt pre code").all():
        assert listing.locator("span.kw").count() >= 1, listing.inner_text()[:60]
    theorem = lesson.locator(".lean-excerpt pre code span.kw", has_text="theorem")
    assert theorem.count() >= spec.min_theorems
    assert lesson.locator(".lean-excerpt pre code span.co").count() >= 1
    # The tactics of a proof are told apart from its terms.
    assert lesson.locator(".lean-excerpt pre code span.fu", has_text="ring").count()


def test_the_page_states_what_compiled_the_proofs(lesson: Page):
    evidence = lesson.locator(".lean-evidence")
    assert evidence.count() == 1
    text = " ".join(evidence.text_content().split())

    toolchain = (LEAN_PROJECT / "lean-toolchain").read_text().strip()
    version = toolchain.rsplit(":v", 1)[1]
    manifest = json.loads((LEAN_PROJECT / "lake-manifest.json").read_text())
    mathlib = next(p for p in manifest["packages"] if p["name"] == "mathlib")
    assert _head_commit() in text
    assert f"Lean {version}" in text
    assert f"Mathlib {mathlib['inputRev']}" in text
    assert mathlib["rev"][:10] in text
    assert "sorry" in text and "CI runs the same check" in text


def test_the_page_says_which_source_is_authoritative(lesson: Page):
    text = " ".join(lesson.locator(".lean-evidence").text_content().split())

    assert (
        "repository at that commit and the result of the CI run are authoritative"
        in text
    )
    assert "web editor is a convenience" in text
    assert "its own version of Mathlib" in text


def test_links_point_at_the_built_commit_and_open_the_proofs(
    lesson: Page, spec: LeanLesson
):
    repository = configured_repository_url(SITE_SOURCE)
    sha = _head_commit()
    links = {
        link.get_attribute("href"): link.text_content()
        for link in lesson.locator(".lean-evidence a").all()
    }

    for module in spec.modules:
        path = f"lean/{module.replace('.', '/')}.lean"
        assert f"{repository}/blob/{sha}/{path}" in links
        editor = [
            href for href in links if href.startswith("https://live.lean-lang.org/")
        ]
        loaded = [
            unquote(href.split("#url=", 1)[1]) for href in editor if "#url=" in href
        ]
        raw = repository.replace("github.com", "raw.githubusercontent.com")
        assert f"{raw}/{sha}/{path}" in loaded
    assert len(editor) == len(spec.modules)
    assert all("Lean web editor" in links[href] for href in editor)


def test_each_listing_links_to_its_lines_at_the_built_commit(lesson: Page):
    repository = configured_repository_url(SITE_SOURCE)
    sha = _head_commit()
    for source in lesson.locator(".lean-excerpt").all():
        link = source.locator(".excerpt-source a").get_attribute("href")
        match = re.fullmatch(
            rf"{re.escape(repository)}/blob/{sha}/(lean/\S+\.lean)#L(\d+)-L(\d+)", link
        )
        assert match, link
        lines = (REPO_ROOT / match.group(1)).read_text().splitlines()
        first, last = int(match.group(2)), int(match.group(3))
        shown = source.locator("pre code").text_content().strip("\n")
        assert shown == "\n".join(lines[first - 1 : last])


def test_every_assumption_of_a_theorem_is_a_hypothesis_on_the_page(
    lesson: Page, spec: LeanLesson
):
    # The assumptions section names the hypotheses that carry the physics, and
    # each name appears in a listing next to it.
    assumptions = lesson.locator("#assumptions").inner_text()
    listings = " ".join(lesson.locator(".lean-excerpt pre code").all_inner_texts())
    for hypothesis in spec.hypotheses:
        assert hypothesis in assumptions, hypothesis
        assert re.search(rf"\({re.escape(hypothesis)} :", listings), hypothesis
    assert "axiom" in assumptions
