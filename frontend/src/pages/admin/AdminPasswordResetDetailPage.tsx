import { useAuth } from "../../context/AuthContext";
import PasswordResetDetailView from "../../components/passwordReset/PasswordResetDetailView";

export default function AdminPasswordResetDetailPage() {
  const { accessToken } = useAuth();
  if (!accessToken) return null;
  return (
    <PasswordResetDetailView
      accessToken={accessToken}
      listPath="/app/admin/password-resets"
      canEscalate
      canReject
    />
  );
}
