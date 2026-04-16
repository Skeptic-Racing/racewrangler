from __future__ import annotations

import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from .detectors import OCRDetector
from .normalizer import normalize_class, normalize_number
from .schemas import OCRResult, OCRToken

NUMERIC_TOKEN_RE = re.compile(r"^[0-9]{1,4}$")
CLASS_TOKEN_RE = re.compile(r"^[A-Z0-9-]{1,8}$")
# Pattern to extract a number (1-4 digits) from the start of a token
LEADING_DIGITS_RE = re.compile(r"^([0-9]{1,4})")
TRAILING_DIGITS_RE = re.compile(r"([0-9]{1,4})$")
LEADING_COMBINED_RE = re.compile(r"^([0-9]{1,4})([A-Z][A-Z0-9-]*)$")
TRAILING_COMBINED_RE = re.compile(r"^([A-Z][A-Z0-9-]*)([0-9]{1,4})$")
# Minimum confidence threshold for accepting a candidate
MIN_CONFIDENCE_THRESHOLD = 0.60

# Common OCR confusions for taped/stenciled numbers.
LETTER_TO_DIGIT_MAP = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "B": "8",
}
DIGIT_TO_LETTER_MAP = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "5": "S",
    "6": "G",
    "8": "B",
}

# Alternate ambiguity mapping used as secondary candidates only.
LETTER_TO_DIGIT_ALT_MAP = {
    "B": "6",
}

ROI_SPECS: list[tuple[str, tuple[float, float, float, float]]] = [
    ("roi_center", (0.18, 0.18, 0.88, 0.92)),
    ("roi_right_mid", (0.42, 0.20, 1.00, 0.95)),
    ("roi_lower", (0.15, 0.40, 0.95, 1.00)),
]


@dataclass(frozen=True)
class AllowedKey:
    key: str
    class_value: str | None
    number_value: str


@dataclass
class ProcessOutcome:
    result: OCRResult
    inference_time_ms: int
    preprocessed_image_path: str | None
    detected_tokens: list[OCRToken]


def _save_variant_image(
    image: Image.Image,
    image_path: str,
    variant_name: str,
    debug_dir: str | None,
) -> tuple[str, bool]:
    filename_stem = Path(image_path).stem
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        out_path = os.path.join(debug_dir, f"{filename_stem}.{variant_name}.png")
        image.save(out_path)
        return out_path, False

    with tempfile.NamedTemporaryFile(
        suffix=f".{variant_name}.png",
        prefix=f"rw_ocr_{filename_stem}_",
        delete=False,
    ) as tmp:
        out_path = tmp.name
    image.save(out_path)
    return out_path, True


def build_preprocessed_variants(
    image_path: str,
    debug_dir: str | None = None,
) -> tuple[list[str], list[str], str | None]:
    source = Image.open(image_path).convert("L")
    variants: list[tuple[str, Image.Image]] = []

    auto = ImageOps.autocontrast(source)
    variants.append(("auto", auto))

    thresholded = auto.point(lambda px: 255 if px >= 155 else 0)
    variants.append(("threshold", thresholded))

    sharpened = auto.filter(ImageFilter.SHARPEN)
    variants.append(("sharpen", sharpened))

    inverted = ImageOps.autocontrast(ImageOps.invert(auto))
    variants.append(("invert", inverted))

    variant_paths: list[str] = [image_path]
    cleanup_paths: list[str] = []
    primary_preprocessed_path: str | None = None

    for variant_name, variant in variants:
        variant_path, should_cleanup = _save_variant_image(
            variant,
            image_path,
            variant_name,
            debug_dir,
        )
        variant_paths.append(variant_path)
        if primary_preprocessed_path is None:
            primary_preprocessed_path = variant_path
        if should_cleanup:
            cleanup_paths.append(variant_path)

    source.close()
    return variant_paths, cleanup_paths, primary_preprocessed_path


