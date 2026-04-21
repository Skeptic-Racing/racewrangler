# OCR Backend Integration Specification
## RaceWrangler — OCR Pipeline in the FastAPI Backend
## Version: April 2026

This document specifies how the OCR POC (`ocr_poc/`) is integrated into the RaceWrangler
FastAPI backend running on the Pi 5 server. It covers architecture, the call interface,
confidence routing, and the handoff to ambiguity resolution.

For the full matching rules (confidence thresholds, number vs. class priority, leading zeros,
multi-class handling), see [matching-policy-specification.md](matching-policy-specification.md).

---

## 1. Architecture

The `ocr_poc/` directory is refactored into a Python package importable by the backend.
It is **not** a separate microservice — spawning a subprocess or an HTTP sidecar adds
latency and complexity that is not justified for a single-server Pi 5 deployment.

```
backend/
  app/
    services/
      ocr_service.py        # Thin wrapper around ocr_poc package
    routers/
      timing_events.py      # Calls ocr_service on image receipt

ocr_poc/                    # Refactored as importable package
  __init__.py               # Exposes run_ocr(image_bytes, candidates) → OcrResult
  processor.py
  detectors.py
  normalizer.py
```

PaddleOCR requires ~2 GB RAM. The Pi 5 (4–8 GB) has sufficient headroom. The Pi Zero 2W
(512 MB) does not — all OCR runs on the Pi 5.

---

## 2. OCR Service Interface

```python
# ocr_poc/__init__.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class OcrCandidate:
    number_normalized: str
    class_normalized: Optional[str]
    confidence_number: float
    confidence_class: float

@dataclass
class OcrResult:
    raw_number: Optional[str]
    raw_class: Optional[str]
    number_normalized: Optional[str]
    class_normalized: Optional[str]
    confidence_number: float       # 0.0–1.0
    confidence_class: float        # 0.0–1.0
    all_candidates: list[OcrCandidate]  # Ranked by combined confidence

def run_ocr(
    image_bytes: bytes,
    run_group_candidates: list[dict],  # Competitor entries restricted to active run group
) -> OcrResult:
    """
    Run OCR on a timing line photo.

    image_bytes: raw JPEG bytes
    run_group_candidates: list of {"competitor_id": str, "number": str, "class": str}
        The run group constraint improves decoding accuracy by restricting the candidate
        space. Always pass the active run group's competitors.

    Returns OcrResult with extracted number/class and confidence scores.
    Raises TimeoutError if OCR takes > 10 seconds.
    """
    ...
```

---

## 3. Integration Point: Timing Event Intake

When a RaceSpy POSTs a timing event, the backend:

1. Validates the payload (camera_id, role, event_id, sequence_number)
2. Persists the raw `TimingEvent` record immediately (timestamp + image)
3. Retrieves the current run group's competitor list
4. Calls `run_ocr(image_bytes, run_group_candidates)` with a 10-second timeout
5. Passes `OcrResult` to the matching engine (see matching-policy-specification.md)
6. Routes the result:
   - `match_status == "auto"` → create `Run` record, associate competitor, no human needed
   - `match_status == "tentative"` → create `Run` record with tentative association, enqueue for review
   - `match_status == "needs_review"` → enqueue timing event in ambiguity queue, no Run created yet
7. Returns 200 OK to the RaceSpy immediately after step 2 (persistence). OCR and matching
   happen asynchronously so the RaceSpy is not blocked.

### 3.1 Async Processing

```
RaceSpy POST  →  validate + persist  →  200 OK (fast)
                      │
                      └──→  background task: run_ocr + match + route
```

Use FastAPI's `BackgroundTasks` for the OCR processing. If the background task fails,
the `TimingEvent` remains persisted and can be reprocessed manually from the admin UI.

---

## 4. Run-Group-Constrained Decoding

Always pass the active run group's competitors to `run_ocr`. This is the primary accuracy
lever from the POC (contributed to 82.5% accuracy). The run group constraint limits the
candidate space so the OCR result can be checked against a small known set rather than
the entire entry list.

If the current run group cannot be determined (event is not active, no group is staged),
pass the full event competitor list as a fallback.

---

## 5. Confidence Routing

Routing thresholds are defined in [matching-policy-specification.md](matching-policy-specification.md):

| Condition | Route |
|-----------|-------|
| `match_status == "auto"` | Auto-accept: create Run, no review |
| `match_status == "tentative"` | Create Run with tentative flag; notify timing worker for confirmation |
| `match_status == "needs_review"` | Enqueue in ambiguity queue; Run not created until resolved |
| OCR `TimeoutError` | Treat as `needs_review`; log timeout |
| OCR raises any exception | Treat as `needs_review`; log exception + stack trace |

---

## 6. Data Stored Per Timing Event

Every timing event stores:

```python
class TimingEvent(Base):
    id: UUID
    event_id: UUID
    camera_id: UUID
    role: str                     # "start" | "finish"
    timestamp_utc_ms: int
    timestamp_monotonic_ns: int
    sequence_number: int
    image_path: str               # Path on Pi 5 local disk (not stored in DB as blob)
    ocr_result_json: str | None   # Full OcrResult as JSON, null until OCR completes
    match_status: str | None      # "auto" | "tentative" | "needs_review" | null
    matched_competitor_id: UUID | None
    resolved_by: str | None       # "ocr" | "human"
    resolved_at: datetime | None
```

Images are written to disk at `{DATA_DIR}/events/{event_id}/timing-events/{sequence_number}.jpg`
and the path is stored in the DB. Do not store images as blobs in SQLite — image I/O would
serialize through the database lock.

---

## 7. OCR Initialization

PaddleOCR takes ~5–10 seconds to initialize on first use (model loading). Initialize the
OCR engine at backend startup, not on the first timing event, to avoid a spike in response
time at the first trigger.

```python
# app/main.py
@app.on_event("startup")
async def startup():
    from ocr_poc import initialize_ocr
    initialize_ocr()  # Loads PaddleOCR models into memory
```

---

## 8. Reprocessing

The admin UI exposes a "Reprocess" action on any `TimingEvent` that is in `needs_review`
state or where OCR failed. This re-runs the full OCR + matching pipeline using the stored
image. Useful if a run group was misconfigured at the time of the original trigger.

---

## 9. Phase 2 Considerations (Deferred)

- **OCR tuning from corrections:** Human corrections in the ambiguity UI are stored with
  original OCR output. These form a training dataset for model fine-tuning in Phase 2.
- **Batch reprocessing:** After a run group correction, reprocess all timing events from
  that group with the corrected candidate list.
- **LoRa / RS-485 events:** Same intake endpoint; payload format unchanged. Images are
  delivered later (stored on RaceSpy SD card, sync over WiFi when available).
