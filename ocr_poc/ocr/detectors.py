from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .schemas import OCRToken


class OCRDetector(ABC):
    @abstractmethod
    def detect(self, image_path: str) -> list[OCRToken]:
        raise NotImplementedError


class MockDetector(OCRDetector):
    """Fallback detector that returns no tokens, useful for wiring tests."""

    def detect(self, image_path: str) -> list[OCRToken]:
        return []


class PaddleOCRDetector(OCRDetector):
    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Install ocr_poc/requirements.txt first."
            ) from exc

        # Angle classification is important for skewed class/number text.
        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def detect(self, image_path: str) -> list[OCRToken]:
        raw_result: Any = self._ocr.ocr(image_path, cls=True)
        tokens: list[OCRToken] = []

        if not raw_result:
            return tokens

        lines = raw_result[0] if isinstance(raw_result, list) else raw_result
        for line in lines or []:
            if not line or len(line) < 2:
                continue
            box_info = line[0]
            text_info = line[1]
            if not text_info or len(text_info) < 2:
                continue
            text = str(text_info[0]).strip()
            confidence = float(text_info[1])
            if text:
                bbox: list[list[float]] | None = None
                if isinstance(box_info, (list, tuple)):
                    bbox = []
                    for point in box_info:
                        if isinstance(point, (list, tuple)) and len(point) == 2:
                            bbox.append([float(point[0]), float(point[1])])
                    if len(bbox) < 4:
                        bbox = None

                tokens.append(
                    OCRToken(
                        text=text,
                        confidence=max(0.0, min(1.0, confidence)),
                        bbox=bbox,
                    )
                )

        return tokens


def build_detector(engine: str) -> OCRDetector:
    lowered = engine.strip().lower()
    if lowered == "paddle":
        return PaddleOCRDetector()
    if lowered == "mock":
        return MockDetector()
    raise ValueError(f"Unsupported OCR engine: {engine}")
