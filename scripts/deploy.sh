#!/usr/bin/env bash
set -euo pipefail

RSYNC_HOST="${RSYNC_HOST:-raspi-epaper.local}"
RSYNC_USER="${RSYNC_USER:-pi}"
REMOTE_PATH="${REMOTE_PATH:-/home/pi/ePaper_Raspi}"
INSTALL_SYSTEMD="${INSTALL_SYSTEMD:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "${SCRIPT_DIR}/.." && pwd)"

rsync -avz --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'out/' \
  "${SRC}/" "${RSYNC_USER}@${RSYNC_HOST}:${REMOTE_PATH}/"

ssh "${RSYNC_USER}@${RSYNC_HOST}" bash -s <<REMOTE
set -euo pipefail
cd '${REMOTE_PATH}'
if ! command -v uv >/dev/null 2>&1; then
  echo 'uv is required on the Pi; install from https://docs.astral.sh/uv/' >&2
  exit 1
fi
uv sync --frozen --extra pi
if [[ '${INSTALL_SYSTEMD}' == '1' ]]; then
  sudo cp deploy/weather-epaper.service /etc/systemd/system/weather-epaper.service
  sudo systemctl daemon-reload
  sudo systemctl enable weather-epaper.service
fi
sudo systemctl restart weather-epaper.service
REMOTE
