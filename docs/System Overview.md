# System Overview / Concept of Operations
## Project: Race Wrangler – Local-First Timing and Scoring System for Motorsports

### 1. Purpose
This document describes how Race Wrangler operates during a motorsports event. It defines the physical flow of vehicles, the responsibilities of workers, the interactions between system components, and the end-to-end timing workflow. The goal is to ensure that Race Wrangler aligns with real-world event operations and supports volunteers with simple, reliable tools.

---

### 2. Physical Flow of Vehicles
Race Wrangler is designed around the actual physical movement of cars at autocross and similar timed motorsports events:

**Grid → Staging (Starter) → Start Line → Course → Finish Line → Grid**

- **Grid:** Cars wait here until they are released toward staging.  
- **Staging:** The starter performs final checks before the run begins.  
- **Start Line:** The run officially begins when the start timing point triggers.  
- **Course:** The competitor drives the timed course.  
- **Finish Line:** The run ends when the finish timing point triggers.  
- **Return to Grid:** The competitor returns to grid for subsequent runs.

Race Wrangler does **not** assume or enforce any run order. Cars may arrive at staging in any sequence.

---

### 3. Worker Roles in Event Flow

#### 3.1 Grid Workers
Grid workers manage:
- Competitor presence  
- Flow of cars toward staging  
- Co-driver swaps  
- Cars that need to cool down or skip temporarily  
- Communicating reruns to drivers after they return from the finish   

Grid workers do **not** perform number/class validation or staging checks.

---

### 3.2 Starter
The starter is the final human checkpoint before a run begins.

Responsibilities:
- Perform final checks of the car and driver  
- Review system‑provided validation results:
  - Number readability  
  - Class/run group correctness  
  - Number Mistake Detection warnings  
- Inform the driver of any issues  
- Release the car when ready  

**Durable POC‑discovered behaviors now included:**
- Starter UI displays a **global Hold Start** banner when timing staff have paused starts.  
- Starter UI may display **expected elapsed time** for the next finishing car when a shared finish trigger is active.

---

### 3.3 Timing & Scoring Staff
Timing staff maintain event integrity and resolve ambiguities.

Responsibilities:
- Monitor incoming timing events  
- Review and correct OCR results  
- Associate runs with competitors
- Flag competitors for reruns
- Approve or dismiss Number Mistake Detection warnings  
- Determine rerun eligibility  
- Notify grid workers of reruns  
- Apply penalties (cones, DNFs)  
- Oversee timing accuracy and event progression  
- Timing staff may assert or release a **global Hold Start** state.  
- Timing staff may raise a **shared finish trigger** that Finish Workers on other devices observe.

---

#### 3.4 Course Workers
Course workers:
- Report cones and DNFs  
- Maintain course safety  
- Reset cones and monitor course conditions  

They do **not** interact with the timing system directly.

---

### 3.5 Event Administrators
Administrators configure the event and oversee system operation.

Responsibilities:
- Configure classes, run groups, and event structure  
- Manage worker tokens  
- Oversee timing hardware deployment  
- Monitor system health  
- Publish results  

---

## 4. System Components

### 4.1 Local Server
Hosts:
- Timing engine  
- OCR engine  
- Validation engine  
- Number Mistake Detection  
- Event database  
- Worker UI server  
- Optional cloud sync  

All critical operations run locally.

---

### 4.2 Timing Cameras
Timing cameras are deployed at:
- Start line  
- Finish line  
- Optional split points  

Each camera:
- Captures images  
- Generates microsecond timestamps  
- Performs lightweight pre‑processing  
- Buffers events  
- Sends timing events to the server  

Timing accuracy is independent of network latency.

---

### 4.3 Worker Interfaces
Workers access role‑specific UIs using event‑scoped tokens:

- Grid UI  
- Starter UI  
- Timing Console  
- Course Worker UI  
- Admin UI  

All interfaces run in a browser.

---

