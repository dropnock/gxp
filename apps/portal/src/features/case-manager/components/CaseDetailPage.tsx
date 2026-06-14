import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  useAddNote,
  useCase,
  useCaseNotes,
  useCaseTimeline,
  useLinkDocument,
  useStartCaseWorkflow,
  useUpdateCase,
} from "../hooks/useCases";

const STATUS_COLOR: Record<string, string> = {
  open: "#059669", pending: "#d97706", on_hold: "#6b7280",
  closed: "#1d4ed8", archived: "#374151",
};

const TIMELINE_ICON: Record<string, string> = {
  case_created: "📁",
  status_change: "🔄",
  note_added: "📝",
  document_linked: "📎",
  workflow_linked: "⚙️",
  workflow_started: "▶️",
  workflow_advanced: "⏩",
  task_completed: "✅",
  participant_added: "👤",
  participant_removed: "🚫",
  document_uploaded: "📤",
  document_scan_passed: "🛡️",
  document_quarantined: "⚠️",
};

export function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: caseData, isLoading, error } = useCase(id ?? null);
  const { data: timeline = [] } = useCaseTimeline(id ?? null);
  const { data: notes = [] } = useCaseNotes(id ?? null, true);
  const updateCase = useUpdateCase(id ?? "");
  const addNote = useAddNote(id ?? "");
  const linkDocument = useLinkDocument(id ?? "");
  const startWorkflow = useStartCaseWorkflow(id ?? "");

  const [activeTab, setActiveTab] = useState<"timeline" | "notes" | "links">("timeline");
  const [noteBody, setNoteBody] = useState("");
  const [noteInternal, setNoteInternal] = useState(true);
  const [docIdInput, setDocIdInput] = useState("");
  const [wfDefIdInput, setWfDefIdInput] = useState("");
  const [wfLabel, setWfLabel] = useState("");
  const [editStatus, setEditStatus] = useState<string | null>(null);

  if (isLoading) return <p>Loading case…</p>;
  if (error || !caseData) return <p style={{ color: "red" }}>Case not found.</p>;

  const c = caseData;
  const statusColor = STATUS_COLOR[c.status] ?? "#6b7280";

  async function handleStatusChange(newStatus: string) {
    await updateCase.mutateAsync({ status: newStatus });
    setEditStatus(null);
  }

  async function submitNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    await addNote.mutateAsync({ body: noteBody, is_internal: noteInternal });
    setNoteBody("");
  }

  async function submitDocLink(e: React.FormEvent) {
    e.preventDefault();
    if (!docIdInput.trim()) return;
    try {
      await linkDocument.mutateAsync(docIdInput.trim());
      setDocIdInput("");
    } catch (err) {
      alert(String(err));
    }
  }

  async function submitStartWorkflow(e: React.FormEvent) {
    e.preventDefault();
    if (!wfDefIdInput.trim()) return;
    try {
      await startWorkflow.mutateAsync({ definition_id: wfDefIdInput.trim(), label: wfLabel || undefined });
      setWfDefIdInput("");
      setWfLabel("");
    } catch (err) {
      alert(String(err));
    }
  }

  const STATUSES = ["open", "pending", "on_hold", "closed", "archived"];

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 20 }}>
        <button onClick={() => navigate(-1)} style={backBtn}>← Back</button>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
            <code style={{ fontSize: 13, color: "#6b7280" }}>{c.case_number}</code>
            <span style={{
              padding: "2px 10px", borderRadius: 10, fontSize: 12, fontWeight: 600,
              background: statusColor + "20", color: statusColor,
            }}>
              {c.status}
            </span>
            <span style={{ fontSize: 12, padding: "2px 8px", border: "1px solid #e5e7eb", borderRadius: 10, color: "#374151" }}>
              {c.priority}
            </span>
          </div>
          <h2 style={{ margin: 0, fontSize: 20 }}>{c.title}</h2>
        </div>

        {/* Status dropdown */}
        {editStatus !== null ? (
          <select
            value={editStatus}
            onChange={(e) => handleStatusChange(e.target.value)}
            onBlur={() => setEditStatus(null)}
            autoFocus
            style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 }}
          >
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        ) : (
          <button onClick={() => setEditStatus(c.status)} style={smBtn}>
            Change Status
          </button>
        )}
      </div>

      {/* Meta grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24, background: "#f9fafb", borderRadius: 6, padding: 16 }}>
        <Meta label="Assigned To" value={c.assigned_to || "Unassigned"} mono={!!c.assigned_to} />
        <Meta label="Created By" value={c.created_by} mono />
        <Meta label="Created At" value={new Date(c.created_at).toLocaleString()} />
        {c.closed_at && <Meta label="Closed At" value={new Date(c.closed_at).toLocaleString()} />}
        <Meta label="Participants" value={`${c.participants?.length ?? 0}`} />
        <Meta label="Documents" value={`${c.document_links?.length ?? 0}`} />
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #e5e7eb", marginBottom: 20 }}>
        {(["timeline", "notes", "links"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "10px 20px", background: "none", border: "none",
              borderBottom: activeTab === tab ? "2px solid #2563eb" : "2px solid transparent",
              color: activeTab === tab ? "#2563eb" : "#374151",
              cursor: "pointer", fontWeight: activeTab === tab ? 600 : 400,
              fontSize: 14, textTransform: "capitalize",
            }}
          >
            {tab === "timeline" ? `Timeline (${timeline.length})` :
             tab === "notes" ? `Notes (${notes.length})` : "Links"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "timeline" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {timeline.length === 0 && <p style={{ color: "#6b7280" }}>No events yet.</p>}
          {[...timeline].reverse().map((ev: TimelineRow) => (
            <div key={ev.id} style={{ display: "flex", gap: 12, paddingBottom: 16, position: "relative" }}>
              <div style={{ fontSize: 20, flexShrink: 0, width: 28 }}>
                {TIMELINE_ICON[ev.event_type] ?? "•"}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{ev.event_type.replace(/_/g, " ")}</div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>
                  {new Date(ev.occurred_at).toLocaleString()} · actor: <code>{ev.actor_id.slice(0, 12)}…</code>
                </div>
                {Object.keys(ev.metadata).length > 0 && (
                  <pre style={{ margin: "4px 0 0", fontSize: 11, color: "#374151", background: "#f3f4f6", borderRadius: 4, padding: "4px 8px" }}>
                    {JSON.stringify(ev.metadata, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "notes" && (
        <div>
          <form onSubmit={submitNote} style={{ marginBottom: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            <textarea
              value={noteBody}
              onChange={(e) => setNoteBody(e.target.value)}
              rows={3}
              placeholder="Add a note…"
              style={{ padding: 10, border: "1px solid #d1d5db", borderRadius: 4, fontSize: 14, resize: "vertical" }}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input type="checkbox" checked={noteInternal} onChange={(e) => setNoteInternal(e.target.checked)} />
                Internal only
              </label>
              <button type="submit" disabled={addNote.isPending} style={saveBtn}>
                {addNote.isPending ? "Saving…" : "Add Note"}
              </button>
            </div>
          </form>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {notes.length === 0 && <p style={{ color: "#6b7280" }}>No notes yet.</p>}
            {notes.map((note: NoteRow) => (
              <div key={note.id} style={{
                border: "1px solid #e5e7eb", borderRadius: 6, padding: 12,
                background: note.is_internal ? "#fefce8" : "#fff",
              }}>
                <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
                  <code>{note.created_by.slice(0, 12)}…</code>
                  {" · "}{new Date(note.created_at).toLocaleString()}
                  {note.is_internal && <span style={{ color: "#d97706", fontWeight: 600 }}> · Internal</span>}
                </div>
                <div style={{ fontSize: 14, whiteSpace: "pre-wrap" }}>{note.body}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "links" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Document links */}
          <div>
            <h3 style={{ marginBottom: 12, fontSize: 15 }}>Document Links ({c.document_links?.length ?? 0})</h3>
            {c.document_links?.map((dl: { id: string; document_id: string }) => (
              <div key={dl.id} style={{ padding: "8px 0", borderBottom: "1px solid #f3f4f6", fontSize: 13 }}>
                <code>{dl.document_id.slice(0, 8)}…</code>
              </div>
            ))}
            <form onSubmit={submitDocLink} style={{ marginTop: 12, display: "flex", gap: 8 }}>
              <input
                value={docIdInput}
                onChange={(e) => setDocIdInput(e.target.value)}
                placeholder="Document UUID"
                style={{ flex: 1, padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 }}
              />
              <button type="submit" disabled={linkDocument.isPending} style={smBtn}>
                Link
              </button>
            </form>
          </div>

          {/* Workflow links */}
          <div>
            <h3 style={{ marginBottom: 12, fontSize: 15 }}>Workflow Links ({c.workflow_links?.length ?? 0})</h3>
            {c.workflow_links?.map((wl: { id: string; workflow_instance_id: string; label?: string }) => (
              <div key={wl.id} style={{ padding: "8px 0", borderBottom: "1px solid #f3f4f6", fontSize: 13 }}>
                <code>{wl.workflow_instance_id.slice(0, 8)}…</code>
                {wl.label && <span style={{ color: "#6b7280" }}> · {wl.label}</span>}
              </div>
            ))}
            <form onSubmit={submitStartWorkflow} style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
              <input
                value={wfDefIdInput}
                onChange={(e) => setWfDefIdInput(e.target.value)}
                placeholder="BPMN Definition UUID"
                style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 }}
              />
              <input
                value={wfLabel}
                onChange={(e) => setWfLabel(e.target.value)}
                placeholder="Label (optional)"
                style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 4, fontSize: 13 }}
              />
              <button type="submit" disabled={startWorkflow.isPending} style={smBtn}>
                {startWorkflow.isPending ? "Starting…" : "Start Workflow"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, fontFamily: mono ? "monospace" : undefined }}>{value}</div>
    </div>
  );
}

interface TimelineRow {
  id: string; event_type: string; actor_id: string; occurred_at: string; metadata: Record<string, unknown>;
}
interface NoteRow {
  id: string; body: string; is_internal: boolean; created_by: string; created_at: string;
}

const backBtn: React.CSSProperties = { padding: "6px 12px", background: "none", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 13 };
const smBtn: React.CSSProperties = { padding: "6px 14px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: 13 };
const saveBtn: React.CSSProperties = { padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 14 };
