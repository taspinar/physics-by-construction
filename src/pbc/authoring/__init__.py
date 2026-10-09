"""Helpers lesson pages use to display material by reference.

A lesson calls these from code cells that the build executes, so what the
page shows is read from the repository when the page is built and cannot
drift from it (ADR 002). ``docs/authoring.md`` describes their use.
"""

from pbc.authoring.design import (
    CLAIM_TYPES,
    FIGURE_COLOURS,
    FIGURE_STATUSES,
)
from pbc.authoring.excerpt import Excerpt, excerpt
from pbc.authoring.glossary import Glossary, GlossaryPage, glossary_page
from pbc.authoring.home import PLANNED, HomeContent, Planned, home_content
from pbc.authoring.lean import LeanEvidence, LeanExcerpt, lean_evidence, lean_excerpt
from pbc.authoring.path import (
    COURSES,
    DIFFICULTIES,
    METHODS,
    STRANDS,
    LearningPath,
    LessonHeader,
    PathOverview,
    learning_path,
    lesson_header,
)
from pbc.authoring.repository import BuildCommit, build_commit
from pbc.authoring.reproduce import Reproduction, reproduce_this
from pbc.authoring.tables import ResultTable, is_numeric_console_block, table
from pbc.authoring.widgets import WidgetScript, widget_data, widget_module

__all__ = [
    "CLAIM_TYPES",
    "COURSES",
    "DIFFICULTIES",
    "FIGURE_COLOURS",
    "FIGURE_STATUSES",
    "METHODS",
    "PLANNED",
    "STRANDS",
    "BuildCommit",
    "Excerpt",
    "Glossary",
    "GlossaryPage",
    "HomeContent",
    "LeanEvidence",
    "LeanExcerpt",
    "LearningPath",
    "LessonHeader",
    "PathOverview",
    "Planned",
    "Reproduction",
    "ResultTable",
    "WidgetScript",
    "build_commit",
    "excerpt",
    "glossary_page",
    "home_content",
    "is_numeric_console_block",
    "lean_evidence",
    "lean_excerpt",
    "learning_path",
    "lesson_header",
    "reproduce_this",
    "table",
    "widget_data",
    "widget_module",
]
