import { useState } from "react";
import { useAuditSummary } from "../hooks/useAudit";

const OUTCOME_COLOR: Record<string, string> = {
  success: "#059669",
  client_error: "#d97706",
  server_error: "#dc2626",
};

export function AuditSummaryPage() {
  const [since, setSince] = useState(() => {
    const d = new Date();
    d.setHours(d.getHours() - 24);
    return d.toISOString().slice(0, 16);
  });
  const [until, setUntil] = useState(() => new Date().toISOString().slice(0, 16));
  const [applied, setApplied] = useState({ since, until });

  const { data, isLoading, error } = useAuditSummary(applied.since, applied.until);

  const maxCount = data ? Math.max(1, ...data.rows.map((r: Row) => r.count)) : 1;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Activity Summary</h2>

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

      {data && (
        <>
          <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
            {data.rows.length} event type{data.rows.length !== 1 ? "s" : ""} recorded
            {data.tenant_slug ? ` for tenant ${data.tenant_slug}` : " (all tenants)"}
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Service", "Event Type", "Outcome", "Count", "Volume"].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r: Row, i: number) => (
                <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={tdStyle}><code style={{ fontSize: 12 }}>{r.service}</code></td>
                  <td style={tdStyle}><code style={{ fontSize: 12 }}>{r.event_type}</code></td>
                  <td style={tdStyle}>
                    <span style={{
                      padding: "2px 7px", borderRadius: 10, fontSize: 11, fontWeight: 600,
                      background: (OUTCOME_COLOR[r.outcome] ?? "#6b7280") + "20",
                      color: OUTCOME_COLOR[r.outcome] ?? "#6b7280",
                    }}>
                      {r.outcome}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{r.count.toLocaleString()}</td>
                  <td style={{ ...tdStyle, width: 200 }}>
                    <div style={{
                      height: 12, borderRadius: 4,
                      background: OUTCOME_COLOR[r.outcome] ?? "#6b7280",
                      width: `${Math.round((r.count / maxCount) * 100)}%`,
                      minWidth: 2,
                    }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

interface Row { service: string; event_type: string; outcome: string; count: number }

const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, marginBottom: 3 };
const inputStyle: React.CSSProperties = { padding: "6px 8px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 };
const btnStyle: React.CSSProperties = { padding: "7px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 12px", background: "#f9fafb", borderBottom: "1px solid #e5e7eb", fontSize: 12, fontWeight: 700 };
const tdStyle: React.CSSProperties = { padding: "9px 12px", fontSize: 13 };
