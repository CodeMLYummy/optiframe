"""Display a fullscreen Ronchi ruling with 0.5 mm black and white bars."""

import tkinter as tk

BAR_WIDTH_MM = 0.5


def stripe_boundaries(width_px: int, screen_width_mm: float) -> list[int]:
    """Return rounded pixel boundaries for each 0.5 mm stripe."""
    if width_px <= 0 or screen_width_mm <= 0:
        raise ValueError("Screen dimensions must be positive.")

    stripe_width_px = width_px / screen_width_mm * BAR_WIDTH_MM
    stripe_count = int(width_px / stripe_width_px) + 1
    return [round(index * stripe_width_px) for index in range(stripe_count + 1)]


def main() -> None:
    root = tk.Tk()
    root.title("Ronchi Ruling")
    root.configure(background="black")
    root.attributes("-fullscreen", True)
    root.config(cursor="none")

    screen_width_px = root.winfo_screenwidth()
    screen_width_mm = root.winfo_screenmmwidth()
    if screen_width_mm <= 0:
        root.destroy()
        raise RuntimeError("The display did not report its physical width; cannot calculate 0.5 mm bars.")

    canvas = tk.Canvas(root, background="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    last_size = (0, 0)

    def redraw(event: tk.Event) -> None:
        nonlocal last_size
        size = (event.width, event.height)
        if size == last_size:
            return
        last_size = size
        canvas.delete("ruling")

        boundaries = stripe_boundaries(screen_width_px, screen_width_mm)
        for index, (left, right) in enumerate(zip(boundaries, boundaries[1:])):
            if left >= event.width:
                break
            color = "white" if index % 2 else "black"
            canvas.create_rectangle(
                left,
                0,
                min(right, event.width),
                event.height,
                fill=color,
                outline=color,
                width=0,
                tags="ruling",
            )

    canvas.bind("<Configure>", redraw)
    root.bind("<Escape>", lambda _event: root.destroy())
    root.bind(
        "f",
        lambda _event: root.attributes("-fullscreen", not root.attributes("-fullscreen")),
    )
    root.mainloop()


if __name__ == "__main__":
    main()
