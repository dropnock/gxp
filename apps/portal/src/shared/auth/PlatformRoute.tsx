/**
 * PlatformRoute — restricts access to platform super-admins.
 * Users authenticated against a tenant realm (not gxp-platform) get a 403 page.
 */
import { ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

interface Props {
  children: ReactNode;
}

export function PlatformRoute({ children }: Props) {
  return (
    <ProtectedRoute>
      <PlatformGuard>{children}</PlatformGuard>
    </ProtectedRoute>
  );
}

function PlatformGuard({ children }: Props) {
  const { isPlatformAdmin } = useAuth();

  if (!isPlatformAdmin) {
    return (
      <div style={{ padding: 32, textAlign: "center" }}>
        <h2>Access Denied</h2>
        <p>This section requires platform administrator privileges.</p>
      </div>
    );
  }

  return <>{children}</>;
}
