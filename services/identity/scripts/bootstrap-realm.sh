#!/usr/bin/env bash
# Bootstraps the GXP platform Keycloak realm using the Admin REST API.
# Safe to re-run — skips import if realm already exists.
#
# Usage:
#   GXP_DOMAIN=local.dropnock.com services/identity/scripts/bootstrap-realm.sh
#
# Keycloak is reachable directly on localhost:8180 (bypasses Traefik/DNS/TLS).
# Override with KEYCLOAK_URL=https://keycloak.<domain> if needed.
# For self-signed certs, set CURL_OPTS="--cacert infra/docker/certs/tls.crt"
# or CURL_OPTS="-k" to skip verification (dev only).
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8180}"
KEYCLOAK_URL="${KEYCLOAK_URL%/}"  # strip trailing slash
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme_dev}"
REALM_FILE="$(cd "$(dirname "$0")" && pwd)/../realm-export.json"
CURL_OPTS="${CURL_OPTS:-}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"  # seconds to wait for Keycloak readiness

# Derive GXP_DOMAIN from KEYCLOAK_URL if not set explicitly.
# Works when URL is https://keycloak.<domain> — strips the keycloak. prefix.
# When using the direct localhost URL (default), GXP_DOMAIN must be set explicitly.
if [[ -z "${GXP_DOMAIN:-}" ]]; then
  GXP_DOMAIN="${KEYCLOAK_URL#*://keycloak.}"
  if [[ "$GXP_DOMAIN" == "$KEYCLOAK_URL" || "$GXP_DOMAIN" == "localhost"* ]]; then
    echo "ERROR: Cannot derive GXP_DOMAIN from '$KEYCLOAK_URL'."
    echo "  Set it explicitly: GXP_DOMAIN=local.dropnock.com $0"
    exit 1
  fi
fi

echo "Keycloak URL : $KEYCLOAK_URL"
echo "Domain       : $GXP_DOMAIN"
echo "Realm file   : $REALM_FILE"
echo ""

if [[ ! -f "$REALM_FILE" ]]; then
  echo "ERROR: Realm file not found: $REALM_FILE"
  exit 1
fi

# ── Wait for Keycloak to be ready ─────────────────────────────────────────────
echo "Waiting for Keycloak to be ready (timeout: ${WAIT_TIMEOUT}s)..."
ELAPSED=0
until curl -sf -o /dev/null $CURL_OPTS "$KEYCLOAK_URL/realms/master" 2>/dev/null; do
  if [[ $ELAPSED -ge $WAIT_TIMEOUT ]]; then
    echo "ERROR: Keycloak did not become ready within ${WAIT_TIMEOUT}s."
    echo "  Check: docker compose -f infra/docker/docker-compose.yml logs --tail=50 keycloak"
    exit 1
  fi
  printf '.'
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done
echo " ready."
echo ""

# ── Obtain admin token ─────────────────────────────────────────────────────────
echo "Step 1/2 — Obtaining admin token..."

# shellcheck disable=SC2086
RESPONSE=$(curl -sf -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  $CURL_OPTS \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" 2>&1) || {
  echo "ERROR: Failed to obtain admin token."
  echo "  Response: $RESPONSE"
  echo "  Check KEYCLOAK_ADMIN / KEYCLOAK_ADMIN_PASSWORD in infra/docker/.env"
  exit 1
}

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token // empty')

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: No access token in response."
  echo "Response: $RESPONSE"
  exit 1
fi
echo "Token obtained."

# ── Import realm ───────────────────────────────────────────────────────────────
echo ""
echo "Step 2/2 — Importing gxp-platform realm..."

# Substitute {gxp_domain} placeholder before uploading.
REALM_PAYLOAD=$(sed "s/{gxp_domain}/${GXP_DOMAIN}/g" "$REALM_FILE")

TMPFILE=$(mktemp /tmp/gxp-realm-XXXXXX.json)
trap 'rm -f "$TMPFILE"' EXIT
printf '%s' "$REALM_PAYLOAD" > "$TMPFILE"

# shellcheck disable=SC2086
BODY=$(curl -s -w "\n__HTTP_CODE__:%{http_code}" \
  -X POST "$KEYCLOAK_URL/admin/realms" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  $CURL_OPTS \
  --data-binary "@$TMPFILE")

HTTP_CODE=$(printf '%s' "$BODY" | grep -o '__HTTP_CODE__:[0-9]*' | cut -d: -f2)
BODY_TEXT=$(printf '%s' "$BODY" | sed '/^__HTTP_CODE__:/d')

if [[ "$HTTP_CODE" == "201" ]]; then
  echo "Realm created (HTTP 201)."
elif [[ "$HTTP_CODE" == "409" ]]; then
  echo "Realm already exists (HTTP 409) — skipping import."
else
  echo "ERROR: Realm import returned HTTP ${HTTP_CODE:-000}."
  echo "Response: $BODY_TEXT"
  exit 1
fi

# ── Verify ─────────────────────────────────────────────────────────────────────
echo ""
echo "Verifying realm..."
# shellcheck disable=SC2086
VERIFY=$(curl -sf $CURL_OPTS "$KEYCLOAK_URL/realms/gxp-platform" 2>/dev/null) || {
  echo "ERROR: Realm endpoint not reachable after import."
  exit 1
}
REALM_NAME=$(echo "$VERIFY" | jq -r '.realm // empty')
if [[ "$REALM_NAME" != "gxp-platform" ]]; then
  echo "ERROR: Realm verification failed — got: $VERIFY"
  exit 1
fi
echo "Verified: realm '$REALM_NAME' is live."

echo ""
echo "Done."
echo "  Admin console : $KEYCLOAK_URL/admin"
echo "  Public issuer : https://keycloak.${GXP_DOMAIN}/realms/gxp-platform"
