import type { UserRole } from "./api";

export type NavItem = {
  label: string;
  path: string;
  end?: boolean;
};

export const navigationByRole: Record<UserRole, NavItem[]> = {
  employee: [
    { label: "Home", path: "/app/employee", end: true },
    { label: "AI Chat", path: "/app/employee/chat" },
    { label: "My Tickets", path: "/app/employee/tickets" },
    { label: "Knowledge Base", path: "/app/employee/knowledge" },
    { label: "IT Requests", path: "/app/employee/it-requests" },
    { label: "Password Reset", path: "/app/employee/password-reset" },
    { label: "Security", path: "/app/employee/security" },
  ],
  agent: [
    { label: "Home", path: "/app/agent", end: true },
    { label: "Ticket Queue", path: "/app/agent/queue" },
    { label: "AI Chat", path: "/app/agent/chat" },
    { label: "Assigned Tickets", path: "/app/agent/tickets" },
    { label: "Knowledge Base", path: "/app/agent/knowledge" },
    { label: "IT Requests", path: "/app/agent/it-requests" },
    { label: "Password Resets", path: "/app/agent/password-resets" },
    { label: "Security", path: "/app/agent/security" },
  ],
  admin: [
    { label: "Home", path: "/app/admin", end: true },
    { label: "Tickets", path: "/app/admin/tickets" },
    { label: "Knowledge Base", path: "/app/admin/knowledge" },
    { label: "AI Models", path: "/app/admin/ai-models" },
    { label: "IT Requests", path: "/app/admin/it-requests" },
    { label: "Password Resets", path: "/app/admin/password-resets" },
    { label: "Ticket Analytics", path: "/app/admin/analytics" },
    { label: "AI Observability", path: "/app/admin/observability" },
    { label: "Audit Log", path: "/app/admin/audits" },
    { label: "Users", path: "/app/admin/users" },
    { label: "Security", path: "/app/admin/security" },
  ],
};

export function getNavigationForRole(role: UserRole): NavItem[] {
  return navigationByRole[role];
}
