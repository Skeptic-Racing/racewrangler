# API Overview

## Purpose
This document defines the high‑level API surface for the RaceWrangler backend.  
It describes the major resource groups, core endpoints, authentication model, and operational flows.  
Detailed per‑resource specifications will be defined in separate files.

The API is designed to support:
- competitor registration and management  
- worker check‑in and authentication  
- timing event ingestion  
- run creation and validation  
- results computation  
- event operations  

---

# 1. API Structure

The API is organized into the following groups:

- **Event Management API**  
  Create and manage events, configurations, run groups, and car classes.

- **Competitor API**  
  Manage drivers, cars, competitors, and registration flows.

- **Worker API**  
  Manage worker assignments, check‑in, device sessions, and role tokens.

- **Timing API**  
  Ingest timing events, create runs, apply penalties, and trigger validation.

- **Results API**  
  Retrieve computed results, standings, and run histories.

Each group will have its own specification file.

---

# 2. Authentication Model

The system uses **DeviceSession‑based authentication**:

### Competitor Sessions
- Created during competitor check‑in  
- Long‑lived (event‑scoped)  
- Low‑privilege (view runs, assignments, schedule)

### Worker Sessions
- Created during worker check‑in  
- Short‑lived role tokens  
- Permissions tied to WorkerAssignment  
- Required for:
  - starter actions  
  - grid actions  
  - course worker actions  
  - timing actions  

### Admin Sessions
- (Optional for POC)  
- Simple API key or environment‑based auth  

---

# 3. Core Resources

The API exposes the following top‑level resources:

### Event Resources
- `/events`
- `/events/{event_id}`
- `/events/{event_id}/configuration`
- `/events/{event_id}/run-groups`
- `/events/{event_id}/car-classes`

### Competitor Resources
- `/drivers`
- `/cars`
- `/events/{event_id}/competitors`

### Worker Resources
- `/events/{event_id}/worker-assignments`
- `/device-sessions`
- `/device-sessions/{session_id}/refresh`
- `/worker/check-in`
- `/worker/check-out`

### Timing Resources
- `/events/{event_id}/timing-events`
- `/events/{event_id}/runs`
- `/events/{event_id}/runs/{run_id}/penalties`
- `/events/{event_id}/runs/{run_id}/validate`
- `/events/{event_id}/runs/{run_id}/finalize`

### Results Resources
- `/events/{event_id}/results`
- `/events/{event_id}/results/{competitor_id}`
- `/events/{event_id}/leaderboard`
- `/events/{event_id}/pax-leaderboard`

---

# 4. High-Level Flows

## 4.1 Competitor Check‑In Flow
1. Competitor scans on‑site QR  
2. Identifies themselves (name, number, membership ID, or claim code)  
3. System creates a **DeviceSession**  
4. Competitor gains access to:
   - schedule  
   - run group  
   - worker assignment (if any)  
   - run history  

## 4.2 Worker Check‑In Flow
1. Worker scans Worker Check‑In QR  
2. System identifies competitor  
3. Worker selects or is assigned a role  
4. System creates:
   - WorkerAssignment  
   - DeviceSession (if needed)  
   - role token  
5. Worker gains access to worker UI  

## 4.3 Timing Event Flow
1. Timing device posts a `TimingEvent`  
2. System:
   - associates it with a competitor  
   - creates or updates a Run  
   - applies penalties  
   - triggers validation  
3. Starter/grid/course workers may add metadata  

## 4.4 Run Validation Flow
1. ValidationResult is created  
2. If invalid:
   - run is marked invalid  
   - rerun reason is required  
3. If valid:
   - run is finalized or queued for finalization  

## 4.5 Results Flow
1. Runs are finalized  
2. Results are computed:
   - raw  
   - class  
   - PAX  
3. Results are published via Results API  

---

# 5. Response Format

All responses follow this structure:

```
{
  "success": true/false,
  "data": { ... },
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

Errors use consistent codes such as:
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `CONFLICT`
- `INTERNAL_ERROR`

---

# 6. Versioning

The API is versioned via URL prefix:

```
/api/v1/...
```

Future versions will be introduced as `/api/v2`.

---

# 7. Next Steps

Detailed endpoint specifications will be created in:

- `competitor-api.md`  
- `worker-api.md`  
- `device-session-api.md`  
- `run-api.md`  
- `timing-api.md`  
- `results-api.md`  

These documents will define:
- request/response schemas  
- authentication requirements  
- error cases  
- operational notes  

