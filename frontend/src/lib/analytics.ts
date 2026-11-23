import { API_BASE_URL, authFetch, parseError } from "./api";

export type AnalyticsWindow = 7 | 14 | 30 | 90;
export const ANALYTICS_WINDOWS: AnalyticsWindow[] = [7, 14, 30, 90];

export type DailyTicketPoint = {
  date: string;
  created: number;
  resolved: number;
  escalations: number;
  chat_tickets: number;
};

export type TicketAnalytics = {
  window_days: number;
  window_start: string;
  generated_at: string;
  status: Record<"open" | "in_progress" | "pending" | "resolved" | "closed", number>;
  active_by_priority: Record<"low" | "medium" | "high" | "critical", number>;
  created_by_category: Record<string, number>;
  sla: {
    active_on_track: number;
    active_at_risk: number;
    active_breached: number;
    resolved_within_sla: number;
    resolved_after_sla: number;
    compliance_pct: number | null;
  };
  totals: { created: number; resolved: number; escalations: number; chat_tickets: number };
  daily: DailyTicketPoint[];
  has_data: boolean;
};

export async function fetchTicketAnalytics(
  accessToken: string,
  days: AnalyticsWindow,
  signal?: AbortSignal,
): Promise<TicketAnalytics> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/analytics/tickets?days=${days}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: "include",
    signal,
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

/** Short axis label for an ISO date (YYYY-MM-DD) without timezone shifting. */
export function shortDayLabel(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

/** True when at least one series has a non-zero value in the window. */
export function hasAnyDailyActivity(points: DailyTicketPoint[], keys: (keyof DailyTicketPoint)[]): boolean {
  return points.some((point) => keys.some((key) => typeof point[key] === "number" && (point[key] as number) > 0));
}
