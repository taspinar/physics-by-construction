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
from pathlib import Path
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
# The owner's sentence of the section (Issue #483), shown without scripts
# and, by site/learner/progress.js, without saved progress.
PROGRESS_SENTENCE = (
    "Track completed lessons and continue where you left off. Your progress"
    " stays in this browser."
)
PATH_PAGE = "path/index.qmd"
# The file of the built site with the learning path.
EXPORT_FILE = "path.json"
EXPORT_VERSION = 1

_SEPARATORS = (",", ":")


RECOMMENDATIONS_ID = "recommendations"


def recommendations_markup() -> str:
    """The place where the script shows what to do next: an enhancement with
    the sentence that readers without scripts see in its place."""
    return (
        f'<div id="{RECOMMENDATIONS_ID}" class="recommendations-panel"'
        ' data-enhancement=""><p>With scripts, this place suggests what to do'
        " next, with the reason, from the progress saved in your browser."
        " Without them, follow the learning path.</p></div>"
    )


def progress_markup(
    page: str, lesson: Lesson | None, path: LearningPath | None = None
) -> str:
    """The HTML that makes the page ``page`` (relative to the website
    project) load the learner-state script: a JSON data element and the
    module tag, with relative URLs. ``lesson`` is the lesson the page is, or
    ``None`` for the learning path page. With ``path``, the data element also
    holds the lessons of the learning path, with their pages relative to
    ``page``, for the recommendations of ``site/learner/recommend.js``: the
    browser works them out from the page and never fetches anything."""
    depth = page.count("/")
    data: dict[str, object] = {
        "lesson": lesson.id if lesson else None,
        "explanation": page_href(page, PATH_PAGE, EXPLANATION_ANCHOR),
    }
    if path is not None:
        data["path"] = [
            {
                "id": item.id,
                "title": item.title,
                "href": page_href(page, item.page),
                "prerequisites": list(item.prerequisites),
            }
            for item in path.lessons
        ]
    payload = json.dumps(data, separators=_SEPARATORS).replace("<", "\\u003c")
    panel = (
        '<div id="learner-panel" class="learner-panel" data-enhancement="">'
        "<p>With scripts, this page keeps a record in your browser of whether"
        " you completed the lesson. Nothing is stored without them.</p></div>"
        if lesson
        else ""
    )
    suggestions = recommendations_markup() if lesson and path is not None else ""
    return (
        f"{panel}{suggestions}"
        f'<script type="application/json" id="{DATA_ID}">{payload}</script>'
        f'<script type="module" src="{"../" * depth}{escape(SCRIPT)}"></script>'
    )


def raw_html(markup: str) -> str:
    """Markdown that passes ``markup`` to the page unchanged."""
    return f"```{{=html}}\n{markup}\n```\n"


def path_export(path: LearningPath, site: Path | None = None) -> dict[str, object]:
    """The learning path as data: one entry per lesson in path order, with the
    page of the built site relative to its root. A lesson that fills a slot
    of a method path also names the path and its position there. With the
    website project ``site``, each lesson also names its preview file and the
    alt text of it (F63)."""
    from pbc.authoring.previews import preview_of

    previews = (
        {lesson.id: preview_of(lesson, site) for lesson in path.lessons}
        if site is not None
        else {}
    )
    homed = [slot for slot in path.curriculum.slots if slot.path]
    path_of = {slot.label: slot.path for slot in homed}
    position_of = {slot.label: slot.position for slot in homed}
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
                "slot": lesson.slot or None,
                "path": path_of.get(lesson.slot),
                "position": position_of.get(lesson.slot),
                **(
                    {
                        "preview": {
                            "alt": previews[lesson.id].alt,
                            "src": previews[lesson.id].file,
                        }
                    }
                    if site is not None
                    else {}
                ),
            }
            for lesson in path.lessons
        ],
    }


def export_json(path: LearningPath, site: Path | None = None) -> str:
    """The export as the text of ``path.json``: sorted keys, one trailing
    newline, so that two builds write the same bytes."""
    return json.dumps(path_export(path, site), indent=1, sort_keys=True) + "\n"
