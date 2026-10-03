#!/usr/bin/env bash
# Build the Lambda deployment zip for HotSeat.
# Run from the repo root:  bash deploy/package.sh
# Output: deploy/hotseat-lambda.zip  (upload this in the Lambda console)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/deploy/package"
ZIP="$ROOT/deploy/hotseat-lambda.zip"

echo "==> cleaning $PKG"
rm -rf "$PKG" "$ZIP"
mkdir -p "$PKG"

echo "==> installing dependencies (excluding boto3/botocore: already in Lambda runtime)"
"$ROOT/.venv/bin/pip" install -q \
  --target "$PKG" \
  --exclude boto3 --exclude botocore \
  -r "$ROOT/requirements.txt"

echo "==> copying src/"
cp -r "$ROOT/src" "$PKG/src"

echo "==> zipping"
cd "$PKG" && zip -qr "$ZIP" . && cd "$ROOT"

echo "==> done: $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "    Upload it at: Lambda console > your function > Code > Upload from > .zip file"
