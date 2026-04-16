from __future__ import annotations

import json
import os


def write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def write_markdown_summary(path: str, summary: dict, image_dir: str | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# OCR Evaluation Summary",
        "",
        f"- Total images: {summary.get('total_images', 0)}",
        f"- Per-image key accuracy (primary): {summary.get('per_image_key_accuracy', summary.get('key_accuracy', 0.0))}",
        f"- Misidentification rate (primary): {summary.get('misidentification_rate', 0.0)}",
        f"- Abstain rate (no key predicted): {summary.get('abstain_rate', 0.0)}",
        f"- Number accuracy: {summary.get('number_accuracy', 0.0)}",
        f"- Class accuracy: {summary.get('class_accuracy', 0.0)}",
        f"- Joint accuracy: {summary.get('joint_accuracy', 0.0)}",
        f"- Key accuracy: {summary.get('key_accuracy', 0.0)}",
        "",
    ]

    run_group = summary.get("run_group")
    if run_group:
        lines.extend([f"- Run group: {run_group}", ""])

    expected_validation = summary.get("expected_results_validation", {})
    if expected_validation.get("checked"):
        lines.extend(["## Expected Results Validation", ""])
        missing = expected_validation.get("missing_in_expected_results", [])
        unexpected = expected_validation.get("unexpected_expected_results_keys", [])
        lines.append(f"- Missing keys in expected results: {len(missing)}")
        for key in missing:
            lines.append(f"  - {key}")
        lines.append(f"- Unexpected keys in expected results: {len(unexpected)}")
        for key in unexpected:
            lines.append(f"  - {key}")
        lines.append("")

    no_text_images: list[str] = []

    evaluations = summary.get("evaluations", [])
    if not evaluations:
        lines.extend(["## Per-Image Results", "", "No per-image rows found."])
    else:
        for item in evaluations:
            if int(item.get("token_count", 0)) == 0:
                no_text_images.append(str(item.get("image_filename")))

        lines.extend(["## Images With No Detected Text", ""])
        if no_text_images:
            for name in no_text_images:
                lines.append(f"- {name}")
        else:
            lines.append("- None")

        lines.extend(["", "## Per-Image Results", ""])

        for item in evaluations:
            filename = item.get("image_filename")
            image_ref = filename
            annotated_ref: str | None = None

            if image_dir:
                image_ref = os.path.relpath(
                    os.path.join(image_dir, filename),
                    start=os.path.dirname(path),
                )

            annotated_path = item.get("annotated_image_path")
            if annotated_path:
                annotated_ref = os.path.relpath(
                    annotated_path,
                    start=os.path.dirname(path),
                )

            lines.extend(
                [
                    f"### {filename}",
                    "",
                    f"- Original image: ![{filename}]({image_ref})",
                    "",
                ]
            )

            if annotated_ref:
                lines.extend(
                    [
                        f"- Annotated detections: ![{filename} annotated]({annotated_ref})",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"- Expected number: {item.get('expected_number')}",
                    f"- Predicted number: {item.get('predicted_number')}",
                    f"- Number confidence: {item.get('confidence_number')}",
                    f"- Expected class: {item.get('expected_class')}",
                    f"- Predicted class: {item.get('predicted_class')}",
                    f"- Class confidence: {item.get('confidence_class')}",
                    f"- Expected key: {item.get('expected_key')}",
                    f"- Predicted key: {item.get('predicted_key')}",
                    f"- Key match: {item.get('key_match')}",
                    f"- Number match: {item.get('number_match')}",
                    f"- Class match: {item.get('class_match')}",
                    f"- Joint match: {item.get('joint_match')}",
                    f"- Raw detected token count: {item.get('token_count')}",
                    "",
                ]
            )

            tokens = item.get("detected_tokens", [])
            if not tokens:
                lines.append("- Raw detected tokens: none")
                lines.append("")
            else:
                lines.append("- Raw detected tokens:")
                for token in tokens:
                    lines.append(
                        f"  - {token.get('text')} (confidence={token.get('confidence')}, bbox={token.get('bbox')})"
                    )
                lines.append("")

            suggestions = item.get("candidate_suggestions", [])
            if suggestions:
                lines.append("- Candidate suggestions:")
                for suggestion in suggestions:
                    lines.append(
                        "  - "
                        f"{suggestion.get('key')} "
                        f"(reason={suggestion.get('reason')}, "
                        f"number_match={suggestion.get('number_match')}, "
                        f"class_match={suggestion.get('class_match')})"
                    )
                lines.append("")

    per_key = summary.get("per_key", {})
    lines.extend(["## Per-Key Results", ""])
    lines.append(f"- Total keys: {per_key.get('total_keys', 0)}")
    lines.append(f"- Any-hit key accuracy: {per_key.get('any_hit_accuracy', 0.0)}")
    lines.append(
        f"- Best-confidence key accuracy: {per_key.get('best_confidence_accuracy', 0.0)}"
    )
    lines.append("")
    key_rows = per_key.get("keys", [])
    if not key_rows:
        lines.append("No per-key rows found.")
        lines.append("")
    else:
        for item in key_rows:
            lines.append(
                "- "
                f"{item.get('expected_key')}: "
                f"images={item.get('image_count')}, "
                f"hits={item.get('hit_count')}, "
                f"any_hit={item.get('any_hit')}, "
                f"best_confidence_hit={item.get('best_confidence_hit')}, "
                f"best_image={item.get('best_confidence_image')}, "
                f"best_predicted={item.get('best_confidence_predicted_key')}"
            )
        lines.append("")

    lines.extend(
        [
            "## Mismatches",
            "",
        ]
    )

    mismatches = summary.get("mismatches", [])
    if not mismatches:
        lines.append("No mismatches found.")
    else:
        for item in mismatches:
            lines.append(
                "- "
                f"{item.get('image_filename')}: {item.get('category')} "
                f"(expected number={item.get('expected_number')}, "
                f"predicted number={item.get('predicted_number')}, "
                f"expected class={item.get('expected_class')}, "
                f"predicted class={item.get('predicted_class')}, "
                f"expected key={item.get('expected_key')}, "
                f"predicted key={item.get('predicted_key')})"
            )

            suggestions = item.get("candidate_suggestions", [])
            for suggestion in suggestions:
                lines.append(
                    "  - suggestion: "
                    f"{suggestion.get('key')} "
                    f"(reason={suggestion.get('reason')})"
                )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
