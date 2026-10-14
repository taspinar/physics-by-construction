"""The lessons the running verification executes (ADR 014 decisions 3 and 11)."""

from pbc.authoring import selection as selecting
from pbc.authoring import shards as sharding
from support.paths import REPO_ROOT


def executed_lessons() -> list[str] | None:
    """The lessons this run executes, or None for every lesson: the share of a
    lesson shard that the selection of a base does not restore from it."""
    return sharding.executed(sharding.read(root=REPO_ROOT), selecting.read(REPO_ROOT))


def idle_shard() -> bool:
    """Whether this run is a lesson shard with nothing to execute, which renders
    no page and has no site to check."""
    return sharding.read(root=REPO_ROOT) is not None and executed_lessons() == []
