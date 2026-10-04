"""Run the full pipeline on one photo: glass-edges, close-contour, then boxing."""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Photo of glass over a ChArUco board")
    parser.add_argument("board", type=Path, help="JSON with the board's dimensions")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/" + str(datetime.now()).replace(" ", "_")),
    )
    args = parser.parse_args()

    out = str(args.output_dir)
    image = str(args.image)
    steps = [
        ("glass-edges", ["glass_edges", image, str(args.board), "--output-dir", out]),
        ("close-contour", ["close_contour", out, "--image", image]),
        ("boxing", ["boxing", out, image]),
    ]
    for name, (module, *step_args) in steps:
        print(f"== {name}", flush=True)
        run = subprocess.run([sys.executable, "-m", f"lensdetection.{module}", *step_args])
        if run.returncode != 0:
            sys.exit(f"demo: {name} failed (exit {run.returncode})")


if __name__ == "__main__":
    main()
