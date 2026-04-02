# RunGroup Entity Specification

## 1. Purpose
A **RunGroup** represents a scheduling group within an Event. Run groups determine:

- when competitors run  
- when competitors work  
- how the event is structured operationally  
- which classes run together  
- which competitors appear in the timing UI at a given time  

RunGroup ensures:
- predictable event flow  
- worker/run rotation  
- compatibility with staging and grid workflows  
- flexible grouping for different event formats  

---

## 2. Definition
A RunGroup is an event‑scoped grouping of competitors who run together during a specific portion of the event. Run groups may:

- contain multiple CarClasses  
- contain competitors from multiple classes  
- define worker rotations  
- be assigned manually or automatically  
- be used for staging awareness (optional)  

RunGroup does **not** contain run‑specific data — that belongs to Run.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the run group  
- **event_id** — Reference to the Event  
- **name** — Human‑readable name (e.g., “Group A”, “Heat 1”, “Morning”)  
- **code** — Short code (e.g., “A”, “1”, “PM”)  
- **sort_order** — Integer for ordering run groups in UI and schedules  

### Operational Fields
- **worker_group_id** — Optional reference to another RunGroup that works while this group runs  
- **is_default** — Whether this is the default run group for new competitors  
- **max_competitors** — Optional limit for group size  
- **color** — Optional UI color tag for easy identification  

### Metadata
- **notes** — Freeform notes for organizers  
- **created_at** — Timestamp when the run group was created  
- **updated_at** — Timestamp when the run group was last modified  

---

## 4. Relationships

### Parent
- **Event** — Run groups belong to an event  

### Children
None directly.

### Referenced By
- **Competitor** — Each competitor may belong to a run group  
- **CarClass** — Classes may optionally map to run groups  
- **WorkerAssignment** — Worker roles may be tied to run groups  
- **Timing UI** — Uses run groups to filter active competitors  

### Indirect Relationships
Through Competitor:
- **Run**  
- **ValidationResult**  
- **Finalization**  

---

## 5. Operational Behavior

### Run/Work Rotation
Run groups often define a rotation such as:

```
Group A runs → Group B works  
Group B runs → Group C works  
Group C runs → Group A works  
```

This is optional and event‑dependent.

### Assignment Behavior
- Competitors may be assigned manually or automatically  
- RunGroup may be derived from CarClass if configured  
- RunGroup should not change once runs begin  
- Default run group may be used during registration  

### Staging & Grid Behavior
If staging awareness is enabled:
- RunGroup determines which competitors appear in the staging UI  
- Grid workers may filter by run group  
- Starters may see “expected next” competitors by group  

### UI Behavior
- Run groups appear in:
  - registration UI  
  - timing UI  
  - worker UI  
  - results UI  
- `sort_order` controls display order  

---

## 6. Constraints & Invariants

- A RunGroup must belong to exactly one Event  
- RunGroup codes must be unique within an Event  
- Competitors must reference a valid RunGroup (unless unassigned)  
- RunGroup cannot be deleted once competitors reference it  
- RunGroup becomes locked once the Event becomes active  
- Worker rotations must reference valid RunGroups  

---

## 7. Notes & Implementation Guidance

- RunGroup should be lightweight and event‑scoped  
- Worker rotations should be optional and flexible  
- RunGroup should not contain competitor or class data directly  
- RunGroup should be optimized for:
  - fast lookup  
  - grouping competitors  
  - filtering in timing UI  
  - scheduling logic  
- RunGroup definitions should be cloneable from previous events  

