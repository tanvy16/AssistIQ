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

export default function AdminTicketsPage() {
  const { accessToken } = useAuth();
  const [status, setStatus] = useState<TicketStatus | "">("");
  const [priority, setPriority] = useState<TicketPriority | "">("");
  const [sla, setSla] = useState<SlaState | "">("");
  const { tickets, isLoading, error, updatedAt, live } = useTicketList(
    accessToken,
    { status: status || undefined, priority: priority || undefined },
    sla,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ticket Management"
        description="View and manage all support tickets across the organization."
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

      {isLoading ? <LoadingState label="Loading tickets…" /> : null}
      {!isLoading && error && tickets.length === 0 ? (
        <EmptyState title="Unable to load tickets" description={error} />
      ) : null}
      {!isLoading && !error ? (
        <TicketTable
          tickets={tickets}
          detailBasePath="/app/admin/tickets"
          emptyMessage="No tickets match the current filter."
        />
      ) : null}
    </div>
  );
}
