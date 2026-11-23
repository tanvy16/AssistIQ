import { API_BASE_URL, authFetch, type UserPublic } from "./api";

export type DirectoryUser = UserPublic & {
  mfa_enabled: boolean;
  mfa_required: boolean;
};

export type UserListResponse = {
  items: DirectoryUser[];
  total: number;
};

async function parseError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // ignore
  }
  return `Request failed (${response.status})`;
}

export async function fetchUsers(accessToken: string, signal?: AbortSignal): Promise<UserListResponse> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/users`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    credentials: "include",
    signal,
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}
