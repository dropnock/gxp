import { ReactNode } from "react";
import { ShieldOff } from "lucide-react";
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
      <div className="auth-gate">
        <div className="auth-gate__icon auth-gate__icon--red">
          <ShieldOff size={24} aria-hidden="true" />
        </div>
        <h1 className="auth-gate__title">Platform access only</h1>
        <p className="auth-gate__body">
          This section is restricted to platform administrators and cannot be
          accessed from a tenant account.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
