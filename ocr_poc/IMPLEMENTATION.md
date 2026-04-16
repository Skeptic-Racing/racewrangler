# OCR POC: Implementation Status

## Overview

The OCR POC is a standalone, event-agnostic optical character recognition system designed to extract car identification (number + class) from race photos. It demonstrates practical OCR capability for the RaceWrangler timing system's run identification workflow.

## Architecture

### Core Components

- **OCR Engine**: Paddle OCR (PaddleOCR) with configurable preprocessing pipeline
- **Preprocessing Pipeline**: Applies multiple image variants per input
  - Autocontrast normalization
  - Binary threshold variants (multiple threshold levels)
  - Edge sharpening
  - Inversion (dark-text-on-light backgrounds)
- **Advanced Detection**: ROI (region-of-interest) crop and focused detection for sparse-token images
- **Token Merging**: Consolidates detections across multiple preprocessing passes
- **Run-Group Integration**: Constrained decoding using expected competitor keys from run-group JSON

### Processing Pipeline

```
Input Image
    ↓
Preprocessing (4 variants)
    ↓
OCR Token Detection (per variant)
    ↓
Token Consolidation / Merge
    ├─ If sparse: Run ROI crop detection
    ↓
Parse Detected Tokens → Extract Number + Class
    ↓
JSON Output (spec-only format)
```

## Implemented Capabilities

### 1. Image Processing

- **Multipass preprocessing**: Instead of single-pass OCR, processes image with 4+ preprocessing strategies
- **ROI cropping**: Automatically crops and processes suspected registration regions for sparse cases
- **Quality preservation**: Retains raw token bounding boxes and confidence scores for debugging

### 2. Token Parsing

- **Flexible extraction**: Handles number-class and class-number orderings
- **Leading zero preservation**: Maintains leading zeros (e.g., `007`, `01`)
- **Hyphenated class tokens**: Preserves class markers with embedded delimiters (e.g., `NCAM-S`, `CAM-S360`)
- **Number/class splitting**: Intelligently separates combined tokens (e.g., `S007` → class=S, number=007)

### 3. Run-Group Constrained Decoding

- Accepts expected competitor list from `--run-group-json` parameter
- Restricts OCR token interpretation to known keys
- Improves accuracy by eliminating impossible detections
- Supports multi-pass fallback when constrained set yields no matches

### 4. Evaluation Framework

- **Filename-based ground truth**: Parses truth labels from filenames
  - Formats: `NUMBERCLASS.ext`, `CLASSNUMBER.ext`, `NUMBER.ext`
  - Case-insensitive, normalized to uppercase

- **Metrics computed**:
  - **Per-image key accuracy**: Primary success metric (correct number + class)
  - **Number accuracy**: Isolated numeric extraction
  - **Class accuracy**: Isolated class extraction
  - **Joint accuracy**: Both number and class correct
  - **Misidentification rate**: Wrong key predicted
  - **Abstain rate**: No key predicted (confidence too low or no tokens)

- **Per-key aggregation**: Summarizes performance by competitor ID
- **Missing/unexpected key validation**: Compares evaluated set against run-group expectations

### 5. Output Formats

#### OCR JSON (per-image)
```json
{
  "number": "007",
  "number_confidence": 0.92,
  "class": "STR",
  "class_confidence": 0.88,
  "raw_tokens": [
    {"text": "STR", "confidence": 0.88, "bbox": [[x1, y1], [x2, y2], ...]},
    ...
  ]
}
```

#### Results JSONL (per-image, aggregated)
```json
{"filename": "str007.jpg", "image_path": "...", "number": "007", "class": "STR", ...}
```

#### Summary JSON (run-group level)
- Aggregate metrics (key accuracy, number accuracy, class accuracy, etc.)
- Per-image results (filename, prediction, ground truth, match status)
- Per-key aggregation (failures per competitor)
- Unmapped images and validation status

## CLI Commands

### Process Images
```bash
# Basic: process all images in a directory
python -m ocr_poc.cli process \
  --input-dir docs/ocr/test_images \
  --output-dir ocr_poc/output \
  --engine paddle

# With run-group constraints: improve accuracy using expected keys
python -m ocr_poc.cli process \
  --input-dir docs/ocr/test_images/run_group_1 \
  --output-dir ocr_poc/output \
  --engine paddle \
  --run-group-json docs/ocr/test_images/run_group_1/expected_results.json

# Save annotated debug images
python -m ocr_poc.cli process \
  --input-dir docs/ocr/test_images \
  --output-dir ocr_poc/output \
  --engine paddle \
  --save-debug-images
```

### Evaluate Predictions
```bash
# Basic: evaluate against filename ground truth
python -m ocr_poc.cli evaluate \
  --image-dir docs/ocr/test_images \
  --results-jsonl ocr_poc/output/results.jsonl \
  --report-dir ocr_poc/reports

# With run-group mapping: evaluate against canonical keys
python -m ocr_poc.cli evaluate \
  --image-dir docs/ocr/test_images/run_group_1 \
  --results-jsonl ocr_poc/output/results.jsonl \
  --report-dir ocr_poc/reports \
  --run-group-json docs/ocr/test_images/run_group_1/expected_results.json \
  --expected-results-json docs/ocr/test_images/run_group_1/test_run_group_1.json
```

## Current Performance

| Metric | Value |
|--------|-------|
| **Per-image key accuracy** | 82.5% |
| **Number accuracy** | 82.5% |
| **Class accuracy** | 87.5% |
| **Joint accuracy** | 82.5% |
| **Abstain rate** | 5% |
| **Misidentification rate** | 12.5% |
| **Test set size** | 40 images (run_group_1) |

## Key Limitations and Known Issues

1. **Low-contrast or obscured numbers**: ~5% of images yield no OCR tokens (abstention)
2. **Class detection fragility**: Multi-character classes (e.g., STR, SSM, NCAM-S) are harder than numbers
3. **Digit confusion**: Similar glyphs (1 vs l, 0 vs O) still occur despite multi-pass preprocessing
4. **ROI assumption**: Current ROI cropping assumes registration is in bottom-right quadrant; images with alternate plate positions may miss detections
5. **Preprocessing overhead**: Multi-pass + ROI adds ~3–5× latency vs. single-pass OCR

## Design Decisions

- **Multi-pass preprocessing over model ensemble**: Chose to preprocess the same image in multiple ways rather than train multiple OCR models (simpler, faster to build)
- **Run-group constraints over raw accuracy**: Leveraged expected-keys filtering to eliminate impossible predictions and improve precision
- **Fallback suggestions**: When constrained decoding yields no match, fall back to unconstrained tokens with confidence thresholds
- **Minimal re-training**: Used off-the-shelf Paddle OCR without fine-tuning on race photos (future opportunity for improvement)

## Next Steps for Production

1. **Fine-tune Paddle OCR** on race-photo dataset to improve class and number detection
2. **Adaptive preprocessing**: Learn optimal preprocessing per image region or lighting condition
3. **Dynamic ROI detection**: Move from fixed quadrant assumption to content-driven region detection
4. **Hardware acceleration**: GPU-accelerate OCR inference for real-time event processing
5. **Multi-pass consensus**: Combine multiple OCR engines (Tesseract, EasyOCR) for higher confidence
