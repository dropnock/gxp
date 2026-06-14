/**
 * ProtectedRoute — redirects to Keycloak login if the user is not authenticated.
 * Shows a loading spinner while keycloak-js is initializing.
 */
import { ReactNode } from "react";
import { useAuth } from "./AuthContext";

interface Props {
  children: ReactNode;
  roles?: string[];
}

export function ProtectedRoute({ children, roles }: Props) {
  const { isLoading, isAuthenticated, login, userRoles } = useAuth();

  if (isLoading) {
    return <div style={{ padding: 32, textAlign: "center" }}>Loading…</div>;
  }

  if (!isAuthenticated) {
    return (
      <div style={{ padding: 32, textAlign: "center" }}>
        <p>You must be signed in to access this page.</p>
        <button onClick={login}>Sign In</button>
      </div>
    );
  }

  if (roles && !roles.some((r) => userRoles.includes(r))) {
    return (
      <div style={{ padding: 32, textAlign: "center", color: "#dc2626" }}>
        <p>You do not have permission to access this page.</p>
        <p style={{ fontSize: 13, color: "#6b7280" }}>Required roles: {roles.join(", ")}</p>
      </div>
    );
  }

  return <>{children}</>;
}
