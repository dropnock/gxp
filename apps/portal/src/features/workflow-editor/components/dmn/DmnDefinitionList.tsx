import { Link } from "react-router-dom";
import { useDmnDefinitions } from "../../hooks/useWorkflow";

export function DmnDefinitionList() {
  const { data: definitions = [], isLoading, error } = useDmnDefinitions();

  if (isLoading) return <p>Loading DMN definitions…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>DMN Decision Tables</h2>
        <Link to="/workflows/dmn/new">
          <button style={btnStyle}>+ New Decision Table</button>
        </Link>
      </div>

      {definitions.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No decision tables yet.</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {["Name", "Decision ID", "Version", ""].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {definitions.map((d: DmnDef) => (
              <tr key={d.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={tdStyle}>
                  <Link to={`/workflows/dmn/${d.id}`} style={{ color: "#2563eb" }}>{d.name}</Link>
                </td>
                <td style={tdStyle}><code style={{ fontSize: 12 }}>{d.dmn_id ?? "—"}</code></td>
                <td style={tdStyle}>v{d.version}</td>
                <td style={{ ...tdStyle, display: "flex", gap: 8 }}>
                  <Link to={`/workflows/dmn/${d.id}/edit`}>
                    <button style={smBtn}>Edit</button>
                  </Link>
                  <Link to={`/workflows/dmn/${d.id}/evaluate`}>
                    <button style={{ ...smBtn, background: "#059669", color: "#fff" }}>Evaluate</button>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

interface DmnDef {
  id: string;
  name: string;
  dmn_id: string | null;
  version: number;
}

const btnStyle: React.CSSProperties = {
  padding: "8px 16px", background: "#2563eb", color: "#fff",
  border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14,
};
const smBtn: React.CSSProperties = {
  padding: "4px 10px", background: "#f3f4f6", border: "1px solid #d1d5db",
  borderRadius: 4, cursor: "pointer", fontSize: 12,
};
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse" };
const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "8px 12px", background: "#f9fafb",
  borderBottom: "1px solid #e5e7eb", fontSize: 13, fontWeight: 600,
};
const tdStyle: React.CSSProperties = { padding: "10px 12px", fontSize: 14 };
