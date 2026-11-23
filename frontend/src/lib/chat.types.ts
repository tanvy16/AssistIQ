export type Citation = {
  id: string;
  document_id: string;
  chunk_id: string;
  title: string;
  similarity_score: number;
  category?: string | null;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model_id: string | null;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  intent: string | null;
  confidence_state: string | null;
  citations: Citation[];
  created_at: string;
};

export type Conversation = {
  id: string;
  user_id: string;
  title: string;
  status: string;
  selected_model_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationListResponse = {
  items: Conversation[];
  total: number;
};

export type SendMessageResponse = {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
};

export type ChatStreamMeta = {
  conversation_id: string;
  intent?: string | null;
  confidence_state?: string | null;
  citations: Citation[];
};

export type Escalation = {
  id: string;
  conversation_id: string;
  requested_by: string;
  reason: string;
  status: string;
  notes: string | null;
  created_at: string;
  resolved_at: string | null;
  ticket_id?: string | null;
  ticket_number?: string | null;
};
