"""Write the learning path into the built site as ``path.json``.

The file is the machine-readable form of the learning path for client-side
use: lesson ids with their titles, pages, order, course, methods, difficulty,
prerequisites, and related lessons. It holds nothing about a learner. Runs
after the site is rendered (``post-render``); idempotent; the content comes
from the front matter of the lessons, as the learning path page does.
"""

import os
from pathlib import Path

from pbc.authoring.path import LearningPath
from pbc.authoring.progress import EXPORT_FILE, export_json


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    project = Path(os.environ.get("QUARTO_PROJECT_DIR", "."))
    (output / EXPORT_FILE).write_text(
        export_json(LearningPath.read(project)), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
