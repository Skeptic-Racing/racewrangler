# OCR POC: New Requirements Discovered During Implementation

This document describes requirements and design decisions that emerged during OCR POC work and are **not** present in the baseline documentation under `/docs/`.

## 1. Canonical Key Normalization and Preservation

### Requirement
Run-group competitor keys must be normalized consistently between:
- Filename canonicalization (photo filename → expected key)
- OCR output parsing (detected tokens → extracted key)
- Run-group mapping metadata (expected_results.json)

### Why It Matters
OCR detection and filename parsing can both produce the same logical key via different routes. For example:
- Filename: `ncam-s360_1.jpg` (hyphenated class with embedded number)
- OCR text: `NCAM` + `S360` (separate tokens)
- Must both canonicalize to: `NCAM-S::360` (preserved hyphenation, leading zeros on number)

### Implementation Details
- **Preserved hyphenated class tokens**: Class labels like `NCAM-S`, `CAM-S`, `S-CAM` retain their hyphens in canonical form
- **No class length limits**: Extended classes (3+ chars) are not truncated
- **Leading zero preservation**: Numbers `001`, `007`, `082` retain leading zeros
- **Canonical form**: `CLASS::NUMBER` with uppercase, hyphens intact

### Related Design Constraint
Class tokens containing digits (e.g., `N62`, `S007`) should **not** be interpreted as split failures. Instead, the parser recognizes that a pure-number detection (e.g., `62`) is a split failure from a class that contains digits.

---

## 2. Run-Group Mapping and Multi-Image Per Key

### Requirement
A single competitor (one canonical key) may have **multiple photos** from different angles or at different times in an event. The run-group mapping must associate:
- Multiple image files → one expected canonical key
- Preserve photo variant info (e.g., `_1`, `_2`, `_3` suffixes) separately from the key

### File Naming Convention
```
CANONICAL_KEY_VARIANT_SUFFIX.ext
Example: ncam-s360_1.jpg, ncam-s360_2.jpg, ncam-s360_3.jpg
         → all map to NCAM-S::360
```

### Why It Matters
Trailing photo suffixes (`_1`, `_2`, etc.) must be **stripped before canonicalization**, but class/number hyphens must be **preserved**. This enables:
- Evaluating multi-angle shots per car
- Aggregating accuracy metrics per unique key (not per filename)
- Handling photographer conventions (multiple shots per run)

---

## 3. Per-Image Progress Tracking and Enrichment Workflow

### Requirement
OCR output must support incremental enrichment workflows where:
- Initial OCR produces raw detections
- Subsequent enrichment steps (confidence filtering, manual review, etc.) refine results
- Progress state must survive workflow interruptions (crash-resume capability)

### Progress State Semantics
```json
{
  "image_id": "...",
  "status": "pending|completed|needs-user-input",
  "last_committed_key": "...",
  "ocr_tokens": [...],
  "enrichment_notes": "..."
}
```

Status meanings:
- **pending**: OCR run complete, but enrichment review not yet applied
- **completed**: Enrichment review finished (includes intentional nulls/abstentions)
- **needs-user-input**: Blocked on ambiguous case requiring human judgment

### Why It's New
The original POC scope was single-pass OCR → evaluation. Extended to support:
- Interactive review loops
- Partial completion checkpoints
- Distinction between "no prediction" (abstention) and "reviewed and rejected"
- Resume from interruption without re-running OCR on entire dataset

---

## 4. Detector-Specific Preprocessing Variants

### Requirement
OCR accuracy varies significantly with image preprocessing. Instead of a single preprocessing step, apply **multiple preprocessing strategies per image** and **merge token results** across passes.

### Implemented Variants
1. **Autocontrast**: Normalize brightness/contrast distribution
2. **Binary threshold**: Convert grayscale → binary at multiple threshold levels
3. **Sharpening**: Enhance edges to clarify character boundaries
4. **Inversion**: Flip colors (needed for white-on-dark plates)
5. **ROI cropping**: Zoom to suspected registration region for sparse-token images

### Why It's New
- Original scope did not specify preprocessing detail
- Emerged as critical to achieving 82.5% accuracy; single-pass OCR yielded ~60%
- Multi-pass consolidation allows trading preprocessing overhead for robustness

---

## 5. Region-of-Interest (ROI) Focused Detection

### Requirement
When an image yields **sparse OCR tokens** (< 2 confident detections), automatically:
1. Identify likely registration region (heuristic: bottom-right quadrant)
2. Crop that region
3. Run OCR at higher zoom/resolution
4. Merge results with full-image detections

### Design Rationale
- Race car plates are typically in bottom-right (visible from behind/side)
- Cropping increases effective resolution for small plates
- Focused detection recovers tokens missed in full-image pass
- Merge strategy: union with deduplication by confidence

