# CameraSession Entity Specification

## 1. Purpose
A **CameraSession** represents the assignment of a physical camera to a timing role (start, finish, split, auxiliary) for a specific period of time during an event. CameraSessions enable seamless hardware replacement, support multiple cameras per role, and preserve auditability.

CameraSessions decouple **hardware identity** (Camera) from **timing role and position** (e.g., Split 1, Split 2, Finish Lane A), allowing the system to scale to complex timing setups without mutating historical data.

---

## 2. Definition
A CameraSession is an event‑scoped, time‑bounded record that binds a camera to a timing role and an optional position index. Multiple CameraSessions may be active for the same role, as long as each has a unique `(role, position)` pair.

CameraSessions:
- begin when a camera is activated for a role  
- end when the camera is replaced or deactivated  
- allow backup cameras to be swapped in without rewriting TimingEvents  
- support multi‑camera sector timing and redundancy  
- provide a timeline for validation to interpret TimingEvents accurately  

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the session  
- **event_id** — Reference to the Event  
- **camera_id** — Reference to the physical Camera  
- **role** — One of: `start`, `finish`, `split`, `auxiliary`  
- **position** — Optional integer or string identifying the camera’s position within the role (e.g., `1`, `2`, `A`, `B`)  
- **activated_at** — Timestamp when the session became active  
- **deactivated_at** — Timestamp when the session ended (nullable)  

### Metadata
- **notes** — Freeform notes for timing staff  
- **created_at** — Timestamp when the session was created  
- **updated_at** — Timestamp when the session was last modified  

---

## 4. Relationships

### Parent
- **Event** — Sessions belong to an event  
- **Camera** — Sessions bind a camera to a role and position  

### Children
None — CameraSessions do not own other entities.

### Referenced By
- **Validation logic** — Uses session timelines to interpret TimingEvents  
- **Timing pipeline** — Determines which camera(s) are responsible for each role and position  

---

## 5. Operational Behavior

### Session Lifecycle
```
CameraSession created → becomes active → (optional) replaced → deactivated
```

### Activation Rules
- Multiple active sessions may exist for the same role  
- Each active session must have a unique `(role, position)` pair  
- A session becomes active at `activated_at`  
- A session ends when `deactivated_at` is set  

### Replacement Flow
When a camera fails:
1. A new CameraSession is created for the replacement camera  
2. The old session is closed  
3. TimingEvents continue flowing without interruption  
4. No TimingEvents are reassigned or rewritten  

### Multi‑Camera Roles
CameraSessions support:
- multiple sector cameras (`split` role with positions 1, 2, 3…)  
- multiple finish cameras (e.g., lanes A, B)  
- redundant cameras covering the same point  
- multi‑course or multi‑lane events  

### Role Attribution
Validation determines the meaning of each TimingEvent by:
1. reading the event’s `camera_id`  
2. finding all CameraSessions for that camera  
3. filtering to sessions active at the timestamp  
4. using the session’s `role` and `position` to interpret the event  

This ensures deterministic interpretation even in complex setups.

---

## 6. Constraints & Invariants

- A CameraSession must belong to exactly one event  
- A CameraSession must reference exactly one camera  
- Multiple active sessions per role are allowed  
- `(role, position)` must be unique among active sessions  
- A session’s `activated_at` must be earlier than its `deactivated_at` (if set)  
- Sessions must not overlap for the same `(role, position)`  
- Sessions must not be deleted once TimingEvents exist for their camera  

---

## 7. Notes & Implementation Guidance

- Use `position` to distinguish sector cameras, finish lanes, or redundant devices  
- CameraSessions should be created automatically when cameras connect or are manually activated  
- Deactivation should be explicit to maintain a clean timeline  
- Validation must rely on CameraSession timelines rather than camera roles  
- CameraSessions provide a complete audit trail for hardware usage  
- This model supports:
  - hot‑swapping cameras  
  - multi‑camera timing points  
  - redundant hardware  
  - simulated or virtual cameras for testing  

