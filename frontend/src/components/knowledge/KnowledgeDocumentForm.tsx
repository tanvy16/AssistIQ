import { FormEvent } from "react";

import Button from "../ui/Button";
import Input from "../ui/Input";
import Panel from "../ui/Panel";
import type { KnowledgeCategory, KnowledgeDocumentInput } from "../../lib/knowledge.types";
import { knowledgeCategories, knowledgeCategoryLabels } from "../../lib/knowledgeLabels";

type KnowledgeDocumentFormProps = {
  initial?: Partial<KnowledgeDocumentInput>;
  submitLabel: string;
  isSubmitting?: boolean;
  onSubmit: (input: KnowledgeDocumentInput) => Promise<void>;
  onCancel?: () => void;
};

export default function KnowledgeDocumentForm({
  initial,
  submitLabel,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: KnowledgeDocumentFormProps) {
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const title = String(formData.get("title") ?? "").trim();
    const description = String(formData.get("description") ?? "").trim();
    const body = String(formData.get("body") ?? "");
    const category = String(formData.get("category") ?? "other") as KnowledgeCategory;
    const source = String(formData.get("source") ?? "").trim();

    await onSubmit({
      title,
      description: description || null,
      body,
      category,
      source: source || null,
    });
  }

  return (
    <Panel title="Document details" description="Create or update knowledge base content.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          id="title"
          name="title"
          label="Title"
          defaultValue={initial?.title ?? ""}
          required
          maxLength={200}
        />
        <Input
          id="description"
          name="description"
          label="Description"
          defaultValue={initial?.description ?? ""}
        />
        <div className="space-y-1">
          <label htmlFor="category" className="text-sm font-medium text-ink">
            Category
          </label>
          <select
            id="category"
            name="category"
            defaultValue={initial?.category ?? "other"}
            className="field-control"
          >
            {knowledgeCategories.map((category) => (
              <option key={category} value={category}>
                {knowledgeCategoryLabels[category]}
              </option>
            ))}
          </select>
        </div>
        <Input
          id="source"
          name="source"
          label="Source"
          defaultValue={initial?.source ?? ""}
          placeholder="Internal wiki, runbook, etc."
        />
        <div className="space-y-1">
          <label htmlFor="body" className="text-sm font-medium text-ink">
            Content
          </label>
          <textarea
            id="body"
            name="body"
            rows={12}
            defaultValue={initial?.body ?? ""}
            className="field-control"
            placeholder="Markdown or plain text content…"
          />
        </div>
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : submitLabel}
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
