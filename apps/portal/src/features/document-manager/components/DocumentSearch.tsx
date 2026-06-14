import { useState } from "react";
import { useDocumentSearch } from "../hooks/useDocuments";

export function DocumentSearch() {
  const [query, setQuery] = useState("");
  const { data: results, isFetching } = useDocumentSearch(query);

  return (
    <div style={{ marginBottom: 16 }}>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search documents…"
        style={{ width: "100%", padding: "8px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #ccc" }}
      />

      {isFetching && query.length > 1 && (
        <p style={{ fontSize: 12, color: "#666", margin: "4px 0" }}>Searching…</p>
      )}

      {results && results.length > 0 && (
        <div style={resultsStyle}>
          {(results as Array<{ document_id: string; name: string; score: number; mime_type?: string }>).map((r) => (
            <div key={r.document_id} style={resultItemStyle}>
              <span style={{ fontWeight: 500 }}>{r.name}</span>
              <span style={{ fontSize: 12, color: "#888", marginLeft: 8 }}>{r.mime_type}</span>
              <span style={{ fontSize: 11, color: "#aaa", float: "right" }}>score: {r.score?.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}

      {results?.length === 0 && query.length > 1 && !isFetching && (
        <p style={{ fontSize: 12, color: "#888", margin: "4px 0" }}>No results for "{query}"</p>
      )}
    </div>
  );
}

const resultsStyle: React.CSSProperties = {
  border: "1px solid #e0e0e0",
  borderRadius: 4,
  marginTop: 4,
  maxHeight: 240,
  overflowY: "auto",
};
const resultItemStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #f0f0f0",
  fontSize: 14,
};
