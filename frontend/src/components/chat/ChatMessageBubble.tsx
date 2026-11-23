import Badge from "../ui/Badge";
import { confidenceLabel, confidenceTone } from "../../lib/chat";
import type { ChatMessage } from "../../lib/chat.types";
import MessageCitations from "./MessageCitations";

type ChatMessageBubbleProps = {
  message: ChatMessage;
};

export default function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-3xl border px-4 py-3 ${
          isUser
            ? "rounded-md border-surface-border bg-surface-hover text-ink"
            : "rail-ai rounded-md border-surface-border bg-surface text-ink"
        }`}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${isUser ? "text-ink-muted" : "text-ai"}`}>
            {isUser ? "You" : "AssistIQ"}
          </span>
          {!isUser && message.confidence_state ? (
            <Badge variant={confidenceTone(message.confidence_state)}>
              {confidenceLabel(message.confidence_state)}
            </Badge>
          ) : null}
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        {!isUser && (message.content || message.citations.length > 0) ? (
          <div className="mt-3 border-t border-surface-divider pt-3">
            <MessageCitations citations={message.citations} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
