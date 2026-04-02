# ValidationResult Entity Specification

## 1. Purpose
A **ValidationResult** represents the outcome of the validation process applied to a Run. It captures the system’s interpretation of TimingEvents, penalties, rerun logic, and rule checks. ValidationResults provide a structured, auditable record of how the system determined the authoritative start time, finish time, elapsed time, and any issues requiring human review.

ValidationResults ensure that Runs can be validated repeatedly and deterministically without mutating historical data.

---

## 2. Definition
A ValidationResult is a run‑scoped record produced by the validation pipeline. It summarizes:

- which TimingEvents were selected as authoritative  
- which TimingEvents were ignored or flagged  
- computed timing metrics  
- detected issues (e.g., missing start, multiple finishes, out‑of‑order events)  
- penalties applied  
- whether the run is valid, invalid, or requires review  

ValidationResults are immutable snapshots. Re‑running validation creates a new ValidationResult rather than modifying an existing one.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the validation result  
- **run_id** — Reference to the Run being validated  
- **status** — One of: `valid`, `invalid`, `needs_review`  
- **validated_at** — Timestamp when validation was performed  

### Timing Interpretation Fields
- **selected_start_event_id** — TimingEvent chosen as the authoritative start (nullable)  
- **selected_finish_event_id** — TimingEvent chosen as the authoritative finish (nullable)  
- **computed_elapsed_time** — Duration computed from selected events (nullable)  

### Issue Detection Fields
- **issues** — Array of issue codes (e.g., `missing_start`, `multiple_finishes`, `ambiguous_split`, `camera_offline`)  
- **warnings** — Non‑fatal issues that may require human review  

### Penalty Fields
- **applied_penalty_ids** — List of Penalty entities applied during validation  
- **total_penalty_time** — Aggregate penalty time added to the run  

### Metadata
- **notes** — Freeform notes from the validator (human or automated)  
- **created_at** — Timestamp when the record was created  
- **updated_at** — Timestamp when the record was last modified  

---

## 4. Relationships

### Parent
- **Run** — ValidationResults belong to a run  

### Children
None — ValidationResults do not own other entities.

### Referenced Entities
- **TimingEvent** — Selected start/finish events  
- **Penalty** — Penalties applied during validation  

### Referenced By
- **Finalization logic** — Determines whether a run can be finalized  
- **Results computation** — Uses the authoritative timing and penalties  

---

## 5. Operational Behavior

### Validation Flow
```
TimingEvents → Validation Pipeline → ValidationResult → Finalization
```

### Deterministic Interpretation
Validation must:
- select exactly one start event (if available)  
- select exactly one finish event (if available)  
- compute elapsed time  
- apply penalties  
- detect issues and warnings  
- determine run validity  

### Multiple Validation Passes
- Validation may be run multiple times  
- Each pass creates a new ValidationResult  
- The most recent result is considered authoritative until finalization  

### Interaction with CameraSessions
Validation uses CameraSession timelines to interpret TimingEvents:
- determine which role a camera was serving  
- detect out‑of‑scope or misaligned events  
- identify missing or redundant sector events  

### Human Review
If `status = needs_review`, the system may:
- prompt a human validator  
- allow manual selection of start/finish events  
- allow manual override of penalties  
- attach notes explaining the decision  

---

## 6. Constraints & Invariants

- A ValidationResult must belong to exactly one run  
- A run may have multiple ValidationResults over time  
- ValidationResults are immutable once created  
- Only one ValidationResult is considered “current” (the latest)  
- A run cannot be finalized without at least one ValidationResult  
- A ValidationResult may reference zero or one start/finish events  
- Issue codes must be standardized and machine‑interpretable  

---

## 7. Notes & Implementation Guidance

- Validation should be idempotent: repeated runs should produce consistent results  
- Validation logic should be modular to support:
  - sector timing  
  - multi‑camera redundancy  
  - OCR‑based detections  
  - manual overrides  
- Issue codes should be documented and versioned  
- ValidationResults should be stored even for invalid runs to preserve auditability  
- Human validators should be able to:
  - override selected events  
  - add notes  
  - re‑run validation after adjustments  

