import { lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/layout/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import RoleRedirect from "./components/RoleRedirect";
import { ToastProvider } from "./components/ui/Toast";
import { AuthProvider } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";

const AdminAIModelsPage = lazy(() => import("./pages/admin/AdminAIModelsPage"));
const AdminPasswordResetDetailPage = lazy(() => import("./pages/admin/AdminPasswordResetDetailPage"));
const AdminPasswordResetsPage = lazy(() => import("./pages/admin/AdminPasswordResetsPage"));
const AdminITRequestDetailPage = lazy(() => import("./pages/admin/AdminITRequestDetailPage"));
const AdminITRequestsPage = lazy(() => import("./pages/admin/AdminITRequestsPage"));
const AdminKnowledgeDetailPage = lazy(() => import("./pages/admin/AdminKnowledgeDetailPage"));
const AdminKnowledgeNewPage = lazy(() => import("./pages/admin/AdminKnowledgeNewPage"));
const AdminKnowledgePage = lazy(() => import("./pages/admin/AdminKnowledgePage"));
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard"));
const AdminObservabilityPage = lazy(() => import("./pages/admin/AdminObservabilityPage"));
const AdminAuditsPage = lazy(() => import("./pages/admin/AdminAuditsPage"));
const AdminTicketAnalyticsPage = lazy(() => import("./pages/admin/AdminTicketAnalyticsPage"));
const AdminTicketDetailPage = lazy(() => import("./pages/admin/AdminTicketDetailPage"));
const AdminTicketsPage = lazy(() => import("./pages/admin/AdminTicketsPage"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage"));
const AgentChatPage = lazy(() => import("./pages/agent/ChatPage"));
const AgentPasswordResetDetailPage = lazy(() => import("./pages/agent/AgentPasswordResetDetailPage"));
const AgentPasswordResetsPage = lazy(() => import("./pages/agent/AgentPasswordResetsPage"));
const AgentITRequestDetailPage = lazy(() => import("./pages/agent/AgentITRequestDetailPage"));
const AgentITRequestsPage = lazy(() => import("./pages/agent/AgentITRequestsPage"));
const AgentKnowledgePage = lazy(() => import("./pages/agent/AgentKnowledgePage"));
const AgentDashboard = lazy(() => import("./pages/agent/AgentDashboard"));
const AgentQueuePage = lazy(() => import("./pages/agent/AgentQueuePage"));
const AgentTicketDetailPage = lazy(() => import("./pages/agent/AgentTicketDetailPage"));
const AgentTicketsPage = lazy(() => import("./pages/agent/AgentTicketsPage"));
const EmployeeChatPage = lazy(() => import("./pages/employee/ChatPage"));
const EmployeeCreateTicketPage = lazy(() => import("./pages/employee/EmployeeCreateTicketPage"));
const EmployeePasswordResetDetailPage = lazy(
  () => import("./pages/employee/EmployeePasswordResetDetailPage"),
);
const EmployeePasswordResetPage = lazy(() => import("./pages/employee/EmployeePasswordResetPage"));
const EmployeeITRequestDetailPage = lazy(() => import("./pages/employee/EmployeeITRequestDetailPage"));
const EmployeeITRequestsPage = lazy(() => import("./pages/employee/EmployeeITRequestsPage"));
const EmployeeKnowledgePage = lazy(() => import("./pages/employee/EmployeeKnowledgePage"));
const EmployeeDashboard = lazy(() => import("./pages/employee/EmployeeDashboard"));
const EmployeeTicketDetailPage = lazy(() => import("./pages/employee/EmployeeTicketDetailPage"));
const EmployeeTicketsPage = lazy(() => import("./pages/employee/EmployeeTicketsPage"));
const SecurityPage = lazy(() => import("./pages/SecurityPage"));

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/app" element={<RoleRedirect />} />

            <Route element={<ProtectedRoute allowedRoles={["employee"]} />}>
              <Route element={<AppShell />}>
                <Route path="/app/employee" element={<EmployeeDashboard />} />
                <Route path="/app/employee/tickets" element={<EmployeeTicketsPage />} />
                <Route path="/app/employee/tickets/new" element={<EmployeeCreateTicketPage />} />
                <Route path="/app/employee/tickets/:ticketId" element={<EmployeeTicketDetailPage />} />
                <Route path="/app/employee/knowledge" element={<EmployeeKnowledgePage />} />
                <Route path="/app/employee/chat" element={<EmployeeChatPage />} />
                <Route path="/app/employee/it-requests" element={<EmployeeITRequestsPage />} />
                <Route path="/app/employee/it-requests/:requestId" element={<EmployeeITRequestDetailPage />} />
                <Route path="/app/employee/password-reset" element={<EmployeePasswordResetPage />} />
                <Route
                  path="/app/employee/password-reset/:requestId"
                  element={<EmployeePasswordResetDetailPage />}
                />
                <Route path="/app/employee/security" element={<SecurityPage />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute allowedRoles={["agent"]} />}>
              <Route element={<AppShell />}>
                <Route path="/app/agent" element={<AgentDashboard />} />
                <Route path="/app/agent/queue" element={<AgentQueuePage />} />
                <Route path="/app/agent/tickets" element={<AgentTicketsPage />} />
                <Route path="/app/agent/tickets/:ticketId" element={<AgentTicketDetailPage />} />
                <Route path="/app/agent/knowledge" element={<AgentKnowledgePage />} />
                <Route path="/app/agent/chat" element={<AgentChatPage />} />
                <Route path="/app/agent/it-requests" element={<AgentITRequestsPage />} />
                <Route path="/app/agent/it-requests/:requestId" element={<AgentITRequestDetailPage />} />
                <Route path="/app/agent/password-resets" element={<AgentPasswordResetsPage />} />
                <Route
                  path="/app/agent/password-resets/:requestId"
                  element={<AgentPasswordResetDetailPage />}
                />
                <Route path="/app/agent/security" element={<SecurityPage />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
              <Route element={<AppShell />}>
                <Route path="/app/admin" element={<AdminDashboard />} />
                <Route path="/app/admin/tickets" element={<AdminTicketsPage />} />
                <Route path="/app/admin/tickets/:ticketId" element={<AdminTicketDetailPage />} />
                <Route path="/app/admin/knowledge" element={<AdminKnowledgePage />} />
                <Route path="/app/admin/knowledge/new" element={<AdminKnowledgeNewPage />} />
                <Route path="/app/admin/knowledge/:documentId" element={<AdminKnowledgeDetailPage />} />
                <Route path="/app/admin/kb" element={<Navigate to="/app/admin/knowledge" replace />} />
                <Route path="/app/admin/ai-models" element={<AdminAIModelsPage />} />
                <Route path="/app/admin/it-requests" element={<AdminITRequestsPage />} />
                <Route path="/app/admin/it-requests/:requestId" element={<AdminITRequestDetailPage />} />
                <Route path="/app/admin/password-resets" element={<AdminPasswordResetsPage />} />
                <Route
                  path="/app/admin/password-resets/:requestId"
                  element={<AdminPasswordResetDetailPage />}
                />
                <Route path="/app/admin/observability" element={<AdminObservabilityPage />} />
                <Route path="/app/admin/analytics" element={<AdminTicketAnalyticsPage />} />
                <Route path="/app/admin/audits" element={<AdminAuditsPage />} />
                <Route path="/app/admin/users" element={<AdminUsersPage />} />
                <Route path="/app/admin/security" element={<SecurityPage />} />
              </Route>
            </Route>

            <Route path="/" element={<Navigate to="/app" replace />} />
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
