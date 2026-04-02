# CarClass Entity Specification

## 1. Purpose
A **CarClass** represents a competition class within an Event. Classes group competitors for scoring, awards, PAX/indexing, and results. CarClass definitions are event‑scoped and may reference PAX factors or other rule‑based attributes defined in the EventConfiguration.

CarClass ensures:
- consistent grouping of competitors  
- clear class‑level results  
- compatibility with PAX/indexing systems  
- flexibility for different event formats (SCCA, NASA, custom)  

---

## 2. Definition
A CarClass defines a named competition category within an Event. Each competitor belongs to exactly one CarClass. Classes may have:

- a display name  
- a short code (e.g., “STX”, “CAM‑C”)  
- a PAX/index factor (if applicable)  
- optional metadata for trophies, run order, or grouping  

CarClasses are event‑scoped and may be cloned or reused across events.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the class  
- **event_id** — Reference to the Event  
- **code** — Short class code (e.g., “SS”, “STX”, “CAM‑T”)  
- **name** — Human‑readable class name  
- **description** — Optional longer description  

### Scoring & Indexing Fields
- **pax_factor** — Numeric factor applied to adjusted times (nullable; may be sourced from EventConfiguration)  
- **trophy_count** — Optional number of trophies allocated to this class  
- **is_novice_class** — Whether this class is for novice competitors  

### Operational Fields
- **run_group_id** — Optional reference to a RunGroup (if classes are grouped by run group)  
- **sort_order** — Optional integer for ordering classes in UI or results  

### Metadata
- **notes** — Freeform notes for organizers  
- **created_at** — Timestamp when the class was created  
- **updated_at** — Timestamp when the class was last modified  

---

## 4. Relationships

### Parent
- **Event** — CarClasses belong to an event  

### Children
None — CarClass does not own other entities.

### Referenced By
- **Competitor** — Each competitor belongs to exactly one CarClass  
- **EventConfiguration** — May define PAX factors for classes  
- **Results computation** — Uses CarClass to group and rank competitors  

---

## 5. Operational Behavior

### Class Assignment
- Competitors must be assigned to exactly one CarClass  
- CarClass may optionally determine:
  - run group assignment  
  - PAX factor  
  - trophy allocation  

### PAX / Indexing Behavior
If PAX is enabled:
- `pax_factor` may be stored directly on CarClass  
- or may be resolved from EventConfiguration’s PAX table  
- Finalization uses the resolved factor to compute `pax_time`  

### Class Ordering
- `sort_order` controls display order in:
  - grids  
  - timing UI  
  - results pages  

### Class Mutability
- CarClasses may be edited while the Event is in `draft`  
- CarClasses become locked when the Event becomes `active`  
- Competitors may not change classes after runs begin (unless explicitly overridden)  

---

## 6. Constraints & Invariants

- A CarClass must belong to exactly one Event  
- Class codes must be unique within an Event  
- PAX factor must be non‑negative if present  
- Competitors must reference a valid CarClass  
- CarClasses cannot be deleted once competitors or runs reference them  
- Class definitions must be locked once the Event becomes active  

---

## 7. Notes & Implementation Guidance

- CarClass should be lightweight and event‑scoped  
- PAX factors should be versioned via EventConfiguration  
- Classes may be cloned from previous events for convenience  
- Support for novice classes, ladies classes, or indexed classes should be flexible  
- CarClass should not contain competitor‑specific data  
- CarClass should not contain run‑specific data  
- CarClass should be optimized for:
  - fast lookup  
  - grouping  
  - sorting  
  - results computation  

