import { NavLink, Routes, Route } from "react-router-dom";
import { CaseList } from "./CaseList";
import { CaseCreatePage } from "./CaseCreatePage";
import { CaseDetailPage } from "./CaseDetailPage";

const navItems = [
  { label: "All Cases", to: "/cases" },
  { label: "My Cases", to: "/cases?assigned_to=me" },
];

export function CaseManagerPage() {
  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)" }}>
      {/* Sidebar */}
      <nav style={{
        width: 180, borderRight: "1px solid #e5e7eb", padding: "20px 0",
        background: "#f9fafb", flexShrink: 0,
      }}>
        <div style={{ padding: "0 16px 16px", fontWeight: 700, fontSize: 13, color: "#374151" }}>
          CASES
        </div>
        {navItems.map(({ label, to }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/cases"}
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
          <Route index element={<CaseList />} />
          <Route path="new" element={<CaseCreatePage />} />
          <Route path=":id" element={<CaseDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
