import { useState } from "react";
import { Link } from "react-router-dom";
import { useDefinitions, useDeleteDefinition, useStartInstance } from "../../hooks/useWorkflow";

export function DefinitionList() {
  const { data: definitions = [], isLoading, error } = useDefinitions();
  const deleteDefinition = useDeleteDefinition();
  const startInstance = useStartInstance();
  const [starting, setStarting] = useState<string | null>(null);

  if (isLoading) return <p>Loading definitions…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  async function handleStart(id: string) {
    setStarting(id);
    try {
      await startInstance.mutateAsync({ definition_id: id });
    } finally {
      setStarting(null);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>BPMN Definitions</h2>
        <Link to="/workflows/definitions/new">
          <button style={btnStyle}>+ New Definition</button>
        </Link>
      </div>

      {definitions.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No definitions yet. Create one to get started.</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {["Name", "Process ID", "Version", "Hash", ""].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {definitions.map((d: Definition) => (
              <tr key={d.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={tdStyle}>
                  <Link to={`/workflows/definitions/${d.id}`} style={{ color: "#2563eb" }}>
                    {d.name}
                  </Link>
                </td>
                <td style={tdStyle}><code style={{ fontSize: 12 }}>{d.process_id ?? "—"}</code></td>
                <td style={tdStyle}>v{d.version}</td>
                <td style={tdStyle}><code style={{ fontSize: 11 }}>{d.xml_hash.slice(0, 8)}…</code></td>
                <td style={{ ...tdStyle, display: "flex", gap: 8 }}>
                  <Link to={`/workflows/definitions/${d.id}/edit`}>
                    <button style={smBtn}>Edit</button>
                  </Link>
                  <button
                    style={{ ...smBtn, background: "#059669", color: "#fff" }}
                    onClick={() => handleStart(d.id)}
                    disabled={starting === d.id}
                  >
                    {starting === d.id ? "Starting…" : "Run"}
                  </button>
                  <button
                    style={{ ...smBtn, background: "#dc2626", color: "#fff" }}
                    onClick={() => {
                      if (confirm(`Deactivate "${d.name}"?`)) deleteDefinition.mutate(d.id);
                    }}
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

interface Definition {
  id: string;
  name: string;
  process_id: string | null;
  version: number;
  xml_hash: string;
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
