#!/bin/bash
# =============================================================================
# RaceWrangler Pi 5 Image Builder — Full Bake
# =============================================================================
# Builds a Raspberry Pi OS image with EVERYTHING pre-installed:
#   - System packages (hostapd, dnsmasq, chrony, avahi, Python...)
#   - All Python / backend dependencies
#   - PaddleOCR (paddlepaddle + paddleocr wheels)
#   - RaceWrangler app code at /opt/racewrangler
#   - All config files (NetworkManager, hostapd, dnsmasq, chrony, udev)
#   - Systemd units pre-installed and enabled
#
# First boot only needs to:
#   - Optionally install HTTPS cert/key (if cert files are on the SD card)
#   - Remove the one-shot systemd.run hook from cmdline.txt
#   - Write a completion marker
#
# Works identically locally and in GitHub Actions.
#
# LOCAL PREREQUISITES:
#   sudo apt-get install -y qemu-user-static binfmt-support parted e2fsprogs xz-utils
#
# USAGE:
#   # Download and unpack the base image first:
#   curl -fL https://downloads.raspberrypi.com/raspios_lite_arm64_latest \
#     -o dist/raspios.img.xz
#   xz -d dist/raspios.img.xz
#
#   bash scripts/build-pi5-image.sh \
#     --base-image dist/raspios.img \
#     --output-image dist/racewrangler-pi5.img \
#     [--wifi-ssid RaceWrangler-Timing] \
#     [--wifi-passphrase timing01]
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# =============================================================================
# Defaults — override with flags
# =============================================================================
WIFI_SSID="RaceWrangler-Timing"
WIFI_PASSPHRASE="timing01"
WIFI_CHANNEL="6"
AP_IP="192.168.10.1"
DHCP_RANGE_START="192.168.10.50"
DHCP_RANGE_END="192.168.10.150"
INSTALL_DIR="/opt/racewrangler"
SERVICE_USER="racewrangler"
BASE_IMAGE=""
OUTPUT_IMAGE=""
EXTRA_GB=6

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-image)      BASE_IMAGE="$2";      shift 2 ;;
        --output-image)    OUTPUT_IMAGE="$2";    shift 2 ;;
        --wifi-ssid)       WIFI_SSID="$2";       shift 2 ;;
        --wifi-passphrase) WIFI_PASSPHRASE="$2"; shift 2 ;;
        -h|--help)         sed -n '3,35p' "$0";  exit 0  ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

[[ -n "$BASE_IMAGE" ]]   || { echo "ERROR: --base-image required";   exit 1; }
[[ -n "$OUTPUT_IMAGE" ]] || { echo "ERROR: --output-image required"; exit 1; }
[[ -f "$BASE_IMAGE" ]]   || { echo "ERROR: base image not found: $BASE_IMAGE"; exit 1; }

for cmd in losetup parted e2fsck resize2fs qemu-aarch64-static; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "ERROR: $cmd not found."
        echo "  Install: sudo apt-get install -y qemu-user-static binfmt-support parted e2fsprogs"
        exit 1
    }
done

# =============================================================================
# Build frontend + package archive
# =============================================================================
bash "${REPO_ROOT}/scripts/build-pi5-package.sh"

ARCHIVE="${REPO_ROOT}/dist/racewrangler-server.tar.gz"
[[ -f "$ARCHIVE" ]] || { echo "ERROR: archive not found after build: $ARCHIVE"; exit 1; }

# =============================================================================
# Setup work directory and cleanup trap
# =============================================================================
mkdir -p "$(dirname "$OUTPUT_IMAGE")"
WORK_DIR="$(mktemp -d)"
MOUNT_ROOT="${WORK_DIR}/rootfs"
LOOPDEV=""

cleanup() {
    set +e
    if [[ -n "${MOUNT_ROOT:-}" && -d "${MOUNT_ROOT}" ]]; then
        sudo rm -f  "${MOUNT_ROOT}/usr/sbin/policy-rc.d"
        sudo rm -f  "${MOUNT_ROOT}/usr/bin/qemu-aarch64-static"
        [[ -f "${MOUNT_ROOT}/etc/resolv.conf.bak" ]] && \
            sudo mv "${MOUNT_ROOT}/etc/resolv.conf.bak" "${MOUNT_ROOT}/etc/resolv.conf"
        for mp in tmp sys proc dev; do
            sudo umount "${MOUNT_ROOT}/${mp}" 2>/dev/null || true
        done
        sudo umount "${MOUNT_ROOT}/boot/firmware" 2>/dev/null || true
        sudo umount "${MOUNT_ROOT}"               2>/dev/null || true
    fi
    [[ -n "${LOOPDEV:-}" ]] && sudo losetup -d "$LOOPDEV" 2>/dev/null || true
    rm -rf "${WORK_DIR:-}"
}
trap cleanup EXIT

