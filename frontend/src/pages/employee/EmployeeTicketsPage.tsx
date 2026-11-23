import { useState } from "react";
import { Link } from "react-router-dom";

import TicketFilterBar from "../../components/tickets/TicketFilterBar";
import TicketTable from "../../components/tickets/TicketTable";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import RefreshMeta from "../../components/ui/RefreshMeta";
import { useAuth } from "../../context/AuthContext";
import type { SlaState } from "../../lib/sla";
import { useTicketList } from "../../lib/useTicketList";
import type { TicketPriority, TicketStatus } from "../../lib/tickets.types";

export default function EmployeeTicketsPage() {
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
        title="My Tickets"
        description="Track requests you have submitted to IT support."
        actions={
          <Link to="/app/employee/tickets/new">
            <Button>Create ticket</Button>
          </Link>
        }
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
      {!isLoading && !error && tickets.length === 0 ? (
        <EmptyState
          title={status || priority || sla ? "No matching tickets" : "No tickets yet"}
          description={
            status || priority || sla
              ? "No loaded tickets match the current status, priority, or SLA filter."
              : "Your tickets will appear here once you create a request."
          }
          action={
            status || priority || sla ? undefined : (
              <Link to="/app/employee/tickets/new">
                <Button size="sm">Create ticket</Button>
              </Link>
            )
          }
        />
      ) : null}
      {!isLoading && tickets.length > 0 ? (
        <TicketTable tickets={tickets} detailBasePath="/app/employee/tickets" />
      ) : null}
    </div>
  );
}
