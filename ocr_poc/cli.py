from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from ocr_poc.evaluation.metrics import evaluate_row, summarize
from ocr_poc.evaluation.parser import is_supported_image, parse_ground_truth_from_filename
from ocr_poc.evaluation.reporter import write_json, write_markdown_summary
from ocr_poc.ocr.detectors import build_detector
from ocr_poc.ocr.processor import process_image
from ocr_poc.ocr.schemas import OCRResult
from ocr_poc.ocr.visualization import save_annotated_image


def _iter_images(input_dir: str) -> list[str]:
    candidates = sorted(Path(input_dir).iterdir())
    return [str(path) for path in candidates if path.is_file() and is_supported_image(str(path))]


def cmd_process(args: argparse.Namespace) -> int:
    images = _iter_images(args.input_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    detector = build_detector(args.engine)
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
            outcome = process_image(image_path=image_path, detector=detector, debug_dir=debug_dir)

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


def cmd_evaluate(args: argparse.Namespace) -> int:
    images = _iter_images(args.image_dir)
    predictions = _load_predictions(args.results_jsonl)

    rows = []
    missing_predictions: list[str] = []
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

        gt = parse_ground_truth_from_filename(filename)
        rows.append(
            evaluate_row(
                gt,
                predicted,
                detected_tokens=predicted_row.get("detected_tokens", []),
                token_count=int(predicted_row.get("token_count", 0)),
                annotated_image_path=predicted_row.get("annotated_image_path"),
            )
        )

    summary = summarize(rows)
    summary["missing_predictions"] = missing_predictions
    summary["evaluations"] = [asdict(row) for row in rows]

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
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RaceWrangler OCR POC CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process", help="Process images through OCR")
    process_parser.add_argument("--input-dir", required=True)
    process_parser.add_argument("--output-dir", required=True)
    process_parser.add_argument("--engine", default="paddle", choices=["paddle", "mock"])
    process_parser.add_argument("--save-debug-images", action="store_true")
    process_parser.set_defaults(func=cmd_process)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate OCR output")
    eval_parser.add_argument("--image-dir", required=True)
    eval_parser.add_argument("--results-jsonl", required=True)
    eval_parser.add_argument("--report-dir", required=True)
    eval_parser.set_defaults(func=cmd_evaluate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
