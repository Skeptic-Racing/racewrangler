# Competitor Entity Specification

## 1. Purpose
A **Competitor** represents a *driver–car entry* in a specific Event. It is the event‑scoped relationship between:

- a **Driver** (persistent identity across events)  
- a **Car** (persistent or event‑scoped vehicle record)  
- a **CarClass** (competition class for this event)  
- a **RunGroup** (optional scheduling group)  

Competitor ensures:
- drivers can participate in multiple events  
- drivers can switch cars between events  
- cars can be shared or reused  
- event‑specific attributes (number, class, run group) remain isolated  
- timing and results remain cleanly event‑scoped  

---

## 2. Definition
A Competitor is an event‑scoped entry that binds a Driver and a Car to a specific class, number, and run group for the duration of an Event.

A single Driver may have multiple Competitor records in an event (e.g., driving two different cars or running two classes).  
A single Car may be associated with multiple Competitors (e.g., co‑drivers).

Competitors own Runs and appear in results.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the competitor entry  
- **event_id** — Reference to the Event  
- **driver_id** — Reference to the Driver (persistent identity)  
- **car_id** — Reference to the Car (persistent or event‑scoped)  
- **car_class_id** — Reference to the CarClass  
- **run_group_id** — Reference to the RunGroup (nullable)  
- **number** — Car number (unique within class)  

### Driver Convenience Fields
(Cached for performance; source of truth is Driver)
- **driver_first_name**  
- **driver_last_name**  
- **driver_full_name**  

### Car Convenience Fields
(Cached for performance; source of truth is Car)
- **car_make**  
- **car_model**  
- **car_year**  
- **car_color**  
- **car_description**  

### Operational Fields
- **is_worker** — Whether the competitor also serves as a worker  
- **worker_assignment_id** — Optional reference to WorkerAssignment  
- **is_novice** — Whether the competitor is considered a novice  
- **is_dual_driver** — Whether the car is shared with another competitor  

### Metadata
- **notes** — Freeform notes for organizers  
- **created_at** — Timestamp when the competitor was created  
- **updated_at** — Timestamp when the competitor was last modified  

---

## 4. Relationships

### Parent
- **Event** — Competitors belong to an event  

### Required References
- **Driver** — Persistent identity of the person  
- **Car** — Vehicle being driven  
- **CarClass** — Competition class  
- **RunGroup** — Optional scheduling group  

### Children
- **Run** — Competitors own runs  
- **WorkerAssignment** — If the competitor is also a worker  

### Referenced By
- **Timing UI** — For number lookup and run assignment  
- **Results computation** — For class and PAX grouping  
- **DeviceSession** — If the competitor logs in as a worker  

---

## 5. Operational Behavior

### Driver Assignment
- A Competitor must reference exactly one Driver  
- Drivers may appear in multiple events  
- Drivers may have multiple Competitor entries in the same event (multi‑car or multi‑class)  

### Car Assignment
- A Competitor must reference exactly one Car  
- Cars may be shared by multiple Competitors (co‑drivers)  
- Car details are cached for performance but sourced from Car  

### Number Assignment
- Numbers must be unique within a CarClass  
- Dual‑driver conventions (e.g., “42” and “142”) are allowed but not enforced automatically  
- Number uniqueness is enforced at the event level  

### Class Assignment
- Competitors must belong to exactly one CarClass  
- Class changes allowed only while the event is in `draft`  
- After activation, class changes require explicit override  

### Run Group Assignment
- May be assigned manually or automatically  
- Should not change once runs begin  

### Worker Behavior
- Competitors may serve as workers  
- WorkerAssignment links competitor → role → device session  
- Worker status does not affect timing or results  

---

## 6. Constraints & Invariants

- A Competitor must belong to exactly one Event  
- A Competitor must reference exactly one Driver and one Car  
- Car numbers must be unique within a class  
- Competitors cannot be deleted once runs reference them  
- Competitor data becomes locked once the event becomes active  
- WorkerAssignment must reference a valid Competitor  
- Competitors must not change run groups after runs begin  

---

## 7. Notes & Implementation Guidance

- Competitor is the event‑scoped “entry” object; Driver and Car are persistent  
- Cached driver/car fields improve UI performance and reduce joins  
- Competitor should be cloneable from previous events  
- Competitor should not contain timing or run‑specific data  
- Competitor should be optimized for:
  - fast lookup by number  
  - grouping by class  
  - sorting by name or number  
  - linking to runs and results  

