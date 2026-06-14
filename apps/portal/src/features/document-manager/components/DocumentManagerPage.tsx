import { useState } from "react";
import { FolderTree } from "./FolderTree";
import { DocumentList } from "./DocumentList";
import { DocumentUpload } from "./DocumentUpload";
import { DocumentSearch } from "./DocumentSearch";

export function DocumentManagerPage() {
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 48px)" }}>
      <FolderTree selectedFolderId={selectedFolderId} onSelect={setSelectedFolderId} />

      <div style={{ flex: 1, padding: 24, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h1 style={{ margin: 0, fontSize: 22 }}>Documents</h1>
          <button onClick={() => setShowUpload(!showUpload)} style={uploadBtnStyle}>
            {showUpload ? "Cancel" : "Upload"}
          </button>
        </div>

        <DocumentSearch />

        {showUpload && (
          <div style={{ marginBottom: 24 }}>
            <DocumentUpload
              folderId={selectedFolderId}
              onUploaded={() => setShowUpload(false)}
            />
          </div>
        )}

        <DocumentList folderId={selectedFolderId} />
      </div>
    </div>
  );
}

const uploadBtnStyle: React.CSSProperties = {
  padding: "6px 18px",
  background: "#1976d2",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 14,
};
