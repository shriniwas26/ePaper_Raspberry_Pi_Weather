#!/usr/bin/env bash
# Started by systemd (non-interactive); finds `uv` like an SSH login would not reliably do.
set -euo pipefail

export HOME="${HOME:-/home/pi}"
export USER="${USER:-pi}"
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

uv_bin="$(command -v uv 2>/dev/null || true)"
if [[ -z "${uv_bin}" && -x "${HOME}/.local/bin/uv" ]]; then
  uv_bin="${HOME}/.local/bin/uv"
fi
if [[ -z "${uv_bin}" ]]; then
  echo "uv not found (tried PATH and ${HOME}/.local/bin/uv). Install from https://docs.astral.sh/uv/" >&2
  exit 1
fi

"${uv_bin}" sync --extra pi
exec "${ROOT}/.venv/bin/python" -m weather_epaper
