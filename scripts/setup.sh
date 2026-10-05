#!/usr/bin/env bash
# The pipeline environment, isolated and pinned: .venv-pipeline with the precompute and dev requirements. The API
# environment (.venv, requirements-api.txt) is created only when app/ is active. Idempotent; no global installs.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"

mkvenv() { [ -d "$1" ] || "$PY" -m venv "$1"; }
venvpy() { local p="$1/bin/python"; [ -x "$p" ] || p="$1/Scripts/python.exe"; echo "$p"; }

echo "[setup] .venv-pipeline (the offline lane)"
mkvenv .venv-pipeline
VP="$(venvpy .venv-pipeline)"
"$VP" -m pip install --upgrade pip -q
"$VP" -m pip install -q -r requirements-precompute.txt -r requirements-dev.txt
echo "[setup] .venv-pipeline ready"

if [ -f app/main.py ] && grep -qvE '^\s*#|^\s*$' requirements-api.txt 2>/dev/null; then
  echo "[setup] .venv (the API, app/ is active)"
  mkvenv .venv
  VR="$(venvpy .venv)"
  "$VR" -m pip install --upgrade pip -q
  "$VR" -m pip install -q -r requirements-api.txt
  echo "[setup] .venv ready"
fi

echo "[setup] done. Next: ./scripts/precompute.sh (the canonical bake), then cd frontend && npm ci && npm run dev"
