import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../../shared/auth/AuthContext";
import { API_BASE } from "../../../shared/api";

const API = `${API_BASE}/api/v1/apps`;

async function apiFetch(url: string, token: string, opts: RequestInit = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function useApps(status?: string) {
  const { token } = useAuth();
  const params = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["apps", status],
    queryFn: () => apiFetch(`${API}${params}`, token!),
    enabled: !!token,
  });
}

export function useApp(id: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["app", id],
    queryFn: () => apiFetch(`${API}/${id}`, token!),
    enabled: !!token && !!id,
  });
}

export function useAppPages(appId: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["app-pages", appId],
    queryFn: () => apiFetch(`${API}/${appId}/pages`, token!),
    enabled: !!token && !!appId,
  });
}

export function useCreateApp() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      apiFetch(API, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps"] }),
  });
}

export function useUpdateApp(id: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; description?: string }) =>
      apiFetch(`${API}/${id}`, token!, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["apps"] });
      qc.invalidateQueries({ queryKey: ["app", id] });
    },
  });
}

export function useUpsertPage(appId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ pageId, body }: { pageId: string; body: { name: string; route: string; gjs_data: object; styles: object } }) =>
      apiFetch(`${API}/${appId}/pages/${pageId}`, token!, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["app-pages", appId] }),
  });
}

export function useDeletePage(appId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pageId: string) =>
      apiFetch(`${API}/${appId}/pages/${pageId}`, token!, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["app-pages", appId] }),
  });
}

export function useSubmitReview() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appId: string) =>
      apiFetch(`${API}/${appId}/submit-review`, token!, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apps"] }),
  });
}

export function usePublishApp() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appId: string) =>
      apiFetch(`${API}/${appId}/publish`, token!, { method: "POST" }),
    onSuccess: (_data, appId) => {
      qc.invalidateQueries({ queryKey: ["apps"] });
      qc.invalidateQueries({ queryKey: ["app", appId] });
    },
  });
}

export function useAppVersions(appId: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["app-versions", appId],
    queryFn: () => apiFetch(`${API}/${appId}/versions`, token!),
    enabled: !!token && !!appId,
  });
}
