# Event Entity Specification

## 1. Purpose
An **Event** is the root container for all timing, competitor, configuration, and operational data within Race Wrangler. Every other entity — cameras, runs, competitors, penalties, validation results, finalizations — exists within the scope of a single Event.

The Event defines:
- the lifecycle of the competition  
- the configuration and ruleset  
- the set of competitors and classes  
- the timing pipeline context  
- the operational structure (workers, devices, run groups)  

---

## 2. Definition
An Event represents a single competitive motorsports event (e.g., an autocross, rallycross, hillclimb, or track day). It encapsulates all data and workflows required to run, validate, and finalize results for that event.

Events are immutable once completed and finalized, but may be updated during setup and active competition.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the event  
- **name** — Human‑readable event name  
- **date** — Date of the event (or start date for multi‑day events)  
- **status** — One of: `draft`, `active`, `paused`, `completed`, `archived`  
- **location** — Optional venue or geographic location  

### Lifecycle Fields
- **created_at** — Timestamp when the event was created  
- **updated_at** — Timestamp when the event was last modified  
- **started_at** — Timestamp when the event officially began (nullable)  
- **completed_at** — Timestamp when the event was completed (nullable)  

### Configuration Fields
- **configuration_id** — Reference to EventConfiguration  
- **timezone** — Timezone used for all timestamps  
- **ruleset_version** — Version of the ruleset applied to this event  

### Metadata
- **notes** — Freeform notes for organizers  
- **tags** — Optional labels for categorization (e.g., “regional”, “national”, “test”)  

---

## 4. Relationships

### Children
- **CarClass** — Classes defined for the event  
- **RunGroup** — Groups of competitors scheduled to run together  
- **Competitor** — Participants registered for the event  
- **Run** — All runs performed during the event  
- **Camera** — Cameras assigned to the event  
- **CameraSession** — Role assignments for cameras  
- **TimingEvent** — All timing detections for the event  
- **ValidationResult** — Validation passes for runs  
- **Penalty** — Penalties applied to runs  
- **Finalization** — Finalized results for runs  
- **WorkerAssignment** — Worker roles for the event  
- **DeviceSession** — Worker device authentication sessions  
- **RerunReason** — Reasons for rerun assignment  
- **EventConfiguration** — Event‑level settings  

### Parent
None — Event is the root of the data model.

---

## 5. Operational Behavior

### Event Lifecycle
```
draft → active → (paused) → completed → archived
```

### Draft
- Event is being configured  
- Competitors, classes, and run groups may be added  
- Cameras may be registered  
- No timing data should be ingested  

### Active
- Timing pipeline is live  
- Cameras and OCR are ingesting data  
- Runs are being created and validated  
- Worker assignments are active  

### Paused (optional)
- Temporary halt in competition  
- Timing ingestion may be suspended  
- Useful for lunch breaks, weather delays, or course resets  

### Completed
- All runs have been performed  
- Validation and finalization occur  
- Results are locked  

### Archived
- Event is read‑only  
- Upstream timing data may be compacted or purged  
- Finalization snapshots remain intact  

---

## 6. Constraints & Invariants

- An Event must be in `active` state to ingest TimingEvents  
- An Event must be in `completed` state before finalization  
- An Event cannot be deleted once finalized  
- All child entities must reference exactly one Event  
- EventConfiguration must be immutable once the event becomes active  
- Timezone must be set before any timing data is ingested  

---

## 7. Notes & Implementation Guidance

- Event is the anchor for all other entities; all queries should be scoped by event_id  
- EventConfiguration should be versioned to allow rule changes between events  
- Multi‑day events should use `date` as the start date and rely on timestamps for full coverage  
- Archiving should trigger optional data compaction:
  - TimingEvents may be purged  
  - ValidationResults may be reduced  
  - Penalties may be summarized  
  - Finalization snapshots remain authoritative  
- Event status transitions should be explicit and logged  
- Event should support:
  - pre‑event setup  
  - live timing  
  - post‑event auditing  
  - long‑term archival  

