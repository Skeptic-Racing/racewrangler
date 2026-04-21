# Run Group Assignment UX Specification
## RaceWrangler — Admin Workflow
## Version: April 2026

This document defines the UI and backend behavior for assigning competitors to run groups
before an event. It covers the default bulk-by-class workflow and the per-driver override.

---

## 1. Context and Purpose

After a competitor list is imported, every competitor starts **unassigned** — no run group.
The event admin must assign competitors to run groups before the event can go active.

The common pattern at an autocross:
1. Assign each car class to a run group (bulk operation)
2. Move individual drivers who need to run in a different group (override)

---

## 2. Run Group Management

Before assigning competitors, the admin defines the run groups for the event.

### 2.1 Create Run Groups

- Admin names each group (e.g., "Group 1", "Group 2", "Workers/Fun")
- Groups are ordered; order determines the run sequence displayed on other screens
- Minimum 1 group required; no hard maximum

### 2.2 Edit and Delete

- Groups can be renamed at any time before the event goes active
- A group can be deleted only if it has no assigned competitors (or if all competitors in it
  are moved first)
- After the event goes active, groups are read-only (no rename, no delete)

---

## 3. Bulk Assignment by Class

### 3.1 Layout

The assignment screen shows a table with one row per car class currently in the entry list:

| Class | Count | Assign to Run Group |
|-------|-------|---------------------|
| STR | 12 | [Group 1 ▼] |
| STX | 8 | [Group 1 ▼] |
| SM | 5 | [Group 2 ▼] |
| SSM | 3 | [Group 2 ▼] |
| ... | ... | ... |

- Each row shows: class code, competitor count, and a dropdown to select a run group
- Default dropdown value: "— Unassigned —"
- An "Assign All" button at the top applies the current dropdown selections to all competitors
  in each class

### 3.2 Applying the Assignment

When the admin clicks "Assign All" (or "Apply"):
- For each class with a run group selected, bulk-update all competitors in that class to that group
- Classes left at "— Unassigned —" are unchanged
- Success: show a summary ("48 competitors assigned to run groups")
- Partial failure: show which classes failed, leave others applied

### 3.3 Validation Warning

If a class is split across multiple groups (can happen via per-driver overrides after bulk assign),
a warning banner appears on the assignment screen:

> ⚠ Class STR is split across Group 1 (10 drivers) and Group 2 (2 drivers). This is unusual —
> confirm this is intentional.

This is a warning, not a hard block. Split classes are allowed (e.g., a driver who needs to run
with their spouse's group).

---

## 4. Per-Driver Override

### 4.1 Access

After bulk assignment, the admin can view competitors as a list grouped by run group. A
competitor card shows: name, car number, class, current run group.

### 4.2 Moving a Driver

- Drag-and-drop a competitor card to a different run group column
- Or: open the competitor's detail and use a dropdown to change their run group

### 4.3 Use Case

Typical override: a driver who is also a course worker needs to run in Group 2 (workers' group)
even though their class is normally in Group 1.

---

## 5. Locking and the Active Event

- Assignments are freely editable while the event is in `setup` state
- Once the admin transitions the event to `active` state, assignments are locked
- After lock, moving a driver requires an explicit confirmation dialog:
  > "This event is active. Moving [driver name] from Group 1 to Group 2 may affect the
  > current run order. Continue?"
- The move is recorded with a timestamp and a note in the audit log

---

## 6. Display on Other Screens

Run group assignments affect:
- **Starter UI:** shows next driver in queue for the active run group
- **Timing & Scoring UI:** filters OCR candidates to only competitors in the active run group
- **Grid UI:** shows which competitors are staged for the next run

---

## 7. Backend Endpoints Required

### 7.1 Run Group CRUD
```
POST   /api/v1/events/{event_id}/run-groups
GET    /api/v1/events/{event_id}/run-groups
PATCH  /api/v1/events/{event_id}/run-groups/{group_id}
DELETE /api/v1/events/{event_id}/run-groups/{group_id}
```

### 7.2 Bulk Assignment
```
POST /api/v1/events/{event_id}/run-groups/bulk-assign
Body: [{"class_code": "STR", "run_group_id": "<uuid>"}, ...]
```

### 7.3 Per-Competitor Assignment
```
PATCH /api/v1/events/{event_id}/competitors/{competitor_id}
Body: {"run_group_id": "<uuid>"}
```

### 7.4 Assignment Summary (for the assignment UI table)
```
GET /api/v1/events/{event_id}/run-groups/assignment-summary
Response: [{
  "class_code": "STR",
  "competitor_count": 12,
  "assigned_group_id": "<uuid or null>",
  "split": false
}, ...]
```
