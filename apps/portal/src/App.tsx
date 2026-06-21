import { Routes, Route } from "react-router-dom";
import { TenantListPage } from "./features/platform-admin/components/TenantListPage";
import { CatalogPage } from "./features/platform-admin/components/CatalogPage";
import { CrossTenantGrantsPage } from "./features/platform-admin/components/CrossTenantGrantsPage";
import { DocumentManagerPage } from "./features/document-manager";
import { WorkflowEditorPage } from "./features/workflow-editor";
import { CaseManagerPage } from "./features/case-manager";
import { AppBuilderPage } from "./features/app-builder";
import { AuditPage } from "./features/audit";
import { ProtectedRoute, PlatformRoute } from "./shared/auth";
import { NavBar, SystemNotices } from "./shared/components";
import { LandingPage } from "./pages/LandingPage";

export default function App() {
  return (
    <>
      <NavBar />
      <SystemNotices />
      <Routes>
        {/* Public */}
        <Route path="/" element={<LandingPage />} />

        {/* Tenant-authenticated */}
        <Route path="/apps/*"      element={<ProtectedRoute><AppBuilderPage /></ProtectedRoute>} />
        <Route path="/workflows/*" element={<ProtectedRoute><WorkflowEditorPage /></ProtectedRoute>} />
        <Route path="/cases/*"     element={<ProtectedRoute><CaseManagerPage /></ProtectedRoute>} />
        <Route path="/documents"   element={<ProtectedRoute><DocumentManagerPage /></ProtectedRoute>} />
        <Route path="/audit/*"     element={<ProtectedRoute roles={["gxp-auditor", "gxp-admin"]}><AuditPage /></ProtectedRoute>} />

        {/* Platform super-admin */}
        <Route path="/platform/tenants" element={<PlatformRoute><TenantListPage /></PlatformRoute>} />
        <Route path="/platform/catalog" element={<PlatformRoute><CatalogPage /></PlatformRoute>} />
        <Route path="/platform/grants"  element={<PlatformRoute><CrossTenantGrantsPage /></PlatformRoute>} />
      </Routes>
    </>
  );
}
