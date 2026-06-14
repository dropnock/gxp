#!/usr/bin/env bash
# Bootstraps the GXP Keycloak realm using the Admin REST API.
# Run once after Keycloak is up: ./bootstrap-realm.sh
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme_dev}"
REALM_FILE="$(dirname "$0")/../realm-export.json"

echo "Obtaining admin token..."
TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "ERROR: Failed to obtain admin token. Is Keycloak running at $KEYCLOAK_URL?"
  exit 1
fi

echo "Importing GXP realm..."
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$KEYCLOAK_URL/admin/realms" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary "@$REALM_FILE"

echo ""
echo "Realm import complete. Visit $KEYCLOAK_URL/admin to verify."
