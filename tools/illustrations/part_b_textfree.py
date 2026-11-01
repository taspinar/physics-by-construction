"""Text-free masters of the four Part B illustrations: the owner's own drawing
functions and data (render_part_b.py), validated by its own checks, with every
text object hidden (ADR 021 decision 1: interface artwork carries no text,
number, or formula in its pixels).

Run: python part_b_textfree.py [OUTPUT_DIRECTORY]   (default: this directory)
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.text

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_part_b as R  # noqa: E402

SLUGS = ("reasoning", "law_discovery", "benchmarking", "autonomous_research")


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    data = R.make_data()
    R.validate(data)  # the owner's checks must still pass
    for slug, row in zip(SLUGS, R.ROWS, strict=True):
        draw = row[1]
        fig = plt.figure(figsize=(4, 3), facecolor=R.BG)
        ax = fig.add_axes([0.015, 0.015, 0.97, 0.97])
        draw(ax, data, 0, small=True)
        for spine in ax.spines.values():
            spine.set_visible(False)
        hidden = 0
        for text in fig.findobj(matplotlib.text.Text):
            if text.get_text().strip():
                hidden += 1
            text.set_visible(False)
        fig.savefig(out / f"pbc_part_b_{slug}_textfree.png", dpi=400, facecolor=R.BG)
        plt.close(fig)
        print(slug, "text objects hidden:", hidden)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
