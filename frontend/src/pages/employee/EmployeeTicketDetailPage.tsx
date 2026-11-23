import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import TicketDetailView from "../../components/tickets/TicketDetailView";
import { useAuth } from "../../context/AuthContext";
import { addTicketComment, fetchTicket } from "../../lib/tickets";
import type { TicketDetail } from "../../lib/tickets.types";

export default function EmployeeTicketDetailPage() {
  const { ticketId = "" } = useParams();
  const { accessToken } = useAuth();
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!accessToken || !ticketId) return;
    setIsLoading(true);
    try {
      setTicket(await fetchTicket(accessToken, ticketId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ticket");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, ticketId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <TicketDetailView
      ticket={ticket}
      isLoading={isLoading}
      error={error}
      canManage={false}
      canComment
      onAddComment={async (body) => {
        if (!accessToken) return;
        await addTicketComment(accessToken, ticketId, body);
        await reload();
      }}
    />
  );
}
