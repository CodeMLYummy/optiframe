"""Display a configurable ChArUco board fullscreen."""

import argparse
import base64
import math
import re
import subprocess
import tkinter as tk
from dataclasses import dataclass

import cv2

from lensdetection.aruco import DICTIONARIES


@dataclass(frozen=True)
class Monitor:
    name: str
    width_px: int
    width_mm: int
    height_px: int
    x: int
    y: int
    primary: bool


_MONITOR_RE = re.compile(
    r"^\s*\d+:\s+(?P<label>\S+)\s+"
    r"(?P<width_px>\d+)/(?P<width_mm>\d+)x"
    r"(?P<height_px>\d+)/\d+"
    r"(?P<x>[+-]\d+)(?P<y>[+-]\d+)\s+(?P<name>\S+)\s*$"
)


def parse_xrandr_monitors(output: str) -> list[Monitor]:
    """Parse the physical geometry from `xrandr --listactivemonitors`."""
    monitors = []
    for line in output.splitlines():
        match = _MONITOR_RE.match(line)
        if match is None:
            continue
        values = match.groupdict()
        monitors.append(
            Monitor(
                name=values["name"],
                width_px=int(values["width_px"]),
                width_mm=int(values["width_mm"]),
                height_px=int(values["height_px"]),
                x=int(values["x"]),
                y=int(values["y"]),
                primary="*" in values["label"],
            )
        )
    return monitors


def select_monitor(
    monitors: list[Monitor], pointer: tuple[int, int] | None
) -> Monitor | None:
    """Select the monitor under the pointer, then the primary or sole monitor."""
    if pointer is not None:
        pointer_x, pointer_y = pointer
        for monitor in monitors:
            if (
                monitor.x <= pointer_x < monitor.x + monitor.width_px
                and monitor.y <= pointer_y < monitor.y + monitor.height_px
            ):
                return monitor
    for monitor in monitors:
        if monitor.primary:
            return monitor
    if len(monitors) == 1:
        return monitors[0]
    return None


