"""Run a required check the way ./scripts/verify.sh runs it."""

import os
import shlex
import subprocess
from pathlib import Path

from support import verify_conf
from support.paths import REPO_ROOT


def run_check(
    name: str,
    *arguments: str | Path,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the command of check ``name`` from scripts/verify.conf.

    ``arguments`` are appended to the command, to point a check script at
    another input than the repository. A check that starts with ``uv run``
    can instead be run in another directory: it then still uses the locked
    environment of the repository.
    """
    command = verify_conf.command(name)
    if arguments:
        command += " " + shlex.join(str(argument) for argument in arguments)
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", command],
        cwd=cwd,
        env={**os.environ, "UV_PROJECT": str(REPO_ROOT), **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr
