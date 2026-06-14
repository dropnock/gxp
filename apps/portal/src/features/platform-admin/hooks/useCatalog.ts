import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAuthHeader } from "../../../shared/auth";

export interface CatalogTemplate {
  id: string;
  category: "app" | "workflow" | "dmn" | "case_type";
  name: string;
  description: string | null;
  version: string;
  tags: string[] | null;
  published_at: string;
  is_active: boolean;
}

export interface CatalogTemplateCreate {
  category: "app" | "workflow" | "dmn" | "case_type";
  name: string;
  description?: string;
  schema_json: object;
  tags?: string[];
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

const BASE = "/api/v1/catalog";

export function useCatalog(category?: string) {
  const params = category ? `?category=${category}` : "";
  return useQuery<CatalogTemplate[]>({
    queryKey: ["catalog", category],
    queryFn: () => apiFetch(`${BASE}${params}`),
  });
}

export function usePublishTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CatalogTemplateCreate) =>
      apiFetch<CatalogTemplate>(BASE, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalog"] }),
  });
}

export function useDeactivateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      apiFetch<null>(`${BASE}/${templateId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalog"] }),
  });
}

export function useForkTemplate() {
  return useMutation({
    mutationFn: (templateId: string) =>
      apiFetch<unknown>(`${BASE}/${templateId}/fork`, { method: "POST" }),
  });
}
