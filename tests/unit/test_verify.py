"""The worked examples of "How we verify the science" (F134): each resolves to
a claim of a published lesson and to evidence of the kind it names, and every
missing target raises, which fails the build of the page."""

from dataclasses import replace

import pytest
from support.paths import REPO_ROOT, SITE_SOURCE

from pbc.authoring.evidence import Evidence, markdown_text
from pbc.authoring.path import LearningPath
from pbc.authoring.verify import (
    EXAMPLES,
    VERIFY_PAGE,
    Example,
    VerifyPage,
    resolve,
    verify_page,
)

PATH = LearningPath.read(SITE_SOURCE)


@pytest.fixture(scope="module")
def page():
    return verify_page(site=SITE_SOURCE)


def test_the_three_examples_are_a_cell_a_card_and_a_theorem(page):
    assert [e.kind for e in EXAMPLES] == ["cell", "card", "theorem"]
    assert [e.type for e in EXAMPLES] == [
        "numerically-verified",
        "experimentally-supported",
        "formal-theorem",
    ]
    for worked in page.examples:
        assert worked.claim.type == worked.example.type
        assert worked.example.evidence in worked.claim.evidence
        kinds = {s.name: s.kind for s in worked.sources}
        assert kinds[worked.example.evidence] == worked.example.kind
        assert worked.lesson.page == worked.claim.page


def test_each_example_links_its_claim_its_evidence_and_its_row(page):
    text = str(page)
    evidence = Evidence(REPO_ROOT, VERIFY_PAGE, SITE_SOURCE)
    for worked in page.examples:
        lesson = worked.lesson.page.removesuffix(".qmd") + ".html"
        assert f"({lesson}#{worked.claim.anchor})" in text
        assert f"(evidence.html#{worked.claim.row})" in text
        for word in worked.claim.evidence:
            assert f"({evidence.resolve(worked.claim.page, word).href})" in text
    assert "```lean\ntheorem euler_energy_step" in text
    assert "CC-BY-4.0" in text  # the dataset card's licence


@pytest.mark.parametrize(
    "example",
    [
        Example("numerically-verified", "no-such-lesson", "x", "cell"),
        Example("formal-theorem", "harmonic-oscillator", "euler-energy-ratios", "cell"),
        Example("numerically-verified", "harmonic-oscillator", "no-such-cell", "cell"),
        Example(
            "numerically-verified", "harmonic-oscillator", "euler-energy-ratios", "card"
        ),
    ],
    ids=["lesson", "type", "word", "kind"],
)
def test_a_missing_target_raises(example):
    with pytest.raises(ValueError, match="the example"):
        verify_page((example,), site=SITE_SOURCE)


def test_evidence_that_names_nothing_raises(tmp_path):
    # A copy of the lesson whose claim names a word that no longer exists.
    example = EXAMPLES[0]
    lesson = PATH.lesson(example.lesson)
    target = tmp_path / lesson.page
    target.parent.mkdir(parents=True)
    text = (SITE_SOURCE / lesson.page).read_text(encoding="utf-8")
    target.write_text(
        text.replace(
            f'evidence="{example.evidence}"', f'evidence="{example.evidence} gone"'
        ),
        encoding="utf-8",
    )
    evidence = Evidence(REPO_ROOT, VERIFY_PAGE, tmp_path)
    with pytest.raises(ValueError, match="'gone' names nothing"):
        resolve(example, PATH, evidence, tmp_path)


def test_the_scope_is_escaped_as_the_evidence_map_escapes_it(page):
    """A scope with Markdown's special characters reads the same here as in
    the Evidence map, which escapes it with markdown_text."""
    worked = page.examples[0]
    scope = "a *step* of h_0 [one] <period>"
    claim = replace(worked.claim, scope=scope)
    text = VerifyPage((), page.root).example(replace(worked, claim=claim))
    assert f"Scope: {markdown_text(scope)}." in text
    assert "&lt;" not in text
