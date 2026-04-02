# Run Entity Specification

## 1. Purpose
A **Run** represents a single competitive attempt by a competitor during an event. It is created at staging, may exist without timing data, and progresses through a defined lifecycle as timing events, penalties, and validation results are attached. The Run entity is the central unit of competition in Race Wrangler.

---

## 2. Definition
A Run is an event-scoped record representing one attempt by one competitor. It is created when a competitor is staged and persists through timing, validation, and finalization.

Runs are immutable in terms of identity: once created, they are never replaced, only updated or marked invalid.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the run  
- **event_id** — Reference to the Event  
- **competitor_id** — Reference to the Competitor  
- **run_number** — Sequential number of this competitor’s attempt (1, 2, 3, …)  
- **state** — Current lifecycle state (see section 5)  
- **is_rerun** — Boolean indicating whether this run is a rerun  
- **rerun_reason_id** — Optional reference to a RerunReason  
- **rerun_of_run_id** — Optional reference to the run this one replaces  

### Timing Fields
- **start_time** — Timestamp of associated start TimingEvent (if any)  
- **finish_time** — Timestamp of associated finish TimingEvent (if any)  
- **elapsed_time** — Computed finish minus start (if both exist)  

### Validation Fields
- **validated_at** — Timestamp when validation completed  
- **finalized_at** — Timestamp when results were locked  

### Metadata
- **notes** — Freeform notes for timing staff  
- **created_at** — Timestamp of run creation (staging moment)  
- **updated_at** — Timestamp of last modification  

---

## 4. Relationships

### Parent
- **Event** — A run belongs to exactly one event  
- **Competitor** — A run belongs to exactly one competitor  

### Children
- **TimingEvent** — A run may have zero or many associated timing events  
- **Penalty** — A run may have zero or many penalties  
- **ValidationResult** — A run may have zero or many validation results  

### Optional
- **RerunReason** — If the run is a rerun  
- **Run (self-reference)** — If this run replaces another run  

---

## 5. Lifecycle / State Machine

A Run progresses through the following states:

```
CREATED (at staging)
   ↓
IN_PROGRESS (start event associated)
   ↓
FINISHED (finish event associated)
   ↓
VALIDATED (OCR, penalties, validation resolved)
   ↓
FINALIZED (locked for results)
```

Exceptional state:

```
INVALID — used when a run cannot be completed or is superseded by a rerun.
```

### State Rules
- A run **must** start in `CREATED`.  
- A run **cannot** enter `IN_PROGRESS` without a start TimingEvent.  
- A run **cannot** enter `FINISHED` without a finish TimingEvent.  
- A run **cannot** enter `VALIDATED` until all validation checks have been applied.  
- A run **cannot** enter `FINALIZED` until validated.  
- A run may enter `INVALID` from any state.  

---

## 6. Constraints & Invariants

- A competitor may have multiple runs, but each run_number must be unique per competitor.  
- A run may exist without any timing events (e.g., DNS, timing failure, manual override).  
- A run may have timing events without being fully validated.  
- A run marked as a rerun must reference a rerun reason.  
- A run that is replaced by a rerun should be marked `INVALID`.  
- TimingEvents may be associated or disassociated without deleting the run.  

---

## 7. Notes & Implementation Guidance

- Runs should be created **as soon as staging confirms a competitor is next**, not when timing events arrive.  
- This allows the system to handle missing start/finish events gracefully.  
- Validation should be idempotent — re-running validation should not create duplicate ValidationResults.  
- Finalization should lock all fields except administrative notes.  
- Rerun logic should never delete or overwrite runs; it should only create new runs and mark old ones invalid.
