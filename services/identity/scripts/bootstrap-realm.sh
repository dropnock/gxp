#!/usr/bin/env bash
# Bootstraps the GXP Keycloak realm using the Admin REST API.
# Run once after Keycloak is healthy:
#   KEYCLOAK_URL=http://keycloak.gxp.localhost ./bootstrap-realm.sh
# Requires 127.0.0.1 keycloak.gxp.localhost in /etc/hosts.
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak.gxp.localhost}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme_dev}"
REALM_FILE="$(dirname "$0")/../realm-export.json"

echo "Obtaining admin token from $KEYCLOAK_URL ..."
RESPONSE=$(curl -sf -L -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" 2>&1) || {
  echo "ERROR: curl failed — is Keycloak reachable at $KEYCLOAK_URL?"
  echo "  Check: docker compose ps keycloak"
  echo "  Check: 127.0.0.1 keycloak.gxp.localhost is in /etc/hosts"
  exit 1
}

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "ERROR: No access token in response. Wrong admin credentials or Keycloak not ready."
  echo "Response: $RESPONSE"
  exit 1
fi

echo "Importing GXP realm..."
HTTP_CODE=$(curl -s -L -o /dev/null -w "%{http_code}" \
  -X POST "$KEYCLOAK_URL/admin/realms" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary "@$REALM_FILE")

if [[ "$HTTP_CODE" == "201" ]]; then
  echo "Realm import complete (HTTP $HTTP_CODE)."
elif [[ "$HTTP_CODE" == "409" ]]; then
  echo "Realm already exists (HTTP 409) — skipping import."
else
  echo "ERROR: Realm import returned HTTP $HTTP_CODE."
  exit 1
fi

echo "Done. Visit $KEYCLOAK_URL/admin to verify."
