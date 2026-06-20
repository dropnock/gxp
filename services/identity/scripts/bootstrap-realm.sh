#!/usr/bin/env bash
# Bootstraps the GXP Keycloak realm using the Admin REST API.
# Run once after Keycloak is healthy:
#   KEYCLOAK_URL=https://keycloak.gxp.localhost ./bootstrap-realm.sh
# Requires 127.0.0.1 keycloak.gxp.localhost in /etc/hosts.
# If using a self-signed certificate, set CURL_OPTS="--cacert infra/docker/certs/tls.crt"
# or pass CURL_OPTS="-k" to skip verification (dev only).
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8180}"
KEYCLOAK_URL="${KEYCLOAK_URL%/}"  # strip trailing slash
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme_dev}"
REALM_FILE="$(cd "$(dirname "$0")" && pwd)/../realm-export.json"
CURL_OPTS="${CURL_OPTS:--k}"  # default to -k for dev self-signed certs

# Derive GXP_DOMAIN from KEYCLOAK_URL if not set explicitly.
# Works when URL is https://keycloak.<domain> — strips the keycloak. prefix.
# When using the direct localhost URL (default), GXP_DOMAIN must be set explicitly.
if [[ -z "${GXP_DOMAIN:-}" ]]; then
  GXP_DOMAIN="${KEYCLOAK_URL#*://keycloak.}"
  if [[ "$GXP_DOMAIN" == "$KEYCLOAK_URL"* || "$GXP_DOMAIN" == "localhost"* ]]; then
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

echo "Step 1/2 — Obtaining admin token..."

# shellcheck disable=SC2086
RESPONSE=$(curl -sf -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  $CURL_OPTS \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" 2>&1) || {
  echo "ERROR: curl failed — is Keycloak reachable at $KEYCLOAK_URL?"
  echo "  Check: docker compose ps keycloak"
  echo "  Check: /etc/hosts has an entry for keycloak.${GXP_DOMAIN}"
  exit 1
}

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "ERROR: No access token in response. Wrong admin credentials or Keycloak not ready."
  echo "Response: $RESPONSE"
  exit 1
fi
echo "Token obtained."

echo ""
echo "Step 2/2 — Importing gxp-platform realm to $KEYCLOAK_URL/admin/realms ..."

# Substitute {gxp_domain} placeholder before uploading.
REALM_PAYLOAD=$(sed "s/{gxp_domain}/${GXP_DOMAIN}/g" "$REALM_FILE")

# Write to a temp file so curl reads the full body (avoids stdin-consumed-by-redirect issues).
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
  echo "Realm imported successfully (HTTP 201)."
elif [[ "$HTTP_CODE" == "409" ]]; then
  echo "Realm already exists (HTTP 409) — skipping import."
else
  echo "ERROR: Realm import returned HTTP ${HTTP_CODE:-000}."
  echo "Response body: $BODY_TEXT"
  exit 1
fi

echo ""
echo "Done. Admin console: $KEYCLOAK_URL/admin"
