"""Locations in the repository that tests refer to."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_SOURCE = REPO_ROOT / "site"
BUILT_SITE = SITE_SOURCE / "_site"
LEAN_PROJECT = REPO_ROOT / "lean"
SCRIPTS = REPO_ROOT / "scripts"
