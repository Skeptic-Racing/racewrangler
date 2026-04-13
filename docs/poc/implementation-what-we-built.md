# RaceWrangler POC: What Was Actually Implemented

## Purpose
This document summarizes the implemented state of the POC as of April 2026, based on the running codebase.

## Delivered Architecture
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React + TypeScript + Vite
- Storage: local file storage for start and finish photos
- Deployment modes: local dev and Docker-oriented structure
- Multi-device operation: role UIs can run on different devices on the same network

## Implemented UIs

### Starter UI
- Searchable car selector (car number and model filtering)
- Camera capture and photo preview
- Confirm Start creates run with photo
- Hold-start warning banner that reflects shared backend hold state

### Finish Worker UI
- Active-run photo grid with manual selection
- Auto-select oldest active run on finish trigger
- Confirm Finish workflow
- Missed Trip button per run
- Expected elapsed time shown for oldest active run at trigger time
- Trigger window is shared across devices via backend status polling

### Timing & Scoring UI
- Two run tabs: Active Runs and Completed Runs
- Run # column
- Status badges (Active, Completed, DNF, Re-Run, Missed Trip)
- Penalty actions (+1, +2, clear)
- DNF toggle
- Re-Run toggle
- Delete run action
- Global Hold Start / Release Start control
- Hold banner messaging with missed-trip context

### Admin UI
- Shared Finish Trigger control
- Reset Data action with confirmation

## Implemented Backend/API Surface
In addition to baseline endpoints, the backend currently supports:
- `POST /api/runs/hold-start`
- `POST /api/runs/release-start`
- `GET /api/runs/hold-status`
- `POST /api/runs/trigger-finish`
- `GET /api/runs/finish-trigger-status`
- `DELETE /api/runs/{run_id}`
- `POST /api/admin/reset`

Baseline endpoints remain in place:
- `GET /api/cars`
- `POST /api/start`
- `POST /api/finish`
- `GET /api/runs`
- `POST /api/runs/{run_id}/update`

## Data Model Extensions Used by the POC
- Run:
  - `is_missed_trip`
- SystemState (singleton):
  - `is_start_held`
  - `finish_triggered_at`

## Timing Behavior Implemented
- Shared finish trigger can be raised from Admin and observed on other devices
- Expected finish elapsed display uses trigger time minus run start time
- Confirm Finish stores finish time using trigger timestamp when available
- Frontend time rendering standardized to UTC display format for consistency across devices

## Operational Behaviors Implemented
- Missed Trip keeps run in active queue and visually highlighted
- Hold state is global and independent from DNF/Re-Run paperwork
- Hold can be manually asserted and manually released from Timing
- Admin reset clears runs, photos, and shared hold/trigger state

## Notes
- This POC intentionally uses simulated triggers and placeholder finish photo generation.
- The implementation now exceeds the original minimal POC scope and includes additional operational controls to support multi-device demos.