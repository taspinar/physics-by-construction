"""Real datasets as declared inputs (ADR 007).

Cards live in ``data/registry/``, committed samples in ``data/samples/``. The
readers here parse only committed samples or files a learner downloaded with
``scripts/fetch-data.sh``; nothing in this package opens a network connection.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = REPO_ROOT / "data" / "registry"
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
DOWNLOADS_DIR = REPO_ROOT / "data" / "downloads"
