# Stakeholder & User Roles Document
## Project: Race Wrangler – Local-First Timing and Scoring System for Motorsports

### 1. Purpose
This document defines the roles, responsibilities, and system interactions for all stakeholders involved in operating Race Wrangler during a motorsports event. It ensures that each worker type has clear, realistic duties aligned with actual event workflows.

---

### 2. Overview of Worker Roles
Race Wrangler supports a distributed, volunteer-friendly workflow. Each worker accesses a role-specific interface using an event-scoped token. No accounts or passwords are required for workers.

Primary roles include:
- Grid Workers  
- Starter  
- Timing & Scoring Staff  
- Course Workers  
- Event Administrators  
- Competitors  

---

### 3. Role Definitions

---

## 3.1 Grid Workers

### **Purpose**
Grid workers manage the flow of cars and competitor readiness. They are the first point of contact for drivers returning from the finish and play a key role in communicating reruns.

### **Responsibilities**
- Track competitor presence in grid  
- Manage the flow of cars toward staging  
- Handle co-driver swaps and grid spot organization  
- Direct cars that need to cool down or temporarily skip  
- Communicate reruns to drivers returning from the finish  
- Mark competitors as “rerun pending” in the Grid UI  
- Maintain awareness of event progress and heat transitions  

### **What Grid Workers Do *Not* Do**
- They do **not** perform number or class validation  
- They do **not** perform staging checks  
- They do **not** enforce run order  
- They do **not** handle OCR corrections  
- They do **not** resolve Number Mistake Detection warnings  

Grid workers focus on flow, communication, and competitor readiness.

---

## 3.2 Starter

### **Purpose**
The starter is the final human checkpoint before a run begins. They ensure that the car and driver are ready and that the system has validated the competitor’s information.

### **Responsibilities**
- Perform final checks of the car and driver before releasing them  
- Review system-provided validation results, including:
  - Number readability  
  - Class/run group correctness  
  - Number Mistake Detection warnings  
- Inform the driver if a correction is required before starting  
- Hold the car until issues are resolved  
- Release the car when ready  

### **What the Starter Does *Not* Do**
- They do **not** manage grid flow  
- They do **not** communicate reruns  
- They do **not** resolve OCR ambiguities (timing staff handles this)  

The starter ensures correctness and safety at the final stage before the run.

---

## 3.3 Timing & Scoring Staff

### **Purpose**
Timing staff maintain event integrity, resolve ambiguities, and ensure accurate results.

### **Responsibilities**
- Monitor incoming timing events  
- Review and correct OCR results  
- Associate runs with competitors when OCR is uncertain  
- Approve or dismiss Number Mistake Detection warnings  
- Determine rerun eligibility  
- Notify grid workers of reruns  
- Apply penalties (cones, DNFs)  
- Oversee timing accuracy and event progression  

### **What Timing Staff Do *Not* Do**
- They do **not** manage grid flow  
- They do **not** perform staging checks  
- They do **not** interact directly with competitors  

Timing staff operate primarily from the timing trailer or control area.

---

## 3.4 Course Workers

### **Purpose**
Course workers observe the course and report penalties.

### **Responsibilities**
- Report cones and DNFs to timing staff  
- Maintain course safety  
- Reset cones and monitor course conditions  

### **What Course Workers Do *Not* Do**
- They do **not** interact with the timing system directly  
- They do **not** communicate reruns  
- They do **not** perform staging or grid duties  

---

## 3.5 Event Administrators

### **Purpose**
Administrators configure the event and oversee system operation.

### **Responsibilities**
- Configure classes, run groups, and event structure  
- Manage worker tokens  
- Oversee timing hardware deployment  
- Monitor system health  
- Publish results (locally or to the cloud)  

---

## 3.6 Competitors

### **Purpose**
Competitors participate in the event and may optionally interact with the system.

### **Responsibilities**
- Ensure their car number and class letters are correct  
- Follow grid and staging instructions  
- Review their results  
- Complete assigned worker duties  

### **Optional Interactions**
Competitors with accounts may:
- Receive digital worker assignments  
- View personalized results  
- Update profile information  

---

### 4. System Interaction Summary

| Role                 | Grid UI | Starter UI | Timing Console | Course UI | Admin UI |
|----------------------|---------|------------|----------------|-----------|----------|
| Grid Worker          | ✔       |            |                |           |          |
| Starter              |         | ✔          |                |           |          |
| Timing Staff         |         |            | ✔              |           | ✔        |
| Course Worker        |         |            |                | ✔         |          |
| Event Administrator  |         |            | ✔              |           | ✔        |
| Competitor           | Optional|            |                |           | Optional |

---

### 5. Summary
Race Wrangler’s role model reflects real-world event operations. Grid workers manage flow and communicate reruns, the starter performs final checks before each run, and timing staff maintain event integrity. The system supports volunteers with simple, role-specific interfaces and avoids assumptions about run order or rigid sequencing.
