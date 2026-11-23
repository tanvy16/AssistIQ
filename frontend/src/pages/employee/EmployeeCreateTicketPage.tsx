import { useNavigate } from "react-router-dom";

import TicketForm from "../../components/tickets/TicketForm";
import PageHeader from "../../components/ui/PageHeader";
import { useAuth } from "../../context/AuthContext";
import { createTicket } from "../../lib/tickets";
import type { TicketCreateInput } from "../../lib/tickets.types";

export default function EmployeeCreateTicketPage() {
  const { accessToken } = useAuth();
  const navigate = useNavigate();

  async function handleCreate(input: TicketCreateInput) {
    if (!accessToken) return;
    const ticket = await createTicket(accessToken, input);
    navigate(`/app/employee/tickets/${ticket.id}`);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create ticket"
        description="Submit a new IT support request."
      />
      <TicketForm
        onSubmit={handleCreate}
        onCancel={() => navigate("/app/employee/tickets")}
      />
    </div>
  );
}