echo "=== RaceWrangler Pi 5 Full-Bake Image Builder ==="
echo "Base image  : $BASE_IMAGE"
echo "Output image: $OUTPUT_IMAGE"
echo "WiFi SSID   : $WIFI_SSID"
echo ""

# =============================================================================
# 1. Grow image to make room for dependencies
# =============================================================================
echo "[1/9] Preparing image (adding ${EXTRA_GB} GB)..."
cp "$BASE_IMAGE" "$OUTPUT_IMAGE"
truncate -s "+${EXTRA_GB}G" "$OUTPUT_IMAGE"
parted -s "$OUTPUT_IMAGE" resizepart 2 100%

# =============================================================================
# 2. Mount image partitions
# =============================================================================
echo "[2/9] Mounting image..."
mkdir -p "$MOUNT_ROOT"
LOOPDEV=$(sudo losetup -fP --show "$OUTPUT_IMAGE")
echo "  Loop device: $LOOPDEV"

sudo e2fsck -f "${LOOPDEV}p2"
EXIT_CODE=$?
[[ $EXIT_CODE -gt 2 ]] && { echo "ERROR: e2fsck failed (exit $EXIT_CODE)"; exit 1; }
sudo resize2fs "${LOOPDEV}p2"

sudo mount "${LOOPDEV}p2" "$MOUNT_ROOT"
sudo mount "${LOOPDEV}p1" "${MOUNT_ROOT}/boot/firmware"

# =============================================================================
# 3. Set up chroot environment (qemu, bind mounts, DNS, policy-rc.d)
# =============================================================================
echo "[3/9] Configuring chroot environment..."
sudo mount --bind /dev  "${MOUNT_ROOT}/dev"
sudo mount --bind /proc "${MOUNT_ROOT}/proc"
sudo mount --bind /sys  "${MOUNT_ROOT}/sys"
sudo mount -t tmpfs tmpfs "${MOUNT_ROOT}/tmp"

sudo cp /usr/bin/qemu-aarch64-static "${MOUNT_ROOT}/usr/bin/"

sudo cp  "${MOUNT_ROOT}/etc/resolv.conf" "${MOUNT_ROOT}/etc/resolv.conf.bak" 2>/dev/null || true
printf 'nameserver 8.8.8.8\n' | sudo tee "${MOUNT_ROOT}/etc/resolv.conf" > /dev/null

# Prevent service starts during apt-get install inside chroot
printf '#!/bin/sh\nexit 101\n' | sudo tee "${MOUNT_ROOT}/usr/sbin/policy-rc.d" > /dev/null
sudo chmod +x "${MOUNT_ROOT}/usr/sbin/policy-rc.d"

# =============================================================================
# 4. Write all config files into rootfs (no chroot needed — pure file writes)
# =============================================================================
echo "[4/9] Writing configuration files..."
CHRONY_NETWORK="${AP_IP%.*}.0"

# NetworkManager: leave wlan0 to hostapd
sudo mkdir -p "${MOUNT_ROOT}/etc/NetworkManager/conf.d"
sudo tee "${MOUNT_ROOT}/etc/NetworkManager/conf.d/10-unmanaged-wlan0.conf" > /dev/null << 'CONF'
[keyfile]
unmanaged-devices=interface-name:wlan0
CONF

# wlan0 static-IP service
sudo tee "${MOUNT_ROOT}/etc/systemd/system/wlan0-static-ip.service" > /dev/null << UNIT
[Unit]
Description=Assign static IP to wlan0 timing AP
After=hostapd.service
Requires=hostapd.service
Before=dnsmasq.service

[Service]
Type=oneshot
ExecStart=/sbin/ip addr replace ${AP_IP}/24 dev wlan0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT

# dnsmasq ordering drop-in
sudo mkdir -p "${MOUNT_ROOT}/etc/systemd/system/dnsmasq.service.d"
sudo tee "${MOUNT_ROOT}/etc/systemd/system/dnsmasq.service.d/after-wlan0.conf" > /dev/null << 'DROPIN'
[Unit]
After=wlan0-static-ip.service
Requires=wlan0-static-ip.service
DROPIN

# hostapd config (SSID and passphrase baked in here)
sudo mkdir -p "${MOUNT_ROOT}/etc/hostapd"
sudo tee "${MOUNT_ROOT}/etc/hostapd/hostapd.conf" > /dev/null << HAPDCONF
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
HAPDCONF

if grep -q '#DAEMON_CONF=""' "${MOUNT_ROOT}/etc/default/hostapd" 2>/dev/null; then
    sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' \
        "${MOUNT_ROOT}/etc/default/hostapd"
