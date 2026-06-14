/**
 * Create or edit a BPMN definition.
 * Route: /workflows/definitions/new  (create)
 *        /workflows/definitions/:id/edit  (update)
 */
import { useRef, useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import BpmnEditor, { type BpmnEditorHandle } from "./BpmnEditor";
import {
  useCreateDefinition,
  useDefinition,
  useUpdateDefinition,
} from "../../hooks/useWorkflow";

export function DefinitionEditorPage() {
  const { id } = useParams<{ id?: string }>();
  const isNew = !id;
  const navigate = useNavigate();

  const editorRef = useRef<BpmnEditorHandle>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const { data: existing, isLoading } = useDefinition(id ?? null);
  const createDefinition = useCreateDefinition();
  const updateDefinition = useUpdateDefinition(id ?? "");

  useEffect(() => {
    if (existing) {
      setName(existing.name ?? "");
      setDescription(existing.description ?? "");
    }
  }, [existing]);

  if (!isNew && isLoading) return <p>Loading…</p>;

  async function handleSave() {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    const xml = await editorRef.current?.getXml();
    if (!xml) {
      setError("BPMN diagram is empty");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        await createDefinition.mutateAsync({ name, description, xml_content: xml });
      } else {
        await updateDefinition.mutateAsync({ name, description, xml_content: xml });
      }
      navigate("/workflows/definitions");
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, flexShrink: 0 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>{isNew ? "New BPMN Definition" : `Edit: ${name}`}</h2>
      </div>

      <div style={{ display: "flex", gap: 16, flexShrink: 0 }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>Name *</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={inputStyle}
            placeholder="e.g. Permit Approval Process"
          />
        </div>
        <div style={{ flex: 2 }}>
          <label style={labelStyle}>Description</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={inputStyle}
            placeholder="Optional description"
          />
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        <BpmnEditor
          ref={editorRef}
          xml={existing?.xml_content}
          onChange={() => {}}
        />
      </div>

      {error && <p style={{ color: "#dc2626", margin: 0 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
        <button onClick={handleSave} disabled={saving} style={saveBtn}>
          {saving ? "Saving…" : isNew ? "Create Definition" : "Save Changes"}
        </button>
        <button onClick={() => navigate(-1)} style={cancelBtn}>Cancel</button>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 };
const inputStyle: React.CSSProperties = {
  width: "100%", padding: "8px 10px", border: "1px solid #d1d5db",
  borderRadius: 4, fontSize: 14, boxSizing: "border-box",
};
const saveBtn: React.CSSProperties = {
  padding: "10px 20px", background: "#2563eb", color: "#fff",
  border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14,
};
const cancelBtn: React.CSSProperties = {
  padding: "10px 20px", background: "#f3f4f6", border: "1px solid #d1d5db",
  borderRadius: 4, cursor: "pointer", fontSize: 14,
};
const backBtn: React.CSSProperties = {
  padding: "6px 12px", background: "none", border: "1px solid #d1d5db",
  borderRadius: 4, cursor: "pointer", fontSize: 13,
};
