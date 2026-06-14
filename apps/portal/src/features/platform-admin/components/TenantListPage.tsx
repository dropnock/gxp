import { useState } from "react";
import { useTenants, useSuspendTenant } from "../hooks/useTenants";
import { TenantCreateForm } from "./TenantCreateForm";

export function TenantListPage() {
  const { data: tenants, isLoading, error } = useTenants();
  const suspendMutation = useSuspendTenant();
  const [showCreate, setShowCreate] = useState(false);

  if (isLoading) return <p>Loading tenants…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Tenants</h1>
        <button onClick={() => setShowCreate(true)}>+ New Tenant</button>
      </div>

      {showCreate && (
        <TenantCreateForm onSuccess={() => setShowCreate(false)} onCancel={() => setShowCreate(false)} />
      )}

      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
        <thead>
          <tr>
            {["Slug", "Name", "Realm", "Status", "Created", "Actions"].map((h) => (
              <th key={h} style={{ textAlign: "left", padding: "8px 12px", borderBottom: "1px solid #ccc" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tenants?.map((t) => (
            <tr key={t.id}>
              <td style={{ padding: "8px 12px" }}><code>{t.slug}</code></td>
              <td style={{ padding: "8px 12px" }}>{t.name}</td>
              <td style={{ padding: "8px 12px" }}><code>{t.keycloak_realm}</code></td>
              <td style={{ padding: "8px 12px" }}>
                <span style={{ color: t.status === "active" ? "green" : "orange" }}>{t.status}</span>
              </td>
              <td style={{ padding: "8px 12px" }}>{new Date(t.created_at).toLocaleDateString()}</td>
              <td style={{ padding: "8px 12px" }}>
                {t.status === "active" && (
                  <button
                    onClick={() => suspendMutation.mutate(t.slug)}
                    disabled={suspendMutation.isPending}
                  >
                    Suspend
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
