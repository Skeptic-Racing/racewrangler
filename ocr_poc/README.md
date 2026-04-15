# OCR POC

This package provides a standalone, event-agnostic OCR proof of concept.

Implemented commands:

- process: runs OCR over an image folder and writes JSON output.
- evaluate: compares OCR output to filename-derived ground truth.

## Filename Ground Truth Rules

The evaluator reads labels from image filenames using these compact forms:

- NUMBERCLASS.ext (example: 62csp.jpg)
- CLASSNUMBER.ext (example: camc27.png)
- NUMBER.ext (example: 151.jpg)

Class is optional. Parsing is case-insensitive and normalized to uppercase.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies from ocr_poc/requirements.txt.

## Process Images

python -m ocr_poc.cli process --input-dir docs/ocr/test_images --output-dir ocr_poc/output --engine paddle --save-debug-images

Outputs:

- ocr_poc/output/predictions/<image>.json (spec-only OCR JSON object)
- ocr_poc/output/results.jsonl (one line per image, includes filename)
- ocr_poc/output/manifest.json

## Evaluate Predictions

python -m ocr_poc.cli evaluate --image-dir docs/ocr/test_images --results-jsonl ocr_poc/output/results.jsonl --report-dir ocr_poc/reports

Outputs:

- ocr_poc/reports/summary.json
- ocr_poc/reports/summary.md
