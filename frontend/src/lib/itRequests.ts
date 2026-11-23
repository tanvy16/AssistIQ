import { API_BASE_URL, authFetch } from "./api";
import type {
  AccessCatalogItem,
  ITRequestDetail,
  ITRequestEvent,
  ITRequestListItem,
  RunbookItem,
  SoftwareCatalogItem,
} from "./itRequests.types";
import { memoryInvalidate, memoryLoad } from "./queryMemory";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") return payload.detail;
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

function invalidateITRequestQueries(): void {
  memoryInvalidate("it-requests:");
}

export async function createITRequest(accessToken: string, message: string): Promise<ITRequestDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ message }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidateITRequestQueries();
  return response.json();
}

export async function fetchITRequests(
  accessToken: string,
  options: { force?: boolean } = {},
): Promise<{ items: ITRequestListItem[]; total: number }> {
  return memoryLoad(
    `it-requests:${accessToken}`,
    async () => {
      const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests`, {
        headers: authHeaders(accessToken),
        credentials: "include",
      });
      if (!response.ok) throw new Error(await parseError(response));
      return response.json();
    },
    { ttlMs: 15_000, force: options.force },
  );
}

export async function fetchITRequest(accessToken: string, id: string): Promise<ITRequestDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/${id}`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchITRequestEvents(
  accessToken: string,
  id: string,
): Promise<ITRequestEvent[]> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/${id}/events`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function approveITRequest(accessToken: string, id: string, comment?: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/${id}/approve`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ comment }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidateITRequestQueries();
  return response.json();
}

export async function rejectITRequest(accessToken: string, id: string, comment?: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/${id}/reject`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ comment }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidateITRequestQueries();
  return response.json();
}

export async function cancelITRequest(accessToken: string, id: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/${id}/cancel`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidateITRequestQueries();
  return response.json();
}

export async function fetchSoftwareCatalog(accessToken: string): Promise<SoftwareCatalogItem[]> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/catalog/software`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchAccessCatalog(accessToken: string): Promise<AccessCatalogItem[]> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/catalog/access`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchRunbooks(accessToken: string): Promise<RunbookItem[]> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/it-requests/runbooks`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function statusExplanation(status: string): string {
  switch (status) {
    case "approval_required":
      return "This request requires manager or admin approval before a simulated action can proceed.";
    case "completed":
      return "Simulation completed successfully. No real software was installed and no real access was changed.";
    case "escalated":
      return "This request was sent for human review and was not executed.";
    case "rejected":
      return "Policy denied this request. The resource may be missing from the approved catalog.";
    case "rolled_back":
      return "The simulated action failed validation and was rolled back.";
    case "cancelled":
      return "This request was cancelled before execution.";
    default:
      return "The request is being processed by the IT workflow.";
  }
}
