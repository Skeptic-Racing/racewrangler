#!/bin/bash
# =============================================================================
# RaceWrangler Pi 5 Deploy Script
# =============================================================================
# Builds the frontend, uploads changed backend + frontend files to the Pi 5,
# and restarts the racewrangler service.
#
# USAGE:
#   bash scripts/deploy-pi5.sh [--host racewrangler] [--skip-frontend]
#
# Requires SSH access to the Pi 5 (configured in ~/.ssh/config as 'racewrangler').
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_HOST="racewrangler"
REMOTE_DIR="/opt/racewrangler"
SKIP_FRONTEND=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)         SSH_HOST="$2"; shift 2 ;;
        --skip-frontend) SKIP_FRONTEND=1; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

log() { echo "==> $*"; }
remote() { ssh "$SSH_HOST" "$@"; }

log "Deploying to $SSH_HOST:$REMOTE_DIR"

# ---------------------------------------------------------------------------
# 1. Build frontend
# ---------------------------------------------------------------------------

if [[ $SKIP_FRONTEND -eq 0 ]]; then
    log "Building frontend..."
    cd "${REPO_ROOT}/frontend"
    npm run build
    log "Frontend built."
else
    log "Skipping frontend build (--skip-frontend)."
fi

cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# 2. Upload backend files
# ---------------------------------------------------------------------------

log "Uploading backend..."
rsync -az --delete \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="*.db" \
    --exclude=".venv" \
    --exclude="dev_data" \
    "${REPO_ROOT}/backend/" \
    "${SSH_HOST}:/tmp/rw_backend/"

remote "sudo rsync -az --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.db' \
    --exclude='.venv' \
    /tmp/rw_backend/ ${REMOTE_DIR}/backend/ && \
    sudo chown -R racewrangler:racewrangler ${REMOTE_DIR}/backend"

log "Backend uploaded."

# ---------------------------------------------------------------------------
# 3. Upload frontend dist
# ---------------------------------------------------------------------------

if [[ $SKIP_FRONTEND -eq 0 ]]; then
    log "Uploading frontend dist..."
    rsync -az --delete \
        "${REPO_ROOT}/frontend/dist/" \
        "${SSH_HOST}:/tmp/rw_frontend_dist/"

    remote "sudo rsync -az --delete \
        /tmp/rw_frontend_dist/ ${REMOTE_DIR}/frontend/dist/ && \
        sudo chown -R racewrangler:racewrangler ${REMOTE_DIR}/frontend/dist"

    log "Frontend uploaded."
fi

# ---------------------------------------------------------------------------
# 4. Restart service
# ---------------------------------------------------------------------------

log "Restarting racewrangler service..."
remote "sudo systemctl restart racewrangler"
sleep 3
remote "systemctl status racewrangler --no-pager | tail -5"

log "Deploy complete. Browse to http://racewrangler/ to verify."
