import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getAuthHeader } from "../../../shared/auth";

export interface Folder {
  id: string;
  parent_id: string | null;
  name: string;
  path: string;
  created_by: string;
  created_at: string;
}

export interface Document {
  id: string;
  folder_id: string | null;
  name: string;
  description: string | null;
  mime_type: string | null;
  tags: string[];
  current_version_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  size_bytes: number | null;
  checksum_sha256: string | null;
  av_status: "pending" | "scanning" | "clean" | "infected" | "error";
  av_scanned_at: string | null;
  uploaded_by: string;
  uploaded_at: string;
}

const BASE = "/api/v1/documents";

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { ...getAuthHeader(), ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Folders ──────────────────────────────────────────────────────────────────

export function useFolders(parentId: string | null = null) {
  const params = parentId ? `?parent_id=${parentId}` : "";
  return useQuery<Folder[]>({
    queryKey: ["folders", parentId],
    queryFn: () => apiFetch(`${BASE}/folders${params}`),
  });
}

export function useCreateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; parent_id?: string | null }) =>
      apiFetch<Folder>(`${BASE}/folders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    onSuccess: (_, vars) => qc.invalidateQueries({ queryKey: ["folders", vars.parent_id ?? null] }),
  });
}

// ── Documents ─────────────────────────────────────────────────────────────────

export function useDocuments(folderId: string | null = null) {
  const params = folderId ? `?folder_id=${folderId}` : "";
  return useQuery<Document[]>({
    queryKey: ["documents", folderId],
    queryFn: () => apiFetch(`${BASE}${params}`),
  });
}

export function useDocument(documentId: string | undefined) {
  return useQuery<Document>({
    queryKey: ["document", documentId],
    queryFn: () => apiFetch(`${BASE}/${documentId}`),
    enabled: !!documentId,
    refetchInterval: (query) => {
      // Poll while the current version is still being scanned
      const data = query.state.data as Document | undefined;
      return data && !data.current_version_id ? 3000 : false;
    },
  });
}

export function useDocumentVersions(documentId: string | undefined) {
  return useQuery<DocumentVersion[]>({
    queryKey: ["document-versions", documentId],
    queryFn: () => apiFetch(`${BASE}/${documentId}/versions`),
    enabled: !!documentId,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      folderId,
      description,
      tags,
    }: {
      file: File;
      folderId?: string | null;
      description?: string;
      tags?: string[];
    }) => {
      const form = new FormData();
      form.append("file", file);
      if (folderId) form.append("folder_id", folderId);
      if (description) form.append("description", description);
      if (tags?.length) form.append("tags", tags.join(","));

      const res = await fetch(BASE, {
        method: "POST",
        headers: { ...getAuthHeader() },
        body: form,
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    onSuccess: (_, vars) =>
      qc.invalidateQueries({ queryKey: ["documents", vars.folderId ?? null] }),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      fetch(`${BASE}/${documentId}`, {
        method: "DELETE",
        headers: { ...getAuthHeader() },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });
}

// ── Search ────────────────────────────────────────────────────────────────────

export interface SearchResult {
  document_id: string;
  name: string;
  score: number;
  mime_type?: string;
}

export function useDocumentSearch(query: string, tags?: string[]) {
  const params = new URLSearchParams({ q: query });
  if (tags?.length) params.set("tags", tags.join(","));

  return useQuery<SearchResult[]>({
    queryKey: ["document-search", query, tags],
    queryFn: () => apiFetch<SearchResult[]>(`${BASE}/search?${params}`),
    enabled: query.length > 1,
  });
}