def build_roi_variants(
    image_path: str,
    debug_dir: str | None = None,
) -> tuple[list[str], list[str]]:
    source = Image.open(image_path).convert("L")
    width, height = source.size
    variant_paths: list[str] = []
    cleanup_paths: list[str] = []

    for roi_name, (x0f, y0f, x1f, y1f) in ROI_SPECS:
        x0 = int(width * x0f)
        y0 = int(height * y0f)
        x1 = int(width * x1f)
        y1 = int(height * y1f)
        x0 = max(0, min(width - 1, x0))
        y0 = max(0, min(height - 1, y0))
        x1 = max(x0 + 1, min(width, x1))
        y1 = max(y0 + 1, min(height, y1))

        crop = source.crop((x0, y0, x1, y1))
        auto = ImageOps.autocontrast(crop)
        threshold = auto.point(lambda px: 255 if px >= 150 else 0)

        for suffix, variant in (("auto", auto), ("threshold", threshold)):
            out_path, should_cleanup = _save_variant_image(
                variant,
                image_path,
                f"{roi_name}.{suffix}",
                debug_dir,
            )
            variant_paths.append(out_path)
            if should_cleanup:
                cleanup_paths.append(out_path)

        crop.close()

    source.close()
    return variant_paths, cleanup_paths


def _merge_tokens(tokens: list[OCRToken]) -> list[OCRToken]:
    best_by_text: dict[str, OCRToken] = {}
    for token in tokens:
        key = token.text.strip().upper()
        if not key:
            continue
        current = best_by_text.get(key)
        if current is None or token.confidence > current.confidence:
            best_by_text[key] = token
    return sorted(best_by_text.values(), key=lambda token: token.confidence, reverse=True)


def _extract_number_from_token(text: str) -> str | None:
    """
    Try to extract a number (1-4 leading digits) from a token.
    Handles combined tokens like "62CSP" -> "62" or "17xB" -> "17".
    """
    match = LEADING_DIGITS_RE.match(text.strip())
    if match:
        return match.group(1)
    return None


def _clean_token(text: str) -> str:
    cleaned = text.strip().upper().replace(" ", "")
    cleaned = re.sub(r"[^A-Z0-9/-]", "", cleaned)
    return cleaned


def _clean_raw_token(text: str) -> str:
    cleaned = text.strip().replace(" ", "")
    cleaned = re.sub(r"[^A-Za-z0-9/-]", "", cleaned)
    return cleaned


def _split_token_chunks(text: str) -> list[str]:
    cleaned = _clean_token(text)
    if not cleaned:
        return []
    chunks = [part for part in cleaned.split("/") if part]
    return chunks if chunks else [cleaned]


def _split_raw_token_chunks(text: str) -> list[str]:
    cleaned = _clean_raw_token(text)
    if not cleaned:
        return []
    chunks = [part for part in cleaned.split("/") if part]
    return chunks if chunks else [cleaned]


def _map_chars(text: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(ch, ch) for ch in text)


def _extract_number_candidates(text: str) -> set[str]:
    candidates: set[str] = set()

    # Raw-first pass: preserve lowercase/uppercase distinctions before normalization.
    for raw_chunk in _split_raw_token_chunks(text):
        raw_lower_b = re.fullmatch(r"b([0-9]{2,3})", raw_chunk)
        if raw_lower_b:
            candidates.add(f"6{raw_lower_b.group(1)}")
            candidates.add(f"8{raw_lower_b.group(1)}")

        if NUMERIC_TOKEN_RE.fullmatch(raw_chunk):
            candidates.add(raw_chunk)

    for chunk in _split_token_chunks(text):
        if NUMERIC_TOKEN_RE.fullmatch(chunk):
            candidates.add(chunk)

        lead = LEADING_DIGITS_RE.match(chunk)
        if lead:
            candidates.add(lead.group(1))

        trail = TRAILING_DIGITS_RE.search(chunk)
        if trail:
            candidates.add(trail.group(1))

        mapped = _map_chars(chunk, LETTER_TO_DIGIT_MAP)
        mapped_alt = _map_chars(mapped, LETTER_TO_DIGIT_ALT_MAP)
        if NUMERIC_TOKEN_RE.fullmatch(mapped):
            candidates.add(mapped)
        if NUMERIC_TOKEN_RE.fullmatch(mapped_alt):
            candidates.add(mapped_alt)

        lead_mapped = LEADING_DIGITS_RE.match(mapped)
        if lead_mapped:
            candidates.add(lead_mapped.group(1))
        lead_mapped_alt = LEADING_DIGITS_RE.match(mapped_alt)
        if lead_mapped_alt:
            candidates.add(lead_mapped_alt.group(1))

        trail_mapped = TRAILING_DIGITS_RE.search(mapped)
        if trail_mapped:
            candidates.add(trail_mapped.group(1))
        trail_mapped_alt = TRAILING_DIGITS_RE.search(mapped_alt)
        if trail_mapped_alt:
            candidates.add(trail_mapped_alt.group(1))

    return {candidate for candidate in candidates if normalize_number(candidate) is not None}


