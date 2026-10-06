"""The repository a page is built from: its location, address, and commit."""

import subprocess
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

# The package is installed from its checkout (uv installs the project in
# editable mode), so the repository is found from this file:
# <root>/src/pbc/authoring/repository.py.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def repository_url() -> str:
    """Return the public address of the repository, without a trailing slash.

    It is the ``Repository`` entry of ``[project.urls]`` in pyproject.toml.
    """
    for entry in metadata.metadata("pbc").get_all("Project-URL") or []:
        label, _, url = entry.partition(",")
        if label.strip() == "Repository":
            return url.strip().rstrip("/")
    raise LookupError("pyproject.toml declares no 'Repository' URL for pbc")


@dataclass(frozen=True)
class BuildCommit:
    """The commit of the checkout a page is built from."""

    sha: str | None  # None when the package is not in a Git checkout
    dirty: bool  # the working tree differs from that commit

    @property
    def exact(self) -> bool:
        """Whether checking out ``sha`` gives exactly the files that were built."""
        return self.sha is not None and not self.dirty


def _git(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def build_commit(root: Path = REPOSITORY_ROOT) -> BuildCommit:
    """Return the commit checked out in ``root`` and whether the tree is dirty.

    Untracked files that Git does not ignore count as changes: a page built
    from them is not in the commit. Build output is ignored by Git and does
    not count.
    """
    top_level = _git(root, "rev-parse", "--show-toplevel")
    if top_level is None or Path(top_level.strip()).resolve() != root.resolve():
        # Not a checkout of its own; a repository further up is another one.
        return BuildCommit(sha=None, dirty=False)
    sha = _git(root, "rev-parse", "--verify", "HEAD")
    status = _git(root, "status", "--porcelain")
    if sha is None or status is None:
        return BuildCommit(sha=None, dirty=False)
    return BuildCommit(sha=sha.strip(), dirty=bool(status.strip()))
