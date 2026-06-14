import { useState } from "react";
import { Link } from "react-router-dom";
import { useCases } from "../hooks/useCases";

const STATUS_COLOR: Record<string, string> = {
  open: "#059669", pending: "#d97706", on_hold: "#6b7280",
  closed: "#1d4ed8", archived: "#374151",
};

const PRIORITY_COLOR: Record<string, string> = {
  low: "#6b7280", normal: "#374151", high: "#d97706", urgent: "#dc2626",
};

export function CaseList() {
  const [statusFilter, setStatusFilter] = useState("");
  const { data: cases = [], isLoading, error } = useCases(
    statusFilter ? { status: statusFilter } : undefined
  );

  if (isLoading) return <p>Loading cases…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Cases</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={selectStyle}
          >
            <option value="">All statuses</option>
            {["open", "pending", "on_hold", "closed", "archived"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <Link to="/cases/new">
            <button style={btnStyle}>+ New Case</button>
          </Link>
        </div>
      </div>

      {cases.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No cases found.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {cases.map((c: CaseRow) => (
            <Link to={`/cases/${c.id}`} key={c.id} style={{ textDecoration: "none", color: "inherit" }}>
              <div style={{
                border: "1px solid #e5e7eb", borderRadius: 6, padding: "12px 16px",
                background: "#fff", display: "flex", alignItems: "center", gap: 16,
                cursor: "pointer",
              }}>
                <div style={{ flexShrink: 0 }}>
                  <code style={{ fontSize: 12, color: "#6b7280" }}>{c.case_number}</code>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 2 }}>{c.title}</div>
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <Chip text={c.status} color={STATUS_COLOR[c.status] ?? "#6b7280"} />
                  <Chip text={c.priority} color={PRIORITY_COLOR[c.priority] ?? "#6b7280"} />
                </div>
                <div style={{ fontSize: 12, color: "#9ca3af", flexShrink: 0 }}>
                  {new Date(c.created_at).toLocaleDateString()}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Chip({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 10,
      fontSize: 12, fontWeight: 600,
      background: color + "20", color,
    }}>
      {text}
    </span>
  );
}

interface CaseRow {
  id: string; case_number: string; title: string;
  status: string; priority: string; created_at: string;
}

const btnStyle: React.CSSProperties = {
  padding: "8px 16px", background: "#2563eb", color: "#fff",
  border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14,
};
const selectStyle: React.CSSProperties = {
  padding: "6px 10px", border: "1px solid #d1d5db",
  borderRadius: 4, fontSize: 13,
};
