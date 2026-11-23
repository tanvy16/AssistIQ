import { API_BASE_URL, authFetch } from "./api";
import type { DashboardSummary } from "./dashboard.types";

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

export async function fetchDashboardSummary(
  accessToken: string,
  signal?: AbortSignal,
): Promise<DashboardSummary> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/dashboard/summary`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    credentials: "include",
    signal,
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function formatSlaCompliance(value: number | null): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}%`;
}
