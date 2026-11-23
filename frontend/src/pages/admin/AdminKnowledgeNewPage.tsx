import { useState } from "react";
import { useNavigate } from "react-router-dom";

import KnowledgeDocumentForm from "../../components/knowledge/KnowledgeDocumentForm";
import PageHeader from "../../components/ui/PageHeader";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { createKnowledgeDocument } from "../../lib/knowledge";

export default function AdminKnowledgeNewPage() {
  const { accessToken } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!accessToken) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Knowledge Document"
        description="Create a draft document. Publish when content is ready for search."
      />
      <KnowledgeDocumentForm
        submitLabel="Create draft"
        isSubmitting={isSubmitting}
        onCancel={() => navigate("/app/admin/knowledge")}
        onSubmit={async (input) => {
          setIsSubmitting(true);
          try {
            const document = await createKnowledgeDocument(accessToken, input);
            showToast("Document created as draft.", "success");
            navigate(`/app/admin/knowledge/${document.id}`);
          } catch (err) {
            showToast(
              err instanceof Error ? err.message : "Failed to create document",
              "error",
            );
          } finally {
            setIsSubmitting(false);
          }
        }}
      />
    </div>
  );
}
