# Minimal API Specification (POC Version)

## Purpose
This document defines the minimal set of API endpoints required for the RaceWrangler POC.  
It specifies the method, path, request body, and response body for each endpoint.

This is not a full API design — it is the smallest possible contract needed for Copilot to generate a working backend.

---

# 1. POST /start

## Description
Creates a new run when the starter confirms the start trigger and uploads a photo of the car.

## Request
**Content-Type:** `multipart/form-data`

Fields:
- `car_id` (integer, required)
- `photo` (file, required)

## Response (200)
```
{
  "success": true,
  "data": {
    "run_id": 1,
    "car_id": 12,
    "start_time": "2026-04-02T14:32:10.123Z",
    "start_photo_url": "/storage/photos/start/1.jpg",
    "penalties": 0,
    "is_dnf": false,
    "is_aborted": false,
    "finish_confirmed": false
  }
}
```

---

# 2. POST /finish

## Description
Completes a run when the finish worker selects the correct photo after a simulated finish trigger.

## Request (JSON)
```
{
  "run_id": 1
}
```

## Response (200)
```
{
  "success": true,
  "data": {
    "run_id": 1,
    "finish_time": "2026-04-02T14:32:45.987Z",
    "raw_time": 35.864,
    "finish_confirmed": true
  }
}
```

---

# 3. GET /runs

## Description
Returns all runs, both active and completed.  
Used by the Timing & Scoring UI.

## Query Parameters (optional)
- `status=active`  
- `status=completed`  

## Response (200)
```
{
  "success": true,
  "data": [
    {
      "run_id": 1,
      "car_id": 12,
      "car_number": "42",
      "class": "STX",
      "start_time": "2026-04-02T14:32:10.123Z",
      "finish_time": "2026-04-02T14:32:45.987Z",
      "raw_time": 35.864,
      "penalties": 2,
      "is_dnf": false,
      "is_aborted": false,
      "adjusted_time": 39.864,
      "start_photo_url": "/storage/photos/start/1.jpg",
      "finish_confirmed": true
    }
  ]
}
```

---

# 4. POST /runs/{id}/update

## Description
Updates penalties, DNF status, or aborted status for a run.  
Used by the Timing & Scoring UI.

## Request (JSON)
Any of the following fields may be included:

```
{
  "penalties": 2,
  "is_dnf": false,
  "is_aborted": false
}
```

## Response (200)
```
{
  "success": true,
  "data": {
    "run_id": 1,
    "penalties": 2,
    "is_dnf": false,
    "is_aborted": false,
    "adjusted_time": 39.864
  }
}
```

---

# 5. Error Format (All Endpoints)

```
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Run not found"
  }
}
```

Common error codes:
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `INTERNAL_ERROR`

---

# 6. Notes

- Authentication is disabled for the POC.  
- All timestamps are ISO 8601 strings.  
- Adjusted time = raw_time + penalties * 2.0 (hardcoded).  
- Photos are stored locally and referenced by URL.  
- Car list is hardcoded in the frontend or backend.  

