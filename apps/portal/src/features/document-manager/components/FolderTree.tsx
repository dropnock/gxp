import { useState } from "react";
import { useFolders, useCreateFolder, Folder } from "../hooks/useDocuments";

interface Props {
  selectedFolderId: string | null;
  onSelect: (folderId: string | null) => void;
}

export function FolderTree({ selectedFolderId, onSelect }: Props) {
  const { data: rootFolders, isLoading } = useFolders(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const createMutation = useCreateFolder();

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate(
      { name: newName, parent_id: null },
      { onSuccess: () => { setCreating(false); setNewName(""); } },
    );
  }

  if (isLoading) return <div style={styles.tree}>Loading…</div>;

  return (
    <div style={styles.tree}>
      <div style={styles.treeHeader}>
        <strong>Folders</strong>
        <button style={styles.addBtn} onClick={() => setCreating(true)}>+</button>
      </div>

      {creating && (
        <form onSubmit={handleCreate} style={{ padding: "4px 8px" }}>
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Folder name"
            style={{ width: "100%", marginBottom: 4 }}
          />
          <button type="submit" disabled={createMutation.isPending}>Create</button>
          <button type="button" onClick={() => setCreating(false)} style={{ marginLeft: 4 }}>Cancel</button>
        </form>
      )}

      <div
        style={{ ...styles.folderItem, background: selectedFolderId === null ? "#e8f0fe" : undefined }}
        onClick={() => onSelect(null)}
      >
        📁 All Documents
      </div>

      {rootFolders?.map((f) => (
        <FolderNode
          key={f.id}
          folder={f}
          depth={1}
          selectedFolderId={selectedFolderId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

function FolderNode({
  folder,
  depth,
  selectedFolderId,
  onSelect,
}: {
  folder: Folder;
  depth: number;
  selectedFolderId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const { data: children } = useFolders(expanded ? folder.id : null);

  return (
    <div>
      <div
        style={{
          ...styles.folderItem,
          paddingLeft: depth * 16,
          background: selectedFolderId === folder.id ? "#e8f0fe" : undefined,
        }}
        onClick={() => { onSelect(folder.id); setExpanded(true); }}
      >
        <span onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }} style={{ marginRight: 4 }}>
          {expanded ? "▾" : "▸"}
        </span>
        📁 {folder.name}
      </div>
      {expanded && children?.map((c) => (
        <FolderNode key={c.id} folder={c} depth={depth + 1} selectedFolderId={selectedFolderId} onSelect={onSelect} />
      ))}
    </div>
  );
}

const styles = {
  tree: { width: 220, borderRight: "1px solid #e0e0e0", minHeight: "100%", flexShrink: 0 } as React.CSSProperties,
  treeHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderBottom: "1px solid #e0e0e0" } as React.CSSProperties,
  addBtn: { background: "none", border: "none", fontSize: 18, cursor: "pointer", lineHeight: 1 } as React.CSSProperties,
  folderItem: { padding: "6px 12px", cursor: "pointer", fontSize: 13, userSelect: "none" as const },
};
