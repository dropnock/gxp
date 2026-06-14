import { useState } from "react";
import { Link } from "react-router-dom";
import { useCancelInstance, useInstances } from "../../hooks/useWorkflow";

const STATUS_COLORS: Record<string, string> = {
  running:   "#d97706",
  waiting:   "#2563eb",
  completed: "#059669",
  cancelled: "#6b7280",
  error:     "#dc2626",
};

export function InstanceList() {
  const [statusFilter, setStatusFilter] = useState("");
  const { data: instances = [], isLoading, error } = useInstances(statusFilter || undefined);
  const cancelInstance = useCancelInstance();

  if (isLoading) return <p>Loading instances…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Workflow Instances</h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 }}
        >
          <option value="">All statuses</option>
          <option value="running">Running</option>
          <option value="waiting">Waiting</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {instances.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No instances found.</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {["ID", "Status", "Started By", "Started At", "Completed At", ""].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {instances.map((inst: Instance) => (
              <tr key={inst.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={tdStyle}>
                  <Link to={`/workflows/instances/${inst.id}`} style={{ color: "#2563eb", fontSize: 12, fontFamily: "monospace" }}>
                    {inst.id.slice(0, 8)}…
                  </Link>
                </td>
                <td style={tdStyle}>
                  <span style={{
                    display: "inline-block", padding: "2px 8px",
                    borderRadius: 10, fontSize: 12,
                    background: STATUS_COLORS[inst.status] + "20",
                    color: STATUS_COLORS[inst.status],
                    fontWeight: 600,
                  }}>
                    {inst.status}
                  </span>
                </td>
                <td style={tdStyle}><code style={{ fontSize: 12 }}>{inst.started_by.slice(0, 16)}…</code></td>
                <td style={tdStyle}>{new Date(inst.started_at).toLocaleString()}</td>
                <td style={tdStyle}>{inst.completed_at ? new Date(inst.completed_at).toLocaleString() : "—"}</td>
                <td style={tdStyle}>
                  {(inst.status === "running" || inst.status === "waiting") && (
                    <button
                      style={{ padding: "4px 10px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}
                      onClick={() => {
                        if (confirm("Cancel this instance?")) cancelInstance.mutate(inst.id);
                      }}
                    >
                      Cancel
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

interface Instance {
  id: string;
  status: string;
  started_by: string;
  started_at: string;
  completed_at: string | null;
}

const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse" };
const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "8px 12px", background: "#f9fafb",
  borderBottom: "1px solid #e5e7eb", fontSize: 13, fontWeight: 600,
};
const tdStyle: React.CSSProperties = { padding: "10px 12px", fontSize: 14 };