else
    printf 'DAEMON_CONF="/etc/hostapd/hostapd.conf"\n' | \
        sudo tee -a "${MOUNT_ROOT}/etc/default/hostapd" > /dev/null
fi

# dnsmasq
sudo mv "${MOUNT_ROOT}/etc/dnsmasq.conf" "${MOUNT_ROOT}/etc/dnsmasq.conf.orig" 2>/dev/null || true
sudo tee "${MOUNT_ROOT}/etc/dnsmasq.conf" > /dev/null << DNSCONF
interface=wlan0
bind-interfaces
dhcp-range=${DHCP_RANGE_START},${DHCP_RANGE_END},24h
dhcp-option=3,${AP_IP}
dhcp-option=6,${AP_IP}
address=/racewrangler/${AP_IP}
address=/racewrangler.local/${AP_IP}
domain-needed
bogus-priv
DNSCONF

# chrony
sudo tee -a "${MOUNT_ROOT}/etc/chrony/chrony.conf" > /dev/null << CHRONYCONF

# RaceWrangler timing network
allow ${CHRONY_NETWORK}/24
minpoll 3
maxpoll 4
local stratum 10
CHRONYCONF

# udev rule — auto-unblock wifi radio on every boot; no rfkill call needed at runtime
sudo mkdir -p "${MOUNT_ROOT}/etc/udev/rules.d"
sudo tee "${MOUNT_ROOT}/etc/udev/rules.d/10-rfkill-unblock.rules" > /dev/null << 'UDEV'
SUBSYSTEM=="rfkill", ATTR{type}=="wlan", ATTR{soft}="0"
UDEV

# racewrangler.service (HTTP default; first-boot-minimal switches to HTTPS if cert present)
sudo tee "${MOUNT_ROOT}/etc/systemd/system/racewrangler.service" > /dev/null << SVCUNIT
[Unit]
Description=RaceWrangler Backend
After=network-online.target dnsmasq.service chrony.service
Wants=network-online.target

[Service]
User=${SERVICE_USER}
AmbientCapabilities=CAP_NET_BIND_SERVICE
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5
EnvironmentFile=${INSTALL_DIR}/.env
Environment=PYTHONPATH=${INSTALL_DIR}/backend

[Install]
WantedBy=multi-user.target
SVCUNIT

# racewrangler-http.service (redirect; enabled by first-boot-minimal if HTTPS)
sudo tee "${MOUNT_ROOT}/etc/systemd/system/racewrangler-http.service" > /dev/null << RDRUNIT
[Unit]
Description=RaceWrangler HTTP to HTTPS Redirect
After=network-online.target
Wants=network-online.target

[Service]
User=${SERVICE_USER}
AmbientCapabilities=CAP_NET_BIND_SERVICE
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn http_redirect:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5
Environment=PYTHONPATH=${INSTALL_DIR}/backend

[Install]
WantedBy=multi-user.target
RDRUNIT

# .env + storage directory
sudo mkdir -p "${MOUNT_ROOT}${INSTALL_DIR}/storage/events"
sudo tee "${MOUNT_ROOT}${INSTALL_DIR}/.env" > /dev/null << ENVFILE
DATA_DIR=${INSTALL_DIR}/storage
ENVFILE

# =============================================================================
# 5. Extract app code into rootfs
# =============================================================================
echo "[5/9] Extracting app code..."
sudo tar -xzf "$ARCHIVE" -C "${MOUNT_ROOT}${INSTALL_DIR}"

# =============================================================================
# 6. Create service user
# =============================================================================
echo "[6/9] Creating service user..."
if ! sudo chroot "$MOUNT_ROOT" /usr/bin/id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo chroot "$MOUNT_ROOT" /usr/sbin/useradd \
        --create-home --shell /bin/bash "$SERVICE_USER"
fi
sudo chroot "$MOUNT_ROOT" /bin/chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR"

# =============================================================================
# 7. Enable services via systemctl --root (runs on host, no chroot needed)
# =============================================================================
echo "[7/9] Enabling services..."
sudo systemctl unmask --root="$MOUNT_ROOT" hostapd
sudo systemctl enable --root="$MOUNT_ROOT" \
    hostapd dnsmasq avahi-daemon chrony \
    wlan0-static-ip racewrangler

# =============================================================================
# 8. Install packages + Python deps inside ARM64 chroot (emulated via QEMU)
# =============================================================================
echo "[8/9] Installing apt packages and Python deps (slow under QEMU emulation — 20-40 min)..."
sudo chroot "$MOUNT_ROOT" /bin/bash << CHROOTSCRIPT
set -e
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq \
    hostapd dnsmasq avahi-daemon chrony \
    python3-pip python3-venv git \
    libgomp1 libopenblas-dev curl

