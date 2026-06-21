import { ReactNode } from "react";
import { Lock, ShieldOff } from "lucide-react";
import { useAuth } from "./AuthContext";

interface Props {
  children: ReactNode;
  roles?: string[];
}

export function ProtectedRoute({ children, roles }: Props) {
  const { isLoading, isAuthenticated, login, userRoles } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-gate">
        <div className="spinner" role="status" aria-label="Authenticating" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-gate">
        <div className="auth-gate__icon auth-gate__icon--blue">
          <Lock size={24} aria-hidden="true" />
        </div>
        <h1 className="auth-gate__title">Sign in required</h1>
        <p className="auth-gate__body">
          You need to be signed in to access this page.
        </p>
        <button onClick={login} className="btn btn--primary">
          Sign In
        </button>
      </div>
    );
  }

  if (roles && !roles.some((r) => userRoles.includes(r))) {
    return (
      <div className="auth-gate">
        <div className="auth-gate__icon auth-gate__icon--red">
          <ShieldOff size={24} aria-hidden="true" />
        </div>
        <h1 className="auth-gate__title">Access denied</h1>
        <p className="auth-gate__body">
          You do not have the required role to access this page. Contact your
          administrator if you believe this is incorrect.
        </p>
        <p className="auth-gate__meta">Required: {roles.join(", ")}</p>
      </div>
    );
  }

  return <>{children}</>;
}
