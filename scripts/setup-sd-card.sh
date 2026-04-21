#!/bin/bash
# =============================================================================
# RaceWrangler SD Card Configurator
# =============================================================================
#
# Run this AFTER flashing the SD card with Raspberry Pi Imager.
# Copies the right files to the boot partition and injects the first-boot
# script into cloud-init (user-data), without overwriting Imager's SSH /
# hostname / password settings.
#
# USAGE:
#   Pi 5 server:
#     bash scripts/setup-sd-card.sh --type pi5 --mount /mnt/j
#
#   Pi Zero RaceSpy (start line):
#     bash scripts/setup-sd-card.sh --type pi-zero --role start --mount /mnt/k
#
#   Pi Zero RaceSpy (finish line):
#     bash scripts/setup-sd-card.sh --type pi-zero --role finish --mount /mnt/l
#
# On Windows (WSL2) the SD card boot partition shows up as J:\, K:\ etc.
# Pass it as /mnt/j, /mnt/k, etc.  Or pass the Windows path directly (J: or J:\)
# and the script will convert it.
#
# PRE-REQUISITES:
#   Pi 5:     Flash Raspberry Pi OS Lite (64-bit).
#             In Imager advanced settings: hostname=racewrangler, enable SSH.
#             Do NOT configure WiFi (wlan0 becomes the timing AP).
#   Pi Zero:  Flash Raspberry Pi OS Lite (64-bit).
#             In Imager advanced settings: hostname=racespy-start (or -finish),
#             enable SSH.
#             Do NOT configure WiFi here — the setup script does it.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

TYPE=""
MOUNT=""
ROLE="start"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --type)   TYPE="$2";  shift 2 ;;
        --mount)  MOUNT="$2"; shift 2 ;;
        --role)   ROLE="$2";  shift 2 ;;
        -h|--help)
            sed -n '3,30p' "$0"   # Print the usage block
            exit 0
            ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

[[ -n "$TYPE" ]]  || { echo "ERROR: --type pi5|pi-zero required"; exit 1; }
[[ -n "$MOUNT" ]] || { echo "ERROR: --mount <path> required";     exit 1; }
[[ "$TYPE" == "pi5" || "$TYPE" == "pi-zero" ]] \
    || { echo "ERROR: --type must be pi5 or pi-zero"; exit 1; }
[[ "$TYPE" != "pi-zero" || "$ROLE" == "start" || "$ROLE" == "finish" ]] \
    || { echo "ERROR: --role must be start or finish for pi-zero"; exit 1; }

# ---------------------------------------------------------------------------
# Normalize Windows paths (J: or J:\) to WSL2 /mnt/j
# ---------------------------------------------------------------------------

if [[ "$MOUNT" =~ ^([A-Za-z]):[\\/]?$ ]]; then
    DRIVE="${BASH_REMATCH[1],,}"   # lower-case drive letter
    MOUNT="/mnt/${DRIVE}"
    echo "Converted Windows path to WSL2 mount: $MOUNT"
fi

# ---------------------------------------------------------------------------
# Verify the mount point looks like a Raspberry Pi boot partition
# ---------------------------------------------------------------------------

if [[ ! -f "${MOUNT}/config.txt" ]]; then
    echo "ERROR: ${MOUNT}/config.txt not found."
    echo "  Is the SD card mounted? Is this the boot/firmware partition?"
    echo "  On WSL2: try /mnt/j, /mnt/k, etc."
    exit 1
fi

echo "=== RaceWrangler SD Card Configurator ==="
echo "Type  : $TYPE"
[[ "$TYPE" == "pi-zero" ]] && echo "Role  : $ROLE"
echo "Mount : $MOUNT"
echo ""

# ---------------------------------------------------------------------------
# Helper: inject runcmd entry into user-data
# ---------------------------------------------------------------------------
# Raspberry Pi Imager creates a cloud-init user-data file.  We add our
# first-boot script to the runcmd list without touching the rest of the file.
# ---------------------------------------------------------------------------