def _extract_class_candidates(text: str) -> set[str]:
    candidates: set[str] = set()

    raw_chunks = _split_raw_token_chunks(text)
    number_like_raw_chunks = {
        raw_chunk
        for raw_chunk in raw_chunks
        if re.fullmatch(r"[a-z][0-9]{2,3}", raw_chunk)
    }

    for chunk in _split_token_chunks(text):
        if any(chunk == raw_chunk.upper() for raw_chunk in number_like_raw_chunks):
            continue
        parts = [
            re.sub(r"^[0-9]+", "", chunk),
            re.sub(r"[0-9]+$", "", chunk),
            _map_chars(re.sub(r"^[0-9]+", "", chunk), DIGIT_TO_LETTER_MAP),
            _map_chars(re.sub(r"[0-9]+$", "", chunk), DIGIT_TO_LETTER_MAP),
        ]

        for part in parts:
            cleaned = re.sub(r"[^A-Z0-9-]", "", part)
            if not cleaned or not CLASS_TOKEN_RE.fullmatch(cleaned):
                continue
            normalized = normalize_class(cleaned)
            if normalized is None:
                continue
            # Class tokens with digits are usually split failures (e.g. N62).
            if any(char.isdigit() for char in normalized):
                continue
            candidates.add(normalized)

    return candidates


