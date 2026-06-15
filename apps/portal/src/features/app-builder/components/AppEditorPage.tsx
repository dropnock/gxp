/**
 * GrapesJS-based app editor.
 *
 * Sidebar: page list (add / switch / delete pages)
 * Main canvas: GrapesJS editor
 * Top bar: app name, status, save, submit-review, publish buttons
 */
import { useRef, useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import GrapesEditor, { type GrapesEditorHandle } from "./GrapesEditor";
import {
  useApp, useAppPages, useDeletePage, usePublishApp,
  useSubmitReview, useUpsertPage,
} from "../hooks/useApps";

export function AppEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: app, isLoading: appLoading } = useApp(id ?? null);
  const { data: pages = [], isLoading: pagesLoading } = useAppPages(id ?? null);
  const upsertPage = useUpsertPage(id ?? "");
  const deletePage = useDeletePage(id ?? "");
  const submitReview = useSubmitReview();
  const publishApp = usePublishApp();

  const editorRef = useRef<GrapesEditorHandle>(null);
  const [activePageId, setActivePageId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Set active page to first page once loaded
  useEffect(() => {
    if (pages.length > 0 && !activePageId) {
      setActivePageId(pages[0].page_id);
    }
  }, [pages, activePageId]);

  const activePage = pages.find((p: PageRow) => p.page_id === activePageId);

  if (appLoading || pagesLoading) return <p style={{ padding: 24 }}>Loading…</p>;
  if (!app) return <p style={{ padding: 24, color: "red" }}>App not found.</p>;

  const isEditable = app.status === "draft" || app.status === "rejected";

  async function addPage() {
    const pageId = `page-${Date.now()}`;
    const name = prompt("Page name:", "New Page");
    if (!name) return;
    const route = `/${name.toLowerCase().replace(/\s+/g, "-")}`;
    await upsertPage.mutateAsync({
      pageId,
      body: { name, route, gjs_data: {}, styles: {} },
    });
    setActivePageId(pageId);
  }

  async function savePage() {
    if (!activePageId || !editorRef.current) return;
    setSaving(true);
    setStatusMsg(null);
    try {
      const project = editorRef.current.getProject();
      await upsertPage.mutateAsync({
        pageId: activePageId,
        body: {
          name: activePage?.name ?? "Page",
          route: activePage?.route ?? "/",
          gjs_data: project,
          styles: (project as any).styles ?? {},
        },
      });
      setStatusMsg("Saved");
      setTimeout(() => setStatusMsg(null), 2000);
    } catch (err) {
      setStatusMsg(`Error: ${err}`);
    } finally {
      setSaving(false);
    }
  }

  const STATUS_COLOR: Record<string, string> = {
    draft: "#6b7280", under_review: "#d97706",
    published: "#059669", rejected: "#dc2626",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Top bar */}
      <div style={{ height: 52, borderBottom: "1px solid #e5e7eb", display: "flex", alignItems: "center", padding: "0 16px", gap: 12, flexShrink: 0, background: "#fff" }}>
        <button onClick={() => navigate("/apps")} style={{ padding: "4px 10px", background: "none", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 13 }}>← Apps</button>
        <span style={{ fontWeight: 700, fontSize: 15 }}>{app.name}</span>
        <span style={{
          padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600,
          background: (STATUS_COLOR[app.status] ?? "#6b7280") + "20",
          color: STATUS_COLOR[app.status] ?? "#6b7280",
        }}>
          {app.status}
        </span>
        <div style={{ flex: 1 }} />
        {statusMsg && <span style={{ fontSize: 12, color: statusMsg.startsWith("Error") ? "#dc2626" : "#059669" }}>{statusMsg}</span>}
        {isEditable && (
          <button onClick={savePage} disabled={saving} style={{ padding: "6px 14px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
            {saving ? "Saving…" : "Save"}
          </button>
        )}
        {app.status === "draft" && (
          <button
            onClick={() => submitReview.mutate(app.id)}
            disabled={submitReview.isPending}
            style={{ padding: "6px 14px", background: "#d97706", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 13 }}
          >
            Submit for Review
          </button>
        )}
        {app.status === "under_review" && (
          <button
            onClick={() => publishApp.mutate(app.id)}
            disabled={publishApp.isPending}
            style={{ padding: "6px 14px", background: "#059669", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 13 }}
          >
            Publish
          </button>
        )}
      </div>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* Page sidebar */}
        <div style={{ width: 180, borderRight: "1px solid #e5e7eb", background: "#f9fafb", display: "flex", flexDirection: "column", flexShrink: 0 }}>
          <div style={{ padding: "12px 12px 8px", fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Pages
          </div>
          {pages.map((page: PageRow) => (
            <div
              key={page.page_id}
              onClick={() => setActivePageId(page.page_id)}
              style={{
                padding: "8px 12px", cursor: "pointer", fontSize: 13,
                background: activePageId === page.page_id ? "#eff6ff" : "transparent",
                borderLeft: activePageId === page.page_id ? "3px solid #2563eb" : "3px solid transparent",
                color: activePageId === page.page_id ? "#2563eb" : "#374151",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{page.name}</span>
              {isEditable && pages.length > 1 && (
                <button
                  onClick={(e) => { e.stopPropagation(); if (confirm(`Delete page "${page.name}"?`)) { deletePage.mutate(page.page_id); if (activePageId === page.page_id) setActivePageId(null); } }}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", fontSize: 14, padding: "0 2px" }}
                >
                  ×
                </button>
              )}
            </div>
          ))}
          {isEditable && (
            <button
              onClick={addPage}
              style={{ margin: 8, padding: "6px 8px", background: "none", border: "1px dashed #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 12, color: "#6b7280" }}
            >
              + Add Page
            </button>
          )}
        </div>

        {/* Editor canvas */}
        <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
          {activePage ? (
            <GrapesEditor
              key={activePageId}
              ref={editorRef}
              initialData={activePage.gjs_data}
              onChange={isEditable ? () => {} : undefined}
            />
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#9ca3af" }}>
              {isEditable ? "Add a page to get started" : "No pages"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface PageRow {
  page_id: string;
  name: string;
  route: string;
  gjs_data: object;
  styles: object;
}
