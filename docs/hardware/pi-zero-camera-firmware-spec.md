# Pi Zero Camera Firmware Specification
## RaceWrangler RaceSpy — Hardware Timing Camera
## Version: April 2026

This document defines the firmware behavior for the RaceSpy camera unit: a Raspberry Pi Zero 2W
with camera module and GPIO-attached photodiode trigger, deployed at start and finish timing lines.

---

## 1. Hardware Configuration

### 1.1 Compute and Camera

| Component | Specification |
|-----------|---------------|
| Compute | Raspberry Pi Zero 2W (512 MB RAM) |
| Camera (preferred) | Raspberry Pi Global Shutter Camera — eliminates rolling shutter on moving cars |
| Camera (acceptable) | Camera Module v3 or v2.1 |
| OS | Raspberry Pi OS Lite (64-bit) |

**Why Global Shutter:** Cars crossing the timing line at 20–50 mph produce a 3–10 ms window
per body width. Rolling shutter cameras expose row-by-row, causing diagonal distortion on fast
subjects. The Global Shutter Camera exposes the entire frame simultaneously.

### 1.2 Trigger Sensor Wiring

| Signal | Pi Zero GPIO | Notes |
|--------|-------------|-------|
| LM393 DO (trigger) | GPIO 17 | Active HIGH when beam is broken |
| LM393 VCC | 3.3 V | Sensor is 3.3V-compatible — no level shifter needed |
| LM393 GND | GND | |

**LM393 Photodiode Module** (Amazon ASIN B0DXBDRQQ7): digital output (DO) goes HIGH when the
IR beam is interrupted. Threshold is set via onboard potentiometer. Pair with an IR LED emitter
on the opposite side of the timing lane.

### 1.3 Status LED Wiring

| Color | GPIO | State it indicates |
|-------|------|--------------------|
| Green | GPIO 27 | WiFi associated |
| Blue | GPIO 22 | Server reachable / camera registered |
| Yellow | GPIO 5 | Armed — waiting for trigger |
| Red | GPIO 6 | Fault / not ready |

All LEDs use a 330 Ω series resistor to GND. Drive HIGH to illuminate via `gpiozero`.

**Do not use GPIO 14 for LEDs** — GPIO 14 is UART0 TX, reserved for RS-485 in Phase 2.

### 1.4 GPIO Pin Reservation (all builds)

Reserve these pins even if the Phase 2 hardware is not yet installed. Do not assign them to
other functions in Phase 1 wiring or software.

| GPIO | Function | Phase |
|------|----------|-------|
| 17 | LM393 trigger input | Phase 1 |
| 27 | Green LED (WiFi) | Phase 1 |
| 22 | Blue LED (server) | Phase 1 |
| 5 | Yellow LED (armed) | Phase 1 |
| 6 | Red LED (fault) | Phase 1 |
| 9, 10, 11 + CE0 | SPI0 — SX1278 LoRa | Phase 2 |
| 14, 15 | UART0 — RS-485 MAX485 | Phase 2 |
| 2, 3 | I2C — DS3231 RTC + GPS | Phase 2 |

---

## 2. Server Discovery

RaceSpies connect to the Pi 5 server using the hostname `racewrangler`. This hostname is
resolved by dnsmasq on the timing network. It is baked into the firmware configuration at
flash time — the firmware never uses a raw IP address.

```
SERVER_URL = "http://racewrangler"
```

The Pi 5's actual IP address (`192.168.10.1`) is an implementation detail on the server
side and is not referenced in firmware code.

---

## 3. Boot Sequence and State Machine

```
POWER ON
    │
    ▼
[1] WiFi ASSOCIATION
    │  Poll wpa_supplicant until interface is up
    │  → green LED ON
    ▼
[2] NTP SYNC
    │  chrony syncs to racewrangler (NTP server on Pi 5)
    │  Poll chronyc tracking until "System time offset" < 100ms
    │  → proceed once synced
    ▼
[3] SETUP MODE  (skipped if camera_id already registered with server)
    │  Green LED blinks 1 Hz: "show me a QR code"
    │  Camera continuously scans for QR code using picamera2 + pyzbar
    │
    │  QR payload format:
    │    {"role": "start" | "finish", "event_id": "<uuid>"}
    │
    │  On decode:
    │    POST http://racewrangler/api/cameras/register
    │    Body: {"camera_id": "<uuid>", "role": "...", "event_id": "...", "firmware_version": "..."}
    │
    │  200 OK → blue LED ON, proceed to ARMED
    │  4xx/5xx → red LED blinks, retry in 5s
    │
    │  Reboot fallback: if server already has this camera_id registered for an active event,
    │    server returns 200 with existing role → skip QR scan, proceed to ARMED
    ▼
[4] ARMED MODE
    │  Green + Blue + Yellow LEDs solid
    │  GPIO interrupt armed on GPIO 17, rising edge
    │  Waiting for trigger
    ▼
[TRIGGER EVENT]  → see section 4
```

