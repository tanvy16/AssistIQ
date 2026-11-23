import { useAuth } from "../../context/AuthContext";
import KnowledgeSearchPanel from "../../components/knowledge/KnowledgeSearchPanel";
import PageHeader from "../../components/ui/PageHeader";

export default function AgentKnowledgePage() {
  const { accessToken } = useAuth();

  if (!accessToken) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Base"
        description="Search published knowledge while resolving tickets."
      />
      <KnowledgeSearchPanel accessToken={accessToken} />
    </div>
  );
}