python3 -m venv ${INSTALL_DIR}/.venv
${INSTALL_DIR}/.venv/bin/pip install --quiet \
    -r ${INSTALL_DIR}/backend/requirements.txt

echo "Installing PaddleOCR (the slow part)..."
if ${INSTALL_DIR}/.venv/bin/pip install --quiet paddlepaddle paddleocr; then
    echo "PaddleOCR installed successfully."
else
    echo "WARNING: PaddleOCR install failed (ARM64 wheels unavailable?). Server will use MockDetector."
fi

chown -R ${SERVICE_USER}:${SERVICE_USER} ${INSTALL_DIR}/.venv
CHROOTSCRIPT

# =============================================================================
# Clean up chroot environment
# =============================================================================
sudo rm -f  "${MOUNT_ROOT}/usr/sbin/policy-rc.d"
sudo rm -f  "${MOUNT_ROOT}/usr/bin/qemu-aarch64-static"
sudo mv     "${MOUNT_ROOT}/etc/resolv.conf.bak" "${MOUNT_ROOT}/etc/resolv.conf" 2>/dev/null || true

sync
sudo umount "${MOUNT_ROOT}/tmp"
sudo umount "${MOUNT_ROOT}/sys"
sudo umount "${MOUNT_ROOT}/proc"
sudo umount "${MOUNT_ROOT}/dev"

# =============================================================================
# 9. Inject minimal first-boot script + cmdline.txt + user-data
# =============================================================================
echo "[9/9] Injecting first-boot finalizer..."

MINIMAL_FIRST_BOOT="${REPO_ROOT}/scripts/pi5-first-boot-minimal.sh"
[[ -f "$MINIMAL_FIRST_BOOT" ]] || {
    echo "ERROR: $MINIMAL_FIRST_BOOT not found"
    exit 1
}
sudo cp "$MINIMAL_FIRST_BOOT" "${MOUNT_ROOT}/boot/firmware/pi5-first-boot-minimal.sh"
sudo chmod +x "${MOUNT_ROOT}/boot/firmware/pi5-first-boot-minimal.sh"

# Optional HTTPS cert from repo
CERT_DEFAULT="${REPO_ROOT}/certs/pi5/racewrangler-cert.pem"
KEY_DEFAULT="${REPO_ROOT}/certs/pi5/racewrangler-key.pem"
if [[ -f "$CERT_DEFAULT" && -f "$KEY_DEFAULT" ]]; then
    sudo cp "$CERT_DEFAULT" "${MOUNT_ROOT}/boot/firmware/racewrangler-cert.pem"
    sudo cp "$KEY_DEFAULT"  "${MOUNT_ROOT}/boot/firmware/racewrangler-key.pem"
    echo "  Included HTTPS cert/key from certs/pi5/."
fi

# cmdline.txt — add one-shot systemd.run hook (must remain single line)
CMDLINE="${MOUNT_ROOT}/boot/firmware/cmdline.txt"
RUN_ARG="systemd.run=/boot/firmware/pi5-first-boot-minimal.sh systemd.run_success_action=none"
if ! sudo grep -q "pi5-first-boot-minimal.sh" "$CMDLINE" 2>/dev/null; then
    sudo sed -i "1 s|\$| ${RUN_ARG}|" "$CMDLINE"
fi

# user-data (cloud-init fallback)
USER_DATA="${MOUNT_ROOT}/boot/firmware/user-data"
[[ -f "$USER_DATA" ]] || printf '#cloud-config\n' | sudo tee "$USER_DATA" > /dev/null

python3 - "$USER_DATA" << 'PYEOF'
import re, sys

path = sys.argv[1]
cmd  = 'pi5-first-boot-minimal.sh'

with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

entry = f'  - [ bash, /boot/firmware/{cmd} ]'
if entry in text:
    sys.exit(0)

runcmd_re = re.compile(r'^runcmd:\s*$', re.MULTILINE)
if runcmd_re.search(text):
    text = runcmd_re.sub('runcmd:\n' + entry, text, count=1)
else:
    text = text.rstrip('\n') + f'\nruncmd:\n{entry}\n'

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
PYEOF

# =============================================================================
# Unmount
# =============================================================================
sync
sudo umount "${MOUNT_ROOT}/boot/firmware"
sudo umount "$MOUNT_ROOT"
sudo losetup -d "$LOOPDEV"
LOOPDEV=""
MOUNT_ROOT=""

echo ""
echo "=== Build complete ==="
ls -lh "$OUTPUT_IMAGE"
