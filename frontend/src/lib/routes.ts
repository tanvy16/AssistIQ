import type { UserRole } from "./api";

export function getRoleHomePath(role: UserRole): string {
  switch (role) {
    case "agent":
      return "/app/agent";
    case "admin":
      return "/app/admin";
    case "employee":
    default:
      return "/app/employee";
  }
}
