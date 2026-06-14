# services/identity

Keycloak 26 realm configuration for GXP. This directory holds the static `gxp-platform` realm export (used for first-time bootstrap), a parameterised tenant realm template (used by the tenant-service provisioner for every new agency), and the bootstrap shell script.

See [ADR-003](../../docs/adr/ADR-003-keycloak-for-identity-and-access-management.md) for the IAM selection rationale.

---

## Key Design Decisions

- **Two-realm model** — the `gxp-platform` realm is for platform super-admins only; it contains service accounts for every microservice. Tenant realms (`gxp-{slug}`) are created per agency. The tenant-service's `TenantContextMiddleware` distinguishes them by the `iss` claim in the JWT.
- **Template-based tenant provisioning** — `realm-template.json` is a JSON file with `{tenant_slug}` and `{tenant_name}` placeholders. The tenant-service provisioner reads and substitutes these at provisioning time, then calls the Keycloak Admin API to create the realm. This means a new realm inherits the same OIDC settings, client definitions, roles, and MFA policies without any manual Keycloak UI work.
- **Roles defined in template** — the template includes the standard GXP realm roles (`gxp-user`, `gxp-developer`, `gxp-admin`, `gxp-auditor`, `gxp-case-worker`, `gxp-case-manager`, `gxp-approver`) so every tenant realm has them from day one.
- **Import on startup** — in Docker Compose, `realm-export.json` is mounted into the Keycloak container at `/opt/keycloak/data/import/` with the `--import-realm` flag. This means the `gxp-platform` realm is created automatically on first run.
- **Bootstrap script for CI and cold starts** — `scripts/bootstrap-realm.sh` uses the Keycloak Admin REST API directly (no Keycloak CLI dependency) so it can run from any shell environment that has `curl` and `jq`.

---

## Structure

```
services/identity/
├── realm-export.json         # gxp-platform realm: service accounts, platform admin roles
├── realm-template.json       # Tenant realm template with {tenant_slug}/{tenant_name} placeholders
└── scripts/
    └── bootstrap-realm.sh    # Bootstrap script: imports realm-export.json via Admin API
```

---

## Dependencies / Licenses

| Component | License | Purpose |
|---|---|---|
| Keycloak 26 | Apache 2.0 | OIDC / SAML identity provider |
| quay.io/keycloak/keycloak:26.0 | Apache 2.0 | Container image |
| curl + jq | curl: MIT, jq: MIT | Used in bootstrap script |

---

## Bootstrap (first-time setup)

After Keycloak is running:

```bash
KEYCLOAK_URL=http://localhost:8080 \
KEYCLOAK_ADMIN=admin \
KEYCLOAK_ADMIN_PASSWORD=changeme_dev \
services/identity/scripts/bootstrap-realm.sh
```

The script:
1. Obtains an admin token from the `master` realm.
2. `POST`s `realm-export.json` to `/admin/realms`.
3. Prints the HTTP status code and a link to the admin console.

This is idempotent if the realm already exists (Keycloak returns 409, which the script does not treat as an error in dev).

---

## Realm Contents

### `gxp-platform` (`realm-export.json`)

| Resource | Details |
|---|---|
| Roles | `gxp-platform-admin` |
| Clients | One service account per microservice (`gxp-tenant-service`, `gxp-app-service`, etc.) |
| Auth flows | Password + MFA (TOTP/WebAuthn) |
| Session settings | Short-lived access tokens (5 min), rolling refresh tokens |

### Tenant realm template (`realm-template.json`)

| Resource | Details |
|---|---|
| Realm name | `gxp-{tenant_slug}` |
| Display name | `{tenant_name}` |
| Roles | `gxp-user`, `gxp-developer`, `gxp-admin`, `gxp-auditor`, `gxp-case-worker`, `gxp-case-manager`, `gxp-approver` |
| Clients | `gxp-portal` (public, PKCE), `gxp-runtime` (public, PKCE) |
| Auth flows | MFA required for admin roles; optional for standard users (configurable) |

---

## Adding New Roles

1. Add the role to `realm-template.json` in the `roles.realm` array.
2. Update the `require_roles` calls in any Python service that needs to enforce the new role.
3. Re-run `bootstrap-realm.sh` for the platform realm if the role also applies there.
4. New tenant realms will automatically include the role on next provisioning. Existing tenant realms need a Keycloak Admin API call or a migration script to add the role retroactively.

---

## Security Notes

- Keycloak runs in `start-dev` mode in Docker Compose (HTTP, no TLS). **Use `start` with TLS in production.**
- The `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` credentials in `.env` are for the `master` realm bootstrap only — rotate them immediately in production.
- Service account client secrets (`*_SERVICE_CLIENT_SECRET`) are used for OAuth2 client credentials flow between services. Each service uses its own client secret.
- Realm tokens have a 5-minute access token lifetime. Services cache JWKS for 1 hour (`jwt_validator.py`), so key rotations take up to 1 hour to propagate.
