import { API_BASE_URL, authFetch, parseError, type UserPublic } from "./api";

export type MfaStatus = {
  enabled: boolean;
  enabled_at: string | null;
  pending_enrollment: boolean;
  recovery_codes_remaining: number;
  required_for_role: boolean;
  enforcement_mode: "strict" | "grace";
  locked_until: string | null;
};

export type MfaEnrollStart = {
  /** Shown only while enrollment is pending; never returned again. */
  secret: string;
  otpauth_uri: string;
  qr_svg_data_uri: string;
};

export type RecoveryCodesResult = {
  recovery_codes: string[];
  access_token?: string | null;
  user?: UserPublic | null;
};

export type SessionInfo = {
  id: string;
  created_at: string;
  expires_at: string;
  user_agent: string | null;
  mfa_verified: boolean;
  current: boolean;
};

async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await authFetch(`${API_BASE_URL}/api/v1${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    credentials: "include",
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<T>;
}

// Enrollment endpoints also accept the strict-mode enrollment token, which is
// NOT an access token, so they must not go through refresh-and-retry.
async function enrollmentRequest<T>(token: string, path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<T>;
}

export function fetchMfaStatus(token: string, signal?: AbortSignal) {
  return request<MfaStatus>(token, "/auth/mfa/status", { signal });
}

export function startMfaEnrollment(token: string, password: string) {
  return enrollmentRequest<MfaEnrollStart>(token, "/auth/mfa/enroll/start", { password });
}

export function verifyMfaEnrollment(token: string, code: string) {
  return enrollmentRequest<RecoveryCodesResult>(token, "/auth/mfa/enroll/verify", { code });
}

export function regenerateRecoveryCodes(token: string, password: string, code: string) {
  return request<RecoveryCodesResult>(token, "/auth/mfa/recovery-codes/regenerate", {
    method: "POST",
    body: JSON.stringify({ password, code }),
  });
}

export function disableMfa(
  token: string,
  password: string,
  factor: { code: string } | { recovery_code: string },
) {
  return request<{ revoked: number }>(token, "/auth/mfa/disable", {
    method: "POST",
    body: JSON.stringify({ password, ...factor }),
  });
}

export function changePassword(
  token: string,
  currentPassword: string,
  newPassword: string,
  code?: string,
) {
  return request<{ revoked: number }>(token, "/auth/password/change", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      ...(code ? { code } : {}),
    }),
  });
}

export function fetchSessions(token: string, signal?: AbortSignal) {
  return request<{ items: SessionInfo[] }>(token, "/auth/sessions", { signal });
}

export function revokeOtherSessions(token: string) {
  return request<{ revoked: number }>(token, "/auth/sessions/revoke-others", { method: "POST" });
}

export function adminResetUserMfa(token: string, userId: string, adminPassword: string) {
  return request<{ revoked: number }>(token, `/users/${userId}/mfa/reset`, {
    method: "POST",
    body: JSON.stringify({ admin_password: adminPassword }),
  });
}

/** Client-side mirror of the server password policy, for immediate feedback only. */
export function passwordPolicyProblem(password: string): string | null {
  if (password.length < 12) return "Use at least 12 characters.";
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((re) => re.test(password)).length;
  if (classes < 3) return "Mix at least three of: lowercase, uppercase, digits, symbols.";
  return null;
}

export function recoveryCodesFileContent(email: string, codes: string[]): string {
  return [
    `AssistIQ MFA recovery codes for ${email}`,
    `Generated ${new Date().toISOString()}`,
    "Each code works once. Store them somewhere safe and offline.",
    "",
    ...codes,
    "",
  ].join("\n");
}
