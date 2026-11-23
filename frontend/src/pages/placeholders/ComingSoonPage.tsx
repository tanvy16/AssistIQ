import { Link } from "react-router-dom";

import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import Button from "../../components/ui/Button";
import { getRoleHomePath } from "../../lib/routes";
import { useAuth } from "../../context/AuthContext";

type ComingSoonPageProps = {
  feature: string;
  description?: string;
};

export default function ComingSoonPage({
  feature,
  description,
}: ComingSoonPageProps) {
  const { user } = useAuth();
  const homePath = user ? getRoleHomePath(user.role) : "/login";

  return (
    <div className="space-y-6">
      <PageHeader
        title={feature}
        description={description ?? "This module is not available in the current workspace."}
        actions={
          <Link to={homePath}>
            <Button variant="secondary" size="sm">
              Back to Home
            </Button>
          </Link>
        }
      />

      <Panel>
        <p className="text-sm text-ink-muted">
          <span className="font-medium text-ink">{feature}</span> is not enabled for this
          environment. Return to the dashboard to continue with available tools.
        </p>
      </Panel>
    </div>
  );
}
