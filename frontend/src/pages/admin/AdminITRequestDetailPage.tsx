import { useAuth } from "../../context/AuthContext";
import ITRequestDetailPage from "../../components/it/ITRequestDetailPage";

export default function AdminITRequestDetailPage() {
  const { accessToken } = useAuth();
  if (!accessToken) return null;
  return (
    <ITRequestDetailPage
      accessToken={accessToken}
      listPath="/app/admin/it-requests"
      canApprove
    />
  );
}
