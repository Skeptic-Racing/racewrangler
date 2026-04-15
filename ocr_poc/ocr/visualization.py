from __future__ import annotations

import os

from PIL import Image, ImageDraw

from .schemas import OCRToken


def save_annotated_image(
    image_path: str,
    tokens: list[OCRToken],
    output_path: str,
) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for token in tokens:
        if not token.bbox or len(token.bbox) < 4:
            continue

        polygon = [(float(x), float(y)) for x, y in token.bbox]
        draw.polygon(polygon, outline=(255, 0, 0), width=3)

        label = f"{token.text} ({token.confidence:.2f})"
        tx, ty = polygon[0]
        text_pos = (tx, max(0.0, ty - 14.0))
        draw.text(text_pos, label, fill=(255, 0, 0))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)
