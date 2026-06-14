import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCaseTypes, useCreateCase } from "../hooks/useCases";

export function CaseCreatePage() {
  const navigate = useNavigate();
  const { data: caseTypes = [], isLoading } = useCaseTypes();
  const createCase = useCreateCase();

  const [caseTypeId, setCaseTypeId] = useState("");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("normal");
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <p>Loading case types…</p>;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!caseTypeId || !title) {
      setError("Case type and title are required");
      return;
    }
    setError(null);
    try {
      const result = await createCase.mutateAsync({ case_type_id: caseTypeId, title, priority });
      navigate(`/cases/${result.id}`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>New Case</h2>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label style={labelStyle}>Case Type *</label>
          <select
            value={caseTypeId}
            onChange={(e) => setCaseTypeId(e.target.value)}
            style={inputStyle}
            required
          >
            <option value="">— select —</option>
            {caseTypes.map((ct: { id: string; name: string }) => (
              <option key={ct.id} value={ct.id}>{ct.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label style={labelStyle}>Title *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={inputStyle}
            placeholder="Brief description of the case"
            required
          />
        </div>

        <div>
          <label style={labelStyle}>Priority</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} style={inputStyle}>
            {["low", "normal", "high", "urgent"].map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {error && <p style={{ color: "#dc2626", margin: 0 }}>{error}</p>}

        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={createCase.isPending} style={saveBtn}>
            {createCase.isPending ? "Creating…" : "Create Case"}
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
