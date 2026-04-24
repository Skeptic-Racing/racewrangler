#!/bin/bash
# =============================================================================
# RaceSpy Pi Zero 2W First-Boot Setup Script
# =============================================================================
#
# USAGE:
#   1. Flash Raspberry Pi OS Lite (64-bit) with Raspberry Pi Imager.
#      In Imager advanced settings:
#        - Set hostname: racespy-start  (or racespy-finish)
#        - Enable SSH
#        - Set username/password (e.g. racespy / racespy)
#      Do NOT configure WiFi here — this script does it.
#
#   2. After flashing, mount the SD card boot partition (FAT32).
#
#   3. Copy THIS FILE to /boot/firmware/pi-zero-first-boot.sh
#
#   4. Edit the CONFIGURATION section below:
#        - WIFI_SSID / WIFI_PASSPHRASE             → Pi 5 timing AP (must match pi5-first-boot.sh)
#        - CAMERA_ROLE                             → "start" or "finish" for this unit
#        - HOME_WIFI_SSID / HOME_WIFI_PASSPHRASE  → home/shop WiFi (two options):
#            Option A: set these variables here → script adds home WiFi at priority 100
#            Option B: configure WiFi in Pi Imager → leave these blank, Imager handles it
#          Either way, home WiFi is preferred over the timing AP when in range.
#
#   5. Add to /boot/firmware/user-data (cloud-init runcmd section):
#        runcmd:
#          - [ bash, /boot/firmware/pi-zero-first-boot.sh ]
#      Or add to cmdline.txt (legacy):
#        systemd.run=/boot/firmware/pi-zero-first-boot.sh systemd.run_success_action=reboot
#
#   6. Eject and boot. Setup takes 5-10 minutes (pip downloads are small).
#      Check /boot/firmware/racespy-setup.log for progress.
#
#   7. When setup completes, the Pi Zero will reboot and start scanning for
#      the server QR code automatically.
#
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION — edit before copying to SD card
# =============================================================================

# Home/shop WiFi — Pi Zero connects here for development and pre-event prep.
# The RaceWrangler server must be reachable on this network (via Ethernet on the Pi 5).
HOME_WIFI_SSID=""              # e.g. "MyHomeNetwork"
HOME_WIFI_PASSPHRASE=""        # leave blank if open network (unusual)

# Timing AP — Pi 5 broadcasts this at the event. Must match pi5-first-boot.sh.
WIFI_SSID="RaceWrangler-Timing"
WIFI_PASSPHRASE="timing01"

SERVER_HOSTNAME="racewrangler.local" # Works on both timing AP (dnsmasq) and home network (mDNS)
CAMERA_ROLE="start"            # "start" or "finish" — label for this unit

INSTALL_DIR="/opt/racespy"
SERVICE_USER="racespy"

# =============================================================================
# Logging
# =============================================================================

LOG_FILE="/boot/firmware/racespy-setup.log"
MARKER_FILE="/boot/firmware/racespy-setup-complete"

exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

# =============================================================================
# Guard: don't run twice
# =============================================================================

if [ -f "$MARKER_FILE" ]; then
    log "Setup already complete. Exiting."
    exit 0
fi

log "============================================="
log "RaceSpy Pi Zero 2W First-Boot Setup"
log "Role: $CAMERA_ROLE"
log "============================================="

# =============================================================================
# 1. System packages
# =============================================================================

log "Waiting for network (WiFi association can lag behind cloud-init runcmd)..."
for i in $(seq 1 36); do
    if curl -s --max-time 5 --head http://deb.debian.org >/dev/null 2>&1; then
        log "Network is up (attempt ${i})."
        break
    fi
    if [ "${i}" -eq 36 ]; then
        log "--- Network diagnostics ---"
        ip addr show wlan0 2>&1 | while IFS= read -r line; do log "  $line"; done
        nmcli device status 2>&1 | while IFS= read -r line; do log "  $line"; done
        nmcli connection show 2>&1 | while IFS= read -r line; do log "  $line"; done
        rfkill list 2>&1 | while IFS= read -r line; do log "  $line"; done
        log "---------------------------"
        die "Network not available after 3 minutes — see diagnostics above."
    fi
    log "  No network yet, waiting 5s... (${i}/36)"
    sleep 5
