#!/usr/bin/env bash
# Verifies and loads a GXP air-gap image bundle on the target node.
# Usage: ./load-images.sh <bundle.tar.gz>
set -euo pipefail

BUNDLE="${1:-}"
if [[ -z "$BUNDLE" ]]; then
  echo "Usage: $0 <bundle.tar.gz>"
  exit 1
fi

if [[ ! -f "$BUNDLE" ]]; then
  echo "ERROR: Bundle file not found: $BUNDLE"
  exit 1
fi

SHA_FILE="${BUNDLE}.sha256"
SIG_FILE="${SHA_FILE}.asc"

echo "==> Verifying integrity..."
if [[ -f "$SIG_FILE" ]]; then
  gpg --verify "$SIG_FILE" "$SHA_FILE" || { echo "ERROR: GPG signature verification failed."; exit 1; }
  echo "GPG signature verified."
else
  echo "WARNING: No GPG signature found. Proceeding with SHA-256 check only."
fi

sha256sum --check "$SHA_FILE" || { echo "ERROR: SHA-256 checksum failed."; exit 1; }
echo "SHA-256 checksum verified."

echo "==> Loading images (this may take several minutes)..."
if command -v k3s &>/dev/null; then
  k3s ctr images import "$BUNDLE"
  echo "Images loaded into k3s containerd."
else
  docker load < "$BUNDLE"
  echo "Images loaded into Docker."
fi

echo "==> Load complete."
