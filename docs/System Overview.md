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
- Marking competitors as “rerun pending” when applicable  

Grid workers do **not** perform number/class validation or staging checks.

#### 3.2 Starter
The starter is responsible for:
- Performing final checks of the car and driver before the run begins  
- Reviewing system-provided validation results (number readability, class/run group correctness, Number Mistake Detection warnings)  
- Informing the driver if there is a problem that must be corrected before starting  
- Releasing the car when ready  

The starter is the last human checkpoint before the run begins.

#### 3.3 Timing & Scoring Staff
Timing staff:
- Monitor incoming timing events  
- Resolve OCR ambiguities  
- Reassign runs if necessary  
- Notify grid workers of reruns  
- Approve or dismiss Number Mistake Detection warnings  
- Maintain event integrity and timing accuracy  

#### 3.4 Course Workers
Course workers:
- Report cones and DNFs  
- Communicate with timing staff  
- Do not interact with the timing system directly  

---

### 4. System Components

#### 4.1 Local Server
The local server hosts:
- Timing engine  
- OCR engine  
- Competitor database  
- Worker UI server  
- Event state management  
- Optional cloud sync  

All critical operations run locally.

#### 4.2 Timing Cameras
Raspberry Pi–class devices at:
- Start line  
- Finish line  
- Optional split points  

Each camera:
- Captures images  
- Generates microsecond-accurate timestamps  
- Performs lightweight pre-processing  
- Sends events to the server  

#### 4.3 Worker Interfaces
Workers access role-specific UIs using event-scoped tokens:
- Grid UI  
- Starter UI  
- Timing Console  
- Course Worker UI  
- Admin UI  

No accounts or passwords are required for workers.

---

### 5. Event Flow in the System

#### 5.1 Grid Operations
- Grid workers mark competitors present  
- Cars queue in any order  
- Grid workers send cars toward staging when appropriate  
- Grid workers communicate reruns to drivers returning from the finish  

#### 5.2 Staging Operations
At staging, the starter:
- Performs final checks of the car and driver  
- Reviews system validation results:
  - Number readability  
  - Class/run group correctness  
  - Number Mistake Detection warnings  
- Informs the driver of any issues  
- Releases the car when ready  

#### 5.3 Start Line
- Start timing point triggers the beginning of the run  
- No human validation occurs here  

#### 5.4 Course
- Course workers report cones and DNFs  
- Timing staff record penalties  

#### 5.5 Finish Line
- Finish timing point triggers the end of the run  
- Timing staff review the run for:
  - OCR correctness  
  - Penalties  
  - Rerun conditions  

#### 5.6 Rerun Handling
- Timing staff determine rerun eligibility  
- Grid workers inform the driver upon return  
- Grid UI tracks rerun status  

#### 5.6 Camera Replacement and Session-Based Role Assignment

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
- Worker assignments  
- Event configuration  

No run order is stored or required.

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

### 9. Summary
Race Wrangler’s ConOps is built around real-world event flow and volunteer workflows. It avoids assumptions about run order, places validation responsibility with the starter, and empowers grid workers to manage flow and communicate reruns. The system integrates timing cameras, OCR, and optional Number Mistake Detection to deliver a modern, reliable timing experience.
