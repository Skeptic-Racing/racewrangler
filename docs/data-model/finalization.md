# Finalization Entity Specification

## 1. Purpose
A **Finalization** represents the moment when a Run’s timing, penalties, and validation results are officially locked and certified. Finalization marks the transition from the mutable timing pipeline to the immutable results pipeline.

Finalization also serves as an **archival snapshot**, capturing all essential computed fields so that upstream timing data (TimingEvents, ValidationResults, Penalties) may be compacted or purged without losing the ability to reconstruct official results.

---

## 2. Definition
A Finalization is a run‑scoped, immutable record that captures:

- which ValidationResult was used  
- the final computed times (raw, penalty‑adjusted, PAX‑adjusted)  
- the number and types of penalties  
- the official status of the run  
- who finalized it and when  
- any notes or overrides applied by officials  

Once created, a Finalization cannot be modified or deleted.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the finalization record  
- **run_id** — Reference to the Run being finalized  
- **validation_result_id** — Reference to the ValidationResult used for finalization  
- **final_status** — One of: `official`, `disqualified`, `did_not_finish`, `invalid`  
- **finalized_at** — Timestamp when the run was finalized  
- **finalized_by** — User or system that performed the finalization  

---

## 4. Computed Timing Fields (Core Snapshot)
These fields allow the system to reconstruct official results without referencing upstream timing data.

- **raw_time** — Elapsed time between selected start and finish events  
- **penalty_time** — Total penalty time applied  
- **adjusted_time** — `raw_time + penalty_time`  
- **pax_time** — PAX/index‑adjusted time (nullable; depends on event type)  
- **penalty_count** — Number of penalties applied  

---

## 5. Optional Archival Fields (Extended Snapshot)
These fields are not required for basic operation but enable long‑term data compaction and deep auditability.

- **penalty_breakdown** — JSON structure describing each penalty applied  
- **selected_start_event_id** — ID of the TimingEvent used as the official start  
- **selected_finish_event_id** — ID of the TimingEvent used as the official finish  
- **sector_times** — JSON structure of sector or split times (if applicable)  
- **validation_issue_codes** — Array of issue codes present at validation time  
- **override_flags** — Indicators of manual overrides (e.g., `manual_start`, `manual_finish`, `manual_penalty`)  

These fields allow the system to delete or archive:
- TimingEvents  
- ValidationResults  
- Penalties  
…while still preserving a complete, immutable record of the official outcome.

---

## 6. Relationships

### Parent
- **Run** — Finalization belongs to a run  

### Referenced Entities
- **ValidationResult** — The validation snapshot used to finalize the run  
- **Penalty** — Penalties included in the final time (via ValidationResult)  

### Referenced By
- **Results computation** — Finalization is the authoritative source for published results  
- **Audit logs** — Used for appeals, disputes, and post‑event review  

---

## 7. Operational Behavior

### Finalization Flow
```
ValidationResult → Finalization → Official Results
```

### When Finalization Occurs
Finalization typically occurs:
- **after the event**, during post‑event auditing  
- once all runs have been validated  
- once penalties have been reviewed  
- once officials are satisfied with the data  

Optional workflows:
- **auto‑finalization** immediately after validation  
- **manual early finalization** for simple events  

### What Finalization Locks
Once finalized:
- the selected ValidationResult cannot change  
- penalties cannot change  
- start/finish events cannot change  
- computed times cannot change  
- run status cannot change  

Any corrections require:
- invalidating the finalization  
- re‑validating the run  
- creating a new Finalization record  

---

## 8. Constraints & Invariants

- A Finalization must belong to exactly one run  
- A run may have at most one active Finalization  
- Finalization records are immutable once created  
- A run cannot be finalized without a ValidationResult  
- Finalization must reference exactly one ValidationResult  
- Finalization cannot occur before validation  
- Finalization cannot be deleted once results are published  
- Computed fields must reflect the state of the run at the moment of finalization  

---

## 9. Notes & Implementation Guidance

- Finalization is the authoritative boundary between timing and results  
- Finalization records should be visible in audit logs  
- Officials should be able to:
  - review validation details  
  - add notes  
  - override penalties (before finalization)  
- The system should support:
  - post‑event batch finalization  
  - per‑run finalization  
  - auto‑finalization for simple events  
- Extended snapshot fields allow:
  - long‑term storage reduction  
  - deletion of upstream timing data  
  - future rule changes without altering historical results  

