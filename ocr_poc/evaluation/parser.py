from __future__ import annotations

import os
import re
from dataclasses import dataclass
import json

from ocr_poc.ocr.normalizer import normalize_class, normalize_number

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PATTERN_NUMBER_ONLY = re.compile(r"^(?P<number>[0-9]{1,4})$")
PATTERN_CANONICAL_KEY = re.compile(r"^(?P<class>[A-Z][A-Z0-9-]*|null)::(?P<number>[0-9]{1,4})$")
PATTERN_CANONICAL_CLASS = re.compile(r"^[A-Z][A-Z0-9-]*$")


@dataclass
class GroundTruth:
    image_filename: str
    number_normalized: str | None
    class_normalized: str | None


def build_canonical_key(class_value: str | None, number_value: str | None) -> str | None:
    number_normalized = normalize_number(number_value)
    if number_normalized is None:
        return None

    class_normalized = normalize_canonical_class(class_value)
    class_part = class_normalized if class_normalized is not None else "null"
    return f"{class_part}::{number_normalized}"


def normalize_canonical_class(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    if not cleaned or cleaned == "NULL":
        return None
    cleaned = cleaned.replace(" ", "")
    if not PATTERN_CANONICAL_CLASS.fullmatch(cleaned):
        return None
    return cleaned


def parse_canonical_key(key: str) -> tuple[str | None, str | None]:
    match = PATTERN_CANONICAL_KEY.fullmatch(key)
    if not match:
        return (None, None)

    class_part = match.group("class")
    number_part = match.group("number")
    class_value = None if class_part == "null" else class_part
    return (class_value, number_part)


def load_run_group_mapping(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    key_to_images = payload.get("key_to_images_mapping")
    if not isinstance(key_to_images, dict):
        raise ValueError("run_group_json missing object field 'key_to_images_mapping'")

    image_to_key: dict[str, str] = {}
    invalid_keys: list[str] = []
    invalid_image_entries: list[str] = []

    for key, images in key_to_images.items():
        class_part, number_part = parse_canonical_key(str(key))
        if number_part is None:
            invalid_keys.append(str(key))
            continue

        normalized_key = build_canonical_key(class_part, number_part)
        if normalized_key is None:
            invalid_keys.append(str(key))
            continue

        if not isinstance(images, list):
            invalid_image_entries.append(str(key))
            continue

        for image in images:
            filename = os.path.basename(str(image))
            if not filename:
                invalid_image_entries.append(str(key))
                continue
            image_to_key[filename] = normalized_key

    if invalid_keys:
        raise ValueError(f"run_group_json contains invalid canonical keys: {sorted(invalid_keys)}")
    if invalid_image_entries:
        raise ValueError(
            "run_group_json contains invalid key-to-images entries for keys: "
            f"{sorted(set(invalid_image_entries))}"
        )

    return {
        "run_group": payload.get("run_group"),
        "key_to_images_mapping": {
            build_canonical_key(*parse_canonical_key(str(key))): [os.path.basename(str(item)) for item in images]
            for key, images in key_to_images.items()
            if parse_canonical_key(str(key))[1] is not None and isinstance(images, list)
        },
        "image_to_key": image_to_key,
    }


def load_expected_competitors(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("expected_results_json must contain a list of competitor objects")

    by_key: dict[str, dict] = {}
    duplicates: set[str] = set()

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"expected_results_json item at index {idx} is not an object")

        key = build_canonical_key(item.get("class"), item.get("number"))
        if key is None:
            raise ValueError(
                f"expected_results_json item at index {idx} has invalid number/class values"
            )

        if key in by_key:
            duplicates.add(key)
        by_key[key] = item

    if duplicates:
        raise ValueError(
            "expected_results_json contains duplicate canonical keys: "
            f"{sorted(duplicates)}"
        )

    return by_key


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
