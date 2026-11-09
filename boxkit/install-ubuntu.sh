#!/usr/bin/env bash
# Install Craft Boxkit on Ubuntu (headless). Safe to run without sudo except for apt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USE_SUDO="${BOXKIT_USE_SUDO:-sudo}"

need_apt=0
command -v ffmpeg >/dev/null 2>&1 || need_apt=1
command -v ffprobe >/dev/null 2>&1 || need_apt=1
command -v python3 >/dev/null 2>&1 || need_apt=1

if [[ "$need_apt" -eq 1 ]]; then
  if [[ -n "${BOXKIT_SKIP_APT:-}" ]]; then
  echo "BOXKIT_SKIP_APT is set but ffmpeg/python3 are missing." >&2
  exit 1
  fi
  echo "Installing system packages (requires apt)..."
  $USE_SUDO apt-get update -qq
  $USE_SUDO apt-get install -y ffmpeg python3 python3-pip python3-venv fontconfig
fi

VENV="${BOXKIT_VENV:-$ROOT/.venv}"
if [[ ! -d "$VENV" ]]; then
  if python3 -m venv "$VENV" 2>/dev/null; then
    :
  else
    echo "python3-venv unavailable; using virtualenv via pip --user"
    python3 -m pip install --user -U virtualenv
    python3 -m virtualenv "$VENV"
  fi
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install -U pip wheel
python -m pip install -e "$ROOT[dev]"

echo ""
echo "Boxkit installed. Activate: source $VENV/bin/activate"
echo "Try: boxkit validate $ROOT/examples/smoke.yaml"
echo "     boxkit render $ROOT/examples/smoke.yaml -o /tmp/boxkit-smoke.mp4"
