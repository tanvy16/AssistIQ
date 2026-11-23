import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../lib/api";
import { getRoleHomePath } from "../lib/routes";

import LoadingState from "./ui/LoadingState";

type ProtectedRouteProps = {
  allowedRoles?: UserRole[];
};

export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-canvas px-4">
        <LoadingState label="Loading session…" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={getRoleHomePath(user.role)} replace />;
  }

  return <Outlet />;
}
