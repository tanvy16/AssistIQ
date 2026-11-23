import { useMemo } from "react";

import { getSlaState, type SlaState } from "./sla";
import { fetchTickets } from "./tickets";
import { usePolledQuery } from "./usePolledQuery";
import type { TicketFilters, TicketListItem } from "./tickets.types";

const POLL_MS = 20_000;
const TTL_MS = 15_000;

export function useTicketList(
  accessToken: string | null,
  filters: TicketFilters,
  sla: SlaState | "" = "",
) {
  const scope = filters.scope ?? "";
  const status = filters.status ?? "";
  const priority = filters.priority ?? "";
  const page = filters.page ?? 1;
  const pageSize = filters.page_size ?? 20;
  const cacheKey = `tickets:${accessToken ?? "anon"}:${scope}:${status}:${priority}:${page}:${pageSize}`;

  const { data, error, isLoading, updatedAt, live, refresh } = usePolledQuery<TicketListItem[]>({
    enabled: Boolean(accessToken),
    cacheKey,
    intervalMs: POLL_MS,
    ttlMs: TTL_MS,
    fetcher: async (signal) => {
      const response = await fetchTickets(
        accessToken as string,
        { scope: filters.scope, status: filters.status, priority: filters.priority, page, page_size: pageSize },
        signal,
      );
      return response.items;
    },
  });

  const tickets = data ?? [];
  const visibleTickets = useMemo(() => {
    if (!sla) return tickets;
    return tickets.filter((ticket) => getSlaState(ticket.sla_due_at) === sla);
  }, [tickets, sla]);

  return { tickets: visibleTickets, error, isLoading, updatedAt, live, refresh };
}
