# RerunReason Entity Specification

## 1. Purpose
A **RerunReason** represents the justification for granting a rerun to a competitor.  
Reruns must be auditable, consistent, and tied to clear operational causes.

RerunReason ensures:
- transparency in why reruns were granted  
- consistent categorization across events  
- clean integration with Run, ValidationResult, and Finalization  
- support for analytics (e.g., frequency of timing faults, course worker errors)  

---

## 2. Definition
A RerunReason is a predefined or event‑scoped reason explaining why a competitor’s run was invalidated and replaced with a rerun.

RerunReasons may be:
- global (system defaults)  
- event‑scoped (custom reasons for a specific event)  

RerunReasons do **not** contain run‑specific data — they are templates referenced by Run or ValidationResult.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the rerun reason  
- **event_id** — Optional reference to Event (null = global/system reason)  
- **code** — Short code (e.g., `RED_FLAG`, `TIMING_FAULT`, `OBSTRUCTION`)  
- **label** — Human‑readable name (e.g., “Red Flag”, “Timing Equipment Fault”)  

### Description Fields
- **description** — Detailed explanation of the reason  
- **is_system_default** — Whether this is a built‑in system reason  
- **is_active** — Whether this reason is available for use in the event  

### Metadata
- **created_at** — Timestamp when the reason was created  
- **updated_at** — Timestamp when the reason was last modified  

---

## 4. Relationships

### Parent
- **Event** (optional) — If the reason is event‑scoped  

### Referenced By
- **Run** — When a run is marked as a rerun  
- **ValidationResult** — When validation triggers a rerun  
- **Finalization** — For auditability of final results  

### Indirect Relationships
Through Run:
- **Penalty**  
- **TimingEvent**  

---

## 5. Operational Behavior

### Rerun Assignment
A rerun reason may be assigned when:
- a run is invalidated  
- a worker reports an obstruction  
- timing equipment fails  
- a red flag is thrown  
- a cone worker interferes  
- a course worker steps into the course  
- a mechanical failure occurs before the finish lights  

### UI Behavior
- Starter UI: quick‑select common reasons  
- Timing UI: assign rerun reasons during validation  
- Admin UI: manage event‑specific reasons  

### System Behavior
- RerunReason does not itself invalidate a run  
- It is referenced by ValidationResult or Run state  
- It is required for any run marked as “rerun granted”  

---

## 6. Constraints & Invariants

- Codes must be unique within an event  
- System default reasons cannot be deleted  
- Event‑scoped reasons may override labels but not codes  
- A rerun reason must be present for any run marked as rerun  
- RerunReason must not contain run‑specific data  

---

## 7. Notes & Implementation Guidance

### Recommended System Default Reasons
- **RED_FLAG** — Course red‑flagged  
- **TIMING_FAULT** — Timing equipment malfunction  
- **OBSTRUCTION** — Course obstruction (cone, debris, animal, etc.)  
- **WORKER_INTERFERENCE** — Worker stepped into course or interfered  
- **MECHANICAL_FAILURE** — Car failure before finish lights  
- **INCORRECT_START** — Starter error or false start  
- **MISSED_START_BEAM** — Car did not trigger start beam  
- **MISSED_FINISH_BEAM** — Car did not trigger finish beam  

### Implementation Notes
- RerunReason should be lightweight and rarely changed  
- Event‑scoped reasons allow clubs to add custom categories  
- RerunReason should be cached for fast lookup in worker UIs  
- RerunReason should be required for any run flagged as invalidated  

