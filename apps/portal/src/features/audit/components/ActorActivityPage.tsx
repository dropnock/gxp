import { useState } from "react";
import { useActorActivity } from "../hooks/useAudit";

export function ActorActivityPage() {
  const [actorInput, setActorInput] = useState("");
  const [actorId, setActorId] = useState<string | null>(null);
  const [since, setSince] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 16);
  });
  const [until, setUntil] = useState(() => new Date().toISOString().slice(0, 16));
  const [applied, setApplied] = useState<{ actorId: string | null; since: string; until: string }>({
    actorId: null, since, until,
  });

  const { data, isLoading, error } = useActorActivity(applied.actorId, applied.since, applied.until);

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Actor Activity</h2>

      <div style={{ display: "flex", gap: 12, alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 200px" }}>
          <label style={labelStyle}>Actor ID (Keycloak user UUID)</label>
          <input
            value={actorInput}
            onChange={(e) => setActorInput(e.target.value)}
            placeholder="e.g. 550e8400-e29b-41d4-a716-…"
            style={{ ...inputStyle, width: "100%" }}
          />
        </div>
        <div>
          <label style={labelStyle}>From</label>
          <input type="datetime-local" value={since} onChange={(e) => setSince(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={labelStyle}>To</label>
          <input type="datetime-local" value={until} onChange={(e) => setUntil(e.target.value)} style={inputStyle} />
        </div>
        <button
          onClick={() => setApplied({ actorId: actorInput.trim() || null, since, until })}
          style={btnStyle}
        >
          Search
        </button>
      </div>

      {!applied.actorId && <p style={{ color: "#6b7280" }}>Enter an actor ID to search.</p>}
      {applied.actorId && isLoading && <p>Loading…</p>}
      {applied.actorId && error && <p style={{ color: "#dc2626" }}>Error: {String(error)}</p>}

      {data && (
        <>
          <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
            {data.count} event{data.count !== 1 ? "s" : ""} for actor <code>{data.actor_id}</code>
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Time", "Service", "Action", "Resource", "Outcome", "IP"].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.events.map((e: Event) => (
                <tr key={e.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={tdStyle}>{new Date(e.event_time).toLocaleString()}</td>
                  <td style={tdStyle}><code style={{ fontSize: 12 }}>{e.service}</code></td>
                  <td style={tdStyle}>{e.action}</td>
                  <td style={tdStyle}>
                    {e.resource_type && <span><code style={{ fontSize: 11 }}>{e.resource_type}</code> </span>}
                    {e.resource_id && <code style={{ fontSize: 10 }}>{e.resource_id.slice(0, 8)}…</code>}
                  </td>
                  <td style={tdStyle}>
                    <span style={{
                      padding: "1px 6px", borderRadius: 8, fontSize: 11,
                      background: e.outcome === "success" ? "#d1fae5" : "#fee2e2",
                      color: e.outcome === "success" ? "#059669" : "#dc2626",
                    }}>
                      {e.outcome}
                    </span>
                  </td>
                  <td style={tdStyle}><code style={{ fontSize: 11 }}>{e.ip_address}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

interface Event {
  id: string; event_time: string; service: string; action: string;
  resource_type: string; resource_id: string; outcome: string; ip_address: string;
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, marginBottom: 3 };
const inputStyle: React.CSSProperties = { padding: "6px 8px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 };
const btnStyle: React.CSSProperties = { padding: "7px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 12px", background: "#f9fafb", borderBottom: "1px solid #e5e7eb", fontSize: 12, fontWeight: 700 };
const tdStyle: React.CSSProperties = { padding: "8px 12px", fontSize: 13 };
