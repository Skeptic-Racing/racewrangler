from __future__ import annotations

import os
import re
from dataclasses import dataclass

from ocr_poc.ocr.normalizer import normalize_class, normalize_number

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PATTERN_NUMBER_ONLY = re.compile(r"^(?P<number>[0-9]{1,4})$")


@dataclass
class GroundTruth:
    image_filename: str
    number_normalized: str | None
    class_normalized: str | None


def is_supported_image(path: str) -> bool:
    name = os.path.basename(path)
    if ":Zone.Identifier" in name:
        return False
    return os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS


def parse_ground_truth_from_filename(filename: str) -> GroundTruth:
    stem = os.path.splitext(os.path.basename(filename))[0]

    number: str | None = None
    class_code: str | None = None

    # Precedence 1: NUMBERCLASS (digits prefix, class suffix)
    for idx in range(1, min(5, len(stem))):
        n_part = stem[:idx]
        c_part = stem[idx:]
        if n_part.isdigit() and c_part and c_part[0].isalpha():
            normalized_class = normalize_class(c_part)
            if normalized_class is not None:
                number = n_part
                class_code = c_part
                break

    # Precedence 2: CLASSNUMBER (class prefix, digits suffix)
    if number is None:
        for idx in range(max(1, len(stem) - 4), len(stem)):
            c_part = stem[:idx]
            n_part = stem[idx:]
            if n_part.isdigit() and c_part and c_part[0].isalpha():
                normalized_class = normalize_class(c_part)
                if normalized_class is not None:
                    number = n_part
                    class_code = c_part
                    break

    # Precedence 3: NUMBER only
    if number is None:
        match = PATTERN_NUMBER_ONLY.fullmatch(stem)
        if match:
            number = match.group("number")

    return GroundTruth(
        image_filename=os.path.basename(filename),
        number_normalized=normalize_number(number),
        class_normalized=normalize_class(class_code),
    )
