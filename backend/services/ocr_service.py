"""
OCR service — wraps ocr_poc for use by the FastAPI backend.

On the Pi 5, PaddleOCR is available and the full pipeline runs.
On a dev machine without PaddleOCR, the MockDetector is used and every
timing event lands in needs_review (correct behavior for wiring tests).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import asdict
from typing import Optional

# Make ocr_poc importable regardless of working directory.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from ocr_poc.ocr.detectors import MockDetector, OCRDetector, PaddleOCRDetector
from ocr_poc.ocr.processor import AllowedKey, process_image
from ocr_poc.ocr.schemas import OCRResult

# Singleton detector, initialized once at startup.
_detector: OCRDetector | None = None


def initialize_ocr() -> None:
    """Load OCR engine at startup. Falls back to MockDetector if PaddleOCR is absent."""
    global _detector
    try:
        _detector = PaddleOCRDetector()
        print("✓ PaddleOCR initialized")
    except (RuntimeError, ImportError) as exc:
        _detector = MockDetector()
        print(f"⚠ PaddleOCR unavailable ({exc}); using MockDetector — all events will need review")


def _detector_ready() -> OCRDetector:
    if _detector is None:
        # Fallback: if called before initialize_ocr (e.g. in tests), use mock.
        return MockDetector()
    return _detector


def run_ocr(
    image_bytes: bytes,
    run_group_candidates: list[dict],  # [{"competitor_id": str, "number": str, "class_code": str}]
    timeout_seconds: float = 10.0,
) -> dict:
    """
    Run OCR on a timing photo.

    Returns a dict with keys:
        number_normalized, class_normalized, confidence_number, confidence_class,
        match_status ("auto" | "tentative" | "needs_review"),
        matched_competitor_id (str | None),
        ocr_result (the raw OCRResult as a dict),
        inference_time_ms (int)

    Never raises — all exceptions are caught and result in needs_review.
    """
    try:
        return _run_ocr_inner(image_bytes, run_group_candidates, timeout_seconds)
    except Exception as exc:
        return {
            "number_normalized": None,
            "class_normalized": None,
            "confidence_number": None,
            "confidence_class": None,
            "match_status": "needs_review",
            "matched_competitor_id": None,
            "ocr_result": {"error": str(exc)},
            "inference_time_ms": 0,
        }


def _run_ocr_inner(
    image_bytes: bytes,
    run_group_candidates: list[dict],
    timeout_seconds: float,
) -> dict:
    # Write image to a temp file — PaddleOCR requires a file path.
    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        allowed_keys = [
            AllowedKey(
                key=c["competitor_id"],
                class_value=c.get("class_code"),
                number_value=c["number"],
            )
            for c in run_group_candidates
        ]

        start = time.time()
        outcome = process_image(
            image_path=tmp_path,
            detector=_detector_ready(),
            allowed_keys=allowed_keys if allowed_keys else None,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        result: OCRResult = outcome.result
        match_status, matched_id = _apply_matching_policy(result, run_group_candidates)

        return {
            "number_normalized": result.number_normalized,
            "class_normalized": result.class_normalized,
            "confidence_number": result.confidence_number,
            "confidence_class": result.confidence_class,
            "match_status": match_status,
            "matched_competitor_id": matched_id,
            "ocr_result": asdict(result),
            "inference_time_ms": elapsed_ms,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _apply_matching_policy(
    result: OCRResult,
    candidates: list[dict],
) -> tuple[str, Optional[str]]:
    """
    Apply the matching policy from matching-policy-specification.md.
    Returns (match_status, competitor_id | None).
    """
    num = result.number_normalized
    conf_num = result.confidence_number or 0.0

    if not num or conf_num < 0.50:
        return "needs_review", None

    matching = [c for c in candidates if c["number"] == num]

    if len(matching) == 0:
        return "needs_review", None

    if len(matching) == 1:
        # Single number match — route by confidence.
        competitor_id = matching[0]["competitor_id"]
        if conf_num >= 0.80:
            return "auto", competitor_id
        return "tentative", competitor_id

    # Multiple competitors with the same number — use class to disambiguate.
    cls = result.class_normalized
    conf_cls = result.confidence_class or 0.0

    if cls and conf_cls >= 0.70:
        class_match = [c for c in matching if c.get("class_code") == cls]
        if len(class_match) == 1:
            status = "auto" if conf_num >= 0.80 else "tentative"
            return status, class_match[0]["competitor_id"]

    return "needs_review", None