### 3.1 State Transitions

| State | Entry condition | LEDs |
|-------|----------------|------|
| WiFi wait | Boot | Red solid |
| NTP sync | WiFi up | Green solid |
| Setup (QR scan) | NTP synced, not registered | Green blink |
| Armed | Registered with server | Green + Blue + Yellow solid |
| Fault | Any unrecoverable error | Red blink |

### 3.2 Remote Reset to Setup Mode

An admin can reset a camera to Setup Mode from the web UI. The server sets the camera's
registration to `pending`. On the RaceSpy's next keepalive poll (every 10s in Armed mode),
it detects the pending state and transitions back to Setup Mode.

**Use case:** Reassigning a camera to a different role mid-event without physically
touching the device.

### 3.3 Hot-Swap Recovery

If a RaceSpy fails and is replaced:
1. New device boots, reaches Setup Mode
2. Admin holds the same role QR code in front of it
3. New device registers with the same role
4. Server associates the new `camera_id` with the existing role for this event
5. Armed in < 30 seconds from power-on

---

## 4. Trigger Handling

### 4.1 GPIO Interrupt

```
gpiozero Button(pin=17, pull_up=False, bounce_time=0.05)
    → on_press callback
```

- Rising edge on GPIO 17 fires the callback
- `bounce_time=0.05` (50ms) handles contact chatter in the LM393 circuit

### 4.2 Capture Sequence

On trigger:
1. Record `timestamp_monotonic_ns` (monotonic clock, nanoseconds) — immune to NTP slew
2. Record `timestamp_utc_ms` (UTC milliseconds via `time.time()`) — synced by chrony to Pi 5
3. Increment `sequence_number`
4. Capture image via picamera2 (see section 5)
5. Queue payload for POST to server (see section 6)

### 4.3 Debounce / Rearm

After a trigger:
- Ignore further triggers for **2 seconds** (prevents double-triggering on same car)
- Rearm automatically after the 2-second window

### 4.4 Sequence Number

Starts at 0 at boot, increments by 1 per trigger. The server uses sequence numbers to detect
lost events (gap in sequence = missed trigger). A RaceSpy reboot resets the counter; the
server treats the reset as a new session.

---

## 5. Image Capture Settings

### 5.1 Camera Configuration (picamera2)

```python
from picamera2 import Picamera2

camera = Picamera2()
config = camera.create_still_configuration(
    main={"size": (3280, 2464)},   # Full sensor resolution
    controls={
        "ExposureTime": 400,        # 400 µs — freezes motion at 20–50 mph
        "AnalogueGain": 4.0,        # Adjust for lighting conditions
    }
)
camera.configure(config)
camera.start()
```

### 5.2 Shutter Speed Guidance

| Camera model | Target ExposureTime | Notes |
|---|---|---|
| Global Shutter Camera | 400–800 µs | Global exposure; 400 µs freezes motion cleanly |
| Camera Module v3 / v2.1 | 400 µs | Rolling shutter; 400 µs reduces but doesn't eliminate distortion |

400 µs is the reference value from the original racespy prototype.

### 5.3 JPEG Output

Capture to JPEG with quality 85. Target file size: 1.0–2.0 MB per image at full resolution.
Images are base64-encoded for the POST payload.

---

## 6. Server Payload Format