inject_runcmd() {
    local MOUNT="$1"
    local CMD="$2"           # e.g. "bash /boot/firmware/pi5-first-boot.sh"
    local USERDATA="${MOUNT}/user-data"

    if [[ ! -f "$USERDATA" ]]; then
        echo "WARNING: ${USERDATA} not found — creating minimal cloud-init file."
        cat > "$USERDATA" << 'EOF'
#cloud-config
EOF
    fi

    # Use Python to edit the YAML safely.
    python3 - "$USERDATA" "$CMD" << 'PYEOF'
import sys, re

path = sys.argv[1]
cmd  = sys.argv[2]

with open(path) as f:
    text = f.read()

# Check if this command is already present (idempotent)
if cmd in text:
    print(f"  runcmd entry already present — skipping injection")
    sys.exit(0)

# If a runcmd: block already exists, append to it.
runcmd_re = re.compile(r'^runcmd:\s*$', re.MULTILINE)
if runcmd_re.search(text):
    # Insert our entry as the first item in the existing runcmd list.
    new_text = runcmd_re.sub(f'runcmd:\n  - [ bash, /boot/firmware/{cmd} ]', text)
    with open(path, 'w') as f:
        f.write(new_text)
    print(f"  Appended to existing runcmd block.")
else:
    # No runcmd section — append one at the end.
    entry = f'\nruncmd:\n  - [ bash, /boot/firmware/{cmd} ]\n'
    with open(path, 'a') as f:
        f.write(entry)
    print(f"  Added new runcmd block.")
PYEOF
}

# ---------------------------------------------------------------------------
# Pi 5 — server
# ---------------------------------------------------------------------------

if [[ "$TYPE" == "pi5" ]]; then
    echo "--- Building source archive (if needed)..."
    ARCHIVE="${REPO_ROOT}/dist/racewrangler-server.tar.gz"

    if [[ ! -f "$ARCHIVE" ]]; then
        bash "${REPO_ROOT}/scripts/build-pi5-package.sh"
    else
        echo "  Using existing archive: $(du -sh "$ARCHIVE" | cut -f1)"
    fi

    echo ""
    echo "--- Copying files to ${MOUNT}..."
    cp "$ARCHIVE" "${MOUNT}/racewrangler-server.tar.gz"
    echo "  Copied racewrangler-server.tar.gz ($(du -sh "${MOUNT}/racewrangler-server.tar.gz" | cut -f1))"

    cp "${REPO_ROOT}/scripts/pi5-first-boot.sh" "${MOUNT}/pi5-first-boot.sh"
    echo "  Copied pi5-first-boot.sh"

    echo ""
    echo "--- Updating user-data..."
    inject_runcmd "$MOUNT" "pi5-first-boot.sh"

    echo ""
    echo "=== Pi 5 SD card ready ==="
    echo ""
    echo "  Boot partition contents:"
    ls -lh "${MOUNT}/racewrangler-server.tar.gz" "${MOUNT}/pi5-first-boot.sh"
    echo ""
    echo "  Setup log will appear at: ${MOUNT}/setup.log"
    echo "  When it says SETUP COMPLETE, SSH in and verify:"
    echo "    ssh racewrangler@racewrangler.local"
    echo "    systemctl status racewrangler"
fi

# ---------------------------------------------------------------------------
# Pi Zero — RaceSpy camera
# ---------------------------------------------------------------------------

if [[ "$TYPE" == "pi-zero" ]]; then
    echo "--- Copying files to ${MOUNT}..."
    cp "${REPO_ROOT}/racespy/racespy.py" "${MOUNT}/racespy.py"
    echo "  Copied racespy.py"

    # Write a role-stamped copy of the setup script so the CAMERA_ROLE
    # variable is already set for this specific card.
    SETUP_SRC="${REPO_ROOT}/scripts/pi-zero-first-boot.sh"
    SETUP_DST="${MOUNT}/pi-zero-first-boot.sh"
    sed "s/^CAMERA_ROLE=.*/CAMERA_ROLE=\"${ROLE}\"/" "$SETUP_SRC" > "$SETUP_DST"
    echo "  Copied pi-zero-first-boot.sh (CAMERA_ROLE=${ROLE})"

    echo ""
    echo "--- Updating user-data..."
    inject_runcmd "$MOUNT" "pi-zero-first-boot.sh"

    # Extract the camera_id that will be generated — we can't know it yet
    # (it's generated during first-boot), but remind the user where to find it.
    echo ""
    echo "=== Pi Zero (${ROLE}) SD card ready ==="
    echo ""
    echo "  Boot partition contents:"
    ls -lh "${MOUNT}/racespy.py" "${MOUNT}/pi-zero-first-boot.sh"
    echo ""
    echo "  Setup log will appear at: ${MOUNT}/racespy-setup.log"
    echo "  Camera ID assigned during first boot — visible in setup log."
    echo ""
    echo "  After boot:"
    echo "    1. Green LED blinks → scan QR code from RaceWrangler web UI"
    echo "    2. Green + Blue + Yellow solid → ARMED"
fi

echo ""
echo "Eject the SD card and boot."
