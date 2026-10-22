"""The conceptual artwork of the home page's featured capstone (F124): drawn
by code, the same bytes on every build, with no text a reader could take for
data, and registered in the provenance register with its module."""

import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from support.paths import SITE_SOURCE

from pbc.authoring import home_artwork

SVG = "{http://www.w3.org/2000/svg}"


def test_the_artwork_is_the_same_on_every_build_and_well_formed():
    first, second = home_artwork.wavefront(), home_artwork.wavefront()
    assert first == second
    root = ET.fromstring(first)
    assert root.tag == f"{SVG}svg"
    assert root.get("viewBox") == f"0 0 {home_artwork.WIDTH} {home_artwork.HEIGHT}"


def test_the_artwork_carries_no_axis_label_or_number():
    root = ET.fromstring(home_artwork.wavefront())
    # The title names what it is; nothing else in it is text: no axis, scale,
    # legend, or measurement label.
    texts = [
        element for element in root.iter() if element.text and element.text.strip()
    ]
    assert [element.tag for element in texts] == [f"{SVG}title"]
    assert texts[0].text == home_artwork.ALT
    assert texts[0].text.startswith("Conceptual artwork")
    assert not any(character.isdigit() for character in home_artwork.ALT)
    assert not list(root.iter(f"{SVG}text"))


def test_the_fronts_are_at_equal_distances_from_the_source_line():
    root = ET.fromstring(home_artwork.wavefront())
    fronts = root.findall(f"{SVG}g/{SVG}path")
    assert len(fronts) == home_artwork.FRONTS
    for index, front in enumerate(fronts, start=1):
        radius = index * home_artwork.SPACING
        assert f" A{radius:g},{radius:g} " in front.get("d")
    opacities = [float(front.get("stroke-opacity")) for front in fronts]
    assert opacities == sorted(opacities, reverse=True)


def test_the_build_writes_the_artwork_into_the_assets_of_the_site(tmp_path: Path):
    path = home_artwork.write(tmp_path)
    assert path == tmp_path / "assets" / home_artwork.WAVEFRONT
    assert path.read_text(encoding="utf-8") == home_artwork.wavefront()


def test_the_register_names_the_module_and_the_build_runs_it():
    register = yaml.safe_load((SITE_SOURCE / "assets" / "provenance.yaml").read_text())
    assert register["assets"][home_artwork.WAVEFRONT] == {
        "module": home_artwork.__name__
    }
    config = (SITE_SOURCE / "_quarto.yml").read_text()
    assert "    - home-artwork.py\n" in config
    script = (SITE_SOURCE / "home-artwork.py").read_text()
    assert "from pbc.authoring.home_artwork import write" in script
