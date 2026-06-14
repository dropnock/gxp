/**
 * Keycloak singleton — one instance per browser tab.
 *
 * Realm resolution:
 *   - Platform admin portal (platform.portal.gxp.*) → gxp-platform realm
 *   - Agency portal (dot.portal.gxp.*)             → gxp-dot realm
 *   - Dev override: VITE_KEYCLOAK_REALM env var
 *
 * Tokens are kept in memory by keycloak-js (never localStorage).
 */
import Keycloak from "keycloak-js";

function resolveRealm(): string {
  // Dev/test override
  const envRealm = import.meta.env.VITE_KEYCLOAK_REALM as string | undefined;
  if (envRealm) return envRealm;

  // Production: infer from subdomain
  const hostname = window.location.hostname;
  const parts = hostname.split(".");

  // e.g. platform.portal.gxp.internal → parts[0] = 'platform'
  if (parts[0] === "platform") {
    return "gxp-platform";
  }

  // e.g. dot.portal.gxp.internal → parts[0] = 'dot'
  // Validate it looks like a slug (alphanumeric + underscore)
  if (/^[a-z0-9][a-z0-9_]*$/.test(parts[0]) && parts.length > 1) {
    return `gxp-${parts[0]}`;
  }

  // Fallback for local dev without VITE_KEYCLOAK_REALM set
  return "gxp-platform";
}

const keycloakUrl = import.meta.env.VITE_KEYCLOAK_URL ?? "http://keycloak.gxp.localhost";

export const keycloak = new Keycloak({
  url: keycloakUrl,
  realm: resolveRealm(),
  clientId: resolveRealm() === "gxp-platform" ? "gxp-platform-portal" : "gxp-portal",
});

export function getToken(): string | undefined {
  return keycloak.token;
}

export function getAuthHeader(): Record<string, string> {
  const token = keycloak.token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
