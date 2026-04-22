#!/bin/bash
# =============================================================================
# RaceWrangler Pi 5 First-Boot Setup Script
# =============================================================================
#
# USAGE:
#   1. Flash Raspberry Pi OS Lite (64-bit) with Raspberry Pi Imager.
#      In Imager advanced settings: set hostname=racewrangler, enable SSH.
#      Do NOT configure WiFi — wlan0 becomes the timing AP.
#
#   2. After flashing, mount the SD card on any computer. Open the
#      /boot/firmware partition (FAT32, visible on Windows/Mac/Linux).
#
#   3. Copy THIS FILE to /boot/firmware/pi5-first-boot.sh
#
#   4. Edit WIFI_PASSPHRASE below to your desired timing network password.
#      This same password must be flashed into every RaceSpy firmware config.
#
#   5. Open /boot/firmware/cmdline.txt in a plain text editor.
#      Add the following to the END of the single existing line (no newline):
#        systemd.run=/boot/firmware/pi5-first-boot.sh systemd.run_success_action=reboot
#
#   6. Eject and boot the Pi 5 with ethernet plugged in (needs internet for
#      apt and pip). Setup takes 20-40 minutes (PaddleOCR is a 1 GB download).
#
#   7. Check /boot/firmware/setup.log from any computer to see progress/errors.
#      When it says "SETUP COMPLETE", you can SSH in and verify.
#
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION — edit these before copying to the SD card
# =============================================================================

WIFI_PASSPHRASE="timing"   # Change this. Same in all RaceSpy configs.
WIFI_SSID="RaceWrangler-Timing"
WIFI_CHANNEL="6"
AP_IP="192.168.10.1"
DHCP_RANGE_START="192.168.10.50"
DHCP_RANGE_END="192.168.10.150"

REPO_URL="https://github.com/Skeptic-Racing/racewrangler.git"
REPO_BRANCH="main"
INSTALL_DIR="/opt/racewrangler"
SERVICE_USER="racewrangler"

# =============================================================================
# Logging — output goes to console AND to /boot/firmware/setup.log
# =============================================================================

LOG_FILE="/boot/firmware/setup.log"
MARKER_FILE="/etc/racewrangler-setup-complete"

exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

# =============================================================================
# Guard: don't run twice
# =============================================================================

if [ -f "$MARKER_FILE" ]; then
    log "Setup already complete (marker file exists). Exiting."
    exit 0
fi

log "============================================="
log "RaceWrangler Pi 5 First-Boot Setup"
log "============================================="

# =============================================================================
# 1. System packages
# =============================================================================

