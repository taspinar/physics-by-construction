"""Helpers lesson pages use to display material by reference.

A lesson calls these from code cells that the build executes, so what the
page shows is read from the repository when the page is built and cannot
drift from it (ADR 002). ``docs/authoring.md`` describes their use.
"""

from pbc.authoring.excerpt import Excerpt, excerpt
from pbc.authoring.path import (
    DIFFICULTIES,
    STRANDS,
    LearningPath,
    LessonHeader,
    PathOverview,
    learning_path,
    lesson_header,
)
from pbc.authoring.repository import BuildCommit, build_commit
from pbc.authoring.reproduce import Reproduction, reproduce_this
from pbc.authoring.widgets import WidgetScript, widget_data, widget_module

__all__ = [
    "DIFFICULTIES",
    "STRANDS",
    "BuildCommit",
    "Excerpt",
    "LearningPath",
    "LessonHeader",
    "PathOverview",
    "Reproduction",
    "WidgetScript",
    "build_commit",
    "excerpt",
    "learning_path",
    "lesson_header",
    "reproduce_this",
    "widget_data",
    "widget_module",
]
