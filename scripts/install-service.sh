#!/usr/bin/env bash
set -euo pipefail

# Run on the Raspberry Pi after the project is on disk (e.g. under /home/pi/ePaper_Raspi).
# Installs deploy/weather-epaper.service, reloads systemd, enables and starts the unit.

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./scripts/install-service.sh"
  echo "Requires sudo for installing the unit under /etc/systemd/system/."
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
UNIT_SRC="${ROOT}/deploy/weather-epaper.service"

if [[ ! -f "${UNIT_SRC}" ]]; then
  echo "Missing unit file: ${UNIT_SRC}" >&2
  exit 1
fi

if [[ $(id -u) -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

echo "install-service: project root=${ROOT}"
echo "install-service: copying unit ${UNIT_SRC} -> /etc/systemd/system/weather-epaper.service"
${SUDO} cp "${UNIT_SRC}" /etc/systemd/system/weather-epaper.service

echo "install-service: systemctl daemon-reload"
${SUDO} systemctl daemon-reload

echo "install-service: systemctl enable weather-epaper.service"
${SUDO} systemctl enable weather-epaper.service

echo "install-service: systemctl restart weather-epaper.service"
${SUDO} systemctl restart weather-epaper.service

echo "install-service: done (unit installed and service restarted)"
echo "install-service: check status with: ${SUDO} systemctl status weather-epaper.service"
