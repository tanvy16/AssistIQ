import { API_BASE_URL, authFetch } from "./api";

export type AuditEvent = {
  id: string;
  user_id: string | null;
  event_type: string;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type AuditEventListResponse = {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
};

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // ignore
  }
  return `Request failed (${response.status})`;
}

export async function fetchAuditEvents(
  accessToken: string,
  page = 1,
): Promise<AuditEventListResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/audits?page=${page}&page_size=50`,
    {
      headers: { Authorization: `Bearer ${accessToken}` },
      credentials: "include",
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