def detect_pixels_per_mm(
    pointer: tuple[int, int] | None,
) -> tuple[float, str] | None:
    """Read per-monitor physical dimensions from RandR when available."""
    try:
        result = subprocess.run(
            ["xrandr", "--listactivemonitors"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None

    monitor = select_monitor(parse_xrandr_monitors(result.stdout), pointer)
    if monitor is None or monitor.width_px <= 0 or monitor.width_mm <= 0:
        return None
    return (
        monitor.width_px / monitor.width_mm,
        f"RandR {monitor.name}: {monitor.width_px} px / {monitor.width_mm} mm",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display a fullscreen ChArUco calibration board."
    )
    parser.add_argument(
        "squares_x",
        type=int,
        nargs="?",
        default=8,
        help="Number of squares across (default: 8)",
    )
    parser.add_argument(
        "squares_y",
        type=int,
        nargs="?",
        default=6,
        help="Number of squares high (default: 6)",
    )
    parser.add_argument(
        "--square-mm",
        type=float,
        default=25.0,
        help="Square side length in mm (default: 25)",
    )
    parser.add_argument(
        "--marker-mm",
        type=float,
        default=18.0,
        help="Marker side length in mm (default: 18)",
    )
    parser.add_argument(
        "--dictionary",
        choices=sorted(DICTIONARIES),
        default="4X4_50",
        help="ArUco dictionary (default: 4X4_50)",
    )
    args = parser.parse_args()

    if args.squares_x < 2 or args.squares_y < 2:
        parser.error("the board must have at least 2 squares in each direction")
    if (
        not math.isfinite(args.square_mm)
        or not math.isfinite(args.marker_mm)
        or args.square_mm <= 0
        or args.marker_mm <= 0
    ):
        parser.error("square and marker sizes must be positive")
    if args.marker_mm >= args.square_mm:
        parser.error("marker size must be smaller than square size")
    dictionary = cv2.aruco.getPredefinedDictionary(DICTIONARIES[args.dictionary])
    marker_count = (args.squares_x * args.squares_y) // 2
    if marker_count > len(dictionary.bytesList):
        parser.error("the selected dictionary does not have enough marker IDs")
    if not math.isfinite(args.squares_x * args.square_mm) or not math.isfinite(
        args.squares_y * args.square_mm
    ):
        parser.error("board dimensions are too large")
    return args


def main() -> None:
    args = parse_args()
    dictionary = cv2.aruco.getPredefinedDictionary(DICTIONARIES[args.dictionary])
    board = cv2.aruco.CharucoBoard(
        (args.squares_x, args.squares_y),
        args.square_mm,
        args.marker_mm,
        dictionary,
    )
    board_width_mm = args.squares_x * args.square_mm
    board_height_mm = args.squares_y * args.square_mm
    root = tk.Tk()
    root.title("ChArUco Board")
    root.configure(background="white")
    root.attributes("-fullscreen", True)
    root.config(cursor="none")

    screen_width_px = root.winfo_screenwidth()
    screen_height_px = root.winfo_screenheight()
    screen_width_mm = root.winfo_screenmmwidth()
    pointer = (root.winfo_pointerx(), root.winfo_pointery())
    if pointer == (-1, -1):
        pointer = None
    detected_scale = detect_pixels_per_mm(pointer)
    if detected_scale is not None:
        pixels_per_mm, scale_source = detected_scale
    elif screen_width_mm > 0:
        pixels_per_mm = screen_width_px / screen_width_mm
        scale_source = (
            f"Tk fallback: {screen_width_px} px / {screen_width_mm} mm"
        )
    else:
        root.destroy()
        raise RuntimeError(
            "The display did not report its physical width; cannot calculate "
            "the board's on-screen size."
        )

    board_width_px = round(board_width_mm * pixels_per_mm)
    board_height_px = round(board_height_mm * pixels_per_mm)
    if board_width_px <= screen_width_px and board_height_px <= screen_height_px:
        image = board.generateImage(
            (board_width_px, board_height_px), marginSize=0, borderBits=1
        )
        success, png = cv2.imencode(".png", image)
        if not success:
            root.destroy()
            raise RuntimeError("OpenCV could not encode the ChArUco board image.")
        board_image: tk.PhotoImage | None = tk.PhotoImage(
            data=base64.b64encode(png).decode("ascii"), format="png"
        )
    else:
        board_image = None

    info = (
        f"ChArUco: {args.squares_x} x {args.squares_y} squares"
        f"  |  square: {args.square_mm:g} mm"
        f"  |  marker: {args.marker_mm:g} mm"
        f"  |  {args.dictionary}"
        f"  |  size: {board_width_mm:g} x {board_height_mm:g} mm"
        f"  |  scale: {scale_source}"
    )

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    canvas = tk.Canvas(root, background="white", highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")
    status = tk.Label(
        root,
        text=info,
        background="white",
        foreground="black",
        font=("TkDefaultFont", 14),
        padx=12,
        pady=8,
    )
    status.grid(row=1, column=0, sticky="ew")

    def redraw(event: tk.Event) -> None:
        canvas.delete("board")
        if (
            board_image is None
            or board_width_px > event.width
            or board_height_px > event.height
        ):
            canvas.create_text(
                event.width // 2,
                event.height // 2,
                text=(
                    "Board does not fit at the reported physical screen scale.\n"
                    f"Required: {board_width_px} x {board_height_px} px"
                ),
                fill="black",
                justify="center",
                tags="board",
            )
            return
        canvas.create_image(
            event.width // 2,
            event.height // 2,
            image=board_image,
            anchor="center",
            tags="board",
        )

    canvas.bind("<Configure>", redraw)
    root.bind("<Escape>", lambda _event: root.destroy())
    root.bind(
        "f",
        lambda _event: root.attributes(
            "-fullscreen", not root.attributes("-fullscreen")
        ),
    )
    root.mainloop()


if __name__ == "__main__":
    main()
