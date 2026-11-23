import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import LoadingState from "./ui/LoadingState";
import { getRoleHomePath } from "../lib/routes";

export default function RoleRedirect() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingState label="Loading session…" />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getRoleHomePath(user.role)} replace />;
}
