import { useState } from "react";
import { useTenants } from "../hooks/useTenants";
import { useApproveGrant, useGrants, useRevokeGrant } from "../hooks/useGrants";

const STATUS_COLOR: Record<string, string> = {
  pending: "#d97706",
  approved: "#059669",
  revoked: "#6b7280",
  expired: "#9ca3af",
};

export function CrossTenantGrantsPage() {
  const { data: tenants = [] } = useTenants();
  const [selectedSlug, setSelectedSlug] = useState<string>("");

  const { data: grants = [], isLoading } = useGrants(selectedSlug || null);
  const approveGrant = useApproveGrant(selectedSlug);
  const revokeGrant = useRevokeGrant(selectedSlug);

  const tenantName = (id: string) =>
    tenants.find((t) => t.id === id)?.name ?? id.slice(0, 8) + "…";

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Cross-Tenant Access Grants</h1>

      <div style={{ marginBottom: 20 }}>
        <label style={{ fontSize: 13, fontWeight: 600, marginRight: 8 }}>View grants for tenant:</label>
        <select
          value={selectedSlug}
          onChange={(e) => setSelectedSlug(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 14 }}
        >
          <option value="">— select tenant —</option>
          {tenants.map((t) => (
            <option key={t.slug} value={t.slug}>{t.name} ({t.slug})</option>
          ))}
        </select>
      </div>

      {!selectedSlug && (
        <p style={{ color: "#6b7280" }}>Select a tenant to view its cross-tenant grants.</p>
      )}

      {selectedSlug && isLoading && <p>Loading grants…</p>}

      {selectedSlug && !isLoading && grants.length === 0 && (
        <p style={{ color: "#6b7280" }}>No cross-tenant grants for this tenant.</p>
      )}

      {grants.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Requesting", "Granting", "Resource Type", "Resource ID", "Permissions", "Expires", "Status", "Actions"].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grants.map((g) => (
              <tr key={g.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={tdStyle}>{tenantName(g.requesting_tenant_id)}</td>
                <td style={tdStyle}>{tenantName(g.granting_tenant_id)}</td>
                <td style={tdStyle}><code style={{ fontSize: 12 }}>{g.resource_type}</code></td>
                <td style={tdStyle}><code style={{ fontSize: 11 }}>{g.resource_id.slice(0, 8)}…</code></td>
                <td style={tdStyle}>{g.permissions.join(", ")}</td>
                <td style={tdStyle}>
                  {g.expires_at ? new Date(g.expires_at).toLocaleDateString() : "Never"}
                </td>
                <td style={tdStyle}>
                  <span style={{
                    padding: "2px 8px", borderRadius: 10, fontSize: 12, fontWeight: 600,
                    background: (STATUS_COLOR[g.status] ?? "#6b7280") + "20",
                    color: STATUS_COLOR[g.status] ?? "#6b7280",
                  }}>
                    {g.status}
                  </span>
                </td>
                <td style={{ ...tdStyle, display: "flex", gap: 6 }}>
                  {g.status === "pending" && (
                    <button
                      onClick={() => approveGrant.mutate(g.id)}
                      disabled={approveGrant.isPending}
                      style={{ ...smBtn, background: "#059669", color: "#fff" }}
                    >
                      Approve
                    </button>
                  )}
                  {(g.status === "pending" || g.status === "approved") && (
                    <button
                      onClick={() => { if (confirm("Revoke this grant?")) revokeGrant.mutate(g.id); }}
                      disabled={revokeGrant.isPending}
                      style={{ ...smBtn, background: "#dc2626", color: "#fff" }}
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "8px 12px", background: "#f9fafb",
  borderBottom: "1px solid #e5e7eb", fontSize: 13, fontWeight: 600,
};
const tdStyle: React.CSSProperties = { padding: "10px 12px", fontSize: 13 };
const smBtn: React.CSSProperties = {
  padding: "4px 10px", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12,
};