done

log "Syncing clock..."
HTTP_DATE=$(curl -sI --max-time 5 http://google.com | grep -i '^date:' | cut -d' ' -f2- | tr -d '\r' || true)
if [ -n "$HTTP_DATE" ]; then
    date -s "$HTTP_DATE" > /dev/null
    log "Clock set: $HTTP_DATE"
fi

log "Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3-pip \
    python3-venv \
    python3-picamera2 \
    libzbar0 \
    chrony \
    git \
    curl
log "System packages installed."

# =============================================================================
# 2. Create service user
# =============================================================================

if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
    usermod -aG video,gpio "$SERVICE_USER"
    log "Created user $SERVICE_USER."
fi

# Allow racespy user to reboot without a password (needed for SSH-based reboot)
echo "${SERVICE_USER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/racespy-nopasswd
chmod 440 /etc/sudoers.d/racespy-nopasswd
log "Passwordless sudo configured for ${SERVICE_USER}."

# =============================================================================
# 3. WiFi configuration
# =============================================================================
# The timing AP is always added at priority -10 (lowest).
# The home network can be added two ways — pick one:
#   A) Set HOME_WIFI_SSID/PASSPHRASE below → this script adds it at priority 100.
#   B) Configure WiFi in Pi Imager → NM adds it at priority 0.
# Either way, home WiFi beats the timing AP (-10), so NM prefers home when in range
# and auto-roams to the timing AP at the event.

if [ -n "${HOME_WIFI_SSID}" ]; then
    log "Adding home WiFi network: ${HOME_WIFI_SSID} (priority 100)..."
    if [ -n "${HOME_WIFI_PASSPHRASE}" ]; then
        nmcli con add type wifi \
            con-name "Home-WiFi" \
            ssid "${HOME_WIFI_SSID}" \
            wifi-sec.key-mgmt wpa-psk \
            wifi-sec.psk "${HOME_WIFI_PASSPHRASE}" \
            connection.autoconnect yes \
            connection.autoconnect-priority 100
    else
        nmcli con add type wifi \
            con-name "Home-WiFi" \
            ssid "${HOME_WIFI_SSID}" \
            connection.autoconnect yes \
            connection.autoconnect-priority 100
    fi
    log "Home WiFi added."
else
    log "HOME_WIFI_SSID is blank — assuming home network was configured via Pi Imager."
fi

log "Adding RaceWrangler-Timing as fallback WiFi network (priority -10)..."
nmcli con add type wifi \
    con-name "RaceWrangler-Timing" \
    ssid "${WIFI_SSID}" \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "${WIFI_PASSPHRASE}" \
    connection.autoconnect yes \
    connection.autoconnect-priority -10
log "RaceWrangler-Timing added."

# =============================================================================
# 4. chrony — sync to Pi 5 server
# =============================================================================

log "Configuring chrony..."
cat > /etc/chrony/chrony.conf << EOF
# Sync to Pi 5 NTP server only
server ${SERVER_HOSTNAME} iburst minpoll 3 maxpoll 4
driftfile /var/lib/chrony/drift
makestep 1 3
rtcsync
EOF

systemctl enable chrony
log "chrony configured."

# =============================================================================
# 5. Install RaceSpy firmware
# =============================================================================

log "Installing RaceSpy firmware..."
mkdir -p "$INSTALL_DIR"

# Generate a stable camera_id UUID for this unit
CAMERA_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

# Write config
mkdir -p "${INSTALL_DIR}"
cat > "${INSTALL_DIR}/config.json" << EOF
{
  "camera_id": "${CAMERA_ID}",
  "server_url": "http://${SERVER_HOSTNAME}",
  "wifi_ssid": "${WIFI_SSID}",
  "ntp_server": "${SERVER_HOSTNAME}",
  "trigger_gpio": 17,
  "led_wifi_gpio": 27,
  "led_server_gpio": 22,
  "led_armed_gpio": 5,
  "led_fault_gpio": 6,
  "debounce_seconds": 2.0,
  "exposure_time_us": 400,
  "jpeg_quality": 85,
  "flip": true,
  "role": null,
  "event_id": null
}
EOF

# Symlink config to /etc/racespy/
mkdir -p /etc/racespy
ln -sf "${INSTALL_DIR}/config.json" /etc/racespy/config.json

# Create Python venv
python3 -m venv "${INSTALL_DIR}/.venv" --system-site-packages
chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR"

log "Installing Python dependencies..."
sudo -u "$SERVICE_USER" "${INSTALL_DIR}/.venv/bin/pip" install --quiet \
    requests \
    pyzbar \
    Pillow
# picamera2 and gpiozero installed as system packages (apt) above — use --system-site-packages

log "RaceSpy firmware installed. camera_id=${CAMERA_ID}"
log "Role label (human reference only): ${CAMERA_ROLE}"

# =============================================================================
#  Create required RaceSpy state + log directories with correct permissions
# =============================================================================

# Persistent state directory
mkdir -p /var/lib/racespy/buffer
chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/lib/racespy
chmod -R 755 /var/lib/racespy

# Logging directory
mkdir -p /var/log/racespy
chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/log/racespy
chmod 755 /var/log/racespy

# Runtime directory
mkdir -p /var/run/racespy
chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/run/racespy
chmod 755 /var/run/racespy


# =============================================================================
# 6. Copy firmware script
# =============================================================================

FIRMWARE_SCRIPT="${INSTALL_DIR}/racespy.py"

# The racespy.py should be placed at /boot/firmware/racespy.py before first boot,
# or it will be fetched below. Copy it if present.
if [ -f "/boot/firmware/racespy.py" ]; then
    cp /boot/firmware/racespy.py "$FIRMWARE_SCRIPT"
    chmod +x "$FIRMWARE_SCRIPT"
    chown "${SERVICE_USER}:${SERVICE_USER}" "$FIRMWARE_SCRIPT"
    log "Copied racespy.py from boot partition."

touch /var/log/racespy.log
chown "${SERVICE_USER}:${SERVICE_USER}" /var/log/racespy.log
else
    log "WARNING: /boot/firmware/racespy.py not found."
    log "Place racespy.py on the boot partition before running this script."
    log "Or install it manually at ${FIRMWARE_SCRIPT} after setup."
fi

# =============================================================================
# 7. Systemd service
# =============================================================================

log "Creating racespy systemd service..."
cat > /etc/systemd/system/racespy.service << EOF
[Unit]
Description=RaceSpy Camera Firmware
After=network-online.target chrony.service
Wants=network-online.target

[Service]
User=${SERVICE_USER}
ExecStart=${INSTALL_DIR}/.venv/bin/python3 ${FIRMWARE_SCRIPT}
Restart=always
RestartSec=5
Environment=RACESPY_CONFIG=/etc/racespy/config.json

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable racespy
log "racespy service enabled."

# =============================================================================
# 8. Log rotation
# =============================================================================

cat > /etc/logrotate.d/racespy << EOF
/var/log/racespy.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF

# =============================================================================
# 9. Mark setup complete
# =============================================================================

echo "$(date)" > "$MARKER_FILE"

log ""
log "============================================="
log "RACESPY SETUP COMPLETE"
log "============================================="
log "Camera ID : ${CAMERA_ID}"
log "Role label: ${CAMERA_ROLE}"
log "Server    : http://${SERVER_HOSTNAME}"
log ""
log "Rebooting now to start the racespy service..."
log "============================================="

reboot
