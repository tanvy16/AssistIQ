import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { useAuth } from "../../context/AuthContext";
import { fetchKnowledgeDocuments } from "../../lib/knowledge";
import type { KnowledgeDocument } from "../../lib/knowledge.types";
import {
  knowledgeCategoryLabels,
  knowledgeStatusLabels,
} from "../../lib/knowledgeLabels";

export default function AdminKnowledgePage() {
  const { accessToken } = useAuth();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    void (async () => {
      setIsLoading(true);
      try {
        const response = await fetchKnowledgeDocuments(accessToken);
        setDocuments(response.items);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load documents");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [accessToken]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Base"
        description="Manage IT knowledge documents, publish articles, and review ingestion status."
        actions={
          <Link to="/app/admin/knowledge/new">
            <Button>New document</Button>
          </Link>
        }
      />

      {isLoading ? <LoadingState label="Loading documents…" /> : null}
      {!isLoading && error ? (
        <EmptyState title="Unable to load documents" description={error} />
      ) : null}

      {!isLoading && !error && documents.length === 0 ? (
        <EmptyState
          title="No knowledge documents yet"
          description="Create your first document to start building the knowledge base."
        />
      ) : null}

      {!isLoading && !error && documents.length > 0 ? (
        <Panel title="Documents" description={`${documents.length} total`}>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-surface-muted text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
                  <th className="px-3 py-2 font-medium">Title</th>
                  <th className="px-3 py-2 font-medium">Category</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Version</th>
                  <th className="px-3 py-2 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="border-b border-surface-divider hover:bg-surface-hover">
                    <td className="px-3 py-3">
                      <Link
                        to={`/app/admin/knowledge/${doc.id}`}
                        className="font-medium text-ink hover:underline"
                      >
                        {doc.title}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      {knowledgeCategoryLabels[doc.category]}
                    </td>
                    <td className="px-3 py-3">
                      <Badge variant={doc.status === "published" ? "success" : "muted"}>
                        {knowledgeStatusLabels[doc.status]}
                      </Badge>
                    </td>
                    <td className="px-3 py-3">v{doc.version}</td>
                    <td className="px-3 py-3 text-ink-muted">
                      {new Date(doc.updated_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
