# Camera Entity Specification

## 1. Purpose
A **Camera** represents a physical timing device responsible for generating TimingEvents. Cameras are the authoritative hardware sources for start, finish, and split detections. They provide timestamps, optional sequence numbers, and raw payloads that feed the timing pipeline.

Cameras are immutable hardware records. Their assignment to timing roles (start, finish, split) is handled by CameraSessions.

---

## 2. Definition
A Camera is a hardware or software timing device registered to an Event. It may be:
- a custom Race Wrangler timing camera  
- a third‑party timing sensor  
- a virtual or simulated device (for testing)

Cameras emit TimingEvents, which are immutable atomic records.  
Cameras do **not** store timing roles; roles are assigned via CameraSessions.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the camera  
- **event_id** — Reference to the Event  
- **name** — Human‑readable identifier (e.g., “Start Camera A”, “Finish Camera 1”)  
- **is_active** — Whether the camera is currently expected to produce events  

### Hardware Fields
- **device_type** — Hardware model or type (e.g., “RR‑Cam‑v2”, “USB‑Trigger”)  
- **serial_number** — Optional hardware serial number  
- **firmware_version** — Optional firmware version  

### Networking Fields
- **ip_address** — Last known IP address  
- **connection_status** — One of: `online`, `offline`, `unknown`  
- **last_heartbeat_at** — Timestamp of last successful communication  

### Metadata
- **notes** — Freeform notes for timing staff  
- **created_at** — Timestamp when the camera was registered  
- **updated_at** — Timestamp when the camera was last modified  

---

## 4. Relationships

### Parent
- **Event** — Cameras belong to an event  

### Children
- **TimingEvent** — Cameras generate zero or many TimingEvents  
- **CameraSession** — Cameras may be assigned to one or more CameraSessions over time  

---

## 5. Operational Behavior

### Event Flow
```
Camera → TimingEvent → Run association → Validation → Results
```

### Heartbeats
- Cameras may periodically send heartbeat messages  
- Heartbeats update:
  - `connection_status`
  - `last_heartbeat_at`
  - optional device metadata (firmware, uptime, etc.)

### Event Generation
- Cameras emit raw detections  
- The system converts detections into TimingEvents  
- Cameras do not classify events (start/finish) — classification is handled by validation  

---

## 6. Camera Replacement & Session Management

Cameras are immutable hardware records. When a camera fails:

1. A new CameraSession is created for the replacement hardware  
2. The old CameraSession is closed  
3. TimingEvents continue flowing without interruption  
4. Historical TimingEvents remain tied to the original camera  

This ensures:
- clean audit trails  
- no mutation of camera roles  
- no rewriting of TimingEvents  
- seamless hardware replacement during an event  

---

## 7. Constraints & Invariants

- A camera must belong to exactly one event  
- A camera may generate zero or many TimingEvents  
- Cameras do **not** store timing roles  
- Cameras should not be deleted once TimingEvents exist  
- Camera metadata should be auditable for post‑event review  

---

## 8. Notes & Implementation Guidance

- Cameras should be registered before the event begins to ensure consistent IDs  
- Avoid dynamic reassignment of camera roles on the Camera entity  
- Store raw payloads from cameras for debugging and auditability  
- Connection status should not be used as a hard requirement for event flow  
- The system should tolerate:
  - intermittent connectivity  
  - duplicate triggers  
  - out‑of‑order events  
- Cameras should ideally provide:
  - monotonic sequence numbers  
  - stable timestamps  
  - consistent payload formats  
