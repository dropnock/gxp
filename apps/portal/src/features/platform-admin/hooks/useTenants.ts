import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAuthHeader } from "../../../shared/auth";
import { API_BASE } from "../../../shared/api";

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  keycloak_realm: string;
  status: "active" | "suspended" | "deprovisioning";
  created_at: string;
  suspended_at: string | null;
}

export interface TenantCreate {
  slug: string;
  name: string;
}

const BASE = `${API_BASE}/api/v1/tenants`;

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function useTenants() {
  return useQuery<Tenant[]>({
    queryKey: ["tenants"],
    queryFn: () => apiFetch(BASE),
  });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TenantCreate) =>
      apiFetch<Tenant>(BASE, { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tenants"] }),
  });
}

export function useSuspendTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      apiFetch<Tenant>(`${BASE}/${slug}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "suspended" }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tenants"] }),
  });
}
