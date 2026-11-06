"""The "Suggest an improvement" links name real forms and real field ids.

GitHub fills a field of an issue form from the query parameter named by the
field's ``id`` (F135). CI cannot reach github.com, so what it can check is
that every generated link names a form of ``.github/ISSUE_TEMPLATE/`` and
only parameters that are ``id``s of a field of that form.
"""

import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import yaml

from pbc.authoring.educators import forms_list
from pbc.authoring.improvement import (
    FORMS,
    LABEL,
    PAGE_FIELD,
    TEMPLATE_DIRECTORY,
    form_url,
    suggestion,
)
from pbc.authoring.repository import BuildCommit, repository_url
from pbc.authoring.reproduce import Reproduction
from pbc.authoring.website import page_address

REPO_ROOT = Path(__file__).parents[2]
TEMPLATES = REPO_ROOT / TEMPLATE_DIRECTORY
REPOSITORY = "https://github.com/taspinar/physics-by-construction"
ADDRESS = (
    "https://taspinar.github.io/physics-by-construction/"
    "lessons/mechanics/01-x/index.html"
)
_LINK = re.compile(r"\]\(([^)\s]+)\)")


def field_ids(template: Path) -> set[str]:
    data = yaml.safe_load(template.read_text(encoding="utf-8"))
    return {str(field["id"]) for field in data["body"] if "id" in field}


def link_problems(url: str, templates: Path = TEMPLATES) -> list[str]:
    """What is wrong with a link to an issue form: a form that does not
    exist, or a parameter that is not the ``id`` of a field of the form."""
    parts = urlsplit(url)
    if not parts.path.endswith("/issues/new"):
        return [f"{url}: not a link to a new issue"]
    query = dict(parse_qsl(parts.query))
    template = templates / query.pop("template", "")
    if not template.is_file() or template.suffix != ".yml":
        return [f"{url}: no form {template.name!r}"]
    ids = field_ids(template)
    return [
        f"{url}: {name!r} is not the id of a field of {template.name}"
        for name in query
        if name not in ids
    ]


def links(markdown: str) -> list[str]:
    return _LINK.findall(markdown)


def test_every_link_of_a_lesson_names_a_form_and_its_field_ids():
    line = suggestion(REPOSITORY, ADDRESS)

    found = links(line)
    assert len(found) == len(FORMS) == 3
    for url in found:
        assert link_problems(url) == []
        assert dict(parse_qsl(urlsplit(url).query))[PAGE_FIELD] == ADDRESS


def test_the_check_fails_for_a_missing_form_or_an_unknown_parameter(tmp_path: Path):
    (tmp_path / "bug.yml").write_text(
        "name: Bug\ndescription: x\nbody:\n"
        "  - type: input\n    id: page\n    attributes:\n      label: Page\n"
        "  - type: textarea\n    attributes:\n      label: Current behavior\n"
    )

    assert link_problems(form_url(REPOSITORY, "bug", ADDRESS), tmp_path) == []
    missing = form_url(REPOSITORY, "nonexistent", ADDRESS)
    assert link_problems(missing, tmp_path) == [f"{missing}: no form 'nonexistent.yml'"]
    unknown = f"{REPOSITORY}/issues/new?template=bug.yml&where={ADDRESS}"
    assert link_problems(unknown, tmp_path) == [
        f"{unknown}: 'where' is not the id of a field of bug.yml"
    ]
    # A field without an id cannot be filled in from the link.
    no_id = f"{REPOSITORY}/issues/new?template=bug.yml&Current+behavior=x"
    assert len(link_problems(no_id, tmp_path)) == 1


def test_each_form_of_the_line_has_a_page_field_with_its_id():
    for form in FORMS:
        data = yaml.safe_load((TEMPLATES / f"{form.name}.yml").read_text())
        pages = [field for field in data["body"] if field.get("id") == PAGE_FIELD]
        assert len(pages) == 1, form.name
        assert pages[0]["type"] == "input"
        assert pages[0]["attributes"]["label"] == "Page"


