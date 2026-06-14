import { Link } from "react-router-dom";
import { useAuth } from "../auth";

export function NavBar() {
  const { isAuthenticated, isLoading, userEmail, isPlatformAdmin, login, logout } = useAuth();

  return (
    <nav style={{
      display: "flex",
      alignItems: "center",
      gap: 16,
      padding: "8px 16px",
      borderBottom: "1px solid #e0e0e0",
      background: "#1a1a2e",
      color: "#fff",
    }}>
      <Link to="/" style={{ color: "#fff", textDecoration: "none", fontWeight: "bold" }}>
        GXP
      </Link>

      {isAuthenticated && (
        <>
          <Link to="/apps"      style={navLink}>Apps</Link>
          <Link to="/workflows" style={navLink}>Workflows</Link>
          <Link to="/cases"     style={navLink}>Cases</Link>
          <Link to="/documents" style={navLink}>Documents</Link>
          {isPlatformAdmin && (
            <>
              <Link to="/platform/tenants" style={{ ...navLink, color: "#ffd700" }}>Tenants</Link>
              <Link to="/platform/catalog" style={{ ...navLink, color: "#ffd700" }}>Catalog</Link>
              <Link to="/platform/grants"  style={{ ...navLink, color: "#ffd700" }}>Grants</Link>
            </>
          )}
        </>
      )}

      <span style={{ marginLeft: "auto" }}>
        {isLoading ? null : isAuthenticated ? (
          <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ fontSize: 13, opacity: 0.8 }}>{userEmail}</span>
            <button onClick={logout} style={btnStyle}>Sign Out</button>
          </span>
        ) : (
          <button onClick={login} style={btnStyle}>Sign In</button>
        )}
      </span>
    </nav>
  );
}

const navLink: React.CSSProperties = {
  color: "#ccc",
  textDecoration: "none",
  fontSize: 14,
};

const btnStyle: React.CSSProperties = {
  padding: "4px 12px",
  borderRadius: 4,
  border: "1px solid #ccc",
  background: "transparent",
  color: "#fff",
  cursor: "pointer",
  fontSize: 13,
};
