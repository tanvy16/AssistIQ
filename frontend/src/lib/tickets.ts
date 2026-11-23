import { API_BASE_URL, authFetch } from "./api";
import { memoryInvalidate } from "./queryMemory";
import type {
  TicketCreateInput,
  TicketDetail,
  TicketFilters,
  TicketListResponse,
  TicketStatus,
  TicketPriority,
} from "./tickets.types";

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

function buildQuery(filters: TicketFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.category) params.set("category", filters.category);
  if (filters.scope) params.set("scope", filters.scope);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function invalidateTicketQueries(): void {
  memoryInvalidate("tickets:");
  memoryInvalidate("dashboard:");
}

export async function fetchTickets(
  accessToken: string,
  filters: TicketFilters = {},
  signal?: AbortSignal,
): Promise<TicketListResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/tickets${buildQuery(filters)}`,
    { headers: authHeaders(accessToken), credentials: "include", signal },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchTicket(
  accessToken: string,
  ticketId: string,
): Promise<TicketDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/tickets/${ticketId}`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createTicket(
  accessToken: string,
  input: TicketCreateInput,
): Promise<TicketDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/tickets`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidateTicketQueries();
  return response.json();
}

export async function updateTicket(
  accessToken: string,
  ticketId: string,
  data: { status?: TicketStatus; priority?: TicketPriority },
): Promise<TicketDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/tickets/${ticketId}`, {
    method: "PATCH",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidateTicketQueries();
  return response.json();
}

export async function assignTicket(
  accessToken: string,
  ticketId: string,
): Promise<TicketDetail> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/tickets/${ticketId}/assign`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
      body: JSON.stringify({}),
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  invalidateTicketQueries();
  return response.json();
}

export async function unassignTicket(
  accessToken: string,
  ticketId: string,
): Promise<TicketDetail> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/tickets/${ticketId}/unassign`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  invalidateTicketQueries();
  return response.json();
}

export async function addTicketComment(
  accessToken: string,
  ticketId: string,
  body: string,
): Promise<void> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/tickets/${ticketId}/comments`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
      body: JSON.stringify({ body }),
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  invalidateTicketQueries();
}
