import { useState } from "react";
import {
  useCatalog, useDeactivateTemplate, usePublishTemplate,
  type CatalogTemplateCreate,
} from "../hooks/useCatalog";

const CATEGORIES = ["app", "workflow", "dmn", "case_type"] as const;
const CATEGORY_LABELS: Record<string, string> = {
  app: "App", workflow: "Workflow (BPMN)", dmn: "Decision Table (DMN)", case_type: "Case Type",
};

export function CatalogPage() {
  const [filterCategory, setFilterCategory] = useState<string>("");
  const { data: templates = [], isLoading } = useCatalog(filterCategory || undefined);
  const publish = usePublishTemplate();
  const deactivate = useDeactivateTemplate();
  const [showForm, setShowForm] = useState(false);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>Platform Catalog</h1>
        <button
          onClick={() => setShowForm(true)}
          style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
        >
          + Publish Template
        </button>
      </div>

      {showForm && (
        <PublishForm
          onSubmit={async (data) => {
            await publish.mutateAsync(data);
            setShowForm(false);
          }}
          onCancel={() => setShowForm(false)}
          isPending={publish.isPending}
        />
      )}

      {/* Filter */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 13, fontWeight: 600, marginRight: 8 }}>Category:</label>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          style={{ padding: "5px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 14 }}
        >
          <option value="">All</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
        </select>
      </div>

      {isLoading && <p>Loading templates…</p>}

      {!isLoading && templates.length === 0 && (
        <p style={{ color: "#6b7280" }}>No catalog templates yet.</p>
      )}

      {templates.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {templates.map((t) => (
            <div key={t.id} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: "14px 16px", background: "#fff", display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontWeight: 700 }}>{t.name}</span>
                  <span style={{
                    padding: "1px 7px", borderRadius: 10, fontSize: 11, fontWeight: 600,
                    background: "#eff6ff", color: "#2563eb",
                  }}>
                    {CATEGORY_LABELS[t.category] ?? t.category}
                  </span>
                  <span style={{ fontSize: 11, color: "#6b7280" }}>v{t.version}</span>
                  {!t.is_active && (
                    <span style={{ fontSize: 11, color: "#9ca3af", fontStyle: "italic" }}>deactivated</span>
                  )}
                </div>
                {t.description && <div style={{ fontSize: 13, color: "#6b7280" }}>{t.description}</div>}
                {t.tags && t.tags.length > 0 && (
                  <div style={{ marginTop: 4, display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {t.tags.map((tag) => (
                      <span key={tag} style={{ padding: "1px 6px", background: "#f3f4f6", border: "1px solid #e5e7eb", borderRadius: 4, fontSize: 11 }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>
                {new Date(t.published_at).toLocaleDateString()}
              </div>
              {t.is_active && (
                <button
                  onClick={() => { if (confirm(`Deactivate "${t.name}"?`)) deactivate.mutate(t.id); }}
                  disabled={deactivate.isPending}
                  style={{ padding: "5px 12px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}
                >
                  Deactivate
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PublishForm({
  onSubmit,
  onCancel,
  isPending,
}: {
  onSubmit: (data: CatalogTemplateCreate) => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  const [category, setCategory] = useState<CatalogTemplateCreate["category"]>("app");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [schemaJson, setSchemaJson] = useState("{}");
  const [tags, setTags] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    let parsed: object;
    try {
      parsed = JSON.parse(schemaJson);
      setJsonError(null);
    } catch {
      setJsonError("Invalid JSON");
      return;
    }
    onSubmit({
      category,
      name,
      description: description || undefined,
      schema_json: parsed,
      tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : undefined,
    });
  }

  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 20, marginBottom: 24, background: "#fafafa" }}>
      <h3 style={{ marginTop: 0 }}>Publish New Template</h3>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div>
            <label style={labelStyle}>Category *</label>
            <select value={category} onChange={(e) => setCategory(e.target.value as typeof category)} style={inputStyle}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Name *</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required style={inputStyle} placeholder="My Template" />
          </div>
        </div>
        <div>
          <label style={labelStyle}>Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} style={inputStyle} placeholder="Optional" />
        </div>
        <div>
          <label style={labelStyle}>Tags (comma-separated)</label>
          <input value={tags} onChange={(e) => setTags(e.target.value)} style={inputStyle} placeholder="permits, federal, hr" />
        </div>
        <div>
          <label style={labelStyle}>Schema JSON *</label>
          <textarea
            value={schemaJson}
            onChange={(e) => setSchemaJson(e.target.value)}
            rows={6}
            style={{ ...inputStyle, fontFamily: "monospace", fontSize: 12, resize: "vertical" }}
          />
          {jsonError && <p style={{ color: "#dc2626", margin: "4px 0 0", fontSize: 12 }}>{jsonError}</p>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={isPending} style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
            {isPending ? "Publishing…" : "Publish"}
          </button>
          <button type="button" onClick={onCancel} style={{ padding: "8px 16px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer" }}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 };
const inputStyle: React.CSSProperties = {
  width: "100%", padding: "7px 10px", border: "1px solid #d1d5db",
  borderRadius: 4, fontSize: 14, boxSizing: "border-box",
};
