# EventConfiguration Entity Specification

## 1. Purpose
An **EventConfiguration** defines all event‑level settings that control how timing, validation, penalties, classes, and operational workflows behave. It acts as the ruleset and configuration brain for an Event.

EventConfiguration ensures:
- consistent behavior across the timing pipeline  
- reproducible validation logic  
- clear separation between event rules and event data  
- versioned, immutable settings once the event becomes active  

---

## 2. Definition
An EventConfiguration is a structured, versioned set of parameters that govern:

- timing rules  
- penalty rules  
- PAX/indexing rules  
- sector/split behavior  
- camera and OCR settings  
- run group behavior  
- worker/role requirements  
- UI and operational preferences  

Each Event references exactly one EventConfiguration.  
Configurations may be reused across events or cloned for new events.

---

## 3. Attributes

### Core Fields
- **id** — Unique identifier for the configuration  
- **name** — Human‑readable name (e.g., “2025 SCCA Solo Ruleset”)  
- **version** — Version identifier for the ruleset  
- **created_at** — Timestamp when the configuration was created  
- **updated_at** — Timestamp when the configuration was last modified  

### Timing & Validation Settings
- **require_start_event** — Whether a run must have a start event  
- **require_finish_event** — Whether a run must have a finish event  
- **allow_multiple_splits** — Whether sector timing is enabled  
- **max_split_count** — Maximum number of supported splits  
- **allow_early_start_detection** — Whether early starts trigger penalties  
- **allow_late_finish_detection** — Whether late finishes trigger penalties  
- **validation_tolerance_ms** — Allowed timestamp tolerance for event ordering  

### Penalty Settings
- **penalty_definitions** — JSON structure defining penalty codes, descriptions, and time adjustments  
- **auto_penalty_rules** — Rules for automatically applying penalties (e.g., missing split, jump start)  
- **allow_manual_penalties** — Whether officials may add penalties manually  

### PAX / Indexing Settings
- **enable_pax** — Whether PAX/indexing is used  
- **pax_table** — Mapping of CarClass → PAX factor  
- **pax_version** — Version of the PAX table used  

### Camera & OCR Settings
- **ocr_enabled** — Whether OCR is active  
- **ocr_confidence_threshold** — Minimum confidence for valid OCR detections  
- **camera_heartbeat_timeout_ms** — Time before a camera is considered offline  
- **allow_redundant_cameras** — Whether multiple cameras may serve the same role/position  
- **frame_rate_limit** — Maximum frames per second to ingest per camera  

### Run Group & Operational Settings
- **max_runs_per_competitor** — Maximum allowed runs  
- **allow_reruns** — Whether reruns are permitted  
- **rerun_rules** — JSON structure defining rerun conditions  
- **grid_behavior** — Settings for staging/grid logic (if used)  
- **auto_assign_run_groups** — Whether competitors are auto‑assigned to run groups  

### UI & Worker Settings
- **worker_roles** — List of worker roles required for the event  
- **ui_theme** — Optional UI theme or branding  
- **show_live_results** — Whether live results are displayed during the event  
- **allow_worker_device_login** — Whether workers may authenticate via DeviceSession  

---

## 4. Relationships

### Parent
None — EventConfiguration is standalone and reusable.

### Children
None — EventConfiguration does not own other entities.

### Referenced By
- **Event** — Each Event references exactly one EventConfiguration  
- **ValidationResult** — Uses configuration rules to interpret TimingEvents  
- **Penalty** — Uses penalty definitions and auto‑penalty rules  
- **Finalization** — Uses PAX and penalty rules to compute final times  
- **CameraSession** — Uses camera/OCR settings for operational behavior  

---

## 5. Operational Behavior

### Configuration Lifecycle
```
draft → active → locked
```

### Draft
- Configuration may be edited freely  
- New rules, penalties, PAX tables, and settings may be added  

### Active
- Configuration is assigned to an Event  
- Minor edits may be allowed (optional)  

### Locked
- Event has started  
- Configuration becomes immutable  
- All timing and validation must use the locked configuration  

### Versioning
- Configurations should be versioned to support:
  - rule changes between seasons  
  - different event formats  
  - experimental configurations  
  - reproducibility for historical events  

---

## 6. Constraints & Invariants

- An Event must reference exactly one EventConfiguration  
- A configuration cannot be modified once the Event is active  
- PAX tables must be complete if PAX is enabled  
- Penalty definitions must include standardized codes  
- Validation rules must be deterministic  
- OCR settings must be compatible with camera ingestion rates  

---

## 7. Notes & Implementation Guidance

- EventConfiguration should be stored as structured JSON for flexibility  
- Penalty definitions and rerun rules should be machine‑interpretable  
- PAX tables should be versioned and externally referenceable  
- Camera/OCR settings should be tuned per event type  
- Worker roles should be customizable per event  
- UI settings allow event‑specific branding or behavior  
- Cloning configurations is recommended for new events  

