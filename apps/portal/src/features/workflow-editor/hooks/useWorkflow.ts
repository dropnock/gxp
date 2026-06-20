import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../../shared/auth/AuthContext";
import { API_BASE } from "../../../shared/api";

const API = `${API_BASE}/api/v1/workflow`;

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

// ── BPMN Definitions ──────────────────────────────────────────────────────────

export function useDefinitions(activeOnly = true) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["workflow-definitions", activeOnly],
    queryFn: () => apiFetch(`${API}/definitions?active_only=${activeOnly}`, token!),
    enabled: !!token,
  });
}

export function useDefinition(id: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["workflow-definition", id],
    queryFn: () => apiFetch(`${API}/definitions/${id}`, token!),
    enabled: !!token && !!id,
  });
}

export function useCreateDefinition() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string; xml_content: string }) =>
      apiFetch(`${API}/definitions`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflow-definitions"] }),
  });
}

export function useUpdateDefinition(id: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; description?: string; xml_content?: string }) =>
      apiFetch(`${API}/definitions/${id}`, token!, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      qc.invalidateQueries({ queryKey: ["workflow-definition", id] });
    },
  });
}

export function useDeleteDefinition() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`${API}/definitions/${id}`, token!, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflow-definitions"] }),
  });
}

// ── DMN Definitions ───────────────────────────────────────────────────────────

export function useDmnDefinitions(activeOnly = true) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["dmn-definitions", activeOnly],
    queryFn: () => apiFetch(`${API}/dmn-definitions?active_only=${activeOnly}`, token!),
    enabled: !!token,
  });
}

export function useDmnDefinition(id: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["dmn-definition", id],
    queryFn: () => apiFetch(`${API}/dmn-definitions/${id}`, token!),
    enabled: !!token && !!id,
  });
}

export function useCreateDmnDefinition() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string; xml_content: string }) =>
      apiFetch(`${API}/dmn-definitions`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dmn-definitions"] }),
  });
}

export function useUpdateDmnDefinition(id: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name?: string; description?: string; xml_content?: string }) =>
      apiFetch(`${API}/dmn-definitions/${id}`, token!, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dmn-definitions"] });
      qc.invalidateQueries({ queryKey: ["dmn-definition", id] });
    },
  });
}

export function useEvaluateDmn(id: string) {
  const { token } = useAuth();
  return useMutation({
    mutationFn: (input_data: Record<string, unknown>) =>
      apiFetch(`${API}/dmn-definitions/${id}/evaluate`, token!, {
        method: "POST",
        body: JSON.stringify({ input_data }),
      }),
  });
}

// ── Instances ─────────────────────────────────────────────────────────────────

export function useInstances(status?: string, definitionId?: string) {
  const { token } = useAuth();
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (definitionId) params.set("definition_id", definitionId);
  return useQuery({
    queryKey: ["workflow-instances", status, definitionId],
    queryFn: () => apiFetch(`${API}/instances?${params}`, token!),
    enabled: !!token,
  });
}

export function useInstance(id: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["workflow-instance", id],
    queryFn: () => apiFetch(`${API}/instances/${id}`, token!),
    enabled: !!token && !!id,
    refetchInterval: (query) => {
      const data = query.state.data as { status?: string } | undefined;
      return data?.status === "running" || data?.status === "waiting" ? 3000 : false;
    },
  });
}

export function useStartInstance() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      definition_id: string;
      initial_variables?: Record<string, unknown>;
      case_id?: string;
    }) =>
      apiFetch(`${API}/instances`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflow-instances"] }),
  });
}

export function useCancelInstance() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`${API}/instances/${id}/cancel`, token!, { method: "POST" }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["workflow-instances"] });
      qc.invalidateQueries({ queryKey: ["workflow-instance", id] });
    },
  });
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export function useInbox() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["workflow-inbox"],
    queryFn: () => apiFetch(`${API}/tasks/inbox`, token!),
    enabled: !!token,
    refetchInterval: 30_000,
  });
}

export function useTask(id: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["workflow-task", id],
    queryFn: () => apiFetch(`${API}/tasks/${id}`, token!),
    enabled: !!token && !!id,
  });
}

export function useClaimTask() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`${API}/tasks/${id}/claim`, token!, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-inbox"] });
      qc.invalidateQueries({ queryKey: ["workflow-task"] });
    },
  });
}

export function useCompleteTask() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, completion_data }: { id: string; completion_data: Record<string, unknown> }) =>
      apiFetch(`${API}/tasks/${id}/complete`, token!, {
        method: "POST",
        body: JSON.stringify({ completion_data }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-inbox"] });
      qc.invalidateQueries({ queryKey: ["workflow-instances"] });
    },
  });
}
