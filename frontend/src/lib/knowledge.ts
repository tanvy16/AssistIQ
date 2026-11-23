import { API_BASE_URL, authFetch } from "./api";
import type {
  KnowledgeDocument,
  KnowledgeDocumentInput,
  KnowledgeDocumentListResponse,
  KnowledgeDocumentStatus,
  KnowledgeSearchResponse,
} from "./knowledge.types";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // ignore
  }
  return `Request failed (${response.status})`;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

export async function fetchKnowledgeDocuments(
  accessToken: string,
  status?: KnowledgeDocumentStatus,
): Promise<KnowledgeDocumentListResponse> {
  const params = status ? `?status=${status}` : "";
  const response = await authFetch(`${API_BASE_URL}/api/v1/knowledge${params}`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchKnowledgeDocument(
  accessToken: string,
  documentId: string,
): Promise<KnowledgeDocument> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/knowledge/${documentId}`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createKnowledgeDocument(
  accessToken: string,
  input: KnowledgeDocumentInput,
): Promise<KnowledgeDocument> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/knowledge`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function updateKnowledgeDocument(
  accessToken: string,
  documentId: string,
  input: Partial<KnowledgeDocumentInput>,
): Promise<KnowledgeDocument> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/knowledge/${documentId}`, {
    method: "PATCH",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function publishKnowledgeDocument(
  accessToken: string,
  documentId: string,
): Promise<KnowledgeDocument> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/knowledge/${documentId}/publish`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function archiveKnowledgeDocument(
  accessToken: string,
  documentId: string,
): Promise<KnowledgeDocument> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/knowledge/${documentId}/archive`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function deleteKnowledgeDocument(
  accessToken: string,
  documentId: string,
): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/knowledge/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function searchKnowledge(
  accessToken: string,
  query: string,
  topK = 5,
): Promise<KnowledgeSearchResponse> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/knowledge/search`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
