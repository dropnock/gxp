import { useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { LogOut, ChevronRight, Menu, X } from "lucide-react";
import { useAuth } from "../auth";

const TENANT_LINKS = [
  { to: "/apps",      label: "Apps" },
  { to: "/workflows", label: "Workflows" },
  { to: "/cases",     label: "Cases" },
  { to: "/documents", label: "Documents" },
  { to: "/audit",     label: "Audit" },
] as const;

const PLATFORM_LINKS = [
  { to: "/platform/tenants", label: "Tenants" },
  { to: "/platform/catalog", label: "Catalog" },
  { to: "/platform/grants",  label: "Grants" },
] as const;

export function NavBar() {
  const { isAuthenticated, isLoading, userEmail, isPlatformAdmin, login, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const links = isPlatformAdmin ? PLATFORM_LINKS : TENANT_LINKS;

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "nav__link nav__link--active" : "nav__link";

  const drawerLinkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "nav__drawer-link nav__drawer-link--active" : "nav__drawer-link";

  return (
    <header className="nav">
      <div className="nav__bar container">
        <Link to="/" className="nav__logo" aria-label="GXP home">
          {isPlatformAdmin ? "GXP Platform" : "GXP"}
        </Link>

        {isAuthenticated && !isLoading && (
          <nav className="nav__links" aria-label="Main navigation">
            {links.map(({ to, label }) => (
              <NavLink key={to} to={to} className={linkClass}>
                {label}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="nav__right">
          {!isLoading && (
            isAuthenticated ? (
              <>
                <span className="nav__email" title={userEmail ?? undefined}>
                  {userEmail}
                </span>
                <div className="nav__divider" aria-hidden="true" />
                <button
                  onClick={logout}
                  className="nav__btn nav__btn--ghost"
                  aria-label="Sign out"
                >
                  <LogOut size={15} aria-hidden="true" />
                  <span>Sign Out</span>
                </button>
              </>
            ) : (
              <button
                onClick={login}
                className="nav__btn nav__btn--primary"
              >
                Sign In
                <ChevronRight size={15} aria-hidden="true" />
              </button>
            )
          )}

          {isAuthenticated && !isLoading && (
            <button
              onClick={() => setDrawerOpen((o) => !o)}
              className="nav__toggle"
              aria-label={drawerOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={drawerOpen}
              aria-controls="nav-drawer"
            >
              {drawerOpen
                ? <X size={20} aria-hidden="true" />
                : <Menu size={20} aria-hidden="true" />
              }
            </button>
          )}
        </div>
      </div>

      {isAuthenticated && !isLoading && (
        <nav
          id="nav-drawer"
          className={`nav__drawer${drawerOpen ? " is-open" : ""}`}
          aria-label="Mobile navigation"
          aria-hidden={!drawerOpen}
        >
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={drawerLinkClass}
              onClick={() => setDrawerOpen(false)}
            >
              {label}
            </NavLink>
          ))}
          <div className="nav__drawer-sep" aria-hidden="true" />
          {userEmail && (
            <p className="nav__drawer-email">{userEmail}</p>
          )}
          <button className="nav__drawer-signout" onClick={logout}>
            Sign Out
          </button>
        </nav>
      )}
    </header>
  );
}
