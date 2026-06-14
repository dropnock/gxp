import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateApp } from "../hooks/useApps";

export function AppCreatePage() {
  const navigate = useNavigate();
  const createApp = useCreateApp();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Name is required"); return; }
    setError(null);
    try {
      const app = await createApp.mutateAsync({ name, description: description || undefined });
      navigate(`/apps/${app.id}/edit`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div style={{ maxWidth: 480 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>New Application</h2>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label style={labelStyle}>Name *</label>
          <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} placeholder="My App" required />
        </div>
        <div>
          <label style={labelStyle}>Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} style={{ ...inputStyle, height: 80, resize: "vertical" }} placeholder="Optional" />
        </div>
        {error && <p style={{ color: "#dc2626", margin: 0 }}>{error}</p>}
        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={createApp.isPending} style={saveBtn}>
            {createApp.isPending ? "Creating…" : "Create & Open Editor"}
          </button>
          <button type="button" onClick={() => navigate(-1)} style={cancelBtn}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 };
const inputStyle: React.CSSProperties = { width: "100%", padding: "8px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 14, boxSizing: "border-box" };
const saveBtn: React.CSSProperties = { padding: "10px 20px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14 };
const cancelBtn: React.CSSProperties = { padding: "10px 20px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 14 };
const backBtn: React.CSSProperties = { padding: "6px 12px", background: "none", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 13 };
