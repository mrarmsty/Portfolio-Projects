#!/usr/bin/env bash
# Builds the GitHub-ready zip of the repository (excludes caches and the pickle working file).
set -e
cd "$(dirname "$0")/.."
OUT=${1:-../diabetes-readmission-powerbi.zip}
rm -f "$OUT"
zip -qr "$OUT" . -x "*.pkl" "*/.pbi/cache.abf" "*/.pbi/localSettings.json" "*__pycache__*" "*.DS_Store"
echo "packaged -> $OUT"
