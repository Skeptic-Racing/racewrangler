from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from ocr_poc.evaluation.metrics import evaluate_row, suggest_candidate_keys, summarize
from ocr_poc.evaluation.parser import (
    GroundTruth,
    build_canonical_key,
    is_supported_image,
    load_expected_competitors,
    load_run_group_mapping,
    parse_canonical_key,
    parse_ground_truth_from_filename,
)
from ocr_poc.evaluation.reporter import write_json, write_markdown_summary
from ocr_poc.ocr.detectors import build_detector
from ocr_poc.ocr.processor import AllowedKey, process_image
from ocr_poc.ocr.schemas import OCRResult
from ocr_poc.ocr.visualization import save_annotated_image


def _iter_images(input_dir: str) -> list[str]:
    candidates = sorted(Path(input_dir).iterdir())
    return [str(path) for path in candidates if path.is_file() and is_supported_image(str(path))]


def cmd_process(args: argparse.Namespace) -> int:
    images = _iter_images(args.input_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    detector = build_detector(args.engine)
    allowed_keys = None
    if args.run_group_json:
        run_group_json_path = _resolve_existing_file(
            args.run_group_json,
            image_dir=args.input_dir,
        )
        run_group_data = load_run_group_mapping(run_group_json_path)
        allowed_keys = []
        for key in sorted(run_group_data["key_to_images_mapping"].keys()):
            class_value, number_value = parse_canonical_key(key)
            if number_value is None:
                continue
            allowed_keys.append(
                AllowedKey(
                    key=key,
                    class_value=class_value,
                    number_value=number_value,
                )
            )
    zero_token_images = 0
    predictions_dir = os.path.join(args.output_dir, "predictions")
    os.makedirs(predictions_dir, exist_ok=True)
    annotated_dir = os.path.join(args.output_dir, "annotated")
    os.makedirs(annotated_dir, exist_ok=True)

    debug_dir = None
    if args.save_debug_images:
        debug_dir = os.path.join(args.output_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)

    jsonl_path = os.path.join(args.output_dir, "results.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as jsonl_handle:
        for image_path in images:
            outcome = process_image(
                image_path=image_path,
                detector=detector,
                debug_dir=debug_dir,
                allowed_keys=allowed_keys,
            )

            # Spec-only output object per image.
            prediction_path = os.path.join(
                predictions_dir, f"{Path(image_path).stem}.json"
            )
            with open(prediction_path, "w", encoding="utf-8") as pred_handle:
                json.dump(outcome.result.to_dict(), pred_handle, indent=2)

            annotated_path = os.path.join(annotated_dir, os.path.basename(image_path))
            save_annotated_image(image_path, outcome.detected_tokens, annotated_path)

            row = {
                "image_filename": os.path.basename(image_path),
                "image_path": image_path,
                "annotated_image_path": annotated_path,
                "inference_time_ms": outcome.inference_time_ms,
                "detected_tokens": [
                    {
                        "text": token.text,
                        "confidence": token.confidence,
                        "bbox": token.bbox,
                    }
                    for token in outcome.detected_tokens
                ],
                "token_count": len(outcome.detected_tokens),
                **outcome.result.to_dict(),
            }
            if row["token_count"] == 0:
                zero_token_images += 1
            jsonl_handle.write(json.dumps(row) + "\n")

    manifest = {
        "input_dir": args.input_dir,
        "engine": args.engine,
        "image_count": len(images),
        "results_jsonl": jsonl_path,
        "predictions_dir": predictions_dir,
        "annotated_dir": annotated_dir,
    }
    write_json(os.path.join(args.output_dir, "manifest.json"), manifest)
    print(f"Processed {len(images)} image(s). Results written to {args.output_dir}")
    if args.engine == "mock":
        print(
            "Warning: engine=mock returns zero tokens by design; "
            "use --engine paddle for real OCR."
        )
    elif images and zero_token_images == len(images):
        print(
            "Warning: all images produced zero detected tokens. "
            "Check OCR dependency install and image quality."
        )
    elif images and zero_token_images > 0:
        print(
            "Notice: "
            f"{zero_token_images}/{len(images)} image(s) produced zero detected tokens."
        )
    return 0


def _load_predictions(results_jsonl_path: str) -> dict[str, dict]:
    predictions: dict[str, dict] = {}
    with open(results_jsonl_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            predictions[item["image_filename"]] = item
    return predictions


def _resolve_existing_file(
    raw_path: str,
    *,
    image_dir: str,
    fallback_candidates: list[str] | None = None,
) -> str:
    candidate_paths: list[str] = []
    raw_exists = os.path.isfile(raw_path)
    if raw_exists:
        return raw_path

    if os.path.isabs(raw_path):
        candidate_paths.append(raw_path)
    else:
        candidate_paths.append(raw_path)
        candidate_paths.append(os.path.join(image_dir, raw_path))
        for extra in fallback_candidates or []:
            candidate_paths.append(extra)

    existing_candidates: list[str] = []
    for candidate in candidate_paths:
        if os.path.isfile(candidate):
            existing_candidates.append(candidate)

    if existing_candidates:
        existing_candidates.sort(key=lambda path: os.path.getmtime(path), reverse=True)
        return existing_candidates[0]

    tested = ", ".join(candidate_paths)
    raise FileNotFoundError(f"Could not find file '{raw_path}'. Checked: {tested}")


def cmd_evaluate(args: argparse.Namespace) -> int:
    if args.expected_results_json and not args.run_group_json:
        raise ValueError("--expected-results-json requires --run-group-json")

    results_jsonl_path = _resolve_existing_file(
        args.results_jsonl,
        image_dir=args.image_dir,
        fallback_candidates=[
            os.path.join("ocr_poc", "output", os.path.basename(args.results_jsonl)),
            os.path.join("ocr_poc", "output_paddle", os.path.basename(args.results_jsonl)),
        ],
    )

    run_group_json_path = None
    expected_results_json_path = None
    if args.run_group_json:
        run_group_json_path = _resolve_existing_file(
            args.run_group_json,
            image_dir=args.image_dir,
        )
    if args.expected_results_json:
        expected_results_json_path = _resolve_existing_file(
            args.expected_results_json,
            image_dir=args.image_dir,
        )

    images = _iter_images(args.image_dir)
    predictions = _load_predictions(results_jsonl_path)

    run_group_data = None
    expected_competitors_by_key: dict[str, dict] = {}
    expected_validation = {
        "checked": False,
        "missing_in_expected_results": [],
        "unexpected_expected_results_keys": [],
    }

    if run_group_json_path:
        run_group_data = load_run_group_mapping(run_group_json_path)

    if expected_results_json_path:
        expected_competitors_by_key = load_expected_competitors(expected_results_json_path)

    if run_group_data and expected_competitors_by_key:
        expected_validation["checked"] = True
        run_group_keys = set(run_group_data["key_to_images_mapping"].keys())
        expected_keys = set(expected_competitors_by_key.keys())
        expected_validation["missing_in_expected_results"] = sorted(run_group_keys - expected_keys)
        expected_validation["unexpected_expected_results_keys"] = sorted(expected_keys - run_group_keys)

    rows = []
    missing_predictions: list[str] = []
    unmapped_images: list[str] = []
    available_keys = (
        sorted(run_group_data["key_to_images_mapping"].keys()) if run_group_data else []
    )
    for image_path in images:
        filename = os.path.basename(image_path)
        predicted_row = predictions.get(filename)
        if not predicted_row:
            missing_predictions.append(filename)
            continue

        predicted = OCRResult(
            number_raw=predicted_row.get("number_raw"),
            number_normalized=predicted_row.get("number_normalized"),
            class_raw=predicted_row.get("class_raw"),
            class_normalized=predicted_row.get("class_normalized"),
            confidence_number=predicted_row.get("confidence_number"),
            confidence_class=predicted_row.get("confidence_class"),
        )

        expected_key = None
        gt: GroundTruth
        if run_group_data:
            expected_key = run_group_data["image_to_key"].get(filename)
            if expected_key is None:
                unmapped_images.append(filename)
                continue
            expected_class, expected_number = parse_canonical_key(expected_key)
            gt = GroundTruth(
                image_filename=filename,
                number_normalized=expected_number,
                class_normalized=expected_class,
            )
        else:
            gt = parse_ground_truth_from_filename(filename)

        predicted_key = build_canonical_key(
            predicted.class_normalized,
            predicted.number_normalized,
        )
        suggestions: list[dict] = []
        if run_group_data and expected_key != predicted_key:
            suggestions = suggest_candidate_keys(
                predicted.number_normalized,
                predicted.class_normalized,
                available_keys,
            )

        rows.append(
            evaluate_row(
                gt,
                predicted,
                detected_tokens=predicted_row.get("detected_tokens", []),
                token_count=int(predicted_row.get("token_count", 0)),
                annotated_image_path=predicted_row.get("annotated_image_path"),
                expected_key=expected_key,
                predicted_key=predicted_key,
                candidate_suggestions=suggestions,
            )
        )

    summary = summarize(rows)
    summary["missing_predictions"] = missing_predictions
    summary["unmapped_images"] = unmapped_images
    summary["run_group"] = run_group_data.get("run_group") if run_group_data else None
    summary["expected_results_validation"] = expected_validation
    if run_group_data:
        report_rows = [row for row in rows if row.key_match is not True]
    else:
        report_rows = rows
    summary["evaluations"] = [asdict(row) for row in report_rows]

    os.makedirs(args.report_dir, exist_ok=True)
    write_json(os.path.join(args.report_dir, "summary.json"), summary)
    write_markdown_summary(
        os.path.join(args.report_dir, "summary.md"),
        summary,
        image_dir=args.image_dir,
    )
    print(f"Evaluated {len(rows)} image(s). Report written to {args.report_dir}")
    if missing_predictions:
        print(f"Warning: missing predictions for {len(missing_predictions)} image(s).")
    if unmapped_images:
        print(f"Warning: {len(unmapped_images)} image(s) are not mapped in run-group json.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RaceWrangler OCR POC CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process", help="Process images through OCR")
    process_parser.add_argument("--input-dir", required=True)
    process_parser.add_argument("--output-dir", required=True)
    process_parser.add_argument("--engine", default="paddle", choices=["paddle", "mock"])
    process_parser.add_argument("--save-debug-images", action="store_true")
    process_parser.add_argument("--run-group-json")
    process_parser.set_defaults(func=cmd_process)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate OCR output")
    eval_parser.add_argument("--image-dir", required=True)
    eval_parser.add_argument("--results-jsonl", required=True)
    eval_parser.add_argument("--report-dir", required=True)
    eval_parser.add_argument("--run-group-json")
    eval_parser.add_argument("--expected-results-json")
    eval_parser.set_defaults(func=cmd_evaluate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
