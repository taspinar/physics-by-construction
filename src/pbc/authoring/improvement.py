"""Suggest an improvement: links to the issue forms, with the page pre-filled.

Every lesson ends with one line of three links (F135): a scientific
correction, a problem report, and a proposed change, each to the matching
form of ``.github/ISSUE_TEMPLATE/``. GitHub fills a field of an issue form
from the query parameter named by the field's ``id``, so each form has a
field with the id ``page``, and the link carries the lesson's address in it.
The visitor needs a GitHub account, and the issue is public; nothing is sent
from the page itself (no script, no request, no storage).
"""

from collections.abc import Sequence
from typing import NamedTuple
from urllib.parse import urlencode

TEMPLATE_DIRECTORY = ".github/ISSUE_TEMPLATE"
# The id of the field of each form that names the page.
PAGE_FIELD = "page"
LABEL = "Suggest an improvement"


class Form(NamedTuple):
    name: str  # the file name of the form, without ``.yml``
    title: str  # the link text
    what: str  # what the form is for


# The three choices of a lesson's last line, in their order.
FORMS = (
    Form(
        "scientific-correction",
        "Scientific correction",
        "a wrong statement, number, or derivation",
    ),
    Form(
        "bug",
        "Report a problem",
        "a listing that does not run, a broken link or figure, or another"
        " fault of a page",
    ),
    Form("feature", "Propose a change", "an improvement to a page or the site"),
)


def form_url(repository: str, name: str, page: str = "") -> str:
    """The address of the issue form ``name`` of ``repository``, with the
    field ``page`` filled in with ``page`` when it is given."""
    query = {"template": f"{name}.yml"}
    if page:
        query[PAGE_FIELD] = page
    return f"{repository}/issues/new?{urlencode(query)}"


def suggestion(repository: str, page: str, forms: Sequence[Form] = FORMS) -> str:
    """The Markdown of the last line of a lesson: the three links, each with
    the lesson's address ``page`` filled in."""
    links = " · ".join(
        f"[{form.title.lower()}]({form_url(repository, form.name, page)})"
        for form in forms
    )
    return f"{LABEL}: {links}."
