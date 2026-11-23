import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";

import ModelSelector from "../../components/ai/ModelSelector";
import ChatMessageBubble from "../../components/chat/ChatMessageBubble";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import Input from "../../components/ui/Input";
import LoadingState from "../../components/ui/LoadingState";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import { useToast } from "../../components/ui/Toast";
import { useAuth } from "../../context/AuthContext";
import type { AIModel } from "../../lib/ai.types";
import {
  createConversation,
  escalateConversation,
  fetchConversationMessages,
  fetchConversations,
  sendChatMessageStream,
} from "../../lib/chat";
import type { ChatMessage, Citation, Conversation } from "../../lib/chat.types";

type ChatPageProps = {
  title?: string;
  description?: string;
};

function ThinkingIndicator() {
  return (
    <div className="rail-ai flex items-center gap-3 rounded-md border border-surface-border bg-surface px-4 py-3" role="status">
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className="thinking-dot h-1.5 w-1.5 rounded-full bg-ai"
            style={{ animationDelay: `${index * 0.16}s` }}
          />
        ))}
      </span>
      <p className="text-sm text-ink-muted">AssistIQ is thinking...</p>
    </div>
  );
}

export default function ChatPage({
  title = "AI Support Chat",
  description = "Ask IT support questions grounded in published knowledge. Escalate to a human agent when needed.",
}: ChatPageProps) {
  const { accessToken } = useAuth();
  const { showToast } = useToast();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [hasStreamedTokens, setHasStreamedTokens] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  async function loadConversations(
    token: string,
    preferredId?: string | null,
    signal?: AbortSignal,
  ) {
    const response = await fetchConversations(token, signal);
    if (signal?.aborted) return;
    setConversations(response.items);
    const nextId = preferredId ?? activeConversationId ?? response.items[0]?.id ?? null;
    setActiveConversationId(nextId);
    if (nextId) {
      const history = await fetchConversationMessages(token, nextId, signal);
      if (signal?.aborted) return;
      setMessages(history);
    } else {
      setMessages([]);
    }
  }

  useEffect(() => {
    if (!accessToken) return;
    const controller = new AbortController();
    void (async () => {
      setIsLoading(true);
      try {
        await loadConversations(accessToken, undefined, controller.signal);
        if (controller.signal.aborted) return;
        setError(null);
      } catch (err) {
        if (controller.signal.aborted || (err instanceof Error && err.name === "AbortError")) return;
        setError(err instanceof Error ? err.message : "Failed to load chat");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    })();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending, hasStreamedTokens]);

  if (!accessToken) return null;
  const token = accessToken;

  async function handleNewConversation() {
    try {
      const conversation = await createConversation(token, {
        selected_model_id: selectedModel?.id,
      });
      await loadConversations(token, conversation.id);
      showToast("Conversation created.", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Could not create conversation", "error");
    }
  }

  async function handleSelectConversation(conversationId: string) {
    setActiveConversationId(conversationId);
    try {
      const history = await fetchConversationMessages(token, conversationId);
      setMessages(history);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Could not load messages", "error");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim() || isSending) return;

    const content = draft.trim();
    setIsSending(true);
    setHasStreamedTokens(false);
    setDraft("");

    const optimisticUser: ChatMessage = {
      id: `local-user-${Date.now()}`,
      conversation_id: activeConversationId ?? "pending",
      role: "user",
      content,
      model_id: null,
      latency_ms: null,
      prompt_tokens: null,
      completion_tokens: null,
      total_tokens: null,
      intent: null,
      confidence_state: null,
      citations: [],
      created_at: new Date().toISOString(),
    };
    const streamingAssistant: ChatMessage = {
      id: `local-assistant-${Date.now()}`,
      conversation_id: activeConversationId ?? "pending",
      role: "assistant",
      content: "",
      model_id: null,
      latency_ms: null,
      prompt_tokens: null,
      completion_tokens: null,
      total_tokens: null,
      intent: null,
      confidence_state: null,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, optimisticUser, streamingAssistant]);

    try {
      let conversationId = activeConversationId;
      if (!conversationId) {
        const conversation = await createConversation(token, {
          selected_model_id: selectedModel?.id,
        });
        conversationId = conversation.id;
        setActiveConversationId(conversationId);
      }

      await sendChatMessageStream(
        token,
        conversationId,
        {
          content,
          selected_model_id: selectedModel?.id,
        },
        {
          onMeta: (meta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === streamingAssistant.id
                  ? {
                      ...message,
                      intent: meta.intent ?? null,
                      confidence_state: meta.confidence_state ?? null,
                      citations: (meta.citations ?? []) as Citation[],
                    }
                  : message,
              ),
            );
          },
          onToken: (text) => {
            setHasStreamedTokens(true);
            setMessages((current) =>
              current.map((message) =>
                message.id === streamingAssistant.id
                  ? { ...message, content: `${message.content}${text}` }
                  : message,
              ),
            );
          },
          onDone: (result) => {
            setMessages((current) =>
              current
                .filter((message) => message.id !== optimisticUser.id && message.id !== streamingAssistant.id)
                .concat(result.user_message, result.assistant_message),
            );
          },
        },
      );
      await loadConversations(token, conversationId);
    } catch (err) {
      setMessages((current) =>
        current.filter((message) => message.id !== streamingAssistant.id),
      );
      showToast(err instanceof Error ? err.message : "Failed to send message", "error");
    } finally {
      setIsSending(false);
      setHasStreamedTokens(false);
    }
  }

  async function handleEscalate() {
    if (!activeConversationId) return;
    try {
      const result = await escalateConversation(token, activeConversationId, {
        reason: "user_requested_human",
      });
      if (result.ticket_number) {
        showToast(
          `Ticket ${result.ticket_number} created. An agent can pick it up from the queue.`,
          "success",
        );
      } else {
        showToast("Human assistance was requested, but no ticket number was returned.", "error");
      }
      await loadConversations(token, activeConversationId);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Escalation failed", "error");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        actions={
          <>
            <Button variant="secondary" onClick={() => void handleNewConversation()}>
              New conversation
            </Button>
            <Button
              variant="secondary"
              onClick={() => void handleEscalate()}
              disabled={!activeConversationId}
            >
              Request human
            </Button>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <Panel title="Conversations" description={`${conversations.length} total`}>
          {isLoading ? <LoadingState label="Loading conversations…" /> : null}
          {!isLoading && conversations.length === 0 ? (
            <EmptyState
              title="No conversations yet"
              description="Start a new conversation to ask AssistIQ for IT support help."
            />
          ) : null}
          <ul className="space-y-2">
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <button
                  type="button"
                  onClick={() => void handleSelectConversation(conversation.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                    conversation.id === activeConversationId
                      ? "border-ai bg-ai-soft"
                      : "border-surface-border hover:bg-surface-hover"
                  }`}
                >
                  <span className="block font-medium text-ink">{conversation.title}</span>
                  <span className="block text-xs capitalize text-ink-muted">{conversation.status}</span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>

        <div className="space-y-4">
          <ModelSelector
            accessToken={token}
            filterType="llm"
            title="Generation model"
            description="Responses use an enabled LLM from the model registry, grounded in published knowledge."
            onModelChange={setSelectedModel}
          />

          <Panel title="Messages">
            {error ? <p className="mb-4 text-sm text-danger">{error}</p> : null}
            <div className="max-h-[min(64vh,720px)] space-y-4 overflow-y-auto pr-1">
              {messages.map((message) => (
                <ChatMessageBubble key={message.id} message={message} />
              ))}
              {isSending && !hasStreamedTokens ? <ThinkingIndicator /> : null}
              {!messages.length && !isLoading && !isSending ? (
                <EmptyState
                  title="Start the conversation"
                  description="Ask about VPN, access, hardware, software, or your tickets."
                />
              ) : null}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={(event) => void handleSubmit(event)} className="mt-4 space-y-3">
              <Input
                label="Your message"
                value={draft}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setDraft(event.target.value)}
                placeholder="How do I connect to the corporate VPN?"
                disabled={isSending}
              />
              <Button type="submit" variant="primary" disabled={isSending || !draft.trim()}>
                {isSending ? "Sending…" : "Send message"}
              </Button>
            </form>
          </Panel>
        </div>
      </div>
    </div>
  );
}
