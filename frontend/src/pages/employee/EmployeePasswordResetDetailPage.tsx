import { useAuth } from "../../context/AuthContext";
import PasswordResetDetailView from "../../components/passwordReset/PasswordResetDetailView";

export default function EmployeePasswordResetDetailPage() {
  const { accessToken } = useAuth();
  if (!accessToken) return null;
  return (
    <PasswordResetDetailView
      accessToken={accessToken}
      listPath="/app/employee/password-reset"
      canVerify
      canConfirm
      canEscalate
    />
  );
}
