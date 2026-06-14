import { useNavigate, useParams } from "react-router-dom";
import { useCancelInstance, useInstance } from "../../hooks/useWorkflow";

const STATUS_COLORS: Record<string, string> = {
  running: "#d97706", waiting: "#2563eb", completed: "#059669",
  cancelled: "#6b7280", error: "#dc2626",
};

export function InstanceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: instance, isLoading, error } = useInstance(id ?? null);
  const cancelInstance = useCancelInstance();

  if (isLoading) return <p>Loading instance…</p>;
  if (error || !instance) return <p style={{ color: "red" }}>Instance not found.</p>;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>
          Instance{" "}
          <code style={{ fontSize: 16 }}>{instance.id.slice(0, 8)}…</code>
        </h2>
        <span style={{
          padding: "3px 10px", borderRadius: 10, fontSize: 13, fontWeight: 600,
          background: (STATUS_COLORS[instance.status] ?? "#6b7280") + "20",
          color: STATUS_COLORS[instance.status] ?? "#6b7280",
        }}>
          {instance.status}
        </span>
        {(instance.status === "running" || instance.status === "waiting") && (
          <button
            onClick={() => {
              if (confirm("Cancel this instance?")) {
                cancelInstance.mutate(instance.id);
              }
            }}
            style={{ marginLeft: "auto", padding: "6px 14px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
          >
            Cancel
          </button>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
        <Detail label="Definition ID" value={instance.definition_id} mono />
        <Detail label="Definition Version" value={`v${instance.definition_version}`} />
        <Detail label="Started By" value={instance.started_by} mono />
        <Detail label="Started At" value={new Date(instance.started_at).toLocaleString()} />
        {instance.completed_at && (
          <Detail label="Completed At" value={new Date(instance.completed_at).toLocaleString()} />
        )}
        {instance.case_id && <Detail label="Case ID" value={instance.case_id} mono />}
      </div>

      {/* Process variables */}
      {Object.keys(instance.variables ?? {}).length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 8 }}>Process Variables</h3>
          <pre style={{
            background: "#f9fafb", border: "1px solid #e5e7eb",
            borderRadius: 4, padding: 12, fontSize: 12, overflowX: "auto",
          }}>
            {JSON.stringify(instance.variables, null, 2)}
          </pre>
        </section>
      )}

      {/* Human tasks */}
      <section>
        <h3 style={{ marginBottom: 8 }}>Tasks</h3>
        {(!instance.task_instances || instance.task_instances.length === 0) ? (
          <p style={{ color: "#6b7280" }}>No human tasks.</p>
        ) : (
          <table style={tableStyle}>
            <thead>
              <tr>
                {["Task Name", "Status", "Assigned To", "Created At", "Completed At"].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {instance.task_instances.map((t: TaskRow) => (
                <tr key={t.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={tdStyle}>{t.task_title || t.task_name}</td>
                  <td style={tdStyle}>{t.status}</td>
                  <td style={tdStyle}>{t.assigned_to ? <code style={{ fontSize: 12 }}>{t.assigned_to.slice(0, 12)}…</code> : "Unassigned"}</td>
                  <td style={tdStyle}>{new Date(t.created_at).toLocaleString()}</td>
                  <td style={tdStyle}>{t.completed_at ? new Date(t.completed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 14, fontFamily: mono ? "monospace" : undefined }}>{value}</div>
    </div>
  );
}

interface TaskRow {
  id: string;
  task_name: string;
  task_title: string | null;
  status: string;
  assigned_to: string | null;
  created_at: string;
  completed_at: string | null;
}

const backBtn: React.CSSProperties = {
  padding: "6px 12px", background: "none", border: "1px solid #d1d5db",
  borderRadius: 4, cursor: "pointer", fontSize: 13,
};
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse" };
const thStyle: React.CSSProperties = {
  textAlign: "left", padding: "8px 12px", background: "#f9fafb",
  borderBottom: "1px solid #e5e7eb", fontSize: 13, fontWeight: 600,
};
const tdStyle: React.CSSProperties = { padding: "10px 12px", fontSize: 14 };