log "Syncing system clock before apt (Pi has no RTC on first boot)..."
HTTP_DATE=$(curl -sI --max-time 5 http://google.com | grep -i '^date:' | cut -d' ' -f2- | tr -d '\r' || true)
if [ -n "$HTTP_DATE" ]; then
    date -s "$HTTP_DATE" > /dev/null
    log "Clock set from HTTP: $HTTP_DATE"
else
    log "Warning: could not set clock from HTTP — apt signature checks may fail."
fi
log "Clock sync done: $(date -u)"

log "Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    hostapd \
    dnsmasq \
    avahi-daemon \
    chrony \
    python3-pip \
    python3-venv \
    git \
    libgomp1 \
    libopenblas-dev \
    curl
log "System packages installed."

# =============================================================================
# 2. Static IP on wlan0
# =============================================================================

log "Configuring static IP on wlan0..."
cat >> /etc/dhcpcd.conf << EOF

# RaceWrangler timing AP
interface wlan0
    static ip_address=${AP_IP}/24
    nohook wpa_supplicant
EOF
log "Static IP configured: ${AP_IP}"

# =============================================================================
# 3. hostapd — WiFi access point
# =============================================================================

log "Configuring hostapd..."
cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=${WIFI_SSID}
hw_mode=g
channel=${WIFI_CHANNEL}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=${WIFI_PASSPHRASE}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
systemctl unmask hostapd
systemctl enable hostapd
log "hostapd configured (SSID: ${WIFI_SSID})."

# =============================================================================
# 4. dnsmasq — DHCP and DNS
# =============================================================================

log "Configuring dnsmasq..."
# Preserve original config as backup
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig 2>/dev/null || true

cat > /etc/dnsmasq.conf << EOF
interface=wlan0
bind-interfaces

# DHCP pool
dhcp-range=${DHCP_RANGE_START},${DHCP_RANGE_END},24h
dhcp-option=3,${AP_IP}
dhcp-option=6,${AP_IP}

# DNS — resolve racewrangler and racewrangler.local to this server
address=/racewrangler/${AP_IP}
address=/racewrangler.local/${AP_IP}

domain-needed
bogus-priv
EOF

systemctl enable dnsmasq
log "dnsmasq configured."

# =============================================================================
# 5. avahi-daemon — mDNS fallback
# =============================================================================

log "Enabling avahi-daemon..."
systemctl enable avahi-daemon
log "avahi-daemon enabled."

# =============================================================================
# 6. chrony — NTP server for RaceSpies
# =============================================================================

log "Configuring chrony..."
cat >> /etc/chrony/chrony.conf << EOF

# Allow RaceSpies on the timing network to sync
allow ${AP_IP%.*}.0/24

# Aggressive polling so RaceSpies sync quickly at boot
minpoll 3
maxpoll 4

# If no internet, serve from local clock (less accurate but better than nothing)
local stratum 10
EOF

systemctl enable chrony
log "chrony configured."

# =============================================================================
# 7. Install RaceWrangler code and Python dependencies
# =============================================================================

PACKAGE_ARCHIVE="/boot/firmware/racewrangler-server.tar.gz"

if [ -f "$PACKAGE_ARCHIVE" ]; then
    log "Found package archive — extracting source code..."
    mkdir -p "$INSTALL_DIR"
    tar -xzf "$PACKAGE_ARCHIVE" -C "$INSTALL_DIR"
    chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR"
    log "Code extracted to $INSTALL_DIR."
else
    log "No package archive found — cloning from GitHub..."
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR"
        git pull origin "$REPO_BRANCH" || log "Warning: git pull failed, using existing code."
    else
        git clone --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR" \
            || die "Failed to clone from $REPO_URL — no internet and no package archive found."
    fi
    chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR"
fi

log "Creating Python virtual environment..."
sudo -u "$SERVICE_USER" python3 -m venv "${INSTALL_DIR}/.venv"

log "Installing backend requirements from PyPI..."
sudo -u "$SERVICE_USER" \
    "${INSTALL_DIR}/.venv/bin/pip" install --quiet \
    -r "${INSTALL_DIR}/backend/requirements.txt"
log "Backend requirements installed."

# =============================================================================
# 8. PaddleOCR (requires internet — too large for boot partition)
# =============================================================================

log "Installing PaddleOCR (15-20 minutes, requires internet)..."
if sudo -u "$SERVICE_USER" \
    "${INSTALL_DIR}/.venv/bin/pip" install --quiet paddlepaddle paddleocr; then
    log "PaddleOCR installed successfully."
else
    log "WARNING: PaddleOCR installation failed (no internet, or ARM64 wheels unavailable)."
    log "The server will run with MockDetector — all timing events go to the ambiguity queue."
    log "Retry later: sudo -u ${SERVICE_USER} ${INSTALL_DIR}/.venv/bin/pip install paddlepaddle paddleocr"
fi

# =============================================================================
# 10. Storage directory and environment file
# =============================================================================

log "Creating storage directory and environment file..."
mkdir -p "${INSTALL_DIR}/storage/events"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}/storage"

cat > "${INSTALL_DIR}/.env" << EOF
DATA_DIR=${INSTALL_DIR}/storage
EOF
chown "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}/.env"
log "Storage and .env configured."

# =============================================================================
# 11. Systemd service for RaceWrangler backend
# =============================================================================

log "Creating racewrangler systemd service..."
cat > /etc/systemd/system/racewrangler.service << EOF
[Unit]
Description=RaceWrangler Backend
After=network-online.target dnsmasq.service chrony.service
Wants=network-online.target

[Service]
User=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5
EnvironmentFile=${INSTALL_DIR}/.env
Environment=PYTHONPATH=${INSTALL_DIR}/backend

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable racewrangler
log "racewrangler service enabled."

# =============================================================================
# 12. Mark setup complete
# =============================================================================

echo "$(date)" > "$MARKER_FILE"
log ""
log "============================================="
log "SETUP COMPLETE"
log "============================================="
log "WiFi SSID : ${WIFI_SSID}"
log "Password  : ${WIFI_PASSPHRASE}"
log "Server IP : ${AP_IP}"
log "Hostname  : http://racewrangler/"
log ""
log "The Pi will reboot now. After reboot:"
log "  - Connect to '${WIFI_SSID}' and browse to http://racewrangler/"
log "  - Or SSH in and run: systemctl status racewrangler"
log "============================================="
