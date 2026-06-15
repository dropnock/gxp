#!/usr/bin/env bash
# Generates a self-signed wildcard TLS certificate for local GXP development.
# Run once before starting the stack:
#   infra/scripts/gen-certs.sh
#
# To use a CA-signed certificate instead:
#   Place your certificate at infra/docker/certs/tls.crt
#   Place your private key  at infra/docker/certs/tls.key
#   Then restart Traefik:   docker compose restart traefik
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/../docker/certs"
ENV_FILE="${SCRIPT_DIR}/../docker/.env"

# Read GXP_DOMAIN from .env if not already set in the environment
if [[ -z "${GXP_DOMAIN:-}" && -f "$ENV_FILE" ]]; then
  GXP_DOMAIN=$(grep -E '^GXP_DOMAIN=' "$ENV_FILE" | cut -d= -f2 | tr -d '"' | tr -d "'" | head -1)
fi
DOMAIN="${GXP_DOMAIN:-gxp.localhost}"

mkdir -p "$CERTS_DIR"

if [[ -f "$CERTS_DIR/tls.crt" && -f "$CERTS_DIR/tls.key" ]]; then
  echo "Certificates already exist at $CERTS_DIR — skipping generation."
  echo "Delete tls.crt and tls.key and re-run to regenerate."
  exit 0
fi

echo "Generating self-signed wildcard certificate for *.${DOMAIN} ..."

openssl req -x509 \
  -newkey rsa:4096 \
  -sha256 \
  -days 3650 \
  -nodes \
  -keyout "${CERTS_DIR}/tls.key" \
  -out "${CERTS_DIR}/tls.crt" \
  -subj "/CN=*.${DOMAIN}/O=GXP Dev CA" \
  -addext "subjectAltName=DNS:${DOMAIN},DNS:*.${DOMAIN},DNS:localhost,IP:127.0.0.1"

chmod 600 "${CERTS_DIR}/tls.key"

echo ""
echo "Certificate generated:"
echo "  ${CERTS_DIR}/tls.crt"
echo "  ${CERTS_DIR}/tls.key"
echo ""
echo "To remove the browser 'Not secure' warning, trust the certificate:"
echo ""
echo "  Linux (system-wide):"
echo "    sudo cp ${CERTS_DIR}/tls.crt /usr/local/share/ca-certificates/gxp-dev.crt"
echo "    sudo update-ca-certificates"
echo ""
echo "  macOS:"
echo "    open ${CERTS_DIR}/tls.crt"
echo "    # Keychain Access → find 'GXP Dev CA' → Get Info → Trust → Always Trust"
echo ""
echo "  Windows:"
echo "    Double-click ${CERTS_DIR}/tls.crt → Install Certificate → Local Machine"
echo "    → Place all certificates in 'Trusted Root Certification Authorities'"
echo ""
echo "Then restart your browser."
