from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class OCRToken:
    text: str
    confidence: float
    bbox: list[list[float]] | None = None


@dataclass
class OCRResult:
    number_raw: str | None
    number_normalized: str | None
    class_raw: str | None
    class_normalized: str | None
    confidence_number: float | None
    confidence_class: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
