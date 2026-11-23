import { useAuth } from "../../context/AuthContext";
import PasswordResetDetailView from "../../components/passwordReset/PasswordResetDetailView";

export default function AgentPasswordResetDetailPage() {
  const { accessToken } = useAuth();
  if (!accessToken) return null;
  return (
    <PasswordResetDetailView
      accessToken={accessToken}
      listPath="/app/agent/password-resets"
      canEscalate
      canReject
    />
  );
}
