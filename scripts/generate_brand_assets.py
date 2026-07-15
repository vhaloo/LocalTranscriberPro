"""Generate deterministic application icons for every desktop package."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def make_icon(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), "#08101F")
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.10)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(size * 0.22),
        fill="#111C32",
    )
    center = size // 2
    microphone_width = int(size * 0.24)
    top = int(size * 0.22)
    bottom = int(size * 0.62)
    draw.rounded_rectangle(
        (center - microphone_width // 2, top, center + microphone_width // 2, bottom),
        radius=microphone_width // 2,
        fill="#5EE4B7",
    )
    stroke = max(8, int(size * 0.045))
    draw.arc(
        (int(size * 0.27), int(size * 0.39), int(size * 0.73), int(size * 0.73)),
        0,
        180,
        fill="#65A8FF",
        width=stroke,
    )
    draw.line((center, int(size * 0.70), center, int(size * 0.80)), fill="#65A8FF", width=stroke)
    draw.rounded_rectangle(
        (int(size * 0.35), int(size * 0.78), int(size * 0.65), int(size * 0.84)),
        radius=stroke,
        fill="#65A8FF",
    )
    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    image = make_icon()
    image.save(ASSETS / "icon.png", optimize=True)
    image.save(
        ASSETS / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
