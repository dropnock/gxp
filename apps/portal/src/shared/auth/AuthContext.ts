import { createContext, useContext } from "react";

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | undefined;
  userId: string | null;
  userEmail: string | null;
  userRoles: string[];
  tenantSlug: string | null;
  isPlatformAdmin: boolean;
  login: () => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  isLoading: true,
  token: undefined,
  userId: null,
  userEmail: null,
  userRoles: [],
  tenantSlug: null,
  isPlatformAdmin: false,
  login: () => {},
  logout: () => {},
});

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
