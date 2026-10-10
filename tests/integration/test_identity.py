"""Open-source identity and attribution (F57): one source for the wording,
the surfaces that carry it, the citation metadata, and the Issue forms.

``support/data/cff-1.2.0-schema.json`` is the schema of the Citation File
Format 1.2.0 (https://github.com/citation-file-format/citation-file-format,
CC BY 4.0), vendored so that the test needs no network.
"""

import json
import re

import jsonschema
import yaml
from support.paths import REPO_ROOT, SITE_SOURCE

from pbc.authoring import identity

CITATION = REPO_ROOT / "CITATION.cff"
SCHEMA = REPO_ROOT / "tests" / "support" / "data" / "cff-1.2.0-schema.json"
FORMS = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
CANONICAL = (
    "Physics by Construction is a free, open-source educational initiative by "
    "JIDAI, created by Ahmet Taspinar."
)


def _citation() -> dict:
    return yaml.safe_load(CITATION.read_text(encoding="utf-8"))


def test_the_source_yields_the_sentence_and_the_line_without_its_subject():
    assert identity.description() == CANONICAL
    assert identity.footer_line() == (
        "An open-source educational initiative by JIDAI, created by Ahmet Taspinar"
    )
    assert identity.footer_html().count("<a ") == 1
    assert 'href="https://jidai.nl"' in identity.footer_html()


def test_readme_and_citation_carry_the_sentence_verbatim():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(
        re.escape(identity.README_START) + r"\n(.*)\n" + re.escape(identity.README_END),
        readme,
    )
    assert block is not None and block.group(1) == identity.description()
    assert _citation()["abstract"] == identity.description()
    # The sync tool agrees: nothing is stale.
    assert identity.main(["--check"]) == 0


def test_the_footer_token_is_the_only_footer_attribution_in_the_site_source():
    config = (SITE_SOURCE / "_quarto.yml").read_text(encoding="utf-8")
    assert "PBC-ATTRIBUTION" in config
    for source in SITE_SOURCE.rglob("*.qmd"):
        assert identity.footer_line() not in source.read_text(encoding="utf-8")


def test_citation_validates_against_the_cff_schema_and_has_no_doi():
    citation = _citation()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(citation)
    assert "doi" not in citation
    assert all("doi" not in entry for entry in citation.get("identifiers", []))
    assert "version" not in citation  # the release tag decides it, once it exists
    assert citation["authors"] == [{"family-names": "Taspinar", "given-names": "Ahmet"}]
    assert citation["license"] == "MIT"
    assert "CC BY 4.0" in citation["message"]
    assert citation["repository-code"].endswith("/taspinar/physics-by-construction")
    assert citation["url"].startswith("https://taspinar.github.io/")


def _required(form: str) -> set[str]:
    body = yaml.safe_load((FORMS / form).read_text(encoding="utf-8"))["body"]
    return {
        item["attributes"]["label"]
        for item in body
        if item.get("validations", {}).get("required")
    }


def test_the_five_issue_forms_open_with_their_required_fields():
    expected = {
        "scientific-correction.yml": {
            "Page",
            "The statement",
            "The correction",
            "Source and its licence",
            "Evidence",
        },
        "dataset-suggestion.yml": {
            "Source URL or DOI",
            "Creator",
            "Licence",
            "Measurement type",
            "Size",
            "What a lesson could learn from it",
        },
    }
    for form, labels in expected.items():
        assert labels <= _required(form), form
    for form in ("bug.yml", "feature.yml", "lesson-proposal.yml"):
        assert _required(form), form
    for form in (*expected, "bug.yml", "feature.yml", "lesson-proposal.yml"):
        data = yaml.safe_load((FORMS / form).read_text(encoding="utf-8"))
        assert {"name", "description", "body"} <= data.keys(), form
        # No form collects contact details.
        assert not re.search(r"e-?mail|phone", json.dumps(data["body"]), re.I), form


def test_contribution_guides_name_the_new_forms_without_contacting_anyone():
    for path in (
        REPO_ROOT / "CONTRIBUTING.md",
        SITE_SOURCE / "contribute.qmd",
    ):
        text = path.read_text(encoding="utf-8")
        for name in ("Scientific correction", "Dataset suggestion"):
            assert name in text, (path.name, name)
        assert "contact JIDAI" in text, path.name
        assert "independent review" in text, path.name
