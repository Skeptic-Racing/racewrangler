# WorkerAssignment Entity Specification

## 1. Purpose
A **WorkerAssignment** represents the assignment of a person (via Competitor → Driver) to a specific worker role during an Event. It defines:

- which role the worker is performing  
- when the assignment is active  
- which run group (if any) the assignment applies to  
- how the worker authenticates (via DeviceSession)  
- what permissions the worker receives through role tokens  

WorkerAssignment ensures:
- clean, event‑scoped worker management  
- compatibility with the role‑token access model  
- support for digital worker check‑in  
- support for worker/run rotations  
- auditability of worker actions  

---

## 2. Definition
A WorkerAssignment is an event‑scoped record linking:

- a **Competitor** (and therefore a Driver)  
- to a **worker role**  
- optionally to a **RunGroup**  
- optionally to a **DeviceSession**  

WorkerAssignments may be created manually by organizers or automatically based on event configuration.

Workers do **not** need accounts or passwords — authentication is handled via ephemeral DeviceSessions and role tokens.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the worker assignment  
- **event_id** — Reference to the Event  
- **competitor_id** — Reference to the Competitor (and therefore the Driver)  
- **role** — Worker role (e.g., `starter`, `grid`, `course_worker`, `timing`, `registration`)  
- **run_group_id** — Optional reference to the RunGroup this worker supports  

### Session & Authentication Fields
- **device_session_id** — Optional reference to DeviceSession  
- **token_issued_at** — Timestamp when the role token was issued  
- **token_expires_at** — Timestamp when the role token expires  

### Operational Fields
- **is_active** — Whether the worker is currently on duty  
- **checked_in_at** — Timestamp when the worker checked in  
- **checked_out_at** — Timestamp when the worker checked out  
- **auto_assigned** — Whether the assignment was created automatically  

### Metadata
- **notes** — Freeform notes for organizers  
- **created_at** — Timestamp when the assignment was created  
- **updated_at** — Timestamp when the assignment was last modified  

---

## 4. Relationships

### Parent
- **Event** — WorkerAssignments belong to an event  

### Required References
- **Competitor** — The person performing the worker role  
- **Driver** — Indirectly referenced through Competitor  

### Optional References
- **RunGroup** — If the worker role is tied to a specific group  
- **DeviceSession** — If the worker is logged in on a device  

### Referenced By
- **DeviceSession** — For authentication  
- **Timing UI** — To determine worker permissions  
- **Starter UI** — To determine who can start cars  
- **Grid UI** — To determine who can manage grid  
- **Course Worker UI** — To determine who can report cones/offs  

---

## 5. Operational Behavior

### Worker Check‑In
Workers may check in via:
- scanning a QR code  
- clicking “Start Worker Shift” in the competitor portal  
- being manually checked in by an organizer  

Check‑in triggers:
- creation of a DeviceSession (if needed)  
- issuance of a role token  
- setting `is_active = true`  

### Worker Check‑Out
Workers may check out manually or automatically.  
Check‑out triggers:
- invalidation of the role token  
- closing the DeviceSession (optional)  
- setting `is_active = false`  

### Role Token Behavior
Role tokens grant:
- access to worker UIs  
- permissions to perform worker actions  
- ephemeral identity separate from competitor identity  

Tokens:
- are short‑lived  
- are tied to DeviceSession  
- may be revoked at any time  

### Run Group Behavior
If run groups are used:
- WorkerAssignment may specify which group the worker supports  
- Starter, Grid, and Course Worker roles often depend on run group  
- Timing & Scoring roles typically do not  

### Auto‑Assignment
If enabled in EventConfiguration:
- Workers may be auto‑assigned based on class, run group, or rotation rules  
- `auto_assigned = true` indicates system‑generated assignments  

---

## 6. Constraints & Invariants

- A WorkerAssignment must belong to exactly one Event  
- A WorkerAssignment must reference exactly one Competitor  
- A Competitor may have multiple WorkerAssignments (e.g., morning vs afternoon)  
- Worker roles must be valid per EventConfiguration  
- WorkerAssignments cannot be deleted once referenced by DeviceSession  
- WorkerAssignments become locked once the Event becomes active  
- Only one active WorkerAssignment per competitor per role is allowed  

---

## 7. Notes & Implementation Guidance

- WorkerAssignment is the bridge between Competitor and DeviceSession  
- WorkerAssignment should be lightweight and event‑scoped  
- Cached fields on Competitor help reduce joins in worker UIs  
- Worker roles should be flexible and configurable per event  
- WorkerAssignment should be optimized for:
  - fast lookup by role  
  - filtering by run group  
  - determining active workers  
  - issuing and validating role tokens  
- WorkerAssignment should not contain timing or run‑specific data  

