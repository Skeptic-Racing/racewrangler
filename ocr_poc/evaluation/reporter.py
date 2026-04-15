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
        f"- Number accuracy: {summary.get('number_accuracy', 0.0)}",
        f"- Class accuracy: {summary.get('class_accuracy', 0.0)}",
        f"- Joint accuracy: {summary.get('joint_accuracy', 0.0)}",
        "",
    ]

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
                f"predicted class={item.get('predicted_class')})"
            )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
