import { useState } from "react";

import TicketFilterBar from "../../components/tickets/TicketFilterBar";
import TicketTable from "../../components/tickets/TicketTable";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import RefreshMeta from "../../components/ui/RefreshMeta";
import { useAuth } from "../../context/AuthContext";
import type { SlaState } from "../../lib/sla";
import { useTicketList } from "../../lib/useTicketList";
import type { TicketPriority, TicketStatus } from "../../lib/tickets.types";

export default function AgentTicketsPage() {
  const { accessToken } = useAuth();
  const [status, setStatus] = useState<TicketStatus | "">("");
  const [priority, setPriority] = useState<TicketPriority | "">("");
  const [sla, setSla] = useState<SlaState | "">("");
  const { tickets, isLoading, error, updatedAt, live } = useTicketList(
    accessToken,
    { scope: "assigned", status: status || undefined, priority: priority || undefined },
    sla,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assigned Tickets"
        description="Tickets currently assigned to you."
      />
      <RefreshMeta live={live} updatedAt={updatedAt} staleReason={error} />
      <TicketFilterBar
        status={status}
        priority={priority}
        sla={sla}
        onStatusChange={setStatus}
        onPriorityChange={setPriority}
        onSlaChange={setSla}
      />
      {isLoading ? <LoadingState label="Loading assigned tickets…" /> : null}
      {!isLoading && error && tickets.length === 0 ? (
        <EmptyState title="Unable to load tickets" description={error} />
      ) : null}
      {!isLoading && !error ? (
        <TicketTable
          tickets={tickets}
          detailBasePath="/app/agent/tickets"
          emptyMessage="No assigned tickets."
        />
      ) : null}
    </div>
  );
}
