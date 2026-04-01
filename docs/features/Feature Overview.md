# Feature Overview Document
## Project: Race Wrangler – Local-First Timing and Scoring System for Motorsports

### 1. Purpose
This document provides a comprehensive overview of the features included in Race Wrangler. It describes the system’s capabilities, the worker-facing interfaces, and the timing and validation features that support accurate, efficient event operation.

---

### 2. Core System Features

---

## 2.1 Local-First Architecture
Race Wrangler is designed to operate fully offline. All critical components—including the timing engine, OCR engine, event database, and worker interfaces—run on a local server. Internet connectivity is optional and used only for cloud sync or results publishing.

---

## 2.2 Timing Cameras
Race Wrangler supports Raspberry Pi–class timing cameras at:
- Start line  
- Finish line  
- Optional split points  

Each camera:
- Captures images  
- Generates microsecond-accurate timestamps  
- Performs lightweight pre-processing  
- Sends timing events to the server  

This ensures deterministic timing independent of network latency.

---

## 2.3 Hybrid OCR Pipeline
Race Wrangler uses a hybrid OCR approach:
- Timing cameras perform pre-processing  
- The server performs OCR and competitor association  

OCR extracts:
- Car number  
- Class letters  

The system then associates the run with the correct competitor.

---

## 2.4 Validation Features
Race Wrangler performs several validation checks to ensure data accuracy:

### **Number Readability**
Ensures the competitor’s number is legible enough for OCR.

### **Class / Run Group Correctness**
Checks that the competitor is running in the correct group.

### **Number Mistake Detection (Phase Two)**
A lightweight, privacy-safe system that detects:
- A driver appearing with multiple numbers  
- Multiple drivers appearing under the same number  
- Sudden appearance changes that may indicate a number swap error  

All warnings are advisory and reviewed by timing staff.

---

## 2.5 Rerun Handling
Race Wrangler supports full rerun management:
- Timing staff determine rerun eligibility  
- Grid workers communicate reruns to drivers  
- Grid UI tracks rerun status  
- Runs marked as reruns are clearly identified in results  

---

### 3. Worker Interfaces

Race Wrangler provides role-specific browser interfaces accessed via event-scoped tokens. No accounts or passwords are required for workers.

---

## 3.1 Grid UI
The Grid UI supports:
- Marking competitors present/absent  
- Tracking rerun status  
- Managing flow of cars toward staging  
- Handling co-driver swaps  
- Viewing basic competitor information  

The Grid UI does **not** include:
- Run order  
- Number/class validation  
- Staging checks  
- OCR correction tools  

---

## 3.2 Starter UI
The Starter UI provides:
- Final validation results before the run begins:
  - Number readability  
  - Class/run group correctness  
  - Number Mistake Detection warnings  
- Clear “Ready / Hold” indicators  
- Simple controls for acknowledging issues  

The starter is the final human checkpoint before the run begins.

---

## 3.3 Timing Console
The Timing Console is used by timing staff to:
- Review incoming timing events  
- Resolve OCR ambiguities  
- Associate runs with competitors  
- Approve or dismiss Number Mistake Detection warnings  
- Apply penalties (cones, DNFs)  
- Determine rerun eligibility  
- Monitor event progress  

---

## 3.4 Course Worker UI
A lightweight interface for:
- Reporting cones  
- Reporting DNFs  
- Communicating course issues  

Course workers do not interact with timing or validation features.

---

## 3.5 Admin UI
The Admin UI supports:
- Event configuration  
- Class and run group setup  
- Worker token generation  
- Timing hardware monitoring  
- Optional cloud sync  
- Results publishing  

---

### 4. Competitor-Facing Features

## 4.1 Digital Worker Assignments (Optional)
Competitors with accounts may receive:
- Worker assignments  
- Shift reminders  
- Personalized event information  

## 4.2 Results Access
Competitors can:
- View their times  
- Review penalties  
- See run-by-run breakdowns  
- Access final results  

---

### 5. Event Structure Features

## 5.1 Classes and Run Groups
Race Wrangler supports:
- Arbitrary class structures  
- Flexible run group definitions  
- Multi-heat and multi-day events  

Run groups define *who runs when*, not a strict run order.

---

## 5.2 Multi-Point Timing
The system supports:
- Start and finish  
- Optional split points  
- Long-distance hill climbs  
- Remote timing points  

All timing points integrate seamlessly into the timing engine.

---

### 6. Data Integrity and Safety Features

## 6.1 Automatic Recovery
- Cameras buffer events  
- Server recovers from restarts  
- Network interruptions do not affect timing accuracy  

## 6.2 Manual Overrides
Timing staff can:
- Reassign runs  
- Correct OCR errors  
- Apply penalties  
- Override system warnings  

---

### 7. Summary
Race Wrangler provides a modern, reliable, and volunteer-friendly timing system built around real-world event workflows. Its hybrid OCR pipeline, validation features, and role-specific interfaces support accurate timing without imposing rigid structures such as run order. Number Mistake Detection enhances data integrity, while rerun handling and clear worker responsibilities ensure smooth event operation.