def test_the_line_names_the_three_choices_and_encodes_the_address():
    line = suggestion(REPOSITORY, ADDRESS)

    assert line.startswith(f"{LABEL}: [scientific correction](")
    assert "[report a problem](" in line and "[propose a change](" in line
    # The address is one query value, encoded, so that GitHub reads it whole.
    assert "page=https%3A%2F%2Ftaspinar.github.io%2F" in line


def test_a_link_without_a_page_has_only_the_template():
    url = form_url(REPOSITORY, "bug")

    assert url == f"{REPOSITORY}/issues/new?template=bug.yml"


def test_the_contribute_list_has_the_three_forms_and_valid_links():
    listing = forms_list(FORMS)

    for form in FORMS:
        assert f"[{form.title}](" in listing and form.what in listing
    for url in links(listing):
        assert url.startswith(repository_url())
        assert link_problems(url) == []


def test_the_page_address_is_the_canonical_url_of_the_built_page(tmp_path: Path):
    page = "lessons/mechanics/01-x/index.qmd"
    (tmp_path / "_quarto.yml").write_text(
        "website:\n  site-url: https://example.org/pbc/\n"
    )

    assert page_address(tmp_path, page) == (
        "https://example.org/pbc/lessons/mechanics/01-x/index.html"
    )
    (tmp_path / "_quarto.yml").write_text("project:\n  type: website\n")
    assert page_address(tmp_path, page) == "lessons/mechanics/01-x/index.html"


def test_the_real_site_prefills_its_public_address():
    site = REPO_ROOT / "site"
    config = yaml.safe_load((site / "_quarto.yml").read_text())

    address = page_address(site, "lessons/mechanics/01-x/index.qmd")

    assert address.startswith(config["website"]["site-url"].rstrip("/") + "/")
    assert address.endswith("/lessons/mechanics/01-x/index.html")


def test_the_last_section_of_a_lesson_ends_with_the_prefilled_links(tmp_path: Path):
    """The post-render step builds the last section with the page's public
    address, and the links are its last line."""
    from pbc.authoring.context import markdown
    from pbc.authoring.repository import BuildCommit

    (tmp_path / "_quarto.yml").write_text(
        "website:\n  site-url: https://example.org/pbc/\n"
    )
    page = "lessons/mechanics/02-x/index.qmd"
    payload = {
        "page": f"site/{page}",
        "code": [],
        "tests": [],
        "experiment": "pbc.mechanics.experiments.kinematics",
        "kind": "run",
        "lean_modules": [],
        "live": "",
    }

    shown = markdown(
        "reproduce", page, payload, tmp_path, BuildCommit("0" * 40, False), REPOSITORY
    )

    last = shown.rstrip("\n").splitlines()[-4:]
    assert last == [
        "::: {.suggest-improvement}",
        suggestion(
            REPOSITORY, "https://example.org/pbc/lessons/mechanics/02-x/index.html"
        ),
        ":::",
        ":::",
    ]
    for url in links(last[1]):
        assert link_problems(url) == []


def _reproduction(address: str = "") -> Reproduction:
    return Reproduction(
        page="site/lessons/mechanics/01-x/index.qmd",
        code=(),
        tests=(),
        commit=BuildCommit(None, False),
        repository=REPOSITORY,
        experiment="pbc.mechanics.experiments.x",
        kind="run",
        address=address,
    )


def test_a_reproduction_without_an_address_names_the_page_in_the_site():
    # The fallback is the built page's path in the site, as page_address gives
    # it without a site-url, and never the repository path of the source (#364).
    reproduction = _reproduction()

    assert reproduction.page_address == "lessons/mechanics/01-x/index.html"
    line = reproduction.markdown()
    assert "page=lessons%2Fmechanics%2F01-x%2Findex.html" in line
    assert "index.qmd" not in line.split("suggest-improvement")[-1]


def test_a_reproduction_with_an_address_keeps_it():
    assert _reproduction(ADDRESS).page_address == ADDRESS
