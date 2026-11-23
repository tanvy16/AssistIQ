import { API_BASE_URL, authFetch } from "./api";
import type { AIModel, AIModelListResponse } from "./ai.types";
import { memoryInvalidate, memoryLoad } from "./queryMemory";

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

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

export async function fetchAIModels(
  accessToken: string,
  signal?: AbortSignal,
): Promise<AIModelListResponse> {
  return memoryLoad(
    `models:${accessToken}`,
    async () => {
      const response = await authFetch(`${API_BASE_URL}/api/v1/ai/models`, {
        headers: authHeaders(accessToken),
        credentials: "include",
        signal,
      });
      if (!response.ok) throw new Error(await parseError(response));
      return response.json();
    },
    { ttlMs: 60_000 },
  );
}

export async function updateAIModelEnabled(
  accessToken: string,
  modelId: string,
  enabled: boolean,
): Promise<AIModel> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/ai/models/${modelId}`, {
    method: "PATCH",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  // The model list is cached for 60 s; drop it so the toggle and the chat
  // model picker reflect the server's new state immediately.
  memoryInvalidate("models:");
  return response.json();
}

export const AI_MODEL_SELECTION_KEY = "assistiq_selected_model_id";

export function getStoredModelId(): string | null {
  return localStorage.getItem(AI_MODEL_SELECTION_KEY);
}

export function storeModelId(modelId: string): void {
  localStorage.setItem(AI_MODEL_SELECTION_KEY, modelId);
}

export function clearStoredModelId(): void {
  localStorage.removeItem(AI_MODEL_SELECTION_KEY);
}
