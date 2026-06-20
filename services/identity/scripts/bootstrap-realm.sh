#!/usr/bin/env bash
# Bootstraps the GXP Keycloak realm using the Admin REST API.
# Run once after Keycloak is healthy:
#   KEYCLOAK_URL=https://keycloak.gxp.localhost ./bootstrap-realm.sh
# Requires 127.0.0.1 keycloak.gxp.localhost in /etc/hosts.
# If using a self-signed certificate, set CURL_OPTS="--cacert infra/docker/certs/tls.crt"
# or pass CURL_OPTS="-k" to skip verification (dev only).
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-https://keycloak.gxp.localhost}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme_dev}"
REALM_FILE="$(dirname "$0")/../realm-export.json"
CURL_OPTS="${CURL_OPTS:-}"

# Derive GXP_DOMAIN from KEYCLOAK_URL if not set explicitly.
# e.g. https://keycloak.gxp.localhost → gxp.localhost
if [[ -z "${GXP_DOMAIN:-}" ]]; then
  GXP_DOMAIN="${KEYCLOAK_URL#*://keycloak.}"
fi

echo "Domain: ${GXP_DOMAIN}"
echo "Obtaining admin token from $KEYCLOAK_URL ..."

# shellcheck disable=SC2086
RESPONSE=$(curl -k -sf -L -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  $CURL_OPTS \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" 2>&1) || {
  echo "ERROR: curl failed — is Keycloak reachable at $KEYCLOAK_URL?"
  echo "  Check: docker compose ps keycloak"
  echo "  Check: ${GXP_DOMAIN%%.*} entries in /etc/hosts"
  exit 1
}

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "ERROR: No access token in response. Wrong admin credentials or Keycloak not ready."
  echo "Response: $RESPONSE"
  exit 1
fi

echo "Importing GXP realm..."

# Substitute {gxp_domain} placeholder before uploading
REALM_PAYLOAD=$(sed "s/{gxp_domain}/${GXP_DOMAIN}/g" "$REALM_FILE")

# shellcheck disable=SC2086
HTTP_CODE=$(echo "$REALM_PAYLOAD" | curl -s -L -o /dev/null -w "%{http_code}" \
  -X POST "$KEYCLOAK_URL/admin/realms" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  $CURL_OPTS \
  --data-binary @-)

if [[ "$HTTP_CODE" == "201" ]]; then
  echo "Realm import complete (HTTP $HTTP_CODE)."
elif [[ "$HTTP_CODE" == "409" ]]; then
  echo "Realm already exists (HTTP 409) — skipping import."
else
  echo "ERROR: Realm import returned HTTP $HTTP_CODE."
  exit 1
fi

echo "Done. Visit $KEYCLOAK_URL/admin to verify."
