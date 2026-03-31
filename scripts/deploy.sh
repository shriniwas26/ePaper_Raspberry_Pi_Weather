#!/usr/bin/env bash
set -euo pipefail

RSYNC_HOST="${RSYNC_HOST:-raspi-epaper.local}"
RSYNC_USER="${RSYNC_USER:-pi}"
REMOTE_PATH="${REMOTE_PATH:-/home/pi/ePaper_Raspi}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEST="${RSYNC_USER}@${RSYNC_HOST}:${REMOTE_PATH}"

RSYNC_DIR_OPTS=( -avz --delete --exclude '__pycache__/' --exclude '*.pyc' )

sync_dir() {
  local name="$1"
  echo "deploy: rsync directory ${name}/ -> ${REMOTE_PATH}/${name}/"
  rsync "${RSYNC_DIR_OPTS[@]}" "${SRC}/${name}/" "${DEST}/${name}/"
}

sync_file() {
  local path="$1"
  echo "deploy: rsync file ${path} -> ${REMOTE_PATH}/"
  rsync -avz "${SRC}/${path}" "${DEST}/"
}

echo "deploy: source=${SRC}"
echo "deploy: destination=${DEST}"

sync_dir src
sync_dir third_party
sync_dir deploy
sync_dir scripts
sync_file pyproject.toml

if [[ -f "${SRC}/.python-version" ]]; then
  sync_file .python-version
else
  echo "deploy: skip .python-version (not in repo tree)"
fi

echo "deploy: rsync steps finished (uv.lock not copied)"

ssh "${RSYNC_USER}@${RSYNC_HOST}" \
  REMOTE_PATH="${REMOTE_PATH}" \
  bash -s <<'REMOTE'
set -euo pipefail
cd "${REMOTE_PATH}"
if ! command -v uv >/dev/null 2>&1; then
  echo 'uv is required on the Pi; install from https://docs.astral.sh/uv/' >&2
  exit 1
fi
uv sync --extra pi
bash scripts/install-service.sh
REMOTE
