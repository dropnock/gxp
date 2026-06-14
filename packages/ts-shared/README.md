# packages/ts-shared

The `@gxp/ts-shared` TypeScript package. Shared types and utilities consumed by both `apps/portal` and `apps/runtime`. It provides the canonical `AppSchema` type that the visual builder writes and the runtime reads, plus a thin OIDC client factory wrapper.

---

## Key Design Decisions

- **Schema as contract** — `AppSchema` is the single source of truth for the serialisable representation of a published app. The portal's GrapesJS integration serialises to this schema; the runtime deserialises from it. Both sides import from this package so the shape is guaranteed to match.
- **pnpm workspace dependency** — both apps declare `"@gxp/ts-shared": "workspace:*"` so local changes to this package are immediately reflected without publishing.
- **No runtime dependencies** — this package exports only types and a trivial Keycloak factory function. It adds no bundle weight beyond what TypeScript erases.

---

## Structure

```
packages/ts-shared/
├── src/
│   ├── index.ts                  # Re-exports from all sub-modules
│   ├── auth/
│   │   ├── index.ts
│   │   └── oidc-client.ts        # createKeycloakClient(config) factory
│   ├── gxp-schema/
│   │   ├── index.ts
│   │   └── app-schema.ts         # AppSchema, Page, ComponentNode, DatasourceConfig
│   └── api-types/
│       └── .gitkeep              # Placeholder for generated OpenAPI types (future)
└── tsconfig.json
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| keycloak-js 26 | Apache 2.0 | Type peer for `createKeycloakClient` return type |

`keycloak-js` is a peer dependency — consumers (`portal`, `runtime`) provide it.

---

## Local Development

This package has no standalone dev server. TypeScript compilation is validated by the consuming apps:

```bash
# Type-check from repo root
pnpm --filter @gxp/portal typecheck
pnpm --filter @gxp/runtime typecheck

# Or build the package directly (required by Turborepo before apps build)
pnpm --filter @gxp/ts-shared build
```

---

## Key Exported Symbols

### `gxp-schema`

**`AppSchema`**
```ts
interface AppSchema {
  schemaVersion: "1.0";
  appId: string;
  metadata: { name: string; description: string; version: number; theme: string };
  datasources: DatasourceConfig[];
  pages: Page[];
  permissions: { viewRoles: string[]; editRoles: string[] };
}
```

**`ComponentNode`**
```ts
interface ComponentNode {
  type: string;          // must match a key in the runtime component registry
  id: string;
  attributes: Record<string, unknown>;
  datasourceBinding: { datasourceId: string; field: string } | null;
  children: ComponentNode[];
}
```

**`DatasourceConfig`**
```ts
interface DatasourceConfig {
  id: string;
  type: "rest" | "workflow" | "document" | "case";
  config: { endpoint: string; method: "GET" | "POST" | ...; headers?: Record<string,string> };
}
```

**`Page`**
```ts
interface Page {
  id: string; name: string; route: string;
  components: ComponentNode[];
  styles: Record<string, Record<string, string>>;
}
```

### `auth`

**`createKeycloakClient(config: GxpAuthConfig): Keycloak`**

Creates and returns a `keycloak-js` instance configured with the given URL, realm, and client ID. Used by the portal's `keycloak.ts` singleton.
