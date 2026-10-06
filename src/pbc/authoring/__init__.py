"""Helpers lesson pages use to display material by reference.

A lesson calls these from code cells that the build executes, so what the
page shows is read from the repository when the page is built and cannot
drift from it (ADR 002). ``docs/authoring.md`` describes their use.
"""

from pbc.authoring.excerpt import Excerpt, excerpt
from pbc.authoring.repository import BuildCommit, build_commit
from pbc.authoring.reproduce import Reproduction, reproduce_this

__all__ = [
    "BuildCommit",
    "Excerpt",
    "Reproduction",
    "build_commit",
    "excerpt",
    "reproduce_this",
]
