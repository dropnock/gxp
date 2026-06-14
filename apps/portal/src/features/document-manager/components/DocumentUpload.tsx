import { useRef, useState } from "react";
import { useUploadDocument } from "../hooks/useDocuments";

interface Props {
  folderId: string | null;
  onUploaded: () => void;
}

export function DocumentUpload({ folderId, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const upload = useUploadDocument();

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return;
    for (const file of Array.from(files)) {
      await upload.mutateAsync({
        file,
        folderId,
        description: description || undefined,
        tags: tags ? tags.split(",").map((t) => t.trim()) : undefined,
      });
    }
    setDescription("");
    setTags("");
    onUploaded();
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        style={dropzoneStyle}
      >
        {upload.isPending
          ? "Uploading…"
          : "Drop files here or click to upload"}
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          style={{ flex: 1, padding: "4px 8px" }}
        />
        <input
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="Tags (comma-separated)"
          style={{ flex: 1, padding: "4px 8px" }}
        />
      </div>

      {upload.error && (
        <p style={{ color: "red", marginTop: 4, fontSize: 13 }}>
          {String(upload.error)}
        </p>
      )}
      {upload.isSuccess && (
        <p style={{ color: "green", marginTop: 4, fontSize: 13 }}>
          Uploaded — scanning in progress…
        </p>
      )}
    </div>
  );
}

const dropzoneStyle: React.CSSProperties = {
  border: "2px dashed #90caf9",
  borderRadius: 8,
  padding: 24,
  textAlign: "center",
  cursor: "pointer",
  color: "#666",
  fontSize: 14,
  background: "#f8faff",
};
