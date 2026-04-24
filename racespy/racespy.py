#!/usr/bin/env python3
"""
RaceSpyCamera Firmware
Raspberry Pi Zero 2W + picamera2 + LM393 photodiode trigger

State machine:
    WIFI_WAIT → NTP_SYNC → SETUP (live preview → admin assigns role) → ARMED → [TRIGGER → post → ARMED]

Config: /etc/racespy/config.json
Buffer: /var/lib/racespy/buffer/ (payloads that failed to POST)
"""
import base64
import io
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from enum import Enum, auto
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(os.environ.get("RACESPY_CONFIG", "/etc/racespy/config.json"))
BUFFER_DIR = Path("/var/lib/racespy/buffer")
LOG_PATH = "/var/log/racespy.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_PATH),
    ],
)
log = logging.getLogger("racespy")

# ---------------------------------------------------------------------------
# Imports that only exist on Pi hardware
# ---------------------------------------------------------------------------

try:
    from gpiozero import LED, Button
    GPIO_AVAILABLE = True
except (ImportError, Exception):
    GPIO_AVAILABLE = False
    log.warning("gpiozero not available — LEDs and GPIO trigger disabled")

try:
    from picamera2 import Picamera2
    from libcamera import Transform
    CAMERA_AVAILABLE = True
except (ImportError, Exception):
    CAMERA_AVAILABLE = False
    log.warning("picamera2 not available — camera capture disabled")


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class State(Enum):
    WIFI_WAIT = auto()
    NTP_SYNC = auto()
    SETUP = auto()
    ARMED = auto()
    FAULT = auto()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "camera_id": str(uuid.uuid4()),
    "server_url": "http://racewrangler.local",
    "wifi_ssid": "RaceWrangler-Timing",
    "ntp_server": "racewrangler.local",
    "trigger_gpio": 17,
    "led_wifi_gpio": 27,
    "led_server_gpio": 22,
    "led_armed_gpio": 5,
    "led_fault_gpio": 6,
    "debounce_seconds": 2.0,
    "exposure_time_us": 400,
    "jpeg_quality": 85,
    "flip": False,
    # Populated after QR scan:
    "role": None,
    "event_id": None,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        log.info("Config not found — writing defaults to %s", CONFIG_PATH)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    # Fill any missing keys with defaults (firmware upgrades add keys)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# LED helpers
# ---------------------------------------------------------------------------

class LEDSet:
    """Manages the four status LEDs."""

    def __init__(self, cfg: dict):
        if GPIO_AVAILABLE:
            self.wifi = LED(cfg["led_wifi_gpio"])
            self.server = LED(cfg["led_server_gpio"])
            self.armed = LED(cfg["led_armed_gpio"])
            self.fault = LED(cfg["led_fault_gpio"])
            self._all = [self.wifi, self.server, self.armed, self.fault]
        else:
            self.wifi = self.server = self.armed = self.fault = None
            self._all = []

    def all_off(self):
        for led in self._all:
            led.off()

    def blink(self, led, on_time=0.5, off_time=0.5):
        if led:
            led.blink(on_time=on_time, off_time=off_time)

    def on(self, led):
        if led:
            led.on()

    def off(self, led):
        if led:
            led.off()

    def set_wifi_wait(self):
        """Green blink — attempting WiFi connection."""
        self.all_off()
        self.blink(self.wifi)

    def set_no_wifi(self):
        """Red solid — WiFi connection timed out."""
        self.all_off()
        self.on(self.fault)

    def set_wifi_up(self):
        """Green solid — WiFi connected."""
        self.all_off()
        self.on(self.wifi)

    def set_server_ready(self):
        """Green solid + Blue blink — server reachable, awaiting QR scan."""
        self.all_off()
        self.on(self.wifi)
        self.blink(self.server)

    def set_registered(self):
        """Green solid + Blue solid — QR scanned and registered."""
        self.all_off()
        self.on(self.wifi)
        self.on(self.server)

    def set_arming(self):
        """Green + Blue solid + Yellow blink — arming GPIO trigger."""
        self.all_off()
        self.on(self.wifi)
        self.on(self.server)
        self.blink(self.armed)

    def set_armed(self):
        """Green + Blue + Yellow solid — fully armed."""
        self.all_off()
        self.on(self.wifi)
        self.on(self.server)
        self.on(self.armed)

    def set_fault(self):
        """Red blink — unrecoverable error."""
        self.all_off()
        self.blink(self.fault, on_time=0.5, off_time=0.5)

    def set_buffered(self):
        """Armed pattern + yellow blink — payloads buffered locally."""
        self.all_off()
        self.on(self.wifi)
        self.on(self.server)
        self.blink(self.armed)


