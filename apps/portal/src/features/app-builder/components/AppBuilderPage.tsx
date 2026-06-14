import { NavLink, Route, Routes } from "react-router-dom";
import { AppList } from "./AppList";
import { AppCreatePage } from "./AppCreatePage";
import { AppEditorPage } from "./AppEditorPage";

export function AppBuilderPage() {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Left nav — hidden on the full-screen editor */}
      <Routes>
        <Route
          path=":id/edit"
          element={null}
        />
        <Route
          path="*"
          element={
            <nav style={{ width: 220, borderRight: "1px solid #e5e7eb", background: "#f9fafb", padding: "24px 0", display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
              <div style={{ padding: "0 16px 16px", fontWeight: 700, fontSize: 14, color: "#374151" }}>
                App Builder
              </div>
              <NavItem to="/apps" end>All Apps</NavItem>
            </nav>
          }
        />
      </Routes>

      {/* Main content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        <Routes>
          <Route index element={<div style={{ padding: 32 }}><AppList /></div>} />
          <Route path="new" element={<div style={{ padding: 32 }}><AppCreatePage /></div>} />
          <Route path=":id/edit" element={<AppEditorPage />} />
        </Routes>
      </div>
    </div>
  );
}

function NavItem({ to, end, children }: { to: string; end?: boolean; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={end}
      style={({ isActive }) => ({
        display: "block",
        padding: "8px 16px",
        fontSize: 14,
        textDecoration: "none",
        color: isActive ? "#2563eb" : "#374151",
        background: isActive ? "#eff6ff" : "transparent",
        borderLeft: isActive ? "3px solid #2563eb" : "3px solid transparent",
      })}
    >
      {children}
    </NavLink>
  );
}
