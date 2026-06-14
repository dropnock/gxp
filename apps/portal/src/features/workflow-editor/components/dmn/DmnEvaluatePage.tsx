/**
 * Ad-hoc DMN evaluation page.
 * Users paste/type JSON input data, submit, and see the decision output.
 */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useDmnDefinition, useEvaluateDmn } from "../../hooks/useWorkflow";

export function DmnEvaluatePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: defn, isLoading } = useDmnDefinition(id ?? null);
  const evaluate = useEvaluateDmn(id ?? "");

  const [inputJson, setInputJson] = useState("{\n  \n}");
  const [parseError, setParseError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  if (isLoading) return <p>Loading…</p>;
  if (!defn) return <p style={{ color: "red" }}>Decision table not found.</p>;

  async function handleEvaluate() {
    setParseError(null);
    setResult(null);

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(inputJson);
    } catch (e) {
      setParseError(`Invalid JSON: ${e}`);
      return;
    }

    try {
      const res = await evaluate.mutateAsync(parsed);
      setResult(res.output);
    } catch (e) {
      setParseError(String(e));
    }
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>Evaluate: {defn.name}</h2>
        <span style={{ fontSize: 12, color: "#6b7280", fontFamily: "monospace" }}>
          decision id: {defn.dmn_id ?? "—"}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <label style={labelStyle}>Input Data (JSON)</label>
          <textarea
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            rows={14}
            spellCheck={false}
            style={{
              width: "100%", fontFamily: "monospace", fontSize: 13,
              padding: 10, border: "1px solid #d1d5db", borderRadius: 4,
              boxSizing: "border-box", resize: "vertical",
            }}
          />
          {parseError && (
            <p style={{ color: "#dc2626", fontSize: 13, marginTop: 4 }}>{parseError}</p>
          )}
          <button
            onClick={handleEvaluate}
            disabled={evaluate.isPending}
            style={{ ...saveBtn, marginTop: 12 }}
          >
            {evaluate.isPending ? "Evaluating…" : "Evaluate"}
          </button>
        </div>

        <div>
          <label style={labelStyle}>Output</label>
          {result === null ? (
            <div style={{
              height: 200, border: "1px dashed #d1d5db", borderRadius: 4,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#9ca3af", fontSize: 13,
            }}>
              Run the evaluation to see output
            </div>
          ) : (
            <pre style={{
              background: "#f0fdf4", border: "1px solid #86efac",
              borderRadius: 4, padding: 12, fontSize: 13,
              fontFamily: "monospace", overflowX: "auto",
            }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 };
const saveBtn: React.CSSProperties = { padding: "10px 20px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14 };
const backBtn: React.CSSProperties = { padding: "6px 12px", background: "none", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 13 };
