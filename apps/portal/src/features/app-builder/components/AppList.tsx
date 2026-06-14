import { Link } from "react-router-dom";
import { useApps, usePublishApp, useSubmitReview } from "../hooks/useApps";

const STATUS_COLOR: Record<string, string> = {
  draft: "#6b7280", under_review: "#d97706",
  published: "#059669", rejected: "#dc2626",
};

export function AppList() {
  const { data: apps = [], isLoading, error } = useApps();
  const submitReview = useSubmitReview();
  const publishApp = usePublishApp();

  if (isLoading) return <p>Loading apps…</p>;
  if (error) return <p style={{ color: "red" }}>Error: {String(error)}</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Applications</h2>
        <Link to="/apps/new">
          <button style={btnStyle}>+ New App</button>
        </Link>
      </div>

      {apps.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No apps yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {apps.map((app: AppRow) => (
            <div key={app.id} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: "12px 16px", background: "#fff", display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{app.name}</div>
                {app.description && <div style={{ fontSize: 13, color: "#6b7280" }}>{app.description}</div>}
              </div>
              <span style={{
                padding: "2px 10px", borderRadius: 10, fontSize: 12, fontWeight: 600,
                background: (STATUS_COLOR[app.status] ?? "#6b7280") + "20",
                color: STATUS_COLOR[app.status] ?? "#6b7280",
              }}>
                {app.status}
              </span>
              <div style={{ display: "flex", gap: 8 }}>
                <Link to={`/apps/${app.id}/edit`}>
                  <button style={smBtn}>Edit</button>
                </Link>
                {app.status === "draft" && (
                  <button
                    style={{ ...smBtn, color: "#d97706" }}
                    onClick={() => submitReview.mutate(app.id)}
                    disabled={submitReview.isPending}
                  >
                    Submit for Review
                  </button>
                )}
                {app.status === "under_review" && (
                  <button
                    style={{ ...smBtn, background: "#059669", color: "#fff" }}
                    onClick={() => publishApp.mutate(app.id)}
                    disabled={publishApp.isPending}
                  >
                    Publish
                  </button>
                )}
                {app.status === "published" && (
                  <a
                    href={`/runtime/index.html?appId=${app.id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <button style={{ ...smBtn, background: "#2563eb", color: "#fff" }}>Preview</button>
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface AppRow { id: string; name: string; description?: string; status: string }

const btnStyle: React.CSSProperties = { padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14 };
const smBtn: React.CSSProperties = { padding: "5px 12px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 12 };
