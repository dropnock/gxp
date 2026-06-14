import { useEffect, useState } from "react";
import type { AppSchema, DatasourceConfig } from "@gxp/ts-shared/gxp-schema";
import { renderComponentTree } from "./renderer";

export function RuntimeApp() {
  const [schema, setSchema] = useState<AppSchema | null>(null);
  const [dsData, setDsData] = useState<Record<string, unknown>>({});
  const params = new URLSearchParams(window.location.search);
  const appId = params.get("appId");

  useEffect(() => {
    if (!appId) return;
    fetch(`/api/v1/apps/${appId}/published`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((v) => { if (v?.schema_json) setSchema(v.schema_json); });
  }, [appId]);

  // Fetch all datasources in parallel once schema is loaded
  useEffect(() => {
    if (!schema) return;
    Promise.all(
      schema.datasources.map((ds) =>
        fetchDatasource(ds).then((data) => ({ id: ds.id, data }))
      )
    ).then((results) => {
      const map: Record<string, unknown> = {};
      results.forEach(({ id, data }) => { map[id] = data; });
      setDsData(map);
    });
  }, [schema]);

  if (!appId) return <AppShell><p>No appId specified.</p></AppShell>;
  if (!schema) return <AppShell><p>Loading…</p></AppShell>;

  const currentPath = window.location.pathname;
  const page = schema.pages.find((p) => p.route === currentPath) ?? schema.pages[0];
  if (!page) return <AppShell><p>Page not found.</p></AppShell>;

  return (
    <AppShell>
      {renderComponentTree(page.components, { datasourceData: dsData })}
    </AppShell>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 24, maxWidth: 960, margin: "0 auto" }}>
      {children}
    </div>
  );
}

function getToken(): string {
  // In air-gapped deployment the runtime shares the Keycloak session via
  // a cookie or localStorage token set by the portal. For the MVP we read
  // a sessionStorage key that the portal sets before opening the runtime iframe.
  return sessionStorage.getItem("gxp_access_token") ?? "";
}

async function fetchDatasource(ds: DatasourceConfig): Promise<unknown> {
  try {
    const res = await fetch(ds.config.endpoint, {
      method: ds.config.method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        ...ds.config.headers,
      },
    });
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}
