#!/usr/bin/env bash
# Generates services/gateway/dynamic/routers.yml from routers.tmpl.yml
# by substituting $GXP_DOMAIN.  Run once before 'docker compose up' and
# again whenever GXP_DOMAIN changes.
#
# Usage (from repo root):
#   infra/scripts/gen-traefik-config.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../docker/.env"
TMPL="$SCRIPT_DIR/../../services/gateway/routers.tmpl.yml"
OUT="$SCRIPT_DIR/../../services/gateway/dynamic/routers.yml"

# Load .env if present so GXP_DOMAIN is available
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

GXP_DOMAIN="${GXP_DOMAIN:-gxp.localhost}"
export GXP_DOMAIN

# Only substitute $GXP_DOMAIN — leave any other $ expressions untouched
envsubst '$GXP_DOMAIN' < "$TMPL" > "$OUT"

echo "Generated routers.yml for GXP_DOMAIN=$GXP_DOMAIN"
