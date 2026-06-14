# apps/runtime

A lightweight React application that renders published GXP apps at runtime. It is the execution environment for apps built in the portal's visual editor — it fetches a published `AppSchema` JSON from the app-service, resolves datasource bindings, and renders the component tree using a closed registry of GXP components.

End users (not developers) interact with this app when they open a published internal tool.

---

## Key Design Decisions

- **Closed component registry** — only the six components listed in `component-registry.ts` can render (`gxp-text`, `gxp-button`, `gxp-form`, `gxp-table`, `gxp-card`, `gxp-container`). No `eval()`, no dynamic imports, no arbitrary HTML injection. This is a security boundary: the builder strips unknown component types at publish time; the runtime ignores them at render time.
- **Schema-driven rendering** — `AppSchema` (from `@gxp/ts-shared`) is a serialisable JSON tree of `ComponentNode` objects. The `renderComponentTree` function walks the tree recursively and maps each `node.type` string to a React component via the registry.
- **Datasource binding** — components declare a `datasourceBinding` (`{ datasourceId, field }`). On load, the runtime fetches all datasources in parallel from their REST endpoints and injects the resolved value as the `value` prop.
- **Token sharing with the portal** — the portal writes the current Keycloak access token to `sessionStorage` under `gxp_access_token` before opening a runtime iframe. The runtime reads this key for API calls. This avoids a second Keycloak initialisation in the iframe.
- **Separate Vite app** — the runtime is its own pnpm workspace package and Vite entry so it can be deployed independently (e.g., on a separate subdomain or as an embedded iframe) without including the portal's editor libraries.

---

## Structure

```
apps/runtime/
├── src/
│   ├── main.tsx                  # React root entry
│   ├── components/               # GXP primitive components
│   │   ├── GxpButton.tsx
│   │   ├── GxpCard.tsx
│   │   ├── GxpContainer.tsx
│   │   ├── GxpForm.tsx
│   │   ├── GxpTable.tsx
│   │   └── GxpText.tsx
│   └── engine/
│       ├── component-registry.ts # type string → React component map (security boundary)
│       ├── renderer.tsx          # Recursive ComponentNode tree walker
│       └── RuntimeApp.tsx        # Root: fetches schema, datasources, renders page
└── package.json
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| react 18 | MIT | UI framework |
| react-dom 18 | MIT | DOM renderer |
| keycloak-js 26 | Apache 2.0 | OIDC (reserved — token currently read from sessionStorage) |
| @gxp/ts-shared | internal | `AppSchema`, `ComponentNode`, `DatasourceConfig` types |

---

## Local Development

```bash
pnpm install
pnpm --filter @gxp/runtime dev
# Served at http://localhost:5174 (Vite default, offset from portal)
# Open with ?appId=<uuid> query parameter
```

The app reads `?appId=<uuid>` from the URL query string and calls `GET /api/v1/apps/{appId}/published`. Ensure either the Traefik gateway or a local app-service is reachable.

Type-check:
```bash
pnpm --filter @gxp/runtime typecheck
```

---

## Key Interfaces

### `renderComponentTree(nodes, ctx)`
Recursively renders a `ComponentNode[]` tree. Each node's `type` is resolved to a component from the registry. Datasource bindings inject a `value` prop.

### `RuntimeApp`
Top-level component. Reads `?appId` from the URL, fetches the published schema, fetches all datasource endpoints in parallel, and renders the first matching page.

### Component registry keys

| Key | Component |
|---|---|
| `gxp-text` | `GxpText` |
| `gxp-button` | `GxpButton` |
| `gxp-form` | `GxpForm` |
| `gxp-table` | `GxpTable` |
| `gxp-card` | `GxpCard` |
| `gxp-container` | `GxpContainer` |

The set of valid types here **must match** `VALID_COMPONENT_TYPES` in `services/app-service/app/services/builder.py`. Both enforce the allowlist independently.

---

## Security Notes

- Unknown component types are silently dropped — the renderer returns `null` for any `node.type` not in the registry.
- Datasource `endpoint` values come from the stored `AppSchema`, which was validated and published by an admin. They are not user-supplied at runtime.
- The runtime never directly accepts or eval-uates arbitrary user input as code.
