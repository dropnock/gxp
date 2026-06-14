import { NavLink, Route, Routes } from "react-router-dom";
import { AuditSummaryPage } from "./AuditSummaryPage";
import { ActorActivityPage } from "./ActorActivityPage";
import { FailedActionsPage } from "./FailedActionsPage";

const NAV = [
  { to: "/audit", label: "Activity Summary", end: true },
  { to: "/audit/actor", label: "Actor Lookup" },
  { to: "/audit/failures", label: "Failed Actions" },
];

export function AuditPage() {
  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)" }}>
      <nav style={{ width: 200, borderRight: "1px solid #e5e7eb", padding: "20px 0", background: "#f9fafb", flexShrink: 0 }}>
        <div style={{ padding: "0 16px 16px", fontWeight: 700, fontSize: 12, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Audit &amp; Compliance
        </div>
        {NAV.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
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
      <main style={{ flex: 1, overflow: "auto", padding: 28 }}>
        <Routes>
          <Route index element={<AuditSummaryPage />} />
          <Route path="actor" element={<ActorActivityPage />} />
          <Route path="failures" element={<FailedActionsPage />} />
        </Routes>
      </main>
    </div>
  );
}
