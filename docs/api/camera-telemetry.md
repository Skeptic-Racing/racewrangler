# Camera Telemetry Endpoint

## Overview
RaceSpies periodically POST diagnostic telemetry to the server for real-time health monitoring and troubleshooting. This endpoint collects GPS/PPS synchronization status, system resource utilization, and buffer state.

## Endpoint

```
POST /api/cameras/{camera_id}/telemetry
```

## Request

### Headers
```
Content-Type: application/json
```

### Body

```json
{
  "camera_id": "<uuid>",
  "event_id": "<uuid>",
  "timestamp_utc_ms": 1745800000000,
  "gps": {
    "pps_lock": true,
    "pps_offset_us": 1.322,
    "gps_lock": false,
    "ntp_lock": false,
    "stratum": 10
  },
  "health": {
    "temperature_c": 42.5,
    "wifi_signal_dbm": -65,
    "memory_usage_percent": 38.2,
    "disk_usage_percent": 24,
    "uptime_seconds": 86400
  },
  "buffered_payloads": 0
}
```

## Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `camera_id` | UUID string | Unique camera identifier (stable across reboots) |
| `event_id` | UUID string | Active event on the server |
| `timestamp_utc_ms` | integer | UTC millisecond timestamp when telemetry was collected |
| `gps` | object | GPS/timing synchronization status |
| `health` | object | System resource and hardware metrics |
| `buffered_payloads` | integer | Count of buffered timing events waiting to be POSTed |

### GPS Object

| Field | Type | Description |
|-------|------|-------------|
| `pps_lock` | boolean | PPS source is selected as primary time reference (GPS-disciplined; ±1-10 µs accuracy) |
| `pps_offset_us` | float or null | Current PPS time offset in microseconds (null if not locked) |
| `gps_lock` | boolean | GPS NMEA/SHM source is providing valid time (±50-200 ms accuracy) |
| `ntp_lock` | boolean | NTP peer (racewrangler) is reachable and providing valid time |
| `stratum` | integer or null | Current chrony stratum level (1 = directly connected to time source) |

**Interpretation:**
- ✅ Best case: `pps_lock = true`, `stratum = 1` or `10` (10 is OK if racewrangler is unavailable)
- ⚠️ Acceptable: `gps_lock = true` but `pps_lock = false` (accurate to ~100 ms)
- ❌ Problem: All three false (camera has no time source lock)

### Health Object

| Field | Type | Description |
|-------|------|-------------|
| `temperature_c` | float or null | CPU temperature in Celsius (Pi Zero 2W throttles at ~80°C) |
| `wifi_signal_dbm` | integer or null | WiFi signal strength in dBm (-30 is excellent, -90 is unusable) |
| `memory_usage_percent` | float or null | Percentage of RAM in use |
| `disk_usage_percent` | integer or null | Percentage of root filesystem in use |
| `uptime_seconds` | integer or null | Seconds since last boot |

**Thresholds for alerts:**
- `temperature_c > 75`: Getting hot, check airflow or reduce polling rate
- `wifi_signal_dbm < -80`: Weak signal, consider antenna placement
- `memory_usage_percent > 90`: Memory pressure, possible OOM risk
- `disk_usage_percent > 85`: Low disk, buffer may not flush properly
- `buffered_payloads > 10`: Persistent upload failures, investigate connectivity

## Response

### 200 OK / 201 Created / 202 Accepted

```json
{
  "status": "acknowledged",
  "camera_id": "<uuid>",
  "server_time_utc_ms": 1745800010000
}
```

### 400 Bad Request

```json
{
  "error": "Invalid payload",
  "details": "Missing required field: event_id"
}
```

### 404 Not Found

```json
{
  "error": "Camera not found",
  "camera_id": "<uuid>"
}
```

### 409 Conflict

```json
{
  "error": "Event mismatch",
  "details": "Camera is registered for event X but telemetry claims event Y"
}
```

## Posting Frequency

RaceSpies POST telemetry **every 60 seconds** while in ARMED state. If the POST fails, it is not buffered (telemetry is informational only; timing events take priority).

## Data Retention & Metrics

The server should:
1. Store telemetry records per camera per event for the duration of the event.
2. Provide a dashboard or API endpoint for operators to monitor real-time camera health during the event.
3. Generate post-event diagnostics: e.g., "Camera A had 3 PPS unlocks over 2 hours" or "Camera B's WiFi signal dropped 15 times."
4. Alert operators if telemetry stops arriving (indicates camera crashed or network failure).

## Error Handling on Camera

If the POST fails (network unreachable, server error, timeout), the RaceSpy firmware logs the error but does NOT retry or buffer telemetry. The next POST attempt occurs 60 seconds later. This is by design — timing events have priority, and telemetry is best-effort diagnostic.

## Example Use Case: UI Dashboard

A real-time event dashboard could display:

```
┌─────────────────────────────────────────────────────────────┐
│ Event: "Spring Series Round 2"  Start: 10:30 UTC            │
├────────────────────────────────────────────────────────────-┤
│ Camera          Role    PPS Lock  WiFi   Uptime  Buffered   │
├────────────────────────────────────────────────────────────-┤
│ cam_001_start   START   ✅ +1.2µs  -62dBm  3.5h      0       │
│ cam_002_finish  FINISH  ✅ +3.8µs  -71dBm  3.5h      0       │
│ cam_003_start   START   ⚠️  unlocked -89dBm  2.1h      2       │  ← alert
│ cam_004_finish  FINISH  ✅ +0.9µs  -58dBm  3.5h      0       │
└────────────────────────────────────────────────────────────-┘
```

## Integration Notes

- **Do NOT** require telemetry for timing event acceptance. Telemetry is optional (server should return 404 if camera not found, but not reject timing events).
- **Store** telemetry separately from timing events (different schema/table).
- **Index** telemetry by `(camera_id, event_id, timestamp_utc_ms)` for efficient queries.
- **Alert** operators if any camera's telemetry latency exceeds 2 minutes (indicates stale/offline state).
