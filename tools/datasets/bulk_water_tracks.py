"""Track the 40 frames of trackpy-examples ``bulk_water`` once, to the CSV sample.

    uv run python tools/datasets/bulk_water_tracks.py INPUT_DIR OUTPUT_DIR

The one-time processing of the dataset ``trackpy-bulk-water``: the frames
000-039 (7,602,501 bytes) are more than the sample can hold, so the
particles are located and linked once, outside the build, and the committed
sample holds the result with three of the frames. The build, the
verification, and CI never run this script; the two committed files are its
output and the dataset check compares them with the card's sha256:

- ``bulk_water_tracks.csv``: every located feature of the 40 frames;
- ``bulk_water_green_000-002.npy``: the green channel of frames 000-002,
  the grey levels unchanged, as an array of shape (3, 424, 640) and type
  uint8. The frames are data here, not pictures: the repository commits no
  image file outside ``site/assets/`` (invariant I6), so the PNGs are not
  committed, and the build repeats the tracking of these three frames on
  the array.

``INPUT_DIR`` holds the frames as ``./scripts/fetch-data.sh trackpy-bulk-water``
downloads them. Each frame's SHA-256 must equal the one pinned below (the
files of commit 09fb3074 of soft-matter/trackpy-examples, inspected for the
dossier); any other file is refused. The tracking is
``pbc.data.reference.trackpy_bulk_water.track`` with the parameters of that
module (``pbc.data.tracking``: band-pass, centroid, mutual nearest
neighbours; NumPy and SciPy, not trackpy). The output is the same bytes on
each run: one row per located feature, ordered by frame and then by the
row-major position of its peak, positions to 0.001 px and mass to 0.1,
after comment lines that name the source, the parameters, and the units.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np

from pbc.data.reference import trackpy_bulk_water as bw

COMMIT = "09fb3074a173585d48b5001b5b4b7e6479999598"
# The SHA-256 of bulk_water_000.png to bulk_water_039.png, in order.
_PINNED = (
    "feae7568616c191e7cfa7a24b913c8bb6c7418baf6dd9f83122e3db996cd682b",
    "70eaa055e631e531ee83ec16501a47e20521b34df2cb27281915203414e6eb85",
    "e07c854b4dddb3105da6b2cc6591cc1291768d7e1c6a152550c574352e4da1c5",
    "995456bb46493805c0c248d110b8a7e5b09e30ad25cae0e315bd243519e63776",
    "d644d1bb4bc753ba6ac259843cfa61f5d2476c8c22af772bef7403356b367c93",
    "eac6b93629127e60b6ec633027ae7370be8a45f9ff433ccd3e21f1216fb9dcac",
    "60e9a7da1a9bab4766ea3c4eceb2ff00ce05ef114264f791daed9dbca483383e",
    "3559aff34b2b85701c75aeb39354d09182dc6dfea141223732e8e94247674f46",
    "eea86635e8b5fe13343dcb0e1f4b90cdf871b3a7d8dde95b949d91d7f82467ac",
    "18433282025ecbc82627ef8f62d161615c80acf89c639c42d31d90da1f827bbd",
    "ccb4cb9e28466efdc613faa2293ab2ec1774b68c686a5608f0e36fc6c3b4d18c",
    "e6a9d83a2c91c96ce11b8a87706d658fec46f5441dc0a99d9c8f04fc786af69c",
    "f2864a9528322432c6052b307cb33390410a1752b7dfc3915b24b4db3b2ef7be",
    "497a8bd8067863ac6ab7bbb99a218dcb0c774b6b22d3bad7b2920c1868bb63b0",
    "ffc945782b6084f50d5f9463a555d4ef9d70c82d7faf62ce5c2cdcb16675deb1",
    "5ad91a8980349ccd660bb4dc77f17778edb78602eb9c177adafddf816b7ac13f",
    "6181d2475b8d6b769e0fbc3b9c0df61cf605b6901616ebca46d39e4888caac57",
    "02fb9db2d0d85cc666c631cec0f68b7c8468cbacd31481d6aaeaf83f64892858",
    "e4f7960e89c967093ea0e5cddf199b1c8356462b4dcc158ad554de381044f98e",
    "5d542c8f8542cb874a6eabcf1dd48f3739a8358c23ac927edb7392e7d58bdd43",
    "f3a5add0744112329df399888ca03070183027a70852906cd35539641883c061",
    "afe0faa904644aef8cf58684076e1d148aabd572b1a62c93d3a1450819007a77",
    "3652cd7193b257c699bca9e085a4ec81369dbb2f7f44db74f5376e8bce077386",
    "147a8788666c124e2b248b28bba584a9f1e1b1c7c6c3d4d02dcbc39e73df7df2",
    "d30396f7b81d05b989e60b29ce24ba35592f38e8a55dadf3301bb181b414ab92",
    "cd2172d64386a83fde37e5a7d3723207c7011e9d0a2e9da9a3da71f1db6b59ad",
    "e54cd40fc2325574fa7b717846701f38202087d6628c80f4476d708a93de905e",
    "84723fb684e2bddcc1c6e5c4bb5d1bb8aaa7b355c332e586ce695f69c14f55be",
    "98f77422df88e5c59c04171d56d89cdf559bf7de884d5565c4ad1ad3ba7f5f0d",
    "2ae3b253ee499a6a666f2b3e06a233d9e4ae7d57e251d5cd5ff9ce9c6594ddb5",
    "f89afef4f01881979bdcb9a87785c3f767e14613576c09d10de261f6cdf3f204",
    "5c67ae1d912daa0eefe8d1961001fe6397b0cde82f6ecb481890a21cc329b383",
    "ba072d1c24cf4bf85c62821a6b0b7114a066b56d525d6fef320495faff80335e",
    "7742b893a8156622a6202e2650b1ea289a4a0796f1e94aeda5f7c776ee93b15d",
    "957560a7a4b1b38bbd08e4f53bccce47abc1c85234a592bd650c1c958a787614",
    "91134b44834b35177135af2945059ee240a324052eda424d0b7f3dc1721324c3",
    "4485fed31b84ac649e2516f0240d593913ff415a4dc33e2799b1d109652c3162",
    "1effa1b08f866c6554bc3fc361d973d23365e0382520bed726d88a46f33dffd9",
    "8e7ad590311fef5ff43b1a2036cc5865edba5bd98de412bb0e17e28b159c5478",
    "3b1d65b2ce9836aa6002574fe43abd4acf9b8ccebe00353d8e4b56b4472f83b6",
)
FRAME_SHA256 = {f"bulk_water_{k:03d}.png": sha for k, sha in enumerate(_PINNED)}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def header() -> list[str]:
    return [
        "# trackpy-examples sample_data/bulk_water, frames bulk_water_000.png to"
        f" bulk_water_039.png at commit {COMMIT}",
        "# (the SHA-256 of each frame is pinned in"
        " tools/datasets/bulk_water_tracks.py)",
        "# processing of this project, not the provider's: green channel; band-pass"
        f" (Gaussian {bw.SMOOTHING} px minus the mean over {2 * bw.RADIUS + 1} px);"
        f" maxima over a disk of radius {bw.RADIUS} px; centroid; mass >= {bw.MINMASS};"
        f" mutual nearest neighbours within {bw.SEARCH_RANGE} px, no memory",
        "# frame: 0-39 at 24 frames per second; particle: track number; x, y: px from"
        " the centre of the top-left pixel, y downwards (1 um = 2.85 px);"
        " mass: grey levels",
    ]


def convert(input_dir: Path, output_dir: Path) -> None:
    frames = []
    for name, expected in FRAME_SHA256.items():
        path = Path(input_dir) / name
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"{path}: sha256 {actual}, expected {expected}")
        frames.append(bw.read_frame(path))
    rows = bw.track(frames)
    lines = [*header(), ",".join(bw.FIELDS), *bw.format_rows(rows)]
    output_dir = Path(output_dir)
    (output_dir / bw.TRACKS).write_text("\n".join(lines) + "\n", encoding="ascii")
    green = np.stack(frames[: bw.COMMITTED_FRAMES]).astype(np.uint8)
    np.save(output_dir / bw.FRAMES, green, allow_pickle=False)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        convert(Path(argv[0]), Path(argv[1]))
    except (OSError, ValueError) as error:
        print(f"bulk_water_tracks: {error}", file=sys.stderr)
        return 1
    print(f"wrote {bw.TRACKS} and {bw.FRAMES} in {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
