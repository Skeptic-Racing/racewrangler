# Requirements Added During POC Implementation (Not in Main Documentation Baseline)

## Scope of Comparison
This compares implemented requirements against the main documentation baseline under `docs/` (notably Product Vision, System Overview, and the POC docs in `docs/poc/`).

Main baseline docs describe high-level concepts, but the items below were added during implementation as concrete, new POC requirements and behaviors.

## Added/Changed Requirements

### 1. Advanced car selection UX in Starter
- Search by car number and model
- Dropdown behavior changed to a true filterable select with click-open and list UI
- Layering/z-index behavior fixed to keep selector over camera view

### 2. Device camera behavior customization
- Prefer rear camera on mobile devices (`environment` facing mode)
- Added practical fallback behavior when facing mode is unavailable

### 3. Navigation workflow changes
- Removed automatic tab switching after start/finish confirmations

### 4. Multi-device network and HTTPS support for demo usage
- Host/proxy behavior adjusted for phone access on LAN
- HTTPS support added for camera usage on mobile browsers
- Local cert/key environment-variable flow added for Vite dev server

### 5. Timing UI structure changes
- Added Active Runs / Completed Runs tab model in Timing UI
- Added Run # column
- Removed All Runs tab after user feedback

### 6. Run lifecycle controls beyond baseline
- Replaced prior abort button usage with explicit run deletion action
- Added Re-Run action and Re-Run status behavior in Timing UI

### 7. Missed Trip operational workflow
- Added per-run Missed Trip flagging from Finish Worker
- Keep missed-trip runs in Active Runs, visually highlighted
- Move run to Completed when Timing marks DNF or Re-Run

### 8. Global Hold Start control plane
- Added global Hold Start / Release Start controls in Timing UI
- Hold state made independent from DNF/Re-Run actions
- Hold banner shown in Starter and Timing using shared backend state

### 9. Admin capabilities added to POC
- Added Admin UI (explicitly out-of-scope in original POC scope doc)
- Added Reset Data operation that clears runs, photos, and sequencing context
- Moved finish-trigger control into Admin UI

### 10. Shared finish-trigger event across devices
- Finish trigger changed from local UI state to backend-shared event
- Trigger status polling added so Finish Worker on another device sees the event

### 11. Trigger-anchored finish timing semantics
- Finish Worker expected elapsed time now uses delta to trigger timestamp (not live now)
- Confirm Finish records trigger timestamp as finish time when available

### 12. Cross-device time consistency requirement
- Frontend time parsing/formatting normalized to UTC display so all connected devices show consistent values

## Why These Count as On-the-Fly Additions
- Many of these are absent from `docs/poc/scope.md` and `docs/poc/ui-component-overview.md`.
- Several directly contradict original POC non-goals (for example, Admin UI).
- Several are implementation-level operational requirements (global hold state, shared trigger state, trigger-time finish semantics) not specified in the baseline API spec.

## Recommended Documentation Follow-Up
To keep documentation aligned with reality, update these baseline docs next:
- `docs/poc/scope.md`
- `docs/poc/ui-component-overview.md`
- `docs/poc/minimal-api-spec.md`
- `docs/System Overview.md` (if you want to keep some of these behaviors beyond POC)
