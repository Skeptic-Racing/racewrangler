# UI Component Overview (POC Version)

## Purpose
This document defines the user interfaces required for the RaceWrangler POC.  
It describes the screens, components, actions, and data flows for:

- Starter UI  
- Finish Worker UI  
- Timing & Scoring UI  

These UIs demonstrate the core innovation of RaceWrangler:  
**eliminating false triggers and giving timing workers the tools they actually use during an event.**

This is not a full UI specification — it is a high‑level map for Copilot to generate working components.

---

# 1. Starter UI

## 1.1 Purpose
Allow the starter to:
- select the next car  
- take a photo of the car  
- confirm the start trigger  

This creates a new Run in the backend.

## 1.2 Screen Layout
- **Header:** “Starter”
- **Car Selector:**  
  - Dropdown or list of hardcoded cars  
  - Shows car number + class  
- **Camera View / Photo Capture:**  
  - “Take Photo” button  
  - Preview of captured photo  
- **Start Confirmation:**  
  - “Confirm Start” button  
  - Disabled until a photo is taken  

## 1.3 Actions
### Take Photo
- Opens device camera  
- Captures image  
- Stores temporary preview  
- Prepares file for upload  

### Confirm Start
Sends `POST /start` with:
- `car_id`  
- `photo` (multipart upload)  

Backend returns:
- `run_id`  
- `start_time`  
- `start_photo_url`  

Starter UI may show a simple “Run Started” toast.

---

# 2. Finish Worker UI

## 2.1 Purpose
Allow the finish worker to:
- acknowledge a simulated finish trigger  
- select which car just finished by choosing the correct photo  

This completes the Run in the backend.

## 2.2 Screen Layout
- **Header:** “Finish Worker”
- **Trigger Indicator:**  
  - “Finish Trigger Detected” message  
  - Triggered by a button or simulated event  
- **Photo Selection Grid:**  
  - Shows thumbnails of all active runs (awaiting finish)  
  - Each tile shows:
    - photo  
    - car number  
- **Confirm Finish Button:**  
  - Enabled only after selecting a photo  

## 2.3 Actions
### Finish Trigger
- Simulated by a button: “Simulate Finish Trigger”
- When pressed:
  - UI fetches active runs from backend  
  - Displays their photos  

### Select Photo
- Worker taps the correct photo  
- UI highlights selection  

### Confirm Finish
Sends `POST /finish` with:
- `run_id` (from selected photo)

Backend returns:
- `finish_time`  
- `raw_time`  

Finish UI may show a “Run Completed” toast.

---

# 3. Timing & Scoring UI

## 3.1 Purpose
Simulate the real timing trailer workflow:
- monitor active and completed runs  
- apply penalties  
- mark DNFs  
- mark aborted runs  
- correct mistakes  
- watch runs complete in real time  

This makes the POC feel like a real timing system, not just a results viewer.

## 3.2 Screen Layout
- **Header:** “Timing & Scoring”
- **Runs Table:**  
  Columns:
  - Photo thumbnail  
  - Car number  
  - Class  
  - Start time  
  - Finish time  
  - Raw time  
  - Penalties  
  - Adjusted time  
  - Status badges  
  - Action buttons  

### Status Badges
- **Active** (awaiting finish)  
- **Completed**  
- **DNF**  
- **Aborted**  

## 3.3 Actions

### Penalties
For each run:
- **+1 Cone**  
- **+2 Cones**  
- **Clear Penalties**  

Backend stores:
```
penalties: integer
```

Adjusted time = raw_time + penalties * 2.0  
(2 seconds per cone, hardcoded for POC)

### DNF Toggle
- “Mark as DNF”
- “Unmark DNF”

Backend stores:
```
is_dnf: boolean
```

If DNF:
- Hide finish time and raw time  
- Disable penalty buttons  

### Aborted Toggle
- “Mark as Aborted”
- “Unmark Aborted”

Backend stores:
```
is_aborted: boolean
```

If aborted:
- Show “Aborted” in orange  
- Disable penalties and DNF  
- Run does not count toward results (in real system)  
- In POC, just visually differentiate it  

### Refresh / Auto‑Refresh
- Poll `/runs` every 1–2 seconds  
- Or use WebSocket (optional)

---

# 4. Component Summary

| UI | Components | Backend Calls |
|----|------------|----------------|
| **Starter UI** | Car selector, camera capture, start button | `POST /start` |
| **Finish Worker UI** | Trigger button, photo grid, confirm button | `POST /finish`, `GET /runs?status=awaiting_finish` |
| **Timing UI** | Runs table, penalty buttons, DNF toggle, aborted toggle | `GET /runs`, `POST /runs/{id}/update` |

---

# 5. Interaction Flow Summary

1. **Starter UI**
   - Select car  
   - Take photo  
   - Confirm start  
   → Backend creates Run  

2. **Finish Worker UI**
   - Simulate finish trigger  
   - Select matching photo  
   - Confirm finish  
   → Backend completes Run  

3. **Timing & Scoring UI**
   - Displays completed runs  
   - Allows penalties, DNF, aborted marking  
   - Updates run list in real time  

---

# 6. Out of Scope for POC UI

The following UI elements are intentionally excluded:

- Worker login  
- DeviceSession flows  
- Event selection  
- Run group selection  
- Penalties beyond simple cone count  
- Validation  
- Finalization  
- Results pages  
- Admin dashboards  
- CameraSession or OCR UI  

These belong in the full system, not the POC.

---

# 7. Success Criteria

The UI is successful if:

- Starter can take a photo and start a run  
- Finish worker can select the correct photo and finish a run  
- Timing UI shows completed runs with correct times  
- Timing UI allows penalties, DNF, and aborted marking  
- The workflow clearly demonstrates how RaceWrangler avoids false triggers  
- The demo feels like a real timing trailer workflow  