# ---------------------------------------------------------------------------
# WiFi check
# ---------------------------------------------------------------------------

def wifi_is_up() -> bool:
    # Check for any default route — works on both home WiFi (internet-connected)
    # and the timing AP (192.168.10.1 gateway, no internet).
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def wait_for_wifi(leds: LEDSet, timeout: float = 300.0) -> bool:
    log.info("Waiting for WiFi...")
    leds.set_wifi_wait()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if wifi_is_up():
            log.info("WiFi up")
            leds.set_wifi_up()
            return True
        time.sleep(5)
    return False


# ---------------------------------------------------------------------------
# NTP / chrony sync check
# ---------------------------------------------------------------------------

def ntp_is_synced() -> bool:
    try:
        result = subprocess.run(
            ["chronyc", "tracking"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            if "System time" in line:
                # "System time     :  0.000123456 seconds slow of NTP time"
                parts = line.split()
                if len(parts) >= 4:
                    offset_s = float(parts[3])
                    return abs(offset_s) < 0.1   # < 100ms = good enough
        return False
    except Exception:
        return False


def wait_for_ntp(leds: LEDSet, timeout: float = 120.0) -> bool:
    log.info("Waiting for NTP sync...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if ntp_is_synced():
            log.info("NTP synced")
            return True
        time.sleep(10)
    log.warning("NTP sync timeout — clock may be inaccurate")
    return False


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

class RaceSpyCamera:
    """Wraps picamera2. Call open() once at startup; capture_jpeg() per trigger."""

    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._cam = None

    def _transform(self):
        if not CAMERA_AVAILABLE:
            return None
        flip = self._cfg.get("flip", False)
        return Transform(hflip=flip, vflip=flip)

    def open(self):
        if not CAMERA_AVAILABLE:
            return
        self._cam = Picamera2()
        preview_cfg = self._cam.create_preview_configuration(
            main={"size": (640, 480)},
            transform=self._transform(),
        )
        self._cam.configure(preview_cfg)
        self._cam.start()
        log.info("Camera started in preview mode (flip=%s)", self._cfg.get("flip", False))

    def switch_to_capture_mode(self):
        """Switch to full-res fixed-exposure still mode for trigger captures."""
        if not CAMERA_AVAILABLE or self._cam is None:
            return
        self._cam.stop()
        still_cfg = self._cam.create_still_configuration(
            main={"size": (3280, 2464)},
            transform=self._transform(),
            controls={
                "ExposureTime": self._cfg["exposure_time_us"],
                "AnalogueGain": 4.0,
            },
        )
        self._cam.configure(still_cfg)
        self._cam.start()
        log.info("Camera switched to capture mode")

    def capture_jpeg(self) -> bytes:
        if not CAMERA_AVAILABLE or self._cam is None:
            return b""
        buf = io.BytesIO()
        self._cam.capture_file(buf, format="jpeg")
        return buf.getvalue()

    def close(self):
        if self._cam:
            self._cam.stop()
            self._cam.close()
            self._cam = None


# ---------------------------------------------------------------------------
# Server communication

def server_is_reachable(cfg: dict) -> bool:
    try:
        r = requests.get(cfg["server_url"], timeout=5)
        return r.status_code < 500
    except Exception:
        return False
# ---------------------------------------------------------------------------

def register_camera(cfg: dict) -> bool:
    """POST /api/cameras/register. Returns True if registered (200 or already registered)."""
    url = cfg["server_url"] + "/api/cameras/register"
    payload = {
        "camera_id": cfg["camera_id"],
        "role": cfg.get("role"),
        "event_id": cfg.get("event_id"),
        "firmware_version": "1.0.0",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            body = r.json().get("data", {})
            role = body.get("role")
            event_id = body.get("event_id")
            if role and event_id:
                cfg["role"] = role
                cfg["event_id"] = event_id
                save_config(cfg)
            return True
        log.warning("register_camera: HTTP %s", r.status_code)
        return False
    except Exception as exc:
        log.warning("register_camera error: %s", exc)
        return False


def get_camera_status(cfg: dict) -> str | None:
    """GET /api/cameras/{camera_id}/keepalive. Returns status string or None."""
    url = cfg["server_url"] + f"/api/cameras/{cfg['camera_id']}/keepalive"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", {}).get("status")
    except Exception:
        pass
    return None


def post_timing_event(cfg: dict, payload: dict) -> bool:
    """POST timing event to server. Returns True on 200 OK."""
    event_id = cfg.get("event_id")
    if not event_id:
        log.warning("post_timing_event: no event_id configured")
        return False
    url = cfg["server_url"] + f"/api/v1/events/{event_id}/timing-events"
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            return True
        log.warning("post_timing_event: HTTP %s", r.status_code)
        return False
    except Exception as exc:
        log.warning("post_timing_event error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Local buffer (for WiFi-drop resilience)
# ---------------------------------------------------------------------------

def buffer_payload(payload: dict, seq: int):
    BUFFER_DIR.mkdir(parents=True, exist_ok=True)
    path = BUFFER_DIR / f"{seq:06d}.json"
    with open(path, "w") as f:
        json.dump(payload, f)
    log.info("Buffered payload seq=%d to %s", seq, path)


def flush_buffer(cfg: dict):
    if not BUFFER_DIR.exists():
        return
    files = sorted(BUFFER_DIR.glob("*.json"))
    if not files:
        return
    log.info("Flushing %d buffered payloads...", len(files))
    for path in files:
        try:
            with open(path) as f:
                payload = json.load(f)
            if post_timing_event(cfg, payload):
                path.unlink()
                log.info("Flushed %s", path.name)
            else:
                break   # Server still unreachable; stop trying
        except Exception as exc:
            log.warning("flush_buffer error for %s: %s", path, exc)
            break


def buffer_is_empty() -> bool:
    if not BUFFER_DIR.exists():
        return True
    return not any(BUFFER_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Live preview setup mode
# ---------------------------------------------------------------------------

def push_frame(cfg: dict, jpeg: bytes) -> dict | None:
    """POST a JPEG frame to the server. Returns the response body or None on failure."""
    url = cfg["server_url"] + f"/api/cameras/{cfg['camera_id']}/frame"
    try:
        r = requests.post(url, files={"image": ("frame.jpg", jpeg, "image/jpeg")}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as exc:
        log.debug("push_frame error: %s", exc)
    return None


def run_setup_mode(cfg: dict, leds: LEDSet, camera: RaceSpyCamera) -> bool:
    """
    Push live preview frames to the server until an admin assigns a role via the web UI.
    Updates cfg in place and persists to disk. Returns True on success.
    """
    log.info("Entering SETUP mode — pushing preview frames, waiting for admin assignment")

    while not server_is_reachable(cfg):
        log.info("Server not reachable, waiting...")
        leds.set_wifi_up()
        time.sleep(5)

    leds.set_server_ready()
    log.info("Server reachable — streaming preview to admin UI")

    while True:
        jpeg = camera.capture_jpeg()
        if not jpeg:
            time.sleep(1)
            continue

        response = push_frame(cfg, jpeg)
        if response is None:
            log.warning("Lost server connection")
            leds.set_wifi_up()
            while not server_is_reachable(cfg):
                time.sleep(5)
            leds.set_server_ready()
            continue

        if response.get("status") == "assigned":
            cfg["role"] = response["role"]
            cfg["event_id"] = response["event_id"]
            save_config(cfg)
            log.info("Assignment received: role=%s event_id=%s", cfg["role"], cfg["event_id"])
            leds.set_registered()
            return True

        time.sleep(1)   # ~1 fps preview


# ---------------------------------------------------------------------------
# Trigger handler (runs in gpiozero callback thread)
# ---------------------------------------------------------------------------

class TriggerHandler:
    def __init__(self, cfg: dict, camera: RaceSpyCamera):
        self._cfg = cfg
        self._camera = camera
        self._debounce = cfg["debounce_seconds"]
        self._last_trigger = 0.0
        self._seq = 0
        self._lock = threading.Lock()

    def on_trigger(self):
        now = time.monotonic()
        with self._lock:
            if now - self._last_trigger < self._debounce:
                return
            self._last_trigger = now
            seq = self._seq
            self._seq += 1

        # Timestamps captured as close to trigger as possible
        timestamp_utc_ms = int(time.time() * 1000)
        timestamp_monotonic_ns = time.monotonic_ns()

        log.info("Trigger! seq=%d utc_ms=%d", seq, timestamp_utc_ms)

        jpeg = self._camera.capture_jpeg()
        image_base64 = base64.b64encode(jpeg).decode("ascii") if jpeg else None

        payload = {
            "camera_id": self._cfg["camera_id"],
            "role": self._cfg.get("role", "unknown"),
            "timestamp_utc_ms": timestamp_utc_ms,
            "timestamp_monotonic_ns": timestamp_monotonic_ns,
            "sequence_number": seq,
            "image_base64": image_base64,
        }

        # Try to post immediately; buffer on failure
        if post_timing_event(self._cfg, payload):
            log.info("Timing event posted: seq=%d", seq)
        else:
            buffer_payload(payload, seq)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== RaceSpy firmware starting ===")
    BUFFER_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    leds = LEDSet(cfg)
    camera = RaceSpyCamera(cfg)

    # -----------------------------------------------------------------------
    # 1. Wait for WiFi
    # -----------------------------------------------------------------------
    state = State.WIFI_WAIT
    if not wait_for_wifi(leds):
        log.error("WiFi not available after timeout — halting")
        leds.set_no_wifi()
        time.sleep(30)   # systemd will restart us; don't spin fast
        return

    state = State.NTP_SYNC

    # -----------------------------------------------------------------------
    # 2. NTP sync
    # -----------------------------------------------------------------------
    wait_for_ntp(leds)   # Warn but don't block — better to arm than sit forever
    leds.set_wifi_up()   # Green solid — WiFi up and clock synced

    # -----------------------------------------------------------------------
    # 3. Open camera (done once; stays open for the event)
    # -----------------------------------------------------------------------
    while True:
        try:
            camera.open()
            break
        except Exception as exc:
            log.error("Camera not detected: %s — check ribbon cable. Retrying in 30s.", exc)
            leds.set_fault()
            time.sleep(30)

    # -----------------------------------------------------------------------
    # 4. Setup mode — register if not already configured
    # -----------------------------------------------------------------------
    state = State.SETUP

    # Check if already registered from a previous boot
    if cfg.get("role") and cfg.get("event_id"):
        log.info("Config has role=%s event_id=%s — attempting keepalive to confirm", cfg["role"], cfg["event_id"])
        status = get_camera_status(cfg)
        if status == "active":
            log.info("Server confirms active registration — skipping QR scan")
        elif status == "pending":
            log.info("Server says pending — running QR setup")
            run_setup_mode(cfg, leds, camera)
        else:
            log.info("Server unreachable or unknown status — re-registering")
            register_camera(cfg)
    else:
        run_setup_mode(cfg, leds, camera)

    # -----------------------------------------------------------------------
    # 5. Armed mode
    # -----------------------------------------------------------------------
    state = State.ARMED
    log.info("=== ARMED: role=%s event_id=%s ===", cfg.get("role"), cfg.get("event_id"))
    leds.set_arming()
    camera.switch_to_capture_mode()

    handler = TriggerHandler(cfg, camera)

    if GPIO_AVAILABLE:
        trigger_btn = Button(
            pin=cfg["trigger_gpio"],
            pull_up=False,
            bounce_time=0.05,
        )
        trigger_btn.when_pressed = handler.on_trigger
    else:
        log.warning("GPIO not available — trigger will never fire")
        trigger_btn = None

    leds.set_armed()

    # -----------------------------------------------------------------------
    # 6. Main loop: keepalive + buffer flush
    # -----------------------------------------------------------------------
    last_keepalive = 0.0
    while True:
        now = time.monotonic()

        # Buffer flush on reconnect
        if not buffer_is_empty():
            leds.set_buffered()
            flush_buffer(cfg)
            if buffer_is_empty():
                leds.set_armed()

        # Keepalive every 10 seconds
        if now - last_keepalive >= 10.0:
            status = get_camera_status(cfg)
            last_keepalive = time.monotonic()

            if status == "pending":
                # Admin reset camera to setup mode from web UI
                log.info("Server set camera to pending — returning to SETUP mode")
                leds.set_setup()
                run_setup_mode(cfg, leds, camera)
                log.info("Re-armed: role=%s", cfg.get("role"))
                leds.set_armed()

        time.sleep(1)


if __name__ == "__main__":
    main()
