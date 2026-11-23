import { API_BASE_URL, authFetch } from "./api";
import type { PasswordResetDetail, PasswordResetListItem } from "./passwordResets.types";
import { memoryInvalidate, memoryLoad } from "./queryMemory";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // ignore
  }
  return `Request failed (${response.status})`;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

function invalidatePasswordResetQueries(): void {
  memoryInvalidate("password-resets:");
}

export async function createPasswordReset(accessToken: string, message?: string): Promise<PasswordResetDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ message }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidatePasswordResetQueries();
  return response.json();
}

export async function fetchPasswordResets(
  accessToken: string,
  options: { force?: boolean } = {},
): Promise<{ items: PasswordResetListItem[]; total: number }> {
  return memoryLoad(
    `password-resets:${accessToken}`,
    async () => {
      const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets`, {
        headers: authHeaders(accessToken),
        credentials: "include",
      });
      if (!response.ok) throw new Error(await parseError(response));
      return response.json();
    },
    { ttlMs: 15_000, force: options.force },
  );
}

export async function fetchPasswordReset(accessToken: string, id: string): Promise<PasswordResetDetail> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets/${id}`, {
    headers: authHeaders(accessToken),
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function verifyPasswordReset(accessToken: string, id: string, email: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets/${id}/verify`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidatePasswordResetQueries();
  return response.json() as Promise<PasswordResetDetail>;
}

export async function confirmPasswordReset(accessToken: string, id: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets/${id}/confirm`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidatePasswordResetQueries();
  return response.json() as Promise<PasswordResetDetail>;
}

export async function escalatePasswordReset(accessToken: string, id: string, reason?: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets/${id}/escalate`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidatePasswordResetQueries();
  return response.json() as Promise<PasswordResetDetail>;
}

export async function rejectPasswordReset(accessToken: string, id: string, reason?: string) {
  const response = await authFetch(`${API_BASE_URL}/api/v1/password-resets/${id}/reject`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  invalidatePasswordResetQueries();
  return response.json() as Promise<PasswordResetDetail>;
}

export function passwordResetStatusCopy(status: string): string {
  switch (status) {
    case "verification_required":
      return "Confirm your registered email to verify this request. No password has been changed.";
    case "verification_failed":
      return "Identity verification failed. You can retry with your registered email.";
    case "confirmation_required":
      return "Identity verified. Confirm to start a simulated password reset. This will not change your real password.";
    case "completed":
      return "Simulation completed successfully.";
    case "escalated":
      return "This request needs human review and was not executed.";
    case "rejected":
      return "This password reset was denied by policy or a reviewer.";
    case "failed":
      return "The simulated reset did not validate and was not marked successful.";
    default:
      return "The password reset request is in progress.";
  }
}
