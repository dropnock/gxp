/**
 * AuthProvider — initializes keycloak-js and provides auth state to the app.
 *
 * Initialization uses `check-sso` so that users are not forced into a login
 * redirect if they load the app without an active session (they'll see the
 * login button instead). Routes that require auth use <ProtectedRoute />.
 *
 * Token refresh: keycloak-js handles silent refresh automatically when
 * `onTokenExpired` fires. We also set a 60-second early-refresh interval.
 */
import { ReactNode, useEffect, useRef, useState } from "react";
import { keycloak } from "./keycloak";
import { AuthContext, AuthState } from "./AuthContext";

function parseSlugFromIssuer(issuer: string | undefined): string | null {
  if (!issuer) return null;
  const realm = issuer.split("/").at(-1) ?? "";
  if (realm.startsWith("gxp-") && realm !== "gxp-platform") {
    return realm.slice("gxp-".length);
  }
  return null;
}

interface Props {
  children: ReactNode;
}

export function AuthProvider({ children }: Props) {
  const [state, setState] = useState<Omit<AuthState, "login" | "logout">>({
    isAuthenticated: false,
    isLoading: true,
    token: undefined,
    userId: null,
    userEmail: null,
    userRoles: [],
    tenantSlug: null,
    isPlatformAdmin: false,
  });

  const initialized = useRef(false);

  function buildState(): Omit<AuthState, "login" | "logout"> {
    const parsed = keycloak.tokenParsed;
    const issuer: string | undefined = parsed?.iss;
    const roles: string[] = (parsed?.realm_access as { roles?: string[] })?.roles ?? [];
    return {
      isAuthenticated: keycloak.authenticated ?? false,
      isLoading: false,
      token: keycloak.token,
      userId: (parsed?.sub as string) ?? null,
      userEmail: (parsed?.email as string) ?? null,
      userRoles: roles,
      tenantSlug: parseSlugFromIssuer(issuer),
      isPlatformAdmin: roles.includes("gxp-platform-admin"),
    };
  }

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    keycloak
      .init({
        onLoad: "check-sso",
        silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
        pkceMethod: "S256",
        checkLoginIframe: false,
      })
      .then(() => {
        setState(buildState());
      })
      .catch((err) => {
        console.error("Keycloak init failed:", err);
        setState((prev) => ({ ...prev, isLoading: false }));
      });

    keycloak.onTokenExpired = () => {
      keycloak.updateToken(60).then(() => setState(buildState())).catch(() => {
        keycloak.logout();
      });
    };

    keycloak.onAuthSuccess = () => setState(buildState());
    keycloak.onAuthLogout = () =>
      setState({
        isAuthenticated: false,
        isLoading: false,
        token: undefined,
        userId: null,
        userEmail: null,
        userRoles: [],
        tenantSlug: null,
        isPlatformAdmin: false,
      });
  }, []);

  const value: AuthState = {
    ...state,
    login: () => keycloak.login(),
    logout: () => keycloak.logout({ redirectUri: window.location.origin }),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
