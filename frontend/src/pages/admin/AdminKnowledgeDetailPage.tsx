import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import KnowledgeDocumentForm from "../../components/knowledge/KnowledgeDocumentForm";
import KnowledgeSearchPanel from "../../components/knowledge/KnowledgeSearchPanel";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { useToast } from "../../components/ui/Toast";
import { useAuth } from "../../context/AuthContext";
import {
  archiveKnowledgeDocument,
  deleteKnowledgeDocument,
  fetchKnowledgeDocument,
  publishKnowledgeDocument,
  updateKnowledgeDocument,
} from "../../lib/knowledge";
import type { KnowledgeDocument } from "../../lib/knowledge.types";
import {
  knowledgeCategoryLabels,
  knowledgeStatusLabels,
} from "../../lib/knowledgeLabels";

export default function AdminKnowledgeDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { accessToken } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [document, setDocument] = useState<KnowledgeDocument | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isActionRunning, setIsActionRunning] = useState(false);

  useEffect(() => {
    if (!accessToken || !documentId) return;
    void (async () => {
      setIsLoading(true);
      try {
        const doc = await fetchKnowledgeDocument(accessToken, documentId);
        setDocument(doc);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [accessToken, documentId]);

  if (!accessToken || !documentId) return null;

  async function reload() {
    const doc = await fetchKnowledgeDocument(accessToken!, documentId!);
    setDocument(doc);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={document?.title ?? "Knowledge Document"}
        description="Edit, publish, archive, or delete this knowledge article."
        actions={
          <Link to="/app/admin/knowledge">
            <Button variant="secondary">Back to list</Button>
          </Link>
        }
      />

      {isLoading ? <LoadingState label="Loading document…" /> : null}
      {!isLoading && error ? (
        <EmptyState title="Unable to load document" description={error} />
      ) : null}

      {!isLoading && document ? (
        <>
          <Panel title="Status">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={document.status === "published" ? "success" : "muted"}>
                {knowledgeStatusLabels[document.status]}
              </Badge>
              <span className="text-sm text-ink-muted">
                {knowledgeCategoryLabels[document.category]} · v{document.version}
              </span>
              <div className="flex flex-wrap gap-2">
                {document.status !== "published" ? (
                  <Button
                    disabled={isActionRunning}
                    onClick={async () => {
                      setIsActionRunning(true);
                      try {
                        await publishKnowledgeDocument(accessToken, document.id);
                        await reload();
                        showToast("Document published.", "success");
                      } catch (err) {
                        showToast(
                          err instanceof Error ? err.message : "Publish failed",
                          "error",
                        );
                      } finally {
                        setIsActionRunning(false);
                      }
                    }}
                  >
                    Publish
                  </Button>
                ) : null}
                {document.status !== "archived" ? (
                  <Button
                    variant="secondary"
                    disabled={isActionRunning}
                    onClick={async () => {
                      setIsActionRunning(true);
                      try {
                        await archiveKnowledgeDocument(accessToken, document.id);
                        await reload();
                        showToast("Document archived.", "success");
                      } catch (err) {
                        showToast(
                          err instanceof Error ? err.message : "Archive failed",
                          "error",
                        );
                      } finally {
                        setIsActionRunning(false);
                      }
                    }}
                  >
                    Archive
                  </Button>
                ) : null}
                <Button
                  variant="danger"
                  disabled={isActionRunning}
                  onClick={async () => {
                    if (!window.confirm("Delete this document permanently?")) return;
                    setIsActionRunning(true);
                    try {
                      await deleteKnowledgeDocument(accessToken, document.id);
                      showToast("Document deleted.", "success");
                      navigate("/app/admin/knowledge");
                    } catch (err) {
                      showToast(
                        err instanceof Error ? err.message : "Delete failed",
                        "error",
                      );
                    } finally {
                      setIsActionRunning(false);
                    }
                  }}
                >
                  Delete
                </Button>
              </div>
            </div>
          </Panel>

          <KnowledgeDocumentForm
            initial={{
              title: document.title,
              description: document.description,
              body: document.body,
              category: document.category,
              source: document.source,
            }}
            submitLabel="Save changes"
            isSubmitting={isSubmitting}
            onSubmit={async (input) => {
              setIsSubmitting(true);
              try {
                const updated = await updateKnowledgeDocument(
                  accessToken,
                  document.id,
                  input,
                );
                setDocument(updated);
                showToast("Document updated.", "success");
              } catch (err) {
                showToast(
                  err instanceof Error ? err.message : "Update failed",
                  "error",
                );
              } finally {
                setIsSubmitting(false);
              }
            }}
          />

          {document.status === "published" ? (
            <KnowledgeSearchPanel
              accessToken={accessToken}
              title="Preview search"
              description="Test retrieval against this published document."
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
