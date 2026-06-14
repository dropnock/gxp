import { Link } from "react-router-dom";
import { useClaimTask, useInbox } from "../../hooks/useWorkflow";

export function TaskInbox() {
  const { data: tasks = [], isLoading, error } = useInbox();
  const claimTask = useClaimTask();

  if (isLoading) return <p>Loading inbox…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>Task Inbox</h2>

      {tasks.length === 0 ? (
        <p style={{ color: "#6b7280" }}>Your inbox is empty.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {tasks.map((t: TaskRow) => (
            <div
              key={t.id}
              style={{
                border: "1px solid #e5e7eb", borderRadius: 6, padding: 16,
                background: t.status === "claimed" ? "#eff6ff" : "#fff",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
                    {t.task_title || t.task_name}
                  </div>
                  <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
                    Instance:{" "}
                    <Link to={`/workflows/instances/${t.instance_id}`} style={{ color: "#2563eb" }}>
                      {t.instance_id.slice(0, 8)}…
                    </Link>
                    {" · "}
                    Roles: {t.candidate_roles?.join(", ") || "any"}
                    {t.assigned_to && ` · Claimed`}
                  </div>
                  <div style={{ fontSize: 12, color: "#9ca3af" }}>
                    Created {new Date(t.created_at).toLocaleString()}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  {t.status === "ready" && (
                    <button
                      onClick={() => claimTask.mutate(t.id)}
                      disabled={claimTask.isPending}
                      style={smBtn}
                    >
                      Claim
                    </button>
                  )}
                  <Link to={`/workflows/tasks/${t.id}`}>
                    <button style={{ ...smBtn, background: "#2563eb", color: "#fff" }}>
                      Open
                    </button>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface TaskRow {
  id: string;
  instance_id: string;
  task_name: string;
  task_title: string | null;
  status: string;
  assigned_to: string | null;
  candidate_roles: string[];
  created_at: string;
}

const smBtn: React.CSSProperties = {
  padding: "6px 14px", background: "#f3f4f6", border: "1px solid #d1d5db",
  borderRadius: 4, cursor: "pointer", fontSize: 13,
};
