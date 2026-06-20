import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAuthHeader } from "../../../shared/auth";
import { API_BASE } from "../../../shared/api";

export interface CrossTenantGrant {
  id: string;
  requesting_tenant_id: string;
  granting_tenant_id: string;
  resource_type: string;
  resource_id: string;
  permissions: string[];
  status: "pending" | "approved" | "revoked" | "expired";
  expires_at: string | null;
  created_at: string;
  approved_at: string | null;
}

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
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

const BASE = `${API_BASE}/api/v1/tenants`;

export function useGrants(tenantSlug: string | null) {
  return useQuery<CrossTenantGrant[]>({
    queryKey: ["grants", tenantSlug],
    queryFn: () => apiFetch(`${BASE}/${tenantSlug}/cross-tenant-grants`),
    enabled: !!tenantSlug,
  });
}

export function useApproveGrant(tenantSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (grantId: string) =>
      apiFetch<CrossTenantGrant>(`${BASE}/${tenantSlug}/cross-tenant-grants/${grantId}/approve`, {
        method: "POST",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grants"] }),
  });
}

export function useRevokeGrant(tenantSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (grantId: string) =>
      apiFetch<null>(`${BASE}/${tenantSlug}/cross-tenant-grants/${grantId}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grants"] }),
  });
}
