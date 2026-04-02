# Car Entity Specification

## 1. Purpose
A **Car** represents a vehicle that may be used by one or more Drivers across one or more Events. Cars may be persistent (recommended) or event‑scoped depending on the organizer’s workflow.

Car ensures:
- clean support for multi‑driver cars  
- support for drivers switching cars between events  
- persistent vehicle history and analytics  
- separation between vehicle identity and event‑specific competitor data  
- compatibility with classing, PAX, and results  

---

## 2. Definition
A Car is a persistent (or optionally event‑scoped) record describing a vehicle. Cars may:

- be shared by multiple competitors in the same event  
- be used by different drivers across different events  
- appear in multiple classes depending on configuration  
- have multiple Competitor entries referencing them  
- store descriptive metadata for UI and results  

Cars do **not** contain event‑specific attributes like number or class — those belong to Competitor.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the car  
- **owner_driver_id** — Optional reference to the Driver who owns the car  
- **nickname** — Optional short name (e.g., “The Miata”, “Blue Subie”)  

### Vehicle Identity Fields
- **make** — Manufacturer (e.g., “Mazda”)  
- **model** — Model (e.g., “Miata”)  
- **year** — Model year (optional)  
- **color** — Primary color (optional)  
- **trim** — Trim level or variant (optional)  
- **vin** — Vehicle Identification Number (optional; not required)  

### Technical / Classification Fields
(Useful for future expansion or rule‑based classing)
- **engine** — Engine description (optional)  
- **drivetrain** — FWD / RWD / AWD (optional)  
- **modifications** — Freeform or structured description of mods  
- **class_hint** — Optional suggested class (e.g., “STX”)  

### Metadata
- **notes** — Freeform notes for organizers  
- **created_at** — Timestamp when the car record was created  
- **updated_at** — Timestamp when the car record was last modified  

---

## 4. Relationships

### Parent
None — Car is a top‑level persistent entity.

### Children
None directly.

### Referenced By
- **Competitor** — Event‑scoped entry linking Driver → Car → Class → Number  
- **Driver** — If the driver is the owner or primary driver  
- **Results computation** — For car‑specific analytics or filtering  

### Indirect Relationships
Through Competitor:
- **Run**  
- **Penalty**  
- **ValidationResult**  
- **Finalization**  

---

## 5. Operational Behavior

### Car Lifecycle
Cars persist across events and seasons.  
They may be:

- created during registration  
- reused for future events  
- shared between drivers  
- updated with new details  
- marked inactive if no longer used  

### Event Participation
A Car participates in an Event through one or more **Competitor** records.

Examples:
- One car, two drivers → two Competitor records  
- One driver, two cars → two Competitor records  
- One car, two classes → two Competitor records  

### Ownership
- `owner_driver_id` is optional  
- A car may have no owner (e.g., rental, loaner, team car)  
- Ownership does not affect event behavior  

### Technical Data
Technical fields are optional but useful for:
- classing assistance  
- tech inspection  
- future automated classing logic  
- analytics  

---

## 6. Constraints & Invariants

- Car records must not contain event‑specific data  
- Cars must not be deleted if referenced by any Competitor  
- VIN is optional and must not be treated as a unique identifier  
- Car identity must remain stable across events  
- Cars may be shared by multiple drivers  

---

## 7. Notes & Implementation Guidance

- Car is the persistent vehicle identity; Competitor is the event‑scoped entry  
- Cached car fields on Competitor improve UI performance  
- Car should be optimized for:
  - fast lookup by make/model/year  
  - linking to competitors  
  - multi‑driver workflows  
  - historical analytics  
- Car should not contain classing or number information  
- Cars may be imported/exported across seasons  

