#!/bin/bash
# =============================================================================
# RaceWrangler Pi 5 First-Boot Finalizer (Minimal)
# =============================================================================
# Used with the pre-baked CI image.  ALL packages, Python deps, PaddleOCR,
# app code, config files, and systemd units are already installed.
#
# This script only handles two things:
#   1. Optional HTTPS certificate install (if cert files were placed on the
#      SD card's boot partition alongside this script)
#   2. Cleaning up the cmdline.txt hook so subsequent boots are faster
#
# On every subsequent boot the marker file causes an immediate exit.
# =============================================================================

set -euo pipefail

MARKER_FILE="/etc/racewrangler-setup-complete"
INSTALL_DIR="/opt/racewrangler"
CERTS_DIR="${INSTALL_DIR}/certs"
SERVICE_USER="racewrangler"
BOOT_DIR="/boot/firmware"
LOG_FILE="${BOOT_DIR}/setup.log"

exec >> "$LOG_FILE" 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Guard: run once only
if [[ -f "$MARKER_FILE" ]]; then
    exit 0
fi

log "============================================="
log "RaceWrangler first-boot finalizer"
log "============================================="

# =============================================================================
# Optional HTTPS certificate install
# =============================================================================
HTTPS_ENABLED=0
BOOT_CERT="${BOOT_DIR}/racewrangler-cert.pem"
BOOT_KEY="${BOOT_DIR}/racewrangler-key.pem"

if [[ -f "$BOOT_CERT" && -f "$BOOT_KEY" ]]; then
    log "Installing HTTPS certificate..."
    mkdir -p "$CERTS_DIR"
    cp "$BOOT_CERT" "${CERTS_DIR}/racewrangler-cert.pem"
    cp "$BOOT_KEY"  "${CERTS_DIR}/racewrangler-key.pem"
    chown "${SERVICE_USER}:${SERVICE_USER}" \
        "${CERTS_DIR}/racewrangler-cert.pem" \
        "${CERTS_DIR}/racewrangler-key.pem"
    chmod 644 "${CERTS_DIR}/racewrangler-cert.pem"
    chmod 600 "${CERTS_DIR}/racewrangler-key.pem"
    HTTPS_ENABLED=1
    log "HTTPS certificate installed."
fi

if [[ "$HTTPS_ENABLED" -eq 1 ]]; then
    log "Switching racewrangler service to HTTPS..."
    cat > /etc/systemd/system/racewrangler.service << EOF
[Unit]
Description=RaceWrangler Backend
After=network-online.target dnsmasq.service chrony.service
Wants=network-online.target

[Service]
User=${SERVICE_USER}
AmbientCapabilities=CAP_NET_BIND_SERVICE
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 443 --ssl-certfile ${CERTS_DIR}/racewrangler-cert.pem --ssl-keyfile ${CERTS_DIR}/racewrangler-key.pem
Restart=always
RestartSec=5
EnvironmentFile=${INSTALL_DIR}/.env
Environment=PYTHONPATH=${INSTALL_DIR}/backend

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable racewrangler-http
    log "HTTPS service configured."
fi

# =============================================================================
# Remove one-shot hook from cmdline.txt (keeps subsequent boots clean)
# =============================================================================
if grep -q 'pi5-first-boot-minimal.sh' "${BOOT_DIR}/cmdline.txt" 2>/dev/null; then
    sed -i \
        's| systemd\.run=[^ ]*||g;
         s| systemd\.run_success_action=[^ ]*||g' \
        "${BOOT_DIR}/cmdline.txt"
    log "Removed systemd.run hook from cmdline.txt."
fi

# =============================================================================
# Done
# =============================================================================
echo "$(date)" > "$MARKER_FILE"
log ""
log "============================================="
log "SETUP COMPLETE"
log "  Connect to the RaceWrangler-Timing Wi-Fi"
if [[ "$HTTPS_ENABLED" -eq 1 ]]; then
    log "  Browse to: https://racewrangler.local/"
else
    log "  Browse to: http://racewrangler/"
fi
log "============================================="
