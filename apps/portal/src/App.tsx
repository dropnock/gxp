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
import { NavBar } from "./shared/components/NavBar";

export default function App() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<div style={{ padding: 32 }}>GXP Portal</div>} />

        {/* Tenant-authenticated routes */}
        <Route path="/apps/*"          element={<ProtectedRoute><AppBuilderPage /></ProtectedRoute>} />
        <Route path="/workflows/*"    element={<ProtectedRoute><WorkflowEditorPage /></ProtectedRoute>} />
        <Route path="/cases/*"         element={<ProtectedRoute><CaseManagerPage /></ProtectedRoute>} />
        <Route path="/documents"      element={<ProtectedRoute><DocumentManagerPage /></ProtectedRoute>} />
        <Route path="/audit/*"        element={<ProtectedRoute roles={["gxp-auditor", "gxp-admin"]}><AuditPage /></ProtectedRoute>} />
        <Route path="/admin"          element={<ProtectedRoute><div>Admin</div></ProtectedRoute>} />

        {/* Platform super-admin routes — require gxp-platform realm + gxp-platform-admin role */}
        <Route path="/platform/tenants" element={<PlatformRoute><TenantListPage /></PlatformRoute>} />
        <Route path="/platform/catalog" element={<PlatformRoute><CatalogPage /></PlatformRoute>} />
        <Route path="/platform/grants"  element={<PlatformRoute><CrossTenantGrantsPage /></PlatformRoute>} />
      </Routes>
    </>
  );
}
