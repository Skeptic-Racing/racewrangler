# OCR POC

This package provides a standalone, event-agnostic OCR proof of concept.

Implemented commands:

- process: runs OCR over an image folder and writes JSON output.
- evaluate: compares OCR output to filename-derived ground truth or run-group mapped expectations.

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

To constrain OCR decoding to known competitors in a run group:

python -m ocr_poc.cli process --input-dir docs/ocr/test_images/run_group_1 --output-dir ocr_poc/output --engine paddle --run-group-json docs/ocr/test_images/run_group_1/expected_results.json

The processor now applies multiple preprocessing variants per image (autocontrast, threshold, sharpen, invert) and merges detected tokens.
For hard images with sparse OCR tokens, it also runs focused ROI crops and merges those detections.

Note: `--engine mock` is for wiring tests only and returns zero tokens by design.

Outputs:

- ocr_poc/output/predictions/<image>.json (spec-only OCR JSON object)
- ocr_poc/output/results.jsonl (one line per image, includes filename)
- ocr_poc/output/manifest.json

## Evaluate Predictions

python -m ocr_poc.cli evaluate --image-dir docs/ocr/test_images --results-jsonl ocr_poc/output/results.jsonl --report-dir ocr_poc/reports

The evaluator accepts relative file paths. For input files, it first checks the path as given and then checks relative to `--image-dir`.
For `--results-jsonl`, it also checks common defaults such as `ocr_poc/output/results.jsonl` and `ocr_poc/output_paddle/results.jsonl`.

## Evaluate With Run-Group Mapping And Expected Results

Use the run-group mapping file to evaluate each image against its expected canonical competitor key.
When an expected competitor list is also provided, the evaluator reports missing/unexpected keys between both files.

python -m ocr_poc.cli evaluate --image-dir docs/ocr/test_images/run_group_1 --results-jsonl ocr_poc/output/results.jsonl --report-dir ocr_poc/reports --run-group-json docs/ocr/test_images/run_group_1/expected_results.json --expected-results-json docs/ocr/test_images/run_group_1/test_run_group_1.json

Outputs:

- ocr_poc/reports/summary.json
- ocr_poc/reports/summary.md

Additional run-group fields in summary output:

- key_accuracy
- per_image_key_accuracy (primary run-identification metric)
- misidentification_rate (wrong key predicted)
- abstain_rate (no key predicted)
- per_key (aggregate key-level evaluation)
- run_group
- unmapped_images
- expected_results_validation

In run-group mode, `summary.evaluations` and markdown per-image rows include only images that did not match their expected canonical keys.