def _extract_pair_candidates(text: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()

    for chunk in _split_token_chunks(text):
        for candidate in (chunk, _map_chars(chunk, LETTER_TO_DIGIT_MAP), _map_chars(chunk, DIGIT_TO_LETTER_MAP)):
            lead = LEADING_COMBINED_RE.match(candidate)
            if lead:
                number = normalize_number(lead.group(1))
                class_code = normalize_class(lead.group(2))
                if number and class_code and not any(char.isdigit() for char in class_code):
                    pairs.add((number, class_code))

            trail = TRAILING_COMBINED_RE.match(candidate)
            if trail:
                class_code = normalize_class(trail.group(1))
                number = normalize_number(trail.group(2))
                if number and class_code and not any(char.isdigit() for char in class_code):
                    pairs.add((number, class_code))

    return pairs


def _extract_class_from_token(text: str) -> str | None:
    """
    Try to extract a class from a token by removing leading digits and cleaning.
    Handles combined tokens like "62CSP" -> "CSP" or "23EST" -> "EST".
    Also handles "/" delimiters like "BSP/MUSTANG" -> "BSP".
    """
    candidates = _extract_class_candidates(text)
    if not candidates:
        return None
    # Prefer shorter class tokens; they are less likely to include extra livery text.
    return sorted(candidates, key=lambda item: (len(item), item))[0]


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
            nums = _extract_number_candidates(token.text)
            for num in nums:
                candidates.append((num, token.confidence))
    
    # Phase 2: Look for pure number tokens (fallback)
    if not candidates:
        for token in tokens:
            if token.confidence >= MIN_CONFIDENCE_THRESHOLD:
                stripped = _clean_token(token.text)
                mapped = _map_chars(stripped, LETTER_TO_DIGIT_MAP)
                if NUMERIC_TOKEN_RE.fullmatch(stripped):
                    candidates.append((stripped, token.confidence + 0.02))
                if NUMERIC_TOKEN_RE.fullmatch(mapped):
                    candidates.append((mapped, token.confidence))
    
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
            classes = _extract_class_candidates(token.text)
            for cls in classes:
                candidates.append((cls, token.confidence))
    
    # Phase 2: Look for pure class tokens (fallback)
    if not candidates:
        for token in tokens:
            if token.confidence >= MIN_CONFIDENCE_THRESHOLD:
                cleaned = _clean_token(token.text)
                if CLASS_TOKEN_RE.fullmatch(cleaned):
                    normalized = normalize_class(cleaned)
                    if normalized and not any(char.isdigit() for char in normalized):
                        candidates.append((normalized, token.confidence))
    
    if not candidates:
        return None, None
    
    # Score by: confidence first (higher is better), then shorter length (less likely stray text)
    best = max(candidates, key=lambda c: (c[1], -len(c[0])))
    return best[0], best[1]


def _pick_best_from_allowed_keys(
    tokens: list[OCRToken],
    allowed_keys: list[AllowedKey],
) -> tuple[str | None, str | None, float | None, float | None]:
    if not tokens or not allowed_keys:
        return (None, None, None, None)

    def _bbox_center(token: OCRToken) -> tuple[float, float] | None:
        if not token.bbox or len(token.bbox) < 4:
            return None
        xs = [point[0] for point in token.bbox]
        ys = [point[1] for point in token.bbox]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _bbox_span(token: OCRToken) -> tuple[float, float] | None:
        if not token.bbox or len(token.bbox) < 4:
            return None
        xs = [point[0] for point in token.bbox]
        ys = [point[1] for point in token.bbox]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        if width <= 0 or height <= 0:
            return None
        return (width, height)

    def _number_token_quality(token: OCRToken, expected_number: str) -> float:
        cleaned = _clean_token(token.text)
        mapped = _map_chars(cleaned, LETTER_TO_DIGIT_MAP)
        if cleaned == expected_number:
            return 1.0
        if mapped == expected_number:
            return 0.86
        if expected_number in cleaned:
            return 0.94 if any(char.isalpha() for char in cleaned) else 0.98
        if expected_number in mapped:
            return 0.82
        return 0.76

    def _soft_number_match_score(expected_number: str, candidate_number: str) -> float:
        if expected_number == candidate_number:
            return 1.0
        if len(candidate_number) >= 2 and expected_number.endswith(candidate_number):
            return 0.62 * (len(candidate_number) / len(expected_number))
        if len(expected_number) >= 2 and candidate_number.endswith(expected_number):
            return 0.56 * (len(expected_number) / len(candidate_number))
        if len(candidate_number) >= 2 and expected_number.startswith(candidate_number):
            return 0.46 * (len(candidate_number) / len(expected_number))
        return 0.0

    def _class_token_quality(token: OCRToken, expected_class: str) -> float:
        cleaned = _clean_token(token.text)
        mapped = _map_chars(cleaned, DIGIT_TO_LETTER_MAP)
        if cleaned == expected_class:
            return 1.0
        if mapped == expected_class:
            return 0.86
        if cleaned.startswith(expected_class) or cleaned.endswith(expected_class):
            return 0.92
        if expected_class in cleaned:
            return 0.88
        if expected_class in mapped:
            return 0.82
        if len(cleaned) > max(8, len(expected_class) + 4):
            return 0.74
        return 0.78

    def _soft_class_match_score(expected_class: str, candidate_class: str) -> float:
        if expected_class == candidate_class:
            return 1.0
        if expected_class.startswith(candidate_class) or expected_class.endswith(candidate_class):
            return 0.58
        if candidate_class.startswith(expected_class) or candidate_class.endswith(expected_class):
            return 0.54
        return 0.0

    def _pair_spatial_bonus(number_token: OCRToken, class_token: OCRToken) -> float:
        n_center = _bbox_center(number_token)
        c_center = _bbox_center(class_token)
        n_span = _bbox_span(number_token)
        c_span = _bbox_span(class_token)
        if n_center is None or c_center is None or n_span is None or c_span is None:
            return 0.0

        avg_width = max(1.0, (n_span[0] + c_span[0]) / 2.0)
        avg_height = max(1.0, (n_span[1] + c_span[1]) / 2.0)
        dx_norm = abs(n_center[0] - c_center[0]) / (2.2 * avg_width)
        dy_norm = abs(n_center[1] - c_center[1]) / (1.4 * avg_height)

        proximity_score = max(0.0, 1.0 - min(1.0, dx_norm)) * max(0.0, 1.0 - min(1.0, dy_norm))
        span_ratio_w = min(n_span[0], c_span[0]) / max(n_span[0], c_span[0])
        span_ratio_h = min(n_span[1], c_span[1]) / max(n_span[1], c_span[1])
        size_score = (span_ratio_w + span_ratio_h) / 2.0
        return (0.42 * proximity_score) + (0.18 * size_score)

    best_key: AllowedKey | None = None
    best_total = 0.0
    best_number_conf = 0.0
    best_class_conf = 0.0

    for allowed in allowed_keys:
        number_conf = 0.0
        class_conf = 0.0
        pair_conf = 0.0
        number_match_tokens: list[OCRToken] = []
        class_match_tokens: list[OCRToken] = []

        for token in tokens:
            if token.confidence < 0.45:
                continue
            number_candidates = _extract_number_candidates(token.text)
            class_candidates = _extract_class_candidates(token.text)
            pair_candidates = _extract_pair_candidates(token.text)

            if allowed.number_value in number_candidates:
                weighted_number = token.confidence * _number_token_quality(token, allowed.number_value)
                number_conf = max(number_conf, weighted_number)
                number_match_tokens.append(token)
            else:
                soft_number = max(
                    (
                        token.confidence
                        * _soft_number_match_score(allowed.number_value, candidate_number)
                    )
                    for candidate_number in number_candidates
                ) if number_candidates else 0.0
                if soft_number > 0:
                    number_conf = max(number_conf, soft_number)
                    number_match_tokens.append(token)

            if allowed.class_value is not None and allowed.class_value in class_candidates:
                weighted_class = token.confidence * _class_token_quality(token, allowed.class_value)
                class_conf = max(class_conf, weighted_class)
                class_match_tokens.append(token)
            elif allowed.class_value is not None and class_candidates:
                soft_class = max(
                    (
                        token.confidence
                        * _soft_class_match_score(allowed.class_value, candidate_class)
                    )
                    for candidate_class in class_candidates
                )
                if soft_class > 0:
                    class_conf = max(class_conf, soft_class)
                    class_match_tokens.append(token)

            if allowed.class_value is not None and (allowed.number_value, allowed.class_value) in pair_candidates:
                pair_conf = max(pair_conf, token.confidence)

        spatial_bonus = 0.0
        if allowed.class_value is not None and number_match_tokens and class_match_tokens:
            spatial_bonus = max(
                _pair_spatial_bonus(number_token, class_token)
                for number_token in number_match_tokens
                for class_token in class_match_tokens
            )

        if allowed.class_value is None:
            total = (1.95 * number_conf) + (0.45 * pair_conf)
        else:
            total = (1.75 * number_conf) + (1.25 * class_conf) + (2.2 * pair_conf) + spatial_bonus

        if total > best_total:
            best_total = total
            best_key = allowed
            best_number_conf = max(number_conf, pair_conf)
            best_class_conf = max(class_conf, pair_conf)

    if best_key is None or best_total < 0.9:
        return (None, None, None, None)

    return (
        best_key.number_value,
        best_key.class_value,
        round(best_number_conf, 4) if best_number_conf > 0 else None,
        round(best_class_conf, 4) if best_key.class_value is not None and best_class_conf > 0 else None,
    )


def process_image(
    image_path: str,
    detector: OCRDetector,
    debug_dir: str | None = None,
    allowed_keys: list[AllowedKey] | None = None,
) -> ProcessOutcome:
    variant_paths, cleanup_paths, primary_preprocessed_path = build_preprocessed_variants(
        image_path,
        debug_dir=debug_dir,
    )

    start = time.time()
    all_tokens: list[OCRToken] = []
    for variant_path in variant_paths:
        all_tokens.extend(detector.detect(variant_path))

    # Hard-image fallback: when few tokens are found, probe likely number plate regions.
    if len(all_tokens) < 4:
        roi_paths, roi_cleanup_paths = build_roi_variants(image_path, debug_dir=debug_dir)
        for roi_path in roi_paths:
            all_tokens.extend(detector.detect(roi_path))
        cleanup_paths.extend(roi_cleanup_paths)

    elapsed_ms = int((time.time() - start) * 1000)
    tokens = _merge_tokens(all_tokens)

    for temp_path in cleanup_paths:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    number_raw: str | None
    class_raw: str | None
    confidence_number: float | None
    confidence_class: float | None

    constrained = _pick_best_from_allowed_keys(tokens, allowed_keys or [])
    if constrained[0] is not None:
        number_raw, class_raw, confidence_number, confidence_class = constrained
    else:
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
        preprocessed_image_path=primary_preprocessed_path if debug_dir else None,
        detected_tokens=tokens,
    )
