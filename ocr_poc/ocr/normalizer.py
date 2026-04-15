from __future__ import annotations

import re

NUMBER_RE = re.compile(r"^[0-9]{1,4}$")
CLASS_ALLOWED_RE = re.compile(r"^[A-Z0-9-]{1,8}$")


def normalize_number(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip()
    if not NUMBER_RE.fullmatch(cleaned):
        return None
    return cleaned


def normalize_class(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip().upper().replace(" ", "")
    cleaned = re.sub(r"[^A-Z0-9-]", "", cleaned)
    if not cleaned:
        return None

    # Canonical CAM class formatting.
    if cleaned in {"CAMC", "CAM-C"}:
        cleaned = "CAM-C"
    elif cleaned in {"CAMS", "CAM-S"}:
        cleaned = "CAM-S"
    elif cleaned in {"CAMT", "CAM-T"}:
        cleaned = "CAM-T"

    if not CLASS_ALLOWED_RE.fullmatch(cleaned):
        return None
    if len(cleaned) > 4 and cleaned not in {"CAM-C", "CAM-S", "CAM-T"}:
        return None
    return cleaned
