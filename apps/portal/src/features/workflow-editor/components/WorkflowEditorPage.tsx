/**
 * Top-level layout for the workflow editor feature.
 * Sub-routes are handled here; the parent App.tsx renders /workflows/* to this component.
 */
import { NavLink, Routes, Route, useNavigate } from "react-router-dom";
import { DefinitionList } from "./bpmn/DefinitionList";
import { DefinitionEditorPage } from "./bpmn/DefinitionEditorPage";
import { InstanceList } from "./instances/InstanceList";
import { InstanceDetailPage } from "./instances/InstanceDetailPage";
import { TaskInbox } from "./tasks/TaskInbox";
import { TaskFormPage } from "./tasks/TaskFormPage";
import { DmnDefinitionList } from "./dmn/DmnDefinitionList";
import { DmnEditorPage } from "./dmn/DmnEditorPage";
import { DmnEvaluatePage } from "./dmn/DmnEvaluatePage";

const navItems = [
  { label: "BPMN Definitions", to: "/workflows/definitions" },
  { label: "Instances", to: "/workflows/instances" },
  { label: "Task Inbox", to: "/workflows/tasks/inbox" },
  { label: "Decision Tables", to: "/workflows/dmn" },
];

export function WorkflowEditorPage() {
  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)" }}>
      {/* Sidebar */}
      <nav style={{
        width: 200, borderRight: "1px solid #e5e7eb", padding: "20px 0",
        background: "#f9fafb", flexShrink: 0,
      }}>
        <div style={{ padding: "0 16px 16px", fontWeight: 700, fontSize: 13, color: "#374151" }}>
          WORKFLOW
        </div>
        {navItems.map(({ label, to }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: "block", padding: "8px 16px", fontSize: 14,
              color: isActive ? "#2563eb" : "#374151",
              background: isActive ? "#eff6ff" : "transparent",
              textDecoration: "none",
              borderLeft: isActive ? "3px solid #2563eb" : "3px solid transparent",
            })}
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <Routes>
          <Route index element={<DefinitionList />} />

          {/* BPMN definitions */}
          <Route path="definitions" element={<DefinitionList />} />
          <Route path="definitions/new" element={<DefinitionEditorPage />} />
          <Route path="definitions/:id" element={<DefinitionEditorPage />} />
          <Route path="definitions/:id/edit" element={<DefinitionEditorPage />} />

          {/* Instances */}
          <Route path="instances" element={<InstanceList />} />
          <Route path="instances/:id" element={<InstanceDetailPage />} />

          {/* Tasks */}
          <Route path="tasks/inbox" element={<TaskInbox />} />
          <Route path="tasks/:id" element={<TaskFormPage />} />

          {/* DMN */}
          <Route path="dmn" element={<DmnDefinitionList />} />
          <Route path="dmn/new" element={<DmnEditorPage />} />
          <Route path="dmn/:id" element={<DmnEditorPage />} />
          <Route path="dmn/:id/edit" element={<DmnEditorPage />} />
          <Route path="dmn/:id/evaluate" element={<DmnEvaluatePage />} />
        </Routes>
      </main>
    </div>
  );
}
