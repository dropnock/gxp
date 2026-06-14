#!/usr/bin/env bash
# Builds and packages all GXP container images for air-gapped deployment.
# Run this on an internet-connected CI machine, then transfer the .tar.gz to the target.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERSION="${GXP_VERSION:-$(git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null || echo 'dev')}"
BUNDLE="gxp-airgap-bundle-${VERSION}.tar.gz"

echo "==> Building GXP service images (version: $VERSION)..."
docker compose -f "$REPO_ROOT/infra/docker/docker-compose.yml" build

echo "==> Pulling third-party images..."
THIRD_PARTY=(
  "quay.io/keycloak/keycloak:26.0"
  "minio/minio:RELEASE.2025-01-20T14-49-07Z"
  "valkey/valkey:8-alpine"
  "postgres:16-alpine"
  "opensearchproject/opensearch:2.18.0"
  "clamav/clamav:1.4"
  "traefik:v3.3"
  "nginx:1.27-alpine"
)
for img in "${THIRD_PARTY[@]}"; do
  docker pull "$img"
done

echo "==> Collecting all image names..."
CUSTOM_IMAGES=$(docker compose -f "$REPO_ROOT/infra/docker/docker-compose.yml" config --images)
ALL_IMAGES=("${THIRD_PARTY[@]}" $CUSTOM_IMAGES)

echo "==> Saving images to $BUNDLE..."
docker save "${ALL_IMAGES[@]}" | gzip > "$BUNDLE"

echo "==> Generating SHA-256 manifest..."
sha256sum "$BUNDLE" > "${BUNDLE}.sha256"

if command -v gpg &>/dev/null && [[ -n "${GPG_KEY_ID:-}" ]]; then
  echo "==> Signing manifest with GPG key $GPG_KEY_ID..."
  gpg --default-key "$GPG_KEY_ID" --armor --detach-sign "${BUNDLE}.sha256"
else
  echo "WARNING: GPG_KEY_ID not set — skipping signature. Set it for production bundles."
fi

echo ""
echo "Bundle ready: $BUNDLE ($(du -sh "$BUNDLE" | cut -f1))"
echo "Transfer to the target node and run: infra/scripts/load-images.sh $BUNDLE"
