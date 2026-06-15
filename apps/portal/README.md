# apps/portal

The staff-facing React SPA. Agency employees use it to build internal applications, design and run BPMN workflows, manage cases, store and search documents, review audit logs, and (for platform super-admins) provision tenants. It is the primary human interface into the GXP platform.

---

## Key Design Decisions

- **Feature-slice layout** — each domain area (`app-builder`, `workflow-editor`, `case-manager`, `document-manager`, `audit`, `platform-admin`) is a self-contained slice with its own components, hooks, and index barrel export. Cross-cutting concerns (auth, API client, shared UI) live in `src/shared/`.
- **Keycloak OIDC with `check-sso`** — `AuthProvider` initialises `keycloak-js` with `check-sso` so users are not force-redirected before they interact. Silent SSO renewal uses `/public/silent-check-sso.html`. PKCE (S256) is enforced.
- **Tenant vs. platform routes** — `<ProtectedRoute>` guards tenant-realm routes; `<PlatformRoute>` guards the `/platform/*` super-admin routes and requires the `gxp-platform-admin` role from the `gxp-platform` Keycloak realm. Both are implemented via React Router `<Route>` wrappers.
- **TanStack Query for data fetching** — 30 s stale time, 1 retry. All API calls go through the `/api` proxy (Vite dev) or Traefik (production) so the frontend never holds a direct service URL.
- **Role-based visibility** — the audit section is only rendered for users holding `gxp-auditor` or `gxp-admin` roles; other feature flags are enforced server-side in the respective services.

---

## Structure

```
apps/portal/
├── public/
│   └── silent-check-sso.html     # Keycloak silent SSO iframe page
├── src/
│   ├── App.tsx                   # Root route declarations
│   ├── main.tsx                  # React root: AuthProvider > QueryClientProvider > BrowserRouter
│   ├── features/
│   │   ├── app-builder/          # GrapesJS drag-and-drop editor + app CRUD
│   │   ├── audit/                # Audit log viewer, summary, actor activity, failed actions
│   │   ├── case-manager/         # Case list, create, detail
│   │   ├── document-manager/     # Folder tree, upload, search, document list
│   │   ├── platform-admin/       # Tenant list, cross-tenant grants, template catalog
│   │   └── workflow-editor/
│   │       ├── bpmn/             # BPMN definition list + bpmn-js editor
│   │       ├── dmn/              # DMN definition list + dmn-js editor + evaluate UI
│   │       ├── instances/        # Instance list + detail
│   │       └── tasks/            # Task inbox + form completion
│   └── shared/
│       ├── api/index.ts          # Base fetch/Axios client, adds Authorization header
│       ├── auth/
│       │   ├── keycloak.ts       # keycloak-js singleton
│       │   ├── AuthContext.ts    # React context type (AuthState)
│       │   ├── AuthProvider.tsx  # OIDC init, token refresh, context provision
│       │   ├── ProtectedRoute.tsx# Tenant-realm route guard
│       │   └── PlatformRoute.tsx # Platform-admin route guard
│       └── components/
│           └── NavBar.tsx        # Top navigation
├── vite.config.ts                # Dev server on :3000, /api proxied to :8000
└── package.json
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| react 18 | MIT | UI framework |
| react-dom 18 | MIT | DOM renderer |
| react-router-dom 6 | MIT | Client-side routing |
| @tanstack/react-query 5 | MIT | Data fetching and cache |
| keycloak-js 26 | Apache 2.0 | Keycloak OIDC adapter |
| grapesjs 0.21 | BSD-3 | Visual app builder editor |
| bpmn-js 17 | MIT | BPMN diagram editor |
| dmn-js 16 | MIT | DMN decision table editor |
| @gxp/ts-shared | internal | GXP shared TypeScript types |

---

## Local Development

```bash
# From repo root
pnpm install
pnpm --filter @gxp/portal dev
# Portal at http://localhost:3000
# API calls proxied to http://localhost:8000 (Traefik or a local service)
```

Type-check only:
```bash
pnpm --filter @gxp/portal typecheck
```

Production build:
```bash
pnpm --filter @gxp/portal build
# Output in apps/portal/dist/
```

---

## Route Map

| Path | Guard | Feature |
|---|---|---|
| `/apps/*` | `ProtectedRoute` | App builder |
| `/workflows/*` | `ProtectedRoute` | Workflow + DMN editor, task inbox |
| `/cases/*` | `ProtectedRoute` | Case manager |
| `/documents` | `ProtectedRoute` | Document manager |
| `/audit/*` | `ProtectedRoute` (roles: `gxp-auditor`, `gxp-admin`) | Audit log |
| `/platform/tenants` | `PlatformRoute` | Tenant provisioning |
| `/platform/catalog` | `PlatformRoute` | Template catalog |
| `/platform/grants` | `PlatformRoute` | Cross-tenant grants |

---

## Configuration

The portal has no server-side env vars. Runtime configuration is baked in at build time via Vite:

| Setting | Location | Default |
|---|---|---|
| Dev server port | `vite.config.ts` | `3000` |
| API proxy target | `vite.config.ts` | `https://localhost:8000` |
| Keycloak URL | `src/shared/auth/keycloak.ts` | `https://keycloak.gxp.localhost` |

For production, set `VITE_KEYCLOAK_URL` and `VITE_API_BASE_URL` before running `pnpm build`.

---

## Security Notes

- Tenant slug is derived from the JWT `iss` claim (`gxp-{slug}`) by `AuthProvider`, not from user-supplied input.
- `PlatformRoute` checks both `tenant_slug === null` (platform realm) and the `gxp-platform-admin` role before rendering.
- The silent SSO page must be served from the same origin as the portal to avoid CORS errors with the Keycloak iframe.
