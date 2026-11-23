import { FormEvent, useState } from "react";

import Alert from "../ui/Alert";
import Button from "../ui/Button";
import Input from "../ui/Input";
import Panel from "../ui/Panel";
import { categoryLabels, priorityLabels } from "../../lib/ticketLabels";
import type {
  TicketCategory,
  TicketCreateInput,
  TicketPriority,
} from "../../lib/tickets.types";

type TicketFormProps = {
  onSubmit: (input: TicketCreateInput) => Promise<void>;
  onCancel?: () => void;
};

const categories = Object.keys(categoryLabels) as TicketCategory[];
const priorities = Object.keys(priorityLabels) as TicketPriority[];

export default function TicketForm({ onSubmit, onCancel }: TicketFormProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<TicketCategory>("software");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ title, description, category, priority });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Panel title="Create ticket">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <Input
          label="Title"
          id="ticket-title"
          required
          minLength={3}
          maxLength={200}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />

        <div className="space-y-1">
          <label htmlFor="ticket-description" className="block text-sm font-medium text-ink">
            Description
          </label>
          <textarea
            id="ticket-description"
            required
            minLength={10}
            rows={5}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="field-control"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <label htmlFor="ticket-category" className="block text-sm font-medium text-ink">
              Category
            </label>
            <select
              id="ticket-category"
              value={category}
              onChange={(event) => setCategory(event.target.value as TicketCategory)}
              className="field-control"
            >
              {categories.map((value) => (
                <option key={value} value={value}>
                  {categoryLabels[value]}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label htmlFor="ticket-priority" className="block text-sm font-medium text-ink">
              Priority
            </label>
            <select
              id="ticket-priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value as TicketPriority)}
              className="field-control"
            >
              {priorities.map((value) => (
                <option key={value} value={value}>
                  {priorityLabels[value]}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error ? <Alert>{error}</Alert> : null}

        <div className="flex gap-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create ticket"}
          </Button>
          {onCancel ? (
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
          ) : null}
        </div>
      </form>
    </Panel>
  );
}
