import { useState } from "react";
import { useFailedActions } from "../hooks/useAudit";

export function FailedActionsPage() {
  const [since, setSince] = useState(() => {
    const d = new Date();
    d.setHours(d.getHours() - 24);
    return d.toISOString().slice(0, 16);
  });
  const [until, setUntil] = useState(() => new Date().toISOString().slice(0, 16));
  const [applied, setApplied] = useState({ since, until });

  const { data = [], isLoading, error } = useFailedActions(applied.since, applied.until);

  const errors = data.filter((e: FailedEvent) => e.outcome === "server_error");
  const denials = data.filter((e: FailedEvent) => e.outcome === "client_error");

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Failed &amp; Denied Actions</h2>
      <p style={{ fontSize: 13, color: "#6b7280", marginTop: -8, marginBottom: 16 }}>
        Auto-refreshes every minute. Useful for security review (NIST AU-6).
      </p>

      <div style={{ display: "flex", gap: 12, alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap" }}>
        <div>
          <label style={labelStyle}>From</label>
          <input type="datetime-local" value={since} onChange={(e) => setSince(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={labelStyle}>To</label>
          <input type="datetime-local" value={until} onChange={(e) => setUntil(e.target.value)} style={inputStyle} />
        </div>
        <button onClick={() => setApplied({ since, until })} style={btnStyle}>Apply</button>
      </div>

      {isLoading && <p>Loading…</p>}
      {error && <p style={{ color: "#dc2626" }}>Error: {String(error)}</p>}

      {!isLoading && (
        <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
          <Stat label="Server Errors (5xx)" value={errors.length} color="#dc2626" />
          <Stat label="Client Errors / Denials (4xx)" value={denials.length} color="#d97706" />
          <Stat label="Total" value={data.length} color="#6b7280" />
        </div>
      )}

      {data.length === 0 && !isLoading && (
        <p style={{ color: "#059669" }}>No failed actions in the selected time range.</p>
      )}

      {data.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Time", "Tenant", "Service", "Actor", "Action", "Outcome", "IP"].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((e: FailedEvent) => (
              <tr
                key={e.id}
                style={{
                  borderBottom: "1px solid #f3f4f6",
                  background: e.outcome === "server_error" ? "#fef2f2" : undefined,
                }}
              >
                <td style={tdStyle}>{new Date(e.event_time).toLocaleString()}</td>
                <td style={tdStyle}><code style={{ fontSize: 11 }}>{e.tenant_slug ?? "platform"}</code></td>
                <td style={tdStyle}><code style={{ fontSize: 12 }}>{e.service}</code></td>
                <td style={tdStyle}><code style={{ fontSize: 10 }}>{e.actor_id.slice(0, 8)}…</code></td>
                <td style={tdStyle}>{e.action}</td>
                <td style={tdStyle}>
                  <span style={{
                    padding: "1px 7px", borderRadius: 8, fontSize: 11, fontWeight: 600,
                    background: e.outcome === "server_error" ? "#fee2e2" : "#fef3c7",
                    color: e.outcome === "server_error" ? "#dc2626" : "#d97706",
                  }}>
                    {e.outcome}
                  </span>
                </td>
                <td style={tdStyle}><code style={{ fontSize: 11 }}>{e.ip_address}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ padding: "12px 20px", border: "1px solid #e5e7eb", borderRadius: 6, background: "#fff", minWidth: 140 }}>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{label}</div>
    </div>
  );
}

interface FailedEvent {
  id: string; event_time: string; service: string; actor_id: string;
  action: string; outcome: string; ip_address: string; tenant_slug: string | null;
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, marginBottom: 3 };
const inputStyle: React.CSSProperties = { padding: "6px 8px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 };
const btnStyle: React.CSSProperties = { padding: "7px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 12px", background: "#f9fafb", borderBottom: "1px solid #e5e7eb", fontSize: 12, fontWeight: 700 };
const tdStyle: React.CSSProperties = { padding: "8px 12px", fontSize: 13 };
