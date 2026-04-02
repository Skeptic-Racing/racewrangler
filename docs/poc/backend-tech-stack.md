# Backend Tech Stack (POC Version)

## Purpose
This document defines the backend technologies, architecture, and conventions used for the RaceWrangler POC.  
It provides Copilot with the constraints and structure needed to generate consistent, runnable backend code.

The POC backend is intentionally minimal.  
It supports only the flows required for the demo:
- Starter creates a run with a photo  
- Finish worker selects the matching photo  
- Timing UI displays completed runs  

---

# 1. Technology Choices

## 1.1 Framework
**FastAPI** (Python)

Reasons:
- Extremely fast to scaffold  
- Automatic OpenAPI docs  
- Easy file uploads  
- Simple async support  
- Copilot generates excellent FastAPI code  

## 1.2 Database
**SQLite** (file‑based or in‑memory)

Reasons:
- Zero configuration  
- Perfect for a POC  
- Works seamlessly with SQLAlchemy  

## 1.3 ORM
**SQLAlchemy** (declarative models)

Reasons:
- Copilot knows it well  
- Easy to define simple models  
- Works with SQLite out of the box  

## 1.4 Storage
**Local file storage** for photos

Structure:
```
/storage/photos/start/
/storage/photos/finish/
```

No cloud storage needed for the POC.

## 1.5 API Format
JSON responses using a consistent envelope:
```
{
  "success": true/false,
  "data": { ... },
  "error": { "code": "...", "message": "..." }
}
```

---

# 2. Backend Architecture

## 2.1 High-Level Components
The POC backend consists of:

- **Models**
  - Car (hardcoded list)
  - Run (database table)

- **Routes**
  - `POST /start` — create run + upload photo
  - `POST /finish` — complete run + associate photo
  - `GET /runs` — list completed runs

- **Services**
  - run_service.py — create, update, list runs
  - photo_service.py — save and retrieve photos

- **Storage**
  - local filesystem for photos

- **No authentication**
  - All endpoints are open for the POC

---

# 3. Data Model (POC Version)

## 3.1 Car (hardcoded)
```
{
  "id": 1,
  "number": "42",
  "class": "STX"
}
```

A small list of 5–10 cars is sufficient.

## 3.2 Run (database model)
Fields:
- `id` — primary key  
- `car_id` — foreign key to hardcoded list  
- `start_time` — timestamp  
- `finish_time` — timestamp  
- `raw_time` — computed float (seconds)  
- `start_photo_url` — string  
- `finish_confirmed` — boolean  

No penalties, validation, or finalization in the POC.

---

# 4. API Endpoints (POC Version)

## 4.1 POST /start
Creates a new run.

Input:
- `car_id`
- `photo` (multipart upload)

Behavior:
- Save photo to `/storage/photos/start/`
- Create Run with:
  - car_id
  - start_time = now()
  - start_photo_url
  - finish_confirmed = false

Output:
- run_id
- start_time
- start_photo_url

---

## 4.2 POST /finish
Completes a run.

Input:
- `run_id`
- (optional) `photo_id` or `photo_url` selected by finish worker

Behavior:
- Set finish_time = now()
- Compute raw_time = finish_time - start_time
- Set finish_confirmed = true

Output:
- run_id
- finish_time
- raw_time

---

## 4.3 GET /runs
Returns all completed runs.

Output:
List of:
- car number
- class
- start_time
- finish_time
- raw_time
- start_photo_url

---

# 5. Simulated Timing Hardware

The POC simulates timing triggers:

### Start Trigger
Triggered when the starter taps “Confirm Start”.

### Finish Trigger
Triggered when the finish worker taps “Finish Trigger”.

No real sensors are used.

---

# 6. Project Structure

Recommended layout:

```
backend/
  main.py
  models/
    run.py
  services/
    run_service.py
    photo_service.py
  routes/
    start.py
    finish.py
    runs.py
  storage/
    photos/
      start/
      finish/
```

---

# 7. Build & Run

The POC backend should run with:

```
uvicorn main:app --reload
```

No environment variables required.

---

# 8. Out of Scope for POC

The backend does NOT include:

- Worker authentication  
- DeviceSession  
- WorkerAssignment  
- Event configuration  
- Penalties  
- Validation  
- Finalization  
- Reruns  
- Results computation  
- CameraSession  
- OCR  
- WebSockets (optional)  
- Real timing hardware integration  

These belong in the full system, not the POC.

---

# 9. Success Criteria

The backend is successful if:

- Starter can upload a photo and create a run  
- Finish worker can select a photo and complete a run  
- Timing UI can list completed runs  
- The workflow clearly demonstrates how RaceWrangler avoids false triggers  

