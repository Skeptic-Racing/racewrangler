from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass

from PIL import Image, ImageOps

from .detectors import OCRDetector
from .normalizer import normalize_class, normalize_number
from .schemas import OCRResult, OCRToken

NUMERIC_TOKEN_RE = re.compile(r"^[0-9]{1,4}$")
CLASS_TOKEN_RE = re.compile(r"^[A-Z0-9-]{1,8}$")
# Pattern to extract a number (1-4 digits) from the start of a token
LEADING_DIGITS_RE = re.compile(r"^([0-9]{1,4})")
# Minimum confidence threshold for accepting a candidate
MIN_CONFIDENCE_THRESHOLD = 0.75


@dataclass
class ProcessOutcome:
    result: OCRResult
    inference_time_ms: int
    preprocessed_image_path: str | None
    detected_tokens: list[OCRToken]


def preprocess_image(image_path: str, debug_dir: str | None = None) -> str:
    image = Image.open(image_path).convert("L")
    image = ImageOps.autocontrast(image)

    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        out_path = os.path.join(debug_dir, f"{os.path.basename(image_path)}.preprocessed.png")
        image.save(out_path)
        return out_path

    return image_path


def _extract_number_from_token(text: str) -> str | None:
    """
    Try to extract a number (1-4 leading digits) from a token.
    Handles combined tokens like "62CSP" -> "62" or "17xB" -> "17".
    """
    match = LEADING_DIGITS_RE.match(text.strip())
    if match:
        return match.group(1)
    return None


def _extract_class_from_token(text: str) -> str | None:
    """
    Try to extract a class from a token by removing leading digits and cleaning.
    Handles combined tokens like "62CSP" -> "CSP" or "23EST" -> "EST".
    Also handles "/" delimiters like "BSP/MUSTANG" -> "BSP".
    """
    # Remove leading digits
    without_digits = re.sub(r"^[0-9]+", "", text.strip())
    
    # If there's a "/" delimiter, try to use just the first part (likely the class)
    if "/" in without_digits:
        parts = without_digits.split("/")
        without_digits = parts[0]
    
    # Clean up: uppercase, remove spaces and non-alphanumeric (except hyphens)
    cleaned = without_digits.upper().replace(" ", "")
    cleaned = re.sub(r"[^A-Z0-9-]", "", cleaned)
    # Verify it matches class pattern
    if cleaned and CLASS_TOKEN_RE.fullmatch(cleaned):
        return cleaned
    return None


def _pick_best_number(tokens: list[OCRToken]) -> tuple[str | None, float | None]:
    """
    Pick the best number from tokens using a multi-phase approach:
    1. First, try to extract numbers from combined tokens (e.g., "62CSP" -> "62")
    2. Then, look for pure number tokens
    3. Filter by confidence threshold and prefer shorter, more specific matches
    """
    candidates: list[tuple[str, float]] = []
    
    # Phase 1: Look for numbers in combined tokens (highest priority)
    for token in tokens:
        if token.confidence >= MIN_CONFIDENCE_THRESHOLD:
            num = _extract_number_from_token(token.text)
            if num:
                candidates.append((num, token.confidence))
    
    # Phase 2: Look for pure number tokens (fallback)
    if not candidates:
        for token in tokens:
            if token.confidence >= MIN_CONFIDENCE_THRESHOLD:
                stripped = token.text.strip().replace(" ", "")
                if NUMERIC_TOKEN_RE.fullmatch(stripped):
                    candidates.append((stripped, token.confidence))
    
    if not candidates:
        return None, None
    
    # Score by: confidence first (higher is better), then shorter length (less likely stray text)
    best = max(candidates, key=lambda c: (c[1], -len(c[0])))
    return best[0], best[1]


def _pick_best_class(tokens: list[OCRToken]) -> tuple[str | None, float | None]:
    """
    Pick the best class from tokens using a multi-phase approach:
    1. First, try to extract classes from combined tokens (e.g., "62CSP" -> "CSP")
    2. Then, look for pure class tokens
    3. Filter by confidence threshold and prefer shorter, more specific matches
    """
    candidates: list[tuple[str, float]] = []
    
    # Phase 1: Look for classes in combined tokens (highest priority)
    for token in tokens:
        if token.confidence >= MIN_CONFIDENCE_THRESHOLD:
            cls = _extract_class_from_token(token.text)
            if cls:
                candidates.append((cls, token.confidence))
    
    # Phase 2: Look for pure class tokens (fallback)
    if not candidates:
        for token in tokens:
            if token.confidence >= MIN_CONFIDENCE_THRESHOLD:
                cleaned = token.text.upper().replace(" ", "")
                cleaned = re.sub(r"[^A-Z0-9-]", "", cleaned)
                if CLASS_TOKEN_RE.fullmatch(cleaned):
                    normalized = normalize_class(cleaned)
                    if normalized:
                        candidates.append((cleaned, token.confidence))
    
    if not candidates:
        return None, None
    
    # Score by: confidence first (higher is better), then shorter length (less likely stray text)
    best = max(candidates, key=lambda c: (c[1], -len(c[0])))
    return best[0], best[1]


def process_image(
    image_path: str,
    detector: OCRDetector,
    debug_dir: str | None = None,
) -> ProcessOutcome:
    preprocessed = preprocess_image(image_path, debug_dir=debug_dir)

    start = time.time()
    tokens = detector.detect(preprocessed)
    elapsed_ms = int((time.time() - start) * 1000)

    number_raw, confidence_number = _pick_best_number(tokens)
    class_raw, confidence_class = _pick_best_class(tokens)

    result = OCRResult(
        number_raw=number_raw,
        number_normalized=normalize_number(number_raw),
        class_raw=class_raw,
        class_normalized=normalize_class(class_raw),
        confidence_number=confidence_number,
        confidence_class=confidence_class,
    )

    return ProcessOutcome(
        result=result,
        inference_time_ms=elapsed_ms,
        preprocessed_image_path=preprocessed if debug_dir else None,
        detected_tokens=tokens,
    )
