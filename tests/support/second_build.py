"""A second build of the site from a copy of its sources.

The build starts from the same state as the one it is compared with: a run
with a base (ADR 014) restored the executed results of the unchanged lessons
from a base built on another machine, so the second build restores them again
and only the lessons the run executes execute twice. Without the selection of
the run it would execute every lesson on this machine, and a preview the base
holds would be compared with one this machine computed, which is no
reproduction (ADR 012 decision 4).
"""

import os
import shutil
import subprocess
from pathlib import Path

from pbc.authoring import selection as selecting
from support.paths import REPO_ROOT, SITE_SOURCE


def selection_environment(root: Path = REPO_ROOT) -> dict[str, str]:
    """The environment that gives a build of a copy the selection of the run,
    and nothing for a full run."""
    chosen = selecting.read(root)
    if chosen is None or chosen.get("mode") != "selective":
        return {}
    return {"PBC_STORE_SELECTION": str(root / selecting.SELECTION_FILE)}


def build_copy(
    source: Path,
    second: Path,
    work: Path,
    *,
    root: Path = REPO_ROOT,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Copy ``source`` to ``work / "site"`` without any build state and build it
    into ``second`` through ``scripts/build-site.sh``."""
    copy = work / "site"
    shutil.copytree(
        source,
        copy,
        ignore=shutil.ignore_patterns(
            "_site", ".quarto", "_freeze", "_digests.json", "_timings.json"
        ),
    )
    env = {**os.environ, **selection_environment(root), **(environment or {})}
    return subprocess.run(
        [str(root / "scripts/build-site.sh"), str(copy), str(second)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


__all__ = ["SITE_SOURCE", "build_copy", "selection_environment"]
