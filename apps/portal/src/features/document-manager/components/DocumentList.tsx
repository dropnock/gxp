import { useState } from "react";
import { useDocuments, useDeleteDocument, Document } from "../hooks/useDocuments";
import { getAuthHeader } from "../../../shared/auth";
import { API_BASE } from "../../../shared/api";

interface Props {
  folderId: string | null;
}

const AV_STATUS_COLORS: Record<string, string> = {
  clean: "green",
  infected: "red",
  pending: "gray",
  scanning: "orange",
  error: "crimson",
};

export function DocumentList({ folderId }: Props) {
  const { data: docs, isLoading, error } = useDocuments(folderId);
  const deleteMutation = useDeleteDocument();
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  if (isLoading) return <p>Loading documents…</p>;
  if (error) return <p style={{ color: "red" }}>{String(error)}</p>;
  if (!docs?.length) return <p style={{ color: "#888", fontSize: 13 }}>No documents in this folder.</p>;

  function handleDownload(doc: Document) {
    const url = `${API_BASE}/api/v1/documents/${doc.id}/download`;
    // Fetch with auth header, then follow the presigned redirect
    fetch(url, { headers: getAuthHeader(), redirect: "follow" })
      .then((r) => r.url || url)
      .then((presignedUrl) => {
        const a = window.document.createElement("a");
        a.href = presignedUrl;
        a.download = doc.name;
        a.click();
      });
  }

  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          {["Name", "Type", "Tags", "Status", "Uploaded", "Actions"].map((h) => (
            <th key={h} style={thStyle}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {docs.map((doc) => (
          <tr key={doc.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
            <td style={tdStyle}>{doc.name}</td>
            <td style={{ ...tdStyle, fontSize: 12, color: "#666" }}>{doc.mime_type ?? "—"}</td>
            <td style={tdStyle}>
              {doc.tags.map((t) => (
                <span key={t} style={tagStyle}>{t}</span>
              ))}
            </td>
            <td style={tdStyle}>
              <span style={{ color: AV_STATUS_COLORS[doc.current_version_id ? "clean" : "pending"] ?? "gray", fontSize: 12 }}>
                {doc.current_version_id ? "Ready" : "Scanning…"}
              </span>
            </td>
            <td style={{ ...tdStyle, fontSize: 12 }}>{new Date(doc.created_at).toLocaleDateString()}</td>
            <td style={tdStyle}>
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  onClick={() => handleDownload(doc)}
                  disabled={!doc.current_version_id}
                  style={actionBtn}
                >
                  Download
                </button>
                {confirmDelete === doc.id ? (
                  <>
                    <button
                      onClick={() => { deleteMutation.mutate(doc.id); setConfirmDelete(null); }}
                      style={{ ...actionBtn, color: "red" }}
                    >
                      Confirm
                    </button>
                    <button onClick={() => setConfirmDelete(null)} style={actionBtn}>Cancel</button>
                  </>
                ) : (
                  <button onClick={() => setConfirmDelete(doc.id)} style={actionBtn}>Delete</button>
                )}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 14 };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "6px 12px", borderBottom: "2px solid #e0e0e0", fontWeight: 600 };
const tdStyle: React.CSSProperties = { padding: "8px 12px", verticalAlign: "middle" };
const tagStyle: React.CSSProperties = { background: "#e3f2fd", borderRadius: 4, padding: "1px 6px", fontSize: 11, marginRight: 4 };
const actionBtn: React.CSSProperties = { padding: "3px 10px", fontSize: 12, cursor: "pointer" };
