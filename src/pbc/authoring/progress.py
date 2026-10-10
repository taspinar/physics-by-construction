"""What the pages hand to the learner-state script, and the export of the
learning path.

Learner state (docs/architecture.md, "Learner state") is kept in the
learner's browser by ``site/learner/progress.js`` and never leaves it. The
script needs two things from the build: which lesson a page is, and where the
explanation of what is stored sits. ``progress_markup`` writes them into the
page as JSON next to the script tag. ``path_export`` is the machine-readable
learning path that the built site carries as ``path.json`` for client-side
use (F14); it holds lessons and their relations, never learner state.
"""

import json
from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pbc.authoring.path import LearningPath, Lesson
from pbc.authoring.website import page_href

# The key in local storage; site/learner/progress.js uses the same.
STORAGE_KEY = "physics-by-construction:learner-state"
# The script and the data element of a page that uses it.
SCRIPT = "learner/progress.js"
DATA_ID = "learner-state-data"
# Where the page that explains the stored data lives, and the anchor of its
# section. The path page holds it, with the clear-data control.
EXPLANATION_ANCHOR = "your-progress"
PATH_PAGE = "path/index.qmd"
# The file of the built site with the learning path.
EXPORT_FILE = "path.json"
EXPORT_VERSION = 1

_SEPARATORS = (",", ":")


def progress_markup(page: str, lesson: Lesson | None) -> str:
    """The HTML that makes the page ``page`` (relative to the website
    project) load the learner-state script: a JSON data element and the
    module tag, with relative URLs. ``lesson`` is the lesson the page is, or
    ``None`` for the learning path page."""
    depth = page.count("/")
    data = {
        "lesson": lesson.id if lesson else None,
        "explanation": page_href(page, PATH_PAGE, EXPLANATION_ANCHOR),
    }
    payload = json.dumps(data, separators=_SEPARATORS).replace("<", "\\u003c")
    panel = (
        '<div id="learner-panel" class="learner-panel" data-enhancement="">'
        "<p>With scripts, this page keeps a record in your browser of whether"
        " you completed the lesson. Nothing is stored without them.</p></div>"
        if lesson
        else ""
    )
    return (
        f"{panel}"
        f'<script type="application/json" id="{DATA_ID}">{payload}</script>'
        f'<script type="module" src="{"../" * depth}{escape(SCRIPT)}"></script>'
    )


def raw_html(markup: str) -> str:
    """Markdown that passes ``markup`` to the page unchanged."""
    return f"```{{=html}}\n{markup}\n```\n"


def path_export(path: LearningPath) -> dict[str, object]:
    """The learning path as data: one entry per lesson in path order, with the
    page of the built site relative to its root."""
    return {
        "version": EXPORT_VERSION,
        "lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "page": page_href("index.qmd", lesson.page),
                "strand": lesson.strand,
                "order": lesson.order,
                "course": lesson.course,
                "methods": list(lesson.methods),
                "difficulty": lesson.difficulty,
                "prerequisites": list(lesson.prerequisites),
                "related": list(lesson.related),
            }
            for lesson in path.lessons
        ],
    }


def export_json(path: LearningPath) -> str:
    """The export as the text of ``path.json``: sorted keys, one trailing
    newline, so that two builds write the same bytes."""
    return json.dumps(path_export(path), indent=1, sort_keys=True) + "\n"
