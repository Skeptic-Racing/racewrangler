# DeviceSession Entity Specification

## 1. Purpose
A **DeviceSession** represents an authenticated session for a worker during an Event. It is the mechanism by which workers gain temporary access to worker UIs and permissions without needing accounts, passwords, or persistent logins.

DeviceSession ensures:
- secure, ephemeral authentication  
- clean separation between worker identity and device identity  
- support for QR‑code login flows  
- compatibility with role tokens and WorkerAssignment  
- auditability of worker actions  

---

## 2. Definition
A DeviceSession is a short‑lived authentication session tied to:

- a **WorkerAssignment** (and therefore a Competitor → Driver)  
- a **physical device** (phone, tablet, laptop)  
- a **role token** granting permissions  

DeviceSessions are created when a worker checks in and destroyed when they check out or when the token expires.

Workers do **not** need accounts — DeviceSession is the entire authentication model.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the device session  
- **event_id** — Reference to the Event  
- **worker_assignment_id** — Reference to the WorkerAssignment  
- **device_id** — Optional device fingerprint or identifier  
- **ip_address** — Optional IP address for auditing  

### Authentication Fields
- **session_token** — Random, opaque token identifying the session  
- **session_issued_at** — Timestamp when the session was created  
- **session_expires_at** — Timestamp when the session expires  
- **revoked_at** — Timestamp when the session was revoked (nullable)  

### Role Token Fields
(These mirror WorkerAssignment but are stored here for fast validation)
- **role** — Cached worker role for this session  
- **role_token** — Ephemeral token granting permissions  
- **role_token_issued_at**  
- **role_token_expires_at**  

### Operational Fields
- **is_active** — Whether the session is currently valid  
- **last_seen_at** — Timestamp of last activity (heartbeat)  
- **user_agent** — Optional device/browser info  

### Conflict Handling Fields (optional)
- **conflict_state** — Enum describing session conflict status:
    - `none` — No conflict detected  
    - `pending_user_confirmation` — A second login attempt occurred; awaiting user confirmation  
    - `locked_pending_organizer` — User denied the conflict; organizer intervention required  
- **conflict_triggered_at** — Timestamp when the conflict was detected  

### Metadata
- **created_at** — Timestamp when the session was created  
- **updated_at** — Timestamp when the session was last modified  

---

## 4. Relationships

### Parent
- **Event** — DeviceSessions belong to an event  

### Required References
- **WorkerAssignment** — Defines the worker and role  
- **Competitor** — Indirectly referenced through WorkerAssignment  
- **Driver** — Indirectly referenced through Competitor  

### Referenced By
- **Worker UIs** — To validate permissions  
- **Timing UI** — To authorize starter/grid/course actions  
- **Audit logs** — To track worker actions  

---

## 5. Operational Behavior

### Session Creation
A DeviceSession is created when a worker:
- scans a QR code  
- enters a one‑time code  
- is checked in manually  

Creation triggers:
- generation of `session_token`  
- generation of `role_token`  
- setting `is_active = true`  

### Session Validation
Every worker action validates:
- session_token  
- role_token  
- expiration timestamps  
- worker role permissions  

### Session Expiration
Sessions expire when:
- `session_expires_at` is reached  
- worker checks out  
- organizer revokes the session  
- WorkerAssignment becomes inactive  

### Role Token Behavior
Role tokens:
- grant permissions for worker actions  
- are short‑lived  
- may be refreshed without creating a new DeviceSession  
- are tied to a specific WorkerAssignment  

### Heartbeats
Worker UIs may send periodic heartbeats to:
- update `last_seen_at`  
- extend session lifetime (optional)  
- detect abandoned devices  

### Revocation
Sessions may be revoked:
- manually by an organizer  
- automatically when worker checks out  
- automatically when WorkerAssignment is deactivated  

Revocation sets:
- `revoked_at`  
- `is_active = false`  

### Identity Conflict Behavior (optional)
When a new DeviceSession is created for a Competitor who already has an active session:
- The system prompts the user: “Another device is logged in as you. Is that you?”
- If the user confirms, the old session is revoked and the new one becomes active.
- If the user denies, both sessions enter `locked_pending_organizer` state and organizers are notified.

---

## 6. Constraints & Invariants

- A DeviceSession must belong to exactly one Event  
- A DeviceSession must reference exactly one WorkerAssignment  
- Only one active DeviceSession per WorkerAssignment is allowed  
- Session tokens must be opaque and unguessable  
- Role tokens must be short‑lived and tied to the session  
- DeviceSessions cannot be deleted while referenced by audit logs  
- DeviceSessions become invalid when WorkerAssignment becomes inactive  

---

## 7. Notes & Implementation Guidance

- DeviceSession is the core of your passwordless worker authentication model  
- Session tokens should be long, random, and stored hashed  
- Role tokens should be short‑lived (e.g., 5–15 minutes)  
- DeviceSession should be optimized for:
  - fast token validation  
  - fast permission checks  
  - minimal database lookups  
- DeviceSession should not contain competitor or timing data  
- DeviceSession should be event‑scoped and ephemeral  

