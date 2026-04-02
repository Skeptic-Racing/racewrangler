# RaceWrangler POC Scope Document

## Purpose
This Proof‑of‑Concept (POC) demonstrates the core innovation of RaceWrangler’s timing and scoring system:  
**eliminating false triggers by putting humans in the loop at the right moments, while giving timing trailer workers the tools they actually use during an event.**

The POC is intentionally minimal.  
It is not a full timing system.  
It is a demo of the *workflow* that solves the biggest pain points for clubs.

This document defines exactly what the POC must include, what it may stub, and what is explicitly out of scope.

---

# 1. POC Goals

The POC must demonstrate:

### **1. Starter confirms the correct car at the start line**
- Starter selects the next car  
- Starter takes a photo of the car  
- Starter confirms the start trigger  
- Backend creates a Run with the photo  

### **2. Finish worker confirms which car crossed the finish**
- Finish worker receives a simulated finish trigger  
- Finish worker selects the matching photo  
- Backend completes the Run  

### **3. Timing & Scoring UI simulates real timing trailer workflow**
- Shows active and completed runs  
- Allows marking penalties  
- Allows marking DNF  
- Allows marking aborted runs  
- Shows adjusted times  
- Updates in real time  

### **4. Demonstrate that RaceWrangler avoids false triggers**
This is the narrative of the demo.

---

# 2. POC Non‑Goals (Explicitly Out of Scope)

The POC does **not** include:

- Worker authentication  
- DeviceSession logic  
- WorkerAssignment logic  
- Event creation or configuration  
- Competitor registration  
- Run groups  
- Validation logic  
- Finalization logic  
- Reruns  
- Results computation  
- CameraSession or OCR  
- Real timing hardware integration  
- Multi‑event support  
- Admin UI  
- Series scoring  

These belong in the full system, not the POC.

---

# 3. POC Architecture

## Backend
- FastAPI service  
- SQLite or in‑memory DB  
- Local file storage for photos  
- Minimal endpoints:
  - `POST /start` — create run + upload photo  
  - `POST /finish` — complete run  
  - `GET /runs` — list runs  
  - `POST /runs/{id}/update` — update penalties, DNF, aborted  

## Frontend
Three simple UIs:

### **Starter UI**
- Select car  
- Take photo  
- Confirm start  

### **Finish Worker UI**
- Simulate finish trigger  
- Select matching photo  
- Confirm finish  

### **Timing & Scoring UI**
- View active + completed runs  
- Apply penalties  
- Mark DNF  
- Mark aborted  
- See adjusted times  

---

# 4. Data Model (POC Version)

## **Car** (hardcoded)
- `id`  
- `number`  
- `class`  

## **Run** (database model)
- `id`  
- `car_id`  
- `start_time`  
- `finish_time`  
- `raw_time`  
- `start_photo_url`  
- `penalties` (integer, default 0)  
- `is_dnf` (boolean, default false)  
- `is_aborted` (boolean, default false)  
- `finish_confirmed` (boolean, default false)  

No other entities are needed for the POC.

---

# 5. Timing Flow (POC Version)

## **1. Starter Flow**
1. Starter selects next car  
2. Starter takes a photo  
3. Starter taps “Confirm Start”  
4. Backend:
   - stores photo  
   - creates Run with start timestamp  
   - marks run as “awaiting finish”  

## **2. Finish Worker Flow**
1. Finish trigger is simulated  
2. Finish UI displays photos of all “awaiting finish” runs  
3. Worker selects the correct photo  
4. Backend:
   - updates Run with finish timestamp  
   - computes raw time  
   - marks run as complete  

## **3. Timing & Scoring Flow**
- UI displays active + completed runs  
- Worker may:
  - add penalties  
  - clear penalties  
  - mark DNF  
  - unmark DNF  
  - mark aborted  
  - unmark aborted  
- Backend updates run via `/runs/{id}/update`  

---

# 6. Simulated Hardware

The POC simulates timing hardware:

### Start Trigger
Triggered when the starter taps “Confirm Start”.

### Finish Trigger
Triggered when the finish worker taps “Simulate Finish Trigger”.

No real sensors are used.

---

# 7. API Endpoints (POC Version)

### **POST /start**
Creates a run with a photo.

### **POST /finish**
Completes a run.

### **GET /runs**
Returns all runs (active + completed).

### **POST /runs/{id}/update**
Updates:
- penalties  
- is_dnf  
- is_aborted  

---

# 8. Demo Script (Recommended)

1. Show Starter UI  
2. Select a car  
3. Take a photo  
4. Confirm start  
5. Switch to Finish UI  
6. Simulate finish trigger  
7. Select the matching photo  
8. Confirm finish  
9. Switch to Timing UI  
10. Show the completed run  
11. Add penalties  
12. Mark DNF  
13. Mark aborted  
14. Show how the system updates instantly  

This tells the story cleanly and visually.

---

# 9. Success Criteria

The POC is successful if:

- A run can be started with a photo  
- A run can be finished by selecting that photo  
- Timing UI shows completed runs with correct times  
- Timing UI allows penalties, DNF, and aborted marking  
- The workflow clearly demonstrates how RaceWrangler avoids false triggers  
- The demo feels like a real timing trailer workflow  

