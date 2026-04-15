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


def evaluate_row(
    ground_truth: GroundTruth,
    predicted: OCRResult,
    detected_tokens: list[dict] | None = None,
    token_count: int = 0,
    annotated_image_path: str | None = None,
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
    )


def summarize(rows: list[EvaluationRow]) -> dict:
    total = len(rows)
    if total == 0:
        return {
            "total_images": 0,
            "number_accuracy": 0.0,
            "class_accuracy": 0.0,
            "joint_accuracy": 0.0,
            "mismatches": [],
        }

    number_hits = sum(1 for row in rows if row.number_match)
    class_hits = sum(1 for row in rows if row.class_match)
    joint_hits = sum(1 for row in rows if row.joint_match)

    mismatches = []
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
            }
        )

    return {
        "total_images": total,
        "number_accuracy": round(number_hits / total, 4),
        "class_accuracy": round(class_hits / total, 4),
        "joint_accuracy": round(joint_hits / total, 4),
        "mismatches": mismatches,
    }
