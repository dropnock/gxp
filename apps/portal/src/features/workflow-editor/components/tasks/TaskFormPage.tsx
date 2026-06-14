/**
 * Human task detail + form completion.
 *
 * Renders a generic form from the task's JSON Schema (form_schema).
 * Supports string, integer, boolean, and date fields.
 * On submit, enqueues the complete_task Celery job and shows a "processing" state.
 */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useClaimTask, useCompleteTask, useTask } from "../../hooks/useWorkflow";

export function TaskFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: task, isLoading, error } = useTask(id ?? null);
  const claimTask = useClaimTask();
  const completeTask = useCompleteTask();

  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (isLoading) return <p>Loading task…</p>;
  if (error || !task) return <p style={{ color: "red" }}>Task not found.</p>;

  if (submitted) {
    return (
      <div style={{ textAlign: "center", padding: 48 }}>
        <h3>Task submitted</h3>
        <p style={{ color: "#6b7280" }}>The workflow is advancing in the background.</p>
        <button onClick={() => navigate("/workflows/tasks/inbox")} style={saveBtn}>
          Back to Inbox
        </button>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    try {
      await completeTask.mutateAsync({ id: task.id, completion_data: formValues });
      setSubmitted(true);
    } catch (err) {
      setSubmitError(String(err));
    }
  }

  const schema = task.form_schema ?? {};
  const properties: Record<string, FieldSchema> = schema.properties ?? {};
  const required: string[] = schema.required ?? [];

  function setValue(key: string, value: unknown) {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>{task.task_title || task.task_name}</h2>
        <span style={{
          padding: "2px 10px", borderRadius: 10, fontSize: 12, fontWeight: 600,
          background: task.status === "claimed" ? "#dbeafe" : "#fef3c7",
          color: task.status === "claimed" ? "#1d4ed8" : "#92400e",
        }}>
          {task.status}
        </span>
      </div>

      {task.status === "ready" && (
        <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 6, padding: 12, marginBottom: 16, fontSize: 13 }}>
          This task is unclaimed.{" "}
          <button
            onClick={() => claimTask.mutate(task.id)}
            disabled={claimTask.isPending}
            style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", fontSize: 13, textDecoration: "underline" }}
          >
            Claim it
          </button>{" "}
          before completing, or complete directly as an admin.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {Object.keys(properties).length === 0 ? (
          <p style={{ color: "#6b7280", marginBottom: 16 }}>This task has no form fields.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 24 }}>
            {Object.entries(properties).map(([key, fieldSchema]) => (
              <FormField
                key={key}
                fieldKey={key}
                schema={fieldSchema}
                required={required.includes(key)}
                value={formValues[key]}
                onChange={(v) => setValue(key, v)}
              />
            ))}
          </div>
        )}

        {submitError && <p style={{ color: "#dc2626", marginBottom: 12 }}>{submitError}</p>}

        <div style={{ display: "flex", gap: 8 }}>
          <button type="submit" disabled={completeTask.isPending} style={saveBtn}>
            {completeTask.isPending ? "Submitting…" : "Complete Task"}
          </button>
          <button type="button" onClick={() => navigate(-1)} style={cancelBtn}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

interface FieldSchema {
  title?: string;
  type?: "string" | "integer" | "boolean" | "number";
  format?: string;
}

function FormField({
  fieldKey,
  schema,
  required,
  value,
  onChange,
}: {
  fieldKey: string;
  schema: FieldSchema;
  required: boolean;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const label = schema.title || fieldKey;
  const type = schema.type ?? "string";

  return (
    <div>
      <label style={labelStyle}>
        {label}{required ? " *" : ""}
      </label>
      {type === "boolean" ? (
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          style={{ width: 18, height: 18 }}
        />
      ) : type === "integer" || type === "number" ? (
        <input
          type="number"
          value={String(value ?? "")}
          onChange={(e) => onChange(Number(e.target.value))}
          required={required}
          style={inputStyle}
        />
      ) : schema.format === "date" ? (
        <input
          type="date"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          style={inputStyle}
        />
      ) : (
        <input
          type="text"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          style={inputStyle}
        />
      )}
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
