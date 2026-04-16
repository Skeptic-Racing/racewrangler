from __future__ import annotations

from dataclasses import dataclass

from ocr_poc.evaluation.parser import GroundTruth
from ocr_poc.ocr.schemas import OCRResult


@dataclass
class EvaluationRow:
    image_filename: str
    expected_number: str | None
    predicted_number: str | None
    expected_class: str | None
    predicted_class: str | None
    confidence_number: float | None
    confidence_class: float | None
    number_match: bool
    class_match: bool
    joint_match: bool
    token_count: int
    detected_tokens: list[dict]
    annotated_image_path: str | None
    expected_key: str | None
    predicted_key: str | None
    key_match: bool | None
    candidate_suggestions: list[dict]


def evaluate_row(
    ground_truth: GroundTruth,
    predicted: OCRResult,
    detected_tokens: list[dict] | None = None,
    token_count: int = 0,
    annotated_image_path: str | None = None,
    expected_key: str | None = None,
    predicted_key: str | None = None,
    candidate_suggestions: list[dict] | None = None,
) -> EvaluationRow:
    number_match = ground_truth.number_normalized == predicted.number_normalized
    class_match = ground_truth.class_normalized == predicted.class_normalized
    joint_match = number_match and class_match
    return EvaluationRow(
        image_filename=ground_truth.image_filename,
        expected_number=ground_truth.number_normalized,
        predicted_number=predicted.number_normalized,
        expected_class=ground_truth.class_normalized,
        predicted_class=predicted.class_normalized,
        confidence_number=predicted.confidence_number,
        confidence_class=predicted.confidence_class,
        number_match=number_match,
        class_match=class_match,
        joint_match=joint_match,
        token_count=token_count,
        detected_tokens=detected_tokens or [],
        annotated_image_path=annotated_image_path,
        expected_key=expected_key,
        predicted_key=predicted_key,
        key_match=(expected_key == predicted_key) if expected_key is not None else None,
        candidate_suggestions=candidate_suggestions or [],
    )


def suggest_candidate_keys(
    predicted_number: str | None,
    predicted_class: str | None,
    candidate_keys: list[str],
    limit: int = 3,
) -> list[dict]:
    def parse_key(key: str) -> tuple[str | None, str | None]:
        if "::" not in key:
            return (None, None)
        class_part, number_part = key.split("::", 1)
        return (None if class_part == "null" else class_part, number_part)

    ranked: list[tuple[tuple[int, int, int, str], dict]] = []
    for key in candidate_keys:
        class_part, number_part = parse_key(key)
        number_match = predicted_number is not None and number_part == predicted_number
        class_match = predicted_class is not None and class_part == predicted_class
        predicted_has_class = 1 if predicted_class is not None else 0
        score = (1 if number_match else 0, 1 if class_match else 0, predicted_has_class, key)
        reason_parts = []
        if number_match:
            reason_parts.append("number_match")
        if class_match:
            reason_parts.append("class_match")
        if not reason_parts:
            reason_parts.append("fallback")
        ranked.append(
            (
                score,
                {
                    "key": key,
                    "reason": "+".join(reason_parts),
                    "number_match": number_match,
                    "class_match": class_match,
                },
            )
        )

    ranked.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[0][3]))
    return [item[1] for item in ranked[:limit]]


def summarize_per_key(rows: list[EvaluationRow]) -> dict:
    grouped: dict[str, list[EvaluationRow]] = {}
    for row in rows:
        if row.expected_key is None:
            continue
        grouped.setdefault(row.expected_key, []).append(row)

    if not grouped:
        return {
            "total_keys": 0,
            "any_hit_accuracy": 0.0,
            "best_confidence_accuracy": 0.0,
            "keys": [],
        }

    any_hits = 0
    best_hits = 0
    key_rows: list[dict] = []

    for key in sorted(grouped.keys()):
        items = grouped[key]
        hit_count = sum(1 for item in items if item.key_match is True)
        any_hit = hit_count > 0
        if any_hit:
            any_hits += 1

        best_row = max(
            items,
            key=lambda item: (item.confidence_number or 0.0) + (item.confidence_class or 0.0),
        )
        best_hit = best_row.key_match is True
        if best_hit:
            best_hits += 1

        key_rows.append(
            {
                "expected_key": key,
                "image_count": len(items),
                "hit_count": hit_count,
                "any_hit": any_hit,
                "best_confidence_hit": best_hit,
                "best_confidence_image": best_row.image_filename,
                "best_confidence_predicted_key": best_row.predicted_key,
            }
        )

    total_keys = len(grouped)
    return {
        "total_keys": total_keys,
        "any_hit_accuracy": round(any_hits / total_keys, 4),
        "best_confidence_accuracy": round(best_hits / total_keys, 4),
        "keys": key_rows,
    }


def summarize(rows: list[EvaluationRow]) -> dict:
    total = len(rows)
    if total == 0:
        return {
            "total_images": 0,
            "number_accuracy": 0.0,
            "class_accuracy": 0.0,
            "joint_accuracy": 0.0,
            "mismatches": [],
            "key_accuracy": 0.0,
            "per_image_key_accuracy": 0.0,
            "misidentification_rate": 0.0,
            "abstain_rate": 0.0,
        }

    number_hits = sum(1 for row in rows if row.number_match)
    class_hits = sum(1 for row in rows if row.class_match)
    joint_hits = sum(1 for row in rows if row.joint_match)

    mismatches = []
    key_rows = [row for row in rows if row.expected_key is not None]
    key_hits = sum(1 for row in key_rows if row.key_match is True)
    misidentified = sum(
        1
        for row in key_rows
        if row.predicted_key is not None and row.predicted_key != row.expected_key
    )
    abstained = sum(1 for row in key_rows if row.predicted_key is None)
    for row in rows:
        if row.joint_match:
            continue
        if not row.number_match and not row.class_match:
            category = "number_and_class"
        elif not row.number_match:
            category = "number_only"
        else:
            category = "class_only"
        mismatches.append(
            {
                "image_filename": row.image_filename,
                "category": category,
                "expected_number": row.expected_number,
                "predicted_number": row.predicted_number,
                "expected_class": row.expected_class,
                "predicted_class": row.predicted_class,
                "confidence_number": row.confidence_number,
                "confidence_class": row.confidence_class,
                "expected_key": row.expected_key,
                "predicted_key": row.predicted_key,
                "candidate_suggestions": row.candidate_suggestions,
            }
        )

    return {
        "total_images": total,
        "number_accuracy": round(number_hits / total, 4),
        "class_accuracy": round(class_hits / total, 4),
        "joint_accuracy": round(joint_hits / total, 4),
        "key_accuracy": round(key_hits / len(key_rows), 4) if key_rows else 0.0,
        "per_image_key_accuracy": round(key_hits / len(key_rows), 4) if key_rows else 0.0,
        "misidentification_rate": round(misidentified / len(key_rows), 4) if key_rows else 0.0,
        "abstain_rate": round(abstained / len(key_rows), 4) if key_rows else 0.0,
        "mismatches": mismatches,
        "per_key": summarize_per_key(rows),
    }