### 4.4 Competitor Database
Stores:
- Competitor profiles  
- Car numbers  
- Class assignments  
- Run group assignments  
- Worker assignments  
- Event participation history  

---

### 4.5 Event State Engine
Tracks:
- Runs  
- Reruns  
- Penalties  
- Timing events  
- Validation results  
- Heat and group progression  

**Durable POC‑discovered addition:**  
A global **SystemState** object containing:
- `is_start_held`  
- `finish_triggered_at`  

This supports synchronized multi‑device behavior.

---

### 4.6 CameraSession Component
CameraSessions bind physical cameras to timing roles and allow hardware replacement without data mutation.

---

## 5. Event Flow in the System

### 5.1 Grid Operations
- Grid workers mark competitors present  
- Cars queue in any order  
- Grid workers send cars toward staging  
- Grid workers communicate reruns  

---

### 5.2 Staging Operations
Starter:
- Performs final checks  
- Reviews validation results  
- Resolves issues  
- Releases the car  

**Durable POC behavior:**  
Starter sees **Hold Start** state if timing staff have paused starts.

---

### 5.3 Start Line
- Start timing point triggers the run  
- No human validation occurs here  

---

### 5.4 Course
- Course workers report cones and DNFs  
- Timing staff record penalties  

#### 5.5 Finish Line
- Finish timing point triggers the end of the run  
- Finish worker reviews the run for:
  - OCR correctness  
  - Penalties  
  - Rerun conditions  

#### 5.6 Rerun Handling
- Timing staff determine rerun eligibility  
- Grid workers inform the driver  
- Grid UI tracks rerun status  

#### 5.7 Camera Replacement and Session-Based Role Assignment

Cameras may fail during an event. To support seamless hardware replacement, Race Wrangler uses **CameraSessions** to bind a physical camera to a timing role (start, finish, split).

When a camera fails:
1. A new CameraSession is created for the replacement camera  
2. The old session is closed  
3. TimingEvents continue flowing without interruption  
4. No TimingEvents are reassigned or rewritten  

This ensures operational continuity and preserves a complete audit trail.


---

### 6. OCR and Validation Pipeline

#### 6.1 OCR Flow
1. Image captured at timing point  
2. Pre-processing performed on the device  
3. Image sent to server  
4. OCR engine extracts:
   - Car number  
   - Class letters  
5. System associates run with competitor  

#### 6.2 Validation Checks
The system performs:
- Number readability checks  
- Class/run group correctness checks  
- **Number Mistake Detection** (Phase Two)  
  - Detects mismatches such as:
    - Same driver appearing with multiple numbers  
    - Multiple drivers appearing under the same number  
    - Sudden appearance changes  

All warnings are advisory only.

---

### 7. Data Model Overview
The system tracks:
- Competitors  
- Classes  
- Run groups  
- Runs and reruns  
- Timing events  
- Penalties  
- Validation results  
- Worker assignments  
- Event configuration  
- A global **SystemState** object for synchronized operational controls.

---

### 8. Operational Modes

#### 8.1 Offline Mode
All features operate without internet access.

#### 8.2 Online Mode (Optional)
Cloud sync may provide:
- Competitor profile import  
- Results publishing  
- Remote monitoring  

---

### 8.3 Multi‑Device Synchronization
Race Wrangler supports synchronized operational states across multiple worker devices, including:

- Shared finish trigger  
- Global Hold Start  
- UTC‑normalized time rendering  
- Shared active run state  

This ensures consistent behavior during multi‑device operation.

---

## 9. Summary
Race Wrangler’s architecture is built around real‑world event flow, deterministic timing, and volunteer‑friendly operation.  
The system avoids assumptions about run order, places final validation responsibility with the starter, and empowers grid workers to manage flow and communicate reruns.

The POC revealed several durable operational behaviors — such as **Hold Start**, **shared finish trigger**, **trigger‑anchored finish timing**, and **multi‑device synchronization** — which have now been incorporated into the long‑term system model.

