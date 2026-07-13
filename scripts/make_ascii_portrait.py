#!/usr/bin/env python3
"""Create a deterministic ASCII portrait from a real photograph."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageFont, ImageOps


GLYPHS = " .,:;irsXA253hMHGS#9B&@"
CANVAS_SIZE = 512
COLS = 128
ROWS = 128


def render(source: Path, output: Path) -> None:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")

        # Fixed crop from the supplied close portrait: hood, face and shoulders.
        width, height = image.size
        left = round(width * 0.24)
        top = round(height * 0.39)
        side = round(min(width * 0.48, height * 0.27))
        image = image.crop((left, top, left + side, top + side))
        image = ImageOps.fit(image, (CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)

    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray, cutoff=(1, 1))
    gray = gray.point(lambda value: round(255 * (value / 255) ** 0.72))
    gray = ImageEnhance.Contrast(gray).enhance(1.35)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1.3, percent=125, threshold=3))

    samples = gray.resize((COLS, ROWS), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (CANVAS_SIZE, CANVAS_SIZE), 0)
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 5)

    from PIL import ImageDraw

    draw = ImageDraw.Draw(canvas)
    cell_w = CANVAS_SIZE / COLS
    cell_h = CANVAS_SIZE / ROWS
    pixels = samples.load()

    for row in range(ROWS):
        for col in range(COLS):
            value = pixels[col, row]
            glyph = GLYPHS[round(value / 255 * (len(GLYPHS) - 1))]
            if glyph == " ":
                continue
            x = round(col * cell_w)
            y = round(row * cell_h) - 1
            draw.text((x, y), glyph, font=font, fill=value)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.source, args.output)


if __name__ == "__main__":
    main()