```
POST http://racewrangler/api/timing-events
Content-Type: application/json

{
  "camera_id": "<uuid>",
  "role": "start" | "finish",
  "event_id": "<uuid>",
  "timestamp_utc_ms": 1745800000000,
  "timestamp_monotonic_ns": 12345678901234,
  "sequence_number": 42,
  "image_base64": "<base64-encoded JPEG>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `camera_id` | UUID | Unique identifier for this RaceSpy, stable across reboots |
| `role` | enum | `"start"` or `"finish"` |
| `event_id` | UUID | Active event on the server |
| `timestamp_utc_ms` | int | UTC timestamp in milliseconds (chrony-synced) |
| `timestamp_monotonic_ns` | int | Monotonic nanosecond timestamp (immune to clock slew) |
| `sequence_number` | int | Monotonically increasing per session, resets on reboot |
| `image_base64` | string | JPEG image, base64-encoded |

### 6.1 Expected Responses

| Status | Meaning | RaceSpy action |
|--------|---------|---------------|
| 200 OK | Accepted | Continue; no retry needed |
| 409 Conflict | Duplicate sequence number | Log warning; do not retry |
| 5xx | Server error | Buffer locally; retry with exponential backoff |

---

## 7. Failure Modes

### 7.1 WiFi Drop During Event

1. Trigger fires, payload POST fails
2. Buffer payload to local SD card (file named `<sequence_number>.json` + `<sequence_number>.jpg`)
3. Retry POST every 10 seconds while WiFi is down
4. On reconnect, flush buffer in sequence order
5. Yellow LED blinks while buffer is non-empty to signal pending uploads

### 7.2 Server Unreachable at Boot

1. After WiFi association, POST to `http://racewrangler/api/cameras/register` fails
2. Red LED solid
3. Retry every 10 seconds
4. Do not enter Armed mode until server confirms registration

### 7.3 NTP Sync Failure

1. If chrony cannot sync within 60 seconds of WiFi association, enter Fault state (red LED)
2. Retry NTP every 10 seconds
3. Do not arm until clock is synced — an unsynced timestamp is worse than no timestamp

---

## 8. Clock Sync Accuracy

**Phase 1 (NTP via WiFi):**
- chrony on the RaceSpy syncs to the Pi 5 every 8–16 seconds (`minpoll 3 maxpoll 4`)
- Typical accuracy: ±1–2 ms under local LAN conditions
- Pi Zero 2W oscillator drift: ~50–100 ppm → ~0.3 ms drift per 8-second interval, corrected by next sync
- Acceptable for a test event. Autocross run times are 60–200 seconds; ±5ms timing error is negligible.

**Phase 2 (DS3231 RTC + GPS PPS, deferred):**
- DS3231 TCXO: ±2 ppm → ±0.6 ms drift over 5 minutes without sync
- u-blox NEO-M8N GPS PPS: ±50–200 ns absolute accuracy
- I2C GPIO 2/3 — does not conflict with UART (RS-485) on GPIO 14/15

---

## 9. Firmware Configuration File

The following values are baked into a config file at flash time (`/etc/racespy/config.json`):

```json
{
  "camera_id": "<uuid generated at flash time>",
  "server_url": "http://racewrangler",
  "wifi_ssid": "RaceWrangler-Timing",
  "wifi_psk": "<pre-shared key>",
  "ntp_server": "racewrangler",
  "trigger_gpio": 17,
  "led_wifi_gpio": 27,
  "led_server_gpio": 22,
  "led_armed_gpio": 5,
  "led_fault_gpio": 6,
  "debounce_seconds": 2.0,
  "exposure_time_us": 400,
  "jpeg_quality": 85
}
```

`camera_id` is a UUID generated once at flash time. It persists across reboots. It is the
stable identity used by the server to correlate registrations.

---

## 10. Systemd Service

The firmware script runs as a systemd service that starts automatically after the network
is up and chrony has synced:

```ini
[Unit]
Description=RaceSpy Camera Firmware
After=network-online.target chrony.service
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/racespy.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 11. Dependencies

```
picamera2       # Camera capture (replaces deprecated picamera)
gpiozero        # LED output + trigger input
pyzbar          # QR code decoding for role assignment
requests        # HTTP POST to server
chrony          # NTP client (system package)
```

---

## 12. Reference

- Existing prototype: https://github.com/c4tachan/racespy
  - Uses deprecated `picamera` → replace with `picamera2`
  - GPIO 14 used as power LED → **do not replicate** (conflicts with UART/RS-485)
  - GPIO 19 = blue LED → reassigned in this spec
  - 400 µs shutter speed, 3280×2464 resolution → keep
  - No networking or GPIO interrupt → add per this spec
