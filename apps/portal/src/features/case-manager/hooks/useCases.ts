import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../../shared/auth/AuthContext";
import { API_BASE } from "../../../shared/api";

const API = `${API_BASE}/api/v1`;

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

// ── Case Types ────────────────────────────────────────────────────────────────

export function useCaseTypes() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["case-types"],
    queryFn: () => apiFetch(`${API}/case-types`, token!),
    enabled: !!token,
  });
}

export function useCreateCaseType() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string; schema?: Record<string, unknown>; default_workflow_id?: string }) =>
      apiFetch(`${API}/case-types`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case-types"] }),
  });
}

// ── Cases ─────────────────────────────────────────────────────────────────────

export function useCases(filters?: { status?: string; assigned_to?: string }) {
  const { token } = useAuth();
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.assigned_to) params.set("assigned_to", filters.assigned_to);
  return useQuery({
    queryKey: ["cases", filters],
    queryFn: () => apiFetch(`${API}/cases?${params}`, token!),
    enabled: !!token,
  });
}

export function useCase(id: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["case", id],
    queryFn: () => apiFetch(`${API}/cases/${id}`, token!),
    enabled: !!token && !!id,
  });
}

export function useCreateCase() {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      case_type_id: string;
      title: string;
      priority?: string;
      metadata?: Record<string, unknown>;
      assigned_to?: string;
    }) => apiFetch(`${API}/cases`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cases"] }),
  });
}

export function useUpdateCase(id: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      title?: string; status?: string; priority?: string;
      metadata?: Record<string, unknown>; assigned_to?: string;
    }) => apiFetch(`${API}/cases/${id}`, token!, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases"] });
      qc.invalidateQueries({ queryKey: ["case", id] });
    },
  });
}

// ── Notes ─────────────────────────────────────────────────────────────────────

export function useCaseNotes(caseId: string | null, includeInternal = false) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["case-notes", caseId, includeInternal],
    queryFn: () =>
      apiFetch(`${API}/cases/${caseId}/notes?include_internal=${includeInternal}`, token!),
    enabled: !!token && !!caseId,
  });
}

export function useAddNote(caseId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { body: string; is_internal?: boolean }) =>
      apiFetch(`${API}/cases/${caseId}/notes`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case-notes", caseId] }),
  });
}

// ── Participants ──────────────────────────────────────────────────────────────

export function useAddParticipant(caseId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { user_id: string; role: string }) =>
      apiFetch(`${API}/cases/${caseId}/participants`, token!, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", caseId] }),
  });
}

export function useRemoveParticipant(caseId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${API}/cases/${caseId}/participants/${userId}`, token!, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", caseId] }),
  });
}

// ── Timeline ──────────────────────────────────────────────────────────────────

export function useCaseTimeline(caseId: string | null) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["case-timeline", caseId],
    queryFn: () => apiFetch(`${API}/cases/${caseId}/timeline`, token!),
    enabled: !!token && !!caseId,
    refetchInterval: 15_000,
  });
}

// ── Links ─────────────────────────────────────────────────────────────────────

export function useLinkDocument(caseId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      apiFetch(`${API}/cases/${caseId}/document-links`, token!, {
        method: "POST",
        body: JSON.stringify({ document_id: documentId }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", caseId] }),
  });
}

export function useStartCaseWorkflow(caseId: string) {
  const { token } = useAuth();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { definition_id: string; label?: string; initial_variables?: Record<string, unknown> }) =>
      apiFetch(`${API}/cases/${caseId}/start-workflow`, token!, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["case", caseId] });
      qc.invalidateQueries({ queryKey: ["case-timeline", caseId] });
    },
  });
}
