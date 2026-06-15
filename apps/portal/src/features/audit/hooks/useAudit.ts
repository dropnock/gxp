import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../../shared/auth/AuthContext";

const BASE = "/api/v1/audit";

async function apiFetch(url: string, token: string) {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

export function useAuditSummary(since?: string, until?: string) {
  const { token } = useAuth();
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (until) params.set("until", until);
  const qs = params.toString() ? `?${params}` : "";
  return useQuery({
    queryKey: ["audit-summary", since, until],
    queryFn: () => apiFetch(`${BASE}/reports/summary${qs}`, token!),
    enabled: !!token,
  });
}

export function useActorActivity(actorId: string | null, since?: string, until?: string) {
  const { token } = useAuth();
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (until) params.set("until", until);
  params.set("limit", "200");
  return useQuery({
    queryKey: ["audit-actor", actorId, since, until],
    queryFn: () => apiFetch(`${BASE}/reports/actor-activity?actor_id=${actorId}&${params}`, token!),
    enabled: !!token && !!actorId,
  });
}

export function useFailedActions(since?: string, until?: string) {
  const { token } = useAuth();
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (until) params.set("until", until);
  params.set("limit", "100");
  const qs = params.toString() ? `?${params}` : "";
  return useQuery({
    queryKey: ["audit-failed", since, until],
    queryFn: () => apiFetch(`${BASE}/reports/failed-actions${qs}`, token!),
    enabled: !!token,
    refetchInterval: 60_000,
  });
}

export function useAuditEvents(filters: {
  tenant_slug?: string;
  service?: string;
  event_type?: string;
  actor_id?: string;
  since?: string;
  until?: string;
  limit?: number;
}) {
  const { token } = useAuth();
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") params.set(k, String(v));
  });
  return useQuery({
    queryKey: ["audit-events", filters],
    queryFn: () => apiFetch(`${BASE}/events?${params}`, token!),
    enabled: !!token,
  });
}
