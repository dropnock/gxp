import { useState } from "react";

interface Field {
  name: string;
  label: string;
  type: "text" | "number" | "date" | "textarea" | "select";
  required?: boolean;
  options?: string[];
}

interface Props {
  fields?: Field[];
  submitLabel?: string;
  datasourceAction?: string;
  [k: string]: unknown;
}

export function GxpForm({ fields = [], submitLabel = "Submit" }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});

  function set(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // In the runtime, datasourceAction would POST values to the bound datasource
    console.info("[GXP Form] submit", values);
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {fields.map((f) => (
        <div key={f.name}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
            {f.label}{f.required ? " *" : ""}
          </label>
          {f.type === "textarea" ? (
            <textarea
              value={values[f.name] ?? ""}
              onChange={(e) => set(f.name, e.target.value)}
              required={f.required}
              rows={3}
              style={inputStyle}
            />
          ) : f.type === "select" ? (
            <select
              value={values[f.name] ?? ""}
              onChange={(e) => set(f.name, e.target.value)}
              required={f.required}
              style={inputStyle}
            >
              <option value="">— select —</option>
              {(f.options ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input
              type={f.type}
              value={values[f.name] ?? ""}
              onChange={(e) => set(f.name, e.target.value)}
              required={f.required}
              style={inputStyle}
            />
          )}
        </div>
      ))}
      <button
        type="submit"
        style={{ padding: "10px 20px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", alignSelf: "flex-start" }}
      >
        {submitLabel}
      </button>
    </form>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "8px 10px", border: "1px solid #d1d5db",
  borderRadius: 4, fontSize: 14, boxSizing: "border-box",
};
