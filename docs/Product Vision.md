# Product Vision Document
## Project: Race Wrangler – Local-First Timing and Scoring System for Motorsports

### 1. Purpose
Race Wrangler is a modern, resilient, camera-driven timing and scoring system designed for autocross, time trials, hill climbs, and similar timed motorsports. It provides a local-first, browser-based platform with optional cloud connectivity and integrates custom timing cameras built on Raspberry Pi–class Linux edge devices.

The system is engineered around real-world event workflows, volunteer-friendly operation, and deterministic timing accuracy. Race Wrangler embraces the natural variability of motorsports events rather than imposing rigid structures that do not reflect how events actually run.

---

### 2. Problem Statement
Existing grassroots motorsports timing systems suffer from several limitations:

- Outdated hardware and proprietary protocols  
- Poor offline reliability  
- Manual data entry and fragmented workflows  
- No integrated OCR or automated car identification  
- Limited support for long-distance or multi-point timing  
- Interfaces that assume strict run order, which is unrealistic  
- Volunteer workflows that depend on ad-hoc communication  

Race Wrangler solves these problems through a unified, local-first, camera-driven timing system that adapts to real-world event flow.

---

### 3. Target Users
- Event administrators  
- Timing and scoring staff  
- Starters  
- Grid workers  
- Course workers  
- Competitors  
- Spectators and announcers  
- Technical staff deploying hardware  
- Developers and integrators  

---

### 4. High-Level Goals
- Provide a complete timing workflow with integrated OCR  
- Operate fully offline with optional cloud augmentation  
- Support arbitrary split points and long-distance hill climbs  
- Run on commodity hardware (PC + Raspberry Pi cameras + phones)  
- Deliver intuitive, role-specific browser interfaces  
- Maintain microsecond-level timing accuracy  
- Support digital worker assignment delivery to competitors  
- Use staging validation instead of run-order enforcement  
- Provide optional driver appearance consistency checking  
- Offer an open-source foundation with commercial potential  

---

### 5. Non-Goals
- Mandatory cloud services  
- Mandatory user accounts for workers  
- Enforcing strict run order  
- Facial recognition or identity detection  
- Heavy ML processing on timing cameras  
- Complex analytics in the MVP  

---

### 6. Guiding Principles

#### **Local-First Reliability**
All critical operations run on a local server. Internet access is optional.

#### **Deterministic Timing**
Timing cameras provide microsecond timestamps independent of network latency.

#### **Real-World Workflow Alignment**
Race Wrangler reflects the actual physical and operational flow of events:

**Grid → Staging → Start Line → Course → Finish → Grid**

- No strict run order  
- Staging validation performed by the starter  
- Grid workers manage flow and communicate reruns  
- Timing staff resolve anomalies  

#### **Volunteer-Friendly Operation**
Workers use role tokens to access simple, purpose-built UIs.  
No accounts or training required.

#### **Modularity and Extensibility**
Hardware and software components are replaceable, upgradable, and open to integration.

#### **Graceful Failure and Recovery**
Cameras buffer events, the server recovers from restarts, and manual timing is always available.

---

### 7. Key Differentiators

#### **Hybrid OCR Pipeline**
- Phone and Raspberry Pi cameras perform pre-processing  
- Server performs OCR and competitor association  
- Enables fast, accurate number recognition with minimal bandwidth  

#### **Number Mistake Detection (Phase Two)**
A privacy-safe, lightweight system detects:

- A driver appearing with multiple numbers  
- Multiple drivers appearing under the same number  
- Sudden appearance changes  

Runs are flagged for review; no automatic blocking occurs.

#### **Role-Token Access Model**
Workers access role-specific UIs via event-scoped tokens.  
Competitors with accounts can receive digital worker assignments.

#### **Local-First Architecture**
All critical operations run locally, with optional cloud sync for results and competitor profiles.

#### **Mesh-Capable Timing Cameras**
Supports long-distance hill climbs and remote timing points.

#### **Volunteer-Centric Workflow Design**
- Grid workers manage flow and communicate reruns  
- Starter handles staging validation  
- Timing staff resolve anomalies  
- Competitors receive clear, immediate feedback  

---

### 8. Vision Summary
Race Wrangler is a modern, resilient, camera-driven timing system built for the realities of grassroots motorsports. It eliminates the friction of legacy systems, embraces the natural variability of event flow, and empowers volunteers with simple, reliable tools.

By combining local-first architecture, hybrid OCR, phone-based staging validation, and optional driver consistency checking, Race Wrangler sets a new standard for accuracy, usability, and adaptability in motorsports timing.
