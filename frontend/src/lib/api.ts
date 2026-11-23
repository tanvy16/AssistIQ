const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:18765";

export type UserRole = "employee" | "agent" | "admin";

export type UserPublic = {
  id: string;
  email: string;
  role: UserRole;
  display_name: string | null;
  is_active: boolean;
  mfa_enabled?: boolean;
  /** Role requires MFA and the user has not enrolled yet. */
  mfa_enrollment_required?: boolean;
};

/**
 * One of three shapes: signed in (access_token + user), MFA challenge
 * (mfa_required + mfa_token), or strict-mode enrollment required
 * (mfa_enrollment_required + enrollment_token, no access token).
 */
export type LoginResponse = {
  access_token: string | null;
  token_type: string;
  user: UserPublic | null;
  mfa_required?: boolean;
  mfa_token?: string | null;
  enrollment_token?: string | null;
  mfa_enrollment_required?: boolean;
};

export type SecondFactor = { code: string } | { recovery_code: string };

export type RefreshResponse = {
  access_token: string;
  token_type: string;
  user?: UserPublic;
};

export async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
      return String(payload.detail[0].msg).replace(/^Value error, /, "");
    }
  } catch {
    // ignore parse errors
  }
  return `Request failed (${response.status})`;
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export async function verifyMfaLogin(
  mfaToken: string,
  factor: SecondFactor,
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/mfa/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ mfa_token: mfaToken, ...factor }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function refreshAccessToken(): Promise<RefreshResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function fetchMe(accessToken: string): Promise<UserPublic> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

// --- Access-token renewal -------------------------------------------------
// Access tokens are short-lived (15 min). Every authenticated wrapper calls
// authFetch: on a 401 it performs ONE shared refresh via the HttpOnly refresh
// cookie, hands the new token to AuthContext, and retries the request once.
// If refresh fails the session is ended instead of leaving a broken UI.

type SessionHandlers = {
  onRefreshed: (token: string, user: UserPublic | undefined) => void;
  onExpired: () => void;
};

let sessionHandlers: SessionHandlers | null = null;
let refreshInflight: Promise<string | null> | null = null;

export function registerSessionHandlers(handlers: SessionHandlers | null): void {
  sessionHandlers = handlers;
}

export function refreshSessionOnce(): Promise<string | null> {
  if (!refreshInflight) {
    refreshInflight = refreshAccessToken()
      .then((refreshed) => {
        sessionHandlers?.onRefreshed(refreshed.access_token, refreshed.user);
        return refreshed.access_token;
      })
      .catch(() => {
        sessionHandlers?.onExpired();
        return null;
      })
      .finally(() => {
        refreshInflight = null;
      });
  }
  return refreshInflight;
}

function withAuthorization(init: RequestInit | undefined, token: string): RequestInit {
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

export async function authFetch(input: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status !== 401) return response;
  const hadBearer = new Headers(init?.headers).has("Authorization");
  if (!hadBearer || init?.signal?.aborted) return response;
  const token = await refreshSessionOnce();
  if (!token || init?.signal?.aborted) return response;
  return fetch(input, withAuthorization(init, token));
}

export { API_BASE_URL };
