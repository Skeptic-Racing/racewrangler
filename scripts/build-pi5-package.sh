#!/bin/bash
# =============================================================================
# RaceWrangler Pi 5 Package Builder
# =============================================================================
# Run this on your dev machine BEFORE flashing the SD card.
# Creates racewrangler-server.tar.gz (~5 MB) — copy it to the SD card's boot partition.
#
# The package contains the RaceWrangler source code only.
# Python packages and PaddleOCR are installed from the internet at first-boot
# (apt + pip — same internet requirement as before, but now no GitHub needed).
#
# USAGE:
#   bash scripts/build-pi5-package.sh
#   Then copy dist/racewrangler-server.tar.gz to J:\ (the boot partition).
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
ARCHIVE="${DIST_DIR}/racewrangler-server.tar.gz"

echo "=== RaceWrangler Pi 5 Package Builder ==="
echo "Output: $ARCHIVE"
echo ""

[ -f "${REPO_ROOT}/backend/requirements.txt" ] \
    || { echo "ERROR: Run this from the racewrangler repo root or scripts/ directory."; exit 1; }

mkdir -p "$DIST_DIR"
rm -f "$ARCHIVE"

echo "Bundling source code..."
tar -czf "$ARCHIVE" \
    -C "$REPO_ROOT" \
    --exclude="backend/__pycache__" \
    --exclude="backend/*.db" \
    --exclude="backend/.venv" \
    --exclude="ocr_poc/__pycache__" \
    --exclude="ocr_poc/.venv" \
    backend/ \
    ocr_poc/

ARCHIVE_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo ""
echo "=== Done ==="
echo "Archive : $ARCHIVE"
echo "Size    : $ARCHIVE_SIZE"
echo ""
echo "Copy these files to J:\\ (the Pi 5 boot partition):"
echo "  $ARCHIVE"
echo "  scripts/pi5-first-boot.sh"
echo ""
echo "For each Pi Zero RaceSpy SD card (K:\\, L:\\, etc.):"
echo "  racespy/racespy.py"
echo "  scripts/pi-zero-first-boot.sh"
