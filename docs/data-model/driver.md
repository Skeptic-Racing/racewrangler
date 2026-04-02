# Driver Entity Specification

## 1. Purpose
A **Driver** represents a persistent person who may participate in many Events over time. Drivers own no runs directly; instead, they participate in events through **Competitor** records, which bind a Driver to a Car, CarClass, number, and run group for a specific Event.

Driver ensures:
- persistent identity across events  
- long‑term history and analytics  
- support for multi‑car and multi‑class participation  
- clean separation between personal identity and event‑specific data  
- compatibility with worker roles and device sessions  

---

## 2. Definition
A Driver is a long‑lived, cross‑event entity representing a real person. Drivers may:

- compete in multiple events  
- drive different cars in different events  
- co‑drive a car with others  
- run multiple classes in the same event  
- serve as workers  
- accumulate historical results  

Drivers do **not** contain event‑specific data — that belongs in Competitor.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the driver  
- **first_name** — Driver’s first name  
- **last_name** — Driver’s last name  
- **full_name** — Cached full name for convenience  

### Contact & Identity Fields
(These are optional and may be shared between multiple drivers)
- **email** — Contact email (optional; not required to be unique)  
- **phone** — Contact phone number (optional; not required to be unique)  
- **membership_id** — Club or organization membership number (optional)  
- **license_id** — Competition license number (optional)  

### Profile Fields
- **is_active** — Whether the driver is currently active  
- **preferred_number** — Optional preferred car number  
- **preferred_class** — Optional preferred class code  
- **preferred_car_id** — Optional reference to a Car the driver commonly uses  

### Worker Fields
- **is_worker_eligible** — Whether the driver may serve as a worker  
- **default_worker_role** — Optional default worker role  

### Metadata
- **notes** — Freeform notes for organizers  
- **created_at** — Timestamp when the driver profile was created  
- **updated_at** — Timestamp when the driver profile was last modified  

---

## 4. Relationships

### Parent
None — Driver is a top‑level persistent entity.

### Children
None directly.

### Referenced By
- **Competitor** — Event‑scoped entry linking Driver → Car → Class → Number  
- **WorkerAssignment** — If the driver serves as a worker  
- **DeviceSession** — If the driver logs in as a worker  
- **Car** — If the driver is the owner or primary driver (optional)  

### Indirect Relationships
Through Competitor:
- **Run**  
- **Penalty**  
- **ValidationResult**  
- **Finalization**  
- **Results**  

---

## 5. Operational Behavior

### Driver Lifecycle
Drivers persist across events and seasons.  
They may be:

- created during registration  
- reused for future events  
- updated with new contact info  
- marked inactive if no longer participating  

### Event Participation
A Driver participates in an Event by having one or more **Competitor** records.

Examples:
- Same driver, two cars → two Competitor records  
- Same driver, two classes → two Competitor records  
- Two drivers, one car → two Competitor records  

### Worker Behavior
Drivers may also serve as workers.  
WorkerAssignment links:

```
Driver → Competitor → WorkerAssignment → DeviceSession
```

### Preferred Settings
Preferred number/class/car are convenience fields that help pre‑populate future event registrations.

---

## 6. Constraints & Invariants

- Driver names should be normalized for consistent lookup  
- Drivers must not be deleted if referenced by any Competitor  
- Drivers must not contain event‑specific data  
- Driver identity must remain stable across events
- Email and phone are optional and may be shared; they must NOT be treated as unique identifiers  

---

## 7. Notes & Implementation Guidance

- Driver is the persistent identity; Competitor is the event‑scoped entry  
- Cached fields (full_name) improve performance and reduce joins  
- Driver should be optimized for:
  - fast lookup by name  
  - linking to historical results  
  - registration workflows  
  - worker assignment workflows  
- Driver should not contain car‑specific or event‑specific data  
- Drivers may be imported/exported across seasons  

