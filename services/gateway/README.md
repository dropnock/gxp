# services/gateway

Traefik v3 reverse proxy configuration. Traefik is the single entry point for all HTTPS traffic to the GXP platform. Individual services register themselves via Docker labels; the gateway configuration here defines TLS, routing catch-all rules, security middleware, and rate limiting.

---

## Key Design Decisions

- **Traefik over Nginx** — Traefik v3 is chosen because it discovers services dynamically via Docker labels (no reload needed when services start/stop), supports native Let's Encrypt (not needed in air-gap but useful during development), and has first-class Kubernetes CRD support for when deploying to K8s.
- **Two-layer config** — `traefik.yml` is the static config (entry points, providers, log level). The `dynamic/` directory is file-watched for dynamic config (routers, middleware) without restart. Services add their own routers via Docker `labels`.
- **HTTP → HTTPS redirect** — the `web` entrypoint (port 80) permanently redirects all traffic to `websecure` (port 443). All browser-facing URLs use HTTPS.
- **TLS certificates** — configured in `dynamic/tls.yml`. Drop `tls.crt` and `tls.key` into `infra/docker/certs/` and Traefik hot-reloads them. If no cert files exist Traefik falls back to its auto-generated self-signed cert.
- **ForwardAuth for JWT verification** — the `jwt-auth` middleware uses Traefik's `forwardAuth` to call an `auth-checker` sidecar that validates JWTs and forwards user identity headers (`X-User-Id`, `X-User-Roles`, `X-Request-Id`) to downstream services. This is the planned production pattern; in dev, services also perform their own JWT validation via `TenantContextMiddleware`.
- **Secure-headers middleware** — `frameDeny`, `contentTypeNosniff`, `browserXssFilter`, and removal of `Server` / `X-Powered-By` headers applied to all API routes.
- **Rate limiting** — 100 req/s average, 50 burst applied at the gateway level, independent of per-service application-level limits.
- **Internal service-to-service traffic** — remains plain HTTP on the Docker `gxp-net` network. Only browser-facing traffic goes through Traefik's TLS termination.

---

## Structure

```
services/gateway/
├── traefik.yml           # Static config: entry points, HTTP→HTTPS redirect, providers
└── dynamic/
    ├── tls.yml           # TLS certificate configuration (hot-reloaded)
    ├── routers.yml       # Catch-all API router rule + secure-headers + rate-limit
    └── middlewares.yml   # jwt-auth (ForwardAuth), secure-headers, rate-limit definitions
```

---

## TLS Certificate Setup

### Self-signed (dev default)

```bash
# Generates infra/docker/certs/tls.crt and tls.key for *.GXP_DOMAIN
infra/scripts/gen-certs.sh
```

To remove the browser warning, import `infra/docker/certs/tls.crt` as a trusted CA:

- **Linux**: `sudo cp infra/docker/certs/tls.crt /usr/local/share/ca-certificates/gxp-dev.crt && sudo update-ca-certificates`
- **macOS**: `open infra/docker/certs/tls.crt` → Keychain Access → Trust → Always Trust
- **Windows**: double-click the file → Install → Local Machine → Trusted Root Certification Authorities

### CA-signed certificate (production)

```bash
# Drop your signed cert and key into the certs directory
cp /path/to/your.crt infra/docker/certs/tls.crt
cp /path/to/your.key infra/docker/certs/tls.key
# Traefik hot-reloads; no restart needed
```

---

## Configuration Knobs

### `traefik.yml`

| Setting | Current value | Notes |
|---|---|---|
| `api.dashboard` | `true` | Dashboard at `:8080` — **disable or password-protect in production** |
| `api.insecure` | `true` | Dev only |
| `entryPoints.web` | `:80` | Permanent HTTP → HTTPS redirect |
| `entryPoints.websecure` | `:443` | TLS entry point |
| `providers.docker.exposedByDefault` | `false` | Services must opt-in via labels |
| `providers.file.directory` | `/etc/traefik/dynamic` | Watched for live reload |
| `log.level` | `INFO` | |

### `dynamic/tls.yml`

Configures the default TLS certificate from `infra/docker/certs/`. Traefik hot-reloads when these files change.

### `dynamic/middlewares.yml`

| Middleware | Type | Key settings |
|---|---|---|
| `jwt-auth` | `forwardAuth` | Calls `http://auth-checker:9000/verify`; passes `X-User-Id`, `X-User-Roles`, `X-Request-Id` headers |
| `secure-headers` | `headers` | `frameDeny`, `contentTypeNosniff`, `browserXssFilter`, `referrerPolicy`, clears `Server` and `X-Powered-By` |
| `rate-limit` | `rateLimit` | 100 req/s average, burst 50 |

---

## How Services Register

Each application service in `infra/docker/docker-compose.yml` includes labels like:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.app-service.rule=Host(`api.gxp.localhost`) && PathPrefix(`/api/v1/apps`)"
  - "traefik.http.routers.app-service.entrypoints=websecure"
  - "traefik.http.routers.app-service.tls=true"
  - "traefik.http.services.app-service.loadbalancer.server.port=8000"
```

Traefik picks these up automatically when the container starts.

---

## Local Development

1. Generate certificates: `infra/scripts/gen-certs.sh`
2. Start the stack: `cd infra/docker && docker compose up -d`
3. Access the dashboard at `http://localhost:8080`

Add to `/etc/hosts`:
```
127.0.0.1  portal.gxp.localhost api.gxp.localhost keycloak.gxp.localhost runtime.gxp.localhost minio.gxp.localhost
```

---

## Production Checklist

- Set `api.insecure: false` and remove `api.dashboard: true` (or protect with Basic Auth middleware).
- Replace the `forwardAuth` address with your production auth-checker service or Traefik JWT plugin.
- Replace self-signed cert with a CA-issued wildcard certificate.
- Tune `rateLimit.average` per traffic profile.
- Restrict `providers.docker.network` to the internal GXP network.
