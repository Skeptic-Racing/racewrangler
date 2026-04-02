# Penalty Entity Specification

## 1. Purpose
A **Penalty** represents an adjustment applied to a Run’s computed time due to rule violations, course infractions, or operational issues. Penalties ensure that results reflect both raw performance and compliance with event rules.

Penalties are applied during validation and contribute to the final elapsed time of a run.

---

## 2. Definition
A Penalty is a run‑scoped record representing a time adjustment or rule violation. Penalties may be:

- automatically detected (e.g., missed gate, early start, late finish)  
- manually applied by a human official  
- imported from external rule systems  
- associated with specific TimingEvents or validation issues  

Penalties are immutable once applied, ensuring a complete audit trail.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the penalty  
- **run_id** — Reference to the Run  
- **type** — Penalty category (e.g., `time_addition`, `disqualification`, `warning`)  
- **code** — Standardized penalty code (e.g., `PEN_MISSED_GATE`, `PEN_JUMP_START`)  
- **description** — Human‑readable explanation of the penalty  
- **time_adjustment** — Time added to the run (nullable; required for time‑based penalties)  

### Metadata
- **source** — One of: `automated`, `manual`, `imported`  
- **applied_by** — User or system that applied the penalty (nullable)  
- **notes** — Freeform notes for officials  
- **created_at** — Timestamp when the penalty was applied  
- **updated_at** — Timestamp when the penalty was last modified  

---

## 4. Relationships

### Parent
- **Run** — Penalties belong to a run  

### Referenced By
- **ValidationResult** — Penalties are aggregated and applied during validation  
- **Results computation** — Penalties affect final elapsed time  

### Optional References
- **TimingEvent** — If the penalty is tied to a specific event  
- **ValidationResult** — If the penalty was generated during validation  

---

## 5. Operational Behavior

### Penalty Application Flow
```
Rule violation → Penalty created → ValidationResult aggregates penalties → Final time computed
```

### Types of Penalties
- **Time‑based penalties**  
  Add a fixed duration to the run (e.g., +2 seconds)

- **Disqualifications**  
  Mark the run as invalid regardless of timing

- **Warnings**  
  Do not affect time but may require review

### Automated Penalties
The system may automatically generate penalties based on:
- missing required TimingEvents  
- out‑of‑order sector detections  
- early or late start  
- camera/session anomalies  
- rule‑based validation logic  

### Manual Penalties
Officials may apply penalties for:
- course violations  
- safety infractions  
- sportsmanship issues  
- manual overrides  

---

## 6. Constraints & Invariants

- A penalty must belong to exactly one run  
- Penalties are immutable once created  
- Time‑based penalties must specify `time_adjustment`  
- Disqualification penalties must set `type = disqualification`  
- Penalty codes must be standardized and versioned  
- A run may have zero or many penalties  
- Penalties must not be deleted after finalization  

---

## 7. Notes & Implementation Guidance

- Penalty codes should be documented in a central rulebook  
- Penalties should be applied before finalization  
- Validation should aggregate penalties deterministically  
- Human officials should be able to:
  - add penalties  
  - annotate penalties  
  - override automated penalties  
- Penalties should be visible in audit logs and result summaries  

