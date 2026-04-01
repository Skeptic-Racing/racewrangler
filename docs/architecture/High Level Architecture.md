# High‑Level Architecture Document
## Project: Race Wrangler – Local‑First Timing and Scoring System for Motorsports

### 1. Purpose
This document describes the high‑level architecture of Race Wrangler, including system components, data flow, timing pipeline, validation pipeline, worker interfaces, and hardware integration. It provides a structural overview of how the system operates during a motorsports event.

---

### 2. Architectural Goals

#### **Local‑First Reliability**
All critical operations run on a local server. Internet access is optional.

#### **Deterministic Timing**
Timing cameras generate microsecond‑accurate timestamps independent of network latency.

#### **Real‑World Workflow Alignment**
Architecture reflects the actual physical flow of vehicles:

**Grid → Staging (Starter) → Start Line → Course → Finish → Grid**

No run order is assumed or enforced.

#### **Volunteer‑Friendly Operation**
Role‑specific browser interfaces require no accounts or training.

#### **Modularity**
Timing cameras, OCR, validation, and UI layers are independently replaceable and extensible.

#### **Graceful Failure**
Cameras buffer events, the server recovers from restarts, and manual timing is always available.

---

### 3. System Components

---

## 3.1 Local Server
The local server hosts all critical system functions:

- Timing engine  
- OCR engine  
- Validation engine  
- Number Mistake Detection (Phase Two)  
- Event database  
- Worker UI server  
- Admin tools  
- Optional cloud sync  

The server is the authoritative source of event state.

---

## 3.2 Timing Cameras
Timing cameras are Raspberry Pi–class devices deployed at:

- Start line  
- Finish line  
- Optional split points  

Each camera performs:
- Image capture  
- Microsecond timestamp generation  
- Lightweight pre‑processing  
- Event buffering  
- Transmission of timing events to the server  

Timing accuracy is independent of network latency.

---

## 3.3 Worker Interfaces
Workers access role‑specific UIs using event‑scoped tokens:

- Grid UI  
- Starter UI  
- Timing Console  
- Course Worker UI  
- Admin UI  

All interfaces run in a browser and require no installation.

---

## 3.4 Competitor Database
Stores:
- Competitor profiles  
- Car numbers  
- Class assignments  
- Run group assignments  
- Worker assignments  
- Event participation history  

---

## 3.5 Event State Engine
Tracks:
- Runs  
- Reruns  
- Penalties  
- Timing events  
- Validation results  
- Heat and group progression  

No run order is stored or required.

---

### 4. Timing Pipeline Architecture

The timing pipeline processes events from capture to final scoring.

---

## 4.1 Event Capture
1. Timing camera captures an image  
2. Camera generates a microsecond timestamp  
3. Camera performs lightweight pre‑processing  
4. Event is sent to the server  

---

## 4.2 OCR Processing
The server:
- Receives the image  
- Performs OCR  
- Extracts car number and class letters  
- Associates the run with a competitor  

If OCR is uncertain, timing staff resolve the ambiguity.

---

## 4.3 Run Association
The system associates:
- Start event  
- Finish event  
- Optional split events  
- Penalties  
- Validation results  

into a single run record.

---

## 4.4 Rerun Handling
Timing staff determine rerun eligibility.  
Grid workers communicate reruns to drivers.  
The system tracks rerun status in the event state engine.

---

### 5. Validation Pipeline Architecture

The validation pipeline ensures correctness before and after each run.

---

## 5.1 Pre‑Run Validation (Starter)
The starter reviews:
- Number readability  
- Class/run group correctness  
- Number Mistake Detection warnings  

The starter performs final checks of the car and driver before releasing them.

---

## 5.2 Post‑Run Validation (Timing Staff)
Timing staff review:
- OCR correctness  
- Penalties  
- Rerun conditions  
- Number Mistake Detection warnings  

---

## 5.3 Number Mistake Detection (Phase Two)
A lightweight, privacy‑safe system that detects:
- A driver appearing with multiple numbers  
- Multiple drivers appearing under the same number  
- Sudden appearance changes  

Warnings are advisory only.

---

### 6. Worker Interface Architecture

---

## 6.1 Grid UI
Supports:
- Competitor presence tracking  
- Rerun communication  
- Flow management  
- Co‑driver handling  

Does **not** include:
- Run order  
- Validation checks  
- OCR correction  

---

## 6.2 Starter UI
Provides:
- Final validation results  
- Clear “Ready / Hold” indicators  
- Simple acknowledgment controls  

The starter is the final human checkpoint before the run.

---

## 6.3 Timing Console
Provides:
- OCR review  
- Run association tools  
- Penalty entry  
- Rerun determination  
- Validation review  

---

## 6.4 Course Worker UI
Provides:
- Cone reporting  
- DNF reporting  

---

## 6.5 Admin UI
Provides:
- Event configuration  
- Class and run group setup  
- Worker token generation  
- Timing hardware monitoring  
- Optional cloud sync  

---

### 7. Data Model Overview

The system stores:
- Competitors  
- Classes  
- Run groups  
- Runs and reruns  
- Timing events  
- Validation results  
- Worker assignments  
- Event configuration  

No run order is stored.

---

### 8. Hardware Architecture

- Local server (Windows, Linux, or macOS)  
- Raspberry Pi–class timing cameras  
- Worker devices (phones, tablets, laptops)  
- Local Wi‑Fi network  

All components communicate over the local network.

---

### 9. Summary
Race Wrangler’s architecture is built around real‑world event flow, deterministic timing, and volunteer‑friendly operation. The system avoids assumptions about run order, places final validation responsibility with the starter, and empowers grid workers to manage flow and communicate reruns. Timing cameras, OCR, validation, and Number Mistake Detection work together to deliver a modern, reliable timing system for grassroots motorsports.
