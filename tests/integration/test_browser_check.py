"""The browser check behind preflight and doctor detects a missing build."""

import os
import subprocess
import sys
from pathlib import Path

from support.paths import SCRIPTS

CHECK = SCRIPTS / "lib" / "check_browser.py"


def run_check(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK)],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_passes_with_the_installed_browser_build():
    assert run_check({}).returncode == 0


def test_reports_a_browser_build_that_is_not_installed(tmp_path: Path):
    # An empty browser directory is what a machine without the one-time
    # setup looks like.
    result = run_check({"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path)})

    assert result.returncode == 3, result.stderr
