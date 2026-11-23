import { API_BASE_URL, authFetch } from "./api";
import type {
  ChatMessage,
  ChatStreamMeta,
  Conversation,
  ConversationListResponse,
  Escalation,
  SendMessageResponse,
} from "./chat.types";

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

export async function createConversation(
  accessToken: string,
  payload: { title?: string; selected_model_id?: string } = {},
): Promise<Conversation> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/chat/conversations`, {
    method: "POST",
    headers: authHeaders(accessToken),
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchConversations(
  accessToken: string,
  signal?: AbortSignal,
): Promise<ConversationListResponse> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/chat/conversations`, {
    headers: authHeaders(accessToken),
    credentials: "include",
    signal,
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function fetchConversationMessages(
  accessToken: string,
  conversationId: string,
  signal?: AbortSignal,
): Promise<ChatMessage[]> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/messages`,
    {
      headers: authHeaders(accessToken),
      credentials: "include",
      signal,
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function sendChatMessage(
  accessToken: string,
  conversationId: string,
  payload: { content: string; selected_model_id?: string },
): Promise<SendMessageResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function sendChatMessageStream(
  accessToken: string,
  conversationId: string,
  payload: { content: string; selected_model_id?: string },
  handlers: {
    onMeta?: (meta: ChatStreamMeta) => void;
    onToken?: (text: string) => void;
    onDone?: (result: SendMessageResponse) => void;
  } = {},
): Promise<SendMessageResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/messages/stream`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  if (!response.body) throw new Error("Streaming is not supported in this browser.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload: SendMessageResponse | null = null;
  let streamError: string | null = null;

  const consume = (chunk: string) => {
    const eventMatch = chunk.match(/^event:\s*(.+)$/m);
    const dataMatch = chunk.match(/^data:\s*(.+)$/m);
    if (!eventMatch || !dataMatch) return;
    const event = eventMatch[1].trim();
    const data = JSON.parse(dataMatch[1]);
    if (event === "meta") handlers.onMeta?.(data as ChatStreamMeta);
    if (event === "token" && typeof data.text === "string") handlers.onToken?.(data.text);
    if (event === "done") {
      donePayload = data as SendMessageResponse;
      handlers.onDone?.(donePayload);
    }
    if (event === "error") {
      streamError = typeof data.detail === "string" ? data.detail : "AssistIQ could not complete the response.";
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) consume(part.trim());
  }
  if (buffer.trim()) consume(buffer.trim());

  if (streamError) throw new Error(streamError);
  if (!donePayload) throw new Error("AssistIQ did not finish generating a response.");
  return donePayload;
}

export async function escalateConversation(
  accessToken: string,
  conversationId: string,
  payload: { reason: string; notes?: string },
): Promise<Escalation> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/chat/conversations/${conversationId}/escalate`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
      credentials: "include",
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function confidenceLabel(state: string | null | undefined): string {
  switch (state) {
    case "HIGH_CONFIDENCE":
      return "High confidence";
    case "LOW_CONFIDENCE":
      return "Low confidence";
    case "NO_EVIDENCE":
      return "Limited evidence";
    default:
      return "Unknown";
  }
}

export function confidenceTone(state: string | null | undefined): "ai" | "default" | "muted" {
  switch (state) {
    case "HIGH_CONFIDENCE":
      return "ai";
    case "LOW_CONFIDENCE":
      return "default";
    default:
      return "muted";
  }
}
