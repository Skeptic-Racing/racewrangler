# Ambiguity Resolution UX Specification
## RaceWrangler — Timing & Scoring Worker Workflow
## Version: April 2026

This document defines the UI and behavior for resolving timing events that OCR could not
automatically match to a competitor. It covers who sees the prompts, the screen layout,
available actions, and edge cases.

---

## 1. Purpose

Some timing events cannot be automatically matched to a competitor — OCR confidence is
too low, multiple candidates tie, or OCR fails entirely. These events land in the
**ambiguity queue**. A human timing worker reviews them and makes the final call.

---

## 2. Who Reviews Ambiguities

The **Timing & Scoring worker** resolves all ambiguities. This is a single authoritative
device (typically a tablet at the timing table), not a shared workload across multiple
workers.

Rationale: Ambiguity resolution creates `Run` records and assigns competitors. Conflicting
concurrent edits from multiple workers would produce duplicate runs. One reviewer, one device.

---

## 3. Where It Appears

A notification badge appears on the Timing & Scoring UI whenever the ambiguity queue is
non-empty. The worker taps the badge to open the resolution screen.

The resolution screen can be opened at any time during the event — it does not interrupt
the main timing display.

---

## 4. Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Ambiguity Resolution              2 pending                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Photo of car crossing timing line]                         │
│                                                              │
│  Finish line  •  12:34:07.421  •  Run Group 2               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Candidates (OCR suggestions, ranked by confidence):         │
│                                                              │
│  ○  #124  STR   Jane Smith         (confidence: 0.72)        │
│  ○  #12   STX   Bob Johnson        (confidence: 0.41)        │
│  ○  #1    SM    Alice Chen         (confidence: 0.28)        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  [Enter number manually: _______ ]                           │
│                                                              │
│  [ Select ]  [ Skip / Defer ]  [ Mark Unknown ]             │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 Photo Display

- Full image from the RaceSpy camera, scaled to fit the screen
- Tap to zoom in
- No image enhancement applied by default (may add brightness/contrast slider in Phase 2)

### 4.2 Event Metadata

Displayed above the candidate list:
- Which timing point (start or finish)
- UTC timestamp formatted as local time (`HH:MM:SS.mmm`)
- Active run group at the time of the trigger

### 4.3 Candidate List

- OCR candidates ranked by `confidence_number` (highest first)
- Each row: car number, class, driver name, confidence score
- Up to 5 candidates displayed; "Show more" expands if OCR returned additional candidates
- Tap a row to select it (radio button behavior)
- If `match_status == "tentative"`, the top candidate is pre-selected with a "Confirm?" label

### 4.4 Manual Entry

If the correct car is not in the candidate list, the worker types the car number manually.
The system looks up the competitor by number+class in the run group, then auto-selects if
unambiguous. If the number is ambiguous (multiple competitors with same number), a secondary
class prompt appears.

---

## 5. Actions

### 5.1 Select (Resolve)

Worker picks a candidate (or enters manually) and taps "Select":
- Creates a `Run` record with the chosen `competitor_id`
- Records `resolved_by = "human"` and `resolved_at = now()`
- Stores the original OCR output alongside the correction (for future tuning)
- Removes the event from the ambiguity queue
- Shows next pending event, or returns to main timing screen if queue is empty

### 5.2 Skip / Defer

Worker is unsure and wants to come back later:
- Event stays in the ambiguity queue
- Moves to the bottom of the queue (shows other pending events first)
- A deferred event that has been skipped 3 times shows a "⚠ Deferred 3 times" badge

### 5.3 Mark Unknown

The car cannot be identified from the photo (obscured plate, camera misfire, test trigger):
- Event is marked `unidentified`
- Removed from the ambiguity queue
- Run is not created
- Appears in the post-event "Unidentified events" summary for manual reconciliation

---

## 6. Timeout Behavior

There is no automatic timeout that resolves an ambiguity without human input. An unresolved
event stays in `needs_review` state indefinitely.

If an event is still unresolved at the end of the event session, it appears in the post-event
summary under "Unresolved timing events." The admin can resolve or discard these during
post-event review.

---

## 7. Edge Cases

### 7.1 No Candidates Returned

OCR ran but could not extract a number at all. The candidate list is empty.
- Display: "OCR could not read a number from this photo."
- Worker must enter the car number manually or mark as unknown.

### 7.2 OCR Total Failure

The OCR engine threw an exception or timed out. No candidates, no confidence scores.
- Display: "OCR failed for this event. Please identify the car manually."
- Worker experience is the same as 7.1.

### 7.3 Start Event Without a Matching Finish (or Vice Versa)

A start event arrives but no finish event has been paired with it yet (or vice versa).
The timing event is still shown in the ambiguity queue if its individual OCR match failed.
Run pairing (start + finish → elapsed time) is handled by the timing engine after both
events are resolved.

### 7.4 Duplicate Trigger

Same car triggers the beam twice (e.g., spun out and rolled back). Two events arrive
within the 2-second debounce window on the RaceSpy (should be suppressed on the Pi Zero
side). If both make it to the server anyway, the second event's sequence number is
consecutive — the timing worker sees both in the queue and can mark one as "unknown"
(mis-trigger).

---

## 8. Backend Endpoints Required

```
GET  /api/v1/events/{event_id}/ambiguity-queue
     Response: list of pending TimingEvents with OCR candidates

POST /api/v1/events/{event_id}/ambiguity-queue/{timing_event_id}/resolve
     Body: {"competitor_id": "<uuid>", "action": "select" | "skip" | "unknown"}

GET  /api/v1/events/{event_id}/ambiguity-queue/count
     Response: {"pending": 2}  (used for notification badge)
```

---

## 9. Notification Model

The Timing & Scoring UI polls `GET /ambiguity-queue/count` every 5 seconds. When the count
goes above 0, a red badge appears on the queue icon. The worker is not interrupted mid-flow
(no modal or audio alert) — they check the queue between runs.

Phase 2 option: WebSocket push notification so the badge updates without polling. Not
needed for the 2-weekend test.