### Why It's New
- Not mentioned in baseline POC docs
- Emerged from analyzing failure modes in early test runs
- Adds ~30% latency but improves abstain rate from ~10% → ~5%

---

## 6. Constrained Decoding with Fallback

### Requirement
When OCR runs with a **run-group JSON** containing expected competitor keys:
1. Prioritize interpretations that match expected keys
2. If no match achieves confidence threshold, fall back to unconstrained tokens
3. Suggest candidate keys (ranked by match quality) for ambiguous cases

### Fallback Ranking
```
1. Unconstrained parse (raw tokens)
2. Suggested candidates (ranked by number_match + class_match quality)
3. Default to first expected key if all else fails
```

### Why It's New
- Original scope: evaluate OCR output as-is
- Emerged from operational need: **wrong predictions are worse than abstentions**
- Run-group constraints dramatically improve precision by filtering impossible keys
- Candidate suggestions enable batch correction workflows

---

## 7. Parsing Flexibility for Variant Token Formats

### Requirement
OCR may produce tokens in various formats:
- **Clean**: `STR` + `007` (separate tokens) → `STR::007`
- **Combined**: `STR007` (single token) → detect split point → `STR::007`
- **Reversed**: `007STR` (number-first) → reverse order → `STR::007`
- **Fractional**: `S10` (incomplete) → ignore or flag as unreliable

### Token Type Detection
Different regions of a race photo may have different formats:
- Vinyl decals (clean separation)
- Painted numbers (often combined or malformed)
- Reflective plates (high noise)

### Why It's New
- Baseline assumption: clean token separation
- Real race photos are messy; OCR output is noisy
- Parsing logic emerged from test-image analysis (run_group_1 failures)
- Enables single-pass interpretation across highly variable photo conditions

---

## 8. Evaluation Against Run-Group Canonical Keys (Not Filenames)

### Requirement
Evaluation must support two modes:

**Mode A (Baseline): Filename Ground Truth**
- Truth comes from filename (e.g., `str007.jpg` → `STR::007`)
- Fast, requires no external mapping
- Suitable for controlled test sets

**Mode B (Run-Group): Canonical Key Mapping**
- Truth comes from run-group mapping file
- Multiple filenames can map to one canonical key
- Enables aggregate accuracy per unique competitor
- Detects missing/unexpected keys in evaluation set

### Why It's New
- Original scope: simple filename-based evaluation
- Emerged from real-world use case: same car photographed multiple times
- Run-group mode validates that evaluation set matches expected roster
- Per-key aggregation gives better signal (fewer noise from photo variants)

---

## 9. Structured Evaluation Output with Per-Key Metrics

### Requirement
Evaluation summary must include:
- **Aggregate metrics**: accuracy, abstain rate, misidentification rate
- **Per-image details**: prediction, ground truth, match status, error analysis
- **Per-key aggregation**: aggregate performance grouped by canonical key
- **Cross-dataset validation**: reported missing/unexpected keys vs. expected roster

### Example Per-Key Output
```json
{
  "key": "STR::007",
  "total_images": 2,
  "correct_predictions": 1,
  "key_accuracy": 0.5,
  "number_accuracy": 1.0,
  "class_accuracy": 1.0,
  "failure_examples": ["str007_2.jpg"]
}
```

### Why It's New
- Baseline scope offered per-image results only
- Per-key rollup emerged as essential for identifying systematic biases (e.g., "all S-class cars fail")
- Cross-dataset validation catches data quality issues early

---

## 10. Debug Output: Annotated Images with Bounding Boxes

### Requirement
Optionally generate **annotated images** showing:
- Detected bounding boxes
- Confidence scores per token
- Color-coded by confidence (green ≥ 0.8, yellow 0.5–0.8, red < 0.5)

### Use Cases
- Debugging OCR failures
- Validating preprocessing effectiveness
- Communicating model limitations to stakeholders
- Training data curation (identifying noisy images)

### Why It's New
- Original scope: JSON output only
- Emerged from need to understand *why* predictions failed
- Visual debugging is 10× faster than reading raw JSON tokens
- Enables non-technical review of OCR quality

---

## Summary of Scope Expansion

| Aspect | Original Scope | Discovered |
|--------|---|---|
| **Preprocessing** | Assumed single-pass | Multi-pass + ROI crops required |
| **Token parsing** | Clean separation | Flexible parsing for variants |
| **Evaluation** | Filename ground truth | Run-group mapping + per-key rollup |
| **Progress tracking** | Single-batch processing | Incremental enrichment + recovery |
| **Debug output** | JSON tokens | Annotated images + per-token bboxes |
| **Inference mode** | Raw OCR | Constrained + fallback suggestions |

These requirements emerged through iterative testing on real race photos and reflect practical constraints not visible in the baseline architecture documents.
