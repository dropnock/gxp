interface Column { key: string; label: string }
interface Props {
  columns?: Column[];
  data?: Record<string, unknown>[];
  value?: Record<string, unknown>[];
  [k: string]: unknown;
}

export function GxpTable({ columns = [], data, value }: Props) {
  const rows = value ?? data ?? [];
  const cols = columns.length > 0 ? columns
    : rows[0] ? Object.keys(rows[0]).map((k) => ({ key: k, label: k })) : [];

  if (cols.length === 0) {
    return <p style={{ color: "#9ca3af", fontSize: 13 }}>Table: no data</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c.key} style={{ textAlign: "left", padding: "8px 12px", background: "#f9fafb", borderBottom: "1px solid #e5e7eb", fontWeight: 600 }}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid #e5e7eb" }}>
              {cols.map((c) => (
                <td key={c.key} style={{ padding: "10px 12px" }}>
                  {String(row[c.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={cols.length} style={{ padding: 16, textAlign: "center", color: "#9ca3af" }}>
                No data
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
